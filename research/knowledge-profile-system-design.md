# Design Doc: Knowledge Profile System

**Created:** 2026-04-06  
**Status:** Ready for implementation  
**Scope:** Learner knowledge profiles from voice data — storage, retrieval, prompt injection, candidate selection fix

---

## Problem Statement

Voice elicitation captures the richest knowledge data in the system — the user's actual words, connections, uncertainties, what stuck and what didn't. But this data is stored and forgotten:

- **Transcripts are write-only**: stored in `voice_transcripts.transcript`, never queried
- **`captured`/`interesting` fields**: stored in `llm_result` JSON, never read back by any prompt
- **Review prompts are blind**: when generating a review card about Aristotle, the LLM has zero knowledge that the user talked extensively about the Alexander-Aristotle relationship
- **Candidate selection has topic overlap**: the user talked about the 4th Crusade during a Constantinople elicitation, but the system still offers "The Fourth Crusade" as a fresh topic because it was filed under a different node_id
- **Cross-node knowledge is invisible**: if the user mentions Plato during an Aristotle elicitation, the Plato node doesn't benefit

## Current Data

- 18 elicitation transcripts across 5 domains (17 unique nodes)
- 10 voice captures (explore + capture mode)
- Transcript sizes: 97 chars to 7,005 chars (median ~2,500 chars)
- Each has: transcript text, LLM result JSON (captured, missed, interesting, wonderings, research_questions, coverage_pct, suggested_score, feedback_summary)

---

## Architecture

### Core principle: append, don't merge

Store raw transcript chunks with relational links to entities and curriculum nodes. Don't LLM-merge at write time. At read time, retrieve relevant chunks and let the LLM sort them out. If the LLM produces a good summary during read-time processing, cache it alongside (lazy cleanup).

### Transcript chunking strategy

Voice transcripts are typically 200-2000 words of natural speech. Chunking approach:

1. **Split on topic shifts**: Use the LLM result's `captured` array as anchor points. Each captured fact roughly corresponds to a topical segment of the transcript.
2. **Paragraph-level**: Split transcript on natural pauses (sentence boundaries after 100+ words). Most transcripts produce 3-8 chunks.
3. **Overlap**: Include 1 sentence of overlap between chunks to preserve context.
4. **Embed each chunk**: Use limbic.amygdala to generate embeddings for each chunk. Store in `transcript_chunks` table.

For existing transcripts, reprocessing can use a simpler approach: the LLM result already has structured data (captured facts, interesting connections, wonderings). These can serve as pre-chunked summaries without re-splitting the raw transcript.

### New tables

```sql
-- Transcript chunks with embeddings
CREATE TABLE IF NOT EXISTS transcript_chunks (
    id TEXT PRIMARY KEY,
    transcript_id TEXT NOT NULL,  -- FK to voice_transcripts.id
    chunk_text TEXT NOT NULL,
    chunk_type TEXT NOT NULL,  -- 'raw_speech', 'captured_fact', 'interesting', 'wondering', 'feedback'
    embedding BLOB,  -- limbic embedding vector
    created_at TEXT DEFAULT (datetime('now'))
);

-- Many-to-many: chunks ↔ curriculum nodes
CREATE TABLE IF NOT EXISTS chunk_node_links (
    chunk_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    domain_id TEXT NOT NULL,
    relevance REAL DEFAULT 1.0,  -- cosine similarity or manual weight
    PRIMARY KEY (chunk_id, node_id)
);

-- Many-to-many: chunks ↔ entities
CREATE TABLE IF NOT EXISTS chunk_entity_links (
    chunk_id TEXT NOT NULL,
    entity_name TEXT NOT NULL,
    relevance REAL DEFAULT 1.0,
    PRIMARY KEY (chunk_id, entity_name)
);
```

### How chunks are created (write path)

After `run_voice_elicitation()` returns its LLM result:

1. **Extract structured chunks** from the LLM result:
   - Each item in `captured` → chunk_type='captured_fact'
   - Each item in `interesting` → chunk_type='interesting'
   - Each item in `wonderings` → chunk_type='wondering'
   - The `feedback_summary` → chunk_type='feedback'
   - The full transcript → chunk_type='raw_speech' (split into paragraphs if > 500 words)

2. **Embed each chunk** using limbic.amygdala

3. **Link to nodes**: The primary node_id is the elicitation target. But also:
   - Run entity recognition on the transcript (or use entities already extracted)
   - For each entity, look up which curriculum nodes reference that entity via `entity_curriculum_links`
   - Create `chunk_node_links` for each relevant node
   - Example: Aristotle elicitation mentions "Plato" → link to both the Aristotle node AND the Plato node

4. **Link to entities**: Extract entity names from transcript, create `chunk_entity_links`

### How chunks are retrieved (read path)

When generating a review question for node X:

1. **Direct links**: `SELECT chunk_text FROM transcript_chunks tc JOIN chunk_node_links cnl ON tc.id = cnl.chunk_id WHERE cnl.node_id = ?`
2. **Embedding search**: Embed the node description, find top-5 most similar chunks by cosine similarity across ALL chunks (this catches cross-domain connections the relational links might miss)
3. **Combine and deduplicate**: merge both result sets
4. **Format for prompt**: Include as "LEARNER CONTEXT" section in the review prompt

### Voice elicitation candidate selection fix

The current bug: user talks about the 4th Crusade during a Constantinople elicitation → system still offers "The Fourth Crusade" as a fresh topic.

**Fix**: When filtering candidates, check not just `voice_transcripts.node_id` but also `chunk_node_links`. If ANY chunk from ANY elicitation links to a node, reduce that node's priority (don't exclude entirely — the user might want to go deeper).

```python
# In _elicitation_candidates_for_domain():
# Current: exclude nodes with direct voice_transcripts
recent_nodes = {r[0] for r in conn.execute(
    "SELECT node_id FROM voice_transcripts WHERE domain_id = ? AND source = 'elicitation'",
    (domain_id,)
).fetchall()}

# New: also check chunk_node_links
covered_nodes = {r[0] for r in conn.execute(
    "SELECT DISTINCT node_id FROM chunk_node_links WHERE domain_id = ?",
    (domain_id,)
).fetchall()}

# Nodes with direct elicitation: skip
# Nodes covered by cross-node links: penalize score by -0.5 (don't skip)
if node['id'] in recent_nodes:
    continue
if node['id'] in covered_nodes:
    score -= 0.5  # already partially covered by other elicitations
```

---

## Voice Elicitation Prompt Changes

### Current problems
1. The prompt optimizes for grading (captured/missed) rather than knowledge extraction useful to the system
2. Doesn't ask the LLM to identify entities mentioned
3. Doesn't ask for confidence tagging (user's apparent certainty per fact)
4. Doesn't identify the user's organizing framework
5. "Don't know" is a valid response but the system offers topics without checking if the user has already covered them via adjacent nodes

### Revised prompt additions

Add to VOICE_ELICITATION_PROMPT output JSON:

```json
{
  // existing fields...
  "entities_mentioned": ["Alexander the Great", "Plato", "Athens", "Stagira"],
  "confidence_tagged": [
    {"fact": "Aristotle was student of Plato", "confidence": "certain"},
    {"fact": "His father was a tutor to Philip", "confidence": "uncertain"}
  ],
  "organizing_framework": "biographical_arc",  // or "chronological", "geographic", "thematic"
  "cross_domain_connections": [
    {"from": "Aristotle", "to": "French neoclassical drama", "type": "reception_history"}
  ],
  "adjacent_nodes_covered": ["ag_plato", "ag_alexander_and_the_hellenistic_world"]
}
```

The `entities_mentioned` and `adjacent_nodes_covered` fields directly feed the candidate selection fix and the chunk-to-node linking.

### "Don't know" optimization

Currently pressing "Don't know" fires `reportKnowNothing()` which just logs it. It should also:
1. Check if the user already covered this topic via adjacent elicitations (chunk_node_links)
2. If yes, skip it automatically (don't even show the card)
3. If no, record as genuinely unknown and lower the node's priority for future elicitation

---

## Implementation Plan

### Phase 1: Reprocess existing transcripts (test cases)

Write a script that:
1. Reads all 28 existing voice_transcripts
2. For elicitations: extracts chunks from `llm_result` JSON (captured, interesting, wonderings, feedback_summary)
3. For captures: extracts chunks from transcript text (paragraph-split)
4. Embeds each chunk with limbic.amygdala
5. Creates chunk_node_links by:
   a. Primary link to the transcript's node_id
   b. Entity extraction → entity_curriculum_links lookup → secondary node links
6. Creates chunk_entity_links from extracted entities
7. Outputs summary: how many chunks, how many cross-node links, what unexpected connections emerged

This is the test harness. Run it, inspect the results, iterate on the chunking/linking strategy before wiring it into the live pipeline.

### Phase 2: Inject into review prompts

Modify `generate_question()` in review_engine.py:
1. Query `chunk_node_links` for the current node_id
2. Also run embedding search for top-5 similar chunks
3. Format as "LEARNER CONTEXT" section appended to the prompt
4. Measure: does the LLM produce better questions? (Qualitative assessment during review)

### Phase 3: Fix candidate selection

Modify `_elicitation_candidates_for_domain()`:
1. Query `chunk_node_links` to find nodes already partially covered
2. Penalize these nodes in scoring (don't exclude — user might want deeper coverage)
3. Test: does the 4th Crusade still appear after Constantinople elicitation? It shouldn't rank high.

### Phase 4: Update voice elicitation prompt

Add entity extraction, confidence tagging, adjacent_nodes_covered to the LLM output. Wire these into the chunk creation pipeline for new elicitations.

### Phase 5: Domain summaries (the digital twin)

After phases 1-4 are working:
1. For each domain with 3+ elicitations, compile all chunks into a single prompt
2. Ask Opus to synthesize a "learner knowledge portrait" — 1-2 pages covering what the user knows, their framework, connections, interests, gaps, misconceptions
3. Store as a document, regenerate after every 3 new elicitations
4. Use as primary context for all LLM calls in that domain
5. Track diffs between versions as a growth metric

---

## Test Cases (from existing data)

### Test 1: Cross-node coverage detection
- Input: Constantinople transcript mentions "Fourth Crusade in 1204, the Venetians' Doge"
- Expected: chunk_node_links includes both `byzantine__constantinople_as_a_world_city` AND `byzantine__the_fourth_crusade_and_the_sack`
- Validation: candidate selection penalizes "Fourth Crusade" node

### Test 2: Cross-domain entity retrieval
- Input: Generating review card about "The Western Greeks: Why They Came" (Sicily)
- Expected: retrieves chunk from "480 BC: Salamis and Himera" (Ancient Greece) where user talked about Greek colonization
- Validation: review prompt includes cross-domain learner context

### Test 3: Entity aggregation
- Input: Query "what does the user know about Alexander the Great?"
- Expected: finds references from Aristotle elicitation ("Aristotle tutored Alexander, sent specimens back, destroyed Stagira"), from Sicily ("Hellenistic world"), from Ancient Greece ("480 BC" context)
- Validation: aggregated view across all mentions

### Test 4: Embedding-based unexpected connections
- Input: Generating ML card about Arabic philosophical schools
- Expected: embedding search finds Aristotle elicitation (Arabic transmission of Greek philosophy)
- Validation: cross-domain connection surfaced without explicit linking

### Test 5: "Don't know" with existing coverage
- Input: User is shown "The Fourth Crusade" card for voice elicitation
- Expected: system detects that Constantinople elicitation already covered this topic
- Validation: card either doesn't appear or shows "(You discussed this during your Constantinople recall)"

---

## Data Model Summary

```
voice_transcripts (existing)
    ├── transcript (raw text)
    ├── llm_result (JSON: captured, missed, interesting, wonderings, ...)
    └── node_id, domain_id (primary target)

transcript_chunks (new)
    ├── chunk_text (individual fact, connection, wondering, or speech segment)
    ├── chunk_type (captured_fact | interesting | wondering | feedback | raw_speech)
    ├── embedding (limbic vector)
    ├── chunk_node_links → curriculum_nodes (many-to-many)
    └── chunk_entity_links → shared_entities (many-to-many)

Usage:
    generate_question(node_id)
        → SELECT chunks WHERE node_id = X (relational)
        → SELECT top-5 chunks by embedding similarity (semantic)
        → Inject as LEARNER CONTEXT in prompt

    get_elicitation_candidates(domain_id)
        → Check chunk_node_links for already-covered nodes
        → Penalize score for partially-covered nodes
```

---

## Open Questions

1. **Chunk granularity**: Should each `captured` fact be its own chunk, or should we keep them grouped per elicitation? Individual facts are more precise for linking; grouped facts provide better context for prompts.

2. **Embedding model**: limbic.amygdala uses what model? Is it good enough for cross-domain similarity? Might need to test with a few examples.

3. **Reprocessing cadence**: Should domain summaries regenerate after every elicitation, or every 3? More frequent = more responsive but more API cost.

4. **Voice notes integration**: Open-ended voice notes (not tied to curriculum nodes) need entity/topic routing to find the right nodes. This could be a separate script or integrated into the capture pipeline.

5. **Book proxy**: "If I read a book about Alexander the Great and we don't have the text, what do I probably know?" This could be a curriculum-generation task: given a book title + table of contents, generate probable knowledge coverage per curriculum node.

# Connecting Books and Articles: A Focused Proposal

**Date**: 2026-03-22
**Status**: Proposal
**Depends on**: overlapping-curricula-vision.md, reading-companion-process-design.md

## Current State

**Books**: 23 books tracked. 3 actively reading (all Sicily-related). ~10 finished with topic tags. No book research data generated yet (book_research/ directory doesn't exist). Curriculum mappings exist for 2 Sicily books against the Sicily curriculum.

**Articles**: 257 articles, ~4,500 atomic claims with MiniLM embeddings, similarity matrix, novelty scoring, feed ranking.

**Existing connections**: `book_research_agent.py` finds article connections via topic overlap when book research runs. But book research hasn't been run for any books.

**Infrastructure gap**: `build_book_claim_embeddings.py` exists but uses Gemini embeddings (incompatible with article MiniLM embeddings). Not in pipeline.

## Where Connection Makes Sense

### 1. Curriculum as the Bridge (highest value, most principled)

Both books and articles can map to curriculum nodes. The curriculum becomes the meeting ground rather than direct claim-to-claim matching.

**Why this is better than direct matching:**
- Curriculum nodes are curated, pedagogically meaningful — they represent "things worth knowing"
- Avoids the embedding model mismatch problem entirely
- A book chapter about "the siege of Syracuse" and an article about "Archimedes' engineering" both map to the same curriculum node but might not have similar claim text
- Curriculum provides context ("you're learning about this") that raw similarity can't

**What's needed:**
- Embed curriculum node descriptions with MiniLM (same model as article claims)
- Map article claims → curriculum nodes via cosine similarity
- Books already map to curriculum nodes (existing infrastructure)
- Connection: "This article covers [curriculum node] — which you're also reading about in [book]"

### 2. Active Reading Boost in Feed Ranking (simple, immediate value)

When you're actively reading a book with certain topics, articles covering those same topics should get a relevance boost in the feed.

**Implementation**: In `store.ts` feed ranking, check if any article topics overlap with topics of books where `reading_status === 'reading'`. If so, add a small boost to the curiosity score.

**Why it makes sense**: If you're reading "Syracuse: City of Legends," an article about Greek colonization or Sicilian archaeology is more interesting to you right now than it would be otherwise.

**What's needed**: Minimal — book topics already exist, article topics already exist. Just a ranking signal in `store.ts`.

### 3. Chapter-Completion Article Surfacing (natural moment)

When you finish a chapter (chapter advance trigger from the reading companion design), surface 1-2 relevant articles as "further reading."

**Implementation**: Use the curriculum mapping — chapter → curriculum nodes → articles covering those nodes.

**Why it makes sense**: You just read about the Norman conquest. Here's a recent article about medieval Sicily's multicultural legacy. This is a natural extension of the "chapter complete" card.

**What's needed**: Curriculum node → article claim mapping (from point 1 above).

### 4. "Reading Echoes" in Feed (delight, not utility)

When an article in the feed mentions something you've read in a book, show a subtle indicator: "Connects to your reading of [book title]."

**Implementation**: If an article claim maps to a curriculum node that a currently-read book also covers, show the connection.

**Why it makes sense**: The compound effect of reading about the same thing from multiple angles is exactly what makes knowledge sticky (the temporal hooks principle). Making this visible reinforces it.

**What's needed**: Same curriculum-mediated matching as above.

## Where Connection Does NOT Make Sense

### Direct claim-to-claim cross-matching
- Book claims are from LLM-generated chapter summaries (generic, high-level)
- Article claims are extracted from specific articles (detailed, current)
- Different granularity — matching them directly produces noise
- The embedding model mismatch (Gemini vs MiniLM) would need fixing
- Curriculum provides a better abstraction layer

### Forcing all books to connect to articles
- A Norwegian literature history book has no meaningful connection to the tech/history article feed
- Only connect when curriculum overlap exists or topic overlap is strong
- Don't show connections for the sake of showing connections

### Complex recommendation engine
- "Because you read X, you should read Y" is a different problem (book recommendation)
- Keep the scope to "here's how your current reading connects to your articles"
- Let the curriculum + temporal hooks handle the deeper knowledge mapping

## Implementation Plan

### Phase 1: Curriculum Node Embeddings (foundation)
1. Add `embed_curriculum_nodes()` to `curriculum.py` using amygdala MiniLM
2. Save to `data/curricula/embeddings_{domain_id}.npz`
3. One-time cost: ~192 nodes × 384 dims ≈ trivial

### Phase 2: Article → Curriculum Mapping (pipeline addition)
1. In `build_knowledge_index.py`, add a step that maps article claims to curriculum nodes
2. For each claim, find curriculum nodes with cosine ≥ 0.70 (lower than claim-claim 0.74, since node descriptions are broader)
3. Add to knowledge_index.json: `curriculum_claim_map: {domain_id: {node_id: [claim_ids]}}`
4. Inverse: `article_curriculum_nodes: {article_id: [{node_id, count, domain_id}]}`

### Phase 3: Reading Boost in Feed (client-side)
1. In `store.ts`, when computing feed ranking, check active books' topics
2. Articles matching active book topics get +0.15 curiosity boost
3. No server changes needed

### Phase 4: Chapter-Complete Article Suggestions (server-side)
1. When chapter complete triggers, query curriculum nodes for that chapter
2. Find articles mapped to those nodes (from Phase 2 data)
3. Return top 1-2 as "further reading" in the chapter-complete card

### Phase 5: "Reading Echo" Badges (client-side)
1. In ArticleRow, check if article covers curriculum nodes from active books
2. If so, show subtle indicator: "✦ Connects to [book title]"
3. Tap reveals which curriculum nodes overlap

## What NOT to Build

- Don't fix `build_book_claim_embeddings.py` — the curriculum bridge is better
- Don't build a recommendation engine — focus on connections during active reading
- Don't show connections for books that aren't currently being read
- Don't generate book research just for article matching — generate it when it's useful for the reading companion (chapter briefings, reviews)

## Implementation Results (2026-03-22)

### Phase 1: Curriculum Node Embeddings — DONE
- Script: `scripts/build_curriculum_embeddings.py`
- 192 nodes embedded with MiniLM 384d (same model as article claims)
- Saved to server: `data/curricula/curriculum_embeddings.npz`

### Phase 2: Article → Curriculum Node Mapping — DONE
- Threshold calibrated to 0.65 (MiniLM cosine, node descriptions vs atomic claims)
  - 0.70 was too strict (only 45 nodes), 0.45 was noise (matches everything)
  - 0.65: 769 links across 98 articles and 70 curriculum nodes
- Top matches are high quality: "Sicilian Mafia" → "Mafia — Cosa Nostra" (0.88)
- Asymmetry reflects reading: Sicily nodes have most coverage, Greece modest, Rome little
- Saved to server: `data/curricula/article_curriculum_mappings.json`
- Mapping structure: `{node_claims: {domain → {node_id → [claims]}}, article_nodes: {article_id → [nodes]}}`

### Threshold Notes
- MiniLM claim-to-node similarity runs lower than claim-to-claim (node descriptions are broader)
- 0.65 is the equivalent of ~0.74 in claim-to-claim terms (both produce "clearly related" matches)
- Can be calibrated further via card-stack if needed

## Dependencies

- **Curriculum enrichment** (done): dates, prerequisites, cross-curriculum entities
- **Curriculum node embeddings** (done): 192 nodes, MiniLM 384d
- **Article claim → curriculum node mapping** (done): 769 links, threshold 0.65
- **Chapter-complete trigger**: from reading-companion-process-design.md (not yet built)

## Expected Value

The highest-value connection is **Phase 4: chapter-complete article suggestions**. When you finish reading about the siege of Syracuse and the system says "Here's a recent article about Archimedes' mathematical legacy that connects to what you just read" — that's the kind of connection that makes both the book and the article more valuable.

The lowest-effort win is **Phase 3: reading boost**. Five lines of code in `store.ts` to boost articles matching your current reading topics.

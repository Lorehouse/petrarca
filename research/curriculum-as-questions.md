# Curriculum as Structured Questions: Design Research

*Session 41, April 1 2026*

## Problem Statement

The review system generates vague conceptual questions ("What characterized...") despite having rich structured curriculum data (dates, prerequisites, descriptions). The question generation prompt tried to avoid trivial source-text facts but overcorrected by avoiding ALL factual questions. The curriculum already solves "what's worth knowing" — we just aren't using that structure.

## Key Insight: Facts Are Load-Bearing Scaffolding

E.D. Hirsch's Core Knowledge approach (confirmed by reading "What Your Sixth Grader Needs to Know") embeds factual knowledge in compelling narrative. The Core Knowledge Sequence (the specification) defines WHAT students should know; the books deliver HOW.

Our curriculum nodes already mirror this: rich prose descriptions with dates, names, and events embedded. What's missing is extracting those facts into structured, testable form.

The user's framing: "If I know what happened in 1492 in Spain and Italy, that makes anything I read about that period so much more interesting." Facts are the scaffolding that makes deeper reading possible.

## Reference Formats

### AP (College Board) — Most Structured
Hierarchy: Period > Key Concept (KC) > Sub-points > Illustrative Examples
```
KC-1.1.I.A: "Italian Renaissance humanists, including Petrarch,
             promoted a revival in classical literature..."
```
- Key Concepts are testable statements with specific names, dates, movements
- Illustrative examples are optional depth (teachers choose which to cover)
- Very specific about WHAT to know at each level

### IB (International Baccalaureate) — Concept-Driven
- "Understandings": declarative statements ("internal energy is...")
- "Applications and Skills": action verbs (solve, calculate, explain)
- "Linking Questions": cross-references between topics
- Explicitly does NOT do facts-first — embeds facts in conceptual frameworks
- **Not our model** — too skills-focused for knowledge scaffolding

### Core Knowledge (E.D. Hirsch) — Knowledge-Rich
- Specific factual knowledge organized by grade level
- Narrative delivery (prose with embedded dates, names, events)
- Cumulative: knowledge builds year over year
- **Closest to our philosophy** — facts as shared cultural/intellectual scaffolding

## Proposed Schema: `key_facts` on Curriculum Nodes

Each curriculum node gets a `key_facts` JSON array, populated once at curriculum enrichment time:

```json
{
  "key_facts": [
    {
      "type": "date",
      "question": "When was the Battle of Himera?",
      "answer": "480 BC",
      "priority": 1,
      "bloom": "remember"
    },
    {
      "type": "person",
      "question": "Who defeated the Carthaginians at Himera?",
      "answer": "Gelon, tyrant of Syracuse",
      "priority": 1,
      "bloom": "remember"
    },
    {
      "type": "event",
      "question": "What did Gelon build with the spoils of Himera?",
      "answer": "Syracuse into a metropolis, including the Temple of Athena (columns still stand in Syracuse Cathedral)",
      "priority": 2,
      "bloom": "remember"
    },
    {
      "type": "connection",
      "question": "The Battle of Himera was fought the same day as which mainland Greek battle?",
      "answer": "Battle of Salamis (against Persia) — 480 BC",
      "priority": 2,
      "bloom": "understand"
    },
    {
      "type": "significance",
      "question": "Why did Himera matter for Sicilian Greek identity?",
      "answer": "It let Sicilian Greeks claim they were defenders of Hellenism against the same existential threat (Persia/Carthage) that menaced mainland Greece",
      "priority": 3,
      "bloom": "understand"
    }
  ]
}
```

### Fact Types
- **date**: When? What year/century/decade?
- **person**: Who? What was their role?
- **event**: What happened? What was the outcome?
- **connection**: What was happening elsewhere? What came before/after?
- **significance**: Why did this matter? (only after factual foundation is solid)
- **comparison**: How does this compare to X? (review 3+)

### Priority Levels
1. **Load-bearing**: The single most important fact. Test first. (date + key figure usually)
2. **Framework**: Facts that connect this node to others. Test second.
3. **Depth**: Significance, comparison, analysis. Test after priorities 1-2 are solid.

### Bloom Progression (Score-Gated)
- **remember** (priority 1-2): Test until "knew" with stability > 7 days
- **understand** (priority 3): Only unlock after remember facts are solid
- **analyze** (LLM-generated): Only after understand is solid (stability > 14 days)
- **evaluate** (LLM cross-curriculum): Only after analyze (stability > 30 days)

## Enrichment Pipeline

### One-Time Pass Per Curriculum
1. Load all nodes for a curriculum
2. For each node, pass `title + description + date_start + date_end + prerequisites` to LLM
3. LLM extracts 3-6 key_facts in the structured format above
4. Human review (optional but recommended for quality)
5. Store in `key_facts` JSON column on `curriculum_nodes` table

### Why LLM-Assisted, Not Fully Manual
- 719 nodes × 4-5 facts each = ~3,200 facts — too many to hand-write
- Node descriptions already contain the facts in prose form
- LLM extraction is reliable when the source is well-structured curriculum prose (not free-form book text)
- The curriculum ALREADY defines what's important — LLM just reformats

### Why Not Fully Automated
- Quality matters: a bad question tested 50 times is worse than no question
- Review a sample (10-20 nodes per curriculum) to calibrate prompt quality
- Can iterate the extraction prompt based on review

## Question Generation: Deterministic for Facts, LLM for Analysis

### Reviews 1-2: Deterministic from `key_facts`
```python
def get_question_for_review(node, review_count, last_score):
    facts = node['key_facts']
    # Pick highest priority fact not yet tested
    # (tracked via question_history on knowledge_item)
    for fact in sorted(facts, key=lambda f: f['priority']):
        if fact['bloom'] == 'remember' and not already_tested(fact):
            return fact
    # All remember facts tested — cycle through understand
    ...
```
No LLM call needed. Instant. Deterministic. Reliable.

### Reviews 3-4: LLM with Structured Context
Pass the node's key_facts (which the user now knows) plus cross-curriculum context to LLM for analytical questions. The LLM BUILDS ON the factual foundation rather than trying to generate facts from prose.

### Reviews 5+: LLM Cross-Curriculum Synthesis
When multiple related nodes across curricula are solid (stability > 30 days), generate synthesis questions that span the knowledge graph.

## Cross-Curriculum Integration

### Shared Facts via Entities
The 25 cross-curriculum entities (Rome, Syracuse, Athens, etc.) already link nodes across curricula. When the same fact appears in multiple curricula (e.g., "Fall of Constantinople 1453" in both Byzantine and Islamic), it should be:
- **Tested once** (whichever curriculum the user is studying first)
- **Cross-referenced**: "You know this from Byzantine history. In Islamic history, this same event is seen as..."
- **Deduplicated in the review queue**: don't test the same date twice from two curricula

### User Inquiry Integration
- **Microlearning cards** (from follow-up queries) enrich parent node's key_facts if the user demonstrates retention
- **Voice recall wonderings** map to nearest curriculum node and create microlearning
- **Tier 3 proposals** (rare): when inquiry clusters form far from any node, propose new curriculum expansion

## Long-Term User Journeys

### Active Reader (2-3 books/month)
- Month 1-2: Factual recall dominates (dates, names, events)
- Month 3-4: Analytical questions emerge as facts stabilize
- Month 5-6: Cross-curriculum synthesis, capstone questions
- FSRS steady state: ~20-30 due items/day despite growing corpus

### Sporadic Reader (3-week gap)
- Welcome-back triage: 10 curated items, not 80 overdue
- Gap decay: stability × 0.5, not reset to 1.0
- Frame positively: "45 solid facts maintained" not "82 overdue"

### Deep Diver (heavy fractal exploration)
- Auto-expire unreviewed microlearning after 14 days
- Reanchor to curriculum after depth 3 in exploration chain
- Soft inquiry budget per session

## Implementation Plan

### Phase 1: key_facts Enrichment (this session or next)
1. Add `key_facts TEXT DEFAULT '[]'` column to `curriculum_nodes`
2. Write extraction prompt + pipeline script
3. Run on Sicily curriculum (70 nodes) as proof of concept
4. Review quality, iterate prompt
5. Run on remaining 8 curricula

### Phase 2: Deterministic Question Generation
1. Modify `generate_question()` to use key_facts for reviews 1-2
2. Track which facts have been tested in `question_history`
3. Score-gate progression: don't escalate Bloom level until facts are solid

### Phase 3: Cross-Curriculum and Synthesis
1. Deduplicate shared facts across curricula
2. Generate bridge questions when related nodes are stable
3. Capstone synthesis questions for mature knowledge clusters

## References
- E.D. Hirsch, "Cultural Literacy" (1987) — the original case for shared factual knowledge
- E.D. Hirsch, "What Your Sixth Grader Needs to Know" (1993) — Core Knowledge Series
- Core Knowledge Sequence — the specification (coreknowledge.org)
- AP European History Curriculum Framework — College Board (publicly available)
- Design research agent analysis (session 41) — cross-curriculum, user journeys, Bloom progression

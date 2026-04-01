# Curriculum as Structured Questions: Design Research

*Session 41 (initial), Session 42 (revised design + implementation)*

## Problem Statement

The review system generates vague conceptual questions ("What characterized...") despite having rich structured curriculum data (dates, prerequisites, descriptions). The question generation prompt tried to avoid trivial source-text facts but overcorrected by avoiding ALL factual questions. The curriculum already solves "what's worth knowing" — we just aren't using that structure.

## Key Insight: Facts Are Load-Bearing Scaffolding

E.D. Hirsch's Core Knowledge approach embeds factual knowledge in compelling narrative. The Core Knowledge Sequence defines WHAT students should know; the books deliver HOW.

Our curriculum nodes already mirror this: rich prose descriptions with dates, names, and events embedded. What's missing is extracting those facts into structured, testable form.

The user's framing: "If I know what happened in 1492 in Spain and Italy, that makes anything I read about that period so much more interesting." Facts are the scaffolding that makes deeper reading possible.

## Design Decisions (Session 42)

### No Bloom Taxonomy

The original design used Bloom levels (`remember`, `understand`, `analyze`, `evaluate`) to gate question progression. **Dropped in session 42** because:
- A "connection" question like "Himera was fought the same day as which Greek battle?" was classified as `understand` but it's pure recall
- Bloom levels were being used as a proxy for dependency ordering, which is better handled by priority + type
- The cognitive classification added complexity without changing behavior

### No Explicit Dependencies (`depends_on`)

The original design had explicit `depends_on` arrays between facts. **Dropped** because:
- Pattern-based ordering handles 90% of cases: `event → date → person → connection → significance` maps naturally to priority 1 → 2 → 3
- "Don't ask when X happened if we don't know what X is" is a heuristic, not a per-fact dependency
- Cross-node dependencies are already handled by `curriculum_prerequisites` (the DAG between nodes)
- Entity intro cards handle the remaining edge case (unknown entities referenced in a question)
- Getting the wrong answer is a learning opportunity, not a failure — the rich_answer teaches context

### Entity References on Every Fact

Every key_fact has an `entities` array linking to `shared_entities`. This enables:
- **Cross-curriculum dedup**: same entity + same fact type = test once, credit both curricula
- **Entity exploration portals**: tap an entity → map, timeline, all facts about it, "tell me more"
- **Entity intro cards**: system knows which entities a fact requires, can insert intros for unknown ones
- **Depth tracking**: how many facts does the user know about entity X across all curricula?

### Rich Cards from Structured Data (not just LLM prose)

Every card flip is a learning opportunity. Rich context can often be composed from structured data:
- **DATE facts**: mini-timeline from other known dates within ±100 years
- **PLACE facts**: map pin from `shared_entities.latitude/longitude` + nearby known places
- **PERSON facts**: entity card with dates, locations, per-curriculum lenses
- **CONNECTION facts**: both entities side by side with knowledge states

Pre-written `rich_answer` text is a fallback for significance/analytical facts where templates don't work. The client renders structured data when available, falls back to rich_answer text.

### Growing Knowledge Map: Entities Accumulate Depth

**Curricula are bounded** (that's the point — a teacher made deliberate choices). But **entities grow** as the user goes deeper.

Three mechanisms:
1. **Microlearning promotion**: when a microlearning card survives review (stability > 7 days), its core fact promotes to the entity
2. **Book-evidence extraction**: when 3+ book chapters reference the same entity, extract additional facts from accumulated evidence
3. **Auto-curriculum generation** (future): when entity depth is sufficient, generate a focused curriculum (e.g., "Plato: A Semester Course" from accumulated Plato knowledge)

This means `shared_entities` can also have a `key_facts` column — entity-level facts that supplement curriculum-level facts.

## Finalized Schema: `key_facts` on Curriculum Nodes

```json
{
  "key_facts": [
    {
      "id": "himera_date",
      "type": "date",
      "priority": 1,
      "question": "In what year was the Battle of Himera fought?",
      "answer": "480 BC — tradition holds it was fought on the very same day as the Battle of Salamis in Greece.",
      "entities": ["himera", "gelon"]
    },
    {
      "id": "himera_who",
      "type": "event",
      "priority": 1,
      "question": "Who won the Battle of Himera and against whom?",
      "answer": "The tyrant Gelon of Syracuse crushed a massive Carthaginian invasion on Sicily's north coast.",
      "entities": ["gelon", "syracuse", "carthage", "himera"]
    },
    {
      "id": "himera_salamis",
      "type": "connection",
      "priority": 2,
      "question": "How does the Battle of Himera connect to events on mainland Greece?",
      "answer": "Greek tradition held that Himera and Salamis occurred on the same day, as a coordinated Persian-Carthaginian assault on the Greek world.",
      "rich_answer": "The synchronicity was probably propaganda — Sicilian Greeks claimed Himera happened on the very day of Salamis, framing themselves as co-defenders of the Greek world against 'barbarian' invasion. Whether literally true or not, the pairing embedded Sicilian Greeks firmly in the Panhellenic narrative.",
      "entities": ["gelon", "himera", "carthage", "syracuse"]
    },
    {
      "id": "himera_significance",
      "type": "significance",
      "priority": 3,
      "question": "Why did Gelon's victory at Himera reinforce tyranny in Sicily?",
      "answer": "The victory demonstrated that a strongman could save Greek civilization, intertwining tyranny with military glory in ways that scandalized democratic Athens.",
      "rich_answer": "...",
      "entities": ["gelon", "syracuse", "himera"]
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

### Priority Levels
1. **Load-bearing** (2-3 per node): The essential facts. Dates, key figures, key events. Short answers, no rich_answer needed.
2. **Framework** (1-2 per node): Facts connecting this node to others. Include rich_answer for teaching moment.
3. **Depth** (0-1 per node): Significance, long-term consequences. Include rich_answer.

### Ordering Heuristic (replaces Bloom gating)
- Priority 1 before priority 2 before priority 3
- Within same priority: event → date → person → connection → significance
- Cross-node ordering via `curriculum_prerequisites` (existing DAG)
- Entity intro cards inserted for unknown entities referenced in upcoming questions

## Enrichment Pipeline

### Batch-by-Area Extraction

Curricula are processed in batches by level-1 area (not node-by-node, not full-curriculum-at-once):
- Each batch: 6-14 related nodes + relevant entities from `shared_entities`
- LLM sees enough context for cross-node connections within an area
- Output is reviewable (~50-70 facts per batch)
- Entity tagging uses canonical IDs from entity list; provisional IDs for unlisted entities

### Script: `scripts/extract_key_facts.py`

```bash
# Extract one area (proof of concept)
python extract_key_facts.py --curriculum sicily_history_culture_and_legacy --area 0 --entities /tmp/sicily_entities.json

# Extract all areas
python extract_key_facts.py --curriculum sicily_history_culture_and_legacy --entities /tmp/sicily_entities.json

# Dry run (show prompt)
python extract_key_facts.py --curriculum sicily_history_culture_and_legacy --area 0 --dry-run

# Load results into SQLite
python extract_key_facts.py --load results/sicily_key_facts.json
```

Uses `claude -p` for Opus quality. Results saved to `scripts/key_facts_results/`.

### Sicily Greek Area: Proof of Concept Results (Session 42)

Extracted 66 facts across 14 nodes (4.7 avg per node), 152 entity references.
Quality assessment:
- P1 facts are concrete dates/events/people — no vague "characterized by" questions
- P2 connections are cross-node and cross-curriculum (Agathocles→Scipio, Archimedes→Cicero)
- Entity tagging includes good provisional IDs for entities not yet in DB (dion, aeschylus, cicero, gorgias, thucydides)
- rich_answer only on P2-3 facts as designed

## Question Generation: Deterministic for Facts, LLM for Analysis

### Reviews 1-2: Deterministic from `key_facts`
```python
def get_question_for_review(node, review_count, question_history):
    facts = node['key_facts']
    # Pick highest priority untested fact
    for fact in sorted(facts, key=lambda f: f['priority']):
        if fact['id'] not in question_history:
            return fact
    # All facts tested — pick lowest-scoring for retry
    ...
```
No LLM call needed. Instant. Deterministic. Reliable.

### Reviews 3+: LLM with Structured Context
Pass the node's key_facts (which the user now knows) plus cross-curriculum context to LLM for analytical questions. The LLM BUILDS ON the factual foundation.

## Four-Layer Data Architecture

### Layer 1: Curriculum Structure (long-lived, rarely changes)
- `curriculum_nodes` + `key_facts` — framework + testable facts
- `curriculum_prerequisites` — DAG between nodes
- `shared_entities` — people, places, events with coords, dates
- `entity_curriculum_links` — entity↔node mapping with lenses

### Layer 2: User Knowledge State (long-lived, slowly evolving)
- `knowledge_states` — per-node: knowledge level, interest, confidence
- `knowledge_items` — per-node review scheduling: stability, due date, sources, question_history

### Layer 3: Content & Evidence (grows with pipeline + reading)
- Articles, claims, embeddings, similarity pairs
- Book chapters → node mapping → sources array on knowledge_items
- Voice recall → analysis → knowledge state updates
- Microlearning cards → entity-level depth accumulation

### Layer 4: Review Card (ephemeral, generated per request)
- `cached_question` on knowledge_items — regenerated when stale
- Review stream assembly: scoring, ordering, domain interleaving
- Entity span annotations, entity intro cards
- Rich context composition from structured data

## Cross-Curriculum Integration

### Shared Facts via Entities
The 54+ entities per curriculum link nodes across curricula. When the same fact appears in multiple curricula (e.g., "Fall of Constantinople 1453" in both Byzantine and Islamic), it should be:
- **Tested once** (whichever curriculum the user encounters first)
- **Cross-referenced**: "You know this from Byzantine history. In Islamic history, this same event is seen as..."
- **Deduplicated in the review queue** via shared entity_ids on key_facts

### Entity Depth Accumulation
When a user goes deep on a topic (multiple books, microlearning, voice recall), depth accumulates on the **entity**, not the curriculum node:
1. Promoted microlearning facts → entity key_facts
2. Book-evidence extraction → entity key_facts
3. Future: auto-generate entity-focused curricula when depth is sufficient

## Implementation Plan

### Phase 1: key_facts Enrichment ← CURRENT (Session 42)
1. ✅ Add `key_facts` column to `curriculum_nodes` (migration in db.py)
2. ✅ Write `extract_key_facts.py` with batch-by-area approach
3. ✅ Run on Sicily Greek area (14 nodes, 66 facts) — quality validated
4. Run on remaining 6 Sicily areas
5. Run on remaining 8 curricula (need entity data per curriculum)
6. Load into server SQLite

### Phase 2: Deterministic Question Generation
1. Modify `generate_question()` to use key_facts for reviews 1-2
2. Track which fact IDs have been tested in `question_history`
3. Priority-gated progression: don't show P2 until P1 facts are known

### Phase 3: Rich Card Rendering
1. Structured data composition (timeline, map, entity cards) on client
2. Fallback to rich_answer text when structured data insufficient

### Phase 4: Cross-Curriculum and Entity Depth
1. Deduplicate shared facts across curricula via entity IDs
2. Microlearning promotion to entity key_facts
3. Entity-focused auto-curriculum generation (when depth is sufficient)

## References
- E.D. Hirsch, "Cultural Literacy" (1987)
- Core Knowledge Sequence — coreknowledge.org
- AP European History Curriculum Framework — College Board
- Session 41 review consolidation memory
- Session 34 overlapping curricula vision (`research/overlapping-curricula-vision.md`)

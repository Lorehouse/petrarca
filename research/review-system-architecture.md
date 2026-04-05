# Knowledge Review System — Architecture & Long-Term Design

**Created:** 2026-03-27
**Updated:** 2026-04-05 (session 54: overlapping-curricula implementation)
**Status:** Core architecture implemented. Cross-curriculum features (multi-domain mapping, nexus cards, temporal cross-refs) added in session 54. Some UI integration still pending.
**Context:** Written after first end-to-end test with Syracuse book, 42 review items, autoresearch on question quality

---

## 1. The Fundamental Flaw in the Current Model

The current system creates one `review_item` per **(curriculum_node × book_chapter)**. This conflates two things that should be separate:

| Concept | What it is | Should be stored as |
|---------|------------|---------------------|
| **Reading event** | "Chapter 3 of the Syracuse book covered Gelon and Himera" | A source record |
| **Knowledge state** | "My understanding of Gelon and the Battle of Himera" | A knowledge item |

The result of conflating them:

- "Which city founded Naxos?" appears **7 times** in 42 items — because 2 chapters both mapped to the same node "The Western Greeks: Why They Came"
- The Athenian Expedition node exists in the curriculum but has **zero review items** because no chapter strongly mapped to it
- Adding a second book on Sicily or Greece would **not enrich existing review items** — it would create a third, fourth, fifth copy of the same question
- Stability scheduling operates on the (node × chapter) pair, not on the concept — so reviewing "Gelon" in one item doesn't reduce the due urgency of the duplicate "Gelon" item from another chapter

**The correct unit of knowledge is the curriculum node, not the (node × source) pair.**

---

## 2. What the Data Model Should Be

### Current (wrong)
```
review_items:
  id: "ri_syracuse_ch3_age_of_tyrants"
  curriculum_node_id: "sicily_his_the_age_of_tyrants"
  source_book_id: "syracuse_city_of_legends"
  source_chapter_number: 3
  source_text: "..."   ← ONE source, baked in
  stability_days: 1.0
  due_at: ...
  cached_question: ...
```

### Correct (proposed)
```
knowledge_items:
  id: "ki_sicily_his_the_age_of_tyrants"   ← ONE per curriculum node
  curriculum_node_id: "sicily_his_the_age_of_tyrants"
  curriculum_domain: "sicily_history_culture_and_legacy"
  stability_days: 1.0
  due_at: ...
  review_count: 0
  sources: [                               ← accumulates over time
    {
      book_id: "syracuse_city_of_legends",
      chapter_number: 3,
      chapter_title: "The Tyrants and Democracy",
      source_text: "Gelon defeated Carthage at Himera in 480 BC...",
      added_at: 1234567890
    },
    {
      book_id: "peloponnesian_war_kagan",   ← added when second book read
      chapter_number: 7,
      chapter_title: "Sicily and Athens",
      source_text: "Thucydides' account of the Sicilian background...",
      added_at: 1234999999
    }
  ]
  cached_question: ...
```

**Key change:** When a new chapter maps to an existing node, it **adds a source** rather than creating a duplicate item. The node's stability/scheduling is unaffected (you already know this concept). If the new source adds significantly new information, a small stability nudge could be applied (optional).

---

## 3. Coverage: How to Ensure the Whole Curriculum Gets Reviewed

### The current problem
Review items are created reactively — only when a chapter is marked complete AND the LLM decides that chapter covers a node. Nodes that aren't strongly represented in any chapter go unreviewed indefinitely.

With the Syracuse book:
- **Well covered:** Greek colonization, Gelon/Himera, Dionysius I, Archimedes, Byzantines/Arabs, Normans, Baroque
- **Missing:** Athenian Expedition (415-413 BC) — the most dramatic event in Syracusan history
- **Missing:** Agathocles' full story, the Roman province system in depth, Hiero II's treaty with Rome

### The solution: proactive coverage pass

After completing a book (or periodically), run a **gap analysis**:

```python
def identify_coverage_gaps(book_id, curriculum_domain):
    all_nodes = get_curriculum_nodes(curriculum_domain, min_level=2)
    covered_nodes = get_nodes_with_knowledge_items(curriculum_domain)

    uncovered = [n for n in all_nodes if n['id'] not in covered_nodes]

    # For each uncovered node, check if book research mentions it
    # If yes: create a knowledge_item with source from book research
    # If no: flag as "gap — needs a source"

    return uncovered
```

Then offer the user: *"5 curriculum nodes aren't covered yet. Want to add them from the book research?"*

For nodes with no book source, they should appear occasionally in the review queue as **discovery cards** — "Here's something you haven't encountered yet in your reading" — with the curriculum description as context, not a question. The learner can rate their prior knowledge, and it gets scheduled accordingly.

### Temporal coverage requirement
A well-covered curriculum should include at least **one question per 200-year period** for history curricula. This can be checked automatically.

---

## 4. How This Works Across Multiple Books

### Scenario: adding a second book on Sicilian history
*"Roger II: The First European" by John Julius Norwich*

When you finish Chapter 4 (The Kingdom of Sicily):
1. MAP_CHAPTER_PROMPT maps to nodes: Norman Conquest, Arab-Norman Synthesis, Roger II
2. "The Norman Conquest of Sicily" already has a `knowledge_item` (from Syracuse book)
3. **New behavior:** Add Norwich's chapter as a second source to the existing item
4. The question generator now has TWO sources to draw from — can pick the most interesting angle, or explicitly compare ("The Syracuse book described Roger I as a military leader; Norwich emphasizes his administrative genius. Which aspect stands out to you?")
5. The stability/scheduling is unchanged — you already know this concept

### Scenario: adding a book from a different but overlapping curriculum
*"Justinian's Flea: Plague, Empire and the Birth of Europe" by William Rosen*

This maps primarily to a **Byzantine Empire** curriculum (not yet built). But it touches:
- Belisarius's reconquest (already in Sicily curriculum: "Late Antiquity and Byzantine Sicily")
- The Arab invasions of Byzantine territory (leads into Sicily's Arab conquest)
- Justinian's legal code

**What should happen:**
1. The Byzantine curriculum is created/loaded
2. Knowledge items are created for Byzantine nodes
3. **Cross-curriculum links** are established: Belisarius appears in BOTH Sicily and Byzantine curricula
4. The existing Sicily knowledge_item for "Late Antiquity and Byzantine Sicily" gets Rosen's chapter added as a source with a `cross_curriculum_link: "byzantine_his_belisarius_and_the_reconquest"`
5. Review questions can now explicitly reference both curricula: "You've read about Belisarius in both a Sicilian and Byzantine context — what was his significance in each?"

### Scenario: reading a thematic book that touches many curricula
*"The Fate of Rome: Climate, Disease, and the End of an Empire" by Kyle Harper*

This touches: Roman History, Byzantine history, Sicily, maybe Islamic expansion. It doesn't map cleanly to any single curriculum. But:
- Each chapter that covers a node already in any curriculum should add a source
- New nodes it introduces (climate/plague as historical force) might warrant a new "Thematic Frameworks" curriculum or just tagged as cross-cutting claims
- The book research agent's `chapter_research` still works — the chapter context is available for source_text

---

## 5. Multi-Curriculum Architecture

### Active curricula (as of session 54)
9 curricula generated, 6 active (with knowledge_items):

| Curriculum | Nodes | Knowledge Items | Status |
|------------|-------|----------------|--------|
| Sicily | 70 | 38 | Active, deep engagement |
| Rome | 55 | 42 | Active |
| Ancient Greece | 67 | 60 | Active |
| Byzantine | 86 | 56 | Active |
| Islamic Civilization | 89 | 41 | Active |
| Classical Reception | 106 | 19 | Active, early stage |
| AP European History | 95 | 0 | Generated, not yet activated |
| AP World History Modern | 78 | 0 | Generated, not yet activated |
| Ancient & Classical World | 73 | 0 | Generated, not yet activated |

### Cross-curriculum features — IMPLEMENTED (Session 54)

**Multi-domain chapter mapping**: `create_review_items_for_chapter()` maps each chapter against top-2-3 curricula (embedding similarity >= 0.40), not just the primary domain. A Syracuse book now creates knowledge_items in Sicily AND Rome AND Greece.

**Cross-curriculum context in questions**: `_get_cross_curriculum_context()` queries `entity_curriculum_links` + `knowledge_states` across domains. When generating a question about the Arab Conquest in Sicily, the prompt includes: "the learner already knows about the Byzantine Empire from the Islamic Civilization curriculum (engaged)."

**Temporal cross-references**: `_get_temporal_cross_references()` finds contemporaneous events from other curricula (50-year overlap window). For Arab Conquest (~878 AD): "Meanwhile in Islamic Civilization: The Abbasid Revolution (~750 AD), The House of Wisdom (~750 AD), Al-Andalus (~711 AD)."

**Entity nexus cards**: When a review card references an entity with `nexus_score >= 3`, `_insert_nexus_cards()` adds a cross-perspective card: "You know Byzantine Empire from Sicily. How does their role differ in this context?" Currently 2 qualifying entities: Carthage, Byzantine Empire.

**Book pre-scan**: `GET /book/prescan/{book_id}` shows what the learner already knows, what's new, missing prerequisites, and cross-book overlaps. For Syracuse book: 16 known, 19 new, 10 missing prerequisites, 2 cross-book overlaps.

### Still TODO

1. **Client rendering of nexus cards** — `type: 'nexus'` returned in stream but review.tsx doesn't have a component for them yet
2. **Client integration of book prescan** — endpoint works but no UI
3. **Cross-curriculum stability adjustment** — reviewing a concept in one domain doesn't yet partially credit the same concept in another domain
4. **Node deduplication across curricula** — linked but not deduplicated. Sicily: "The Arab Conquest of Sicily" and Islamic: "The Aghlabid Conquest" are separate knowledge_items. Could be linked via shared_entities.

---

## 6. The Review Session at Scale

### Current problem
10 items due today, drawn by `due_at`. No guarantee of breadth, no awareness of which periods are over-represented.

### Better session design

**Session composition** (for a 10-card session):
- 6 items: due today (spaced repetition core)
- 2 items: "breadth cards" — nodes from underrepresented periods in recent sessions
- 1 item: "discovery card" — a curriculum node with no knowledge_item yet, shown as context not question
- 1 item: "cross-curriculum synthesis" — only when ≥2 curricula active and a nexus point is available

**Within-session breadth constraint:**
Don't show more than 3 cards from the same historical period in one session. If 8 Greek colonization items are due, spread them across multiple sessions while surfacing items from other periods.

**Session vs. coverage tracking:**
Track `period_coverage_score` — what fraction of 200-year periods in the active curricula have at least one "known" knowledge item. Show this as a progress metric in the Review tab header.

---

## 7. Stability Semantics with Multiple Sources

When a knowledge_item has multiple sources (multiple books covering the same node), how should scoring work?

**Proposed:**
- `knew` on a single-source item: stability × 2.5 (current)
- `knew` on a multi-source item with synthesis question: stability × 3.0 (harder question, bigger reward)
- `missed` always resets to 1.0 day regardless of source count
- Adding a new source to an existing `knew` item: no stability change, but `cached_question` cleared so next question can reference the new source
- Adding a source to a `missed` item: small stability nudge (+20%) since new context may help encode it

---

## 8. Question Generation at Scale

### What changes with node-centric model

**Review count 1 (first encounter):** Draw from node description + one source_text. Basic recall question (current approach — this is working well after autoresearch).

**Review count 2:** Different aspect of the same node. If there are multiple sources, draw from a different one than review 1. The `question_history` field tracks which aspects have been tested.

**Review count 3+:** Analytical lens questions. If multiple sources exist, compare them: "The Syracuse book emphasizes X; Norwich emphasizes Y. Which do you find more significant?"

**Cross-curriculum review (special):** "You've encountered [entity] in both [curriculum A] and [curriculum B]. How do the two perspectives differ?" — triggered when learner has `knew` in both linked knowledge_items.

### Tracking what's been asked

Add `question_history: [{question, score, ts}]` to knowledge_items. The question generator receives this and explicitly avoids repeating the same aspect. This prevents "Which city founded Syracuse?" from being asked at review 7 when Dionysius I, Archimedes, and the Athenian Expedition have never been the focus.

---

## 9. Measurement: Does the Learner Actually Know the History?

### The skeletal understanding test

A learner has "decent skeletal understanding" of a history curriculum if they can:
1. Name the major figures in each major period
2. Roughly order events chronologically (within ±50 years for events >500 years ago)
3. Name the major turning points (events that changed who controlled the territory)
4. Know one distinctive fact about each major period (what was unique or surprising)

For Sicily specifically, this means: Archias/733 BC → Gelon/Himera/480 BC → Dionysius I/Euryalus → Athenian Expedition/415-413 BC → Rome/212 BC → Archimedes → Belisarius/535 AD → Constans II/663 AD → Arab conquest/878 AD → Roger I/1091 AD → Al-Idrisi/Roger II → Sicilian Vespers/1282 → Spanish rule → 1693 earthquake.

**A learner who knows all the unique facts in the current 42 items does NOT yet have skeletal understanding** — the Athenian Expedition is missing, and 7 slots are wasted on "Which city founded Naxos?".

### Automated coverage score

```python
def compute_skeletal_coverage(curriculum_domain) -> dict:
    curriculum = load_curriculum(curriculum_domain)
    knowledge_items = get_knowledge_items(curriculum_domain)

    # Level 2 nodes are "major topics" — should all have items
    level2_nodes = [n for n in curriculum['nodes'] if n['level'] == 2]
    covered_level2 = [n for n in level2_nodes
                      if any(ki['curriculum_node_id'] == n['id']
                             for ki in knowledge_items)]

    # Temporal coverage: unique 200-year periods with ≥1 known item
    periods = get_temporal_periods(curriculum)  # from date_start/date_end
    covered_periods = [p for p in periods if any_item_in_period(p, knowledge_items)]

    return {
        'level2_coverage': len(covered_level2) / len(level2_nodes),
        'temporal_coverage': len(covered_periods) / len(periods),
        'unique_facts': count_unique_facts(knowledge_items),  # deduplicated
        'skeletal_score': geometric_mean([level2_coverage, temporal_coverage])
    }
```

### Measurement hypotheses (in priority order)

| Hypothesis | Measure | Target |
|------------|---------|--------|
| H_coverage: every Level-2 node has ≥1 knowledge item | `level2_coverage` score | >90% |
| H_uniqueness: questions test distinct facts | Jaccard similarity between cached questions | <0.3 between any two items for same node |
| H_temporal_spine: learner can order events | Ask 5 "which came first?" pairs after 2 reviews | >80% correct |
| H_retention_gain: knew rate improves with source richness | Compare knew% for single-source vs multi-source items | Multi-source >single-source by >10% |
| H_cross_curriculum: synthesis questions perform better | Compare time-to-reveal and score for synthesis vs single-curriculum questions | (measure first, no target) |

---

## 10. Implementation Roadmap

### Phase 1 — Fix the current system (immediate, before adding more books)

1. **Migrate review_items to node-centric model:**
   - Merge all items with the same `curriculum_node_id` into one, combining source_texts
   - Keep the best stability/scheduling from the set
   - This eliminates the 7-duplicate "Naxos" problem immediately

2. **Gap analysis + Athenian Expedition:**
   - Run coverage check against all Level-2 Sicily nodes
   - For missing nodes, check book_research for mentions, create lightweight items
   - Specifically: create knowledge_item for Athenian Expedition using curriculum description

3. **Question deduplication logic:**
   - After generating a question, check it against `question_history` for that node
   - If too similar (cosine > 0.85), generate another question targeting a different aspect

### Phase 2 — Multi-source support (before reading second book)

1. Change `create_review_items_for_chapter` to upsert (add source) not insert
2. Question generator picks source based on review_count (cycle through sources)
3. `question_history` field to avoid repeating aspects

### Phase 3 — New curricula + cross-curriculum review

1. Build Byzantine, Islamic, Roman curricula (Opus-only generation)
2. Cross-curriculum entity matching: when adding a new curriculum, auto-detect nodes that match existing cross_curriculum_entities
3. Cross-curriculum review question type (triggered at nexus points)
4. Session composition logic: breadth cards + discovery cards

### Phase 4 — Coverage tracking in UI

1. `skeletal_coverage` score visible in Review tab
2. Per-period coverage visualization (timeline of covered/uncovered periods)
3. "Gap cards" — surfacing uncovered Level-2 nodes as discovery items
4. "You've read about X in 3 books now — here's a synthesis question" notifications

---

## 11. What Good Looks Like at 12 Months

After reading ~10 books touching on Sicily, Byzantine, Islamic, and Norman history:

- **~150-200 knowledge items** across 4-5 curricula (not 42 × number of books)
- Each item has **2-5 sources** from different books — questions can now draw on multiple perspectives
- **Cross-curriculum synthesis questions** regularly appearing in sessions
- **>90% Level-2 coverage** in Sicily, Byzantine, and Islamic curricula
- Review sessions are genuinely varied — the same fact is never asked twice in a row, analytical questions appear from review 3 onward, synthesis questions from review 5+
- Skeletal understanding of the connected history from 700 BC (Greek colonization) through 1700 AD (Baroque Sicily) is solid — learner can place events in order, name major figures, describe turning points

The system serves the user's stated goal: reading broadly across overlapping topics (Sicily, Byzantium, Islam, Rome, Medieval Italy) and building a coherent connected understanding — not siloed per-book knowledge that's reviewed in isolation.

---

## 12. The Question that Should Guide Every Design Decision

*"If I read 15 books on overlapping topics over the next 2 years and never touched the review system directly, what would it do with that?"*

The answer right now: create ~600 review_items, 70% of which are duplicates, with some periods totally uncovered and others reviewed 12 times. The session would be full of "Which city founded Naxos?" variants.

The answer after Phase 1-3: ~180 knowledge_items, each enriched by multiple sources, with full Level-2 coverage, synthesis questions appearing as sources accumulate, and cross-curriculum connections surfaced when they become meaningful.

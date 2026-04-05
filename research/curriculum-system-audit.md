# Curriculum System: Audit & Architecture (Session 54)

**Date**: 2026-04-05
**Status**: Reference document — comprehensive audit of curriculum system design, usage, and value

## Purpose of This Document

The multiple overlapping curriculum system was introduced at one stage of development, and over 47+ sessions a huge amount of functionality has been built around it. This document audits where the curriculum earns its keep, where it's under-utilized, and what was built to close the gaps.

---

## 1. What the Curriculum System Is

The system has **9 pre-generated curricula** with **719 total nodes** organized into hierarchical trees (Area -> Topic -> Concept, max 4 levels). Each curriculum is modeled on a rigorous college course: 50-80 concepts, deliberately bounded, with prerequisite DAGs.

### Database Tables

| Table | Purpose | Scale |
|-------|---------|-------|
| `curriculum_domains` | 9 domain definitions | 9 |
| `curriculum_nodes` | Node trees with descriptions, dates, key_facts | 719 |
| `curriculum_prerequisites` | DAG of prerequisite relationships | ~2000 |
| `knowledge_states` | Per-node knowledge level (unknown/mentioned/engaged/anchored) | 248 |
| `knowledge_items` | Per-node review scheduling (FSRS) + source accumulation | 256 |
| `shared_entities` | Cross-curriculum entity registry | 261 |
| `entity_curriculum_links` | Entity-to-node connections with lens data | 511 |
| `book_curriculum_mappings` | Book-to-node coverage mappings | ~300 |
| `article_curriculum_nodes` | Article claim-to-node mappings | 378 |

### Active vs Inactive

| Domain | Nodes | Knowledge Items | States |
|--------|-------|----------------|--------|
| Sicily | 70 | 38 | 69 tracked |
| Rome | 55 | 42 | 51 tracked |
| Ancient Greece | 67 | 60 | 38 tracked |
| Byzantine | 86 | 56 | 49 tracked |
| Islamic Civilization | 89 | 41 | 40 tracked |
| Classical Reception | 106 | 19 | 0 |
| AP European History | 95 | 0 | 0 |
| AP World History Modern | 78 | 0 | 0 |
| Ancient & Classical World | 73 | 0 | 0 |

---

## 2. Where Curriculum Earns Its Keep

### 2.1 Review Card Deduplication — ESSENTIAL

Without curriculum nodes as the unit, duplicate questions proliferate (the old approach produced 7 copies of "Which city founded Naxos?" from different chapters). The curriculum node is the dedup key: no matter how many books mention Archimedes, there's one `knowledge_item` with accumulating sources.

### 2.2 Knowledge State Tracking — ESSENTIAL

`knowledge_states` tracks per-node levels: unknown -> mentioned -> engaged -> anchored (never downgrades). 60-80 nodes per domain is cognitively manageable: "I know 45/67 Ancient Greece concepts" is meaningful and motivating.

### 2.3 Voice Elicitation — ESSENTIAL

`get_elicitation_candidates()` uses curriculum nodes as the curated list of topics to ask about, with knowledge states driving which to prioritize (medium-confidence engaged nodes at the 0.5 sweet spot).

### 2.4 Deterministic Questions — ESSENTIAL

`key_facts` on curriculum nodes enable instant question generation without LLM calls. First 1-2 reviews per node are deterministic from structured fact data.

### 2.5 Statistics Dashboard & Knowledge Atlas — ESSENTIAL

The motivational "I'll manage your memory" promise requires visible progress: knowledge bars per curriculum, knowledge atlas visualization. Without curriculum, no map.

### 2.6 Microlearning Cards — MODERATE

ML cards use `{node_title}: {node_description}` as context in the prompt and propagate quiz scores back to the parent curriculum node. Useful but not structurally required.

### 2.7 Article Pipeline — MODERATE

Articles map to curriculum nodes via `article_curriculum_nodes`, feeding novelty detection. Complementary to claim-level similarity, not essential.

### 2.8 Gap-Fill — LOW (Improved in Session 54)

Previously created speculative items for prerequisites AND siblings within 200 years. Narrowed to prerequisites only, enriched with book_curriculum_mappings data when available.

---

## 3. Where Curriculum Was Under-Utilized (Fixed in Session 54)

### 3.1 Single-Domain Book Mapping — THE BIGGEST GAP

`detect_curriculum()` returned ONE domain per book. A Syracuse book only mapped to Sicily, not Rome or Greece. **Fixed**: `create_review_items_for_chapter()` now uses `suggest_curricula_for_book()` to map against top-2-3 curricula with similarity >= 0.40.

### 3.2 No Cross-Domain Context in Questions

Questions only referenced known nodes from the same domain. **Fixed**: `_get_cross_curriculum_context()` queries `entity_curriculum_links` + `knowledge_states` across domains to include "what the learner knows from other perspectives."

### 3.3 No Temporal Cross-References

The `date_start`/`date_end` fields existed but weren't used for cross-domain connections. **Fixed**: `_get_temporal_cross_references()` finds contemporaneous events from other curricula (50-year window), adds "Meanwhile in..." context.

### 3.4 Entity Nexus Points Unused

`shared_entities` (261 entities, 511 links) existed but wasn't queried during review. **Fixed**: `_insert_nexus_cards()` inserts cross-perspective cards for entities with `nexus_score >= 3`.

### 3.5 No Book Pre-Scan

The reading companion design doc described preview of what you know before starting a book, but it wasn't implemented. **Fixed**: `GET /book/prescan/{book_id}` shows known/new nodes, missing prerequisites, cross-book overlaps.

---

## 4. The Thought Experiment: What If No Curricula?

### Would Break Badly
- **Review card deduplication** — duplicates across book chapters
- **Progress visualization** — no "45/67 known" bars, no knowledge atlas
- **Voice elicitation** — no curated topic list, no reference description
- **Deterministic questions** — every question needs an LLM call

### Would Work Fine
- Microlearning cards (query-driven, not structure-driven)
- Book reading and capturing
- Article novelty detection (claim-level similarity)
- Review scheduling math (SRS doesn't need curriculum)

### Would Need Replacement
- Knowledge state tracking — needs *some* unit (entities too granular, claims too numerous)
- Chapter-to-concept mapping — needs another way to answer "what did this chapter teach me?"

---

## 5. Design Tension: Bounded vs Organic

The fundamental tension: **bounded pedagogical units** (curricula as courses, where "done" means something) vs **organic knowledge growth** (reading about Syracuse touches Greece, Rome, Carthage simultaneously).

The current system chose boundedness. Multi-domain mapping (session 54) bridges the gap: books now map to multiple curricula, and cross-domain context flows into questions. The data model (one `knowledge_item` per `(domain, node)`) naturally supports this.

---

## 6. Key Code Paths

### Chapter -> Review Items
```
create_review_items_for_chapter()
  -> suggest_curricula_for_book()     # rank all curricula by similarity
  -> for each domain (top 2-3):
       map_chapter_to_nodes()          # LLM maps chapter to nodes in this curriculum
       _upsert_chapter_mappings()      # create/update knowledge_items
       fill_prerequisite_gaps()        # create items for missing prerequisites
  -> background thread: generate_question() for each item
```

### Question Generation
```
generate_question()
  -> key_facts path (deterministic, reviews 1-2)
  -> LLM path (reviews 3+):
       _get_cross_curriculum_context()   # entities known from other domains
       _get_temporal_cross_references()  # contemporaneous events from other domains
       known same-domain nodes
       QUESTION_GEN_PROMPT or QUESTION_GEN_PROMPT_FACTUAL
```

### Review Stream Assembly
```
generate_review_stream()
  -> query knowledge_items + knowledge_states + curriculum_nodes
  -> score by knowledge weight + due status + answer type
  -> domain round-robin interleaving
  -> mix in microlearning (high-priority voice/user at 1:3, low at 1:7)
  -> annotate entity spans
  -> insert entity intro cards for unknown entities
  -> insert nexus cards for high-connectivity entities
```

### Voice Elicitation
```
get_elicitation_candidates()
  -> iterate curriculum nodes per domain
  -> score by confidence sweet-spot (peak at 0.5)
  -> interleave domains
  -> mix in chapter/book recalls

run_voice_elicitation()
  -> transcribe audio
  -> compare against node description + book sources
  -> update knowledge_states + knowledge_items
  -> create review_items for wonderings
  -> trigger microlearning from wonderings
```

---

## 7. What's Still Missing

1. **Client rendering of nexus cards** — backend sends `type: 'nexus'` but review.tsx doesn't render them
2. **Client integration of book prescan** — endpoint works but no UI
3. **Cross-curriculum stability adjustment** — reviewing a concept in one domain doesn't partially credit another domain
4. **Node dedup across curricula** — same concept in different curricula creates separate knowledge_items
5. **Dynamic curriculum growth** — no mechanism to grow curricula as reading reveals new interests
6. **Multi-domain timeline visualization** — timeline HTML shows single domain only
7. **Key_facts for non-Sicily curricula** — only Sicily Greek has 299 structured facts

---

## 8. Connections to Design Principles

| Principle | How Curriculum Serves It |
|-----------|------------------------|
| "Hooks, not facts" | Curriculum provides the scaffold framework; cross-curriculum connections ARE the hooks |
| "I'll manage your memory" | Knowledge bars per curriculum show tracking is happening; prescan shows "I know what you know" |
| "Comprehension before memory" | Key_facts start with factual scaffold, LLM questions progress to analytical |
| "Atomic claims are fundamental" | Claims map to curriculum nodes via article_curriculum_nodes; curriculum provides the organizing layer above claims |
| "Curriculum as bridge" | Multi-domain mapping bridges books to multiple curricula; nexus cards bridge curricula to each other |
| "Temporal hooks" | Cross-domain temporal references now generated automatically from date ranges |
| "Facts first, then concepts" | Key_facts are deterministic factual questions; LLM questions come after review 2 |
| "Curiosity zone at 70% novelty" | Book prescan shows 45% known / 55% new for Syracuse — near the sweet spot |

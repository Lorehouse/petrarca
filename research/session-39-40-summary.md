# Sessions 39-40: Curriculum SQLite Migration + Retrieval Practice System

*2026-03-29 to 2026-03-30. Two intensive sessions building the knowledge review system.*

---

## What Was Built

### 1. Curriculum System Migrated to SQLite

**Before:** Curriculum data was scattered across ~29 JSON files in `data/curricula/` — curriculum structures, knowledge states, book mappings, retrieval questions, timeline entries, elicitation sessions, cross-curriculum entities. All disconnected from the main `petrarca.db`.

**After:** 12 new tables in `petrarca.db`:
- `curriculum_domains` — 5 domains (Ancient Greece, Rome, Sicily, Byzantine, Islamic)
- `curriculum_nodes` — 367 nodes with hierarchical structure
- `curriculum_prerequisites` — 431 prerequisite edges (DAG)
- `knowledge_states` — 236 assessed nodes (single source of truth)
- `book_curriculum_mappings` — 283 book→node links across 18+ books
- `retrieval_questions` — 19 v2 hand-crafted questions (Greek Sicily)
- `review_schedule` — per-question SRS scheduling
- `review_history` — append-only answer log
- `timeline_entries` — 80 dated events for Sicily
- `shared_entities` — cross-curriculum entity links
- `elicitation_sessions` — 20Q session logs

**Files:**
- `scripts/db.py` — schema + migrations + book sync helpers
- `scripts/curriculum_db.py` — SQLite-backed API (replaces JSON-reading `curriculum.py`)
- `scripts/migrate_curricula_to_sqlite.py` — one-time migration script

### 2. Book Sync Migrated to SQLite

**Before:** Book data lived in `physical_books.json`, synced via JSON merge. Curriculum system couldn't see books because they were in a different format.

**After:** `POST /book/sync` and `GET /book/sync` read/write directly to `physical_books` + `book_captures` SQLite tables via UPSERT. 25 books + 17 captures migrated. JSON file no longer read or written.

**Files changed:** `scripts/db.py` (upsert_books, upsert_captures, load_all_books_and_captures, migrate_books_json_to_sqlite), `scripts/research-server.py` (sync handlers), `scripts/resurfacing_engine.py` (reads SQLite with JSON fallback)

### 3. Retrieval Practice Question System (v2)

**The v1 problem:** Generated 171 questions in one LLM batch. Many were compound ("when X and why was it significant?"), vague ("list the major events"), or had bare answers ("480 BC") without context. Impossible to self-grade properly.

**v2 design principles (from calibration feedback):**
1. **One fact per card** — never combine two concepts
2. **A question is really two questions** — name↔concept and concept↔date are separate cards
3. **Graded date answers** — exact year / right decade / right century / missed (4 levels, not binary)
4. **Rich answers** — mini-articles restating full context, not bare facts
5. **Memory hooks** (minnekrok from Hamarquizen) — vivid mnemonics on every card
6. **Temporal anchors** — "same year as Salamis", "right after Akragas fell"
7. **No "list N things"** — too hard to self-grade
8. **No open "what happened?"** — too many possible answers
9. **Prerequisites** — don't ask date before user knows what the thing IS
10. **Question levels** — Level 1 (identity+timeline skeleton), Level 2 (connections+causes), Level 3 (significance+analysis)

**19 hand-crafted questions for Greek Sicily covering:**
| Topic | Cards | What they test |
|-------|-------|---------------|
| Colonization | 3 | Naxos, 734 BC, Corinth→Syracuse |
| Akragas | 2 | Agrigento, 580 BC |
| Battle of Himera | 3 | What/when/who (480 BC, Gelon) |
| Athenian Expedition | 2 | What/when (415-413 BC) |
| Akragas/Dionysius I | 3 | Destruction 406, Dionysius 405 BC |
| Plato | 1 | Connection to Syracuse |
| Archimedes | 2 | Who/how died (212 BC) |
| Roman Sicily | 1 | When (241 BC, First Punic War) |
| Sequencing | 2 | Timeline ordering |

**New DB fields on retrieval_questions:** `answer_type`, `level`, `anchors` (JSON array), `memory_hook`, `grading_options` (JSON array), `rich_answer`

### 4. Review Tab Rewritten

**Before:** Bottom-nav Review tab used old `review_engine.py` / `knowledge_items` system (book-chapter based, different question format, different scheduling).

**After:** Review tab directly uses curriculum review system:
- One question at a time (not all visible)
- Type badge (DATE / IDENTITY / CONCEPT / TIMELINE) — node title hidden until reveal to avoid spoilers
- "Show answer" → reveals rich answer + memory hook + temporal anchors
- Graded self-assessment buttons based on answer_type (4 options for dates, 2 for names, 3 for concepts)
- Auto-advance after grading (600ms delay)
- Progress counter (3/10)
- "Session complete" → "New session" button
- Results write to `review_schedule` (SRS) + `review_history` (log) + `knowledge_states` (confidence adjustment)

### 5. Books Mapped to Sicily Curriculum

- **Syracuse, City of Legends** (finished) — 35 nodes mapped, marked finished
- **The Invention of Sicily** (currently reading) — 62 of 70 nodes mapped (covers almost everything)
- **Finished button** on book detail now sets `finished_date`

### 6. Timeline + Ordering Questions Generated

- 80 timeline entries for Sicily (734 BC → 2017)
- 7 temporal ordering questions ("put in order: A, B, C, D")
- Printable timeline reference: `data/curricula/sicily_timeline.md`

---

## Research & Design Documents Created

### In ~/src/research/notes/
- `norway-learning-science-landscape.md` — Full Norwegian academic landscape (515+ nodes of curriculum data across 7 domains)
- `norway-humanities-curriculum-knowledge.md` — Curriculum debates, history/literature education
- `knowledge-building-cognitive-science.md` — Cognitive science of humanities learning, knowledge diagnostics
- `norway-language-learning-tech-resources.md` — Corpora, language models, tools
- `norway-learning-research-synthesis.md` — Master synthesis sorted by relevance
- `petrarca-landscape-implications.md` — What research means for Petrarca (academic framing)
- `petrarca-practical-improvements.md` — Actionable feature improvements
- `petrarca-knowledge-system-deep-analysis.md` — Deep system architecture analysis
- `petrarca-evolution-deep-analysis.md` — How to evolve Petrarca (informed by knowledge-based-curricula research)
- `petrarca-book-companion-next-steps.md` — Concrete build plan for book companion

### In ~/src/petrarca/research/
- `curriculum-sqlite-design.md` — SQLite schema design + integrated flow
- `retrieval-question-design.md` — v2 question design principles (from calibration)
- `sicily-greek-period-questions-v2.md` — 19 hand-crafted questions

### In ~/src/research/knowledge-based-curricula/
- 28 research files on knowledge-based curricula (E.D. Hirsch, Core Knowledge, international implementations, technology, spaced repetition, assessment, classroom pedagogy, Norwegian experiment design, etc.)

---

## Calibration Process

### Format experiment (20 questions, 10 formats)
Built custom HTML evaluation page (Petrarca design system, question on left, answer on right, keyboard-driven rating). Tested formats:

**Formats that work:** Exact date with anchors, century-level for minor events, date+context, sequence ordering, "what's the connection?"

**Formats that don't work:** Compound questions (anything with "and"), "list N things", open "what happened?", "describe the significance" (essay-length), reign brackets as single question

**Key insight from calibration:** A question like "When was the Battle of Himera?" is actually TWO questions — (1) connect name "Himera" to concept (battle between Syracuse and Carthage), (2) connect concept to date (480 BC). These should be separate cards.

**Key insight from Alif/Hamarquizen:** Forgetting means you need richer hooks, not more repetition. When you forget, the system should ENRICH (add more anchors, vivid details, connections, micro-articles) rather than just show the same card sooner.

---

## What's Next (Not Yet Done)

### Immediate
1. **Generate v2 questions for other Sicily periods** — Roman, Arab-Norman, Medieval/Spanish (currently only Greek period has v2 questions)
2. **The Alif enrichment loop** — when user gets a question wrong, show richer answer next time; offer to generate micro-article; link to curriculum node detail
3. **Question prerequisites** — don't ask date before identity is mastered; track per-question mastery level

### Short-term
4. **Generate questions as part of curriculum creation** — not a separate step
5. **Post-chapter review flow** — finish chapter → system identifies covered nodes → surfaces relevant questions
6. **Pre-reading priming** — single question before reading an article about a topic you know
7. **Knowledge state computed from evidence graph** — replace FSRS with evidence-based confidence (engagement quality × recency × source diversity)

### Longer-term
8. **Expand Sicily curriculum** — Punic Wars branch (currently one node), Roger II branch (currently one node) — both need deepening as reading expands
9. **Cross-curriculum connections** — "What was happening in mainland Greece when Dionysius I ruled Syracuse?"
10. **Voice timeline dumps** — walk and narrate everything you know chronologically, system maps against curriculum
11. **Norwegian corpus experiment** — identify presupposed background knowledge in Norwegian texts

---

## Technical State

### Server: alifstian.duckdns.org:8090
- `petrarca.db` has all curriculum + book data in SQLite
- `curriculum_db.py` is the active API for curriculum operations
- Old `curriculum.py` still used for: generate_curriculum, elicitation (20Q), entity tagging, graph visualization
- `physical_books.json` still exists on server but is NO LONGER READ OR WRITTEN — SQLite is canonical

### Client: Expo app
- Review tab (bottom nav) → curriculum review with v2 cards
- Resurfacing screen (Library → ✦ Revisit) → still has the old Review/Revisit toggle, partially redundant with the new Review tab
- Book detail → curriculum context + finished button

### Key API endpoints
- `POST /curriculum/review/generate` — generates review session from SQLite
- `POST /curriculum/review/result` — records graded answer, updates schedule + knowledge state
- `GET /curriculum/review/status` — review stats
- `POST /book/sync` — UPSERT books/captures to SQLite
- `GET /book/sync` — load books/captures from SQLite
- `POST /curriculum/map-book` — map book to curriculum nodes (LLM call)
- `GET /curriculum/{domain_id}/coverage` — gap analysis
- `GET /curriculum/list` — list all curricula

### Data in petrarca.db
- 5 curriculum domains, 367 nodes, 431 prerequisites
- 236 knowledge states (AG 38, Byzantine 49, Islamic 40, Rome 50, Sicily 59)
- 283 book-curriculum mappings
- 19 v2 retrieval questions (Greek Sicily only)
- 80 timeline entries
- 26 books, 17 captures

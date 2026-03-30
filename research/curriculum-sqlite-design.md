# Curriculum System: SQLite Design & Integrated Flow

*2026-03-30. Moving from ad-hoc JSON files to a proper database-backed system.*

---

## Current State (the mess)

### In SQLite already
- `knowledge_items` — one row per curriculum node, with SRS scheduling (stability, due_at, review_count, sources array). Created by migrating from `review_items`.
- `article_curriculum_nodes` — links articles to curriculum nodes (claim_count, avg_similarity)
- `review_items` — the old per-book×chapter×node model, mostly superseded by knowledge_items

### In JSON files (data/curricula/)
- `{domain}.json` — curriculum structure: nodes with id, title, description, parent_id, level, prerequisites, obscurity, bloom_floor
- `knowledge_{domain}.json` — per-node knowledge state: knowledge level, interest, confidence, sources, last_assessed
- `mappings_{domain}_{book_id}.json` — which curriculum nodes a book covers, at what depth
- `sicily_retrieval_questions.json` — 171 generated retrieval questions
- `sicily_ordering_questions.json` — 7 temporal ordering questions
- `sicily_timeline.json` — 80 dated events
- `cross_curriculum_entities.json` — 25 shared entities with per-curriculum lenses
- `elicit_{domain}_{session_id}.json` — 20Q session logs
- `self_report_{domain}_{date}.json` — self-assessment results

### In a separate JSON file (scripts/data/)
- `curriculum_review_state.json` — the ad-hoc review scheduling I just built yesterday

### The problems
1. Two parallel knowledge-state systems (knowledge_items table + knowledge_{domain}.json)
2. Retrieval questions disconnected from the nodes they test
3. Review scheduling disconnected from knowledge state updates
4. No way to query across curricula (e.g. "all nodes I'm weak on across all domains")
5. Book mappings not queryable — can't answer "which books contributed to this node"
6. Pipeline can't run SQL to decide what to generate next

---

## Proposed Schema

### New tables (replacing all curriculum JSON files)

```sql
-- The curriculum structure itself
CREATE TABLE IF NOT EXISTS curriculum_nodes (
    id TEXT NOT NULL,                    -- e.g. "sicily_his_gelon_and_the_battle_of_himera"
    domain_id TEXT NOT NULL,             -- e.g. "sicily_history_culture_and_legacy"
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    parent_id TEXT,                       -- FK to curriculum_nodes.id (same domain)
    level INTEGER NOT NULL DEFAULT 1,    -- 1=area, 2=topic, 3=concept, 4=detail
    obscurity INTEGER DEFAULT 2,         -- 1=everyone knows, 5=specialist
    bloom_floor TEXT DEFAULT 'recognize', -- recognize | explain | analyze
    knowledge_type TEXT DEFAULT 'core',  -- core | hinterland (Counsell's distinction)
    date_start INTEGER,                  -- year (negative for BC)
    date_end INTEGER,
    PRIMARY KEY (domain_id, id)
);
CREATE INDEX IF NOT EXISTS idx_cn_domain ON curriculum_nodes(domain_id);
CREATE INDEX IF NOT EXISTS idx_cn_parent ON curriculum_nodes(domain_id, parent_id);

-- Prerequisite edges (DAG)
CREATE TABLE IF NOT EXISTS curriculum_prerequisites (
    domain_id TEXT NOT NULL,
    node_id TEXT NOT NULL,               -- this node
    prerequisite_id TEXT NOT NULL,        -- requires this node
    strength TEXT DEFAULT 'hard',        -- hard | soft
    PRIMARY KEY (domain_id, node_id, prerequisite_id),
    FOREIGN KEY (domain_id, node_id) REFERENCES curriculum_nodes(domain_id, id),
    FOREIGN KEY (domain_id, prerequisite_id) REFERENCES curriculum_nodes(domain_id, id)
);

-- Curriculum-level metadata (title, description, generated_at, etc.)
CREATE TABLE IF NOT EXISTS curriculum_domains (
    id TEXT PRIMARY KEY,                 -- e.g. "sicily_history_culture_and_legacy"
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    depth TEXT DEFAULT 'introductory',   -- introductory | intermediate | advanced
    generated_at TEXT,
    generated_by TEXT,
    node_count INTEGER DEFAULT 0
);

-- Knowledge state per node per user (replaces knowledge_{domain}.json)
-- This is the SINGLE source of truth for "what do I know"
CREATE TABLE IF NOT EXISTS knowledge_states (
    domain_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    knowledge TEXT NOT NULL DEFAULT 'unknown',  -- unknown | mentioned | engaged | anchored
    interest TEXT DEFAULT 'none',               -- none | curious | core
    confidence REAL DEFAULT 0.0,               -- 0.0-1.0
    highest_layer INTEGER DEFAULT 0,           -- 0=none, 1=encountered, 2=understood, 3=can_apply
    source_summary TEXT DEFAULT '[]',          -- JSON array of {type, id, date, weight}
    last_assessed TEXT,
    last_evidence TEXT,                         -- most recent evidence timestamp
    PRIMARY KEY (domain_id, node_id),
    FOREIGN KEY (domain_id, node_id) REFERENCES curriculum_nodes(domain_id, id)
);
CREATE INDEX IF NOT EXISTS idx_ks_knowledge ON knowledge_states(knowledge);

-- Book-to-curriculum mappings (replaces mappings_{domain}_{book_id}.json)
CREATE TABLE IF NOT EXISTS book_curriculum_mappings (
    book_id TEXT NOT NULL,
    domain_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    coverage TEXT DEFAULT 'surface',           -- surface | moderate | deep
    inferred_from TEXT DEFAULT 'llm_inference', -- book_research | kindle_highlights | user_report | llm_inference
    PRIMARY KEY (book_id, domain_id, node_id),
    FOREIGN KEY (domain_id, node_id) REFERENCES curriculum_nodes(domain_id, id)
);
CREATE INDEX IF NOT EXISTS idx_bcm_book ON book_curriculum_mappings(book_id);
CREATE INDEX IF NOT EXISTS idx_bcm_node ON book_curriculum_mappings(domain_id, node_id);

-- Retrieval questions (replaces sicily_retrieval_questions.json etc.)
CREATE TABLE IF NOT EXISTS retrieval_questions (
    id TEXT PRIMARY KEY,                       -- hash of question text
    domain_id TEXT NOT NULL,
    node_id TEXT NOT NULL,                     -- which curriculum node this tests
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    question_type TEXT DEFAULT 'event',        -- date | person | event | sequence | significance | temporal_ordering
    node_title TEXT DEFAULT '',
    cluster_label TEXT,                        -- for temporal_ordering questions
    generated_at TEXT,
    FOREIGN KEY (domain_id, node_id) REFERENCES curriculum_nodes(domain_id, id)
);
CREATE INDEX IF NOT EXISTS idx_rq_domain ON retrieval_questions(domain_id);
CREATE INDEX IF NOT EXISTS idx_rq_node ON retrieval_questions(domain_id, node_id);

-- Review history (replaces curriculum_review_state.json AND knowledge_items scheduling)
CREATE TABLE IF NOT EXISTS review_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id TEXT NOT NULL REFERENCES retrieval_questions(id),
    result TEXT NOT NULL,                      -- correct | partial | wrong
    reviewed_at TEXT NOT NULL,
    session_id TEXT                            -- which review session this was part of
);
CREATE INDEX IF NOT EXISTS idx_rh_question ON review_history(question_id);

-- Review scheduling state per question
CREATE TABLE IF NOT EXISTS review_schedule (
    question_id TEXT PRIMARY KEY REFERENCES retrieval_questions(id),
    review_count INTEGER DEFAULT 0,
    last_reviewed_at INTEGER,                  -- unix ms
    last_result TEXT,                          -- correct | partial | wrong
    stability_days REAL DEFAULT 1.0,
    due_at INTEGER DEFAULT 0                   -- unix ms
);

-- Cross-curriculum shared entities (replaces cross_curriculum_entities.json)
CREATE TABLE IF NOT EXISTS shared_entities (
    entity_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    dates TEXT,
    location TEXT,
    nexus_score INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS entity_curriculum_links (
    entity_id TEXT NOT NULL REFERENCES shared_entities(entity_id),
    domain_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    lens_title TEXT,                           -- curriculum-specific framing
    lens_emphasis TEXT,
    PRIMARY KEY (entity_id, domain_id, node_id)
);

-- Timeline entries (replaces sicily_timeline.json)
CREATE TABLE IF NOT EXISTS timeline_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_id TEXT NOT NULL,
    year INTEGER NOT NULL,                     -- negative for BC
    label TEXT NOT NULL,
    detail TEXT DEFAULT '',
    node_id TEXT,                              -- optional link to curriculum node
    FOREIGN KEY (domain_id, node_id) REFERENCES curriculum_nodes(domain_id, id)
);
CREATE INDEX IF NOT EXISTS idx_tl_domain ON timeline_entries(domain_id);
CREATE INDEX IF NOT EXISTS idx_tl_year ON timeline_entries(year);

-- 20Q elicitation session logs
CREATE TABLE IF NOT EXISTS elicitation_sessions (
    id TEXT PRIMARY KEY,
    domain_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    questions_asked INTEGER DEFAULT 0,
    nodes_assessed INTEGER DEFAULT 0,
    responses TEXT DEFAULT '[]'                -- JSON array of {node_id, response, confidence}
);
```

### What happens to existing tables

- **`knowledge_items`** — Keep for now as the SRS scheduling for book-chapter review (the existing review system). The new `review_schedule` table handles curriculum question scheduling separately. Eventually merge.
- **`review_items`** — Already superseded by knowledge_items. Can be dropped after confirming no code references it.
- **`article_curriculum_nodes`** — Stays as-is. It links the article pipeline to curriculum nodes. Will reference `curriculum_nodes` via (domain_id, node_id).

---

## The Integrated Flow

### Flow 1: Curriculum creation

```
User requests a new curriculum domain (e.g. "Punic Wars")
  → curriculum.py generates nodes via Opus
  → INSERT INTO curriculum_domains + curriculum_nodes + curriculum_prerequisites
  → Generate retrieval questions for all nodes with bloom ≥ explain
  → INSERT INTO retrieval_questions
  → Generate timeline entries from dated nodes
  → INSERT INTO timeline_entries
  → All in one transaction
```

No more separate JSON files. Everything is in the database from the start.

### Flow 2: Book-curriculum mapping

```
User adds/imports a book
  → Book research agent runs (existing)
  → curriculum.py maps book to curriculum nodes
  → INSERT INTO book_curriculum_mappings (book_id, domain_id, node_id, coverage, inferred_from)
  → UPDATE knowledge_states:
      For each mapped node:
        - If unknown → mentioned (confidence based on book significance × coverage)
        - If mentioned → keep, but increase confidence if new source
        - Add source to source_summary array
  → Knowledge states now reflect what the book taught
```

### Flow 3: 20Q assessment

```
User starts a curriculum scan
  → SELECT nodes + knowledge_states for the domain
  → Question selection: find boundary nodes (prerequisites known, node uncertain)
  → User answers (new_to_me / knew_some / knew_all + interest)
  → UPDATE knowledge_states with assessment result
  → INSERT INTO elicitation_sessions (log the session)
  → Knowledge map UI refreshes from database
```

### Flow 4: Reading an article (existing, but now curriculum-aware)

```
Article pipeline extracts claims
  → build_curriculum_embeddings maps claims to curriculum nodes
  → INSERT INTO article_curriculum_nodes (already happens)
  → When user reads the article:
      UPDATE knowledge_states for mapped nodes:
        - Increase confidence slightly (article encounter = weak evidence)
        - Add article as source in source_summary
```

### Flow 5: Review session (the new thing)

```
User opens Revisit → Review tab
  → POST /curriculum/review/generate
  → Server queries:
      SELECT rq.*, rs.review_count, rs.last_result, rs.due_at
      FROM retrieval_questions rq
      LEFT JOIN review_schedule rs ON rq.id = rs.question_id
      WHERE (rs.due_at IS NULL OR rs.due_at <= :now)  -- due or never reviewed
      ORDER BY
        CASE WHEN rs.review_count IS NULL THEN 0 ELSE 1 END,  -- new questions first
        CASE WHEN rs.last_result = 'wrong' THEN 0 ELSE 1 END, -- wrong answers next
        rs.due_at ASC                                           -- oldest due first
      LIMIT 10
  → Return questions to client
  → User answers each (correct / partial / wrong)
  → POST /curriculum/review/result for each
  → Server:
      INSERT INTO review_history (question_id, result, reviewed_at, session_id)
      UPSERT review_schedule: update review_count, last_result, compute next due_at
      UPDATE knowledge_states: if the question maps to a node,
        adjust confidence based on result (correct → boost, wrong → reduce)
```

### Flow 6: Knowledge state is always computed, never stale

The `knowledge_states` table is updated by EVERY interaction:
- Book import → mentioned + sources
- 20Q scan → assessed level + sources
- Article reading → slight confidence boost
- Review question answered → confidence adjustment
- Voice dump → higher-layer evidence
- Time passing → slow confidence decay (computed on read, not stored)

When the client requests the knowledge map, the server:
1. Reads knowledge_states for the domain
2. Applies time-based confidence decay (formula, not stored)
3. Computes coherence metric (connected component of confident nodes)
4. Returns everything

No JSON files to sync. No dual state. One source of truth.

---

## Migration Plan

### Step 1: Create new tables
Add the new CREATE TABLE statements to db.py SCHEMA. Run `python db.py init`.

### Step 2: Migrate existing curriculum JSON → SQLite
Write a one-time migration script:
```python
def migrate_curricula():
    for json_file in CURRICULA_DIR.glob('*.json'):
        if json_file.name.startswith(('knowledge_', 'mappings_', 'elicit_', 'self_report_', 'sicily_retrieval', 'sicily_ordering', 'sicily_timeline', 'sicily_study', 'cross_curriculum')):
            continue  # handle separately
        # This is a curriculum structure file
        data = json.loads(json_file.read_text())
        # INSERT INTO curriculum_domains
        # INSERT INTO curriculum_nodes for each node
        # INSERT INTO curriculum_prerequisites for each prerequisite edge

    # Migrate knowledge states
    for kf in CURRICULA_DIR.glob('knowledge_*.json'):
        # INSERT INTO knowledge_states

    # Migrate book mappings
    for mf in CURRICULA_DIR.glob('mappings_*.json'):
        # INSERT INTO book_curriculum_mappings

    # Migrate retrieval questions
    for rq in CURRICULA_DIR.glob('*_retrieval_questions.json'):
        # INSERT INTO retrieval_questions

    # Migrate timeline
    for tl in CURRICULA_DIR.glob('*_timeline.json'):
        # INSERT INTO timeline_entries
```

### Step 3: Update curriculum.py to read/write SQLite
Replace all `json.loads(path.read_text())` with SQL queries. Replace all `path.write_text(json.dumps(...))` with SQL inserts/updates.

### Step 4: Update resurfacing_engine.py
The curriculum review functions should query `retrieval_questions` and `review_schedule` tables instead of scanning for JSON files on disk.

### Step 5: Update API endpoints
Server endpoints for curriculum operations should use `db.get_connection()` instead of reading JSON files.

### Step 6: Update client
The client already talks to API endpoints, so minimal changes. The knowledge map screen fetches from `/curriculum/{domain_id}` which the server builds from SQL. The review session fetches from `/curriculum/review/generate` which the server builds from SQL.

### Step 7: Delete JSON files
After migration is verified, remove the JSON file reads from all scripts. Keep the files as backup for a few weeks.

---

## What This Enables That JSON Files Can't

1. **Cross-domain queries**: "Show me all nodes I'm weak on across all curricula" = one SQL query
2. **Integrated scheduling**: Review questions and knowledge states in the same transaction
3. **Book impact analysis**: "Which books contributed to my knowledge of this node?" = JOIN book_curriculum_mappings
4. **Pipeline integration**: The content refresh pipeline can update knowledge states in the same database it writes articles to
5. **Atomic updates**: Book mapping + knowledge state update + review scheduling in one transaction
6. **No sync issues**: One database, one source of truth, no JSON files to get out of sync

---

## Build Order

1. **Add tables to db.py** — the schema above. `python db.py init` creates them.
2. **Migration script** — one-time, moves existing data from JSON → SQLite
3. **Update curriculum.py** — read/write SQLite. This is the biggest change.
4. **Update resurfacing_engine.py** — review functions use SQL
5. **Update research-server.py endpoints** — use db.get_connection()
6. **Verify client still works** — it talks to API endpoints, should be transparent
7. **Generate retrieval questions as part of curriculum creation** — not a separate step

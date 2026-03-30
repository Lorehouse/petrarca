"""
Petrarca SQLite database — connection helper + schema.

Usage:
    from db import get_connection, init_db

    init_db()  # creates tables if not exist

    conn = get_connection()
    conn.execute("INSERT INTO projects (...) VALUES (?, ?)", (id, name))
    conn.commit()
    conn.close()

Connection-per-request pattern: each handler opens/commits/closes its own
connection. WAL mode (via limbic.amygdala.connect) makes this safe and cheap with
ThreadingHTTPServer.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, '/opt/limbic')
from limbic.amygdala import connect

DB_PATH = Path(os.environ.get('PETRARCA_DB', '/opt/petrarca/data/petrarca.db'))


def get_connection(readonly: bool = False):
    """Get a new database connection with WAL, 64MB cache, FK enforcement."""
    return connect(DB_PATH, readonly=readonly)


SCHEMA = """
-- Projects
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS project_notes (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    text TEXT DEFAULT '',
    audio_file TEXT,
    source TEXT,
    voice_routing TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_project_notes_project ON project_notes(project_id);

-- Feedback
CREATE TABLE IF NOT EXISTS feedback (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    context TEXT NOT NULL,
    text TEXT DEFAULT '',
    screenshot_file TEXT,
    audio_file TEXT,
    transcript TEXT,
    transcript_error TEXT,
    voice_routing TEXT
);

-- Voice/text notes
CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,
    article_id TEXT DEFAULT '',
    article_title TEXT DEFAULT '',
    topics TEXT DEFAULT '[]',
    status TEXT DEFAULT 'transcribing',
    transcript TEXT,
    actions TEXT DEFAULT '[]',
    voice_routing TEXT,
    created_at INTEGER,
    extra TEXT DEFAULT '{}'
);

-- Scrape reports
CREATE TABLE IF NOT EXISTS scrape_reports (
    article_id TEXT PRIMARY KEY,
    url TEXT,
    title TEXT,
    reported_at TEXT NOT NULL,
    status TEXT DEFAULT 'pending'
);

-- Media log
CREATE TABLE IF NOT EXISTS media_items (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    source TEXT DEFAULT '',
    url TEXT,
    date_consumed TEXT,
    duration INTEGER,
    description TEXT DEFAULT '',
    extra TEXT DEFAULT '{}'
);

-- Chat conversations
CREATE TABLE IF NOT EXISTS chat_conversations (
    id TEXT PRIMARY KEY,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL REFERENCES chat_conversations(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chat_conv ON chat_messages(conversation_id);

-- Research results
CREATE TABLE IF NOT EXISTS research_results (
    id TEXT PRIMARY KEY,
    type TEXT DEFAULT 'research',
    status TEXT NOT NULL,
    data TEXT NOT NULL,
    requested_at INTEGER,
    completed_at INTEGER
);
CREATE INDEX IF NOT EXISTS idx_research_status ON research_results(status);

-- Physical books
CREATE TABLE IF NOT EXISTS physical_books (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT NOT NULL DEFAULT '',
    cover_image_uri TEXT,
    cover_url TEXT,
    isbn TEXT,
    publisher TEXT,
    year INTEGER,
    page_count INTEGER,
    language TEXT DEFAULT 'en',
    topics TEXT DEFAULT '[]',
    chapters TEXT DEFAULT '[]',
    current_chapter TEXT,
    current_page INTEGER,
    reading_status TEXT DEFAULT 'reading',
    significance TEXT,
    added_at INTEGER NOT NULL,
    last_interaction_at INTEGER NOT NULL,
    metadata_source TEXT,
    processing_status TEXT,
    kindle_asin TEXT,
    kindle_book_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_books_reading_status ON physical_books(reading_status);

CREATE TABLE IF NOT EXISTS book_captures (
    id TEXT PRIMARY KEY,
    book_id TEXT NOT NULL REFERENCES physical_books(id),
    type TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    audio_uri TEXT,
    transcript TEXT,
    transcription_status TEXT,
    photo_uri TEXT,
    ocr_text TEXT,
    ocr_status TEXT,
    text TEXT,
    page_number INTEGER,
    chapter TEXT,
    extracted_ideas TEXT DEFAULT '[]',
    topics TEXT DEFAULT '[]',
    key_passage TEXT,
    elaborative_question TEXT,
    server_id TEXT,
    upload_status TEXT DEFAULT 'pending'
);
CREATE INDEX IF NOT EXISTS idx_captures_book ON book_captures(book_id);

-- Kindle library
CREATE TABLE IF NOT EXISTS kindle_books (
    key TEXT PRIMARY KEY,
    asin TEXT,
    book_id TEXT,
    title TEXT NOT NULL DEFAULT '',
    author TEXT DEFAULT '',
    cover_url TEXT,
    progress TEXT DEFAULT '{}',
    first_seen TEXT,
    last_seen TEXT,
    status TEXT DEFAULT 'unreviewed',
    finished_date TEXT,
    last_read TEXT,
    purchase_date TEXT,
    language TEXT,
    publisher TEXT,
    is_sideloaded INTEGER DEFAULT 0,
    category TEXT,
    added_to_petrarca INTEGER DEFAULT 0,
    epub_path TEXT,
    title_resolved TEXT
);
CREATE INDEX IF NOT EXISTS idx_kindle_status ON kindle_books(status);
CREATE INDEX IF NOT EXISTS idx_kindle_category ON kindle_books(category);

CREATE TABLE IF NOT EXISTS kindle_sync_meta (
    id INTEGER PRIMARY KEY DEFAULT 1,
    sync_count INTEGER DEFAULT 0,
    last_sync TEXT
);

CREATE TABLE IF NOT EXISTS kindle_highlights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_key TEXT NOT NULL,
    text TEXT NOT NULL,
    location TEXT,
    color TEXT,
    synced_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_kh_book ON kindle_highlights(book_key);

CREATE TABLE IF NOT EXISTS kindle_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_key TEXT NOT NULL,
    text TEXT NOT NULL,
    location TEXT,
    synced_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_kn_book ON kindle_notes(book_key);

CREATE TABLE IF NOT EXISTS kindle_highlight_books (
    key TEXT PRIMARY KEY,
    asin TEXT,
    title TEXT DEFAULT '',
    author TEXT DEFAULT '',
    cover_url TEXT,
    first_sync TEXT,
    last_sync TEXT
);

-- ===== Content Pipeline Tables (replaces JSON files) =====

-- Articles (replaces articles.json)
CREATE TABLE IF NOT EXISTS articles (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '',
    author TEXT NOT NULL DEFAULT '',
    source_url TEXT NOT NULL DEFAULT '',
    hostname TEXT NOT NULL DEFAULT '',
    date TEXT DEFAULT '',
    content_markdown TEXT DEFAULT '',
    one_line_summary TEXT DEFAULT '',
    full_summary TEXT DEFAULT '',
    key_claims TEXT DEFAULT '[]',
    topics TEXT DEFAULT '[]',
    interest_topics TEXT DEFAULT '[]',
    novelty_claims TEXT DEFAULT '[]',
    entities TEXT DEFAULT '[]',
    estimated_read_minutes INTEGER DEFAULT 0,
    content_type TEXT DEFAULT 'unknown',
    word_count INTEGER DEFAULT 0,
    sources TEXT DEFAULT '[]',
    fetch_method TEXT,
    exploration_tag TEXT,
    parent_id TEXT,
    exploration_tier TEXT,
    exploration_order INTEGER,
    ingested_at TEXT,
    similar_articles TEXT,
    follow_up_questions TEXT DEFAULT '[]',
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- Article sections
CREATE TABLE IF NOT EXISTS article_sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    section_index INTEGER NOT NULL,
    heading TEXT DEFAULT '',
    content TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    key_claims TEXT DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_article_sections_article ON article_sections(article_id);

-- Atomic claims (composite PK: same claim ID can appear in multiple articles)
CREATE TABLE IF NOT EXISTS atomic_claims (
    id TEXT NOT NULL,
    article_id TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    normalized_text TEXT NOT NULL DEFAULT '',
    original_text TEXT DEFAULT '',
    claim_type TEXT DEFAULT 'factual',
    source_paragraphs TEXT DEFAULT '[]',
    topics TEXT DEFAULT '[]',
    PRIMARY KEY (article_id, id)
);
CREATE INDEX IF NOT EXISTS idx_claims_article ON atomic_claims(article_id);
CREATE INDEX IF NOT EXISTS idx_claims_id ON atomic_claims(id);

-- Claim similarity pairs (from build_knowledge_index.py)
CREATE TABLE IF NOT EXISTS claim_similarities (
    claim_a TEXT NOT NULL,
    claim_b TEXT NOT NULL,
    score REAL NOT NULL,
    PRIMARY KEY (claim_a, claim_b)
);
CREATE INDEX IF NOT EXISTS idx_claimsim_a ON claim_similarities(claim_a);
CREATE INDEX IF NOT EXISTS idx_claimsim_b ON claim_similarities(claim_b);

-- NLI verdicts for ambiguous pairs
CREATE TABLE IF NOT EXISTS nli_verdicts (
    claim_a TEXT NOT NULL,
    claim_b TEXT NOT NULL,
    verdict TEXT NOT NULL,
    PRIMARY KEY (claim_a, claim_b)
);

-- Article-level similarity pairs
CREATE TABLE IF NOT EXISTS article_similarities (
    article_a TEXT NOT NULL,
    article_b TEXT NOT NULL,
    score REAL NOT NULL,
    PRIMARY KEY (article_a, article_b)
);
CREATE INDEX IF NOT EXISTS idx_artsim_a ON article_similarities(article_a);
CREATE INDEX IF NOT EXISTS idx_artsim_b ON article_similarities(article_b);

-- Article novelty matrix (per target-read pair)
CREATE TABLE IF NOT EXISTS article_novelty_matrix (
    target_article_id TEXT NOT NULL,
    read_article_id TEXT NOT NULL,
    new_count INTEGER NOT NULL DEFAULT 0,
    extends_count INTEGER NOT NULL DEFAULT 0,
    known_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (target_article_id, read_article_id)
);

-- Paragraph-to-claim mapping
CREATE TABLE IF NOT EXISTS paragraph_claim_map (
    article_id TEXT NOT NULL,
    paragraph_index INTEGER NOT NULL,
    claim_id TEXT NOT NULL,
    PRIMARY KEY (article_id, paragraph_index, claim_id)
);

-- Article-to-curriculum node links
CREATE TABLE IF NOT EXISTS article_curriculum_nodes (
    article_id TEXT NOT NULL,
    domain_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    node_title TEXT DEFAULT '',
    claim_count INTEGER DEFAULT 0,
    avg_similarity REAL DEFAULT 0,
    max_similarity REAL DEFAULT 0,
    PRIMARY KEY (article_id, domain_id, node_id)
);

-- Delta reports per topic
CREATE TABLE IF NOT EXISTS delta_reports (
    topic TEXT PRIMARY KEY,
    summary TEXT DEFAULT '',
    claim_count INTEGER DEFAULT 0,
    article_count INTEGER DEFAULT 0,
    top_claims TEXT DEFAULT '[]',
    subtopics TEXT
);

-- Concept clusters
CREATE TABLE IF NOT EXISTS concept_clusters (
    cluster_id INTEGER PRIMARY KEY,
    label TEXT DEFAULT '',
    size INTEGER DEFAULT 0,
    articles TEXT DEFAULT '[]',
    core_article_ids TEXT DEFAULT '[]',
    peripheral_article_ids TEXT DEFAULT '[]',
    top_topics TEXT DEFAULT '[]',
    total_unique_claims INTEGER DEFAULT 0,
    total_shared_claims INTEGER DEFAULT 0,
    key_shared_claims TEXT DEFAULT '[]',
    internal_edges INTEGER DEFAULT 0,
    avg_edge_weight REAL DEFAULT 0
);

-- Near-duplicate article pairs
CREATE TABLE IF NOT EXISTS near_duplicates (
    article_a TEXT NOT NULL,
    article_b TEXT NOT NULL,
    title_a TEXT DEFAULT '',
    title_b TEXT DEFAULT '',
    known_claims INTEGER DEFAULT 0,
    total_claims_a INTEGER DEFAULT 0,
    overlap_ratio REAL DEFAULT 0,
    PRIMARY KEY (article_a, article_b)
);

-- Syntheses
CREATE TABLE IF NOT EXISTS syntheses (
    cluster_id TEXT PRIMARY KEY,
    label TEXT DEFAULT '',
    synthesis_markdown TEXT DEFAULT '',
    article_ids TEXT DEFAULT '[]',
    article_coverage TEXT DEFAULT '{}',
    claims_covered TEXT DEFAULT '[]',
    unique_per_article TEXT DEFAULT '{}',
    follow_up_questions TEXT DEFAULT '[]',
    tensions TEXT DEFAULT '[]',
    generated_at TEXT DEFAULT '',
    total_articles INTEGER DEFAULT 0,
    total_claims_covered INTEGER DEFAULT 0,
    total_claims_in_cluster INTEGER DEFAULT 0
);

-- Pipeline metadata (version, hashes, timestamps)
CREATE TABLE IF NOT EXISTS pipeline_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- Cluster metadata (parameters, stats — one row per pipeline run)
CREATE TABLE IF NOT EXISTS cluster_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Knowledge Review Items (spaced retrieval practice)
CREATE TABLE IF NOT EXISTS review_items (
  id TEXT PRIMARY KEY,
  item_type TEXT NOT NULL DEFAULT 'book_chapter',  -- book_chapter | exploration | voice_followup
  curriculum_domain TEXT,
  curriculum_node_id TEXT,
  curriculum_node_title TEXT,
  source_book_id TEXT,
  source_chapter_number INTEGER,
  source_chapter_title TEXT,
  source_article_id TEXT,
  source_text TEXT NOT NULL DEFAULT '',
  temporal_hook TEXT DEFAULT '',
  lens TEXT,                          -- CAUSAL | COMPARATIVE | SIGNIFICANCE | TEMPORAL | PATTERN | CONSEQUENCE
  parent_item_id TEXT,                -- for follow-up chains
  stability_days REAL NOT NULL DEFAULT 1.0,
  due_at INTEGER NOT NULL,            -- unix ms timestamp
  last_reviewed_at INTEGER,
  last_score TEXT,                    -- knew | partly | missed
  review_count INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL,
  cached_question TEXT                -- JSON: pre-generated question, cleared after answer
);

-- Node-centric knowledge items — one row per curriculum node, sources array accumulates all books/chapters
-- LEGACY: superseded by knowledge_states for curriculum tracking; kept for existing book-chapter review
CREATE TABLE IF NOT EXISTS knowledge_items (
    id TEXT PRIMARY KEY,
    curriculum_node_id TEXT NOT NULL,
    curriculum_domain TEXT NOT NULL,
    stability_days REAL NOT NULL DEFAULT 1.0,
    due_at INTEGER NOT NULL DEFAULT 0,
    last_reviewed_at INTEGER,
    last_score TEXT,
    review_count INTEGER NOT NULL DEFAULT 0,
    sources TEXT NOT NULL DEFAULT '[]',
    question_history TEXT NOT NULL DEFAULT '[]',
    created_at INTEGER NOT NULL,
    cached_question TEXT,
    UNIQUE(curriculum_domain, curriculum_node_id)
);

-- ===== Curriculum System (replaces JSON files in data/curricula/) =====

-- Curriculum domains (e.g. "Sicily: History, Culture, and Legacy")
CREATE TABLE IF NOT EXISTS curriculum_domains (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    depth TEXT DEFAULT 'introductory',
    generated_at TEXT,
    generated_by TEXT,
    node_count INTEGER DEFAULT 0
);

-- Curriculum nodes — the actual knowledge structure
CREATE TABLE IF NOT EXISTS curriculum_nodes (
    id TEXT NOT NULL,
    domain_id TEXT NOT NULL REFERENCES curriculum_domains(id),
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    parent_id TEXT,
    level INTEGER NOT NULL DEFAULT 1,
    obscurity INTEGER DEFAULT 2,
    bloom_floor TEXT DEFAULT 'recognize',
    knowledge_type TEXT DEFAULT 'core',
    date_start INTEGER,
    date_end INTEGER,
    PRIMARY KEY (domain_id, id)
);
CREATE INDEX IF NOT EXISTS idx_cn_domain ON curriculum_nodes(domain_id);
CREATE INDEX IF NOT EXISTS idx_cn_parent ON curriculum_nodes(domain_id, parent_id);

-- Prerequisite edges (DAG within a domain)
CREATE TABLE IF NOT EXISTS curriculum_prerequisites (
    domain_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    prerequisite_id TEXT NOT NULL,
    strength TEXT DEFAULT 'hard',
    PRIMARY KEY (domain_id, node_id, prerequisite_id),
    FOREIGN KEY (domain_id, node_id) REFERENCES curriculum_nodes(domain_id, id),
    FOREIGN KEY (domain_id, prerequisite_id) REFERENCES curriculum_nodes(domain_id, id)
);

-- Knowledge state per node — SINGLE source of truth for "what do I know"
CREATE TABLE IF NOT EXISTS knowledge_states (
    domain_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    knowledge TEXT NOT NULL DEFAULT 'unknown',
    interest TEXT DEFAULT 'none',
    confidence REAL DEFAULT 0.0,
    highest_layer INTEGER DEFAULT 0,
    source_summary TEXT DEFAULT '[]',
    last_assessed TEXT,
    last_evidence TEXT,
    PRIMARY KEY (domain_id, node_id),
    FOREIGN KEY (domain_id, node_id) REFERENCES curriculum_nodes(domain_id, id)
);
CREATE INDEX IF NOT EXISTS idx_ks_knowledge ON knowledge_states(knowledge);

-- Book-to-curriculum mappings
CREATE TABLE IF NOT EXISTS book_curriculum_mappings (
    book_id TEXT NOT NULL,
    domain_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    coverage TEXT DEFAULT 'surface',
    inferred_from TEXT DEFAULT 'llm_inference',
    PRIMARY KEY (book_id, domain_id, node_id),
    FOREIGN KEY (domain_id, node_id) REFERENCES curriculum_nodes(domain_id, id)
);
CREATE INDEX IF NOT EXISTS idx_bcm_book ON book_curriculum_mappings(book_id);
CREATE INDEX IF NOT EXISTS idx_bcm_node ON book_curriculum_mappings(domain_id, node_id);

-- Retrieval practice questions per curriculum node
-- node_id can be empty for cross-node questions (e.g. temporal_ordering spanning multiple nodes)
CREATE TABLE IF NOT EXISTS retrieval_questions (
    id TEXT PRIMARY KEY,
    domain_id TEXT NOT NULL,
    node_id TEXT NOT NULL DEFAULT '',
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    question_type TEXT DEFAULT 'event',
    node_title TEXT DEFAULT '',
    cluster_label TEXT,
    generated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_rq_domain ON retrieval_questions(domain_id);
CREATE INDEX IF NOT EXISTS idx_rq_node ON retrieval_questions(domain_id, node_id);

-- Review scheduling state per question
CREATE TABLE IF NOT EXISTS review_schedule (
    question_id TEXT PRIMARY KEY REFERENCES retrieval_questions(id),
    review_count INTEGER DEFAULT 0,
    last_reviewed_at INTEGER,
    last_result TEXT,
    stability_days REAL DEFAULT 1.0,
    due_at INTEGER DEFAULT 0
);

-- Review answer history (append-only log)
CREATE TABLE IF NOT EXISTS review_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id TEXT NOT NULL REFERENCES retrieval_questions(id),
    result TEXT NOT NULL,
    reviewed_at TEXT NOT NULL,
    session_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_rh_question ON review_history(question_id);

-- Timeline entries per domain
CREATE TABLE IF NOT EXISTS timeline_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_id TEXT NOT NULL,
    year INTEGER NOT NULL,
    label TEXT NOT NULL,
    detail TEXT DEFAULT '',
    node_id TEXT,
    FOREIGN KEY (domain_id, node_id) REFERENCES curriculum_nodes(domain_id, id)
);
CREATE INDEX IF NOT EXISTS idx_tl_domain ON timeline_entries(domain_id);
CREATE INDEX IF NOT EXISTS idx_tl_year ON timeline_entries(year);

-- Cross-curriculum shared entities
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
    lens_title TEXT,
    lens_emphasis TEXT,
    PRIMARY KEY (entity_id, domain_id, node_id)
);

-- 20Q elicitation session logs
CREATE TABLE IF NOT EXISTS elicitation_sessions (
    id TEXT PRIMARY KEY,
    domain_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    questions_asked INTEGER DEFAULT 0,
    nodes_assessed INTEGER DEFAULT 0,
    responses TEXT DEFAULT '[]'
);
"""

MIGRATIONS = [
    # Add cached_question column if not present (idempotent)
    "ALTER TABLE review_items ADD COLUMN cached_question TEXT",
    # physical_books: add missing fields from JSON sync
    "ALTER TABLE physical_books ADD COLUMN finished_date TEXT",
    "ALTER TABLE physical_books ADD COLUMN category TEXT",
    "ALTER TABLE physical_books ADD COLUMN progress_percent REAL",
    # v2 question system: richer question metadata
    "ALTER TABLE retrieval_questions ADD COLUMN answer_type TEXT DEFAULT 'concept'",
    "ALTER TABLE retrieval_questions ADD COLUMN level INTEGER DEFAULT 1",
    "ALTER TABLE retrieval_questions ADD COLUMN anchors TEXT DEFAULT '[]'",
    "ALTER TABLE retrieval_questions ADD COLUMN memory_hook TEXT",
    "ALTER TABLE retrieval_questions ADD COLUMN prerequisite_questions TEXT DEFAULT '[]'",
    "ALTER TABLE retrieval_questions ADD COLUMN grading_options TEXT DEFAULT '[]'",
    "ALTER TABLE retrieval_questions ADD COLUMN rich_answer TEXT",
]


def init_db():
    """Create all tables if they don't exist, apply migrations."""
    conn = get_connection()
    conn.executescript(SCHEMA)
    for migration in MIGRATIONS:
        try:
            conn.execute(migration)
        except Exception:
            pass  # column already exists
    conn.commit()
    conn.close()
    print(f'[db] Initialized database at {DB_PATH}', flush=True)


# --- JSON field sets for articles ---

ARTICLE_JSON_FIELDS = {
    'key_claims', 'topics', 'interest_topics', 'novelty_claims',
    'entities', 'sources', 'follow_up_questions', 'similar_articles',
}

ARTICLE_OPTIONAL_FIELDS = [
    'fetch_method', 'exploration_tag', 'parent_id',
    'exploration_tier', 'exploration_order', 'ingested_at',
    'similar_articles',
]


# --- Pipeline sync helpers ---

def sync_articles(articles: list[dict], conn=None):
    """Write articles list to SQLite (articles + sections + claims). One transaction."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()

    conn.execute("DELETE FROM atomic_claims")
    conn.execute("DELETE FROM article_sections")
    conn.execute("DELETE FROM articles")

    for a in articles:
        values = {
            'id': a['id'],
            'title': a.get('title', ''),
            'author': a.get('author', ''),
            'source_url': a.get('source_url', ''),
            'hostname': a.get('hostname', ''),
            'date': a.get('date', ''),
            'content_markdown': a.get('content_markdown', ''),
            'one_line_summary': a.get('one_line_summary', ''),
            'full_summary': a.get('full_summary', ''),
            'estimated_read_minutes': a.get('estimated_read_minutes', 0),
            'content_type': a.get('content_type', 'unknown'),
            'word_count': a.get('word_count', 0),
        }

        for field in ARTICLE_JSON_FIELDS:
            if field in a:
                values[field] = json.dumps(a[field], ensure_ascii=False)
            elif field in ('similar_articles', 'entities', 'follow_up_questions',
                           'interest_topics', 'novelty_claims'):
                # Truly optional — store NULL if absent so export skips them
                values[field] = None
            else:
                values[field] = '[]'

        for field in ARTICLE_OPTIONAL_FIELDS:
            if field in ARTICLE_JSON_FIELDS:
                continue
            values[field] = a.get(field)

        cols = ', '.join(values.keys())
        placeholders = ', '.join(['?'] * len(values))
        conn.execute(f"INSERT INTO articles ({cols}) VALUES ({placeholders})", list(values.values()))

        for si, sec in enumerate(a.get('sections', [])):
            conn.execute(
                "INSERT INTO article_sections (article_id, section_index, heading, content, summary, key_claims) VALUES (?, ?, ?, ?, ?, ?)",
                (a['id'], si, sec.get('heading', ''), sec.get('content', ''),
                 sec.get('summary', ''), json.dumps(sec.get('key_claims', []), ensure_ascii=False)),
            )

        for claim in a.get('atomic_claims', []):
            conn.execute(
                "INSERT INTO atomic_claims (id, article_id, normalized_text, original_text, claim_type, source_paragraphs, topics) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (claim['id'], a['id'], claim.get('normalized_text', ''),
                 claim.get('original_text', ''), claim.get('claim_type', 'factual'),
                 json.dumps(claim.get('source_paragraphs', [])),
                 json.dumps(claim.get('topics', []), ensure_ascii=False)),
            )

    conn.commit()
    if own_conn:
        conn.close()
    return len(articles)


def sync_knowledge_index(ki_data: dict, conn=None):
    """Write knowledge index data to SQLite tables. One transaction."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()

    # Pipeline meta
    conn.execute("DELETE FROM pipeline_meta WHERE key LIKE 'knowledge_index_%'")
    for key in ('version', 'generated_at'):
        if key in ki_data:
            conn.execute("INSERT INTO pipeline_meta (key, value) VALUES (?, ?)",
                         (f"knowledge_index_{key}", str(ki_data[key])))
    if ki_data.get('stats'):
        conn.execute("INSERT INTO pipeline_meta (key, value) VALUES (?, ?)",
                     ("knowledge_index_stats", json.dumps(ki_data['stats'])))

    # Claim similarities
    conn.execute("DELETE FROM claim_similarities")
    sims = ki_data.get('similarities', [])
    if sims:
        conn.executemany(
            "INSERT INTO claim_similarities (claim_a, claim_b, score) VALUES (?, ?, ?)",
            [(p['a'], p['b'], p['score']) for p in sims])

    # NLI verdicts
    conn.execute("DELETE FROM nli_verdicts")
    verdicts = ki_data.get('nli_verdicts', {})
    if verdicts:
        rows = []
        for key, verdict in verdicts.items():
            parts = key.split('::')
            if len(parts) == 2:
                rows.append((parts[0], parts[1], verdict))
        conn.executemany("INSERT INTO nli_verdicts (claim_a, claim_b, verdict) VALUES (?, ?, ?)", rows)

    # Article similarities
    conn.execute("DELETE FROM article_similarities")
    asims = ki_data.get('article_similarities', [])
    if asims:
        conn.executemany(
            "INSERT INTO article_similarities (article_a, article_b, score) VALUES (?, ?, ?)",
            [(p['a'], p['b'], p['score']) for p in asims])

    # Article novelty matrix
    conn.execute("DELETE FROM article_novelty_matrix")
    anm = ki_data.get('article_novelty_matrix', {})
    rows = []
    for target_id, read_map in anm.items():
        for read_id, counts in read_map.items():
            rows.append((target_id, read_id, counts['new'], counts['extends'], counts['known']))
    if rows:
        conn.executemany(
            "INSERT INTO article_novelty_matrix (target_article_id, read_article_id, new_count, extends_count, known_count) VALUES (?, ?, ?, ?, ?)",
            rows)

    # Paragraph claim map
    conn.execute("DELETE FROM paragraph_claim_map")
    pmap = ki_data.get('paragraph_map', {})
    rows = []
    for article_id, para_map in pmap.items():
        for para_idx_str, claim_ids in para_map.items():
            for claim_id in claim_ids:
                rows.append((article_id, int(para_idx_str), claim_id))
    if rows:
        conn.executemany(
            "INSERT INTO paragraph_claim_map (article_id, paragraph_index, claim_id) VALUES (?, ?, ?)",
            rows)

    # Article curriculum nodes
    conn.execute("DELETE FROM article_curriculum_nodes")
    acn = ki_data.get('article_curriculum_nodes', {})
    rows = []
    for article_id, nodes in acn.items():
        for node in nodes:
            rows.append((article_id, node.get('domain_id', node.get('curriculum', '')),
                         node['node_id'], node.get('node_title', ''),
                         node.get('claim_count', 0), node.get('avg_similarity', 0),
                         node.get('max_similarity', 0)))
    if rows:
        conn.executemany(
            "INSERT INTO article_curriculum_nodes (article_id, domain_id, node_id, node_title, claim_count, avg_similarity, max_similarity) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows)

    # Delta reports
    conn.execute("DELETE FROM delta_reports")
    for topic, report in ki_data.get('delta_reports', {}).items():
        conn.execute(
            "INSERT INTO delta_reports (topic, summary, claim_count, article_count, top_claims, subtopics) VALUES (?, ?, ?, ?, ?, ?)",
            (topic, report.get('summary', ''), report.get('claim_count', 0),
             report.get('article_count', 0),
             json.dumps(report.get('top_claims', []), ensure_ascii=False),
             json.dumps(report.get('subtopics'), ensure_ascii=False) if report.get('subtopics') else None))

    conn.commit()
    if own_conn:
        conn.close()


def sync_clusters(clusters_data: dict, conn=None):
    """Write concept clusters to SQLite. One transaction."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()

    conn.execute("DELETE FROM cluster_meta")
    for key in ('version', 'generated_at'):
        if key in clusters_data:
            conn.execute("INSERT INTO cluster_meta (key, value) VALUES (?, ?)",
                         (key, str(clusters_data[key])))
    if clusters_data.get('parameters'):
        conn.execute("INSERT INTO cluster_meta (key, value) VALUES (?, ?)",
                     ('parameters', json.dumps(clusters_data['parameters'])))
    if clusters_data.get('stats'):
        conn.execute("INSERT INTO cluster_meta (key, value) VALUES (?, ?)",
                     ('stats', json.dumps(clusters_data['stats'])))

    conn.execute("DELETE FROM concept_clusters")
    for c in clusters_data.get('clusters', []):
        conn.execute(
            """INSERT INTO concept_clusters
               (cluster_id, label, size, articles, core_article_ids, peripheral_article_ids,
                top_topics, total_unique_claims, total_shared_claims, key_shared_claims,
                internal_edges, avg_edge_weight) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (c['cluster_id'], c.get('label', ''), c.get('size', 0),
             json.dumps(c.get('articles', []), ensure_ascii=False),
             json.dumps(c.get('core_article_ids', []), ensure_ascii=False),
             json.dumps(c.get('peripheral_article_ids', []), ensure_ascii=False),
             json.dumps(c.get('top_topics', []), ensure_ascii=False),
             c.get('total_unique_claims', 0), c.get('total_shared_claims', 0),
             json.dumps(c.get('key_shared_claims', []), ensure_ascii=False),
             c.get('internal_edges', 0), c.get('avg_edge_weight', 0)))

    conn.execute("DELETE FROM near_duplicates")
    for nd in clusters_data.get('near_duplicates', []):
        conn.execute(
            "INSERT INTO near_duplicates (article_a, article_b, title_a, title_b, known_claims, total_claims_a, overlap_ratio) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (nd['article_a'], nd['article_b'], nd.get('title_a', ''),
             nd.get('title_b', ''), nd.get('known_claims', 0),
             nd.get('total_claims_a', 0), nd.get('overlap_ratio', 0)))

    conn.commit()
    if own_conn:
        conn.close()


def sync_syntheses(syntheses_data: dict, conn=None):
    """Write syntheses to SQLite. One transaction."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()

    conn.execute("DELETE FROM pipeline_meta WHERE key LIKE 'syntheses_%'")
    if isinstance(syntheses_data, dict):
        for key in ('version', 'generated_at'):
            if key in syntheses_data:
                conn.execute("INSERT OR REPLACE INTO pipeline_meta (key, value) VALUES (?, ?)",
                             (f"syntheses_{key}", str(syntheses_data[key])))
        if syntheses_data.get('stats'):
            conn.execute("INSERT OR REPLACE INTO pipeline_meta (key, value) VALUES (?, ?)",
                         ("syntheses_stats", json.dumps(syntheses_data['stats'])))

    synths = syntheses_data.get('syntheses', []) if isinstance(syntheses_data, dict) else syntheses_data

    conn.execute("DELETE FROM syntheses")
    for s in synths:
        conn.execute(
            """INSERT INTO syntheses
               (cluster_id, label, synthesis_markdown, article_ids, article_coverage,
                claims_covered, unique_per_article, follow_up_questions, tensions,
                generated_at, total_articles, total_claims_covered, total_claims_in_cluster)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(s['cluster_id']), s.get('label', ''), s.get('synthesis_markdown', ''),
             json.dumps(s.get('article_ids', []), ensure_ascii=False),
             json.dumps(s.get('article_coverage', {}), ensure_ascii=False),
             json.dumps(s.get('claims_covered', []), ensure_ascii=False),
             json.dumps(s.get('unique_per_article', {}), ensure_ascii=False),
             json.dumps(s.get('follow_up_questions', []), ensure_ascii=False),
             json.dumps(s.get('tensions', []), ensure_ascii=False),
             s.get('generated_at', ''),
             s.get('total_articles', 0), s.get('total_claims_covered', 0),
             s.get('total_claims_in_cluster', 0)))

    conn.commit()
    if own_conn:
        conn.close()


# --- Book sync helpers (replaces physical_books.json) ---

BOOK_FIELDS = [
    'id', 'title', 'author', 'cover_image_uri', 'cover_url', 'isbn', 'publisher',
    'year', 'page_count', 'language', 'topics', 'chapters', 'current_chapter',
    'current_page', 'reading_status', 'significance', 'added_at', 'last_interaction_at',
    'metadata_source', 'processing_status', 'kindle_asin', 'kindle_book_id',
    'finished_date', 'category', 'progress_percent',
]

BOOK_JSON_FIELDS = {'topics', 'chapters'}

CAPTURE_FIELDS = [
    'id', 'book_id', 'type', 'created_at', 'audio_uri', 'transcript',
    'transcription_status', 'photo_uri', 'ocr_text', 'ocr_status', 'text',
    'page_number', 'chapter', 'extracted_ideas', 'topics', 'key_passage',
    'elaborative_question', 'server_id', 'upload_status',
]

CAPTURE_JSON_FIELDS = {'extracted_ideas', 'topics'}


def upsert_books(books: list[dict], conn=None):
    """Upsert books into physical_books table. Client wins for same ID."""
    own = conn is None
    if own:
        conn = get_connection()
    for book in books:
        values = {}
        for f in BOOK_FIELDS:
            v = book.get(f)
            if f in BOOK_JSON_FIELDS and isinstance(v, (list, dict)):
                v = json.dumps(v, ensure_ascii=False)
            values[f] = v
        if not values.get('id'):
            continue
        cols = ', '.join(values.keys())
        placeholders = ', '.join(['?'] * len(values))
        updates = ', '.join(f'{k}=excluded.{k}' for k in values if k != 'id')
        conn.execute(
            f'INSERT INTO physical_books ({cols}) VALUES ({placeholders}) '
            f'ON CONFLICT(id) DO UPDATE SET {updates}',
            list(values.values())
        )
    if own:
        conn.commit()
        conn.close()
    return len(books)


def upsert_captures(captures: list[dict], conn=None):
    """Upsert captures into book_captures table. Client wins for same ID."""
    own = conn is None
    if own:
        conn = get_connection()
    for cap in captures:
        values = {}
        for f in CAPTURE_FIELDS:
            v = cap.get(f)
            if f in CAPTURE_JSON_FIELDS and isinstance(v, (list, dict)):
                v = json.dumps(v, ensure_ascii=False)
            values[f] = v
        if not values.get('id'):
            continue
        cols = ', '.join(values.keys())
        placeholders = ', '.join(['?'] * len(values))
        updates = ', '.join(f'{k}=excluded.{k}' for k in values if k != 'id')
        conn.execute(
            f'INSERT INTO book_captures ({cols}) VALUES ({placeholders}) '
            f'ON CONFLICT(id) DO UPDATE SET {updates}',
            list(values.values())
        )
    if own:
        conn.commit()
        conn.close()
    return len(captures)


def load_all_books_and_captures(conn=None) -> dict:
    """Load all books and captures from SQLite. Returns {books: [...], captures: [...]}."""
    own = conn is None
    if own:
        conn = get_connection(readonly=True)
    try:
        books = []
        for row in conn.execute('SELECT * FROM physical_books ORDER BY last_interaction_at DESC').fetchall():
            book = dict(row)
            for f in BOOK_JSON_FIELDS:
                if isinstance(book.get(f), str):
                    try:
                        book[f] = json.loads(book[f])
                    except (json.JSONDecodeError, TypeError):
                        pass
            books.append(book)

        captures = []
        for row in conn.execute('SELECT * FROM book_captures ORDER BY created_at DESC').fetchall():
            cap = dict(row)
            for f in CAPTURE_JSON_FIELDS:
                if isinstance(cap.get(f), str):
                    try:
                        cap[f] = json.loads(cap[f])
                    except (json.JSONDecodeError, TypeError):
                        pass
            captures.append(cap)

        return {'books': books, 'captures': captures}
    finally:
        if own:
            conn.close()


def migrate_books_json_to_sqlite():
    """One-time migration: physical_books.json → SQLite tables."""
    books_path = Path(os.environ.get('PHYSICAL_BOOKS_PATH', '/opt/petrarca/data/physical_books.json'))
    if not books_path.exists():
        print('[db] No physical_books.json found, skipping', flush=True)
        return

    data = json.loads(books_path.read_text())
    books = data.get('books', [])
    captures = data.get('captures', [])

    conn = get_connection()
    book_count = upsert_books(books, conn)
    cap_count = upsert_captures(captures, conn)
    conn.commit()
    conn.close()
    print(f'[db] Migrated {book_count} books, {cap_count} captures from JSON → SQLite', flush=True)


# --- Migration helpers ---

def migrate_projects():
    """Migrate projects.json → projects + project_notes tables."""
    projects_path = Path(os.environ.get('PROJECTS_PATH', '/opt/petrarca/data/projects.json'))
    if not projects_path.exists():
        print('[db] No projects.json found, skipping', flush=True)
        return

    data = json.loads(projects_path.read_text())
    conn = get_connection()

    for p in data.get('projects', []):
        conn.execute(
            "INSERT OR IGNORE INTO projects (id, name, description, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (p['id'], p['name'], p.get('description', ''), p.get('status', 'active'), p['created_at']),
        )

    for n in data.get('notes', []):
        conn.execute(
            "INSERT OR IGNORE INTO project_notes (id, project_id, text, audio_file, source, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (n['id'], n['project_id'], n.get('text', ''), n.get('audio_file'),
             json.dumps(n.get('source')) if n.get('source') else None, n['created_at']),
        )

    conn.commit()
    proj_count = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    note_count = conn.execute("SELECT COUNT(*) FROM project_notes").fetchone()[0]
    conn.close()

    print(f'[db] Migrated {proj_count} projects, {note_count} notes', flush=True)


def migrate_review_items_to_knowledge_items(conn) -> int:
    """Collapse review_items (one per book×chapter×node) into knowledge_items (one per node).

    For each distinct (curriculum_domain, curriculum_node_id) pair in review_items, picks
    the best scheduling state (max stability, max review_count) and accumulates all
    book/chapter sources into a JSON array.  Uses INSERT OR IGNORE so running twice is safe.
    Returns count of rows inserted.
    """
    import json as _json

    groups = conn.execute('''
        SELECT curriculum_domain, curriculum_node_id,
               MAX(stability_days) as stability_days,
               MAX(due_at) as due_at,
               MAX(review_count) as review_count,
               MIN(created_at) as created_at,
               last_score
        FROM review_items
        WHERE curriculum_node_id IS NOT NULL AND curriculum_domain IS NOT NULL
        GROUP BY curriculum_domain, curriculum_node_id
    ''').fetchall()

    count = 0
    for g in groups:
        item_id = f"{g['curriculum_domain']}:{g['curriculum_node_id']}"

        rows = conn.execute('''
            SELECT source_book_id, source_chapter_number, source_chapter_title,
                   source_text, lens, temporal_hook, created_at
            FROM review_items
            WHERE curriculum_domain=? AND curriculum_node_id=?
        ''', (g['curriculum_domain'], g['curriculum_node_id'])).fetchall()

        sources = []
        seen = set()
        for r in rows:
            key = (r['source_book_id'], r['source_chapter_number'])
            if key not in seen:
                seen.add(key)
                sources.append({
                    'book_id': r['source_book_id'],
                    'chapter_number': r['source_chapter_number'],
                    'chapter_title': r['source_chapter_title'],
                    'source_text': r['source_text'] or '',
                    'lens': r['lens'] or 'SIGNIFICANCE',
                    'temporal_hook': r['temporal_hook'] or '',
                    'added_at': r['created_at'],
                })

        try:
            conn.execute('''
                INSERT OR IGNORE INTO knowledge_items
                (id, curriculum_node_id, curriculum_domain, stability_days, due_at,
                 last_score, review_count, sources, question_history, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            ''', (
                item_id, g['curriculum_node_id'], g['curriculum_domain'],
                g['stability_days'], g['due_at'], g['last_score'],
                g['review_count'], _json.dumps(sources), '[]', g['created_at'],
            ))
            count += 1
        except Exception as e:
            print(f'[migrate] skip {item_id}: {e}', flush=True)

    conn.commit()
    return count


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: python db.py [init|migrate <type>]')
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == 'init':
        init_db()
    elif cmd == 'migrate':
        init_db()
        data_type = sys.argv[2] if len(sys.argv) > 2 else 'all'
        if data_type in ('projects', 'all'):
            migrate_projects()
        if data_type in ('knowledge_items', 'all'):
            conn = get_connection()
            n = migrate_review_items_to_knowledge_items(conn)
            conn.close()
            print(f'[db] Migrated {n} knowledge_items from review_items', flush=True)
        if data_type in ('books', 'all'):
            migrate_books_json_to_sqlite()
    else:
        print(f'Unknown command: {cmd}')

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
"""


def init_db():
    """Create all tables if they don't exist."""
    conn = get_connection()
    conn.executescript(SCHEMA)
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
    else:
        print(f'Unknown command: {cmd}')

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

sys.path.insert(0, '/opt/amygdala')
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
"""


def init_db():
    """Create all tables if they don't exist."""
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print(f'[db] Initialized database at {DB_PATH}', flush=True)


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

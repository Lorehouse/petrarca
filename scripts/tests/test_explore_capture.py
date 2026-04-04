"""Tests for the explore capture pipeline.

Tests the note-saving and entity-routing logic using an in-memory SQLite DB.
No real Soniox/Gemini calls — the LLM analysis is provided as a dict.

Run: cd scripts && python -m pytest tests/test_explore_capture.py -v
"""

import json
import sqlite3
import sys
import time
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPT_DIR))


# --- In-memory DB setup (mirrors the real schema) ---

SCHEMA = """
CREATE TABLE IF NOT EXISTS shared_entities (
    entity_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    entity_type TEXT,
    modern_name TEXT,
    wikipedia_url TEXT,
    latitude REAL,
    longitude REAL,
    aliases TEXT DEFAULT '[]',
    dates TEXT,
    date_start INTEGER,
    date_end INTEGER,
    nexus_score INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS entity_curriculum_links (
    entity_id TEXT NOT NULL,
    domain_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    lens_title TEXT,
    lens_emphasis TEXT,
    PRIMARY KEY (entity_id, domain_id, node_id)
);

CREATE TABLE IF NOT EXISTS entity_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS voice_transcripts (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    node_id TEXT,
    domain_id TEXT,
    node_title TEXT,
    transcript TEXT NOT NULL,
    audio_bytes INTEGER,
    llm_result TEXT,
    microlearning_triggered TEXT DEFAULT '[]',
    created_at INTEGER NOT NULL
);
"""


@pytest.fixture
def conn():
    """In-memory SQLite with the tables needed for explore capture."""
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)

    # Seed test entities
    db.execute(
        "INSERT INTO shared_entities (entity_id, name, description, entity_type) "
        "VALUES (?, ?, ?, ?)",
        ('plato', 'Plato', 'Ancient Greek philosopher, student of Socrates', 'person'),
    )
    db.execute(
        "INSERT INTO shared_entities (entity_id, name, description, entity_type) "
        "VALUES (?, ?, ?, ?)",
        ('athens', 'Athens', 'Major Greek city-state', 'place'),
    )
    db.execute(
        "INSERT INTO entity_curriculum_links (entity_id, domain_id, node_id, lens_title) "
        "VALUES (?, ?, ?, ?)",
        ('plato', 'ancient_greece', 'ag_plato_academy', 'Philosophy'),
    )
    db.commit()
    yield db
    db.close()


# --- Extracted pipeline logic (mirrors the handler's DB portion) ---

def run_capture_pipeline(
    conn: sqlite3.Connection,
    transcript: str,
    analysis: dict,
    entity_id: str | None,
    entity_name: str | None,
    mode: str,
) -> dict:
    """
    The DB portion of _handle_explore_capture, extracted for testability.

    Takes a pre-computed LLM analysis dict and a connection, does all the
    DB writes, returns the result dict.
    """
    claims = analysis.get('knowledge_claims', [])
    queries = analysis.get('queries', [])
    entities_mentioned = analysis.get('entities_mentioned', [])
    now_ms = int(time.time() * 1000)
    notes_saved = 0

    # Entity-scoped: save claims as a note on the target entity
    if entity_id and claims:
        note_text = '\n'.join(f'• {c}' for c in claims)
        conn.execute(
            'INSERT INTO entity_notes (entity_id, note, created_at) VALUES (?, ?, ?)',
            (entity_id, note_text, now_ms),
        )
        notes_saved += 1

    # General mode: route to matching entities
    if mode == 'general' and entities_mentioned:
        rows = conn.execute(
            'SELECT entity_id, name FROM shared_entities WHERE name IN ({})'.format(
                ','.join('?' * len(entities_mentioned))
            ),
            entities_mentioned,
        ).fetchall()
        for r in rows:
            if claims:
                note_text = '\n'.join(f'• {c}' for c in claims)
                conn.execute(
                    'INSERT INTO entity_notes (entity_id, note, created_at) VALUES (?, ?, ?)',
                    (r['entity_id'], note_text, now_ms),
                )
                notes_saved += 1

    conn.commit()

    return {
        'status': 'completed',
        'transcript': transcript,
        'notes_saved': notes_saved,
        'research_triggered': [],  # would be filled by create_microlearning_request
        'entities_detected': entities_mentioned,
    }


# --- Tests ---

class TestEntityScopedCapture:
    """When mode='entity' and entity_id is provided."""

    def test_saves_claims_as_note(self, conn):
        result = run_capture_pipeline(
            conn,
            transcript='Plato was a student of Socrates and founded the Academy',
            analysis={
                'knowledge_claims': [
                    'Plato was a student of Socrates',
                    'Plato founded the Academy',
                ],
                'queries': [],
                'entities_mentioned': ['Plato', 'Socrates'],
            },
            entity_id='plato',
            entity_name='Plato',
            mode='entity',
        )

        assert result['status'] == 'completed'
        assert result['notes_saved'] == 1

        # Verify note was written to DB
        notes = conn.execute(
            'SELECT * FROM entity_notes WHERE entity_id = ?', ('plato',)
        ).fetchall()
        assert len(notes) == 1
        assert '• Plato was a student of Socrates' in notes[0]['note']
        assert '• Plato founded the Academy' in notes[0]['note']

    def test_no_claims_means_no_notes(self, conn):
        result = run_capture_pipeline(
            conn,
            transcript='I wonder about Plato',
            analysis={
                'knowledge_claims': [],
                'queries': ['What was Plato known for?'],
                'entities_mentioned': ['Plato'],
            },
            entity_id='plato',
            entity_name='Plato',
            mode='entity',
        )

        assert result['notes_saved'] == 0
        notes = conn.execute('SELECT * FROM entity_notes').fetchall()
        assert len(notes) == 0

    def test_multiple_captures_accumulate(self, conn):
        """Triggering capture multiple times should create multiple notes."""
        for i in range(3):
            run_capture_pipeline(
                conn,
                transcript=f'Fact {i}',
                analysis={'knowledge_claims': [f'Claim {i}'], 'queries': [], 'entities_mentioned': []},
                entity_id='plato',
                entity_name='Plato',
                mode='entity',
            )

        notes = conn.execute(
            'SELECT * FROM entity_notes WHERE entity_id = ?', ('plato',)
        ).fetchall()
        assert len(notes) == 3


class TestGeneralCapture:
    """When mode='general' — entities are auto-detected and routed."""

    def test_routes_to_known_entities(self, conn):
        result = run_capture_pipeline(
            conn,
            transcript='Plato taught in Athens at the Academy',
            analysis={
                'knowledge_claims': ['Plato taught at the Academy in Athens'],
                'queries': [],
                'entities_mentioned': ['Plato', 'Athens'],
            },
            entity_id=None,
            entity_name=None,
            mode='general',
        )

        assert result['notes_saved'] == 2  # one for Plato, one for Athens
        assert set(result['entities_detected']) == {'Plato', 'Athens'}

        plato_notes = conn.execute(
            'SELECT * FROM entity_notes WHERE entity_id = ?', ('plato',)
        ).fetchall()
        athens_notes = conn.execute(
            'SELECT * FROM entity_notes WHERE entity_id = ?', ('athens',)
        ).fetchall()
        assert len(plato_notes) == 1
        assert len(athens_notes) == 1

    def test_unknown_entities_are_ignored(self, conn):
        """Entities mentioned but not in shared_entities don't crash."""
        result = run_capture_pipeline(
            conn,
            transcript='I read about Aristotle in Stagira',
            analysis={
                'knowledge_claims': ['Aristotle was born in Stagira'],
                'queries': [],
                'entities_mentioned': ['Aristotle', 'Stagira'],  # neither is in our DB
            },
            entity_id=None,
            entity_name=None,
            mode='general',
        )

        assert result['notes_saved'] == 0
        assert result['entities_detected'] == ['Aristotle', 'Stagira']

    def test_mix_of_known_and_unknown(self, conn):
        result = run_capture_pipeline(
            conn,
            transcript='Plato and Aristotle both studied in Athens',
            analysis={
                'knowledge_claims': ['Both Plato and Aristotle studied in Athens'],
                'queries': [],
                'entities_mentioned': ['Plato', 'Aristotle', 'Athens'],
            },
            entity_id=None,
            entity_name=None,
            mode='general',
        )

        # Only Plato and Athens are in our DB
        assert result['notes_saved'] == 2

    def test_no_claims_no_notes_even_with_entities(self, conn):
        result = run_capture_pipeline(
            conn,
            transcript='Tell me about Plato',
            analysis={
                'knowledge_claims': [],
                'queries': ['Who was Plato?'],
                'entities_mentioned': ['Plato'],
            },
            entity_id=None,
            entity_name=None,
            mode='general',
        )

        assert result['notes_saved'] == 0


class TestEdgeCases:
    def test_empty_transcript(self, conn):
        result = run_capture_pipeline(
            conn,
            transcript='',
            analysis={'knowledge_claims': [], 'queries': [], 'entities_mentioned': []},
            entity_id='plato',
            entity_name='Plato',
            mode='entity',
        )
        assert result['status'] == 'completed'
        assert result['notes_saved'] == 0

    def test_entity_id_not_in_db(self, conn):
        """Entity ID provided but not in shared_entities — still saves note."""
        result = run_capture_pipeline(
            conn,
            transcript='Socrates drank hemlock',
            analysis={
                'knowledge_claims': ['Socrates drank hemlock'],
                'queries': [],
                'entities_mentioned': ['Socrates'],
            },
            entity_id='socrates',  # not in our test DB
            entity_name='Socrates',
            mode='entity',
        )
        # Note is saved to entity_notes even if entity isn't in shared_entities
        # (entity_notes has no FK constraint)
        assert result['notes_saved'] == 1

    def test_llm_fallback_on_failure(self, conn):
        """Simulates what happens when LLM analysis fails — transcript becomes the claim."""
        result = run_capture_pipeline(
            conn,
            transcript='Plato wrote the Republic',
            analysis={
                'knowledge_claims': ['Plato wrote the Republic'],
                'queries': [],
                'entities_mentioned': [],
            },
            entity_id='plato',
            entity_name='Plato',
            mode='entity',
        )
        assert result['notes_saved'] == 1
        note = conn.execute('SELECT note FROM entity_notes WHERE entity_id = ?', ('plato',)).fetchone()
        assert 'Republic' in note['note']

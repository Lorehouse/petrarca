"""Tests for scripts/merge_entity_dupes.py.

Exercises the safety classifier, the find_dedup_pairs query, and an
end-to-end merge against an in-memory DB.

Run: cd scripts && python3 -m pytest tests/test_merge_entity_dupes.py -v
"""

import json
import sqlite3
import sys
import time
import uuid
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPT_DIR))


SCHEMA = """
CREATE TABLE IF NOT EXISTS shared_entities (
    entity_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    entity_type TEXT,
    nexus_score INTEGER DEFAULT 1,
    wikidata_qid TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_shared_entities_qid
    ON shared_entities(wikidata_qid) WHERE wikidata_qid IS NOT NULL;

CREATE TABLE IF NOT EXISTS entity_curriculum_links (
    entity_id TEXT NOT NULL,
    domain_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    lens_title TEXT,
    PRIMARY KEY (entity_id, domain_id, node_id)
);

CREATE TABLE IF NOT EXISTS entity_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS entity_resolutions (
    id TEXT PRIMARY KEY,
    entity_id TEXT,
    capture_id TEXT,
    mention_text TEXT NOT NULL,
    context_excerpt TEXT,
    type_hint TEXT,
    candidate_qids TEXT,
    chosen_qid TEXT,
    confidence REAL NOT NULL,
    status TEXT NOT NULL,
    resolver_model TEXT,
    reasoning TEXT,
    cost_usd REAL DEFAULT 0,
    created_at INTEGER NOT NULL,
    superseded_by TEXT,
    date_hint_start INTEGER,
    date_hint_end INTEGER
);

CREATE TABLE IF NOT EXISTS entity_external_ids (
    entity_id TEXT NOT NULL,
    property_id TEXT NOT NULL,
    value TEXT NOT NULL,
    source TEXT DEFAULT 'wikidata',
    PRIMARY KEY (entity_id, property_id, value)
);
"""


@pytest.fixture
def conn():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    db.commit()
    yield db
    db.close()


# ---------- Safety classifier ----------

def test_is_safe_suffix_person():
    from merge_entity_dupes import is_high_confidence_dupe
    pair = {"canonical": "homer", "duplicate": "homer_person",
            "canonical_name": "Homer", "duplicate_name": "Homer"}
    ok, reason = is_high_confidence_dupe(pair)
    assert ok is True
    assert "suffix" in reason


def test_is_safe_suffix_place():
    from merge_entity_dupes import is_high_confidence_dupe
    pair = {"canonical": "rome", "duplicate": "rome_place",
            "canonical_name": "Rome", "duplicate_name": "Rome"}
    ok, reason = is_high_confidence_dupe(pair)
    assert ok is True


def test_is_safe_known_alias():
    from merge_entity_dupes import is_high_confidence_dupe
    pair = {"canonical": "augustus", "duplicate": "octavian",
            "canonical_name": "Augustus", "duplicate_name": "Octavian"}
    ok, reason = is_high_confidence_dupe(pair)
    assert ok is True
    assert reason == "known-alias"


def test_is_safe_identical_name_different_ids():
    from merge_entity_dupes import is_high_confidence_dupe
    pair = {"canonical": "empire", "duplicate": "roman_empire_place",
            "canonical_name": "Empire", "duplicate_name": "Empire"}
    ok, reason = is_high_confidence_dupe(pair)
    assert ok is True
    assert reason == "identical-name"


def test_is_safe_of_place_dupe():
    from merge_entity_dupes import is_high_confidence_dupe
    # Distinct names so the identical-name heuristic doesn't fire first.
    pair = {"canonical": "empedocles", "duplicate": "empedocles_of_akragas",
            "canonical_name": "Empedocles", "duplicate_name": "Empedocles of Akragas"}
    ok, reason = is_high_confidence_dupe(pair)
    assert ok is True
    assert reason == "of-place-dupe"


def test_is_safe_regnal_suffix():
    from merge_entity_dupes import is_high_confidence_dupe
    pair = {"canonical": "constantine", "duplicate": "constantine_i",
            "canonical_name": "Constantine", "duplicate_name": "Constantine I"}
    ok, reason = is_high_confidence_dupe(pair)
    assert ok is True
    assert "regnal" in reason


def test_is_safe_ancient_greece_curriculum_alias():
    """Petrarca's `greece` entity is actually 'Ancient civilization conquered
    by Rome' — the curriculum uses it as a dupe of ancient_greece. The
    classifier treats this as a known-alias after session 70 analysis."""
    from merge_entity_dupes import is_high_confidence_dupe
    pair = {"canonical": "ancient_greece", "duplicate": "greece",
            "canonical_name": "Ancient Greece", "duplicate_name": "Greece"}
    ok, reason = is_high_confidence_dupe(pair)
    assert ok is True
    assert reason == "known-alias"


def test_is_unsafe_different_concepts():
    """Generic vs specific should remain REVIEW-only."""
    from merge_entity_dupes import is_high_confidence_dupe
    pair = {"canonical": "abbasid_caliphate", "duplicate": "arab_caliphates",
            "canonical_name": "Abbasid Caliphate", "duplicate_name": "Arab Caliphates"}
    ok, reason = is_high_confidence_dupe(pair)
    assert ok is False
    assert reason == "needs-review"


def test_is_unsafe_parent_vs_specific():
    from merge_entity_dupes import is_high_confidence_dupe
    pair = {"canonical": "abbasid_caliphate", "duplicate": "arab_caliphates",
            "canonical_name": "Abbasid Caliphate", "duplicate_name": "Arab Caliphates"}
    ok, reason = is_high_confidence_dupe(pair)
    assert ok is False


# ---------- find_dedup_pairs query ----------

def test_find_dedup_pairs_identifies_merge_candidate(conn):
    from merge_entity_dupes import find_dedup_pairs

    conn.execute(
        "INSERT INTO shared_entities (entity_id, name, wikidata_qid) VALUES ('augustus', 'Augustus', 'Q1405')"
    )
    conn.execute(
        "INSERT INTO shared_entities (entity_id, name) VALUES ('octavian', 'Octavian')"
    )
    conn.execute(
        """
        INSERT INTO entity_resolutions (
            id, entity_id, mention_text, chosen_qid, confidence, status,
            resolver_model, created_at
        ) VALUES ('er1', 'octavian', 'Octavian', 'Q1405', 0.9, 'needs_review',
                  'deterministic-0.1', ?)
        """,
        (int(time.time()),),
    )
    conn.commit()

    pairs = find_dedup_pairs(conn)
    assert len(pairs) == 1
    assert pairs[0]["canonical"] == "augustus"
    assert pairs[0]["duplicate"] == "octavian"
    assert pairs[0]["qid"] == "Q1405"


def test_find_dedup_pairs_dedups_multiple_audit_rows(conn):
    """Pre-supersede-logic DBs may have multiple active rows for same pair."""
    from merge_entity_dupes import find_dedup_pairs

    conn.execute(
        "INSERT INTO shared_entities (entity_id, name, wikidata_qid) VALUES ('rome', 'Rome', 'Q220')"
    )
    conn.execute(
        "INSERT INTO shared_entities (entity_id, name) VALUES ('rome_place', 'Rome')"
    )
    # Two needs_review rows for the same pair (stale + fresh).
    for i, ts in enumerate([1000, 2000]):
        conn.execute(
            """
            INSERT INTO entity_resolutions (
                id, entity_id, mention_text, chosen_qid, confidence, status,
                resolver_model, created_at
            ) VALUES (?, 'rome_place', 'Rome', 'Q220', 0.9, 'needs_review',
                      'deterministic-0.1', ?)
            """,
            (f"er{i}", ts),
        )
    conn.commit()

    pairs = find_dedup_pairs(conn)
    # Dedup by (qid, duplicate) should return just one.
    assert len(pairs) == 1
    # Uses the latest resolution row.
    assert pairs[0]["resolution_id"] == "er1"


def test_find_dedup_pairs_skips_already_merged(conn):
    from merge_entity_dupes import find_dedup_pairs

    # Only canonical exists — duplicate already deleted.
    conn.execute(
        "INSERT INTO shared_entities (entity_id, name, wikidata_qid) VALUES ('rome', 'Rome', 'Q220')"
    )
    conn.commit()

    assert find_dedup_pairs(conn) == []


# ---------- End-to-end merge ----------

def test_merge_pair_moves_references_and_deletes_duplicate(conn):
    from merge_entity_dupes import merge_pair
    from io import StringIO

    conn.execute(
        "INSERT INTO shared_entities (entity_id, name, wikidata_qid) VALUES ('augustus', 'Augustus', 'Q1405')"
    )
    conn.execute(
        "INSERT INTO shared_entities (entity_id, name) VALUES ('octavian', 'Octavian')"
    )

    # Octavian has a curriculum link, a note, and an external ID.
    conn.execute(
        "INSERT INTO entity_curriculum_links (entity_id, domain_id, node_id) "
        "VALUES ('octavian', 'ancient_rome', 'octavian_node')"
    )
    conn.execute(
        "INSERT INTO entity_notes (entity_id, note, created_at) "
        "VALUES ('octavian', 'before he became Augustus', ?)", (int(time.time()),)
    )
    conn.execute(
        "INSERT INTO entity_external_ids (entity_id, property_id, value) "
        "VALUES ('octavian', 'P214', '1001')"
    )

    rid = str(uuid.uuid4())[:8]
    conn.execute(
        """
        INSERT INTO entity_resolutions (
            id, entity_id, mention_text, chosen_qid, confidence, status,
            resolver_model, created_at
        ) VALUES (?, 'octavian', 'Octavian', 'Q1405', 0.9, 'needs_review',
                  'deterministic-0.1', ?)
        """,
        (rid, int(time.time())),
    )
    conn.commit()

    audit = StringIO()
    summary = merge_pair(
        conn, canonical="augustus", duplicate="octavian", qid="Q1405",
        resolution_id=rid, dry_run=False, audit_log=audit,
    )

    # Duplicate row gone.
    assert conn.execute(
        "SELECT COUNT(*) FROM shared_entities WHERE entity_id = 'octavian'"
    ).fetchone()[0] == 0
    assert summary["deleted_duplicate"] is True

    # Curriculum link moved.
    assert conn.execute(
        "SELECT COUNT(*) FROM entity_curriculum_links WHERE entity_id = 'augustus'"
    ).fetchone()[0] == 1
    # Notes moved.
    assert conn.execute(
        "SELECT COUNT(*) FROM entity_notes WHERE entity_id = 'augustus'"
    ).fetchone()[0] == 1
    # External IDs moved.
    assert conn.execute(
        "SELECT COUNT(*) FROM entity_external_ids WHERE entity_id = 'augustus'"
    ).fetchone()[0] == 1

    # Original needs_review row got superseded by the merge row.
    prior = conn.execute(
        "SELECT superseded_by FROM entity_resolutions WHERE id = ?", (rid,)
    ).fetchone()
    assert prior["superseded_by"] is not None

    # New merge audit row exists.
    merge_row = conn.execute(
        "SELECT * FROM entity_resolutions WHERE capture_id = 'merge' AND chosen_qid='Q1405'"
    ).fetchone()
    assert merge_row is not None
    assert merge_row["entity_id"] == "augustus"
    assert merge_row["status"] == "resolved"


def test_merge_pair_handles_pk_collision(conn):
    """If both entities have a curriculum_link to the same (domain, node),
    the duplicate's row is dropped rather than causing an IntegrityError."""
    from merge_entity_dupes import merge_pair
    from io import StringIO

    conn.execute(
        "INSERT INTO shared_entities (entity_id, name, wikidata_qid) VALUES ('augustus', 'Augustus', 'Q1405')"
    )
    conn.execute(
        "INSERT INTO shared_entities (entity_id, name) VALUES ('octavian', 'Octavian')"
    )
    # Both point at the same curriculum node.
    conn.execute(
        "INSERT INTO entity_curriculum_links (entity_id, domain_id, node_id) "
        "VALUES ('augustus', 'ancient_rome', 'first_emperor')"
    )
    conn.execute(
        "INSERT INTO entity_curriculum_links (entity_id, domain_id, node_id) "
        "VALUES ('octavian', 'ancient_rome', 'first_emperor')"
    )

    rid = str(uuid.uuid4())[:8]
    conn.execute(
        """
        INSERT INTO entity_resolutions (
            id, entity_id, mention_text, chosen_qid, confidence, status,
            resolver_model, created_at
        ) VALUES (?, 'octavian', 'Octavian', 'Q1405', 0.9, 'needs_review',
                  'deterministic-0.1', ?)
        """,
        (rid, int(time.time())),
    )
    conn.commit()

    audit = StringIO()
    summary = merge_pair(
        conn, canonical="augustus", duplicate="octavian", qid="Q1405",
        resolution_id=rid, dry_run=False, audit_log=audit,
    )

    # Collision dropped, canonical still has its row.
    assert summary["dropped_dupes"]["entity_curriculum_links"] == 1
    remaining = conn.execute(
        "SELECT entity_id FROM entity_curriculum_links WHERE node_id = 'first_emperor'"
    ).fetchall()
    assert len(remaining) == 1
    assert remaining[0]["entity_id"] == "augustus"


def test_merge_pair_rejects_if_canonical_lacks_qid(conn):
    """Sanity check: refuses to merge if canonical doesn't actually own the QID."""
    from merge_entity_dupes import merge_pair
    from io import StringIO

    conn.execute(
        "INSERT INTO shared_entities (entity_id, name) VALUES ('augustus', 'Augustus')"
    )
    conn.execute(
        "INSERT INTO shared_entities (entity_id, name) VALUES ('octavian', 'Octavian')"
    )
    conn.commit()

    audit = StringIO()
    with pytest.raises(RuntimeError, match="does not own QID"):
        merge_pair(
            conn, canonical="augustus", duplicate="octavian", qid="Q1405",
            resolution_id="nonexistent", dry_run=False, audit_log=audit,
        )


def test_merge_pair_dry_run_makes_no_changes(conn):
    from merge_entity_dupes import merge_pair
    from io import StringIO

    conn.execute(
        "INSERT INTO shared_entities (entity_id, name, wikidata_qid) VALUES ('augustus', 'Augustus', 'Q1405')"
    )
    conn.execute(
        "INSERT INTO shared_entities (entity_id, name) VALUES ('octavian', 'Octavian')"
    )
    conn.commit()

    audit = StringIO()
    merge_pair(
        conn, canonical="augustus", duplicate="octavian", qid="Q1405",
        resolution_id="rid", dry_run=True, audit_log=audit,
    )

    # Duplicate still exists.
    assert conn.execute(
        "SELECT COUNT(*) FROM shared_entities WHERE entity_id = 'octavian'"
    ).fetchone()[0] == 1

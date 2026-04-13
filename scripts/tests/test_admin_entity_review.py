"""Tests for the /admin/entity* endpoints in research-server.py.

Tests the SQL query logic, dedup semantics, and superseded_by chaining
directly against an in-memory DB, without spinning up the HTTP server.
The handlers are thin wrappers over these queries — testing the queries
covers the behaviour users care about.

Run: cd scripts && python3 -m pytest tests/test_admin_entity_review.py -v
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

CREATE TABLE IF NOT EXISTS curriculum_nodes (
    id TEXT, domain_id TEXT, title TEXT, description TEXT,
    PRIMARY KEY (id, domain_id)
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


def insert_resolution(conn, *, entity_id, status="ambiguous", chosen_qid=None,
                      mention=None, confidence=0.5, candidates=None,
                      created_at=None, superseded_by=None, reasoning="",
                      resolver_model="deterministic-0.1"):
    """Convenience: insert an entity_resolutions row, return its id."""
    rid = f"er_{uuid.uuid4().hex[:12]}"
    conn.execute(
        """
        INSERT INTO entity_resolutions (
            id, entity_id, mention_text, candidate_qids, chosen_qid,
            confidence, status, resolver_model, reasoning, created_at,
            superseded_by
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            rid, entity_id, mention or entity_id,
            json.dumps(candidates or []),
            chosen_qid, confidence, status, resolver_model, reasoning,
            created_at if created_at is not None else int(time.time()),
            superseded_by,
        ),
    )
    return rid


# ---------- queue-data query (dedup via MAX(created_at)) ----------

QUEUE_QUERY_TEMPLATE = """
    SELECT er.id, er.entity_id, er.mention_text, er.status, er.chosen_qid,
           er.confidence, er.candidate_qids
    FROM entity_resolutions er
    JOIN (
        SELECT entity_id, MAX(created_at) AS latest
        FROM entity_resolutions
        WHERE superseded_by IS NULL AND entity_id IS NOT NULL
        GROUP BY entity_id
    ) latest ON latest.entity_id = er.entity_id AND latest.latest = er.created_at
    WHERE er.status IN ({ph})
      AND er.superseded_by IS NULL
"""


def test_queue_shows_only_latest_per_entity(conn):
    """Multiple un-superseded rows for same entity: query returns only the latest."""
    conn.execute(
        "INSERT INTO shared_entities (entity_id, name) VALUES ('rome', 'Rome')"
    )
    # Two rows, superseded_by not set — simulates pre-supersede-logic stale data.
    insert_resolution(conn, entity_id="rome", status="ambiguous",
                      confidence=0.5, created_at=1000)
    insert_resolution(conn, entity_id="rome", status="ambiguous",
                      confidence=0.8, created_at=2000)
    conn.commit()

    rows = conn.execute(
        QUEUE_QUERY_TEMPLATE.format(ph="?"),
        ("ambiguous",),
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["confidence"] == 0.8  # the newer one


def test_queue_excludes_superseded(conn):
    conn.execute(
        "INSERT INTO shared_entities (entity_id, name) VALUES ('rome', 'Rome')"
    )
    rid_old = insert_resolution(
        conn, entity_id="rome", status="ambiguous",
        confidence=0.5, created_at=1000,
    )
    rid_new = insert_resolution(
        conn, entity_id="rome", status="resolved", chosen_qid="Q220",
        confidence=0.9, created_at=2000,
    )
    # Mark old as superseded.
    conn.execute(
        "UPDATE entity_resolutions SET superseded_by = ? WHERE id = ?",
        (rid_new, rid_old),
    )
    conn.commit()

    # Query for ambiguous: should return nothing (old is superseded).
    rows = conn.execute(
        QUEUE_QUERY_TEMPLATE.format(ph="?"),
        ("ambiguous",),
    ).fetchall()
    assert len(rows) == 0


def test_queue_filter_status(conn):
    conn.execute(
        "INSERT INTO shared_entities (entity_id, name) VALUES ('rome', 'Rome'), ('xyz', 'XYZ')"
    )
    insert_resolution(conn, entity_id="rome", status="resolved", chosen_qid="Q220")
    insert_resolution(conn, entity_id="xyz", status="no_match")
    conn.commit()

    # Status filter for needs_review only → zero rows.
    rows = conn.execute(
        QUEUE_QUERY_TEMPLATE.format(ph="?"),
        ("needs_review",),
    ).fetchall()
    assert len(rows) == 0

    # Status filter for no_match.
    rows = conn.execute(
        QUEUE_QUERY_TEMPLATE.format(ph="?"),
        ("no_match",),
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["entity_id"] == "xyz"


# ---------- entity detail view (/admin/entity/<qid>) ----------

def test_entity_detail_returns_committed_and_history(conn):
    """The detail endpoint shows all resolutions for a QID plus the owner."""
    conn.execute(
        "INSERT INTO shared_entities (entity_id, name, wikidata_qid) "
        "VALUES ('rome', 'Rome', 'Q220')"
    )
    insert_resolution(conn, entity_id="rome", status="ambiguous",
                      chosen_qid="Q220", confidence=0.7, created_at=1000)
    insert_resolution(conn, entity_id="rome", status="resolved",
                      chosen_qid="Q220", confidence=0.95, created_at=2000)
    conn.commit()

    # Mimic the detail-endpoint queries.
    committed = conn.execute(
        "SELECT entity_id, name FROM shared_entities WHERE wikidata_qid = ?",
        ("Q220",),
    ).fetchone()
    assert committed["entity_id"] == "rome"

    # History: both rows (no superseded_by filter on detail view — we want full log).
    resolutions = conn.execute(
        "SELECT id, status, confidence FROM entity_resolutions "
        "WHERE chosen_qid = ? ORDER BY created_at DESC",
        ("Q220",),
    ).fetchall()
    assert len(resolutions) == 2
    assert resolutions[0]["confidence"] == 0.95  # most recent first


# ---------- POST /admin/entity/resolve: 409 on QID conflict ----------

def test_resolve_endpoint_conflict_check(conn):
    """Manual resolve should detect when a QID is already owned by another entity."""
    conn.execute(
        "INSERT INTO shared_entities (entity_id, name, wikidata_qid) "
        "VALUES ('augustus', 'Augustus', 'Q1405')"
    )
    conn.execute(
        "INSERT INTO shared_entities (entity_id, name) VALUES ('octavian', 'Octavian')"
    )
    conn.commit()

    # Check: is there another entity owning Q1405?
    conflict = conn.execute(
        "SELECT entity_id FROM shared_entities "
        "WHERE wikidata_qid = ? AND entity_id != ?",
        ("Q1405", "octavian"),
    ).fetchone()
    assert conflict is not None
    assert conflict["entity_id"] == "augustus"


def test_resolve_endpoint_no_conflict_when_same_entity(conn):
    """If the same entity already has the QID, there's no conflict."""
    conn.execute(
        "INSERT INTO shared_entities (entity_id, name, wikidata_qid) "
        "VALUES ('augustus', 'Augustus', 'Q1405')"
    )
    conn.commit()

    conflict = conn.execute(
        "SELECT entity_id FROM shared_entities "
        "WHERE wikidata_qid = ? AND entity_id != ?",
        ("Q1405", "augustus"),
    ).fetchone()
    assert conflict is None


def test_manual_resolve_supersedes_prior(conn):
    """Simulates POST /admin/entity/resolve: writes new row, supersedes prior."""
    conn.execute(
        "INSERT INTO shared_entities (entity_id, name) VALUES ('rome', 'Rome')"
    )
    rid_prior = insert_resolution(
        conn, entity_id="rome", status="ambiguous", confidence=0.5,
        created_at=1000,
    )
    conn.commit()

    # Manual commit.
    new_rid = f"er_manual_{uuid.uuid4().hex[:8]}"
    conn.execute(
        """
        INSERT INTO entity_resolutions (
            id, entity_id, capture_id, mention_text, candidate_qids,
            chosen_qid, confidence, status, resolver_model, reasoning,
            created_at
        ) VALUES (?, 'rome', 'admin:manual', 'Rome', '[]', 'Q220', 1.0,
                  'resolved', 'manual', 'test', ?)
        """,
        (new_rid, int(time.time())),
    )
    conn.execute(
        "UPDATE entity_resolutions SET superseded_by = ? "
        "WHERE entity_id = ? AND id != ? AND superseded_by IS NULL",
        (new_rid, "rome", new_rid),
    )
    conn.execute(
        "UPDATE shared_entities SET wikidata_qid = ? WHERE entity_id = ?",
        ("Q220", "rome"),
    )
    conn.commit()

    # Prior row is superseded.
    prior = conn.execute(
        "SELECT superseded_by FROM entity_resolutions WHERE id = ?",
        (rid_prior,),
    ).fetchone()
    assert prior["superseded_by"] == new_rid

    # shared_entities updated.
    qid = conn.execute(
        "SELECT wikidata_qid FROM shared_entities WHERE entity_id = 'rome'"
    ).fetchone()["wikidata_qid"]
    assert qid == "Q220"


def test_unique_qid_constraint_holds(conn):
    """Enforces that two entities can't both own the same QID."""
    conn.execute(
        "INSERT INTO shared_entities (entity_id, name, wikidata_qid) "
        "VALUES ('rome1', 'Rome1', 'Q220')"
    )
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO shared_entities (entity_id, name, wikidata_qid) "
            "VALUES ('rome2', 'Rome2', 'Q220')"
        )
        conn.commit()


def test_unique_qid_allows_multiple_nulls(conn):
    """Partial unique index: multiple NULL qids are allowed."""
    conn.execute(
        "INSERT INTO shared_entities (entity_id, name) VALUES ('a', 'A'), ('b', 'B'), ('c', 'C')"
    )
    conn.commit()
    n = conn.execute(
        "SELECT COUNT(*) FROM shared_entities WHERE wikidata_qid IS NULL"
    ).fetchone()[0]
    assert n == 3

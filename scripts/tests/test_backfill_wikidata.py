"""Tests for scripts/backfill_wikidata.py helpers.

Tests the pure-Python helpers and the DB write paths via an in-memory
SQLite DB. Does NOT hit the Wikidata API or call an LLM — all external
calls are mocked out.

Run: cd scripts && python3 -m pytest tests/test_backfill_wikidata.py -v
"""

import json
import sqlite3
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPT_DIR))


# ---------- Fixtures ----------

SCHEMA = """
CREATE TABLE IF NOT EXISTS shared_entities (
    entity_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    dates TEXT,
    location TEXT,
    nexus_score INTEGER DEFAULT 1,
    description TEXT,
    entity_type TEXT,
    modern_name TEXT,
    wikipedia_url TEXT,
    latitude REAL,
    longitude REAL,
    aliases TEXT DEFAULT '[]',
    date_start INTEGER,
    date_end INTEGER,
    wikidata_qid TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_shared_entities_qid
    ON shared_entities(wikidata_qid) WHERE wikidata_qid IS NOT NULL;

CREATE TABLE IF NOT EXISTS entity_curriculum_links (
    entity_id TEXT NOT NULL,
    domain_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    lens_title TEXT,
    lens_emphasis TEXT,
    PRIMARY KEY (entity_id, domain_id, node_id)
);

CREATE TABLE IF NOT EXISTS curriculum_nodes (
    id TEXT,
    domain_id TEXT,
    title TEXT,
    description TEXT,
    PRIMARY KEY (id, domain_id)
);

CREATE TABLE IF NOT EXISTS entity_resolutions (
    id TEXT PRIMARY KEY,
    entity_id TEXT,
    capture_id TEXT,
    mention_text TEXT NOT NULL,
    context_excerpt TEXT,
    type_hint TEXT,
    date_hint_start INTEGER,
    date_hint_end INTEGER,
    candidate_qids TEXT,
    chosen_qid TEXT,
    confidence REAL NOT NULL,
    status TEXT NOT NULL,
    resolver_model TEXT,
    reasoning TEXT,
    cost_usd REAL DEFAULT 0,
    created_at INTEGER NOT NULL,
    superseded_by TEXT
);
CREATE INDEX IF NOT EXISTS idx_entity_resolutions_entity ON entity_resolutions(entity_id);

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


# ---------- Fake ScoredCandidate / Resolution for _write_resolution tests ----------

@dataclass
class FakeDateRange:
    start: int
    end: int


@dataclass
class FakeScoredCandidate:
    qid: str
    label: str = ""
    description: str = ""
    total: float = 0.0
    rank: int = 0
    scores: dict = field(default_factory=dict)
    dates: object | None = None
    aliases: list = field(default_factory=list)
    external_ids: dict = field(default_factory=dict)


@dataclass
class FakeResolution:
    mention: str
    context_text: str = ""
    type_hint: str | None = None
    date_hint: object | None = None
    status: str = "ambiguous"
    chosen_qid: str | None = None
    confidence: float = 0.5
    candidates: list = field(default_factory=list)
    reasoning: str = ""


# ---------- _date_range_from_entity ----------

def test_date_range_both_bounds_present():
    from backfill_wikidata import _date_range_from_entity
    row = {"date_start": 1200, "date_end": 1500}
    # sqlite3.Row has .keys() + indexing — mimic with a dict-like that supports it.
    class RowDict(dict):
        def keys(self):
            return super().keys()
    r = RowDict(row)
    dr = _date_range_from_entity(r)
    assert dr is not None
    assert dr.start == 1200
    assert dr.end == 1500


def test_date_range_only_start():
    """Mirror the missing bound — DateRange requires both."""
    from backfill_wikidata import _date_range_from_entity
    class RowDict(dict):
        def keys(self):
            return super().keys()
    dr = _date_range_from_entity(RowDict({"date_start": 1807, "date_end": None}))
    assert dr is not None
    assert dr.start == 1807
    assert dr.end == 1807


def test_date_range_only_end():
    from backfill_wikidata import _date_range_from_entity
    class RowDict(dict):
        def keys(self):
            return super().keys()
    dr = _date_range_from_entity(RowDict({"date_start": None, "date_end": 1500}))
    assert dr is not None
    assert dr.start == 1500
    assert dr.end == 1500


def test_date_range_both_none():
    from backfill_wikidata import _date_range_from_entity
    class RowDict(dict):
        def keys(self):
            return super().keys()
    assert _date_range_from_entity(RowDict({"date_start": None, "date_end": None})) is None


def test_date_range_normalizes_order():
    """If somehow start > end, DateRange still gets sorted bounds."""
    from backfill_wikidata import _date_range_from_entity
    class RowDict(dict):
        def keys(self):
            return super().keys()
    dr = _date_range_from_entity(RowDict({"date_start": 1500, "date_end": 1200}))
    assert dr.start == 1200
    assert dr.end == 1500


# ---------- _is_disambiguation_only ----------

def test_disambiguation_only_true_for_disambig_only():
    from backfill_wikidata import _is_disambiguation_only
    payload = json.dumps([
        {"qid": "Q232572", "description": "Wikimedia disambiguation page"},
    ])
    assert _is_disambiguation_only(payload) is True


def test_disambiguation_only_false_for_real_candidates():
    from backfill_wikidata import _is_disambiguation_only
    payload = json.dumps([
        {"qid": "Q133331", "description": "Council of Christian bishops in Nicaea, 325"},
        {"qid": "Q232572", "description": "Wikimedia disambiguation page"},
    ])
    assert _is_disambiguation_only(payload) is False


def test_disambiguation_only_false_for_empty():
    from backfill_wikidata import _is_disambiguation_only
    assert _is_disambiguation_only("[]") is False
    assert _is_disambiguation_only(None) is False


def test_disambiguation_only_handles_bad_json():
    from backfill_wikidata import _is_disambiguation_only
    assert _is_disambiguation_only("not json") is False


def test_disambiguation_only_case_insensitive():
    from backfill_wikidata import _is_disambiguation_only
    payload = json.dumps([
        {"qid": "Q1", "description": "Wikimedia DISAMBIGUATION PAGE"},
    ])
    assert _is_disambiguation_only(payload) is True


# ---------- _write_resolution + supersede ----------

def test_write_resolution_supersedes_prior(conn):
    """Writing a new resolution for an entity supersedes prior un-superseded rows."""
    from backfill_wikidata import _write_resolution

    # Seed the entity.
    conn.execute(
        "INSERT INTO shared_entities (entity_id, name) VALUES ('rome', 'Rome')"
    )
    conn.commit()

    res1 = FakeResolution(mention="Rome", status="ambiguous", confidence=0.5)
    rid1 = _write_resolution(conn, res1, "rome",
                             capture_id="test:1", resolver_model="deterministic-0.1")
    conn.commit()

    res2 = FakeResolution(mention="Rome", status="resolved",
                          chosen_qid="Q220", confidence=0.9)
    rid2 = _write_resolution(conn, res2, "rome",
                             capture_id="test:2", resolver_model="deterministic-0.1")
    conn.commit()

    rows = conn.execute(
        "SELECT id, status, superseded_by FROM entity_resolutions WHERE entity_id='rome' ORDER BY created_at"
    ).fetchall()
    assert len(rows) == 2
    assert rows[0]["id"] == rid1
    assert rows[0]["superseded_by"] == rid2
    assert rows[1]["id"] == rid2
    assert rows[1]["superseded_by"] is None


def test_write_resolution_no_entity_id_does_not_supersede(conn):
    """Ad-hoc resolutions (entity_id=NULL) don't touch other rows."""
    from backfill_wikidata import _write_resolution
    res = FakeResolution(mention="Unknown", status="no_match", confidence=0.0)
    rid = _write_resolution(conn, res, None,
                            capture_id="adhoc", resolver_model="deterministic-0.1")
    conn.commit()
    # No entity rows should have been UPDATEd (there aren't any).
    # The row itself should exist.
    row = conn.execute(
        "SELECT id, entity_id FROM entity_resolutions WHERE id = ?", (rid,)
    ).fetchone()
    assert row["entity_id"] is None


def test_write_resolution_serializes_candidates(conn):
    from backfill_wikidata import _write_resolution

    conn.execute("INSERT INTO shared_entities (entity_id, name) VALUES ('rome', 'Rome')")
    conn.commit()

    cand = FakeScoredCandidate(
        qid="Q220", label="Rome", description="Italian city", total=0.85,
        rank=0, scores={"type": 1.0, "date": 1.0},
        dates=FakeDateRange(start=-753, end=2025),
        aliases=["Roma"], external_ids={"P214": "123456789"},
    )
    res = FakeResolution(
        mention="Rome", status="resolved", chosen_qid="Q220",
        confidence=0.85, candidates=[cand], reasoning="test",
    )
    _write_resolution(conn, res, "rome",
                      capture_id="test", resolver_model="deterministic-0.1")
    conn.commit()

    row = conn.execute(
        "SELECT candidate_qids FROM entity_resolutions WHERE entity_id='rome'"
    ).fetchone()
    payload = json.loads(row["candidate_qids"])
    assert len(payload) == 1
    c = payload[0]
    assert c["qid"] == "Q220"
    assert c["label"] == "Rome"
    assert c["total"] == 0.85
    assert c["dates"] == {"start": -753, "end": 2025}
    assert c["external_ids"] == {"P214": "123456789"}
    assert c["aliases"] == ["Roma"]


# ---------- _commit_external_ids ----------

def test_commit_external_ids_filters_to_allowlist(conn):
    from backfill_wikidata import _commit_external_ids, EXTERNAL_ID_PROPS

    conn.execute("INSERT INTO shared_entities (entity_id, name) VALUES ('e', 'E')")
    conn.commit()

    # Include one allowed + one unknown property.
    _commit_external_ids(conn, "e", {
        "P214": "12345",            # VIAF — allowed
        "P99999999": "noise",       # not in allowlist — should be dropped
        "P227": ["10", "20"],        # GND — allowed, list form
    })
    conn.commit()

    rows = conn.execute(
        "SELECT property_id, value FROM entity_external_ids WHERE entity_id='e' ORDER BY property_id, value"
    ).fetchall()
    got = [(r["property_id"], r["value"]) for r in rows]
    assert got == [("P214", "12345"), ("P227", "10"), ("P227", "20")]
    # Verify the allowlist doesn't include P99999999.
    assert "P99999999" not in EXTERNAL_ID_PROPS


def test_commit_external_ids_idempotent(conn):
    from backfill_wikidata import _commit_external_ids
    conn.execute("INSERT INTO shared_entities (entity_id, name) VALUES ('e', 'E')")
    conn.commit()
    for _ in range(3):
        _commit_external_ids(conn, "e", {"P214": "abc"})
        conn.commit()
    n = conn.execute(
        "SELECT COUNT(*) FROM entity_external_ids WHERE entity_id='e'"
    ).fetchone()[0]
    assert n == 1


def test_commit_external_ids_none_or_empty(conn):
    from backfill_wikidata import _commit_external_ids
    conn.execute("INSERT INTO shared_entities (entity_id, name) VALUES ('e', 'E')")
    conn.commit()
    _commit_external_ids(conn, "e", None)
    _commit_external_ids(conn, "e", {})
    conn.commit()
    n = conn.execute(
        "SELECT COUNT(*) FROM entity_external_ids WHERE entity_id='e'"
    ).fetchone()[0]
    assert n == 0


# ---------- dedup_report ----------

def test_dedup_report_identifies_duplicates(conn):
    from backfill_wikidata import dedup_report

    # Canonical owner + a duplicate that got queued as needs_review.
    conn.execute(
        "INSERT INTO shared_entities (entity_id, name, wikidata_qid) "
        "VALUES ('augustus', 'Augustus', 'Q1405')"
    )
    conn.execute(
        "INSERT INTO shared_entities (entity_id, name) VALUES ('octavian', 'Octavian')"
    )
    # Audit row: deterministic resolver picked Q1405 for octavian, then
    # rewrote to needs_review due to dedup.
    conn.execute(
        """
        INSERT INTO entity_resolutions (
            id, entity_id, mention_text, chosen_qid, confidence, status,
            resolver_model, created_at
        ) VALUES ('er_x', 'octavian', 'Octavian', 'Q1405', 0.9, 'needs_review',
                  'deterministic-0.1', ?)
        """,
        (int(time.time()),),
    )
    conn.commit()

    dupes = dedup_report(conn)
    assert len(dupes) == 1
    qid, eids = dupes[0]
    assert qid == "Q1405"
    # Canonical + duplicate both present.
    assert set(eids) == {"augustus", "octavian"}


def test_dedup_report_empty_when_no_duplicates(conn):
    from backfill_wikidata import dedup_report

    conn.execute(
        "INSERT INTO shared_entities (entity_id, name, wikidata_qid) "
        "VALUES ('rome', 'Rome', 'Q220')"
    )
    conn.execute(
        """
        INSERT INTO entity_resolutions (
            id, entity_id, mention_text, chosen_qid, confidence, status,
            resolver_model, created_at
        ) VALUES ('er1', 'rome', 'Rome', 'Q220', 0.9, 'resolved',
                  'deterministic-0.1', ?)
        """,
        (int(time.time()),),
    )
    conn.commit()
    assert dedup_report(conn) == []


# ---------- _format_candidate_for_llm ----------

def test_format_candidate_for_llm_includes_dates():
    from backfill_wikidata import _format_candidate_for_llm
    c = {
        "qid": "Q220", "label": "Rome",
        "description": "ancient Italian city",
        "dates": {"start": -753, "end": 2025},
        "aliases": ["Roma"], "total": 0.85,
    }
    out = _format_candidate_for_llm(c, 0)
    assert "Q220" in out
    assert "Rome" in out
    assert "aka Roma" in out
    assert "dates: -753..2025" in out
    assert "score 0.85" in out


def test_format_candidate_for_llm_handles_missing_fields():
    from backfill_wikidata import _format_candidate_for_llm
    c = {"qid": "Q1", "label": "Thing"}
    out = _format_candidate_for_llm(c, 0)
    assert "Q1" in out
    assert "Thing" in out
    # No dates, no aliases → no crash.
    assert "dates:" not in out
    assert "aka" not in out


def test_format_candidate_for_llm_truncates_long_descriptions():
    from backfill_wikidata import _format_candidate_for_llm
    c = {"qid": "Q1", "label": "X", "description": "A" * 500}
    out = _format_candidate_for_llm(c, 0)
    # Description is clipped to 250 chars.
    assert "A" * 251 not in out
    assert "A" * 250 in out

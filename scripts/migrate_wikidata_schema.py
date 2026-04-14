#!/usr/bin/env python3
"""One-off migration: add Wikidata resolution tables + column.

Idempotent. Safe to run multiple times against the same DB. Designed to be
scp'd to alif and run against /opt/petrarca/data/petrarca.db, and also run
locally against any snapshot of that DB.

Adds:
- shared_entities.wikidata_qid TEXT
- unique partial index idx_shared_entities_qid
- entity_resolutions table + indexes
- entity_external_ids table + index

See research/wikidata-entity-resolution-plan.md for the design.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path


def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == column for r in rows)


def migrate(db_path: Path) -> None:
    if not db_path.exists():
        print(f"error: {db_path} does not exist", file=sys.stderr)
        sys.exit(2)

    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute("PRAGMA foreign_keys=ON")

    # 1. shared_entities.wikidata_qid
    if column_exists(conn, "shared_entities", "wikidata_qid"):
        print("ok: shared_entities.wikidata_qid already present")
    else:
        conn.execute("ALTER TABLE shared_entities ADD COLUMN wikidata_qid TEXT")
        print("added: shared_entities.wikidata_qid")

    # 2. unique index (allows multiple NULLs, at most one row per non-NULL QID)
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_shared_entities_qid "
        "ON shared_entities(wikidata_qid) WHERE wikidata_qid IS NOT NULL"
    )
    print("ok: idx_shared_entities_qid")

    # 3. entity_resolutions
    conn.execute(
        """
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
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_entity_resolutions_entity ON entity_resolutions(entity_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_entity_resolutions_capture ON entity_resolutions(capture_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_entity_resolutions_status ON entity_resolutions(status)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_entity_resolutions_chosen ON entity_resolutions(chosen_qid)"
    )
    print("ok: entity_resolutions + indexes")

    # 4. entity_external_ids
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS entity_external_ids (
            entity_id TEXT NOT NULL REFERENCES shared_entities(entity_id),
            property_id TEXT NOT NULL,
            value TEXT NOT NULL,
            source TEXT DEFAULT 'wikidata',
            PRIMARY KEY (entity_id, property_id, value)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_entity_ext_ids_prop ON entity_external_ids(property_id, value)"
    )
    print("ok: entity_external_ids + index")

    conn.commit()
    conn.close()
    print(f"done: {db_path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "db_path",
        type=Path,
        nargs="?",
        default=Path("/opt/petrarca/data/petrarca.db"),
        help="Path to petrarca.db (default: /opt/petrarca/data/petrarca.db)",
    )
    args = p.parse_args()
    migrate(args.db_path)

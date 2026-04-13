#!/usr/bin/env python3
"""Clean up stale un-superseded rows in entity_resolutions.

Background: the first run of `scripts/backfill_wikidata.py` predates the
supersede-on-write logic in `_write_resolution`. Those early rows have
`superseded_by IS NULL` even when newer rows exist for the same entity.

Symptoms (cosmetic, not functional):
  - `entity_resolutions` queries over-count history (stale rows appear
    alongside current ones)
  - Admin UI is belt-and-suspenders via MAX(created_at), but raw SQL
    queries may double-count

This script:
  1. Finds entities with >1 rows where `superseded_by IS NULL`.
  2. For each, marks all but the latest as superseded by the latest.
  3. Commits atomically per entity.

Idempotent. Safe to re-run.

Usage:
    python3 scripts/cleanup_stale_resolutions.py [DB_PATH] [--dry-run]
"""
from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("cleanup_stale_resolutions")


def find_stale(conn: sqlite3.Connection) -> list[dict]:
    """Entities with >1 un-superseded rows."""
    rows = conn.execute(
        """
        SELECT entity_id, COUNT(*) AS n,
               MAX(created_at) AS latest_ts
        FROM entity_resolutions
        WHERE superseded_by IS NULL AND entity_id IS NOT NULL
        GROUP BY entity_id
        HAVING COUNT(*) > 1
        ORDER BY entity_id
        """
    ).fetchall()
    return [dict(r) for r in rows]


def supersede_stale_for_entity(conn: sqlite3.Connection, entity_id: str,
                                latest_ts: int, *, dry_run: bool) -> int:
    """Mark all rows for entity_id with created_at != latest_ts as superseded.

    The latest row supersedes all prior un-superseded rows for the entity.
    """
    latest = conn.execute(
        """
        SELECT id FROM entity_resolutions
        WHERE entity_id = ? AND superseded_by IS NULL
              AND created_at = ?
        LIMIT 1
        """,
        (entity_id, latest_ts),
    ).fetchone()
    if not latest:
        return 0
    latest_id = latest["id"]

    to_supersede = conn.execute(
        """
        SELECT id FROM entity_resolutions
        WHERE entity_id = ? AND superseded_by IS NULL AND id != ?
        """,
        (entity_id, latest_id),
    ).fetchall()
    n = len(to_supersede)
    if dry_run or n == 0:
        return n
    conn.execute(
        """
        UPDATE entity_resolutions SET superseded_by = ?
        WHERE entity_id = ? AND superseded_by IS NULL AND id != ?
        """,
        (latest_id, entity_id, latest_id),
    )
    conn.commit()
    return n


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("db_path", type=Path, nargs="?",
                   default=Path("/opt/petrarca/data/petrarca.db"))
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if not args.db_path.exists():
        log.error("DB not found: %s", args.db_path)
        sys.exit(2)

    conn = sqlite3.connect(str(args.db_path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")

    stale = find_stale(conn)
    log.info("found %d entities with stale audit rows", len(stale))
    if not stale:
        return

    total_superseded = 0
    for s in stale:
        n = supersede_stale_for_entity(
            conn, s["entity_id"], s["latest_ts"], dry_run=args.dry_run
        )
        total_superseded += n
        log.info("  %-30s %d rows → superseded", s["entity_id"], n)

    log.info("done: %d rows %s",
             total_superseded,
             "would be superseded" if args.dry_run else "superseded")

    conn.close()


if __name__ == "__main__":
    main()

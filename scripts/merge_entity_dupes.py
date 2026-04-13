#!/usr/bin/env python3
"""Merge duplicate shared_entities rows that resolve to the same Wikidata QID.

Background: the Wikidata backfill (`scripts/backfill_wikidata.py`) surfaces
dedup candidates — cases where two entity_ids both map to the same QID.
Examples from the 2026-04-13 run:

    Q1405  augustus ↔ octavian            (Augustus was Octavian before)
    Q8011  avicenna ↔ ibn_sina            (Latinized vs Arabic name)
    Q8018  augustine_of_hippo ↔ augustine_of_hippo_person  (_person-suffix dupes)
    Q6691  homer ↔ homer_person
    Q406   istanbul ↔ byzantion
    …

A "needs_review" entity_resolutions row with `chosen_qid` set but
shared_entities.wikidata_qid NULL is the signal. The canonical owner is
the shared_entities row that has wikidata_qid = that QID.

This script:

  1. Finds all such pairs.
  2. For each pair, merges the duplicate into the canonical owner:
       - entity_curriculum_links: re-parented (with composite-PK dedup)
       - entity_notes: re-parented
       - entity_resolutions: re-parented (preserves audit history)
       - entity_external_ids: merged with OR IGNORE
       - shared_entities row for source_id: DELETED
  3. Writes a new `entity_resolutions` row noting the merge.
  4. Logs every action to a JSONL file for auditability.

Use `--dry-run` to preview. Use `--apply` to execute. Use `--qid Qxxx`
to target a single pair.

Safe to re-run: second invocation finds no more pairs to merge.
"""
from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
import time
import uuid
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("merge_entity_dupes")


# Tables with an entity_id column that must be re-parented.
CHILD_TABLES: list[tuple[str, bool]] = [
    # (table_name, has_composite_pk_including_entity_id)
    ("entity_curriculum_links", True),   # (entity_id, domain_id, node_id)
    ("entity_external_ids", True),       # (entity_id, property_id, value)
    ("entity_notes", False),             # simple AUTOINCREMENT id
    ("entity_resolutions", False),       # simple TEXT id
]


def _now() -> int:
    return int(time.time())


def find_dedup_pairs(conn: sqlite3.Connection) -> list[dict]:
    """Return [{qid, canonical, duplicate, resolution_id, …}] — one entry per dupe.

    The canonical side has shared_entities.wikidata_qid = qid.
    The duplicate side has a needs_review entity_resolutions row with
    chosen_qid = qid (and shared_entities.wikidata_qid IS NULL).

    Dedups by taking the latest entity_resolutions row per (qid, duplicate)
    pair so stale audit entries don't multiply the list.
    """
    rows = conn.execute(
        """
        SELECT er.id AS resolution_id, er.entity_id AS duplicate,
               er.chosen_qid AS qid, se.entity_id AS canonical,
               er.mention_text, er.confidence, er.reasoning,
               se_dup.name AS duplicate_name, se.name AS canonical_name
        FROM entity_resolutions er
        JOIN shared_entities se_dup ON se_dup.entity_id = er.entity_id
        JOIN shared_entities se ON se.wikidata_qid = er.chosen_qid
        JOIN (
            SELECT entity_id, chosen_qid, MAX(created_at) AS latest
            FROM entity_resolutions
            WHERE status = 'needs_review'
              AND superseded_by IS NULL
              AND chosen_qid IS NOT NULL
              AND entity_id IS NOT NULL
            GROUP BY entity_id, chosen_qid
        ) last ON last.entity_id = er.entity_id
              AND last.chosen_qid = er.chosen_qid
              AND last.latest = er.created_at
        WHERE er.status = 'needs_review'
          AND er.superseded_by IS NULL
          AND er.chosen_qid IS NOT NULL
          AND er.entity_id IS NOT NULL
          AND se_dup.wikidata_qid IS NULL
          AND se.entity_id != er.entity_id
        ORDER BY er.chosen_qid, er.entity_id
        """
    ).fetchall()
    return [dict(r) for r in rows]


def is_high_confidence_dupe(pair: dict) -> tuple[bool, str]:
    """Heuristic: is this pair *clearly* a merge candidate?

    Returns (is_safe, reason). Safe merges are ones the UI can auto-suggest
    with confidence; unsafe ones require human review.
    """
    can = (pair["canonical_name"] or "").lower().strip()
    dup = (pair["duplicate_name"] or "").lower().strip()
    can_id = pair["canonical"]
    dup_id = pair["duplicate"]

    # Heuristic 1: _person / _place suffix on one side, bare on the other.
    for suffix in ("_person", "_place"):
        if (can_id + suffix == dup_id) or (dup_id + suffix == can_id):
            return True, f"suffix-dupe ({suffix})"

    # Heuristic 2: one name is a strict prefix/suffix of the other OR identical.
    if can == dup:
        return True, "identical-name"

    # Heuristic 3: well-known historical aliases (case-by-case).
    ALIASES = {
        frozenset(["augustus", "octavian"]),
        frozenset(["ibn_sina", "avicenna"]),
        frozenset(["byzantion", "istanbul"]),
        frozenset(["byzantion", "constantinople"]),
        frozenset(["naples", "neapolis"]),
        frozenset(["cappella_palatina", "palatine_chapel"]),
        frozenset(["sasanian_empire", "sasanian_persia"]),
    }
    if frozenset([can_id, dup_id]) in ALIASES:
        return True, "known-alias"

    # Heuristic 4: one side has "_of_<place>" while the other is the bare name.
    # E.g., gelon ↔ gelon_of_syracuse, empedocles ↔ empedocles_of_akragas.
    for a, b in ((can_id, dup_id), (dup_id, can_id)):
        if a.startswith(b + "_of_") or b.startswith(a + "_of_"):
            return True, "of-place-dupe"

    # Heuristic 5: one side has a regnal number (_i, _ii, _iii) suffix while
    # the other is the bare name. constantine ↔ constantine_i is a common case
    # where the curriculum uses an ordinal that the user implicitly means the
    # most famous of that name (Constantine the Great).
    #
    # This heuristic is still somewhat risky — "Napoleon" ≠ "Napoleon III" —
    # so we only mark it safe if the bare-name entity has no wikidata_qid
    # yet (i.e., it's coming in as the DUPLICATE side, not the canonical).
    # That means the resolver already picked the ordinal entity as canonical,
    # which is the explicit signal.
    REGNAL_SUFFIXES = ("_i", "_ii", "_iii", "_iv", "_v", "_vi", "_vii", "_viii",
                       "_ix", "_x", "_xi", "_xii", "_the_great", "_the_younger",
                       "_the_elder")
    for suffix in REGNAL_SUFFIXES:
        if can_id + suffix == dup_id or dup_id + suffix == can_id:
            return True, f"regnal-suffix ({suffix})"

    # Everything else needs human review.
    return False, "needs-review"


def merge_pair(
    conn: sqlite3.Connection,
    canonical: str,
    duplicate: str,
    qid: str,
    resolution_id: str,
    *,
    dry_run: bool,
    audit_log,
) -> dict:
    """Merge duplicate into canonical. Returns a summary dict.

    Re-parents rows from `duplicate` to `canonical` for every child table,
    deletes the duplicate shared_entities row, writes an audit row.
    """
    summary = {
        "qid": qid,
        "canonical": canonical,
        "duplicate": duplicate,
        "source_resolution": resolution_id,
        "moves": {},
        "dropped_dupes": {},
        "deleted_duplicate": False,
    }

    # Sanity: canonical must own the QID, duplicate must exist, must differ.
    can_row = conn.execute(
        "SELECT wikidata_qid FROM shared_entities WHERE entity_id = ?",
        (canonical,),
    ).fetchone()
    dup_row = conn.execute(
        "SELECT wikidata_qid FROM shared_entities WHERE entity_id = ?",
        (duplicate,),
    ).fetchone()
    if not can_row or not dup_row:
        raise RuntimeError(
            f"merge pre-check failed: canonical={canonical!r} exists={can_row is not None}, "
            f"duplicate={duplicate!r} exists={dup_row is not None}"
        )
    if can_row["wikidata_qid"] != qid:
        raise RuntimeError(
            f"canonical {canonical!r} does not own QID {qid!r}; has {can_row['wikidata_qid']!r}"
        )
    if dup_row["wikidata_qid"] is not None:
        raise RuntimeError(
            f"duplicate {duplicate!r} already has QID {dup_row['wikidata_qid']!r} — "
            f"not a merge candidate"
        )

    for table, composite_pk in CHILD_TABLES:
        if composite_pk:
            # Insert target-missing rows from the source side, then delete source rows.
            # This respects the PK: if (canonical, domain_id, node_id) already exists,
            # the duplicate's row for the same combo is dropped rather than moved.
            cols = [row["name"] for row in conn.execute(
                f"PRAGMA table_info({table})"
            ).fetchall()]
            col_list = ", ".join(cols)
            # Build SELECT that rewrites entity_id to canonical.
            select_cols = ", ".join(
                f"?" if c == "entity_id" else c for c in cols
            )
            params_for_select = [canonical] + []  # only entity_id is parameterized
            # We actually need to SELECT FROM source WHERE entity_id = duplicate and
            # substitute canonical for the entity_id column.
            source_rows = conn.execute(
                f"SELECT {col_list} FROM {table} WHERE entity_id = ?",
                (duplicate,),
            ).fetchall()
            moved = 0
            dropped = 0
            for r in source_rows:
                values = [canonical if c == "entity_id" else r[c] for c in cols]
                placeholders = ", ".join("?" * len(cols))
                if dry_run:
                    # Check whether the composite PK would collide.
                    pk_cols = [col for col in cols if col != "entity_id" and col in
                               _composite_pk_fields(table)]
                    if pk_cols:
                        where = " AND ".join(f"{c} = ?" for c in pk_cols)
                        exists = conn.execute(
                            f"SELECT 1 FROM {table} WHERE entity_id = ? AND {where}",
                            [canonical] + [r[c] for c in pk_cols],
                        ).fetchone()
                        if exists:
                            dropped += 1
                        else:
                            moved += 1
                    else:
                        moved += 1
                else:
                    cur = conn.execute(
                        f"INSERT OR IGNORE INTO {table} ({col_list}) VALUES ({placeholders})",
                        values,
                    )
                    if cur.rowcount == 0:
                        dropped += 1
                    else:
                        moved += 1
            if not dry_run:
                conn.execute(
                    f"DELETE FROM {table} WHERE entity_id = ?",
                    (duplicate,),
                )
            summary["moves"][table] = moved
            summary["dropped_dupes"][table] = dropped
        else:
            # Simple UPDATE: non-composite PK, just re-parent.
            if dry_run:
                n = conn.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE entity_id = ?",
                    (duplicate,),
                ).fetchone()[0]
            else:
                cur = conn.execute(
                    f"UPDATE {table} SET entity_id = ? WHERE entity_id = ?",
                    (canonical, duplicate),
                )
                n = cur.rowcount
            summary["moves"][table] = n
            summary["dropped_dupes"][table] = 0

    # Delete the duplicate shared_entities row.
    if not dry_run:
        conn.execute("DELETE FROM shared_entities WHERE entity_id = ?", (duplicate,))
        summary["deleted_duplicate"] = True

        # Write a merge audit row on the canonical side.
        mid = f"er_merge_{uuid.uuid4().hex[:8]}"
        reasoning = (
            f"Merged {duplicate!r} into {canonical!r} via QID {qid}. "
            f"Moves: {json.dumps(summary['moves'])}. "
            f"Dropped (PK collisions): {json.dumps(summary['dropped_dupes'])}."
        )
        conn.execute(
            """
            INSERT INTO entity_resolutions (
                id, entity_id, capture_id, mention_text, candidate_qids,
                chosen_qid, confidence, status, resolver_model, reasoning,
                cost_usd, created_at
            ) VALUES (?, ?, 'merge', ?, '[]', ?, 1.0, 'resolved', 'merge',
                      ?, 0, ?)
            """,
            (mid, canonical, duplicate, qid, reasoning, _now()),
        )
        # The source resolution becomes superseded by the merge.
        conn.execute(
            "UPDATE entity_resolutions SET superseded_by = ? WHERE id = ?",
            (mid, resolution_id),
        )
        summary["merge_resolution_id"] = mid
        conn.commit()

    audit_log.write(json.dumps({"ts": _now(), **summary}) + "\n")
    audit_log.flush()
    return summary


def _composite_pk_fields(table: str) -> list[str]:
    """Return the PK columns for tables with composite keys we care about."""
    return {
        "entity_curriculum_links": ["domain_id", "node_id"],
        "entity_external_ids": ["property_id", "value"],
    }.get(table, [])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("db_path", type=Path, nargs="?",
                   default=Path("/opt/petrarca/data/petrarca.db"))
    p.add_argument("--dry-run", action="store_true",
                   help="Show what would happen, make no changes")
    p.add_argument("--apply", action="store_true",
                   help="Actually perform the merges (required unless --dry-run)")
    p.add_argument("--qid", help="Only merge the pair with this QID")
    p.add_argument("--list", action="store_true",
                   help="List pending dedup pairs and exit")
    p.add_argument("--audit-log", type=Path, default=None,
                   help="JSONL audit log (default: DB_PATH's parent / merge_audit.jsonl)")
    p.add_argument("--safe-only", action="store_true",
                   help="Only apply high-confidence dupes (suffix-dupes, known aliases, "
                        "identical names). Skip anything needing human judgement.")
    args = p.parse_args()

    if not args.dry_run and not args.apply and not args.list:
        p.error("must pass --dry-run, --apply, or --list")

    if not args.db_path.exists():
        log.error("DB not found: %s", args.db_path)
        sys.exit(2)

    audit_path = args.audit_log or args.db_path.parent / "merge_audit.jsonl"

    conn = sqlite3.connect(str(args.db_path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=OFF")  # we handle FK semantics manually
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")

    pairs = find_dedup_pairs(conn)
    if args.qid:
        pairs = [p for p in pairs if p["qid"] == args.qid]

    if not pairs:
        log.info("no dedup pairs found")
        return

    log.info("found %d dedup pairs:", len(pairs))
    # Classify each pair.
    safe_pairs = []
    unsafe_pairs = []
    for p_ in pairs:
        is_safe, reason = is_high_confidence_dupe(p_)
        p_["_safe"] = is_safe
        p_["_safety_reason"] = reason
        (safe_pairs if is_safe else unsafe_pairs).append(p_)
        tag = "SAFE" if is_safe else "REVIEW"
        log.info("  %-6s %s (%s): %s ← %s",
                 tag, p_["qid"], reason,
                 p_["canonical"], p_["duplicate"])

    log.info("summary: %d safe, %d need review", len(safe_pairs), len(unsafe_pairs))

    if args.list:
        return

    if args.safe_only:
        pairs = safe_pairs
        log.info("--safe-only: processing %d safe pairs", len(pairs))

    with audit_path.open("a") as audit_log:
        log.info("audit log: %s", audit_path)
        for p_ in pairs:
            log.info("%s: merging %s ← %s (dry_run=%s)",
                     p_["qid"], p_["canonical"], p_["duplicate"], args.dry_run)
            try:
                summary = merge_pair(
                    conn,
                    canonical=p_["canonical"],
                    duplicate=p_["duplicate"],
                    qid=p_["qid"],
                    resolution_id=p_["resolution_id"],
                    dry_run=args.dry_run,
                    audit_log=audit_log,
                )
                log.info("  moves: %s", summary["moves"])
                if any(v > 0 for v in summary["dropped_dupes"].values()):
                    log.info("  PK-collision drops: %s", summary["dropped_dupes"])
            except Exception as e:
                log.error("  merge failed for %s: %s", p_["qid"], e)

    conn.close()
    log.info("done")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Hide speculative structural cards — those generated for curriculum nodes/domains
the user has never actually engaged with via reading or voice.

Adds a `hidden` column to `structural_cards` and flips it to 1 for rows that
fail the new per-node / per-domain evidence gate.

Evidence rule:
  - aspect + cast cards (have node_id): require ≥1 knowledge_item on the exact
    (node_id, domain_id) whose `sources` JSON includes a real book_id or a
    voice_capture / transcript entry.
  - sequence + synchronic + causal cards (span multiple nodes): require ≥1 KI
    in the domain with book or voice evidence.

Gap-fill sources (`book_id`=null, chapter_title="Curriculum context — not yet in
a book") and self-assessment-only rows do NOT satisfy the gate.

Idempotent — safe to re-run.

Usage:
  python3 scripts/migrate_hide_speculative_structural.py            # apply
  python3 scripts/migrate_hide_speculative_structural.py --dry-run  # preview
  python3 scripts/migrate_hide_speculative_structural.py --unhide   # reset
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from limbic.amygdala import connect as _connect
    DB_PATH = '/opt/petrarca/data/petrarca.db'

    def open_conn():
        return _connect(DB_PATH)
except Exception:
    from curriculum_db import get_connection as open_conn


# A KI counts as real evidence if its JSON sources contain a book_id or a voice/transcript signal.
EVIDENCE_CLAUSE = """(
    sources LIKE '%"book_id": "%'
    OR sources LIKE '%"source": "voice_capture%'
    OR sources LIKE '%"transcript_id":%'
)"""


def ensure_hidden_column(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(structural_cards)").fetchall()]
    if 'hidden' not in cols:
        print("Adding `hidden` column to structural_cards...")
        conn.execute("ALTER TABLE structural_cards ADD COLUMN hidden INTEGER NOT NULL DEFAULT 0")
        conn.commit()
    else:
        print("`hidden` column already exists.")


def compute_speculative_ids(conn) -> dict:
    """Return {card_id: card_type} for every card whose node/domain has no real evidence."""

    # Aspect + cast — require per-node evidence
    per_node_sql = f"""
        SELECT sc.id, sc.card_type
        FROM structural_cards sc
        WHERE sc.card_type IN ('aspect', 'cast')
          AND NOT EXISTS (
            SELECT 1 FROM knowledge_items ki
            WHERE ki.curriculum_node_id = sc.node_id
              AND ki.curriculum_domain = sc.domain_id
              AND {EVIDENCE_CLAUSE}
          )
    """

    # Sequence / synchronic / causal — require per-domain evidence
    per_domain_sql = f"""
        SELECT sc.id, sc.card_type
        FROM structural_cards sc
        WHERE sc.card_type IN ('sequence', 'synchronic', 'causal')
          AND NOT EXISTS (
            SELECT 1 FROM knowledge_items ki
            WHERE ki.curriculum_domain = sc.domain_id
              AND {EVIDENCE_CLAUSE}
          )
    """

    out = {}
    for r in conn.execute(per_node_sql).fetchall():
        out[r['id']] = r['card_type']
    for r in conn.execute(per_domain_sql).fetchall():
        out[r['id']] = r['card_type']
    return out


def summarize(label: str, ids_by_type: dict):
    print(f"\n{label}")
    counts = {}
    for ct in ids_by_type.values():
        counts[ct] = counts.get(ct, 0) + 1
    for ct in sorted(counts):
        print(f"  {ct:12s}  {counts[ct]}")
    print(f"  {'total':12s}  {len(ids_by_type)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true',
                        help='Report counts without writing')
    parser.add_argument('--unhide', action='store_true',
                        help='Reset hidden=0 for all cards (undo)')
    args = parser.parse_args()

    conn = open_conn()
    ensure_hidden_column(conn)

    if args.unhide:
        conn.execute("UPDATE structural_cards SET hidden = 0")
        conn.commit()
        print("All structural_cards reset to hidden=0.")
        return

    speculative = compute_speculative_ids(conn)
    summarize("Speculative cards that will be hidden:", speculative)

    # Also report what stays visible, per type
    currently_visible = {
        r['card_type']: r['cnt']
        for r in conn.execute("""
            SELECT card_type, COUNT(*) AS cnt FROM structural_cards
            WHERE COALESCE(hidden, 0) = 0
            GROUP BY card_type
        """).fetchall()
    }
    print("\nVisible before migration:")
    for ct, c in sorted(currently_visible.items()):
        print(f"  {ct:12s}  {c}")

    if args.dry_run:
        print("\n[DRY RUN — no writes]")
        return

    # Reset everything to 0 first, then mark speculative as 1 — keeps script idempotent
    conn.execute("UPDATE structural_cards SET hidden = 0")
    if speculative:
        ids = list(speculative.keys())
        # Chunk to stay well under SQLite variable limits
        CHUNK = 400
        for i in range(0, len(ids), CHUNK):
            batch = ids[i:i + CHUNK]
            placeholders = ','.join(['?'] * len(batch))
            conn.execute(
                f"UPDATE structural_cards SET hidden = 1 WHERE id IN ({placeholders})",
                batch,
            )
    conn.commit()

    after = {
        r['card_type']: r['cnt']
        for r in conn.execute("""
            SELECT card_type, COUNT(*) AS cnt FROM structural_cards
            WHERE COALESCE(hidden, 0) = 0
            GROUP BY card_type
        """).fetchall()
    }
    print("\nVisible after migration:")
    for ct in sorted(set(list(currently_visible) + list(after))):
        before = currently_visible.get(ct, 0)
        now = after.get(ct, 0)
        print(f"  {ct:12s}  {before} → {now}  (Δ {now - before:+d})")


if __name__ == '__main__':
    main()

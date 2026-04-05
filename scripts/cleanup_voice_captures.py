#!/usr/bin/env python3
"""Clean up voice capture data: dedup sources, remove bad mappings, trigger wonderings."""
import json
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import get_connection

# Nodes that should NOT have voice_capture sources — medieval Sicily facts
# mapped to ancient Roman/Greek nodes by over-eager LLM matching
BAD_MAPPINGS = {
    'rm_tacitus',           # monk's account ≠ Tacitus
    'rm_slavery_rome',      # medieval prisoners ≠ Roman slavery
    'rm_roads_infrastructure',  # Palermo growing ≠ Roman roads
    'rm_roman_religion',    # Islamic legal scholars ≠ Roman religion
    'rm_constantine',       # vague "Byzantine period" reference
    'rm_fall_west',         # vague "Byzantine period" reference
    'rm_augustan_culture',  # Frederick II's poets ≠ Augustan culture
    'rm_conquest_italy',    # Arab conquest of Sicily ≠ Roman conquest of Italy
    'rm_conquest_greece',   # Norman spies using Greeks ≠ Roman conquest of Greece
    'rm_christianity',      # medieval Islamic/Christian relations ≠ Roman Christianity
}


def dedup_sources():
    """Remove duplicate voice_capture source entries, keeping one per unique source_text."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, sources FROM knowledge_items WHERE sources LIKE '%voice_capture%'"
    ).fetchall()

    deduped = 0
    for row in rows:
        sources = json.loads(row['sources'])
        vc = [s for s in sources if s.get('source') == 'voice_capture']
        other = [s for s in sources if s.get('source') != 'voice_capture']

        if len(vc) <= 1:
            continue

        # Dedup by first 60 chars of source_text
        seen = {}
        unique_vc = []
        for s in vc:
            key = s.get('source_text', '')[:60]
            if key not in seen:
                seen[key] = True
                unique_vc.append(s)

        if len(unique_vc) < len(vc):
            removed = len(vc) - len(unique_vc)
            new_sources = other + unique_vc
            conn.execute('UPDATE knowledge_items SET sources = ? WHERE id = ?',
                         (json.dumps(new_sources), row['id']))
            print(f'  Deduped {row["id"]}: {len(vc)} → {len(unique_vc)} vc sources (-{removed})')
            deduped += removed

    conn.commit()
    conn.close()
    return deduped


def remove_bad_mappings():
    """Remove voice_capture sources and revert knowledge states for bad node mappings."""
    conn = get_connection()
    removed_items = []

    for node_id in BAD_MAPPINGS:
        rows = conn.execute(
            "SELECT id, sources, review_count FROM knowledge_items WHERE curriculum_node_id = ? AND sources LIKE '%voice_capture%'",
            (node_id,)
        ).fetchall()

        for row in rows:
            sources = json.loads(row['sources'])
            vc = [s for s in sources if s.get('source') == 'voice_capture']
            other = [s for s in sources if s.get('source') != 'voice_capture']

            if not vc:
                continue

            if other:
                # Has non-vc sources — just remove vc sources, keep item
                conn.execute('UPDATE knowledge_items SET sources = ?, cached_question = NULL WHERE id = ?',
                             (json.dumps(other), row['id']))
                print(f'  Stripped vc sources from {row["id"]} (kept {len(other)} other sources)')
            else:
                # Only vc sources — remove the item entirely
                conn.execute('DELETE FROM knowledge_items WHERE id = ?', (row['id'],))
                print(f'  Deleted {row["id"]} (only had vc sources)')

            removed_items.append(node_id)

    # Also revert knowledge states that were set only by voice_capture
    for node_id in BAD_MAPPINGS:
        state = conn.execute(
            "SELECT domain_id, node_id, source_summary FROM knowledge_states WHERE node_id = ? AND source_summary LIKE '%voice_capture%'",
            (node_id,)
        ).fetchone()
        if state:
            summary = state['source_summary'] or ''
            # If voice_capture is the only source, reset to unknown
            sources = [s.strip() for s in summary.split(',') if s.strip()]
            non_vc = [s for s in sources if 'voice_capture' not in s]
            if not non_vc:
                conn.execute(
                    "UPDATE knowledge_states SET knowledge = 'unknown', confidence = 0.0, source_summary = '' WHERE node_id = ?",
                    (node_id,))
                print(f'  Reset knowledge state for {node_id} → unknown')
            else:
                new_summary = ', '.join(non_vc)
                conn.execute(
                    "UPDATE knowledge_states SET source_summary = ? WHERE node_id = ?",
                    (new_summary, node_id))

    conn.commit()
    conn.close()
    return len(removed_items)


def fix_review_counts():
    """Fix inflated review_counts from multiple test runs."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, sources, review_count FROM knowledge_items WHERE sources LIKE '%voice_capture%'"
    ).fetchall()

    fixed = 0
    for row in rows:
        sources = json.loads(row['sources'])
        vc = [s for s in sources if s.get('source') == 'voice_capture']
        other = [s for s in sources if s.get('source') != 'voice_capture']
        # Expected review_count: existing reviews + number of distinct voice captures
        # If review_count is way higher, it was inflated by reruns
        # Simple fix: cap at len(vc) for items that had no prior reviews
        if not other and row['review_count'] > len(vc):
            conn.execute('UPDATE knowledge_items SET review_count = ? WHERE id = ?',
                         (len(vc), row['id']))
            print(f'  Fixed review_count {row["id"]}: {row["review_count"]} → {len(vc)}')
            fixed += 1

    conn.commit()
    conn.close()
    return fixed


def trigger_wonderings():
    """Extract wonderings from voice_transcripts and create microlearning requests."""
    from review_engine import create_microlearning_request

    conn = get_connection(readonly=True)
    rows = conn.execute("""
        SELECT id, node_id, domain_id, llm_result
        FROM voice_transcripts
        WHERE source IN ('voice_capture', 'explore_capture')
          AND created_at > ?
        ORDER BY created_at DESC
    """, (int((time.time() - 48 * 3600) * 1000),)).fetchall()  # last 48h
    conn.close()

    all_wonderings = []
    seen_queries = set()

    for row in rows:
        try:
            result = json.loads(row['llm_result']) if row['llm_result'] else {}
        except Exception:
            continue

        wonderings = result.get('wonderings', [])
        node_id = row['node_id']
        domain_id = row['domain_id']

        # Also check for node_assessments to get better source node
        assessments = result.get('node_assessments', [])
        if assessments:
            # Use the node with highest fact count as primary
            best = max(assessments, key=lambda a: a.get('fact_count', 0))
            node_id = best.get('node_id', node_id)

        for w in wonderings:
            w_key = w[:60].lower()
            if w_key not in seen_queries:
                seen_queries.add(w_key)
                all_wonderings.append({
                    'query': w,
                    'node_id': node_id,
                    'domain_id': domain_id,
                })

    print(f'  Found {len(all_wonderings)} unique wonderings across {len(rows)} transcripts')

    triggered = 0
    for w in all_wonderings[:15]:  # cap at 15
        try:
            card_id = create_microlearning_request(
                query=w['query'],
                source_node_id=w['node_id'],
                source_domain=w['domain_id'],
            )
            print(f'  → {card_id}: {w["query"][:70]}')
            triggered += 1
        except Exception as e:
            print(f'  FAILED: {w["query"][:50]}: {e}')

    return triggered


def main():
    dry_run = '--dry-run' in sys.argv

    print('=== 1. DEDUP VOICE CAPTURE SOURCES ===')
    if dry_run:
        print('  [DRY RUN]')
    else:
        n = dedup_sources()
        print(f'  Removed {n} duplicate source entries')

    print('\n=== 2. REMOVE BAD MAPPINGS ===')
    print(f'  Nodes to clean: {sorted(BAD_MAPPINGS)}')
    if dry_run:
        print('  [DRY RUN]')
    else:
        n = remove_bad_mappings()
        print(f'  Cleaned {n} bad node mappings')

    print('\n=== 3. FIX REVIEW COUNTS ===')
    if dry_run:
        print('  [DRY RUN]')
    else:
        n = fix_review_counts()
        print(f'  Fixed {n} inflated review counts')

    print('\n=== 4. TRIGGER WONDERINGS ===')
    if dry_run:
        print('  [DRY RUN]')
    else:
        n = trigger_wonderings()
        print(f'  Triggered {n} microlearning cards')

    print('\nDone!')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Reprocess stuck pending microlearning cards.

Finds all ML cards in 'pending' status and triggers _run_microlearning_research()
for each one. Run on server: cd /opt/petrarca && python3 scripts/reprocess_pending_ml.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from db import get_connection
from review_engine import _run_microlearning_research

def main():
    conn = get_connection()
    pending = conn.execute("""
        SELECT id, query, source_node_id, source_domain, source_type
        FROM microlearning_cards
        WHERE status = 'pending'
        ORDER BY created_at ASC
    """).fetchall()
    conn.close()

    print(f'Found {len(pending)} pending ML cards')

    for i, card in enumerate(pending):
        print(f'\n[{i+1}/{len(pending)}] {card["id"]}: {card["query"][:80]}')
        print(f'  source: {card["source_type"]}, node: {card["source_node_id"]}, domain: {card["source_domain"]}')
        try:
            _run_microlearning_research(
                card_id=card['id'],
                query=card['query'],
                node_id=card['source_node_id'],
                domain_id=card['source_domain'],
            )
            print(f'  ✓ completed')
        except Exception as e:
            print(f'  ✗ failed: {e}')

    # Summary
    conn = get_connection()
    stats = conn.execute("""
        SELECT status, COUNT(*) as cnt
        FROM microlearning_cards
        GROUP BY status
    """).fetchall()
    conn.close()
    print(f'\nFinal status:')
    for s in stats:
        print(f'  {s["status"]}: {s["cnt"]}')

if __name__ == '__main__':
    main()

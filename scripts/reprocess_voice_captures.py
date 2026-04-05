#!/usr/bin/env python3
"""Reprocess voice captures from explore_capture through the rich pipeline.

Usage: python3 reprocess_voice_captures.py [--dry-run]

Reads transcripts from voice_transcripts where source='explore_capture',
runs them through process_voice_capture(), and reports results.
"""
import json
import sys
import os

# Add scripts dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import get_connection
from review_engine import process_voice_capture


def main():
    dry_run = '--dry-run' in sys.argv

    conn = get_connection(readonly=True)
    rows = conn.execute("""
        SELECT id, node_id, domain_id, node_title, transcript, llm_result,
               datetime(created_at/1000, 'unixepoch') as ts
        FROM voice_transcripts
        WHERE source = 'explore_capture'
        ORDER BY created_at DESC
    """).fetchall()
    conn.close()

    print(f'Found {len(rows)} explore_capture transcripts to reprocess')
    print('=' * 70)

    for row in rows:
        print(f'\n--- {row["id"]} ({row["ts"]}) ---')
        print(f'  Title: {row["node_title"]}')
        print(f'  Transcript: {row["transcript"][:150]}...')

        # Parse old LLM result to see what entities were detected
        old_result = {}
        try:
            old_result = json.loads(row['llm_result']) if row['llm_result'] else {}
        except Exception:
            pass
        old_entities = old_result.get('entities_mentioned', [])
        print(f'  Old entities detected: {old_entities}')
        print(f'  Old claims: {len(old_result.get("knowledge_claims", []))}')

        if dry_run:
            print('  [DRY RUN] Would reprocess this transcript')
            continue

        # Reprocess through the rich pipeline
        # These were all general-mode captures (no entity_id)
        result = process_voice_capture(
            transcript=row['transcript'],
            entity_id=None,
            entity_name=None,
            mode='general',
        )

        if result.get('error'):
            print(f'  ERROR: {result["error"]}')
            continue

        print(f'  Facts extracted: {result.get("facts_extracted", 0)}')
        print(f'  Nodes assessed: {result.get("nodes_assessed", 0)}')
        for ku in result.get('knowledge_updates', []):
            print(f'    -> {ku["node_id"]}: {ku["knowledge_level"]} ({ku["facts_captured"]} facts)')
        print(f'  Items created: {result.get("items_created", 0)}, updated: {result.get("items_updated", 0)}')
        print(f'  Questions queued: {result.get("questions_queued", 0)}')
        print(f'  Wonderings: {len(result.get("wonderings", []))}')
        for w in result.get('wonderings', [])[:3]:
            print(f'    ? {w}')
        print(f'  ML cards triggered: {len(result.get("microlearning_triggered", []))}')
        print(f'  Summary: {result.get("overall_summary", "")}')

    print('\n' + '=' * 70)
    print('Done!')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Reprocess existing voice transcripts into the knowledge profile system.

Creates transcript_chunks with embeddings and links them to curriculum nodes
and entities. Idempotent — safe to run multiple times.

Usage: python3 reprocess_transcripts.py
"""

import json
import sys
import time

sys.path.insert(0, '/opt/limbic')

from db import get_connection, init_db
from review_engine import create_transcript_chunks


def main():
    init_db()
    conn = get_connection()

    # Fetch all voice transcripts
    transcripts = conn.execute(
        '''SELECT id, source, node_id, domain_id, transcript, llm_result
           FROM voice_transcripts
           ORDER BY created_at ASC'''
    ).fetchall()

    print(f'Found {len(transcripts)} voice transcripts to process')

    total_chunks = 0
    processed = 0
    skipped = 0
    errors = 0

    for row in transcripts:
        transcript_id = row['id']
        source = row['source']
        node_id = row['node_id'] or ''
        domain_id = row['domain_id'] or ''
        transcript = row['transcript'] or ''

        # Check if already processed
        existing = conn.execute(
            'SELECT COUNT(*) FROM transcript_chunks WHERE transcript_id = ?',
            (transcript_id,)
        ).fetchone()
        if existing[0] > 0:
            skipped += 1
            continue

        # Parse llm_result
        llm_result = {}
        if row['llm_result']:
            try:
                llm_result = json.loads(row['llm_result'])
            except (json.JSONDecodeError, TypeError):
                pass

        if not transcript and not llm_result:
            skipped += 1
            continue

        try:
            count = create_transcript_chunks(
                transcript_id=transcript_id,
                node_id=node_id,
                domain_id=domain_id,
                transcript=transcript,
                llm_result=llm_result,
                conn=conn,
            )
            total_chunks += count
            processed += 1
            if count > 0:
                print(f'  [{processed}] {transcript_id} ({source}): {count} chunks — node={node_id}')
        except Exception as e:
            errors += 1
            print(f'  ERROR processing {transcript_id}: {e}')
            # Rollback any partial writes and continue
            conn.rollback()

    # Summary statistics
    node_links = conn.execute('SELECT COUNT(*) FROM chunk_node_links').fetchone()[0]
    entity_links = conn.execute('SELECT COUNT(*) FROM chunk_entity_links').fetchone()[0]
    unique_nodes = conn.execute('SELECT COUNT(DISTINCT node_id) FROM chunk_node_links').fetchone()[0]
    unique_entities = conn.execute('SELECT COUNT(DISTINCT entity_name) FROM chunk_entity_links').fetchone()[0]

    conn.close()

    print(f'\n--- Summary ---')
    print(f'Transcripts: {len(transcripts)} total, {processed} processed, {skipped} skipped, {errors} errors')
    print(f'Chunks created: {total_chunks}')
    print(f'Node links: {node_links} (across {unique_nodes} unique nodes)')
    print(f'Entity links: {entity_links} (across {unique_entities} unique entities)')

    # Generate domain summaries for domains with sufficient data
    print('\n--- Generating domain summaries ---')
    from review_engine import generate_domain_summary
    conn = get_connection(readonly=True)
    domains = conn.execute(
        'SELECT DISTINCT domain_id FROM chunk_node_links WHERE domain_id IS NOT NULL AND domain_id != ""'
    ).fetchall()
    domain_chunks = {}
    for row in domains:
        domain_id = row[0]
        chunk_count = conn.execute(
            'SELECT COUNT(DISTINCT cnl.chunk_id) FROM chunk_node_links cnl WHERE cnl.domain_id = ?',
            (domain_id,)
        ).fetchone()[0]
        domain_chunks[domain_id] = chunk_count
    conn.close()

    for domain_id, chunk_count in domain_chunks.items():
        if chunk_count >= 10:
            try:
                result = generate_domain_summary(domain_id)  # manages its own connections
                if result:
                    print(f'  Generated summary for {domain_id}: {len(result)} chars')
                else:
                    print(f'  Skipped {domain_id}: insufficient data')
            except Exception as e:
                print(f'  ERROR generating summary for {domain_id}: {e}')
        else:
            print(f'  Skipped {domain_id}: only {chunk_count} chunks (need 10+)')


if __name__ == '__main__':
    main()

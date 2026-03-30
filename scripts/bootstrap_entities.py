#!/usr/bin/env python3
"""Bootstrap shared_entities from curriculum nodes using LLM extraction.

Reads all curriculum nodes, extracts named entities (places, people, events,
periods) with coordinates, descriptions, Wikipedia URLs, and curriculum links.
Writes results to shared_entities + entity_curriculum_links tables.

Usage:
    python3 bootstrap_entities.py                    # all domains
    python3 bootstrap_entities.py --domain sicily    # one domain
    python3 bootstrap_entities.py --dry-run          # show prompt, don't call LLM
    python3 bootstrap_entities.py --dump             # dump current entities as JSON
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from db import get_connection, init_db
from curriculum_db import load_curriculum, list_curricula

try:
    from gemini_llm import call_llm
except ImportError:
    call_llm = None


def build_extraction_prompt(domain: dict) -> str:
    """Build prompt to extract entities from curriculum nodes."""
    nodes_block = []
    for n in domain['nodes']:
        if n.get('level', 1) < 2:
            continue  # skip top-level area headers
        dates = ""
        if n.get('date_start') is not None:
            start = n['date_start']
            end = n.get('date_end')
            dates = f" [{start}{'–' + str(end) if end else ''} {'BC' if start < 0 else 'AD'}]"
        nodes_block.append(
            f"  {n['id']}: {n['title']}{dates}\n"
            f"    {n.get('description', '')[:200]}"
        )

    return f"""Extract named entities from this curriculum for a knowledge review app.

Curriculum: {domain['title']}
Description: {domain.get('description', '')}

Nodes:
{chr(10).join(nodes_block)}

For each important entity mentioned or implied by these nodes, extract:

- "entity_id": lowercase slug (e.g., "akragas", "gelon", "battle_of_himera")
- "name": Display name as it appears in historical text (e.g., "Akragas", "Gelon", "Battle of Himera")
- "entity_type": one of "place", "person", "event", "period"
- "description": 1-2 sentences — what a learner needs to know to understand references to this entity
- "modern_name": modern equivalent if different (e.g., "Agrigento" for Akragas), null if same or N/A
- "wikipedia_url": English Wikipedia article URL (must be real, use standard article naming)
- "latitude": decimal degrees (for places only, null for others)
- "longitude": decimal degrees (for places only, null for others)
- "aliases": array of alternate names/spellings (e.g., ["Agrigentum"] for Akragas)
- "date_start": year as integer, negative for BCE (e.g., -580 for 580 BC)
- "date_end": year as integer, null if still exists or single event
- "node_links": array of objects linking this entity to curriculum nodes:
  - "node_id": exact node ID from the list above
  - "lens_title": how this entity appears in this node's context (2-5 words)
  - "lens_emphasis": what aspect of the entity matters for this node (1 sentence)

Guidelines:
- Extract 30-60 entities per curriculum. Focus on entities that appear in review questions.
- Every place that a learner might encounter in a review card should be included.
- Every historically significant person mentioned in node titles/descriptions should be included.
- Major battles, treaties, and turning-point events get their own entity.
- Periods (e.g., "Age of Tyrants") are entities too.
- For coordinates: use the ancient site location, not the modern city center.
- Deduplicate: if the same entity appears across multiple nodes, produce ONE entity with multiple node_links.
- Wikipedia URLs must follow the pattern: https://en.wikipedia.org/wiki/Article_Name

Return ONLY valid JSON array:
[{{"entity_id":"...","name":"...","entity_type":"...","description":"...","modern_name":"...","wikipedia_url":"...","latitude":null,"longitude":null,"aliases":[],"date_start":null,"date_end":null,"node_links":[{{"node_id":"...","lens_title":"...","lens_emphasis":"..."}}]}}]"""


def parse_json_response(text: str) -> list | None:
    """Extract JSON array from LLM response."""
    if not text:
        return None
    # Try direct parse
    text = text.strip()
    if text.startswith('```'):
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    # Try extracting array from response
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def insert_entities(entities: list, domain_id: str, conn) -> tuple[int, int]:
    """Insert entities and links into database. Returns (entities_created, links_created)."""
    entities_created = 0
    links_created = 0

    for e in entities:
        eid = e.get('entity_id', '')
        if not eid:
            continue

        # Upsert entity
        existing = conn.execute(
            'SELECT entity_id FROM shared_entities WHERE entity_id = ?', (eid,)
        ).fetchone()

        if existing:
            conn.execute('''
                UPDATE shared_entities SET
                    name = COALESCE(?, name),
                    description = COALESCE(?, description),
                    entity_type = COALESCE(?, entity_type),
                    modern_name = COALESCE(?, modern_name),
                    wikipedia_url = COALESCE(?, wikipedia_url),
                    latitude = COALESCE(?, latitude),
                    longitude = COALESCE(?, longitude),
                    aliases = COALESCE(?, aliases),
                    date_start = COALESCE(?, date_start),
                    date_end = COALESCE(?, date_end),
                    nexus_score = nexus_score + 1
                WHERE entity_id = ?
            ''', (
                e.get('name'), e.get('description'), e.get('entity_type'),
                e.get('modern_name'), e.get('wikipedia_url'),
                e.get('latitude'), e.get('longitude'),
                json.dumps(e.get('aliases', [])),
                e.get('date_start'), e.get('date_end'),
                eid,
            ))
        else:
            conn.execute('''
                INSERT INTO shared_entities
                (entity_id, name, description, entity_type, modern_name,
                 wikipedia_url, latitude, longitude, aliases, dates,
                 date_start, date_end, nexus_score, location)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ''', (
                eid, e.get('name', ''), e.get('description'),
                e.get('entity_type'), e.get('modern_name'),
                e.get('wikipedia_url'), e.get('latitude'), e.get('longitude'),
                json.dumps(e.get('aliases', [])),
                e.get('dates', ''),
                e.get('date_start'), e.get('date_end'),
                1, e.get('location', ''),
            ))
            entities_created += 1

        # Insert curriculum links
        for link in e.get('node_links', []):
            node_id = link.get('node_id', '')
            if not node_id:
                continue
            try:
                conn.execute('''
                    INSERT OR IGNORE INTO entity_curriculum_links
                    (entity_id, domain_id, node_id, lens_title, lens_emphasis)
                    VALUES (?,?,?,?,?)
                ''', (
                    eid, domain_id, node_id,
                    link.get('lens_title', ''), link.get('lens_emphasis', ''),
                ))
                links_created += 1
            except Exception as ex:
                print(f'  Link skip {eid}→{node_id}: {ex}', flush=True)

    return entities_created, links_created


def dump_entities(conn):
    """Dump all entities as JSON to stdout."""
    rows = conn.execute('''
        SELECT e.*, GROUP_CONCAT(l.domain_id || ':' || l.node_id, '|') as links
        FROM shared_entities e
        LEFT JOIN entity_curriculum_links l ON e.entity_id = l.entity_id
        GROUP BY e.entity_id
        ORDER BY e.name
    ''').fetchall()
    entities = []
    for r in rows:
        entities.append({
            'entity_id': r['entity_id'],
            'name': r['name'],
            'entity_type': r['entity_type'],
            'description': r['description'],
            'modern_name': r['modern_name'],
            'wikipedia_url': r['wikipedia_url'],
            'latitude': r['latitude'],
            'longitude': r['longitude'],
            'aliases': json.loads(r['aliases'] or '[]'),
            'date_start': r['date_start'],
            'date_end': r['date_end'],
            'nexus_score': r['nexus_score'],
            'links': r['links'],
        })
    print(json.dumps(entities, indent=2, ensure_ascii=False))
    print(f'\n{len(entities)} entities total', file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description='Bootstrap entities from curriculum nodes')
    parser.add_argument('--domain', help='Only process this domain (partial match)')
    parser.add_argument('--dry-run', action='store_true', help='Show prompt without calling LLM')
    parser.add_argument('--dump', action='store_true', help='Dump current entities as JSON')
    parser.add_argument('--model', default=None, help='LLM model override')
    args = parser.parse_args()

    init_db()
    conn = get_connection()

    if args.dump:
        dump_entities(conn)
        conn.close()
        return

    curricula = list_curricula(conn)
    if not curricula:
        print('No curricula found')
        conn.close()
        return

    for meta in curricula:
        domain_id = meta['id']
        if args.domain and args.domain.lower() not in domain_id.lower():
            continue

        print(f'\n=== {meta["title"]} ({domain_id}) ===', flush=True)
        curriculum = load_curriculum(domain_id, conn)
        if not curriculum:
            print('  Failed to load curriculum')
            continue

        level2_plus = [n for n in curriculum['nodes'] if n.get('level', 1) >= 2]
        print(f'  {len(level2_plus)} nodes (level 2+)', flush=True)

        prompt = build_extraction_prompt(curriculum)

        if args.dry_run:
            print(f'\n--- PROMPT ({len(prompt)} chars) ---')
            print(prompt[:2000])
            print('...')
            continue

        if not call_llm:
            print('  No LLM available (gemini_llm not importable)')
            continue

        print(f'  Calling LLM ({len(prompt)} chars)...', flush=True)
        model = args.model or 'gemini-2.5-flash'
        raw = call_llm(prompt, model=model, max_tokens=8192,
                       response_mime_type='application/json')

        entities = parse_json_response(raw)
        if not entities:
            print(f'  Failed to parse response')
            if raw:
                print(f'  Raw: {raw[:500]}')
            continue

        print(f'  Extracted {len(entities)} entities', flush=True)
        created, links = insert_entities(entities, domain_id, conn)
        conn.commit()
        print(f'  Inserted: {created} entities, {links} links', flush=True)

    # Summary
    total = conn.execute('SELECT COUNT(*) FROM shared_entities').fetchone()[0]
    total_links = conn.execute('SELECT COUNT(*) FROM entity_curriculum_links').fetchone()[0]
    print(f'\nTotal: {total} entities, {total_links} links')
    conn.close()


if __name__ == '__main__':
    main()

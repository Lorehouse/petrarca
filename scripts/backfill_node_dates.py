#!/usr/bin/env python3
"""Backfill date_start/date_end on curriculum nodes that lack them.

For each curriculum missing dates, builds a prompt with all node titles,
descriptions, and key_facts answers, then calls Claude to extract structured
date ranges. Updates both JSON files and SQLite database.

Usage:
    python3 scripts/backfill_node_dates.py                      # all curricula missing dates
    python3 scripts/backfill_node_dates.py --domain sicily       # one domain (partial match)
    python3 scripts/backfill_node_dates.py --dry-run             # show prompt, don't call LLM
    python3 scripts/backfill_node_dates.py --json-only           # update JSON files only (no SQLite)
    python3 scripts/backfill_node_dates.py --report              # just show coverage report
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

DATA_DIR = Path(os.environ.get('CURRICULUM_DIR', 'data/curricula'))

# ── Claude CLI helper ───────────────────────────────────────────────────────

def call_claude(prompt: str, timeout: int = 300) -> str | None:
    """Call Claude via `claude -p` subprocess (free with Max plan)."""
    try:
        cmd = ['claude', '-p', '--output-format', 'json', '--no-session-persistence']
        proc = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True, timeout=timeout
        )
        if proc.returncode == 0 and proc.stdout.strip():
            resp = json.loads(proc.stdout)
            if not resp.get('is_error'):
                return resp.get('result', '')
            print(f'  Claude returned error: {resp}', file=sys.stderr)
        else:
            if proc.stderr:
                print(f'  Claude stderr: {proc.stderr[:300]}', file=sys.stderr)
    except subprocess.TimeoutExpired:
        print(f'  Claude call timed out after {timeout}s', file=sys.stderr)
    except Exception as e:
        print(f'  Claude call failed: {e}', file=sys.stderr)
    return None


# ── Prompt building ─────────────────────────────────────────────────────────

def build_date_extraction_prompt(curriculum: dict, nodes: list[dict] | None = None) -> str:
    """Build a prompt asking Claude to assign date_start/date_end to each node."""
    target_nodes = nodes if nodes is not None else curriculum['nodes']
    nodes_block = []
    for n in target_nodes:
        node_text = f"NODE: {n['id']}\n  Title: {n['title']}\n  Level: {n.get('level', 2)}"
        if n.get('description'):
            # Trim description to 250 chars for large curricula
            desc = n['description'][:250]
            node_text += f"\n  Description: {desc}"
        # Include key_facts answers (just date-type facts, max 3) for temporal info
        facts = n.get('key_facts', [])
        if facts:
            date_facts = [f.get('answer', '') for f in facts[:3]
                          if f.get('answer') and f.get('type') in ('date', 'event')]
            if not date_facts:
                date_facts = [f.get('answer', '') for f in facts[:2] if f.get('answer')]
            if date_facts:
                node_text += f"\n  Key facts: {' | '.join(date_facts)}"
        nodes_block.append(node_text)

    return f"""You are a historian. For each curriculum node below, determine the approximate date range it covers.

Curriculum: {curriculum['title']}

{chr(10).join(nodes_block)}

For EACH node above, output a JSON object with exactly these fields:
- "id": the node ID (copy exactly from above)
- "date_start": integer year. Negative for BCE (e.g., 734 BC = -734, 330 AD = 330). Use the earliest relevant date for the topic.
- "date_end": integer year. Use the latest relevant date. If a node covers a single event, date_end should equal date_start or be within a few years.

RULES:
- Level 1 (area) nodes should span the full range of their children.
- Level 2+ nodes should be as precise as the content allows.
- For undatable topics (e.g., "historiography", "cultural legacy", "reception"), use the dates of the period being discussed, not when the reception happened. If truly undatable, use null for both.
- For topics spanning "to the present", use the last historically significant date discussed, not today.
- Every node MUST get dates unless genuinely undatable. Aim for 95%+ coverage.

Output ONLY a JSON array. No markdown fencing, no explanation."""


# ── JSON parsing ────────────────────────────────────────────────────────────

def parse_json_response(text: str) -> list | None:
    """Extract JSON array from Claude response."""
    if not text:
        return None
    text = text.strip()
    # Strip markdown fences
    if text.startswith('```'):
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```\s*$', '', text)
        text = text.strip()
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    # Try extracting array
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    # Handle truncated JSON
    if text.startswith('['):
        last_complete = text.rfind('},')
        if last_complete > 0:
            truncated = text[:last_complete + 1] + ']'
            try:
                data = json.loads(truncated)
                if isinstance(data, list):
                    print(f'  (parsed truncated response: {len(data)} items)')
                    return data
            except json.JSONDecodeError:
                pass
    return None


# ── Main logic ──────────────────────────────────────────────────────────────

def load_all_curricula() -> list[dict]:
    """Load all curriculum JSONs from data directory."""
    curricula = []
    for path in sorted(DATA_DIR.glob('*.json')):
        if path.name.startswith('sicily_timeline') or path.name == 'entity_index.json':
            continue
        if path.name == 'place_hierarchy.json':
            continue
        try:
            data = json.load(open(path))
            if isinstance(data, dict) and 'nodes' in data and 'id' in data:
                data['_path'] = str(path)
                curricula.append(data)
        except (json.JSONDecodeError, KeyError):
            continue
    return curricula


def needs_dates(curriculum: dict) -> bool:
    """Check if a curriculum needs date backfill."""
    nodes = curriculum.get('nodes', [])
    if not nodes:
        return False
    with_dates = sum(1 for n in nodes if n.get('date_start') is not None)
    return with_dates < len(nodes)


def apply_dates(curriculum: dict, date_results: list) -> tuple[int, int]:
    """Apply date results to a curriculum. Returns (updated_count, skipped_count)."""
    date_map = {}
    for entry in date_results:
        nid = entry.get('id', '')
        if nid:
            date_map[nid] = entry

    updated = 0
    skipped = 0
    for node in curriculum['nodes']:
        if node.get('date_start') is not None:
            continue  # already has dates
        entry = date_map.get(node['id'])
        if entry and entry.get('date_start') is not None:
            node['date_start'] = int(entry['date_start'])
            node['date_end'] = int(entry['date_end']) if entry.get('date_end') is not None else int(entry['date_start'])
            updated += 1
        else:
            skipped += 1

    return updated, skipped


def save_curriculum_json(curriculum: dict):
    """Save curriculum back to its JSON file."""
    path = curriculum.pop('_path', None)
    if not path:
        print('  No path found, cannot save')
        return
    # Remove internal _path before saving
    with open(path, 'w') as f:
        json.dump(curriculum, f, indent=2, ensure_ascii=False)
    curriculum['_path'] = path
    print(f'  Saved to {path}')


def update_sqlite(curriculum: dict):
    """Update date_start/date_end in SQLite for nodes that got dates."""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from db import get_connection, init_db
        init_db()
        conn = get_connection()
    except Exception as e:
        print(f'  SQLite update skipped (not on server?): {e}')
        return

    domain_id = curriculum['id']
    updated = 0
    for node in curriculum['nodes']:
        if node.get('date_start') is not None:
            conn.execute(
                'UPDATE curriculum_nodes SET date_start = ?, date_end = ? '
                'WHERE domain_id = ? AND id = ?',
                (node['date_start'], node.get('date_end'), domain_id, node['id'])
            )
            updated += 1

    conn.commit()
    conn.close()
    print(f'  SQLite: updated {updated} nodes in {domain_id}')


def print_report(curricula: list[dict]):
    """Print coverage report for all curricula."""
    total_nodes = 0
    total_dated = 0
    print('\n=== Date Coverage Report ===\n')
    for c in curricula:
        nodes = c.get('nodes', [])
        dated = sum(1 for n in nodes if n.get('date_start') is not None)
        total = len(nodes)
        total_nodes += total
        total_dated += dated
        status = 'OK' if dated == total else f'MISSING {total - dated}'
        print(f'  {c["id"]:<60} {dated:>3}/{total:<3}  {status}')

    print(f'\n  TOTAL: {total_dated}/{total_nodes} nodes have dates '
          f'({total_dated * 100 // total_nodes if total_nodes else 0}%)')
    missing = total_nodes - total_dated
    if missing:
        print(f'  {missing} nodes still need dates')


def main():
    parser = argparse.ArgumentParser(description='Backfill date_start/date_end on curriculum nodes')
    parser.add_argument('--domain', help='Only process this domain (partial match)')
    parser.add_argument('--dry-run', action='store_true', help='Show prompt without calling Claude')
    parser.add_argument('--json-only', action='store_true', help='Update JSON files only (no SQLite)')
    parser.add_argument('--report', action='store_true', help='Just show coverage report')
    args = parser.parse_args()

    curricula = load_all_curricula()
    if not curricula:
        print(f'No curricula found in {DATA_DIR}')
        return

    if args.report:
        print_report(curricula)
        return

    processed = 0
    for curriculum in curricula:
        domain_id = curriculum['id']

        if args.domain and args.domain.lower() not in domain_id.lower():
            continue

        if not needs_dates(curriculum):
            print(f'\n--- {curriculum["title"]} --- all {len(curriculum["nodes"])} nodes have dates, skipping')
            continue

        nodes = curriculum['nodes']
        undated = [n for n in nodes if n.get('date_start') is None]
        dated_count = len(nodes) - len(undated)
        print(f'\n=== {curriculum["title"]} ({domain_id}) ===')
        print(f'  {len(nodes)} nodes, {dated_count} already have dates, {len(undated)} need dates')

        # Split into batches if prompt would be too large (>50K chars)
        test_prompt = build_date_extraction_prompt(curriculum, undated)
        if len(test_prompt) > 50000:
            mid = len(undated) // 2
            batches = [undated[:mid], undated[mid:]]
            print(f'  Large curriculum — splitting into {len(batches)} batches')
        else:
            batches = [undated]

        if args.dry_run:
            prompt = build_date_extraction_prompt(curriculum, batches[0])
            print(f'  Prompt: {len(prompt)} chars (batch 1 of {len(batches)})')
            print(f'\n--- PROMPT (first 2000 chars) ---')
            print(prompt[:2000])
            print('...')
            continue

        all_date_results = []
        for batch_idx, batch_nodes in enumerate(batches):
            prompt = build_date_extraction_prompt(curriculum, batch_nodes)
            print(f'  Batch {batch_idx + 1}/{len(batches)}: {len(batch_nodes)} nodes, {len(prompt)} chars')
            print(f'  Calling Claude...', flush=True)
            raw = call_claude(prompt, timeout=600)
            if not raw:
                print(f'  No response from Claude for batch {batch_idx + 1}')
                continue

            print(f'  Response: {len(raw)} chars')
            date_results = parse_json_response(raw)
            if not date_results:
                print(f'  Failed to parse response for batch {batch_idx + 1}')
                if raw:
                    print(f'  First 300: {raw[:300]}')
                continue

            print(f'  Parsed {len(date_results)} date entries')
            all_date_results.extend(date_results)

        if not all_date_results:
            print(f'  No date results obtained')
            continue

        updated, skipped = apply_dates(curriculum, all_date_results)
        print(f'  Applied: {updated} nodes updated, {skipped} nodes skipped (no dates from LLM)')

        save_curriculum_json(curriculum)

        if not args.json_only:
            update_sqlite(curriculum)

        processed += 1

    if processed > 0:
        print(f'\n{"=" * 50}')
        print_report(curricula)
    elif not args.dry_run:
        print('\nNo curricula needed date backfill.')


if __name__ == '__main__':
    main()

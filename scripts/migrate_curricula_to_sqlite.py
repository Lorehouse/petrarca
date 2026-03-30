"""One-time migration: move all curriculum JSON files into SQLite.

Run: python3 migrate_curricula_to_sqlite.py [--dry-run]

Migrates:
  - Curriculum structures ({domain}.json → curriculum_domains + curriculum_nodes + curriculum_prerequisites)
  - Knowledge states (knowledge_{domain}.json → knowledge_states)
  - Book mappings (mappings_{domain}_{book_id}.json → book_curriculum_mappings)
  - Retrieval questions (*_retrieval_questions.json → retrieval_questions)
  - Timeline entries (*_timeline.json → timeline_entries)
  - Elicitation sessions (elicit_*.json → elicitation_sessions)
  - Cross-curriculum entities (cross_curriculum_entities.json → shared_entities + entity_curriculum_links)
"""

import hashlib
import json
import os
import sys
from pathlib import Path

# Ensure imports work
sys.path.insert(0, str(Path(__file__).parent))
# Default to petrarca.db on server, petrarca_content.db locally (if petrarca.db doesn't exist)
_default_db = Path(__file__).parent.parent / 'data' / 'petrarca.db'
if not _default_db.exists():
    _default_db = Path(__file__).parent.parent / 'data' / 'petrarca_content.db'
os.environ.setdefault('PETRARCA_DB', str(_default_db))

from db import get_connection, init_db

CURRICULA_DIR = Path(__file__).parent.parent / 'data' / 'curricula'

# Known curriculum structure files (not knowledge_, mappings_, etc.)
CURRICULUM_STRUCTURE_FILES = [
    'ancient_greece_800300_bc_political_military_cultural_and.json',
    'roman_republic_and_empire.json',
    'roman_republic_and_empire_509_bc_476_ad.json',
    'roman_republic_and_late_republic_50927_bc_politics.json',
    'sicily_history_culture_and_legacy.json',
    'byzantine_empire_history_culture_and_legacy_3301453_ad.json',
    'islamic_civilization_history_expansion_and_intellectual_legacy_5701500.json',
]


def log(msg):
    print(f'[migrate] {msg}', flush=True)


def migrate_curriculum_structure(conn, path: Path) -> str | None:
    """Migrate a curriculum JSON file into curriculum_domains + curriculum_nodes + curriculum_prerequisites."""
    data = json.loads(path.read_text())

    domain_id = data.get('id')
    if not domain_id:
        log(f'  Skipping {path.name}: no id field')
        return None

    # Check if already migrated
    existing = conn.execute('SELECT id FROM curriculum_domains WHERE id = ?', (domain_id,)).fetchone()
    if existing:
        log(f'  Domain {domain_id} already exists, skipping')
        return domain_id

    nodes = data.get('nodes', [])
    log(f'  Domain: {domain_id} — {len(nodes)} nodes')

    conn.execute(
        'INSERT INTO curriculum_domains (id, title, description, depth, generated_at, generated_by, node_count) VALUES (?,?,?,?,?,?,?)',
        (domain_id, data.get('title', ''), data.get('description', ''),
         data.get('depth', 'introductory'), data.get('generated_at'), data.get('generated_by'), len(nodes))
    )

    for node in nodes:
        conn.execute(
            '''INSERT OR IGNORE INTO curriculum_nodes
               (id, domain_id, title, description, parent_id, level, obscurity, bloom_floor,
                knowledge_type, date_start, date_end)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
            (node['id'], domain_id, node['title'], node.get('description', ''),
             node.get('parent_id'), node.get('level', 1), node.get('obscurity', 2),
             node.get('bloom_floor', 'recognize'), node.get('knowledge_type', 'core'),
             node.get('date_start'), node.get('date_end'))
        )

    # Insert prerequisites in a second pass (all nodes must exist first)
    node_ids = {n['id'] for n in nodes}
    prereq_count = 0
    for node in nodes:
        for prereq_id in node.get('prerequisites', []):
            if prereq_id in node_ids:
                conn.execute(
                    'INSERT OR IGNORE INTO curriculum_prerequisites (domain_id, node_id, prerequisite_id, strength) VALUES (?,?,?,?)',
                    (domain_id, node['id'], prereq_id, 'hard')
                )
                prereq_count += 1
            else:
                log(f'    Warning: prerequisite {prereq_id} not found in {domain_id}, skipping')
    log(f'    {prereq_count} prerequisite edges')

    return domain_id


def migrate_knowledge_states(conn, path: Path):
    """Migrate knowledge_{domain}.json → knowledge_states."""
    data = json.loads(path.read_text())
    # Extract domain_id from filename: knowledge_{domain_id}.json
    fname = path.stem  # knowledge_ancient_greece_800300_bc_...
    domain_id = fname.replace('knowledge_', '', 1)

    count = 0
    for node_id, state in data.items():
        conn.execute(
            '''INSERT OR REPLACE INTO knowledge_states
               (domain_id, node_id, knowledge, interest, confidence, highest_layer,
                source_summary, last_assessed)
               VALUES (?,?,?,?,?,?,?,?)''',
            (domain_id, node_id, state.get('knowledge', 'unknown'),
             state.get('interest', 'none'), state.get('confidence', 0.0),
             _knowledge_to_layer(state.get('knowledge', 'unknown')),
             json.dumps(state.get('sources', []), ensure_ascii=False),
             state.get('last_assessed'))
        )
        count += 1
    log(f'  Knowledge states: {count} nodes for {domain_id}')


def _knowledge_to_layer(knowledge: str) -> int:
    return {'unknown': 0, 'mentioned': 1, 'engaged': 2, 'anchored': 3}.get(knowledge, 0)


def migrate_book_mappings(conn, path: Path):
    """Migrate mappings_{domain}_{book_id}.json → book_curriculum_mappings."""
    data = json.loads(path.read_text())
    if not data:
        return

    # Parse domain and book_id from filename
    fname = path.stem  # mappings_{domain}_{book_id_type}_{book_id}
    # The domain is everything between 'mappings_' and the last two segments
    # e.g. mappings_ancient_greece_800300_bc_political_military_cultural_and_kindle_B003E1BGLO
    # This is tricky because domain_id itself has underscores. Use known domain IDs.
    parts = fname.replace('mappings_', '', 1)

    # Try to match against known domains
    domain_id = None
    book_id = None
    for known_domain in _get_known_domains(conn):
        if parts.startswith(known_domain + '_'):
            domain_id = known_domain
            book_id = parts[len(known_domain) + 1:]
            break

    if not domain_id:
        log(f'  Skipping mapping {path.name}: could not determine domain')
        return

    count = 0
    for entry in data:
        node_id = entry.get('node_id')
        if not node_id:
            continue
        conn.execute(
            'INSERT OR IGNORE INTO book_curriculum_mappings (book_id, domain_id, node_id, coverage, inferred_from) VALUES (?,?,?,?,?)',
            (book_id, domain_id, node_id, entry.get('coverage', 'surface'),
             entry.get('inferred_from', 'llm_inference'))
        )
        count += 1
    log(f'  Book mappings: {count} links for book {book_id[:20]}... → {domain_id[:30]}...')


def _get_known_domains(conn) -> list[str]:
    rows = conn.execute('SELECT id FROM curriculum_domains').fetchall()
    return [r[0] for r in rows]


def migrate_retrieval_questions(conn, path: Path):
    """Migrate *_retrieval_questions.json → retrieval_questions."""
    data = json.loads(path.read_text())
    domain_slug = path.stem.replace('_retrieval_questions', '')

    # Find matching domain_id
    domain_id = _find_domain_for_slug(conn, domain_slug)
    if not domain_id:
        log(f'  Skipping retrieval questions {path.name}: no matching domain for "{domain_slug}"')
        return

    count = 0
    for q in data:
        q_id = hashlib.md5(q['question'].encode()).hexdigest()[:12]
        # Try to find the node_id from the node_title
        node_id = _find_node_by_title(conn, domain_id, q.get('node_title', ''))
        conn.execute(
            '''INSERT OR IGNORE INTO retrieval_questions
               (id, domain_id, node_id, question, answer, question_type, node_title, cluster_label, generated_at)
               VALUES (?,?,?,?,?,?,?,?,?)''',
            (q_id, domain_id, node_id or '', q['question'], q['answer'],
             q.get('type', 'event'), q.get('node_title', ''), q.get('cluster_label'),
             None)
        )
        count += 1
    log(f'  Retrieval questions: {count} for {domain_id}')


def migrate_ordering_questions(conn, path: Path):
    """Migrate *_ordering_questions.json → retrieval_questions (as type temporal_ordering)."""
    data = json.loads(path.read_text())
    domain_slug = path.stem.replace('_ordering_questions', '')
    domain_id = _find_domain_for_slug(conn, domain_slug)
    if not domain_id:
        log(f'  Skipping ordering questions {path.name}: no matching domain')
        return

    count = 0
    for q in data:
        q_id = hashlib.md5(q['question'].encode()).hexdigest()[:12]
        conn.execute(
            '''INSERT OR IGNORE INTO retrieval_questions
               (id, domain_id, node_id, question, answer, question_type, node_title, cluster_label, generated_at)
               VALUES (?,?,?,?,?,?,?,?,?)''',
            (q_id, domain_id, '', q['question'], q['answer'],
             'temporal_ordering', '', q.get('cluster_label'), None)
        )
        count += 1
    log(f'  Ordering questions: {count} for {domain_id}')


def migrate_timeline(conn, path: Path):
    """Migrate *_timeline.json → timeline_entries."""
    data = json.loads(path.read_text())
    domain_slug = path.stem.replace('_timeline', '')
    domain_id = _find_domain_for_slug(conn, domain_slug)
    if not domain_id:
        log(f'  Skipping timeline {path.name}: no matching domain')
        return

    count = 0
    for entry in data:
        year = entry.get('year', entry.get('year_start'))
        if year is None:
            continue
        conn.execute(
            'INSERT INTO timeline_entries (domain_id, year, label, detail, node_id) VALUES (?,?,?,?,?)',
            (domain_id, year, entry['label'], entry.get('detail', ''),
             entry.get('node_id'))
        )
        count += 1
    log(f'  Timeline entries: {count} for {domain_id}')


def migrate_elicitation_sessions(conn, path: Path):
    """Migrate elicit_*.json → elicitation_sessions."""
    data = json.loads(path.read_text())
    session_id = data.get('id', path.stem)
    responses = data.get('history', data.get('responses', []))
    nodes_assessed = data.get('nodes_assessed', 0)
    if isinstance(nodes_assessed, list):
        nodes_assessed = len(nodes_assessed)
    conn.execute(
        '''INSERT OR IGNORE INTO elicitation_sessions
           (id, domain_id, started_at, completed_at, questions_asked, nodes_assessed, responses)
           VALUES (?,?,?,?,?,?,?)''',
        (session_id, data.get('domain_id', ''), data.get('started_at', ''),
         data.get('completed_at'), data.get('questions_asked', 0),
         nodes_assessed,
         json.dumps(responses, ensure_ascii=False))
    )
    log(f'  Elicitation session: {session_id}')


def migrate_cross_curriculum_entities(conn, path: Path):
    """Migrate cross_curriculum_entities.json → shared_entities + entity_curriculum_links."""
    data = json.loads(path.read_text())
    count = 0
    for entity in data:
        eid = entity.get('entity_id', entity.get('id', ''))
        if not eid:
            continue
        conn.execute(
            'INSERT OR IGNORE INTO shared_entities (entity_id, name, dates, location, nexus_score) VALUES (?,?,?,?,?)',
            (eid, entity.get('name', ''), entity.get('dates'), entity.get('location'),
             entity.get('nexus_score', len(entity.get('curricula', []))))
        )
        for link in entity.get('lenses', entity.get('curricula_lenses', [])):
            conn.execute(
                'INSERT OR IGNORE INTO entity_curriculum_links (entity_id, domain_id, node_id, lens_title, lens_emphasis) VALUES (?,?,?,?,?)',
                (eid, link.get('domain_id', link.get('curriculum', '')),
                 link.get('node_id', ''), link.get('title', ''), link.get('emphasis', ''))
            )
        count += 1
    log(f'  Shared entities: {count}')


def _find_domain_for_slug(conn, slug: str) -> str | None:
    """Find a domain_id that matches a slug like 'sicily'."""
    # Try exact match first
    row = conn.execute('SELECT id FROM curriculum_domains WHERE id = ?', (slug,)).fetchone()
    if row:
        return row[0]
    # Try partial match
    row = conn.execute('SELECT id FROM curriculum_domains WHERE id LIKE ?', (f'%{slug}%',)).fetchone()
    if row:
        return row[0]
    return None


def _find_node_by_title(conn, domain_id: str, title: str) -> str | None:
    """Find a node_id by its title within a domain."""
    if not title:
        return None
    row = conn.execute(
        'SELECT id FROM curriculum_nodes WHERE domain_id = ? AND title = ?',
        (domain_id, title)
    ).fetchone()
    return row[0] if row else None


def migrate_self_reports_into_knowledge_states(conn, path: Path):
    """Migrate self_report_{domain}_{date}.json answers into knowledge_states."""
    data = json.loads(path.read_text())
    domain_id = data.get('domain_id', '')
    answers = data.get('answers', {})
    if not answers:
        return

    familiarity_map = {
        'new_to_me': ('unknown', 0.0, 0),
        'heard_of': ('mentioned', 0.3, 1),
        'knew_some': ('engaged', 0.6, 2),
        'knew_all': ('anchored', 0.85, 3),
    }

    count = 0
    assessed_at = data.get('assessed_at', '')
    for node_id, answer in answers.items():
        fam = answer.get('familiarity', 'new_to_me')
        knowledge, confidence, layer = familiarity_map.get(fam, ('unknown', 0.0, 0))
        interest = answer.get('interest', 'none')

        conn.execute(
            '''INSERT OR REPLACE INTO knowledge_states
               (domain_id, node_id, knowledge, interest, confidence, highest_layer,
                source_summary, last_assessed)
               VALUES (?,?,?,?,?,?,?,?)''',
            (domain_id, node_id, knowledge, interest, confidence, layer,
             json.dumps(['self_report']), assessed_at)
        )
        count += 1
    log(f'  Self-report → knowledge_states: {count} nodes for {domain_id}')


def main():
    dry_run = '--dry-run' in sys.argv

    if not CURRICULA_DIR.exists():
        log(f'Curricula directory not found: {CURRICULA_DIR}')
        sys.exit(1)

    log(f'Initializing database...')
    init_db()
    conn = get_connection()

    log(f'\n=== Migrating curriculum structures ===')
    for fname in CURRICULUM_STRUCTURE_FILES:
        path = CURRICULA_DIR / fname
        if path.exists():
            migrate_curriculum_structure(conn, path)

    conn.commit()

    log(f'\n=== Migrating knowledge states ===')
    for path in sorted(CURRICULA_DIR.glob('knowledge_*.json')):
        migrate_knowledge_states(conn, path)

    log(f'\n=== Migrating self-reports into knowledge states ===')
    for path in sorted(CURRICULA_DIR.glob('self_report_*.json')):
        migrate_self_reports_into_knowledge_states(conn, path)

    conn.commit()

    log(f'\n=== Migrating book mappings ===')
    for path in sorted(CURRICULA_DIR.glob('mappings_*.json')):
        migrate_book_mappings(conn, path)

    conn.commit()

    log(f'\n=== Migrating retrieval questions ===')
    for path in sorted(CURRICULA_DIR.glob('*_retrieval_questions.json')):
        migrate_retrieval_questions(conn, path)

    log(f'\n=== Migrating ordering questions ===')
    for path in sorted(CURRICULA_DIR.glob('*_ordering_questions.json')):
        migrate_ordering_questions(conn, path)

    conn.commit()

    log(f'\n=== Migrating timeline entries ===')
    for path in sorted(CURRICULA_DIR.glob('*_timeline.json')):
        migrate_timeline(conn, path)

    log(f'\n=== Migrating elicitation sessions ===')
    for path in sorted(CURRICULA_DIR.glob('elicit_*.json')):
        migrate_elicitation_sessions(conn, path)

    log(f'\n=== Migrating cross-curriculum entities ===')
    ent_path = CURRICULA_DIR / 'cross_curriculum_entities.json'
    if ent_path.exists():
        migrate_cross_curriculum_entities(conn, ent_path)
    else:
        log('  No cross_curriculum_entities.json found')

    conn.commit()

    # Print summary
    log(f'\n=== Migration Summary ===')
    for table in ['curriculum_domains', 'curriculum_nodes', 'curriculum_prerequisites',
                  'knowledge_states', 'book_curriculum_mappings', 'retrieval_questions',
                  'timeline_entries', 'elicitation_sessions', 'shared_entities',
                  'entity_curriculum_links', 'review_schedule', 'review_history']:
        count = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
        log(f'  {table}: {count} rows')

    conn.close()
    log(f'\nDone.')


if __name__ == '__main__':
    main()

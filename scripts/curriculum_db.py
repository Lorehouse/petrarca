"""Curriculum system backed by SQLite.

Drop-in replacement for curriculum.py — same public API, but reads/writes
petrarca.db instead of JSON files in data/curricula/.

Imports db.get_connection() for all database access. All functions that
modify state take an optional `conn` parameter; if omitted, they open
and close their own connection.
"""

import hashlib
import json
import math
import os
import random
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

from db import get_connection, init_db

try:
    from gemini_llm import call_llm
except ImportError:
    call_llm = None

# ── LLM helpers (unchanged from curriculum.py) ──────────────────────────────

def _call_opus(prompt: str, max_tokens: int = 32768, timeout: int = 300) -> str | None:
    anthropic_key = os.environ.get('ANTHROPIC_KEY') or os.environ.get('ANTHROPIC_API_KEY')
    if anthropic_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key, timeout=600.0)
            with client.messages.stream(
                model='claude-opus-4-6', max_tokens=max_tokens,
                messages=[{'role': 'user', 'content': prompt}],
            ) as stream:
                return stream.get_final_text()
        except Exception as e:
            print(f'[curriculum] Anthropic SDK failed: {e}', flush=True)
    try:
        cmd = ['claude', '-p', '--tools', '', '--output-format', 'json',
               '--model', 'opus', '--no-session-persistence']
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout)
        if proc.returncode == 0 and proc.stdout.strip():
            resp = json.loads(proc.stdout)
            if not resp.get('is_error'):
                return resp.get('result', '')
    except Exception as e:
        print(f'[curriculum] claude CLI failed: {e}', flush=True)
    return None


# ── ID helpers ───────────────────────────────────────────────────────────────

def make_node_id(domain_id: str, title: str) -> str:
    slug = title.lower().strip()
    slug = ''.join(c if c.isalnum() or c == ' ' else '' for c in slug)
    slug = '_'.join(slug.split()[:6])
    return f"{domain_id[:10]}_{slug}"


def make_domain_id(title: str) -> str:
    slug = title.lower().strip()
    slug = ''.join(c if c.isalnum() or c == ' ' else '' for c in slug)
    slug = '_'.join(slug.split()[:8])
    return slug


# ═════════════════════════════════════════════════════════════════════════════
# CURRICULUM CRUD
# ═════════════════════════════════════════════════════════════════════════════

def load_curriculum(domain_id: str, conn=None) -> dict | None:
    """Load a curriculum by ID. Returns dict with {id, title, description, depth, nodes, ...}."""
    own = conn is None
    if own:
        conn = get_connection(readonly=True)
    try:
        row = conn.execute(
            'SELECT id, title, description, depth, generated_at, generated_by, node_count '
            'FROM curriculum_domains WHERE id = ?', (domain_id,)
        ).fetchone()
        if not row:
            return None

        nodes = conn.execute(
            'SELECT id, title, description, parent_id, level, obscurity, bloom_floor, '
            'knowledge_type, date_start, date_end '
            'FROM curriculum_nodes WHERE domain_id = ? ORDER BY level, title',
            (domain_id,)
        ).fetchall()

        prereqs = conn.execute(
            'SELECT node_id, prerequisite_id, strength '
            'FROM curriculum_prerequisites WHERE domain_id = ?',
            (domain_id,)
        ).fetchall()
        prereq_map: dict[str, list[str]] = {}
        for p in prereqs:
            prereq_map.setdefault(p['node_id'], []).append(p['prerequisite_id'])

        node_list = []
        for n in nodes:
            node_list.append({
                'id': n['id'],
                'title': n['title'],
                'description': n['description'],
                'parent_id': n['parent_id'],
                'level': n['level'],
                'obscurity': n['obscurity'],
                'bloom_floor': n['bloom_floor'],
                'knowledge_type': n['knowledge_type'] or 'core',
                'date_start': n['date_start'],
                'date_end': n['date_end'],
                'prerequisites': prereq_map.get(n['id'], []),
            })

        return {
            'id': row['id'],
            'title': row['title'],
            'description': row['description'],
            'depth': row['depth'],
            'generated_at': row['generated_at'],
            'generated_by': row['generated_by'],
            'node_count': row['node_count'],
            'nodes': node_list,
        }
    finally:
        if own:
            conn.close()


def list_curricula(conn=None) -> list[dict]:
    """List all available curricula (metadata only)."""
    own = conn is None
    if own:
        conn = get_connection(readonly=True)
    try:
        rows = conn.execute(
            'SELECT id, title, depth, node_count, generated_at FROM curriculum_domains ORDER BY title'
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            conn.close()


# ═════════════════════════════════════════════════════════════════════════════
# KNOWLEDGE STATES
# ═════════════════════════════════════════════════════════════════════════════

def load_knowledge_states(domain_id: str, conn=None) -> dict[str, dict]:
    """Load knowledge states for a domain. Returns {node_id: state_dict}."""
    own = conn is None
    if own:
        conn = get_connection(readonly=True)
    try:
        rows = conn.execute(
            'SELECT node_id, knowledge, interest, confidence, highest_layer, '
            'source_summary, last_assessed, last_evidence '
            'FROM knowledge_states WHERE domain_id = ?',
            (domain_id,)
        ).fetchall()
        result = {}
        for r in rows:
            sources = r['source_summary']
            if isinstance(sources, str):
                try:
                    sources = json.loads(sources)
                except (json.JSONDecodeError, TypeError):
                    sources = []
            result[r['node_id']] = {
                'knowledge': r['knowledge'],
                'interest': r['interest'],
                'confidence': r['confidence'],
                'highest_layer': r['highest_layer'],
                'sources': sources,
                'last_assessed': r['last_assessed'],
                'last_evidence': r['last_evidence'],
            }
        return result
    finally:
        if own:
            conn.close()


def update_knowledge(domain_id: str, node_id: str,
                     knowledge: str | None = None,
                     interest: str | None = None,
                     confidence: float | None = None,
                     source: str | None = None,
                     highest_layer: int | None = None,
                     conn=None) -> dict:
    """Update knowledge state for a single node. Creates if not exists."""
    own = conn is None
    if own:
        conn = get_connection()
    try:
        now = datetime.now().isoformat()
        existing = conn.execute(
            'SELECT knowledge, interest, confidence, highest_layer, source_summary '
            'FROM knowledge_states WHERE domain_id = ? AND node_id = ?',
            (domain_id, node_id)
        ).fetchone()

        if existing:
            cur_knowledge = knowledge or existing['knowledge']
            cur_interest = interest or existing['interest']
            cur_confidence = confidence if confidence is not None else existing['confidence']
            cur_layer = highest_layer if highest_layer is not None else existing['highest_layer']
            sources = existing['source_summary']
            if isinstance(sources, str):
                try:
                    sources = json.loads(sources)
                except (json.JSONDecodeError, TypeError):
                    sources = []
            if source and source not in sources:
                sources.append(source)

            conn.execute(
                '''UPDATE knowledge_states
                   SET knowledge=?, interest=?, confidence=?, highest_layer=?,
                       source_summary=?, last_assessed=?, last_evidence=?
                   WHERE domain_id=? AND node_id=?''',
                (cur_knowledge, cur_interest, cur_confidence, cur_layer,
                 json.dumps(sources), now, now, domain_id, node_id)
            )
            state = {'knowledge': cur_knowledge, 'interest': cur_interest,
                     'confidence': cur_confidence, 'highest_layer': cur_layer,
                     'sources': sources, 'last_assessed': now}
        else:
            sources = [source] if source else []
            k = knowledge or 'unknown'
            i = interest or 'none'
            c = confidence if confidence is not None else 0.0
            layer = highest_layer if highest_layer is not None else 0
            conn.execute(
                '''INSERT INTO knowledge_states
                   (domain_id, node_id, knowledge, interest, confidence, highest_layer,
                    source_summary, last_assessed, last_evidence)
                   VALUES (?,?,?,?,?,?,?,?,?)''',
                (domain_id, node_id, k, i, c, layer, json.dumps(sources), now, now)
            )
            state = {'knowledge': k, 'interest': i, 'confidence': c,
                     'highest_layer': layer, 'sources': sources, 'last_assessed': now}

        if own:
            conn.commit()
        return state
    finally:
        if own:
            conn.close()


# ═════════════════════════════════════════════════════════════════════════════
# BOOK MAPPING
# ═════════════════════════════════════════════════════════════════════════════

BOOK_MAPPING_PROMPT = """You are mapping a book's content against a curriculum to determine which topics the book covers.

BOOK:
Title: {title}
Author: {author}
Topics: {topics}
Chapters: {chapters}
Thesis: {thesis}
Key terms: {key_terms}

CURRICULUM NODES (the topics we want to map against):
{curriculum_nodes}

For each curriculum node that this book covers, output a JSON object with:
- "node_title": exact title from the curriculum
- "coverage": "surface" (mentions it briefly), "moderate" (covers it meaningfully), or "deep" (substantial coverage)
- "evidence": Brief explanation of why you think this book covers this topic

Only include nodes the book actually covers — don't guess. If uncertain, use "surface" coverage.

Output as a JSON array. No markdown, just the JSON array."""


def map_book_to_curriculum(book_id: str, domain_id: str, conn=None) -> list[dict] | None:
    """Map a book's content against a curriculum. Returns list of mappings."""
    own = conn is None
    if own:
        conn = get_connection()
    try:
        curriculum = load_curriculum(domain_id, conn=conn)
        if not curriculum:
            return None

        # Load book from DB
        book_row = conn.execute(
            'SELECT id, title, author, topics, chapters, significance FROM physical_books WHERE id = ?',
            (book_id,)
        ).fetchone()
        if not book_row:
            return None

        book_title = book_row['title']
        book_author = book_row['author']
        book_topics = book_row['topics']
        if isinstance(book_topics, str):
            try:
                book_topics = json.loads(book_topics)
            except (json.JSONDecodeError, TypeError):
                book_topics = []
        chapters_raw = book_row['chapters']
        if isinstance(chapters_raw, str):
            try:
                chapters_raw = json.loads(chapters_raw)
            except (json.JSONDecodeError, TypeError):
                chapters_raw = []
        book_significance = book_row['significance'] or 'read'

        # Format curriculum nodes for prompt
        node_lines = []
        title_to_id = {}
        for node in curriculum['nodes']:
            indent = '  ' * (node['level'] - 1)
            node_lines.append(f"{indent}- {node['title']}: {node['description'][:100]}")
            title_to_id[node['title']] = node['id']

        chapters_text = ', '.join(
            f"Ch {ch.get('number', '?')}: {ch.get('title', '?')}"
            for ch in chapters_raw
        ) or 'No chapters available'

        # Look for book research
        from pathlib import Path as _Path
        research_dir = _Path(os.environ.get('BOOK_RESEARCH_DIR',
                                            '/opt/petrarca/scripts/data/book_research'))
        research_path = research_dir / f'{book_id}.json'
        thesis = ''
        key_terms = ''
        if research_path.exists():
            research = json.loads(research_path.read_text())
            thesis = research.get('thesis', '')
            key_terms = ', '.join(t.get('term', '') for t in research.get('key_terms', [])[:20])

        if not call_llm:
            print('[curriculum_db] No LLM available for book mapping', flush=True)
            return None

        prompt = BOOK_MAPPING_PROMPT.format(
            title=book_title, author=book_author,
            topics=', '.join(book_topics), chapters=chapters_text,
            thesis=thesis or 'Not available', key_terms=key_terms or 'Not available',
            curriculum_nodes='\n'.join(node_lines),
        )

        raw = call_llm(prompt, model='gemini-2.5-flash', max_tokens=8192,
                       response_mime_type='application/json')
        if not raw:
            return None

        try:
            mappings_raw = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(mappings_raw, list):
            return None

        # Confidence based on significance × coverage
        confidence_map = {
            ('essential', 'deep'): 0.9, ('essential', 'moderate'): 0.8, ('essential', 'surface'): 0.6,
            ('read', 'deep'): 0.8, ('read', 'moderate'): 0.65, ('read', 'surface'): 0.45,
            ('skimmed', 'deep'): 0.6, ('skimmed', 'moderate'): 0.4, ('skimmed', 'surface'): 0.25,
        }

        mappings = []
        for m in mappings_raw:
            node_title = m.get('node_title', '')
            if node_title not in title_to_id:
                continue
            node_id = title_to_id[node_title]
            coverage = m.get('coverage', 'surface')
            confidence = confidence_map.get((book_significance, coverage), 0.5)

            # Insert mapping
            conn.execute(
                'INSERT OR REPLACE INTO book_curriculum_mappings '
                '(book_id, domain_id, node_id, coverage, inferred_from) VALUES (?,?,?,?,?)',
                (book_id, domain_id, node_id, coverage, 'llm_inference')
            )

            # Update knowledge state
            update_knowledge(domain_id, node_id,
                             knowledge='mentioned', confidence=confidence,
                             source=f'book:{book_id}', conn=conn)

            mappings.append({
                'node_id': node_id, 'node_title': node_title,
                'coverage': coverage, 'confidence': confidence,
            })

        if own:
            conn.commit()
        print(f"Mapped book '{book_title}' → {len(mappings)} curriculum nodes", flush=True)
        return mappings
    finally:
        if own:
            conn.close()


# ═════════════════════════════════════════════════════════════════════════════
# BOOK CURRICULUM CONTEXT (for client)
# ═════════════════════════════════════════════════════════════════════════════

def get_book_curriculum_context(book_id: str, conn=None) -> dict:
    """Get all curriculum context for a book."""
    own = conn is None
    if own:
        conn = get_connection(readonly=True)
    try:
        # Find all domains this book maps to
        domain_rows = conn.execute(
            'SELECT DISTINCT domain_id FROM book_curriculum_mappings WHERE book_id = ?',
            (book_id,)
        ).fetchall()

        domains = []
        for dr in domain_rows:
            domain_id = dr['domain_id']

            # Get domain info
            domain_info = conn.execute(
                'SELECT title, node_count FROM curriculum_domains WHERE id = ?',
                (domain_id,)
            ).fetchone()
            if not domain_info:
                continue

            # Get this book's mappings with node info and knowledge state
            mappings = conn.execute(
                '''SELECT bcm.node_id, cn.title as node_title, bcm.coverage,
                          cn.description, ks.knowledge, ks.interest, ks.confidence
                   FROM book_curriculum_mappings bcm
                   JOIN curriculum_nodes cn ON cn.domain_id = bcm.domain_id AND cn.id = bcm.node_id
                   LEFT JOIN knowledge_states ks ON ks.domain_id = bcm.domain_id AND ks.node_id = bcm.node_id
                   WHERE bcm.book_id = ? AND bcm.domain_id = ?''',
                (book_id, domain_id)
            ).fetchall()

            annotated = [{
                'node_id': m['node_id'], 'node_title': m['node_title'],
                'coverage': m['coverage'], 'description': m['description'] or '',
                'knowledge': m['knowledge'] or 'unknown',
                'interest': m['interest'] or 'none',
                'confidence': m['confidence'] or 0.0,
            } for m in mappings]

            # Cross-book connections: other books mapping to same nodes
            my_node_ids = {m['node_id'] for m in mappings}
            cross_books = []
            if my_node_ids:
                placeholders = ','.join('?' * len(my_node_ids))
                other_mappings = conn.execute(
                    f'''SELECT bcm.node_id, cn.title as node_title, bcm.book_id as other_book_id,
                               bcm.coverage as other_coverage, pb.title as other_book_title
                        FROM book_curriculum_mappings bcm
                        JOIN curriculum_nodes cn ON cn.domain_id = bcm.domain_id AND cn.id = bcm.node_id
                        LEFT JOIN physical_books pb ON pb.id = bcm.book_id
                        WHERE bcm.domain_id = ? AND bcm.book_id != ?
                              AND bcm.node_id IN ({placeholders})''',
                    [domain_id, book_id] + list(my_node_ids)
                ).fetchall()
                cross_books = [{
                    'node_id': om['node_id'], 'node_title': om['node_title'],
                    'other_book_id': om['other_book_id'],
                    'other_book_title': om['other_book_title'] or om['other_book_id'],
                    'other_coverage': om['other_coverage'],
                } for om in other_mappings]

            domains.append({
                'domain_id': domain_id,
                'domain_title': domain_info['title'],
                'node_count': domain_info['node_count'],
                'mappings': annotated,
                'cross_book_connections': cross_books,
            })

        return {'domains': domains}
    finally:
        if own:
            conn.close()


# ═════════════════════════════════════════════════════════════════════════════
# COVERAGE / GAP ANALYSIS
# ═════════════════════════════════════════════════════════════════════════════

def get_coverage_report(domain_id: str, conn=None) -> dict | None:
    """Generate a coverage report for a curriculum domain."""
    own = conn is None
    if own:
        conn = get_connection(readonly=True)
    try:
        curriculum = load_curriculum(domain_id, conn=conn)
        if not curriculum:
            return None
        states = load_knowledge_states(domain_id, conn=conn)
        nodes = curriculum['nodes']

        by_state = {'anchored': [], 'engaged': [], 'mentioned': [], 'unknown': []}
        curious = []
        core_interest = []

        for node in nodes:
            state = states.get(node['id'], {})
            knowledge = state.get('knowledge', 'unknown')
            interest = state.get('interest', 'none')
            summary = {
                'id': node['id'], 'title': node['title'], 'level': node['level'],
                'knowledge': knowledge, 'interest': interest,
                'confidence': state.get('confidence', 0.0),
            }
            by_state.get(knowledge, by_state['unknown']).append(summary)
            if interest == 'curious':
                curious.append(summary)
            elif interest == 'core':
                core_interest.append(summary)

        # Ready to learn: unknown nodes with all prerequisites met
        known_ids = {s['id'] for bucket in ('anchored', 'engaged', 'mentioned') for s in by_state[bucket]}
        ready_to_learn = []
        for node in nodes:
            if states.get(node['id'], {}).get('knowledge', 'unknown') != 'unknown':
                continue
            prereqs = node.get('prerequisites', [])
            if all(p in known_ids for p in prereqs):
                ready_to_learn.append({'id': node['id'], 'title': node['title'], 'level': node['level']})

        total = len(nodes)
        covered = total - len(by_state['unknown'])

        return {
            'domain_id': domain_id, 'title': curriculum['title'],
            'total_nodes': total, 'covered_nodes': covered,
            'coverage_percent': round(100 * covered / total) if total > 0 else 0,
            'by_state': {k: len(v) for k, v in by_state.items()},
            'anchored': by_state['anchored'], 'engaged': by_state['engaged'],
            'mentioned': by_state['mentioned'], 'unknown': by_state['unknown'],
            'curious': curious, 'core_interest': core_interest,
            'ready_to_learn': ready_to_learn[:20],
        }
    finally:
        if own:
            conn.close()


# ═════════════════════════════════════════════════════════════════════════════
# RETRIEVAL QUESTIONS
# ═════════════════════════════════════════════════════════════════════════════

def get_retrieval_questions(domain_id: str, node_id: str | None = None, conn=None) -> list[dict]:
    """Get retrieval questions, optionally filtered by node."""
    own = conn is None
    if own:
        conn = get_connection(readonly=True)
    try:
        if node_id:
            rows = conn.execute(
                'SELECT * FROM retrieval_questions WHERE domain_id = ? AND node_id = ?',
                (domain_id, node_id)
            ).fetchall()
        else:
            rows = conn.execute(
                'SELECT * FROM retrieval_questions WHERE domain_id = ?',
                (domain_id,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            conn.close()


def get_timeline(domain_id: str, conn=None) -> list[dict]:
    """Get timeline entries for a domain, sorted chronologically."""
    own = conn is None
    if own:
        conn = get_connection(readonly=True)
    try:
        rows = conn.execute(
            'SELECT year, label, detail, node_id FROM timeline_entries '
            'WHERE domain_id = ? ORDER BY year',
            (domain_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own:
            conn.close()


# ═════════════════════════════════════════════════════════════════════════════
# REVIEW SESSION (replaces JSON-based resurfacing review)
# ═════════════════════════════════════════════════════════════════════════════

REVIEW_INTERVALS = [1, 3, 7, 14, 30, 60, 120]
QUESTIONS_PER_SESSION = 8
ORDERING_PER_SESSION = 2


def _load_entity_index(conn) -> list[dict]:
    """Load all entities with their names and aliases for text matching."""
    rows = conn.execute(
        'SELECT entity_id, name, entity_type, aliases FROM shared_entities'
    ).fetchall()
    index = []
    for r in rows:
        names = [r['name']]
        try:
            aliases = json.loads(r['aliases'] or '[]')
            if isinstance(aliases, list):
                names.extend(aliases)
        except (json.JSONDecodeError, TypeError):
            pass
        index.append({
            'entity_id': r['entity_id'],
            'name': r['name'],
            'entity_type': r['entity_type'],
            'match_names': names,
        })
    # Sort by longest name first so "Battle of Himera" matches before "Himera"
    index.sort(key=lambda e: max(len(n) for n in e['match_names']), reverse=True)
    return index


def annotate_entity_spans(text: str, entity_index: list[dict]) -> list[dict]:
    """Find entity name mentions in text and return span annotations.

    Returns list of {start, end, entity_id, entity_type, name} dicts,
    non-overlapping, sorted by position.
    """
    if not text or not entity_index:
        return []

    spans = []
    taken = set()  # character positions already claimed

    for entity in entity_index:
        for match_name in entity['match_names']:
            # Case-insensitive search for whole-word matches
            pattern = r'\b' + re.escape(match_name) + r'\b'
            for m in re.finditer(pattern, text, re.IGNORECASE):
                start, end = m.start(), m.end()
                # Skip if overlaps with already-claimed span
                if any(pos in taken for pos in range(start, end)):
                    continue
                spans.append({
                    'start': start,
                    'end': end,
                    'entity_id': entity['entity_id'],
                    'entity_type': entity['entity_type'],
                    'name': entity['name'],
                })
                taken.update(range(start, end))

    spans.sort(key=lambda s: s['start'])
    return spans


def _annotate_item_entities(item: dict, entity_index: list[dict]) -> dict:
    """Add entity_spans to a review session item."""
    if not entity_index:
        return item
    # Annotate rich_answer, memory_hook, and question
    all_spans = {}
    for field in ('rich_answer', 'memory_hook', 'question'):
        text = item.get(field)
        if text and isinstance(text, str):
            spans = annotate_entity_spans(text, entity_index)
            if spans:
                all_spans[field] = spans
    if all_spans:
        item['entity_spans'] = all_spans
    return item


def generate_review_session(domain_filter: str | None = None, conn=None) -> dict:
    """Generate a curriculum retrieval practice session from the database."""
    own = conn is None
    if own:
        conn = get_connection()
    try:
        now_ms = int(time.time() * 1000)

        # Query questions with their scheduling state
        domain_clause = "AND rq.domain_id LIKE ?" if domain_filter else ""
        params = [f'%{domain_filter}%'] if domain_filter else []

        rows = conn.execute(
            f'''SELECT rq.id, rq.domain_id, rq.node_id, rq.question, rq.answer,
                       rq.question_type, rq.node_title, rq.cluster_label,
                       rq.answer_type, rq.level, rq.anchors, rq.memory_hook,
                       rq.grading_options, rq.rich_answer,
                       rs.review_count, rs.last_result, rs.due_at, rs.last_reviewed_at,
                       COALESCE(ks.knowledge, 'unknown') as node_knowledge,
                       COALESCE(ks.confidence, 0) as node_confidence
                FROM retrieval_questions rq
                LEFT JOIN review_schedule rs ON rq.id = rs.question_id
                LEFT JOIN knowledge_states ks ON ks.domain_id = rq.domain_id AND ks.node_id = rq.node_id
                WHERE 1=1 {domain_clause}
                ORDER BY
                    CASE WHEN rs.review_count IS NULL OR rs.review_count = 0 THEN 0 ELSE 1 END,
                    CASE WHEN rs.last_result = 'wrong' THEN 0 ELSE 1 END,
                    COALESCE(rs.due_at, 0) ASC''',
            params
        ).fetchall()

        # Filter to due or new questions
        # Prioritize questions about nodes you've actually studied
        candidates = []
        for r in rows:
            review_count = r['review_count'] or 0
            due_at = r['due_at'] or 0
            node_knowledge = r['node_knowledge']

            # Skip questions about topics the user hasn't encountered yet
            # (they can't retrieve what they never learned)
            if node_knowledge == 'unknown' and r['question_type'] != 'temporal_ordering':
                continue

            # Knowledge-weighted base score: studied nodes are more valuable to review
            knowledge_weight = {
                'anchored': 8.0, 'engaged': 6.0, 'mentioned': 4.0, 'unknown': 1.0
            }.get(node_knowledge, 2.0)

            if review_count == 0:
                # Never reviewed — high priority, weighted by knowledge
                candidates.append((knowledge_weight + 2.0 + random.random(), dict(r)))
            elif due_at <= now_ms:
                # Due for review
                overdue_days = (now_ms - due_at) / (24 * 3600 * 1000)
                score = knowledge_weight + min(overdue_days * 0.3, 5.0)
                if r['last_result'] == 'wrong':
                    score += 3.0
                candidates.append((score, dict(r)))
            # else: not due yet, skip

        # Split by type
        retrieval = [(s, q) for s, q in candidates if q['question_type'] != 'temporal_ordering']
        ordering = [(s, q) for s, q in candidates if q['question_type'] == 'temporal_ordering']

        # Sort and select
        retrieval.sort(key=lambda x: x[0], reverse=True)
        ordering.sort(key=lambda x: x[0], reverse=True)

        selected_retrieval = [q for _, q in retrieval[:QUESTIONS_PER_SESSION]]
        selected_ordering = [q for _, q in ordering[:ORDERING_PER_SESSION]]

        # Build response items
        def _parse_json_field(val, default=None):
            if val is None:
                return default or []
            if isinstance(val, (list, dict)):
                return val
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return default or []

        items = []
        for q in selected_retrieval:
            items.append({
                'type': 'retrieval',
                'question_id': q['id'],
                'question': q['question'],
                'answer': q['answer'],
                'rich_answer': q.get('rich_answer') or q['answer'],
                'question_type': q['question_type'],
                'answer_type': q.get('answer_type') or 'concept',
                'node_title': q['node_title'],
                'domain': q['domain_id'],
                'memory_hook': q.get('memory_hook'),
                'anchors': _parse_json_field(q.get('anchors'), []),
                'grading_options': _parse_json_field(q.get('grading_options'), []),
            })
        for q in selected_ordering:
            items.append({
                'type': 'temporal_ordering',
                'question_id': q['id'],
                'question': q['question'],
                'answer': q['answer'],
                'rich_answer': q.get('rich_answer') or q['answer'],
                'answer_type': 'sequence',
                'cluster_label': q['cluster_label'],
                'domain': q['domain_id'],
                'memory_hook': q.get('memory_hook'),
                'anchors': _parse_json_field(q.get('anchors'), []),
                'grading_options': _parse_json_field(q.get('grading_options'), []),
            })
        # Annotate items with entity spans for tappable entities in frontend
        entity_index = _load_entity_index(conn)
        if entity_index:
            items = [_annotate_item_entities(item, entity_index) for item in items]

        random.shuffle(items)

        count_domain_clause = "AND domain_id LIKE ?" if domain_filter else ""
        total_questions = conn.execute(
            f"SELECT COUNT(*) FROM retrieval_questions WHERE 1=1 {count_domain_clause}", params
        ).fetchone()[0]

        return {
            'id': f'cr_{int(time.time())}',
            'items': items,
            'generated_at': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            'domain': domain_filter or 'all',
            'retrieval_count': len(selected_retrieval),
            'ordering_count': len(selected_ordering),
            'total_questions_in_pool': total_questions,
        }
    finally:
        if own:
            conn.close()


def record_review_result(question_id: str, result: str, session_id: str | None = None,
                         conn=None):
    """Record the result of answering a review question. Updates schedule + knowledge state."""
    own = conn is None
    if own:
        conn = get_connection()
    try:
        now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        now_ms = int(time.time() * 1000)

        # Insert into history
        conn.execute(
            'INSERT INTO review_history (question_id, result, reviewed_at, session_id) VALUES (?,?,?,?)',
            (question_id, result, now, session_id)
        )

        # Upsert schedule
        existing = conn.execute(
            'SELECT review_count, stability_days FROM review_schedule WHERE question_id = ?',
            (question_id,)
        ).fetchone()

        if existing:
            count = existing['review_count']
            stability = existing['stability_days']
            # Map graded results to scheduling categories
            is_strong = result in ('correct', 'exact_year', 'all_correct')
            is_partial = result in ('partial', 'right_decade', 'mostly_right')
            is_weak = result in ('right_century',)
            # is_fail = result in ('wrong', 'missed')

            if is_strong:
                new_count = count + 1
                new_stability = min(stability * 2.0, 365)
            elif is_partial:
                new_count = count + 1
                new_stability = stability * 1.3
            elif is_weak:
                # Knows something but fuzzy — short interval to reinforce
                new_count = count
                new_stability = max(1.0, stability * 0.7)
            else:  # wrong/missed
                new_count = max(1, count - 1)
                new_stability = max(1.0, stability * 0.4)

            due_at = now_ms + int(new_stability * 24 * 3600 * 1000)
            conn.execute(
                '''UPDATE review_schedule
                   SET review_count=?, last_reviewed_at=?, last_result=?,
                       stability_days=?, due_at=?
                   WHERE question_id=?''',
                (new_count, now_ms, result, new_stability, due_at, question_id)
            )
        else:
            is_strong = result in ('correct', 'exact_year', 'all_correct')
            is_fail = result in ('wrong', 'missed')
            stability = 1.0 if is_fail else (3.0 if is_strong else 1.5)
            due_at = now_ms + int(stability * 24 * 3600 * 1000)
            conn.execute(
                '''INSERT INTO review_schedule
                   (question_id, review_count, last_reviewed_at, last_result, stability_days, due_at)
                   VALUES (?,?,?,?,?,?)''',
                (question_id, 1, now_ms, result, stability, due_at)
            )

        # Update knowledge state for the node this question tests
        q_row = conn.execute(
            'SELECT domain_id, node_id FROM retrieval_questions WHERE id = ?',
            (question_id,)
        ).fetchone()
        if q_row and q_row['node_id']:
            # Graded confidence adjustments — date questions have finer granularity
            confidence_delta = {
                'correct': 0.05, 'exact_year': 0.08, 'all_correct': 0.06,
                'partial': 0.0, 'right_decade': 0.02, 'mostly_right': 0.02,
                'right_century': -0.02,
                'wrong': -0.1, 'missed': -0.1,
            }.get(result, 0)
            ks = conn.execute(
                'SELECT confidence FROM knowledge_states WHERE domain_id=? AND node_id=?',
                (q_row['domain_id'], q_row['node_id'])
            ).fetchone()
            if ks:
                new_conf = max(0.0, min(1.0, (ks['confidence'] or 0) + confidence_delta))
                conn.execute(
                    'UPDATE knowledge_states SET confidence=?, last_evidence=? WHERE domain_id=? AND node_id=?',
                    (new_conf, now, q_row['domain_id'], q_row['node_id'])
                )

        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def get_review_status(conn=None) -> dict:
    """Get curriculum review stats."""
    own = conn is None
    if own:
        conn = get_connection(readonly=True)
    try:
        total_q = conn.execute('SELECT COUNT(*) FROM retrieval_questions').fetchone()[0]
        reviewed = conn.execute(
            'SELECT COUNT(*) FROM review_schedule WHERE review_count > 0'
        ).fetchone()[0]
        correct = conn.execute(
            "SELECT COUNT(*) FROM review_schedule WHERE last_result = 'correct'"
        ).fetchone()[0]
        wrong = conn.execute(
            "SELECT COUNT(*) FROM review_schedule WHERE last_result = 'wrong'"
        ).fetchone()[0]
        total_reviews = conn.execute('SELECT COUNT(*) FROM review_history').fetchone()[0]

        domains = conn.execute(
            'SELECT DISTINCT domain_id FROM retrieval_questions'
        ).fetchall()

        return {
            'total_retrieval_questions': total_q,
            'reviewed_at_least_once': reviewed,
            'last_correct': correct,
            'last_wrong': wrong,
            'total_reviews': total_reviews,
            'domains': [d['domain_id'] for d in domains],
        }
    finally:
        if own:
            conn.close()


# ═════════════════════════════════════════════════════════════════════════════
# ASSESSMENT IMPORT (self-report / 20Q)
# ═════════════════════════════════════════════════════════════════════════════

FAMILIARITY_TO_KNOWLEDGE = {
    'unknown': ('unknown', 0.0, 0),
    'heard_of': ('mentioned', 0.4, 1),
    'know_basics': ('engaged', 0.6, 2),
    'could_explain': ('anchored', 0.8, 2),
    'know_deeply': ('anchored', 0.95, 3),
    'new_to_me': ('unknown', 0.0, 0),
    'knew_some': ('engaged', 0.6, 2),
    'knew_all': ('anchored', 0.9, 3),
}

INTEREST_TO_CANONICAL = {
    'core': 'core', 'curious': 'curious', 'none': 'none',
    'interested': 'curious', 'star': 'core', 'skip': 'none',
}


def import_assessment_answers(domain_id: str, answers: dict, conn=None) -> dict:
    """Import assessment answers into knowledge states.

    answers: {node_id: {familiarity, interest, ...}}
    """
    own = conn is None
    if own:
        conn = get_connection()
    try:
        imported = 0
        by_level = {}
        for node_id, answer in answers.items():
            fam = answer.get('familiarity', 'unknown')
            interest_raw = answer.get('interest', 'none')
            knowledge, confidence, layer = FAMILIARITY_TO_KNOWLEDGE.get(fam, ('unknown', 0.0, 0))
            interest = INTEREST_TO_CANONICAL.get(interest_raw, 'curious')
            update_knowledge(domain_id, node_id, knowledge=knowledge,
                             interest=interest, confidence=confidence,
                             source='self_report', highest_layer=layer, conn=conn)
            imported += 1
            by_level[knowledge] = by_level.get(knowledge, 0) + 1
        if own:
            conn.commit()
        return {'imported': imported, 'total': len(answers), 'by_level': by_level}
    finally:
        if own:
            conn.close()

#!/usr/bin/env python3
"""
Knowledge Review Engine — spaced retrieval practice from book chapters.

Manages a review_items table with simplified FSRS scheduling, maps book
chapters to curriculum nodes via LLM, and generates personalized
retrieval questions at review time using current knowledge state.
"""

import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path

from gemini_llm import call_llm
from curriculum import (
    load_curriculum, load_knowledge_states, update_knowledge,
)

DATA_DIR = Path(os.environ.get('PETRARCA_DATA', '/opt/petrarca/data'))
SCRIPT_DIR = Path(__file__).parent
BOOK_RESEARCH_DIR = SCRIPT_DIR / 'data' / 'book_research'

# ── FSRS (simplified) ─────────────────────────────────────────────────────────

STABILITY_MULTIPLIERS = {'knew': 2.5, 'partly': 1.5}
INITIAL_STABILITY_DAYS = 1.0
MAX_STABILITY_DAYS = 365.0

SCORE_TO_KNOWLEDGE = {
    'knew':   ('anchored', 0.85),
    'partly': ('engaged',  0.55),
    'missed': ('unknown',  0.1),
}

# ── Curriculum auto-detection ─────────────────────────────────────────────────

def detect_curriculum(book_title: str, book_topics: list) -> str:
    """Find the best-matching curriculum for a book using embedding similarity.

    Embeds the book's title + topics and compares against the title + description
    of every available curriculum. Falls back to Sicily if nothing scores above 0.35.
    Returns the single best-matching domain_id.
    """
    from curriculum import list_curricula, load_curriculum
    curricula = list_curricula()
    if not curricula:
        return 'sicily_history_culture_and_legacy'

    book_text = f"{book_title}. Topics: {', '.join(book_topics)}"

    try:
        from limbic.amygdala import EmbeddingModel
        model = EmbeddingModel()
        book_vec = model.embed([book_text])[0]

        best_id, best_score = curricula[0]['id'], -1.0
        for meta in curricula:
            c = load_curriculum(meta['id'])
            if not c:
                continue
            c_text = f"{c.get('title', '')}. {c.get('description', '')} {' '.join(n['title'] for n in c.get('nodes', [])[:10])}"
            c_vec = model.embed([c_text])[0]
            import numpy as np
            score = float(np.dot(book_vec, c_vec) / (np.linalg.norm(book_vec) * np.linalg.norm(c_vec) + 1e-9))
            if score > best_score:
                best_score, best_id = score, meta['id']

        if best_score >= 0.35:
            return best_id
    except Exception:
        pass

    # Keyword fallback
    text = ' '.join([book_title] + book_topics).lower()
    keyword_map = {
        'sicily_history_culture_and_legacy': ['sicily', 'sicilian', 'syracuse', 'palermo'],
        'ancient_greece_800300_bc_political_military_cultural_and': ['greece', 'greek', 'athens', 'sparta'],
        'roman_republic_and_empire': ['rome', 'roman', 'caesar', 'republic'],
        'byzantine': ['byzantine', 'byzantium', 'constantinople', 'justinian', 'belisarius'],
        'islamic': ['islamic', 'islam', 'arab', 'caliphate', 'muslim', 'ottoman'],
    }
    for domain_id, keywords in keyword_map.items():
        if any(kw in text for kw in keywords):
            # Check if a curriculum with this prefix actually exists
            for meta in curricula:
                if meta['id'].startswith(domain_id) or meta['id'] == domain_id:
                    return meta['id']

    return curricula[0]['id']  # default to first available


def suggest_curricula_for_book(book_title: str, book_topics: list) -> list[dict]:
    """Return curricula sorted by relevance to a book, with scores.

    Used to suggest which curriculum(a) to map a new book against,
    and to surface gaps where no curriculum exists yet.
    """
    from curriculum import list_curricula, load_curriculum
    curricula = list_curricula()
    if not curricula:
        return []

    book_text = f"{book_title}. Topics: {', '.join(book_topics)}"
    results = []

    try:
        from limbic.amygdala import EmbeddingModel
        import numpy as np
        model = EmbeddingModel()
        book_vec = model.embed([book_text])[0]

        for meta in curricula:
            c = load_curriculum(meta['id'])
            if not c:
                continue
            c_text = f"{c.get('title', '')}. {' '.join(n['title'] for n in c.get('nodes', [])[:15])}"
            c_vec = model.embed([c_text])[0]
            score = float(np.dot(book_vec, c_vec) / (np.linalg.norm(book_vec) * np.linalg.norm(c_vec) + 1e-9))
            results.append({'id': meta['id'], 'title': meta['title'], 'score': round(score, 3)})

        results.sort(key=lambda x: -x['score'])
    except Exception:
        results = [{'id': m['id'], 'title': m['title'], 'score': 0.0} for m in curricula]

    return results


# ── LLM helpers ───────────────────────────────────────────────────────────────

def _call_claude(prompt: str, timeout: int = 120) -> str | None:
    try:
        r = subprocess.run(['claude', '-p', prompt], capture_output=True, text=True, timeout=timeout)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def _parse_json(text: str) -> dict | list | None:
    cleaned = text.strip()
    if cleaned.startswith('```'):
        cleaned = re.sub(r'^```(?:json)?\n?', '', cleaned)
        cleaned = re.sub(r'\n?```$', '', cleaned)
    for pattern in [r'\[[\s\S]*\]', r'\{[\s\S]*\}']:
        m = re.search(pattern, cleaned)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


# ── Topological ordering ──────────────────────────────────────────────────────

def compute_node_depths(curriculum: dict) -> dict:
    nodes = {n['id']: n for n in curriculum['nodes']}
    depths = {}

    def depth(nid, visited=None):
        if visited is None:
            visited = set()
        if nid in depths:
            return depths[nid]
        if nid in visited:
            return 0
        visited.add(nid)
        prereqs = nodes.get(nid, {}).get('prerequisites', [])
        depths[nid] = (1 + max((depth(p, visited) for p in prereqs), default=-1)) if prereqs else 0
        return depths[nid]

    for nid in nodes:
        depth(nid)
    return depths


def get_dependent_node_ids(target_id: str, curriculum: dict) -> list:
    return [n['id'] for n in curriculum['nodes'] if target_id in n.get('prerequisites', [])]


# ── Prompts ───────────────────────────────────────────────────────────────────

MAP_CHAPTER_PROMPT = """Map a book chapter to curriculum nodes for a knowledge review system.

Book: {book_title}
Chapter {chapter_number}: {chapter_title}
Context:
{chapter_context}

Curriculum nodes ({curriculum_title}) — level 2-3 only:
{nodes_list}

Which 3-6 nodes does this chapter directly cover (not just passing mentions)?

For each matched node:
- "node_id": exact ID from the list
- "node_title": node title
- "source_text": 1-2 sentences of SPECIFIC FACTS from the chapter — exact names, dates, events, numbers. Do NOT write abstract summaries like "the chapter discusses the importance of X" — instead write "Gelon defeated the Carthaginians at Himera in 480 BC" or "Syracuse fell to the Arabs in 878 AD after a 75-year siege". If the chapter is thin on specifics, name the most concrete nouns it mentions.
- "lens": best retrieval lens — CAUSAL | COMPARATIVE | SIGNIFICANCE | TEMPORAL | PATTERN | CONSEQUENCE
- "temporal_hook": optional 1-sentence cross-period anchor (e.g. "Simultaneous with Rome's Second Punic War")

Output JSON array only:
[{{"node_id":"...","node_title":"...","source_text":"...","lens":"...","temporal_hook":"..."}}]"""


QUESTION_GEN_PROMPT_FACTUAL = """Generate a concept-check question for a knowledge review.

This is FIRST ENCOUNTER with this concept. The goal is NOT to test a specific fact — it is to check
whether the learner can explain what this node represents in history: what happened, who was involved,
why it mattered, or what characterized this period/event/person.

Concept: {node_title}
Curriculum definition: {node_description}

The curriculum definition IS the answer. Write a question whose correct answer IS the substance of that definition.
The question should be answerable by someone who read and understood the definition — not by someone who memorized a name or date.

Step 1 — identify the CORE CONCEPT the definition conveys:
- What was the central dynamic or conflict?
- What characterized this period/event/figure?
- What caused or resulted from this?
- What makes this significant or distinctive in Sicilian history?

Step 2 — write a SHORT question (6-12 words) that asks for that core concept.
Start with: What / Why / How / Who was / What characterized / What drove / What resulted

Good questions (test understanding of the concept):
- "What drove Greek colonization of Sicily?" → tests the Why-they-came concept
- "What was the central military conflict of Sicilian history for 300 years?" → tests Greeks-vs-Carthage
- "Why did Sicilian Greek cities produce more tyrants than mainland Greece?" → tests the Age of Tyrants insight
- "What made the Norman kingdom of Sicily culturally distinctive?" → tests Arab-Norman synthesis
- "What happened to Syracuse in 212 BC and why does it matter?" → tests Siege of Syracuse

Bad questions (test isolated facts the curriculum doesn't emphasize):
- "Which city founded Naxos?" → a minor detail, not the concept
- "What year did Belisarius arrive?" → a date, not the concept
- "Who was the leader of the Carthaginian army?" → a name, not the concept

The answer_guidance should be 2-3 sentences drawn from the curriculum definition — what a good answer should cover.

{temporal_context}

Output JSON only:
{{"question":"...","answer_guidance":"2-3 sentences from the curriculum definition covering what a good answer should include","temporal_hook":"...","curriculum_context":"brief placement in the larger history"}}"""


QUESTION_GEN_PROMPT = """Generate an analytical review question.

Concept: {node_title}
Curriculum definition: {node_description}
Review #{review_count}

{difficulty_instruction}

{known_nodes_context}
{temporal_context}

The learner already understands what this concept IS. Now push deeper with the {lens} lens.
The question should connect, compare, or explain — not test an isolated name or date.

Lens options:
- CAUSAL: What caused this? What sequence of events led here?
- COMPARATIVE: How does this compare to another period or polity the learner knows?
- SIGNIFICANCE: What did this change? Why does it matter for what came next?
- TEMPORAL: What else was happening simultaneously? What's the chronological anchor?
- PATTERN: What recurring dynamic does this exemplify across Sicilian/Mediterranean history?
- CONSEQUENCE: What long-term effects did this produce?

Keep question under 20 words.

Output JSON only:
{{"question":"...","answer_guidance":"2-3 sentences on what a good answer covers","temporal_hook":"...","curriculum_context":"..."}}"""


EXPLORE_PROMPT = """A learner reviewed this concept and wants to explore further.

Concept: {node_title}
Source: {source_text}
Their score: {score}

Generate 3 research questions to deepen understanding. Vary lenses:
1. Causal depth (why/how)
2. Comparative (relation to other periods/places)
3. Significance (consequences or modern relevance)

Output JSON:
[{{"question":"...","lens":"...","suggested_source":"brief hint where to find the answer"}}]"""


VOICE_EXTRACT_PROMPT = """Extract signals from a learner's voice memo during knowledge review.

Concept being reviewed: {node_title}
Transcript: {transcript}

Extract:
1. What they seem to remember correctly
2. Questions or uncertainties they expressed
3. Connections to other topics they noticed
4. Their apparent confidence level

Output JSON:
{{"remembered":"...","questions":["..."],"connections":["..."],"suggested_score":"knew|partly|missed"}}"""


# ── Chapter mapping ───────────────────────────────────────────────────────────

def _get_chapter_context(book_id: str, chapter_number: int, chapter_title: str) -> str:
    path = BOOK_RESEARCH_DIR / f'{book_id}.json'
    if not path.exists():
        return f'Chapter: {chapter_title}'
    try:
        research = json.loads(path.read_text())
        ch = research.get('chapter_research', {}).get(str(chapter_number), {})
        parts = []
        if ch.get('summary'):
            parts.append(f"Summary: {ch['summary']}")
        if ch.get('claims'):
            parts.append('Claims:\n' + '\n'.join(f'- {c}' for c in ch['claims']))
        return '\n'.join(parts) or f'Chapter: {chapter_title}'
    except Exception:
        return f'Chapter: {chapter_title}'


def map_chapter_to_nodes(book_id: str, book_title: str, book_topics: list,
                          chapter_number: int, chapter_title: str) -> list:
    domain_id = detect_curriculum(book_title, book_topics)
    curriculum = load_curriculum(domain_id)
    if not curriculum:
        return []

    node_lines = [
        f"- {n['id']}: {n['title']} — {n['description'][:120]}..."
        for n in curriculum['nodes'] if n.get('level', 1) >= 2
    ]

    chapter_context = _get_chapter_context(book_id, chapter_number, chapter_title)

    curriculum_title = curriculum.get('title', curriculum.get('name', domain_id.replace('_', ' ').title()))

    prompt = MAP_CHAPTER_PROMPT.format(
        book_title=book_title,
        chapter_number=chapter_number,
        chapter_title=chapter_title,
        chapter_context=chapter_context,
        nodes_list='\n'.join(node_lines),
        curriculum_title=curriculum_title,
    )

    raw = call_llm(prompt, max_tokens=65536,
                   response_mime_type='application/json')
    if not raw:
        return []

    mappings = _parse_json(raw)
    valid_ids = {n['id'] for n in curriculum['nodes']}
    return [m for m in (mappings or []) if isinstance(m, dict) and m.get('node_id') in valid_ids]


def fill_prerequisite_gaps(domain_id: str, mapped_node_ids: list, conn, now: int) -> int:
    """Create lightweight knowledge_items for prerequisites and same-period siblings.

    Only creates items for Level 2+ nodes that don't already exist in knowledge_items.
    Uses the curriculum node description as the sole source (book_id=None).
    Returns count of gap-fill items created.
    """
    curriculum = load_curriculum(domain_id)
    if not curriculum:
        return 0

    nodes_by_id = {n['id']: n for n in curriculum['nodes']}
    gaps_created = 0

    candidate_ids: set = set()

    for node_id in mapped_node_ids:
        node = nodes_by_id.get(node_id, {})
        # Prerequisites of mapped nodes
        for prereq_id in node.get('prerequisites', []):
            prereq = nodes_by_id.get(prereq_id, {})
            if prereq.get('level', 1) >= 2:
                candidate_ids.add(prereq_id)
        # Siblings: same parent, same rough time period (within 200 years)
        parent_id = node.get('parent_id')
        node_start = node.get('date_start')
        if parent_id and node_start is not None:
            for sibling in curriculum['nodes']:
                if (sibling.get('parent_id') == parent_id
                        and sibling['id'] != node_id
                        and sibling.get('level', 1) >= 2):
                    sib_start = sibling.get('date_start')
                    if sib_start is not None and abs(sib_start - node_start) <= 200:
                        candidate_ids.add(sibling['id'])

    for cand_id in candidate_ids:
        if cand_id in mapped_node_ids:
            continue
        item_id = f"{domain_id}:{cand_id}"
        existing = conn.execute(
            'SELECT id FROM knowledge_items WHERE id=?', (item_id,)
        ).fetchone()
        if existing:
            continue

        node = nodes_by_id.get(cand_id, {})
        source = {
            'book_id': None,
            'chapter_number': None,
            'chapter_title': 'Curriculum context — not yet in a book',
            'source_text': node.get('description', '')[:400],
            'lens': 'SIGNIFICANCE',
            'temporal_hook': '',
            'added_at': now,
        }
        try:
            conn.execute('''
                INSERT INTO knowledge_items
                (id, curriculum_node_id, curriculum_domain, stability_days, due_at,
                 sources, question_history, created_at)
                VALUES (?,?,?,?,?,?,?,?)
            ''', (
                item_id, cand_id, domain_id,
                INITIAL_STABILITY_DAYS, now,
                json.dumps([source]), '[]', now,
            ))
            gaps_created += 1
        except Exception as e:
            print(f'[review] gap-fill skip {item_id}: {e}', flush=True)

    return gaps_created


def create_review_items_for_chapter(book_id: str, book_title: str, book_topics: list,
                                     chapter_number: int, chapter_title: str, conn) -> dict:
    """Map chapter to curriculum nodes and upsert into knowledge_items. Returns summary."""
    mappings = map_chapter_to_nodes(book_id, book_title, book_topics, chapter_number, chapter_title)
    domain_id = detect_curriculum(book_title, book_topics)
    if not mappings:
        return {'nodes_covered': [], 'items_created': 0, 'items_updated': 0,
                'gaps_filled': 0, 'domain': domain_id}

    now = int(time.time() * 1000)
    created = 0
    updated = 0
    node_titles = []
    mapped_node_ids = []

    for m in mappings:
        item_id = f"{domain_id}:{m['node_id']}"
        mapped_node_ids.append(m['node_id'])

        new_source = {
            'book_id': book_id,
            'chapter_number': chapter_number,
            'chapter_title': chapter_title,
            'source_text': m.get('source_text', ''),
            'lens': m.get('lens', 'SIGNIFICANCE'),
            'temporal_hook': m.get('temporal_hook', ''),
            'added_at': now,
        }

        existing = conn.execute(
            'SELECT id, sources FROM knowledge_items WHERE id=?', (item_id,)
        ).fetchone()

        if existing:
            # Merge new source into existing sources array (skip if same book+chapter already there)
            try:
                sources = json.loads(existing['sources'] or '[]')
            except Exception:
                sources = []
            already = any(
                s.get('book_id') == book_id and s.get('chapter_number') == chapter_number
                for s in sources
            )
            if not already:
                sources.append(new_source)
                conn.execute(
                    'UPDATE knowledge_items SET sources=?, cached_question=NULL WHERE id=?',
                    (json.dumps(sources), item_id)
                )
                updated += 1
        else:
            conn.execute('''
                INSERT INTO knowledge_items
                (id, curriculum_node_id, curriculum_domain, stability_days, due_at,
                 sources, question_history, created_at)
                VALUES (?,?,?,?,?,?,?,?)
            ''', (
                item_id, m['node_id'], domain_id,
                INITIAL_STABILITY_DAYS, now,
                json.dumps([new_source]), '[]', now,
            ))
            created += 1

        node_titles.append(m.get('node_title', m['node_id']))

    gaps_filled = fill_prerequisite_gaps(domain_id, mapped_node_ids, conn, now)
    conn.commit()
    print(f'[review] Ch{chapter_number} mapped: {created} created, {updated} updated, '
          f'{gaps_filled} gaps → {node_titles}', flush=True)

    # Pre-generate questions in background for items with no cached_question
    items_needing_questions = conn.execute(
        '''SELECT id FROM knowledge_items
           WHERE curriculum_domain=? AND cached_question IS NULL
             AND id IN ({})'''.format(','.join('?' * len(mapped_node_ids))),
        [domain_id] + [f"{domain_id}:{nid}" for nid in mapped_node_ids]
    ).fetchall()
    if items_needing_questions:
        ids_to_gen = [r['id'] for r in items_needing_questions]
        def _pregen():
            from db import get_connection as _conn
            c = _conn()
            for iid in ids_to_gen:
                try:
                    q = generate_question(iid, c)
                    c.execute('UPDATE knowledge_items SET cached_question=? WHERE id=?',
                              (json.dumps(q), iid))
                    c.commit()
                except Exception as e:
                    print(f'[review] pre-gen failed {iid}: {e}', flush=True)
            c.close()
            print(f'[review] pre-generated {len(ids_to_gen)} questions for ch{chapter_number}', flush=True)
        threading.Thread(target=_pregen, daemon=True).start()

    return {
        'nodes_covered': node_titles,
        'items_created': created,
        'items_updated': updated,
        'gaps_filled': gaps_filled,
        'domain': domain_id,
    }


# ── Review queue ──────────────────────────────────────────────────────────────

def _knowledge_item_to_queue_row(ki: dict, curriculum_cache: dict) -> dict:
    """Convert a knowledge_items row to the ReviewItem shape the client expects."""
    domain = ki.get('curriculum_domain', '')
    curriculum = curriculum_cache.get(domain)
    node_id = ki.get('curriculum_node_id', '')

    # Resolve node title from curriculum
    node_title = ''
    if curriculum:
        node = next((n for n in curriculum.get('nodes', []) if n['id'] == node_id), None)
        node_title = node['title'] if node else node_id

    # Pick best source: most recently added (last in array), falling back to first
    try:
        sources = json.loads(ki.get('sources') or '[]')
    except Exception:
        sources = []

    # Determine item_type: gap_fill if all sources have book_id=None, else book_chapter
    item_type = 'gap_fill' if sources and all(s.get('book_id') is None for s in sources) else 'book_chapter'

    # Best source for display: prefer a real book source; within those, most recently added
    book_sources = [s for s in sources if s.get('book_id') is not None]
    best = book_sources[-1] if book_sources else (sources[-1] if sources else {})

    return {
        'id': ki['id'],
        'item_type': item_type,
        'curriculum_domain': domain,
        'curriculum_node_id': node_id,
        'curriculum_node_title': node_title,
        'source_book_id': best.get('book_id'),
        'source_chapter_number': best.get('chapter_number'),
        'source_chapter_title': best.get('chapter_title', ''),
        'source_text': best.get('source_text', ''),
        'lens': best.get('lens', 'SIGNIFICANCE'),
        'temporal_hook': best.get('temporal_hook', ''),
        'stability_days': ki.get('stability_days', 1.0),
        'due_at': ki.get('due_at', 0),
        'last_reviewed_at': ki.get('last_reviewed_at'),
        'last_score': ki.get('last_score'),
        'review_count': ki.get('review_count', 0),
        'sources': sources,
        'cached_question': ki.get('cached_question'),
    }


def get_review_queue(limit: int = 20, book_id: str | None = None, conn=None) -> list:
    now = int(time.time() * 1000)
    soon = now + 24 * 60 * 60 * 1000

    # knowledge_items: core curriculum nodes (book_chapter + gap_fill)
    ki_query = 'SELECT * FROM knowledge_items WHERE due_at <= ?'
    ki_params = [soon]
    if book_id:
        # Filter to items that have at least one source from this book
        # (SQLite JSON: simpler to post-filter in Python)
        ki_rows = conn.execute(ki_query, ki_params).fetchall()
        ki_rows = [r for r in ki_rows
                   if any(s.get('book_id') == book_id
                          for s in (json.loads(r['sources'] or '[]') if r['sources'] else []))]
    else:
        ki_rows = conn.execute(ki_query, ki_params).fetchall()

    # exploration + voice_followup items still live in review_items
    ri_query = "SELECT * FROM review_items WHERE due_at <= ? AND item_type != 'book_chapter'"
    ri_params = [soon]
    if book_id:
        ri_query += ' AND source_book_id = ?'
        ri_params.append(book_id)
    ri_rows = conn.execute(ri_query, ri_params).fetchall()

    # Pre-load curricula for depth ordering
    domains: set = set()
    for r in ki_rows:
        if r['curriculum_domain']:
            domains.add(r['curriculum_domain'])
    for r in ri_rows:
        if r['curriculum_domain']:
            domains.add(r['curriculum_domain'])

    curriculum_cache: dict = {}
    node_depths: dict = {}
    for domain in domains:
        curriculum = load_curriculum(domain)
        curriculum_cache[domain] = curriculum
        if curriculum:
            node_depths.update(compute_node_depths(curriculum))

    # Build unified item list
    items = []
    for r in ki_rows:
        items.append(_knowledge_item_to_queue_row(dict(r), curriculum_cache))
    for r in ri_rows:
        items.append(dict(r))

    items.sort(key=lambda i: (node_depths.get(i.get('curriculum_node_id', ''), 999), i.get('due_at', 0)))
    return items[:limit]


# ── Question generation ───────────────────────────────────────────────────────

def _best_source_for_question(sources: list) -> dict:
    """Pick the most useful source for question generation.

    Prefer real book sources (book_id not None). Among those, prefer the most
    recently added (last) since it tends to have the freshest context.
    Falls back to curriculum gap-fill source if no book sources exist.
    """
    book_sources = [s for s in sources if s.get('book_id') is not None]
    if book_sources:
        # Most recently added = last in the list
        return book_sources[-1]
    return sources[-1] if sources else {}


def generate_question(item_id: str, conn) -> dict:
    # First try knowledge_items (node-centric); fall back to review_items (exploration/voice)
    row = conn.execute('SELECT * FROM knowledge_items WHERE id=?', (item_id,)).fetchone()
    if row is None:
        row = conn.execute('SELECT * FROM review_items WHERE id=?', (item_id,)).fetchone()
    if not row:
        return {}
    item = dict(row)

    # Serve from cache if available
    if item.get('cached_question'):
        try:
            return json.loads(item['cached_question'])
        except Exception:
            pass

    domain_id = item.get('curriculum_domain', 'sicily_history_culture_and_legacy')
    curriculum = load_curriculum(domain_id)
    knowledge_state = load_knowledge_states(domain_id)

    node = next((n for n in (curriculum or {}).get('nodes', [])
                 if n['id'] == item.get('curriculum_node_id')), None)
    node_title = node['title'] if node else item.get('curriculum_node_title', item.get('curriculum_node_id', ''))
    node_description = node.get('description', '') if node else ''

    # Resolve source_text and temporal_hook from sources array (knowledge_items) or direct fields (review_items)
    if 'sources' in item and item['sources']:
        try:
            sources = json.loads(item['sources'])
        except Exception:
            sources = []
        best = _best_source_for_question(sources)
        source_text = best.get('source_text', '')
        temporal_hook = best.get('temporal_hook', '')
        lens = best.get('lens', 'SIGNIFICANCE')
    else:
        source_text = item.get('source_text', '')
        temporal_hook = item.get('temporal_hook', '')
        lens = item.get('lens', 'SIGNIFICANCE')

    known = [n['title'] for n in (curriculum or {}).get('nodes', [])
             if knowledge_state.get(n['id'], {}).get('knowledge') in ('engaged', 'anchored')
             and n['id'] != item.get('curriculum_node_id')]

    known_ctx = ''
    if known[:3]:
        known_ctx = ('Other concepts the learner knows:\n'
                     + '\n'.join(f'- {t}' for t in known[:3]))

    temporal_ctx = ''
    if temporal_hook:
        temporal_ctx = f"Temporal hook: {temporal_hook}"

    review_count = item.get('review_count', 0) + 1

    # Reviews 1-2: pure factual recall — who/when/what, no analysis
    if review_count <= 2:
        prompt = QUESTION_GEN_PROMPT_FACTUAL.format(
            node_title=node_title,
            node_description=node_description,
            source_text=source_text[:400],
            temporal_context=temporal_ctx,
        )
    else:
        if review_count == 3:
            difficulty = f'Review #{review_count} — now that the fact is solid, ask why it mattered or what caused it.'
        else:
            difficulty = f'Review #{review_count} — push for comparisons, patterns, or long-term implications.'

        prompt = QUESTION_GEN_PROMPT.format(
            node_title=node_title,
            node_description=node_description,
            source_text=source_text[:400],
            review_count=review_count,
            lens=lens,
            difficulty_instruction=difficulty,
            known_nodes_context=known_ctx, temporal_context=temporal_ctx,
        )

    raw = call_llm(prompt, max_tokens=1024, response_mime_type='application/json')
    result = _parse_json(raw) if raw else None

    if isinstance(result, dict) and 'question' in result:
        result.setdefault('temporal_hook', temporal_hook)
        return result

    return {
        'question': f'What was historically significant about {node_title}?',
        'answer_guidance': source_text,
        'temporal_hook': temporal_hook,
        'curriculum_context': '',
    }


# ── Record answer ─────────────────────────────────────────────────────────────

def record_answer(item_id: str, score: str, conn) -> dict:
    # Look up in knowledge_items first; fall back to review_items (exploration/voice)
    row = conn.execute('SELECT * FROM knowledge_items WHERE id=?', (item_id,)).fetchone()
    table = 'knowledge_items'
    if row is None:
        row = conn.execute('SELECT * FROM review_items WHERE id=?', (item_id,)).fetchone()
        table = 'review_items'
    if not row:
        return {}
    item = dict(row)

    now = int(time.time() * 1000)
    if score == 'missed':
        new_stability = INITIAL_STABILITY_DAYS
    else:
        new_stability = min(item['stability_days'] * STABILITY_MULTIPLIERS.get(score, 1.0), MAX_STABILITY_DAYS)

    next_due = now + int(new_stability * 24 * 60 * 60 * 1000)

    # Clear cached question — knowledge state has changed, regenerate for next session
    conn.execute(f"""
        UPDATE {table} SET stability_days=?, due_at=?, last_reviewed_at=?,
          last_score=?, review_count=review_count+1, cached_question=NULL
        WHERE id=?
    """, (new_stability, next_due, now, score, item_id))

    if item.get('curriculum_domain') and item.get('curriculum_node_id'):
        knowledge_val, confidence_val = SCORE_TO_KNOWLEDGE.get(score, ('unknown', 0.0))
        # Determine source book/chapter for the curriculum update note
        if table == 'knowledge_items':
            try:
                sources = json.loads(item.get('sources') or '[]')
                best = _best_source_for_question(sources)
                src_book = best.get('book_id', '')
                src_chapter = best.get('chapter_number', '')
            except Exception:
                src_book, src_chapter = '', ''
        else:
            src_book = item.get('source_book_id', '')
            src_chapter = item.get('source_chapter_number', '')
        update_knowledge(item['curriculum_domain'], item['curriculum_node_id'],
                         knowledge=knowledge_val, confidence=confidence_val,
                         source=f"review:{src_book}:{src_chapter}")

    if score == 'missed' and item.get('curriculum_domain') and item.get('curriculum_node_id'):
        curriculum = load_curriculum(item['curriculum_domain'])
        if curriculum:
            dep_ids = get_dependent_node_ids(item['curriculum_node_id'], curriculum)
            if dep_ids:
                soon = now + 24 * 60 * 60 * 1000
                ph = ','.join('?' * len(dep_ids))
                # Reschedule dependents in both tables
                conn.execute(
                    f"UPDATE knowledge_items SET stability_days=1.0, due_at=? WHERE curriculum_node_id IN ({ph}) AND (last_score IS NULL OR last_score != 'knew')",
                    [soon] + dep_ids,
                )
                conn.execute(
                    f"UPDATE review_items SET stability_days=1.0, due_at=? WHERE curriculum_node_id IN ({ph}) AND (last_score IS NULL OR last_score != 'knew')",
                    [soon] + dep_ids,
                )

    conn.commit()

    # Background re-generation — pre-cache question for next session
    def _regen():
        try:
            from db import get_connection as _conn
            c = _conn()
            q = generate_question(item_id, c)
            c.execute(f'UPDATE {table} SET cached_question=? WHERE id=?',
                      (json.dumps(q), item_id))
            c.commit()
            c.close()
            print(f'[review] re-generated question for {table} item {item_id}', flush=True)
        except Exception as e:
            print(f'[review] re-gen failed for {table} item {item_id}: {e}', flush=True)
    threading.Thread(target=_regen, daemon=True).start()

    return {'next_due_at': next_due, 'new_stability_days': new_stability}


# ── Stats ──────────────────────────────────────────────────────────────────────

def get_review_stats(conn) -> dict:
    now = int(time.time() * 1000)
    end_today = now + 24 * 60 * 60 * 1000
    end_week = now + 7 * 24 * 60 * 60 * 1000

    # Core nodes from knowledge_items
    ki_due_today = conn.execute(
        'SELECT COUNT(*) FROM knowledge_items WHERE due_at <= ?', (end_today,)
    ).fetchone()[0]
    ki_due_week = conn.execute(
        'SELECT COUNT(*) FROM knowledge_items WHERE due_at <= ?', (end_week,)
    ).fetchone()[0]
    ki_total = conn.execute('SELECT COUNT(*) FROM knowledge_items').fetchone()[0]

    # Exploration / voice items from review_items
    ri_due_today = conn.execute(
        "SELECT COUNT(*) FROM review_items WHERE due_at <= ? AND item_type != 'book_chapter'", (end_today,)
    ).fetchone()[0]
    ri_due_week = conn.execute(
        "SELECT COUNT(*) FROM review_items WHERE due_at <= ? AND item_type != 'book_chapter'", (end_week,)
    ).fetchone()[0]
    ri_total = conn.execute(
        "SELECT COUNT(*) FROM review_items WHERE item_type != 'book_chapter'"
    ).fetchone()[0]

    # Per-book breakdown: iterate knowledge_items sources arrays
    by_book: dict = {}
    ki_rows = conn.execute(
        'SELECT sources FROM knowledge_items WHERE due_at <= ?', (end_today,)
    ).fetchall()
    for r in ki_rows:
        try:
            sources = json.loads(r['sources'] or '[]')
            book_sources = [s for s in sources if s.get('book_id')]
            if book_sources:
                bid = book_sources[-1]['book_id']
                by_book[bid] = by_book.get(bid, 0) + 1
        except Exception:
            pass

    return {
        'due_today': ki_due_today + ri_due_today,
        'due_this_week': ki_due_week + ri_due_week,
        'total': ki_total + ri_total,
        'knowledge_items_total': ki_total,
        'by_source': by_book,
    }


# ── Exploration items ──────────────────────────────────────────────────────────

def _load_item_for_child(item_id: str, conn) -> dict | None:
    """Load parent item from knowledge_items or review_items, normalising field names."""
    row = conn.execute('SELECT * FROM knowledge_items WHERE id=?', (item_id,)).fetchone()
    if row:
        item = dict(row)
        # Derive flat fields from sources array for use in child items
        try:
            sources = json.loads(item.get('sources') or '[]')
            best = _best_source_for_question(sources)
        except Exception:
            best = {}
        item['source_book_id'] = best.get('book_id')
        item['source_chapter_number'] = best.get('chapter_number')
        item['source_chapter_title'] = best.get('chapter_title', '')
        item['source_text'] = best.get('source_text', '')
        # Resolve curriculum_node_title from curriculum
        domain = item.get('curriculum_domain', '')
        curriculum = load_curriculum(domain)
        node_id = item.get('curriculum_node_id', '')
        if curriculum:
            node = next((n for n in curriculum.get('nodes', []) if n['id'] == node_id), None)
            item['curriculum_node_title'] = node['title'] if node else node_id
        else:
            item['curriculum_node_title'] = node_id
        return item

    row = conn.execute('SELECT * FROM review_items WHERE id=?', (item_id,)).fetchone()
    return dict(row) if row else None


def create_exploration_items(item_id: str, conn) -> list:
    item = _load_item_for_child(item_id, conn)
    if not item:
        return []

    # Don't create duplicates if unexpired exploration items already exist for this parent
    now = int(time.time() * 1000)
    existing = conn.execute(
        "SELECT count(*) FROM review_items WHERE parent_item_id=? AND item_type='exploration' AND due_at > ?",
        (item_id, now - 7 * 24 * 60 * 60 * 1000)  # within last week
    ).fetchone()[0]
    if existing > 0:
        return []

    prompt = EXPLORE_PROMPT.format(
        node_title=item.get('curriculum_node_title', ''),
        source_text=item.get('source_text', '')[:400],
        score=item.get('last_score', 'partly'),
    )

    raw = _call_claude(prompt) or call_llm(prompt, max_tokens=65536, response_mime_type='application/json')
    questions = _parse_json(raw) if raw else None
    if not isinstance(questions, list):
        return []

    tomorrow = now + 24 * 60 * 60 * 1000
    created = []

    for i, q in enumerate(questions[:3]):
        child_id = f'{item_id}_explore_{i}_{now}'
        conn.execute("""
            INSERT INTO review_items
              (id, item_type, curriculum_domain, curriculum_node_id, curriculum_node_title,
               source_book_id, source_chapter_number, source_chapter_title,
               source_text, lens, parent_item_id, stability_days, due_at, review_count, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            child_id, 'exploration',
            item.get('curriculum_domain'), item.get('curriculum_node_id'), item.get('curriculum_node_title'),
            item.get('source_book_id'), item.get('source_chapter_number'), item.get('source_chapter_title'),
            q.get('question', ''), q.get('lens', 'SIGNIFICANCE'),
            item_id, 1.0, tomorrow, 0, now,
        ))
        created.append({'id': child_id, 'question': q.get('question', ''), 'lens': q.get('lens', ''),
                        'suggested_source': q.get('suggested_source', '')})

    conn.commit()
    return created


# ── Voice memo ────────────────────────────────────────────────────────────────

def process_voice_memo(item_id: str, audio_path: Path, conn, transcribe_fn) -> dict:
    """transcribe_fn: callable(Path) -> str  (e.g. transcribe_on_server)"""
    item = _load_item_for_child(item_id, conn)
    if not item:
        return {}

    transcript = transcribe_fn(audio_path)
    if not transcript:
        return {'error': 'Transcription failed'}

    prompt = VOICE_EXTRACT_PROMPT.format(
        node_title=item.get('curriculum_node_title', ''),
        transcript=transcript,
    )

    raw = _call_claude(prompt) or call_llm(prompt, max_tokens=65536, response_mime_type='application/json')
    extracted = _parse_json(raw) if raw else {}
    if not isinstance(extracted, dict):
        extracted = {}

    score = extracted.get('suggested_score', 'partly')
    now = int(time.time() * 1000)
    soon = now + 2 * 60 * 60 * 1000  # 2h: high priority
    follow_ups = []

    for i, question in enumerate(extracted.get('questions', [])[:3]):
        child_id = f'{item_id}_voice_{i}_{now}'
        conn.execute("""
            INSERT INTO review_items
              (id, item_type, curriculum_domain, curriculum_node_id, curriculum_node_title,
               source_book_id, source_chapter_number, source_chapter_title,
               source_text, lens, parent_item_id, stability_days, due_at, review_count, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            child_id, 'voice_followup',
            item.get('curriculum_domain'), item.get('curriculum_node_id'), item.get('curriculum_node_title'),
            item.get('source_book_id'), item.get('source_chapter_number'), item.get('source_chapter_title'),
            question, 'SIGNIFICANCE', item_id, 1.0, soon, 0, now,
        ))
        follow_ups.append({'id': child_id, 'question': question})

    conn.commit()
    return {
        'transcript': transcript,
        'remembered': extracted.get('remembered', ''),
        'suggested_score': score,
        'connections': extracted.get('connections', []),
        'follow_ups_created': follow_ups,
    }

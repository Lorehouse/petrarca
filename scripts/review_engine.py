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

CURRICULUM_KEYWORDS = {
    'sicily_history_culture_and_legacy': ['sicily', 'sicilian', 'syracuse', 'palermo', 'agrigento', 'norman sicily'],
    'ancient_greece_800300_bc_political_military_cultural_and': ['greece', 'greek', 'athens', 'sparta', 'alexander', 'hellenistic'],
    'roman_republic_and_empire': ['rome', 'roman', 'caesar', 'republic', 'augustus'],
}

def detect_curriculum(book_title: str, book_topics: list) -> str:
    text = ' '.join([book_title] + book_topics).lower()
    for domain_id, keywords in CURRICULUM_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return domain_id
    return 'sicily_history_culture_and_legacy'


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


QUESTION_GEN_PROMPT_FACTUAL = """Generate a factual recall question for a knowledge review.

Concept: {node_title}
Curriculum definition: {node_description}
Chapter evidence: {source_text}

The curriculum definition is the AUTHORITATIVE source for what this concept IS and what facts matter.
The chapter evidence shows what this particular book said about it.

Step 1 — from the curriculum definition, pick the single most memorable and testable fact:
a specific person's name, a year, a battle, an achievement, a distinctive detail.
Priority: vivid and surprising facts over generic ones.
Good targets: "Gelon crushed Carthage on the same day as Salamis", "Constans II moved the capital to Syracuse", "Archimedes held off Rome for two years with war machines", "tyrannos just meant 'sole ruler'".

Step 2 — write one question starting with one of: Who / When / Which / What year / What did [X] / What replaced / Which [X]
Do NOT start with: Why / How / What factors / What was [X] known for

Keep it SHORT — 6-10 words max. Any context or clarification goes in answer_guidance, not the question.

Good:
- "Who led Carthage's invasion at Himera?" → specific name
- "What year did Belisarius take Sicily for Byzantium?" → specific date
- "What did 'tyrannos' originally mean?" → surprising vocabulary fact
- "What did Archimedes build to hold off Rome?" → vivid achievement

Bad:
- "Which city experienced the transition to autocratic rule?" — abstract, no specific fact
- "Who was the most powerful tyrant in Greek history, controlling most of Sicily?" — 16 words
- "What was Gelon known for?" — too vague

{temporal_context}

Output JSON only:
{{"question":"...","answer_guidance":"1-2 sentences: the specific fact(s) a correct answer should include","temporal_hook":"...","curriculum_context":"..."}}"""


QUESTION_GEN_PROMPT = """Generate a knowledge review question.

Concept: {node_title}
Curriculum definition: {node_description}
Chapter evidence: {source_text}
Review #{review_count}

{difficulty_instruction}

{known_nodes_context}
{temporal_context}

The learner already knows the basic facts (who/when/what). Now push deeper using the {lens} lens:
- CAUSAL: causes/sequences/why this happened
- COMPARATIVE: compare to another period, ruler, or place
- SIGNIFICANCE: historical importance, what it changed
- TEMPORAL: simultaneous events or chronological anchor
- PATTERN: recurring dynamics across periods
- CONSEQUENCE: long-term effects

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


def create_review_items_for_chapter(book_id: str, book_title: str, book_topics: list,
                                     chapter_number: int, chapter_title: str, conn) -> dict:
    """Map chapter to curriculum nodes and create review_items. Returns summary."""
    mappings = map_chapter_to_nodes(book_id, book_title, book_topics, chapter_number, chapter_title)
    if not mappings:
        return {'nodes_covered': [], 'items_created': 0, 'domain': detect_curriculum(book_title, book_topics)}

    now = int(time.time() * 1000)
    created = 0
    node_titles = []

    for m in mappings:
        existing = conn.execute(
            'SELECT id FROM review_items WHERE source_book_id=? AND source_chapter_number=? AND curriculum_node_id=?',
            (book_id, chapter_number, m['node_id'])
        ).fetchone()
        if existing:
            continue

        item_id = f"ri_{book_id}_{chapter_number}_{m['node_id'].replace(' ', '_')[:20]}_{now}"
        conn.execute("""
            INSERT INTO review_items
              (id, item_type, curriculum_domain, curriculum_node_id, curriculum_node_title,
               source_book_id, source_chapter_number, source_chapter_title,
               source_text, temporal_hook, lens, stability_days, due_at, review_count, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            item_id, 'book_chapter',
            detect_curriculum(book_title, book_topics),
            m['node_id'], m.get('node_title', ''),
            book_id, chapter_number, chapter_title,
            m.get('source_text', ''), m.get('temporal_hook', ''),
            m.get('lens', 'SIGNIFICANCE'),
            INITIAL_STABILITY_DAYS, now, 0, now,
        ))
        created += 1
        node_titles.append(m.get('node_title', m['node_id']))

    conn.commit()
    print(f'[review] Ch{chapter_number} mapped: {created} items → {node_titles}', flush=True)

    # Pre-generate questions in background — items will be ready before user opens review
    new_ids = conn.execute(
        'SELECT id FROM review_items WHERE source_book_id=? AND source_chapter_number=? AND cached_question IS NULL',
        (book_id, chapter_number)
    ).fetchall()
    if new_ids:
        def _pregen():
            from db import get_connection as _conn
            c = _conn()
            for (iid,) in new_ids:
                try:
                    q = generate_question(iid, c)
                    c.execute('UPDATE review_items SET cached_question=? WHERE id=?',
                              (json.dumps(q), iid))
                    c.commit()
                except Exception as e:
                    print(f'[review] pre-gen failed {iid}: {e}', flush=True)
            c.close()
            print(f'[review] pre-generated {len(new_ids)} questions for ch{chapter_number}', flush=True)
        threading.Thread(target=_pregen, daemon=True).start()

    return {
        'nodes_covered': node_titles,
        'items_created': created,
        'domain': detect_curriculum(book_title, book_topics),
    }


# ── Review queue ──────────────────────────────────────────────────────────────

def get_review_queue(limit: int = 20, book_id: str | None = None, conn = None) -> list:
    now = int(time.time() * 1000)
    soon = now + 24 * 60 * 60 * 1000

    query = 'SELECT * FROM review_items WHERE due_at <= ?'
    params = [soon]
    if book_id:
        query += ' AND source_book_id = ?'
        params.append(book_id)

    rows = conn.execute(query, params).fetchall()
    items = [dict(r) for r in rows]

    domains = {i['curriculum_domain'] for i in items if i.get('curriculum_domain')}
    node_depths: dict = {}
    for domain in domains:
        curriculum = load_curriculum(domain)
        if curriculum:
            node_depths.update(compute_node_depths(curriculum))

    items.sort(key=lambda i: (node_depths.get(i.get('curriculum_node_id', ''), 999), i.get('due_at', 0)))
    return items[:limit]


# ── Question generation ───────────────────────────────────────────────────────

def generate_question(item_id: str, conn) -> dict:
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
    node_title = node['title'] if node else item.get('curriculum_node_title', '')
    node_description = node.get('description', '') if node else ''


    known = [n['title'] for n in (curriculum or {}).get('nodes', [])
             if knowledge_state.get(n['id'], {}).get('knowledge') in ('engaged', 'anchored')
             and n['id'] != item.get('curriculum_node_id')]

    known_ctx = ''
    if known[:3]:
        known_ctx = ('Other concepts the learner knows:\n'
                     + '\n'.join(f'- {t}' for t in known[:3]))

    temporal_ctx = ''
    if item.get('temporal_hook'):
        temporal_ctx = f"Temporal hook: {item['temporal_hook']}"

    review_count = item.get('review_count', 0) + 1
    lens = item.get('lens', 'SIGNIFICANCE')

    # Reviews 1-2: pure factual recall — who/when/what, no analysis
    if review_count <= 2:
        prompt = QUESTION_GEN_PROMPT_FACTUAL.format(
            node_title=node_title,
            node_description=node_description,
            source_text=item.get('source_text', '')[:400],
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
            source_text=item.get('source_text', '')[:400],
            review_count=review_count,
            lens=lens,
            difficulty_instruction=difficulty,
            known_nodes_context=known_ctx, temporal_context=temporal_ctx,
        )

    raw = call_llm(prompt, max_tokens=1024, response_mime_type='application/json')
    result = _parse_json(raw) if raw else None

    if isinstance(result, dict) and 'question' in result:
        result.setdefault('temporal_hook', item.get('temporal_hook', ''))
        return result

    return {
        'question': f'What was historically significant about {node_title}?',
        'answer_guidance': item.get('source_text', ''),
        'temporal_hook': item.get('temporal_hook', ''),
        'curriculum_context': '',
    }


# ── Record answer ─────────────────────────────────────────────────────────────

def record_answer(item_id: str, score: str, conn) -> dict:
    row = conn.execute('SELECT * FROM review_items WHERE id=?', (item_id,)).fetchone()
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
    conn.execute("""
        UPDATE review_items SET stability_days=?, due_at=?, last_reviewed_at=?,
          last_score=?, review_count=review_count+1, cached_question=NULL
        WHERE id=?
    """, (new_stability, next_due, now, score, item_id))

    if item.get('curriculum_domain') and item.get('curriculum_node_id'):
        knowledge_val, confidence_val = SCORE_TO_KNOWLEDGE.get(score, ('unknown', 0.0))
        update_knowledge(item['curriculum_domain'], item['curriculum_node_id'],
                         knowledge=knowledge_val, confidence=confidence_val,
                         source=f"review:{item.get('source_book_id','')}:{item.get('source_chapter_number','')}")

    if score == 'missed' and item.get('curriculum_domain') and item.get('curriculum_node_id'):
        curriculum = load_curriculum(item['curriculum_domain'])
        if curriculum:
            dep_ids = get_dependent_node_ids(item['curriculum_node_id'], curriculum)
            if dep_ids:
                soon = now + 24 * 60 * 60 * 1000
                ph = ','.join('?' * len(dep_ids))
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
            c.execute('UPDATE review_items SET cached_question=? WHERE id=?',
                      (json.dumps(q), item_id))
            c.commit()
            c.close()
            print(f'[review] re-generated question for item {item_id}', flush=True)
        except Exception as e:
            print(f'[review] re-gen failed for item {item_id}: {e}', flush=True)
    threading.Thread(target=_regen, daemon=True).start()

    return {'next_due_at': next_due, 'new_stability_days': new_stability}


# ── Stats ──────────────────────────────────────────────────────────────────────

def get_review_stats(conn) -> dict:
    now = int(time.time() * 1000)
    end_today = now + 24 * 60 * 60 * 1000
    end_week = now + 7 * 24 * 60 * 60 * 1000

    due_today = conn.execute('SELECT COUNT(*) FROM review_items WHERE due_at <= ?', (end_today,)).fetchone()[0]
    due_week = conn.execute('SELECT COUNT(*) FROM review_items WHERE due_at <= ?', (end_week,)).fetchone()[0]
    total = conn.execute('SELECT COUNT(*) FROM review_items').fetchone()[0]
    by_book = conn.execute(
        'SELECT source_book_id, COUNT(*) FROM review_items WHERE due_at<=? GROUP BY source_book_id', (end_today,)
    ).fetchall()

    return {
        'due_today': due_today,
        'due_this_week': due_week,
        'total': total,
        'by_source': {r[0]: r[1] for r in by_book if r[0]},
    }


# ── Exploration items ──────────────────────────────────────────────────────────

def create_exploration_items(item_id: str, conn) -> list:
    row = conn.execute('SELECT * FROM review_items WHERE id=?', (item_id,)).fetchone()
    if not row:
        return []
    item = dict(row)

    prompt = EXPLORE_PROMPT.format(
        node_title=item.get('curriculum_node_title', ''),
        source_text=item.get('source_text', '')[:400],
        score=item.get('last_score', 'partly'),
    )

    raw = _call_claude(prompt) or call_llm(prompt, max_tokens=65536, response_mime_type='application/json')
    questions = _parse_json(raw) if raw else None
    if not isinstance(questions, list):
        return []

    now = int(time.time() * 1000)
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
    row = conn.execute('SELECT * FROM review_items WHERE id=?', (item_id,)).fetchone()
    if not row:
        return {}
    item = dict(row)

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

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

from claude_llm import call_claude, call_claude_json, call_claude_or_gemini, call_claude_search
from curriculum import load_curriculum
from curriculum_db import update_knowledge, load_knowledge_states

DATA_DIR = Path(os.environ.get('PETRARCA_DATA', '/opt/petrarca/data'))


def _log_voice_transcript(source: str, node_id: str, domain_id: str,
                          node_title: str, transcript: str, audio_bytes: int,
                          llm_result: dict, ml_triggered: list):
    """Persist every voice transcript for later analysis."""
    try:
        from db import get_connection
        conn = get_connection()
        vt_id = f'vt_{int(time.time())}_{hash(transcript) % 10000:04d}'
        conn.execute(
            '''INSERT OR IGNORE INTO voice_transcripts
               (id, source, node_id, domain_id, node_title, transcript,
                audio_bytes, llm_result, microlearning_triggered, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)''',
            (vt_id, source, node_id, domain_id, node_title, transcript,
             audio_bytes, json.dumps(llm_result) if llm_result else None,
             json.dumps([m.get('id', m) for m in ml_triggered]) if ml_triggered else '[]',
             int(time.time() * 1000)),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f'[voice-log] Failed to persist transcript: {e}', flush=True)
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
        book_vec = model.embed(book_text)

        import numpy as np
        best_id, best_score = curricula[0]['id'], -1.0
        for meta in curricula:
            c = load_curriculum(meta['id'])
            if not c:
                continue
            c_text = f"{c.get('title', '')}. {c.get('description', '')} {' '.join(n['title'] for n in c.get('nodes', [])[:10])}"
            c_vec = model.embed(c_text)
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
        'classical_reception': ['classics', 'classical education', 'humanism', 'humanist', 'liberal arts', 'trivium', 'quadrivium', 'paideia', 'hellenism', 'renaissance learning', 'erasmus', 'petrarch', 'scriptoria', 'manuscript'],
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
        book_vec = model.embed(book_text)

        for meta in curricula:
            c = load_curriculum(meta['id'])
            if not c:
                continue
            c_text = f"{c.get('title', '')}. {' '.join(n['title'] for n in c.get('nodes', [])[:15])}"
            c_vec = model.embed(c_text)
            score = float(np.dot(book_vec, c_vec) / (np.linalg.norm(book_vec) * np.linalg.norm(c_vec) + 1e-9))
            results.append({'id': meta['id'], 'title': meta['title'], 'score': round(score, 3)})

        results.sort(key=lambda x: -x['score'])
    except Exception as e:
        print(f'[review] suggest_curricula embedding failed: {e}', flush=True)
        results = [{'id': m['id'], 'title': m['title'], 'score': 0.0} for m in curricula]

    return results


# ── LLM helpers ───────────────────────────────────────────────────────────────

def _call_claude(prompt: str, timeout: int = 180) -> str | None:
    """Legacy wrapper — delegates to claude_llm module."""
    return call_claude(prompt, timeout=timeout)


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
- "source_text": 1-2 sentences of SPECIFIC FACTS from the chapter — exact names, dates, events, numbers. Do NOT write abstract summaries like "the chapter discusses the importance of X" — instead write concrete facts: "Themistocles persuaded Athens to build 200 triremes before Salamis" or "The Macedonian dynasty ruled 867–1056 AD, Byzantium's cultural golden age". If the chapter is thin on specifics, name the most concrete nouns it mentions.
- "lens": best retrieval lens — CAUSAL | COMPARATIVE | SIGNIFICANCE | TEMPORAL | PATTERN | CONSEQUENCE
- "temporal_hook": optional 1-sentence cross-period anchor (e.g. "Simultaneous with the Roman conquest of Carthage" or "Two centuries before the rise of Islam")

Output JSON array only:
[{{"node_id":"...","node_title":"...","source_text":"...","lens":"...","temporal_hook":"..."}}]"""


QUESTION_GEN_PROMPT_FACTUAL = """Generate a factual review question that tests framework knowledge.

The learner is building a mental scaffold of history. They need to recall KEY FACTS:
dates, key figures, key events, and where things fit in the timeline. These facts are
the load-bearing pillars that make everything else they read richer and more connected.

Concept: {node_title}
Curriculum definition: {node_description}

Extract the most important FACTS from this curriculum node and test ONE of them:
- KEY DATES: When did this happen? What century/decade? (e.g., "When was the Battle of Himera?")
- KEY FIGURES: Who was the central person? What was their role? (e.g., "Who was Gelon?")
- KEY EVENTS: What happened? What was the outcome? (e.g., "What ended Arab rule in Sicily?")
- TIMELINE PLACEMENT: What came before/after? What was happening elsewhere? (e.g., "Himera was simultaneous with which Greek battle?")

Pick the single most important fact to test — the one that, once known, makes this
entire period click into place. Prefer dates and figures for early reviews.

DO NOT ask vague conceptual questions like "What characterized..." or "What made X unique..."
— those come later. Right now we need the factual scaffolding.

The answer should be SHORT and specific (a date, a name, a 1-sentence event).

{temporal_context}

Output JSON only:
{{"question":"short factual question (6-15 words)","answer_guidance":"the specific factual answer (1-2 sentences max)","rich_answer":"4-5 sentences placing this fact in vivid context — who, what, when, why it matters. Include a temporal anchor to another known period. This is shown when the learner gets it wrong.","temporal_hook":"connection to another era the learner knows","curriculum_context":"brief placement in the larger history"}}"""


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
{{"question":"...","answer_guidance":"2-3 sentences on what a good answer covers","rich_answer":"4-5 sentences expanding on the answer with vivid detail, a concrete example, and a temporal anchor to another period. This is shown when the learner gets it wrong — make it a learning moment, not a punishment.","temporal_hook":"...","curriculum_context":"..."}}"""


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


VOICE_ELICITATION_PROMPT = """Analyze a learner's free recall about a historical topic.

TOPIC: {node_title}
TOPIC DEFINITION: {node_description}

BOOK SOURCES (what the learner has read about this):
{sources_text}

LEARNER'S RECALL (transcribed speech):
{transcript}

Compare the learner's recall against the topic definition and book sources. Identify:

1. CAPTURED: Specific facts or concepts from the definition/sources that the learner mentioned (even if imprecisely). Be generous — paraphrases count.
2. MISSED: Important facts from the definition/sources that were NOT mentioned. Focus on the 2-3 most important omissions, not every detail.
3. INTERESTING: Things the learner said that go BEYOND the sources — personal connections, questions, hypotheses, links to other topics. These are valuable signals.
4. WONDERINGS: Any "I wonder..." or questioning statements — these are research triggers.

Output JSON:
{{"captured": ["fact1", "fact2"], "missed": ["important_fact1", "important_fact2"], "interesting": ["connection1"], "wonderings": ["question1"], "coverage_pct": 65, "suggested_score": "knew|partly|missed", "feedback_summary": "2-3 sentence personalized feedback highlighting what was strong and what key thing was missed"}}"""


HAMARQUIZEN_PROMPT = """Generate a Hamarquizen-style micro-lesson for reviewing a book topic.

Book: {book_title} by {book_author}
Curriculum node: {node_title}
Node description: {node_description}
Source text from book: {source_text}
Reader's current knowledge: {knowledge_level} (confidence: {confidence})

Create a PRIME→READ→TEST sequence:

1. PRIME: A casual question to activate memory (8-15 words). Start with "What do you remember about..." or "Do you recall why..." or "Can you picture..."

2. READ: 2-3 vivid, specific sentences that bring the topic alive. Include:
   - Concrete names, dates, places (not abstractions)
   - One sensory or dramatic detail ("the walls were 5km long", "he was 75 when he died in the siege")
   - One surprising connection or temporal anchor to another known event
   Keep it tight — this is a micro-narrative, not a textbook paragraph.

3. TEST: A focused question (6-12 words) whose answer is directly in the READ section. Tests understanding, not trivia. Start with What/Why/How.

4. ANSWER: 1-2 sentence answer guidance drawn from the READ section.

5. TEMPORAL_HOOK: One cross-period anchor connecting this to another era the reader might know.

Output JSON:
{{"prime":"...","read":"...","test":"...","answer":"...","temporal_hook":"..."}}"""


MAP_WHOLE_BOOK_PROMPT = """Map a finished book to curriculum nodes for a knowledge review system.

The reader has finished this book. Identify ALL curriculum nodes the reader would have been meaningfully exposed to through reading it. Include nodes where the book provides substantial content — not passing one-sentence mentions.

Book: {book_title} by {book_author}
Topics: {book_topics}
{book_context}

Curriculum nodes ({curriculum_title}) — level 2+ only:
{nodes_list}

Which nodes does this book substantially cover? For historical fiction, include nodes whose events, figures, or settings form part of the narrative. For nonfiction, include nodes whose subject matter is discussed in depth.

For each matched node:
- "node_id": exact ID from the list
- "node_title": node title
- "source_text": 1-2 sentences of SPECIFIC content from this book relevant to the node — name concrete characters, events, settings, arguments. For fiction: "Cicero's prosecution of Verres is a central plot arc in the novel, depicting the corruption of Roman provincial governance in Sicily." For nonfiction: "Chapter on the Arab conquest covers the fall of Syracuse in 878 and the shift to Palermo as capital."
- "lens": best retrieval lens — CAUSAL | COMPARATIVE | SIGNIFICANCE | TEMPORAL | PATTERN | CONSEQUENCE
- "confidence": how central this node is to the book — "high" (major theme/arc), "medium" (significant coverage), "low" (meaningful but secondary)

Be thorough — a 300-page book about Sicilian history might cover 20+ nodes. Don't under-count.

Output JSON array only:
[{{"node_id":"...","node_title":"...","source_text":"...","lens":"...","confidence":"..."}}]"""

# Minimum score from suggest_curricula_for_book to consider a curriculum relevant
CURRICULUM_RELEVANCE_THRESHOLD = 0.40


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

    mappings = call_claude_json(prompt, timeout=240)
    if not mappings:
        return []

    valid_ids = {n['id'] for n in curriculum['nodes']}
    return [m for m in (mappings if isinstance(mappings, list) else [])
            if isinstance(m, dict) and m.get('node_id') in valid_ids]


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


# ── Whole-book mapping ───────────────────────────────────────────────────────

def _get_book_context(book_id: str, book_title: str) -> str:
    """Gather any available context about a book: research, chapters, highlights."""
    parts = []
    # Book research file
    path = BOOK_RESEARCH_DIR / f'{book_id}.json'
    if path.exists():
        try:
            research = json.loads(path.read_text())
            if research.get('summary'):
                parts.append(f"Book summary: {research['summary']}")
            if research.get('chapter_research'):
                ch_titles = []
                for ch_num, ch in sorted(research['chapter_research'].items(), key=lambda x: int(x[0])):
                    title = ch.get('title', f'Chapter {ch_num}')
                    ch_titles.append(f"  Ch {ch_num}: {title}")
                if ch_titles:
                    parts.append("Chapters:\n" + '\n'.join(ch_titles))
        except Exception:
            pass
    # Chapter list from DB
    try:
        from db import get_connection
        conn = get_connection()
        row = conn.execute('SELECT chapters FROM physical_books WHERE id=?', (book_id,)).fetchone()
        conn.close()
        if row and row['chapters']:
            chapters = json.loads(row['chapters'])
            if chapters and not parts:  # Only if we don't already have chapter research
                ch_list = [f"  {ch.get('title', ch.get('number', '?'))}" for ch in chapters[:30]]
                if ch_list:
                    parts.append("Chapter list:\n" + '\n'.join(ch_list))
    except Exception:
        pass
    return '\n'.join(parts) if parts else f'(No additional context available for "{book_title}")'


def _map_book_to_curriculum(book_id: str, book_title: str, book_author: str,
                            book_topics: list, domain_id: str) -> list:
    """Map a whole book against a single curriculum. Returns list of node mappings."""
    curriculum = load_curriculum(domain_id)
    if not curriculum:
        return []

    node_lines = [
        f"- {n['id']}: {n['title']} — {n['description'][:150]}..."
        for n in curriculum['nodes'] if n.get('level', 1) >= 2
    ]
    if not node_lines:
        return []

    book_context = _get_book_context(book_id, book_title)
    curriculum_title = curriculum.get('title', domain_id.replace('_', ' ').title())

    prompt = MAP_WHOLE_BOOK_PROMPT.format(
        book_title=book_title,
        book_author=book_author or 'Unknown',
        book_topics=', '.join(book_topics) if book_topics else 'None specified',
        book_context=book_context,
        nodes_list='\n'.join(node_lines),
        curriculum_title=curriculum_title,
    )

    mappings = call_claude_json(prompt, timeout=240)
    if not mappings:
        return []

    valid_ids = {n['id'] for n in curriculum['nodes']}
    return [m for m in (mappings if isinstance(mappings, list) else [])
            if isinstance(m, dict) and m.get('node_id') in valid_ids]


def map_whole_book(book_id: str, conn) -> dict:
    """Map a finished book to ALL relevant curricula, creating knowledge_items.

    Returns summary with per-curriculum results.
    """
    row = conn.execute(
        'SELECT title, author, topics FROM physical_books WHERE id=?', (book_id,)
    ).fetchone()
    if not row:
        return {'error': f'Book {book_id} not found'}

    book_title = row['title']
    book_author = row['author'] or ''
    book_topics = json.loads(row['topics'] or '[]')

    # Find all relevant curricula
    scored = suggest_curricula_for_book(book_title, book_topics)
    relevant = [c for c in scored if c['score'] >= CURRICULUM_RELEVANCE_THRESHOLD]
    if not relevant:
        return {'error': 'No relevant curricula found', 'scores': scored}

    print(f'[review] Mapping whole book "{book_title}" to {len(relevant)} curricula: '
          f'{[(c["id"][:30], c["score"]) for c in relevant]}', flush=True)

    now = int(time.time() * 1000)
    results = []

    for curr_meta in relevant:
        domain_id = curr_meta['id']
        mappings = _map_book_to_curriculum(
            book_id, book_title, book_author, book_topics, domain_id
        )
        if not mappings:
            results.append({'domain': domain_id, 'score': curr_meta['score'],
                            'nodes_covered': [], 'items_created': 0, 'items_updated': 0})
            continue

        created = 0
        updated = 0
        node_titles = []
        mapped_node_ids = []

        for m in mappings:
            item_id = f"{domain_id}:{m['node_id']}"
            mapped_node_ids.append(m['node_id'])

            new_source = {
                'book_id': book_id,
                'chapter_number': None,
                'chapter_title': f'Whole book: {book_title}',
                'source_text': m.get('source_text', ''),
                'lens': m.get('lens', 'SIGNIFICANCE'),
                'confidence': m.get('confidence', 'medium'),
                'added_at': now,
            }

            existing = conn.execute(
                'SELECT id, sources FROM knowledge_items WHERE id=?', (item_id,)
            ).fetchone()

            if existing:
                try:
                    sources = json.loads(existing['sources'] or '[]')
                except Exception:
                    sources = []
                # Skip if this book already mapped to this node
                already = any(s.get('book_id') == book_id for s in sources)
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

        print(f'[review] Book→{domain_id[:30]}: {created} created, {updated} updated, '
              f'{gaps_filled} gaps, {len(node_titles)} nodes', flush=True)

        results.append({
            'domain': domain_id,
            'score': curr_meta['score'],
            'nodes_covered': node_titles,
            'items_created': created,
            'items_updated': updated,
            'gaps_filled': gaps_filled,
        })

    # Pre-generate questions in background for all new items
    all_new_ids = []
    for r in results:
        domain_id = r['domain']
        items = conn.execute(
            'SELECT id FROM knowledge_items WHERE curriculum_domain=? AND cached_question IS NULL',
            (domain_id,)
        ).fetchall()
        all_new_ids.extend(row['id'] for row in items)

    if all_new_ids:
        def _pregen():
            from db import get_connection as _conn
            c = _conn()
            for iid in all_new_ids:
                try:
                    q = generate_question(iid, c)
                    c.execute('UPDATE knowledge_items SET cached_question=? WHERE id=?',
                              (json.dumps(q), iid))
                    c.commit()
                except Exception as e:
                    print(f'[review] pre-gen failed {iid}: {e}', flush=True)
            c.close()
            print(f'[review] pre-generated {len(all_new_ids)} questions for "{book_title}"', flush=True)
        threading.Thread(target=_pregen, daemon=True).start()

    total_created = sum(r.get('items_created', 0) for r in results)
    total_updated = sum(r.get('items_updated', 0) for r in results)
    return {
        'book_id': book_id,
        'book_title': book_title,
        'curricula_mapped': len([r for r in results if r.get('nodes_covered')]),
        'total_items_created': total_created,
        'total_items_updated': total_updated,
        'details': results,
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
    node_meta: dict = {}  # node_id -> {area_order, date_start}
    for domain in domains:
        curriculum = load_curriculum(domain)
        curriculum_cache[domain] = curriculum
        if curriculum:
            # Build area order from Level 1 nodes (their position in the list = priority)
            area_order = {}
            area_pos = 0
            for n in curriculum.get('nodes', []):
                if n.get('level') == 1:
                    area_order[n['id']] = area_pos
                    area_pos += 1
            # Assign each node its area's position
            parent_map = {n['id']: n.get('parent_id') for n in curriculum.get('nodes', [])}
            for n in curriculum.get('nodes', []):
                parent = parent_map.get(n['id'])
                grandparent = parent_map.get(parent) if parent else None
                area_id = grandparent or parent or n['id']
                node_meta[n['id']] = {
                    'area_order': area_order.get(area_id, 99),
                    'date_start': n.get('date_start'),
                }

    def _sort_key(item):
        nid = item.get('curriculum_node_id', '')
        meta = node_meta.get(nid, {})
        area = meta.get('area_order', 99)
        ds = meta.get('date_start')
        date_sort = ds if ds is not None else 5000
        return (area, date_sort, item.get('due_at', 0))

    # Build unified item list
    items = []
    for r in ki_rows:
        items.append(_knowledge_item_to_queue_row(dict(r), curriculum_cache))
    for r in ri_rows:
        items.append(dict(r))

    items.sort(key=_sort_key)
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


def _pick_key_fact(key_facts: list, question_history: list) -> dict | None:
    """Pick the highest-priority untested key_fact. Returns None if all tested."""
    tested_ids = {h.get('fact_id') for h in question_history if h.get('fact_id')}
    # Priority ordering, then type ordering within same priority
    type_order = {'event': 0, 'date': 1, 'person': 2, 'connection': 3, 'significance': 4}
    sorted_facts = sorted(key_facts, key=lambda f: (
        f.get('priority', 99),
        type_order.get(f.get('type', ''), 5),
    ))
    for fact in sorted_facts:
        if fact.get('id') not in tested_ids:
            return fact
    # All tested — pick the one with worst score for retry
    return None


def _key_fact_to_question(fact: dict, node_title: str, node_description: str) -> dict:
    """Convert a key_fact to the cached_question format."""
    return {
        'question': fact['question'],
        'answer_guidance': fact['answer'],
        'rich_answer': fact.get('rich_answer') or fact['answer'],
        'answer_type': fact.get('type', 'event'),
        'temporal_hook': '',
        'curriculum_context': node_description[:200] if node_description else '',
        'fact_id': fact.get('id', ''),
        'entities': fact.get('entities', []),
    }


def generate_question(item_id: str, conn) -> dict:
    # First try knowledge_items (node-centric); fall back to review_items (exploration/voice)
    row = conn.execute('SELECT * FROM knowledge_items WHERE id=?', (item_id,)).fetchone()
    if row is None:
        row = conn.execute('SELECT * FROM review_items WHERE id=?', (item_id,)).fetchone()
    if not row:
        return {}
    item = dict(row)

    domain_id = item.get('curriculum_domain') or 'sicily_history_culture_and_legacy'
    curriculum = load_curriculum(domain_id)
    knowledge_state = load_knowledge_states(domain_id)

    node = next((n for n in (curriculum or {}).get('nodes', [])
                 if n['id'] == item.get('curriculum_node_id')), None)

    # ── Check key_facts FIRST (deterministic, no LLM) ────────────────────────
    # key_facts live in SQLite (not in curriculum JSON files), so query DB directly
    key_facts = []
    node_id = item.get('curriculum_node_id')
    if node_id and domain_id:
        try:
            kf_row = conn.execute(
                'SELECT key_facts FROM curriculum_nodes WHERE id=? AND domain_id=?',
                (node_id, domain_id)
            ).fetchone()
            if kf_row and kf_row['key_facts']:
                key_facts = json.loads(kf_row['key_facts'])
        except Exception:
            key_facts = []

    if key_facts:
        try:
            question_history = json.loads(item.get('question_history') or '[]')
        except Exception:
            question_history = []
        review_count = item.get('review_count', 0) + 1

        if review_count <= len(key_facts):
            fact = _pick_key_fact(key_facts, question_history)
            if fact:
                node_title = node['title'] if node else ''
                node_description = node.get('description', '') if node else ''
                result = _key_fact_to_question(fact, node_title, node_description)
                entities = fact.get('entities', [])
                # Generate specific follow-up queries from the fact context
                entity_name = entities[0].replace('_', ' ').title() if entities else ''
                fact_q = fact.get('question', '')
                fact_a = fact.get('answer', '')
                result['follow_up_queries'] = [
                    f'Why did {entity_name} matter beyond {node_title}?' if entity_name else f'What were the long-term consequences of {node_title}?',
                    f'What was happening elsewhere when {fact_a[:50].rstrip()}?' if fact_a else f'What was the wider context around {node_title}?',
                    f'What would a contemporary have found most surprising about {entity_name or node_title}?',
                ]
                return result

    # ── Serve from cache if no key_facts path applied ─────────────────────────
    if item.get('cached_question'):
        try:
            cached = json.loads(item['cached_question'])
            # If cached question has fact_id, it's from key_facts — serve it
            # If not, it's an old LLM question — still serve as fallback
            return cached
        except Exception:
            pass

    # ── LLM path: reviews 3+ or no key_facts ────────────────────────────────
    node_title = node['title'] if node else item.get('curriculum_node_title', item.get('curriculum_node_id', ''))
    node_description = node.get('description', '') if node else ''

    # Resolve source_text and temporal_hook
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

    try:
        question_history = json.loads(item.get('question_history') or '[]')
    except Exception:
        question_history = []

    review_count = item.get('review_count', 0) + 1

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

    # Include mastered key_facts as context for analytical questions
    known_facts_ctx = ''
    if key_facts:
        mastered = [f for f in key_facts if f.get('id') in
                    {h.get('fact_id') for h in question_history if h.get('score') == 'knew'}]
        if mastered:
            known_facts_ctx = 'Facts the learner already knows:\n' + '\n'.join(
                f'- {f["question"]} → {f["answer"]}' for f in mastered[:6])

    if review_count <= 2 and not key_facts:
        # No key_facts available — use LLM factual prompt
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
        if known_facts_ctx:
            prompt += f'\n\n{known_facts_ctx}'

    result = call_claude_json(prompt, timeout=120)

    if isinstance(result, dict) and 'question' in result:
        result.setdefault('temporal_hook', temporal_hook)
    else:
        result = {
            'question': f'What was historically significant about {node_title}?',
            'answer_guidance': source_text,
            'temporal_hook': temporal_hook,
            'curriculum_context': '',
        }

    # Generate follow-up research queries via Claude
    if 'follow_up_queries' not in result:
        try:
            fq_prompt = (
                f'A history reader just reviewed "{node_title}": {node_description[:150]}\n\n'
                f'Generate 3 questions that would make them genuinely curious — the kind that make you '
                f'go "wait, really?" or "I never thought about it that way." Be specific, name real '
                f'people/places/events. NO generic templates like "How does X connect to Y?" or '
                f'"Tell me more about X."\n\n'
                f'Examples of good questions:\n'
                f'- "Did Archimedes\' war machines actually work, or was Polybius exaggerating?"\n'
                f'- "Why did Syracuse back Carthage when every other Sicilian city backed Rome?"\n'
                f'- "What happened to the Arab poets who wrote for Norman kings after Frederick II died?"\n\n'
                f'Output JSON array of 3 strings only: ["q1","q2","q3"]'
            )
            fq = call_claude_json(fq_prompt, timeout=60, model='sonnet')
            if isinstance(fq, list) and len(fq) >= 2:
                result['follow_up_queries'] = fq[:3]
        except Exception as e:
            print(f'[review] follow-up gen failed for {node_title}: {e}', flush=True)

    return result


# ── Record answer ─────────────────────────────────────────────────────────────

def record_answer(item_id: str, score: str, conn) -> dict:
    # Look up in knowledge_items first; fall back to review_items, then microlearning_cards
    row = conn.execute('SELECT * FROM knowledge_items WHERE id=?', (item_id,)).fetchone()
    table = 'knowledge_items'
    if row is None:
        row = conn.execute('SELECT * FROM review_items WHERE id=?', (item_id,)).fetchone()
        table = 'review_items'
    if row is None:
        row = conn.execute('SELECT * FROM microlearning_cards WHERE id=?', (item_id,)).fetchone()
        table = 'microlearning_cards'
    if not row:
        return {}
    item = dict(row)

    now = int(time.time() * 1000)
    if score == 'missed':
        new_stability = INITIAL_STABILITY_DAYS
    else:
        new_stability = min(item['stability_days'] * STABILITY_MULTIPLIERS.get(score, 1.0), MAX_STABILITY_DAYS)

    next_due = now + int(new_stability * 24 * 60 * 60 * 1000)

    if table == 'microlearning_cards':
        # Microlearning cards: update FSRS fields (no cached_question to clear)
        conn.execute("""
            UPDATE microlearning_cards SET stability_days=?, due_at=?, last_reviewed_at=?,
              last_score=?, review_count=review_count+1
            WHERE id=?
        """, (new_stability, next_due, now, score, item_id))
        print(f'[review] microlearning {item_id}: {score} → stability={new_stability:.1f}d, next_due in {new_stability:.1f}d', flush=True)

        # Update knowledge state if microlearning card has curriculum context
        if item.get('source_domain') and item.get('source_node_id'):
            knowledge_val, confidence_val = SCORE_TO_KNOWLEDGE.get(score, ('unknown', 0.0))
            update_knowledge(item['source_domain'], item['source_node_id'],
                             knowledge=knowledge_val, confidence=confidence_val,
                             source=f"microlearning:{item_id}")
    else:
        # Regular knowledge_items / review_items
        conn.execute(f"""
            UPDATE {table} SET stability_days=?, due_at=?, last_reviewed_at=?,
              last_score=?, review_count=review_count+1, cached_question=NULL
            WHERE id=?
        """, (new_stability, next_due, now, score, item_id))

    # Knowledge state update for non-microlearning items
    if table != 'microlearning_cards' and item.get('curriculum_domain') and item.get('curriculum_node_id'):
        knowledge_val, confidence_val = SCORE_TO_KNOWLEDGE.get(score, ('unknown', 0.0))
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

    # Reschedule dependents on miss (applies to all card types with curriculum context)
    domain = item.get('curriculum_domain') or item.get('source_domain')
    node_id = item.get('curriculum_node_id') or item.get('source_node_id')
    if score == 'missed' and domain and node_id:
        curriculum = load_curriculum(domain)
        if curriculum:
            dep_ids = get_dependent_node_ids(node_id, curriculum)
            if dep_ids:
                soon = now + 24 * 60 * 60 * 1000
                ph = ','.join('?' * len(dep_ids))
                conn.execute(
                    f"UPDATE knowledge_items SET stability_days=1.0, due_at=? WHERE curriculum_node_id IN ({ph}) AND (last_score IS NULL OR last_score != 'knew')",
                    [soon] + dep_ids,
                )
                conn.execute(
                    f"UPDATE review_items SET stability_days=1.0, due_at=? WHERE curriculum_node_id IN ({ph}) AND (last_score IS NULL OR last_score != 'knew')",
                    [soon] + dep_ids,
                )

    conn.commit()

    # Background re-generation — pre-cache question for next session (not for microlearning)
    if table != 'microlearning_cards':
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


# ── Microlearning research ────────────────────────────────────────────────────

MICROLEARNING_PROMPT = """You are a knowledgeable historian and educator. Answer this research question
concisely but richly, as a microlearning card for a reader studying history and culture.

Research question: {query}

Context — the learner was reviewing this curriculum concept:
{node_title}: {node_description}

Write:
1. A clear, engaging answer in 3-4 SHORT paragraphs (total 150-250 words). Include specific
   names, dates, and vivid details. Write for someone who already has basic knowledge
   of the period — don't over-explain fundamentals.
2. One assessment question about the content (test whether they absorbed the key insight)
3. 3 follow-up research queries for going even deeper

Output JSON only:
{{"content":"the 3-4 paragraph answer","question":"assessment question about this content","answer_guidance":"1-2 sentence answer to the assessment question","follow_up_queries":["query1","query2","query3"]}}"""


def create_microlearning_request(query: str, source_item_id: str | None = None,
                                  source_node_id: str | None = None,
                                  source_domain: str | None = None) -> str:
    """Create a pending microlearning card and return its ID.

    The actual research runs in a background thread.
    """
    from db import get_connection
    card_id = f'ml_{int(time.time())}_{hash(query) % 10000:04d}'
    now_ms = int(time.time() * 1000)

    conn = get_connection()
    conn.execute('''
        INSERT OR IGNORE INTO microlearning_cards
        (id, query, source_item_id, source_node_id, source_domain,
         content, status, created_at)
        VALUES (?, ?, ?, ?, ?, '', 'pending', ?)
    ''', (card_id, query, source_item_id, source_node_id, source_domain, now_ms))
    conn.commit()
    conn.close()

    # Run research in background
    threading.Thread(
        target=_run_microlearning_research,
        args=(card_id, query, source_node_id, source_domain),
        daemon=True
    ).start()

    return card_id


def _run_microlearning_research(card_id: str, query: str,
                                 node_id: str | None, domain_id: str | None):
    """Background: run search + LLM, fill in the microlearning card."""
    from db import get_connection
    try:
        # Load node context if available
        node_title = ''
        node_description = ''
        if node_id and domain_id:
            conn = get_connection(readonly=True)
            row = conn.execute(
                'SELECT title, description FROM curriculum_nodes WHERE id=? AND domain_id=?',
                (node_id, domain_id)
            ).fetchone()
            conn.close()
            if row:
                node_title = row['title']
                node_description = row['description'] or ''

        # Search for factual accuracy via Claude with web search
        search_result = None
        try:
            from claude_llm import call_claude_search
            search_prompt = f"Research this question thoroughly: {query}"
            if node_title:
                search_prompt += f"\nContext: this relates to {node_title}"
            search_result = call_claude_search(search_prompt, timeout=120)
        except Exception as e:
            print(f'[microlearning] search failed for {card_id}: {e}', flush=True)

        # Generate structured microlearning card via Claude
        prompt = MICROLEARNING_PROMPT.format(
            query=query,
            node_title=node_title or 'General history',
            node_description=node_description or '(no curriculum context)',
        )
        if search_result:
            prompt += f"\n\nSearch results to incorporate:\n{search_result[:2000]}"

        result = call_claude_json(prompt, timeout=120)

        if not result or 'content' not in result:
            raise ValueError(f'Invalid response: {str(result)[:200] if result else "empty"}')

        # Update the card
        now_ms = int(time.time() * 1000)
        conn = get_connection()
        conn.execute('''
            UPDATE microlearning_cards SET
                content=?, question=?, answer_guidance=?,
                follow_up_queries=?, status='completed',
                due_at=?
            WHERE id=?
        ''', (
            result['content'],
            result.get('question', ''),
            result.get('answer_guidance', ''),
            json.dumps(result.get('follow_up_queries', [])),
            now_ms,  # due immediately
            card_id,
        ))
        conn.commit()
        conn.close()
        print(f'[microlearning] completed {card_id}: {query[:60]}', flush=True)

    except Exception as e:
        print(f'[microlearning] failed {card_id}: {e}', flush=True)
        import traceback; traceback.print_exc()
        try:
            conn = get_connection()
            conn.execute(
                "UPDATE microlearning_cards SET status='failed' WHERE id=?",
                (card_id,))
            conn.commit()
            conn.close()
        except Exception:
            pass


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

    questions = call_claude_json(prompt, timeout=120)
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


# ── Entity exploration ────────────────────────────────────────────────────────

ENTITY_EXPLORE_PROMPTS = {
    'place': """A learner tapped "Tell me more" on this place during a knowledge review session.

Entity: {name}
Description: {description}
Type: Place

Generate 3 research questions to deepen understanding of this place. Vary lenses:
1. Geographic/founding: Why was it located here? What strategic or economic factors?
2. Comparative: How does it compare to other places in the region or period?
3. Legacy: What remains today? What's its modern significance?

Output JSON only:
[{{"question":"...","lens":"...","suggested_source":"brief hint where to find the answer"}}]""",

    'person': """A learner tapped "Tell me more" on this person during a knowledge review session.

Entity: {name}
Description: {description}
Type: Person

Generate 3 research questions to deepen understanding of this person. Vary lenses:
1. Formative: What shaped their worldview or actions?
2. Impact: How did they change the course of events?
3. Legacy: How are they remembered? What's their modern significance?

Output JSON only:
[{{"question":"...","lens":"...","suggested_source":"brief hint where to find the answer"}}]""",

    'event': """A learner tapped "Tell me more" on this event during a knowledge review session.

Entity: {name}
Description: {description}
Type: Event

Generate 3 research questions to deepen understanding of this event. Vary lenses:
1. Causal: What chain of events led to this?
2. Consequences: What were the long-term effects?
3. Parallels: What similar events happened elsewhere or in other periods?

Output JSON only:
[{{"question":"...","lens":"...","suggested_source":"brief hint where to find the answer"}}]""",

    'default': """A learner tapped "Tell me more" on this entity during a knowledge review session.

Entity: {name}
Description: {description}

Generate 3 research questions to deepen understanding. Vary lenses:
1. Causal depth (why/how)
2. Comparative (relation to other periods/places/concepts)
3. Significance (consequences or modern relevance)

Output JSON only:
[{{"question":"...","lens":"...","suggested_source":"brief hint where to find the answer"}}]""",
}


def create_entity_exploration_items(entity: dict, domain_id: str, node_id: str, conn) -> list:
    """Generate 3 AI exploration prompts scoped to an entity and queue as review items."""
    entity_id = entity['entity_id']
    entity_type = entity.get('entity_type', '')
    now = int(time.time() * 1000)

    # Don't create duplicates — check for recent entity exploration items
    existing = conn.execute(
        """SELECT count(*) FROM review_items
           WHERE parent_item_id = ? AND item_type = 'exploration' AND due_at > ?""",
        (f'entity:{entity_id}', now - 7 * 24 * 60 * 60 * 1000)
    ).fetchone()[0]
    if existing > 0:
        return []

    prompt_template = ENTITY_EXPLORE_PROMPTS.get(entity_type, ENTITY_EXPLORE_PROMPTS['default'])
    prompt = prompt_template.format(
        name=entity.get('name', ''),
        description=entity.get('description', '')[:400],
    )

    questions = call_claude_json(prompt, timeout=120)
    if not isinstance(questions, list):
        return []

    # Look up node title for the review items
    node = conn.execute(
        'SELECT title FROM curriculum_nodes WHERE id = ? AND domain_id = ?',
        (node_id, domain_id)
    ).fetchone()
    node_title = node['title'] if node else entity.get('name', '')

    tomorrow = now + 24 * 60 * 60 * 1000
    created = []

    for i, q in enumerate(questions[:3]):
        child_id = f'entity:{entity_id}_explore_{i}_{now}'
        conn.execute("""
            INSERT INTO review_items
              (id, item_type, curriculum_domain, curriculum_node_id, curriculum_node_title,
               source_book_id, source_chapter_number, source_chapter_title,
               source_text, lens, parent_item_id, stability_days, due_at, review_count, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            child_id, 'exploration',
            domain_id, node_id, f'{node_title} — {entity.get("name", "")}',
            None, None, f'Entity exploration: {entity.get("name", "")}',
            q.get('question', ''), q.get('lens', 'SIGNIFICANCE'),
            f'entity:{entity_id}', 1.0, tomorrow, 0, now,
        ))
        created.append({
            'id': child_id,
            'question': q.get('question', ''),
            'lens': q.get('lens', ''),
            'suggested_source': q.get('suggested_source', ''),
        })

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

    extracted = call_claude_json(prompt, timeout=120)
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

    # Trigger microlearning for research-worthy questions
    ml_triggered = []
    for question in extracted.get('questions', [])[:2]:
        try:
            card_id = create_microlearning_request(
                query=question,
                source_item_id=item_id,
                source_node_id=item.get('curriculum_node_id'),
                source_domain=item.get('curriculum_domain'),
            )
            ml_triggered.append({'id': card_id, 'query': question})
            print(f'[voice→ml] memo question → {card_id}: {question[:60]}', flush=True)
        except Exception as e:
            print(f'[voice→ml] memo trigger failed: {e}', flush=True)

    result = {
        'transcript': transcript,
        'remembered': extracted.get('remembered', ''),
        'suggested_score': score,
        'connections': extracted.get('connections', []),
        'follow_ups_created': follow_ups,
        'microlearning_triggered': ml_triggered,
    }

    _log_voice_transcript(
        source='review_memo', node_id=item.get('curriculum_node_id', ''),
        domain_id=item.get('curriculum_domain', ''),
        node_title=item.get('curriculum_node_title', ''),
        transcript=transcript,
        audio_bytes=audio_path.stat().st_size if audio_path.exists() else 0,
        llm_result=extracted, ml_triggered=ml_triggered,
    )

    return result


# ── Voice elicitation (free recall) ─────────────────────────────────────────

def run_voice_elicitation(node_id: str, domain_id: str, audio_path: Path, conn, transcribe_fn) -> dict:
    """Run voice free-recall elicitation for a curriculum node or chapter recall.

    User speaks freely about what they know about a topic.
    System transcribes, compares against node definition + book sources, gives rich feedback.
    """
    # Handle chapter recall pseudo-nodes (chapter:{book_id}:{chapter_number})
    is_chapter_recall = node_id.startswith('chapter:')
    if is_chapter_recall:
        parts = node_id.split(':')
        book_id = parts[1] if len(parts) > 1 else ''
        chapter_num = parts[2] if len(parts) > 2 else ''
        # Look up chapter title and book from knowledge_items sources
        book_title = ''
        chapter_title = ''
        chapter_source_texts = []
        rows = conn.execute(
            "SELECT sources FROM knowledge_items WHERE curriculum_domain = ? AND sources LIKE ?",
            (domain_id, f'%{book_id}%')
        ).fetchall()
        for r in rows:
            try:
                sources = json.loads(r['sources'])
                for s in sources:
                    if str(s.get('chapter_number', '')) == str(chapter_num) and s.get('book_id') == book_id:
                        chapter_title = chapter_title or s.get('chapter_title', '')
                        book_title = book_title or s.get('book_title', book_id)
                        if s.get('source_text'):
                            chapter_source_texts.append(s['source_text'])
            except Exception:
                pass
        node = {
            'id': node_id,
            'title': f'Chapter {chapter_num}: {chapter_title}' if chapter_title else f'Chapter {chapter_num}',
            'description': f'What do you remember from Chapter {chapter_num} of {book_title}? Key ideas, people, events, and arguments.',
        }
    else:
        # Standard curriculum node
        curriculum = load_curriculum(domain_id)
        if not curriculum:
            return {'error': f'Curriculum {domain_id} not found'}

        node = None
        for n in curriculum.get('nodes', []):
            if n['id'] == node_id:
                node = n
                break
        if not node:
            return {'error': f'Node {node_id} not found'}

    # Release connection before slow work (transcription + LLM) to avoid lock
    conn.commit()

    # Transcribe
    print(f'[voice-elicit] Transcribing {audio_path} ({audio_path.stat().st_size} bytes)...', flush=True)
    transcript = transcribe_fn(audio_path)
    print(f'[voice-elicit] Transcript: {repr(transcript[:200]) if transcript else "EMPTY"}', flush=True)
    if not transcript:
        return {'error': 'Transcription failed'}

    # Gather sources — for chapter recall, use the chapter source texts we already found
    if is_chapter_recall and chapter_source_texts:
        sources_text = '\n'.join(chapter_source_texts[:5])
    else:
        sources_text = _gather_node_sources(node_id, domain_id, conn)
    print(f'[voice-elicit] Sources: {len(sources_text)} chars', flush=True)

    # Run LLM analysis
    prompt = VOICE_ELICITATION_PROMPT.format(
        node_title=node['title'],
        node_description=node['description'],
        sources_text=sources_text or 'No specific book sources available.',
        transcript=transcript,
    )

    result = call_claude_json(prompt, timeout=180)
    print(f'[voice-elicit] LLM result type={type(result).__name__}, keys={list(result.keys()) if isinstance(result, dict) else "N/A"}', flush=True)
    if not isinstance(result, dict):
        print(f'[voice-elicit] LLM returned non-dict: {repr(str(result)[:200])}', flush=True)
        result = {}

    # Generate temporal hook (skip for chapter recall — no curriculum node to anchor)
    temporal_hook = '' if is_chapter_recall else _generate_temporal_hook(node, domain_id, conn)
    result['temporal_hook'] = temporal_hook
    result['node_title'] = node['title']
    result['node_description'] = node['description']
    result['transcript'] = transcript

    # Process "wonderings" — create research triggers
    wonderings = result.get('wonderings', [])
    research_triggers = []
    for w in wonderings[:3]:
        trigger_id = f'wonder_{node_id}_{int(time.time() * 1000)}'
        try:
            conn.execute("""
                INSERT INTO review_items
                  (id, item_type, curriculum_domain, curriculum_node_id, curriculum_node_title,
                   source_text, lens, stability_days, due_at, review_count, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                trigger_id, 'voice_followup',
                domain_id, node_id, node['title'],
                w, 'SIGNIFICANCE', 1.0,
                int(time.time() * 1000) + 4 * 3600 * 1000,  # due in 4h
                0, int(time.time() * 1000),
            ))
            research_triggers.append({'id': trigger_id, 'question': w})
        except Exception:
            pass

    # Update knowledge state based on coverage
    coverage = result.get('coverage_pct', 50)
    score = result.get('suggested_score', 'partly')
    knowledge_level = 'anchored' if score == 'knew' else 'engaged' if score == 'partly' else 'mentioned'
    confidence = coverage / 100.0

    if is_chapter_recall:
        # Chapter recall covers multiple nodes — update all knowledge_items for this book+chapter
        if book_id and chapter_num:
            ki_rows = conn.execute(
                "SELECT id, curriculum_node_id FROM knowledge_items WHERE curriculum_domain = ? AND sources LIKE ?",
                (domain_id, f'%"chapter_number": {chapter_num}%' if chapter_num else f'%{book_id}%')
            ).fetchall()
            for ki in ki_rows:
                update_knowledge(domain_id, ki['curriculum_node_id'],
                                 knowledge=knowledge_level, confidence=confidence,
                                 source=f'voice_chapter_recall:{book_id}:{chapter_num}')  # opens own conn
    else:
        update_knowledge(domain_id, node_id, knowledge=knowledge_level,
                         confidence=confidence, source='voice_elicitation')  # opens own conn

    # Update knowledge_items if one exists for this node
    now_ms = int(time.time() * 1000)
    stability_mult = {'knew': 2.5, 'partly': 1.5, 'missed': 0.4}.get(score, 1.0)
    conn.execute("""
        UPDATE knowledge_items
        SET last_score = ?, last_reviewed_at = ?,
            stability_days = MIN(365.0, MAX(1.0, stability_days * ?)),
            due_at = ? + CAST(MIN(365.0, MAX(1.0, stability_days * ?)) * 86400000 AS INTEGER),
            review_count = review_count + 1,
            cached_question = NULL
        WHERE curriculum_node_id = ? AND curriculum_domain = ?
    """, (score, now_ms, stability_mult, now_ms, stability_mult, node_id, domain_id))

    conn.commit()

    result['research_triggers'] = research_triggers

    # Trigger microlearning for wonderings, research triggers, and top missed fact
    ml_triggered = []
    # Wonderings → microlearning (purest signal — user literally said "I wonder...")
    for w in wonderings[:2]:
        try:
            card_id = create_microlearning_request(
                query=w, source_node_id=node_id, source_domain=domain_id,
            )
            ml_triggered.append({'id': card_id, 'query': w})
            print(f'[voice→ml] wondering → {card_id}: {w[:60]}', flush=True)
        except Exception as e:
            print(f'[voice→ml] wondering trigger failed: {e}', flush=True)

    # Explicit research triggers from LLM extraction
    for trigger in result.get('research_triggers_raw', result.get('research_triggers', []))[:2]:
        q = trigger.get('question', '') if isinstance(trigger, dict) else str(trigger)
        if q and q not in [m['query'] for m in ml_triggered]:
            try:
                card_id = create_microlearning_request(
                    query=q, source_node_id=node_id, source_domain=domain_id,
                )
                ml_triggered.append({'id': card_id, 'query': q})
                print(f'[voice→ml] research trigger → {card_id}: {q[:60]}', flush=True)
            except Exception as e:
                print(f'[voice→ml] research trigger failed: {e}', flush=True)

    # Top missed critical fact → targeted microlearning
    missed = result.get('missed', [])
    if missed and len(ml_triggered) < 3:
        most_important = missed[0] if isinstance(missed[0], str) else str(missed[0])
        q = f'Why is this important to know: {most_important}'
        try:
            card_id = create_microlearning_request(
                query=q, source_node_id=node_id, source_domain=domain_id,
            )
            ml_triggered.append({'id': card_id, 'query': q})
            print(f'[voice→ml] missed fact → {card_id}: {q[:60]}', flush=True)
        except Exception as e:
            print(f'[voice→ml] missed trigger failed: {e}', flush=True)

    result['microlearning_triggered'] = ml_triggered

    # Persist transcript for later analysis
    _log_voice_transcript(
        source='elicitation', node_id=node_id, domain_id=domain_id,
        node_title=node['title'], transcript=transcript,
        audio_bytes=audio_path.stat().st_size if audio_path.exists() else 0,
        llm_result=result, ml_triggered=ml_triggered,
    )

    return result


def _gather_node_sources(node_id: str, domain_id: str, conn) -> str:
    """Gather all book source texts for a curriculum node."""
    rows = conn.execute("""
        SELECT sources FROM knowledge_items
        WHERE curriculum_node_id = ? AND curriculum_domain = ?
    """, (node_id, domain_id)).fetchall()

    parts = []
    for row in rows:
        try:
            sources = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            if isinstance(sources, list):
                for s in sources:
                    if isinstance(s, dict):
                        book_title = s.get('book_title', s.get('book_id', 'Unknown book'))
                        chapter = s.get('chapter_title', '')
                        text = s.get('source_text', '')
                        if text:
                            parts.append(f"From {book_title}" + (f", {chapter}" if chapter else "") + f": {text}")
        except (json.JSONDecodeError, TypeError):
            pass

    return '\n'.join(parts) if parts else ''


def _generate_temporal_hook(node: dict, domain_id: str, conn) -> str:
    """Generate a temporal hook by finding overlapping nodes in other curricula."""
    date_start = node.get('date_start')
    date_end = node.get('date_end')
    if date_start is None:
        return ''

    if date_end is None:
        date_end = date_start

    # Find nodes in OTHER curricula with overlapping dates where user has knowledge
    try:
        rows = conn.execute("""
            SELECT cn.title, cn.date_start, cn.date_end, cd.title as domain_title,
                   ks.knowledge, ks.confidence
            FROM curriculum_nodes cn
            JOIN curriculum_domains cd ON cn.domain_id = cd.id
            LEFT JOIN knowledge_states ks ON ks.node_id = cn.id AND ks.domain_id = cn.domain_id
            WHERE cn.domain_id != ?
              AND cn.date_start IS NOT NULL
              AND cn.date_start <= ? AND COALESCE(cn.date_end, cn.date_start) >= ?
              AND (ks.knowledge IN ('engaged', 'anchored') OR ks.confidence > 0.5)
            ORDER BY ks.confidence DESC
            LIMIT 3
        """, (domain_id, date_end + 50, date_start - 50)).fetchall()

        if rows:
            best = rows[0]
            return f"Contemporaneous with {best[0]} ({best[3]})"
    except Exception:
        pass

    return ''


def _elicitation_candidates_for_domain(domain_id: str, conn) -> list[dict]:
    """Get elicitation candidates for a single domain (internal helper)."""
    curriculum = load_curriculum(domain_id)
    if not curriculum:
        return []

    # Get domain title
    row = conn.execute('SELECT title FROM curriculum_domains WHERE id = ?', (domain_id,)).fetchone()
    domain_title = row['title'] if row else domain_id.replace('_', ' ').title()

    rows = conn.execute("""
        SELECT node_id, knowledge, confidence
        FROM knowledge_states
        WHERE domain_id = ?
    """, (domain_id,)).fetchall()

    states = {r[0]: {'knowledge': r[1], 'confidence': r[2]} for r in rows}

    # Exclude nodes that already have a voice transcript (elicitation is mapping, not drilling)
    recent_nodes = set()
    try:
        recent_rows = conn.execute(
            "SELECT node_id FROM voice_transcripts WHERE domain_id = ? AND source = 'elicitation'",
            (domain_id,)
        ).fetchall()
        recent_nodes = {r[0] for r in recent_rows}
    except Exception:
        pass  # table might not exist yet

    candidates = []
    for node in curriculum.get('nodes', []):
        if node['level'] < 2:
            continue  # skip Area-level nodes
        state = states.get(node['id'], {})
        knowledge = state.get('knowledge', 'unknown')
        confidence = state.get('confidence', 0.0)

        if knowledge == 'unknown':
            continue  # nothing to recall
        if node['id'] in recent_nodes:
            continue  # already recalled recently

        # Score: prefer medium confidence (peak at 0.5)
        score = 1.0 - abs(confidence - 0.5) * 2  # peaks at 0.5
        if knowledge == 'engaged':
            score += 0.3  # bonus for engaged (most to gain)
        elif knowledge == 'mentioned':
            score += 0.1

        candidates.append({
            'node_id': node['id'],
            'node_title': node['title'],
            'node_description': node['description'],
            'domain_id': domain_id,
            'domain_title': domain_title,
            'knowledge': knowledge,
            'confidence': confidence,
            'elicitation_score': round(score, 2),
        })

    return candidates


def get_elicitation_candidates(domain_id: str | None = None, limit: int = 8, conn=None) -> list[dict]:
    """Get curriculum nodes suitable for voice elicitation.

    Prioritizes: medium-confidence nodes (engaged, 0.3-0.7) where voice recall
    would be most informative. Avoids unknown (nothing to recall) and anchored
    (already well-known).

    If domain_id is None, returns candidates from ALL domains where the user
    has engaged/anchored nodes, merged and sorted by elicitation_score.
    """
    own = conn is None
    if own:
        from db import get_connection
        conn = get_connection(readonly=True)

    try:
        if domain_id:
            candidates = _elicitation_candidates_for_domain(domain_id, conn)
        else:
            # Find all domains with engaged/anchored nodes
            domain_rows = conn.execute("""
                SELECT DISTINCT domain_id FROM knowledge_states
                WHERE knowledge IN ('engaged', 'anchored', 'mentioned')
            """).fetchall()
            candidates = []
            for row in domain_rows:
                candidates.extend(_elicitation_candidates_for_domain(row[0], conn))

        # Add chapter recall candidates — "What do you remember from Chapter X?"
        chapter_recalls = _chapter_recall_candidates(conn, limit=2)

        # Interleave domains for variety (don't let one domain dominate)
        from collections import defaultdict
        domain_groups: dict[str, list] = defaultdict(list)
        for c in candidates:
            domain_groups[c['domain_id']].append(c)
        for g in domain_groups.values():
            g.sort(key=lambda c: c['elicitation_score'], reverse=True)

        interleaved = []
        sorted_domains = sorted(domain_groups.keys(),
                                key=lambda d: len(domain_groups[d]), reverse=True)
        idx = 0
        while len(interleaved) < len(candidates):
            added = False
            for d in sorted_domains:
                if idx < len(domain_groups[d]):
                    interleaved.append(domain_groups[d][idx])
                    added = True
            if not added:
                break
            idx += 1

        # Mix in chapter recalls (max 2, interspersed)
        result = []
        ch_idx = 0
        for i, c in enumerate(interleaved):
            if i > 0 and i % 3 == 0 and ch_idx < len(chapter_recalls):
                result.append(chapter_recalls[ch_idx])
                ch_idx += 1
            result.append(c)
        # Append remaining chapter recalls
        while ch_idx < len(chapter_recalls):
            result.append(chapter_recalls[ch_idx])
            ch_idx += 1

        return result[:limit]
    finally:
        if own:
            conn.close()


def _chapter_recall_candidates(conn, limit: int = 2) -> list[dict]:
    """Generate chapter-specific recall prompts from knowledge_items sources.

    Finds recent book chapters that have curriculum mappings and creates
    prompts like "What do you remember from Chapter 5: The Founding of Syracuse?"
    """
    # Find distinct book+chapter combos from knowledge_items sources
    rows = conn.execute("""
        SELECT ki.curriculum_domain, ki.sources, pb.title as book_title
        FROM knowledge_items ki
        LEFT JOIN physical_books pb ON pb.id = json_extract(ki.sources, '$[0].book_id')
        WHERE ki.sources LIKE '%chapter_number%'
          AND ki.review_count <= 1
        ORDER BY ki.created_at DESC
        LIMIT 50
    """).fetchall()

    # Exclude chapters already elicited
    already_elicited = set()
    try:
        elicited_rows = conn.execute(
            "SELECT node_id FROM voice_transcripts WHERE source = 'elicitation' AND node_id LIKE 'chapter:%'"
        ).fetchall()
        already_elicited = {r[0] for r in elicited_rows}
    except Exception:
        pass

    seen_chapters = set()
    candidates = []
    for r in rows:
        try:
            sources = json.loads(r['sources'])
        except Exception:
            continue
        for s in sources:
            ch_num = s.get('chapter_number')
            ch_title = s.get('chapter_title', '')
            book_id = s.get('book_id', '')
            if not ch_num or not ch_title:
                continue
            node_id = f'chapter:{book_id}:{ch_num}'
            key = f'{book_id}:{ch_num}'
            if key in seen_chapters or node_id in already_elicited:
                continue
            seen_chapters.add(key)

            book_title = r['book_title'] or book_id
            candidates.append({
                'type': 'chapter_recall',
                'node_id': f'chapter:{book_id}:{ch_num}',
                'node_title': f'Chapter {ch_num}: {ch_title}',
                'node_description': f'What do you remember from Chapter {ch_num} of {book_title}? '
                                   f'Speak freely about the key ideas, people, and events.',
                'domain_id': r['curriculum_domain'],
                'knowledge': 'engaged',
                'confidence': 0.5,
                'elicitation_score': 1.5,  # slightly above curriculum nodes
                'book_id': book_id,
                'book_title': book_title,
                'chapter_number': ch_num,
                'chapter_title': ch_title,
            })

            if len(candidates) >= limit:
                break
        if len(candidates) >= limit:
            break

    return candidates


# ── Article-read curriculum updates ──────────────────────────────────────────

def notify_article_read_curriculum(article_id: str, conn) -> dict:
    """When an article is read, update curriculum knowledge states for mapped nodes.

    Returns node_details with titles and domain info for client display.
    """
    rows = conn.execute("""
        SELECT acn.node_id, acn.domain_id, acn.node_title, acn.claim_count, acn.avg_similarity,
               cd.title AS domain_title
        FROM article_curriculum_nodes acn
        LEFT JOIN curriculum_domains cd ON cd.id = acn.domain_id
        WHERE acn.article_id = ?
    """, (article_id,)).fetchall()

    if not rows:
        return {'nodes_updated': 0, 'node_details': []}

    updated = 0
    nodes = []
    node_details = []
    for row in rows:
        node_id, domain_id = row['node_id'], row['domain_id']
        claim_count, avg_sim = row['claim_count'], row['avg_similarity']
        # Only update if the mapping is strong enough
        if claim_count >= 2 or avg_sim >= 0.70:
            current = conn.execute(
                "SELECT knowledge, confidence FROM knowledge_states WHERE node_id = ? AND domain_id = ?",
                (node_id, domain_id)
            ).fetchone()

            if current is None or current['knowledge'] == 'unknown':
                update_knowledge(domain_id, node_id, knowledge='mentioned',
                                 confidence=0.2, source=f'article:{article_id}')
                updated += 1
                nodes.append(node_id)
                node_details.append({
                    'node_id': node_id,
                    'node_title': row['node_title'] or node_id.replace('_', ' ').title(),
                    'domain_id': domain_id,
                    'domain_title': row['domain_title'] or domain_id,
                })
            elif current['knowledge'] == 'mentioned':
                # Bump confidence slightly for additional article encounters
                new_conf = min(0.5, (current['confidence'] or 0.2) + 0.05)
                update_knowledge(domain_id, node_id, knowledge='mentioned',
                                 confidence=new_conf, source=f'article:{article_id}')
                updated += 1
                nodes.append(node_id)
                node_details.append({
                    'node_id': node_id,
                    'node_title': row['node_title'] or node_id.replace('_', ' ').title(),
                    'domain_id': domain_id,
                    'domain_title': row['domain_title'] or domain_id,
                })

    return {'nodes_updated': updated, 'nodes': nodes, 'node_details': node_details}


# ── Hamarquizen sessions ─────────────────────────────────────────────────────

def generate_hamarquizen_session(book_id: str, limit: int = 5, conn=None) -> list[dict]:
    """Generate Hamarquizen PRIME->READ->TEST cards for a finished book."""
    own = conn is None
    if own:
        from db import get_connection
        conn = get_connection(readonly=True)

    try:
        row = conn.execute(
            'SELECT title, author, topics FROM physical_books WHERE id=?', (book_id,)
        ).fetchone()
        if not row:
            return []

        book_title = row['title']
        book_author = row['author'] or ''

        # Find knowledge_items linked to this book, ordered by lowest confidence first
        items = conn.execute("""
            SELECT ki.id, ki.curriculum_node_id, ki.curriculum_domain,
                   ki.sources, ki.review_count, ki.stability_days,
                   ks.knowledge, ks.confidence
            FROM knowledge_items ki
            LEFT JOIN knowledge_states ks
              ON ks.node_id = ki.curriculum_node_id AND ks.domain_id = ki.curriculum_domain
            WHERE ki.sources LIKE ?
            ORDER BY COALESCE(ks.confidence, 0.5) ASC, ki.review_count ASC
            LIMIT ?
        """, (f'%{book_id}%', limit * 3)).fetchall()

        if not items:
            return []

        cards = []
        curriculum_cache: dict = {}

        for item_row in items:
            if len(cards) >= limit:
                break

            item_id = item_row['id']
            node_id = item_row['curriculum_node_id']
            domain_id = item_row['curriculum_domain']
            sources_raw = item_row['sources']
            knowledge = item_row['knowledge'] or 'unknown'
            confidence = item_row['confidence'] or 0.0

            # Get source text for this node from this book
            source_text = ''
            try:
                sources = json.loads(sources_raw) if isinstance(sources_raw, str) else sources_raw
                if isinstance(sources, list):
                    for s in sources:
                        if isinstance(s, dict) and s.get('book_id') == book_id:
                            source_text = s.get('source_text', '')
                            break
            except (json.JSONDecodeError, TypeError):
                pass

            # Load curriculum and find node description
            if domain_id not in curriculum_cache:
                curriculum_cache[domain_id] = load_curriculum(domain_id)
            curriculum = curriculum_cache[domain_id]

            node_title = node_id
            node_desc = ''
            if curriculum:
                for n in curriculum.get('nodes', []):
                    if n['id'] == node_id:
                        node_title = n.get('title', node_id)
                        node_desc = n.get('description', '')
                        break

            prompt = HAMARQUIZEN_PROMPT.format(
                book_title=book_title,
                book_author=book_author or 'Unknown',
                node_title=node_title,
                node_description=node_desc,
                source_text=source_text or 'No specific source text available',
                knowledge_level=knowledge,
                confidence=confidence,
            )

            card_data = call_claude_json(prompt, timeout=120)
            if not isinstance(card_data, dict):
                card_data = {}

            if card_data.get('test'):
                cards.append({
                    'item_id': item_id,
                    'node_id': node_id,
                    'domain_id': domain_id,
                    'node_title': node_title,
                    'book_id': book_id,
                    'book_title': book_title,
                    'prime': card_data.get('prime', ''),
                    'read': card_data.get('read', ''),
                    'test': card_data.get('test', ''),
                    'answer': card_data.get('answer', ''),
                    'temporal_hook': card_data.get('temporal_hook', ''),
                    'knowledge': knowledge,
                    'confidence': confidence,
                })

        return cards
    finally:
        if own:
            conn.close()


CROSS_BOOK_HAMARQUIZEN_PROMPT = """Generate a cross-book comparison micro-lesson.

Two books cover the same historical topic from different angles:

Topic: {node_title}
Definition: {node_description}

Book A: "{book_a_title}" — {source_a}
Book B: "{book_b_title}" — {source_b}

Create a PRIME->READ->TEST sequence that COMPARES the two perspectives:

1. PRIME: "What do you remember about [topic] from your reading?" (8-15 words)

2. READ: 3-4 sentences that juxtapose the two books' treatments. What does Book A emphasize that Book B doesn't? What's the same event seen from two angles? Include specific names, dates, details from both. Make the comparison vivid — this is not a summary, it's a dialogue between two authors.

3. TEST: A question (6-12 words) that requires understanding BOTH perspectives. "Why might [Author A] and [Author B] emphasize different aspects of [event]?" or "What does the contrast between [X] and [Y] reveal about [topic]?"

4. ANSWER: 2 sentences explaining the comparative insight.

5. TEMPORAL_HOOK: One cross-period anchor.

Output JSON:
{{"prime":"...","read":"...","test":"...","answer":"...","temporal_hook":"..."}}"""


def generate_cross_book_hamarquizen(limit: int = 5, conn=None) -> list[dict]:
    """Generate cross-book comparison Hamarquizen cards for curriculum nodes covered by 2+ books."""
    own = conn is None
    if own:
        from db import get_connection
        conn = get_connection(readonly=True)

    try:
        # Find curriculum nodes with knowledge_items sourced from 2+ different books
        rows = conn.execute("""
            SELECT ki.curriculum_node_id, ki.curriculum_domain, ki.sources, ki.id AS item_id
            FROM knowledge_items ki
            WHERE ki.sources IS NOT NULL AND ki.sources != '[]'
        """).fetchall()

        # Group by node, collect distinct book sources
        from collections import defaultdict
        node_books: dict[tuple[str, str], list[dict]] = defaultdict(list)
        node_item_ids: dict[tuple[str, str], str] = {}

        for row in rows:
            node_id = row['curriculum_node_id']
            domain_id = row['curriculum_domain']
            item_id = row['item_id']
            key = (domain_id, node_id)
            node_item_ids[key] = item_id
            try:
                sources = json.loads(row['sources']) if isinstance(row['sources'], str) else row['sources']
                if isinstance(sources, list):
                    for s in sources:
                        if isinstance(s, dict) and s.get('book_id'):
                            node_books[key].append(s)
            except (json.JSONDecodeError, TypeError):
                pass

        # Filter to nodes with 2+ distinct books
        multi_book_nodes = []
        for key, sources in node_books.items():
            book_ids = list({s['book_id'] for s in sources})
            if len(book_ids) >= 2:
                multi_book_nodes.append((key, sources, book_ids))

        if not multi_book_nodes:
            return []

        # Load book titles
        all_book_ids = set()
        for _, _, bids in multi_book_nodes:
            all_book_ids.update(bids)

        book_titles = {}
        for bid in all_book_ids:
            brow = conn.execute('SELECT title FROM physical_books WHERE id=?', (bid,)).fetchone()
            if brow:
                book_titles[bid] = brow['title']

        # Build cards (limit * 3 attempts, stop at limit)
        cards = []
        curriculum_cache: dict = {}

        for (domain_id, node_id), sources, book_ids in multi_book_nodes[:limit * 3]:
            if len(cards) >= limit:
                break

            # Get node metadata
            if domain_id not in curriculum_cache:
                curriculum_cache[domain_id] = load_curriculum(domain_id)
            curriculum = curriculum_cache[domain_id]

            node_title = node_id
            node_desc = ''
            if curriculum:
                for n in curriculum.get('nodes', []):
                    if n['id'] == node_id:
                        node_title = n.get('title', node_id)
                        node_desc = n.get('description', '')
                        break

            # Pick first two distinct books
            book_a_id, book_b_id = book_ids[0], book_ids[1]
            source_a = ''
            source_b = ''
            for s in sources:
                if s.get('book_id') == book_a_id and not source_a:
                    source_a = s.get('source_text', '')
                elif s.get('book_id') == book_b_id and not source_b:
                    source_b = s.get('source_text', '')

            book_a_title = book_titles.get(book_a_id, book_a_id)
            book_b_title = book_titles.get(book_b_id, book_b_id)

            prompt = CROSS_BOOK_HAMARQUIZEN_PROMPT.format(
                node_title=node_title,
                node_description=node_desc,
                book_a_title=book_a_title,
                source_a=source_a or 'No specific source text available',
                book_b_title=book_b_title,
                source_b=source_b or 'No specific source text available',
            )

            card_data = call_claude_json(prompt, timeout=120)
            if not isinstance(card_data, dict):
                card_data = {}

            if card_data.get('test'):
                item_id = node_item_ids.get((domain_id, node_id), f'{domain_id}:{node_id}')
                cards.append({
                    'item_id': item_id,
                    'node_id': node_id,
                    'domain_id': domain_id,
                    'node_title': node_title,
                    'book_id': book_a_id,
                    'book_title': book_a_title,
                    'book_b_id': book_b_id,
                    'book_b_title': book_b_title,
                    'prime': card_data.get('prime', ''),
                    'read': card_data.get('read', ''),
                    'test': card_data.get('test', ''),
                    'answer': card_data.get('answer', ''),
                    'temporal_hook': card_data.get('temporal_hook', ''),
                    'knowledge': 'engaged',
                    'confidence': 0.5,
                })

        return cards
    finally:
        if own:
            conn.close()

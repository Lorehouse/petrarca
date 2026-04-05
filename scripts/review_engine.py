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
from curriculum_db import load_curriculum, list_curricula, update_knowledge, load_knowledge_states

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


FOLLOW_UP_PROMPT = """A history reader just reviewed a topic. Generate 3 follow-up research questions
that go SIDEWAYS — exploring adjacent angles the card didn't cover, not drilling deeper into
what was already said. The reader should think "oh, I never thought about it from THAT angle."

Topic: {node_title}
Topic description: {node_description}
Specific fact just reviewed: {fact_context}

VARIETY IS ESSENTIAL. Each question should take a DIFFERENT angle. Prioritize these:
- GEOGRAPHY AS EXPLANATION: Why HERE specifically? What about the landscape, harbors, climate,
  trade routes explains why this happened in this place?
  (e.g., "Why did the Greek-Carthaginian border run exactly where it did — what was special about the Halycus river?")
- STRUCTURAL / SYSTEMIC: What institutional, economic, or social structure made this possible or inevitable?
  (e.g., "How did the Norman feudal system interact with the existing Arab land-tenure system?")
- TRANSMISSION & RECEPTION: How did knowledge of this reach us? Who carried it, translated it, debated it?
  (e.g., "How did Western scholars actually access Greek manuscripts in Constantinople before 1453?")
- COUNTER-NARRATIVES: What did the OTHER side think? The conquered, the losers, the minority voices?
  (e.g., "What do we know about how ordinary Sicilian Muslims experienced the Norman conquest?")
- CONNECTED FIGURES: Fascinating people adjacent to this story the reader hasn't met yet
  (e.g., "Who was George of Antioch, and why did a Greek Orthodox Syrian become Roger II's chief minister?")
- MODERN ECHOES: What modern institution, place name, legal concept, or cultural practice traces back here?
  (e.g., "Which Sicilian place names are actually Arabic, and what do they reveal about settlement patterns?")
- ART & CULTURAL AFTERLIFE: Opera, theatre, poetry, novels, films — how this event lives in culture
  (e.g., "Which Verdi opera dramatizes the Sicilian Vespers, and how accurate is it?")

Rules:
- Be SPECIFIC — name real people, places, events, dates. Never generic.
- DO NOT ask about things already covered in the card content. Go sideways, not deeper.
- NO templates like "How does X connect to Y?" or "What was happening elsewhere?" or "Tell me more about X"
- Each question should feel like it could be its own microlearning rabbit hole

Output JSON array of 3 strings only: ["q1","q2","q3"]"""


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
2. MISSED: The 2-3 most structurally important omissions — facts that serve as scaffolding for understanding the broader topic (key dates, actors, causal relationships). Prefer load-bearing facts over colorful details.
3. INTERESTING: Things the learner said that go BEYOND the sources — personal connections, questions, hypotheses, links to other topics. These are valuable signals.
4. WONDERINGS: Extract ALL questioning or curious statements — "I wonder...", "I'm not sure if...", "was it...?", "I'd like to know...", hedged questions, speculative connections, anything where the learner is reaching beyond what they know. These are the most valuable signals — err on the side of including too many. Rephrase as clear research questions.
5. RESEARCH_QUESTIONS: Specific questions that could be researched to deepen the learner's understanding. Derive from wonderings, gaps in knowledge, and interesting but uncertain claims. Frame as searchable questions.

If the learner demonstrates extensive knowledge about adjacent or broader topics beyond the node definition, acknowledge this in feedback_summary and give partial credit in coverage_pct for related knowledge that connects to this topic.

Output JSON:
{{"captured": ["fact1", "fact2"], "missed": ["important_fact1", "important_fact2"], "interesting": ["connection1"], "wonderings": ["I wonder if X was related to Y", "Was it Z who did this?", "I'm curious whether..."], "research_questions": ["What was the relationship between X and Y?", "Did Z lead to the outcome described?"], "coverage_pct": 65, "suggested_score": "knew|partly|missed", "feedback_summary": "2-3 sentence personalized feedback highlighting what was strong and what key thing was missed"}}"""


VOICE_CAPTURE_ANALYSIS_PROMPT = """Analyze a voice capture where a learner describes what they know about a topic.
This is NOT a recall test — the learner is freely sharing knowledge from a podcast, book, conversation, or their own thinking.
Your job is to extract concrete facts, map them to curriculum nodes, and identify wonderings.

{context_section}

CURRICULUM NODES (candidate matches — the learner's knowledge may touch any of these):
{nodes_list}

LEARNER'S VOICE CAPTURE (transcribed speech):
{transcript}

Instructions:
1. Extract every concrete FACT the learner states or implies. Be thorough — include dates, names, events, causal claims, and connections. Each fact should be a standalone statement.
2. Map each fact to the most relevant curriculum node from the list above. Use the exact node_id. A fact can map to multiple nodes if relevant. CRITICAL MAPPING RULE: Only map a fact to a node if the fact is GENUINELY ABOUT that node's subject matter. The fact must belong to the same historical period and topic as the node. Do NOT map medieval facts to ancient nodes or vice versa. Do NOT map facts to nodes just because they share a word (e.g., a medieval monk writing is NOT about the Roman historian Tacitus; Arab prisoners are NOT about Roman slavery; medieval church politics is NOT about Roman religion). When in doubt, leave the fact unmapped rather than force a bad match.
3. For each node that has at least one mapped fact, assess the knowledge demonstrated:
   - "anchored": learner shows confident, detailed knowledge (multiple facts, connections, temporal placement)
   - "engaged": learner demonstrates real knowledge but with gaps or uncertainty
   - "mentioned": learner references the topic but with little substance
4. Extract ALL wonderings, questions, uncertainties, "I think...", "I'm not sure if...", speculative statements. These are the most valuable signals. Rephrase as clear research questions.

Output JSON:
{{"facts": [{{"fact": "specific factual claim", "node_ids": ["node_id_1"], "source_excerpt": "relevant 1-2 sentences from transcript"}}],
"node_assessments": [{{"node_id": "...", "node_title": "...", "knowledge_level": "anchored|engaged|mentioned", "fact_count": 3, "summary": "brief summary of what learner knows about this node"}}],
"wonderings": ["research question 1", "research question 2"],
"entities_mentioned": ["entity name 1", "entity name 2"],
"overall_summary": "2-3 sentence summary of what the learner shared"}}"""


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
                          chapter_number: int, chapter_title: str,
                          domain_id: str | None = None) -> list:
    """Map a chapter to curriculum nodes in a specific domain.

    If domain_id is None, auto-detects via detect_curriculum().
    """
    if not domain_id:
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
    """Create knowledge_items for prerequisites of mapped nodes.

    Only creates items for Level 2+ prerequisite nodes that don't already exist.
    Enriches gap-fill sources with book_curriculum_mappings when available,
    rather than relying solely on the curriculum node description.
    Returns count of gap-fill items created.
    """
    curriculum = load_curriculum(domain_id)
    if not curriculum:
        return 0

    nodes_by_id = {n['id']: n for n in curriculum['nodes']}
    gaps_created = 0

    # Only expand prerequisites (not siblings — too speculative)
    candidate_ids: set = set()
    for node_id in mapped_node_ids:
        node = nodes_by_id.get(node_id, {})
        for prereq_id in node.get('prerequisites', []):
            prereq = nodes_by_id.get(prereq_id, {})
            if prereq.get('level', 1) >= 2:
                candidate_ids.add(prereq_id)

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

        # Try to enrich with book content: check if any book covers this node
        book_source = conn.execute("""
            SELECT bcm.book_id, bcm.coverage, pb.title as book_title
            FROM book_curriculum_mappings bcm
            LEFT JOIN physical_books pb ON pb.id = bcm.book_id
            WHERE bcm.domain_id = ? AND bcm.node_id = ?
            ORDER BY CASE bcm.coverage
                WHEN 'deep' THEN 0 WHEN 'moderate' THEN 1 ELSE 2 END
            LIMIT 1
        """, (domain_id, cand_id)).fetchone()

        if book_source:
            source = {
                'book_id': book_source['book_id'],
                'chapter_number': None,
                'chapter_title': f"Covered in: {book_source['book_title'] or book_source['book_id']}",
                'source_text': node.get('description', '')[:400],
                'lens': 'SIGNIFICANCE',
                'temporal_hook': '',
                'added_at': now,
                'coverage': book_source['coverage'],
            }
        else:
            source = {
                'book_id': None,
                'chapter_number': None,
                'chapter_title': 'Prerequisite — not yet covered by a book',
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


def _upsert_chapter_mappings(domain_id: str, mappings: list, book_id: str,
                              chapter_number: int, chapter_title: str,
                              conn, now: int) -> tuple[int, int, int, list]:
    """Upsert knowledge_items for one domain's chapter mappings. Returns (created, updated, gaps, titles)."""
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
    return created, updated, gaps_filled, node_titles


def create_review_items_for_chapter(book_id: str, book_title: str, book_topics: list,
                                     chapter_number: int, chapter_title: str, conn) -> dict:
    """Map chapter to curriculum nodes across multiple domains and upsert into knowledge_items.

    Maps against the primary domain plus up to 2 secondary domains (score >= 0.40)
    to realize the overlapping-curricula vision.
    """
    # Find relevant curricula ranked by similarity
    suggestions = suggest_curricula_for_book(book_title, book_topics)
    primary_domain = detect_curriculum(book_title, book_topics)

    # Build ordered list: primary first, then high-scoring secondaries
    SECONDARY_THRESHOLD = 0.40
    MAX_SECONDARY = 2
    domains_to_map = [primary_domain]
    for s in suggestions:
        if s['id'] == primary_domain:
            continue
        if s['score'] >= SECONDARY_THRESHOLD and len(domains_to_map) <= MAX_SECONDARY:
            domains_to_map.append(s['id'])

    now = int(time.time() * 1000)
    total_created = 0
    total_updated = 0
    total_gaps = 0
    all_node_titles = []
    all_items_to_pregen = []
    domains_mapped = []

    for domain_id in domains_to_map:
        mappings = map_chapter_to_nodes(
            book_id, book_title, book_topics,
            chapter_number, chapter_title,
            domain_id=domain_id,
        )
        if not mappings:
            continue

        created, updated, gaps, titles = _upsert_chapter_mappings(
            domain_id, mappings, book_id, chapter_number, chapter_title, conn, now,
        )
        total_created += created
        total_updated += updated
        total_gaps += gaps
        all_node_titles.extend(titles)
        domains_mapped.append(domain_id)

        # Collect items needing question pre-generation
        mapped_ids = [m['node_id'] for m in mappings]
        items = conn.execute(
            '''SELECT id FROM knowledge_items
               WHERE curriculum_domain=? AND cached_question IS NULL
                 AND id IN ({})'''.format(','.join('?' * len(mapped_ids))),
            [domain_id] + [f"{domain_id}:{nid}" for nid in mapped_ids]
        ).fetchall()
        all_items_to_pregen.extend(r['id'] for r in items)

        is_secondary = domain_id != primary_domain
        label = f'(secondary)' if is_secondary else '(primary)'
        print(f'[review] Ch{chapter_number} → {domain_id} {label}: '
              f'{created} created, {updated} updated, {gaps} gaps → {titles}', flush=True)

    if not domains_mapped:
        return {'nodes_covered': [], 'items_created': 0, 'items_updated': 0,
                'gaps_filled': 0, 'domain': primary_domain, 'domains_mapped': []}

    conn.commit()

    # Pre-generate questions in background
    if all_items_to_pregen:
        ids_to_gen = list(all_items_to_pregen)
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
        'nodes_covered': all_node_titles,
        'items_created': total_created,
        'items_updated': total_updated,
        'gaps_filled': total_gaps,
        'domain': primary_domain,
        'domains_mapped': domains_mapped,
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


def _generate_follow_up_queries(node_title: str, node_description: str,
                                fact_context: str = '') -> list[str]:
    """Generate 3 LLM-powered follow-up queries for a review item.
    Returns empty list on failure (caller should fall back to templates)."""
    try:
        prompt = FOLLOW_UP_PROMPT.format(
            node_title=node_title,
            node_description=node_description[:500],
            fact_context=fact_context or '(general review)',
        )
        fq = call_claude_json(prompt, timeout=60, model='sonnet')
        if isinstance(fq, list) and len(fq) >= 2:
            return fq[:3]
    except Exception as e:
        print(f'[review] follow-up gen failed for {node_title}: {e}', flush=True)
    return []


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


def _get_cross_curriculum_context(domain_id: str, node_id: str, conn) -> str:
    """Find what the learner knows about related entities from OTHER curricula.

    Queries shared_entities → entity_curriculum_links → knowledge_states to find
    cross-domain perspectives the learner already has on entities in this node.
    Returns a context string for question generation prompts.
    """
    # Find entities linked to this node
    entity_rows = conn.execute("""
        SELECT ecl.entity_id, se.name, ecl.lens_title
        FROM entity_curriculum_links ecl
        JOIN shared_entities se ON se.entity_id = ecl.entity_id
        WHERE ecl.domain_id = ? AND ecl.node_id = ?
    """, (domain_id, node_id)).fetchall()

    if not entity_rows:
        return ''

    entity_ids = [r['entity_id'] for r in entity_rows]
    # Find these entities in OTHER domains where the learner has engaged/anchored knowledge
    cross_perspectives = []
    for eid in entity_ids[:5]:
        rows = conn.execute("""
            SELECT ecl.domain_id, ecl.node_id, ecl.lens_title, ecl.lens_emphasis,
                   se.name as entity_name,
                   ks.knowledge, cn.title as node_title, cd.title as domain_title
            FROM entity_curriculum_links ecl
            JOIN shared_entities se ON se.entity_id = ecl.entity_id
            LEFT JOIN knowledge_states ks ON ks.domain_id = ecl.domain_id AND ks.node_id = ecl.node_id
            LEFT JOIN curriculum_nodes cn ON cn.id = ecl.node_id AND cn.domain_id = ecl.domain_id
            LEFT JOIN curriculum_domains cd ON cd.id = ecl.domain_id
            WHERE ecl.entity_id = ?
              AND ecl.domain_id != ?
              AND ks.knowledge IN ('engaged', 'anchored')
        """, (eid, domain_id)).fetchall()

        for r in rows:
            lens = r['lens_title'] or r['lens_emphasis'] or r['node_title'] or ''
            cross_perspectives.append(
                f"- {r['entity_name']}: learner knows this from {r['domain_title']} "
                f"({r['knowledge']}) — {lens}"
            )

    if not cross_perspectives:
        return ''

    return ('Cross-curriculum context (the learner knows these entities from other domains):\n'
            + '\n'.join(cross_perspectives[:5]))


def _get_temporal_cross_references(domain_id: str, node_id: str, conn) -> str:
    """Find events in OTHER curricula happening at the same time as this node.

    Uses date_start/date_end on curriculum_nodes to find contemporaneous events
    the learner already knows about in different domains.
    """
    # Get this node's date range
    node_row = conn.execute(
        'SELECT date_start, date_end FROM curriculum_nodes WHERE id=? AND domain_id=?',
        (node_id, domain_id)
    ).fetchone()
    if not node_row or node_row['date_start'] is None:
        return ''

    date_start = node_row['date_start']
    date_end = node_row['date_end'] or date_start
    # Allow 50-year overlap window
    window = 50

    # Find nodes in OTHER domains with overlapping dates where learner has knowledge
    rows = conn.execute("""
        SELECT cn.title, cn.date_start, cn.date_end, cn.domain_id,
               cd.title as domain_title, ks.knowledge
        FROM curriculum_nodes cn
        JOIN curriculum_domains cd ON cd.id = cn.domain_id
        JOIN knowledge_states ks ON ks.domain_id = cn.domain_id AND ks.node_id = cn.id
        WHERE cn.domain_id != ?
          AND cn.date_start IS NOT NULL
          AND cn.date_start <= ? + ?
          AND COALESCE(cn.date_end, cn.date_start) >= ? - ?
          AND ks.knowledge IN ('engaged', 'anchored')
          AND cn.level >= 2
        ORDER BY ABS(cn.date_start - ?) ASC
        LIMIT 4
    """, (domain_id, date_end, window, date_start, window, date_start)).fetchall()

    if not rows:
        return ''

    lines = []
    for r in rows:
        date_label = str(r['date_start'])
        if r['date_start'] < 0:
            date_label = f'{abs(r["date_start"])} BC'
        elif r['date_start'] < 1000:
            date_label = f'{r["date_start"]} AD'
        lines.append(f"- Meanwhile in {r['domain_title']}: {r['title']} (~{date_label})")

    return ('Contemporaneous events the learner knows from other domains:\n'
            + '\n'.join(lines))


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
                fact_q = fact.get('question', '')
                fact_a = fact.get('answer', '')
                fact_ctx = f'{fact_q} — {fact_a}' if fact_a else fact_q
                fqs = _generate_follow_up_queries(node_title, node_description, fact_ctx)
                if fqs:
                    result['follow_up_queries'] = fqs
                # No fallback templates — empty is better than generic
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

    # Cross-curriculum context: what the learner knows about related entities from other domains
    cross_ctx = _get_cross_curriculum_context(domain_id, node_id, conn)
    if cross_ctx:
        known_ctx = (known_ctx + '\n\n' + cross_ctx) if known_ctx else cross_ctx

    temporal_ctx = ''
    if temporal_hook:
        temporal_ctx = f"Temporal hook: {temporal_hook}"

    # Temporal cross-references: contemporaneous events from other domains
    temporal_xref = _get_temporal_cross_references(domain_id, node_id, conn)
    if temporal_xref:
        temporal_ctx = (temporal_ctx + '\n\n' + temporal_xref) if temporal_ctx else temporal_xref

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
        fqs = _generate_follow_up_queries(node_title, node_description,
                                          source_text[:200] if source_text else '')
        if fqs:
            result['follow_up_queries'] = fqs

    return result


# ── Record answer ─────────────────────────────────────────────────────────────

def record_answer(item_id: str, score: str, conn) -> dict:
    # Look up in knowledge_items first; fall back to review_items,
    # then microlearning_quizzes, then microlearning_cards (legacy)
    row = conn.execute('SELECT * FROM knowledge_items WHERE id=?', (item_id,)).fetchone()
    table = 'knowledge_items'
    if row is None:
        row = conn.execute('SELECT * FROM review_items WHERE id=?', (item_id,)).fetchone()
        table = 'review_items'
    if row is None:
        try:
            row = conn.execute('SELECT * FROM microlearning_quizzes WHERE id=?', (item_id,)).fetchone()
            if row:
                table = 'microlearning_quizzes'
        except Exception:
            pass
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

    if table == 'microlearning_quizzes':
        # Individual quiz from a microlearning card
        conn.execute("""
            UPDATE microlearning_quizzes SET stability_days=?, due_at=?, last_reviewed_at=?,
              last_score=?, review_count=review_count+1
            WHERE id=?
        """, (new_stability, next_due, now, score, item_id))
        print(f'[review] ml_quiz {item_id}: {score} → stability={new_stability:.1f}d', flush=True)

        # Propagate knowledge update via the parent card's curriculum context
        parent = conn.execute(
            'SELECT source_domain, source_node_id FROM microlearning_cards WHERE id=?',
            (item['card_id'],)).fetchone()
        if parent and parent['source_domain'] and parent['source_node_id']:
            knowledge_val, confidence_val = SCORE_TO_KNOWLEDGE.get(score, ('unknown', 0.0))
            update_knowledge(parent['source_domain'], parent['source_node_id'],
                             knowledge=knowledge_val, confidence=confidence_val,
                             source=f"microlearning:{item_id}")

    elif table == 'microlearning_cards':
        # Legacy: whole microlearning card as review unit
        conn.execute("""
            UPDATE microlearning_cards SET stability_days=?, due_at=?, last_reviewed_at=?,
              last_score=?, review_count=review_count+1
            WHERE id=?
        """, (new_stability, next_due, now, score, item_id))
        print(f'[review] microlearning {item_id}: {score} → stability={new_stability:.1f}d', flush=True)

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

MICROLEARNING_PROMPT = """You are a knowledgeable historian and educator. Write a microlearning card for
a reader studying history and culture. This reader is especially interested in primary sources,
cultural artifacts, and material evidence — not just "what happened" but "what survives and
what was created."

Research question: {query}

Context — the learner was reviewing this curriculum concept:
{node_title}: {node_description}

Write:
1. A SHORT TITLE (under 60 chars) that names the specific subject with dates/years when relevant.
   Good: "The Catiline Conspiracy (63 BC)" or "Al-Idrisi's World Map for Roger II (1154)"
   Bad: "Cultural Blending in Medieval Sicily" or "An Ancient Conspiracy"

2. A vivid, specific answer as an array of labeled SECTIONS (total 200-350 words). Each section
   has a "heading" (short label, null for the opening narrative) and "text" (the paragraph).
   REQUIRED sections:
   - Opening narrative (heading: null): who, what, when, why it matters. 2-3 sentences.
   - "Sources": Name specific authors and works. If the person wrote anything, mention it.
     If no sources survive, say so — absence is historically significant. Use proper titles
     without markdown formatting.
   - "Still Visible": What can you visit or see today? Buildings, inscriptions, coins,
     manuscripts in specific museums. Be concrete about locations.
   - Optionally one more: "Surprising Detail" or "Cultural Legacy" (art, opera, literature).

3. 3-5 quiz questions testing SPECIFIC facts from the content. Short questions (6-15 words)
   with short specific answers (1-2 sentences). Each targets a different detail.

4. 3 follow-up queries that go SIDEWAYS — exploring angles the card DIDN'T cover. Don't repeat
   what's already in the content. Think: geography as explanation, counter-narratives, structural
   causes, transmission history, modern echoes, connected figures. Each should open a new rabbit hole.

5. Entities mentioned — people, places, events, concepts with canonical IDs.

Output JSON only:
{{"title":"short title with dates","sections":[{{"heading":null,"text":"opening narrative"}},{{"heading":"Sources","text":"primary source info"}},{{"heading":"Still Visible","text":"material evidence"}}],"quizzes":[{{"question":"...","answer":"..."}}],"follow_up_queries":["q1","q2","q3"],"entities":[{{"name":"Archimedes","canonical":"archimedes_of_syracuse","type":"person"}}]}}"""


ENTITY_RESEARCH_PROMPT = """You are a knowledgeable historian. Write a rich microlearning card about this entity,
making connections to the learner's known context. Include primary sources and material evidence.

Entity: {entity_name} ({entity_type})
{entity_description}

Related entities from the same period or region that the learner has encountered:
{related_entities}

Write:
1. A SHORT TITLE (under 60 chars) with dates when relevant.
   Good: "George of Antioch, Roger II's Admiral (d. 1151)" or "The Motya Charioteer (5th c. BC)"
   Bad: "An Important Historical Figure"

2. A vivid profile (3-5 SHORT paragraphs, 200-350 words) that:
   - Covers who/what this is and why it matters
   - Makes SPECIFIC connections to the related entities listed above
   - Names PRIMARY SOURCES: who wrote about this entity? What survives?
   - Names MATERIAL EVIDENCE: buildings, artifacts, inscriptions, museum objects
   - Includes one surprising or lesser-known detail

3. 3-5 quiz questions testing SPECIFIC facts. Short questions (6-15 words), short answers.

4. 3 follow-up queries latching onto specific details from the card content

5. Entities mentioned in the text

Output JSON only:
{{"title":"short title with dates","content":"the profile text","quizzes":[{{"question":"...","answer":"..."}}],"follow_up_queries":["q1","q2","q3"],"entities":[{{"name":"Name","canonical":"canonical_id","type":"person|place|event|concept|period"}}]}}"""


ENTITY_QUESTIONS_PROMPT = """Generate 3 research questions about this entity that would make a history reader
genuinely curious — the kind that make you go "wait, really?" or "I never thought about it that way."

Entity: {entity_name} ({entity_type})
{entity_description}

Related entities from the same period or region:
{related_entities}

Requirements:
- Be SPECIFIC — name real people, places, events, dates
- At least one question should connect this entity to a related entity listed above
- Vary the angle: one factual/what-happened, one comparative/connection, one surprising/counter-intuitive
- NO generic templates like "How does X connect to Y?"

Output JSON array of 3 strings only: ["q1","q2","q3"]"""


def _find_related_entities(entity_id: str, entity_name: str, entity_type: str,
                           conn) -> list[dict]:
    """Find entities related by time period or location."""
    related = []

    # Get the target entity's details if in shared_entities
    target = conn.execute(
        'SELECT * FROM shared_entities WHERE entity_id = ?', (entity_id,)
    ).fetchone()

    if target:
        target = dict(target)
        date_start = target.get('date_start')
        date_end = target.get('date_end')
        lat = target.get('latitude')
        lon = target.get('longitude')

        # Find temporally overlapping entities (within 100 years)
        if date_start is not None:
            time_related = conn.execute('''
                SELECT entity_id, name, entity_type, date_start, date_end, description
                FROM shared_entities
                WHERE entity_id != ? AND date_start IS NOT NULL
                  AND ABS(date_start - ?) < 100
                ORDER BY ABS(date_start - ?) ASC
                LIMIT 5
            ''', (entity_id, date_start, date_start)).fetchall()
            for r in time_related:
                related.append({
                    'name': r['name'], 'type': r['entity_type'],
                    'relation': 'same period',
                    'detail': f"({r['date_start']} to {r['date_end'] or '?'})" if r['date_start'] else '',
                })

        # Find spatially nearby entities (within ~2 degrees ≈ 200km)
        if lat is not None and lon is not None:
            space_related = conn.execute('''
                SELECT entity_id, name, entity_type, description
                FROM shared_entities
                WHERE entity_id != ? AND latitude IS NOT NULL
                  AND ABS(latitude - ?) < 2.0 AND ABS(longitude - ?) < 2.0
                LIMIT 5
            ''', (entity_id, lat, lon)).fetchall()
            seen = {r['name'] for r in related}
            for r in space_related:
                if r['name'] not in seen:
                    related.append({
                        'name': r['name'], 'type': r['entity_type'],
                        'relation': 'same region',
                    })

    # Also search microlearning cards for co-occurring entities
    try:
        ml_rows = conn.execute(
            "SELECT entities FROM microlearning_cards WHERE status='completed' AND entities LIKE ?",
            (f'%{entity_id}%',)
        ).fetchall()
        co_entities = {}
        eid_lower = entity_id.lower()
        for row in ml_rows:
            ents = json.loads(row['entities'] or '[]')
            for e in ents:
                cid = e.get('canonical', '')
                if cid and cid.lower() != eid_lower and cid not in co_entities:
                    co_entities[cid] = {'name': e['name'], 'type': e.get('type', 'concept'),
                                        'relation': 'co-mentioned in research'}
        seen = {r['name'] for r in related}
        for cid, info in list(co_entities.items())[:5]:
            if info['name'] not in seen:
                related.append(info)
    except Exception:
        pass

    return related[:8]


def _strip_markdown(text: str) -> tuple[str, list[tuple[int, int, int, int]]]:
    """Strip *italic* and **bold** markers from text.
    Returns (clean_text, offset_map) where offset_map maps clean positions to original positions."""
    import re
    # Track removals to build an offset map
    result = []
    i = 0
    while i < len(text):
        if text[i:i+2] == '**':
            # Find closing **
            end = text.find('**', i + 2)
            if end != -1:
                result.append(text[i+2:end])
                i = end + 2
                continue
        if text[i] == '*' and (i == 0 or text[i-1] != '*') and (i + 1 < len(text) and text[i+1] != '*'):
            # Find closing *
            end = text.find('*', i + 1)
            if end != -1 and text[end-1:end+1] != '**':
                result.append(text[i+1:end])
                i = end + 1
                continue
        result.append(text[i])
        i += 1
    return ''.join(result), []


def _compute_entity_spans(text: str, entities: list) -> list:
    """Find entity mentions in text and return span objects for the client."""
    spans = []
    for ent in entities:
        name = ent.get('name', '')
        if not name or len(name) < 2:
            continue
        start = 0
        while True:
            idx = text.find(name, start)
            if idx == -1:
                break
            spans.append({
                'start': idx,
                'end': idx + len(name),
                'entity_id': ent.get('canonical', name.lower().replace(' ', '_')),
                'name': name,
                'entity_type': ent.get('type', 'concept'),
            })
            start = idx + len(name)
    # Sort by position, deduplicate overlapping spans
    spans.sort(key=lambda s: s['start'])
    filtered = []
    last_end = 0
    for s in spans:
        if s['start'] >= last_end:
            filtered.append(s)
            last_end = s['end']
    return filtered


def generate_entity_questions(entity_id: str, entity_name: str,
                              entity_type: str = 'concept',
                              description: str = '') -> list[str]:
    """Generate 3 research questions about an entity, informed by related entities."""
    from db import get_connection
    conn = get_connection(readonly=True)
    related = _find_related_entities(entity_id, entity_name, entity_type, conn)
    conn.close()

    related_text = '\n'.join(
        f'- {r["name"]} ({r["type"]}, {r["relation"]})'
        + (f' {r.get("detail", "")}' if r.get('detail') else '')
        for r in related
    ) if related else '(none found — focus on the entity itself)'

    prompt = ENTITY_QUESTIONS_PROMPT.format(
        entity_name=entity_name,
        entity_type=entity_type,
        entity_description=description or '(no description available)',
        related_entities=related_text,
    )
    result = call_claude_json(prompt, timeout=60, model='sonnet')
    if isinstance(result, list) and len(result) >= 2:
        return result[:3]
    return [f'What was the historical significance of {entity_name}?']


def _find_duplicate_quiz(question: str, existing: list[tuple[str, 'numpy.ndarray']],
                         model, threshold: float = 0.82) -> str | None:
    """Check if a question is semantically duplicate of an existing one.

    Uses MiniLM embeddings via limbic.amygdala with the calibrated 0.82 cosine
    threshold (same as KNOWN for claim similarity).
    Returns the matching question text if duplicate, None otherwise.
    """
    import numpy as np
    if not existing:
        return None
    new_vec = model.embed(question)
    new_norm = np.linalg.norm(new_vec)
    if new_norm < 1e-9:
        return None
    best_score, best_text = 0.0, None
    for ex_text, ex_vec in existing:
        ex_norm = np.linalg.norm(ex_vec)
        if ex_norm < 1e-9:
            continue
        cos = float(np.dot(new_vec, ex_vec) / (new_norm * ex_norm))
        if cos > best_score:
            best_score, best_text = cos, ex_text
    # Log top match for calibration review
    if best_text:
        print(f'[quiz-dedup] best match ({best_score:.3f}): '
              f'"{question[:50]}" ~ "{best_text[:50]}"'
              f'{" → DUPLICATE" if best_score >= threshold else ""}', flush=True)
    if best_score >= threshold:
        return best_text
    return None


def _store_quizzes(card_id: str, quizzes: list, conn) -> int:
    """Store quiz questions, skipping semantic duplicates via limbic embeddings."""
    now_ms = int(time.time() * 1000)

    # Load embedding model for dedup
    model = None
    existing_embedded: list[tuple[str, any]] = []
    try:
        from limbic.amygdala import EmbeddingModel
        model = EmbeddingModel()

        # Collect and embed existing questions
        existing_texts = []
        for row in conn.execute(
            "SELECT question FROM microlearning_quizzes WHERE status='active'"
        ).fetchall():
            existing_texts.append(row['question'])
        try:
            for row in conn.execute(
                "SELECT key_facts FROM curriculum_nodes "
                "WHERE key_facts IS NOT NULL AND key_facts != '[]'"
            ).fetchall():
                facts = json.loads(row['key_facts'] or '[]')
                for f in facts:
                    if f.get('question'):
                        existing_texts.append(f['question'])
        except Exception:
            pass

        if existing_texts:
            vecs = model.embed_batch(existing_texts)
            existing_embedded = list(zip(existing_texts, vecs))
    except Exception as e:
        print(f'[quiz-dedup] embedding init failed, skipping dedup: {e}', flush=True)

    stored = 0
    skipped = 0
    for i, q in enumerate(quizzes):
        question = q.get('question', '').strip()
        answer = q.get('answer', '').strip()
        if not question:
            continue

        # Check for semantic duplicates
        if model and existing_embedded:
            dup = _find_duplicate_quiz(question, existing_embedded, model)
            if dup:
                print(f'[quiz-dedup] skipping: "{question[:50]}" ~ "{dup[:50]}"', flush=True)
                skipped += 1
                continue

        quiz_id = f'{card_id}_q{i}'
        conn.execute('''
            INSERT OR IGNORE INTO microlearning_quizzes
            (id, card_id, question, answer, status, stability_days, due_at,
             review_count, created_at)
            VALUES (?, ?, ?, ?, 'active', 1.0, ?, 0, ?)
        ''', (quiz_id, card_id, question, answer, now_ms, now_ms))
        # Add to existing pool so intra-batch dupes are caught too
        if model:
            existing_embedded.append((question, model.embed(question)))
        stored += 1

    if skipped:
        print(f'[quiz-dedup] {stored} stored, {skipped} skipped for {card_id}', flush=True)

    # Backfill legacy fields with first stored quiz
    if quizzes:
        first = quizzes[0]
        conn.execute(
            'UPDATE microlearning_cards SET question=?, answer_guidance=? WHERE id=?',
            (first.get('question', ''), first.get('answer', ''), card_id))

    return stored


def create_entity_research(entity_id: str, entity_name: str,
                           entity_type: str = 'concept',
                           description: str = '') -> str:
    """Create a microlearning card about an entity with related-entity context.

    Returns the card ID. Research runs in background.
    """
    from db import get_connection
    query = f'Profile: {entity_name} — who/what, why it matters, connections'
    card_id = f'ml_{int(time.time())}_{hash(entity_id) % 10000:04d}'
    now_ms = int(time.time() * 1000)

    conn = get_connection()
    conn.execute('''
        INSERT OR IGNORE INTO microlearning_cards
        (id, query, source_item_id, source_node_id, source_domain,
         content, status, created_at)
        VALUES (?, ?, ?, ?, ?, '', 'pending', ?)
    ''', (card_id, query, f'entity:{entity_id}', None, None, now_ms))
    conn.commit()
    conn.close()

    threading.Thread(
        target=_run_entity_research,
        args=(card_id, entity_id, entity_name, entity_type, description),
        daemon=True,
    ).start()
    return card_id


def _run_entity_research(card_id: str, entity_id: str, entity_name: str,
                          entity_type: str, description: str):
    """Background: generate a rich entity profile with related-entity connections."""
    from db import get_connection
    try:
        conn = get_connection(readonly=True)
        related = _find_related_entities(entity_id, entity_name, entity_type, conn)
        conn.close()

        related_text = '\n'.join(
            f'- {r["name"]} ({r["type"]}, {r["relation"]})'
            + (f' {r.get("detail", "")}' if r.get('detail') else '')
            for r in related
        ) if related else '(none known — focus on the entity itself)'

        # Web search for factual accuracy
        search_result = None
        try:
            search_prompt = f'Research: {entity_name} historical significance and connections'
            search_result = call_claude_search(search_prompt, timeout=120)
        except Exception as e:
            print(f'[entity-research] search failed for {card_id}: {e}', flush=True)

        prompt = ENTITY_RESEARCH_PROMPT.format(
            entity_name=entity_name,
            entity_type=entity_type,
            entity_description=description or '(no description available)',
            related_entities=related_text,
        )
        if search_result:
            prompt += f'\n\nSearch results to incorporate:\n{search_result[:2000]}'

        result = call_claude_json(prompt, timeout=120)
        if not result or 'content' not in result:
            raise ValueError(f'Invalid response: {str(result)[:200]}')

        entities = result.get('entities', [])
        quizzes = result.get('quizzes', [])
        if not quizzes and result.get('question'):
            quizzes = [{'question': result['question'],
                        'answer': result.get('answer_guidance', '')}]

        now_ms = int(time.time() * 1000)
        conn = get_connection()
        conn.execute('''
            UPDATE microlearning_cards SET
                title=?, content=?, follow_up_queries=?, entities=?,
                status='completed', due_at=?
            WHERE id=?
        ''', (
            result.get('title', entity_name),
            result['content'],
            json.dumps(result.get('follow_up_queries', [])),
            json.dumps(entities),
            now_ms,
            card_id,
        ))
        quiz_count = _store_quizzes(card_id, quizzes, conn)
        conn.commit()
        conn.close()
        print(f'[entity-research] completed {card_id}: {entity_name} '
              f'({quiz_count} quizzes, {len(entities)} entities, {len(related)} related)', flush=True)

    except Exception as e:
        print(f'[entity-research] failed {card_id}: {e}', flush=True)
        import traceback; traceback.print_exc()
        try:
            conn = get_connection()
            conn.execute("UPDATE microlearning_cards SET status='failed' WHERE id=?",
                         (card_id,))
            conn.commit()
            conn.close()
        except Exception:
            pass


def generate_also_want_to_know(item_id: str, question_text: str,
                               entities: list) -> list:
    """Generate tappable 'I also want to know...' suggestions after a review answer.

    Uses entity metadata, key_facts, and node dates to produce 2-4 quick suggestions.
    Each suggestion has: query, type ('simple_fact' or 'research'), label.
    """
    from db import get_connection
    suggestions = []
    conn = get_connection()

    try:
        # Get curriculum node context
        ki = conn.execute(
            'SELECT curriculum_node_id, curriculum_domain FROM knowledge_items WHERE id=?',
            (item_id,)).fetchone()
        if not ki:
            return suggestions
        node_id, domain_id = ki[0], ki[1]

        node = conn.execute(
            'SELECT title, date_start, date_end, key_facts FROM curriculum_nodes '
            'WHERE id=? AND domain_id=?', (node_id, domain_id)).fetchone()
        if not node:
            return suggestions

        node_title = node[0] or ''
        date_start = node[1]
        date_end = node[2]
        key_facts = json.loads(node[3]) if node[3] else []

        # Get already-asked fact_ids from question_history
        ki_full = conn.execute('SELECT question_history FROM knowledge_items WHERE id=?',
                               (item_id,)).fetchone()
        asked_fact_ids = set()
        if ki_full and ki_full[0]:
            try:
                for qh in json.loads(ki_full[0]):
                    if qh.get('fact_id'):
                        asked_fact_ids.add(qh['fact_id'])
            except (json.JSONDecodeError, TypeError):
                pass

        # Entity-based suggestions
        for ent in (entities or []):
            name = ent.get('name', '')
            etype = ent.get('type', ent.get('entity_type', ''))
            if not name:
                continue
            if etype == 'person':
                suggestions.append({
                    'query': f'When did {name} live?',
                    'type': 'simple_fact',
                    'label': f'{name} \u2014 dates',
                })
                if len(suggestions) < 4:
                    suggestions.append({
                        'query': f'Where was {name} primarily based?',
                        'type': 'simple_fact',
                        'label': f'{name} \u2014 location',
                    })
            elif etype == 'place':
                suggestions.append({
                    'query': f'What is the historical significance of {name}?',
                    'type': 'research',
                    'label': f'{name} \u2014 significance',
                })
            elif etype in ('event', 'battle', 'treaty'):
                suggestions.append({
                    'query': f'What were the consequences of {name}?',
                    'type': 'research',
                    'label': f'{name} \u2014 consequences',
                })
            if len(suggestions) >= 4:
                break

        # Key_facts-based suggestions (facts not yet quizzed)
        for fact in key_facts:
            fact_id = fact.get('id', '')
            if fact_id in asked_fact_ids:
                continue
            ft = fact.get('type', '')
            fname = fact.get('name', fact.get('value', ''))
            if ft == 'date' and fname:
                suggestions.append({
                    'query': f'When: {fname}',
                    'type': 'simple_fact',
                    'label': f'Date: {fname}',
                })
            elif ft == 'person' and fname:
                suggestions.append({
                    'query': f'Who was {fname}?',
                    'type': 'simple_fact',
                    'label': f'Person: {fname}',
                })
            elif ft == 'place' and fname:
                suggestions.append({
                    'query': f'Where is {fname}?',
                    'type': 'simple_fact',
                    'label': f'Place: {fname}',
                })
            elif fname:
                suggestions.append({
                    'query': f'What was {fname}?',
                    'type': 'simple_fact',
                    'label': fname,
                })
            if len(suggestions) >= 6:
                break

        # Date-based cross-temporal suggestion
        if date_start and len(suggestions) < 6:
            year_str = f'{abs(int(date_start))} {"BC" if date_start < 0 else "AD"}'
            suggestions.append({
                'query': f'What else was happening around {year_str}?',
                'type': 'research',
                'label': f'Around {year_str}',
            })

    except Exception as e:
        print(f'[also-want-to-know] Error: {e}', flush=True)
    finally:
        conn.close()

    # Deduplicate by query
    seen = set()
    unique = []
    for s in suggestions:
        if s['query'] not in seen:
            seen.add(s['query'])
            unique.append(s)
    return unique[:6]


def create_targeted_quiz(item_id: str, query: str) -> dict:
    """Create a simple quiz card for a specific fact gap (not a full ML research card).

    For quick factual questions like 'When was Cicero assassinated?'
    Returns the created quiz info.
    """
    from db import get_connection
    conn = get_connection()

    try:
        # Get node context for the LLM
        ki = conn.execute(
            'SELECT curriculum_node_id, curriculum_domain FROM knowledge_items WHERE id=?',
            (item_id,)).fetchone()
        if not ki:
            return {'error': 'item not found'}

        node_id, domain_id = ki[0], ki[1]
        node = conn.execute(
            'SELECT title, description FROM curriculum_nodes WHERE id=? AND domain_id=?',
            (node_id, domain_id)).fetchone()
        node_title = node[0] if node else ''
        node_desc = (node[1] or '')[:300] if node else ''

        # Quick LLM call to generate Q+A for this specific fact
        prompt = f"""Generate a single quiz question and answer for this specific knowledge gap.

Topic: {node_title}
Context: {node_desc}
User wants to know: {query}

Return JSON: {{"question": "...", "answer": "..."}}
The question should be direct and factual. The answer should be 1-2 sentences."""

        try:
            from claude_llm import call_claude_json
            result = call_claude_json(prompt, model='haiku')
        except Exception:
            from gemini_llm import call_llm
            raw = call_llm(prompt, model='gemini-2.0-flash-lite')
            result = json.loads(raw) if isinstance(raw, str) else raw

        question = result.get('question', query)
        answer = result.get('answer', '')

        # Store as a microlearning quiz linked to a lightweight ML card
        card_id = f'ml_{int(time.time())}_{hash(query) % 10000:04d}'
        quiz_id = f'mq_{int(time.time())}_{hash(question) % 10000:04d}'
        now_ms = int(time.time() * 1000)

        conn.execute('''
            INSERT OR IGNORE INTO microlearning_cards
            (id, query, source_item_id, source_node_id, source_domain,
             content, status, created_at, source_type, generation_depth, title)
            VALUES (?, ?, ?, ?, ?, ?, 'completed', ?, 'user_request', 0, ?)
        ''', (card_id, query, item_id, node_id, domain_id,
              answer, now_ms, node_title))

        conn.execute('''
            INSERT OR IGNORE INTO microlearning_quizzes
            (id, card_id, question, answer, status, stability_days, due_at, review_count, created_at)
            VALUES (?, ?, ?, ?, 'active', 1.0, ?, 0, ?)
        ''', (quiz_id, card_id, question, answer, now_ms, now_ms))

        conn.commit()
        return {'card_id': card_id, 'quiz_id': quiz_id, 'question': question, 'answer': answer}
    except Exception as e:
        print(f'[targeted-quiz] Error: {e}', flush=True)
        return {'error': str(e)}
    finally:
        conn.close()


def create_microlearning_request(query: str, source_item_id: str | None = None,
                                  source_node_id: str | None = None,
                                  source_domain: str | None = None,
                                  source_type: str = 'follow_up',
                                  generation_depth: int = 0) -> str:
    """Create a pending microlearning card and return its ID.

    source_type: 'voice_wondering', 'follow_up', 'entity_research', 'user_request'
    generation_depth: 0 = root, 1+ = child of another ML card

    The actual research runs in a background thread.
    """
    from db import get_connection
    card_id = f'ml_{int(time.time())}_{hash(query) % 10000:04d}'
    now_ms = int(time.time() * 1000)

    conn = get_connection()
    conn.execute('''
        INSERT OR IGNORE INTO microlearning_cards
        (id, query, source_item_id, source_node_id, source_domain,
         content, status, created_at, source_type, generation_depth)
        VALUES (?, ?, ?, ?, ?, '', 'pending', ?, ?, ?)
    ''', (card_id, query, source_item_id, source_node_id, source_domain,
          now_ms, source_type, generation_depth))
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

        if not result or ('content' not in result and 'sections' not in result):
            raise ValueError(f'Invalid response: {str(result)[:200] if result else "empty"}')

        # Handle sections format → join into flat content for entity spans
        sections = result.get('sections', [])
        if sections and isinstance(sections, list):
            # Join section texts into flat content
            result['content'] = '\n\n'.join(s.get('text', '') for s in sections)
        elif not result.get('content'):
            result['content'] = ''

        # Strip markdown for entity span computation
        raw_content = result['content']
        clean_content, _ = _strip_markdown(raw_content)
        entities = result.get('entities', [])
        entity_spans = _compute_entity_spans(clean_content, entities)
        spans_json = json.dumps({'content': [
            {'start': s['start'], 'end': s['end'], 'entity_id': s['entity_id'],
             'name': s['name'], 'entity_type': s['entity_type']}
            for s in entity_spans
        ]}) if entity_spans else '{}'

        # Update the card — store clean content (for spans) in content field
        now_ms = int(time.time() * 1000)
        quizzes = result.get('quizzes', [])
        # Backwards compat: if model returned old single-question format
        if not quizzes and result.get('question'):
            quizzes = [{'question': result['question'],
                        'answer': result.get('answer_guidance', '')}]

        conn = get_connection()
        conn.execute('''
            UPDATE microlearning_cards SET
                title=?, content=?, sections=?, follow_up_queries=?, entities=?, entity_spans=?,
                status='completed', due_at=?
            WHERE id=?
        ''', (
            result.get('title', query[:60]),
            clean_content,
            json.dumps(sections) if sections else '[]',
            json.dumps(result.get('follow_up_queries', [])),
            json.dumps(entities),
            spans_json,
            now_ms,
            card_id,
        ))
        quiz_count = _store_quizzes(card_id, quizzes, conn)
        conn.commit()
        conn.close()
        print(f'[microlearning] completed {card_id}: {query[:60]} '
              f'({quiz_count} quizzes, {len(entities)} entities)', flush=True)

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
                source_type='voice_wondering',
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

    conn can be None — the function manages its own connections to avoid holding
    the write lock during slow operations (transcription + LLM).
    """
    from db import get_connection
    if conn is None:
        conn = get_connection()
    # Handle chapter recall pseudo-nodes (chapter:{book_id}:{chapter_number})
    is_chapter_recall = node_id.startswith('chapter:')
    is_book_recall = node_id.startswith('book:')
    book_id = ''
    chapter_num = ''
    chapter_source_texts = []

    if is_chapter_recall or is_book_recall:
        parts = node_id.split(':')
        book_id = parts[1] if len(parts) > 1 else ''
        chapter_num = parts[2] if len(parts) > 2 and is_chapter_recall else ''

        # Auto-detect domain_id from book if not provided
        if not domain_id and book_id:
            row = conn.execute(
                "SELECT DISTINCT curriculum_domain FROM knowledge_items WHERE sources LIKE ? LIMIT 1",
                (f'%{book_id}%',)
            ).fetchone()
            if row:
                domain_id = row['curriculum_domain']

        # Look up book title and chapter sources
        book_title = ''
        chapter_title = ''
        source_query = f'%{book_id}%'
        domain_clause = "AND curriculum_domain = ?" if domain_id else ""
        domain_params = (source_query, domain_id) if domain_id else (source_query,)
        rows = conn.execute(
            f"SELECT sources FROM knowledge_items WHERE sources LIKE ? {domain_clause}",
            domain_params
        ).fetchall()
        for r in rows:
            try:
                sources = json.loads(r['sources'])
                for s in sources:
                    if s.get('book_id') != book_id:
                        continue
                    book_title = book_title or s.get('book_title', book_id)
                    if is_chapter_recall:
                        if str(s.get('chapter_number', '')) == str(chapter_num):
                            chapter_title = chapter_title or s.get('chapter_title', '')
                            if s.get('source_text'):
                                chapter_source_texts.append(s['source_text'])
                    else:
                        # Book recall — gather all source texts
                        if s.get('source_text'):
                            chapter_source_texts.append(s['source_text'])
            except Exception:
                pass

        # Fall back to book title from physical_books table
        if not book_title:
            bt_row = conn.execute('SELECT title FROM physical_books WHERE id = ?', (book_id,)).fetchone()
            if bt_row:
                book_title = bt_row['title']

        if is_chapter_recall:
            node = {
                'id': node_id,
                'title': f'Chapter {chapter_num}: {chapter_title}' if chapter_title else f'Chapter {chapter_num}',
                'description': f'What do you remember from Chapter {chapter_num} of {book_title}? Key ideas, people, events, and arguments.',
            }
        else:
            node = {
                'id': node_id,
                'title': book_title or book_id,
                'description': f'What do you remember from {book_title}? Speak freely about key ideas, people, events, themes, and anything that stuck with you.',
            }
    else:
        # Standard curriculum node
        if not domain_id:
            return {'error': 'Missing domain_id for curriculum node'}
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

    # Gather sources BEFORE closing connection
    if (is_chapter_recall or is_book_recall) and chapter_source_texts:
        sources_text = '\n'.join(chapter_source_texts[:8])
    else:
        sources_text = _gather_node_sources(node_id, domain_id, conn) if domain_id else ''

    # Dedup: if this exact audio was already processed for this node, return cached result
    audio_size = audio_path.stat().st_size if audio_path.exists() else 0
    if audio_size > 0:
        existing = conn.execute(
            "SELECT llm_result FROM voice_transcripts WHERE node_id = ? AND audio_bytes = ? AND source = 'elicitation' LIMIT 1",
            (node_id, audio_size)
        ).fetchone()
        if existing and existing['llm_result']:
            try:
                cached = json.loads(existing['llm_result'])
                cached['from_cache'] = True
                print(f'[voice-elicit] Dedup hit: node={node_id}, audio={audio_size} bytes — returning cached result', flush=True)
                conn.close()
                return cached
            except (json.JSONDecodeError, TypeError):
                pass

    # Close connection before slow work (transcription + LLM) to avoid write lock
    conn.close()

    # Transcribe
    print(f'[voice-elicit] Transcribing {audio_path} ({audio_path.stat().st_size} bytes)...', flush=True)
    transcript = transcribe_fn(audio_path)
    print(f'[voice-elicit] Transcript: {repr(transcript[:200]) if transcript else "EMPTY"}', flush=True)
    if not transcript:
        return {'error': 'Transcription failed'}

    # Quality gate: reject very short/interrupted recordings
    word_count = len(transcript.split())
    if word_count < 15:
        print(f'[voice-elicit] Too short ({word_count} words), skipping LLM analysis', flush=True)
        return {
            'error': 'too_short',
            'transcript': transcript,
            'word_count': word_count,
            'node_title': node['title'],
            'feedback_summary': 'Recording too short for analysis. Try speaking for at least 30 seconds about what you remember.',
            'captured': [], 'missed': [], 'interesting': [], 'wonderings': [],
            'coverage_pct': 0, 'suggested_score': 'missed',
            'research_triggers': [], 'microlearning_triggered': [],
        }

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

    # Populate result metadata (no DB needed)
    result['node_title'] = node['title']
    result['node_description'] = node['description']
    result['transcript'] = transcript

    # DB writes with retry — the expensive work (transcription + LLM) is done,
    # so we retry only the cheap write portion if the DB is locked.
    import sqlite3
    research_triggers = []
    max_write_attempts = 3
    for attempt in range(max_write_attempts):
        try:
            conn = get_connection()
            conn.execute('PRAGMA busy_timeout = 60000')  # 60s wait for lock

            # Generate temporal hook (skip for chapter recall)
            temporal_hook = '' if (is_chapter_recall or is_book_recall) else _generate_temporal_hook(node, domain_id, conn)
            result['temporal_hook'] = temporal_hook

            # Process "wonderings" — create research triggers (with dedup)
            wonderings = result.get('wonderings', [])
            research_triggers = []
            for w in wonderings[:5]:
                # Skip if this exact wondering already exists for this node
                existing_q = conn.execute(
                    "SELECT id FROM review_items WHERE item_type = 'voice_followup' AND curriculum_node_id = ? AND source_text = ?",
                    (node_id, w)
                ).fetchone()
                if existing_q:
                    research_triggers.append({'id': existing_q['id'], 'question': w, 'existing': True})
                    continue
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

            if is_chapter_recall or is_book_recall:
                if book_id and domain_id:
                    if is_chapter_recall and chapter_num:
                        source_filter = f'%"chapter_number": {chapter_num}%'
                    else:
                        source_filter = f'%{book_id}%'
                    ki_rows = conn.execute(
                        "SELECT id, curriculum_node_id FROM knowledge_items WHERE curriculum_domain = ? AND sources LIKE ?",
                        (domain_id, source_filter)
                    ).fetchall()
                    source_tag = f'voice_chapter_recall:{book_id}:{chapter_num}' if is_chapter_recall else f'voice_book_recall:{book_id}'
                    for ki in ki_rows:
                        update_knowledge(domain_id, ki['curriculum_node_id'],
                                         knowledge=knowledge_level, confidence=confidence,
                                         source=source_tag, conn=conn)
            else:
                update_knowledge(domain_id, node_id, knowledge=knowledge_level,
                                 confidence=confidence, source='voice_elicitation', conn=conn)

            now_ms = int(time.time() * 1000)
            stability_mult = {'knew': 2.5, 'partly': 1.5, 'missed': 0.4}.get(score, 1.0)
            if is_chapter_recall or is_book_recall:
                # Update all matched knowledge_items for book/chapter recall
                if book_id and domain_id:
                    if is_chapter_recall and chapter_num:
                        source_filter = f'%"chapter_number": {chapter_num}%'
                    else:
                        source_filter = f'%{book_id}%'
                    conn.execute("""
                        UPDATE knowledge_items
                        SET last_score = ?, last_reviewed_at = ?,
                            stability_days = MIN(365.0, MAX(1.0, stability_days * ?)),
                            due_at = ? + CAST(MIN(365.0, MAX(1.0, stability_days * ?)) * 86400000 AS INTEGER),
                            review_count = review_count + 1,
                            cached_question = NULL
                        WHERE curriculum_domain = ? AND sources LIKE ?
                    """, (score, now_ms, stability_mult, now_ms, stability_mult, domain_id, source_filter))
            else:
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
            conn.close()
            break  # success
        except sqlite3.OperationalError as e:
            if 'locked' in str(e) and attempt < max_write_attempts - 1:
                print(f'[voice-elicit] DB locked on write attempt {attempt + 1}, retrying in {5 * (attempt + 1)}s...', flush=True)
                try:
                    conn.close()
                except Exception:
                    pass
                time.sleep(5 * (attempt + 1))
            else:
                print(f'[voice-elicit] DB write failed after {attempt + 1} attempts: {e}', flush=True)
                try:
                    conn.close()
                except Exception:
                    pass
                # Don't raise — return the LLM result even if writes failed
                break

    result['research_triggers'] = research_triggers

    # Trigger microlearning for wonderings, research triggers, and top missed fact
    ml_triggered = []
    # Wonderings → microlearning (purest signal — user literally said "I wonder...")
    for w in wonderings[:3]:
        try:
            card_id = create_microlearning_request(
                query=w, source_node_id=node_id, source_domain=domain_id,
                source_type='voice_wondering',
            )
            ml_triggered.append({'id': card_id, 'query': w})
            print(f'[voice→ml] wondering → {card_id}: {w[:60]}', flush=True)
        except Exception as e:
            print(f'[voice→ml] wondering trigger failed: {e}', flush=True)

    # Research questions from LLM extraction (derived from wonderings + gaps)
    for q in result.get('research_questions', [])[:3]:
        if isinstance(q, dict):
            q = q.get('question', '') or q.get('query', '')
        q = str(q).strip()
        if q and q not in [m['query'] for m in ml_triggered]:
            try:
                card_id = create_microlearning_request(
                    query=q, source_node_id=node_id, source_domain=domain_id,
                    source_type='voice_wondering',
                )
                ml_triggered.append({'id': card_id, 'query': q})
                print(f'[voice→ml] research question → {card_id}: {q[:60]}', flush=True)
            except Exception as e:
                print(f'[voice→ml] research question failed: {e}', flush=True)

    # Top missed critical fact → targeted microlearning
    missed = result.get('missed', [])
    if missed and len(ml_triggered) < 3:
        most_important = missed[0] if isinstance(missed[0], str) else str(missed[0])
        q = f'Why is this important to know: {most_important}'
        try:
            card_id = create_microlearning_request(
                query=q, source_node_id=node_id, source_domain=domain_id,
                source_type='voice_wondering',
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


def process_voice_capture(transcript: str, entity_id: str = None,
                          entity_name: str = None, mode: str = 'general',
                          sync: bool = False) -> dict:
    """Process a voice capture for knowledge graph ingestion.

    Unlike run_voice_elicitation (which tests recall of a specific node),
    this ingests new knowledge: extracting facts, mapping to curriculum nodes,
    updating knowledge states, adding sources to knowledge_items, and
    triggering question generation + microlearning from wonderings.

    Returns dict with: transcript, facts, node_assessments, wonderings,
    knowledge_updates, microlearning_triggered, questions_queued.
    """
    from db import get_connection
    import sqlite3

    if not transcript or len(transcript.split()) < 5:
        return {'error': 'Transcript too short for analysis', 'transcript': transcript}

    conn = get_connection(readonly=True)

    # --- Find candidate curriculum nodes ---
    # Strategy: start with directly-linked nodes (high confidence), then expand
    # with relevant sibling nodes from the same domains. Keep it focused to avoid
    # bloating the LLM prompt with irrelevant nodes.
    directly_linked_node_ids = set()  # highest priority
    candidate_domains = set()
    detected_entity_ids = []

    # Helper: check if entity name matches transcript via word overlap
    transcript_lower = transcript.lower()
    transcript_words = set(w.lower() for w in re.split(r'\W+', transcript) if len(w) > 3)

    def _entity_matches_transcript(name: str) -> bool:
        """Match multi-word entity names by checking word overlap with transcript."""
        if len(name) < 4:
            return False
        name_lower = name.lower()
        # Direct substring match with word boundary check for short names
        if name_lower in transcript_lower:
            # For short names (< 8 chars), verify word boundary to avoid false positives
            if len(name) < 8:
                import re as _re
                if not _re.search(r'\b' + _re.escape(name_lower) + r'\b', transcript_lower):
                    return False
            return True
        # Word overlap: require >60% of significant words to match,
        # and at least 2 matching words for multi-word entities
        name_words = set(w.lower() for w in re.split(r'\W+', name) if len(w) > 3)
        if not name_words:
            return False
        matching = name_words & transcript_words
        overlap = len(matching) / len(name_words)
        if len(name_words) == 1:
            return overlap >= 1.0  # single-word entities must match exactly
        return overlap >= 0.6 and len(matching) >= 2

    if entity_id:
        # Entity mode: get all curriculum links for this entity
        detected_entity_ids = [entity_id]
        links = conn.execute(
            'SELECT domain_id, node_id FROM entity_curriculum_links WHERE entity_id = ?',
            (entity_id,)
        ).fetchall()
        for link in links:
            directly_linked_node_ids.add(link['node_id'])
            candidate_domains.add(link['domain_id'])

    # For general mode or as fallback: detect entities from transcript
    if not entity_id or not candidate_domains:
        entity_rows = conn.execute(
            'SELECT entity_id, name FROM shared_entities'
        ).fetchall()
        for row in entity_rows:
            if _entity_matches_transcript(row['name']):
                detected_entity_ids.append(row['entity_id'])
                if not entity_name:
                    entity_name = row['name']

        if detected_entity_ids:
            links = conn.execute(
                'SELECT DISTINCT domain_id, node_id, entity_id FROM entity_curriculum_links WHERE entity_id IN ({})'.format(
                    ','.join('?' * len(detected_entity_ids))),
                detected_entity_ids
            ).fetchall()
            for link in links:
                directly_linked_node_ids.add(link['node_id'])
                candidate_domains.add(link['domain_id'])

    print(f'[voice-capture] Detected entities: {detected_entity_ids[:10]}, '
          f'directly linked nodes: {len(directly_linked_node_ids)}, '
          f'domains: {candidate_domains}', flush=True)

    # Build candidate nodes: start with directly-linked, then add relevant siblings
    candidate_nodes = []
    seen_node_ids = set()

    # Phase 1: Directly linked nodes (always included)
    if directly_linked_node_ids:
        placeholders = ','.join('?' * len(directly_linked_node_ids))
        nodes = conn.execute(
            f'SELECT id, domain_id, title, description FROM curriculum_nodes WHERE id IN ({placeholders})',
            list(directly_linked_node_ids)
        ).fetchall()
        for n in nodes:
            candidate_nodes.append({
                'node_id': n['id'],
                'domain_id': n['domain_id'],
                'title': n['title'],
                'description': (n['description'] or '')[:200],
                'priority': 'direct',
            })
            seen_node_ids.add(n['id'])

    # Phase 2: Sibling nodes from the same domains that have title word overlap with transcript
    for domain_id in candidate_domains:
        nodes = conn.execute(
            'SELECT id, title, description FROM curriculum_nodes WHERE domain_id = ? AND level >= 2',
            (domain_id,)
        ).fetchall()
        for n in nodes:
            if n['id'] in seen_node_ids:
                continue
            title_words = set(w.lower() for w in re.split(r'\W+', n['title']) if len(w) > 3)
            overlap = len(title_words & transcript_words)
            if overlap > 0:
                candidate_nodes.append({
                    'node_id': n['id'],
                    'domain_id': domain_id,
                    'title': n['title'],
                    'description': (n['description'] or '')[:200],
                    'priority': 'sibling',
                    'overlap': overlap,
                })
                seen_node_ids.add(n['id'])

    # Phase 3: If still very few nodes, expand only the primary domain
    # (the one with the most direct links — avoids dumping 70 Ancient Greece
    # nodes when the transcript is about medieval Sicily)
    if len(candidate_nodes) < 10 and directly_linked_node_ids:
        # Find which domain has the most direct links
        domain_counts = {}
        for n in candidate_nodes:
            if n.get('priority') == 'direct':
                domain_counts[n['domain_id']] = domain_counts.get(n['domain_id'], 0) + 1
        if domain_counts:
            primary_domain = max(domain_counts, key=domain_counts.get)
            nodes = conn.execute(
                'SELECT id, title, description FROM curriculum_nodes WHERE domain_id = ? AND level >= 2',
                (primary_domain,)
            ).fetchall()
            for n in nodes:
                if n['id'] not in seen_node_ids:
                    candidate_nodes.append({
                        'node_id': n['id'],
                        'domain_id': primary_domain,
                        'title': n['title'],
                        'description': (n['description'] or '')[:200],
                        'priority': 'domain',
                    })
                    seen_node_ids.add(n['id'])

    # Phase 4: Last resort — scan all nodes for title keyword matches
    if not candidate_nodes:
        all_nodes = conn.execute(
            'SELECT id, domain_id, title, description FROM curriculum_nodes WHERE level >= 2'
        ).fetchall()
        for n in all_nodes:
            title_words = set(w.lower() for w in re.split(r'\W+', n['title']) if len(w) > 3)
            if title_words & transcript_words:
                candidate_nodes.append({
                    'node_id': n['id'],
                    'domain_id': n['domain_id'],
                    'title': n['title'],
                    'description': (n['description'] or '')[:200],
                    'priority': 'keyword',
                })
                candidate_domains.add(n['domain_id'])

    conn.close()

    if not candidate_nodes:
        print(f'[voice-capture] No candidate nodes found for entity={entity_id}, mode={mode}', flush=True)
        return {
            'error': 'no_curriculum_match',
            'transcript': transcript,
            'message': 'Could not find relevant curriculum nodes for this capture.',
        }

    # Sort: direct links first, then siblings by overlap, then domain fillers
    priority_order = {'direct': 0, 'sibling': 1, 'domain': 2, 'keyword': 3}
    candidate_nodes.sort(key=lambda n: (priority_order.get(n.get('priority', 'keyword'), 3),
                                         -n.get('overlap', 0)))

    by_priority = {}
    for n in candidate_nodes:
        p = n.get('priority', '?')
        by_priority[p] = by_priority.get(p, 0) + 1
    print(f'[voice-capture] Found {len(candidate_nodes)} candidate nodes across {len(candidate_domains)} domains '
          f'(breakdown: {by_priority})', flush=True)

    # --- Build context section for prompt ---
    if entity_id and entity_name:
        context_section = f'CONTEXT: The learner is speaking about {entity_name}.'
    elif entity_name:
        context_section = f'CONTEXT: The learner appears to be discussing topics related to {entity_name}.'
    else:
        context_section = 'CONTEXT: The learner is sharing knowledge from a recent podcast, book, or personal study.'

    # Build nodes list (limit to 40 most relevant to avoid prompt bloat)
    nodes_for_prompt = candidate_nodes[:40]
    nodes_list = '\n'.join(
        f'- {n["node_id"]}: {n["title"]} — {n["description"]}'
        for n in nodes_for_prompt
    )

    # --- Run Claude analysis (slow — no DB lock held) ---
    prompt = VOICE_CAPTURE_ANALYSIS_PROMPT.format(
        context_section=context_section,
        nodes_list=nodes_list,
        transcript=transcript,
    )

    analysis = call_claude_json(prompt, timeout=180)
    if not isinstance(analysis, dict):
        print(f'[voice-capture] LLM returned non-dict: {repr(str(analysis)[:200])}', flush=True)
        analysis = {}

    facts = analysis.get('facts', [])
    node_assessments = analysis.get('node_assessments', [])
    wonderings = analysis.get('wonderings', [])
    entities_mentioned = analysis.get('entities_mentioned', [])

    print(f'[voice-capture] Analysis: {len(facts)} facts, {len(node_assessments)} nodes assessed, '
          f'{len(wonderings)} wonderings', flush=True)

    # --- DB writes: upsert knowledge_items, update knowledge states ---
    now_ms = int(time.time() * 1000)
    knowledge_updates = []
    items_created = 0
    items_updated = 0
    questions_queued = []

    # Build a lookup from node_id to domain_id
    node_domain_map = {n['node_id']: n['domain_id'] for n in candidate_nodes}

    max_write_attempts = 3
    for attempt in range(max_write_attempts):
        try:
            conn = get_connection()
            conn.execute('PRAGMA busy_timeout = 60000')

            for assessment in node_assessments:
                nid = assessment.get('node_id', '')
                did = node_domain_map.get(nid)
                if not nid or not did:
                    continue

                knowledge_level = assessment.get('knowledge_level', 'engaged')
                if knowledge_level not in ('mentioned', 'engaged', 'anchored'):
                    knowledge_level = 'engaged'

                confidence = min(1.0, (assessment.get('fact_count', 1) / 5.0) + 0.3)
                item_id = f'{did}:{nid}'

                # Gather facts for this node as source text
                node_facts = [f['fact'] for f in facts if nid in f.get('node_ids', [])]
                source_text = '; '.join(node_facts[:5]) if node_facts else assessment.get('summary', '')

                new_source = {
                    'source': 'voice_capture',
                    'entity_id': entity_id,
                    'entity_name': entity_name,
                    'source_text': source_text[:400],
                    'fact_count': len(node_facts),
                    'added_at': now_ms,
                }

                existing = conn.execute(
                    'SELECT id, sources FROM knowledge_items WHERE id = ?', (item_id,)
                ).fetchone()

                if existing:
                    try:
                        sources = json.loads(existing['sources'] or '[]')
                    except Exception:
                        sources = []
                    sources.append(new_source)
                    conn.execute(
                        'UPDATE knowledge_items SET sources = ?, cached_question = NULL WHERE id = ?',
                        (json.dumps(sources), item_id)
                    )
                    items_updated += 1
                else:
                    conn.execute('''
                        INSERT INTO knowledge_items
                        (id, curriculum_node_id, curriculum_domain, stability_days, due_at,
                         sources, question_history, created_at)
                        VALUES (?,?,?,?,?,?,?,?)
                    ''', (
                        item_id, nid, did,
                        INITIAL_STABILITY_DAYS, now_ms,
                        json.dumps([new_source]), '[]', now_ms,
                    ))
                    items_created += 1

                # Update knowledge state (only upgrades, per system rules)
                update_knowledge(did, nid, knowledge=knowledge_level,
                                 confidence=confidence, source='voice_capture', conn=conn)

                # Update scheduling on knowledge_items
                stability_mult = {'anchored': 2.5, 'engaged': 1.5, 'mentioned': 1.0}.get(knowledge_level, 1.0)
                conn.execute("""
                    UPDATE knowledge_items
                    SET last_reviewed_at = ?,
                        stability_days = MIN(365.0, MAX(1.0, stability_days * ?)),
                        due_at = ? + CAST(MIN(365.0, MAX(1.0, stability_days * ?)) * 86400000 AS INTEGER),
                        review_count = review_count + 1
                    WHERE id = ?
                """, (now_ms, stability_mult, now_ms, stability_mult, item_id))

                questions_queued.append(item_id)
                knowledge_updates.append({
                    'node_id': nid,
                    'domain_id': did,
                    'knowledge_level': knowledge_level,
                    'facts_captured': len(node_facts),
                })

            # Save entity notes (preserve existing behavior)
            if entity_id and facts:
                note_text = '\n'.join(f'• {f["fact"]}' for f in facts[:15])
                conn.execute(
                    'INSERT INTO entity_notes (entity_id, note, created_at) VALUES (?, ?, ?)',
                    (entity_id, note_text, now_ms))

            conn.commit()
            conn.close()
            break  # success
        except sqlite3.OperationalError as e:
            if 'locked' in str(e) and attempt < max_write_attempts - 1:
                print(f'[voice-capture] DB locked on write attempt {attempt + 1}, retrying...', flush=True)
                try:
                    conn.close()
                except Exception:
                    pass
                time.sleep(5 * (attempt + 1))
            else:
                print(f'[voice-capture] DB write failed: {e}', flush=True)
                try:
                    conn.close()
                except Exception:
                    pass
                break

    print(f'[voice-capture] Knowledge updates: {items_created} created, {items_updated} updated, '
          f'{len(knowledge_updates)} nodes touched', flush=True)

    # --- Pre-generate questions ---
    if questions_queued:
        def _pregen_questions():
            from db import get_connection as _gc
            c = _gc()
            generated = 0
            for iid in questions_queued:
                try:
                    row = c.execute('SELECT cached_question FROM knowledge_items WHERE id = ?', (iid,)).fetchone()
                    if row and not row['cached_question']:
                        q = generate_question(iid, c)
                        c.execute('UPDATE knowledge_items SET cached_question = ? WHERE id = ?',
                                  (json.dumps(q), iid))
                        c.commit()
                        generated += 1
                except Exception as e:
                    print(f'[voice-capture] pre-gen failed {iid}: {e}', flush=True)
            c.close()
            print(f'[voice-capture] Pre-generated {generated}/{len(questions_queued)} questions', flush=True)
        if sync:
            _pregen_questions()
        else:
            threading.Thread(target=_pregen_questions, daemon=True).start()

    # --- Trigger microlearning from wonderings ---
    ml_triggered = []
    primary_domain = next(iter(candidate_domains)) if candidate_domains else None
    primary_node = node_assessments[0]['node_id'] if node_assessments else None

    if not sync:
        for w in wonderings[:5]:
            try:
                card_id = create_microlearning_request(
                    query=w,
                    source_node_id=primary_node,
                    source_domain=primary_domain,
                )
                ml_triggered.append({'id': card_id, 'query': w})
                print(f'[voice-capture→ml] wondering → {card_id}: {w[:60]}', flush=True)
            except Exception as e:
                print(f'[voice-capture→ml] failed: {e}', flush=True)

    # --- Log transcript ---
    _log_voice_transcript(
        source='voice_capture',
        node_id=primary_node or entity_id or 'general',
        domain_id=primary_domain or '',
        node_title=entity_name or 'general',
        transcript=transcript,
        audio_bytes=0,
        llm_result={**analysis, 'knowledge_updates': knowledge_updates},
        ml_triggered=ml_triggered,
    )

    result = {
        'status': 'completed',
        'transcript': transcript,
        'facts_extracted': len(facts),
        'nodes_assessed': len(node_assessments),
        'node_assessments': node_assessments,
        'knowledge_updates': knowledge_updates,
        'items_created': items_created,
        'items_updated': items_updated,
        'questions_queued': len(questions_queued),
        'wonderings': wonderings,
        'entities_mentioned': entities_mentioned,
        'microlearning_triggered': ml_triggered,
        'overall_summary': analysis.get('overall_summary', ''),
    }

    print(f'[voice-capture] Done: {len(facts)} facts → {len(knowledge_updates)} nodes, '
          f'{len(ml_triggered)} ML cards', flush=True)
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
    # Note: don't use json_extract in JOINs — unreliable with varying JSON structures.
    # Look up book titles in Python instead (same pattern as get_review_queue).
    rows = conn.execute("""
        SELECT ki.curriculum_domain, ki.sources
        FROM knowledge_items ki
        WHERE ki.sources LIKE '%chapter_number%'
          AND ki.review_count <= 1
        ORDER BY ki.created_at DESC
        LIMIT 50
    """).fetchall()

    # Build book title cache
    book_titles: dict[str, str] = {}
    for r in rows:
        try:
            for s in json.loads(r['sources'] or '[]'):
                bid = s.get('book_id', '')
                if bid and bid not in book_titles:
                    bt_row = conn.execute('SELECT title FROM physical_books WHERE id = ?', (bid,)).fetchone()
                    book_titles[bid] = bt_row['title'] if bt_row else ''
        except Exception:
            pass

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

            book_title = book_titles.get(book_id, '') or book_id
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

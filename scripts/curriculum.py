"""
Curriculum-based knowledge mapping system.

Generates hierarchical curricula for humanities domains, maps books against them,
tracks user knowledge states, and runs adaptive "20 Questions" elicitation sessions.

Data stored in /opt/petrarca/data/curricula/
"""

import json
import os
import math
import random
import time
from datetime import datetime
from pathlib import Path

from gemini_llm import call_llm

DATA_DIR = Path(os.environ.get('CURRICULUM_DIR', '/opt/petrarca/data/curricula'))
PHYSICAL_BOOKS_PATH = Path(os.environ.get('PHYSICAL_BOOKS_PATH', '/opt/petrarca/data/physical_books.json'))

# Ensure dirs exist
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────

def make_node_id(domain_id: str, title: str) -> str:
    """Generate a stable node ID from domain + title."""
    slug = title.lower().strip()
    slug = ''.join(c if c.isalnum() or c == ' ' else '' for c in slug)
    slug = '_'.join(slug.split()[:6])
    return f"{domain_id[:10]}_{slug}"


def make_domain_id(title: str) -> str:
    """Generate a domain ID from title."""
    slug = title.lower().strip()
    slug = ''.join(c if c.isalnum() or c == ' ' else '' for c in slug)
    slug = '_'.join(slug.split()[:8])
    return slug


# ─────────────────────────────────────────────
# Curriculum generation
# ─────────────────────────────────────────────

CURRICULUM_GENERATION_PROMPT = """You are an expert curriculum designer for university-level humanities education.

Generate a hierarchical curriculum for an introductory course on: {domain}

STRUCTURE RULES:
- Maximum 4 levels deep: Area (level 1) → Topic (level 2) → Concept (level 3) → Detail (level 4, use sparingly)
- Aim for 50-80 leaf nodes total
- Each area should have 3-7 topics
- Topics can have 0-5 concepts (not every topic needs sub-concepts)
- Balance breadth across the domain — don't over-represent any single area

FOR EACH NODE, provide:
- "title": Clear, specific name
- "description": 2-3 sentences describing what "knowing this" means at an introductory level. Be specific enough that someone could self-assess: "I know this" or "I don't know this."
- "parent": Title of parent node (null for top-level areas)
- "level": 1 for Area, 2 for Topic, 3 for Concept, 4 for Detail
- "prerequisites": List of titles of nodes that should be known before this one (can be empty). Only include direct prerequisites, not transitive ones.
- "obscurity": 1-5 (1 = widely known by anyone with passing interest, 5 = specialist knowledge)
- "bloom_floor": The minimum level of understanding expected: "recognize" (know it exists), "explain" (understand the basics), or "analyze" (can discuss significance and connections)

GUIDELINES:
- Cover the major areas a well-designed introductory course would include
- Include political, social, cultural, intellectual, and economic dimensions
- Don't just list events chronologically — organize by theme and significance
- Prerequisites should reflect genuine dependencies: you can't understand the Peloponnesian War without knowing about Athens and Sparta
- Obscurity ratings should reflect what an educated non-specialist would know vs. what requires specific study

Output as a JSON array of node objects. No markdown, just the JSON array."""


def generate_curriculum(domain: str, depth: str = "introductory") -> dict | None:
    """Generate a curriculum for a domain. Returns the full curriculum dict or None."""

    prompt = CURRICULUM_GENERATION_PROMPT.format(domain=domain)

    if depth == "intermediate":
        prompt += "\n\nThis is an INTERMEDIATE level curriculum. Aim for 150-200 nodes with more specific detail."
    elif depth == "advanced":
        prompt += "\n\nThis is an ADVANCED level curriculum. Aim for 250-300+ nodes with specialist detail."

    raw = call_llm(prompt, model="gemini-2.5-flash", max_tokens=16384,
                   response_mime_type="application/json")
    if not raw:
        return None

    try:
        nodes_raw = json.loads(raw)
    except json.JSONDecodeError:
        print(f"Failed to parse curriculum JSON: {raw[:200]}...", flush=True)
        return None

    if not isinstance(nodes_raw, list):
        print(f"Curriculum output is not a list: {type(nodes_raw)}", flush=True)
        return None

    domain_id = make_domain_id(domain)

    # Build nodes with IDs and resolve parent/prerequisite references
    title_to_id: dict[str, str] = {}
    nodes = []

    for raw_node in nodes_raw:
        title = raw_node.get("title", "").strip()
        if not title:
            continue
        node_id = make_node_id(domain_id, title)
        title_to_id[title] = node_id

        nodes.append({
            "id": node_id,
            "title": title,
            "description": raw_node.get("description", ""),
            "parent_title": raw_node.get("parent"),
            "parent_id": None,  # resolved below
            "level": raw_node.get("level", 1),
            "prerequisite_titles": raw_node.get("prerequisites", []),
            "prerequisites": [],  # resolved below
            "obscurity": raw_node.get("obscurity", 3),
            "bloom_floor": raw_node.get("bloom_floor", "recognize"),
        })

    # Resolve references
    for node in nodes:
        parent_title = node.pop("parent_title", None)
        if parent_title and parent_title in title_to_id:
            node["parent_id"] = title_to_id[parent_title]

        prereq_titles = node.pop("prerequisite_titles", [])
        node["prerequisites"] = [
            title_to_id[t] for t in prereq_titles if t in title_to_id
        ]

    curriculum = {
        "id": domain_id,
        "title": domain,
        "description": f"Introductory curriculum for {domain}",
        "depth": depth,
        "generated_at": datetime.now().isoformat(),
        "version": 1,
        "node_count": len(nodes),
        "nodes": nodes,
    }

    # Save
    path = DATA_DIR / f"{domain_id}.json"
    with open(path, 'w') as f:
        json.dump(curriculum, f, indent=2)

    print(f"Generated curriculum '{domain}': {len(nodes)} nodes, saved to {path}", flush=True)
    return curriculum


def load_curriculum(domain_id: str) -> dict | None:
    """Load a curriculum by ID."""
    path = DATA_DIR / f"{domain_id}.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def list_curricula() -> list[dict]:
    """List all available curricula (metadata only)."""
    results = []
    for path in DATA_DIR.glob("*.json"):
        if path.stem.startswith("knowledge_") or path.stem.startswith("elicit_"):
            continue
        try:
            with open(path) as f:
                data = json.load(f)
            results.append({
                "id": data["id"],
                "title": data["title"],
                "depth": data.get("depth", "introductory"),
                "node_count": data.get("node_count", len(data.get("nodes", []))),
                "generated_at": data.get("generated_at"),
            })
        except Exception:
            pass
    return results


# ─────────────────────────────────────────────
# Knowledge state tracking
# ─────────────────────────────────────────────

def _knowledge_path(domain_id: str) -> Path:
    return DATA_DIR / f"knowledge_{domain_id}.json"


def load_knowledge_states(domain_id: str) -> dict[str, dict]:
    """Load knowledge states for a domain. Returns {node_id: state_dict}."""
    path = _knowledge_path(domain_id)
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def save_knowledge_states(domain_id: str, states: dict[str, dict]):
    """Save knowledge states for a domain."""
    path = _knowledge_path(domain_id)
    with open(path, 'w') as f:
        json.dump(states, f, indent=2)


def update_knowledge(domain_id: str, node_id: str,
                     knowledge: str | None = None,
                     interest: str | None = None,
                     confidence: float | None = None,
                     source: str | None = None) -> dict:
    """Update knowledge state for a single node."""
    states = load_knowledge_states(domain_id)

    if node_id not in states:
        states[node_id] = {
            "knowledge": "unknown",
            "interest": "none",
            "confidence": 0.0,
            "sources": [],
            "last_assessed": None,
        }

    state = states[node_id]
    if knowledge:
        state["knowledge"] = knowledge
    if interest:
        state["interest"] = interest
    if confidence is not None:
        state["confidence"] = confidence
    if source and source not in state.get("sources", []):
        state.setdefault("sources", []).append(source)
    state["last_assessed"] = datetime.now().isoformat()

    save_knowledge_states(domain_id, states)
    return state


# Mapping from self-report familiarity levels to knowledge states.
# v1 (5-level): unknown, heard_of, know_basics, could_explain, know_deeply
# v2 (3-level): new_to_me, knew_some, knew_all
FAMILIARITY_TO_KNOWLEDGE = {
    # v1 format
    "unknown": ("unknown", 0.0),
    "heard_of": ("mentioned", 0.4),
    "know_basics": ("engaged", 0.6),
    "could_explain": ("anchored", 0.8),
    "know_deeply": ("anchored", 0.95),
    # v2 format
    "new_to_me": ("unknown", 0.0),
    "knew_some": ("engaged", 0.6),
    "knew_all": ("anchored", 0.9),
}

INTEREST_TO_CANONICAL = {
    # v1
    "core": "core",
    "curious": "curious",
    "none": "none",
    # v2
    "interested": "curious",
    "star": "core",
    "skip": "none",
}


def import_self_report(domain_id: str, self_report_path: str | Path) -> dict:
    """Import a self-report JSON file into canonical knowledge states.

    Returns summary: {imported, skipped, total, by_level}.
    """
    with open(self_report_path) as f:
        report = json.load(f)

    answers = report.get("answers", {})
    states = load_knowledge_states(domain_id)
    now = datetime.now().isoformat()
    imported = 0
    by_level = {}

    for node_id, answer in answers.items():
        fam = answer.get("familiarity", "unknown")
        interest_raw = answer.get("interest", "none")

        knowledge, confidence = FAMILIARITY_TO_KNOWLEDGE.get(fam, ("unknown", 0.0))
        interest = INTEREST_TO_CANONICAL.get(interest_raw, "curious")

        states[node_id] = {
            "knowledge": knowledge,
            "interest": interest,
            "confidence": confidence,
            "sources": ["self_report"],
            "last_assessed": now,
        }
        imported += 1
        by_level[knowledge] = by_level.get(knowledge, 0) + 1

    save_knowledge_states(domain_id, states)
    return {
        "imported": imported,
        "total": len(answers),
        "by_level": by_level,
        "domain_id": domain_id,
    }


def import_assessment_answers(domain_id: str, answers: dict) -> dict:
    """Import assessment answers dict (from HTML UI) directly into knowledge states.

    answers: {node_id: {familiarity, interest, ...}}
    Returns summary.
    """
    states = load_knowledge_states(domain_id)
    now = datetime.now().isoformat()
    imported = 0
    by_level = {}

    for node_id, answer in answers.items():
        fam = answer.get("familiarity", "unknown")
        interest_raw = answer.get("interest", "none")

        knowledge, confidence = FAMILIARITY_TO_KNOWLEDGE.get(fam, ("unknown", 0.0))
        interest = INTEREST_TO_CANONICAL.get(interest_raw, "curious")

        states[node_id] = {
            "knowledge": knowledge,
            "interest": interest,
            "confidence": confidence,
            "sources": ["self_report"],
            "last_assessed": now,
        }
        imported += 1
        by_level[knowledge] = by_level.get(knowledge, 0) + 1

    save_knowledge_states(domain_id, states)
    return {
        "imported": imported,
        "total": len(answers),
        "by_level": by_level,
        "domain_id": domain_id,
    }


# ─────────────────────────────────────────────
# Book-to-curriculum mapping
# ─────────────────────────────────────────────

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


def map_book_to_curriculum(book_id: str, domain_id: str) -> list[dict] | None:
    """Map a book's content against a curriculum. Returns list of mappings."""
    curriculum = load_curriculum(domain_id)
    if not curriculum:
        return None

    # Load book data
    books_data = {}
    if PHYSICAL_BOOKS_PATH.exists():
        with open(PHYSICAL_BOOKS_PATH) as f:
            books_data = json.load(f)

    book = None
    for b in books_data.get("books", []):
        if b.get("id") == book_id:
            book = b
            break

    if not book:
        return None

    # Format curriculum nodes for the prompt
    node_lines = []
    title_to_id = {}
    for node in curriculum["nodes"]:
        indent = "  " * (node["level"] - 1)
        node_lines.append(f"{indent}- {node['title']}: {node['description'][:100]}")
        title_to_id[node["title"]] = node["id"]

    chapters_text = ", ".join(
        f"Ch {ch.get('number', '?')}: {ch.get('title', '?')}"
        for ch in book.get("chapters", [])
    ) or "No chapters available"

    # Look for book research
    research_path = PHYSICAL_BOOKS_PATH.parent / "books" / f"research_{book_id}.json"
    thesis = ""
    key_terms = ""
    if research_path.exists():
        with open(research_path) as f:
            research = json.load(f)
        thesis = research.get("thesis", "")
        key_terms = ", ".join(t.get("term", "") for t in research.get("key_terms", [])[:20])

    prompt = BOOK_MAPPING_PROMPT.format(
        title=book.get("title", "Unknown"),
        author=book.get("author", "Unknown"),
        topics=", ".join(book.get("topics", [])),
        chapters=chapters_text,
        thesis=thesis or "Not available",
        key_terms=key_terms or "Not available",
        curriculum_nodes="\n".join(node_lines),
    )

    raw = call_llm(prompt, model="gemini-2.5-flash", max_tokens=8192,
                   response_mime_type="application/json")
    if not raw:
        return None

    try:
        mappings_raw = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if not isinstance(mappings_raw, list):
        return None

    # Resolve titles to IDs and update knowledge states
    mappings = []
    book_significance = book.get("significance", "read")
    confidence_map = {
        ("essential", "deep"): 0.9,
        ("essential", "moderate"): 0.8,
        ("essential", "surface"): 0.6,
        ("read", "deep"): 0.8,
        ("read", "moderate"): 0.65,
        ("read", "surface"): 0.45,
        ("skimmed", "deep"): 0.6,
        ("skimmed", "moderate"): 0.4,
        ("skimmed", "surface"): 0.25,
    }

    for m in mappings_raw:
        node_title = m.get("node_title", "")
        if node_title not in title_to_id:
            continue
        node_id = title_to_id[node_title]
        coverage = m.get("coverage", "surface")
        confidence = confidence_map.get((book_significance, coverage), 0.5)

        mappings.append({
            "node_id": node_id,
            "node_title": node_title,
            "coverage": coverage,
            "evidence": m.get("evidence", ""),
            "book_id": book_id,
            "confidence": confidence,
        })

        # Update knowledge state
        update_knowledge(
            domain_id, node_id,
            knowledge="mentioned",
            confidence=confidence,
            source=f"book:{book_id}",
        )

    # Save mappings
    mappings_path = DATA_DIR / f"mappings_{domain_id}_{book_id}.json"
    with open(mappings_path, 'w') as f:
        json.dump(mappings, f, indent=2)

    print(f"Mapped book '{book.get('title')}' → {len(mappings)} curriculum nodes", flush=True)
    return mappings


# ─────────────────────────────────────────────
# Gap analysis
# ─────────────────────────────────────────────

def get_coverage_report(domain_id: str) -> dict | None:
    """Generate a coverage report for a curriculum domain."""
    curriculum = load_curriculum(domain_id)
    if not curriculum:
        return None

    states = load_knowledge_states(domain_id)
    nodes = curriculum["nodes"]

    # Categorize nodes
    known = []
    mentioned = []
    engaged = []
    anchored = []
    unknown = []
    curious = []
    core_interest = []

    for node in nodes:
        state = states.get(node["id"], {})
        knowledge = state.get("knowledge", "unknown")
        interest = state.get("interest", "none")

        node_summary = {
            "id": node["id"],
            "title": node["title"],
            "level": node["level"],
            "knowledge": knowledge,
            "interest": interest,
            "confidence": state.get("confidence", 0.0),
            "sources": state.get("sources", []),
        }

        if knowledge == "anchored":
            anchored.append(node_summary)
        elif knowledge == "engaged":
            engaged.append(node_summary)
        elif knowledge == "mentioned":
            mentioned.append(node_summary)
        else:
            unknown.append(node_summary)

        if interest == "curious":
            curious.append(node_summary)
        elif interest == "core":
            core_interest.append(node_summary)

    # Find "ready to learn" gaps: unknown nodes whose prerequisites are all known
    ready_to_learn = []
    known_ids = {n["id"] for n in anchored + engaged + mentioned}
    for node in nodes:
        state = states.get(node["id"], {})
        if state.get("knowledge", "unknown") != "unknown":
            continue
        prereqs = node.get("prerequisites", [])
        if all(p in known_ids for p in prereqs):
            ready_to_learn.append({
                "id": node["id"],
                "title": node["title"],
                "level": node["level"],
                "prerequisites_met": True,
            })

    total = len(nodes)
    covered = len(anchored) + len(engaged) + len(mentioned)

    return {
        "domain_id": domain_id,
        "title": curriculum["title"],
        "total_nodes": total,
        "covered_nodes": covered,
        "coverage_percent": round(100 * covered / total) if total > 0 else 0,
        "by_state": {
            "anchored": len(anchored),
            "engaged": len(engaged),
            "mentioned": len(mentioned),
            "unknown": len(unknown),
        },
        "anchored": anchored,
        "engaged": engaged,
        "mentioned": mentioned,
        "unknown": unknown,
        "curious": curious,
        "core_interest": core_interest,
        "ready_to_learn": ready_to_learn[:20],
    }


# ─────────────────────────────────────────────
# 20 Questions knowledge elicitation
# ─────────────────────────────────────────────

def _entropy(probs: list[float]) -> float:
    """Shannon entropy of a probability distribution."""
    return -sum(p * math.log2(p) for p in probs if p > 0)


def _information_gain(p_knows: float) -> float:
    """Expected information gain from asking about a node with P(knows)=p_knows.
    Maximum when p_knows = 0.5 (maximum uncertainty)."""
    if p_knows <= 0 or p_knows >= 1:
        return 0.0
    return _entropy([p_knows, 1 - p_knows])


ELICITATION_QUESTION_PROMPT = """You are helping someone map what they know about {domain}.
This is NOT a test — it's a friendly conversation to understand their existing knowledge.

Based on the conversation so far and what we know about their knowledge, generate the next question.

CURRENT KNOWLEDGE MAP:
{knowledge_summary}

TARGET NODE TO PROBE:
Title: {node_title}
Description: {node_description}
Level: {level_desc}

QUESTION TYPE: {question_type}

CONVERSATION HISTORY:
{history}

GUIDELINES:
- Frame as curiosity, not examination
- If this is a recognition question, a simple "Have you encountered..." or "Are you familiar with..." works
- If this is a comparison question, compare two topics the user might know about at different levels
- If this is a scoping question, ask about specific aspects (when, where, who, significance)
- Keep it conversational and natural
- Include a brief (2-sentence) "card flip" summary of the topic that will be shown after the user answers

Output JSON with:
- "question": The question to ask
- "card_summary": 2-3 sentence summary of this topic (shown after user answers, like flipping a card)
- "follow_up_if_yes": A brief follow-up question to probe depth (optional)"""


def start_elicitation(domain_id: str) -> dict | None:
    """Start a new 20Q elicitation session for a curriculum domain."""
    curriculum = load_curriculum(domain_id)
    if not curriculum:
        return None

    states = load_knowledge_states(domain_id)

    # Calculate initial beliefs based on existing knowledge
    beliefs = {}
    for node in curriculum["nodes"]:
        state = states.get(node["id"], {})
        knowledge = state.get("knowledge", "unknown")

        if knowledge == "anchored":
            beliefs[node["id"]] = 0.95
        elif knowledge == "engaged":
            beliefs[node["id"]] = 0.85
        elif knowledge == "mentioned":
            beliefs[node["id"]] = state.get("confidence", 0.6)
        else:
            # Prior based on obscurity: common topics more likely known
            obscurity = node.get("obscurity", 3)
            beliefs[node["id"]] = max(0.05, 0.5 - obscurity * 0.08)

    session = {
        "id": f"elicit_{domain_id}_{int(time.time())}",
        "domain_id": domain_id,
        "started_at": datetime.now().isoformat(),
        "beliefs": beliefs,
        "history": [],
        "questions_asked": 0,
        "nodes_assessed": [],
    }

    # Generate first question (modifies session in-place: adds history, increments counter)
    result = _generate_next_question(session, curriculum)

    # Save session AFTER question generation so state is persisted
    session_path = DATA_DIR / f"{session['id']}.json"
    with open(session_path, 'w') as f:
        json.dump(session, f, indent=2)

    return result


def continue_elicitation(session_id: str, response: dict) -> dict | None:
    """Continue an elicitation session with user's response.

    response: {
        "familiarity": "unknown" | "heard_of" | "know_basics" | "could_explain" | "know_deeply",
        "interest": "none" | "curious" | "core" (optional),
        "revised": bool (optional — user revised after seeing card flip)
    }
    """
    session_path = DATA_DIR / f"{session_id}.json"
    if not session_path.exists():
        return None

    with open(session_path) as f:
        session = json.load(f)

    curriculum = load_curriculum(session["domain_id"])
    if not curriculum:
        return None

    # Process the response
    if session["history"]:
        last_q = session["history"][-1]
        node_id = last_q["node_id"]
        familiarity = response.get("familiarity", "unknown")
        interest = response.get("interest", "none")

        # Map familiarity to knowledge state and belief
        familiarity_to_knowledge = {
            "unknown": ("unknown", 0.05),
            "heard_of": ("mentioned", 0.4),
            "know_basics": ("mentioned", 0.7),
            "could_explain": ("engaged", 0.85),
            "know_deeply": ("anchored", 0.95),
        }
        knowledge, belief = familiarity_to_knowledge.get(familiarity, ("unknown", 0.05))

        # Update belief for this node
        session["beliefs"][node_id] = belief

        # Propagate through prerequisites
        nodes_by_id = {n["id"]: n for n in curriculum["nodes"]}
        node = nodes_by_id.get(node_id)

        if node and familiarity in ("unknown", "heard_of"):
            # If doesn't know this, likely doesn't know children either
            for n in curriculum["nodes"]:
                if node_id in n.get("prerequisites", []):
                    current = session["beliefs"].get(n["id"], 0.3)
                    session["beliefs"][n["id"]] = min(current, 0.2)

        if node and familiarity in ("could_explain", "know_deeply"):
            # If knows this well, likely knows prerequisites
            for prereq_id in node.get("prerequisites", []):
                current = session["beliefs"].get(prereq_id, 0.3)
                session["beliefs"][prereq_id] = max(current, 0.8)

        # Record in history
        last_q["response"] = {
            "familiarity": familiarity,
            "interest": interest,
            "belief_after": belief,
        }
        session["nodes_assessed"].append(node_id)

        # Update persistent knowledge state
        update_knowledge(
            session["domain_id"], node_id,
            knowledge=knowledge,
            interest=interest if interest != "none" else None,
            confidence=belief,
            source="elicitation",
        )

    # Check if we should stop
    if session["questions_asked"] >= 30:
        session["status"] = "complete"
        with open(session_path, 'w') as f:
            json.dump(session, f, indent=2)
        return {
            "status": "complete",
            "message": "Assessment complete! Here's your knowledge map.",
            "coverage": get_coverage_report(session["domain_id"]),
        }

    # Generate next question
    result = _generate_next_question(session, curriculum)

    # Save session
    with open(session_path, 'w') as f:
        json.dump(session, f, indent=2)

    return result


def _generate_next_question(session: dict, curriculum: dict) -> dict:
    """Select and generate the next question."""
    beliefs = session["beliefs"]
    assessed = set(session.get("nodes_assessed", []))

    # Find node with highest information gain (closest to P=0.5)
    candidates = []
    for node in curriculum["nodes"]:
        if node["id"] in assessed:
            continue
        p = beliefs.get(node["id"], 0.3)
        ig = _information_gain(p)
        candidates.append((ig, p, node))

    if not candidates:
        return {
            "status": "complete",
            "message": "All topics assessed!",
            "coverage": get_coverage_report(session["domain_id"]),
        }

    # Sort by information gain (descending), take top candidate
    candidates.sort(key=lambda x: x[0], reverse=True)
    _, p_knows, target_node = candidates[0]

    # Choose question type based on context
    q_num = session["questions_asked"]
    if q_num < 3:
        question_type = "recognition"  # Start broad
    elif q_num % 4 == 0 and len(candidates) >= 2:
        question_type = "comparison"  # Mix in comparisons
    elif p_knows > 0.6:
        question_type = "scoping"  # They probably know it — probe depth
    else:
        question_type = "recognition"

    # Build knowledge summary for LLM context
    known_titles = []
    unknown_titles = []
    for node in curriculum["nodes"]:
        nid = node["id"]
        if nid in assessed:
            state = beliefs.get(nid, 0.3)
            if state > 0.5:
                known_titles.append(node["title"])
            else:
                unknown_titles.append(node["title"])

    knowledge_summary = ""
    if known_titles:
        knowledge_summary += f"KNOWS: {', '.join(known_titles[:15])}\n"
    if unknown_titles:
        knowledge_summary += f"DOESN'T KNOW: {', '.join(unknown_titles[:10])}\n"
    if not known_titles and not unknown_titles:
        knowledge_summary = "This is the first question — we don't know anything yet."

    level_desc = {1: "broad area", 2: "specific topic", 3: "detailed concept", 4: "specific detail"}.get(
        target_node.get("level", 2), "topic")

    history_text = ""
    for h in session.get("history", [])[-5:]:
        resp = h.get("response", {})
        fam = resp.get("familiarity", "?")
        history_text += f"Q: {h.get('question', '?')}\nA: {fam}\n\n"
    if not history_text:
        history_text = "No questions asked yet."

    prompt = ELICITATION_QUESTION_PROMPT.format(
        domain=curriculum["title"],
        knowledge_summary=knowledge_summary,
        node_title=target_node["title"],
        node_description=target_node.get("description", ""),
        level_desc=level_desc,
        question_type=question_type,
        history=history_text,
    )

    raw = call_llm(prompt, model="gemini-2.5-flash", max_tokens=1024,
                   response_mime_type="application/json")

    question_text = f"Are you familiar with {target_node['title']}?"
    card_summary = target_node.get("description", "")
    follow_up = None

    if raw:
        try:
            q_data = json.loads(raw)
            question_text = q_data.get("question", question_text)
            card_summary = q_data.get("card_summary", card_summary)
            follow_up = q_data.get("follow_up_if_yes")
        except json.JSONDecodeError:
            pass

    # Record in history
    entry = {
        "question_number": session["questions_asked"] + 1,
        "node_id": target_node["id"],
        "node_title": target_node["title"],
        "question": question_text,
        "card_summary": card_summary,
        "follow_up": follow_up,
        "question_type": question_type,
        "p_knows_before": beliefs.get(target_node["id"], 0.3),
        "information_gain": _information_gain(beliefs.get(target_node["id"], 0.3)),
    }
    session["history"].append(entry)
    session["questions_asked"] += 1

    # Calculate remaining entropy
    remaining_uncertain = sum(
        1 for nid, p in beliefs.items()
        if nid not in assessed and 0.2 < p < 0.8
    )

    return {
        "status": "in_progress",
        "session_id": session["id"],
        "question_number": entry["question_number"],
        "total_nodes": len(curriculum["nodes"]),
        "assessed_so_far": len(assessed),
        "remaining_uncertain": remaining_uncertain,
        "question": question_text,
        "card_summary": card_summary,
        "follow_up": follow_up,
        "question_type": question_type,
        "node_title": target_node["title"],
        "familiarity_options": [
            {"value": "unknown", "label": "Never heard of it"},
            {"value": "heard_of", "label": "I've heard the name"},
            {"value": "know_basics", "label": "I know the basics"},
            {"value": "could_explain", "label": "I could explain it"},
            {"value": "know_deeply", "label": "I know this in depth"},
        ],
        "interest_options": [
            {"value": "none", "label": "Not particularly interested"},
            {"value": "curious", "label": "I'd like to know more"},
            {"value": "core", "label": "Deeply interesting to me"},
        ],
    }

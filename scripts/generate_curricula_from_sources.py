"""
Generate Petrarca-format curriculum JSONs from structured source data
(AP World History, AP European History, OpenStax Ancient & Classical World).

Each curriculum's topic list is defined inline. For each curriculum, calls Opus
to generate full node details (descriptions, prerequisites, dates, etc.),
then validates and saves to data/curricula/.

Usage:
    python3 scripts/generate_curricula_from_sources.py --curriculum ap_world_history
    python3 scripts/generate_curricula_from_sources.py --curriculum ap_european_history
    python3 scripts/generate_curricula_from_sources.py --curriculum ancient_classical_world
    python3 scripts/generate_curricula_from_sources.py --curriculum all
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(os.environ.get('CURRICULUM_DIR', '/opt/petrarca/data/curricula'))

# ─────────────────────────────────────────────
# Opus calling (same pattern as curriculum.py)
# ─────────────────────────────────────────────

def call_opus(prompt: str, max_tokens: int = 32768, timeout: int = 600) -> str | None:
    """Call Claude Opus. Tries Anthropic SDK first, then claude CLI."""
    anthropic_key = os.environ.get('ANTHROPIC_KEY') or os.environ.get('ANTHROPIC_API_KEY')

    if anthropic_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key, timeout=600.0)
            with client.messages.stream(
                model='claude-opus-4-6',
                max_tokens=max_tokens,
                messages=[{'role': 'user', 'content': prompt}],
            ) as stream:
                return stream.get_final_text()
        except Exception as e:
            print(f'  Anthropic SDK failed: {e}', flush=True)

    # Fallback: claude -p CLI (free with Max plan, local only)
    try:
        cmd = ['claude', '-p', '--tools', '', '--output-format', 'json',
               '--model', 'opus', '--no-session-persistence']
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout)
        if proc.returncode == 0 and proc.stdout.strip():
            resp = json.loads(proc.stdout)
            if not resp.get('is_error'):
                return resp.get('result', '')
    except Exception as e:
        print(f'  claude CLI failed: {e}', flush=True)

    return None


# ─────────────────────────────────────────────
# ID generation (matches curriculum.py)
# ─────────────────────────────────────────────

def make_node_id(domain_id: str, title: str) -> str:
    slug = title.lower().strip()
    slug = ''.join(c if c.isalnum() or c == ' ' else '' for c in slug)
    slug = '_'.join(slug.split()[:6])
    return f"{domain_id[:10]}_{slug}"


# ─────────────────────────────────────────────
# Source data: AP World History Modern (1200-present)
# 9 units, 66 topics
# ─────────────────────────────────────────────

AP_WORLD_HISTORY = {
    "id": "ap_world_history_modern",
    "title": "AP World History: Modern (1200-Present)",
    "description": "World history from 1200 CE to the present, covering global interactions, state building, economic systems, social structures, and technology across all major civilizations.",
    "date_range": "1200 CE to present",
    "units": [
        {
            "unit": "Unit 1: The Global Tapestry (c. 1200-1450)",
            "topics": [
                "1.1 Developments in East Asia from c. 1200 to c. 1450",
                "1.2 Developments in Dar al-Islam from c. 1200 to c. 1450",
                "1.3 Developments in South and Southeast Asia from c. 1200 to c. 1450",
                "1.4 Developments in the Americas from c. 1200 to c. 1450",
                "1.5 Developments in Africa from c. 1200 to c. 1450",
                "1.6 Developments in Europe from c. 1200 to c. 1450",
                "1.7 Comparison in the Period from c. 1200 to c. 1450",
            ],
        },
        {
            "unit": "Unit 2: Networks of Exchange (c. 1200-1450)",
            "topics": [
                "2.1 The Silk Roads",
                "2.2 The Mongol Empire and the Making of the Modern World",
                "2.3 Exchange in the Indian Ocean World",
                "2.4 Trans-Saharan Trade Routes",
                "2.5 Cultural Consequences of Connectivity",
                "2.6 Environmental Consequences of Connectivity",
                "2.7 Comparison of Economic Exchange",
            ],
        },
        {
            "unit": "Unit 3: Land-Based Empires (c. 1450-1750)",
            "topics": [
                "3.1 Empires Expand",
                "3.2 Empires: Administration",
                "3.3 Empires: Belief Systems",
                "3.4 Comparison in Land-Based Empires",
            ],
        },
        {
            "unit": "Unit 4: Transoceanic Interconnections (c. 1450-1750)",
            "topics": [
                "4.1 Technological Innovations from 1450 to 1750",
                "4.2 Exploration: Causes and Events from 1450 to 1750",
                "4.3 Columbian Exchange",
                "4.4 Maritime Empires Established",
                "4.5 Maritime Empires Maintained and Developed",
                "4.6 Internal and External Challenges to State Power from 1450 to 1750",
                "4.7 Changing Social Hierarchies from 1450 to 1750",
                "4.8 Continuity and Change from 1450 to 1750",
            ],
        },
        {
            "unit": "Unit 5: Revolutions (c. 1750-1900)",
            "topics": [
                "5.1 The Enlightenment",
                "5.2 Nationalism and Revolutions in the Period from 1750 to 1900",
                "5.3 Industrial Revolution Begins",
                "5.4 Industrialization Spreads in the Period from 1750 to 1900",
                "5.5 Technology of the Industrial Age",
                "5.6 Industrialization: Government's Role from 1750 to 1900",
                "5.7 Economic Developments and Their Social Impact in the Period from 1750 to 1900",
                "5.8 Reactions to the Industrial Economy from 1750 to 1900",
            ],
        },
        {
            "unit": "Unit 6: Consequences of Industrialization (c. 1750-1900)",
            "topics": [
                "6.1 Rationales for Imperialism from 1750 to 1900",
                "6.2 State Expansion from 1750 to 1900",
                "6.3 Indigenous Responses to State Expansion from 1750 to 1900",
                "6.4 Global Economic Development from 1750 to 1900",
                "6.5 Economic Imperialism from 1750 to 1900",
                "6.6 Causes of Migration in an Interconnected World",
                "6.7 Effects of Migration",
                "6.8 Causation in the Imperial Age",
            ],
        },
        {
            "unit": "Unit 7: Global Conflict (c. 1900-present)",
            "topics": [
                "7.1 Shifting Power After 1900",
                "7.2 Causes of World War I",
                "7.3 Conducting World War I",
                "7.4 The Economy in the Interwar Period",
                "7.5 Unresolved Tensions After World War I",
                "7.6 Causes of World War II",
                "7.7 Conducting World War II",
                "7.8 Mass Atrocities After 1900",
                "7.9 Causation in Global Conflict",
            ],
        },
        {
            "unit": "Unit 8: Cold War and Decolonization (c. 1900-present)",
            "topics": [
                "8.1 Setting the Stage for the Cold War and Decolonization",
                "8.2 The Cold War",
                "8.3 Effects of the Cold War",
                "8.4 Spread of Communism After 1900",
                "8.5 Decolonization After 1900",
                "8.6 Newly Independent States",
                "8.7 Global Resistance to Established Power Structures After 1900",
                "8.8 End of the Cold War",
                "8.9 Causation in the Age of the Cold War and Decolonization",
            ],
        },
        {
            "unit": "Unit 9: Globalization (c. 1900-present)",
            "topics": [
                "9.1 Advances in Technology and Exchange After 1900",
                "9.2 Technological Advances and Limitations After 1900: Disease",
                "9.3 Technological Advances: Debates About the Environment After 1900",
                "9.4 Economics in the Global Age",
                "9.5 Calls for Reform and Responses After 1900",
                "9.6 Globalized Culture After 1900",
                "9.7 Resistance to Globalization After 1900",
                "9.8 Institutions Developing in a Globalized World",
                "9.9 Continuity and Change in a Globalized World",
            ],
        },
    ],
}


# ─────────────────────────────────────────────
# Source data: AP European History (1450-present)
# 9 units, 88 topics
# ─────────────────────────────────────────────

AP_EUROPEAN_HISTORY = {
    "id": "ap_european_history",
    "title": "AP European History (1450-Present)",
    "description": "European history from the Renaissance to the present day, covering intellectual, political, diplomatic, social, cultural, and economic developments that shaped Europe and the world.",
    "date_range": "1450 CE to present",
    "units": [
        {
            "unit": "Unit 1: Renaissance and Exploration (c. 1450-1648)",
            "topics": [
                "1.1 Contextualizing Renaissance and Discovery",
                "1.2 Italian Renaissance",
                "1.3 Northern Renaissance",
                "1.4 Printing Press",
                "1.5 New Monarchies",
                "1.6 Technological Advances and the Age of Exploration",
                "1.7 Rivalry Between European States for Colonial Possessions",
                "1.8 Columbian Exchange, the Commercial Revolution, and Mercantilism",
                "1.9 The Reformation",
                "1.10 The Catholic/Counter-Reformation",
                "1.11 Religious Conflicts and Wars of Religion",
            ],
        },
        {
            "unit": "Unit 2: Age of Reformation (c. 1450-1648)",
            "topics": [
                "2.1 Contextualizing 16th- and 17th-Century Challenges and State Responses",
                "2.2 The Rise of Absolutism and the Consolidation of Power",
                "2.3 The English Civil War",
                "2.4 The Thirty Years' War",
                "2.5 The Dutch Golden Age",
                "2.6 Balance of Power in Europe",
                "2.7 Mercantilism and the Development of National Economies",
                "2.8 The Scientific Revolution",
                "2.9 Continuity and Change in the Age of Reformation",
            ],
        },
        {
            "unit": "Unit 3: Absolutism and Constitutionalism (c. 1648-1815)",
            "topics": [
                "3.1 Contextualizing Absolutism and Constitutionalism",
                "3.2 The English Restoration and Glorious Revolution",
                "3.3 The Palace of Versailles as Political Architecture",
                "3.4 Louis XIV and French Absolutism",
                "3.5 Absolutism in Central and Eastern Europe",
                "3.6 The Enlightenment",
                "3.7 Enlightened Absolutism",
                "3.8 18th-Century European Society",
                "3.9 The Atlantic Economy and Colonial Competition",
                "3.10 The Seven Years' War",
                "3.11 Continuity and Change in Absolutism and Constitutionalism",
            ],
        },
        {
            "unit": "Unit 4: Scientific, Philosophical, and Political Developments (c. 1648-1815)",
            "topics": [
                "4.1 Contextualizing 18th-Century States",
                "4.2 The Rise of Enlightenment Thought",
                "4.3 Social Effects of the Enlightenment",
                "4.4 18th-Century Economic Change",
                "4.5 The French Revolution",
                "4.6 Napoleon's Rise, Dominance, and Defeat",
                "4.7 The Congress of Vienna",
                "4.8 Romanticism",
                "4.9 Continuity and Change in the Age of Revolutions",
            ],
        },
        {
            "unit": "Unit 5: Conflict, Crisis, and Reaction in the Early Modern Period (c. 1648-1815)",
            "topics": [
                "5.1 Contextualizing Industrialization",
                "5.2 The Industrialization of Continental Europe",
                "5.3 Second Industrial Revolution",
                "5.4 Social Effects of Industrialization",
                "5.5 Ideological Responses to Industrialization",
                "5.6 The Congress System and Concert of Europe",
                "5.7 The Revolutions of 1848",
                "5.8 National Unification and Diplomacy",
                "5.9 Darwinism and Social Darwinism",
                "5.10 Continuity and Change in Industrialization",
            ],
        },
        {
            "unit": "Unit 6: Industrialization and Its Effects (c. 1815-1914)",
            "topics": [
                "6.1 Contextualizing 19th-Century Perspectives and Political Developments",
                "6.2 The Rise of Realpolitik: Cavour and Italian Unification",
                "6.3 The Rise of Realpolitik: Bismarck and German Unification",
                "6.4 New Imperialism: Motivations and Methods",
                "6.5 New Imperialism: Acquired Territories",
                "6.6 New Imperialism: Colonial Resistance",
                "6.7 Reform in the Ottoman Empire",
                "6.8 19th-Century Culture and Arts",
                "6.9 Responses to Industrialization Over Time",
            ],
        },
        {
            "unit": "Unit 7: 19th-Century Perspectives and Political Developments (c. 1815-1914)",
            "topics": [
                "7.1 Contextualizing 20th-Century Global Conflicts",
                "7.2 World War I",
                "7.3 The Russian Revolution",
                "7.4 Versailles Conference and Peace Settlement",
                "7.5 National Self-Determination",
                "7.6 The Rise of Fascism",
                "7.7 The Great Depression",
                "7.8 World War II and the Holocaust",
                "7.9 The Cold War: Ideology and the Iron Curtain",
                "7.10 Continuity and Change in 20th-Century Conflicts",
            ],
        },
        {
            "unit": "Unit 8: 20th-Century Global Conflicts (c. 1914-present)",
            "topics": [
                "8.1 Contextualizing Cold War and Contemporary Europe",
                "8.2 Rebuilding Europe: Marshall Plan and European Integration",
                "8.3 Demographic Changes and Immigration",
                "8.4 The Welfare State",
                "8.5 Postwar Cultural Developments",
                "8.6 The Fall of Communism",
                "8.7 Migration and Its Effects",
                "8.8 The European Union",
                "8.9 Continuity and Change in the Cold War and Contemporary Europe",
            ],
        },
        {
            "unit": "Unit 9: Cold War and Contemporary Europe (c. 1914-present)",
            "topics": [
                "9.1 Contextualizing Globalization",
                "9.2 20th- and 21st-Century Feminism",
                "9.3 Technology and Innovation in the 20th and 21st Centuries",
                "9.4 Environmentalism and Green Parties",
                "9.5 Terrorism and Its Consequences",
                "9.6 The European Union in the 21st Century",
                "9.7 The Challenges of European Unity",
                "9.8 Continuity and Change in Globalization",
            ],
        },
    ],
}


# ─────────────────────────────────────────────
# Source data: Ancient & Classical World (OpenStax Vol 1, Chs 3-13)
# Prehistory to ~1200 CE
# ─────────────────────────────────────────────

ANCIENT_CLASSICAL_WORLD = {
    "id": "ancient_classical_world",
    "title": "Ancient and Classical World (Prehistory to 1200 CE)",
    "description": "World history from the earliest civilizations through the classical and post-classical eras, covering Mesopotamia, Egypt, Greece, Rome, China, India, the Islamic Golden Age, and early medieval developments across all major regions.",
    "date_range": "c. 3500 BCE to 1200 CE",
    "units": [
        {
            "unit": "Unit 1: Early Civilizations and the Ancient Near East",
            "chapters": [
                {
                    "chapter": "Chapter 3: Early Civilizations and Urban Societies",
                    "sections": [
                        "3.1 Early Civilizations",
                        "3.2 Ancient Mesopotamia",
                        "3.3 Ancient Egypt",
                        "3.4 The Indus Valley Civilization",
                        "3.5 Early China (Shang and Zhou Dynasties)",
                    ],
                },
                {
                    "chapter": "Chapter 4: The Near East",
                    "sections": [
                        "4.1 The Hittites",
                        "4.2 The Assyrian Empire",
                        "4.3 The Neo-Babylonian Empire",
                        "4.4 The Persian Empire (Achaemenids)",
                        "4.5 Ancient Israel and the Hebrew Bible",
                        "4.6 Phoenicians and Their Legacy",
                    ],
                },
            ],
        },
        {
            "unit": "Unit 2: The Classical Mediterranean World",
            "chapters": [
                {
                    "chapter": "Chapter 5: Ancient Greece",
                    "sections": [
                        "5.1 Greek Dark Ages and Archaic Period",
                        "5.2 The Greek Polis: Athens and Sparta",
                        "5.3 The Persian Wars",
                        "5.4 The Golden Age of Athens",
                        "5.5 The Peloponnesian War",
                        "5.6 Greek Philosophy, Science, and Culture",
                    ],
                },
                {
                    "chapter": "Chapter 6: The Hellenistic World",
                    "sections": [
                        "6.1 Alexander the Great and His Conquests",
                        "6.2 The Successor Kingdoms (Diadochi)",
                        "6.3 Hellenistic Culture, Science, and Philosophy",
                        "6.4 Hellenistic Economy and Trade",
                    ],
                },
                {
                    "chapter": "Chapter 7: The Roman Republic",
                    "sections": [
                        "7.1 The Founding and Early Republic",
                        "7.2 Roman Expansion in Italy and the Mediterranean",
                        "7.3 The Punic Wars",
                        "7.4 Crisis of the Late Republic",
                        "7.5 Julius Caesar and the End of the Republic",
                    ],
                },
                {
                    "chapter": "Chapter 8: The Roman Empire",
                    "sections": [
                        "8.1 Augustus and the Principate",
                        "8.2 The Pax Romana",
                        "8.3 Roman Society, Economy, and Culture",
                        "8.4 The Rise of Christianity",
                        "8.5 Crisis of the Third Century and Reforms",
                        "8.6 The Fall of the Western Roman Empire",
                    ],
                },
            ],
        },
        {
            "unit": "Unit 3: Ancient Asia and the Americas",
            "chapters": [
                {
                    "chapter": "Chapter 9: Ancient and Imperial China",
                    "sections": [
                        "9.1 The Qin Dynasty and Unification of China",
                        "9.2 The Han Dynasty",
                        "9.3 Chinese Philosophy: Confucianism, Daoism, Legalism",
                        "9.4 The Silk Roads and Chinese Trade",
                        "9.5 Period of Division and the Sui-Tang Reunification",
                    ],
                },
                {
                    "chapter": "Chapter 10: South and Southeast Asia",
                    "sections": [
                        "10.1 The Maurya Empire",
                        "10.2 The Gupta Empire and Classical Indian Culture",
                        "10.3 Hinduism and Buddhism: Origins and Spread",
                        "10.4 Indian Ocean Trade Networks",
                        "10.5 Kingdoms of Southeast Asia (Funan, Srivijaya, Khmer)",
                    ],
                },
                {
                    "chapter": "Chapter 11: Early Americas",
                    "sections": [
                        "11.1 Mesoamerica: The Olmec and Maya",
                        "11.2 Teotihuacan and Classic Mesoamerican Cities",
                        "11.3 The Andean World: Chavín, Moche, and Nazca",
                        "11.4 North American Peoples (Ancestral Puebloans, Mound Builders)",
                    ],
                },
            ],
        },
        {
            "unit": "Unit 4: The Post-Classical World (c. 500-1200 CE)",
            "chapters": [
                {
                    "chapter": "Chapter 12: The Islamic World",
                    "sections": [
                        "12.1 The Rise of Islam and the Prophet Muhammad",
                        "12.2 The Umayyad and Abbasid Caliphates",
                        "12.3 Islamic Golden Age: Science, Philosophy, and Culture",
                        "12.4 Trade and Economy in the Islamic World",
                        "12.5 Islamic Expansion: North Africa, Iberia, and Central Asia",
                    ],
                },
                {
                    "chapter": "Chapter 13: The Medieval World",
                    "sections": [
                        "13.1 The Byzantine Empire",
                        "13.2 Early Medieval Europe and the Carolingian Empire",
                        "13.3 Feudalism and Manorialism",
                        "13.4 The Viking Age and Norse Expansion",
                        "13.5 The Crusades",
                        "13.6 Song Dynasty China and East Asian Developments",
                        "13.7 Sub-Saharan African Kingdoms (Ghana, Mali, Great Zimbabwe)",
                    ],
                },
            ],
        },
    ],
}


# ─────────────────────────────────────────────
# Prompt formatting
# ─────────────────────────────────────────────

def format_topics_for_ap(curriculum_data: dict) -> str:
    """Format AP-style curriculum (units + topics) into text for the prompt."""
    lines = []
    for unit_data in curriculum_data["units"]:
        lines.append(f"\n{unit_data['unit']}")
        for topic in unit_data["topics"]:
            lines.append(f"  - {topic}")
    return "\n".join(lines)


def format_topics_for_openstax(curriculum_data: dict) -> str:
    """Format OpenStax-style curriculum (units + chapters + sections) into text."""
    lines = []
    for unit_data in curriculum_data["units"]:
        lines.append(f"\n{unit_data['unit']}")
        for chapter_data in unit_data["chapters"]:
            lines.append(f"  {chapter_data['chapter']}")
            for section in chapter_data["sections"]:
                lines.append(f"    - {section}")
    return "\n".join(lines)


def count_topics_ap(curriculum_data: dict) -> int:
    total = 0
    for unit_data in curriculum_data["units"]:
        total += 1  # unit itself
        total += len(unit_data["topics"])
    return total


def count_topics_openstax(curriculum_data: dict) -> int:
    total = 0
    for unit_data in curriculum_data["units"]:
        total += 1  # unit
        for chapter_data in unit_data["chapters"]:
            total += 1  # chapter
            total += len(chapter_data["sections"])
    return total


GENERATION_PROMPT_AP = """You are generating a structured curriculum for a knowledge mapping system. Convert these AP course topics into fully detailed curriculum nodes.

DOMAIN: {domain_title}
DOMAIN ID: {domain_id}
DATE RANGE: {date_range}

This is an AP course with units and topics. Map:
- Units -> Level 1 (Area) nodes
- Topics -> Level 2 (Topic) nodes

TOPICS:
{topics_text}

For EACH node (both units and topics), generate a JSON object with these fields:
- "id": string — format: "{domain_id_prefix}_slugified_short_name" (lowercase, underscores, max 6 words in slug). The domain_id_prefix is "{domain_id_prefix}".
- "title": string — clear, specific name. Use the topic name but improve readability (e.g., drop "from c. 1200 to c. 1450" repetition, make it more descriptive).
- "description": string — 2-3 sentences defining what "knowing this" means at an introductory level. Be specific: mention key events, figures, movements, concepts. This description serves as an answer guide for review questions.
- "parent_id": string or null — the ID of the parent unit node (null for level 1 units).
- "level": integer — 1 for units, 2 for topics.
- "prerequisites": array of strings — IDs of nodes that should be known first. Only direct prerequisites within this curriculum. Earlier units are natural prerequisites for later ones. Within a unit, list specific topic dependencies.
- "obscurity": integer 1-5 — 1 = widely known by educated adults, 2 = known with some historical interest, 3 = requires specific study, 4 = specialized, 5 = specialist only. Most AP topics should be 1-3.
- "bloom_floor": string — "recognize" for basic facts/dates, "explain" for concepts requiring understanding, "analyze" for topics requiring comparison/evaluation/synthesis.
- "date_start": integer — start year (negative for BCE). Be specific based on the topic's content.
- "date_end": integer — end year. Be specific.

IMPORTANT GUIDELINES:
- Unit (level 1) nodes should have broad date ranges and high-level descriptions summarizing what the unit covers.
- Topic (level 2) nodes should be specific, with targeted date ranges and detailed descriptions.
- Prerequisites should form a logical learning path. Don't just chain everything linearly — identify genuine conceptual dependencies.
- Descriptions should be rich enough that someone could self-assess whether they know the material.
- Comparison/continuity topics (e.g., "Comparison in the Period") should have "analyze" bloom_floor.
- IDs must be unique. Use descriptive slugs.

Output ONLY a JSON array of node objects. No markdown fencing, no explanation — just the raw JSON array."""


GENERATION_PROMPT_OPENSTAX = """You are generating a structured curriculum for a knowledge mapping system. Convert these textbook chapters and sections into fully detailed curriculum nodes.

DOMAIN: {domain_title}
DOMAIN ID: {domain_id}
DATE RANGE: {date_range}

This textbook is organized as: Units -> Chapters -> Sections. Map:
- Units -> Level 1 (Area) nodes
- Chapters -> Level 2 (Topic) nodes
- Sections -> Level 3 (Concept) nodes

CONTENTS:
{topics_text}

For EACH node (units, chapters, and sections), generate a JSON object with these fields:
- "id": string — format: "{domain_id_prefix}_slugified_short_name" (lowercase, underscores, max 6 words in slug). The domain_id_prefix is "{domain_id_prefix}".
- "title": string — clear, specific name. Improve the section titles for clarity where needed.
- "description": string — 2-3 sentences defining what "knowing this" means. Be specific: mention key events, figures, dates, and concepts. This serves as an answer guide for review questions.
- "parent_id": string or null — the ID of the parent node (null for level 1 units, unit ID for chapters, chapter ID for sections).
- "level": integer — 1 for units, 2 for chapters, 3 for sections.
- "prerequisites": array of strings — IDs of nodes that should be known first. Only direct prerequisites within this curriculum. Follow logical learning order, not just sequential order.
- "obscurity": integer 1-5 — 1 = widely known, 5 = specialist. Most intro textbook material should be 1-3.
- "bloom_floor": string — "recognize" for basic facts, "explain" for concepts requiring understanding, "analyze" for comparison/evaluation topics.
- "date_start": integer — start year (negative for BCE). Be historically precise.
- "date_end": integer — end year. Be historically precise.

IMPORTANT GUIDELINES:
- Unit (level 1) nodes should span the full date range of their contents.
- Chapter (level 2) nodes should have the date range of their chapter's subject matter.
- Section (level 3) nodes should have precise date ranges for the specific topic.
- For prehistoric/undated topics, use approximate conventional dates.
- Prerequisites should reflect genuine conceptual dependencies — e.g., you need to understand the Roman Republic before the Roman Empire.
- Descriptions should be detailed enough for self-assessment.
- IDs must be unique. Use descriptive slugs.

Output ONLY a JSON array of node objects. No markdown fencing, no explanation — just the raw JSON array."""


# ─────────────────────────────────────────────
# JSON parsing and validation
# ─────────────────────────────────────────────

def extract_json_array(raw: str) -> list | None:
    """Extract a JSON array from Opus response, handling markdown wrapping."""
    raw = raw.strip()

    # Strip markdown code fences
    if raw.startswith('```'):
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw.strip())

    # Try direct parse first
    try:
        result = json.loads(raw)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # Try to find embedded JSON array
    m = re.search(r'\[[\s\S]*\]', raw)
    if m:
        try:
            result = json.loads(m.group())
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    return None


def validate_nodes(nodes: list[dict], domain_id: str) -> list[str]:
    """Validate generated nodes. Returns list of warnings."""
    warnings = []
    ids = {n["id"] for n in nodes}

    for node in nodes:
        # Check required fields
        for field in ["id", "title", "description", "level"]:
            if not node.get(field):
                warnings.append(f"Node missing '{field}': {node.get('id', 'UNKNOWN')}")

        # Check parent references
        if node.get("parent_id") and node["parent_id"] not in ids:
            warnings.append(f"Node '{node['id']}' references unknown parent '{node['parent_id']}'")

        # Check prerequisite references
        for prereq in node.get("prerequisites", []):
            if prereq not in ids:
                warnings.append(f"Node '{node['id']}' references unknown prerequisite '{prereq}'")

        # Check dates
        if "date_start" not in node or "date_end" not in node:
            warnings.append(f"Node '{node['id']}' missing date_start or date_end")

    # Check for duplicate IDs
    seen = set()
    for node in nodes:
        if node["id"] in seen:
            warnings.append(f"Duplicate node ID: '{node['id']}'")
        seen.add(node["id"])

    return warnings


def fix_prerequisite_references(nodes: list[dict]) -> int:
    """Remove prerequisite references to non-existent nodes. Returns count of removed refs."""
    ids = {n["id"] for n in nodes}
    removed = 0
    for node in nodes:
        orig = node.get("prerequisites", [])
        node["prerequisites"] = [p for p in orig if p in ids]
        removed += len(orig) - len(node["prerequisites"])
    return removed


def fix_parent_references(nodes: list[dict]) -> int:
    """Remove parent references to non-existent nodes. Returns count of removed refs."""
    ids = {n["id"] for n in nodes}
    removed = 0
    for node in nodes:
        if node.get("parent_id") and node["parent_id"] not in ids:
            node["parent_id"] = None
            removed += 1
    return removed


# ─────────────────────────────────────────────
# Curriculum generation
# ─────────────────────────────────────────────

def generate_ap_curriculum(curriculum_data: dict, output_dir: Path, dry_run: bool = False) -> dict | None:
    """Generate a full Petrarca curriculum from AP course data."""
    domain_id = curriculum_data["id"]
    domain_title = curriculum_data["title"]
    date_range = curriculum_data["date_range"]
    domain_id_prefix = domain_id[:10]

    topics_text = format_topics_for_ap(curriculum_data)
    expected_count = count_topics_ap(curriculum_data)

    print(f"\n{'='*60}", flush=True)
    print(f"Generating: {domain_title}", flush=True)
    print(f"Domain ID: {domain_id}", flush=True)
    print(f"Expected nodes: ~{expected_count} (units + topics)", flush=True)
    print(f"{'='*60}", flush=True)

    prompt = GENERATION_PROMPT_AP.format(
        domain_title=domain_title,
        domain_id=domain_id,
        date_range=date_range,
        domain_id_prefix=domain_id_prefix,
        topics_text=topics_text,
    )

    if dry_run:
        print(f"\n[DRY RUN] Would send prompt ({len(prompt)} chars) to Opus", flush=True)
        print(f"First 500 chars of prompt:\n{prompt[:500]}...", flush=True)
        return None

    print(f"\nCalling Opus ({len(prompt)} chars)...", flush=True)
    t0 = time.time()
    raw = call_opus(prompt, max_tokens=32768)
    elapsed = time.time() - t0
    print(f"  Opus responded in {elapsed:.1f}s", flush=True)

    if not raw:
        print("  ERROR: No response from Opus", flush=True)
        return None

    print(f"  Response length: {len(raw)} chars", flush=True)

    nodes = extract_json_array(raw)
    if not nodes:
        print(f"  ERROR: Could not parse JSON from response", flush=True)
        print(f"  First 300 chars: {raw[:300]}", flush=True)
        # Save raw response for debugging
        debug_path = output_dir / f"{domain_id}_raw_response.txt"
        with open(debug_path, 'w') as f:
            f.write(raw)
        print(f"  Raw response saved to {debug_path}", flush=True)
        return None

    print(f"  Parsed {len(nodes)} nodes", flush=True)

    # Fix broken references
    removed_parents = fix_parent_references(nodes)
    removed_prereqs = fix_prerequisite_references(nodes)
    if removed_parents:
        print(f"  Fixed {removed_parents} broken parent references", flush=True)
    if removed_prereqs:
        print(f"  Fixed {removed_prereqs} broken prerequisite references", flush=True)

    # Validate
    warnings = validate_nodes(nodes, domain_id)
    if warnings:
        print(f"  Warnings ({len(warnings)}):", flush=True)
        for w in warnings[:10]:
            print(f"    - {w}", flush=True)
        if len(warnings) > 10:
            print(f"    ... and {len(warnings)-10} more", flush=True)

    # Count by level
    level_counts = {}
    for n in nodes:
        lv = n.get("level", "?")
        level_counts[lv] = level_counts.get(lv, 0) + 1
    print(f"  Node levels: {dict(sorted(level_counts.items()))}", flush=True)

    # Build final curriculum
    curriculum = {
        "id": domain_id,
        "title": domain_title,
        "description": curriculum_data["description"],
        "depth": "introductory",
        "generated_at": datetime.now().isoformat(),
        "generated_by": "claude-opus-4-6",
        "version": 1,
        "node_count": len(nodes),
        "nodes": nodes,
    }

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{domain_id}.json"
    with open(path, 'w') as f:
        json.dump(curriculum, f, indent=2)

    print(f"\n  Saved to {path}", flush=True)
    print(f"  {len(nodes)} nodes total", flush=True)
    return curriculum


def generate_openstax_curriculum(curriculum_data: dict, output_dir: Path, dry_run: bool = False) -> dict | None:
    """Generate a full Petrarca curriculum from OpenStax-style data."""
    domain_id = curriculum_data["id"]
    domain_title = curriculum_data["title"]
    date_range = curriculum_data["date_range"]
    domain_id_prefix = domain_id[:10]

    topics_text = format_topics_for_openstax(curriculum_data)
    expected_count = count_topics_openstax(curriculum_data)

    print(f"\n{'='*60}", flush=True)
    print(f"Generating: {domain_title}", flush=True)
    print(f"Domain ID: {domain_id}", flush=True)
    print(f"Expected nodes: ~{expected_count} (units + chapters + sections)", flush=True)
    print(f"{'='*60}", flush=True)

    prompt = GENERATION_PROMPT_OPENSTAX.format(
        domain_title=domain_title,
        domain_id=domain_id,
        date_range=date_range,
        domain_id_prefix=domain_id_prefix,
        topics_text=topics_text,
    )

    if dry_run:
        print(f"\n[DRY RUN] Would send prompt ({len(prompt)} chars) to Opus", flush=True)
        print(f"First 500 chars of prompt:\n{prompt[:500]}...", flush=True)
        return None

    print(f"\nCalling Opus ({len(prompt)} chars)...", flush=True)
    t0 = time.time()
    raw = call_opus(prompt, max_tokens=65536)
    elapsed = time.time() - t0
    print(f"  Opus responded in {elapsed:.1f}s", flush=True)

    if not raw:
        print("  ERROR: No response from Opus", flush=True)
        return None

    print(f"  Response length: {len(raw)} chars", flush=True)

    nodes = extract_json_array(raw)
    if not nodes:
        print(f"  ERROR: Could not parse JSON from response", flush=True)
        print(f"  First 300 chars: {raw[:300]}", flush=True)
        debug_path = output_dir / f"{domain_id}_raw_response.txt"
        with open(debug_path, 'w') as f:
            f.write(raw)
        print(f"  Raw response saved to {debug_path}", flush=True)
        return None

    print(f"  Parsed {len(nodes)} nodes", flush=True)

    # Fix broken references
    removed_parents = fix_parent_references(nodes)
    removed_prereqs = fix_prerequisite_references(nodes)
    if removed_parents:
        print(f"  Fixed {removed_parents} broken parent references", flush=True)
    if removed_prereqs:
        print(f"  Fixed {removed_prereqs} broken prerequisite references", flush=True)

    # Validate
    warnings = validate_nodes(nodes, domain_id)
    if warnings:
        print(f"  Warnings ({len(warnings)}):", flush=True)
        for w in warnings[:10]:
            print(f"    - {w}", flush=True)
        if len(warnings) > 10:
            print(f"    ... and {len(warnings)-10} more", flush=True)

    # Count by level
    level_counts = {}
    for n in nodes:
        lv = n.get("level", "?")
        level_counts[lv] = level_counts.get(lv, 0) + 1
    print(f"  Node levels: {dict(sorted(level_counts.items()))}", flush=True)

    # Build final curriculum
    curriculum = {
        "id": domain_id,
        "title": domain_title,
        "description": curriculum_data["description"],
        "depth": "introductory",
        "generated_at": datetime.now().isoformat(),
        "generated_by": "claude-opus-4-6",
        "version": 1,
        "node_count": len(nodes),
        "nodes": nodes,
    }

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{domain_id}.json"
    with open(path, 'w') as f:
        json.dump(curriculum, f, indent=2)

    print(f"\n  Saved to {path}", flush=True)
    print(f"  {len(nodes)} nodes total", flush=True)
    return curriculum


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

CURRICULA = {
    "ap_world_history": ("ap", AP_WORLD_HISTORY),
    "ap_european_history": ("ap", AP_EUROPEAN_HISTORY),
    "ancient_classical_world": ("openstax", ANCIENT_CLASSICAL_WORLD),
}


def main():
    parser = argparse.ArgumentParser(
        description="Generate Petrarca curriculum JSONs from structured source data"
    )
    parser.add_argument(
        "--curriculum",
        required=True,
        choices=list(CURRICULA.keys()) + ["all"],
        help="Which curriculum to generate (or 'all')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print prompt info without calling Opus",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help=f"Override output directory (default: {DATA_DIR})",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else DATA_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.output_dir:
        print(f"Output directory: {output_dir}", flush=True)

    targets = list(CURRICULA.keys()) if args.curriculum == "all" else [args.curriculum]

    results = {}
    for name in targets:
        kind, data = CURRICULA[name]
        if kind == "ap":
            result = generate_ap_curriculum(data, output_dir=output_dir, dry_run=args.dry_run)
        else:
            result = generate_openstax_curriculum(data, output_dir=output_dir, dry_run=args.dry_run)
        results[name] = result

    # Summary
    print(f"\n{'='*60}", flush=True)
    print("SUMMARY", flush=True)
    print(f"{'='*60}", flush=True)
    for name, result in results.items():
        if result:
            print(f"  {name}: {result['node_count']} nodes -> {output_dir / (result['id'] + '.json')}", flush=True)
        elif args.dry_run:
            print(f"  {name}: [dry run]", flush=True)
        else:
            print(f"  {name}: FAILED", flush=True)


if __name__ == "__main__":
    main()

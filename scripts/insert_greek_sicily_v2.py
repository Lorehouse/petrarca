"""Insert 19 hand-crafted Greek Sicily Level 1 questions with rich answers and memory hooks."""

import json
import os
import sys
import hashlib

sys.path.insert(0, os.path.dirname(__file__))
from db import get_connection, init_db

DOMAIN = 'sicily_history_culture_and_legacy'

QUESTIONS = [
    # ── Colonization ──
    {
        'question': 'What was the first Greek colony on Sicily?',
        'answer': 'Naxos',
        'rich_answer': 'Naxos — founded by settlers from Chalcis around 734 BC on the east coast. Syracuse was founded the same year by Corinthians, but Naxos was technically first.',
        'answer_type': 'name',
        'level': 1,
        'node_title': 'The Western Greeks: Why They Came',
        'memory_hook': 'Naxos and Syracuse — both 734 BC, like twins born the same year. Naxos came first but Syracuse became the star.',
        'anchors': json.dumps(['Same year as Syracuse founding', 'About 250 years before Battle of Himera']),
        'grading_options': json.dumps(['correct', 'wrong']),
    },
    {
        'question': 'When did Greek colonization of Sicily begin?',
        'answer': '~734 BC',
        'rich_answer': 'Around 734 BC, when Chalcidians founded Naxos and Corinthians founded Syracuse. This was part of the great wave of Greek colonization across the Mediterranean — driven by land hunger, trade ambitions, and political exile from overpopulated city-states.',
        'answer_type': 'date',
        'level': 1,
        'node_title': 'The Western Greeks: Why They Came',
        'memory_hook': '734 — about 250 years before the Battle of Himera (480). Three-quarters of a millennium before Christ.',
        'anchors': json.dumps(['~250 years before Himera (480 BC)', '~500 years before Sicily becomes Roman (241 BC)']),
        'grading_options': json.dumps(['exact_year', 'right_decade', 'right_century', 'missed']),
    },
    {
        'question': 'Which Greek city founded Syracuse?',
        'answer': 'Corinth',
        'rich_answer': 'Corinth — not Athens, not Sparta. Corinth dominated western colonization. The settlers chose the island of Ortygia for its defensible natural harbors and the freshwater spring of Arethusa.',
        'answer_type': 'name',
        'level': 1,
        'node_title': 'Syracuse: Corinth\'s Greatest Colony',
        'memory_hook': 'CORinth → CORe of Syracuse. The mother city that built the greatest Greek colony.',
        'anchors': json.dumps(['Corinth also founded other western colonies']),
        'grading_options': json.dumps(['correct', 'wrong']),
    },
    # ── Akragas ──
    {
        'question': 'What is the modern name of the Greek colony Akragas?',
        'answer': 'Agrigento',
        'rich_answer': 'Agrigento — on Sicily\'s south coast. Founded ~580 BC. Famous for its spectacular Greek temples (the Valley of the Temples still stands) and extraordinary grain wealth. Empedocles said its citizens "built as if they would live forever and feasted as if they would die tomorrow."',
        'answer_type': 'name',
        'level': 1,
        'node_title': 'Akragas, Selinunte, and the Western Colonies',
        'memory_hook': 'AKRAGAS → AGRIGENTO. The Valley of the Temples you can still visit today.',
        'anchors': json.dumps(['Founded ~580 BC', '~150 years after Syracuse']),
        'grading_options': json.dumps(['correct', 'wrong']),
    },
    {
        'question': 'When was Akragas (Agrigento) founded?',
        'answer': '~580 BC',
        'rich_answer': 'Around 580 BC. It grew fabulously wealthy from grain exports. Destroyed by Carthage in 406 BC — the crisis that brought Dionysius I to power in Syracuse.',
        'answer_type': 'date',
        'level': 1,
        'node_title': 'Akragas, Selinunte, and the Western Colonies',
        'memory_hook': '580 — halfway between colonization (734) and Himera (480). The golden middle of Greek Sicily.',
        'anchors': json.dumps(['~150 years after Syracuse (734)', '~100 years before Himera (480)', 'Destroyed by Carthage 406 BC']),
        'grading_options': json.dumps(['exact_year', 'right_decade', 'right_century', 'missed']),
    },
    # ── Battle of Himera ──
    {
        'question': 'What was the Battle of Himera?',
        'answer': 'A decisive Greek victory over Carthage in Sicily',
        'rich_answer': 'A decisive Greek victory over Carthage on Sicily\'s north coast in 480 BC. Gelon, tyrant of Syracuse, crushed a massive Carthaginian invasion. This established Syracuse as the dominant power in the western Greek world and was seen as the "western Salamis."',
        'answer_type': 'concept',
        'level': 1,
        'node_title': 'Gelon and the Battle of Himera, 480 BC',
        'memory_hook': 'HIMERA and SALAMIS — SAME YEAR, same survival. The Greek world attacked from BOTH sides at once, and won BOTH.',
        'anchors': json.dumps(['Same year as Salamis (Persian Wars)', '480 BC']),
        'grading_options': json.dumps(['correct', 'partial', 'missed']),
    },
    {
        'question': 'When was the Battle of Himera?',
        'answer': '480 BC',
        'rich_answer': '480 BC — tradition says the very same day as the Battle of Salamis in mainland Greece. The Greek world survived a coordinated two-front attack from Persia (east) and Carthage (west). Gelon used the spoils to build the Temple of Athena in Syracuse — its Doric columns still stand inside the cathedral today.',
        'answer_type': 'date',
        'level': 1,
        'node_title': 'Gelon and the Battle of Himera, 480 BC',
        'memory_hook': '480 — FOUR-EIGHTY, the year the Greek world survived TWO attacks on the SAME DAY. Salamis in the east, Himera in the west.',
        'anchors': json.dumps(['Same year as Battle of Salamis', '~250 years after colonization (734)', '~65 years before Athenian expedition (415)']),
        'grading_options': json.dumps(['exact_year', 'right_decade', 'right_century', 'missed']),
    },
    {
        'question': 'Who won the Battle of Himera?',
        'answer': 'Gelon, tyrant of Syracuse',
        'rich_answer': 'Gelon, tyrant of Syracuse. He had seized Syracuse from Gela in 485 BC. After Himera, he was the most powerful Greek ruler anywhere — and used the spoils and slave labor to transform Syracuse into a metropolis.',
        'answer_type': 'name',
        'level': 1,
        'node_title': 'Gelon and the Battle of Himera, 480 BC',
        'memory_hook': 'GELON the GIANT of Greek Sicily — crushed Carthage and built Syracuse into the greatest Greek city in the west.',
        'anchors': json.dumps(['Tyrant of Syracuse', 'Seized power 485 BC, won Himera 480 BC']),
        'grading_options': json.dumps(['correct', 'wrong']),
    },
    # ── Athenian Expedition ──
    {
        'question': 'What was the Athenian expedition to Syracuse?',
        'answer': 'Athens\' catastrophic attempt to conquer Syracuse',
        'rich_answer': 'Athens sent a massive fleet and army to conquer Syracuse in 415 BC during the Peloponnesian War. It ended in total catastrophe by 413 BC — the entire force was destroyed, ~40,000 men killed or enslaved. It marked the beginning of Athens\' decline as a great power.',
        'answer_type': 'concept',
        'level': 1,
        'node_title': 'Greeks versus Carthage: The Struggle for Sicily',
        'memory_hook': 'Athens tried to conquer Syracuse and lost EVERYTHING — 40,000 men, the entire fleet. The beginning of the end for Athens.',
        'anchors': json.dumps(['During the Peloponnesian War (Athens vs Sparta)', '415-413 BC']),
        'grading_options': json.dumps(['correct', 'partial', 'missed']),
    },
    {
        'question': 'When was the Athenian expedition to Syracuse?',
        'answer': '415-413 BC',
        'rich_answer': '415–413 BC. Athens was already at war with Sparta (Peloponnesian War) and made the catastrophic decision to open a second front in Sicily. The disaster weakened Athens so severely that Sparta eventually won the war.',
        'answer_type': 'date',
        'level': 1,
        'node_title': 'Greeks versus Carthage: The Struggle for Sicily',
        'memory_hook': '415 — about 65 years after Himera. Athens at the HEIGHT of arrogance, trying to grab Sicily while fighting Sparta. Lost everything.',
        'anchors': json.dumps(['~65 years after Himera (480)', '~10 years before Dionysius I takes power (405)', 'During the Peloponnesian War']),
        'grading_options': json.dumps(['exact_year', 'right_decade', 'right_century', 'missed']),
    },
    # ── Akragas falls / Dionysius I ──
    {
        'question': 'What happened to Akragas in 406 BC?',
        'answer': 'Destroyed by Carthage',
        'rich_answer': 'Carthage sacked and destroyed Akragas — one of the richest Greek cities in the world. The catastrophe terrified the Syracusans and directly led to Dionysius I seizing power in Syracuse the following year (405 BC).',
        'answer_type': 'concept',
        'level': 1,
        'node_title': 'Dionysius I: Empire Builder of Syracuse',
        'memory_hook': 'Akragas falls → Syracuse panics → Dionysius I grabs power. 406 → 405, one year apart. CRISIS creates TYRANNY.',
        'anchors': json.dumps(['406 BC', 'The year BEFORE Dionysius I takes power', '~75 years after Himera']),
        'grading_options': json.dumps(['correct', 'wrong']),
    },
    {
        'question': 'Who was Dionysius I?',
        'answer': 'Tyrant of Syracuse',
        'rich_answer': 'Tyrant of Syracuse (ruled 405–367 BC) — the most powerful ruler in the Greek world at that time. Rose to power after Carthage sacked Akragas. Built massive fortifications, waged four wars against Carthage, controlled most of Sicily and southern Italy. Also a playwright who desperately wanted to win at Athens\' dramatic festivals.',
        'answer_type': 'name',
        'level': 1,
        'node_title': 'Dionysius I: Empire Builder of Syracuse',
        'memory_hook': 'The tyrant-playwright who DIED CELEBRATING winning a drama prize. Ruled for 38 years and made Syracuse an empire.',
        'anchors': json.dumps(['Ruled 405-367 BC', 'Rose to power after Akragas fell to Carthage']),
        'grading_options': json.dumps(['correct', 'wrong']),
    },
    {
        'question': 'When did Dionysius I come to power in Syracuse?',
        'answer': '405 BC',
        'rich_answer': '405 BC — immediately after Carthage destroyed Akragas (406 BC). He used the crisis and Syracusan panic to seize power as tyrant. Ruled for 38 years until his death in 367 BC.',
        'answer_type': 'date',
        'level': 1,
        'node_title': 'Dionysius I: Empire Builder of Syracuse',
        'memory_hook': '405 — RIGHT AFTER Akragas fell (406). CRISIS → STRONGMAN. He then ruled until 367 — subtract 38 years from 405.',
        'anchors': json.dumps(['Right after Akragas fell (406 BC)', '~10 years after Athenian expedition', '~75 years after Himera', 'Ruled 38 years until 367 BC']),
        'grading_options': json.dumps(['exact_year', 'right_decade', 'right_century', 'missed']),
    },
    # ── Plato ──
    {
        'question': 'What connects Plato to Syracuse?',
        'answer': 'He visited three times trying to create a philosopher-king',
        'rich_answer': 'Plato visited Syracuse three times (~388, 367, 361 BC), hoping to create a philosopher-king. His first visit to Dionysius I\'s court ended badly — tradition says he was sold into slavery. His later visits to Dionysius II also failed. The experiences deeply shaped his political philosophy, including The Republic.',
        'answer_type': 'concept',
        'level': 1,
        'node_title': 'Plato\'s Syracuse: Philosophy Meets Tyranny',
        'memory_hook': 'The greatest philosopher was SOLD INTO SLAVERY by a Sicilian tyrant. Three visits, three disasters — but it gave us The Republic.',
        'anchors': json.dumps(['Visits: ~388, 367, 361 BC', 'First visit to Dionysius I, later to Dionysius II']),
        'grading_options': json.dumps(['correct', 'partial', 'missed']),
    },
    # ── Archimedes ──
    {
        'question': 'Who was Archimedes?',
        'answer': 'Syracusan mathematician and inventor',
        'rich_answer': 'Syracusan mathematician and inventor (~287–212 BC). One of the greatest scientists of antiquity. Studied in Alexandria, returned to Syracuse. Famous for principles of buoyancy, calculating pi, and the lever. Defended Syracuse against Roman siege with ingenious war machines.',
        'answer_type': 'name',
        'level': 1,
        'node_title': 'Archimedes of Syracuse',
        'memory_hook': 'ARCHIMEDES of SYRACUSE — not Athens, not Alexandria. A Syracusan who defended his city with SCIENCE.',
        'anchors': json.dumps(['~287-212 BC', 'Killed during Roman siege of Syracuse']),
        'grading_options': json.dumps(['correct', 'wrong']),
    },
    {
        'question': 'How did Archimedes die?',
        'answer': 'Killed by a Roman soldier when Syracuse fell in 212 BC',
        'rich_answer': 'Killed by a Roman soldier in 212 BC when Syracuse finally fell after a two-year siege. His war machines — catapults, giant cranes that lifted ships — had held off the Roman navy for two years. The Roman general Marcellus reportedly wanted him captured alive, but a soldier killed him anyway.',
        'answer_type': 'concept',
        'level': 1,
        'node_title': 'The Siege of Syracuse, 212 BC',
        'memory_hook': 'The GREATEST MIND killed by the DUMBEST SOLDIER. Marcellus wanted him alive — the soldier didn\'t care. 212 BC.',
        'anchors': json.dumps(['212 BC', 'Part of Second Punic War', '~30 years after Sicily became Roman province']),
        'grading_options': json.dumps(['correct', 'wrong']),
    },
    # ── Roman Sicily ──
    {
        'question': 'When did Sicily become part of the Roman world?',
        'answer': '241 BC',
        'rich_answer': '241 BC, at the end of the First Punic War (Rome vs Carthage). Sicily became Rome\'s very first overseas province — the template for how Rome would govern all its future conquests. This ended ~500 years of Greek independence on the island.',
        'answer_type': 'date',
        'level': 1,
        'node_title': 'Roman Sicily — The First Province',
        'memory_hook': '241 — Rome\'s FIRST province. The TEMPLATE for empire. 500 years of Greek Sicily, over in one war.',
        'anchors': json.dumps(['End of First Punic War', '~240 years after colonization (734)', '~30 years before Archimedes killed (212)', 'Rome\'s FIRST overseas province']),
        'grading_options': json.dumps(['exact_year', 'right_decade', 'right_century', 'missed']),
    },
    # ── Sequence checks ──
    {
        'question': 'Put in order: Battle of Himera, Greek colonization begins, Athenian expedition, Dionysius I takes power',
        'answer': 'Colonization (734) → Himera (480) → Athenian expedition (415) → Dionysius I (405)',
        'rich_answer': 'Colonization (734 BC) → Himera (480 BC) → Athenian expedition (415 BC) → Dionysius I (405 BC). Note how the last three are within 75 years of each other — the dramatic century of Greek Sicily.',
        'answer_type': 'sequence',
        'level': 1,
        'node_title': 'Greek Sicily — Magna Graecia',
        'question_type': 'temporal_ordering',
        'memory_hook': 'The Greek Sicily timeline: FOUND (734) → FIGHT Carthage (480) → Athens FAILS (415) → DIONYSIUS takes over (405)',
        'anchors': json.dumps([]),
        'grading_options': json.dumps(['all_correct', 'mostly_right', 'wrong']),
    },
    {
        'question': 'Put in order: Akragas destroyed, Archimedes killed, Sicily becomes Roman',
        'answer': 'Akragas destroyed (406) → Sicily becomes Roman (241) → Archimedes killed (212)',
        'rich_answer': 'Akragas destroyed by Carthage (406 BC) → Sicily becomes Roman province (241 BC, end of First Punic War) → Archimedes killed at siege of Syracuse (212 BC, during Second Punic War). Note: Sicily was already Roman when Archimedes was killed — Syracuse had allied with Carthage against Rome.',
        'answer_type': 'sequence',
        'level': 1,
        'node_title': 'Roman Sicily — The First Province',
        'question_type': 'temporal_ordering',
        'memory_hook': 'AKRAGAS falls (406) → long gap → ROME takes over (241) → ARCHIMEDES dies defending against Rome (212)',
        'anchors': json.dumps([]),
        'grading_options': json.dumps(['all_correct', 'mostly_right', 'wrong']),
    },
]


def node_id_for_title(conn, domain_id, title):
    """Look up node_id from title."""
    row = conn.execute(
        'SELECT id FROM curriculum_nodes WHERE domain_id = ? AND title = ?',
        (domain_id, title)
    ).fetchone()
    return row['id'] if row else ''


def main():
    init_db()
    conn = get_connection()

    # Delete old v1 questions for Greek Sicily nodes
    # (keep ordering questions and non-Greek questions)
    greek_node_titles = set(q['node_title'] for q in QUESTIONS)
    for title in greek_node_titles:
        node_id = node_id_for_title(conn, DOMAIN, title)
        if node_id:
            deleted = conn.execute(
                'DELETE FROM retrieval_questions WHERE domain_id = ? AND node_id = ?',
                (DOMAIN, node_id)
            ).rowcount
            if deleted:
                print(f'  Deleted {deleted} old questions for {title[:40]}')

    # Insert new v2 questions
    inserted = 0
    for q in QUESTIONS:
        q_id = hashlib.md5(q['question'].encode()).hexdigest()[:12]
        node_id = node_id_for_title(conn, DOMAIN, q['node_title'])
        question_type = q.get('question_type', q['answer_type'])

        conn.execute('''
            INSERT OR REPLACE INTO retrieval_questions
            (id, domain_id, node_id, question, answer, question_type, node_title,
             answer_type, level, anchors, memory_hook, grading_options, rich_answer,
             generated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
        ''', (
            q_id, DOMAIN, node_id, q['question'], q['answer'],
            question_type, q['node_title'],
            q['answer_type'], q['level'], q.get('anchors', '[]'),
            q.get('memory_hook'), q.get('grading_options', '[]'),
            q.get('rich_answer', q['answer']),
        ))
        inserted += 1
        print(f'  [{q["answer_type"]:8}] {q["question"][:60]}')

    conn.commit()
    conn.close()
    print(f'\nInserted {inserted} v2 questions for Greek Sicily')


if __name__ == '__main__':
    main()

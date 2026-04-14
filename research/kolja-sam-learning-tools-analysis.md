# Kolja Sam's Learning Tool Research — Analysis for Petrarca

**Date:** 2026-04-10
**Source:** https://koljasam.com/, https://zk.koljasam.com/, https://github.com/koljapluemer
**Purpose:** Extract actionable insights from an independent learning tool builder's research and projects

---

## Who is Kolja Sam?

Berlin-based developer/designer with 197 GitHub repos, mission statement: "make the world a better place by building excellent tools for learning." Primarily works in TypeScript/Vue. No visible academic affiliation — this is practitioner research, not academic. His digital garden (zk.koljasam.com) is a zettelkasten of ~200+ notes on learning science, drawing from CLT, ZPD, ACT-R, SLA research, and game design literature.

Key projects:
- **karten** — SRS with "interdependent flashcards" (cards aware of each other, can create compound exercises)
- **The Queue** — Obsidian plugin for serendipitous note resurfacing via FSRS scheduling
- **know-every-year** — FSRS + Major System mnemonics for history dates (archived — stalled)
- **learn-worldmap** — Geography SRS with progressive precision (continent → country → border)
- **Angry Luhmann** — Obsidian plugin enforcing hierarchical zettelkasten structure
- **zk** — Digital garden on learning tool design (the richest resource)

---

## Insights Relevant to Petrarca

### 1. Learning Bugs vs. Fatigue Lapses

**The problem:** SR systems treat all failures identically. But a "fatigue lapse" (knew it, just tired/distracted) and a "learning bug" (systematic misconception) require fundamentally different interventions.

**What makes it a learning bug:** It's *predictable* — you can anticipate which wrong answer the student will give. A fatigue lapse is random; a learning bug is systematic (e.g., consistently confusing Himera with Marathon, or believing Gelon came after Dionysius).

**Current Petrarca state:** FSRS grading (knew/partly/missed) doesn't distinguish these. The `confidence_tagged` mechanism from voice elicitation (session 61) is a step — it flags wrong facts — but treats them as one-off corrections, not patterns.

**Actionable idea:** Mine voice elicitation transcripts for *repeated* wrong associations across sessions. If someone consistently places the Battle of Himera in the wrong century, or confuses two similar entities, that's a learning bug that needs targeted intervention (perhaps a specific microlearning card addressing the confusion directly), not just another FSRS cycle. Could track `(entity_a, entity_b, confusion_count)` tuples.

**Kolja's framing:** "A testable hypothesis: you correctly predict the student's (wrong) answer." If Petrarca could predict confusion patterns, it could preemptively address them.

### 2. SR Optimizes Prediction Accuracy, Not Learning

**The argument:** FSRS/SuperMemo algorithms are incentivized to *predict* whether you'll remember something, not to *maximize* your actual retention. The metric is retrievability prediction accuracy, not learning outcomes. A system could perfectly predict your retrieval patterns while doing nothing to improve them.

**Why Petrarca partially escapes this trap:** The FSRS scheduling (`desired_retention=0.80`) handles timing, but the *content* of review cards (elaborative questions, temporal hooks, memory hooks, cross-source synthesis, voice elicitation) is doing the real pedagogical work. The scheduling algorithm matters less when the retrieval event itself is rich and elaborative rather than a simple flashcard flip.

**Still worth monitoring:** Are there nodes where FSRS stability is high (algorithm says "you know this") but voice elicitation reveals the knowledge is shallow? That gap between predicted retention and actual understanding is exactly the metric misalignment Kolja identifies. The knowledge_transitions table could track cases where FSRS-confident items get "missed" in voice recall.

### 3. Overlearn Then Refresh (vs. Continuous SR)

**The argument:** Instead of continuous drip-feed review, some evidence (cited from Area9 Lyceum / LearnTec 2025) suggests: intensively overlearn material initially, then use periodic refreshers.

**How this maps to Petrarca:** When you read a Sicily book, you're doing intensive encoding — the book provides narrative structure, emotional engagement, temporal hooks. The system then provides refreshers through review cards. But Petrarca doesn't currently distinguish between "initial intensive encoding phase" and "long-term maintenance phase."

**Actionable idea:** A freshly-sourced node (just mapped from a chapter read) might benefit from a short burst of massed practice (2-3 encounters in the first week) before switching to expanded spacing. FSRS `learning_steps=()` is currently empty (disabled). Re-evaluating this for newly-sourced nodes specifically could improve initial encoding without the burden of continuous massed practice for all items.

**Counterpoint:** Petrarca's design philosophy says "books encode, system maintains" — the book already provides the massed initial encoding. But voice elicitation data (session 63: 32.5% spontaneous recall) suggests the book encoding isn't always sufficient. A brief "encoding boost" phase for weak initial recall could help.

### 4. Confidence Trajectories, Not Just Pass/Fail

**The argument:** Rather than binary correct/incorrect (or even Petrarca's 3-level knew/partly/missed), track user *confidence* on a scale. A confidently-wrong answer and a hesitantly-correct answer are fundamentally different knowledge states that should schedule differently.

**Current Petrarca state:** Voice elicitation captures confidence signals implicitly (hedging language, "I think...", corrections mid-sentence), and `confidence_tagged` flags wrong facts. But this data isn't fed back into scheduling.

**Actionable idea:** Track confidence trajectory per-node across review sessions. A node where confidence is *increasing* each session (even if still partly-known) is a developing skill that needs different treatment than one that's flat or declining. This connects to Kolja's note on "dynamic assessment" — tracking emerging abilities, not just established ones.

### 5. Serendipitous Resurfacing of Own Knowledge

**Source:** The Queue (Obsidian plugin) randomly surfaces notes you've written.

**The gap in Petrarca:** The feed surfaces *new articles* with novelty detection, and the review system surfaces *scheduled items*. But there's no mechanism for serendipitously resurfacing the user's *own* knowledge — voice transcripts, past quiz answers, past wonderings, past voice dumps.

**Actionable idea:** Periodically surface "you said this 3 weeks ago about the Battle of Himera" or "your voice recall on Roman architecture from March 28." Not as review items (no grading), but as knowledge reinforcement through re-encounter with your own articulation. The microlearning `voice_wondering` cards are a start, but surfacing past *correct* knowledge (not just gaps) strengthens the network.

**Connection to design principle:** This aligns with "I'll manage your memory" (principle #2) — showing users their knowledge is accumulating and being maintained, reducing the fear of forgetting.

### 6. Interdependent Cards / Prerequisite Detection

**Source:** karten project (interdependent flashcards), zk notes on production rules and prerequisite mastery.

**The concept:** Cards that are aware of each other. When you fail "Why did the Athenian expedition fail?", the system can detect whether the gap is in prerequisite facts (who led it, when it happened, what was the political context) vs. analytical understanding. Two leeching cards on related topics can generate a compound exercise ("make a sentence connecting Alcibiades and the Sicilian Expedition").

**Current Petrarca state:** Curriculum nodes have implicit dependencies through the graph structure, and nexus cards (session 54, currently disabled) were designed to surface cross-node connections. But there's no explicit prerequisite tracking — the system doesn't know that understanding Dionysius I requires understanding the fall of Akragas.

**Long-term relevance:** As the curriculum grows beyond history into music, literature, philosophy (session 64), cross-domain prerequisites become important. Understanding Renaissance architecture requires some knowledge of Roman architecture; understanding Monteverdi requires understanding of the Florentine Camerata. The curriculum graph could encode these dependencies, and review scheduling could enforce prerequisite mastery before advancing.

### 7. "Stealth Learning Doesn't Work"

**The argument:** Games that hide the learning intent perform worse than those that are honest about being educational. Metacognitive engagement (knowing you're learning) is a prerequisite for transfer.

**Validation for Petrarca:** The system is explicitly a knowledge management tool — knowledge maps, growth metrics, review schedules, decay tracking are all visible. This is the right approach. Gamifying away the learning intent (progress bars, streaks, badges) would actually reduce effectiveness. The statistics dashboard, knowledge atlas, and growth visualization serve double duty: they're useful *and* they reinforce metacognitive awareness.

---

## Insights from Failed Projects

### know-every-year (history dates via Major System)
Used FSRS + mnemonic pegs to memorize what happened each year from 0-2025. Technically worked but creator lost motivation. The failure validates Petrarca's principle #1 ("hooks, not facts") — pure date memorization without narrative context isn't motivating. Dates need to be scaffolding for stories, not endpoints.

### AI-based learning material generator
Failed because it "lacked a coherent usage flow" — generated exercises with no context for when/why to use them. This is the CRM trap: building a database of learning materials without a reading/learning loop to drive engagement. Petrarca avoids this by anchoring everything to the reading pipeline (articles → claims → curricula → review → voice recall).

---

## What Petrarca Already Does Better

Several of Kolja's insights are things Petrarca has already implemented, often more deeply:

| Kolja's Insight | Petrarca's Implementation |
|----------------|--------------------------|
| SRS fails for conceptual knowledge | Elaborative retrieval, temporal hooks, memory hooks (not flashcards) |
| Free recall > cued recall | Voice elicitation (open-ended, no prompts) |
| Prerequisite mastery matters | Curriculum nodes with knowledge levels (unknown→anchored) |
| Spacing through natural re-encounters | Cross-article novelty detection, claim-level tracking |
| Output > input for deep processing | Voice recall, voice wondering, voice corrections |
| Elaborative interrogation for complex facts | Follow-up queries, "also want to know" chips, related_facts checklists |
| Books as superstructure for content | "Books encode, system maintains" (principle #8) |

---

## Actionable Summary

**High priority (addresses known gaps):**
1. **Learning bug detection** — mine voice transcripts for systematic confusion patterns, not just one-off errors
2. **Confidence trajectory tracking** — per-node confidence trend across sessions, feed into scheduling
3. **Serendipitous self-knowledge resurfacing** — surface past voice articulations as positive reinforcement

**Medium priority (worth experimenting):**
4. **Encoding boost phase** — short massed practice burst for freshly-sourced nodes (re-evaluate `learning_steps`)
5. **FSRS vs. actual understanding gap** — compare FSRS-predicted stability with voice elicitation recall rates

**Low priority (long-term architecture):**
6. **Prerequisite graph** — explicit dependency edges in curriculum, enforce mastery ordering
7. **Compound review exercises** — cross-node synthesis prompts (related to disabled nexus cards)

---

## Resources

- Digital garden: https://zk.koljasam.com/
- Blog: https://cards.koljasam.com/
- GitHub: https://github.com/koljapluemer (197 repos)
- Key project: https://github.com/koljapluemer/obsidian-the-queue (44 stars, FSRS-based Obsidian plugin)
- Key project: https://github.com/koljapluemer/karten (interdependent flashcards SRS)
- Lectures curation: https://lectures.koljasam.com/

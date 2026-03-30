# Retrieval Question Design — Principles from Calibration

*2026-03-30. Distilled from hands-on evaluation of 20 format experiments.*

---

## Core Principles

### 1. One fact per card. Always.

Never combine "when" + "why" or "who" + "what they did" in one question. Every question tests exactly one retrievable fact. If there are two things worth knowing, make two cards.

Bad: "When was the Battle of Himera, and why was it historically significant?"
Good: Card 1: "When was the Battle of Himera?" Card 2: "Why was Himera significant for Greek Sicily?"

### 2. A question is really two questions: name↔concept

"When was the Battle of Himera?" actually tests two things:
- Can you connect the *name* "Himera" to the *concept* (battle between Syracuse and Carthage)?
- Can you connect the *concept* to the *date* (480 BC)?

These should be separate cards that can be tested independently:
- "What was the name of the major battle between Syracuse and Carthage around 480 BC?" → Himera
- "When was the Battle of Himera?" → 480 BC

### 3. Graded date answers, not binary

For date questions, don't ask correct/wrong. Ask:
- **Exact year** (480 BC) — full credit
- **Right decade** (480s BC) — strong partial
- **Right century** (5th century BC) — weak partial
- **Missed** — no credit

Even "right century" means something was retained. This gives much richer signal about knowledge decay than binary.

### 4. Rich answers, not bare facts

The answer card should restate the full context, not just the bare answer:

Bad answer: "480 BC"
Good answer: "The Battle of Himera — where Gelon of Syracuse defeated a Carthaginian invasion — happened in 480 BC, the same year as the Battle of Salamis in mainland Greece."

The answer card IS a micro-learning moment. Make it reinforce the full picture.

### 5. Temporal anchors everywhere

Bare dates are hard to remember and hard to place. Always provide relative anchors:

- "Same year as Salamis (Persian Wars)"
- "Right after Carthage destroyed Akragas (406 BC)"
- "About 250 years after Greek colonization began"
- "30 years before Alexander the Great"

These anchors ARE the timeline scaffold. Over time, the dates anchor to each other, not to abstract numbers.

### 6. No "list N things" format

"Name 3 things about Dionysius I" fails because:
- Hard to self-grade (is "he was powerful" a valid thing?)
- Feels bad when you get 2/4
- Doesn't target specific knowledge gaps

Instead, make each "thing" a specific prompted question:
- "How did Dionysius I rise to power?"
- "What was Syracuse's relationship with Carthage under Dionysius I?"
- "Which Sicilian ruler was also a playwright?"
- "When did Plato visit Syracuse, and who was ruler?"

### 7. No open "what happened?" questions

"What happened after Carthage destroyed Akragas?" is too broad — there could be many consequences. Be specific:

Bad: "What happened after Akragas fell?"
Good: "Who seized power in Syracuse after Akragas fell to Carthage?"

The more specific the prompt, the clearer the retrieval target, the easier to self-grade.

### 8. Prerequisites must be satisfied

Don't ask "When was the Sicilian Vespers?" before the user knows what the Vespers was. Don't ask about Dionysius I's reign dates before establishing Akragas.

Questions have an implicit dependency chain:
1. Know what the thing IS (identity/concept level)
2. Know WHEN it happened (date level)
3. Know HOW it unfolded (narrative level)
4. Know WHY it mattered (significance level)

The system should track which level the user has reached per node and only ask questions at or one step above that level.

### 9. Formats that WORK

Rated "great" by the user:

- **Exact date with anchors**: "When was X?" with temporal context in the answer
- **Century-level**: "Roughly when did X happen?" for less critical events
- **Date + context**: "When did Rome take Sicily, and what war was it part of?"
- **Sequence ordering**: "Put in order: A, B, C" with 3-4 events
- **"What's the connection?"**: "What connects Plato and Syracuse?" — OK when well-scoped

### 10. Formats that DON'T work

- **Compound questions**: Anything with "and" joining two different concepts
- **"List N things"**: Too open, too hard to grade, feels bad
- **"What happened because of X?"**: Too broad, multiple valid answers
- **"Describe the significance"**: Essay-length, impossible to self-grade binary
- **Reign brackets as one question**: "When did X rule?" is really two dates — break it up or accept "started right after Y" as sufficient

---

## Question Levels

### Level 1: Identity + Timeline (the skeleton)

These are the load-bearing facts. If you know these, everything else has hooks to attach to.

**Types:**
- Name ↔ concept: "What was the name of the battle between Syracuse and Carthage in 480 BC?"
- Date of key event: "When was the Battle of Himera?"
- Who was X: "Who was Gelon?" → "Tyrant of Syracuse"
- Sequence: "Put in order: Himera, Athenian expedition, Dionysius I"

**Grading:** Exact year / decade / century / missed (for dates). Correct / wrong (for names/identities).

### Level 2: Connections + Causes (the tissue)

These connect the skeleton into a narrative. Only ask after Level 1 is solid.

**Types:**
- What caused X: "What crisis led to Dionysius I seizing power?" → Carthage sacking Akragas
- What's the connection: "What connects Plato and Syracuse?"
- Who did what in context: "Which Sicilian ruler wrote drama?"
- Specific consequence: "Who seized power after Akragas fell?"

**Grading:** Correct concept / vague but right direction / missed.

### Level 3: Significance + Analysis (the meaning)

Only ask when Level 1-2 are solid for this node.

**Types:**
- Why did X matter: "Why was Himera significant?" (any valid reason counts)
- Compare: "How did Sicilian tyranny differ from mainland Greek tyranny?"
- Pattern: "Why did Sicily keep getting conquered?"

**Grading:** Any substantive answer / too vague / missed.

---

## Technical Implications

### Question data model

```
RetrievalQuestion:
  id: str
  domain_id: str
  node_id: str
  question: str
  answer: str                    # Rich, full-context answer
  answer_type: 'date' | 'name' | 'concept' | 'sequence' | 'connection'
  level: 1 | 2 | 3
  anchors: str[]                 # Temporal/conceptual anchors shown with answer
  prerequisite_questions: str[]  # Question IDs that should be mastered first
  grading_options:               # Specific to answer_type
    - for date: ['exact_year', 'right_decade', 'right_century', 'missed']
    - for name: ['correct', 'wrong']
    - for concept: ['correct', 'partial', 'missed']
    - for sequence: ['all_correct', 'mostly_right', 'wrong']
```

### Grading feeds back differently per type

- Date exact year → high confidence, long interval
- Date right decade → moderate confidence, medium interval
- Date right century → low confidence, short interval (knows something, needs reinforcement)
- Date missed → zero confidence, shortest interval

This is much richer signal than binary correct/wrong.

---

## The Alif Principle: Forgetting Means You Need Richer Hooks

When you forget something, the response should NOT be "show it again sooner." The response should be: **enrich the hooks around it.**

This is exactly what Alif does for vocabulary. When you forget a word, Alif adds:
- Etymology (where the word comes from — connects to other words you know)
- Memory hooks (vivid, sometimes ridiculous mnemonics)
- Usage in sentences you've seen (contextual association)
- Root family connections (learning one root gives you 7-23 related words)

For historical knowledge, the same principle applies:

### What "richer hooks" means for history

When you can't remember when Himera was:
- **Temporal anchor**: "Same year as Salamis — 480 BC. The Greek world survived a two-front attack."
- **Vivid detail**: "Gelon used the captured slaves to build the Temple of Athena in Syracuse — its columns still stand inside the cathedral today."
- **Connection to something you know**: "About 250 years after Syracuse was founded."
- **Narrative hook**: "Tradition says Himera and Salamis happened on the very same day."
- **Sensory/spatial**: "Himera was on Sicily's north coast — the Carthaginians came from just across the water."

When you can't remember who Dionysius I was:
- **How he rose to power**: "After Carthage sacked Akragas in 406 BC, the terrified Syracusans turned to a strongman"
- **Vivid detail**: "He was also a playwright who desperately wanted to win at Athens' dramatic festivals — and when he finally did, he reportedly died of the celebratory drinking"
- **Connection**: "Plato visited his court and was so horrified that the experience shaped the Republic"

### The answer card as enrichment opportunity

The answer card shouldn't just confirm "480 BC." It should be a **micro-article** — 3-5 sentences that provide multiple hooks:

```
The Battle of Himera (480 BC)

Gelon, tyrant of Syracuse, crushed a massive Carthaginian invasion
on Sicily's north coast. Tradition says it happened the very same
day as the Battle of Salamis — the Greek world survived a coordinated
two-front attack from Persia and Carthage simultaneously.

Gelon used the spoils and captured slaves to build Syracuse into a
metropolis, including the great Temple of Athena on Ortygia — its
Doric columns still stand inside Syracuse's cathedral today.
```

### When the user gets it wrong: generate more hooks

This is the key behavioral loop:

```
User answers "missed" or "right century"
  → System flags this question for hook enrichment
  → Next review: show the enriched answer card with MORE context
  → If still failing: generate a "deep dive" micro-article
     (2-3 paragraphs, AI-generated, focused on this specific fact)
  → Offer: "Read more about this?" → links to curriculum node detail
  → Offer: "Generate article?" → creates a focused piece for the reading queue
```

This is the Alif loop applied to history:
1. Simple question → simple answer
2. If forgotten → enriched answer with hooks
3. If still forgotten → full micro-article with narrative, vivid details, connections
4. If STILL forgotten → maybe the prerequisite hooks aren't there and we need to go back a level

### AI prompts on answer cards

When showing an answer card, offer 1-2 tappable prompts that would generate deeper content:

- "Tell me the story of the Battle of Himera" → generates a 500-word narrative
- "What was happening in the rest of the Greek world in 480 BC?" → generates a cross-reference piece
- "Show me Himera on a map and explain the geography" → generates a spatial context piece

These go into an "incoming reading" queue — short, focused pieces generated on demand when curiosity is triggered by a review session. The review session becomes a DISCOVERY mechanism, not just a testing mechanism.

---

---

## The Hamarquizen Pattern: PRIME → READ → TEST → HOOK

Hamarquizen (built for an 11-year-old learning Hamar history) proved this loop works:

1. **Pre-question (PRIME)**: Low-stakes curiosity trigger before reading. "What do you think happened when Carthage invaded Sicily?" — it's OK to guess wrong. The pretesting effect (Bjork: 95% failure rate still enhanced learning) means even wrong guesses prime the brain.

2. **Micro-story (READ)**: 2-3 vivid paragraphs on ONE topic. Not a textbook — a narrative with sensory details, surprising facts, human moments. Expandable inline terms for context.

3. **Minnekrok (MEMORY HOOK)**: A vivid, sometimes ridiculous mnemonic. "BREAK-SPEAR — imagine a man BREAKING A SPEAR against the cathedral wall. Breakspear founded the bishopric." For Sicily: "Dionysius I — the tyrant who died from PARTYING TOO HARD after winning a drama prize."

4. **Check question (TEST)**: Retrieval practice immediately after reading. Wrong answers get rich context explaining WHY the right answer is right.

5. **Spaced review**: SM-2 scheduling. Wrong answers come back sooner. Mastered items disappear until due.

### Applying to Petrarca

The review card in Petrarca should evolve toward this:

**When showing a question for the first time** (never reviewed):
- Show question
- After answer: show the rich answer card (micro-article format)
- Show memory hook if one exists
- Offer "Read more" → links to curriculum node detail or generates micro-article

**When reviewing a known question** (previously correct):
- Show question
- After answer: brief answer only (you've seen the full version before)
- If wrong this time: re-show the full rich answer + hooks

**When a question keeps failing**:
- Enrich the hooks (add more anchors, vivid details, connections)
- Generate a "deep dive" micro-article
- Offer to add it to reading queue
- Consider: maybe the prerequisite isn't solid — check parent questions

### Memory hook examples for Sicily

Each major curriculum node should have a handcrafted (or AI-generated) memory hook:

| Topic | Hook |
|-------|------|
| Himera 480 BC | "SAME DAY as Salamis — the Greek world attacked from BOTH sides at once" |
| Dionysius I | "The tyrant-playwright who DIED CELEBRATING winning a drama prize" |
| Archimedes | "His columns STILL STAND inside Syracuse cathedral — you can visit them TODAY" |
| Plato at Syracuse | "The greatest philosopher was SOLD INTO SLAVERY by a Sicilian tyrant" |
| Sicilian Vespers 1282 | "A French soldier insulted a woman at EVENING PRAYERS — every French person on the island was killed" |
| Roger II crowned 1130 | "CHRISTMAS DAY — he got a kingdom for Christmas" |

These hooks are the high-value creative content. They can be:
- Handcrafted (highest quality, most effort)
- AI-generated with human review (good quality, scalable)
- Crowd-sourced from the user's own voice notes ("why did this strike you?")

---

### Generation approach

Don't generate questions in one big batch. Generate per curriculum node, level by level:

1. For each node, generate 2-3 Level 1 questions (identity, date, one key fact)
2. Link them with prerequisites (date question requires identity question)
3. Only generate Level 2 questions for nodes where Level 1 is mastered
4. Only generate Level 3 for nodes where Level 2 is mastered

This means the question set GROWS as the user learns. Starting from ~2 questions per node (identity + date) → expanding to 4-6 as mastery develops.

### The review session picks questions at the right level

```
For each node with questions:
  Check: what's the highest level the user has mastered?
  Pick questions at that level + one level above
  Don't pick questions below mastered level (waste of time)
  Don't pick questions two+ levels above (prerequisites not met)
```

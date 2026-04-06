# Deep Analysis: Voice Elicitation Data & Knowledge Utilization

**Date**: 2026-04-06  
**Status**: Analysis complete, proposals ready for prioritization

## The Core Problem

Voice elicitation generates the richest, most personal knowledge data in the entire system — the user's actual words, their connections, their uncertainties, what stuck and what didn't. But almost none of this data flows back into the system's prompts or decisions. The transcript is stored and forgotten. The system treats voice elicitation as a one-shot grading event rather than a continuous knowledge accumulation mechanism.

---

## 1. Current State: What's Captured vs. What's Used

### Data generated per voice elicitation

| Field | Stored where | Used later? |
|-------|-------------|-------------|
| `transcript` (full text) | `voice_transcripts.transcript` | **NEVER** — only for dedup by audio_bytes |
| `captured` (facts recalled) | `voice_transcripts.llm_result` | Statistics dashboard only |
| `missed` (key omissions) | `voice_transcripts.llm_result` | Triggers 1 ML card for biggest gap |
| `interesting` (beyond sources) | `voice_transcripts.llm_result` | **NEVER** read from DB |
| `wonderings` (questions asked) | `review_items` + `microlearning_cards` | **YES** — drives ML card generation |
| `research_questions` | `microlearning_cards` | **YES** — drives ML card generation |
| `coverage_pct` | scoring logic | Used once to set knowledge level |
| `suggested_score` | `knowledge_items.last_score` | Drives SRS scheduling |
| `feedback_summary` | `voice_transcripts.llm_result` | Displayed once, never re-read |

**Bottom line**: Only `wonderings`, `research_questions`, and `suggested_score` have downstream effects. The transcript itself — the richest data — is write-only.

### What review card generation knows about the user

When generating a review question about, say, "Aristotle and the Lyceum", the LLM receives:

- Node title + description (from curriculum)
- Source text from books (first 400 chars)
- Other nodes the user knows in the same domain (up to 3)
- Cross-curriculum connections (contemporaneous events the user knows)
- Temporal hooks
- Key facts the user got right previously

What it does **NOT** receive:

- What the user actually said during voice elicitation about Aristotle
- That they found the Alexander-Aristotle relationship interesting
- That they wondered about Stagira being destroyed
- That they connected Aristotle to the Macedonian political context
- Their misconceptions (e.g., "his father was a tutor to Philip")
- Their confidence levels on different sub-topics
- Any of their voice notes about related topics

The LLM is essentially blind to the user's actual knowledge state beyond a single score (knew/partly/missed) and a coverage percentage.

---

## 2. Two Modes of Elicitation

Voice elicitation serves fundamentally different purposes depending on temporal distance:

### Distant recall (Byzantium, 1814, Henry VIII, Karl XII)
- Topics studied through multiple sources over time
- Reveals **what matters to the learner**: which facts stuck, which connections they built naturally, what framework they use
- The "interesting" field is gold here — it shows original thinking and cross-domain connections
- Less about gaps to fill, more about **personal salience mapping**
- Example: Stian remembering that Aristotle tried to make Alexander "less bellicose" — this is a connection he found personally meaningful, not something in the curriculum definition

### Fresh recall (chapter just read, podcast just heard)
- Recent encoding, rich in specific facts
- Without active processing, only gists survive: "Sicily was part of Ancient Greece from Homer to 200s"
- The specific names, sequences, dates will be lost: when was Hiero I, when was Archimedes
- This is **retention prevention** — the system's primary anti-forgetting function
- The `missed` field directly identifies what needs reinforcement

**Implication**: The system should tag elicitations by mode (the UI already distinguishes chapter_recall vs. curriculum recall) and weight the data differently in downstream use.

---

## 3. The "Digital Twin" Gap

The user's aspiration: voice elicitation data should build toward a "limited digital twin of my brain." Current reality:

### What a digital twin would know
- "Stian finds the relationship between Aristotle and Alexander fascinating"
- "Stian consistently connects Macedonian politics to the intellectual life of Athens"
- "Stian confuses the chronology of Hiero I and Archimedes"
- "Stian has strong knowledge of Arab Sicily but weak on Norman succession"
- "When thinking about Aristotle, Stian naturally reaches for French neoclassical drama connections"
- "Stian's mental model of Byzantine history is organized around Constantinople as a city, not around emperors"

### What the system currently knows
- knowledge_state: "engaged" (confidence: 0.45)
- last_score: "partly"
- review_count: 3

That's the entire user model for a topic. The rich signal from hours of voice elicitation is reduced to two numbers.

---

## 4. Concrete Proposals

### Proposal A: Learner Knowledge Profile per Node

**What**: After each voice elicitation, compile a structured "learner knowledge profile" for that node and store it in a new `learner_profiles` table (or a JSON column on `knowledge_items`).

**Schema**:
```
node_id, domain_id
-- Aggregated across all elicitations for this node:
facts_known: ["Aristotle was student of Plato", "Tutored Alexander", ...]
facts_missed: ["Invented formal logic", "Ethics and politics writings"]  
misconceptions: ["Father was tutor to Philip" (actually physician to Amyntas III)]
connections_made: ["Alexander-Aristotle personal relationship", "Macedonian politics → Athenian intellectual life"]
interests: ["Alexander-Aristotle dynamic", "French neoclassical drama reception"]
uncertainties: ["Chronology of return to Athens", "What exactly he taught Alexander"]
organizing_framework: "Biographical arc + political context"  
last_updated: timestamp
```

**How it's built**: After each elicitation, an LLM call merges the new transcript data with any existing profile. This is an append/merge operation, not a replacement — knowledge accumulates.

**How it's used**: Injected into review question prompts, microlearning prompts, and follow-up generation. The LLM knows what the user finds interesting, what they're confused about, and what framework they use — so it can ask better questions.

**Cost**: One additional LLM call per elicitation (could use Gemini Flash). Storage is minimal. The profile would be ~200-500 tokens per node.

### Proposal B: Cross-Topic Knowledge Retrieval (RAG-like)

**What**: When generating content about a topic, retrieve relevant snippets from ALL the user's voice data — not just the current node.

**Example**: When generating a review card about "The Lyceum", pull in:
- What the user said about Plato (since Aristotle was his student)
- What they said about Alexander (since Aristotle tutored him)
- What they said about Athens (since the Lyceum was there)
- What they said about Arab transmission of Aristotle (from Islamic civilization curriculum)

**Implementation**: Use limbic.amygdala embeddings on transcript chunks. At review generation time, embed the node description, find the top-k most relevant transcript passages, and include them as "what the learner has said about related topics."

**Storage**: Embed transcript chunks (paragraph-level) and store in a `transcript_embeddings` table. Use the existing limbic infrastructure.

**Cost**: Embedding cost is one-time per transcript. Retrieval is fast (SQLite + cosine similarity). Adds ~500-1000 tokens to review prompts.

### Proposal C: Entity-Level Knowledge Aggregation

**What**: For each entity (person, place, event) mentioned across all voice data, build an aggregated "what the user knows/thinks about X."

**Example for "Alexander the Great"**:
- From Aristotle elicitation: "Tutored by Aristotle, sent specimens back, destroyed Stagira"
- From Sicily elicitation: "Part of the Hellenistic world after Alexander"
- From Persian Empire elicitation: (future) "Defeated Darius, spread Greek culture east"

**Implementation**: Entity recognition on transcripts (already done partially in voice capture pipeline — session 52). Aggregate per entity. Store as JSON.

**Use**: When any review card mentions Alexander, include "what the learner has said about Alexander across all topics." This creates the cross-domain connections naturally.

### Proposal D: Enriched Prompts with Transcript Context

**What**: The simplest possible improvement — when generating a review question for node X, include a summary of the user's most recent elicitation transcript for that node.

**Implementation**: In `generate_question()`, query `voice_transcripts` for the most recent transcript with `node_id = X`, take the LLM-generated `feedback_summary` + `captured` + `missed`, and append it to the prompt as:

```
LEARNER CONTEXT: In a recent voice recall, the learner demonstrated:
- Known: {captured items}
- Gaps: {missed items}  
- Interesting connections: {interesting items}
- Open questions: {wonderings}
```

**Cost**: Zero new LLM calls. Just a DB query + string formatting. Adds ~300-500 tokens.

**Impact**: The review question can now target known gaps, build on connections the learner already made, and avoid re-testing what they clearly know.

### Proposal E: Compile Voice Data into "Learner Summary" Documents

**What**: Periodically (or on-demand), compile ALL voice data for a domain into a single "learner knowledge summary" — a document that represents what the user knows, thinks, and cares about in that domain.

**Implementation**: Take all transcripts for a domain, all captured/missed/interesting data, and ask an LLM to synthesize a 1-2 page "knowledge portrait." Store as a document.

**Use**: This becomes the primary context for all content generation in that domain. Instead of passing raw node descriptions, pass "here's what this specific learner knows and cares about in Ancient Greece."

**Cost**: One Opus call per domain, run periodically (e.g., after every 3 new elicitations).

---

## 5. Priority Ranking

| Proposal | Impact | Effort | Recommendation |
|----------|--------|--------|----------------|
| **D: Enriched prompts** | Medium | Very low | **Do first** — immediate improvement, zero new infrastructure |
| **A: Learner profiles** | High | Medium | **Do second** — structured accumulation enables everything else |
| **B: Cross-topic RAG** | Very high | Medium | **Do third** — requires embeddings but limbic is already set up |
| **C: Entity aggregation** | High | Medium | Can build on B's embedding infrastructure |
| **E: Domain summaries** | Very high | Low (once A/B exist) | Natural capstone — the actual "digital twin" |

### Recommended implementation order

1. **Proposal D** (1 session): Inject existing `captured`/`missed`/`interesting`/`wonderings` from `voice_transcripts.llm_result` into `generate_question()` and `MICROLEARNING_PROMPT`. Pure win with no new infrastructure.

2. **Proposal A** (1-2 sessions): Build the learner profile system. After each elicitation, merge new data into a structured profile. This becomes the canonical "what does the user know about X."

3. **Proposal B** (1-2 sessions): Embed transcript chunks with limbic. At review time, retrieve relevant cross-topic passages. This is what makes the system "think in connections" the way the user does.

4. **Proposals C + E** emerge naturally from A + B.

---

## 6. Prompt Token Budget Analysis

Current prompts use roughly 3,000-6,000 tokens of context. Claude Opus and Sonnet can handle 200K+ tokens. Gemini Flash handles 1M. We're using **~3%** of available context.

Even adding:
- Learner profile for current node (~300 tokens)
- Top-5 relevant transcript passages (~500 tokens)
- Cross-domain entity knowledge (~300 tokens)
- Recent elicitation summary (~200 tokens)

...we'd still be at ~8,000 tokens total — well within budget. The limiting factor is not token space but **retrieval quality** — what to include matters more than how much we can include.

---

## 7. The Elicitation Prompt Itself

The current `VOICE_ELICITATION_PROMPT` is well-designed but could be enhanced:

### Current strengths
- Explicitly asks for "interesting" (beyond-sources observations)
- Captures "wonderings" as research questions
- Distinguishes captured vs. missed vs. interesting

### Suggested additions
- **Confidence tagging**: Ask the LLM to tag each captured fact with the user's apparent confidence (certain / hedging / guessing). The user's phrasing ("I'm pretty sure" vs "I wonder if") carries signal.
- **Framework detection**: Ask "what organizing principle does the learner use to think about this topic?" (chronological, biographical, geographic, thematic). This shapes how review cards should be framed.
- **Connection type**: For each "interesting" item, classify: temporal connection, causal reasoning, cross-domain link, personal interpretation, methodological insight.
- **Emotional markers**: What topics did the user show enthusiasm about? ("I think I've read part of that" = casual, vs. "it became extremely important for French theory" = engaged). This feeds salience scoring.

---

## 8. Open Questions

1. **When should learner profiles be regenerated?** After every elicitation, or batched? Incremental merge vs. full recompile?

2. **Should the system distinguish between "I knew this from before Petrarca" vs. "I learned this through the app"?** Distant recall of pre-existing knowledge is different from demonstrating retention of app-presented material.

3. **Privacy/comfort**: The "digital twin" idea means storing detailed models of what the user thinks and believes. For a single-user app this is fine, but the design should assume the user might want to see/edit their profile.

4. **Feedback loops**: If the system knows the user finds X interesting, should it surface more X-related content? This creates a filter bubble risk. Counter: the curriculum structure already provides breadth; the personalization only affects *how* content is presented, not *what* content is shown.

5. **Voice notes vs. voice elicitation**: Voice notes (open-ended recordings not tied to a curriculum node) contain knowledge too. Should they feed the same profile system?

# Knowledge Curriculum System — Implementation Plan

**Date**: 2026-03-15
**Status**: Plan — awaiting review

---

## Executive Summary

Build a curriculum-based knowledge mapping system that models what Stian knows across humanities domains, maps books and articles onto that curriculum, identifies knowledge gaps and frontiers, and uses this model to personalize reading preparation, cross-referencing, and exploration.

The system has four phases, each delivering standalone value while building toward the complete vision.

---

## Lessons from Otak (Critical — Do Not Repeat)

Otak's hierarchical knowledge tree failed at scale (67K items, 10K nodes, 16 levels deep) due to three problems we must avoid:

1. **Recursive splitting creates semantic drift**: Auto-splitting at 15 children produced near-synonym branches ("Professional Autonomy and Pedagogical Freedom" → "Professional Autonomy and Pedagogical Judgment"). **Fix**: Enforce max 4 levels. Never auto-split.
2. **Claims are the wrong granularity for hierarchy**: Individual claims are too atomic. You need: claims → findings → concepts → domains. **Fix**: Curriculum nodes are at "concept" level (~what a lecture would cover), not "claim" level.
3. **One tree can't serve classification, browsing, and navigation**: **Fix**: Curriculum is for human understanding and gap analysis. Embeddings handle content matching. Don't force books into the tree — link them via embeddings.

**The successful pattern from Otak**: Embeddings + typed links + filtered search, with a shallow human-readable hierarchy as a *lens*, not the primary organization.

---

## Phase 0: Data Foundation (1 session, builds on existing infrastructure)

### 0A: Book Significance Rating

**What**: Add a `significance` field to PhysicalBook: `skimmed` | `read` | `essential`

**Why**: Different books contribute different confidence to the knowledge map. An "essential" book about the Persian Wars means high-confidence knowledge; a "skimmed" book about Greek art means surface exposure.

**Implementation**:
- Add `significance` field to `PhysicalBook` type in `app/data/types.ts`
- Default: `read` (most books)
- UI: Three-segment control on book-detail screen, below reading position
- Server: Already handled by existing book sync endpoint
- Infer default from capture density: 5+ captures → suggest "essential"

**Effort**: Small — field addition + 3-segment UI control

### 0B: Import Greek History Kindle Books

**What**: Stian goes through Kindle library and includes relevant Greek/Roman history books.

**Why**: Each imported book is a knowledge signal. Even without full text, the system knows: title, author, topics, highlights, reading progress. This is the passive knowledge mapping layer.

**Action items**:
- Stian reviews Kindle library for ancient history, classical culture, philosophy books
- Uses existing `/kindle/include` flow to import each
- Sets significance rating after import
- Server runs book research agent for each (thesis, key terms, chapter insights, article connections)

**Effort**: User time only — infrastructure exists

### 0C: Library Records Import (Optional)

**What**: Import books from Norwegian library borrowing history.

**Why**: Expands coverage to physical library books read but not owned on Kindle.

**Implementation**: Depends on library API/export format. Could be a simple list of titles + dates that gets matched via Google Books API. Deferred until Kindle imports are done.

---

## Phase 1: Curriculum Generation (1-2 sessions)

### 1A: The Curriculum Data Model

**Server-side** (new file: `scripts/curriculum.py` or integrate into `research-server.py`):

```python
CurriculumDomain:
    id: str                    # "ancient_greece_500_300bc"
    title: str                 # "Ancient Greece (500-300 BC)"
    description: str           # One paragraph overview
    generated_at: datetime
    version: int               # Bump when regenerated

CurriculumNode:
    id: str                    # "ag_persian_wars_thermopylae"
    domain_id: str             # FK to domain
    title: str                 # "Thermopylae and the 300"
    description: str           # 2-3 sentence summary of what "knowing this" means
    parent_id: str | None      # Hierarchy (max 4 levels: domain → area → topic → concept)
    level: int                 # 0=domain, 1=area, 2=topic, 3=concept
    prerequisites: list[str]   # IDs of prerequisite nodes
    estimated_obscurity: int   # 1-5 (1=everyone knows, 5=specialist only)
    bloom_floor: str           # Minimum Bloom level to "know" this: recognize|explain|analyze

UserKnowledgeState:
    node_id: str
    knowledge: str             # unknown | mentioned | engaged | anchored
    interest: str              # none | curious | core
    confidence: float          # 0.0-1.0 — how sure the system is
    sources: list[str]         # book_ids, article_ids that contributed
    last_assessed: datetime    # When this node was last probed or updated
    notes: str | None          # User's own note about this topic

BookCurriculumMapping:
    book_id: str
    node_id: str
    coverage: str              # surface | moderate | deep
    inferred_from: str         # book_research | kindle_highlights | user_report | llm_inference
```

**Key design decisions**:
- **Max 4 levels** (learned from Otak): Domain → Area → Topic → Concept
- **Node descriptions are specific**: Not just "Thermopylae" but "The Battle of Thermopylae (480 BC) — Leonidas and the 300 Spartans' defense against Xerxes' invasion, its strategic significance in delaying the Persian advance, and its role in Greek cultural memory"
- **Prerequisites are a DAG**, not a tree — you can have multiple prerequisite paths
- **Bloom floor**: "Thermopylae" requires at least "recognize" (know it happened); "Athenian Democracy's structural weaknesses" requires "explain" (understand the mechanisms)

### 1B: Curriculum Generation Endpoint

**Endpoint**: `POST /curriculum/generate`

**Input**: `{ domain: "Ancient Greece 500-300 BC", depth: "introductory" | "intermediate" | "advanced" }`

**Process**:
1. LLM call (Gemini Flash) with structured output:
   - "Generate a curriculum for a {depth} university course on {domain}"
   - "Organize into max 4 levels: areas → topics → concepts"
   - "For each node: title, 2-3 sentence description of what 'knowing this' means, prerequisites (by title), obscurity rating 1-5"
   - "Aim for 50-80 leaf nodes at introductory level"
2. Parse structured output into CurriculumNode objects
3. Resolve prerequisite references (title → id)
4. Save to `data/curricula/{domain_id}.json`

**Depth levels**:
- **Introductory**: ~50-80 nodes. What a good 1-semester course covers. The default starting point.
- **Intermediate**: ~150-200 nodes. What a history major would know after 2-3 courses.
- **Advanced**: ~300+ nodes. What a graduate student specializing in this area would know.

Start at introductory. Expand specific branches to intermediate/advanced based on interest.

### 1C: Sample Curriculum Review

**Experiment E1**: Generate curricula for 3 domains Stian cares about:
1. Ancient Greece (500-300 BC)
2. Roman Republic and Empire
3. Renaissance and Early Modern Europe

Review each for:
- Is the granularity right? Too fine? Too coarse?
- Are the categories meaningful? Do they match how Stian thinks about the domain?
- Are prerequisites sensible?
- Does it feel like "if I knew all of this, I'd have a solid foundation"?

**This is the most important calibration step.** The entire system depends on curriculum quality. Spend time here.

---

## Phase 2: Book-to-Curriculum Mapping (1 session)

### 2A: Automatic Book Mapping

**Endpoint**: `POST /curriculum/map-book`

**Input**: `{ book_id: str, domain_id: str }`

**Process**:
1. Load book metadata: title, author, topics, chapter list, thesis, key_terms (from book research)
2. Load Kindle highlights if available
3. LLM call: "Given this book's metadata and content signals, which curriculum nodes does it cover? For each, estimate coverage depth (surface/moderate/deep)."
4. Save as BookCurriculumMapping entries
5. Update UserKnowledgeState for each mapped node:
   - If node was UNKNOWN → MENTIONED (from reading the book)
   - Confidence based on: book significance × coverage depth × source type
   - Essential + deep = 0.9 confidence
   - Skimmed + surface = 0.4 confidence

### 2B: Curriculum Coverage Visualization

**Endpoint**: `GET /curriculum/{domain_id}/coverage`

**Returns**: The curriculum tree with knowledge states color-coded:
- Green: ANCHORED (multiple sources, high confidence)
- Blue: ENGAGED (explicitly interacted with)
- Yellow: MENTIONED (appeared in a book/article)
- Gray: UNKNOWN
- Border/badge: interest level (starred = CORE, dotted = CURIOUS)

**UI**: Could be a web-only view initially (tree/outline format). Not a complex visualization — just the curriculum as an expandable outline with color-coded nodes.

### 2C: Gap Analysis

**Endpoint**: `GET /curriculum/{domain_id}/gaps`

**Returns**:
- List of UNKNOWN nodes that have all prerequisites MENTIONED or higher ("ready to learn")
- List of UNKNOWN nodes that are prerequisites for CURIOUS/CORE interest nodes ("blocking your interests")
- Summary: "You cover 45% of the introductory Ancient Greece curriculum. Strongest: political/military history. Gaps: Greek theater, pre-Socratic philosophy, economic/social history."

---

## Phase 3: 20 Questions Knowledge Elicitation (1-2 sessions)

### 3A: Elicitation Session Endpoint

**Endpoint**: `POST /curriculum/{domain_id}/elicit`

**Input**: Conversational — each request includes the user's response to the previous question.

**State**: Server maintains session state (which nodes are assessed, current belief distribution).

**Process**:
1. **Initialize**: Load curriculum, load existing knowledge states (from book imports), compute initial belief distribution
2. **Select question**: Find the node with highest expected information gain (closest to P(knows)=0.5, accounting for prerequisite propagation)
3. **Generate question**: LLM formats a natural conversational question about the selected node
4. **Present**: Send question + optional "card flip" summary (hidden until user responds)
5. **Process response**: User answers (unknown / heard of it / know the basics / could explain / know deeply) + optional interest (don't care / curious / core)
6. **Update beliefs**: Bayesian update on the answered node + propagate through prerequisites (if knows child → likely knows parent; if doesn't know parent → likely doesn't know children)
7. **Repeat** until: (a) 15-25 questions asked, or (b) remaining entropy is below threshold, or (c) user stops

### 3B: Question Types (Mixed for Engagement)

Based on research: don't just ask "do you know X?" repeatedly. Mix question types:

1. **Recognition**: "Have you encountered the concept of [X]?" — fast, low depth
2. **Comparison**: "Which do you know more about: [X] or [Y]?" — efficient, two data points for one question, relative judgment more reliable than absolute
3. **Connection**: "Do you know how [X you said you know] relates to [Y]?" — probes depth, reveals structure
4. **Scoping**: "You said you know about [X]. Do you know roughly when, where, and the key people involved?" — calibrates depth without testing
5. **Interest probe**: "Among these topics you haven't studied, which sounds most interesting to you?" — captures interest alongside knowledge

### 3C: Card-Flip Interaction

For each question:
1. Ask the question
2. User responds (taps a familiarity level)
3. **Flip**: Show a 2-3 sentence summary of the concept
4. User can revise: "Actually, I knew more/less than I thought"
5. This teaches while assessing — the user learns something even from the assessment

### 3D: Calibration Probes (Optional, Experimental)

Occasionally include a fabricated but plausible-sounding topic. If the user claims familiarity, adjust confidence downward for other self-reports. Use sparingly — it could feel adversarial.

Alternatively: include a topic the system knows the user knows (from a book they marked Essential) and check if their self-report matches. If they say "I don't know about the Persian Wars" but they've read Tom Holland's Persian Fire marked Essential, something's miscalibrated.

### 3E: Elicitation UI

Two options to explore:

**Option A: Chat-based** (reuse SynthesisChat component)
- Conversational flow in the existing inline chat modal
- Questions appear as messages, user types or taps responses
- Natural and familiar, but may feel slow for a rapid assessment

**Option B: Card-based** (new component)
- Full-screen cards, swipe or tap to answer
- Familiarity levels as buttons at bottom
- Card flip for summary
- Interest toggle
- Faster, more focused, feels like an activity not a conversation

**Recommendation**: Start with Option B (card-based) for the core assessment. It's faster and more suited to rapid binary decisions. Use chat for follow-up depth probes ("You said you know about X — can you tell me more?").

---

## Phase 4: Knowledge-Aware Features (2+ sessions)

These build on the knowledge map from Phases 1-3. Each is an independent experiment.

### 4A: Pre-Reading Context Generation

**The most requested feature.** When starting a new book/article:

1. Load the content's topics/claims
2. Map against curriculum
3. Identify prerequisite nodes that are UNKNOWN
4. Generate a personalized briefing covering only the gaps

**Endpoint**: `POST /curriculum/prereading-guide`

**Input**: `{ content_id: str, content_type: "book" | "article" }`

**Output**: Markdown briefing, personalized based on knowledge map. A reader who knows Greek political history but not Greek theater gets a different guide than someone who knows neither.

### 4B: Cross-Book Connection Surfacing

When a new book is imported, find curriculum nodes it shares with existing books:

"Syracuse, City of Legends and A War Like No Other both cover the Athenian expedition to Sicily (415-413 BC). Your knowledge of this event comes from two independent sources — it's becoming an anchor."

**Endpoint**: `GET /curriculum/connections?book_id=X`

### 4C: Knowledge Frontier Prompts

Generate brief "did you know?" prompts that sit at the knowledge frontier:

"You know about the Battle of Salamis (480 BC) and you just read about Carthage being expelled from Sicily the same year. Did you know this wasn't coincidence? Carthage and Persia had an alliance to attack the Greek world on two fronts simultaneously."

These are the "hooks" that make knowledge stick. They connect known anchors to adjacent unknowns.

**Trigger**: After updating reading position, after importing a new book, or as idle prompts.

### 4D: Interest-Driven Exploration

For nodes marked CURIOUS:

"You're interested in Greek musical systems but haven't studied them yet. Here's a 5-minute primer, plus two articles in your feed that touch on this."

### 4E: Curriculum-Aware Article Ranking

Integrate the knowledge map into feed ranking:

- Articles covering UNKNOWN nodes adjacent to ANCHORED nodes score highest (maximum hook potential)
- Articles covering entirely UNKNOWN territory with no hooks score lower (no context to attach to)
- Articles covering only ANCHORED nodes score lowest (nothing new)

This is the existing novelty scoring system, but informed by curriculum structure rather than just embedding similarity.

---

## Experiments & Hypotheses

### E1: Curriculum Quality (Phase 1C)

**Hypothesis**: An LLM can generate a curriculum for a humanities domain at introductory level that a knowledgeable user finds reasonable and well-structured.

**Method**: Generate 3 curricula (Ancient Greece, Roman history, Renaissance). Have Stian review each for: granularity, category meaningfulness, prerequisite accuracy, completeness.

**Success criteria**: Stian says "yes, if I knew all of this, I'd have a solid foundation" for at least 2/3 curricula with only minor adjustments.

**Risk**: LLM might produce generic/Wikipedia-level structure. Mitigation: use few-shot examples of good curricula, or use textbook TOCs as seeds.

### E2: Book Mapping Accuracy (Phase 2A)

**Hypothesis**: Given a book's metadata (title, author, topics, chapters, thesis, key_terms) and optionally Kindle highlights, an LLM can accurately map which curriculum nodes the book covers.

**Method**: Map 5+ imported books against the Ancient Greece curriculum. Have Stian verify: "Does this book actually cover these topics? At the estimated depth?"

**Success criteria**: ≥80% of mappings are correct. False positives (claiming coverage that isn't there) should be <10%.

**Risk**: Without full text, mapping may be too superficial. Mitigation: use book research (thesis, chapter summaries) + Kindle highlights + LLM knowledge of well-known books.

### E3: 20 Questions Convergence (Phase 3)

**Hypothesis**: 15-25 adaptive questions can map a user's knowledge of a domain to useful resolution (correctly classifying ≥70% of curriculum nodes as known/unknown).

**Method**: Run a 20Q session on Ancient Greece. Then manually verify: for each node the system classified, does Stian agree? Count correct classifications.

**Success criteria**: ≥70% accuracy after 15 questions, ≥85% after 25 questions.

**Baseline**: Random guessing would be ~50% (assuming balanced known/unknown).

### E4: Self-Report Calibration (Phase 3D)

**Hypothesis**: Stian's self-report is reliable for specific, well-scoped questions (≥80% accurate vs. probed verification).

**Method**: After the 20Q session, select 10 nodes where Stian claimed "know the basics" or higher. Ask a follow-up probing question for each. Count how many he can actually explain.

**Success criteria**: ≥80% of "know the basics" claims hold up under probing.

**If it fails**: Adjust the familiarity scale descriptions to be more specific, or add more calibration probes.

### E5: Pre-Reading Guide Usefulness (Phase 4A)

**Hypothesis**: A personalized pre-reading guide (covering only unknown prerequisites) is more useful than a generic introduction.

**Method**: Generate a pre-reading guide for a book Stian is about to read. Have him read it, then read the first chapter. Ask: "Did the guide help? Did it cover the right gaps? Was anything missing? Was anything unnecessary?"

**Success criteria**: Stian says the guide was helpful and correctly identified his knowledge gaps.

### E6: Curriculum Growth (Ongoing)

**Hypothesis**: The curriculum can grow organically as interest deepens — expanding specific branches from introductory to intermediate depth without losing coherence.

**Method**: After E1-E5, pick a branch where Stian has deep interest (e.g., "The Persian Wars"). Generate an intermediate-depth expansion of just that branch. Review for quality and integration with the existing curriculum.

**Success criteria**: Expanded branch feels like a natural deepening, not a separate disconnected curriculum.

### E7: Collateral Credit from Reading (Phase 2 + ongoing)

**Hypothesis**: Reading a book about the Peloponnesian War should give collateral credit to multiple curriculum nodes (Athenian democracy, Spartan society, naval warfare, Sicilian expedition) — similar to how Alif gives credit to all words in a sentence.

**Method**: After mapping 5+ books, check: does the knowledge map look reasonable? Are nodes getting credited that should be? Are any nodes incorrectly credited?

**Success criteria**: The knowledge map after importing 5+ books correctly reflects Stian's self-assessed knowledge of the domain (verified by a 20Q session).

---

## Build Order

```
Phase 0 (foundation)     Phase 1 (curriculum)      Phase 2 (mapping)
┌─────────────────┐     ┌──────────────────────┐  ┌──────────────────┐
│ 0A: Significance│     │ 1A: Data model       │  │ 2A: Auto-mapping │
│ 0B: Import books│────→│ 1B: Generate endpoint│─→│ 2B: Visualization│
│ 0C: Library?    │     │ 1C: Review/calibrate │  │ 2C: Gap analysis │
└─────────────────┘     └──────────────────────┘  └──────────────────┘
                                                          │
                              Phase 3 (elicit)            │
                        ┌──────────────────────┐          │
                        │ 3A: Session endpoint │          │
                        │ 3B: Question types   │←─────────┘
                        │ 3C: Card-flip UI     │
                        │ 3E: Elicitation UI   │
                        └──────────────────────┘
                                  │
                              Phase 4 (features)
                        ┌──────────────────────┐
                        │ 4A: Pre-reading guide│
                        │ 4B: Cross-book links │
                        │ 4C: Frontier prompts │
                        │ 4D: Interest explore │
                        │ 4E: Article ranking  │
                        └──────────────────────┘
```

**Phase 0** can happen immediately (Stian imports books while I add the significance field).
**Phase 1** is the critical experiment — if curriculum generation quality is good, everything else follows.
**Phase 2** is where the knowledge map first becomes visible and useful.
**Phase 3** fills gaps that book imports alone can't cover.
**Phase 4** delivers the real value — each feature is an independent experiment.

---

## First Session Plan (Next Time)

1. Add `significance` field to book model + UI (30 min)
2. Generate sample curriculum for "Ancient Greece 500-300 BC" (30 min)
3. Review curriculum together — calibrate granularity (30 min)
4. If curriculum is good: build `POST /curriculum/generate` endpoint (30 min)
5. Map Stian's imported books against the curriculum (30 min)
6. First look at coverage visualization (30 min)

**Total**: ~3 hours for Phase 0 + Phase 1 + start of Phase 2

---

## Technical Architecture

### Storage
- Curricula: `data/curricula/{domain_id}.json` on server
- Knowledge states: `data/knowledge_states.json` on server
- Book mappings: embedded in curriculum files or separate `data/book_curriculum_mappings.json`
- All server-first (per existing architecture)

### API Endpoints (New)
- `POST /curriculum/generate` — Generate curriculum for a domain
- `GET /curriculum/{domain_id}` — Get curriculum with current knowledge states
- `GET /curriculum/{domain_id}/coverage` — Coverage summary
- `GET /curriculum/{domain_id}/gaps` — Gap analysis
- `POST /curriculum/map-book` — Map a book to curriculum nodes
- `POST /curriculum/{domain_id}/elicit` — Run one step of 20Q elicitation
- `POST /curriculum/prereading-guide` — Generate personalized pre-reading guide
- `GET /curriculum/connections?book_id=X` — Cross-book curriculum connections

### LLM Usage
- Curriculum generation: Gemini Flash (structured output, ~50-80 nodes)
- Book mapping: Gemini Flash (given book metadata → node coverage)
- Question generation: Gemini Flash (natural conversational questions)
- Response evaluation: Gemini Flash (assess self-report, update beliefs)
- Pre-reading guide: Claude or Gemini (longer-form, nuanced writing)

### Client Integration
- New "Knowledge Map" screen accessible from ✦ drawer
- Curriculum visualization (web: expandable outline with color-coded nodes)
- 20Q session: new card-based component (could also work in a web view)
- Pre-reading guide: shown in book-detail or reader, using existing Crimson Pro reading typography

---

### E8: Voice Knowledge Dump (Phase 3 alternative)

**Hypothesis**: A 5-10 minute voice dump ("tell me everything you know about X") provides richer knowledge mapping data than 20 Questions for areas of deep knowledge.

**Method**: Pick a topic where Stian has strong knowledge (e.g., the Persian Wars). Do both a 20Q session and a voice dump. Compare: which gives a more accurate knowledge map? Which captures connections and nuance that the other misses?

**Success criteria**: Voice dump identifies at least 3 knowledge claims/connections that 20Q missed, and updates the knowledge map to better match Stian's self-assessment.

**Implementation**: Reuse existing voice capture → Soniox → LLM pipeline from book voice notes. New: LLM extraction prompt that maps transcript against curriculum nodes.

### E9: Confidence Decay and Natural Resurfacing

**Hypothesis**: Knowledge confidence should decay gradually over time (not FSRS-style but a slow fade), and encountering related content in new reading should reset the decay.

**Method**: After initial mapping, apply gentle confidence decay (e.g., -0.01/month). Track whether reading new articles/books about related topics naturally refreshes confidence. Check after 3 months: does the decayed map still feel accurate?

**Success criteria**: Decayed confidence matches Stian's self-assessment better than static confidence after 3+ months.

### E10: Re-Read Recommendations

**Hypothesis**: The system can identify books worth re-reading by comparing: (a) how much the book covers, (b) how much the user actually retained (from 20Q/voice), (c) how much their context has grown since first reading.

**Method**: For "Who Needs Greek?" — the book covers "The Contest Over Hellenism" deeply, but if the user's confidence on that node is lower than expected for a deep-coverage essential book, suggest re-reading with new context.

**Success criteria**: At least one re-read recommendation feels genuinely motivated ("yes, I'd get much more from it now").

---

## What This Does NOT Cover (Explicitly Deferred)

1. **Tech/tweets/current events**: Different problem, different solution. The curriculum approach is for deep/humanities knowledge only.
2. **Multi-user**: Single user (Stian). No multi-user considerations.
3. **Automated testing**: We verify by user review, not automated tests. The "test" is whether the knowledge map feels right.
4. **Temporal decay**: For now, knowledge doesn't decay. If you read a book 5 years ago, it still counts. This may need revisiting later.
5. **Article claim → curriculum mapping**: Could map individual article claims to curriculum nodes for finer-grained tracking. Deferred until we see if book-level mapping is sufficient.
6. **Otak integration**: Otak's 67K claims could theoretically feed into the curriculum system. But Otak's hierarchy problems make this risky. Deferred.

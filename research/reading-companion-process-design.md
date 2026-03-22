# Reading Companion Process Design

**Date**: 2026-03-21
**Status**: Active design — will iterate over multiple sessions
**Depends on**: overlapping-curricula-vision.md, curriculum system, Amygdala knowledge_map module

## The Core Problem

The system collects rich data about books (chapter summaries, claims, key terms, curriculum mappings, article connections, captures) but almost none of it is reflected back to the reader during the reading process. Page tracking is silent. Chapter changes trigger nothing. Captures are stored but extracted ideas go nowhere. The resurfacing engine is fully built but orphaned from the book UI. The story-so-far feature triggers only after 48h gaps and is too generic to be useful.

**Goal**: Create a natural reading companion loop that makes knowledge stick without feeling annoying.

## Temporal Hooks: The Key Retention Mechanism

### Why They Work

The Hamarquizen "Hanna Winsnes born 1789 = French Revolution" pattern demonstrates **elaborative encoding through temporal association**. When you connect a new fact to something you already know, the new fact becomes dramatically more durable. This is the generation effect from cognitive science.

For historical reading, dates are natural hooks because every date can be cross-referenced against known events in other curricula.

### Hook Types (All Valuable, Priority Order)

1. **Anchoring to known events** (HIGHEST PRIORITY)
   - "Archimedes died ~75 years after Alexander the Great"
   - Requires: knowing what the reader already knows (curriculum knowledge state)
   - Power: uses familiar anchor to locate unfamiliar date

2. **Same-moment connections**
   - "While Archimedes died in Syracuse, Hannibal was marching through Italy"
   - Requires: date overlap detection across curricula
   - Power: simultaneous events create spatial-temporal maps

3. **Causal chains**
   - "Archimedes' death during Rome's siege was a consequence of Hannibal's invasion — Syracuse had allied with Carthage"
   - Requires: narrative understanding of connections (LLM-generated)
   - Power: narrative connections are the stickiest memory hooks

4. **Cross-domain surprises** (ONLY when reader knows the other domain)
   - "Archimedes and Qin Shi Huang were alive at the same time"
   - SKIP when the other domain is unknown — just confusing
   - Must check: does the reader have knowledge in the referenced curriculum?

### Ad-Hoc Connections (Beyond Curricula)

Not every valuable connection fits into a curriculum. "Archimedes ↔ Leonardo da Vinci as polymaths" is memorable but doesn't belong to any single course. These are more like tags or edges in a graph than nodes in a tree.

Could work as: LLM-generated "surprising connections" that reference entities across curricula, or even entities not in any curriculum. The curriculum provides scaffolding; the richest connections are often cross-scaffold.

## Three Interaction Moments

### 1. Chapter Complete Trigger

**When**: User selects a new chapter in the dropdown (selecting "Ch 4" = "I'm starting Ch 4" = "I finished Ch 3")

**What appears**: A brief card (dismissable in 1 tap):
- 2-3 curriculum nodes this chapter covered (from chapter research + curriculum mapping)
- 1 temporal hook cross-referencing dates to other curricula
- 1 quick self-assessment: "Did you already know about [X]?" → 3-tap (new / some / knew it)
- Updates curriculum knowledge state directly

**Data needed**:
- Chapter → curriculum node mapping (from book research + curriculum mapping)
- Temporal cross-references (precomputed from curriculum node dates)
- Knowledge state (to select the most informative question)

**Design principle**: Zero friction. Must be dismissable instantly. Value comes from repetition over weeks, not from any single card.

### 2. "Review What I've Read" (On-Demand, ~3-5 Minutes)

**When**: User taps a button in book detail (or a dedicated screen)

**What it generates**: A mini-tutorial combining content from ALL books being read:
- Claims from chapters read, turned into questions with hooks
- Temporal cross-references across curricula
- "What else was happening?" connections
- Cross-book connections ("In your Sicily book you read about X, but in your Greek history book Y gives a different perspective")
- Surprising juxtapositions
- Quick self-assessment feeding into curriculum knowledge

**This is Hamarquizen's PRIME→READ→TEST pattern at scale:**
- PRIME: "Before we review, what do you remember about [X]?" (pre-question)
- READ: Mini-text with hooks, connections, context
- TEST: "Based on what you've read, [question]?" → self-assessment

**Must feel rich and surprising**, not like a quiz. More like a short, well-written essay that teaches through connections and asks a few questions along the way.

**Feedback capture**: Easy to rate each card/section (useful / not useful / wrong). This feeds into improving the generation.

### 3. Map an Old Book (For Past Reading)

**When**: User adds a book from Kindle library or manually, marks it as previously read

**Process**:
1. Run curriculum mapping against the book (using book metadata, chapters, key terms)
2. Focused Amygdala probe on the mapped nodes: "You read this book a while ago. What stuck?"
   - ~10 questions, EIG-driven, converges fast
   - Results update curriculum knowledge state
3. Show connections to current reading: "Based on what you remember from [old book], here's how it connects to what you're reading now about Sicily"

**Amygdala integration**: If Amygdala doesn't support everything needed for this flow, improve Amygdala rather than building Petrarca-specific code. This functionality should be available to other projects too.

**Use case**: Persian Wars from Connie Goldman → probe what's remembered → connect to Sicily reading (Greek colonies, Persians as context for Greek expansion westward)

## Chapter Dropdown Semantics

**Decision**: The dropdown represents "what I'm currently reading" (not "what I finished").

**Selecting a new chapter implies finishing the previous one.** When user goes from "Ch 3" → "Ch 4":
- System records: Ch 3 completed at this timestamp
- Triggers the "chapter complete" card for Ch 3
- New data needed: `chapter_completions: Record<number, timestamp>` field on book

**Edge cases**:
- First chapter selection: no completion trigger (user is starting the book)
- Skipping chapters: selecting Ch 6 after Ch 3 implies Ch 3 is done, but Ch 4-5 are ambiguous. Could ask: "Did you read chapters 4-5?" or just mark Ch 3 as the last completed.
- Re-selecting earlier chapter: going back, not a completion

## Pre-Reading Book Scan

Once curriculum + knowledge map are populated enough, scanning a new book should show:
- "You already know well: [nodes]" (green, high confidence)
- "You'll likely learn about: [nodes]" (new to you, covered by this book)
- "Key context you're missing: [prerequisites of new nodes that you don't know]"

This is the "pre-chapter briefing" idea extended to the whole book. Helps set expectations and prime learning.

## Rapid Feedback / Calibration Pattern

**Proven pattern from Session 33**: HTML card-stack interface with keyboard-driven 3-way choices (j/k/l keys), flash feedback, progress bar, JSON export. Produced actionable threshold recalibration (KNOWN 0.88→0.82) in ~15 minutes of user time.

**Apply to reading companion**:
- Generate 20-30 temporal hooks → rate as "useful / meh / wrong"
- Generate 20-30 curriculum node mappings for books → rate as "accurate / partial / wrong"
- Generate review mini-texts → rate as "engaging / boring / inaccurate"

**Key insight from Session 33**: Algorithm calibration (thresholds, similarity) works great in standalone card-stack. But knowledge calibration (what do I know?) is better embedded in reading context. The reading companion should collect knowledge signals during natural use, not in a separate calibration session.

## Current Infrastructure (What Exists)

### Built and Working
- Book research: thesis, chapter summaries, claims, key terms, article connections
- Curriculum mapping: book → curriculum nodes, with coverage depth
- BookCurriculumContext component: shows curriculum coverage in book detail
- Chapter insights endpoint: `POST /book/chapter-insights` (exists but NOT called from UI)
- Resurfacing engine: generate review sessions from captures (exists but orphaned)
- Amygdala EIG probing: converges in ~10 questions on 50-70 node graphs
- Feedback calibration HTML template: proven keyboard-driven card-stack

### Needs Building
- Chapter completion tracking (`chapter_completions` field)
- Chapter complete card (brief, dismissable)
- Temporal hook generation (cross-reference dates across curricula)
- Cross-book review generation (mini-tutorials from multiple books)
- "Map old book" flow (curriculum mapping → Amygdala probe → connections)
- Pre-reading book scan (curriculum-based preview)
- Feedback capture on generated content (inline rating)

### Current Pain Points (User Feedback)
- Catch-up / story-so-far is not helpful — too generic, only triggers after 48h
- No feedback from marking pages — silent save
- No feedback from capturing notes — ideas extracted but not reflected back
- Chapter dropdown semantics unclear (currently reading vs finished)

## Open Questions

1. **Where does the review screen live?** Dedicated screen in ✦ drawer? Section within book detail? Both?
2. **How often should reviews combine cross-book content?** Every time? Only when books overlap on curriculum nodes?
3. **What's the minimum curriculum coverage needed before the system is useful?** Just Sicily (70 nodes)? Need 3+ curricula with cross-links?
4. **Should temporal hooks be precomputed or generated on-demand?** Precomputed is faster but less contextual. On-demand is richer but slower.
5. **How to handle books without good chapter data?** Many Kindle imports may lack chapter structure.
6. **Voice-based review?** "Tell me what you remember about Chapter 3" → transcribe → compare to curriculum → update knowledge state.

## Connections to Other Research

- **overlapping-curricula-vision.md**: Nexus points (multi-curriculum entities) are the highest-value hooks
- **feedback_knowledge_encoding.md**: Books provide encoding, system maintains through connections — hooks ARE those connections
- **feedback_michel_thomas.md**: "I'll manage your memory" — chapter complete cards and reviews are the system doing this
- **beyond-flashcards-knowledge-retention.md**: Elaborative retrieval > rote retrieval — hooks > flashcards
- **Hamarquizen**: PRIME→READ→TEST validated, memory hooks work for 11-year-olds and adults
- **Session 33 calibration**: Card-stack feedback pattern proven for rapid iteration

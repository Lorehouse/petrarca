# Knowledge Curriculum Vision — Design Ideas & Open Questions

**Date**: 2026-03-15
**Status**: Exploratory — ideas captured from brainstorming session

---

## The Core Vision

A curriculum-based knowledge mapping system that:
1. Models what Stian knows across history, philosophy, literature, art, culture, geography
2. Maps incoming content (books, articles, videos) onto that curriculum
3. Identifies gaps and the "knowledge frontier" (Zone of Proximal Development)
4. Uses gaps to personalize: pre-reading guides, explanations, connections, recommendations
5. Tracks both **knowledge** and **interest** separately

**Scope**: This applies to humanities/deep knowledge (history, philosophy, sociology, art history, culture, geography). It does NOT apply to tech news, tweets, Claude Code articles — those are a different problem solved differently.

---

## The Curriculum Idea

### Bottom-Up Generation
Instead of building a universal ontology top-down, ask: "What would a good university introductory course on [domain] cover?" The LLM generates ~50-80 concepts organized hierarchically. This defines the units of knowledge.

### Curriculum as Organizing Principle
Everything read in the humanities category maps onto curriculum branches:
- One book might cover multiple branches (a history of Sicily touches politics, military, culture, geography)
- One book might skip sibling branches (covers the Athenian expedition but not Spartan society)
- This makes gaps visible: "You know branch A and C but not B"

### Open Questions on Structure
1. **Single curriculum or interlinked set?** — Is "Ancient History" one curriculum? Or is it "Ancient Greece," "Ancient Rome," "Ancient Egypt" as separate curricula with cross-links?
2. **Pre-generate or grow organically?** — Do we generate the full curriculum upfront, or start with what the user encounters and expand?
3. **How deep to go?** — A semester course on Alexander the Great goes extremely deep. An intro to ancient history mentions him briefly. Depth should match interest, but start shallow.
4. **Resolution**: Start at introductory course level (~50-80 topics per domain). Deepen organically when the user shows interest or reads deeply in a sub-area.

### Mapping Content to Curriculum
Precision of mapping varies by source:
- **EPUB/full text**: Precise extraction of topics covered
- **Kindle highlights**: Good signal for what was engaged with
- **No full text**: Use book reviews, summaries, table of contents, LLM knowledge of the book
- **Post-reading questions**: "Did you learn about X in this book?" — direct but requires user input
- **Physical book captures**: Voice notes and page photos give specific content signals

---

## Knowledge + Interest: Two Dimensions

The system should track both:

### Knowledge States
- **Unknown**: Never encountered
- **Mentioned**: Appeared in something I read (collateral credit)
- **Engaged**: I explicitly interacted with it (hook, voice note, 20Q probe)
- **Anchored**: Multiple sources, strong connections, vivid memory

### Interest Levels
- **Don't care**: "I don't care about ancient Greek boat design" — skip unless it's prerequisite for something I do care about
- **Curious**: "I'd like to know about Greek musical rhythm systems" — actively want to explore
- **Core interest**: "Ancient Greek political history is deeply fascinating to me" — prioritize, go deep

Interest and knowledge are independent: you can be very interested in something you know nothing about, or knowledgeable about something you're not particularly interested in.

---

## The 20 Questions Knowledge Elicitation

### Self-Report Reliability
Stian mostly trusts his own self-assessment. The key is **question specificity**:
- Too broad: "Have you heard about the Battle of Salamis?" → Almost certainly "yes" but what does that mean?
- Better: "Do you know roughly when, where, and who was involved?" → Much more calibrating
- Even better: Provide context that helps calibrate

### Card-Flip UI Idea
One promising interaction pattern:
1. System asks: "Do you know about [X]?"
2. User answers yes/no/somewhat
3. System "flips the card" — shows a brief summary of X
4. User can revise: "Oh, I actually didn't know that part" or "Yes, exactly what I thought"

This serves dual purposes:
- Calibrates the self-report (user sees what "knowing X" actually means)
- Teaches — if the user didn't know, they just learned something
- Creates a natural, non-test-like interaction

### Capturing Interest During Elicitation
During the 20 Questions session, capture interest alongside knowledge:
- "I don't know about Greek boat design, and I don't care" → UNKNOWN + LOW INTEREST
- "I don't know about Greek musical systems, but I'd love to" → UNKNOWN + HIGH INTEREST
- "I know about the Persian Wars and I'm deeply fascinated" → KNOWN + HIGH INTEREST

---

## Alif Parallel (Deeper)

Alif demonstrates the principle at word level:
- "You know these words → here's one more word → now you can read this sentence"
- Building on known foundation, one step at a time
- Every interaction generates passive signals (collateral credit)

The humanities equivalent:
- "You know about the Peloponnesian War and the Persian Wars → did you know that at the same time in Persia, [person] was connected to [person], and it's actually analogous to [thing you know]?"
- Building conceptual knowledge by layering new information onto known hooks
- Every book read generates passive signals across the curriculum

Key difference: Alif has discrete, well-defined units (words). History has fuzzy, overlapping concepts. The curriculum provides the structure that makes concepts more word-like.

---

## Otak Connection

The Otak project (~/src/otak) attempted:
- Extract claims from thousands of academic articles
- Map claims onto a self-balancing hierarchical tree
- Bottom-up knowledge organization

This was "too bottom-up" and didn't fully succeed. The curriculum approach is a middle ground:
- Structure comes from a curriculum (top-down scaffold)
- Content maps onto that structure (bottom-up filling)
- The scaffold grows and adapts based on what's being read

Research in Otak's research/ directory may contain useful work on:
- Knowledge graph construction
- Claim extraction and organization
- Hierarchical knowledge structures

---

## The "Layering" Principle

The most powerful use of the knowledge map:

> "You know this and this and this. But did you know that in Persia at that time, this person was connected to that person, and it's actually kind of analogous to [thing you know]?"

This is the ZPD in action:
1. Start from what the user knows (anchors)
2. Find the nearest interesting unknown (frontier)
3. Connect the unknown to the known (hook)
4. Present it in a way that makes the connection vivid

This works for:
- **Pre-reading guides**: "Before reading this book, here's the context you're missing"
- **In-reading annotations**: "This connects to [thing you know from another book]"
- **Post-reading reflection**: "Now that you know this, here's how it connects to [other domain]"
- **Curiosity prompts**: "You know A and C — did you know B connects them?"

---

## Use Cases (Prioritized by Impact)

1. **Pre-reading context generation** — "I want to read the Oresteia" → personalized prerequisite guide
2. **Cross-book connection surfacing** — "The Syracuse book and your Kindle book about the Peloponnesian War overlap here"
3. **Gap identification** — "Your knowledge of Classical Greece is strong but you have no coverage of the Hellenistic period"
4. **Interest-driven exploration** — "You're curious about Greek music — here are 3 articles and a book chapter"
5. **Knowledge frontier prompts** — "You know X, and here's one more thing that connects beautifully"
6. **Book significance-aware revisiting** — Essential books get deeper curriculum mapping and more revisit prompts

---

## Book Significance Rating

Three tiers for how significant/formative a book was:
- **Skimmed**: "I've seen the content" (knowledge map value, low revisit value)
- **Read**: Standard reading (solid knowledge map, moderate revisit)
- **Essential**: "This book shaped my thinking" (high revisit value, strong hooks, deep curriculum mapping)

Significance affects:
- How much weight to give the book's content in the knowledge map
- Whether to generate deep connections from this book
- Whether to suggest revisiting when new connections emerge
- How much curriculum credit to assign (Essential = high confidence, Skimmed = lower)

Could potentially infer a default from: capture density, reading time, highlights count.

---

## Technical Considerations

### Curriculum Data Model (Sketch)
```
CurriculumNode:
  id, title, description
  parent_id (hierarchy)
  domain ("ancient_greece", "renaissance_art", etc.)
  depth_level (1=broad, 5=very specific)
  prerequisites: [CurriculumNode]

UserKnowledgeState:
  node_id, user_id
  knowledge: unknown | mentioned | engaged | anchored
  interest: none | curious | core
  confidence: 0.0-1.0 (how sure we are about the knowledge state)
  sources: [book_id, article_id, ...] (what provided this knowledge)
  last_assessed: timestamp

BookCurriculumMapping:
  book_id, node_id
  coverage_depth: surface | moderate | deep
  chapters: [chapter numbers that cover this node]
```

### Where This Lives
- Server-side (all data server-first per existing architecture)
- Curriculum generation: LLM call (Gemini Flash for structure, possibly Claude for nuance)
- Knowledge state: persisted per user, updated from book imports + 20Q sessions + reading signals
- Curriculum visualization: web UI (good candidate for the 3-column reader layout)

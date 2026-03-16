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

## The Michel Thomas Principle: "I'll Manage Your Memory"

**Critical UX insight**: The fear of being overwhelmed, the fear of forgetting, has been *stopping Stian from reading interesting nonfiction*. Michel Thomas' language teaching method explicitly tells students: "Don't try to remember. I'll manage your memory for you." That freedom from anxiety actually improves learning.

**For Petrarca**: The system should embody this principle. The message to the user is: "Read whatever interests you. Don't worry about forgetting. I'm tracking everything, making connections, and I'll resurface what matters when it matters." The knowledge map isn't a homework assignment — it's liberation from the anxiety of forgetting.

This connects to the Alif experience: when you forget a word in Alif, adding mnemonics, etymology, usage details, more context helps you remember better. The system adapts *its* approach when you struggle, rather than demanding you work harder. The same principle should apply to historical/cultural knowledge.

---

## The Civilization Game Map Metaphor

**Two primary dimensions: Space and Time.**

Imagine a Civilization-style fog-of-war map of human history. You start in darkness. When you anchor on a point — say, Charlemagne — you light up that region. Then you can explore outward:

**Simultaneously (space axis)**: What's happening at the same time in Muslim Spain, Constantinople, Baghdad?

**Backwards (time axis)**: What enabled the Carolingians? What happened with the Roman Empire that made the Pope so weak he had to beg Charlemagne for support?

**Forwards (time axis)**: Viking Age, High Middle Ages, the emergence of France and Germany.

**Even a high-level view would be enormously valuable**: "In the 1300s, roughly this was happening; in the 1400s, roughly this." Not details — just the landscape.

### Multiple Lenses (depth dimensions)

Within any space-time region, you can look through many lenses:
- **Macrohistoric theories**: Pirenne's thesis that Islamic expansion stopped Mediterranean trade, causing the Carolingian ascendancy
- **Fractal depth**: health systems, education, scholasticism, the Church
- **Thematic threads across time**: trace music, painting, the Church, women's rights, or language through centuries
- **Political/military events**: wars, rulers, alliances
- **Economic structures**: trade routes, currency, agriculture
- **Intellectual history**: ideas, philosophies, scientific developments

Each lens reveals a different map of the same territory.

### Dependency Graph (Math Academy Model)

Some knowledge has genuine prerequisites:
- To assess Pirenne's thesis, you first need: Charlemagne, Muslim expansion in the 700s, Mediterranean trade patterns, Frankish economic structure
- Most *facts* in history can be studied independently
- But *theories and analytical models* require factual prerequisites — you need the facts before you can evaluate the explanation

This suggests a layered approach:
1. **Facts/events layer**: Can be learned in any order
2. **Connections/theories layer**: Requires specific facts as prerequisites
3. **Analytical/evaluative layer**: Requires understanding of multiple theories

### Cultural Literacy and "What Should an Educated Person Know?" (E.D. Hirsch)

A different approach to the depth calibration problem: instead of asking "what does a university course cover?", ask "what would an educated person expect you to know?"

- Say "Pericles" or "Alcibiades" → should immediately evoke their life story
- Say "the king of Sparta during the Persian Wars" → should evoke Leonidas, but random other Spartan kings don't matter as much
- This changes across eras and cultures: what a Victorian English gentleman "should know" differs from today
- But it's a useful proxy for calibrating depth

### Network Centrality: Hub Nodes in the Knowledge Graph

Some figures, events, and concepts are **hub nodes** with enormous connectivity:
- **Alexander the Great, Charlemagne, Peter the Great** — learning about them efficiently teaches you about many adjacent topics
- **Wars where civilizations collide** — the Persian Wars, the Crusades, the Mongol conquests
- **Great thinkers** — Aristotle, Augustine, Montesquieu

Two reasons to learn about a hub node:
1. **Efficiency**: It connects to so many things that learning it opens up adjacent knowledge
2. **Reference frequency**: Other texts *assume* you know it. If you're reading Wilamowitz on Greek history or Brandes on European cultural movements, what references do they assume their readers know?

The "reference knowledge" angle is especially important for someone who reads old academic texts and primary sources: the authors assume a shared cultural vocabulary. Mapping what that vocabulary is (for a given era of scholarship) would be extremely valuable.

### Implications for Curriculum Design

These perspectives suggest the curriculum should support multiple views:
1. **Chronological/geographic**: The Civilization map (space × time)
2. **Thematic**: Tracing threads (democracy, trade, art) across time
3. **Dependency-based**: What do you need to know before you can understand X?
4. **Centrality-based**: Which nodes are most connected / most frequently referenced?
5. **Cultural literacy**: What "should" an educated person know about this domain?

The current curriculum structure (hierarchical, max 4 levels) is a good start but may need to be augmented with:
- Cross-links between nodes in different branches (not just prerequisites)
- A "centrality score" or "cultural weight" per node
- Space-time coordinates for each node (century, region)
- Thematic tags allowing slice-by-theme views

---

## Encoding vs Remembering: Books as the Learning Tool

A critical distinction from Alif and SRS research: **spaced repetition is not good for initial learning.** Encoding — getting something into long-term memory in the first place — requires a different process. In Alif, this is the "encounter" phase with hooks, etymology, and rapid repetition before SRS begins.

For history and culture, **each book IS the encoding process**: narrative, anecdotes, structuring, the author's voice, the way arguments build. After finishing a book (or even 3 chapters of the Sicily book), you *feel* like you learned something. That feeling is real — encoding happened through deep engagement with the material.

The system's job is not to teach. It's to **maintain and integrate** that encoded knowledge:
- Connect it to other books and articles
- Surface it when relevant new content appears
- Prevent the vivid mental model from fading into vagueness
- Help prepare for the *next* encoding session (pre-reading guides)

### Imperfect Acquisition

First-read acquisition is always partial. "Who Needs Greek?" was profound and inspirational, but there was so much new information that much was missed. This means:
- Significance rating alone doesn't capture readiness for revisiting
- A book marked "Essential" that was also overwhelming should be flagged as "want to revisit"
- Re-reading with better context (from subsequent reading) would yield much more
- The knowledge map could show: "You read this book but your coverage of its topics suggests you'd get much more from a re-read now"

### Knowledge Decay (Not SRS)

Knowledge does decay, but not like forgetting a flashcard answer. It's more like: the vivid mental model fades, connections become vaguer, the sense of understanding becomes less crisp.

**Don't model this as FSRS.** Instead:
- Model as gradual confidence decay on the knowledge map
- Natural resurfacing through related reading is the best maintenance (the Alif principle: encountering a concept in a new context is better than isolated review)
- The system can notice when confidence is decaying and proactively surface connections

### The Physical-Digital Synergy

Two directions of support between physical reading and the digital system:

**Digital → Physical**: Pre-reading guides prepare you for a physical book. In Alif: pre-studying words during the week → reading fluently from a physical book by the fireplace on the weekend.

**Physical → Digital**: Taking pictures of pages, voice notes, and scheduling reviews ensures that what you read in a physical book actually sticks. The physical reading experience is sacred — the digital system supports it, never replaces it.

---

## Voice Knowledge Dumps: A Third Elicitation Method

Beyond 20 Questions (structured, boundary-finding) and book imports (passive, coverage-based), a third approach: **voice knowledge dumps**.

Go for a walk, speak into the microphone, dump everything you know about a topic. Process this as rich input for the knowledge map.

**Advantages over 20 Questions:**
- Much richer signal for areas of deep knowledge
- Captures connections and narrative structure, not just "I know / I don't know"
- Natural and enjoyable (walking + talking)
- Can reveal knowledge the user didn't realize they had

**Can be prompted/scoped:**
- "Tell me everything you know about Romanticism"
- "Walk me through what you know about these specific people..."
- "What do you know about this time period in this region?"
- "What connections do you see between X and Y?"

**Complements 20 Questions:**
- 20Q is better for breadth and boundary detection
- Voice dumps are better for depth and connection quality
- Use 20Q first to map the terrain, then voice dumps to deepen specific areas

**Processing pipeline:**
- Voice → Soniox transcription → LLM extraction of claims/concepts/connections
- Map extracted knowledge against curriculum nodes
- Update confidence and state based on richness of what was said
- Could even detect misconceptions or partial understanding

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

# Physical Book Companion: Experimental Directions

**Date**: 2026-03-15
**Based on**: 6 parallel research agents covering Matuschak/mnemonic medium, PKM ecosystem, CHI/HCI research, LLM prototypes, spaced learning alternatives, and physical-digital bridging products.

---

## The Central Insight

Six independent research threads converge on one idea:

> **The best way to keep book knowledge alive is not to review it in isolation, but to connect it to new reading.**

Every article in Petrarca's feed is a potential reinforcement event for book knowledge. The system's job is to detect and surface these connections. This is backed by:

- **Spreading activation** (cognitive psychology): encountering concept X automatically triggers partial recall of related concept Y
- **Analogical reminding** research: remindings produce better transfer than explicit comparison
- **Transfer-appropriate processing**: the best "review" context for book knowledge is another reading context, not a flashcard session
- **Fuzzy-trace theory**: gist memory (arguments, frameworks) decays much more slowly than verbatim memory (specific examples, quotes) — so reinforce the gist through new contexts

No existing product connects physical book captures to a broader knowledge system. Readwise, Highlighted, Screvi, Basmo — they all stop at capture. Petrarca's existing 4,500+ article claims with embeddings are a structural advantage nobody else has.

---

## Five Research-Backed Principles

### 1. Comprehension Before Memory
Matuschak's biggest discovery (2023): "What seems like a problem of forgetting is sometimes a problem of reading comprehension — never having understood in the first place." Any resurfacing system must check comprehension at capture time, not just resurface content later.

### 2. Generation > Passive Re-Exposure
Self-generated content is remembered far better than passively consumed content. Voice notes, self-explanation, and responding to prompts all activate the generation effect. Readwise's passive highlight resurfacing is better than nothing, but active engagement is dramatically more effective (effect sizes 0.50-0.61).

### 3. Deliberate Friction Aids Learning
CHI 2024 Best Paper: constraining highlights to 150 words improved comprehension 11-19% over unlimited highlighting. Physical books naturally constrain annotation; digital capture should introduce equivalent selectivity. The Zettelkasten lesson: 5 minutes per note kills adoption. The sweet spot is ~15 seconds of deliberate engagement.

### 4. Voice is the Ideal Capture Modality
Three converging effects: **production effect** (speaking aloud improves memory 10-20%), **generation effect** (producing > consuming), **self-explanation effect** (meta-analysis: g=0.55 across 64 studies). Voice note-taking produces higher conceptual understanding than typing (Kang et al., 2020). AudioPen has proven the "rambling voice → structured text" pipeline works commercially.

### 5. Don't Build Manual Organization
The PKM graveyard is littered with systems that demand manual tagging, linking, and filing. Zettelkasten practitioners report spending 4x more time on notes than on reading. All organization should be computed from embeddings and LLM analysis. Petrarca already has this infrastructure.

---

## Eight Experiments to Test

Ordered by expected impact × feasibility. Each can be built incrementally.

### Experiment 1: Reading Echoes — Books Enriching Articles
**Priority: HIGHEST. Leverages existing infrastructure. Strongest research backing.**

**What**: When reading an article, detect semantic matches between article claims and book captures. Surface as subtle margin annotations: "cf. [Book], Ch. 3: [relevant passage]"

**How it works**:
1. Book captures are embedded using Nomic (same as article claims)
2. At article load time, compare article claims against all book capture embeddings
3. Matches above the EXTENDS threshold (0.68-0.78 cosine) appear as "Reading Echoes"
4. Subtle design: thin left border in rubric color, small book icon, tappable to expand
5. Max 2-3 echoes per article to avoid clutter

**Why it should work**:
- Triggers analogical reminding (research: better transfer than explicit comparison)
- Natural spacing in a genuine reading context (transfer-appropriate processing)
- The reader's recognition of a familiar concept triggers retrieval of the original source
- Intrinsically motivated: the new article is interesting in its own right
- Preserves Petrarca's core reading flow — echoes are optional, not interruptions

**What to measure**:
- Do book concepts that get "echo" reinforcement decay more slowly?
- Click-through rate on echoes
- Does seeing echoes change capture behavior in future book reading?

**Implementation cost**: Low — uses existing embedding infrastructure, existing article reader, existing claim comparison logic.

---

### Experiment 2: Smart Page Photo Processing
**Priority: HIGH. Enhances existing capture with zero UX change.**

**What**: When a user photographs a book page, use Gemini Vision to do more than OCR:
1. **Detect annotations**: highlighted/underlined text, marginal notes, post-it notes
2. **Extract page number**: auto-update reading progress (no competitor does this)
3. **Identify key passages**: flag important passages the user didn't mark ("suggested highlights")
4. **Generate elaborative prompt**: "You marked this passage — why did it strike you?"

**How it works**:
- Extend existing `call_vision()` endpoint with structured JSON output
- Prompt: "This is a photo of page from [Book]. Extract: (a) all text, (b) any highlighted or underlined passages specifically, (c) the page number, (d) any marginal annotations. Also identify the single most important passage on this page."
- Return structured response: `{ full_text, highlighted_passages[], page_number, margin_notes[], key_passage, elaborative_prompt }`
- Auto-update `currentPage` from extracted page number

**Why it should work**:
- Matuschak's highlight-driven prototype (14 participants "broadly loved" it) adapted to physical books
- "Suggested highlights" address the comprehension problem — catching what the reader's eyes skipped
- Page number extraction eliminates manual progress tracking
- Zero additional UX steps — just photograph as usual, get richer output

**What to measure**:
- Accuracy of annotation detection vs. page-level OCR
- Do "suggested highlights" prompt additional captures?
- Does auto progress tracking increase capture frequency?

**Implementation cost**: Low — modify existing vision prompt, add structured parsing to `book-api.ts`.

---

### Experiment 3: Voice-First Capture with Self-Explanation
**Priority: HIGH. Triple cognitive advantage.**

**What**: After any book capture (photo/text), prompt the user to record a 15-30 second voice note with a specific self-explanation frame:

- After first capture from a chapter: "What's the main argument this passage supports?"
- After subsequent captures: "How does this connect to your earlier capture about [X]?"
- After cross-book captures: "This reminds me of [concept from another book]. Do you see a connection?"

**How it works**:
1. User takes photo or types capture
2. App shows brief prompt (one sentence) based on capture context
3. User records voice note (or skips — no forced friction)
4. Soniox transcribes → LLM extracts atomic claims from both OCR + voice
5. Voice note is the user's "literature note"; claims become candidates for the knowledge index

**Why it should work**:
- Production effect + generation effect + self-explanation effect (combined g ≈ 0.55)
- Voice is 3x faster than typing, so friction stays low
- Self-explanation at capture time addresses Matuschak's comprehension-before-memory insight
- The prompt is calibrated to capture history — gets more connective over time

**What to measure**:
- Ratio of voice captures to photo-only captures
- Retention of voiced vs. unvoiced captures (test via prompted recall 2 weeks later)
- Quality of LLM-extracted claims from voice vs. OCR alone

**Implementation cost**: Medium — Soniox integration exists, need prompt logic and claim extraction pipeline for captures.

---

### Experiment 4: Constrained Capture ("Pick 3")
**Priority: MEDIUM. CHI 2024 Best Paper finding.**

**What**: After OCR extracts full page text, present it and ask the user to **tap the 3 most important sentences**. The constraint forces selectivity, which improves comprehension 11-19%.

**How it works**:
1. Page photo → OCR → full text displayed with sentence boundaries
2. User taps up to 3 sentences (highlighted in rubric color)
3. Only selected sentences are saved as captures
4. Optionally: LLM suggests 1 additional sentence the user may have missed ("suggested highlight")

**Why it should work**:
- CHI 2024 Best Paper (University of Waterloo): constrained highlighting outperforms unlimited
- Forces the reader to make a judgment about importance — this IS the comprehension work
- Physical books naturally constrain (you can't highlight everything on paper either)
- Reduces capture noise — future resurfacing and synthesis work better with curated captures

**What to measure**:
- A/B test: constrained vs. unconstrained capture
- Comprehension of captured passages (prompted recall after 2 weeks)
- User preference (do people find the constraint annoying or helpful?)

**Implementation cost**: Medium — needs sentence-level text display and selection UI.

---

### Experiment 5: Resonance Resurfacing (Not Flashcards)
**Priority: MEDIUM. The "timeful" extension for book captures.**

**What**: A periodic resurfacing screen (daily or 3x/week) showing 3-5 captures from books at expanding intervals. NOT as flashcards to test recall, but as **re-encounters** with generative prompts.

**How it works**:
- Each capture appears with original context (book, chapter, page photo thumbnail)
- Below the capture, an LLM-generated "resonance prompt":
  - "How does this connect to something you've been thinking about recently?"
  - "Has your view on this changed since you first captured it?"
  - "Where have you encountered this idea in your recent reading?"
  - "What would you add to this note now?"
- User can: **dismiss** (schedule further out), **respond** (voice/text → linked capture), or **connect** (link to another capture/article)
- Interval scheduling: simple expanding intervals (7d → 14d → 30d → 60d), reset on engagement

**Why it should work**:
- Combines spacing effect with generation effect
- Open-ended prompts address Matuschak's "habits and mindsets resist prompt-ification"
- Reader-driven, not author-driven (avoids the "implicitly authoritarian" problem)
- Marination: "let's come back in a few days, see what bubbles up"
- SRS reframed as attention programming, not memory drilling

**What NOT to do**:
- No cloze deletions or recall testing
- No streak counters or gamification
- No forced daily review — this is optional enrichment

**What to measure**:
- Response rate and response richness over time
- Do users who engage with resurfacing retain book arguments longer?
- Optimal interval schedule (are fixed intervals fine or do we need adaptive?)

**Implementation cost**: Medium — needs scheduling logic, LLM prompt generation, new UI screen.

---

### Experiment 6: Cross-Source Synthesis (The Killer Feature)
**Priority: HIGH (the unique differentiator), but higher implementation cost.**

**What**: Connect physical book captures to Petrarca's 4,500+ article claims using the same embedding infrastructure. Show: "Chapter 3 of this book relates to these 4 articles you've read."

**How it works**:
1. Book captures are embedded alongside article claims in the same vector space
2. On the book detail screen, show a "Connections" section: articles whose claims match book captures
3. On article pages, Reading Echoes (Experiment 1) show the reverse direction
4. Auto-generate "book maps" clustered by topic (not by chapter) using embedding similarity
5. Growth stages (Appleton): seedling (raw photo), budding (photo + voice note), evergreen (connected to other sources)

**Why it should work**:
- Nobody else does this — every competitor stops at capture
- Petrarca's existing embedding/similarity infrastructure makes this feasible
- Closes Brander's "feedback loop" — every new capture forces recursion over old knowledge
- Sensemaking progression: shoebox (raw captures) → evidence file (clustered captures) → schema (cross-source synthesis)
- The same mechanism that powers article-to-article synthesis now works for books-to-articles

**What to measure**:
- Do users click through to connected articles?
- Does cross-source synthesis improve retention of both book and article knowledge?
- Quality of auto-generated book maps vs. chapter-based organization

**Implementation cost**: High — needs capture embedding pipeline, cross-source matching UI, book map visualization.

---

### Experiment 7: Context Restoration ("Story So Far")
**Priority: MEDIUM. Addresses the biggest UX problem in book reading.**

**What**: When a user returns to a book after 48+ hours, show a "Story So Far" briefing before they resume:

```
Welcome back to "The Prince"
Last read: 8 days ago (Ch. 3)

Your captures from Ch. 3:
• [Page photo thumbnail] "Fortune is the arbiter of..."
• [Voice note: 0:34] "The prudence argument is stronger than..."

The argument so far:
Machiavelli argued that effective rulers must learn
"how not to be good." He distinguished between
fortune and virtù as the two forces shaping political
outcomes. You found the economic arguments most
compelling.

Since you last read:
2 articles in your feed touched on related themes.

[Resume reading] [Review captures]
```

**How it works**:
1. Track `lastReadAt` per book (already in BookReadingState)
2. When gap > 48h, show restoration screen before book detail
3. Content: user's own captures (page photos, voice notes, text) + LLM-generated argument summary
4. Spatial memory cue: show actual page photos at thumbnail size (research: spatial position aids recall)
5. Cross-reading connections: articles read during the gap that touch on book topics

**Why it should work**:
- CHI 2021 (Reviews and Previews): showing previews after interruptions improves comprehension
- Context-dependent memory: seeing one's own marginalia reinstates encoding context
- No mainstream reading app does this well — Kindle just drops you at last position
- The spatial cue (page photo thumbnails) leverages physical-book-specific memory advantages

**What to measure**:
- Time to first interaction after gap (< 30s = good)
- Do users who see restoration engage more deeply in the subsequent session?
- Optimal gap threshold (48h? 72h?)

**Implementation cost**: Medium — mostly LLM prompt engineering + UI screen.

---

### Experiment 8: Chapter Digest + Evolving Understanding
**Priority: LOWER (builds on other experiments). Highest intellectual payoff.**

**What**: When a user completes a chapter (updates progress to next chapter), synthesize all captures from that chapter into a "Chapter Digest." Over time, as the user reads related articles and other books, the digest evolves.

**How it works**:
1. On chapter completion, show: "You made 4 captures in Chapter 7. Here they are together."
2. Prompt: "In 2-3 sentences, what was this chapter really about?" (voice response ideal)
3. LLM generates a structured digest: key claims, connections to other chapters, connections to articles
4. Store as a new capture type: `chapter_synthesis`
5. **Weekly evolution**: as new articles arrive that match chapter concepts, update the digest: "Your understanding of Ch. 7 has been enriched by 3 articles this month"

**Why it should work**:
- Forces generation effect at natural chapter boundaries
- Creates the "knowledge should accrue" artifact Matuschak advocates
- Evolving digests make the value of continued reading visible
- The user's own chapter summary becomes richer over time — their understanding demonstrably grows
- Addresses the sensemaking bottleneck: most people collect captures but never progress to synthesis

**What to measure**:
- Do users record chapter summaries? (voice vs. text vs. skip rates)
- Do evolving digests correlate with longer book engagement?
- Can users reconstruct a book's argument better 3 months later with digests vs. without?

**Implementation cost**: High — needs chapter completion detection, LLM synthesis pipeline, evolution tracking.

---

## What NOT to Build

These anti-patterns emerged consistently across all 6 research threads:

1. **Traditional flashcards / Q&A cards from book captures** — Matuschak spent 5 years moving away from this. For humanistic reading, "it's not details but habits and mindsets" that matter.

2. **Manual tagging, linking, or filing** — Every PKM system that requires this sees adoption collapse within weeks. All organization should be computed.

3. **Progressive Summarization layers** (highlighting highlights of highlights) — Creates "parrots, not thinkers." One level of capture + one level of synthesis is enough.

4. **Gamification / streak mechanics** — Optimize for compliance, not understanding. No reading streaks, no points for capture count.

5. **Generic "chat with book"** — Everyone builds this. The opportunity is "chat with YOUR reading of the book" — grounded in the user's specific captures and knowledge state.

6. **Large knowledge graphs** — Every graph visualization with 200+ nodes is useless in practice. Use focus+context: one concept at center, immediate neighbors around it.

7. **Processing at capture time** — Capture should take < 15 seconds. All synthesis, connection-finding, and organization happens asynchronously (server-side LLM pipeline).

---

## Recommended Build Order

### Phase 1: Enhance Capture (builds on Session 21)
- **Experiment 2** (Smart Page Photo) — enhance `call_vision()` prompt
- **Experiment 3** (Voice Self-Explanation) — add prompt after capture
- Auto page number extraction → progress tracking

### Phase 2: Connect Books to Articles (the unique value)
- **Experiment 1** (Reading Echoes) — embed captures, match against articles
- **Experiment 6** (Cross-Source Synthesis) — connections on book detail screen

### Phase 3: Timeful Engagement
- **Experiment 5** (Resonance Resurfacing) — periodic re-encounters
- **Experiment 7** (Context Restoration) — "Story So Far" on return

### Phase 4: Deep Understanding
- **Experiment 4** (Constrained Capture) — "Pick 3" selection UI
- **Experiment 8** (Chapter Digests) — synthesis at chapter boundaries

---

## Research Sources Index

Full source details in the individual research documents:
- `andy-matuschak-research.md` — Comprehensive Matuschak overview
- `mnemonic-medium-physical-books.md` — Deep dive on mnemonic medium + physical books
- `beyond-flashcards-knowledge-retention.md` — Alternatives to SRS for conceptual knowledge
- `physical-book-digital-bridge-research.md` — Products and market landscape
- `ai-book-captures-research.md` — LLM-powered processing prototypes
- `hci-book-reading-annotation.md` — CHI/HCI academic research on reading and annotation

Key papers:
- Constrained Highlighting (CHI 2024 Best Paper): [dl.acm.org](https://dl.acm.org/doi/10.1145/3613904.3642314)
- Karpicke & Blunt (2011, Science): retrieval > elaboration
- Bjork & Bjork (2011): desirable difficulties framework
- Fuzzy-Trace Theory: gist > verbatim memory persistence
- Pirolli & Card: sensemaking model (shoebox → schema)
- Kang et al. (2020): voice > typed notes for conceptual understanding
- Matuschak (2023): comprehension pivot ("forgetting is often never-having-understood")
- Matuschak (2023): highlight-driven prototype results

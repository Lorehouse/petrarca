# Kindle Books: Experiment Design for Finished & In-Progress Books

**Date**: 2026-03-15
**Context**: Stian has hundreds of Kindle books — many finished (some with highlights), many in-progress, plus sideloaded EPUBs. The Kindle Chrome extension syncs library + highlights + progress to the server. The Book Research Agent can research any book from just its title. This document designs experiments that exploit this rich retroactive dataset.

---

## The Unique Opportunity

Unlike physical book captures (prospective — you build data as you read), Kindle books offer **retroactive data**: books already read, highlights already made, reading history already established. This enables experiments impossible with physical books:

1. **Hundreds of books can be researched in batch** — the research agent takes ~10s per book
2. **Highlights are pre-existing captures** — no new user effort required
3. **Reading dates give temporal structure** — we know *when* you read what
4. **Cross-book patterns are already there** — years of reading history to mine
5. **EPUBs can be processed for full content** — chapter-level claim extraction from actual text

---

## Data Pipeline (prerequisites, runs once)

### Step 1: Kindle Sync
Chrome extension → `/kindle/sync` → `kindle_library.json` + `kindle_highlights.json`

### Step 2: Classification
`POST /kindle/classify` → LLM classifies each book as non-fiction / historical-novel / novel / other. Only non-fiction and historical novels are interesting for knowledge experiments.

### Step 3: Batch Research
For every non-fiction book with status "read" or "reading":
```python
for book in kindle_books:
    if book.category in ('non-fiction', 'historical-novel'):
        research_book(book.asin, book.title, book.author, ...)
```
~10s per book. 200 non-fiction books = ~30 minutes. Run overnight.

### Step 4: Highlight Integration
Kindle highlights become BookCaptures:
```python
for highlight in kindle_highlights:
    book_id = highlight.asin
    capture = {
        'id': f'kh_{highlight.asin}_{hash}',
        'book_id': book_id,
        'type': 'kindle_highlight',
        'text': highlight.text,
        'page_number': highlight.location,
        'chapter': highlight.chapter,  # if available
        'created_at': highlight.timestamp,
    }
```

### Step 5: Batch Embedding
Run `build_book_claim_embeddings.py --cross-match` to embed all book claims (from research + highlights) and compute cross-source matches against the 4,500 article claims.

### Step 6: Cross-Book Matching
In addition to book↔article matching, compute book↔book similarity:
- For each pair of books, compute claim similarity
- Identify books that share arguments, contradict each other, or extend each other
- Store as `book_book_connections.json`

**Output after pipeline**: Every non-fiction book has research (thesis, chapter claims), highlights are embedded, cross-source matches exist with articles AND other books.

---

## Experiment A: Knowledge Archaeology

### What It Is
A one-time analysis of your entire reading history as a concept landscape. What have you read deeply? Where are the gaps? How do your books connect?

### How It Works

**Step 1: Topic extraction across all books**
```python
all_topics = {}
for book in researched_books:
    for topic in book.topics + [term for ch in book.chapters for term in ch.key_terms]:
        if topic not in all_topics:
            all_topics[topic] = []
        all_topics[topic].append(book)
```

**Step 2: Cluster books by topic similarity**
Using the book claim embeddings, compute book-level similarity (average of per-claim similarities). Cluster into topic groups using the same graph-based method as article clustering (`build_concept_clusters.py`).

**Step 3: Identify structural gaps**
Topics with books from only one perspective. Topics you've read about tangentially but never deeply. Topics that bridge two of your clusters but have no dedicated reading.

**Step 4: Generate the "reading landscape" report**
LLM synthesis: "You have deep knowledge of Sicilian history (8 books), medieval Mediterranean trade (5 books), Italian art (4 books). These clusters connect through your reading of Peter Robb, who bridges all three. Gap: you've read nothing on modern Italian politics, despite reading extensively about historical corruption."

### UI
A one-time generated report, shown as a special "✦ Your Reading Landscape" section at the top of the Library. Could also suggest: "Based on your gaps, consider reading..."

### Hypothesis
(HA1) The landscape report will identify at least 3 non-obvious connections between books the user didn't consciously link.
(HA2) Suggested gap-filling reading will feel relevant (user self-report).

### Data Required
50+ researched non-fiction books. The more the better — 200+ would show real structure.

---

## Experiment B: Resonance Resurfacing for Finished Books

### What It Is
The core "timeful" experiment adapted for books you finished months or years ago. Periodically resurface highlights with open-ended prompts that ask you to reconnect with the ideas — not test recall.

### Why Finished Books Are the Ideal Test Case

The research on gist vs. verbatim memory predicts a specific pattern:
- **Gist is probably intact**: you still know roughly what Pirenne argued
- **Specifics have faded**: you can't recall the papyrus evidence or the Syrian merchants
- **Highlights mark what YOU found important** — they're personal gist anchors
- **Time since reading creates genuine distance** — the re-encounter is authentic, not artificial

This means resurfacing a highlight from a book you read 2 years ago triggers exactly the "analogical reminding" mechanism the research identifies as superior to explicit review.

### How It Works

**Selection: which books to resurface from**

Priority scoring for each finished book:
```
priority = (
    highlight_count * 2              # more highlights = richer material
    + article_connection_count * 3   # connects to current reading = more relevant
    + topic_overlap_current * 5      # overlaps with currently-reading book = highest
    - months_since_finish * 0.5      # older books get slight priority (more gist decay)
)
```

Books with `priority > threshold` enter the resurfacing pool.

**Selection: which highlights to resurface**

Within a selected book:
- Prefer highlights that match recent article claims (connection-triggered resurfacing)
- Prefer highlights from chapters with high claim density (key arguments)
- Avoid highlights already resurfaced in the last 30 days
- Max 1 highlight per book per resurfacing session

**Prompt generation**

Prompts are contextualized to the specific book and highlight, with awareness of recent reading:

```python
FINISHED_BOOK_PROMPTS = {
    "reconnect": [
        "You highlighted this in '{title}' {months} months ago. What do you remember about the argument it was part of?",
        "From '{title}': \"{highlight_text}\". Does this still resonate, or has your thinking shifted?",
    ],
    "connect_to_current": [
        "You're currently reading '{current_book}'. This highlight from '{title}' seems related: \"{highlight_text}\". Do you see the connection?",
        "'{current_book}' argues {current_thesis}. Here's what '{title}' said about something similar: \"{highlight_text}\". How do these perspectives differ?",
    ],
    "connect_to_article": [
        "You read an article about {article_topic} recently. It connects to this highlight from '{title}': \"{highlight_text}\". What new light does the article shed?",
    ],
    "cross_book": [
        "You highlighted similar ideas in both '{title_a}' and '{title_b}':\n  A: \"{highlight_a}\"\n  B: \"{highlight_b}\"\nHow do these authors approach this differently?",
    ],
    "deep_reconnect": [  # for books read 1+ years ago
        "It's been {months} months since you read '{title}'. What's the single idea from the book that has stuck with you?",
        "If you had to explain '{title}' to someone in one sentence, what would you say now?",
    ],
}
```

**Response handling**

User responds via voice (preferred) or text. Response is stored as a new capture type `reflection`:
```json
{
    "id": "ref_xxx",
    "book_id": "...",
    "type": "reflection",
    "parent_highlight_id": "kh_xxx",
    "prompt_type": "connect_to_current",
    "text": "user's response",
    "created_at": ...,
}
```

Reflections are themselves embeddable — they become part of the knowledge graph, creating a layer of the reader's evolving interpretation on top of the original text.

### Scheduling

**Not daily**. The research says marination > grinding. Schedule:

- **3x per week** maximum (e.g., Mon/Wed/Fri mornings)
- **2-3 highlights per session** (5 minutes total)
- **Expanding intervals per highlight**: first resurface at 7d after pipeline runs, then 30d, then 90d, then 180d
- **Connection-triggered extras**: if an article you read today matches a book highlight, that highlight gets resurfaced in the next session regardless of schedule
- **Dormancy**: after 2 skips in a row, that highlight goes dormant (won't resurface unless connection-triggered)

### UI

**Access**: A "✦ Revisit" section on the Library tab, or a notification badge.

**Session screen**: One card at a time, swipeable.

Each card:
- **Top**: Book cover (small) + title + "Read {N} months ago" in textMuted
- **Middle**: The highlight text in Crimson Pro, with chapter context
- **Below**: The resonance prompt in EB Garamond rubric
- **If cross-book**: Both highlights shown, separated by a subtle "vs" divider
- **Bottom**: [🎤 Respond] [Skip →] [Connect 🔗]

### Hypothesis
(HB1) Response rate > 30% sustained over 4 weeks
(HB2) Responses get richer over time (measured by word count and LLM-judged quality)
(HB3) Books that receive resurfacing will be recalled more accurately at prompted test (vs. control books that don't)
(HB4) Connection-triggered resurfacing (linked to current reading) produces higher engagement than schedule-based

### Data Required
- 20+ finished books with highlights
- 4 weeks of resurfacing sessions
- ~180 resurfacing events (20 books × 3 highlights × 3 resurfaces)
- For HB3: prompted recall test at 8 weeks for resurfaced vs. control books

---

## Experiment C: Cross-Book Voice Dialogues

### What It Is
Present pairs of claims from different books on the same topic. Ask the user to articulate the tension or connection between them — via voice, to maximize the generation effect.

### Why This Is Different From Cross-Book Synthesis

The existing synthesis pipeline (session 20) generates written syntheses of article clusters. This experiment is different:
1. **The user generates the synthesis**, not the LLM — the generation effect means this is more retentive
2. **Voice, not text** — lower friction, more elaboration, production effect
3. **Two books at a time** — focused comparison, not sprawling multi-source synthesis
4. **Prompted by specific claim pairs** — not "compare these books" but "these two specific claims seem to be in tension — what do you think?"

### How It Works

**Step 1: Find interesting claim pairs**

From the cross-book matching pipeline, select pairs where:
- Similarity is in the EXTENDS range (0.68-0.78) — similar enough to be related, different enough to be interesting
- Books are from different authors
- Claims are about the same topic but take different angles

```python
def find_dialogue_pairs(book_connections):
    pairs = []
    for match in book_connections:
        if 0.68 <= match.similarity < 0.78:
            if match.book_a_author != match.book_b_author:
                pairs.append({
                    'claim_a': match.claim_a_text,
                    'book_a': match.book_a_title,
                    'author_a': match.book_a_author,
                    'claim_b': match.claim_b_text,
                    'book_b': match.book_b_title,
                    'author_b': match.book_b_author,
                    'similarity': match.similarity,
                    'tension_prompt': generate_tension_prompt(match),
                })
    return sorted(pairs, key=lambda p: p['similarity'], reverse=True)
```

**Step 2: Generate tension prompts**

```python
TENSION_PROMPT = """Two books the reader has read make related but different claims:

Book A: "{title_a}" by {author_a}
Claim A: "{claim_a}"

Book B: "{title_b}" by {author_b}
Claim B: "{claim_b}"

Generate a brief (1-2 sentence) prompt that:
1. Acknowledges both perspectives
2. Asks the reader to articulate the tension or connection
3. Is open-ended — there's no right answer

Return just the prompt text, nothing else."""
```

Example output: "Robb argues the mafia is embedded in Sicilian culture, while Ferrante portrays it as an external force that distorts Neapolitan life. Which framing feels more accurate to you — and why?"

**Step 3: Present to user**

A "dialogue" card showing both claims, the tension prompt, and a voice recording button.

### UI

**Card layout**:
```
┌──────────────────────────────────────────────────┐
│ ✦ Cross-Book Dialogue                            │
│                                                  │
│ ┌─ 📖 "Midnight in Sicily" (Robb) ─────────────┐│
│ │ "The mafia operates as alternative authority   ││
│ │ filling power vacuums left by the state"       ││
│ └────────────────────────────────────────────────┘│
│                    ↕                              │
│ ┌─ 📖 "My Brilliant Friend" (Ferrante) ────────┐│
│ │ "The Camorra's violence was something that     ││
│ │ came from outside and deformed everything"     ││
│ └────────────────────────────────────────────────┘│
│                                                  │
│ Is organized crime an intrinsic part of          │
│ southern Italian society, or an external force   │
│ imposed upon it?                                 │
│                                                  │
│           [🎤 Share your thoughts]               │
│                                                  │
│ [Skip]                                [Next →]   │
└──────────────────────────────────────────────────┘
```

### Hypothesis
(HC1) Voice responses to cross-book dialogues will be significantly longer and richer than responses to single-highlight resurfacing (Experiment B)
(HC2) Users will generate novel connections not present in either source text
(HC3) Cross-book dialogues will be the most engaging prompt type (measured by response rate and unsolicited continuation)

### Data Required
- 10+ books with cross-book claim matches
- 20+ dialogue pairs generated
- 4 weeks of sessions (1-2 dialogues per session)
- Voice transcripts analyzed for richness

---

## Experiment D: Active Content Discovery (Books → Articles)

### What It Is
When a book is researched, the system finds freely accessible articles that complement, contradict, or contextualize the book — and auto-ingests them into the article feed. The book actively shapes your reading diet.

### Why This Matters for Finished Books

For books you finished months ago, the system can retroactively find articles that relate to the book's arguments. Reading those articles triggers natural connection-based resurfacing — the research on spreading activation says encountering a related concept reactivates the book's knowledge network. This is "natural spaced repetition" — no flashcards needed.

### How It Works

**For each researched book**, the research agent already produces `suggested_reading[]`. Extend this:

```python
def discover_content_for_book(book_research):
    """Find articles to read that complement a book."""

    # 1. Suggested reading from research (already exists)
    suggestions = book_research['suggested_reading']

    # 2. Find articles that CONTRADICT the book's thesis
    contradiction_prompt = f"""
    "{book_research['title']}" argues: {book_research['thesis']}

    Find 2-3 freely accessible articles or essays that present
    counterarguments or alternative perspectives. Prefer recent
    (2020+), substantive pieces from reputable sources.
    Return JSON array: [{{"title": "...", "url": "...", "reason": "..."}}]
    """
    contradictions = call_with_search(contradiction_prompt)

    # 3. Find articles about the book's KEY TERMS (deeper context)
    for term in book_research['key_terms'][:3]:
        term_prompt = f"""
        Find 1 freely accessible article that explains or discusses
        "{term['term']}" ({term['definition']}) in depth.
        Return JSON: {{"title": "...", "url": "...", "reason": "..."}}
        """
        term_article = call_with_search(term_prompt)
        suggestions.append(term_article)

    # 4. Auto-ingest top suggestions
    for s in suggestions[:5]:
        if s.get('url') and url_is_accessible(s['url']):
            ingest_url(s['url'], source='book_discovery',
                      tags=[f"book:{book_research['book_id']}"])

    return suggestions
```

**Feed integration**: Articles auto-ingested from book discovery appear in the feed tagged with the source book. When the user reads them, the Reading Echoes system (Experiment 1 from session 22) will surface the book's claims as margin annotations — closing the loop.

### Scheduling for Finished Books

Don't discover all content at once. Spread it out:
- **Week 1 after batch research**: Discover content for the 5 highest-priority books
- **Each subsequent week**: Discover for 2-3 more books
- **Triggered discovery**: When a new article arrives (via Twitter/Readwise) that matches a book, discover 1-2 more complementary articles for that book

This creates a steady trickle of book-relevant content in the feed, maintaining book knowledge through natural reading rather than artificial review.

### Hypothesis
(HD1) Auto-ingested book-related articles will have higher engagement (read rate, claim signals) than random feed articles
(HD2) Reading a book-related article will trigger recall of the source book (measured by self-report or voice note)
(HD3) Books with active content discovery will be recalled better at 3-month test vs. books without

### Data Required
- 20+ books with suggested reading ingested
- 4 weeks of feed reading with book-related articles mixed in
- Engagement metrics: read rate, dwell time, claim signals for book-related vs. non-related articles

---

## Experiment E: Book Completion Retrospective

### What It Is
When a book is marked "finished" (either from Kindle progress hitting 100% or manual status change), generate a comprehensive "completion retrospective" — then revisit it periodically.

### How It Works

**At completion**: Generate a retrospective from research + highlights + any reflections:

```python
RETROSPECTIVE_PROMPT = """The reader has finished "{title}" by {author}.

Book thesis: {thesis}

Chapter summaries:
{chapter_summaries}

Reader's highlights ({count}):
{highlights_formatted}

Reader's reflections (if any):
{reflections_formatted}

Generate a book completion retrospective:
1. ARGUMENT_ARC: 3-5 sentences tracing the book's argument from start to finish
2. WHAT_THE_READER_FOUND: Based on their highlights, what did they find most interesting? (This may differ from what the book emphasizes)
3. UNRESOLVED_QUESTIONS: 2-3 questions the book raises but doesn't fully answer
4. CONNECTIONS: How does this book connect to other books they've read? (Use cross-book data)
5. REVISIT_HOOKS: 3 specific passages/ideas worth revisiting in 3 months (these become the seeds for Experiment B)

Return JSON.
"""
```

**At 3 months**: Resurface the retrospective with a "revisit" prompt:
"You finished '{title}' 3 months ago. Here's what you highlighted and thought at the time: [retrospective]. Has any of this changed?"

**At 1 year**: "It's been a year since you read '{title}'. What's the one idea that has stayed with you?"

### UI

**At completion**: A modal with the retrospective, similar to the Chapter Digest but for the whole book. Optional voice response: "Any final thoughts?"

**At 3-month revisit**: A card in the Resonance Resurfacing session. Shows the retrospective summary + the 3 revisit hooks.

### Hypothesis
(HE1) Completion retrospectives with user's own highlights are more engaging than generic book summaries
(HE2) The 3-month revisit produces richer reflections than the completion-time response (more distance = more perspective)
(HE3) Unresolved questions from retrospectives will sometimes be answered by subsequent reading (trackable via claim matching)

### Data Required
- 10+ books marked as finished
- Retrospectives generated for each
- 3-month follow-up for at least 5 books

---

## Experiment F: EPUB Deep Processing (Sideloaded Books)

### What It Is
For books where you have the EPUB file, go beyond research-agent claims. Process the actual text: extract real claims from real chapters, identify argument structure, find cross-book connections at the passage level.

### How It Works

This is the full `ingest_book_petrarca.py` pipeline from the book-reader-design.md plan:
1. Parse EPUB via pymupdf
2. Split chapters into sections at heading boundaries
3. For each section: extract claims, key terms, summary via Gemini
4. Embed all claims
5. Cross-match against articles AND other book claims

### Why It's Worth Doing Separately

The research agent generates claims from what Gemini knows about the book. EPUB processing generates claims from the **actual text**. The difference:
- Research claims: "Pirenne argues trade continued" (generic, from public knowledge)
- EPUB claims: "Papyrus imports from Egypt to Gaul prove continued commercial contact with the Eastern Mediterranean through the seventh century" (specific, from the text)

Specific claims produce better embeddings and better cross-source matches.

### Priority

Lower than other experiments — the research agent provides 80% of the value at 1% of the cost. EPUB processing is for books you want to go deep on.

---

## Combined Experiment Schedule

### Week 0: Pipeline Setup
- Batch research all non-fiction Kindle books (overnight)
- Embed all book claims + cross-match
- Generate Knowledge Archaeology report

### Week 1-2: Passive Enrichment
- Auto-discover content for top 10 priority books
- Reading Echoes start appearing in article feed
- No active resurfacing yet — let the system populate

### Week 3-6: Active Resurfacing
- Resonance Resurfacing begins (3x/week, 2-3 highlights per session)
- Cross-Book Dialogues begin (1-2 per week)
- Track response rates, engagement quality

### Week 6+: Retrospectives + Evaluation
- Generate completion retrospectives for finished books
- First 3-month revisits (for books finished ~3 months before pipeline)
- Evaluate: prompted recall test for resurfaced vs. control books
- Evaluate: do responses get richer over time?

---

## What Needs to Be Built (prioritized)

### Must build (enables all experiments)
1. **Kindle → book unification**: Map Kindle books to PhysicalBook records + run research agent
2. **Highlight → capture conversion**: Kindle highlights become embedded book captures
3. **Batch research pipeline**: Script to research all non-fiction books overnight
4. **Cross-book claim matching**: Book × book similarity (extend existing book × article matching)

### Build for specific experiments
5. **Resonance Resurfacing scheduler + UI** (Experiment B)
6. **Cross-book dialogue generator + UI** (Experiment C)
7. **Active content discovery with auto-ingestion** (Experiment D)
8. **Knowledge Archaeology report generator** (Experiment A)
9. **Completion retrospective generator** (Experiment E)
10. **EPUB processing pipeline** (Experiment F — deferred)

### Build order
- Items 1-4 are infrastructure that enables everything else
- Items 5-6 are the highest-value experiments (direct user interaction)
- Items 7-8 are passive/background (enrich the feed without user effort)
- Items 9-10 are later additions

---

## Research Sources

- **Gist vs. verbatim memory**: Fuzzy-trace theory ([Wikipedia](https://en.wikipedia.org/wiki/Fuzzy-trace_theory))
- **Spreading activation**: [Cognitive Psychology reference](https://www.cognitivepsychology.com/Spreading_Activation)
- **Analogical reminding > comparison**: [Gentner et al., 2016](https://link.springer.com/article/10.1186/s41235-016-0028-1)
- **Reactivation during learning**: [npj Science of Learning, 2018](https://www.nature.com/articles/s41539-018-0027-8)
- **Generation effect**: [Structural Learning](https://www.structural-learning.com/post/generation-effect-active-learning)
- **Production effect (voice)**: [MacLeod et al., 2010](https://uwaterloo.ca/memory-attention-cognition-lab/sites/default/files/uploads/files/jep10.pdf)
- **Self-explanation meta-analysis**: g=0.55 across 64 studies ([Bisra et al., 2018](https://www.researchgate.net/publication/324214361))
- **Matuschak on habits resisting prompts**: [Tweet, Oct 2023](https://x.com/andy_matuschak/status/1711501772790063224)
- **Knowledge resonance (mPFC)**: [Alonso et al., 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7479862/)
- **Transfer-appropriate processing**: [Wikipedia](https://en.wikipedia.org/wiki/Transfer-appropriate_processing)
- **InfraNodus structural gaps**: [infranodus.com](https://infranodus.com)

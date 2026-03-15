# AI-Augmented Book Reading: What LLMs Can Do With Captures (2024-2026)

Research report on the landscape of AI book reading tools, vision model capabilities for book pages, voice-to-knowledge processing, LLM question generation, and synthesis from captures — with concrete experiment proposals for Petrarca's physical book companion.

## 1. AI Book Reading Assistants: The 2024-2026 Landscape

### Google NotebookLM — The Benchmark

NotebookLM has become the reference point for "upload documents, talk to AI about them." Its evolution through 2025 is instructive:

- **Source-grounded conversation**: Upload PDFs/EPUBs, get answers with citations back to your specific documents — not generic knowledge
- **Audio Overviews**: Two AI hosts discuss your uploaded content in podcast format; Interactive Mode lets you join and ask questions
- **Video Overviews** (2025): Narrated video presentations with AI-generated visuals from your documents
- **Flashcards & Quizzes** (Sep 2025): Auto-generated from uploaded sources, customizable difficulty, shareable
- **Learning Guide** (2025): Probing open-ended questions that adapt to the learner — "instead of just giving answers, it helps you break down problems step-by-step"
- **Slide Decks & Infographics** (Nov 2025): Powered by Nano Banana Pro image generation
- **Data Table output** (Dec 2025): Structured extraction from unstructured sources

**Key insight for Petrarca**: NotebookLM proves the value of grounded AI — answers come from *your specific sources*, with citations. But it's generic: it knows nothing about what *you* found interesting. Petrarca already has the advantage of capture signals (what was photographed, what was voice-noted, what pages were visited). NotebookLM treats all content equally; Petrarca can weight by reader attention.

Sources: [NotebookLM](https://notebooklm.google/), [Student features](https://blog.google/innovation-and-ai/models-and-research/google-labs/notebooklm-student-features/), [Flashcards & Quizzes](https://workspaceupdates.googleblog.com/2025/09/flashcards-quizzes-reports-notebook-lm-google-education.html), [2025 Transformation](https://automatetodominate.ai/blog/google-notebooklm-2025-updates-complete-guide)

### Amazon Kindle — "Ask This Book" (Dec 2025)

Amazon launched "Ask This Book" as an always-on feature in the Kindle iOS app:

- Uses RAG (retrieval-augmented generation) to answer questions about plot, characters, themes
- After backlash about spoilers, constrained to only text the reader has already read
- **No author opt-out** — caused significant controversy with Authors Guild
- Available for "thousands" of English-language books
- Also launched "Story So Far" — AI briefing on events up to your current reading position

**Relevance to Petrarca**: "Story So Far" is directly buildable for physical books using accumulated page photos and voice notes. The spoiler-constraint (only discuss what's been read) is an important design principle for a reading companion.

Sources: [Writer Beware](https://writerbeware.blog/2025/12/12/kindles-new-gen-ai-powered-ask-this-book-feature-raises-rights-concerns/), [Android Police](https://www.androidpolice.com/amazon-kindle-new-ai-catch-up-tools/), [Pocket-lint](https://www.pocket-lint.com/kindle-updates-coming-in-2026/)

### Readwise — Ghostreader & Chat with Library

Readwise has evolved its AI from a feature into the core experience:

- **Chat sidebar** now subsumes all Ghostreader functionality (summarize, define, explain, custom prompts)
- **Chat with entire highlight library** — "super-powered search" across everything you've ever highlighted from Kindle, Reader, or any connected app
- **Spaced repetition daily review**: Highlights resurfaced via "probabilistic spaced repetition" algorithm (Mastery); active recall cards with Soon/Eventually feedback
- **Mastery cards**: Convert highlights to flashcards with spaced repetition scheduling
- Latest models supported: GPT-4.1-mini included, o3 available with own key

**Relevance to Petrarca**: Readwise's "chat with your highlight library" is essentially what Petrarca could build with accumulated book captures. The spaced repetition of highlights is already in Petrarca's DNA (FSRS). The key gap Readwise has: it doesn't process *physical book* captures at all.

Sources: [Ghostreader docs](https://docs.readwise.io/reader/guides/ghostreader/overview), [Changelog](https://readwise.io/changelog), [Spaced repetition](https://blog.readwise.io/hack-your-brain-with-spaced-repetition-and-active-recall/)

### Kairos (Every.to) — A Beautiful Failure

Kairos was the most conceptually ambitious AI reading companion, with four levels of engagement modeled on Adler's "How to Read a Book":

1. **Elementary Reading**: AI clarifies difficult passages in context
2. **Inspectional Reading**: Chapter summaries, "catch up" on previous sections
3. **Analytical Reading**: AI poses thought-provoking questions ("Is organizational entropy inevitable as business grows?")
4. **Syntopical Reading**: Cross-book connections (linking contemporary philosophy to Bhagavad Gita)

**It shut down.** The core problem: users had to upload their own books, and DRM made that painful. The concept was right; the distribution was wrong.

**Relevance to Petrarca**: Kairos's four-level framework is directly applicable. Physical books have no DRM problem — the user holds the book. Petrarca's camera-based capture sidesteps the ebook distribution barrier entirely.

Sources: [A New Way to Read](https://every.to/source-code/a-new-way-to-read)

### Emdash — Open Source Concept Connections

Emdash is notable for its "Conceptual Cousins" feature: on-device AI analysis finds passages with similar ideas across different books and authors, "often from a different angle." Additional features:

- Semantic search (fuzzy idea matching, not just keyword)
- Dense concept rephrasing with metaphors
- Random discovery ("Roll the Dice") to surface forgotten highlights
- Import from Kindle, export to EPUB
- All analysis on-device for privacy

**Relevance to Petrarca**: "Conceptual Cousins" is exactly the "Connection Finder" Petrarca should build — linking book captures to articles already in the system using the existing Nomic embeddings infrastructure.

Sources: [Emdash](https://emdash.ai/), [GitHub](https://github.com/dmotz/emdash)

### Newer Entrants (2025-2026)

**Chapters** (chapters.chat): AI discussion partner for books. You upload EPUB, chat chapter-by-chapter. The AI *asks* tailored questions rather than waiting for you. Claims "active recall is proven to 2x long-term memory." Multiple AI personality modes (casual to analytical).

**Readever** (readever.app): Highlight text while reading, get immediate contextual AI responses. "Non-intrusive" design — AI is completely optional. All highlights and conversations saved for review.

**BookChat** (bookchat.studio): Upload PDF books, chat about characters, themes, plot. The AI remembers entire conversation and book context.

**Rebind** (rebind.ai): Expert commentary distributed into interactive conversations within an e-reader. Records 1:1 interviews with subject experts, then uses AI to deliver that commentary contextually. Reader notes personalize the ongoing conversation.

**Basmo**: Reading tracker with "ChatBook AI" — an AI chatbot that answers with information from the actual text. Also includes emotional tracking, voice recording, and photo scanning of book pages.

Sources: [Chapters](https://chapters.chat/), [Readever](https://www.readever.app/features/talk-to-books), [BookChat](https://www.bookchat.studio/), [Rebind](https://rebind.ai/), [Basmo](https://basmo.app/)

### Andrej Karpathy's reader3

Karpathy released reader3 (Nov 2025) — a lightweight EPUB reader that displays one chapter at a time for easy copy-paste to your favorite LLM. 1,576 GitHub stars in 48 hours. His workflow:

1. **Pass 1**: Manual reading of the chapter
2. **Pass 2**: Paste chapter into LLM, get summary and explanations
3. **Pass 3**: Q&A — ask about confusing passages

Reports it "dramatically improves understanding and retention" especially for unfamiliar domains or historical texts. Acknowledges the process is "clunky and back-and-forth."

**Relevance to Petrarca**: Karpathy's workflow for *digital* books is what Petrarca should offer for *physical* books — but with the advantage that captures are persistent and cumulative. You're not re-pasting each time; the system builds a growing context window from your photos and notes.

Sources: [reader3 GitHub](https://github.com/karpathy/reader3), [Workflow analysis](https://www.jermainebrown.org/posts/how-andrej-karpathy-reads-books-with-llms)

---

## 2. Vision Model + Book Page Processing

### Current Capabilities (2025)

All major vision models can extract text from book page photos:

| Model | Printed text accuracy | Handwriting | Complex layouts | Strengths |
|-------|----------------------|-------------|-----------------|-----------|
| GPT-4o | ~98% | 80-85% clear | Good | Contextual clue use for messy text |
| Claude 3.5+ | ~97% | Fair | Best | Maintains formatting, complex layouts |
| Gemini 2.5 | ~96% | Good for printed | Good | Multilingual, fast, cost-effective |

**Beyond OCR — what vision models understand from book pages**:
- **Layout parsing**: Headers, body text, footnotes, marginalia, page numbers
- **Multi-column detection**: Distinguishing columns, sidebars, captions
- **Structural elements**: Chapter titles, section breaks, numbered lists, block quotes
- **Visual elements**: Diagrams, charts, tables alongside text
- **Handwritten annotations**: Recognized at 80-85% for clear writing, lower for cursive

Sources: [LLMs vs OCR comparison](https://www.handwritingocr.com/blog/chatgpt-claude-and-ai-for-ocr), [Gemini vision API](https://ai.google.dev/gemini-api/docs/image-understanding), [Document understanding](https://ai.google.dev/gemini-api/docs/document-processing)

### Structured Extraction from Book Pages

Gemini 2.5 Flash is particularly relevant for Petrarca because:

1. **Already in the pipeline**: Petrarca uses `call_vision()` via Gemini for cover identification and TOC extraction
2. **Structured JSON output**: Can return typed schema-constrained JSON from vision input
3. **Cost**: Flash models are optimized for high-volume, low-latency use
4. **Layout understanding**: "Recognizes multi-column layouts, section headers, embedded charts, hierarchical bullet lists, footnotes, captions, tables"

**What Petrarca could extract from a book page photo** (beyond raw text):
- Identified key claims / assertions
- Distinction between author's argument vs. cited evidence
- Definitions of technical terms
- Whether the page is argument, evidence, example, summary, or transition
- Reading context: "This page is presenting the counterargument to the thesis from chapter 3"

Sources: [Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output), [Document processing](https://medium.com/google-cloud/gemini-2-5-flash-the-ai-backbone-for-smarter-document-processing-6b8f4a18135a)

### ColPali — Page-Level Visual Embeddings

ColPali (ICLR 2025) is a vision language model that generates embeddings directly from document page images — no OCR pipeline needed. It outperforms traditional text-based retrieval by understanding visual layout, tables, and figures alongside text.

**Relevance to Petrarca**: Could enable "find similar pages" across different books by embedding page photos directly. However, for Petrarca's use case, the existing Nomic text embeddings on extracted claims are probably more useful than page-level visual similarity.

Sources: [ColPali paper](https://arxiv.org/abs/2407.01449), [HuggingFace blog](https://huggingface.co/blog/manu/colpali)

### Handling Marginalia and Reader Annotations

Research on handwritten text recognition in margins (marginalia) shows:
- Detecting marginalia requires distinguishing printed from handwritten text
- R-CNN / Faster R-CNN networks can detect margin annotation regions
- Recognition uses attention-based sequence-to-sequence models
- Data augmentation and transfer learning help overcome training data scarcity

**For Petrarca**: Vision models can already detect and interpret underlines, highlights, and marginal notes in book page photos. A prompt like "Extract the printed text AND describe any handwritten annotations, underlines, or highlights on this page" would work with current Gemini/Claude vision capabilities. This is a differentiating feature: capture not just what the book says, but what the reader found important.

Sources: [Marginalia HTR](https://arxiv.org/abs/2303.05929), [Transkribus](https://www.transkribus.org/en/blog/whats-that-written-in-the-margin)

---

## 3. Voice Note -> Knowledge Transformation

### The AudioPen Model

AudioPen demonstrates the core loop: speak freely, get structured text. Key features:
- Transcribes via Whisper API, then AI rewrites into structured paragraphs
- "Write like me" feature analyzes your writing style and mimics it
- Removes filler words, structures rambling speech
- Output in your preferred language regardless of input language

**What AudioPen lacks**: It doesn't know what you're talking *about*. It has no context about the book you're reading, the chapter you're in, or the ideas you've already captured.

Sources: [AudioPen](https://www.audiopen.ai/)

### What Petrarca Could Do Differently

Petrarca's voice notes have context that generic voice tools don't:
- **Book context**: Title, author, current chapter, page number
- **Capture history**: All previous photos and notes from this book
- **Article knowledge**: 4,500+ claims from 239 articles already in the system

A voice note processed with this context could be transformed into:

1. **Atomic claims**: "The reader noted that X contradicts the author's earlier claim about Y"
2. **Questions**: "The reader wonders whether Z applies to the Italian case as well"
3. **Connections**: "This observation relates to article [A] which claims..."
4. **Reflections**: "The reader found the argument about X unconvincing because..."
5. **Reading reactions**: Distinguish between "I agree/disagree" vs "this is new to me" vs "I already knew this"

### Voice-to-Knowledge Pipeline (Proposed)

```
Voice recording
  -> Soniox transcription (existing infrastructure)
    -> LLM processing with context:
       - Book title, author, chapter
       - Previous captures from this session
       - Reader's capture history for this book
       -> Structured output:
          {
            raw_transcript: string,
            structured_text: string,        // cleaned-up version
            claims: string[],               // atomic factual claims
            questions: string[],            // questions raised
            connections: string[],          // links to known concepts
            reaction_type: 'agreement' | 'disagreement' | 'surprise' | 'confusion' | 'connection',
            topics: string[]
          }
```

Sources: [AudioPen](https://www.audiopen.ai/), [Soniox](https://soniox.com/), [Voice-LLM Trends](https://www.turing.com/resources/voice-llm-trends)

---

## 4. LLM-Generated Questions and Reading Prompts

### Research Findings on Quality

A 2024 study on LLM question generation across Bloom's taxonomy found:
- **78% of generated questions rated "High Quality"** by human raters
- **65.56% matched the intended cognitive skill level**
- Best results with **Chain-of-Thought prompting + skill definitions + exemplars**
- LLMs excel at lower-order questions (Remember, Understand) but struggle at the highest level (Create)
- **Intermediate prompt complexity works best** — overly detailed instructions paradoxically reduce performance
- Human expertise remains essential for quality assurance of generated questions

Sources: [Bloom's taxonomy study](https://arxiv.org/abs/2408.04394), [School-level questions](https://www.sciencedirect.com/science/article/pii/S2666920X25000104)

### Elaborative Interrogation — The Evidence

Elaborative interrogation ("why?" questions) is one of the most evidence-backed learning strategies:
- Students asked "Why?" every ~150 words showed **significantly better comprehension and lasting recall**
- Students need not generate correct responses — **the process of generating an explanation** forges deeper links
- Self-generated elaborations outperform experimenter-provided ones
- But: only effective in "very specific situations" — works best when learners have some prior knowledge to connect to

**This is directly applicable to Petrarca's capture flow**: After a user photographs a page, the system could generate 1-2 "why" questions about the captured content. Not quiz questions, but prompts for reflection.

Sources: [Elaborative interrogation study](https://www.tandfonline.com/doi/full/10.1080/02702711.2025.2482627), [Dunlosky learning strategies](https://www.whz.de/fileadmin/lehre/hochschuldidaktik/docs/dunloskiimprovingstudentlearning.pdf)

### Proposed Question Types for Petrarca

Based on the research, four question types would serve Petrarca readers:

| Type | Example | Purpose |
|------|---------|---------|
| **Elaborative interrogation** | "Why would the author argue X when most historians say Y?" | Deepens understanding through explanation |
| **Connection prompt** | "How does this relate to [article claim] you read last week about Z?" | Cross-source synthesis |
| **Prediction prompt** | "Based on this chapter's argument, what do you think the author will argue about W?" | Active reading engagement |
| **Application prompt** | "Can you think of a modern example of the pattern the author describes?" | Transfer to personal knowledge |

---

## 5. Synthesis from Captures

### What Could an LLM Synthesize From a Book's Captures?

Given Petrarca's three capture types (page photos, voice notes, text notes), here are concrete synthesis possibilities:

### 5.1 Personal Reading Summary

Not a generic book summary — a summary of *what the reader engaged with*:

**Input**: All captures from a book (20 page photos, 8 voice notes, 5 text notes)
**Output**:
```
"Over 3 weeks of reading 'The Inheritance of Rome', you captured 20 pages
across chapters 4, 7, 8, and 12. Your voice notes focused heavily on the
economic arguments about Mediterranean trade decline (7 of 8 notes). You
photographed three maps and two data tables. Your text notes suggest
disagreement with the author's thesis about Carolingian renewal — you
wrote 'but what about Byzantium?' twice.

Your reading concentrated on: trade networks (45%), political legitimacy
(30%), religious institutions (25%). You skipped the chapters on
Germanic successor kingdoms entirely."
```

This is fundamentally different from what NotebookLM or Kindle's "Ask This Book" provides: it reflects the reader's actual attention and engagement.

### 5.2 Cross-Session Synthesis — "How Your Understanding Evolved"

**Input**: Captures from the same book over time, with timestamps
**Output**:
```
"Week 1: You focused on the basic chronology — most captures were
factual (dates, names, succession of rulers). Your voice notes were
mostly summaries.

Week 2: A shift — your captures became more analytical. You started
questioning the author's periodization. Voice note from Feb 12:
'I think Wickham is wrong about the 7th century being the turning
point — the real break seems earlier.'

Week 3: Cross-referencing intensified. You photographed 3 pages
that referenced Pirenne's thesis and made 2 voice notes connecting
this to your earlier reading of McCormick."
```

### 5.3 Argument Extraction

**Input**: Sequential page photos from a chapter
**Output**:
```json
{
  "chapter": "Chapter 7: The Mediterranean Economy",
  "main_thesis": "Mediterranean long-distance trade did not collapse suddenly but declined gradually through the 6th-7th centuries",
  "supporting_arguments": [
    "Archaeological evidence from African Red Slip pottery distribution",
    "Tax records showing continued grain shipments to Constantinople",
    "But NOT to Rome after the 530s"
  ],
  "counterarguments_addressed": [
    "Pirenne's claim of sudden Islamic disruption"
  ],
  "evidence_types": ["archaeological", "documentary", "numismatic"],
  "reader_annotations": [
    "Underlined passage about pottery distribution",
    "Marginal note: 'compare with McCormick chapter 3'"
  ]
}
```

### 5.4 Weekly Book Digest

A periodic synthesis of recent reading across all books:

```
"This Week's Reading (Mar 8-15):

THE INHERITANCE OF ROME (Wickham)
- 6 new captures from Chapter 8
- Key theme: transition from Roman to Carolingian governance
- You questioned whether the "Pirenne thesis" holds for the western Mediterranean

STORIA DELLA LETTERATURA ITALIANA (De Sanctis)
- 3 page photos from the Dante section
- Captured De Sanctis's claim that Dante's greatness lies in making
  the universal particular

CONNECTIONS BETWEEN YOUR BOOKS:
Both Wickham and De Sanctis are describing the same period (8th-10th
centuries) from different angles — political/economic vs. cultural/literary.
Your capture of Wickham p.234 about Carolingian court culture connects
directly to De Sanctis's discussion of pre-Dante literary traditions.

REFLECTION PROMPTS:
- How does the economic decline Wickham describes affect the literary
  culture De Sanctis celebrates?
- You've now captured 12 pages about the Pirenne thesis across 2 books.
  What's your current position?"
```

---

## 6. Concrete Experiments to Build

### Experiment 1: Smart Page Photo Processing (Low effort, high value)

**What**: Enhance the existing `/book/ocr-page` endpoint to return richer structured output.

**Current state**: The endpoint returns `{ text, detected_page_number, extracted_ideas, topics }`.

**Enhanced output**:
```json
{
  "text": "...",
  "detected_page_number": 234,
  "page_type": "argument",          // argument | evidence | example | summary | transition | map | table
  "key_claims": [
    { "text": "...", "type": "main_claim" | "supporting" | "counterargument" }
  ],
  "definitions": [
    { "term": "...", "definition": "..." }
  ],
  "reader_annotations": {
    "highlights": ["..."],
    "marginal_notes": ["..."],
    "underlined_passages": ["..."]
  },
  "elaborative_question": "Why might the author argue X when...",
  "connection_to_previous": "This relates to your capture from p.198 about..."
}
```

**Implementation**: Modify the Gemini vision prompt in `research-server.py` to request structured JSON with these additional fields. Requires passing previous captures as context.

### Experiment 2: Voice-to-Claims Pipeline (Medium effort, high value)

**What**: Process voice notes about reading into structured knowledge atoms.

**Current state**: Voice notes are transcribed and stored with `extracted_ideas` and `topics`, but ideas are just strings.

**Enhanced pipeline**:
1. Transcribe via Soniox (existing)
2. LLM processes transcript with book context (title, chapter, recent captures)
3. Output structured claims, questions, and connections
4. Claims get embedded via Nomic (existing infrastructure)
5. Cross-reference against article claims in `knowledge_index.json`

**Key prompt**: "You are processing a reader's voice note about [Book Title] by [Author], Chapter [N]. The reader has previously captured: [list of recent captures]. Transform this voice note into: (1) factual claims the reader is noting, (2) questions the reader is raising, (3) agreements or disagreements with the author, (4) connections to other things the reader knows."

### Experiment 3: "Story So Far" / Context Restoration (Medium effort, high value)

**What**: When the reader opens a book they haven't read in days, generate a briefing of where they left off.

**Input**: All captures for the book, sorted chronologically, plus reading position.

**Output**: A 3-paragraph summary: (1) What the book is about and what you've read so far, (2) What you were focusing on in your last reading session, (3) Key open questions or threads from your notes.

**Implementation**: Single LLM call with all captures as context. Display as a modal or card when opening a book that hasn't been interacted with in >3 days.

### Experiment 4: Connection Finder — Book Captures x Article Claims (High effort, very high value)

**What**: When a book capture is processed, automatically find related claims from Petrarca's 4,500+ article claims.

**Implementation**:
1. Extract claims from page photo or voice note
2. Embed claims using Nomic (same model as article claims)
3. Compute cosine similarity against article claim embeddings
4. Surface top 3-5 connections with similarity > 0.68 (the existing EXTENDS threshold)

**Display**: In the book detail view, show connected articles beneath each capture:
```
Your capture from p.234: "Mediterranean trade declined gradually..."
  -> Related: "New evidence from Red Sea ports suggests trade continued
     longer than previously thought" (Article: Red Sea Trade Networks, 0.74)
  -> Related: "Pirenne's thesis has been revised but not refuted"
     (Article: Revisiting the Pirenne Thesis, 0.71)
```

This leverages Petrarca's existing embedding infrastructure and directly fulfills the "knowledge-aware" promise.

### Experiment 5: Elaborative Question Generation (Low effort, medium value)

**What**: After each page capture, generate 1-2 "why" questions for the reader.

**Implementation**: Add to the page OCR response. The prompt includes: the page text, the book context, and the instruction "Generate 1-2 elaborative interrogation questions — 'why' questions that would help the reader think more deeply about this content. Do not generate quiz questions; generate reflection prompts."

**Display**: Show as a subtle prompt below the captured page, dismissible. Track whether the user engages (via logEvent).

### Experiment 6: Weekly Book Digest (Medium effort, high value)

**What**: Weekly synthesis of all book captures.

**Implementation**:
1. Cron job (or manual trigger) collects all captures from the past 7 days
2. Groups by book
3. LLM generates:
   - Per-book summary of what was captured and what themes emerged
   - Cross-book connections (if reading multiple books)
   - Connections to articles in the feed
   - 2-3 reflection prompts
4. Delivered as a push notification or "digest" card in the feed

### Experiment 7: Reading Companion Chat (High effort, very high value)

**What**: Chat with the book informed by your captures.

**Current state**: Petrarca has `SynthesisChat.tsx` for article syntheses and a research server chat endpoint.

**Book companion chat context**:
- All captures for the book (OCR text, voice transcripts, text notes)
- Book metadata (title, author, chapters, current position)
- Article claims that relate to the book's topics
- The reader's capture patterns (what they focused on)

**Key design principle** (from Kindle's experience): Only discuss content the reader has already captured or read. Don't spoil later chapters.

**Example interactions**:
- "What has the author argued so far about X?" (answered from captured pages only)
- "How does this compare to what I read in [Article]?" (cross-referencing captures with article claims)
- "I'm confused about the relationship between Y and Z" (explanation grounded in captured pages)

### Experiment 8: Concept Index Builder (High effort, high value)

**What**: Automatically build a personal concept index from book captures.

**Implementation**:
1. As page photos are processed, extract named entities and key concepts
2. Build a growing index: concept -> list of (book, page, context)
3. When a concept appears in multiple books, flag the cross-reference
4. Embed concepts and find clusters

**Output**: A personal index that grows over time:
```
"Mediterranean trade"
  - Wickham, The Inheritance of Rome, pp. 189, 198, 234, 267
  - McCormick, Origins of the European Economy, pp. 45, 89
  - [Article] "Red Sea Trade Networks" (feed)

  Your notes: "Wickham sees gradual decline; McCormick argues for
  continued connectivity via different routes"
```

This directly mirrors what the existing `knowledge_index.json` does for articles, extended to books.

---

## 7. Priority Ranking for Petrarca

Based on effort, value, and alignment with existing infrastructure:

| Priority | Experiment | Effort | Value | Why |
|----------|-----------|--------|-------|-----|
| 1 | Smart Page Photo Processing | Low | High | Enhances existing endpoint, immediate UX improvement |
| 2 | Elaborative Question Generation | Low | Medium | Piggybacked on page processing, evidence-backed learning strategy |
| 3 | "Story So Far" / Context Restoration | Medium | High | Solves real problem (abandoned books), single LLM call |
| 4 | Voice-to-Claims Pipeline | Medium | High | Leverages Soniox + Nomic infrastructure, creates structured data |
| 5 | Connection Finder | High | Very High | The unique Petrarca differentiator — books x articles knowledge web |
| 6 | Weekly Book Digest | Medium | High | Periodic synthesis drives re-engagement |
| 7 | Reading Companion Chat | High | Very High | Chat infrastructure exists, needs book-specific context |
| 8 | Concept Index Builder | High | High | Long-term value, complex to build well |

---

## 8. Key Insights and Recommendations

### What the landscape tells us

1. **Everyone is building "chat with book" — nobody is building "chat with YOUR reading of the book."** NotebookLM, Kindle, BookChat, Readever all treat the full text as the knowledge base. Petrarca's captures represent the reader's *attention* — what they chose to photograph, voice-note, or type. This is a fundamentally different signal.

2. **The DRM/distribution problem killed Kairos.** Physical book capture via camera sidesteps this entirely. No uploads, no file formats, no licensing.

3. **Cross-source connections are the moat.** Emdash's "Conceptual Cousins" across books and Readwise's "chat with your library" both point to the same insight: value compounds when ideas from different sources connect. Petrarca already has the embedding infrastructure for this.

4. **Elaborative interrogation works.** The research evidence is strong that "why" questions deepen understanding. LLMs can generate these at 78% high quality. This is low-hanging fruit.

5. **Vision models are good enough for book pages.** 96-98% accuracy on printed text, with layout understanding. The existing Gemini integration is sufficient — the gap is in what the prompt asks for, not the model's capability.

6. **Voice is underexploited.** AudioPen proves voice-to-structured-text works. But no tool processes voice notes *about reading* with book context. Petrarca already has Soniox integration and voice capture flow.

### What Petrarca should NOT build

- **Generic book summaries**: NotebookLM and dozens of tools already do this. Petrarca's value is in *personal* reading engagement.
- **Full ebook reader**: reader3, Kindle, and the ebook ecosystem own this. Physical book companion is the niche.
- **Social features**: No book clubs, no sharing reading progress. Personal tool for one power user.
- **Audio narration / text-to-speech**: Speechify, ElevenReader own this space. Not relevant to physical book companion.

### The unique Petrarca angle

No existing tool combines:
1. Camera-based capture from physical books
2. Structured knowledge extraction (claims, concepts, arguments)
3. Cross-referencing with a personal article knowledge base
4. Elaborative question generation grounded in the reader's captures
5. Temporal synthesis showing how understanding evolves

This is the product to build.

---

## Sources

### AI Reading Companions
- [Google NotebookLM](https://notebooklm.google/)
- [NotebookLM student features](https://blog.google/innovation-and-ai/models-and-research/google-labs/notebooklm-student-features/)
- [NotebookLM 2025 updates](https://automatetodominate.ai/blog/google-notebooklm-2025-updates-complete-guide)
- [Kindle "Ask This Book"](https://writerbeware.blog/2025/12/12/kindles-new-gen-ai-powered-ask-this-book-feature-raises-rights-concerns/)
- [Kindle 2026 updates](https://www.androidpolice.com/amazon-kindle-new-ai-catch-up-tools/)
- [Readwise Ghostreader](https://docs.readwise.io/reader/guides/ghostreader/overview)
- [Readwise spaced repetition](https://blog.readwise.io/hack-your-brain-with-spaced-repetition-and-active-recall/)
- [Kairos / Every.to](https://every.to/source-code/a-new-way-to-read)
- [Emdash](https://emdash.ai/)
- [Emdash GitHub](https://github.com/dmotz/emdash)
- [Chapters](https://chapters.chat/)
- [Readever](https://www.readever.app/features/talk-to-books)
- [BookChat](https://www.bookchat.studio/)
- [Rebind](https://rebind.ai/)
- [Basmo](https://basmo.app/)
- [Karpathy reader3](https://github.com/karpathy/reader3)
- [Karpathy workflow](https://www.jermainebrown.org/posts/how-andrej-karpathy-reads-books-with-llms)

### Vision Models & Document Understanding
- [LLMs for OCR comparison](https://www.handwritingocr.com/blog/chatgpt-claude-and-ai-for-ocr)
- [Gemini vision API](https://ai.google.dev/gemini-api/docs/image-understanding)
- [Gemini document processing](https://ai.google.dev/gemini-api/docs/document-processing)
- [Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output)
- [Gemini 2.5 Flash document processing](https://medium.com/google-cloud/gemini-2-5-flash-the-ai-backbone-for-smarter-document-processing-6b8f4a18135a)
- [ColPali (ICLR 2025)](https://arxiv.org/abs/2407.01449)
- [Marginalia recognition](https://arxiv.org/abs/2303.05929)
- [LLMs vs OCR (2026)](https://www.vellum.ai/blog/document-data-extraction-llms-vs-ocrs)
- [SmolDocling](https://openaccess.thecvf.com/content/ICCV2025/papers/Nassar_SmolDocling_An_ultra-compact_vision-language_model_for_end-to-end_multi-modal_document_conversion_ICCV_2025_paper.pdf)

### Voice Processing
- [AudioPen](https://www.audiopen.ai/)
- [Soniox](https://soniox.com/)
- [Voice-LLM Trends 2025](https://www.turing.com/resources/voice-llm-trends)
- [Voxtral](https://www.turing.com/resources/voice-llm-trends)

### Question Generation & Learning
- [Bloom's taxonomy question generation](https://arxiv.org/abs/2408.04394)
- [Elaborative interrogation study](https://www.tandfonline.com/doi/full/10.1080/02702711.2025.2482627)
- [Dunlosky learning strategies](https://www.whz.de/fileadmin/lehre/hochschuldidaktik/docs/dunloskiimprovingstudentlearning.pdf)
- [AI reading comprehension questions (PIRLS)](https://www.tandfonline.com/doi/full/10.1080/2331186X.2025.2458653)
- [BloomLLM](https://link.springer.com/chapter/10.1007/978-3-031-72312-4_11)

### Knowledge Management & Synthesis
- [Personal Knowledge Graphs](https://dasroot.net/posts/2025/12/personal-knowledge-graphs-notes-insights/)
- [Glasp AI summary](https://glasp.co/ai-summary)
- [Mem.ai](https://get.mem.ai/)
- [LLM Knowledge Graph construction](https://arxiv.org/html/2510.20345v1)

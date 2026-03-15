# Physical Book → Digital Bridge: Products, Prototypes, and Research (2023–2026)

**Date**: March 15, 2026
**Purpose**: Comprehensive landscape scan of products, academic prototypes, and community discussions around bridging physical book reading with digital note-taking, knowledge management, and AI-assisted comprehension.

---

## 1. Existing Physical Book → Digital Capture Products

### Tier 1: Highlight Capture (Photo OCR)

**Readwise** — The market leader for digital highlight management. For physical books, users photograph highlighted pages with the mobile app, then use selection handles to choose passages. OCR extracts text, which users can edit before saving. Recent improvements (July 2025): proper camera focus on iOS 18.5, standard lens instead of wide-angle for better low-light captures, multi-page highlight support. Readwise's strength is its *aggregation* — it pulls from Kindle, Apple Books, Kobo, Instapaper, physical book OCR, and more into one unified system, with export to Obsidian, Notion, Logseq, etc.
- https://docs.readwise.io/readwise/docs/importing-highlights/ocr

**Highlighted** (by Damir Stuhec) — Apple "App of the Day". Focused exclusively on physical book quote capture. ISBN scanning for book identification, best-in-class text recognition with smart sentence/paragraph detection, page number detection, bulk drag & drop highlighting on iPad. Exports to Markdown, TXT, PDF. Described as "extremely clean" with no feature bloat. Free, no hidden costs.
- https://apps.apple.com/us/app/highlighted-book-highlights/id1480216009
- https://ebookfriendly.com/highlighted-book-scanner-app-ipad-iphone/

**Screvi** — Newer entrant positioning as Readwise alternative. Key differentiator: *AI-powered extraction of highlighted/underlined text from photos*, not just plain OCR. Uses Google Gemini to identify highlighted passages specifically, handling messy handwriting and complex layouts. Also includes semantic search across highlights (meaning-based, not keyword), spaced repetition via SM-2 algorithm, and multi-source aggregation (Kindle, Kobo, Apple Books, PDFs, web, YouTube, physical books).
- https://screvi.com/

**Excerpt** — Another iOS app for book highlighting via camera, available on App Store.
- https://apps.apple.com/us/app/excerpt-the-book-highlighter/id1447907126

### Tier 2: Reading Trackers with Capture Features

**Basmo** — Reading tracker with surprisingly deep capture features: OCR book scanning in dozens of languages, voice notepad (speech-to-text dictation), emotional tracking during reading, ChatBook AI assistant for discussing book content, reading timer, page/percent/minute logging, Kindle and Notion sync.
- https://basmo.app/

**Bookly** — Reading habit tracker focused on motivation and daily reading goals. Less capture-oriented, more gamification/tracking.
- https://getbookly.com/

**Book Tracker (BookTrack)** — Tracks reading progress (Read/Reading/TBR), includes camera-based quote capture with OCR, detailed progress logging by pages/time/percentage.
- https://booktrack.app/

**Bookmory** — Reading timer + progress tracking, OCR text extraction from photos, reading statistics.
- https://play.google.com/store/apps/details?id=net.tonysoft.bookmory

### Tier 3: Deep Annotation (Primarily Digital, Some Physical Import)

**MarginNote** — Powerful iPad annotation tool for PDFs with mind-mapping and outlining. OCR Pro add-on ($1/month) for scanned documents. Primarily designed for digital documents, not physical book workflows. Exports to Anki, OmniOutliner, various mind map formats.

**LiquidText** — iPad app for PDF annotation with unique "workspace" metaphor where you can drag and pinch document excerpts. Can import photos/images but primarily designed for digital PDFs. Integrates with Zotero/Mendeley.

**Flexcil** — PDF reader + note-taking with gesture-based annotation. Can import photos but core workflow is digital documents.

### Assessment
The capture market is **fragmented by use case**: Readwise for aggregation + review, Highlighted for pure capture quality, Screvi for AI-enhanced extraction, Basmo for integrated tracking + capture. No single product does it all well. The biggest gap: **none of these products understand what you captured in context** — they store text snippets but don't connect them to your broader knowledge or reading patterns.

---

## 2. OCR and Page Photo Processing

### Vision Models vs. Traditional OCR (2025–2026)

The landscape has shifted dramatically. Vision Language Models (VLMs) now compete directly with dedicated OCR:

**Accuracy benchmarks** (OmniAI, Reducto, IntuitionLabs):
- Qwen 2.5 VL 72B: ~75% accuracy (matching GPT-4o)
- GPT-4.5 Preview: Top score overall
- Gemini 2.0 Flash: 88.49% on Mistral's internal dataset
- Mistral OCR: 72.2% (dedicated OCR model, ironically below VLMs)
- Claude: Highest accuracy score most frequently across domains

**Cost comparison** (per 10,000 pages):
- Gemini Flash 2.0: ~$1.67
- GPT-4 Vision: ~$50–100
- Mistral OCR 3: $2 (or $1 with batch API)
- Traditional OCR (Tesseract etc.): Free but lower accuracy

**Key insight**: VLMs *understand* documents, not just recognize characters. They can reason about layout, structure, and intent. Traditional OCR extracts characters but loses context — flowcharts become random word lists, tables become jumbled text, handwritten annotations disappear entirely.

**However**: VLMs have weaknesses on *formatting details*. Strikethroughs, underlines, specific font colors are often ignored by models like Gemini that focus on content over style. When formatting is critical (e.g., distinguishing highlighted vs. non-highlighted text), specialized models or multi-pass approaches work better.

- https://getomni.ai/blog/ocr-benchmark
- https://reducto.ai/blog/lvm-ocr-accuracy-mistral-gemini
- https://www.vellum.ai/blog/document-data-extraction-llms-vs-ocrs

### Mistral OCR (Specialist Model)

Mistral OCR 3 (December 2025) is a dedicated OCR model achieving 74% win rate over its predecessor. Handles interleaved imagery, mathematical expressions, tables, LaTeX, thousands of scripts and languages. $2/1000 pages. Not open source, but may come to Hugging Face.
- https://mistral.ai/news/mistral-ocr-3

### Book Page Challenges: Curvature, Lighting, Fingers

**Dewarping algorithms** use two main approaches for phone photos:
- Optical flow (OF) and structure from motion (SfM) — multi-frame substantially better than single-frame
- CNN-based rectangle detection for edge detection and perspective correction
- 3D shape reconstruction from shading information
- ToF (time-of-flight) sensor integration on newer phones

**vFlat Scan** — The standout app for book page scanning specifically. Automatic book page flattening, two-page spread capture in one click with automatic page separation, auto border detection, free OCR. Also: AI removal of handwritten scribbles to get clean text. Limitation: 100-page OCR cap without purchase.
- https://www.vflat.com/en
- https://apps.apple.com/us/app/vflat-scan-pdf-scanner-ocr/id1540238220

### Extracting Annotations (Underlines, Marginal Notes, Post-its)

**Current state**: GPT-4V/Claude can recognize underlined words and infer handwriting, but accuracy decreases with unusual formatting, handwritten notes, non-Latin scripts, marginalia, and overlays. The approach of using ChatGPT-4o to "extract colored highlights" from page photos works but is not reliable enough for production without human verification.

**Transkribus** — Specialized in historical document transcription (handwritten text across 100+ languages and centuries of scripts). Academic-grade accuracy but not designed for modern book annotation workflows.
- https://www.transkribus.org/

**Practical gap**: No product reliably separates *your annotations* (underlines, margin notes, post-its) from *the book's text* in a single photo. This remains a multi-step manual process.

### Petrarca Opportunity
Petrarca already uses Gemini Vision for book identification. The same `call_vision()` endpoint could be extended to:
1. Extract highlighted/underlined text from page photos (prompt Gemini to identify visual markers)
2. Separate margin notes from printed text
3. Detect page numbers for automatic progress tracking
4. Process sequences of page photos as a reading session with context

---

## 3. Voice-First Book Interaction

### Current Products

**Basmo Voice Notepad** — Speech-to-text dictation integrated into reading tracker. Dictate thoughts while reading, transcribed and attached to the current book.

**Otter.ai** — General voice transcription tool. Not designed for reading, but can be used: record thoughts while reading, highlight key moments, auto-transcribe. Free basic plan. The mobile app is described as "best for recording your own thoughts."
- https://otter.ai/

**Speechify** — Text-to-speech with "Talk to Speechify AI" feature where you can ask questions about content. Primarily for *listening to* text, not *talking about* reading.
- https://speechify.com/

### AI-Powered "Discuss Your Reading"

**NotebookLM Audio Overviews** — The most compelling "book club of one" product. Upload your highlights/notes/sources and NotebookLM generates a podcast-style conversation between two AI hosts discussing your material. As of September 2025: supports 80+ languages, four formats (Deep Dive, Brief, Critique, Debate), interactive mode where you can "join" the conversation, video overviews with visual slides. This is the closest thing to having someone to discuss your reading with.
- https://support.google.com/notebooklm/answer/16212820
- https://blog.google/technology/ai/notebooklm-audio-overviews/

**NotebookLM + Physical Book Workflow**: Upload your highlights (from Readwise/Screvi/manual) → generate audio discussion → listen while commuting or exercising → return to book with new perspectives.

### What's Missing

No product lets you **stream-of-consciousness talk about a book while reading it** and then have AI organize those thoughts into structured notes. The workflow is always: read → stop → type/dictate → organize. A truly voice-first reading companion would:
- Listen continuously while you read and react verbally
- Distinguish between "note to self" and "question about this passage"
- Connect your verbal reactions to specific pages/chapters
- Synthesize a session's worth of verbal notes into structured insights

### Petrarca Opportunity
Petrarca already has voice capture infrastructure (Soniox STT). The gap is: voice notes aren't yet connected to specific pages/passages, and there's no AI synthesis of voice notes into structured reading insights. The NotebookLM approach (upload notes → generate discussion) could be replicated with Gemini.

---

## 4. Reading Progress Tracking for Physical Books

### How Existing Apps Track Progress

**Manual page entry** — The universal approach. Every app (Goodreads, StoryGraph, Basmo, Bookly, BookTrack, Literal) requires you to manually type in your current page number.

**Goodreads** — Page number or percentage updates. Social features (friends' reading, reviews). Owned by Amazon; no OCR or smart capture.

**StoryGraph** — Page tracking with private notes alongside progress updates. Mood-based recommendations. "Pace" stats showing reading speed. Key limitation vs Goodreads: no automatic sync from reading devices — always manual.
- https://thestorygraph.com/

**Literal** — Minimalist, modern Goodreads alternative. Quote capture, open API, bookclub features. Growing community but limited physical book tools.
- https://www.producthunt.com/products/literal-2/reviews

**BookWyrm** — Federated, open-source (ActivityPub). Self-hostable. Reading status updates, reviews, decentralized book database. For privacy-conscious readers who want to own their data.
- https://joinbookwyrm.com/

**BookPace (NFC)** — The most innovative approach: attach an NFC tag to your physical book, tap iPhone to toggle a reading timer automatically. One-time setup per book. Tracks reading time with heatmaps by day/week/month/year. iCloud sync. Distraction blocking during reading sessions. Showcased on Hacker News (November 2025).
- https://www.bookpace.app/
- https://news.ycombinator.com/item?id=45842067

### Automatic Progress Tracking — The Holy Grail

No app currently infers reading progress from *content*. Potential approaches:
- **Page number OCR**: Extract page numbers from photos to auto-log progress
- **Chapter header detection**: Recognize chapter titles in photos → map to TOC → compute percentage
- **Reading session inference**: Multiple page photos in a sitting → estimate pages read

### Petrarca Opportunity
Petrarca's book companion already has TOC lookup (via Gemini + search) and chapter tracking. Adding page number extraction from capture photos would enable automatic progress logging — a feature no competitor offers.

---

## 5. The "Book Club of One" Concept

### Research: Why Discussion Aids Comprehension

Academic research consistently shows that discussing reading improves comprehension:
- Book clubs facilitate "deep reading" — reading for long-term retention at a perspective-transforming level
- Social interaction about reading is a key motivating factor and *directly improves reading comprehension*
- Peer explanations and shared insights improve understanding; exchange of perspectives strengthens emotional engagement
- Students in book clubs increased their independent reading at home
- Discussion promotes insight and empathy through "collective self-reflection"
- Online forums help, but in-person discussion is more effective — suggesting *real-time interaction* matters

Sources:
- https://files.eric.ed.gov/fulltext/EJ1171691.pdf
- https://pmc.ncbi.nlm.nih.gov/articles/PMC8263384/
- https://readingladies.com/2022/05/27/track-your-reading-goodreads-or-story-graph-letstalkbookish-letsdiscuss2022/

### Current AI "Book Club" Products

**Fable** — Social reading app with discussion prompts embedded inside ebooks. Members respond to prompts and annotate with highlights, notes, tabs, comments, reactions. Physical book and audiobook users can download discussion prompts separately. However: Fable disabled its AI features in 2025 after reports of harmful language, suggesting their AI discussion generation was not mature.
- https://fable.co/
- https://bookriot.com/fable-book-club-app-review/

**NotebookLM** — Best current option for solo "discussion." Upload your notes, get an AI-generated conversation you can join interactively. Four discussion formats: Deep Dive, Brief, Critique, Debate.

**Loxie** — Retention app designed for book readers. Uses spaced repetition (SM-2 algorithm) with auto-generated questions. Three difficulty levels: basic recall → application → synthesis. Pre-built content for popular nonfiction. Daily Drills resurface material at optimal intervals. $59.99/year for Pro.
- https://loxie.app/

**Basmo ChatBook** — AI chatbot within reading tracker that answers questions with "actual information from the book."

**General AI assistants** (Claude, ChatGPT) — Increasingly used as reading companions. Claude excels at "in-depth discussion and understanding tone." Users prompt for discussion questions, thematic analysis, character exploration, connection to other books. The limitation: no persistent context of your reading history or notes.

### What AI Can Replicate (and What It Can't)

**Can replicate**: Generating discussion questions, identifying themes, connecting ideas across passages, Socratic questioning, summarizing arguments, providing historical/cultural context.

**Cannot replicate**: The social accountability of a book club, the surprise of someone else's perspective, the emotional bond of shared reading, the motivation of a reading commitment to others.

### Petrarca Opportunity
Petrarca's inline chat (SynthesisChat.tsx) already enables AI discussion about syntheses. Extending this to physical books — where the AI has access to your captures, progress, and the book's TOC/content — could create a genuine "book club of one" that responds to your specific notes and questions rather than generic prompts.

---

## 6. Innovative Physical-Digital Bridges

### NFC Tags

**BookPace** — Consumer-ready NFC-to-timer product. Simple, focused, works well for reading time tracking.
- https://www.bookpace.app/

**NFC in libraries** — Some libraries tag books with NFC for checkout, letting students tap campus cards against bookmark tags. When phones approach the NFC tag, they access related learning resources (ebook versions, author lecture videos, related articles).
- https://www.rfidlabel.com/an-introductory-guide-to-nfc-tags-and-book-systems/

### Smart Bookmarks

**Mark ($129)** — The most ambitious (and controversial) product. A physical bookmark with a small screen and rotary knob. You manually set your page position; the device generates AI summaries of what you've read, highlights themes and quotes, provides statistics. Received brutal HN feedback ("reads like an Onion skit mocking the tech industry"). The product tries to do too much in hardware when a phone app could do it better.
- https://mark.engineering/
- https://news.ycombinator.com/item?id=43193727

**Magic Bookmark (University of Surrey, 2022)** — Academic prototype. A flexible strip with embedded optical sensors that reads an almost-invisible barcode printed along page margins near the spine. Automatically detects which page is open. Uses special off-white ink from Printcolor that is invisible to humans but detectable by sensors. Triggers digital content access by simply placing the bookmark on a page. Elegant concept but requires modified books (barcodes printed in margins), limiting practical adoption.
- https://advanced.onlinelibrary.wiley.com/doi/full/10.1002/aisy.202100138
- https://www.surrey.ac.uk/news/surrey-researchers-breathe-new-life-paper-books-magic-bookmark

### QR Codes in Books

Publishers increasingly embed QR codes linking to supplementary materials, author notes, research sources, and interactive content. Dynamic QR codes allow updating linked content without modifying the physical book. Research (Frontiers in Education, 2025) found QR-supported cooperative learning produced η² = 0.89 effect size — among the strongest outcomes in educational technology research.
- https://scanova.io/blog/qr-codes-books-author-publisher/

### AR and Augmented Paper

**Augmented Library (2024)** — HMD-based AR prototype for libraries: color-coded user groups, virtual tags, data-driven augmented bookshelves for discovery, interactive reviews.
- https://arxiv.org/html/2408.06107v1

**"Phygital" textbooks (Frontiers in Education, 2025)** — Research on smartphone-based textbook companions in Indian classrooms. Examines how students engage with printed textbooks augmented by phone apps. Key finding: "multi-device and cross-media reading contexts through augmented reality systems enable learner interactions with print and digital learning material."
- https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2025.1660133/full

**Market reality**: Despite improved image recognition and AR technology, smart paper solutions haven't achieved commercial success because *scanning with a separate camera/phone compromises the reading experience*. The friction of picking up your phone to scan a page breaks the flow state that physical reading provides.

### E-Ink Devices

**reMarkable** — Best for minimalists. Distraction-free writing/reading. Limited export.
**Supernote** — Best for note-takers. Wacom EMR pen, ceramic nibs, note linking.
**Onyx Boox** — Most versatile. Full Android, Google Play, printing support.

These devices bridge physical-feeling reading/writing with digital storage, but they're *replacements* for physical books, not *companions* to them.

### The Reverse Bridge: Digital → Physical

**"Turn your read-later folder into a physical book"** — A Hacker News Show HN project addressing screen fatigue by printing saved articles as physical books. Reflects the desire for physical reading even among digital-native readers.
- https://news.ycombinator.com/item?id=24690310

---

## 7. What's Missing in the Market

### The Knowledge Connection Gap

Every existing product stops at **capture**. They extract text from physical books into digital form — but then what? Readwise resurfaces highlights via spaced repetition. Obsidian connects notes via manual linking. But no product:

- **Connects physical book notes to your broader knowledge graph** — what you've read in articles, other books, prior research
- **Identifies what's genuinely new vs. what you already know** in a physical book (Petrarca's core competency for articles)
- **Tracks knowledge evolution** across reading sessions — how your understanding of a topic develops chapter by chapter
- **Synthesizes across sources automatically** — connecting a passage in a physical book to relevant articles, other books, your own prior notes

### The Workflow Friction Problem

Reddit and community discussions reveal consistent frustrations:
- "It's too painful to quickly get frequent notes into note-taking platforms"
- The highlight → type → organize → connect pipeline is too many steps
- People want to annotate in physical books AND have digital access, without double-handling
- The hybrid physical + digital workflow always involves compromises
- Picking up a phone to capture something breaks the reading flow state

### The Anti-Digital Perspective

Some readers deliberately avoid digital tools because:
- Physical notebooks feel less distracting
- The tactile experience of writing improves retention
- Digital tools create temptation to switch to other apps
- Manual note-taking forces selective attention (you can't highlight everything)
- The *limitation* of physical notes is a feature, not a bug

### What Readers Actually Want

Based on community discussions and product gaps:

1. **Zero-friction capture** — The act of recording a thought should take < 5 seconds
2. **Context preservation** — Notes should know which book, which chapter, what came before
3. **Automatic organization** — Don't make me file things; connect them for me
4. **Spaced resurfacing** — Bring back insights at the right time, in the right context
5. **Cross-source connections** — Link a book passage to an article, a podcast, a previous note
6. **Respect the physical experience** — Don't require constant phone interaction
7. **Progressive depth** — Quick capture now, deeper engagement later

---

## 8. Opportunities for Petrarca's Physical Book Companion

Based on this research, Petrarca's existing infrastructure positions it uniquely:

### Already Built (Session 21)
- Book identification via camera (Gemini Vision)
- TOC lookup and chapter tracking
- Text, photo, and voice capture types
- Cover image fetching (Open Library / Google Books)
- AsyncStorage persistence

### High-Value Extensions

1. **Vision-enhanced capture** — Use Gemini Vision to extract highlighted/underlined text from page photos, not just plain OCR. Prompt it to identify visual markers (color highlighting, underlines, margin notes, post-its) and separate them from body text.

2. **Page number extraction** — OCR page numbers from captured photos to automatically update reading progress. No competitor does this.

3. **Knowledge overlay** — Apply Petrarca's claim-based knowledge system to book content. When a user captures a passage, match it against the existing knowledge ledger to identify: "You've encountered this idea in [Article X]" or "This extends what you read about [Topic Y]."

4. **Voice session synthesis** — After a reading session with multiple voice notes, use Gemini to synthesize them into structured insights with connections to the user's broader reading.

5. **Reading session as unit** — Group captures by time proximity into "reading sessions." Show what was captured, how many pages were covered, what themes emerged, and what questions remain.

6. **NotebookLM-style audio discussions** — Generate podcast-style AI discussions about a chapter's captures. Upload accumulated notes + book context → get back a 5-minute audio overview.

7. **Cross-source synthesis** — The killer feature no competitor has. Connect physical book notes to Petrarca's article corpus. "Chapter 3 of this book relates to these 4 articles you've read" — using the same embedding/similarity infrastructure already built for articles.

### Design Principles (From Research)

- **Minimize phone pickups** — Batch capture (multiple page photos + one voice note) rather than per-thought interruption
- **Respect the reading flow** — Don't require real-time interaction; let users capture now, engage deeply later
- **Start with capture, grow into understanding** — The capture is the "easy" part; the value is in the connections and synthesis
- **NFC could reduce friction** — Following BookPace's model, an NFC tag on a book could auto-open the capture interface. Expo supports NFC reading on iOS.

---

## Sources

### Products & Apps
- [Readwise OCR Documentation](https://docs.readwise.io/readwise/docs/importing-highlights/ocr)
- [Highlighted App](https://apps.apple.com/us/app/highlighted-book-highlights/id1480216009)
- [Highlighted Review — Ebook Friendly](https://ebookfriendly.com/highlighted-book-scanner-app-ipad-iphone/)
- [Screvi](https://screvi.com/)
- [Basmo Reading Tracker](https://basmo.app/)
- [Bookly](https://getbookly.com/)
- [BookTrack](https://booktrack.app/)
- [BookPace](https://www.bookpace.app/)
- [BookPace HN Discussion](https://news.ycombinator.com/item?id=45842067)
- [Mark AI Bookmark](https://mark.engineering/)
- [Mark HN Discussion](https://news.ycombinator.com/item?id=43193727)
- [vFlat Scan](https://www.vflat.com/en)
- [Fable](https://fable.co/)
- [Loxie Retention App](https://loxie.app/)
- [StoryGraph](https://thestorygraph.com/)
- [Literal](https://www.producthunt.com/products/literal-2/reviews)
- [BookWyrm](https://joinbookwyrm.com/)
- [Speechify](https://speechify.com/)
- [Otter.ai](https://otter.ai/)

### OCR & Vision Models
- [OmniAI OCR Benchmark](https://getomni.ai/blog/ocr-benchmark)
- [Mistral vs Gemini OCR Accuracy — Reducto](https://reducto.ai/blog/lvm-ocr-accuracy-mistral-gemini)
- [Document Data Extraction: LLMs vs OCRs — Vellum](https://www.vellum.ai/blog/document-data-extraction-llms-vs-ocrs)
- [Mistral OCR 3](https://mistral.ai/news/mistral-ocr-3)
- [Gemini Vision Capabilities for Scanned Documents](https://www.datastudios.org/post/can-google-gemini-read-scanned-documents-ocr-capabilities-and-accuracy-limits)
- [Best Open Source OCR Models](https://getomni.ai/blog/benchmarking-open-source-models-for-ocr)

### Academic Research
- [Magic Bookmark — University of Surrey](https://advanced.onlinelibrary.wiley.com/doi/full/10.1002/aisy.202100138)
- [Augmented Library AR Prototype](https://arxiv.org/html/2408.06107v1)
- [Phygital Textbook Companions — Frontiers in Education](https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2025.1660133/full)
- [Book Clubs and Comprehension — ERIC](https://files.eric.ed.gov/fulltext/EJ1171691.pdf)
- [Book Clubs in Sociology Courses — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC8263384/)
- [Dewarping Book Pages — ResearchGate](https://www.researchgate.net/publication/256442484_Dewarping_Book_Page_Spreads_Captured_with_a_Mobile_Phone_Camera)

### AI & Knowledge Management
- [NotebookLM Audio Overviews](https://blog.google/technology/ai/notebooklm-audio-overviews/)
- [NotebookLM Guide (October 2025)](https://medium.com/@shivashanker7337/notebooklm-the-complete-guide-updated-october-2025-1c9ebf5c14f6)
- [AI Reading Companions 2025](https://aiinsightsnews.net/best-ai-reading-companion/)
- [Spaced Repetition App Guide 2025-2026](https://makeheadway.com/blog/spaced-repetition-app/)
- [Transkribus](https://www.transkribus.org/)

### Community Discussions
- [HN: Turn "read later" into physical book](https://news.ycombinator.com/item?id=24690310)
- [Digital vs Analog Note-Taking Debate — MPU Talk](https://talk.macpowerusers.com/t/the-digital-vs-analogue-note-taking-debate-im-finally-at-peace/34863)
- [Physical vs Digital PKM — Curtis McHale](https://curtismchale.ca/2023/05/17/physical-vs-digital-pkm/)
- [Book Notes Capturing with ChatGPT](https://digital-garden.ontheagilepath.net/book-notes-capturing-with-chatgpt)
- [Obsidian as Second Brain (2025)](https://medium.com/@iankesler/best-notetaking-commonplace-tool-ever-update-how-obsidian-10x-my-workflow-and-became-my-c61e609a515b)

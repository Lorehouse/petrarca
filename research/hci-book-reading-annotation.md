# HCI Research on Book Reading, Annotation, and Knowledge Construction

*Research survey for Petrarca's physical book companion feature*
*Conducted 2026-03-15*

This document surveys academic HCI/CHI research on reading, annotation, sensemaking, and knowledge construction from books -- specifically targeting findings relevant to Petrarca's physical book companion, where users capture content from physical books (photos of pages, voice notes, typed text) and the system resurfaces and synthesizes this content.

Complements:
- `hci-reading-systems.md` -- Semantic Reader Project, claim extraction, topic modeling (digital article focus)
- `innovative-reading-ux.md` -- Cross-text visualization, context restoration, argument tracking (book reader Mode B)
- `knowledge-diff-interfaces.md` -- Adaptive presentation, dimming, progressive disclosure

---

## Table of Contents

1. [Augmented Reading Tools (CHI/UIST 2022-2025)](#1-augmented-reading-tools-chiuist-2022-2025)
2. [Annotation and Marginalia Research](#2-annotation-and-marginalia-research)
3. [Sensemaking Frameworks](#3-sensemaking-frameworks)
4. [Context Restoration and Reading Resumption](#4-context-restoration-and-reading-resumption)
5. [Voice Annotation Research](#5-voice-annotation-research)
6. [Cross-Document Synthesis](#6-cross-document-synthesis)
7. [Synthesis: What Should Petrarca Build?](#7-synthesis-what-should-petrarca-build)

---

## 1. Augmented Reading Tools (CHI/UIST 2022-2025)

### 1.1 Constrained Highlighting (CHI 2024 Best Paper)

**"Constrained Highlighting in a Document Reader Can Improve Reading Comprehension"** -- Joshi & Vogel, University of Waterloo. CHI 2024 Best Paper Award.

A between-subjects study (n=127) showed that capping the number of words a reader can highlight leads to *higher* reading comprehension than either unlimited highlighting or no highlighting. The constrained group (150-word cap) scored 11% higher than the unlimited group and 19% higher than the no-highlight group on a 24-hour delayed comprehension test.

Participants reported the constraint forced them to concentrate on the most important parts, producing shorter highlights focused on keywords and nouns rather than whole passages.

- Paper: https://dl.acm.org/doi/10.1145/3613904.3642314
- Project: https://nikhitajoshi.ca/constrained-highlighting

**Petrarca relevance**: This is directly applicable to the book capture flow. When a user photographs a page and the system extracts text, Petrarca could constrain them to select only a limited number of key passages for their capture -- forcing deeper engagement rather than "save everything" behavior. This could be implemented as a "pick your 3 most important sentences" step after OCR extraction.

### 1.2 Scim: Intelligent Skimming Support (IUI 2023)

**"Scim: Intelligent Skimming Support for Scientific Papers"** -- Fok, Kambhamettu, Soldaini, Bragg, Lo, Head, Hearst, Weld. IUI 2023.

Scim classifies and highlights four facets of information: Objective, Novelty, Method, and Result. Highlights are colorized by rhetorical role, evenly distributed throughout the text, and density is configurable by readers at both global and local levels. The key insight: skimming aids should highlight content that is simultaneously *diverse*, *evenly-distributed*, and *important*.

- Paper: https://dl.acm.org/doi/fullHtml/10.1145/3581641.3584034
- GitHub: https://github.com/rayfok/scim
- Extended version (TIIS 2024): https://dl.acm.org/doi/10.1145/3665648

**Petrarca relevance**: When displaying captured book content, Petrarca could apply faceted highlights to surface different types of content: arguments vs. evidence vs. definitions vs. examples. This would help readers quickly re-engage with captured pages during review.

### 1.3 CiteSee: Personalized Reading History (CHI 2023)

**"CiteSee: Augmenting Citations in Scientific Papers with Persistent and Personalized Historical Context"** -- Chang et al. CHI 2023.

CiteSee leverages a reader's reading behavior and history to personalize the reading experience. It automatically identifies inline citations and visually augments them based on their connections to the current reader -- whether the reader has read the cited paper, whether it's in their library, or whether it appears in their publication record.

The key innovation is using *the reader's own reading history* as the primary signal for personalization. Short-term fluid interests are captured from recent reading behavior; longer-term interests from library and publications.

- Paper: https://dl.acm.org/doi/10.1145/3544548.3580847
- Project: https://joe.cat/CHI-citesee/

**Petrarca relevance**: Core pattern for the book companion. When a user opens a new book, Petrarca already knows what they've captured from other books. Cross-references should be visually augmented based on whether the reader has encountered related ideas before -- "you explored this theme in Chapter 3 of Menocal" annotations.

### 1.4 ReaderQuizzer: Just-in-Time Comprehension Questions (CSCW 2023)

**"ReaderQuizzer: Augmenting Research Papers with Just-In-Time Learning Questions to Facilitate Deeper Understanding"** -- Maldonado, Abouzied, Gleason. CSCW 2023.

An augmented reading interface that uses LLMs to generate and co-locate comprehension and analysis questions within the text. Questions are positioned at the point of relevance, not at the end, forcing active engagement during reading rather than passive consumption.

- Paper: https://dl.acm.org/doi/10.1145/3584931.3607494

**Petrarca relevance**: After capturing a page photo, Petrarca could generate 1-2 comprehension questions about the captured content. This combines the self-explanation effect (see Section 5.2) with spaced review -- when the capture resurfaces days later, the question prompts active recall rather than passive re-reading.

### 1.5 GPTSM: Text Saliency Modulation (CHI 2024)

**"An AI-Resilient Text Rendering Technique for Reading and Skimming Documents"** -- Glassman et al., Harvard. CHI 2024.

Grammar-Preserving Text Saliency Modulation (GPTSM) de-emphasizes less important words through reduced opacity while preserving grammatical structure, enabling faster skimming while maintaining comprehension.

- Paper: https://glassmanlab.seas.harvard.edu/papers/gptsm.pdf

**Petrarca relevance**: Directly relevant to the existing "familiar paragraph dimming" feature (opacity 0.55 for known content). GPTSM suggests that *word-level* rather than paragraph-level dimming could be more effective -- de-emphasizing individual words/phrases the reader already knows while keeping novel terms at full opacity.

### 1.6 Priming at Scale (CHI 2025)

**"Priming at Scale: An Evaluation of Using AI to Generate Primes for Mobile Readers"** -- Adobe Research + Monash University. CHI 2025.

AI-generated primes (text summaries, images, mind maps) shown before reading increased reading speed by 7% with no loss in comprehension. Visual primes had a significant interruption recovery effect for non-native English speakers. Text primes resulted in higher comprehension of inferential questions. Study with 44 mobile readers.

- Paper: https://dl.acm.org/doi/10.1145/3706599.3720153

**Petrarca relevance**: When a user returns to a book after days/weeks, Petrarca should generate a "prime" from their previous captures -- a brief summary of what they've read and noted so far. This is the reading resumption problem (Section 4) solved with LLM-generated content.

### 1.7 The Semantic Reader Project (Allen AI, CACM 2024)

The umbrella project has produced ten research prototypes for augmented reading: CiteSee, CiteRead, Scim, ScholarPhi, Paper Plain, Papeos, Threddy, Relatedly, Ocean, and SciA11y. Available for over 7.2M papers. The open-source platform (PaperMage + PaperCraft) provides reusable NLP and React UI components.

- Paper: https://dl.acm.org/doi/10.1145/3659096
- Platform: https://openreader.semanticscholar.org/

### 1.8 CHI 2025 Tools for Thought Workshop

**"Understanding, Protecting, and Augmenting Human Cognition with Generative AI"** -- Tankelevitch et al. Synthesis of the CHI 2025 Tools for Thought Workshop (56 researchers, 34 papers).

Central model: "AI expands humans' multidimensional conceptual environments (spanning knowledge, representations, design possibilities); humans further expand these environments via creativity, critical thinking, and contextual understanding." Key concern: how to use AI to augment cognition without creating dependency or atrophying critical thinking.

- Paper: https://arxiv.org/abs/2508.21036
- Workshop: https://ai-tools-for-thought.github.io/workshop/
- Microsoft papers: https://www.microsoft.com/en-us/research/project/tools-for-thought/chi2025-papers/

**Petrarca relevance**: Petrarca sits at the intersection of this workshop's concerns. The book companion should augment the reader's own thinking (generating connections, resurfacing relevant captures) without replacing the reader's work of synthesis. The "constrained highlighting" result (Section 1.1) is one example of this principle: sometimes *less* AI assistance produces better cognitive outcomes.

---

## 2. Annotation and Marginalia Research

### 2.1 Physical vs. Digital Annotation: Cognitive Differences

**"Interacting with Academic Readings: A Comparison of Paper and Laptop"** (2021) -- A study of university students found that students annotate *significantly less* on laptop than on paper. On paper, students produced 1,535 annotations vs. 379 electronic annotations -- roughly 4x more. However, neither highlighting nor annotations significantly influenced subsequent memory in either condition.

- Paper: https://www.sciencedirect.com/science/article/pii/S2590291121001224

**"The Influence of Text Annotation Tools on Print and Digital Reading Comprehension"** -- Students in grades 5-8 reading on paper vs. laptop. More highlighting and annotating occurred on paper. Overall comprehension scores were slightly better on paper, though *increased paper highlighting was negatively associated with comprehension* -- suggesting that excessive highlighting is counterproductive regardless of medium.

- Paper: https://www.researchgate.net/publication/312549391

**Self-Regulated Learning theory** -- Differences between print and digital comprehension result mainly from differences in Self-Regulated Learning (SRL) dictated by the two media. Paper's fixed spatial layout supports metacognitive monitoring; scrolling digital text undermines it.

**Key insight for Petrarca**: The 4x annotation gap between physical and digital confirms that physical book reading produces richer annotation behavior. Petrarca's book companion should *capture* this rich physical annotation (marginalia photos, voice reactions) and digitize it, rather than trying to replicate physical annotation in a digital interface. The challenge is bridging the gap: making digital captures as rich and contextual as the physical marginalia they derive from.

### 2.2 Expert Annotation Practices

**H.J. Jackson, "Marginalia: Readers Writing in Books" (2001)** -- The definitive study of marginalia practices across centuries. Jackson identifies three categories of marginalia by their relationship to the text:

1. **Embedded** -- marks that engage directly with the text content (underlining, brackets, annotations explaining or questioning the text)
2. **Evaluative** -- judgments about the text (agreement/disagreement markers, quality assessments)
3. **Extratextual** -- connections beyond the text (cross-references to other works, personal associations, application notes)

Jackson found that readers are significantly more likely to annotate when reading for work or educational purposes than for pleasure. Expert readers develop systematic annotation vocabularies: specialized symbols, color codes, margin abbreviations.

- Book: https://www.amazon.com/Marginalia-Readers-H-J-Jackson/dp/0300097204

**Four types of interaction with graphic devices** (Liira, 2024) -- A study of early modern English readers identified: (1) modifications/additions to printed devices, (2) copies of devices, (3) handwritten original devices, (4) reactive/evaluative comments on devices.

- Paper: https://onlinelibrary.wiley.com/doi/10.1111/rest.12995

**Key insight for Petrarca**: Jackson's three-category taxonomy maps directly to Petrarca's capture types:
- **Embedded** = text highlights, page photos with specific passages marked
- **Evaluative** = voice notes expressing agreement/disagreement, "interesting" / "I knew this" signals
- **Extratextual** = cross-book connections, topic tags, links to articles in the feed

Petrarca should prompt users to classify their captures into these categories, or infer the category from the capture modality (voice notes tend to be evaluative/extratextual; photos tend to be embedded).

### 2.3 The Constrained Annotation Principle

The constrained highlighting study (Section 1.1) combined with the physical annotation research yields a powerful design principle: **annotation is most valuable when it forces selectivity**. Too-easy annotation (unlimited digital highlighting) produces worse outcomes than constrained annotation.

Physical books naturally constrain annotation: margin space is limited, ink is permanent, and there's social pressure not to deface a book excessively. Digital capture removes all these constraints, which may paradoxically reduce its cognitive value.

**Design implication**: Petrarca should introduce *deliberate friction* in the capture flow. Instead of "capture everything," the system should ask "what's the single most important idea on this page?" or limit captures to N per reading session. This friction transforms capture from archiving into active processing.

---

## 3. Sensemaking Frameworks

### 3.1 Pirolli & Card's Sensemaking Model

**"The Sensemaking Process and Leverage Points for Analyst Technology"** (2005) -- The foundational framework for understanding how people make sense of information.

Two major loops:
1. **Foraging Loop**: Seeking, filtering, reading, and extracting information. The analyst populates a "shoebox" of potentially relevant documents, then creates an "evidence file" of extracted relevant passages, then builds a "schema" -- a structured representation.
2. **Sensemaking Loop**: Iteratively developing representational schemas. Bottom-up (data to theory) and top-down (theory to data) processes in an "opportunistic mix."

Three key data structures:
- **Shoebox**: Raw collection of potentially relevant documents (cast a wide net)
- **Evidence file**: Extracted passages and facts organized by relevance
- **Schema**: A structured representation that summarizes, abstracts, and eliminates irrelevant information

- Paper: https://andymatuschak.org/files/papers/Pirolli,%20Card%20-%202005%20-%20The%20sensemaking%20process%20and%20leverage%20points%20for%20analyst%20technology%20as.pdf

**Petrarca relevance**: The book companion currently supports the *shoebox* (photo/voice/text captures dumped into a book's capture list) but lacks tools for the *evidence file* (organizing captures by relevance and theme) and *schema* (building a structured understanding across captures and books). The transition from shoebox to evidence file is the critical bottleneck -- most readers collect captures but never process them.

### 3.2 Russell et al.'s Learning Loop Complex

**Russell, Stefik, Pirolli, Card (1993)** -- Framed sensemaking as "the process of forming and working with meaningful representations in order to facilitate insight and subsequent intelligent action."

The core is a "learning loop complex" with three nested loops:
1. **Generation loop**: Search for a good representation (schema)
2. **Data coverage loop**: Attempt to encode information in the representation
3. **Representation shift loop**: When items don't fit ("residue"), adjust the representation

The key concept of **residue** -- items that don't fit the current schema -- is what drives schema evolution. When a reader encounters a claim that contradicts their current understanding, the residue forces a representational shift.

- Paper: https://www.researchgate.net/publication/215439203

**Petrarca relevance**: Petrarca's knowledge model (claims, similarity scores, novelty detection) is essentially automating the detection of *residue*. When the system identifies a claim as "extends" (0.68-0.78 cosine similarity) rather than "known" (>0.78), it's flagging information that doesn't fit cleanly into the reader's current schema. The book companion should surface these "residue" captures prominently -- they're where learning happens.

### 3.3 Fuse: In-Situ Sensemaking in the Browser (UIST 2022)

**"Fuse: In-Situ Sensemaking Support in the Browser"** -- Kuznetsov, Chang, Hahn, Rachatasumrit, Breneisen, Coupland, Kittur. UIST 2022.

A browser extension that externalizes working memory through a compact card-based sidebar. Key design: snipping content creates a card, cards can be organized hierarchically, bundles group related cards. A 22-month public deployment showed that real users naturally developed structuring behaviors -- creating hierarchies, bundling related snippets, and revisiting/reorganizing collections over time.

- Paper: https://dl.acm.org/doi/fullHtml/10.1145/3526113.3545693

**Petrarca relevance**: Fuse's card-based sidebar is a good model for how book captures could be organized within a reading session. Each capture becomes a card; cards can be bundled by theme; bundles persist and grow across sessions. The 22-month deployment validates that this interaction pattern is sustainable for long-term use.

### 3.4 Threddy: Thread-Based Literature Exploration (UIST 2022)

**"Threddy: An Interactive System for Personalized Thread-based Exploration and Organization of Scientific Literature"** -- Kang, Chang, Kim, Kittur. UIST 2022.

Readers highlight passages that contain pre-digested syntheses by other authors (typically in introduction/related work sections). Threddy extracts referenced papers, links them to the citation context, and lets the reader create named "threads" -- organized collections of related citations with their connecting narratives.

Key finding: Threddy decreases the cost of frequent context switching and heightens users' flow state during literature review.

- Paper: https://dl.acm.org/doi/10.1145/3526113.3545660

**Petrarca relevance**: The "thread" concept maps to Petrarca's cross-book connections. When a user captures content from multiple books on the same topic (e.g., "Arabic-Latin transmission"), these captures should automatically form a thread. The reader can then see the thread as a narrative connecting captures across books, ordered by conceptual relationship rather than capture date.

---

## 4. Context Restoration and Reading Resumption

### 4.1 Spatial Memory and Page Position

Research consistently shows that readers encode the spatial position of text on a page as part of their memory for that text:

**Zechmeister et al. (1975, Memory & Cognition)** -- Readers can recall where on a page specific information appeared even when the information itself cannot be retrieved. Location memory and content memory are not independent: each can cue recall of the other. Critically, depriving readers of spatial-location cues (by presenting text as a continuous scroll) *significantly lowered word recall*.

- Paper: https://link.springer.com/article/10.3758/BF03196979

**Spatial representation of text** -- Readers incidentally encode a text's spatial attributes and construct a spatial representation alongside semantic, phonological, and syntactic representations. The page acts as a "visuospatial cue" providing a salient reference frame for word location memory.

- Related: https://pmc.ncbi.nlm.nih.gov/articles/PMC2694611/

**"Reading on Paper Versus Screens: What's the Difference?"** (BrainFacts, 2020) -- When we read, our brains construct a cognitive map of the text. On paper, this map is stable: readers recall that information appeared "near the top, left-hand page." On screens, particularly with scrolling, this mapping is disrupted because words don't have fixed locations.

- Article: https://www.brainfacts.org/neuroscience-in-society/tech-and-the-brain/2020/reading-on-paper-versus-screens-whats-the-difference-072820

**Petrarca relevance**: This is a strong argument for Petrarca's photo capture feature. When a user photographs a page, the spatial layout is preserved. When that capture resurfaces during review, the reader can use spatial memory cues ("I remember this was at the bottom of the left page") to aid recall. The system should display captured page photos at sufficient resolution to preserve spatial layout, and should *not* strip photos down to extracted text alone.

### 4.2 Task Resumption Lag

**Altmann & Trafton (2002, 2004)** -- The task resumption lag is the measurable delay when returning to an interrupted task. Two competing explanations:

1. **Goal decay**: The suspended task's goal representation decays in memory, requiring reactivation
2. **Goal inhibition**: The primary task goal is actively inhibited when switching to the secondary task; resumption requires overcoming this inhibition

Research shows it takes *over 23 minutes* to recover focus after an interruption, with increased stress, time pressure, and "attentional residue" that impairs working memory on subsequent tasks.

- Paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC10896823/
- Paper: https://www.researchgate.net/publication/2909216

**Petrarca relevance**: Returning to a book after days or weeks is an extreme form of task interruption. The resumption lag is substantial. Petrarca must actively reduce this lag through context restoration cues (see 4.3).

### 4.3 Reviews and Previews for Reading Resumption (CHI 2021)

**"Mitigating the Effects of Reading Interruptions by Providing Reviews and Previews"** -- Srivastava & Jain. CHI 2021 Extended Abstracts.

Four types of summary presentations were tested for their ability to mitigate interruption effects:
- **Review before interruption**: Summary of content already read, shown before the break
- **Review after interruption**: Same summary, shown when resuming
- **Preview before interruption**: Summary of upcoming content, shown before the break
- **Preview after interruption**: Same preview, shown when resuming

Key finding: Users *prefer* reviews after interruptions, but *previews* shown after interruptions have the larger positive influence on comprehension. Showing priming cues after the interruption (rather than before) improved reading comprehension and reduced response time.

- Paper: https://dl.acm.org/doi/fullHtml/10.1145/3411763.3451610

**Petrarca relevance**: When a user opens a book they haven't read in days, Petrarca should show both:
1. A **review**: "Last time, you captured these ideas from Chapter 5..." (what they've already processed)
2. A **preview**: "Chapter 6 will explore..." (what's coming next)

The research suggests the preview is more important for comprehension, but users feel better with the review. Show both.

### 4.4 EyeBookmark (CHI 2015)

**"EyeBookmark: Assisting Recovery from Interruption During Reading"** -- Jo, Kim, Seo. CHI 2015.

A gaze-based bookmarking system that automatically tracks where the reader was looking before an interruption and provides visual highlighting to guide resumption. Four highlighting methods were tested; all significantly reduced time to resume reading compared to no highlighting.

- Paper: https://dl.acm.org/doi/10.1145/2702123.2702340

**Petrarca relevance**: Without eye tracking, Petrarca can approximate this by recording the last page/section the user captured from and using that as the resumption point. The "where you left off" indicator should be prominent and include surrounding context, not just a page number.

---

## 5. Voice Annotation Research

### 5.1 Voice Note-Taking Promotes Conceptual Understanding

**"Using Voice Note-Taking to Promote Learners' Conceptual Understanding"** -- Kang et al. (2020).

A study comparing keyboard vs. voice note-taking (n=60) found that:
- Voice notes led to *higher conceptual understanding* of the text
- Voice triggers *generative processes* that result in more elaborate and comprehensive notes
- Voice note-takers produced richer, more connected explanations

The mechanism: voice is faster and more fluid than typing, which reduces the transcription bottleneck and allows the learner to focus on meaning-making rather than word selection. The generative process of articulating understanding verbally activates deeper processing.

- Paper: https://arxiv.org/abs/2012.02927

**Petrarca relevance**: This is the strongest evidence that voice capture should be a first-class feature of the book companion, not an afterthought. When a user records a voice note about what they just read, they're not just creating a record -- they're actively processing the material at a deeper level than if they typed the same note. Petrarca should *encourage* voice notes over text input during book reading sessions.

### 5.2 The Self-Explanation Effect

**Chi et al. (1989, 1994, "Eliciting Self-Explanations Improves Understanding")** -- Students who generated oral explanations while reading achieved significantly higher test scores. The mechanism: self-explanation forces learners to generate inferences about causal connections and conceptual relationships, identify gaps in their understanding, and actively monitor comprehension.

Meta-analysis across 64 studies and 6,000 participants found an overall effect size of g = 0.55 -- a medium-to-large effect.

- Original paper: https://onlinelibrary.wiley.com/doi/10.1207/s15516709cog1803_3
- Meta-analysis: https://www.bps.org.uk/research-digest/self-explanation-powerful-learning-technique-according-meta-analysis-64-studies

**For complex text specifically**: Oral explaining yielded *better comprehension than writing explanations*. Generating oral explanations triggered elaborative processes to a more pronounced extent than written explanations, particularly beneficial for transferable knowledge.

**Petrarca relevance**: Voice notes in Petrarca are essentially self-explanations. The system should explicitly frame voice capture as "explain what you just read in your own words" rather than "record a note." This reframing leverages the self-explanation effect. The transcribed voice note then becomes a richer artifact than a typed summary would be.

### 5.3 The Production Effect

**MacLeod et al. (2010, 2017, "The Production Effect: Delineation of a Phenomenon")** -- Reading a word aloud, versus silently, improves recognition memory by 10-20%. The dual action of speaking and hearing oneself has the most beneficial impact. Reading aloud consistently outperforms non-auditory production (writing, mouthing) and even other auditory production (whispering).

- Paper: https://uwaterloo.ca/memory-attention-cognition-lab/sites/default/files/uploads/files/jep10.pdf
- Waterloo summary: https://uwaterloo.ca/news/news/study-finds-reading-information-aloud-yourself-improves

**Petrarca relevance**: When a user reads a key passage aloud into a voice capture, they get the production effect for free -- the act of speaking the passage enhances their memory for it. This suggests a capture flow where the user is prompted to *read the key passage aloud* before recording their reaction, combining the production effect with the self-explanation effect.

### 5.4 The Generation Effect

**Slamecka & Graf (1978)** -- Information generated from one's own mind is better remembered than information simply read. The generation effect has been replicated across hundreds of studies and extends to all types of material.

- Wikipedia: https://en.wikipedia.org/wiki/Generation_effect

**Combined with voice**: When a user voice-captures a reaction to a book passage, they're combining three memory-enhancing effects: (1) production effect (speaking aloud), (2) generation effect (creating their own interpretation), (3) self-explanation (articulating causal connections). This triple combination makes voice notes potentially the *most powerful capture modality* for long-term retention.

---

## 6. Cross-Document Synthesis

### 6.1 Passages: Reified Text Objects Across Documents (CHI 2022)

**"Passages: Interacting with Text Across Documents"** -- CHI 2022 Honorable Mention.

Text selections become first-class persistent objects (passages) that can be manipulated, reused, and shared across multiple tools while maintaining provenance. A single click on blue text shows the underlying passage as a tooltip; users can open the source document or pin it for later reuse.

User studies with patent examiners and scientists showed that participants valued maintaining visibility of source material while working with excerpts, and that transparent provenance links reduced confusion during document synthesis.

- Paper: https://dl.acm.org/doi/10.1145/3491102.3502052

**Petrarca relevance**: Book captures in Petrarca are essentially "passages" in this framework. Each capture should be a first-class object with: source book, page number, surrounding context, capture date, and any voice/text annotation. When a capture appears in a synthesis or cross-book connection, clicking it should navigate to the full page context.

### 6.2 Syntopical Reading (Adler & Van Doren)

Adler's "How to Read a Book" (1940/1972) defines syntopical reading as the most demanding reading level: reading multiple books on the same subject to compare and contrast ideas, vocabulary, and arguments. The five steps:

1. **Find relevant passages** across all books
2. **Bring authors to terms** -- construct a neutral terminology (the hardest step)
3. **Get the questions clear** -- frame the questions the books address
4. **Define the issues** -- map out where authors agree and disagree
5. **Analyze the discussion** -- produce a map of the intellectual landscape

The output is "something no single book provides: a map showing where thinkers agree, where they clash, and why."

- Summary: https://fs.blog/how-to-read-a-book/
- Five steps: https://theinvisiblementor.com/the-five-steps-of-syntopical-reading-explained/

**Petrarca relevance**: Petrarca's cross-book synthesis feature should automate parts of syntopical reading:
- Step 1 (find passages) = claim extraction + embedding similarity
- Step 2 (bring to terms) = topic normalization + concept clustering
- Step 3 (frame questions) = could be LLM-generated from clustered claims
- Step 4 (define issues) = claim similarity with "contradicts" / "extends" / "agrees" classification
- Step 5 (analyze discussion) = synthesis generation (already built for articles)

The gap is Step 2 -- terminology normalization across books. Two authors may use completely different vocabulary for the same concept. This is where Petrarca's embedding-based similarity already helps, but explicit terminology mapping (a "glossary" across books) could be a powerful feature.

### 6.3 LiquidText: Spatial Active Reading (CHI 2011)

**"LiquidText: A Flexible, Multitouch Environment to Support Active Reading"** -- Tashman & Edwards. CHI 2011.

A multitouch reading system where the document representation is elastic: users can pinch to collapse intervening pages, bringing distant passages into proximity. Excerpts dragged to a freeform workspace maintain live bidirectional links to source documents. Up to 5 documents can be displayed simultaneously with workspace excerpts from different documents coexisting.

A formative study found strong user preference for LiquidText, with users focusing on creating summaries as part of the reading process.

- Paper: https://faculty.cc.gatech.edu/~keith/pubs/chi2011-liquidtext.pdf

### 6.4 Incremental Reading (SuperMemo)

SuperMemo's incremental reading combines reading with spaced repetition: readers extract key fragments, convert them to flashcards, and review them over time. The key insight is that reading and retention should be interleaved rather than sequential -- you don't finish a book and then make flashcards; you extract and schedule as you read.

The process: read article -> extract important fragments -> convert to Q&A items -> review via spaced repetition. This "slow process of jelling out knowledge" provides enhanced meaning and applicability of individual pieces.

- Detailed guide: https://supermemo.guru/wiki/Incremental_reading
- Help: https://help.supermemo.org/wiki/Incremental_reading

**Petrarca relevance**: The book companion's capture flow already follows the "extract during reading" pattern. The missing piece is the scheduled review: captured passages should resurface via the spaced repetition system (FSRS) with comprehension questions generated from the captures.

### 6.5 Orbit: Embedded Spaced Repetition (Matuschak & Nielsen)

**Orbit** -- An experimental platform for embedding spaced repetition prompts directly within prose. Developed from the "mnemonic medium" concept first used in Quantum Country.

Key finding: Spaced repetition is effective for learning *abstract conceptual material*, not just atomic factoids. The mnemonic medium lets authors write texts that readers can deeply internalize with relatively little effort through embedded review prompts.

- Platform: https://withorbit.com/
- GitHub: https://github.com/andymatuschak/orbit
- Notes: https://notes.andymatuschak.org/Mnemonic_medium

**Petrarca relevance**: When Petrarca resurfaces a book capture, it could embed Orbit-style prompts: "In Chapter 3, Menocal argues that ___. How does this relate to Burnett's analysis of transmission?" These prompts combine retrieval practice with cross-book synthesis, testing not just recall but understanding of connections.

### 6.6 Evergreen Notes as Knowledge Construction (Matuschak)

Andy Matuschak's framework for note-writing as the fundamental unit of knowledge work:

- **Evergreen notes** are written and organized to evolve, contribute, and accumulate over time
- Each note should focus on a single idea (atomic)
- Notes should be densely linked to create a network that sparks new connections
- "Write about what you read" to truly internalize a text
- "Write notes for yourself by default, disregarding audience"

The metric for knowledge work productivity: "the number of Evergreen notes written per day."

- Notes: https://notes.andymatuschak.org/Evergreen_notes
- On knowledge work: https://notes.andymatuschak.org/Evergreen_note-writing_as_fundamental_unit_of_knowledge_work

**Petrarca relevance**: Each book capture that is processed (annotated, connected, reviewed) could become an "evergreen note" in Petrarca's knowledge graph. The system should track which captures are raw (unprocessed shoeboxed material) vs. processed (annotated, connected, reviewed) and prompt the user to process raw captures into evergreen knowledge.

---

## 7. Synthesis: What Should Petrarca Build?

Based on the research surveyed above, here are concrete experimental directions for Petrarca's physical book companion, ordered by expected impact.

### 7.1 Constrained Capture Flow (High Impact, Low Effort)

**Research basis**: Constrained highlighting (CHI 2024 Best Paper), annotation frequency vs. comprehension research.

**What to build**: After OCR extraction from a page photo, present the extracted text and ask the user to select *at most 3 key sentences*. This constraint forces active processing during capture, not just archiving. Track whether constrained captures lead to better recall during review sessions compared to unconstrained "save everything" captures.

**Experiment**: A/B test within the app -- some reading sessions use constrained capture (3-sentence limit), others use unconstrained. Measure recall accuracy and self-reported understanding during spaced review.

### 7.2 Voice-First Capture with Self-Explanation Framing (High Impact, Medium Effort)

**Research basis**: Voice note-taking (Kang et al. 2020), self-explanation effect (Chi 1994, meta-analysis g=0.55), production effect (MacLeod 2010).

**What to build**: Make voice the *default* capture modality. After photographing a page, prompt: "In your own words, what's the key idea here?" Record their verbal explanation. The triple memory benefit (production + generation + self-explanation) makes this the most cognitively powerful capture flow.

**Enhancement**: After transcription, use an LLM to identify the core claim in the user's explanation and match it against the knowledge graph. Show "you've connected this to N other ideas" as positive feedback.

**Experiment**: Compare retention at 1-week and 1-month intervals for: (a) photo-only captures, (b) photo + typed note, (c) photo + voice self-explanation. Measure with comprehension questions generated from the captured content.

### 7.3 Reading Resumption Primes (High Impact, Medium Effort)

**Research basis**: Reviews and previews (CHI 2021), AI priming (CHI 2025), task resumption lag research.

**What to build**: When a user opens a book they haven't read in >48 hours, generate a context restoration screen:
1. **Review**: "Last session (3 days ago), you read pages 45-62 of Chapter 3. You captured 4 ideas: [thumbnails of captures with key claims]"
2. **Preview**: "Chapter 4 will explore [LLM-generated preview from table of contents + any available summaries]"
3. **Spatial cue**: Show the last captured page photo with the capture location highlighted

**Experiment**: Track resumption speed (time from opening book to first new capture) with and without the context restoration screen. Track reading session length as a secondary measure.

### 7.4 Sensemaking Progression: Shoebox to Schema (High Impact, High Effort)

**Research basis**: Pirolli & Card sensemaking model, Russell's learning loop complex, Fuse's card-based organization.

**What to build**: Three-stage capture processing:
1. **Shoebox** (default): Raw captures dump into a chronological list. This is what exists today.
2. **Evidence file**: User reviews captures and tags them with themes (LLM-suggested). Captures cluster into theme groups. Cross-book connections surface automatically.
3. **Schema**: User (with LLM assistance) produces a structured synthesis -- "Here's what I've learned about [topic] across [N books]." This becomes an evergreen note.

Track captures through these stages. Surface "unprocessed captures" as gentle nudges: "You have 12 unprocessed captures from The Ornament of the World. Want to organize them?"

**Experiment**: Track how many captures reach the "schema" stage with and without the three-stage pipeline. Measure whether processed captures show higher recall in spaced review.

### 7.5 Cross-Book Thread Detection (Medium Impact, Medium Effort)

**Research basis**: Threddy (UIST 2022), syntopical reading (Adler), Passages (CHI 2022).

**What to build**: Automatically detect when captures from different books discuss the same topic or make related claims. Use embedding similarity (Nomic, already in pipeline) to cluster cross-book captures. Present these as "threads" -- named collections like "The role of translation in cultural transmission" with captures from 3 different books.

When the user captures something new that connects to an existing thread, show: "This connects to your thread on [topic] -- 3 related captures from 2 other books."

**Experiment**: Track whether users who receive cross-book connection notifications engage with more books simultaneously (interleaved reading pattern) and whether their synthesis quality improves.

### 7.6 Embedded Retrieval Practice (Medium Impact, Low Effort)

**Research basis**: Orbit/mnemonic medium (Matuschak & Nielsen), ReaderQuizzer (CSCW 2023), spaced repetition research.

**What to build**: When a capture resurfaces for review (via FSRS scheduling), present it as a retrieval prompt rather than passive re-reading:
- Show the page photo with the key passage masked
- Ask: "What was the main argument on this page?"
- After the user responds (voice or text), reveal the passage and the user's original capture
- User rates their recall (correct/partial/forgot)

This transforms review from passive consumption into active retrieval practice, which is far more effective for retention.

### 7.7 Page Photo as Spatial Memory Anchor (Low Effort, Research Validation)

**Research basis**: Zechmeister spatial memory research, paper vs. screen studies.

**What to build**: Always display captured page photos at full resolution, preserving the spatial layout. Never replace photos with extracted text alone. When showing cross-book connections, display the source page photo alongside the extracted text so the reader can use spatial memory cues.

**Design rule**: The page photo is the *primary* artifact; extracted text is metadata.

### 7.8 Capture-Time Comprehension Questions (Medium Impact, Low Effort)

**Research basis**: ReaderQuizzer (CSCW 2023), self-explanation effect, constrained highlighting.

**What to build**: After a capture, generate 1-2 comprehension questions from the captured content using an LLM. Present them immediately: "Based on what you just captured, can you answer: Why does the author argue that X?" The user can answer (voice/text) or skip. Store the answer alongside the capture.

When the capture resurfaces for review, show the original question and answer as context.

---

## Key Papers Reference

| Paper | Venue | Year | Key Finding |
|-------|-------|------|-------------|
| Constrained Highlighting | CHI (Best Paper) | 2024 | Limited highlighting improves comprehension by 11-19% |
| Scim | IUI | 2023 | Faceted, distributed highlights improve skimming |
| CiteSee | CHI | 2023 | Reading history personalizes cross-document connections |
| ReaderQuizzer | CSCW | 2023 | Just-in-time comprehension questions deepen understanding |
| Priming at Scale | CHI | 2025 | AI-generated primes improve reading speed by 7% |
| Tools for Thought Workshop | CHI | 2025 | Framework for AI-augmented cognition |
| Reviews and Previews | CHI EA | 2021 | Previews after interruptions improve comprehension most |
| EyeBookmark | CHI | 2015 | Visual resumption cues reduce re-engagement time |
| Passages | CHI (HM) | 2022 | Reified text selections with provenance |
| Threddy | UIST | 2022 | Thread-based cross-document exploration |
| Fuse | UIST | 2022 | Card-based sensemaking sidebar (22-month deployment) |
| LiquidText | CHI | 2011 | Elastic document + freeform workspace |
| ScholarPhi | CHI | 2021 | Position-sensitive definitions reduce lookup time |
| Semantic Reader | CACM | 2024 | 10 reading prototypes, open platform |
| Voice Note-Taking | arXiv | 2020 | Voice notes produce higher conceptual understanding |
| Self-Explanation | Cognitive Science | 1994 | Self-explanation effect size g=0.55 across 64 studies |
| Production Effect | JEP:LMC | 2010 | Reading aloud improves memory 10-20% |
| GPTSM | CHI | 2024 | Word-level saliency modulation for skimming |
| Sensemaking Model | Int'l J HCI | 2005 | Shoebox -> Evidence File -> Schema framework |
| Marginalia | Book | 2001 | Embedded/Evaluative/Extratextual annotation categories |
| Spatial Memory | Memory & Cognition | 1983 | Page position aids text recall; scroll disrupts it |
| Incremental Reading | SuperMemo | ongoing | Extract + schedule + review during reading |
| Orbit/Mnemonic Medium | Experimental | ongoing | Embedded spaced repetition in prose |

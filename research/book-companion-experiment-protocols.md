# Physical Book Companion: Detailed Experiment Protocols

**Date**: 2026-03-15
**Purpose**: Specific, testable experiments for Petrarca's physical book companion — each with hypothesis, algorithm, UI flow, user journey, data requirements, and supporting research.

**Current infrastructure**: `PhysicalBook` + `BookCapture` types, `book-store.ts` (AsyncStorage), `call_vision()` (Gemini), Soniox STT, `build_claim_embeddings.py` (Gemini embeddings), cosine similarity thresholds (KNOWN ≥ 0.78, EXTENDS ≥ 0.68), 239 articles with ~4,500 embedded claims.

---

## Experiment 1: Reading Echoes — Book Knowledge Resurfacing in Articles

### Hypothesis

When a user reads an article whose claims semantically match captures from a physical book, surfacing those book captures as inline annotations will:
- (H1a) Slow the decay of book knowledge (measured by prompted recall)
- (H1b) Increase the reader's sense of cross-source connection (measured by self-report)
- (H1c) Not disrupt reading flow (measured by article completion rate remaining stable)

### Research Backing

- **Spreading activation**: Encountering concept X triggers partial recall of connected concept Y ([Collins & Loftus, 1975](https://www.cognitivepsychology.com/Spreading_Activation))
- **Analogical reminding > explicit comparison**: Remindings during encoding of new material produce better transfer than deliberate comparison ([Gentner et al., 2016](https://link.springer.com/article/10.1186/s41235-016-0028-1))
- **Transfer-appropriate processing**: Retrieval is best when cognitive context matches encoding context — both here are "deep reading" ([Morris et al., 1977](https://en.wikipedia.org/wiki/Transfer-appropriate_processing))
- **Incidental spaced retrieval**: Encountering concepts in new contexts provides spacing benefits without flashcard overhead ([Rawson & Dunlosky, 2022](https://www.nature.com/articles/s44159-022-00089-1))

### Algorithm

```
On article load:
  1. Get article claims from knowledge_index.json (already loaded)
  2. Get all book capture embeddings from book_capture_embeddings.npz
  3. For each article claim:
     - Compute cosine similarity against all book capture embeddings
     - If max_sim >= EXTENDS_THRESHOLD (0.68) and < KNOWN_THRESHOLD (0.78):
       mark as "echo candidate" with matched book capture
  4. Rank echo candidates by similarity score descending
  5. Select top 3 (max) — never more, to avoid clutter
  6. Attach echoes to the article claim they matched against
```

**Embedding pipeline addition** (`scripts/build_book_capture_embeddings.py`):
- New script, modeled on `build_claim_embeddings.py`
- Input: all `BookCapture` objects from server (synced via `/book/captures` endpoint)
- Embed `ocr_text || transcript || text` using Gemini Embedding API (same model: `gemini-embedding-001`)
- Output: `book_capture_embeddings.npz` — same format as `claim_embeddings.npz`
- Run incrementally: only embed new captures
- Include in the 4-hour content refresh pipeline (`content-refresh.sh`)

### UI Description

**Position**: Inside the article reader (`reader.tsx`), after the matched article claim card.

**Appearance**: A compact card styled as a margin annotation:
```
┌─ 📖 ──────────────────────────────────────────┐
│ From "The Prince" (Ch. 3, p. 47):             │
│ "Fortune is the arbiter of half our actions"  │
│                                               │
│ Your voice note (Mar 10): "The prudence       │
│ argument feels stronger than the fortune      │
│ one..."                                       │
│                                [Go to book →] │
└───────────────────────────────────────────────┘
```

- **Left border**: 2px in `textMuted` color (#b0a898) — not rubric, since this is supplementary
- **Book icon**: Small 📖 emoji or EB Garamond italic "cf." prefix
- **Content**: The matched book capture text (truncated to 2 lines), plus any voice note transcript (truncated to 1 line)
- **Tap**: Expands to show full capture text + page photo thumbnail if available
- **"Go to book"**: Navigates to book detail screen focused on this capture
- **Animation**: Slides in with 200ms ease-out, like claim cards

**Key constraint**: Echoes appear AFTER the relevant article claim, not before. The reader encounters the article's claim first, then sees the connection. This preserves the article's reading flow and triggers the "reminding" mechanism (you read something new → it reminds you of something old).

### User Journey

1. Stian reads an article about Machiavelli's political philosophy in his morning feed
2. The article claims that "effective leadership requires pragmatism over moral virtue"
3. Below this claim, a Reading Echo appears: a capture from "The Prince" — a page photo he took of the passage about fortune and virtù, plus his voice note reflecting on it
4. He sees the connection, taps to expand, reads his own voice note from 2 weeks ago
5. The encounter reinforces his memory of Machiavelli's argument from a new angle
6. He continues reading the article — the echo took 10 seconds of attention
7. In the background, the system logs this as a "concept encounter" event for the matched book capture, extending its knowledge half-life

### Data Requirements for Testing

**Minimum viable test**: 1 book with 10+ captures, 2 weeks of article reading after captures are embedded.

**Statistical test**: Within-subjects comparison — track knowledge vitality for book captures that get "echoed" in articles vs. captures that don't. After 4 weeks, present prompted recall tests for both groups. Need ~30 captures total (15 echoed, 15 control) for a paired t-test with reasonable power.

**Metrics to log**:
- `reading_echo_shown`: { article_id, capture_id, similarity_score, position_in_article }
- `reading_echo_expanded`: { capture_id, dwell_time_ms }
- `reading_echo_navigate`: { capture_id, destination: 'book_detail' }
- `article_completion_rate`: unchanged = flow not disrupted
- `capture_recall_test`: { capture_id, was_echoed: boolean, recall_quality: 1-5 } (manual test at 4 weeks)

**Realistic timeline**: Need 10+ captures from a real book reading session, then 2-4 weeks of normal article reading for echoes to appear organically. Total: ~6 weeks from first book capture to first meaningful data.

---

## Experiment 2: Smart Page Photo Processing

### Hypothesis

Enhanced vision processing of page photos will:
- (H2a) Automatically detect highlighted/underlined passages with >80% precision
- (H2b) Auto-extract page numbers with >90% accuracy, eliminating manual progress tracking
- (H2c) "Suggested highlights" (important passages the user didn't mark) will prompt additional captures in >20% of cases

### Research Backing

- **Matuschak's highlight-driven prototype** (2023): 14 participants "broadly loved" auto-generated prompts from highlights. "Suggested highlights" at section ends helped catch comprehension gaps. ([Notes: Initial results](https://notes.andymatuschak.org/z9V2PxHVYB9p5DeCnQXcfJa))
- **Vision model accuracy**: GPT-4o ~98%, Claude ~97%, Gemini ~96% on printed text OCR. VLMs understand document structure, not just characters. ([OmniAI benchmark](https://getomni.ai/blog/ocr-benchmark), [Reducto](https://reducto.ai/blog/lvm-ocr-accuracy-mistral-gemini))
- **Screvi**: Already uses Gemini to extract highlighted/underlined text specifically. Proves the approach is viable commercially. ([screvi.com](https://screvi.com/))
- **Constrained Highlighting** (CHI 2024 Best Paper): the act of selecting what's important IS the comprehension work. ([dl.acm.org](https://dl.acm.org/doi/10.1145/3613904.3642314))

### Algorithm

**Enhanced `call_vision()` prompt** (replaces current OCR-only prompt):

```python
SMART_PAGE_PROMPT = """Analyze this photo of a book page.

The book is "{title}" by {author}. The reader is on approximately chapter: {chapter}.

Return a JSON object with:
{{
  "page_number": <integer or null if not visible>,
  "full_text": "<complete text on the page>",
  "highlighted_passages": [
    {{
      "text": "<passage that appears highlighted, underlined, or marked>",
      "marking_type": "highlight|underline|bracket|margin_note",
      "margin_note_text": "<any handwritten text in the margin near this passage, or null>"
    }}
  ],
  "suggested_highlight": {{
    "text": "<the single most important passage on this page that the reader did NOT mark>",
    "reason": "<1-sentence explanation of why this passage matters to the book's argument>"
  }},
  "elaborative_prompt": "<a 'why' question about the most interesting passage on this page>"
}}

If there are no visible markings, return an empty highlighted_passages array.
If the page has no clearly important unmarked passage, set suggested_highlight to null.
"""
```

**Server endpoint modification** (`research-server.py`):

```python
@app.route('/book/smart-capture', methods=['POST'])
def smart_capture():
    image_data = request.files['image'].read()
    book_info = json.loads(request.form['book_info'])

    prompt = SMART_PAGE_PROMPT.format(
        title=book_info['title'],
        author=book_info['author'],
        chapter=book_info.get('chapter', 'unknown')
    )

    result = call_vision(image_data, prompt,
                         response_mime_type="application/json")
    return jsonify(json.loads(result))
```

### UI Description

**Capture confirmation screen** (replaces current simple confirmation):

The screen that appears after photographing a page. Currently shows a simple "Capture saved" message. Enhanced version:

**Top**: Page photo thumbnail (tappable to view full size)

**Middle section**: Extracted content in three parts:
1. **Your markings** (if detected): Each highlighted/underlined passage shown as a claim card with 2px rubric left border. Margin notes shown in DM Sans italic below the passage they annotate.
2. **Suggested highlight** (if generated): A single passage card with dashed left border and a subtle "You might find this important" label in textMuted. Below it, a one-line reason in Crimson Pro italic.
3. **Elaborative prompt**: In EB Garamond, a question about the page: "Why does the author distinguish between fortune and virtù here?"

**Bottom**: Three actions:
- [Save & Continue] — saves captures, returns to book detail
- [Record voice note 🎤] — transitions to voice capture with the elaborative prompt visible
- [Edit] — lets user modify extracted text, add/remove highlights

**Auto progress update**: If page number was extracted, a subtle toast at top: "Progress updated: page 47 of 312"

### User Journey

1. Stian is reading "The Prince" on the couch. He underlines a passage about fortune
2. He opens Petrarca, taps the book, taps "Capture", photographs the page
3. The app sends the photo to `/book/smart-capture` (1-2 seconds processing)
4. The confirmation screen shows:
   - His underlined passage detected and displayed
   - A "suggested highlight" for a passage about virtù he didn't mark
   - A question: "Why does Machiavelli claim fortune controls only half our actions?"
5. He taps "Save & Continue" (fast path) — or taps the mic to record a 20-second voice note responding to the question
6. Progress auto-updates to page 47
7. Total interaction time: 15-30 seconds for photo-only, 45-60 seconds with voice note

### Data Requirements for Testing

**Annotation detection accuracy**: Need 30+ page photos with visible markings (highlights, underlines, margin notes) to measure precision/recall. Grade each detection manually. Target: >80% precision, >60% recall (underlines are harder than highlights).

**Page number accuracy**: Need 50+ page photos. Page numbers are usually bottom-center or top-corner. Grade each extraction. Target: >90% accuracy. Track failure modes (no visible number, OCR misread, header page numbers vs. content page numbers).

**Suggested highlight engagement**: Track `suggested_highlight_saved` events. Of pages where a suggested highlight is shown, does the user save it? Target: >20% save rate. Need 50+ suggested highlights shown to measure.

**A/B test possibility**: Not practical for single user. Instead, compare behavior across books: first book uses basic OCR, second book uses smart processing. Compare capture frequency, voice note rate, and engagement depth.

**Metrics to log**:
- `smart_capture_processed`: { book_id, page_number_detected: boolean, markings_count, suggested_highlight_shown: boolean, elaborative_prompt_shown: boolean, processing_time_ms }
- `suggested_highlight_saved`: { capture_id }
- `suggested_highlight_dismissed`: { capture_id }
- `elaborative_prompt_voice_response`: { capture_id, duration_ms }
- `auto_progress_updated`: { book_id, page_from, page_to }

---

## Experiment 3: Voice-First Capture with Self-Explanation Prompts

### Hypothesis

Prompting users with a targeted self-explanation question after capture will:
- (H3a) Increase voice note rate from <20% to >50% of captures
- (H3b) Produce captures that are recalled 30%+ better at 2-week prompted recall vs. unprompted captures
- (H3c) Generate higher-quality atomic claims than OCR-only captures (measured by LLM judge)

### Research Backing

- **Self-explanation effect**: Meta-analysis across 64 studies, 6,000 participants: g=0.55 — explaining material to yourself significantly improves learning ([Bisra et al., 2018](https://www.researchgate.net/publication/324214361))
- **Production effect**: Speaking aloud improves memory 10-20% over silent reading ([MacLeod et al., 2010](https://uwaterloo.ca/memory-attention-cognition-lab/sites/default/files/uploads/files/jep10.pdf))
- **Generation effect**: Self-generated content is better remembered because it activates semantic elaboration, distinctive processing, and effortful retrieval ([Structural Learning](https://www.structural-learning.com/post/generation-effect-active-learning))
- **Voice > typed notes for conceptual understanding**: Voice note-taking produced higher conceptual understanding than typing in controlled study (n=60) ([Kang et al., 2020](https://arxiv.org/abs/2012.02927))
- **AudioPen**: Commercially proven that "rambling voice → structured text" pipeline works ([audiopen.ai](https://www.audiopen.ai/))

### Algorithm

**Prompt selection logic** (client-side, in capture flow):

```typescript
function getExplanationPrompt(
  book: PhysicalBook,
  capture: BookCapture,
  priorCaptures: BookCapture[]
): string {
  const chapterCaptures = priorCaptures.filter(
    c => c.chapter === capture.chapter
  );
  const otherBookCaptures = priorCaptures.filter(
    c => c.book_id !== capture.book_id
  );

  // First capture from this chapter → broad framing
  if (chapterCaptures.length === 0) {
    return `What's the main argument or idea in this passage?`;
  }

  // Has prior captures in same chapter → connection prompt
  if (chapterCaptures.length > 0 && chapterCaptures.length < 5) {
    const lastCapture = chapterCaptures[chapterCaptures.length - 1];
    const lastSnippet = (lastCapture.ocr_text || lastCapture.transcript || '')
      .slice(0, 60);
    return `How does this connect to your earlier capture: "${lastSnippet}..."?`;
  }

  // 5+ captures in chapter → synthesis prompt
  if (chapterCaptures.length >= 5) {
    return `What would you say is the chapter's central argument so far?`;
  }

  // Has captures from other books → cross-book prompt
  // (only if server has computed similarity matches)
  if (otherBookCaptures.length > 0) {
    return `Does this remind you of anything from your other reading?`;
  }

  // Fallback
  return `Why did this passage strike you?`;
}
```

**Claim extraction pipeline** (server-side, async after capture upload):

```python
VOICE_CLAIM_PROMPT = """The reader captured this from "{title}" by {author} (Ch. {chapter}):

Page text (OCR): {ocr_text}

Reader's voice note: {transcript}

Extract 1-3 atomic claims from what the READER found interesting or important.
Each claim should be a single declarative sentence.
Prefer claims that capture the reader's interpretation, not just the author's words.

Return JSON: {{ "claims": ["claim1", "claim2"] }}
"""
```

### UI Description

**Capture flow** (after photo/text capture, before save):

The current capture flow is: take photo → save. The enhanced flow inserts one screen:

**The prompt screen**: A half-sheet modal (covers bottom 60% of screen) with:
- **Top**: The capture preview (photo thumbnail or text snippet)
- **Middle**: The self-explanation prompt in Crimson Pro 16px, centered
- **Bottom**: Two options side by side:
  - [🎤 Respond] — large, rubric-colored, inviting. Starts voice recording immediately on tap. Recording indicator pulses. Tap again to stop.
  - [Skip →] — small, textMuted, right-aligned. No judgment — this is optional.

**During recording**: The prompt stays visible. A waveform animation replaces the buttons. Tap anywhere to stop.

**After recording**: Brief "Processing..." (Soniox transcription, 1-2s), then:
- Transcript appears below the prompt
- [Save capture + note ✓] button appears

**Key design decision**: The prompt screen should feel like a gentle invitation, not an obligation. The "Skip" option is always visible and easy to reach. The goal is to get voice responses on 50%+ of captures, not 100%.

### User Journey

1. Stian photographs a page from "Mahomet et Charlemagne" about Mediterranean trade
2. The prompt screen slides up: "What's the main argument in this passage?"
3. He taps 🎤 and speaks for 18 seconds: "Pirenne is arguing that trade continued through the Germanic invasions — the evidence is papyrus imports from Egypt. This is the setup for his bigger claim that Islam, not the barbarians, broke the ancient world."
4. Soniox transcribes in 1.5 seconds
5. He taps "Save capture + note"
6. Server-side: LLM extracts claims from both the OCR text and his voice note:
   - "Mediterranean trade continued through Germanic invasions" (from OCR)
   - "Papyrus imports from Egypt prove continued Eastern contact" (from OCR)
   - "Pirenne uses trade continuity as setup for his Islam-as-rupture thesis" (from voice — captures the reader's interpretive framing)
7. These claims are embedded and become available for Reading Echoes and Cross-Source Synthesis

### Data Requirements for Testing

**Voice note adoption rate**: Track across 50+ captures. Measure: what % include a voice note when prompted vs. baseline (current captures without prompt). Target: >50% with prompt.

**Retention comparison**: After 2 weeks of capturing, present 10 book captures back to the reader:
- 5 with voice notes, 5 without
- For each: "What do you remember about this passage? What was the argument?"
- Rate recall quality 1-5 (self-assessment or LLM judge)
- Need minimum 5 captures in each condition for a meaningful comparison

**Claim quality comparison**: For captures with both OCR and voice:
- LLM judge rates claims extracted from OCR-only vs. OCR+voice
- Criteria: does the claim capture the reader's interpretation? Is it useful for future connections?
- Need 20+ captures with voice notes for reliable quality assessment

**Metrics to log**:
- `self_explanation_prompt_shown`: { capture_id, prompt_text, prompt_type }
- `self_explanation_recorded`: { capture_id, duration_ms, word_count }
- `self_explanation_skipped`: { capture_id }
- `claims_extracted`: { capture_id, from_ocr: number, from_voice: number, from_combined: number }

---

## Experiment 4: Constrained Capture ("Pick 3")

### Hypothesis

Forcing users to select only the 3 most important sentences from a page photo will:
- (H4a) Improve comprehension of captured content by 15%+ vs. full-page OCR captures (prompted recall at 2 weeks)
- (H4b) Produce higher-signal captures that generate better connections in Experiments 1 and 6
- (H4c) Not reduce capture frequency (the friction is productive, not discouraging)

### Research Backing

- **Constrained Highlighting** (CHI 2024, University of Waterloo, Best Paper Honorable Mention): Capping highlights to 150 words "improved reading comprehension performance by 11%-19% compared to those who highlighted without a word limit." The constraint forces readers to evaluate importance, which IS the comprehension work. ([dl.acm.org](https://dl.acm.org/doi/10.1145/3613904.3642314))
- **Selective attention and encoding**: Physical annotation produces 4x more annotations than digital, but annotation quality (not quantity) predicts retention. ([Physical vs digital annotation study](https://www.sciencedirect.com/science/article/pii/S2590291121001224))
- **Generation effect**: Making a selection decision is itself a generative act — evaluating, comparing, prioritizing ([Structural Learning](https://www.structural-learning.com/post/generation-effect-active-learning))

### Algorithm

```
After page photo OCR:
  1. Split full_text into sentences using NLP sentence boundary detection
  2. Display sentences in scrollable list
  3. User taps up to 3 sentences (each toggles highlight state)
  4. On save: only highlighted sentences become the capture's extracted_ideas[]
  5. Optional: after user selects 3, show 1 LLM-suggested sentence they missed
     - Computed by: send full_text to LLM, ask for "the most important
       sentence the reader did NOT select", with reason
  6. Store: { selected_sentences: string[], suggested_sentence?: string,
     suggested_accepted: boolean }
```

**Sentence boundary detection**: Use a simple regex-based splitter client-side (split on `.!?` followed by space + uppercase). For complex text (academic, multilingual), fall back to LLM splitting server-side.

### UI Description

**Selection screen** (replaces simple OCR display):

**Top**: Page photo thumbnail (20% height, tappable to zoom)

**Middle**: Scrollable list of sentences extracted from the page. Each sentence is a tappable row:
- **Unselected**: Crimson Pro 15px in textBody (#333333), no border
- **Selected**: Crimson Pro 15px in ink (#2a2420), 2px rubric left border, subtle parchment background
- **Counter**: Top-right badge: "1/3", "2/3", "3/3" — rubric colored
- When 3 are selected, remaining sentences dim to textMuted opacity

**After 3 selected**: A subtle card appears at bottom:
```
┌─ Suggested ────────────────────────────────────┐
│ You might also find this important:            │
│ "The Mediterranean remained a Roman lake       │
│ through the seventh century"                   │
│ (sets up the book's central argument)          │
│                                                │
│ [Add this too] [No thanks]                     │
└────────────────────────────────────────────────┘
```

**Bottom**: [Save 3 selections ✓] — prominent rubric button

### User Journey

1. Stian photographs a dense page from Burnett's essays on Arabic-Latin translation
2. OCR extracts 12 sentences
3. The selection screen shows all 12. He reads through them (this itself is a comprehension exercise)
4. He taps the 3 most important:
   - "Adelard of Bath translated Euclid's Elements from Arabic, not the original Greek"
   - "The translation was likely completed in Bath between 1126 and 1142"
   - "Adelard's preface reveals anxiety about his dependence on Arabic sources"
5. The counter shows "3/3". A suggested highlight appears: "The transmission path — Greek → Arabic → Latin — reversed the usual assumption of direct classical inheritance"
6. He taps "Add this too" — good, he'd missed the meta-argument
7. He saves 4 sentences. The rest of the page text is discarded
8. These 4 sentences become the capture's `extracted_ideas[]`, each embedded for future connections

### Data Requirements for Testing

**Within-subjects comparison**: Alternate between constrained and unconstrained capture across different books or chapters. After 2 weeks, test recall on 10 captures from each condition.

**Minimum data**: 20 constrained captures + 20 unconstrained captures. Prompted recall test at 2 weeks: "I'm going to show you captures you made. For each, tell me what you remember about the context and argument."

**Engagement tracking**: Does the constraint reduce capture frequency? Compare captures-per-reading-session before and after introducing the constraint. Acceptable threshold: no more than 20% reduction.

**Suggested highlight acceptance rate**: What % of suggested highlights are accepted? Target: 30-50%. If <10%, the suggestions aren't useful. If >80%, the constraint is too tight (users are just accepting the LLM's choices).

**Metrics to log**:
- `constrained_capture_completed`: { capture_id, sentences_available, sentences_selected: 3, time_to_select_ms }
- `suggested_sentence_shown`: { capture_id, sentence_text }
- `suggested_sentence_accepted`: { capture_id }
- `suggested_sentence_rejected`: { capture_id }

---

## Experiment 5: Resonance Resurfacing

### Hypothesis

Periodic re-encounters with book captures — using open-ended generative prompts on expanding intervals — will:
- (H5a) Produce richer reflections over time (measured by response length and LLM-judged quality)
- (H5b) Maintain book knowledge vitality longer than passive re-reading (Readwise-style)
- (H5c) Create a "reading journal" artifact that the user finds valuable in itself

### Research Backing

- **Spacing effect without flashcards**: Spacing benefits require expanded intervals + active processing, not the flashcard format specifically ([Rawson & Dunlosky, 2022](https://www.nature.com/articles/s44159-022-00089-1))
- **Free recall > cued recall > recognition**: Open-ended prompts promote relational processing — the kind that supports conceptual understanding. Cued recall and recognition "do not appear to enhance conceptual organization" ([Rowland, 2014](https://www.sciencedirect.com/science/article/abs/pii/S0749596X19300026))
- **SRS as attention programming**: Matuschak reframes SRS as "programming attention" — scheduling what to think about, not what to memorize ([notes.andymatuschak.org](https://notes.andymatuschak.org/Spaced_repetition_systems_can_be_used_to_program_attention))
- **"Incrementally develop inklings"**: SRS can support marination — returning to half-formed ideas, considering a few per day ([notes.andymatuschak.org](https://notes.andymatuschak.org/Spaced_repetition_may_be_a_helpful_tool_to_incrementally_develop_inklings))
- **Matuschak's Great Books problem**: "It's not details of one book that I care about, but the habits and mindsets I'm developing. Hard to externalize." Open-ended prompts address this. ([Tweet, Oct 2023](https://x.com/andy_matuschak/status/1711501772790063224))

### Algorithm

**Scheduling**:

```
For each book capture:
  - initial_interval = 7 days
  - on_engagement (response recorded):
      next_interval = current_interval * 2
      // 7d → 14d → 28d → 56d → 112d
  - on_dismiss:
      next_interval = current_interval * 1.5
      // gentler pushback: 7d → 10d → 15d → 23d
  - on_skip (no interaction):
      next_interval = current_interval * 1.2
      // slow drift: 7d → 8d → 10d → 12d → 14d
  - max_interval = 180 days (6 months)
  - after 3 consecutive skips: mark as "dormant", stop scheduling
```

**Prompt generation**:

```python
RESONANCE_PROMPTS = {
    "first_resurface": [
        "You captured this {days} days ago. What do you remember about why it struck you?",
        "What was the argument this passage was supporting?",
    ],
    "second_resurface": [
        "Has your thinking about this changed since you first read it?",
        "Where have you encountered this idea since reading it?",
    ],
    "later_resurface": [
        "Looking back, how does this connect to your current reading?",
        "If you were explaining this idea to someone, what would you say?",
        "What would you add to this note now that you didn't think of then?",
    ],
    "cross_book": [  # when a connection to another book exists
        "You also captured something related from '{other_book}'. How do these two authors differ?",
        "This idea appears in both '{book}' and '{other_book}'. Which treatment do you find more compelling?",
    ]
}
```

**Selection** (which captures to resurface today):

```
daily_resurface():
  1. Get all captures where next_resurface_date <= today
  2. Exclude "dormant" captures
  3. Sort by: priority = (days_overdue * 2) + (has_cross_book_match * 3) + (has_voice_note * 1)
  4. Select top 5
  5. For each, select prompt based on resurface_count and context
```

### UI Description

**Access point**: A "Resonance" section on the Library tab (or accessible from ✦ drawer). Shows a count badge when captures are due.

**Resurfacing screen**: One capture at a time, swipeable. Each card:

**Top**: Book cover thumbnail (left) + book title and chapter in EB Garamond (right) + "Captured {N} days ago" in DM Sans textMuted

**Middle**: The capture content:
- Page photo: displayed at 40% width, tappable to zoom
- OCR text or typed text: Crimson Pro 15px
- Voice note transcript (if any): DM Sans italic, textSecondary

**Below capture**: The resonance prompt in EB Garamond 16px, rubric color

**Bottom actions** (three columns):
- [🎤 Respond] — records a voice response (saved as a new linked capture with type 'reflection')
- [💭 Skip] — schedules further out, moves to next card
- [🔗 Connect] — shows a picker of recent captures/articles to link to

**After responding**: A brief "Response saved" toast. The response appears below the prompt as a new entry in the capture's "reflection thread." Over time, this thread becomes a journal of evolving thought about a single passage.

**If cross-book match exists**: An additional card appears between capture and prompt:
```
┌─ Also from your reading ──────────────────────┐
│ 📖 "Discourses on Livy" (Ch. 4):             │
│ "Republican virtue requires moral consistency" │
│                                               │
│ Similarity: extends your capture above        │
└───────────────────────────────────────────────┘
```

### User Journey

**Week 1**: Stian captures 8 passages from "The Prince" over 4 reading sessions.

**Day 8**: Resonance badge appears on Library tab: "3 captures to revisit." He taps in:
- **Card 1**: His photo of the fortune passage. Prompt: "You captured this 8 days ago. What do you remember about why it struck you?" He records: "This is where Machiavelli first introduces the tension between skill and luck — I think his real argument is that fortune only matters if you're unprepared." (23 seconds)
- **Card 2**: A text note about virtù. He taps "Skip" — doesn't feel like engaging with this one right now. Scheduled for day 12.
- **Card 3**: A voice note about the prudence argument. Prompt: "What was the argument this passage was supporting?" He skips this too.

**Day 15**: 2 captures resurfaced (card 1 returns, plus card 2 from day 12). Card 1's prompt has evolved: "Has your thinking about this changed since you first read it?" He responds: "Actually, after reading Pirenne, I see that Machiavelli's concept of fortune has a much broader geopolitical dimension than I initially thought."

**Day 30**: Card 1 returns again. Prompt: "Looking back, how does this connect to your current reading?" By now he's reading Pirenne and the connection to Mediterranean geopolitics feels obvious. His reflection thread for this single capture now has 3 entries spanning 22 days.

**Month 3**: The capture is in "dormant" status (he skipped the last 3 resurfacings). But if Experiment 1 (Reading Echoes) surfaces it during article reading, the dormant flag resets and it re-enters the resurfacing cycle.

### Data Requirements for Testing

**Adoption**: Track over 4 weeks minimum. Key metric: response rate (# responses / # shown). Target: >30% response rate sustained over 4 weeks.

**Response richness**: LLM judge rates each response on a 1-5 scale for: (a) specificity, (b) connection to other ideas, (c) personal reflection depth. Track whether richness increases over resurfacing cycles.

**Retention comparison**: Prompted recall test at 8 weeks. Compare retention for captures that received resonance resurfacing vs. captures that did not (control group: captures from a period before the feature was built).

**Minimum data**: 30+ captures across 2+ books. 4 weeks of resurfacing. ~90 resurfacing events (30 captures × ~3 resurfacings each).

**Metrics to log**:
- `resonance_shown`: { capture_id, resurface_count, prompt_type, days_since_capture }
- `resonance_responded`: { capture_id, response_type: 'voice'|'text', response_length, duration_ms }
- `resonance_skipped`: { capture_id, resurface_count }
- `resonance_connected`: { capture_id, connected_to_id, connection_type }
- `resonance_dormant`: { capture_id, total_resurfaces, total_responses }

---

## Experiment 6: Cross-Source Synthesis

### Hypothesis

Connecting book captures to article claims via embedding similarity will:
- (H6a) Surface useful cross-source connections in >50% of books with 5+ captures
- (H6b) Create a sense of "growing understanding" (measured by user self-report)
- (H6c) Increase article engagement with articles that connect to books (longer dwell time, more claim signals)

### Research Backing

- **Pirolli & Card sensemaking model**: The critical bottleneck is moving from "shoebox" (raw collection) to "evidence file" (organized evidence) to "schema" (structured understanding). Most tools only support the shoebox. ([Pirolli & Card, 2005](https://andymatuschak.org/files/papers/Pirolli,%20Card%20-%202005%20-%20The%20sensemaking%20process%20and%20leverage%20points%20for%20analyst%20technology%20as.pdf))
- **Brander's feedback loop**: Every new idea should force recursion over old ideas — but the feedback loop must be automatic, not manual ([Brander, 2023](https://newsletter.squishy.computer/p/knowledge-gardening-is-recursive))
- **Appleton's growth stages**: Captures evolve from seedlings (raw) to budding (reflected upon) to evergreen (connected across sources). Making this visible motivates deeper engagement. ([Appleton, Digital Gardens](https://maggieappleton.com/garden/))
- **Threddy** (UIST 2022): Threads connecting captures across documents reduce context-switching cost and support multi-document sensemaking ([dl.acm.org](https://dl.acm.org/doi/10.1145/3526113.3545660))
- **Passages** (CHI 2022): Reified text objects with provenance enable cross-document connections ([dl.acm.org](https://dl.acm.org/doi/10.1145/3491102.3502052))

### Algorithm

**Batch matching** (server-side, runs after new captures are embedded):

```python
def find_cross_source_connections(book_id: str):
    """Find article claims that match this book's captures."""
    book_embeddings = load_book_capture_embeddings(book_id)
    article_embeddings = load_claim_embeddings()  # existing 4,500+

    connections = []
    for i, cap_emb in enumerate(book_embeddings):
        sims = cosine_similarity(cap_emb.reshape(1, -1), article_embeddings)[0]

        # Find top matches above EXTENDS threshold
        matches = np.where(sims >= 0.68)[0]
        for match_idx in matches:
            connections.append({
                'capture_id': book_captures[i]['id'],
                'article_claim_id': article_claims[match_idx]['id'],
                'article_id': article_claims[match_idx]['article_id'],
                'article_title': article_claims[match_idx]['article_title'],
                'claim_text': article_claims[match_idx]['text'],
                'similarity': float(sims[match_idx]),
                'relationship': classify_relationship(sims[match_idx])
                    # >= 0.78: 'known', >= 0.68: 'extends', else: 'new'
            })

    # Deduplicate: keep top match per article
    best_per_article = {}
    for c in connections:
        key = c['article_id']
        if key not in best_per_article or c['similarity'] > best_per_article[key]['similarity']:
            best_per_article[key] = c

    return sorted(best_per_article.values(),
                  key=lambda x: x['similarity'], reverse=True)[:10]
```

**Growth stage computation**:

```python
def compute_capture_growth_stage(capture: dict, connections: list, reflections: list) -> str:
    has_voice = bool(capture.get('transcript'))
    has_connections = any(c['capture_id'] == capture['id'] for c in connections)
    has_reflections = any(r['parent_capture_id'] == capture['id'] for r in reflections)

    if has_connections or has_reflections:
        return 'evergreen'  # connected to other sources or reflected upon
    elif has_voice:
        return 'budding'    # has voice self-explanation
    else:
        return 'seedling'   # raw photo/text only
```

### UI Description

**Book detail screen** — new "Connections" section (below existing captures list):

```
═══════════════════════════════════════════
✦ Connections to Your Reading
═══════════════════════════════════════════

This book connects to 4 articles in your feed:

┌───────────────────────────────────────────┐
│ "Mediterranean Trade in Late Antiquity"   │
│ Your capture (p. 47): "Trade continued    │
│ through Germanic invasions..."            │
│ ↔ Article claim: "Commercial networks     │
│ persisted until the 7th century"          │
│ Similarity: extends                       │
│                              [Read →]     │
├───────────────────────────────────────────┤
│ "Sicily's Norman Heritage"                │
│ Your capture (p. 112): "The Normans       │
│ inherited Arabic administrative..."       │
│ ↔ Article claim: "Norman Sicily blended   │
│ Arabic and Latin governance"              │
│ Similarity: known (same idea)             │
│                              [Read →]     │
└───────────────────────────────────────────┘
```

**Book map** (new tab or toggle on book detail screen):

A visual cluster view showing captures grouped by topic (not chapter):
- Each cluster is a pill-shaped group with a topic label
- Inside each cluster: small circles representing captures
- Circle fill indicates growth stage: hollow (seedling), half-filled (budding), filled (evergreen)
- Lines connect clusters that share topic tags
- Articles appear as squares at the edges, connected to matching clusters

This is a simple force-directed layout, not a full knowledge graph. Max 30 nodes visible. Focus+context: tap a cluster to see its captures.

### User Journey

1. Stian has been reading "Mahomet et Charlemagne" for 2 weeks, making 15 captures
2. The server runs the cross-source matching pipeline overnight
3. Next morning, the book detail screen shows: "✦ Connections to Your Reading (4 articles)"
4. He taps into the connections section and sees that 3 of his captures about Mediterranean trade match articles he read weeks ago about Roman commerce and Norman Sicily
5. He taps "Read →" on the Sicily article — the article reader opens, and Reading Echoes (Experiment 1) highlight the matched passages
6. On the book map view, he sees his captures clustered into 3 topic groups: "Mediterranean trade" (5 captures, 3 evergreen), "Germanic invasions" (4 captures, all seedlings), "Islam as rupture" (6 captures, 2 budding)
7. The "Germanic invasions" cluster is all seedlings — he hasn't voice-noted or reflected on those captures. This motivates him to revisit them

### Data Requirements for Testing

**Connection quality**: For each book with 5+ captures, run the matching pipeline and manually assess: are the top 5 connections genuinely meaningful? Rate each 1-5 for relevance. Target: average >3.5.

**User engagement with connections**: Track taps on connection cards, article read-throughs from connection links. Need 30+ connections surfaced across 2+ books.

**Growth stage distribution over time**: Track how captures move from seedling → budding → evergreen. After 4 weeks, target: <50% still seedlings (indicating the system is prompting deeper engagement).

**Minimum data**: 2 books with 10+ captures each, 50+ articles with embeddings. The existing 4,500 claims provide the article side; the book side needs real captures.

**Metrics to log**:
- `cross_source_connections_computed`: { book_id, total_connections, unique_articles_matched }
- `connection_card_tapped`: { capture_id, article_id, similarity }
- `connection_article_read`: { article_id, source: 'book_connection', dwell_time_ms }
- `book_map_viewed`: { book_id, clusters_shown, captures_shown }
- `growth_stage_changed`: { capture_id, from_stage, to_stage, trigger }

---

## Experiment 7: Context Restoration ("Story So Far")

### Hypothesis

Showing a personalized "Story So Far" briefing when returning to a book after 48+ hours will:
- (H7a) Reduce time-to-first-interaction from >60s to <30s
- (H7b) Increase capture quality in the subsequent reading session (longer voice notes, more connections)
- (H7c) Increase reading session frequency (by lowering the "where was I?" barrier)

### Research Backing

- **Reviews and Previews** (CHI 2021): Showing previews after reading interruptions improved comprehension on subsequent sections. Users preferred reviews (what they'd already read) but previews (what's coming next) were more effective. Best: a combination. ([dl.acm.org](https://dl.acm.org/doi/fullHtml/10.1145/3411763.3451610))
- **Context-dependent memory**: Recall improves when retrieval context matches encoding context. Seeing your own highlights and annotations reinstates the cognitive state of the original reading session. ([Simply Psychology](https://www.simplypsychology.org/context-and-state-dependent-memory.html))
- **Spatial memory and page position**: Readers encode page position as a memory cue. Removing spatial cues (e.g., scrolling vs. paginated reading) significantly lowers recall. Page photo thumbnails serve as spatial reinstatement cues. ([Zechmeister et al., Springer](https://link.springer.com/article/10.3758/BF03196979))
- **Priming at Scale** (CHI 2025): AI-generated "primes" (contextual previews) improved reading speed by 7% and aided interruption recovery. ([dl.acm.org](https://dl.acm.org/doi/10.1145/3706599.3720153))
- **No mainstream app solves this**: Kindle drops you at last position with zero context. Audible offers chapter recaps for fiction only. Kairos has the best current implementation with AI catch-up summaries. ([Every.to](https://every.to/source-code/a-new-way-to-read))

### Algorithm

**Trigger logic**:

```typescript
function shouldShowStorysoFar(book: PhysicalBook): boolean {
  const hoursSinceLastInteraction =
    (Date.now() - book.last_interaction_at) / (1000 * 60 * 60);
  const hasCaptures = getBookCaptures(book.id).length > 0;
  return hoursSinceLastInteraction >= 48 && hasCaptures;
}
```

**Content generation** (server-side, can be pre-computed):

```python
STORY_SO_FAR_PROMPT = """The reader is returning to "{title}" by {author} after {days} days away.

Their reading position: {chapter}, page {page} of {total_pages}.

Their captures so far (chronological):
{captures_formatted}

Generate a "Story So Far" briefing with:
1. ARGUMENT_SUMMARY: 2-3 sentences summarizing the book's argument up to where the reader stopped, based on their captures. Emphasize what the READER found interesting (based on their captures and voice notes), not a generic summary.
2. THREAD: Pick the 2 most interesting captures and explain why they matter to the book's developing argument.
3. PREVIEW: 1 sentence hinting at what's coming in the next chapter (based on the book's known structure/topic).

Return JSON: {{
  "argument_summary": "...",
  "thread": [{{ "capture_id": "...", "why_it_matters": "..." }}],
  "preview": "..."
}}
"""
```

### UI Description

**Trigger**: When user taps a book on the Library tab and `shouldShowStorySoFar()` returns true, this screen appears INSTEAD of the book detail screen. After dismissal, the normal book detail screen loads.

**Layout**:

**Top section** (20% height):
- Book cover (left, 60px wide)
- Title + author in EB Garamond
- "Last read: {N} days ago" in DM Sans textMuted
- Double rule below

**Middle section** (60% height, scrollable):

**"Your reading so far"** section marker (✦ rubric):
- Argument summary in Crimson Pro 15px — 2-3 sentences, based on the reader's captures
- This is NOT a generic book summary. It reflects what the reader captured and found interesting.

**"Your captures"** section:
- 2-3 most recent captures shown as compact cards:
  - Page photo thumbnail (if photo capture) — tappable to zoom
  - Text excerpt (if text/OCR capture) — 2 lines max
  - Voice note indicator (if voice capture) — with play button
  - Below each: the "why it matters" context in DM Sans italic textSecondary

**"Since you've been away"** section (only if applicable):
- "{N} articles in your feed touch on related themes" — with tappable article titles
- "{N} captures from other books connect to this one" — if cross-book matches exist

**"Coming up"** section:
- 1 sentence preview of the next chapter in Crimson Pro italic

**Bottom** (20% height):
- [Resume reading →] — large rubric button, navigates to book detail
- [Review all captures] — secondary button, opens capture list

### User Journey

1. Stian hasn't opened "Mahomet et Charlemagne" for 5 days (busy with work)
2. He taps the book on the Library tab
3. Instead of the normal book detail, the Story So Far screen appears:

   > **Your reading so far**
   > You've been following Pirenne's argument that Mediterranean trade survived the Germanic invasions. Your captures focused on evidence from papyrus imports and Syrian merchants. Your voice note from day 3: "The papyrus argument is clever — physical evidence of trade routes."
   >
   > **Your captures** (showing 2 of 7)
   > [Photo of page 47: highlighted passage about papyrus]
   > _This is the key evidence for Pirenne's continuity thesis — it connects to what you'll read about Islamic disruption in Part II._
   >
   > [Voice note, 0:23: "I wonder if Burnett has evidence from the translation side"]
   > _This question will be answered when you read Burnett — the cross-book connection is already flagged._
   >
   > **Since you've been away**
   > 2 articles in your feed touched on Mediterranean trade
   >
   > **Coming up**
   > Part II begins Pirenne's central claim: Islam, not Germanic invasions, ended the ancient world.

4. He feels re-oriented in 15 seconds. Taps "Resume reading" and opens directly to the book detail screen, ready to continue.

### Data Requirements for Testing

**Time-to-first-interaction**: Measure time from tapping the book to first capture in the subsequent session. Compare: sessions with Story So Far shown vs. sessions without (gap < 48h, no restoration needed). Target: <30 seconds with restoration vs. >60 seconds without.

**Session quality**: Compare capture richness (voice note rate, extracted ideas count, capture frequency) in sessions immediately after restoration vs. sessions without. Prediction: restoration sessions produce richer captures because the reader is cognitively "warmed up."

**Return rate**: Does seeing a well-crafted Story So Far increase the probability of returning to a book? Track: after a 5+ day gap, how many days until next session? Compare books read before the feature (baseline) vs. after.

**Minimum data**: 3+ books with 5+ captures each. 10+ "return after gap" events over 6 weeks. This is a natural experiment — gaps happen organically.

**Metrics to log**:
- `story_so_far_shown`: { book_id, days_since_last, captures_shown, articles_connected }
- `story_so_far_resume_tapped`: { book_id, dwell_time_on_restoration_ms }
- `story_so_far_review_captures_tapped`: { book_id }
- `post_restoration_session`: { book_id, captures_made, voice_notes_made, session_duration_ms }

---

## Experiment 8: Chapter Digest + Evolving Understanding

### Hypothesis

Prompted synthesis at chapter boundaries, combined with evolving digests as related content is encountered, will:
- (H8a) Generate a "reading journal" artifact that the user revisits (>50% of digests viewed again within 30 days)
- (H8b) Improve reconstruction of the book's argument at 3-month recall vs. captures without digests
- (H8c) Demonstrate visible "knowledge growth" — digests become richer over time as connections accumulate

### Research Backing

- **"Knowledge should accrue"**: Matuschak argues every reading session should produce persistent, interconnected artifacts that compound in value. ([notes.andymatuschak.org](https://notes.andymatuschak.org/Knowledge_work_should_accrue))
- **Sensemaking progression**: Pirolli & Card identify the critical transition from raw collection to structured understanding. Chapter digests are the mechanism that forces this transition. ([Pirolli & Card, 2005](https://andymatuschak.org/files/papers/Pirolli,%20Card%20-%202005%20-%20The%20sensemaking%20process%20and%20leverage%20points%20for%20analyst%20technology%20as.pdf))
- **Generation effect at boundaries**: Generating a summary at a natural pause point forces elaborative retrieval of the entire chapter's argument ([Karpicke & Blunt, 2011](https://www.science.org/doi/10.1126/science.1199327))
- **Progressive Summarization done right**: Unlike Forte's layer-on-layer approach (criticized as "creating parrots"), chapter digests prompt the reader to synthesize in their own words, then evolve the synthesis over time. ([Nick Milo critique](https://medium.com/@nickmilo22/why-progressive-summarization-must-die-c2635d1f79f1))

### Algorithm

**Chapter completion detection**:

```typescript
function detectChapterCompletion(
  book: PhysicalBook,
  newPage: number,
  newChapter: string
): boolean {
  // Detect if the reader has moved to a new chapter
  return book.current_chapter !== undefined
    && newChapter !== book.current_chapter
    && getBookCaptures(book.id)
         .filter(c => c.chapter === book.current_chapter).length > 0;
}
```

**Digest generation** (server-side):

```python
CHAPTER_DIGEST_PROMPT = """The reader just finished chapter "{chapter}" of "{title}" by {author}.

Their captures from this chapter:
{captures_formatted}

Generate a chapter digest:
1. CHAPTER_ARGUMENT: 2-3 sentences summarizing the chapter's argument, emphasizing what the reader captured (their captures reveal what they found important).
2. KEY_CLAIMS: Extract 3-5 atomic claims from the captures.
3. CONNECTIONS_TO_PRIOR: How this chapter's argument connects to earlier chapters (based on the reader's prior chapter digests, if any).
4. OPEN_QUESTIONS: 1-2 questions that remain unanswered, based on what the reader captured.
5. READER_PROMPT: A single question for the reader: "In your own words, what was this chapter really about?"

Return JSON.
"""
```

**Evolution pipeline** (runs weekly in content-refresh.sh):

```python
def evolve_chapter_digests():
    """Update chapter digests with new connections from articles."""
    for digest in all_chapter_digests:
        # Find new article connections since last evolution
        new_connections = find_new_article_connections(
            digest['key_claims'],
            since=digest['last_evolved_at']
        )
        if new_connections:
            evolution_prompt = f"""
            This chapter digest was created {days_ago} days ago:
            {digest['summary']}

            Since then, the reader has encountered {len(new_connections)} articles
            that connect to this chapter's ideas:
            {format_connections(new_connections)}

            Update the digest with a new "ENRICHMENT" section:
            1-2 sentences noting how the reader's understanding has grown.
            """
            enrichment = call_llm(evolution_prompt)
            digest['enrichments'].append({
                'date': today,
                'text': enrichment,
                'article_connections': new_connections
            })
            digest['last_evolved_at'] = today
```

### UI Description

**Chapter completion prompt** (triggered when user updates reading position to a new chapter):

A full-screen modal with soft parchment background:

**Top**: "✦ Chapter {N} complete" in EB Garamond, rubric color

**Middle**:
- "You made {N} captures in this chapter. Here they are together:"
- Compact list of capture cards (photo thumbnails, text snippets, voice note indicators)
- Below the captures: the LLM-generated chapter summary in Crimson Pro

**Bottom**:
- The reader prompt in EB Garamond: "In your own words, what was this chapter really about?"
- [🎤 Record summary] — starts voice recording
- [Type summary] — opens text input
- [Skip for now →] — closes modal, saves LLM digest without reader summary

**Chapter digest card** (on book detail screen):

Each completed chapter shows a digest card:
```
┌─ Ch. 3: "The Eastern Influence" ──────────────┐
│ Your summary: "Pirenne argues that Byzantine   │
│ cultural influence persisted in the West..."   │
│                                                │
│ ★ Enriched Mar 22:                             │
│ 2 articles connected to this chapter's ideas   │
│ about Byzantine cultural influence.            │
│                                  [Expand →]    │
└────────────────────────────────────────────────┘
```

The ★ indicator appears when new enrichments arrive. Tapping "Expand" shows the full digest with all enrichments, connections, and the reader's original summary.

### User Journey

**Day 1-7**: Stian reads Chapter 3 of Pirenne, making 5 captures.

**Day 7**: He updates his reading position to Chapter 4. The chapter completion modal appears:
- Shows his 5 captures together
- LLM digest: "Pirenne argues that Byzantine cultural influence — church architecture, literacy, Greek scholarly tradition — persisted in the West through the 7th century, proving his continuity thesis extends beyond just trade."
- He records a 25-second voice summary: "The key insight is that Pirenne isn't just talking about trade anymore — culture and intellectual life also survived. This makes the Part II bombshell about Islam stronger."

**Day 14**: The weekly evolution pipeline runs. 2 articles from the feed matched claims from Chapter 3's digest. The digest card now shows: "★ Enriched: 2 articles connected — one about Byzantine church architecture in Ravenna, one about Greek manuscripts in Irish monasteries."

**Day 30**: Stian revisits the Chapter 3 digest. It now has 2 enrichment layers. He re-reads his original summary and the enrichments, then records a new reflection: "The Irish monastery connection is fascinating — Pirenne doesn't mention this at all, but it supports his argument from a completely different angle."

**Month 3**: He's finished the book. The book detail screen shows digests for all 9 chapters, some with 3-4 enrichment layers. Together, they form a "reading journal" that shows both the book's argument and the reader's evolving understanding of it.

### Data Requirements for Testing

**Reader summary adoption**: What % of chapter completions get a voice/text summary? Target: >40%. Need 10+ chapter completions across 2+ books.

**Enrichment rate**: How often do articles connect to chapter digests? Depends on capture density and article corpus overlap. Track weekly. Target: at least 1 enrichment per digest per month.

**Revisit rate**: Do users return to digests? Track `digest_viewed` events. Target: >50% of digests viewed at least once after creation.

**Argument reconstruction**: At 3 months post-book-completion, prompt the reader: "Can you reconstruct the argument of [Book], chapter by chapter?" Compare accuracy for books with digests vs. books without.

**Minimum data**: 2 books read to completion (or at least 3 chapters each), 10+ chapter completions with captures, 4+ weeks for enrichment evolution. This is the longest experiment — needs 3+ months of real usage.

**Metrics to log**:
- `chapter_digest_generated`: { book_id, chapter, captures_count, reader_summary: boolean }
- `chapter_digest_reader_summary`: { book_id, chapter, type: 'voice'|'text', duration_ms, word_count }
- `chapter_digest_skipped`: { book_id, chapter }
- `chapter_digest_enriched`: { book_id, chapter, articles_connected, enrichment_text }
- `chapter_digest_viewed`: { book_id, chapter, days_since_creation }

---

## Dependency Graph

```
Experiment 2 (Smart Photos) ─── no dependencies ──────── Phase 1
Experiment 3 (Voice Prompts) ── no dependencies ──────── Phase 1
         │
         ▼
Experiment 4 (Pick 3) ──────── needs Exp 2 (OCR text) ── Phase 4
         │
         ▼ (captures produce embeddings)
Experiment 1 (Reading Echoes) ─ needs capture embeddings ─ Phase 2
Experiment 6 (Cross-Source) ─── needs capture embeddings ─ Phase 2
         │
         ▼ (connections feed scheduling)
Experiment 5 (Resonance) ────── needs captures, optional connections ── Phase 3
Experiment 7 (Story So Far) ─── needs captures ──────────────────────── Phase 3
         │
         ▼ (digests use connections + captures)
Experiment 8 (Chapter Digest) ─ needs captures + connections ─ Phase 4
```

## Total Data Requirements Summary

| Experiment | Minimum Books | Minimum Captures | Time to First Signal | Time to Statistical Confidence |
|-----------|--------------|-----------------|---------------------|-------------------------------|
| 1. Reading Echoes | 1 | 10 | 2 weeks | 6 weeks |
| 2. Smart Photos | 1 | 30 photos | Immediate | 2 weeks |
| 3. Voice Prompts | 1 | 50 captures | 1 week | 4 weeks |
| 4. Pick 3 | 1 | 40 captures (20+20) | 2 weeks | 4 weeks |
| 5. Resonance | 2 | 30 | 4 weeks | 8 weeks |
| 6. Cross-Source | 2 | 20 (10 per book) | 1 week | 4 weeks |
| 7. Story So Far | 3 | 15 (5 per book) | 1 gap event | 6 weeks (10+ gaps) |
| 8. Chapter Digest | 2 | 30+ | 1 chapter done | 3 months |

**Practical reality**: All experiments can start producing qualitative signal with a single book and 10-15 captures over 1-2 weeks. Statistical rigor requires more data and time, but for a single-user personal tool, qualitative "does this feel useful?" signals are the primary decision criteria. The metrics exist to track trends, not to run formal hypothesis tests.

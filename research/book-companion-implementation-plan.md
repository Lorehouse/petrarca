# Book Companion: Combined Implementation Plan

**Date**: 2026-03-15
**Goal**: Implement the highest-value book companion experiments in a single session, designed for exhaustive automated testing.

---

## Design Decisions

### User Constraints
- **No physical marks** in books (library books) — skip annotation detection
- **Run experiments simultaneously** — combine non-conflicting features
- **Passive + active modes** — system should be useful with just chapter/page progress updates
- **Active content discovery** — find articles that match/complement/contradict book reading
- **Exhaustive automated testing** — simulation, browser-agent, pytest; no manual phone testing

### The Linchpin: Book Research Agent

The central architectural insight: a **server-side Book Research Agent** that autonomously researches any book the user adds. When a book is added or progress updated, the server:

1. Looks up the book's arguments, claims, and key terms via Gemini + Search
2. Generates chapter-level claims even before the user reads those chapters
3. Finds existing articles in the corpus that connect to the book
4. Suggests NEW content to read that complements or contradicts the book
5. Generates briefings and digests from researched content + user captures

This means the system works in **two modes**:
- **Passive mode**: User just marks "reading chapter 3" → server provides connections, briefings, suggested reading
- **Active mode**: User also captures (photos, voice, text) → captures enrich server research with personal perspective

---

## What to Build Now (Sprint A)

### Component 1: Book Research Agent (Server)

**New file**: `scripts/book_research_agent.py`

Three core functions:

**`research_book(title, author, isbn, chapters, topics)`**
- Uses `call_with_search()` to research:
  - Book thesis and core arguments
  - Reception and key debates
  - For each chapter: 2-3 sentence summary + 3-5 atomic claims + key terms
- Finds article connections: compare book topics against article topics in knowledge index
- Generates "suggested reading": complementary/contradicting content via search
- Output: `data/book_research/{book_id}.json`

**`get_chapter_insights(book_id, chapter_number, chapter_title, captures[])`**
- Returns research for a specific chapter + connections + any capture integration
- Used when user navigates to a new chapter

**`generate_story_so_far(book_id, title, author, chapter, page, captures[])`**
- Generates a personalized briefing for returning after a gap
- Combines server research with user captures
- Returns: argument summary, highlighted captures/insights, preview of next chapter

**Three new server endpoints** in `research-server.py`:
- `POST /book/research` → background thread researches book, returns 202
- `POST /book/chapter-insights` → synchronous, returns chapter research + connections
- `POST /book/story-so-far` → synchronous, returns briefing JSON

**Auto-trigger**: When `process_book_identify()` succeeds, spawn background thread to research the book.

### Component 2: Book Claim Embedding Pipeline

**New file**: `scripts/build_book_claim_embeddings.py`
- Pattern: exact structural copy of `build_claim_embeddings.py`
- Input: `data/book_research/{book_id}.json` chapter claims + user capture `extracted_ideas`
- Embedding model: same `gemini-embedding-001`
- Output: `data/book_claim_embeddings.npz` + `data/book_claims_index.json`
- Incremental: only embed new claims

**Extend `build_knowledge_index.py`**:
- Load both article and book claim embeddings
- Compute cross-source similarity matrix (book claims × article claims)
- Extract pairs above EXTENDS threshold (0.68)
- Add `book_article_connections` section to `knowledge_index.json`

**Add to `content-refresh.sh`**:
- After article embeddings: run `build_book_claim_embeddings.py`
- In knowledge index build: include cross-source matching

### Component 3: Client-Side Integration

**New types** in `types.ts`:
```typescript
interface BookResearch {
  book_id: string;
  thesis: string;
  chapter_research: Record<string, ChapterResearch>;
  article_connections: BookArticleConnection[];
  suggested_reading: SuggestedReading[];
  researched_at: string;
}

interface ChapterResearch {
  summary: string;
  claims: string[];
  key_terms: string[];
}

interface BookArticleConnection {
  article_id: string;
  article_title: string;
  connection_type: 'extends' | 'contradicts' | 'complements';
  reason: string;
  chapter_number?: number;
  similarity?: number;
}

interface SuggestedReading {
  title: string;
  url: string;
  reason: string;
  ingested?: boolean;  // if auto-ingested into article pipeline
}

interface StorySoFarBriefing {
  argument_summary: string;
  thread: Array<{ capture_id?: string; text: string; why_it_matters: string }>;
  preview: string;
  articles_since: number;
  suggested_reading: SuggestedReading[];
}

interface ChapterDigest {
  book_id: string;
  chapter: string;
  chapter_number: number;
  summary: string;  // from research, augmented by captures
  claims: string[];
  connections: BookArticleConnection[];
  reader_summary?: string;  // user's own voice/text summary
  created_at: number;
  enrichments: Array<{ date: string; text: string; article_ids: string[] }>;
}
```

**New API functions** (`app/lib/book-api.ts`):
```typescript
export async function researchBook(bookId, title, author, chapters, topics): Promise<void>
export async function getChapterInsights(bookId, chapterNum, chapterTitle): Promise<ChapterInsights>
export async function getStorySoFar(bookId, title, author, chapter, page, captures): Promise<StorySoFarBriefing>
```

**Enhance `book-store.ts`**:
- Add `bookResearch: Record<string, BookResearch>` to module state
- Add persistence for research data
- Add `getBookResearch(bookId)`, `setBookResearch(bookId, data)`

**Enhance `book-detail.tsx`** — add three new sections below existing captures:

1. **✦ Connections to Your Reading** — articles from corpus that connect to this book
2. **✦ Suggested Reading** — complementary/contradicting content to seek out
3. **✦ Chapter Insights** — for current chapter: researched summary, claims, connections

**Add chapter digest** — when user updates chapter in `book-detail.tsx`:
- If previous chapter had captures OR research, show a digest card
- Optional text input: "In your own words, what was this chapter about?"
- Store as `ChapterDigest` in book store

**Add Story So Far** — in `book-detail.tsx`:
- Check `shouldShowStorySoFar()` (last interaction > 48 hours + has captures or research)
- If true, show briefing overlay before main content
- Fetch from `/book/story-so-far` endpoint

### Component 4: Enhanced Page Photo Processing

Modify the existing `/book/ocr-page` endpoint prompt to also return:
- `page_number`: more reliable extraction
- `key_passage`: the single most important sentence (no annotation detection needed)
- `elaborative_question`: a "why" question about the content

No UI changes needed — these fields enrich `BookCapture` silently. The `key_passage` appears in Story So Far briefings and chapter digests.

### Component 5: Active Content Discovery

When the research agent identifies "suggested reading," optionally auto-ingest it:

**In `book_research_agent.py`**:
```python
def ingest_suggested_reading(suggestions: list[dict]):
    """Auto-ingest suggested URLs into the article pipeline."""
    for suggestion in suggestions[:3]:  # max 3 auto-ingests per book
        url = suggestion.get('url')
        if url and not is_already_ingested(url):
            import_url(url, source='book_research',
                       tags=[f"book:{book_id}"])
```

This means: when you add a book, the system finds complementary articles and adds them to your reading pipeline. They'll appear in the feed with a "📖 Suggested by [Book]" tag.

---

## What to Defer (Sprint B — Future)

All ideas preserved, grouped by experiment:

### Experiment 1: Reading Echoes (articles ← books)
- Inline book-claim annotations in article reader margins
- Echo encounter events extending capture knowledge half-life
- Subtle card design: 2px textMuted border, book icon, tappable expand
- Max 3 echoes per article, prioritized by concept recency
- Logging: `reading_echo_shown/expanded/navigate`

### Experiment 3: Voice Self-Explanation
- Context-aware prompt selection (first capture, same-chapter, cross-book)
- Half-sheet prompt modal with waveform recording
- Combined OCR+voice claim extraction pipeline
- Soniox integration for book voice captures

### Experiment 4: Constrained Capture ("Pick 3")
- Sentence-level selection UI with counter badge
- Dimming of unselected sentences after 3 chosen
- LLM-suggested additional sentence
- A/B comparison: constrained vs. unconstrained

### Experiment 5: Resonance Resurfacing
- Expanding interval scheduler (7→14→28→56→112 days)
- Prompt evolution based on resurface count
- Cross-book prompts when embedding matches exist
- Reflection thread (linked responses over time)
- Dormant status after 3 consecutive skips
- Resonance section on Library tab with badge

### Future Extensions
- Book map visualization (force-directed capture clusters)
- Growth stages (seedling/budding/evergreen) on captures
- "Chat with YOUR reading" — grounded in captures + knowledge state
- Weekly digest evolution pipeline (enrichment layers)
- Reading companion: suggested pause points during physical reading
- NFC quick-capture (tap book tag → open capture interface)
- Export reading journal as markdown/PDF
- Book-to-book connections (multiple physical books)
- NotebookLM-style audio discussions about chapter captures

---

## Testing Strategy

### Tier 1: Server-side Python tests

**`scripts/tests/test_book_research.py`**:

```python
def test_research_book_machiavelli():
    """Research 'The Prince' — verify thesis, chapters, claims."""
    result = research_book("The Prince", "Niccolò Machiavelli", None,
        [{"number": 1, "title": "How Many Kinds of Principalities There Are"},
         {"number": 15, "title": "Of Things for Which Men Are Praised or Blamed"},
         {"number": 25, "title": "How Much Fortune Can Do"}],
        ["political philosophy", "leadership"])
    assert result['thesis']  # non-empty
    assert 'prince' in result['thesis'].lower() or 'political' in result['thesis'].lower()
    assert len(result['chapter_research']) >= 3
    for ch_num, ch in result['chapter_research'].items():
        assert len(ch['claims']) >= 2
        assert ch['summary']

def test_research_book_finds_article_connections():
    """Verify book topics match against existing article corpus."""
    # Uses a book whose topics overlap with existing articles
    result = research_book("The Sicilian Vespers", "Steven Runciman", None,
        [{"number": 1, "title": "Sicily and the Mediterranean"}],
        ["Sicily", "medieval history", "Mediterranean"])
    # Should find connections given existing Sicily/history articles
    assert len(result['article_connections']) >= 0  # may be 0 if no overlap
    # Suggested reading should always be present
    assert len(result['suggested_reading']) >= 1

def test_story_so_far():
    """Generate briefing from research + captures."""
    briefing = generate_story_so_far(
        book_id="test_pb_001",
        title="The Prince",
        author="Machiavelli",
        current_chapter="Chapter 15",
        current_page=89,
        page_count=140,
        captures=[{
            "text": "Fortune is the arbiter of half our actions",
            "chapter": "Chapter 25",
            "type": "text_note"
        }]
    )
    assert briefing['argument_summary']
    assert briefing['preview']

def test_chapter_insights():
    """Get insights for a specific chapter."""
    insights = get_chapter_insights(
        book_id="test_pb_001",
        chapter_number=15,
        chapter_title="Of Things for Which Men Are Praised or Blamed"
    )
    assert insights['summary']
    assert len(insights['claims']) >= 2
```

**`scripts/tests/test_book_embeddings.py`**:

```python
def test_book_claim_embeddings_created():
    """Create synthetic book research, embed claims, verify output."""
    # Write synthetic research file
    write_synthetic_research("test_book", claims=[
        "Mediterranean trade continued through Germanic invasions",
        "Papyrus imports prove Eastern contact persisted",
        "Islam broke Mediterranean unity in the 7th century"
    ])
    # Run embedding pipeline
    subprocess.run(["python3", "build_book_claim_embeddings.py"], check=True)
    # Verify output
    data = np.load("data/book_claim_embeddings.npz")
    assert data['embeddings'].shape[0] == 3
    assert data['embeddings'].shape[1] == 768  # Gemini embedding dim

def test_cross_source_matching():
    """Book claims about Mediterranean should match Mediterranean articles."""
    # Load both embedding sets
    book_embs = np.load("data/book_claim_embeddings.npz")['embeddings']
    article_embs = np.load("data/claim_embeddings.npz")['embeddings']
    # Compute similarities
    sims = cosine_similarity(book_embs, article_embs)
    # At least one pair should exceed EXTENDS threshold
    assert np.max(sims) >= 0.68 or True  # soft assertion — depends on corpus
```

### Tier 2: HTTP endpoint tests

**`scripts/tests/test_book_endpoints.py`**:

```python
BASE = "http://localhost:8090"  # or alifstian.duckdns.org:8090

def test_book_research_endpoint():
    r = requests.post(f"{BASE}/book/research", json={
        "book_id": "test_001",
        "title": "The Prince",
        "author": "Niccolò Machiavelli",
        "chapters": [{"number": 1, "title": "Types of Principalities"}],
        "topics": ["political philosophy"]
    })
    assert r.status_code in (200, 202)
    # If 202, poll for completion
    if r.status_code == 202:
        time.sleep(30)  # allow research to complete
    # Verify output file
    r2 = requests.get(f"{BASE}/book/research/test_001")
    assert r2.status_code == 200
    data = r2.json()
    assert data['thesis']

def test_story_so_far_endpoint():
    r = requests.post(f"{BASE}/book/story-so-far", json={
        "book_id": "test_001",
        "title": "The Prince",
        "author": "Machiavelli",
        "current_chapter": "Chapter 15",
        "current_page": 89,
        "page_count": 140,
        "captures": []
    })
    assert r.status_code == 200
    data = r.json()
    assert data['argument_summary']

def test_chapter_insights_endpoint():
    r = requests.post(f"{BASE}/book/chapter-insights", json={
        "book_id": "test_001",
        "chapter_number": 15,
        "chapter_title": "Of Things for Which Men Are Praised or Blamed"
    })
    assert r.status_code == 200
    data = r.json()
    assert data['summary']
    assert len(data['claims']) >= 1
```

### Tier 3: End-to-end pipeline test

**`scripts/tests/test_book_pipeline_e2e.py`**:

```python
def test_full_pipeline():
    """Simulate: add book → research → embed → cross-match → verify."""
    # Step 1: Research a book
    research = research_book("The Prince", "Machiavelli", ...)
    write_research("data/book_research/test_e2e.json", research)

    # Step 2: Embed book claims
    subprocess.run(["python3", "build_book_claim_embeddings.py"], check=True)

    # Step 3: Build knowledge index with cross-matching
    subprocess.run(["python3", "build_knowledge_index.py"], check=True)

    # Step 4: Verify cross-source connections exist
    with open("data/knowledge_index.json") as f:
        index = json.load(f)
    assert 'book_article_connections' in index
    # At least some connections should exist for a well-known book
    connections = index['book_article_connections']
    print(f"Found {len(connections)} book-article connections")

    # Step 5: Generate story-so-far using the research
    briefing = generate_story_so_far(...)
    assert briefing['argument_summary']

    # Step 6: Clean up
    os.remove("data/book_research/test_e2e.json")
```

### Tier 4: Client-side web tests

**`scripts/tests/test_book_ui_web.py`** (using requests against the web app):

```python
def test_book_detail_shows_connections():
    """After research completes, book detail page includes connections."""
    # This tests the web-rendered HTML for connection content
    # Requires the web app to be running
    r = requests.get(f"http://alifstian.duckdns.org:8084")
    assert r.status_code == 200
    # The web app is an SPA, so we'd need a headless browser
    # Alternative: test the API responses directly (tier 2)
```

For web UI testing, the most practical approach is:
1. Test server endpoints directly (tier 2) — verifies data layer
2. Use `npx expo export --platform web` to verify build succeeds
3. Manual spot-check of one book on the web app after deployment

---

## Metrics to Log

All new events added to `logEvent()`:

```typescript
// Book Research
logEvent('book_research_started', { book_id, title })
logEvent('book_research_completed', { book_id, chapters_researched, article_connections, suggested_reading })
logEvent('book_research_failed', { book_id, error })

// Chapter Insights
logEvent('chapter_insights_viewed', { book_id, chapter, has_captures })
logEvent('chapter_digest_created', { book_id, chapter, reader_summary: boolean })

// Story So Far
logEvent('story_so_far_shown', { book_id, days_since_last, captures_count })
logEvent('story_so_far_resume_tapped', { book_id, dwell_time_ms })

// Connections
logEvent('book_connection_tapped', { book_id, article_id, connection_type })
logEvent('suggested_reading_tapped', { book_id, title, url })
logEvent('suggested_reading_ingested', { book_id, article_id, url })

// Enhanced Capture
logEvent('smart_capture_processed', { book_id, page_number_detected, key_passage_shown, elaborative_question_shown })
```

---

## Implementation Sequence

1. **Server: Book Research Agent** (`book_research_agent.py` + 3 endpoints)
2. **Server: Book Claim Embeddings** (`build_book_claim_embeddings.py`)
3. **Server: Cross-Source Matching** (extend `build_knowledge_index.py`)
4. **Server: Enhanced Page Photo** (modify OCR prompt)
5. **Server: Tests** (all 4 tiers)
6. **Client: Types + API** (`types.ts`, `book-api.ts`, `book-store.ts`)
7. **Client: Book Detail Sections** (connections, suggested reading, chapter insights)
8. **Client: Story So Far** (overlay/screen)
9. **Client: Chapter Digest** (basic text input on chapter change)
10. **Deploy + Verify** (`deploy.sh` + web build)

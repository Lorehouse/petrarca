# Book Companion System: Complete Handoff Document

**Date**: 2026-03-15 (Session 22)
**Purpose**: Everything built, designed, and decided in this session for any agent continuing the work.

---

## What Exists Now (Built & Deployed)

### Server-Side Scripts

| File | Purpose |
|------|---------|
| `scripts/book_research_agent.py` | Core research agent. `research_book()` takes title/author/chapters/topics → Gemini+Search → thesis, chapter claims, key terms, article connections, suggested reading. `get_chapter_insights()` returns per-chapter research. `generate_story_so_far()` creates personalized briefing for returning after 48h+ gap. `get_all_book_claims()` collects all claims for embedding. ~10s per book. |
| `scripts/resurfacing_engine.py` | Scheduler + prompt generator. `generate_session()` picks top captures by priority score (highlight density × connection count × topic overlap with current reading × time since finish), generates resonance prompts (reconnect/reflect/connect-to-current/deep-reconnect/evolve) and cross-book dialogue prompts (LLM-generated tension questions for claim pairs from different books). Expanding intervals: 7→14→30→60→120→180 days. Dormant after 2 skips. |
| `scripts/process_kindle_books.py` | Batch processor for Kindle library. Reads `kindle_library.json` (from session 23's sync), filters by category (non-fiction, classical-literature, literary-fiction, language-learning) AND status=read, creates unified book records, converts highlights to captures, runs research agent. Handles both ASIN and book_id keys, title_resolved for sideloaded. |
| `scripts/build_book_claim_embeddings.py` | Embeds book claims (from research + captures) using Gemini embedding-001 (same space as article claims). `--cross-match` computes book×article similarity matrix. Output: `book_claim_embeddings.npz` + `book_claims_index.json` + `book_article_connections.json`. Added to `content-refresh.sh` as step 3f. |

### Server Endpoints (all in `scripts/research-server.py`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/book/research` | POST | Background research for a book (returns 202). Body: `{book_id, title, author, isbn?, chapters[], topics[]}` |
| `/book/research/{id}` | GET | Retrieve cached research JSON |
| `/book/chapter-insights` | POST | Per-chapter research + connections. Body: `{book_id, chapter_number, chapter_title, captures[]}` |
| `/book/story-so-far` | POST | Personalized return briefing. Body: `{book_id, title, author, current_chapter, current_page, page_count, captures[]}` |
| `/book/sync` | POST | Save books+captures to server (client→server merge) |
| `/book/sync` | GET | Load books+captures from server (server→client) |
| `/book/resurfacing/generate` | POST | Generate a resurfacing session (3 highlights + 1 dialogue). Body: `{include_dialogues: bool}` |
| `/book/resurfacing/respond` | POST | Record user response. Body: `{capture_id, response_text, response_type}` |
| `/book/resurfacing/skip` | POST | Record skip. Body: `{capture_id}` |
| `/book/resurfacing/status` | GET | Resurfacing stats |
| `/book/process-kindle` | POST | Trigger Kindle batch processing (background). Body: `{max: int}` |
| `/book/ocr-page` | POST | Enhanced: now also returns `key_passage` and `elaborative_question` |

### Client-Side (Expo/React Native)

| File | What's New |
|------|-----------|
| `app/data/types.ts` | BookResearch, ChapterResearch, BookArticleConnection, SuggestedReading, StorySoFarBriefing, ChapterInsights, ResurfacingItem, ResurfacingSession. BookCapture now has `key_passage`, `elaborative_question`. PhysicalBook.reading_status includes `'archived'`. |
| `app/lib/book-api.ts` | `researchBook()`, `getBookResearch()`, `getChapterInsights()`, `getStorySoFar()`, `syncBooksToServer()`, `loadBooksFromServer()`, `generateResurfacingSession()`, `respondToResurfacing()`, `skipResurfacing()`, `getResurfacingStatus()`, `processKindleBooks()` |
| `app/data/book-store.ts` | Server sync on init (merge local+server, server wins) + `syncToServer()` after every mutation |
| `app/app/book-detail.tsx` | Thesis/about section, article connections, suggested reading, Story So Far overlay (on 48h+ gap), status pills (reading/paused/finished/archive). Auto-triggers research on first view. |
| `app/app/resurfacing.tsx` | Resonance cards (book cover, highlight, prompt, respond/skip) + Cross-Book Dialogue cards (two claims, tension prompt). Accessible from Library → ✦ Revisit. |
| `app/app/kindle-curation.tsx` | Full Kindle library triage: sort (title/progress/recent/category), filter (all/unreviewed/non-fiction/read/skipped), quick-action pills (Read/Skip/Undo), Auto-classify button, Process Read Books button. |
| `app/app/(tabs)/library.tsx` | Three header buttons: ✦ Revisit, Kindle, +. Archive filter includes both 'finished' and 'archived'. |
| `app/app/_layout.tsx` | Routes: resurfacing, kindle-curation |

### Server Data Files

| Path | Content |
|------|---------|
| `/opt/petrarca/data/physical_books.json` | Unified book records + captures (server-authoritative) |
| `/opt/petrarca/scripts/data/book_research/{book_id}.json` | Per-book research output |
| `/opt/petrarca/scripts/data/book_claim_embeddings.npz` | Book claim embeddings |
| `/opt/petrarca/scripts/data/book_claims_index.json` | Book claim metadata |
| `/opt/petrarca/scripts/data/book_article_connections.json` | Cross-source matches |
| `/opt/petrarca/scripts/data/resurfacing_state.json` | Per-capture scheduling state |
| `/opt/petrarca/data/kindle_library.json` | Kindle library (from session 23 sync) |
| `/opt/petrarca/data/kindle_highlights.json` | Kindle highlights (from session 23 sync) |

### Tests

`scripts/tests/test_book_research.py` — 11 unit tests + 5 live API tests. All pass. Run: `cd scripts && python -m pytest tests/test_book_research.py -v`

---

## Architecture Decisions

### Server-First Data
All data must be stored on the server. Local storage (AsyncStorage) is only a cache. Every client mutation pushes to server. On init, client merges with server (server wins for conflicts). See `memory/feedback_server_first_data.md`.

### Deploy Workflow
NEVER rsync to server. Always: commit → push → `bash ~/src/expo/scripts/deploy.sh petrarca`. The phone loads JS from Expo dev server (port 8082), not static files. See `memory/feedback_deploy_workflow.md`.

### Book Research Agent as Linchpin
The system provides value from just a book title — no captures needed. The research agent generates thesis, chapter claims, connections, and suggestions autonomously. Captures (from OCR, voice, Kindle highlights) enrich this foundation but don't gate it.

### Processing Requires Curation
Kindle books are NOT auto-processed. The user must first curate (mark as "read" via Kindle curation UI), then trigger processing. Only books with `status=read` AND `category` in {non-fiction, classical-literature, literary-fiction, language-learning} are processed.

### Resurfacing ≠ Flashcards
The resurfacing system uses open-ended generative prompts ("How does this connect to what you're reading now?"), NOT recall testing. Expanding intervals, dormancy after skips, connection-triggered bypass of schedule. Research basis: spreading activation, analogical reminding, generation effect.

---

## What's Designed But NOT Built

### From `research/book-companion-experiments.md` (8 experiments)

| Experiment | Status | Key Idea |
|-----------|--------|----------|
| 1. Reading Echoes | DATA READY, UI DEFERRED | Show book claims as margin annotations while reading articles. Pipeline exists (cross-source matching), UI in article reader not built. |
| 2. Smart Page Photo | PARTIALLY BUILT | Enhanced OCR prompt (key_passage, elaborative_question) deployed. Full capture confirmation screen with suggested highlights NOT built. |
| 3. Voice Self-Explanation | DEFERRED | Prompted voice capture flow after photographing a page. Infrastructure exists (Soniox), prompt UI not built. |
| 4. Constrained Capture ("Pick 3") | DEFERRED | Sentence-selection UI after OCR. Needs real capture data first. |
| 5. Resonance Resurfacing | BUILT | Engine + UI deployed. Needs data (captures/highlights) to be useful. |
| 6. Cross-Source Synthesis | PARTIALLY BUILT | Embedding pipeline + connections on book detail. Book map visualization NOT built. |
| 7. Context Restoration | BUILT | Story So Far endpoint + overlay deployed. |
| 8. Chapter Digest | BASIC VERSION | Server generates digest from research. Weekly evolution pipeline NOT built. |

### From `research/kindle-book-experiments.md` (6 experiments)

| Experiment | Status | Key Idea |
|-----------|--------|----------|
| A. Knowledge Archaeology | DESIGNED | One-time reading landscape report. Needs 50+ researched books. |
| B. Resonance Resurfacing | BUILT | Engine deployed, needs Kindle highlights to flow in. |
| C. Cross-Book Voice Dialogues | BUILT | Engine + UI deployed, needs 2+ researched books with claims. |
| D. Active Content Discovery | DESIGNED | Auto-ingest articles that complement books. Research agent produces suggestions but auto-ingestion not wired. |
| E. Completion Retrospective | DESIGNED | End-of-book synthesis + 3-month revisit. Not built. |
| F. EPUB Deep Processing | DESIGNED | `ingest_book_petrarca.py` exists but not integrated with Kindle flow. |

---

## The Pipeline (end-to-end flow)

```
Kindle Mac app SQLite ──→ kindle_sync.py (4h launchd) ──→ /kindle/sync
Chrome extension ──────→ kindle-notebook.js (12h alarm) ─→ /kindle/sync
                                                            ↓
                                                  kindle_library.json
                                                  kindle_highlights.json
                                                            ↓
User opens Kindle curation UI ──→ marks books as "read" ──→ /kindle/curate
                                                            ↓
User taps "Process Read Books" ─→ /book/process-kindle ────→ process_kindle_books.py
                                                            ↓
                                    For each read book:
                                    ├── Create unified record → physical_books.json
                                    ├── Convert highlights → captures
                                    └── Run research_book() → book_research/{id}.json
                                                            ↓
content-refresh.sh (4h cron) ──→ build_book_claim_embeddings.py --cross-match
                                    ├── book_claim_embeddings.npz
                                    └── book_article_connections.json
                                                            ↓
User opens book detail ──→ sees thesis, connections, suggested reading
User opens ✦ Revisit ───→ resurfacing_engine.py generates session
                           ├── Resonance cards (highlights with prompts)
                           └── Cross-Book Dialogue cards (claim pairs)
User responds (text/voice) → /book/resurfacing/respond → state updated
```

---

## Current Live State

- **1 physical book**: "Midnatt på Sicilia" (Peter Robb) — researched, on server
- **0 Kindle books synced yet** (extension built in session 23, testing in progress)
- **0 resurfaceable captures** (need Kindle highlights or manual captures)
- **239 articles** with ~4,500 embedded claims (ready for cross-matching)
- Research server running via systemd at port 8090
- Expo dev server at port 8082 (phone), nginx web at 8084

---

## Research Documents Created This Session

| Document | Lines | Key Finding |
|----------|-------|-------------|
| `andy-matuschak-research.md` | 317 | Comprehension pivot: "forgetting is often never-having-understood." Highlight-driven prototype most successful (14 users loved it). |
| `mnemonic-medium-physical-books.md` | 438 | Great Books problem: "it's not details but habits and mindsets." LLMs produce surface-level prompts for conceptual material. |
| `beyond-flashcards-knowledge-retention.md` | 506 | Connection-based resurfacing > explicit review. Gist outlasts detail. Best review is another reading context, not flashcards. |
| `physical-book-digital-bridge-research.md` | 404 | Every product stops at capture. No one connects to knowledge graph. Page number OCR is a unique differentiator. |
| `ai-book-captures-research.md` | 612 | "Chat with YOUR reading" not "chat with book." Elaborative interrogation every ~150 words improves comprehension. |
| `hci-book-reading-annotation.md` | 542 | Constrained highlighting (CHI 2024 Best Paper): 11-19% comprehension gain. Voice > typed for conceptual understanding. |
| `book-companion-experiments.md` | 363 | 8 prioritized experiments with build order. Central insight: connect books to articles, don't review in isolation. |
| `book-companion-experiment-protocols.md` | 650 | Full specifications: hypotheses, algorithms, UI, user journeys, data requirements, metrics. |
| `book-companion-implementation-plan.md` | 477 | Sprint A/B plan. Testing strategy (4 tiers). All deferred ideas listed. |
| `kindle-book-experiments.md` | 549 | 6 Kindle-specific experiments. Knowledge Archaeology, Resonance Resurfacing, Cross-Book Dialogues, Active Content Discovery. |

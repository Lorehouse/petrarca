# Knowledge System Implementation Status

**Date**: April 4, 2026 (last updated — session 44: multi-quiz microlearning + entity research)

## Session 44: Multi-Quiz Microlearning, Entity Research, Review Stream Fix (April 4, 2026)

### Review Stream Fix
- **Root cause**: ALL 253 knowledge_items had `cached_question = NULL` — zero regular review cards could be served. Only 5 microlearning cards showed before "no more cards."
- **Batch generation**: New `POST /review/batch-generate` endpoint populated questions for all 109 eligible items.
- **Dynamic ML limit**: When regular items are sparse (<3), ML cards fill the whole batch. Fixed `has_more` pagination to count ML cards.

### Multi-Quiz Microlearning Cards
- **`microlearning_quizzes` table**: Each quiz independently FSRS-scheduled. ML card = content container, quizzes = review atoms.
- **Prompt**: Updated to generate 3-5 specific factual questions per card (date, person, event, consequence, connection).
- **First encounter**: Content shown, then all quizzes stacked with per-quiz Show answer / Skip / Grade. "Complete →" button to advance.
- **Re-review**: Individual quiz shown first (`microlearning_quiz` card type), full content revealed as answer.
- **Dismiss**: Per-quiz "Skip", per-card "Not interested" (top) + "Dismiss card" (bottom).

### Quiz Dedup (limbic MiniLM)
- New quizzes checked against existing quizzes + curriculum key_facts using MiniLM 384d cosine at 0.82 threshold.
- All matches logged with similarity score for calibration review (~Apr 18).
- Verified: caught "When was Battle of Himera?" duplicate at 0.907, let through different-angle questions at 0.77-0.81.

### Entity Research System
- **"3 questions" button**: Claude Sonnet generates research queries informed by temporally/spatially related entities.
- **"Research this" button**: Triggers rich entity profile ML card with connections to same-period/same-region entities.
- **Entity markup**: LLM annotates people/places/events/concepts with canonical IDs in ML card content → tappable spans.
- **Backlinks**: Entity lookup shows "In your research" with ML cards mentioning that entity. Dynamic entities for IDs not in shared_entities.
- **Caching**: Entity research stored as ML cards, available on subsequent entity opens.

### Other
- Scroll to top on card transitions.
- Backfilled 37 legacy ML cards with quiz rows.
- Cleaned up 3 failed + 1 pending ML cards.

## Session 41: Review System Consolidation + Fractal Exploration (March 30 – April 1, 2026)

### Review Tab Rewrite — Infinite River + Knowledge Items
- **Data source changed**: Review now uses `knowledge_items` (253 items across 6 curricula) instead of `retrieval_questions` (19 Sicily-only). Knowledge items carry FSRS scheduling, curriculum context, and source provenance.
- **Cards/Voice sub-tabs**: Review tab split into two modes — card-based review and voice recall. Cards are the default.
- **Infinite river**: No session boundary. Cards stream continuously; user stops when they want. Replaces the old 10-card batch + "Continue" button pattern.
- **Skip button**: Every card has a skip action — logs `review_skip` and moves to next card without affecting scheduling.
- **Simplified grading**: Three grades — knew / partly / missed — feed directly into FSRS scheduling via `review_engine.record_answer()`.

### Fractal Exploration — Microlearning Research Pipeline
- **Follow-up queries**: Each review card gets 3 LLM-generated follow-up research queries (e.g., "How did X influence Y?").
- **Tap to research**: Tapping a query triggers background Gemini + Search. Result stored as a `microlearning_card` with content, an assessment question, and 3 new follow-up queries (recursive fractal).
- **Interleaved in stream**: Microlearning cards appear in the review river every ~5 items, mixing retrieval practice with discovery.
- **Text input**: Every card has a text input for custom research queries — user types a question, same pipeline runs.
- **New table**: `microlearning_cards` in petrarca.db (content, assessment Q, follow-ups, parent card reference).
- **New endpoint**: `POST /review/microlearning` — generates microlearning card from query via Gemini + Search.

### Voice Mode — Chapter Recall Prompts
- Voice elicitation now includes "What do you remember from Chapter X?" prompts for active books.
- Chapter recalls get high priority in candidate selection for voice elicitation sessions.

### Data Cleanup — Legacy Review Code Removed
- **Removed code paths**: `record_review_result()`, `get_review_status()`, `get_retrieval_questions()` — all replaced by knowledge_items + review_engine.
- **Archived tables**: `retrieval_questions` and `review_schedule` tables archived with data preserved (not dropped), but no code references them.
- **Still active**: `review_items` table remains (used for exploration items and voice follow-ups).
- **Scoring**: Exclusively through `review_engine.record_answer()` — single path for all review grading.

### Interaction Logging — Comprehensive Review Events
New events for algorithm tuning:
- `review_card_shown` — card presented to user
- `review_answer_revealed` — user taps to see answer
- `review_result` — grading result with `time_seconds` field for response latency
- `review_skip` — card skipped
- `review_entity_intro_continue` — entity introduction card continued
- `review_custom_query` — user typed a custom research query
- `review_research_triggered` — follow-up research query tapped

### Navigation Cleanup
- **Drawer**: "Voice Recall" and "Hamarquizen" entries removed from drawer navigation.
- **Book detail**: "Hamarquizen" renamed to "Book Review".
- **Book detail review badge**: Now navigates to the Review tab instead of inline Hamarquizen screen.

### Book archive/remove feature
- **Swipe-to-remove on mobile**: `Swipeable` from `react-native-gesture-handler` on book rows in Library tab — swipe left reveals rubric-red "Remove" action. Same pattern as ArticleRow feed dismiss.
- **Hover × on web**: Absolute-positioned remove button appears on hover, with `confirm()` dialog.
- **Soft-delete via `archived` status**: Books set to `reading_status: 'archived'` are hidden from all Library filter tabs (Reading, All, Finished). Status syncs to server, survives app restart. Data preserved (reversible).
- **Bug fix**: `archiveBook()` in `book-store.ts` was incorrectly setting `reading_status: 'finished'` instead of `'archived'` — archived books were appearing in the Finished tab.
- **GestureHandlerRootView**: Added to Library screen (required for `Swipeable` on native).
- Book-detail screen already had an "Archive" status pill that correctly sets `'archived'` and navigates back.

### Files changed
- `app/app/(tabs)/library.tsx` — `GestureHandlerRootView` wrapper, `Swipeable` on native, hover × on web, `archived` filtered from all views
- `app/data/book-store.ts` — `archiveBook()` fixed to set `'archived'`

## Sessions 39–40: Curriculum Review System + Multi-Curriculum Queue (March 27–29, 2026)

### Curriculum Visualization (Session 39)
- **`curriculum_graph.html`**: Force-directed D3 graph of all curricula — nexus entity nodes, domain color lanes, Graph↔Timeline tabs
- **`curriculum_timeline.html`**: Horizontal D3 timeline — 5 curriculum lanes, 220px collapsible entity filter panel (persons/places/events), hierarchical place expansion, D3 brush for zoom, "Undated" column, detail sidebar. Served at `/curriculum/timeline`.

### Review Question Quality (Session 39)
- **Root cause**: Questions tested source-text trivia ("Which city founded Naxos?") instead of curriculum concepts
- **Fix**: `QUESTION_GEN_PROMPT_FACTUAL` redesigned — node description IS the answer guide. Questions test conceptual understanding ("What drove Greek colonization of Sicily?"), not random facts. Examples updated to be curriculum-agnostic.
- **Curriculum scan**: Level 1 container nodes filtered out (never assessable). Queue ordering: history areas before culture areas, chronological by `date_start` within area.
- **Dedup guard**: `create_exploration_items()` checks for unexpired items before creating new ones.
- **Node rename**: "Architecture as Palimpsest" → "Sicily's Architecture: Layers of Conquest" in curriculum JSON.

### Multi-Curriculum Knowledge Items + Review Queue (Session 40)

#### Byzantine + Islamic self-assessments → review queue
- User completed curriculum-scan for Byzantine (49 nodes: 16 engaged, 33 unknown) and Islamic (40 nodes: 11 engaged, 29 unknown)
- **Bridge script**: Creates `knowledge_items` from `knowledge_*.json` state files. Stability based on assessed level: unknown=1d/due-now, engaged=14d, anchored=60d. Sources: `[{type: 'self_assessment', ...}]`.
- **Date enrichment**: LLM-assigned `date_start`/`date_end` to all 78 Level 2+ Byzantine/Islamic nodes (none had dates). Specific events: Nika Revolt 532–532, Justinian 527–565, Arab sieges 632–718, etc.
- **Questions pre-generated**: 89 concept-based questions, 0 failures.

#### Ancient Greece book mapping
- 4 Iggulden novels (Gates of Athens, Protector, The Lion, Falcon of Sparta) + Matyszak "A Year in the Life" mapped to Ancient Greece curriculum via LLM
- 47 knowledge_items created with actual book sources (chapter evidence + temporal hooks)
- 8 additional self-assessment gap items created for nodes not covered by books

#### Roman Republic + other gaps
- Roman Republic: 38 knowledge_items from self-assessment (curriculum already had dates 509 BC–476 AD)
- Ancient Greece: 8 self-assessment gap items filled
- Total: **206 knowledge_items across 5 curricula** (was 24 Sicily-only) → **253 across 6 curricula** by session 41

#### Review queue ordering
- Sort key: `(area_order, date_start, due_at)` — history areas before culture areas, chronological within area
- Result: All 5 curricula interleave historically (~800 BC polis → ~480 BC Persian Wars → ~330 AD Constantinople → ~570 AD Islam)

### Review UX: 10-Card Batches + Continue Button (superseded by session 41 infinite river)
- ~~Session already capped at 10 cards via `getReviewQueue(10)`~~.
- ~~**Done screen**: "✦ Continue · N more due" rubric button when items remain; reloads next batch.~~
- **Replaced in session 41**: Infinite river with no session boundary, skip button on every card, Cards/Voice sub-tabs.

### Article Reading → Review Queue (#9)
- `POST /review/article-read` endpoint: looks up `article_curriculum_nodes` for an article, bumps matching `knowledge_items` due in 1h (if currently far-future).
- Reader `handleDone` fires this fire-and-forget.
- **Effect**: reading an article that covers curriculum topics you don't know well will surface those review cards in your next session.

### Prompt + Code Fixes
- `MAP_CHAPTER_PROMPT`: Examples changed from Sicily-specific to curriculum-agnostic (Themistocles, Byzantine dynasty, Muhammad).
- `QUESTION_GEN_PROMPT_FACTUAL`: "Sicilian history" wording removed; examples now span all curricula.
- Hardcoded `domain_id = ... 'sicily_history_culture_and_legacy'` fallback changed to `or` pattern.
- Review card: now shows curriculum domain in rubric color above chapter title for orientation.

## Session 38: Feed Overview + Web Link Fix (March 27, 2026)

### Web Reader Links Fixed
- **Root cause**: React Native Web's `<Text onPress + href>` calls `preventDefault` on the anchor, then `Linking.openURL`/`window.open()` gets blocked as popup. Also, parent `<Pressable onLongPress>` on paragraphs captured pointer events.
- **Fix**: New `MarkdownLink` component (`app/components/MarkdownLink.tsx`) — web uses native `<a href target="_blank">`, native uses `onPress` + `Linking.openURL`. Paragraph wrappers use `View` on web instead of `Pressable`.
- **Cmd+click**: Opens ingestable links externally on web (skips ingestion)
- **CLAUDE.md**: Documented RNW link gotcha to prevent recurrence

### Feed Overview — Sidebar (Web) + Filter Pills (Mobile)
- **Web**: Grid layout with 180px sticky left sidebar containing topic list (clickable filters with counts), source filters with colored dots, and "Your Research" box showing AI-generated articles with original queries
- **Mobile**: Research section (rubric left border, queries grouped with article titles) + combined topic/source filter pills in one scrollable row above feed
- **Filter pills**: Topic pills (EB Garamond, ink active state) + source pills (DM Sans uppercase, separated by divider) — both filter the feed
- **Data layer** (`store.ts`): `getArticleSourceCategory()` (twitter/newsletter/research/exploration/other), `getResearchArticles()` (grouped by query), `getFeedDistribution()`, `sourceFilter` param added to `getArticlesByLens()`
- **Research queries**: Extracted from `sources[].type` prefix `research:` — e.g. `research:How does compound engineering...`
- **New components**: `FeedFilterPills.tsx`, `FeedSidebar.tsx`, `ResearchSection.tsx`

## Session 36: SQLite Migration — Phases 1–4 (March 22–25, 2026)

### SQLite as Canonical Store
- **`petrarca.db`** at `/opt/petrarca/data/petrarca.db` — stores articles, atomic_claims, knowledge_index, clusters, syntheses alongside existing books/projects/kindle tables
- **Phase 1**: Schema + `db.py` with sync helpers (`sync_articles()`, `sync_knowledge_index()`, `sync_clusters()`, `sync_syntheses()`), each in one transaction
- **Phase 2**: Pipeline scripts (`build_articles.py`, `build_knowledge_index.py`, `build_concept_clusters.py`, `generate_syntheses.py`) dual-write JSON + SQLite
- **Phase 3**: SQLite is canonical — `export_content_json.py` reconstructs served JSON from SQLite, replacing hand-written JSON
- **Phase 4**: 6 `/api/*` endpoints on research-server.py serve directly from SQLite: `manifest`, `articles-meta`, `articles/<id>/content`, `knowledge-index`, `syntheses`, `clusters`

### Client Lazy Content Loading
- **`ArticleMeta`** type (no `content_markdown`/`sections`) used for feed and store — reduces initial payload from 13.6 → 4.7 MB
- **`ArticleContent`** type loaded lazily in reader via `article-content.ts` — in-memory + disk cache, prefetch for offline
- **Fallback**: Client falls back to nginx JSON if API is down

### Bug Fixes
- **Reader content not displaying** (March 25): `fullContent` useMemo in reader.tsx depended only on `article?.id`, which doesn't change when lazy-loaded content arrives. Added `articleContent` to dependency array.
- **Optional JSON fields**: Store NULL when absent in SQLite, skip in export (don't emit `null` keys in JSON)

### Gotchas Documented
- `knowledge_index` claims are derived (topics normalized, only articles with embeddings included)
- Duplicate claim IDs: composite PK `(article_id, id)` in `atomic_claims`
- JSON formatting: `articles.json` uses `indent=2`, `knowledge_index.json` uses compact

### Phase 4c: Pipeline Cleanup (March 25)
- **Removed `export_content_json.py`** from `content-refresh.sh` pipeline cron — SQLite API serves content directly
- Pipeline scripts still dual-write JSON (for nginx fallback compatibility)
- `export_content_json.py` can still be run manually if needed

### Incremental Article Sync (March 25)
- **`content-sync.ts` rewritten** to use manifest-driven smart sync:
  - Fetches manifest first, compares hashes per resource (articles, knowledge_index, clusters, syntheses)
  - **Articles**: if changed and cached data exists, fetches `?since=<last_sync_time>` for only new articles, merges by ID. Falls back to full download on count mismatch.
  - **Knowledge index / clusters / syntheses**: skipped entirely when hash unchanged, loaded from cache
  - **First launch**: still does full download
- **Bandwidth**: typical refresh after 4h cron = manifest (~1 KB) + 0–10 new articles (~20 KB each) vs previous 4.7 MB full article list
- **Logging**: `sync_mode` field in `content_downloaded` event tracks which path was taken (`incremental`, `cached`, `full`, `full_after_mismatch`)

### Next Priorities
- ~~Knowledge model simplification (drop FSRS → binary seen/unseen)~~ — kept FSRS, now exclusively via `review_engine.record_answer()`
- ~~Cross-book review generation with temporal hooks~~ — done (session 40 Hamarquizen cross-book, session 41 Book Review rename)
- Map old books (Kindle → curriculum → Amygdala probes)

## Session 35: Claim Calibration + Article Similarity + Prompt Overhaul (March 21–22, 2026)

### Extraction Prompt Overhaul
- **Both prompts rewritten** in `build_articles.py`: article extraction + atomic claims now prioritize insights, patterns, comparisons over product feature lists
- **Calibration results**: V1 had 31% noise, 17% insight rate. V2: 0% noise, 91% insight rate
- **Model switch**: pipeline tests + defaults → `gemini-3.1-flash-lite-preview` (fastest, cheapest, 5% factual claim rate vs 60% before)
- **All 257 articles backfilled** with new prompt — claims went from 1,473 to 1,045 (fewer but insight-focused), novelty claims 156→368, entities/follow-ups now on 100%

### Article-Level Similarity (amygdala `document_similarity` module)
- **New amygdala module**: `Document`, `find_similar_documents()`, weighted multi-field embeddings
- **Best strategy**: 0.5×summary + 0.5×claims embedding = 94% accuracy, Spearman ρ=0.818 (18 human-rated pairs)
- **Validated**: 300 LLM-rated pairs (AUROC=0.930), 50 synthetic benchmark pairs (ρ=0.895)
- **Calibrated thresholds**: briefing card=0.52 (P=80%, R=78%), feed ranking=0.49, dedup=0.64
- **Integrated**: `build_knowledge_index.py` → `article_similarities` field (6,815 pairs), client `getSimilarArticles()` in knowledge-engine.ts
- **What didn't work**: LLM judge (78%), topic Jaccard (50%), two-stage embed→LLM (no improvement)

### Briefing Card in Reader
- **Verdict line**: "Almost entirely new" / "Extends what you know — N new, M deepening" / "Mostly familiar — N details worth scanning"
- **Similar articles**: top 3 read articles with similarity %, tappable to navigate
- **Skip nudge**: when >70% known, "Read N new claims only →" switches to new_only mode
- **Graceful degradation**: all features return empty when knowledge index not loaded

### Reader UI Additions
- **Follow Topics section**: 2-3 toggleable chips (entity + specific topics) below article, sends interest_chip signals
- **Copy link**: "Copy link" in ⋯ dropdown menu, copies source_url to clipboard

### 9-Agent Research Swarm
- **Datasets**: `scripts/ground-truth/` — 300 LLM-rated pairs, 50 synthetic benchmark, 11 embedding strategies, corpus cluster analysis, two-stage pipeline experiments, threshold config
- **Experiment report**: `scripts/ground-truth/experiment-report.html` — visual report of all experiments
- **Research docs**: `research/auto-research-patterns.md` (Karpathy loop), `research/cross-project-similarity-applications.md` (Petrarca/Alif/Hamarquizen)
- **Amygdala design doc**: `experiments/document_similarity_design.md`

### Corpus Analysis (257 articles)
- 26 natural clusters, 119 singletons (46% don't cluster)
- 70% of articles have 10+ neighbors at threshold 0.47 — briefing card useful for majority
- Sicily dominates overlap (clusters at 0.75-0.88 cohesion); AI/tech articles naturally isolated
- 5-10 near-duplicate pairs identified (>0.90 similarity)

### Otak Integration
- `scripts/dedup_check.py` — pre-ingestion duplicate screening against existing sources
- `scripts/readwise_triage.py` — clusters 11K+ Readwise docs for ingestion prioritization
- `canonical_synthesis.py` — replaced hand-rolled similarity with amygdala's `pairwise_cosine`

### Next Priorities (at time of session 35)
- ~~SQLite migration~~ → Done (session 36, Phases 1–4)
- Atomic claims re-extraction with new prompt (separate from article-level backfill already done)
- Knowledge index rebuild after atomic claims update

## Session 34: Overlapping Curricula + Article-Curriculum Bridge (March 21–22, 2026)

### Curriculum Enrichment (all 3 curricula)
- **Date ranges**: All 192 nodes now have `date_start`/`date_end` fields (negative for BCE)
- **Prerequisite densification**: Sicily 43→101 edges, Greece 59→84, Rome 41→57 (via Sonnet LLM pass)
- **Cross-curriculum entities**: 25 shared entities (Archimedes, Syracuse, Punic Wars, Plato, etc.) with 74 node links and curriculum-specific "lenses"
- **Files**: Enriched JSONs uploaded to `/opt/petrarca/data/curricula/`, `cross_curriculum_entities.json`

### Temporal Hook System
- **Hook generation**: 30 temporal hooks connecting Sicily to Greece/Rome, 4 types: known_anchor, same_moment, causal_chain, surprising_proximity
- **Human calibration**: 29/30 useful, 1 meh, 0 wrong — all hook types work equally well
- **Key finding**: Concrete dates + genuine historical connection + narrative framing = useful. Thematic stretches without factual grounding = meh.
- **Files**: `scripts/hook-calibration.html`, `scripts/hook-calibration-2026-03-22.json`

### Article ↔ Curriculum Bridge
- **`scripts/build_curriculum_embeddings.py`** (new): Embeds 192 curriculum nodes with MiniLM 384d (same model as article claims), maps article claims to curriculum nodes
- **Threshold**: 0.65 cosine (calibrated — 0.70 too strict, 0.45 too noisy)
- **Results**: 769 claim→node links across 98/258 articles and 70/192 curriculum nodes
- **Pipeline integration**: `build_knowledge_index.py` now includes `article_curriculum_nodes` in knowledge_index.json
- **Client**: `getArticleCurriculumNodes()` in knowledge-engine.ts exposes data

### Feed Ranking: Active Book Boost
- Articles matching topics of actively-read books get +0.15 score boost in `getRankedFeedArticles()`
- Topic cache with 60s TTL to avoid re-scanning books per article
- **File**: `app/data/store.ts` — `_getActiveBookTopicBoost()`

### "Connects to Your Reading" Badge
- 📖 badge in ArticleRow margin for articles whose curriculum nodes overlap with active book domains
- `getArticleBookConnections()` in store.ts matches article curriculum domains to book topic keywords
- **File**: `app/components/ArticleRow.tsx`

### Chapter-Complete Trigger
- Selecting a new chapter implies finishing the previous one
- Logs `book_chapter_completed` event with completed/next chapter
- Shows brief green "✦ Finished Ch X" banner (fades after 3s)
- **File**: `app/app/book-detail.tsx` — `handleChapterSelect()`

### Research Documents Created
- `research/overlapping-curricula-vision.md` — Bounded courses model, shared entities with lenses, nexus points
- `research/reading-companion-process-design.md` — 3 interaction moments (chapter complete, cross-book review, map old book), temporal hooks, chapter semantics
- `research/books-articles-connection-proposal.md` — Curriculum as bridge between books and articles, 5-phase plan

### Key Architecture Decisions
- **Curriculum nodes as bridge** between books and articles (not direct claim-to-claim matching — different granularity, different embedding models)
- **Bounded courses > fractal world history** — pedagogical perspective, natural stopping points, cross-references are the richest learning
- **Amygdala-first**: Improve amygdala for probing/mapping rather than building Petrarca-specific code
- **No breadth scan needed for Sicily**: Knowledge starts at zero, book mappings ARE the knowledge state

## Session 32: Reading Flow Fixes + Feed Quality (March 20, 2026)

### Reading Flow
- **Removed PostReadInterestCard** — topic +/- modal after Done was useless friction
- **Auto-advance after Done**: queue → next ranked feed article → back (no more losing scroll position)
- **Bug fix**: pre-compute next article BEFORE `markArticleRead()` (read articles get filtered from feed list)
- **Default reading mode → 'guided'** — known paragraphs dimmed at 0.55 opacity from start

### Feed Quality: Wikipedia Filters
- 146/237 articles were Wikipedia fragments from entity research chunking at H2 boundaries
- **Min word filter**: Wikipedia chunks <500w excluded (36 stubs removed)
- **Per-page cap**: Max 3 per Wikipedia page in feed (29 excess removed)
- **Implementation**: `_capPerSource()` and word count check in `getRankedFeedArticles()` in store.ts

### Research Article Tagging
- `run_ingest()` now passes real source tag to `import_url.py` (was always `--tag manual`)
- **'↗ AI' badge** on ArticleRow for `sources[].type.startsWith('research:')`
- `ArticleSource.type` widened from union literal to `string`

### Race Condition Fix (Critical)
- `build_articles.py` (cron) would overwrite research articles added by concurrent `import_url.py`
- Now acquires `.articles.lock`, re-reads from disk, merges in new articles before final save
- **Root cause of 16/21 lost research articles**

### Related Articles Cleanup
- Connected Reading filters out read articles
- Related Reading excludes read articles + articles already in Connected Reading (fixes duplicate bug)

## Session 30: Reader UX Overhaul + Projects System (March 19, 2026)

### Reader Link Clarity
- **Visual differentiation**: ingestable links show `⊕` suffix (solid underline), external links show `↗` (dashed underline)
- **LinkToast component**: bottom snackbar "Queued: [domain] ✓" with "View Queue" action, auto-dismiss 3s
- **Files**: `reader.tsx` (link rendering), `components/LinkToast.tsx`

### Voice Note Discoverability
- **Always-visible ● icon** in reader toolbar (between star and menu buttons)
- Pulsing red when recording, one tap to start — no menu navigation needed
- **File**: `reader.tsx` (toolbar area)

### Projects System (new feature)
- **Server**: `GET/POST /projects`, `POST /projects/note`, `GET /projects/{id}`, `POST /projects/{id}/update`
- **Data**: `/opt/petrarca/data/projects.json` (projects + notes), `/opt/petrarca/data/projects/` (audio files)
- **Client**: `projects-api.ts`, `ProjectPicker.tsx` (bottom-sheet), `projects.tsx` (list), `project-detail.tsx` (notes + add)
- **Integration**: FeedbackCapture → "Add to project?" after sending, drawer entry

### Voice Routing (auto-classify transcripts)
- `route_voice_input()` in research-server.py — Gemini Flash classifies intent (project_note, research_request, article_feedback, general_note)
- Fuzzy-matches project names, auto-creates project notes when matched
- Background enrichment via daemon threads after feedback/voice note transcription

### Queue Priority in Feed
- Queued articles boosted to top of 'best' feed lens, queue order preserved
- "✦ UP NEXT" section header before queued articles in feed
- ContinueBar falls back to next queued article with "UP NEXT" label when nothing in-progress
- Queue count badge in ✦ drawer

### Bug Fixes
- **Duplicate related articles**: replaced cascading dedup sets with single accumulating `usedIds` set
- **API endpoint mismatches**: fixed client-server contract for projects endpoints (response unwrapping, correct paths)

### Amygdala Migration (completed)
- `build_claim_embeddings.py`: Gemini API → `limbic.amygdala.EmbeddingModel` (local MiniLM)
- `build_knowledge_index.py`: Nomic → single `claim_embeddings.npz`, Gemini judge → `limbic.amygdala.nli_classify_batch`
- `experiment_claim_dedup.py`: manual complete-linkage → `limbic.amygdala.complete_linkage_cluster`

## Session 28: Capture Reliability Fixes (March 16, 2026)

- **Server threading**: Switched from `HTTPServer` to `ThreadingHTTPServer` — each request now gets its own thread. Fixes `ConnectionResetError` when multiple OCR/sync requests queued during rapid photo captures.
- **Photo retry queue**: Failed photo OCR captures now saved to AsyncStorage (`@petrarca/pending_book_photos`) and retried in parallel on screen focus. Mirrors existing voice note retry mechanism.
- **Retroactive queueing**: On focus, book-detail scans existing captures for failed photos with local URIs and auto-queues them for retry.
- **Data recovery**: Manually recovered 1 voice transcript + 1 photo OCR from server-side stored files where the server had completed processing but the client connection had dropped.

## Sessions 20–23 Summary (March 13–16, 2026)

### Session 20: Multi-Stage Synthesis Pipeline
- New `synthesis_pipeline.py` — multi-stage approach (local only, not yet deployed to server)

### Session 21: Physical Book Companion
- Library tab replaces Queue in 2-tab layout (Feed | Library)
- Book tracking: `add-book.tsx`, `book-detail.tsx`, `library.tsx`
- Server: `call_vision()`, book identification, cover lookup (Open Library/Google Books), TOC extraction
- Data: `book-store.ts`, `book-api.ts`, `physical_books.json` on server

### Session 22: Book Research Agent + Cross-Source Matching
- `book_research_agent.py` — Gemini+Search → thesis, chapter claims, key terms, article connections
- `build_book_claim_embeddings.py` — book claims embedded in same space as article claims
- 6 research documents on reading/annotation/knowledge retention
- 8 experiment protocols for book companion features
- Server: `/book/research`, `/book/chapter-insights`, `/book/story-so-far`

### Session 23: Kindle Integration + Media Capture (THIS SESSION)

#### Kindle Library (major feature)
- **Primary source**: Kindle Mac app SQLite (`BookData.sqlite`) — 2,778 books
  - NSKeyedArchiver plist decoding for author metadata (97% coverage)
  - Progress tracking via `ZRAWCURRENTPOSITION/ZRAWMAXPOSITION`
  - Sideloaded (PDOC) vs purchased (EBOK) detection
- **`kindle_sync.py`** — reads local DB, syncs to server. Modes: `--dump`, `--reading`, `--read`, `--resolve-titles`
- **Chrome extension** — 3 Kindle content scripts:
  - `kindle-content.js` — Cloud Reader ASINs from cover image IDs
  - `kindle-notebook.js` — incremental highlight scraping (tracks annotated dates)
  - `kindle-manage.js` — auto-paginates through 883 purchased books
- **Classification** — all 2,776 books classified via Gemini into 6 categories:
  - non-fiction (1,156), genre-fiction (1,097), literary-fiction (254), reference (130), language-learning (74), classical-literature (65)
- **Title resolution** — 349 sideloaded filenames resolved via LLM
- **Gmail attachment downloader** — `gmail_kindle_attachments.py`, 436 book files from `brightkindle@kindle.com`
- **EPUB finder** — `upload_epubs.py`, 190 local EPUBs (539MB)
- **Automation** — launchd plist (4h DB sync, not loaded), chrome.alarms highlight sync **disabled** (was opening kindle website every 12h; manual sync still available)
- **Server endpoints**: `/kindle/sync`, `/kindle/library`, `/kindle/highlights`, `/kindle/curate`, `/kindle/classify`, `/kindle/resolve-titles`, `/kindle/include`

#### YouTube Integration (deployed)
- `youtube-content.js` — "✦ Petrarca" button on YouTube watch pages
- Server: `/ingest-youtube` — fetches transcript via `youtube-transcript-api`, processes through article pipeline
- No API key needed, handles SPA navigation

#### Podcast Integration (built, needs auth)
- `podcast_sync.py` — Overcast export via `overcast-to-sqlite`
- Unified media log: `POST /media/sync`, `GET /media/log` → `media_log.json`

#### Server Data Files Added
- `/opt/petrarca/data/kindle_library.json` — 2,776 books with categories, progress, titles
- `/opt/petrarca/data/kindle_highlights.json` — highlights from notebook
- `/opt/petrarca/data/media_log.json` — YouTube, podcasts, TV consumption log

---

## Pre-Session-20 Status (original document below)
**Status**: Full corpus deployed with knowledge system, reader interactions, voice notes, AI chat, research agents, entity deep-dive, follow-up research, voice note browser + action extraction, activity log tab, scroll-aware encounter tracking, curated novelty card, hierarchical topic feedback, cross-article connections, LLM-verified topic normalization, automatic defragmentation, **unified single-screen feed with lens tabs**, **dynamic reranking**, **✦ drawer navigation**, **clipper auto-save countdown**, **tweet URL ingestion via twikit**, **auto-sync Twitter cookies**, **clipper immediate save via background worker**, **reader disregard + report bad scrape**, **feed ingest metadata**, **floating feedback capture with screenshots + server upload**, **expanded follow-up questions**, **queue auto-advance**, **hybrid topic signals**, **desktop web: 2-column feed grid**, **desktop web: 3-column reader with margin annotations**, **keyboard navigation with multi-key sequences**, **hover actions (archive + dismiss)**, **XML-first article extraction (paragraph merging fix)**, **mobile feed overlap fix**, **reader arrow-key scroll fix**, **LLM judge for ambiguous claims (G2)**, **web layouts for all secondary screens (Topics/Queue/Trails/Landscape/Voice Notes)**, **DoubleRule on all screens**, **drawer quick actions fixed**, **reader date format fix**, **user guide updated + linked from drawer**, **keyboard shortcuts on Queue + Topics screens**, **swipe hint tooltip (mobile)**, **"All topics" pill in feed**, **AnimatedHighlightWrap (reader paragraph highlights)**, **knowledge bar staggered animation**, **DoubleRule in reader**, **reader error boundary**, **cross-article synthesis pipeline (graph clustering → LLM synthesis → claim-level FSRS propagation)**, **26 syntheses with unique labels**, **synthesis reader 3-column web layout + keyboard shortcuts**, **junk article cleanup + pipeline guards**, **Gemini tool calling for structured output**, **"Restrained Folio" synthesis reader redesign (2-col CSS grid, inline chat, article popovers)**, **synthesis prompt overhaul (humanist scholar voice, article reference links, progressive disclosure)**, **feed filtering by synthesis coverage (≥80% excluded, ≥50% demoted)**
**Latest commits**: Session 19 — "Restrained Folio" synthesis reader redesign: complete rewrite of synthesis-reader.tsx (2-column CSS grid with 190px sidebar, Cormorant Garamond + Crimson Pro two-weight typography, local folio color palette, IntersectionObserver TOC tracking, TensionBlock/ExcerptBlock/DetailSection sub-components). New synthesis prompt in generate_syntheses.py (humanist scholar voice, Article Reference Key for `[Title](article:ID)` links, descriptive headings, inline tension blockquotes, progressive disclosure markers, structured tension objects). New components: SynthesisChat.tsx (inline chat modal), ArticlePopover.tsx (web hover popovers for article links). Feed filtering wired: ≥80% synthesis coverage → excluded from feed, ≥50% → score demotion.

---

## What Was Built

On March 8, 2026, the full knowledge-aware reading system was implemented end-to-end based on the design in `research/novelty-system-architecture.md` and validated by 11 experiments documented in `research/experiment-results-report.md`. Subsequently, the full 182-article corpus was restored with claims, embeddings, and knowledge index, and a cost auditing system was added. In session 4, the LLM infrastructure was migrated from litellm to the native `google.genai` SDK (fixing output truncation with newer Gemini models), topic research was rewritten from `claude -p` to Gemini search grounding (reducing latency from 60-120s to ~2.5s), and write contention was fixed with file locking. In session 5, four features were implemented via parallel agents: entity deep-dive (long-press entities in reader), follow-up research prompts (end-of-article questions), voice note browser (new screen), and voice note action extraction (LLM intent extraction from transcripts). In session 6, the Activity Log tab (G7) was implemented: a 4th tab showing a vertical timeline of reading sessions, system/pipeline events, research dispatches, and interest signals. The logger was enhanced with an AsyncStorage-backed offline queue for reliable event delivery, and the pipeline now writes structured JSONL events to the interaction log for server-side aggregation via `GET /activity/feed?days=N` on the research server.

### Architecture Overview

The system splits into **server-computed INDEX** (user-independent) and **client-side LEDGER** (user-specific):

```
Server Pipeline (cron every 4 hours):
  Twitter + Readwise → build_articles.py --claims → atomic claims + entities + follow-up questions
  → cleanup_articles.py → remove junk/duplicates
  → build_claim_embeddings.py → Gemini embedding-001 (batch 100)
  → build_knowledge_index.py → knowledge_index.json (parallel delta reports, 10 workers)
  → build_concept_clusters.py → graph clustering + two-pass contrastive labeling
  → generate_syntheses.py → structured synthesis per cluster (Gemini 3 Flash + tool calling)
  → All LLM calls via gemini_llm.py (google.genai SDK, call_llm/call_llm_tool)
  → All calls tracked by llm_audit.py → data/llm_audit.jsonl
  → research-server.py: ThreadingHTTPServer (concurrent request handling)

App (Expo SDK 54):
  content-sync.ts downloads knowledge_index.json + concept_clusters.json + syntheses.json
  → knowledge-engine.ts classifies claims against user's ledger
  → paragraph dimming, curiosity scoring, delta reports
  → synthesis-reader.tsx: read synthesis → markClaimsEncountered() → all source claims get FSRS entries
  → AsyncStorage persists knowledge ledger (@petrarca/knowledge_ledger)
  → All interactions logged via logger.ts → local + server (port 8091)
```

### Files Created/Modified

#### New Files

| File | Description |
|------|-------------|
| `app/data/knowledge-engine.ts` | Core knowledge engine — FSRS decay, claim classification, paragraph dimming, curiosity scoring, knowledge ledger persistence. Module-level state (singleton). |
| `app/data/queue.ts` | Reading queue with AsyncStorage persistence. Add/remove/list queued article IDs. |
| `app/app/(tabs)/topics.tsx` | Topics screen — articles grouped by broad topic, expandable clusters with delta report summaries and top claims. |
| `app/app/(tabs)/queue.tsx` | Queue screen — saved-for-later articles with swipe-to-remove. |
| `scripts/build_knowledge_index.py` | Server pipeline — loads articles + embeddings, computes cosine similarity matrix, extracts cross-article pairs, builds paragraph mappings, generates LLM delta reports (parallel, 10 workers). Outputs `data/knowledge_index.json`. |
| `scripts/deploy_knowledge_index.sh` | Deploys knowledge_index.json to nginx + updates manifest hash. Supports `--local` mode. |
| `scripts/llm_audit.py` | Thread-safe JSONL audit trail for all LLM calls. Tracks tokens, cost, cache hits per-call. CLI: `python3 scripts/llm_audit.py --days 7`. |
| `scripts/log_server.py` | HTTP server (port 8091) for collecting app interaction logs. Accepts POST /log with JSONL body, stores as daily files in `/opt/petrarca/data/logs/`. |
| `app/data/bookmarks.ts` | Article bookmarking with AsyncStorage persistence. Toggle, query, list bookmarked IDs. |
| `app/components/AskAI.tsx` | Bottom-sheet AI chat modal. Conversation threading, Gemini Flash via `/chat` server endpoint. Article context (title, summary, claims, topics, truncated text) passed as context. |
| `app/components/VoiceFeedback.tsx` | Compact voice note recording bar. Records audio via expo-av, uploads to server `/note` endpoint for async Soniox transcription. Auto-closes on send. |
| `app/lib/chat-api.ts` | API client for research server: `askAI()`, `uploadVoiceNote()`, `spawnTopicResearch()`, `fetchNotes()`, `ingestUrl()`, `getIngestStatus()`, `reportBadScrape()`. |
| `app/public/guide/index.html` | HTML user guide (Annotated Folio styled). Covers all 5 capture flows, 3 tabs, reader modes, knowledge system, usage patterns. Linked from Feed header. |
| `research/user-guide.md` | Markdown source for user guide. Describes all implemented features accurately. |
| `scripts/gemini_llm.py` | Shared Gemini LLM wrapper (google.genai SDK). Functions: `call_llm()`, `call_chat()`, `call_with_search()`, `call_llm_tool()` (forced function calling). Default model: `gemini-3.1-flash-lite-preview` (via `PETRARCA_LLM_MODEL` env var). |
| `app/app/voice-notes.tsx` | Voice notes browser screen. Global notes view with date-grouped sections, ✦ markers, Cormorant Garamond header. Accessible from Feed header "Notes" link. |
| `app/components/VoiceNoteCard.tsx` | Reusable voice note card component. Shows timestamp, duration badge, transcript (3-line max), article link, action chips with type-colored borders. |
| `app/lib/voice-notes-api.ts` | Voice notes API module. `fetchAllNotes()`, `fetchArticleNotes()`, `executeNoteAction()`. TypeScript interfaces for `VoiceNote` and `NoteAction`. |

#### New Files (Session 6: Activity Log)

| File | Description |
|------|-------------|
| `app/app/(tabs)/log.tsx` | Activity Log tab — vertical timeline with reading/system/research/interest nodes. Filter toggles (All/Reading/System/Research). Paged fetch: loads last day first, then 7 days in background. Colored dots per event type, ✦ markers for interest signals, day separators. |

#### New Files (Session 17: Cross-Article Synthesis Pipeline)

| File | Description |
|------|-------------|
| `scripts/build_concept_clusters.py` | Graph-based article clustering from novelty matrix. Connected components → spectral bisection for large clusters → two-pass LLM labeling (specificity prompt + contrastive refinement for collisions). Outputs `data/concept_clusters.json`. |
| `scripts/generate_syntheses.py` | Complete rewrite. Structured synthesis per cluster via Gemini 3 Flash + tool calling (`call_llm_tool()`). Narrative + shared themes + unique contributions + tensions + follow-up questions + claim coverage map. Claim coverage expansion: article_coverage ≥ 0.6 → include all claims, then similarity cascade ≥ 0.78. Incremental (skips unchanged). |
| `scripts/cleanup_articles.py` | Detects/removes X.com JS error pages, duplicates, short junk. Conservative defaults (--report is dry-run). |
| `scripts/compare_synthesis_models.py` | Model comparison framework for synthesis generation. Tests multiple Gemini models across cluster subsets. |
| `research/synthesis-pipeline-design.md` | Full design doc: investigation findings, architecture, model comparison, prompt iteration, decisions. |

#### New Files (Session 19: "Restrained Folio" Synthesis Reader Redesign)

| File | Description |
|------|-------------|
| `app/components/SynthesisChat.tsx` | Inline chat modal for synthesis discussions. Context builder from synthesis data (title, narrative, tensions, article titles). Auto-sends initial question. Restrained Folio styling (Crimson Pro body, folio color palette). 307 lines. |
| `app/components/ArticlePopover.tsx` | Web-only hover popover for `article:ID` reference links. Smart edge-flipping positioning (flips left/right based on viewport edge). Shows article title, summary, topics, coverage bar. Quick actions: Queue / Seen / Disregard. 194 lines. |

#### Modified Files (Session 19: "Restrained Folio" Synthesis Reader Redesign)

| File | Changes |
|------|---------|
| `scripts/generate_syntheses.py` | Major prompt overhaul: "humanist scholar" system instruction (was "expert research synthesizer"). Article Reference Key section in prompt — ID→title lookup so LLM writes proper `[Title](article:ID)` links. Descriptive `##` headings instead of prescribed structure. Inline `> ⚡ **Tension label**` blockquotes for tensions. Inline `*Open question: ...*` research prompts. `<!-- detail -->` / `<!-- /detail -->` progressive disclosure markers. Structured tensions changed from `string[]` to `Array<{label, description, article_ids}>`. Tool schema updated. max_tokens 8192→12288. Tension normalization in post-processing (handles both old string and new object formats). |
| `app/app/synthesis-reader.tsx` | Complete "Restrained Folio" rewrite. 2-column CSS grid (1fr + 190px sidebar) on web, single column on mobile. Two visual weights only: Cormorant Garamond 30px title + Crimson Pro everything else. Local folio color palette (`fc` constant) replacing design token colors. New sub-components: SynthesisTopBar, enhanced MarkdownContent (renders article links, tension blocks, excerpt blocks, detail sections), TensionBlock (amber border), ExcerptBlock (green border), DetailSection (collapsible), SynthesisSidebar with IntersectionObserver TOC tracking. No uppercase letterspaced labels. |
| `app/data/store.ts` | Feed filtering wired: `getArticleSynthesisCoverage()` integrated into `getRankedFeedArticles()` and `getArticlesByLens()`. Articles with ≥80% synthesis coverage excluded from feed. Articles with ≥50% coverage get score demotion `(1 - coverage * 0.5)`. |
| `app/data/types.ts` | `tensions` type broadened from `string[]` to `Array<string \| { label, description, article_ids? }>` for backward compatibility with old string format. |

#### Modified Files (Session 17: Synthesis Pipeline + Reader)

| File | Changes |
|------|---------|
| `scripts/build_articles.py` | Added `_validate_content()` — rejects junk (empty, JS error pages, too short) before LLM processing. |
| `scripts/gemini_llm.py` | Added `call_llm_tool()` for forced function calling with FunctionDeclaration (`mode='ANY'`). Structured output without JSON parsing. |
| `scripts/content-refresh.sh` | Added steps 3b2 (cleanup), 4b (clustering), 4c (synthesis generation), 4d (manifest hash update for clusters + syntheses). |
| `app/data/types.ts` | Expanded `TopicSynthesis` with cluster_id, claims_covered, article_coverage, follow_up_questions, tensions. Added `SynthesisFollowUpQuestion`. |
| `app/data/content-sync.ts` | Downloads concept_clusters.json + syntheses.json alongside articles. |
| `app/data/store.ts` | Module-level syntheses/clusters, getters (getSynthesisForCluster, getSynthesesForArticle, getArticleSynthesisCoverage), completedSyntheses set with AsyncStorage. |
| `app/data/knowledge-engine.ts` | Added `markClaimsEncountered()` for bulk claim encounter tracking from synthesis reader. |
| `app/app/synthesis-reader.tsx` | Complete rewrite: 3-column CSS Grid web layout (220px/1fr/240px matching article reader). Left margin: metadata, claim coverage bar, actions, keyboard shortcuts. Right margin: source articles with per-article coverage bars, follow-up research questions. Keyboard: Escape/d/gi. Browser-native scroll fix. Mobile: single-column with coverage bars. |
| `app/app/_layout.tsx` | Added synthesis-reader route. |
| `app/app/(tabs)/topics.tsx` | Added SynthesisCard component linking to synthesis-reader. |
| `app/app/(tabs)/index.tsx` | Added synthesis coverage indicator in feed article cards. |

#### New Files (Session 9: Unified Feed Redesign)

| File | Description |
|------|-------------|
| `app/components/DoubleRule.tsx` | Reusable double rule separator (2px + 5px gap + 1px ink lines) using layout tokens. |
| `app/components/LensTabs.tsx` | Horizontal tab switcher for Latest/Best/Topics/Quick lenses. EB Garamond 13px, rubric underline active indicator, logs `lens_switch`. |
| `app/components/UpNextSection.tsx` | Pinned top section: shows in-progress article (with progress bar), next queued, or algorithmic pick. Contains ✦ drawer trigger button. Logs `up_next_tap` with type. |
| `app/components/RecommendedSection.tsx` | Hero card for algorithmically top-ranked article. Cormorant Garamond 20px title, claim preview (green left border), novelty badge, "See all" link. Logs `recommended_tap`. |
| `app/components/TopicPillsSection.tsx` | Horizontal scroll of topic pills from `getArticlesGroupedByTopic()`. First pill gets ink (dark) treatment. Logs `topic_pill_tap`. |
| `app/components/TopicsGroupedList.tsx` | Articles grouped by topic with tree-line indentation. Expand/collapse (shows 3, "+N more" to expand). Optional `topicFilter` prop. Logs `topic_group_article_tap`. |
| `app/components/PetrarcaDrawer.tsx` | Bottom sheet (ink background). Quick actions: Triage, Voice Note. Nav items: Voice Notes, Activity Log, Reading Progress, Queue. Logs `drawer_open/close`, `drawer_item_tap`. |
| `research/feed-redesign-plan.md` | Comprehensive plan: 3 rounds of mockup feedback, approved architecture, screen layout, 5-phase implementation order, component specs. |

#### Modified Files (Session 14: Parsing Fix + Mobile Feed Overlap)

| File | Changes |
|------|---------|
| `scripts/build_articles.py` | XML-first extraction: `_xml_to_markdown()` converts trafilatura XML preserving `<p>` boundaries with link/bold/italic handling. `_split_long_paragraphs()` splits prose >200w at sentence boundaries (Latin/Greek/Cyrillic). Tweet text `\n`→`\n\n` normalization in bookmark processing. `fetch_method` now persisted in article JSON. `from xml.etree import ElementTree` added. |
| `scripts/clean_existing_articles.py` | Auto-detects server (`/opt/petrarca/data/`) vs local path. `count_issues()` now reports `long_paragraphs` count. |
| `scripts/research-server.py` | Tweet paragraph normalization in `run_ingest_tweet()`: single `\n` → `\n\n` for non-threaded tweets. |
| `app/app/(tabs)/index.tsx` | Mobile feed overlap fix: header moved from `ListHeaderComponent` into data array as `data[0]`, `stickyHeaderIndices` [0]→[1], `onViewableItemsChanged`/`viewabilityConfig` stabilized via `useRef`, `removeClippedSubviews={false}`, `scrollToIndex` offset +1→+2. |
| `app/app/reader.tsx` | Arrow-key scroll fix: override `body { overflow: auto }` on mount (React Native Web sets `hidden`). Inject `outline: none` on `div:focus, body:focus`. Top bar: `top: 0` + `paddingTop: 4`. |

#### Modified Files (Session 12: Desktop Web Layouts)

| File | Changes |
|------|---------|
| `app/app/(tabs)/index.tsx` | Web layout: ScrollView replaces FlatList, CSS Grid 2-column article grid (1100px max), hover ✓ (archive) and ✕ (dismiss) buttons on cards, Up Next auto-focused on web (focusedIndex=-1), hero articles (Up Next + Recommended) excluded from grid, `gi` multi-key shortcut, `webArticles`/`effectiveFocusedArticleId` for filtered keyboard nav. |
| `app/app/reader.tsx` | Web: browser-native scroll (View replaces ScrollView in center column), `window.scroll` listener for progress tracking. 3-column CSS Grid: left margin (metadata, novelty, mode toggle, actions, full shortcut list), right margin (up next, connected, follow-up, related). Top bar: prev/next article links. `gi` shortcut. Container removes `flex:1` on web. |
| `app/hooks/useKeyboardShortcuts.ts` | Multi-key sequence support: buffers prefix key for 500ms, matches 2-char sequences (e.g. "gi"). Falls back to standalone handler if no second key. |
| `app/components/UpNextSection.tsx` | Added `isFocused` prop with rubric left border + subtle background visual indicator. |
| `app/components/LensTabs.tsx` | Changed maxWidth from `contentMaxWidth` to `webFeedMaxWidth` (1100px). |
| `app/components/KeyboardHintBar.tsx` | Changed inner maxWidth from 680 to 1100px. |
| `app/design/tokens/spacing.ts` | Added web layout tokens: `webFeedMaxWidth` (1100), `webReaderMaxWidth` (1120), `webReaderLeftMargin` (190), `webReaderRightMargin` (210), `sidebarNavWidth` (220), `contentMaxWidth` (960). |

#### New Files (Session 11b: Feedback Capture + More Questions + Auto-Advance + Topic Signals)

| File | Description |
|------|-------------|
| `app/components/FeedbackCapture.tsx` | Floating ✦ feedback button (bottom-right). Tap captures screenshot (react-native-view-shot) + opens voice/text overlay with auto-detected context (screen, article, lens, reading state). Uploads screenshot (PNG) + audio (m4a) + text + context JSON to `POST /feedback`. Falls back to local AsyncStorage. Long-press hides (persisted). Events: `feedback_capture_start/complete/dismiss`. |
| `app/lib/feedback-context.ts` | Module-level feedback context store. `setFeedbackContext()` merges partial updates, `getFeedbackContext()` returns snapshot. Screens call `setFeedbackContext()` on mount/state change to propagate current screen, article ID/title, active lens, reading mode, scroll progress. |

#### Modified Files (Session 11b: Feedback Capture + More Questions + Auto-Advance + Topic Signals)

| File | Changes |
|------|---------|
| `app/app/_layout.tsx` | Added `FeedbackCapture` component (global floating button). |
| `app/app/(tabs)/index.tsx` | Redesigned topic interest signals: `isTopicNew()` function, `KnownTopicDot` component (tap-to-cycle), new topics get left-bordered +/− rows, known topics get compact dot-list. Removed old `TopicLevelRow` and chip styles. Added `getInterestProfile` import. |
| `app/app/reader.tsx` | "More questions" button in FURTHER INQUIRY with pulsing ✦ animation. Queue auto-advance: `advanceOrGoBack()` replaces `router.back()`, "UP NEXT" toast with escape button. Topic signal redesign matching index.tsx changes. |
| `app/lib/chat-api.ts` | Added `generateMoreQuestions()`, `uploadFeedback()` (multipart FormData with web data-URI→Blob conversion for screenshots). |
| `app/components/KeyboardHintBar.tsx` | Modified (minor). |
| `app/components/LensTabs.tsx` | Modified (minor). |
| `scripts/build_articles.py` | Extraction prompt generates 4 follow-up questions (was 2-3), with broader/more divergent framing. |
| `scripts/research-server.py` | New `POST /generate-questions` endpoint. New `POST /feedback` endpoint — accepts multipart/form-data (screenshot PNG, audio m4a, text, context JSON), saves to `/opt/petrarca/data/feedback/`, background Soniox transcription for audio. |

#### Modified Files (Session 11: Clipper Immediate Save + Reader Actions + Feed Metadata)

| File | Changes |
|------|---------|
| `clipper/popup.js` | Save moved to background worker via `fireImmediateSave()`. `doSave()` simplified to send note (if any) and show saved state. Cancel/Escape send `cancelSave` message. |
| `clipper/popup.html` | PETRARCA wordmark changed to clickable `<a>` with `id="open-app"`. |
| `clipper/popup.css` | Wordmark hover style (opacity 0.7 transition). |
| `clipper/background.js` | Added `addNote` → `POST /ingest-note`, `cancelSave` → `POST /ingest-cancel` handlers. `saveClip` gets offline fallback via `storeLocally()`. |
| `app/app/(tabs)/index.tsx` | Added `formatRelativeDate()` (minute/hour/day precision from ISO timestamps), `formatSourceLabel()` (maps source types to display labels). `ArticleCard` gets `showIngestInfo` prop, shown only on Latest lens. |
| `app/app/reader.tsx` | Added "Report bad scrape" menu item (`reportBadScrape()` → `/report-scrape`). Added "Disregard" menu item (dismiss + navigate back). Imported `dismissArticle` from store. |
| `app/lib/chat-api.ts` | Added `reportBadScrape()` function. |
| `app/data/types.ts` | Added `ingested_at?: string` to Article interface. |
| `scripts/import_url.py` | Added `ingested_at` ISO timestamp to article dict. |
| `scripts/build_articles.py` | Added `ingested_at` ISO timestamp to article dict. |
| `scripts/research-server.py` | Added `SCRAPE_REPORTS_PATH`. New endpoints: `POST /ingest-note` (sidecar write), `POST /ingest-cancel` (remove from articles.json), `POST /report-scrape` (append to scrape queue), `GET /scrape-reports` (list pending). |

#### Modified Files (Session 10: Clipper + Tweet Ingestion)

| File | Changes |
|------|---------|
| `clipper/popup.html` | Header gets countdown number + timer overlays on double rule. Note field always visible (dashed placeholder). Note toggle button removed. Cancel button added. |
| `clipper/popup.css` | Timer overlay animation (rubric drains to gray), countdown number (Cormorant 22px), dashed→solid note field transition on focus, Cancel button, gold completion flash (#c9a84c). |
| `clipper/popup.js` | Complete rewrite of save flow. 10s countdown via `requestAnimationFrame` (smooth pause/resume). States: counting → paused (on typing) → saving → saved. Auto-save at 0, Cancel button + Esc. |
| `clipper/manifest.json` | Added `cookies` permission + `host_permissions` for `*.x.com` and `*.twitter.com`. |
| `clipper/background.js` | Added `maybeSyncTwitterCookies()`: extracts `auth_token` + `ct0` via `chrome.cookies.get()` on X.com visits, POSTs to `/twitter/cookies`. Throttled to 4h via `chrome.storage.local` timestamp. `tabs.onUpdated` listener triggers on page load complete. |
| `scripts/research-server.py` | Added tweet URL detection (`_is_tweet_url`), `run_ingest_tweet()` (twikit fetch → thread reconstruction → URL extraction → normal pipeline), `_fetch_tweet_via_twikit()` (async), `_check_twikit_cookies()`. New endpoints: `GET /twitter/status`, `POST /twitter/cookies`. `/ingest` now routes tweet URLs through twikit. |

#### Modified Files (Session 9: Unified Feed Redesign)

| File | Changes |
|------|---------|
| `app/app/(tabs)/index.tsx` | Complete rewrite. Single FlatList with ListHeaderComponent (UpNext → Recommended → Topics → DoubleRule). Lens tabs as sticky `data[0]` via `stickyHeaderIndices={[0]}`. Articles sorted/grouped by active lens. Swipe dismiss/queue preserved. `useFocusEffect` triggers rerank on return from reader. No header chrome (no app name, no date). ~320 lines (was 728). |
| `app/app/(tabs)/_layout.tsx` | Tab bar hidden (`display: 'none'`). Topics/Queue/Log routes preserved with `href: null` for drawer navigation access. ~40 lines (was 82). |
| `app/data/store.ts` | Added `FeedLens` type, `getTopRecommendedArticle()` (highest-scored not in queue/in-progress), `getArticlesByLens()` (filters+sorts by lens), `getArticlesGroupedByTopic()` (groups by broad topic), `getInProgressArticles()`, `getFeedVersion()`/`bumpFeedVersion()` (reactive counter). Integrated `isKnowledgeReady()` + `_getArticleNovelty()` into `getRankedFeedArticles()`: blended score = interest (60%) + curiosity (40%). Quick lens also uses blended scoring. |
| `app/data/queue.ts` | Added `getNextQueued()` (front of queue without removing), `peekQueue(n)` (first N items). |
| `research/README.md` | Added UX Redesign section linking to `feed-redesign-plan.md`. |
| `research/experiment-log.md` | Session 9 entry: design exploration (3 rounds), user interview findings, implementation details, 8 hypotheses to validate, events logged. |

#### New Files (Session 8: Swarm Build + Topic Normalization)

| File | Description |
|------|-------------|
| `app/components/RelatedArticles.tsx` | Related articles component at bottom of reader. Three relationship finders (same topic, shared concepts via knowledge index, same source). Deduped, max 3 per group. Design system tokens. |

#### New Files (Session 8: Topic Hierarchy + Cross-Article + Normalization)

| File | Description |
|------|-------------|
| `scripts/topic_registry.json` | Canonical topic registry — 12 broad categories, 21 specific topics, each with include/exclude descriptions for LLM disambiguation. Hard limits: `max_broad: 25`, `max_specific_per_broad: 15`. Inspired by Otak's `tree_balance.py` approach but avoids its unbounded growth. |
| `scripts/topic_normalizer.py` | Topic normalization + defragmentation. `normalize_article_topics()` validates against registry via LLM merge-or-create. `defragment_registry()` consolidates overpopulated categories. `registry_needs_defrag()` checks if limits exceeded. |

#### Modified Files (Session 8: Topic Hierarchy + Cross-Article + Normalization)

| File | Changes |
|------|---------|
| `app/app/reader.tsx` | Redesigned `PostReadInterestCard` with hierarchical topic display: `TopicGroup` interface, `groupTopicsByBroad()`, `TopicLevelRow` with tree lines + level badges (broad/topic/entity), smart expand (≤2 broad → expanded). Added `ConnectedReadingSection` (bottom section: shared claim counts, read status, queue buttons). Added `InlineCrossArticleAnnotation` (inline "Also in: [title]" below paragraphs). ~400 lines added. |
| `app/data/interest-model.ts` | Added `recordTopicSignalAtLevel()` — signals at exactly one hierarchy level without cascading. Updated `computeInterestMatch()` to include entity-level scores via `Math.max(specificScore, broadScore * 0.7, entityScore)`. |
| `app/data/queue.ts` | Added `addToQueueFront()` — LIFO queue insertion for cross-article connections (user wants "next article I see would be this one"). |
| `app/data/knowledge-engine.ts` | Added `CrossArticleConnection` interface and two new functions: `getCrossArticleConnections()` (groups similar claims by article, max 5 results), `getParagraphConnections()` (maps paragraph indices to connected articles via claim-to-paragraph mapping from knowledge index). |
| `app/data/store.ts` | Added export wrappers: `recordTopicInterestSignalAtLevel()`, `getCrossArticleConnections()`, `getParagraphConnections()`. |
| `scripts/build_articles.py` | Integrated topic normalizer: loads registry once, normalizes each article's `interest_topics` via `normalize_interest_topics()`. Added `_get_topic_hint()` — injects existing categories into LLM extraction prompt. Added `--normalize-topics` for batch re-normalization, `--defrag-topics` for automatic defragmentation. Extended `--enrich` to also backfill `interest_topics`. |
| `scripts/content-refresh.sh` | Added step 3c3: automatic topic defragmentation check after article processing. |

#### Modified Files (Session 6: Activity Log)

| File | Changes |
|------|---------|
| `app/data/logger.ts` | Added AsyncStorage-backed offline queue (`savePendingPayload`, `flushPendingLogs`). Failed server sends are persisted and retried on session start + piggybacked on successful flushes. |
| `app/app/(tabs)/_layout.tsx` | Added 4th "Log" tab to tab bar. |
| `app/design/tokens/colors.ts` | Added `research: '#6a3a8a'` color token for research event dots. |
| `scripts/research-server.py` | Added `GET /activity/feed?days=N` endpoint. Aggregates interaction logs, pipeline events, and research results into grouped timeline nodes (reading sessions, interest signals within 60s, pipeline runs within 15min). |
| `scripts/content-refresh.sh` | Added `pipeline_log()` function writing structured JSONL to interaction log dir. Logs pipeline_start, each major step, and pipeline_complete with elapsed time. |

#### Modified Files (Session 4+5: LLM migration + four features)

| File | Changes |
|------|---------|
| `scripts/build_articles.py` | Migrated from litellm to `gemini_llm.call_llm()`. Added `_locked_append_article()` with `fcntl.flock` for write contention safety. Extended prompt schema with `entities[]` and `follow_up_questions[]`. Fixed `normalize_topic()` to handle dict inputs. |
| `scripts/research-server.py` | Migrated chat from litellm to `gemini_llm.call_chat()`. Rewrote topic research from `claude -p` to `gemini_llm.call_with_search()` (Gemini search grounding). Added `extract_note_actions()` for LLM intent extraction from transcripts. Added `POST /notes/{note_id}/execute-action` endpoint. `/ingest` now returns `ingest_id` + deterministic `article_id`. Added `GET /ingest-status?id=` for polling. |
| `scripts/import_url.py` | Added import of `_locked_append_article` from `build_articles` for concurrent write safety. |
| `app/data/types.ts` | Added `ArticleEntity` interface (7 entity types), `FollowUpQuestion` interface, extended `Article` with `entities?` and `follow_up_questions?`. |
| `app/app/reader.tsx` | Added `EntityHighlightText` (dotted underline on entity mentions, long-press popup), `EntityPopup` (inline marginalia card with entity info + "Research more"), `FollowUpSection` ("✦ FURTHER INQUIRY" section after article with tappable research questions). ~320 lines added. |
| `app/app/(tabs)/index.tsx` | Added "Notes" link in feed header navigating to `/voice-notes`. |
| `app/app/_layout.tsx` | Added `voice-notes` screen to Stack navigator. |

#### Modified Files (Mar 8 session 2)

| File | Changes |
|------|---------|
| `app/app/reader.tsx` | Added ⋯ menu (article info, source, Ask AI, voice note, research topic), ☆ bookmark toggle, AI chat modal, voice feedback panel. `buildAIChatContext()` builds article context string for LLM. |
| `app/app/(tabs)/index.tsx` | Guide link in header, topic normalization for filter chips and tags, `minHeight: 44` on filter scroll. |
| `app/app/(tabs)/topics.tsx` | "↗ Find more on [Topic]" research button in expanded topic clusters. Topic normalization for grouping/display. |
| `app/data/interest-model.ts` | Added `bookmark_add` (weight 1.5) and `bookmark_remove` (weight 0.5) signal types. |
| `app/data/store.ts` | Loads bookmarks on init alongside queue. |
| `app/lib/display-utils.ts` | Added `normalizeTopic()` and `displayTopic()` shared utilities. |
| `scripts/research-server.py` | Added `/chat` (Gemini Flash chat), `/note` (audio upload + Soniox transcription), `/research/topic` (claude -p topic research + auto-ingest), `/notes` GET. |

#### Modified Files (original build)

| File | Changes |
|------|---------|
| `app/data/types.ts` | Added 9 types: `KnowledgeIndex`, `DeltaReport`, `NoveltyClassification`, `ClaimKnowledgeEntry`, `ClaimClassification`, `ParagraphDimming`, `ArticleNovelty` |
| `app/data/content-sync.ts` | Downloads `knowledge_index.json` alongside articles. Added `KNOWLEDGE_INDEX_URL`, `knowledge_index_hash` to manifest checking, graceful fallback if index doesn't exist. |
| `app/data/store.ts` | Imports and initializes knowledge engine + queue in `initStore()`. Exports wrapper functions. Added bundled fallback `require('./knowledge_index.json')`. |
| `app/app/reader.tsx` | 3 reading modes (Full/Guided/New Only), paragraph dimming via `blockDimming` map, collapsible familiar sections (`CollapsedBar` component), "What's new for you" claims card, `ReadingModeToggle` component, `buildParagraphToBlockMap()` for mapping pipeline paragraph indices to markdown block indices. Calls `markArticleEncountered()` on Done. |
| `app/app/(tabs)/index.tsx` | Curiosity-zone re-ranking (with 0.05 threshold for stability), topic filter chips (horizontal ScrollView), swipe-right-to-queue, novelty hints ("N new claims"), `ContinueReadingCard` component (limited to 2 most recent). Interaction logging for swipe-dismiss and swipe-queue. |
| `app/app/(tabs)/_layout.tsx` | Originally 3-tab layout → expanded to 4 tabs (session 6) → **session 9: tab bar hidden, single screen with drawer**. Routes preserved via `href: null`. |
| `app/data/logger.ts` | Dual-write logging: local (localStorage/filesystem) + server buffer (batched POST to port 8091 every 5s). AsyncStorage-backed offline queue retries failed sends on session start. |
| `scripts/content-refresh.sh` | Full 6-step pipeline: fetch sources → build articles → validate → extract entities → extract claims → embed claims → build knowledge index → copy to nginx. Writes structured JSONL pipeline events to interaction log for activity feed. |

### Data Generated

| File | Size | Contents |
|------|------|----------|
| `data/articles.json` | ~7 MB | 237 articles with `atomic_claims[]`, `entities[]`, `follow_up_questions[]` (36 junk removed) |
| `data/claim_embeddings.npz` | ~50 MB | 4,831 Gemini embedding-001 vectors |
| `data/knowledge_index.json` | ~8 MB | 4,831 claims, cross-article similarity pairs (≥0.68), article paragraph maps, article novelty matrix, LLM delta reports |
| `data/concept_clusters.json` | 214 KB | 29 clusters from graph-based article clustering, unique contrastive labels |
| `data/syntheses.json` | 350 KB | 26 structured syntheses (narrative + themes + tensions + follow-up questions + claim coverage maps) |
| `data/llm_audit.jsonl` | ~100 KB | Per-call LLM usage records (tokens, cost, model, purpose) |

### Algorithm Parameters (validated by experiments)

| Parameter | Value | Source |
|-----------|-------|--------|
| KNOWN threshold | ≥ 0.78 cosine | Nomic calibration experiment |
| EXTENDS threshold | ≥ 0.68 cosine | Nomic calibration experiment |
| FORGOTTEN threshold | R < 0.3 | FSRS standard |
| Stability (skim) | 9 days | FSRS experiment |
| Stability (read) | 30 days | FSRS experiment |
| Stability (highlight) | 60 days | FSRS experiment |
| Reinforcement factor | 2.5× | FSRS standard |
| Curiosity peak | 70% novelty | Curiosity zone experiment |
| Curiosity Gaussian σ | 0.15 | Curiosity zone experiment |
| Similarity index threshold | ≥ 0.68 | Pairs below this are always NEW |
| Feed re-rank threshold | 0.05 | Prevents unstable sorts when scores are close |

---

## Deployment Status

### Server (Hetzner: alifstian.duckdns.org)

| Component | Status | Notes |
|-----------|--------|-------|
| nginx content server (:8083) | ✅ Working | Serves articles.json, knowledge_index.json, manifest.json |
| Static web app (:8084) | ✅ Deployed | Session 19: "Restrained Folio" synthesis reader, inline chat, article popovers, feed filtering |
| Expo native (:8082) | ✅ Running | systemd `petrarca-expo` |
| Log server (:8091) | ✅ Running | systemd `petrarca-log`, collects app interaction logs |
| articles.json | ✅ 182 articles | Full corpus with atomic claims, entities, follow-up questions |
| knowledge_index.json | ✅ 4.3MB | 300 delta reports, novelty matrix, paragraph maps |
| claim_embeddings.npz | ✅ 33MB | Gemini embedding-001, 2,954 vectors |
| manifest.json | ✅ Updated | `articles_hash` + `knowledge_index_hash` |
| llm_audit.jsonl | ✅ Collecting | 330 records from pipeline run ($0.035 total) |
| Python deps | ✅ All installed | numpy, google-genai (native SDK) in `/opt/petrarca/.venv` |
| Cron pipeline | ✅ Working | `content-refresh.sh` runs full pipeline including claims + embeddings + knowledge index |
| GEMINI_KEY | ✅ Configured | In `/opt/petrarca/.env` (used by `gemini_llm.py`, also `GEMINI_API_KEY` alias) |
| Voice notes storage | ✅ Working | `/opt/petrarca/data/notes/` (JSON) + `/opt/petrarca/data/audio/` (m4a) |
| Chat conversations | ✅ Working | `/opt/petrarca/data/chats/` (JSON, per conversation_id) |
| Research server endpoints | ✅ Updated | `/chat`, `/note`, `/research/topic`, `/notes`, `/notes/{id}/execute-action`, `/research`, `/research/results`, `/twitter/status`, `/twitter/cookies`, `/ingest-note`, `/ingest-cancel`, `/report-scrape`, `/scrape-reports`, `/generate-questions`, `/review/microlearning` on port 8090 |
| Scrape reports queue | ✅ Working | `/opt/petrarca/data/scrape_reports.json` — user-reported bad scrapes, `GET /scrape-reports` lists pending. **Review periodically** to identify scraping failure patterns and strengthen the pipeline (e.g. site-specific extractors, better fallback logic). |

### SSH Access
- Use `ssh alif` (configured in `~/.ssh/config` → `root@46.225.75.29` via `~/.ssh/hetzner_ed25519`)

---

## Known Issues & Bugs

### UI Issues (from user screenshot, Mar 8)

1. **Filter chips row clipped** — **RESOLVED**: Changed `maxHeight: 40` to `flexGrow: 0`.
2. **Continue Reading section too large** — **RESOLVED**: Limited to 2 most recent.
3. **Continue Reading cards have card-like backgrounds** — **RESOLVED**: Removed parchmentDark background.
4. ~~**UI not visually tested**~~ — **RESOLVED**: Visual testing done with agent-browser. Confirmed all screens render correctly. Topics expansion works (Playwright click issue was a false positive — React Native Web Pressable needs DOM `.click()`, not Playwright's `click @ref`).

### Data Issues

5. ~~**Server has only 47 articles**~~ — **RESOLVED**: Full 171-article corpus restored with 2,954 atomic claims, embeddings, and knowledge index.
6. ~~**Duplicate topic variants**~~ — **RESOLVED**: Added client-side topic normalization in `app/lib/display-utils.ts` (`normalizeTopic()` + `displayTopic()`). Used across feed filter chips, topic tags, and Topics tab grouping. Reduced 67→58 topic groups.
7. ~~**google.generativeai deprecation warning**~~ — **RESOLVED**: Migrated all LLM calls to `google.genai` SDK via shared `gemini_llm.py` wrapper. litellm fully removed.
11. ~~**Twitter cookies expire**~~ — **RESOLVED**: Chrome extension auto-syncs cookies to server on X.com visits (4h throttle). Also available via `POST /twitter/cookies` API and `GET /twitter/status` health check.

### Server Issues

15. ~~**Single-threaded server causes capture failures**~~ — **RESOLVED** (session 28): `HTTPServer` → `ThreadingHTTPServer`. Rapid photo captures no longer cause `ConnectionResetError` from queued requests blocking behind slow Gemini Vision calls.
16. ~~**No retry for failed photo OCR**~~ — **RESOLVED** (session 28): Photo retry queue added (parallel to existing voice retry). Failed captures auto-retry on book-detail focus.

### Logic Issues

8. **Reading mode toggle shows even when no dimming** — Fixed: now checks `Array.from(blockDimming.values()).some(d => d.opacity < 1)`.
9. **Feed sort unstable with empty ledger** — Fixed: added 0.05 threshold + rank tiebreaker so interest model order is preserved until curiosity scores meaningfully diverge.
10. **Paragraph-to-block mapping is heuristic** — `buildParagraphToBlockMap()` uses text prefix matching (first 50 chars). May mismap in articles with repeated paragraph openings.
12. ~~**Synthesis markdown has raw hex claim IDs**~~ — **RESOLVED** (session 19): Synthesis prompt redesigned with Article Reference Key section. LLM now writes proper `[Title](article:ID)` links instead of raw hex claim IDs like `[3d282718e065]`.
13. ~~**Feed does not filter synthesis-covered articles**~~ — **RESOLVED** (session 19): `getArticleSynthesisCoverage()` wired into `getRankedFeedArticles()` and `getArticlesByLens()`. Articles with ≥80% coverage excluded, ≥50% demoted.
14. ~~**Synthesis reader missing claim classification / paragraph dimming**~~ — Partially addressed (session 19): Synthesis reader completely rewritten with "Restrained Folio" design including inline chat, article popovers, and progressive disclosure. Claim classification and paragraph dimming in synthesis context remain future work.

---

## How the Knowledge System Works (User Perspective)

### First Use (Empty Ledger)
1. All claims classify as NEW (no ledger entries to compare against)
2. Feed shows articles ranked by interest model (curiosity scoring has no effect yet)
3. Reader shows "What's new for you" card with novel claims from the knowledge index
4. Reading mode toggle does NOT appear (no familiar blocks to dim)
5. User reads article → Done → claims recorded in ledger with stability=30d

### After Reading Several Articles
1. Open an article on a related topic → knowledge engine finds similar claims via cosine similarity
2. Claims matching ledger entries at ≥0.78 → KNOWN, ≥0.68 → EXTENDS, <0.68 → NEW
3. Paragraph dimming computed: familiar paragraphs get opacity 0.55, novel get 1.0, mixed get blended
4. Reading mode toggle appears:
   - **Full** — all content at normal opacity
   - **Guided** — familiar paragraphs dimmed (opacity from dimming map)
   - **New Only** — familiar blocks collapsed into "N familiar sections" bars, tap to expand
5. Feed re-ranks: articles with ~70% novelty ratio score highest (curiosity zone)

### Knowledge Decay
- Claims fade over time: R = e^(-t/S) where S = stability_days
- Skim=9d, Read=30d, Highlight=60d
- Re-reading reinforces: stability × 2.5
- Forgotten when R < 0.3 → claim treated as unknown again

### Topics & Delta Reports
- Topics tab groups articles by broad topic from `interest_topics`
- Expanding a topic shows the LLM-generated delta report: "What's new in [topic]"
- Delta reports are pre-generated by `build_knowledge_index.py` using Gemini Flash
- Each report: summary paragraph + top 5 claims

---

## Next Steps (Priority Order)

### Completed
1. ~~**Visual testing**~~ — DONE
2. ~~**Topic normalization**~~ — DONE
10. ~~**Research agent button**~~ — DONE: "↗ Research [topic]" in reader menu and Topics tab, spawns `claude -p`, auto-ingests found articles
11. ~~**Voice notes**~~ — DONE: Record in reader → upload to server → async Soniox transcription → stored as notes linked to article + topics
12. ~~**Resourceful bookmark pipeline**~~ — DONE: `build_articles.py --entities` detects short tweets mentioning books/people/products, uses Gemini Flash to extract entities, synthesizes mini-articles. Runs as step 3c2 in cron pipeline. Tested: 5 entity articles ingested successfully.
13. ~~**Topic +/- buttons fixed**~~ — DONE: Per-topic signals (not all topics), visual feedback on votes
14. ~~**Feed refresh on return from reader**~~ — DONE: `useFocusEffect` triggers recalculation of feed, read articles, and continue reading lists
15. ~~**Robust voice recording**~~ — DONE: Saves locally first → uploads in background → retry queue for failures
16. ~~**Long-press entity research**~~ — DONE: Long-press paragraph → action menu (Highlight / Research / Ask AI). Research opens AI chat with passage context.
17. ~~**Feed "..." menu**~~ — DONE: Voice feedback + stats from main feed screen
18. ~~**Inline topic chips**~~ — DONE: +/- buttons at end of article content, not just post-read modal
19. ~~**AskAI initialQuestion**~~ — DONE: Pre-fill AI chat with questions from research context

### Completed (Session 4+5)
4. ~~**Voice note visibility**~~ — DONE: Voice notes browser screen (`voice-notes.tsx`), accessible from Feed header "Notes" link. Date-grouped notes with transcript, duration, article link, action chips.
5. ~~**Voice note action extraction**~~ — DONE: `extract_note_actions()` in research-server.py uses Gemini to extract research/tag/remember intents from transcripts. Actions shown as tappable chips in VoiceNoteCard. Execute via `POST /notes/{id}/execute-action`.
6. ~~**Claude CLI token expired**~~ — RESOLVED: Topic research completely rewritten from `claude -p` to Gemini search grounding (`call_with_search()`). No longer depends on Claude CLI.
7. ~~**Follow-up research prompts**~~ — DONE: Pipeline extracts 2-3 curiosity-driven questions per article. "✦ FURTHER INQUIRY" section in reader after claims. Tap to spawn topic research via `/research/topic`.
20. ~~**Entity deep-dive**~~ — DONE: Pipeline extracts entities (person/book/company/concept/event/place/technology). Reader highlights entity mentions with dotted underline. Long-press shows marginalia popup with synthesis + "Research more".
21. ~~**LLM migration**~~ — DONE: All LLM calls use `google.genai` SDK via `gemini_llm.py`. litellm removed. Default model: Gemini 3.1 Flash-Lite.

### Completed (Session 6)
22. ~~**Re-run pipeline for entities/questions**~~ — DONE: Added `--enrich` flag to `build_articles.py`. All 182 articles now have entities (1,062 total) and follow-up questions (499 total).
23. ~~**Resourceful bookmark pipeline enhancement**~~ — DONE: `research_entity()` now uses Gemini search grounding (`call_with_search()`) for real Google-grounded results instead of plain LLM synthesis.
24. ~~**Server robustness**~~ — DONE: Added `_read_json_body()` / `_send_json_response()` helpers to research server. All 8 POST endpoints now return clean 400 errors on malformed JSON instead of crashing. File read errors in `execute-action` also handled.
25. ~~**Voice notes error handling**~~ — DONE: `handleActionExecute` in `voice-notes.tsx` now catches errors instead of crashing on network failures.
11. ~~**Production bundle optimization**~~ — Already done: `knowledge_index.json` is gitignored, not bundled.

### Completed (Session 7)
26. ~~**Scroll-aware encounter tracking**~~ — DONE: `markArticleReadUpTo()` only marks claims in paragraphs the user scrolled past. Estimates furthest paragraph from `(maxScrollY + viewportHeight) / contentHeight`. Engagement: 'read' (>60s) or 'skim' (≤60s). "Done" button still marks all claims.
27. ~~**Curated "What's new" card**~~ — DONE: Prioritizes non-factual claim types (causal, evaluative, comparative, procedural) over plain factual. Capped at 3 items. Added `claim_type` to `ClaimClassification`.
28. ~~**G1 descoped**~~ — Per-claim feedback UI explored via 4 design mockups. Decided knowledge model should infer from behavioral signals, not explicit per-claim buttons.

### Completed (Session 8)
29. ~~**Hierarchical topic feedback (G9)**~~ — DONE: PostReadInterestCard redesigned with hierarchical display (broad → specific → entity). `recordTopicSignalAtLevel()` for level-specific signaling without cascade. Smart expand logic.
30. ~~**Cross-article connections (G10)**~~ — DONE: Inline "Also in: [title]" annotations below paragraphs + "✦ CONNECTED READING" bottom section with queue-first behavior (LIFO via `addToQueueFront()`). Max 2 annotations per paragraph, max 5 connected articles.
31. ~~**LLM-verified topic normalization**~~ — DONE: Canonical topic registry (`topic_registry.json`) with include/exclude descriptions. `topic_normalizer.py` validates new topics against registry via LLM merge-or-create decisions. Build pipeline injects existing categories into extraction prompt for consistency from the start. Lessons from Otak's `tree_balance.py` applied: include/exclude descriptions work, but avoid unbounded tree growth.
32. ~~**Automatic topic defragmentation**~~ — DONE: `defragment_registry()` consolidates when limits exceeded. Phase 1: merge similar specifics per overpopulated broad. Phase 2: minimal broad merges. Phase 3: update all articles. Auto-runs as pipeline step 3c3. First run: 28→25 broad, 263→172 specific. See `research/topic-normalization-spec.md` for full spec.
33. ~~**Backfill interest_topics**~~ — DONE: Extended `--enrich` to also generate `interest_topics`. All 185 articles now have hierarchical topics, normalized and defragmented.

### Completed (Session 9)
34. ~~**Entity-link merge**~~ — DONE: When text is both a markdown link and a pipeline entity, the entity popup wins. URL is passed as context: shown in popup, used for smart actions. Article-like URLs (containing `/blog/`, `/article/`, `/introducing/`) get "Save article" (auto-ingest). All others get "Research more" with URL as context for Gemini search grounding. Linked entity mentions get rubric-colored dotted underline.
35. ~~**Ingest auth fix**~~ — DONE: Reader-originated ingests (`source: reader_link`) skip auth token check on `/ingest` endpoint. Previously all ingests required `X-Petrarca-Token`, causing 401 failures from the app.
36. ~~**Entity tap (not just long-press)**~~ — DONE: Entity mentions respond to `onPress` instead of `onLongPress` for better discoverability.

### Completed (Session 19: "Restrained Folio" Synthesis Reader Redesign)
51. ~~**Synthesis prompt overhaul**~~ — DONE: `generate_syntheses.py` rewritten with "humanist scholar" system instruction. Article Reference Key section provides ID→title lookup so LLM writes proper `[Title](article:ID)` links. Descriptive `##` headings instead of prescribed structure. Inline tension blockquotes (`> ⚡ **label**`), inline research prompts (`*Open question: ...*`), `<!-- detail -->` progressive disclosure markers. Structured tensions changed from `string[]` to `Array<{label, description, article_ids}>`. max_tokens 8192→12288. Tested on Pirandello + AI orchestration clusters.
52. ~~**"Restrained Folio" synthesis reader**~~ — DONE: Complete rewrite of `synthesis-reader.tsx`. 2-column CSS grid (1fr + 190px sidebar) on web, single column on mobile. Two visual weights: Cormorant Garamond 30px title + Crimson Pro everything else. Local folio color palette. Sub-components: TensionBlock (amber border), ExcerptBlock (green border), DetailSection (collapsible), SynthesisSidebar with IntersectionObserver TOC tracking. No uppercase letterspaced labels.
53. ~~**SynthesisChat component**~~ — DONE: `app/components/SynthesisChat.tsx` (307 lines). Inline chat modal for synthesis discussions. Context builder from synthesis data. Auto-sends initial question. Restrained Folio styling.
54. ~~**ArticlePopover component**~~ — DONE: `app/components/ArticlePopover.tsx` (194 lines). Web-only hover popover for article reference links. Smart edge-flipping positioning. Coverage bar, quick actions (Queue/Seen/Disregard).
55. ~~**Feed synthesis coverage filtering**~~ — DONE: `getArticleSynthesisCoverage()` wired into `getRankedFeedArticles()` and `getArticlesByLens()`. Articles with ≥80% synthesis coverage excluded from feed. Articles with ≥50% coverage get score demotion `(1 - coverage * 0.5)`.

### Completed (Session 11b)
47. ~~**Floating feedback capture**~~ — DONE: `FeedbackCapture.tsx` — floating ✦ button on every screen. Tap opens voice/text overlay with auto-detected context (screen, article ID). Long-press hides (persisted to AsyncStorage). Saves locally to `@petrarca/feedback_items`. TODO: screenshot capture, server upload.
48. ~~**Expanded follow-up questions**~~ — DONE: Pipeline now generates 4 questions per article (was 2-3) with broader framing. "More questions" button in FURTHER INQUIRY section generates 3 more via `POST /generate-questions` (avoids duplicates). Pulsing ✦ animation while loading.
49. ~~**Queue auto-advance**~~ — DONE: After finishing article + closing interest card, auto-navigates to next queued article via `router.replace()`. "UP NEXT: {title}" toast with "← Feed" escape button. `advanceOrGoBack()` replaces all `router.back()` calls.
50. ~~**Hybrid topic interest signals**~~ — DONE: Replaced binary +/- chips with hybrid minimal design. Single signal model: interested/neutral/less. New topics (zero signals, ≤1 articles) get prominent left-bordered +/− rows. Known topics get compact flowing dot-list with tap-to-cycle `KnownTopicDot`.

### Completed (Session 11)
41. ~~**Clipper immediate save**~~ — DONE: Save fires immediately via background service worker on popup open (survives popup close). Cancel/Escape sends `POST /ingest-cancel` to undo. Notes sent separately via `POST /ingest-note`. Offline fallback queues to `chrome.storage.local`.
42. ~~**PETRARCA wordmark opens app**~~ — DONE: Clicking the wordmark in clipper popup cancels capture + opens web app in new tab.
43. ~~**Reader "Disregard" action**~~ — DONE: ⋯ menu gets "Disregard" (muted text, below divider). Calls `dismissArticle()` with reason `reader_disregard`, records interest signal, navigates back to feed.
44. ~~**Report bad scrape queue**~~ — DONE: ⋯ menu gets "Report bad scrape". Sends to `POST /report-scrape` → stored in `/opt/petrarca/data/scrape_reports.json`. `GET /scrape-reports` lists pending reports. Deduplicated by article_id.
45. ~~**Feed ingest metadata**~~ — DONE: Latest lens shows relative ingest time ("2h ago", "yesterday") + source label (Twitter, Readwise). Uses `ingested_at` ISO timestamp (new field) with fallback to `date`.
46. ~~**`ingested_at` timestamp**~~ — DONE: Both `import_url.py` and `build_articles.py` now write `ingested_at: datetime.now(UTC).isoformat()` on all new articles. Existing articles fall back to `date` (day-level precision only).

### Completed (Session 25: Unified Book Library + Kindle Include Fix + Instant Add Book)

56. ~~**Kindle Include button fix**~~ — DONE: Old flow called `POST /book/process-kindle` with `{ max: 1 }` which processed the first alphabetically matching book, not the clicked one. New `POST /kindle/include` endpoint takes `{ "key": "<asin>" }`, creates unified PhysicalBook immediately, converts highlights to captures, marks `added_to_petrarca: true`, starts research in background thread.
57. ~~**Server-side Kindle filtering**~~ — DONE: `GET /kindle/library?exclude_processed=true` filters already-included books server-side, reducing payload from 2,776 to just unprocessed books. Also returns `title_display` for resolved sideloaded titles.
58. ~~**Kindle curation screen renamed**~~ — DONE: "Kindle Library" → "Import from Kindle". Uses display titles, shows toast on include, removes book from list on success.
59. ~~**Unified Library**~~ — DONE: Library subtitle changed from "Physical books" to "Books & reading notes". `metadata_source` type includes `'kindle'`. Kindle-included books appear in Library alongside physical books.
60. ~~**Instant add-book from photo**~~ — DONE: Old flow blocked user 5-10s on "Identifying..." spinner with 3-step wizard (capture → identifying → confirm). New flow: photo → placeholder book created immediately (`processing_status: 'identifying'`) → navigate back to Library in ~100ms. Identification runs in background, updates book when done. Library shows spinner for identifying books.
61. ~~**Reactive book store**~~ — DONE: `onBookStoreChange()` listener system + `useBookStoreVersion()` React hook added to `book-store.ts`. All mutations call `notifyListeners()`. Library and book-detail screens auto-re-render when background processing updates a book.
62. ~~**Book detail voice recording**~~ — DONE: Voice capture with expo-av recording, stable local file copy, background upload with retry queue via AsyncStorage. Shows transcription status (processing/failed with retry button).

**Files changed**:
- `scripts/research-server.py` — new `POST /kindle/include` endpoint, `GET /kindle/library` supports `?exclude_processed=true` + `title_display`
- `app/app/kindle-curation.tsx` — calls `/kindle/include` per-book, filtered fetch, toast feedback, display titles
- `app/app/add-book.tsx` — instant return: placeholder → background identify → update
- `app/data/book-store.ts` — `onBookStoreChange()` listeners, `useBookStoreVersion()` hook, `notifyListeners()` on all mutations
- `app/data/types.ts` — `metadata_source: 'kindle'`, `processing_status: 'identifying' | 'ready'`
- `app/app/(tabs)/library.tsx` — reactive hook, spinner for identifying books, updated subtitle
- `app/app/book-detail.tsx` — reactive hook, voice recording with retry queue
- `app/lib/book-api.ts` — `includeKindleBook(key)` function

### Completed (Session 10)
37. ~~**Clipper auto-save countdown**~~ — DONE: Chrome clipper popup auto-saves after 10 seconds (fire-and-forget via Cmd+Shift+S). Signature double rule acts as countdown timer (rubric drains to gray). Typing in note field pauses countdown. Visible Cancel button + Esc. Gold completion flash (#c9a84c) on save. requestAnimationFrame for smooth 60fps timer.
38. ~~**Tweet URL ingestion via twikit**~~ — DONE: `/ingest` endpoint detects twitter.com/x.com URLs and routes through twikit instead of generic URL import. Fetches full tweet metadata, reconstructs threads (same-author reply chains), extracts + resolves t.co links. If tweet has URLs → ingests linked article with tweet context. If no URLs → uses tweet/thread text as article content. Falls back to normal import if twikit fails.
39. ~~**Auto-sync Twitter cookies**~~ — DONE: Chrome extension silently extracts `auth_token` + `ct0` cookies when user visits X.com and pushes to server via `POST /twitter/cookies`. Throttled to once per 4 hours. Eliminates manual SSH cookie refresh. New manifest permissions: `cookies` + `host_permissions` for x.com/twitter.com.
40. ~~**Cookie health endpoints**~~ — DONE: `GET /twitter/status` checks cookie validity + age. `POST /twitter/cookies` accepts `{auth_token, ct0}` for remote cookie refresh.

### Completed (Session 41: Review System Consolidation + Fractal Exploration)
63. ~~**Review tab rewrite — infinite river**~~ — DONE: Review now uses `knowledge_items` (253 items, 6 curricula) instead of `retrieval_questions` (19 Sicily-only). Cards/Voice sub-tabs. Infinite river with no session boundary. Skip button on every card. Simplified grading (knew/partly/missed) via `review_engine.record_answer()`.
64. ~~**Fractal exploration microlearning**~~ — DONE: Each review card gets 3 LLM-generated follow-up queries. Tap triggers Gemini + Search → stored as `microlearning_card` with content, assessment Q, and 3 new follow-ups. Interleaved every ~5 items. Text input for custom queries. New table: `microlearning_cards`. New endpoint: `POST /review/microlearning`.
65. ~~**Voice chapter recall prompts**~~ — DONE: Voice elicitation includes "What do you remember from Chapter X?" with high-priority candidate selection.
66. ~~**Legacy review code cleanup**~~ — DONE: `record_review_result()`, `get_review_status()`, `get_retrieval_questions()` removed. `retrieval_questions` and `review_schedule` tables archived. Scoring exclusively through `review_engine.record_answer()`.
67. ~~**Review interaction logging**~~ — DONE: 7 new event types for algorithm tuning: `review_card_shown`, `review_answer_revealed`, `review_result` (with `time_seconds`), `review_skip`, `review_entity_intro_continue`, `review_custom_query`, `review_research_triggered`.
68. ~~**Navigation cleanup**~~ — DONE: "Voice Recall" and "Hamarquizen" removed from drawer. "Hamarquizen" → "Book Review" in book-detail. Review badge navigates to Review tab.

### Gap Analysis: Built vs. Full Spec (updated end of session 8)

#### COMPLETED — Original Gaps Now Resolved

| # | Feature | Resolution |
|---|---------|-----------|
| G1 | Claim-level feedback UI | **Descoped** → behavioral inference via scroll-aware tracking + curated "What's new" card |
| G3 | Incremental embedding | **DONE** — only embeds new claims, prunes removed, `--force` for full rebuild |
| G4 | Related articles at reader bottom | **DONE** — 3 groups (same topic / shared concepts / same source) with "+ Queue" buttons |
| G5 | Reader "Up next" footer | **DONE** — footer bar with Done + next queued article title, `router.replace()` flow |
| G6 | Auto-ingest from links | **DONE** — tap link → POST `/ingest` → poll `/ingest-status` → inline badges |
| G7 | Activity Log tab | **DONE** — 4th tab, server aggregation via `/activity/feed`, offline log queue |
| G9 | Topic hierarchy feedback | **DONE** — hierarchical PostReadInterestCard, `recordTopicSignalAtLevel()`, entity scoring |
| G10 | Cross-article connections | **DONE** — inline "Also in: [title]" annotations + "✦ CONNECTED READING" bottom section |
| G12 | Novel section markers | **DONE** — 2px green left border on novel/mostly_novel paragraphs in Guided/New Only modes |
| G13 | Micro-delights (partial) | **DONE** — ✦ pull-to-refresh ornament, claim reveal stagger (80ms), completion flash. AnimatedHighlightWrap deferred. |

#### REMAINING GAPS

| # | Feature | Priority | Notes |
|---|---------|----------|-------|
| G2 | **LLM judge for ambiguous claims** | ~~Medium~~ | **DONE** — `judge_ambiguous_pairs()` in `build_knowledge_index.py`, verdicts in `knowledge_index.json`, client consults verdicts in 0.68–0.78 range. First run: 57% of 200 judged pairs reclassified (mostly EXTENDS→UNRELATED). |
| G8 | **Web split panel + keyboard shortcuts** | Medium | Desktop experience. Left pane article list + right pane reader, `j/k/d/x/q/Space/s` keys. |
| G11 | **Scrollbar novelty minimap** | Low | Colored dots on scrollbar showing novel content locations. |
| G14 | **Scrape report triage + pipeline hardening** | Low | Mostly resolved by session 14 fixes. 2 of 4 reports fixed (tweet normalization, paragraph merging). Remaining: `df64c81e` (Claude docs, JS-heavy) and `450e9396` (newsletter redirect URL). `clean_existing_articles.py` now serves as ongoing quality audit. |
| G13 | **AnimatedHighlightWrap** | Low | Amber long-press border animation. Deferred due to block rendering complexity. |
| G14 | **Entry row sidebar** | Low | 76px sidebar with large Cormorant numbers + depth dots. Design polish. |
| G15 | **Depth navigator** | Low | Summary / Claims / Sections / Full horizontal toggle in reader. |
| G16 | **Novelty badges** | Low | "Mostly new" / "72% new" / "Partly familiar" semantic badges. |
| G17 | **Dismissed articles archive** | Low | Archive view for swiped-left articles. |
| G18 | **Structured comparison** | Low | Elicit-style multi-article comparison matrix. |
| G19 | **Blindspot detection** | Low | Topics with many articles but few absorbed claims. |
| G20 | **Contradiction detection** | Deferred | Corpus too harmonious (86% compatible). |
| G21 | **Book reader** | Deferred | Section-based long-form reading. |
| G22 | **Nomic embeddings** | Low | Experiments preferred Nomic over Gemini embeddings. Works fine with Gemini. |

### User Feedback Summary (from voice notes, Mar 8)
- **Article `6e3cb28c19e1`** (NotebookLM learning compression): User wants to bookmark AND follow multiple topics (AI-assisted learning, learning strategies). Wants topic overview to surface recently-bookmarked articles prominently. Voice feedback should support actionable commands (add tags, research topics, express interest).
- **Article `0708161ff37b`**: 94-second voice note recorded but transcription was client-side (old code). Note may not have been stored server-side — check logs. This was the last interaction before the backend transcription refactor.

---

## Key Design Documents

| Document | Purpose |
|----------|---------|
| `research/system-state-of-the-art.md` | **START HERE** — Comprehensive reference covering all research, algorithms, data structures, experiments, UI mockups |
| `research/novelty-system-architecture.md` | Architecture design for the knowledge-aware system |
| `research/experiment-results-report.md` | Results from 11 validation experiments |
| `research/experiment-log.md` | Append-only chronological experiment log |
| `research/ux-redesign-spec.md` | 2 rounds of mockup feedback, approved interaction models |
| `design/DESIGN_GUIDE.md` | The Annotated Folio design system specification |
| `research/knowledge-diff-interfaces.md` | HCI research on adaptive presentation (dimming, stretchtext) |
| `research/knowledge-tracing-for-reading.md` | FSRS/BKT adaptation for reading knowledge |
| `research/knowledge-deduplication.md` | Embedding + dedup architecture |
| `research/topic-normalization-spec.md` | Topic normalization & defragmentation spec — registry design, LLM merge-or-create, defrag algorithm, Otak lessons |
| `research/user-guide.md` | User-facing guide (markdown source) — also at `app/public/guide/index.html` (HTML) |

## Key Scripts

| Script | Purpose |
|--------|---------|
| `scripts/gemini_llm.py` | Shared Gemini LLM wrapper (google.genai SDK). `call_llm()`, `call_chat()`, `call_with_search()`, `call_llm_tool()`. Model: `gemini-3.1-flash-lite-preview` |
| `scripts/build_articles.py --claims` | Extract atomic claims, entities, and follow-up questions (Gemini 3.1 Flash-Lite, 10 parallel workers) |
| `scripts/build_articles.py --claims-only` | Extract claims/entities/questions for articles that don't have them yet |
| `scripts/build_articles.py --enrich` | Backfill entities + follow-up questions for existing articles (10 parallel workers) |
| `scripts/build_claim_embeddings.py` | Generate Gemini embeddings for all claims (batch 100) |
| `scripts/build_knowledge_index.py` | Build knowledge_index.json from embeddings (parallel delta reports) |
| `scripts/build_knowledge_index.py --skip-delta` | Build without LLM delta reports (faster) |
| `scripts/llm_audit.py` | View LLM usage/cost audit. `--days 7`, `--since 2026-03-01`, `--json` |
| `scripts/log_server.py` | Interaction log collector (port 8091, systemd `petrarca-log`) |
| `scripts/deploy_knowledge_index.sh` | Deploy to nginx + update manifest |
| `scripts/content-refresh.sh` | Full cron pipeline (fetch → extract → claims → embed → index → deploy) |
| `scripts/topic_normalizer.py` | Topic normalization + defragmentation. Normalize, defrag, enforce limits |
| `scripts/topic_registry.json` | Canonical topic registry — 25 broad, 172 specific topics with include/exclude descriptions. Auto-updated by normalizer, consolidated by defrag |
| `scripts/experiment_*.py` | 11 experiment scripts (see experiment-results-report.md) |

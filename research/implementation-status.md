# Petrarca: Current System State

**Last rewritten**: April 4, 2026 (session 45)
**For session-by-session history**: see `research/session-changelog.md`

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│ CLIENT (Expo SDK 54, React Native)                          │
│ native: exp://alifstian.duckdns.org:8082                    │
│ web:    http://alifstian.duckdns.org:8084                   │
│                                                             │
│ 2 tabs: Feed | Library                                      │
│ ✦ drawer: Syntheses, Voice Notes, Queue, Knowledge Map,     │
│           Projects, Review, Book Review                     │
│                                                             │
│ State: module-level vars in store.ts → AsyncStorage          │
│ Sync:  content-sync.ts (manifest hash comparison + ?since=)  │
│ Lazy:  article-content.ts (in-memory + disk cache)           │
└────────────────┬────────────────────────────────────────────┘
                 │ HTTP
┌────────────────▼────────────────────────────────────────────┐
│ HETZNER VM                                                   │
│                                                             │
│ nginx :8083 — static content (JSON fallback)                 │
│ nginx :8084 — web app (static dist/)                         │
│ research-server.py :8090 — API + LLM orchestration           │
│ log_server.py :8091 — interaction log collection             │
│                                                             │
│ petrarca.db (SQLite, WAL) — canonical data store             │
│ /opt/petrarca/data/ — JSON fallback + cache files            │
│   voice_elicit_cache/ — idempotent retry cache (24h TTL)     │
│ /opt/petrarca/.env — GEMINI_KEY, ANTHROPIC_KEY               │
│                                                             │
│ Cron: /etc/cron.d/petrarca-refresh (every 4 hours)           │
│   → content-refresh.sh                                       │
│     → fetch_twitter_bookmarks.py                             │
│     → fetch_readwise_reader.py                               │
│     → build_articles.py (Gemini extraction)                  │
│     → build_claim_embeddings.py (MiniLM via amygdala)        │
│     → build_knowledge_index.py (similarities + delta)        │
│     → build_concept_clusters.py                              │
│     → generate_syntheses.py                                  │
│     → build_curriculum_embeddings.py                         │
└─────────────────────────────────────────────────────────────┘
```

## Content Numbers (as of Apr 4, 2026)

~261 articles, ~4,764 claims, 20 clusters, 27 syntheses, 9,392 article similarity pairs, 9 curricula (719 nodes), 299 key_facts (Sicily Greek).

## App Screens

### Tab Screens
| Screen | File | Role |
|--------|------|------|
| Feed | `(tabs)/index.tsx` | ContinueBar + SynthesisScroll + ArticleRow list. Web: sidebar layout. Mobile: filter pills. |
| Library | `(tabs)/library.tsx` | Unified books (physical+Kindle). Filter tabs: Reading/All/Finished/Kindle. Swipe-to-archive. |
| Review | `(tabs)/review.tsx` | 3-tab: Cards / Voice / Explore. Multi-quiz ML cards (3-5 quizzes, independently FSRS-scheduled). Enriched content with sections, primary sources, tappable dates+entities. Knowledge Explorer with timeline/persons/places. |
| Topics | `(tabs)/topics.tsx` | Synthesis-led view, accessible via ✦ drawer |
| Queue | `(tabs)/queue.tsx` | Reading queue |
| Log | `(tabs)/log.tsx` | Activity timeline |

### Stack Screens
| Screen | File | Role |
|--------|------|------|
| Reader | `reader.tsx` | Article reader — Full/Guided/New Only modes, paragraph dimming, briefing card |
| Synthesis Reader | `synthesis-reader.tsx` | 3-column "Restrained Folio" reader |
| Book Detail | `book-detail.tsx` | Book metadata, captures (photo/voice/text), curriculum context, chapter review, "Record what I remember" book-level recall |
| Add Book | `add-book.tsx` | Camera capture → Gemini identification |
| Knowledge Map | `knowledge-map.tsx` | Tree view of curricula with knowledge dots |
| Curriculum Scan | `curriculum-scan.tsx` | v2 card-based self-assessment (3-level) |
| Hamarquizen | `hamarquizen.tsx` | Book-specific PRIME→READ→TEST review |
| Voice Elicitation | `voice-elicitation.tsx` | Free recall voice prompts for curriculum nodes + chapter/book recall. "Know nothing" vs "Skip" buttons. Auto-loads more prompts when batch exhausted. Fire-and-forget uploads with `request_id` caching. |
| Voice Notes | `voice-notes.tsx` | Voice note list + playback |
| Kindle Curation | `kindle-curation.tsx` | Triage screen for Kindle library |
| Projects | `projects.tsx` | Project list |
| Project Detail | `project-detail.tsx` | Project notes + voice routing |
| Review Session | `review-session.tsx` | Legacy review (may be unused) |
| Resurfacing | `resurfacing.tsx` | Cross-book resurfacing prompts |
| Landscape | `landscape.tsx` | Knowledge landscape visualization |
| Trails | `trails.tsx` | Learning trails |
| Map | `map.tsx` | Geographic/concept map |

### Key Components
| Component | Role |
|-----------|------|
| `ContinueBar` | Dark ink bar for in-progress article at feed top |
| `SynthesisScroll` | Horizontal synthesis cards with margin numbers |
| `ArticleRow` | Tabular article row with novelty badge + swipe gestures |
| `FeedSidebar` | Web: sticky sidebar with topic/source filters |
| `FeedFilterPills` | Mobile: topic + source filter pills |
| `ArticlePopover` | Web: hover popover for article links |
| `MarkdownLink` | Cross-platform link handling (web `<a>`, native `onPress`) |
| `PetrarcaDrawer` | ✦ navigation drawer (must be added per tab screen) |
| `FeedbackCapture` | Global ✦ feedback button (voice + text + screenshot) |
| `VoiceUploadToast` | Global toast for background voice upload success/failure |
| `BookCurriculumContext` | Book-detail curriculum coverage section |
| `ChapterContext` | Chapter preview/review with temporal hooks |
| `EntitySheet` | Entity detail bottom sheet — backlinks, notes, "3 questions", "Research this", "View in timeline" |
| `KnowledgeExplorer` | Reusable 3-tab explorer: Timeline (century groups, era bands) / Persons (450) / Places (384) |
| `ExplorerCapture` | Voice/text entity note capture |
| `VoiceUploadToast` | Global toast for background voice upload success/failure |
| `SynthesisChat` | Inline chat modal for synthesis |

### Client Data Layer
| Module | Role |
|--------|------|
| `store.ts` | Feed ranking, filtering, state management. Module-level vars → AsyncStorage. |
| `content-sync.ts` | Incremental sync from server. Manifest hash comparison, `?since=` for articles. |
| `article-content.ts` | Lazy article content loading. In-memory + disk cache. Prefetch for offline. |
| `knowledge-engine.ts` | FSRS decay, claim classification, paragraph dimming, curiosity scoring |
| `book-store.ts` | Book + capture persistence. Reactive listeners (`onBookStoreChange`). |
| `interest-model.ts` | Topic-level interest tracking with Bayesian smoothing, 30-day decay |
| `queue.ts` | Reading queue with AsyncStorage persistence + content prefetch |
| `logger.ts` | Interaction event logging (`logEvent()`) — daily JSONL files |
| `voice-upload-service.ts` | Background retry of pending voice elicitation uploads on app foreground. 48h expiry. |
| `upload-queue.ts` | Persistent background upload queue for book page photos with exponential backoff |
| `voice-upload-service.ts` | Background retry of pending voice elicitation uploads on app foreground. 48h expiry. Idempotent via request_id. |
| `types.ts` | `ArticleMeta`, `ArticleContent`, `Article`, `TopicSynthesis`, etc. |

## Server: Key Modules

### Core Infrastructure
| Script | Role |
|--------|------|
| `research-server.py` | HTTP server (:8090) — all API endpoints, LLM orchestration |
| `db.py` | SQLite schema + sync helpers (`sync_articles`, `sync_knowledge_index`, etc.) |
| `gemini_llm.py` | `call_llm()`, `call_chat()`, `call_with_search()`, `call_vision()`, `call_llm_tool()`. Default: gemini-3.1-flash-lite-preview |
| `claude_llm.py` | Claude wrapper for review_engine calls (migrated from Gemini in session 42) |
| `review_engine.py` | FSRS scheduling, `record_answer()`, `generate_question()`, `get_candidates()` |
| `curriculum_db.py` | **Runtime reads/writes** — `load_curriculum()`, `update_knowledge()`, `load_knowledge_states()` |
| `curriculum.py` | Curriculum generation + graph utilities only (NOT for runtime data) |
| `log_server.py` | Interaction log collection (:8091) |

### Pipeline (runs via cron every 4h)
| Script | Role |
|--------|------|
| `content-refresh.sh` | Orchestrator — runs all pipeline steps in sequence |
| `fetch_twitter_bookmarks.py` | Fetch bookmarks via twikit |
| `fetch_readwise_reader.py` | Fetch from Readwise Reader API |
| `build_articles.py` | Gemini Flash extraction → summary, claims, topics, entities, questions |
| `build_claim_embeddings.py` | MiniLM 384d embeddings via limbic.amygdala |
| `build_knowledge_index.py` | Claim similarities, article similarities, paragraph mappings, delta reports |
| `build_concept_clusters.py` | Graph-based spectral bisection clustering |
| `generate_syntheses.py` | Monolithic synthesis per cluster (server version) |
| `build_curriculum_embeddings.py` | Embed curriculum nodes, map article claims → nodes (0.65 threshold) |
| `extract_entity_concepts.py` | Entity concept extraction for articles |

### Books & Kindle
| Script | Role |
|--------|------|
| `process_kindle_books.py` | Kindle → unified book conversion |
| `kindle_sync.py` | Kindle library sync from Mac SQLite DB |
| `book_research_agent.py` | Autonomous book research via Gemini+Search |
| `resurfacing_engine.py` | Cross-book resurfacing prompts |
| `extract_key_facts.py` | Key facts extraction from curriculum nodes |

### Experiments & Utilities
| Script | Role |
|--------|------|
| `experiment_*.py` (13 files) | Algorithm experiments (NLI, clustering, dedup, decay, etc.) |
| `synthesis_pipeline.py` | Multi-stage synthesis (local only, not on server) |
| `import_url.py` | Manual URL ingestion |
| `export_content_json.py` | Manual JSON export (removed from pipeline cron) |
| `verify_migration.py` | Deep semantic comparison for SQLite migration |

## API Endpoints (research-server.py :8090)

### Content API (`/api/*`)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/articles` | All article metadata (ArticleMeta). `?since=` for incremental. |
| GET | `/api/article/:id` | Full article content (ArticleContent) |
| GET | `/api/knowledge-index` | Claim similarities, paragraph mappings |
| GET | `/api/clusters` | Concept clusters |
| GET | `/api/syntheses` | All syntheses |
| GET | `/api/manifest` | Content hashes for incremental sync |

### Ingestion
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/ingest` | Chrome clipper / manual URL ingestion |
| POST | `/ingest-youtube` | YouTube transcript ingestion |
| POST | `/ingest-email` | Email-to-article ingestion |
| POST | `/ingest-book` | Book ingestion |
| POST | `/ingest-note` | Reader note ingestion |
| POST | `/ingest-cancel` | Cancel pending ingestion |
| GET | `/ingest-status` | Ingestion progress |

### Review & Knowledge
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/curriculum/review/generate` | Generate review question for a knowledge item |
| POST | `/curriculum/review/result` | Record review answer (FSRS update) |
| POST | `/review/microlearning` | Generate microlearning card from research query |
| POST | `/review/microlearning/dismiss` | Dismiss card or individual quiz (card_id and/or quiz_id) |
| POST | `/review/batch-generate` | Batch generate questions for knowledge items |
| POST | `/review/follow-up/trigger` | Trigger microlearning from follow-up query |
| POST | `/review/follow-up/generate` | Generate sideways follow-up queries via Haiku |
| GET | `/review/queue` | Review queue candidates |
| GET | `/review/stats` | Review statistics |
| POST | `/review/voice-elicit` | Voice free-recall elicitation (transcription + LLM). Supports curriculum nodes, `chapter:{id}:{num}`, and `book:{id}` node types. Auto-detects domain_id for book/chapter. Idempotent via `request_id`. |
| POST | `/review/voice-memo` | Voice memo for review item |
| GET | `/review/elicit-candidates` | Voice elicitation candidates (curriculum nodes + chapter recalls) |
| POST | `/review/elicit-know-nothing` | Record that user knows nothing about a topic (sets knowledge=unknown, confidence=0.8). Auto-detects domain for book/chapter node_ids. |

### Entity
| POST | `/entity/tap` | Log entity tap, generate entity intro |
| POST | `/entity/questions` | Generate entity questions |
| POST | `/entity/research` | Entity research via Gemini+Search |
| POST | `/entity/notes` | Save user note about an entity |
| POST | `/explore/capture` | Voice/text capture routed to entities + research |
| GET | `/entities` | List all entities |
| GET | `/entity/:id` | Entity detail (includes user notes) |

### Books
| POST | `/book/identify` | Gemini Vision book identification |
| POST | `/book/ocr-toc` | OCR table of contents |
| POST | `/book/ocr-page` | OCR page photo |
| POST | `/book/upload-photo` | Upload book photo |
| POST | `/book/photo-results` | Get photo OCR results |
| POST | `/book/voice-note` | Upload voice note |
| POST | `/book/research` | Trigger book research |
| POST | `/book/chapter-insights` | Chapter insights generation |
| POST | `/book/story-so-far` | Story So Far briefing |
| GET/POST | `/book/sync` | Book + capture sync |
| POST | `/book/resurfacing/*` | Generate/respond/skip resurfacing prompts |
| GET | `/book/resurfacing/status` | Resurfacing status |

### Kindle
| POST | `/kindle/sync` | Sync Kindle library data |
| POST | `/kindle/include` | Include specific book from Kindle |
| POST | `/kindle/curate` | Curate Kindle library |
| POST | `/kindle/classify` | Classify Kindle books |
| POST | `/kindle/resolve-titles` | Resolve Kindle titles |
| GET | `/kindle/library` | Kindle library (filterable) |
| GET | `/kindle/recently-started` | Recently started Kindle books |
| GET | `/kindle/highlights` | Kindle highlights |

### Curriculum
| POST | `/curriculum/generate` | Generate new curriculum |
| POST | `/curriculum/map-book` | Map book to curriculum |
| POST | `/curriculum/elicit/start` | Start knowledge elicitation |
| GET | `/curriculum/list` | List all curricula |
| GET | `/curriculum/graph-data` | Graph data for D3 visualization |
| GET | `/curriculum/graph` | Force-directed graph HTML |
| GET | `/curriculum/timeline` | Timeline visualization HTML |
| GET | `/curriculum/entity-index` | Entity index |
| GET | `/curriculum/book-context/:id` | Book-curriculum context |
| GET | `/curriculum/:domain` | Curriculum detail with knowledge annotations |
| GET | `/curriculum/:domain/coverage` | Curriculum coverage stats |

### Other
| POST | `/chat` | Research chat |
| POST | `/research/topic` | Topic research |
| POST | `/research/explore` | Exploration research |
| POST | `/research/explore-batch` | Batch exploration |
| POST | `/feedback` | User feedback |
| POST | `/projects` | Create project |
| POST | `/projects/note` | Add project note |
| GET | `/projects` | List projects |
| GET | `/health` | Health check |

## SQLite Schema (petrarca.db)

31 tables organized into 5 areas:

**Content pipeline**: `articles`, `article_sections`, `atomic_claims`, `claim_similarities`, `nli_verdicts`, `article_similarities`, `article_novelty_matrix`, `paragraph_claim_map`, `article_curriculum_nodes`, `delta_reports`, `concept_clusters`, `near_duplicates`, `syntheses`, `pipeline_meta`, `cluster_meta`

**Books & Kindle**: `physical_books`, `book_captures`, `book_curriculum_mappings`

**Curriculum & Knowledge**: `curriculum_domains`, `curriculum_nodes`, `curriculum_prerequisites`, `knowledge_states`, `knowledge_items`, `timeline_entries`, `shared_entities`, `entity_curriculum_links`

**Review & Microlearning**: `review_items`, `microlearning_cards`, `microlearning_quizzes`

**Other**: `projects`, `project_notes`, `voice_transcripts`

**Key relationships**: `atomic_claims` uses composite PK `(article_id, id)` (one claim ID in multiple articles). `knowledge_items` is the review data source (replaces archived `retrieval_questions`). `microlearning_quizzes` holds individual quiz questions from ML cards, each independently FSRS-scheduled — the ML card is a content container, quizzes are the review atoms. ML cards have `triggered_follow_ups` and `title` columns. Voice uploads use `request_id` for idempotent retry caching. `curriculum_db.py` reads from SQLite; `curriculum.py` reads from JSON.

## Algorithm Parameters (experiment-validated)

### Claim Similarity
- **KNOWN**: ≥ 0.82 cosine (MiniLM 384d)
- **EXTENDS**: ≥ 0.74
- **NLI cascade**: 0.74–0.82 zone, 59% accurate (consider disabling)
- **FORGOTTEN**: retrievability R < 0.3

### Article Similarity
- Weighted 0.5×summary + 0.5×claims via `find_similar_documents()`
- Calibrated on 18 human + 300 LLM-rated pairs: AUROC=0.930, 94% accuracy, ρ=0.818
- **Briefing card**: 0.52, **Feed ranking**: 0.49, **Dedup**: 0.64
- Ground truth: `scripts/ground-truth/`, config: `threshold_config.json`

### Quiz Dedup
- MiniLM 384d cosine via limbic, threshold ≥ 0.82 (same as claim KNOWN)
- Checked against all existing `microlearning_quizzes` + curriculum `key_facts`
- Similarity scores logged: `journalctl -u petrarca-research | grep quiz-dedup`
- Calibration review scheduled ~2026-04-18

### Curriculum Mapping
- Article claim → curriculum node: ≥ 0.65 cosine (broader than claim-claim)
- Active book feed boost: +0.15

### Knowledge Decay (FSRS)
- Stability: skim=9d, read=30d, highlight=60d, reinforcement=2.5×
- Used for curriculum review scheduling (NOT for article novelty — that's binary seen/unseen)

### Feed Scoring
- Curiosity peak: 70% novelty, Gaussian σ=0.15
- Synthesis coverage: ≥80% → hide from feed, ≥50% → demote

### Pipeline
- Extraction model: gemini-3.1-flash-lite-preview (5% factual claim rate)
- Curriculum generation: Opus only (Gemini Flash quality rejected)

### Reader
- 3 modes: Full / Guided / New Only
- Familiar paragraph opacity: 0.55

## Deployment

### Commands
```bash
# Mobile + server (the ONLY correct deploy):
git add . && git commit && git push origin main
bash ~/src/expo/scripts/deploy.sh petrarca

# Web (optional, for cache busting):
bash app/deploy-web.sh

# Native rebuild (only for new native modules):
cd app && eas build --profile development --platform ios
```

### Infrastructure
- SSH: `ssh alif`
- nginx :8083 (content JSON), :8084 (web app static)
- research-server.py :8090 (API)
- log_server.py :8091 (interaction logs)
- Cron: `/etc/cron.d/petrarca-refresh` (every 4 hours)
- DuckDNS: `/etc/cron.d/duckdns` (every 30 min)
- Config: `~/src/expo/config.json` (ports, services, paths)
- Server env: `/opt/petrarca/.env` (GEMINI_KEY, ANTHROPIC_KEY)
- limbic: `/opt/limbic` (rsynced by deploy.sh, editable-installed in venv)

## Known Issues & Gaps

1. **Screens possibly unused**: `review-session.tsx`, `resurfacing.tsx`, `landscape.tsx`, `trails.tsx`, `map.tsx` — may be stubs or superseded
2. **synthesis_pipeline.py** not deployed to server — still uses monolithic `generate_syntheses.py`
3. **NLI cascade** (59% accurate) — may be adding noise rather than signal
4. **knowledge-engine.ts** still has full FSRS code — intended to simplify to binary seen/unseen for articles
5. **No centralized error boundaries** in React Native
6. **Podcast sync** built but needs Overcast auth (deferred)
7. **466 curriculum nodes** with no knowledge_items — need discovery probes
8. **Key_facts only extracted for Sicily Greek** — remaining 8 curricula + 6 Sicily areas pending

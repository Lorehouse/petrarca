# Petrarca — Intelligent Read-Later App

A mobile-first read-later app combining incremental reading, user knowledge modeling, and algorithmic article selection. Named after Francesco Petrarca, pioneer of systematic reading methods. Built for one power user (Stian), not a social platform.

**Frontend**: Expo SDK 54 (React Native), 2-tab layout (Feed / Library) + ✦ drawer. **Backend**: Hetzner VM — nginx (:8083 content, :8084 web), research-server.py (:8090), 4-hour cron pipeline. **Data**: SQLite (petrarca.db, canonical), JSON fallback.

## Design Principles & North Star

These principles are the intellectual foundation of the project. They override implementation convenience. Read the linked docs when making design decisions beyond bug fixes.

1. **"Hooks, not facts."** Reading success = building frameworks (Caesar, Alexander, Charlemagne), not fact-drilling. The system builds scaffold knowledge that makes everything you read richer. *(research/design-vision.md)*

2. **"I'll manage your memory."** The fear of forgetting stops reading nonfiction. Like Michel Thomas: the system takes responsibility for retention so the user can focus on reading. Frame knowledge maps as positive progress, never anxiety-inducing gaps. *(memory/feedback_michel_thomas.md)*

3. **Comprehension before memory.** Ensure understanding before testing (Matuschak's key finding). SRS-style flashcards fail for conceptual knowledge — we need elaborative retrieval, connection-based resurfacing, spreading activation. *(research/andy-matuschak-research.md, research/beyond-flashcards-knowledge-retention.md)*

4. **Atomic claims are the fundamental unit.** Not articles, not words. Claims enable cross-article tracking, knowledge state management, and novelty detection. Delta-only reports show what's new since last read. *(research/novelty-system-architecture.md)*

5. **Curriculum as bridge.** Don't match claims directly across sources. Curriculum nodes (50-80 per domain, Opus-generated) are the organizing principle — they connect books, articles, and review into a coherent structure. *(research/overlapping-curricula-vision.md)*

6. **Temporal hooks are the key retention mechanism.** Priority: (1) anchor to known events, (2) same-moment connections, (3) causal chains, (4) cross-domain surprises only if the reader knows the other domain. *(memory/feedback_temporal_hooks.md)*

7. **Facts first, then concepts.** Dates, key figures, key events are load-bearing scaffolding. Generate factual questions DETERMINISTICALLY from structured `key_facts` data. Only use LLM for rich answers and analytical questions. Never delegate to LLM what can be computed from structure. *(memory/feedback_rules.md § Knowledge System Design)*

8. **Books encode, system maintains.** Books provide initial encoding through narrative/structure. Maintaining and integrating knowledge is the system's job. Not SRS — but real decay exists. Voice dumps as knowledge elicitation. *(memory/feedback_knowledge_encoding.md)*

9. **Curiosity zone at 70% novelty.** Articles with ~70% novel claims + ~30% familiar context are most engaging (zone of proximal development). "Most novel" ≠ "most interesting." *(research/experiment-results-report.md)*

10. **Dim familiar, don't hide.** Familiar paragraphs at 0.55 opacity, not hidden. Constrained highlighting (150 words) improves comprehension 11-19% over highlighting everything (CHI 2024). *(research/knowledge-diff-interfaces.md)*

**Flag design drift proactively.** If implementation diverges from these principles, raise it before the user discovers it.

## Where to Look

| Working on... | Read first |
|--------------|-----------|
| **Any feature work** | `research/implementation-status.md` (architecture, screens, scripts, endpoints, algorithms) |
| **UI changes** | `design/DESIGN_GUIDE.md` — MUST READ. "The Annotated Folio" Renaissance visual language. |
| **Review/retention** | `research/review-system-architecture.md`, `research/reading-companion-process-design.md` |
| **Curriculum/entities** | `research/overlapping-curricula-vision.md`, `research/entity-profiles-design.md` |
| **Synthesis** | `research/synthesis-pipeline-design.md`, `memory/feedback_synthesis_design.md` |
| **Books** | `research/book-companion-handoff.md`, `research/book-companion-experiments.md` |
| **Feed/ranking** | `research/novelty-system-architecture.md` |
| **Deep "why"** | `research/design-vision.md` (master synthesis of all interviews + research) |
| **Research index** | `research/README.md` (50+ docs, tiered reading guide) |
| **Past sessions** | `research/session-changelog.md` |

## Working on This Codebase

This project is exploratory — 45+ sessions in many directions. That means:

1. **There is stale code.** Dead imports, unused tables, deprecated modules. Don't assume everything exists for a reason. Verify before building on it.
2. **Trace data flows before changing them.** Where does it write → what store → who reads → what displays? Critical bugs came from write/read mismatches (JSON vs SQLite).
3. **Test endpoints before telling user to test.** `curl` with realistic data after server changes. Deploy mobile after client changes. "It should work" is not verification.
4. **Clean up what you touch.** Remove dead code, unused imports, stale data when you encounter them.
5. **Diagnose before patching.** Read the full error, check concurrency, understand architecture. One correct fix beats four incremental attempts.

## Critical Rules

### Data Store Discipline
- **SQLite is the ONLY data store** for knowledge states, review items, and all runtime data
- **`curriculum_db.py`** for ALL runtime reads/writes. **`curriculum.py`** is ONLY for generation/CLI.
- **Knowledge levels only upgrade**: unknown → mentioned → engaged → anchored. Never downgrade.
- **Server-first**: All data lives on server. Local storage is cache only.

### Deploy
- **Commit + push first**, then `bash ~/src/expo/scripts/deploy.sh petrarca`
- **After ANY `app/` change**: deploy mobile immediately
- **Web**: `bash app/deploy-web.sh` (optional, for cache busting)
- **NEVER**: rsync to server, `git clean` on server, skip `deploy.sh`
- See `memory/feedback_rules.md` for full deploy details and anti-patterns

### Interaction Logging
- ALL user interactions via `logEvent()` from `app/data/logger.ts`
- Every screen MUST call `setFeedbackContext()` on focus/mount
- New screens: add `setFeedbackContext({ screen: 'screen-name' })` in `useFocusEffect` or `useEffect`

### Pipeline Testing
- Use `scripts/pipeline-tests/run.py` when iterating on prompts/models/extraction
- Always run relevant fixtures before AND after changes

### Research Organization
- ALL research in `research/`, linked from `research/README.md`
- `research/experiment-log.md` is **append-only** — new entries at top, log BEFORE making changes

### Code Conventions
- Branch prefix: `sh/` for all GitHub branches
- No test plans or checklists in PR descriptions
- Component files under ~300 lines. Extract reusable UI into `app/components/`.
- **React Native Web links**: Use `MarkdownLink` component. Never `<Text onPress href>` (RNW blocks it).
- **KeyboardAvoidingView**: Required for bottom-sheet Modals with TextInput on iOS.
- **✦ Drawer**: Must be explicitly added to each tab screen (import `PetrarcaDrawer`).
- **No `as any`** — add proper types instead.
- **limbic.amygdala**: `pip install -e ~/src/limbic`. Server: `/opt/limbic`. Used for embeddings, similarity, clustering.

### Curriculum Generation
- **Opus only** — Gemini Flash curricula have meaningless titles
- Generate locally via `claude -p`, parse JSON, run through `curriculum.py` node builder

## User Preferences
- Prefers Claude Code agents (Max plan) over Anthropic API calls
- Rapid prototyping in small chunks, research depth before building
- Broad interests: history, classical philology, educational research, green party policy, AI
- Languages: Norwegian, Swedish, Danish, Italian, German, Spanish, French, Chinese, Indonesian, Esperanto, English

## Voice Processing
- **Soniox API**: Key in `/Users/stian/src/alignment/.env`, base: `https://api.soniox.com/v1`
- Patterns: `../alif/backend/app/services/soniox_service.py`

## Reference Projects
- **../alif**: Arabic learning app — Expo mobile, FSRS, `claude -p` wrapper
- **../otak**: Twitter bookmarks, Readwise, LLM providers (knowledge graph is a failed experiment)
- **../bookifier**: Pipeline/caching patterns

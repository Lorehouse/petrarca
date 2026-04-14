# Petrarca v2: Structural Review Redesign

**Status**: Proposal (Session 71, 2026-04-14)
**Scope**: Complete rearchitecture of the app around quiz-first review with structural card types
**Supersedes**: Previous feed-centric design, article-based reading companion

## Executive Summary

Petrarca pivots from a read-later app with review features to a **quiz-first knowledge retention app** with voice input. The read-later/feed/article pipeline is disabled. The app launches directly into review. All interactions happen inside the native app (no standalone HTML pages). The review system is rebuilt around **structural review cards** that test relational knowledge (temporal sequences, geographic contemporaries, causal chains) rather than isolated facts — inspired by how Alif captures multiple learning signals from a single sentence interaction.

## Design Principles (unchanged, but re-prioritized)

The 11 principles from CLAUDE.md remain. This redesign operationalizes them more directly:

1. **"Hooks, not facts"** → Structural cards ARE the hooks. A synchronic card showing "The World in 1066" IS the cross-domain connection.
2. **"I'll manage your memory"** → Per-aspect scheduling makes the system's memory management visible: "3/4 known. 'What year?' due Thursday."
3. **Comprehension before memory** → Context cards provide encoding before quick quizzes test retention.
4. **Atomic claims are the unit** → Each aspect of a fact (who/what/when/where) becomes an independently scheduled atom.
5. **Temporal hooks are THE key mechanism** → Sequence cards and synchronic cards make temporal structure a first-class card type, not just decoration.
6. **Facts first, then concepts** → Quick quizzes build the factual scaffold; structural cards build the relational framework.
7. **Dim familiar, don't hide** → On structural cards, known positions are shown (dimmed anchors), not hidden.

## What's Disabled

The following subsystems are **preserved in code but disabled** in the app. Future sessions should not build on or maintain them without explicit request:

| Subsystem | Code Location | Reason |
|-----------|--------------|--------|
| **Feed tab** | `app/(tabs)/index.tsx` | Read-later not adding value; app opens to Review |
| **Article ingestion pipeline** | `scripts/build_articles.py`, `scripts/import_url.py` | No feed to populate |
| **Twitter bookmark fetch** | `scripts/fetch_twitter_bookmarks.py` | Content source disabled |
| **Readwise sync** | `scripts/fetch_readwise_reader.py` | Content source disabled |
| **Email ingestion** | `research-server.py _handle_ingest_email()` | Content source disabled |
| **Kindle sync launchd** | `scripts/com.petrarca.kindle-sync.plist` | Book progress not critical; books remain manually addable |
| **Amazon scraper** | `scripts/amazon_library_scraper.py` | Metadata enrichment not needed |
| **Podcast sync** | `scripts/podcast_sync.py` | Not integrated into review |
| **Synthesis reader** | `app/app/synthesis-reader.tsx` | Depends on article pipeline |
| **Article reader** | `app/app/reader.tsx` | Depends on article pipeline |
| **Reading trails** | `app/app/trails.tsx` | Depends on article pipeline |
| **Landscape view** | `app/app/landscape.tsx` | Article visualization |
| **Queue tab** | `app/(tabs)/queue.tsx` | Article queue |
| **Topics tab** | `app/(tabs)/topics.tsx` | Article topics |
| **Standalone HTML visualizations** | `scripts/knowledge_atlas.html`, `knowledge_growth.html`, etc. | Moving all viz into native app |

### What's Preserved and Active

| Subsystem | Why |
|-----------|-----|
| **Review system** | Core of the app |
| **Voice elicitation + capture** | Primary input mechanism, growing in importance |
| **Physical books + curriculum mapping** | Books remain a key knowledge source |
| **Curriculum generation** | Foundation of the knowledge graph |
| **Entity system + Wikidata resolution** | Enables cross-domain connections (just deployed in Session 70) |
| **Microlearning cards** | Research follow-ups from voice/review |
| **FSRS scheduling** | Retention algorithm (to be tuned) |
| **Interaction logging** | Essential for analytics and algorithm tuning |

## App Architecture

### Navigation: Review-First (modeled on Alif)

**Current**: 3 tabs (Feed, Review, Library) + drawer with 15+ items

**Proposed**: 4 tabs, review is the landing screen

```
Tabs (bottom bar):
  1. Review (landing)     — Card stream + voice quick-access
  2. Voice                — Voice elicitation + capture
  3. Stats                — Detailed analytics (native, not HTML)
  4. More                 — Library, settings, knowledge explorer, admin
```

**Rationale**: Alif's 6-tab layout works well on mobile. But Petrarca's core loop is tighter: review cards and voice input. Stats deserves its own tab (not a buried drawer link) because the user wants detailed analytics visible. "More" absorbs the remaining functionality (library, books, knowledge explorer, map, settings).

**Key change**: The app opens to the Review tab. No feed, no articles, no curation. You open Petrarca to review knowledge and capture voice input.

### Voice Access

Voice input should be frictionless from the review screen:

- **Floating mic button** on the Review tab (like a FAB) for quick voice capture
- **Dedicated Voice tab** for structured elicitation sessions (curriculum-guided recall)
- **Post-podcast capture**: "I just heard something" quick capture mode on Voice tab — transcribe, entity-match, generate knowledge items, prioritize in review stream

Voice captures that mention entities from active curricula should be **prioritized in the review stream** over older book-sourced items. The user's words: "I really want to be able to remember what I just heard in the podcast about Emma of England forever, that takes priority to rehearsing some facts about Caesar from a book I read a year ago."

### Review Priority Model

Current priority: SR cards first (book-sourced highest), gap-fill penalized, ML interleaved.

**Proposed priority** (within a session):

```
1. Voice-sourced items from last 48 hours (highest — fresh encoding window)
2. Structural cards with multiple due positions (efficient — many signals per card)
3. Due quick quizzes for aspects recently missed (targeted remediation)
4. Regular FSRS-due knowledge_items (maintenance)
5. Microlearning follow-ups (enrichment)
6. Discovery cards (new curriculum nodes)
```

**Freshness decay**: Voice-sourced items get a priority boost that decays over 7 days: `boost = max(0, 5.0 * (1 - days_since_capture / 7))`. After 7 days, they're scheduled like everything else.

## Structural Review Cards

### The Core Insight

From Alif: one Arabic sentence assesses 5-15 words simultaneously. The sentence provides encoding context; per-word marking provides granular FSRS signals. The analog for history: one **structural frame** (timeline, world-snapshot, cast-of-characters) assesses multiple knowledge positions simultaneously.

All structural cards follow the same pattern:
1. Present a **meaningful frame** (timeline, map, network, comparison)
2. Some positions are **filled** (anchors — known facts providing context)
3. Some positions are **blank** (tests — facts to recall)
4. User reveals blanks one at a time, marks **knew/missed** (binary, not ternary)
5. Missed positions get **targeted mnemonics** (aspect-specific, not generic)
6. Filled positions generate **collateral exposure** signal (tracked, weighted 0.3x)
7. **Blanks rotate** each appearance based on FSRS state

### Card Type 1: Aspect Card (multi-signal per topic)

**Tests**: Multiple facts about a single topic (who/what/when/where/why)
**When shown**: First encounter with topic, or multiple aspects due simultaneously
**Time**: 20-30 seconds for 3-5 FSRS signals

```
┌─────────────────────────────────────────┐
│ Pompey's Pirate Campaign                │
│ roman_republic · 1st century BC         │
│                                         │
│ What do you remember?                   │
│                                         │
│  ○ Who led it?          [Reveal]        │
│  ○ What year?           [Reveal]        │
│  ○ How long?            [Reveal]        │
│  ○ What authority?      [Reveal]        │
└─────────────────────────────────────────┘

After revealing:

│  ✓ Who led it?     → Pompey       [Knew]  │
│  ✗ What year?      → 67 BC        [Missed] │
│  ✓ How long?       → ~3 months    [Knew]  │
│  ✓ What authority? → Lex Gabinia  [Knew]  │
│                                            │
│ ─── Focusing on: the date ─────────────── │
│ ⋆ 67 BC — 6 years after Spartacus         │
│   (73 BC), 6 years before Caesar crosses   │
│   the Rubicon (49 BC).                     │
│                                            │
│ 3/4 known · "What year?" due Thursday     │
│                          [Continue →]      │
```

**Key behaviors**:
- User does mental free recall BEFORE revealing (preserves elaborative retrieval benefit)
- Each aspect gets independent FSRS scheduling
- Only missed aspects auto-expand rich mnemonic
- Known aspects stay collapsed (no time wasted)
- Trust line at bottom shows per-aspect scheduling
- "Partly" grade eliminated — replaced by per-aspect binary signals

**Aspect-specific mnemonics** (each aspect type gets a different mnemonic strategy):

| Aspect Type | Mnemonic Strategy |
|---|---|
| Date | Temporal hooks: contemporaneous events, decades before/after known anchors |
| Person | Relational web: allies, enemies, contemporaries, role in narrative |
| Event | Causal narrative: what led to it, what changed, consequences |
| Place | Geographic anchoring: what else happened there, relative to known places |
| Duration | Comparison: vs similar campaigns/periods, why surprisingly fast/slow |

### Card Type 2: Sequence Card (temporal ordering)

**Tests**: Chronological ordering within a bounded period
**When shown**: Scaffold building, or when multiple positions in a sequence are due
**Time**: 30-40 seconds for 3-6 FSRS signals

```
┌─────────────────────────────────────────┐
│ Syracuse: The Tyrants                    │
│ 485 BC ──────────────────────── 212 BC   │
│                                          │
│  485 ── Gelon defeats Carthage at Himera │
│                                          │
│  ???  Who seized power after civil war?  │
│                              [Reveal]    │
│                                          │
│  310 ── Agathocles invades North Africa  │
│                                          │
│  ???  Who allied with Rome vs Carthage?  │
│                              [Reveal]    │
│                                          │
│  212 ── Romans besiege Syracuse;         │
│         Archimedes killed                │
└─────────────────────────────────────────┘
```

**Bounding units** (natural sequence boundaries):

| Type | Examples | Typical Size |
|---|---|---|
| Person's career | Caesar, Pompey, Roger II, Justinian | 5-8 life events |
| Dynasty/succession | Syracuse tyrants, Norman kings, Julio-Claudians | 4-7 rulers |
| Period arc | Islamic Sicily, Greek Classical Age, Late Republic | 5-10 events |
| Campaign/conflict | Punic Wars, Caesar's civil war | 4-6 stages |

**Rotating blanks**: Each appearance of a sequence card blanks DIFFERENT positions based on FSRS state. Positions that are well-known become anchors; weak positions become blanks. The card is never identical twice.

**Scale annotations**: Show temporal proportions — "273 years, longer than the USA has existed", "80 years between Gelon and Dionysius I". These encode the SCALE of history, not just the ordering.

**Generation**: Sequences are generated from existing key_facts + entity date ranges within a curriculum domain. LLM selects the 5-8 most important milestones and generates cross-domain hooks.

### Card Type 3: Synchronic Card (geographic contemporaries)

**Tests**: Cross-domain awareness — what was happening elsewhere at the same time
**When shown**: After a temporal anchor is well-established, to build cross-domain connections
**Time**: 25-35 seconds for 3-5 FSRS signals

```
┌─────────────────────────────────────────┐
│ The World in 1066                        │
│ When William conquers England            │
│                                          │
│  England     William the Conqueror       │
│  Sicily      ???                [Reveal] │
│  Papacy      ???                [Reveal] │
│  Byzantium   Constantine X               │
│  HRE         Henry IV                    │
│  Caliphate   al-Qa'im (Baghdad)          │
└─────────────────────────────────────────┘
```

**Presentation**: Schematic geographic layout (scannable text list with region labels), not a map. Maps are too slow for quiz interaction. The existing map view becomes a "See on map" reference link.

**Anchor selection**: Prefer facts the user KNOWS as anchors. If you know Basil II well but not Henry IV, Basil II is an anchor and Henry IV is a blank.

**Cross-domain hooks auto-emerge**: "Norman brothers conquering both ends of Europe simultaneously" — the frame makes the connection obvious without needing to state it explicitly.

**Generation**: For any anchor year/event, query all entities of type ruler/major_figure whose date range spans that year, grouped by domain. LLM selects the most interesting 5-7 regional snapshots.

**Wikidata integration**: The recently deployed Wikidata entity resolution (89.3% QID coverage) enables rich cross-domain queries. Entity date ranges and external IDs make synchronic card generation more reliable.

### Card Type 4: Cast Card (people and roles)

**Tests**: Person-role associations around a pivotal event
**When shown**: When an event has multiple associated entities, some due for review
**Time**: 20-30 seconds for 3-5 FSRS signals

```
┌─────────────────────────────────────────┐
│ The Ides of March, 44 BC                 │
│                                          │
│  Dictator:         Julius Caesar         │
│  Led conspiracy:   ???          [Reveal] │
│  "Et tu":          ???          [Reveal] │
│  Funeral eulogy:   Mark Antony           │
│  Named heir:       ???          [Reveal] │
└─────────────────────────────────────────┘
```

**Generation**: From key_facts where multiple entities are mentioned in the same event. The entity_curriculum_links table already maps entities to nodes with `lens_title` (how the entity is framed in context).

### Card Type 5: Causal Chain Card

**Tests**: Mechanism linking cause to consequence
**When shown**: When both cause and effect are known but the link between them is weak
**Time**: 20-30 seconds for 2-4 FSRS signals

```
┌─────────────────────────────────────────┐
│ How Rome Got Pompey's Pirate Command     │
│                                          │
│  Pirates disrupt grain → Rome starves    │
│           ↓                              │
│  ???  (What law was passed?)    [Reveal] │
│           ↓                              │
│  Pompey given unprecedented command      │
│           ↓                              │
│  ???  (What was the outcome?)   [Reveal] │
│           ↓                              │
│  Senate fears Pompey's growing power     │
└─────────────────────────────────────────┘
```

### Card Type 6: Quick Quiz (single-signal, fast)

**Tests**: One specific aspect, position, or relationship
**When shown**: Individual aspects due for review (the most common card type as knowledge matures)
**Time**: 5-8 seconds for 1 FSRS signal

```
┌─────────────────────────────────────────┐
│ 🕐 Date                                 │
│                                         │
│ What year did Pompey clear the          │
│ Mediterranean pirates?                  │
│                                         │
│ [Reveal]                                │
│  → 67 BC              [Knew ✓] [Missed] │
│                                         │
│ ← Gelon · Dionysius · [Pompey] · Caesar│
│                     [See full topic ↗]  │
└─────────────────────────────────────────┘
```

**Mini-context bar**: At the bottom, a mini-sequence or mini-aspect bar shows where this fact fits in its structure. The fact is never floating in isolation.

**Binary grading**: Knew or Missed. No "partly" — the question is specific enough that you either know the answer or you don't.

**Variants for different structural dimensions**:
- Position quiz: "Who ruled Syracuse between Agathocles and the Roman siege?"
- Order quiz: "Did Agathocles rule before or after Hiero II?"
- Gap quiz: "Roughly how long between Gelon and the Roman siege?"
- Simultaneous quiz: "Who was ruling Syracuse when Alexander conquered Persia?"
- Person-role quiz: "Who gave the funeral eulogy after Caesar's assassination?"
- Causal quiz: "What law gave Pompey his pirate command?"

### Session Composition

**A typical 10-card session** (2.5-3 minutes):

```
1. [Quick Quiz]      "What year...?"                    — 6s
2. [Quick Quiz]      "Who ruled after...?"               — 6s
3. [Sequence Card]   "Caesar's Career" — 2 gaps          — 35s
4. [Quick Quiz]      "What was the...?"                  — 6s
5. [Quick Quiz]      "Before or after...?"               — 6s
6. [Aspect Card]     "Fall of Constantinople" — 4 aspects — 28s
7. [Quick Quiz]      "Who invaded Sicily in 827?"        — 6s
8. [Quick Quiz]      "When did Roger II...?"             — 6s
9. [Synchronic Card] "The World in 1066" — 3 blanks      — 30s
10. [Quick Quiz]     "What came between...?"             — 6s
```

**Session rhythm**: fast-fast-**MEDIUM**-fast-fast-**MEDIUM**-fast-fast-**MEDIUM**-fast. Structural cards are the peaks (satisfying, story-like); quick quizzes are the steady beat (efficient, precise).

**Natural progression**: As knowledge matures, sessions shift from 30% structural / 70% quiz to 10% structural / 90% quiz. Sessions get faster and cover more ground.

**Signal density**: ~14 FSRS signals from 10 cards in 2.5 minutes. Current system: ~10 imprecise signals from 10 rich cards in 5 minutes. 2.8x improvement in signal-per-minute.

## Scheduling & Analytics

### FSRS Tuning

**Immediate changes**:
- Raise `maximum_interval` from 365 to 3650 (10 years). Items you truly know should not cycle annually.
- Keep `desired_retention=0.80` for now. Calibrate from actual data later (like Alif's optimizer).
- "Partly" grade removed for structural/aspect cards (binary knew/missed per position).
- "Partly" retained temporarily for legacy knowledge_item cards during transition.

**Future**: Build an FSRS optimizer script (like Alif's `optimize_fsrs.py`) that runs on the interaction_log to calibrate parameters from real data.

### Collateral Exposure Tracking

When a fact appears as an ANCHOR (filled position) on a structural card:

| Interaction | FSRS Treatment | Weight |
|---|---|---|
| Blank → Knew | Full Easy review | 1.0× |
| Blank → Missed | Full Again review | 1.0× |
| Shown as anchor | Collateral exposure | 0.3× |
| Not shown | Nothing | 0× |

The 0.3× collateral exposure: log the exposure, extend `due_at` by ~15-20% of current interval, but don't count as a full review. This lets well-known facts that keep appearing as anchors drift to very long intervals naturally.

**Exposure log** (new table):
```sql
CREATE TABLE exposure_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_id TEXT NOT NULL,
    card_type TEXT NOT NULL,          -- sequence/synchronic/aspect/cast/causal/quick_quiz
    card_id TEXT NOT NULL,
    exposure_type TEXT NOT NULL,       -- blank_knew/blank_missed/anchor/collateral
    position_in_card INTEGER,
    time_on_card_ms INTEGER,
    session_id TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
```

### Implicit Review Credit (FIRe-inspired)

From Math Academy's Fractional Implicit Repetition: reviewing an advanced topic implicitly reviews prerequisites. When a user correctly places Dionysius I in the Syracuse sequence, this implicitly reviews:
- The fact that Dionysius I existed (entity knowledge)
- His approximate date range (temporal knowledge)
- His association with Syracuse (geographic knowledge)

**Implementation**: Build an encompassing graph from curriculum_prerequisites + entity_curriculum_links. When a structural card position is answered correctly, give 0.2× implicit credit to encompassed facts. Track in exposure_log with `exposure_type='implicit'`.

### Anchor Calibration

Facts used as anchors must themselves be verified periodically:
- Prefer facts with retention probability > 0.8 as anchors
- 1 in 5 appearances: blank an anchor as a "verification check"
- If an anchor's retention drops below 0.7: promote it to a blank on next card
- Track anchor effectiveness: does showing Basil II as anchor improve recall of Constantine X?

### Dependency Tracking (new table)

```sql
CREATE TABLE fact_dependencies (
    fact_a_id TEXT NOT NULL,
    fact_b_id TEXT NOT NULL,
    dependency_type TEXT NOT NULL,
    -- temporal_adjacent: A before B in same sequence
    -- synchronic: A and B are contemporaneous
    -- causal: A causes/enables B
    -- role_in_event: A and B are roles in same event
    -- encompassing: knowing A implicitly exercises B
    strength REAL DEFAULT 0.5,        -- measured from data over time
    last_measured TEXT,
    PRIMARY KEY (fact_a_id, fact_b_id, dependency_type)
);
```

### Leech Detection

Adapted from Alif's leech system. Items with 3+ reviews still at < 3d stability are flagged:
- Sliding window: last 8 reviews
- If accuracy < 50%: suspend, graduated cooldown (3/7/14 days)
- On reintroduction: targeted mnemonic regenerated
- Currently stuck items in production: Dionysius I (5 reviews, 0.9d), Roger II (4 reviews, 1.0d), Pre-Socratics (3 reviews, 1.5d), First Triumvirate (3 reviews, 1.2d)

## In-App Statistics Screen

All analytics move from standalone HTML pages to a native React Native stats screen (tab 3). Modeled on Alif's stats.tsx but adapted for Petrarca's knowledge model.

### Stats Sections

**Today Hero**:
- Cards reviewed today, signal count, time spent
- Knowledge transitions today (unknown→mentioned, mentioned→engaged, etc.)
- Voice captures today

**Knowledge Overview** (per domain):
- Horizontal stacked bars: unknown / mentioned / engaged / anchored
- Node coverage % and edge overlap % (Goldsmith C metric)
- Tap domain → domain detail with per-node breakdown

**Review Performance** (rolling 7d / 30d):
- Grade distribution across card types (knew/missed per aspect, position, quick quiz)
- Average signals per session, average session time
- Accuracy by card type (structural vs quick quiz vs legacy)

**Scheduling Health**:
- Stability distribution: how many items at 1d / 7d / 30d / 90d / 365d+
- Overdue count and trend
- Leech count and list

**Retention Trend** (14-day chart):
- Daily review count + accuracy overlay
- Custom React Native bar chart (no D3, no web view)

**Voice Activity**:
- Captures this week, entities resolved, knowledge items created
- Elicitation coverage: % of curriculum nodes with voice recall data

**Structural Card Coverage**:
- Sequences generated vs possible
- Synchronic cards generated vs possible anchor events
- Aspect decomposition coverage (% of knowledge_items with aspect cards)

## Voice Pipeline Enhancement

### Current State (Session 70)
- Voice elicitation works: record → Soniox transcribe → Claude analyze → create knowledge_items
- Voice capture works: freeform → entity match → domain routing → Gemini analysis → knowledge updates
- Wikidata entity resolution deployed (89.3% QID coverage)
- Domain routing via Gemini Flash for novel entities
- Transcript dedup via SHA-256

### Enhancements for v2

**Priority boost for fresh voice captures**: Items from voice captures in the last 48 hours get highest review priority. The encoding window after hearing something (podcast, conversation, lecture) is when spaced repetition is most valuable.

**Automatic structural card generation from voice**: When a voice capture mentions multiple events in sequence ("First X happened, then Y, then Z"), the system should detect this and generate a sequence card. When a capture mentions multiple contemporaneous rulers/events, generate a synchronic card.

**Reprocess existing transcripts**: 135+ voice transcripts exist. Many were processed before domain routing and Wikidata resolution were deployed. Reprocessing through the updated pipeline would generate more and better knowledge items. (The Rollo transcript is the specific test case — processed through audit but never through the full knowledge item creation pipeline.)

**Voice as primary input**: The app should make it easy to capture knowledge from any source (podcast, audiobook, conversation, lecture, reading) via voice. The review system then reinforces what was captured. This is the "books encode, system maintains" principle applied to all knowledge sources.

## Data Architecture Changes

### New Tables

```sql
-- Structural card definitions
CREATE TABLE structural_cards (
    id TEXT PRIMARY KEY,
    card_type TEXT NOT NULL,          -- sequence/synchronic/cast/causal/transformation
    title TEXT NOT NULL,
    description TEXT,
    domain_id TEXT,                    -- primary domain (nullable for cross-domain)
    date_anchor INTEGER,              -- year for synchronic cards
    date_start INTEGER,               -- range for sequences
    date_end INTEGER,
    milestones TEXT NOT NULL,          -- JSON array of {position, fact_id, entity_id, text, date, is_generated}
    hooks TEXT,                        -- JSON array of cross-domain/scale annotations
    generation_source TEXT,            -- auto/manual/voice
    stability_days REAL DEFAULT 7.0,  -- FSRS for the structural card itself
    due_at INTEGER,
    review_count INTEGER DEFAULT 0,
    fsrs_card_json TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Per-position scheduling within structural cards
CREATE TABLE structural_positions (
    id TEXT PRIMARY KEY,
    card_id TEXT NOT NULL REFERENCES structural_cards(id),
    position INTEGER NOT NULL,
    fact_id TEXT,                      -- links to key_facts or entity facts
    entity_id TEXT,                    -- links to shared_entities
    question_text TEXT NOT NULL,       -- "Who seized power after civil war?"
    answer_text TEXT NOT NULL,         -- "Dionysius I (405 BC)"
    mnemonic TEXT,                     -- aspect-specific rich mnemonic
    mnemonic_type TEXT,                -- temporal/relational/causal/geographic/comparison
    stability_days REAL DEFAULT 1.0,
    due_at INTEGER,
    last_reviewed_at INTEGER,
    last_score TEXT,
    review_count INTEGER DEFAULT 0,
    exposure_count INTEGER DEFAULT 0, -- times shown as anchor
    fsrs_card_json TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE (card_id, position)
);

-- Exposure log (all interactions, including collateral)
CREATE TABLE exposure_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_id TEXT NOT NULL,
    card_type TEXT NOT NULL,
    card_id TEXT NOT NULL,
    exposure_type TEXT NOT NULL,       -- blank_knew/blank_missed/anchor/implicit
    position_in_card INTEGER,
    time_on_card_ms INTEGER,
    session_id TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Fact dependencies (relational knowledge graph)
CREATE TABLE fact_dependencies (
    fact_a_id TEXT NOT NULL,
    fact_b_id TEXT NOT NULL,
    dependency_type TEXT NOT NULL,
    strength REAL DEFAULT 0.5,
    evidence_count INTEGER DEFAULT 0,
    last_measured TEXT,
    PRIMARY KEY (fact_a_id, fact_b_id, dependency_type)
);

-- Sequence definitions (bounding units)
CREATE TABLE sequences (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    sequence_type TEXT NOT NULL,       -- person/dynasty/period/campaign
    domain_id TEXT,
    entity_id TEXT,                    -- for person/dynasty sequences
    date_start INTEGER,
    date_end INTEGER,
    milestone_count INTEGER,
    generation_status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT (datetime('now'))
);
```

### Migration from Current Schema

The existing tables remain. New tables are additive. The migration path:

1. **knowledge_items** → continue as-is for legacy cards; new aspect cards stored in structural_positions
2. **microlearning_quizzes** → existing multicue quizzes become quick_quiz cards; migrate fact_id linkage
3. **key_facts** (JSON on curriculum_nodes) → source data for generating structural_positions
4. **shared_entities** + **entity_curriculum_links** → source data for synchronic/cast card generation
5. **Wikidata QIDs** → enable cross-domain entity queries for synchronic cards

## Implementation Sequence

### Phase 0: Foundation (this session + next)
- [ ] Write this design document (done)
- [ ] Update CLAUDE.md with disabled features
- [ ] Reprocess Rollo transcript through full pipeline (validate voice→knowledge flow)
- [ ] Consider reprocessing all voice transcripts through updated pipeline
- [ ] Merge Wikidata entity resolution work (PR #2 + backfill)

### Phase 1: Review-First App Shell (Session 72 — done)
- [x] Restructure navigation: 4 tabs (Review, Voice, Stats, More)
- [x] App opens to Review tab
- [x] Move Library to More tab
- [x] Disable Feed tab (hide, don't delete)
- [x] Add floating mic button on Review tab
- [ ] Disable launchd jobs for Twitter/Kindle/Amazon sync

### Phase 2: Aspect Cards
- [ ] Implement aspect decomposition for key_facts (structured generation prompt)
- [ ] Batch generate aspects for all 265 knowledge_items with key_facts
- [ ] Build AspectCard component in review.tsx
- [ ] Per-aspect FSRS scheduling in structural_positions table
- [ ] Aspect-specific mnemonic generation (different strategy per type)
- [ ] Integrate into review stream (replace current knowledge_item cards)
- [ ] Remove "partly" grade for aspect cards (binary knew/missed)
- [ ] Trust line: "3/4 known. 'What year?' due Thursday"

### Phase 3: Quick Quiz Cards
- [ ] Build QuickQuizCard component (fast, binary, mini-context bar)
- [ ] Migrate existing microlearning_quizzes to quick quiz format
- [ ] Generate quick quiz variants (position, order, gap, simultaneous, role, causal)
- [ ] Integrate into review stream as primary card type
- [ ] Session composition logic: mix structural + quick quiz cards

### Phase 4: Sequence Cards
- [ ] Define sequence boundaries per domain (LLM-assisted)
- [ ] Milestone selection from key_facts + entity dates
- [ ] Build SequenceCard component with rotating blanks
- [ ] Scale annotations (temporal proportion, duration comparisons)
- [ ] Cross-domain hooks on sequence milestones
- [ ] FSRS scheduling per position + per sequence card
- [ ] Integrate into review stream

### Phase 5: Synchronic Cards
- [ ] Cross-domain entity query (using Wikidata date ranges)
- [ ] Anchor year selection from significant events
- [ ] Build SynchronicCard component (schematic geographic layout)
- [ ] Anchor selection based on user knowledge state
- [ ] Cross-domain hook generation
- [ ] Integrate into review stream

### Phase 6: Additional Card Types
- [ ] Cast cards (people + roles around events)
- [ ] Causal chain cards
- [ ] Transformation cards (before/after)

### Phase 7: Analytics & Scheduling
- [ ] Build native Stats screen (React Native, no D3)
- [ ] Exposure log table + tracking
- [ ] Collateral exposure credit (0.3× FSRS weight)
- [ ] Implicit review credit (FIRe-inspired encompassing graph)
- [ ] Dependency tracking between facts
- [ ] Leech detection + graduated suspension
- [ ] Raise maximum_interval to 3650
- [ ] Anchor calibration (verification checks, effectiveness tracking)
- [ ] FSRS optimizer script (calibrate from interaction_log)

### Phase 8: Voice Enhancements
- [ ] Priority boost for fresh voice captures
- [ ] Auto-detect sequences in voice transcripts → generate sequence cards
- [ ] Auto-detect contemporaneous mentions → generate synchronic cards
- [ ] Batch reprocess historical transcripts through updated pipeline
- [ ] Voice capture from Review tab (floating mic → quick capture)

## Experiments & Hypotheses

Things we want to test empirically. Each experiment should be run as early as possible. Log results in `research/experiment-log.md`.

### E1: Aspect decomposition quality (Phase 2, BLOCKING)
**Hypothesis**: Structured, type-driven aspect generation (required slots per fact type) produces more reliable and comprehensive cues than freeform "generate 2-4 cues."
**Test**: Generate aspects for 20 knowledge_items using both prompts. Human-rate coverage (did it generate all meaningful aspects?) and quality (are questions unambiguous?). Use pipeline-eval fixtures.
**Blocks**: All aspect card work. If generation quality is poor, the whole card type needs redesign.

### E2: Binary grading vs ternary (Phase 2)
**Hypothesis**: Per-aspect binary (knew/missed) produces more accurate FSRS scheduling than single-card ternary (knew/partly/missed).
**Test**: Run both systems in parallel for 2 weeks. Compare: (a) prediction accuracy of FSRS (did items come back when predicted?), (b) user-reported satisfaction, (c) signal-per-minute rate. Need enough data (~200 reviews per system).
**Measurement**: Log both grades in interaction_log. Compare retention curves.

### E3: Collateral exposure actually helps (Phase 4+)
**Hypothesis**: Facts seen as anchors on structural cards are recalled better on their next active test than facts not recently seen.
**Test**: Compare retention of facts that appeared as anchors in the last 7 days vs facts that weren't shown. Control for FSRS-predicted retention. Need exposure_log data.
**Weight calibration**: Start at 0.3×, measure actual effect, adjust.

### E4: Structural cards vs plain quizzes for sequence knowledge (Phase 4)
**Hypothesis**: Seeing events in a timeline context (sequence card) produces better temporal ordering recall than isolated date quizzes.
**Test**: For the first 4 weeks, alternate: some sequences taught via sequence cards, others via individual quick quizzes only. Compare ordering accuracy on a delayed test.

### E5: Synchronic cards create cross-domain connections (Phase 5)
**Hypothesis**: Users who see synchronic cards ("World in 1066") will spontaneously recall cross-domain facts more often in voice elicitations.
**Test**: Before synchronic cards: baseline voice elicitation for cross-domain mentions. After 2 weeks: re-measure. Look for mentions of figures from OTHER domains when eliciting about a single domain.

### E6: Session rhythm affects engagement (Phase 3)
**Hypothesis**: Alternating structural (30s) and quick (6s) cards is more engaging than uniform card types.
**Test**: Track session completion rate and session length. Compare sessions with 2-3 structural cards vs all-quick-quiz sessions.

### E7: Voice priority boost improves fresh-capture retention (Phase 8)
**Hypothesis**: Reviewing voice-captured facts within 48 hours produces significantly better 30-day retention than reviewing them on normal FSRS schedule.
**Test**: A/B: some voice captures get priority boost, others enter normal queue. Compare 30-day retention.

### E8: Mnemonic type effectiveness by aspect type (Phase 2)
**Hypothesis**: Temporal mnemonics (anchored to contemporaneous events) work better for date aspects than generic rich_answers. Relational mnemonics work better for person aspects.
**Test**: Generate both generic and type-specific mnemonics. A/B assign to different facts. Compare retention after 3 reviews.

### Metrics to Track From Day 1

These should be logged for ALL interactions regardless of what phase we're in:

```
Per interaction:
- card_type, card_id, session_id, timestamp
- per_position: fact_id, result (knew/missed), was_anchor (bool), reveal_time_ms
- total_time_on_card_ms
- session_position (1st card, 5th card, etc.)

Per session:
- total_cards, total_signals, total_time_ms
- structural_card_count, quick_quiz_count
- completion (finished vs abandoned, at what card)
- accuracy_by_card_type

Per day:
- sessions_count, total_signals, total_time
- knowledge_transitions (level changes)
- voice_captures_count, items_generated
```

## Decisions Needing User Input

These are marked **INPUT NEEDED** — the implementation can proceed with reasonable defaults, but user preference would improve the design:

1. **INPUT NEEDED: Aspect card reveal flow** — Should aspects auto-reveal after tapping (instant feedback), or require a separate "check" tap (forces commitment before seeing answer)? Default: require tap-to-reveal, then tap knew/missed.

2. **INPUT NEEDED: How many blanks per sequence card?** 2-3 feels right for a 5-milestone sequence, but should we start aggressive (4 blanks) or conservative (2 blanks) and adapt? Default: start with 2, increase as user accuracy improves.

3. **INPUT NEEDED: Synchronic card domain selection** — Show all domains you're studying, or limit to 5-6 most active? Some domains (Western Philosophy, Classical Reception) have very few entities. Default: top 5 by review activity + any domain with a directly relevant entity.

4. **INPUT NEEDED: Transition timeline** — How fast to phase out legacy knowledge_item cards? Immediate (risk: jarring), gradual over 2 weeks (mix old and new), or keep both indefinitely? Default: 2-week transition, decreasing legacy card ratio.

5. **INPUT NEEDED: Stats screen priority** — Should Stats be a tab (always visible) or a More sub-screen? It takes a tab slot but the user said "very detailed statistics screen." Default: tab.

## Open Questions

1. **Sequence boundary curation**: Should sequence boundaries be manually curated (higher quality) or auto-generated from curriculum structure (scalable)? Probably start manual (one-time LLM-assisted generation per domain), then automate.

2. **How many structural cards per session?** The proposal says 2-3 per 10-card session. Needs testing — too many structural cards slow sessions; too few reduce learning richness.

3. **Synchronic card domain breadth**: How many domains should a synchronic card span? All active curricula? Only ones the user is studying? Need to balance breadth (interesting connections) vs relevance (user knows enough to care).

4. **Transition from legacy cards**: How to handle the 265 existing knowledge_items? Migrate all to aspect cards? Keep legacy cards alongside new types? Probably: batch-generate aspects for all, then phase out legacy card display over 2-3 weeks.

5. **Collateral exposure weight**: The proposed 0.3× is a guess. Need to calibrate from data — does seeing a fact as an anchor actually improve retention? If so, by how much?

6. **Quick quiz question quality**: The current multicue generation is freeform LLM ("generate 2-4 cues"). The proposed system needs structured, type-driven generation. How reliable is this? Need to test with pipeline-eval fixtures.

7. **Cross-domain Wikidata queries for synchronic cards**: Performance? The backfill gave 509/570 entities QIDs. For synchronic queries, we need date ranges on entities — how complete is this data? Need to audit entity date coverage.

## Research References

### From Petrarca Research Corpus
- `research/design-vision.md` — Master "why" document
- `research/beyond-flashcards-knowledge-retention.md` — Why SRS fails for conceptual knowledge; elaborative retrieval; gist vs verbatim traces
- `research/andy-matuschak-research.md` — Comprehension before memory; dynamic practice
- `research/review-system-architecture.md` — Node-centric review, multi-source
- `research/reading-companion-process-design.md` — Temporal hooks, three interaction moments
- `research/knowledge-diff-interfaces.md` — Dim familiar don't hide; constrained highlighting
- `research/experiment-results-report.md` — 70% novelty sweet spot

### From Alif
- `../alif/docs/scheduling-system.md` — FSRS tuning, session composition, acquisition→graduation
- `../alif/docs/review-modes.md` — Sentence-based multi-signal assessment
- `../alif/research/learning-algorithm-redesign-2026-02-12.md` — Literature review, cognitive science
- `../alif/backend/scripts/optimize_fsrs.py` — FSRS parameter calibration from data
- `../alif/backend/scripts/replay_fsrs.py` — Scheduler change validation

### External Research (from web search)
- **FIRe (Math Academy)**: Fractional Implicit Repetition for hierarchical knowledge — encompassing graph, discounted implicit credit
- **Q-Matrix / DINA models**: Multi-signal cognitive diagnostic models — one assessment, multiple knowledge components
- **SAK with Pathfinder**: Structural Assessment of Knowledge — network metrics predict expertise
- **Semantic Network Analysis (PMC 2024)**: Clustering coefficient, path length, modularity distinguish experts
- **Contextual Diversity (Nature 2020)**: More diverse contexts > more frequency for retention
- **Incidental Vocabulary Meta-analysis (Cambridge)**: Incidental learning from 2+ exposures; spacing helps deliberate more than incidental
- **Chrono / Timeline board game**: Relative ordering as game mechanic
- **Chronas**: Cross-domain historical atlas (50M+ data points)

### Cognitive Science Principles Applied
- **Karpicke & Blunt (2011)**: Free recall > cued recall > recognition for relational processing
- **Fuzzy-Trace Theory**: Gist traces (frameworks) more durable than verbatim traces (specific facts)
- **Transfer-Appropriate Processing**: Retrieval context should match encoding context
- **Interleaving Effect** (Rohrer & Taylor 2007): 43% better performance from interleaved practice
- **Elaborative Encoding**: Connecting new fact to known facts makes it dramatically more durable
- **Zone of Proximal Development**: 70% novelty is the sweet spot

# Entity Context System — Design Spec

*2026-03-30. Addresses the "Where is Akragas?" problem.*

## Problem

Review cards reference entities (places, people, events, dates) that the learner may not know. A card asking "What happened to Akragas in 406 BC?" assumes you know what Akragas is, where it is, and why it matters. Currently there's no way to:

1. Learn what an entity IS during review
2. Signal that you don't know a referenced entity
3. Explore an entity further (map, Wikipedia, AI-generated context)
4. Ensure prerequisites are met before showing dependent cards

## Design: Hybrid Reactive + Proactive

Inspired by Alif's word-tap system, which combines proactive introduction (ReintroCards before sentences) with reactive signaling (tap words during sentences to mark missed/confused). Applied to knowledge entities:

### Layer 1 — Tappable Entities in Review Cards (Reactive)

After reveal, entity names in `rich_answer`, `memory_hook`, and `anchors` text are tappable. Tapping opens an **Entity Sheet** (bottom sheet or inline expansion).

#### Entity Sheet Contents

- **Name** + modern name if different ("Akragas · modern Agrigento")
- **Type badge**: Place / Person / Event / Period
- **Brief description**: 1-2 sentences (from `shared_entities` or generated)
- **Dates**: lifespan or date range
- **Mini-map** (places only): Small static or interactive map showing location. Could be a WebView with Leaflet, or a static image initially.
- **Your knowledge**: Current knowledge state for this entity (unknown / encountered / anchored) — shows whether you've been assessed on this
- **Related curriculum nodes**: Which nodes reference this entity, with knowledge dots
- **Links**: Wikipedia article link, related books in library

#### Implicit Scheduling: Tap = Interest Signal

**Any tap on an entity auto-schedules a follow-up review item.** This is not an explicit action — it's implicit, like Alif tracking `times_seen` on every word lookup. If you tapped Akragas, you'll get a question about Akragas in a future session.

Implementation:
- On entity tap, log `entity_tapped` event with entity_id, context (which review card), timestamp
- Server-side: if no review item exists for the entity's primary curriculum node, create one with `stability_days=3` (short initial interval — you just showed interest)
- If a review item already exists, don't change its schedule (the tap is passive, not a review signal)
- This means browsing entity sheets during review naturally populates your future review queue with the things you were curious about

#### Explicit Entity Sheet Actions

Three additional actions available on the entity sheet:

1. **"I don't know this"** (red) — Marks entity as unknown in knowledge model. Creates or prioritizes a review item for the underlying curriculum node with `stability_days=1` (high urgency). Next session will include an entity intro card.

2. **"Interesting — tell me more"** (gold) — Queues 3 AI-generated exploration prompts for the entity specifically (not the parent node). Uses the existing `createExplorationItems` pattern but scoped to the entity. Prompts vary by entity type:
   - Place: "Why was Akragas founded where it was?", "How does Akragas compare to Syracuse?", "What's left of Akragas today?"
   - Person: "What shaped Plato's visit to Syracuse?", "How did Plato's Sicilian experience change his philosophy?"
   - Event: "What were the long-term consequences?", "What parallels exist in other civilizations?"

3. **"Got it"** (green, or just dismiss) — Confirms familiarity, marks entity as "encountered" if previously unknown. No scheduling change.

#### Entity Detection

Two approaches, can be combined:

**Simple (v1):** Server annotates entity spans when generating the review session. The `rich_answer` field becomes annotated text with entity references:
```json
{
  "rich_answer": "Carthage sacked and destroyed Akragas...",
  "entity_spans": [
    {"start": 0, "end": 8, "entity_id": "carthage", "type": "place"},
    {"start": 33, "end": 40, "entity_id": "akragas", "type": "place"}
  ]
}
```

Server does simple string matching against the entity dictionary when building the review session response. No NER needed — just exact match against `shared_entities.name` + aliases.

**Rich (v2):** LLM annotates entities during question generation, identifying which entities in the answer a learner might not know and flagging prerequisite relationships.

### Layer 2 — Entity Intro Cards (Proactive)

Before showing a review question that references entities the learner hasn't been exposed to, the session inserts a lightweight **Entity Intro Card**.

#### When to Insert

During session building (`resurfacing_engine.py` review generation or `review_engine.py` queue building):

1. For each question in the session, extract referenced entities
2. Check knowledge state for each entity's curriculum node
3. If state is "unknown" or absent → insert an Entity Intro Card before the question

#### Entity Intro Card Format

Lighter than a full review card — not a quiz, just exposure:

```
┌─────────────────────────────────┐
│  📍 PLACE                       │
│                                 │
│  Akragas                        │
│  Modern: Agrigento, Sicily      │
│                                 │
│  [mini-map]                     │
│                                 │
│  One of the wealthiest Greek    │
│  colonies in Sicily. Founded    │
│  ~580 BC by settlers from       │
│  Gela. Famous for its massive   │
│  temples — the Valley of the    │
│  Temples still stands today.    │
│                                 │
│  • Founded: ~580 BC             │
│  • 154 years before its fall    │
│  • On the south coast of Sicily │
│                                 │
│         [Continue →]            │
└─────────────────────────────────┘
```

Seeing this card marks the entity as "encountered" in knowledge state. The learner now has enough context for the review question that follows.

#### Limit

Max 2-3 intro cards per session to avoid front-loading. If a question has many unknown entity dependencies, prefer showing the intro cards and deferring the question to next session.

### Layer 3 — Map View (Independent Feature)

An interactive map showing places from the active curriculum domain(s). Separate screen accessible from:
- Entity sheet ("View on map" button)
- Curriculum/knowledge-map screen
- Drawer navigation

#### Design Considerations (for design-explorer)

- **Leaflet in WebView**: Lightest option, no API key, great for fixed region (Mediterranean). Custom tile layers, markers with knowledge-state colors, tap markers for entity sheets.
- **react-native-maps**: Heavier, native feel, but more setup. Better for pinch-zoom-pan.
- **Static approach (v0)**: Just a pre-rendered SVG/image of the Mediterranean with dots. Click a dot to see the entity. Zero dependencies.

The map should show:
- Entity markers colored by knowledge state (unknown=gray, encountered=yellow, anchored=green)
- Cluster labels for regions (e.g., "Greek Sicily", "Magna Graecia")
- Tap marker → Entity Sheet (same sheet as from review cards)
- Filter by curriculum domain, time period

## Data Model Changes

### Extend `shared_entities` table

```sql
ALTER TABLE shared_entities ADD COLUMN description TEXT;
ALTER TABLE shared_entities ADD COLUMN entity_type TEXT;        -- place, person, event, period
ALTER TABLE shared_entities ADD COLUMN modern_name TEXT;         -- "Agrigento" for Akragas
ALTER TABLE shared_entities ADD COLUMN wikipedia_url TEXT;
ALTER TABLE shared_entities ADD COLUMN latitude REAL;
ALTER TABLE shared_entities ADD COLUMN longitude REAL;
ALTER TABLE shared_entities ADD COLUMN aliases TEXT;             -- JSON array of alternate names
ALTER TABLE shared_entities ADD COLUMN date_start INTEGER;      -- year (negative for BCE)
ALTER TABLE shared_entities ADD COLUMN date_end INTEGER;
```

### Entity knowledge state

Reuse existing `knowledge_states` table — entities are linked to curriculum nodes via `entity_curriculum_links`. An entity's knowledge state = the state of its primary curriculum node.

If an entity spans multiple curriculum nodes (e.g., Syracuse appears in colonization, Gelon's era, Athenian expedition, etc.), use the *highest* knowledge state across linked nodes.

### New field on review response

```python
# In resurfacing_engine.py or review_engine.py, when building session:
class AnnotatedReviewItem:
    # ... existing fields ...
    entity_spans: list[EntitySpan]  # annotated positions in rich_answer

class EntitySpan:
    start: int
    end: int
    entity_id: str
    entity_type: str
    name: str
    knowledge_state: str  # from knowledge_states
```

## Entity Data Bootstrap

Need ~50-80 entities for the five curriculum domains. Generate via LLM from existing curriculum nodes:

```
For each curriculum node, extract the 2-4 most important named entities
(places, people, events). For each:
- name, entity_type, description (1-2 sentences)
- modern_name (if applicable)
- dates
- coordinates (for places)
- wikipedia_url
- aliases
```

Cross-reference with existing `shared_entities` data (25 entries from session 34).

## Implementation Order

1. **Entity data bootstrap** — Generate entity records for Sicily + Ancient Greece domains
2. **Server entity annotation** — String-match entity names in `rich_answer`/`memory_hook`, return `entity_spans` in review response
3. **Entity Sheet UI** — Bottom sheet component with description, type badge, knowledge state, actions
4. **"I don't know this" action** — Feeds back into knowledge_states, creates/prioritizes review items
5. **Entity Intro Cards** — Session builder checks entity prereqs, inserts intro cards
6. **"Tell me more" action** — AI-generated exploration prompts scoped to entity
7. **Map view** — Separate feature, uses same entity data (design-explorer first)

## Connection to Alif Patterns

| Alif Pattern | Petrarca Equivalent |
|---|---|
| Word tap → WordInfoCard | Entity tap → Entity Sheet |
| Missed (red) / Confused (yellow) | "I don't know this" / implicit (encountered but fuzzy) |
| Root gate (hide meaning if siblings known) | Entity intro card (introduce before quizzing) |
| ReintroCard before sentence | Entity Intro Card before question |
| Memory hooks generated on lapse | Entity description + anchors on "don't know" |
| Per-surface-form variant stats | Per-entity knowledge tracking across nodes |
| Word lookup increments `times_seen` | Entity tap auto-schedules review item |
| "Queue follow-up questions" on node | "Tell me more" on entity |

## Open Questions

1. **How many entities per card?** Rich answers might mention 3-5 entities. Do we annotate all, or only the "important" ones? Maybe annotate all but only highlight unknown ones visually.

2. **Entity sheet depth vs. inline tooltip?** A full bottom sheet is interruptive. Could start with an inline tooltip (name + 1 line + "tap for more") and only open the sheet on second tap.

3. **Map in entity intro cards?** For places, the intro card should probably include a mini-map. Static image (pre-rendered) vs. live map component — static is simpler and works offline.

4. **Entity intro card source text?** Use `shared_entities.description` or generate richer briefings from the curriculum node description + LLM? The latter is better but adds latency.

5. **Threshold for "unknown"?** When is an entity "known enough" to skip the intro card? Options: any encounter counts, or require at least one successful review of a linked node.

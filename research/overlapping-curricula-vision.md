# Overlapping Curricula: A Reading Companion Vision

**Date**: 2026-03-21
**Status**: Exploration / Design

## The Core Idea

Instead of one monolithic knowledge graph, model knowledge as **multiple bounded curricula** that overlap and cross-reference. Each curriculum is like a college course: a teacher made deliberate choices about what to include in ~50-80 concepts, creating a coherent pedagogical perspective on a domain.

### The College Course Metaphor

A "History of Sicily" course covers all of Sicilian history but must choose: emphasize Greek colonization or the Norman kingdom? A "History of Science" course mentions Archimedes but from a completely different angle. A "Classical Literature" course might cover some of the same periods but through texts, not events.

The power comes from **intersections**:
- Plato visiting Syracuse lights up Greek philosophy AND Sicilian politics AND political theory
- Archimedes illuminates Sicily AND history of science AND Greek civilization AND military history
- The Arab-Norman period connects Sicilian history, Islamic civilization, medieval Europe, and architectural history

### Why Bounded Courses, Not Fractal World History

A fractal approach (world history → drill down arbitrarily) is intellectually appealing but pedagogically weak:
- No teacher made deliberate choices about what matters most
- No narrative coherence — just an endless tree
- Hard to feel "done" with anything
- Doesn't match how humans organize knowledge (we think in domains with perspectives, not in hierarchies)

Bounded courses work because:
- A good teacher decided "these 60 things are what you walk away with"
- Natural stopping points create a sense of progress
- Each course has a *perspective* — the same event looks different from different angles
- Cross-references between courses are the richest learning moments

## Data Model: Shared Identities with Curriculum Lenses

### The Hybrid Approach

A concept like "Archimedes" exists as a **shared identity** (one entity across the system), but each curriculum provides a **lens** — its own description, emphasis, and context.

```
SharedEntity: Archimedes (287-212 BCE, Syracuse)
  ├── Sicily curriculum lens: "Archimedes the defender of Syracuse"
  │   emphasis: siege weapons, Roman conquest, death by soldier
  ├── History of Science lens: "Archimedes the mathematician"
  │   emphasis: buoyancy, pi approximation, method of exhaustion
  └── Greek Civilization lens: "Archimedes the Hellenistic genius"
      emphasis: Alexandrian education, Greek intellectual diaspora
```

**Knowledge tracking**: Marking "Archimedes" as known updates the shared identity. All curricula see it. But the *depth* may vary — you might know Archimedes-the-mathematician deeply but Archimedes-the-Sicilian only at surface level.

### Cross-Curriculum Connections

When a node lights up in multiple curricula simultaneously, it becomes a **nexus point**:
- Higher importance score (appears in multiple pedagogical perspectives)
- Richer context (multiple angles available)
- Natural conversation starter: "You know Archimedes from your science reading. Did you know he died during the Roman siege of Syracuse?"

### Proposed Schema Extension

```python
# Shared entity (new)
{
    "entity_id": "archimedes",
    "name": "Archimedes",
    "dates": "287-212 BCE",
    "location": "Syracuse, Sicily",
    "curricula": ["sicily", "history_of_science", "greek_civilization"],
    "nexus_score": 3  # number of curricula referencing this entity
}

# Curriculum node (existing, extended)
{
    "id": "sicily_archimedes",
    "title": "Archimedes and the Defense of Syracuse",
    "description": "...",  # curriculum-specific framing
    "entity_id": "archimedes",  # link to shared entity
    "level": 3,
    "parent_id": "sicily_greek_period",
    "prerequisites": ["sicily_syracuse_founding"],
    # ... existing fields
}
```

## Curriculum Portfolio: Starting Domains

Based on current interests and existing curricula:

### Already Generated (Opus quality, 50-70 nodes each)
1. **Ancient Greece** (67 nodes, 37 assessed) — strong on Homer + Alexander
2. **Roman Republic and Empire** (55 nodes, 50 assessed) — deep (Harris trilogy)
3. **History of Sicily** (70 nodes, 0 assessed) — comprehensive, 7 areas

### Natural Next Additions
4. **History of Science** — Archimedes, Ptolemy, Arabic transmission, Renaissance, Scientific Revolution
5. **Classical Literature** — Homer, Greek tragedy, Virgil, Ovid, Dante, Petrarch
6. **Islamic Civilization** — overlaps with Sicily (Arab period), Spain (Menocal), science transmission
7. **Medieval Europe** — Normans, Crusades, scholasticism, trade routes

### High-Overlap Nexus Points (examples)
| Entity | Curricula it spans |
|--------|--------------------|
| Archimedes | Sicily, Greece, History of Science |
| Plato | Greece, Sicily (visit to Syracuse), Classical Lit, Philosophy |
| Frederick II | Sicily, Medieval Europe, History of Science (court culture) |
| Arabic transmission of Greek texts | Islamic Civ, History of Science, Medieval Europe |
| Norman conquest of Sicily | Sicily, Medieval Europe, Islamic Civ |
| Virgil / Aeneid | Classical Lit, Roman history |
| Thucydides | Greece, Classical Lit, Sicily (Athenian expedition) |

## Cross-Curriculum Behaviors

### 1. Nexus Discovery
When reading about a topic that spans multiple curricula, surface the connections:
> "Archimedes appears in 3 of your curricula. You know him well from History of Science, but his role in the defense of Syracuse against Rome is new to you."

### 2. Contextual Bridging
When reading about Sicily: "What was happening elsewhere at this time?"
- Automatic temporal cross-references to other curricula
- "While the Arabs were conquering Sicily (827-902), the Carolingian Empire was fragmenting"

### 3. Reinforcement Through Overlap
A node known in one curriculum that appears in another creates a **reinforcement opportunity**:
- Lower cognitive load (familiar anchor)
- Deeper understanding (new angle on known concept)
- Memory consolidation (multiple encoding pathways)

### 4. Gap Detection Across Curricula
If you know Roman history well and Sicily's Roman period, but not Syracuse specifically, that's a detectable gap that book recommendations can target.

## Integration with Existing Systems

### Book Mapping (already exists)
Currently maps books → curriculum nodes. Extend to map books → nodes across *all* relevant curricula. A book on Syracuse maps to Sicily, Greece, AND Roman history nodes.

### Article Pipeline (already exists)
Claims extracted from articles could be matched against curriculum nodes across all curricula, not just one. An article mentioning Archimedes triggers connections to all three curricula.

### Knowledge Probing (Amygdala)
Run EIG probing on individual curricula as today, but also consider cross-curriculum information gain: probing a nexus node gives information about multiple curricula simultaneously.

### Hamarquizen Patterns
Apply narrative + memory hooks + spaced retrieval to curriculum nodes:
- Pre-reading priming: "Before reading about the Sicilian Vespers, what do you know about Angevin rule?"
- Memory hooks: vivid, ridiculous mnemonics for key dates/people
- Spaced retrieval: recycled questions about nexus points

## Implementation Thoughts

### Phase 1: Cross-Curriculum Connections (lightweight)
- Add `entity_id` or `cross_references` field to existing curriculum nodes
- When displaying a curriculum, show "also appears in: [other curricula]"
- Compute nexus scores

### Phase 2: Shared Entity Layer
- Build entity registry linking curriculum nodes across domains
- Track knowledge at entity level (not just node level)
- Surface cross-curriculum insights in book context and article reading

### Phase 3: Temporal Context
- Add approximate date ranges to curriculum nodes
- "What else was happening in [century]?" queries across curricula
- Timeline visualization showing multiple curricula in parallel

### Phase 4: Dynamic Curriculum Growth
- As reading reveals new interests, suggest generating new curricula
- "You've been reading a lot about Arabic science. Generate an 'Islamic Golden Age' curriculum?"
- New curriculum automatically finds overlaps with existing ones

## Open Questions

1. **Granularity of shared entities**: Are they people/events only, or also concepts like "hellenism" or "feudalism"?
2. **Knowledge state per entity vs per node**: If I know "Archimedes the mathematician" deeply but not "Archimedes the Sicilian", is that one entity with two knowledge states, or two separate assessments?
3. **Curriculum generation prompts**: Should we include existing curricula as context when generating new ones, to ensure good cross-references?
4. **How many curricula before it gets unwieldy?** 5? 10? 20?
5. **Should curricula be static or grow?** Adding nodes to an existing curriculum vs. generating a new focused sub-curriculum.

## Connections to Prior Research

- **knowledge-curriculum-vision.md**: Original "Civilization game map" metaphor — overlapping curricula is a more practical realization of the same vision
- **Session 31 (Amygdala extraction)**: EIG probing works on individual curricula; could be extended for cross-curriculum information gain
- **Hamarquizen**: Proved that narrative + retrieval + hooks works for knowledge retention, even for an 11-year-old
- **feedback_knowledge_encoding.md**: "Books provide encoding, system maintains through connections" — overlapping curricula are exactly the kind of connections that maintain knowledge
- **feedback_michel_thomas.md**: "I'll manage your memory" — the system tracks what you know across all curricula, you just read

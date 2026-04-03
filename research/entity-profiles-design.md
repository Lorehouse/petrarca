# Entity Profiles — Lightweight Knowledge Structures for Historical Figures & Periods

*Design sketch, April 2026*

## The Problem

Reading historical novels and non-fiction about specific figures (Roger II, Frederick II, Karl XII, Charlemagne) creates a recurring need: **structured knowledge about a person and their era** that doesn't fit neatly into domain curricula.

The existing curriculum system models *domains* (Sicily, Byzantine Empire, Islamic Golden Age) — each with 70+ hierarchical nodes. A historical figure like Frederick II spans multiple domains (Sicily, HRE, Crusades, Papal politics). Creating a full curriculum per person is overkill. But the existing entity system (shared_entities + entity_curriculum_links) is too thin — just names and cross-references, no structured knowledge.

**What's needed**: something between a full curriculum and a bare entity link. A *profile* that accumulates knowledge as you read.

## The Person-vs-Period Duality

Stian's question: "Still unsure if it's the person, or the period/reign."

**They're the same thing.** A historical figure *is* their period/context. Knowing "Roger II" means knowing:
- **The person**: dates (1095–1154), lineage (son of Roger I), title (Rex Siciliae)
- **The period**: what was happening (Norman kingdom, Arab-Norman synthesis, Crusades era)
- **The relationships**: al-Idrisi (court geographer), William I (successor), Frederick II (grandson)
- **The significance**: why this person matters (first European king to rule a multicultural state, Tabula Rogeriana)

This maps naturally to a **biographical scaffold** — a lightweight structure organized around the person but incorporating their historical context.

## Entity Profile Structure

```
EntityProfile {
  entity_id: "roger_ii"
  name: "Roger II of Sicily"
  type: "person"                    // person | dynasty | institution
  dates: { born: 1095, died: 1154, reign_start: 1130 }
  one_liner: "Norman King of Sicily who created Europe's most advanced multicultural state"
  
  // Where this entity appears in curricula
  curriculum_appearances: [
    { domain: "sicily", node_id: "roger_ii_rex_siciliae", lens: "Founder of the Kingdom" },
    { domain: "byzantine", node_id: "norman_threat", lens: "Attacker of Corfu, rival to Constantinople" },
  ]
  
  // Structured knowledge layers (accumulated from books + key_facts)
  scaffold: {
    identity: {
      // Layer 1: Who? When? (load-bearing facts)
      facts: [
        { q: "When did Roger II reign?", a: "1130–1154", source: "sicily_key_facts" },
        { q: "Who was Roger II's father?", a: "Roger I (Great Count of Sicily)", source: "sicily_key_facts" },
      ]
    },
    context: {
      // Layer 2: What was happening? What did they do?
      facts: [
        { q: "What made Roger II's kingdom unique?", a: "Trilingual court (Arabic, Greek, Latin), centralized bureaucracy", source: "sicily_key_facts" },
        { q: "Who was al-Idrisi?", a: "Arab geographer who created the Tabula Rogeriana at Roger's court", source: "sicily_key_facts" },
      ]
    },
    connections: {
      // Layer 3: What came before/after? Who else matters?
      related_entities: ["al_idrisi", "roger_i", "frederick_ii", "william_ii"],
      temporal_neighbors: ["Second Crusade (1147)", "Fall of Edessa (1144)"],
      facts: [
        { q: "How was Frederick II related to Roger II?", a: "Grandson — connected the Norman kingdom to the Holy Roman Empire", source: "sicily_key_facts" },
      ]
    },
    significance: {
      // Layer 4: Why does this matter?
      facts: [
        { q: "Why did Roger II's enemies call him 'the baptized Sultan'?", a: "His court culture and governance resembled an Islamic state more than a European kingdom", source: "sicily_key_facts" },
      ]
    }
  }
  
  // Books that contributed to this profile
  sources: [
    { book_id: "kindle_B00...", title: "A Sultan in Palermo", coverage: "deep" },
    { book_id: "kindle_B00...", title: "The Normans in Sicily", coverage: "moderate" },
  ]
  
  // Knowledge state (how well do I know this entity?)
  knowledge: {
    identity_known: true,       // Can recall dates, basic who
    context_known: "partial",   // Know some of what they did
    connections_known: false,    // Haven't connected to other entities yet
    depth_score: 0.4            // 0-1, weighted across layers
  }
}
```

## How Entity Profiles Generate Questions

This is the key question: where do review questions come from?

### Source 1: Inherited from curriculum key_facts

Entity profiles don't *generate* new facts — they **curate and organize existing ones**. Roger II's profile pulls facts from:
- `sicily_his_roger_ii_rex_siciliae` key_facts (5 facts)
- `sicily_his_the_arabnorman_synthesis` key_facts (3 facts)  
- `sicily_his_the_cappella_palatina` key_facts (4 facts, Roger II as patron)

These already have `question`/`answer` pairs and `entities` tags. The profile just organizes them into the 4-layer scaffold.

### Source 2: Cross-curriculum connection questions

When Roger II appears in both Sicily and Byzantine curricula, the profile can generate **bridge questions**:
- "What was Roger II's relationship with the Byzantine Empire?" (combines Sicily lens: "Founder of the Kingdom" with Byzantine lens: "Norman threat")

These are the most valuable questions because they test *connected* knowledge, not isolated facts.

### Source 3: Reading-triggered questions

When you start reading "A Sultan in Palermo", the system knows:
1. This book is about Roger II and al-Idrisi
2. Your current entity profile for Roger II has identity_known=true but connections_known=false
3. → Generate pre-reading question: "Before you start: what do you already know about Roger II's court?"
4. → Generate reading-companion questions at chapter boundaries: "The novel mentions the Tabula Rogeriana. What was it?"

### Source 4: Entity-to-entity relationship questions

The `connections.related_entities` field enables:
- "How were Roger II and Frederick II related?" (genealogical)
- "What did Roger II and al-Idrisi create together?" (collaboration)
- "What happened to Sicily after Roger II's death?" (succession/consequence)

These test the *web* of knowledge, not isolated nodes.

## The Common Pattern: Reading About Historical Figures

Stian notes: "Reading about a historical person will be very common. Karl XII etc."

The pattern is always:
1. **Encounter** a figure in a book (novel or non-fiction)
2. **Need baseline knowledge**: dates, role, significance
3. **Accumulate depth** as you read more (this book, then related books)
4. **Connect** to other figures and periods you know

Entity profiles serve all four stages without requiring a full curriculum per person.

### Example: Karl XII of Sweden

You read a biography of Karl XII. No "Swedish Empire" curriculum exists yet. The profile is:

```
EntityProfile {
  entity_id: "karl_xii_sweden"
  name: "Karl XII of Sweden"
  dates: { born: 1682, died: 1718, reign_start: 1697 }
  one_liner: "Warrior king who led Sweden into the Great Northern War and lost"
  
  curriculum_appearances: []  // No curriculum yet — that's fine!
  
  scaffold: {
    identity: [
      { q: "When did Karl XII become king?", a: "1697, at age 15", source: "book:karl_xii_bio" }
    ],
    context: [
      { q: "What was the Great Northern War?", a: "Sweden vs Russia/Denmark/Saxony (1700-1721)", source: "book:karl_xii_bio" }
    ],
    connections: {
      related_entities: ["peter_the_great", "august_ii_saxony"],
      temporal_neighbors: ["Battle of Narva (1700)", "Battle of Poltava (1709)"]
    },
    significance: [
      { q: "What happened to Sweden's empire after Karl XII?", a: "Collapsed — Sweden went from great power to secondary power", source: "book:karl_xii_bio" }
    ]
  }
}
```

**No curriculum needed.** The entity profile IS the knowledge structure. If later you read 3 more books about Swedish history, *then* a "Swedish Empire" curriculum might make sense — and the entity profiles would become nodes in it (or link to it).

## Entity Profile as Curriculum Seed

This is the key insight: **entity profiles are proto-curricula**. When you accumulate enough entity profiles in a domain, they naturally suggest a curriculum:

```
Roger I  →  Roger II  →  William II  →  Frederick II  →  Manfred  →  Angevins
```

These connected entity profiles *are* the Norman Sicily story. If you didn't already have a Sicily curriculum, this chain would generate one.

**Growth path:**
1. Read about Roger II → entity profile created (5 facts from key_facts)
2. Read about Frederick II → entity profile created, linked to Roger II
3. Read about al-Idrisi → entity profile created, linked to Roger II
4. System notices: 3+ connected entities in same domain → suggest curriculum generation?

For now, this is future work. The immediate value is: **structured review questions organized around the person you're reading about.**

## Implementation Plan

### Phase 1: Auto-generate from existing key_facts (no new data needed)
- For each entity that appears in ≥2 key_facts across a curriculum, create an entity profile
- Populate scaffold layers from the key_facts (they already have `type` = date/person/event/connection/significance)
- Store in `entity_profiles` table in petrarca.db
- Roger II: already has 5 facts in his own node + appearances in 6 other nodes = rich profile

### Phase 2: Book-linked profiles
- When a book is mapped to curriculum nodes, extract entity profiles for the main figures
- For books *without* curriculum mappings (like Karl XII), generate a standalone profile from book research data
- `POST /entity/profile/{entity_id}` endpoint to serve profiles

### Phase 3: Review integration  
- Entity profile questions appear in the unified card stream alongside curriculum review cards
- Priority: identity facts first (P1), then context (P1-P2), then connections (P2), then significance (P3)
- Cross-entity relationship questions generated from `connections.related_entities`

### Phase 4: Reading companion integration
- When starting a book about a known entity, show current profile state
- "You know Roger II's dates and role. This novel will deepen your understanding of the Arab-Norman synthesis."
- Chapter-boundary questions informed by what the book covers

## What This Is NOT

- **Not a curriculum**: No prerequisites, no hierarchy, no 70+ node tree. Just a flat scaffold around one entity.
- **Not FSRS**: No spaced repetition scheduling. Just "do I know this?" tracking with depth layers.
- **Not auto-generated prose**: The scaffold facts come from key_facts (human-reviewed structured data), not LLM summarization.
- **Not a Wikipedia article**: Short, testable facts organized for review, not encyclopedic coverage.

## Open Questions

1. **How deep should a profile go?** 4 layers (identity/context/connections/significance) seems right, but should significance always be present? For minor figures, identity + context might suffice.

2. **When to auto-create vs. user-triggered?** Auto-create for entities in key_facts? Or only when user starts reading a book about them?

3. **Profile merging**: If Roger II appears in Sicily, Byzantine, and Crusades curricula, the profile is one entity with multiple lenses. How do we merge facts from different curriculum contexts without duplication?

4. **Relationship questions**: "How were Roger II and Frederick II related?" — these cross-entity questions are the most valuable but need a generation strategy. Template-based? LLM-generated from scaffold data?

5. **Standalone profiles (no curriculum)**: For Karl XII (no Swedish curriculum exists), the profile facts must come from somewhere. Book research? LLM extraction with human review? This needs a lightweight fact-extraction pipeline for book-only entities.

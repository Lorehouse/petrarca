# Historiographic Knowledge in Petrarca: Design Document

**Date**: April 11, 2026
**Status**: Design proposal (not yet implemented)
**Context**: Session 67 — triggered by the need to capture "early caliphates prioritized Arab identity, later ones didn't" without triggering the factual knowledge pipeline
**Prerequisite reading**: `design-vision.md`, `review-system-architecture.md`, `overlapping-curricula-vision.md`, `beyond-flashcards-knowledge-retention.md`

---

## 1. The Problem

Petrarca's knowledge model was built for **factual knowledge**: dates, events, people, sequences, causal chains. Every data structure reflects this:

- `key_facts` stores question/answer pairs with types `date | event | person | connection | significance`
- `knowledge_states` tracks a linear progression: `unknown → mentioned → engaged → anchored`
- FSRS scheduling assumes items have a "correct answer" you either knew, partly knew, or missed
- The review stream scores and prioritizes items assuming binary right/wrong evaluation
- Voice capture extracts `facts`, `wonderings`, and `confidence_tagged` claims — all fact-shaped

This works extraordinarily well for what it does. The factual scaffold (principle #7) is load-bearing: knowing that the Abbasid Revolution was in 750 CE, that Baghdad replaced Damascus, that the Umayyads fled to Iberia — these are the hooks that make everything else stick.

But as reading deepens in any domain, a second layer of knowledge emerges that the system cannot represent:

| What you encounter | Example | System handles it? |
|---|---|---|
| **Fact** | "The Abbasid Revolution overthrew the Umayyads in 750 CE" | Yes |
| **Attributed theory** | "Patricia Crone argued Mecca wasn't a major trading center" | No — attribution matters as much as content |
| **Historiographic debate** | "Was the Islamic conquest of the Levant a military conquest or a gradual migration?" | No — it's a *landscape* of positions |
| **Interpretive framework** | "Ibn Khaldun's asabiyyah cycle explains caliphal decline" | Partially — can name it, can't capture it as a *lens* |
| **Personal hypothesis** | "I think early caliphates differ from later ones on Arab priority" | No — unverified, to revisit when reading more |
| **Revision of consensus** | "Revisionist historians challenge the 'Islamic Golden Age' narrative" | No — it's about how understanding *changed* |
| **Source evaluation** | "Al-Tabari's account of the Abbasid revolution may reflect pro-Abbasid bias" | No — requires modeling source reliability |

These are not facts with right/wrong answers. They are **attributed, debatable, and their value is relational** — how they connect to other theories, what evidence supports them, who disagrees.

### Why this matters now

The system is entering domains (Islamic history, classical reception, philosophy) where historiographic perspective is not a "nice to have" but is *constitutive of the knowledge itself*. You cannot understand the Islamic conquests without understanding that scholars fundamentally disagree about what happened and why. The "factual" framing ("Arabs conquered the Levant in 636 CE") hides the historiographic reality ("scholars debate whether this was conquest, migration, or a complex process of cultural transformation").

Principle #1 ("hooks, not facts") anticipated this: the frameworks ARE the hooks. Knowing "Crone challenged the Mecca trade thesis" is exactly the scaffold that makes subsequent reading richer. But the system currently has no way to capture, track, or surface this kind of knowledge.

---

## 2. What We're NOT Trying to Do

Before proposing solutions, it's important to be clear about scope. This document does **not** propose:

- **Replacing the factual scaffold.** Facts first, then frameworks (principle #7) remains correct. The factual layer is load-bearing and must not be diluted. You need to know *when* the Abbasid Revolution happened before you can engage with *why* historians disagree about its causes.

- **Building a full historiographic debate tracker.** A system that models every scholarly disagreement with evidence inventories, citation networks, and argument maps would be academically interesting but practically useless for a single reader's knowledge growth.

- **Making the review system handle theories.** FSRS scheduling assumes a correct answer. Theories don't have correct answers. Trying to schedule "review this debate" on spaced intervals would produce meaningless interactions.

- **Forcing interpretive engagement before the reader is ready.** If you've read one book on Islamic history, you're not ready to evaluate competing historiographic frameworks. The system should hold interpretive knowledge until the factual foundation is strong enough to support it.

---

## 3. A Taxonomy of Non-Factual Knowledge

Not all interpretive knowledge is the same. Understanding the taxonomy helps design the right intervention at each level:

### Level 0: Seeds (personal hypotheses)
**Example**: "I think early caliphates prioritized Arab identity, later ones moved toward universalism"
**Nature**: Unverified personal observation or something heard secondhand. Not attributed to a scholar. May be wrong. Value is as a prompt for future investigation.
**What the system should do**: Save it. Link it to relevant curriculum nodes. Surface it when the reader engages more deeply with those nodes. No processing, no quizzing.
**Current status**: **Implemented** (session 67 — `source='insight'` in voice_transcripts).

### Level 1: Attributed claims
**Example**: "Patricia Crone argued that Mecca was not a major trading center"
**Nature**: A specific scholar made a specific argument. The claim has an author, a publication, and a context. It may be widely accepted, controversial, or superseded.
**What the system should do**: Record the claim with attribution. Track whether the reader is *aware* of the claim. When the reader encounters related material, note "you've seen Crone's argument about this."
**Challenge**: Requires distinguishing "Crone argued X" (historiographic fact about what a scholar said) from "X is true" (factual claim about the world).

### Level 2: Debates (structured disagreements)
**Example**: "Scholars disagree about whether the Islamic conquest of the Levant was primarily military, demographic, or cultural"
**Nature**: Multiple positions exist, each with supporting evidence and proponents. The debate itself is a thing to know about — awareness of it is more valuable than any single position.
**What the system should do**: Track the debate as a first-class object. Know which positions the reader has encountered. Surface new positions when encountered in reading.
**Challenge**: Debates are not binary (for/against) but multidimensional. A reader may understand position A deeply and not know position B exists.

### Level 3: Interpretive frameworks (lenses)
**Example**: "Ibn Khaldun's asabiyyah cycle as a framework for understanding caliphal decline"
**Nature**: A theoretical lens that can be applied across many specific cases. Not a claim about one event but a way of seeing patterns across events.
**What the system should do**: Track whether the reader knows the framework. When encountering a new case (e.g., Ottoman decline), note "you could apply Ibn Khaldun's framework here."
**Challenge**: Frameworks are not right or wrong but more or less useful. The same event can be illuminated by multiple frameworks.

### Level 4: Historiographic evolution
**Example**: "The concept of an 'Islamic Golden Age' was constructed by 19th-century European scholars and is now being critically re-examined"
**Nature**: Knowledge about how historical understanding itself has changed over time. Meta-knowledge about the discipline.
**What the system should do**: This is genuinely advanced and probably out of scope for now. Park it with Level 0 (seeds) until the reader is deeply engaged with the domain.

---

## 4. The Central Risk: Muddying the Waters

The most important section of this document. Adding interpretive knowledge tracking could make the basic learning experience **worse** in several concrete ways:

### 4.1 Diluting review time

**The risk**: If the review stream includes "here's a debate to think about" alongside "when was the Battle of Yarmouk?", the factual scaffold gets built more slowly. The reader spends cognitive energy on nuanced historiographic questions when they should be cementing basic chronology.

**Why this matters**: The 70% novelty finding (principle #9) applies to facts, not theories. A review session that's 70% facts you almost-know and 30% debates you can't evaluate is not in the zone of proximal development — it's frustrating.

**Mitigation**: Strict separation. Interpretive knowledge should NEVER appear in the standard review stream. It appears in a different context: when reading new material (synthesis pipeline), when doing voice elicitation about a topic, or in a dedicated "explore" mode. The review stream stays purely factual.

### 4.2 Ambiguous knowledge states

**The risk**: The current knowledge_states model is beautifully simple: unknown → mentioned → engaged → anchored. Everyone understands what "anchored" means for a fact (you know it cold). What does "anchored" mean for a debate? You firmly believe one side? You can articulate all positions? You've read the primary sources?

**Why this matters**: Knowledge states drive the entire system — review scheduling, stream scoring, voice elicitation targets, the knowledge atlas visualization, the "I'll manage your memory" promise. If knowledge states become ambiguous, all downstream systems lose reliability.

**Mitigation**: Do NOT extend knowledge_states to cover interpretive knowledge. Keep the existing model purely factual. If interpretive knowledge needs tracking, it needs its own parallel state model with different semantics — and it should be clearly labeled as a separate thing.

### 4.3 Premature exposure

**The risk**: Surfacing "scholars disagree about X" before the reader has a solid factual foundation on X creates the illusion of understanding without substance. You can't evaluate whether Crone's Mecca thesis is compelling if you don't know the basic geography and chronology of pre-Islamic Arabia.

**Why this matters**: This directly contradicts principle #7 (facts first, then concepts). The factual scaffold enables historiographic understanding, not the other way around.

**Mitigation**: Gating. Interpretive content surfaces only when the reader's factual knowledge of the relevant nodes reaches a threshold (e.g., `engaged` or `anchored` on 60%+ of related nodes in the domain). Before that threshold, insights are stored but dormant.

### 4.4 False attribution confidence

**The risk**: If the system uses LLMs to extract "Scholar X argued Y" from text, the attribution may be wrong, oversimplified, or missing nuance. LLMs are notoriously unreliable at scholarly attribution. The reader trusts the system ("I'll manage your memory") and now has a wrong mental model of who argued what.

**Why this matters**: Incorrect attribution in historiography is worse than no attribution. "Crone argued X" when she actually argued "X under conditions Y with caveats Z" creates a false sense of understanding that's harder to correct than ignorance.

**Mitigation**: For now, do NOT use LLM to extract attributed claims from text. Only capture what the reader explicitly says ("I heard that Crone argues X") or what's clearly structured in the source material. Human attribution over machine attribution.

### 4.5 Scope creep into the curriculum

**The risk**: If the curriculum node model expands to include "debate nodes" and "theory nodes" alongside fact nodes, the curriculum generation pipeline becomes dramatically more complex. Opus already generates 70-90 nodes per domain; adding historiographic dimensions could double that. The curriculum graph becomes unwieldy, harder to visualize, harder to navigate.

**Why this matters**: The curriculum is the organizing backbone. Its simplicity (area → topic → concept, 70 nodes per domain) is a feature, not a limitation. Adding debate nodes could fragment the coherent progression into a tangled mess.

**Mitigation**: Do NOT add new node types to the curriculum. Interpretive knowledge lives alongside/outside the curriculum, linked to nodes but not part of the node hierarchy itself. Curricula remain factual scaffolds.

---

## 5. Design Proposal: Layered Approach

Given the risks above, the proposal is to build interpretive knowledge support in layers, each independent and deferrable. Each layer should be useful on its own without requiring the next.

### Layer 0: Insight Capture (DONE)

**What**: Voice capture with `capture_type='insight'` saves transcripts linked to curriculum nodes without triggering the analysis pipeline.

**Data**: `voice_transcripts` with `source='insight'`, linked nodes in `llm_result` JSON.

**Value**: The reader can record observations, theories, and hypotheses. They're saved and retrievable. This alone handles the immediate need.

**Status**: Implemented in session 67.

### Layer 1: Insight Surfacing (next step)

**What**: When the reader encounters a curriculum node that has linked insights, surface them. Not as quiz material — as context.

**Where insights surface**:
1. **Voice elicitation**: When testing recall on a node, include "You previously noted: [insight transcript]" in the feedback. This reminds the reader of their hypothesis and lets them evaluate it against what they now know.
2. **Reading companion / synthesis**: When reading an article that maps to nodes with linked insights, show "Your earlier thought on this: [insight]" as a sidebar or popover.
3. **Review card "About"**: The existing ⋯ menu → "About this card" modal could include a section for linked insights.
4. **Knowledge atlas**: Nodes with insights get a visual marker (e.g., a small icon) indicating "you had a thought about this."

**Data model change**: None. Query `voice_transcripts WHERE source='insight'` by node_id/domain_id. The data is already there.

**Implementation sketch**:
```python
def get_insights_for_node(node_id: str, domain_id: str) -> list[dict]:
    """Retrieve insight transcripts linked to a curriculum node."""
    conn = get_connection(readonly=True)
    rows = conn.execute("""
        SELECT id, transcript, llm_result, created_at
        FROM voice_transcripts
        WHERE source = 'insight'
          AND (node_id = ? OR domain_id = ?)
        ORDER BY created_at DESC
    """, (node_id, domain_id)).fetchall()
    conn.close()
    
    results = []
    for row in rows:
        llm = json.loads(row['llm_result'] or '{}')
        nodes_linked = llm.get('nodes_linked', [])
        # Check if this specific node is among the linked nodes
        if any(n['node_id'] == node_id for n in nodes_linked):
            results.append({
                'id': row['id'],
                'transcript': row['transcript'],
                'created_at': row['created_at'],
                'nodes_linked': nodes_linked,
            })
    return results
```

**Gating**: Only surface insights when the reader's knowledge of the node is at least `mentioned`. Don't show insights for nodes the reader hasn't engaged with at all.

**Risk level**: Very low. This is read-only surfacing of existing data. No new processing, no changes to review flow.

### Layer 2: Structured Insight Metadata

**What**: When an insight is saved, optionally extract lightweight metadata — not full LLM analysis, but structured tags that help with retrieval and surfacing.

**Proposed metadata** (extracted by LLM at save time, or retroactively):
```json
{
  "insight_type": "hypothesis | attributed_claim | debate_awareness | framework | question",
  "attribution": "Patricia Crone" | null,
  "confidence": "speculation | informed_guess | well_supported",
  "related_to": ["umayyad_caliphate", "abbasid_revolution"],
  "keywords": ["arab identity", "universalism", "caliphate ideology"]
}
```

**Why this helps**: Enables smarter surfacing. A `hypothesis` surfaces differently than a `debate_awareness`. An `attributed_claim` can be cross-referenced when the reader encounters the same scholar elsewhere.

**Implementation**: Add a `metadata` JSON column to `voice_transcripts`, or store in the existing `llm_result` field. Extraction could use Gemini Flash (fast, cheap) with a simple prompt:

```
Given this recorded insight:
"{transcript}"

Classify it:
- insight_type: hypothesis | attributed_claim | debate_awareness | framework | question
- attribution: name of scholar if any, else null
- confidence: speculation | informed_guess | well_supported
- keywords: 3-5 keywords for retrieval
```

**Risk level**: Low. It's metadata enrichment on already-stored data. If the classification is wrong, no downstream system breaks — it just affects surfacing relevance.

**Decision point**: Should this run at save time (adding ~3s latency) or as a background job? Probably background — the user doesn't need to see the metadata, and it keeps the "Save Insight" path fast.

### Layer 3: Cross-Insight Connections

**What**: When the reader accumulates multiple insights about related topics, surface the connections. "You recorded 3 insights about caliphal ideology — here's how they relate."

**Example**:
- Insight 1 (week 1): "Early caliphates prioritized Arab identity"
- Insight 2 (week 3): "The Abbasid Revolution was partly a revolt by non-Arab Muslims"
- Insight 3 (week 5): "Ibn Khaldun describes asabiyyah as the force behind new dynasties"

The system notices these three insights share curriculum nodes and offers: "Your insights about caliphal transitions form a pattern — the shift from ethnic to universal identity seems connected to the asabiyyah cycle you noted."

**Implementation**: Semantic similarity (limbic.amygdala embeddings) across insight transcripts, clustered by domain. When a cluster reaches 3+ insights, generate a synthesis prompt.

**Risk level**: Medium. This involves LLM generation from user-recorded content. The synthesis could be wrong or miss the point. But since it's surfaced as "here's what your insights suggest" rather than "here's a fact," the stakes are lower.

**Gating**: Only triggers when the reader has 3+ insights in a domain AND factual knowledge is at `engaged` for 50%+ of related nodes.

### Layer 4: Historiographic Annotations on Review Cards

**What**: When a review card's topic has active historiographic debates, annotate the card with a small indicator — not as a quiz element, but as contextual enrichment.

**Example**: A review card asking "When did the Abbasid Revolution begin?" could have a small annotation: "Note: the nature and causes of this revolution are debated — you have insights on this."

**Implementation**: During `generate_review_stream()`, check for insights linked to each card's curriculum node. If insights exist and the reader's knowledge is `anchored`, add an `insights_available` flag to the card data. The client renders a subtle indicator (not a new card type — just a badge or footnote on existing cards).

**Risk level**: Medium-low. The annotation is passive (doesn't affect scoring or scheduling). But it does change the review experience by adding visual noise. Must be very subtle — a small marker, not a paragraph of text.

**Strict rule**: The annotation NEVER affects the review answer evaluation. "Knew" still means you knew the factual answer, regardless of whether you engaged with the historiographic annotation.

### Layer 5: Debate-Structured Review (Future, speculative)

**What**: A new card type (separate from the factual review stream) that presents a historiographic debate and asks the reader to articulate positions.

**Example card**:
```
Scholars disagree about the nature of the Abbasid Revolution.

Position A (Crone & Hinds): It was a tribal Arab revolt co-opted by the Abbasids
Position B (Sharon): It was a genuinely popular movement driven by religious grievance
Position C (modern synthesis): Both factors operated, with regional variation

Can you articulate why these positions differ?
```

**This is the most speculative layer** and has the highest risk of muddying the basic learning experience. It requires:
- A new card type in the review stream
- A different grading model (not knew/partly/missed)
- A different scheduling model (not FSRS)
- A different knowledge state model

**Risk level**: High. This is where the system could lose its clarity. The review stream is currently crisp: here's a question, grade yourself, move on. Adding "articulate a debate" changes the cognitive load entirely.

**Recommendation**: Don't build this until Layers 0-3 are well-tested AND the reader explicitly wants it. The factual review stream's simplicity is a feature, not a limitation. Historiographic engagement may be better served by reading more books, not by app-mediated debate review.

---

## 6. How Existing Systems Already Hint at This

Several existing Petrarca systems already touch on interpretive knowledge without explicitly handling it:

### 6.1 Multi-source knowledge_items

When the same curriculum node accumulates sources from multiple books, the system already implicitly captures "different authors emphasize different things about the same topic." The analytical question prompt (review count 3+) uses lenses like COMPARATIVE: "How does this compare to another perspective?"

**Extension opportunity**: When generating analytical questions for multi-source nodes, check for linked insights. If the reader has recorded hypotheses about this topic, reference them: "You previously wondered whether [insight]. Now that you've read [new source], has your view changed?"

### 6.2 Temporal cross-references

The system already generates "Meanwhile in [other domain]" cross-references. This is factual juxtaposition, but it's one step from interpretive juxtaposition: "You know about the Abbasid Revolution from the Islamic curriculum. The Byzantine curriculum presents a different perspective on the same events."

### 6.3 Entity nexus cards

For entities appearing in 3+ curricula (nexus_score >= 3), the system generates cross-perspective cards. This is already historiographic in spirit — "How does [entity] look different from [domain A] vs [domain B]?"

### 6.4 Voice elicitation confidence_tagged

The voice analysis prompt already detects `confident`, `uncertain`, and `wrong` claims. Uncertain claims are essentially Level 0 hypotheses — the reader is speculating and the system notices. This data exists in `voice_transcripts.llm_result` but isn't used for interpretive knowledge tracking.

### 6.5 The synthesis pipeline's tension detection

The synthesis pipeline explicitly identifies "Source A says X while Source B says Y" — this is debate detection. Currently it's rendered as prose in the synthesis. Making these tensions first-class objects (linked to curriculum nodes, trackable) would be a natural evolution.

---

## 7. What the Research Says

### Matuschak on conceptual vs. factual retention

Andy Matuschak's Quantum Country work validates FSRS-style review for factual knowledge but explicitly notes "the gap between recognition during review and fluent recall during real work" for conceptual understanding. His recent work on "dynamic practice" — AI-synthesized questions grounded in authentic work, increasing in complexity — points toward a different model for interpretive knowledge.

Key quote: "Memory as infrastructure for thinking: conceptual mastery requires remembering foundational details. Just as chess masters recognize 25,000-100,000 positional patterns, learners who solidify foundations access higher abstraction levels."

**Implication**: The factual scaffold enables interpretive understanding. Don't skip the scaffold. But also don't confuse having the scaffold with having interpretive understanding.

### Fuzzy-Trace Theory

Verbatim traces (specific facts) decay faster than gist traces (conceptual frameworks). This suggests that once a reader grasps a historiographic debate (gist), they'll retain the shape of the debate longer than the specific dates involved. The system should invest more in ensuring the reader grasps the gist of debates, less in testing whether they remember which scholar said what.

**Implication**: Interpretive knowledge should be tracked as "aware of the debate" rather than "remembers Scholar X's specific argument."

### Elaborative interrogation

Research consistently shows that asking "why?" improves retention more than asking "what?" For historiographic knowledge, the "why?" is the natural question: "Why do historians disagree about this?" rather than "What did Crone argue?"

**Implication**: If interpretive knowledge ever enters the review system, the prompts should be "why do these positions differ?" not "which scholar argues X?"

### Interleaving

Mixing different types of knowledge (factual and interpretive) in the same study session improves retention by 43% (Rohrer & Taylor). But this benefit only appears when the learner can handle both types. Premature mixing hurts.

**Implication**: Interleaving factual and interpretive content could be beneficial — but only after the factual scaffold is strong. This supports the gating mechanism proposed in Layer 1.

---

## 8. Proposed Data Model (Layers 1-3)

No new tables. Instead, enrich what already exists:

### voice_transcripts (existing table, new source value)

Already has `source='insight'`. The `llm_result` JSON field stores `nodes_linked` and (in Layer 2) structured metadata.

### New: insight_metadata (optional, for Layer 2+)

If the `llm_result` field becomes too overloaded, a small lookup table:

```sql
CREATE TABLE IF NOT EXISTS insight_metadata (
    transcript_id TEXT PRIMARY KEY REFERENCES voice_transcripts(id),
    insight_type TEXT,          -- 'hypothesis' | 'attributed_claim' | 'debate' | 'framework' | 'question'
    attribution TEXT,           -- scholar name if any
    confidence TEXT,            -- 'speculation' | 'informed_guess' | 'well_supported'
    keywords TEXT,              -- JSON array of search terms
    status TEXT DEFAULT 'active', -- 'active' | 'resolved' | 'superseded' | 'wrong'
    resolved_at INTEGER,        -- when the reader marked this as resolved
    resolution_note TEXT,       -- what they concluded
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_im_type ON insight_metadata(insight_type);
CREATE INDEX IF NOT EXISTS idx_im_status ON insight_metadata(status);
```

This is deliberately minimal. No separate tables for debates, evidence, or argument structure. The insight is still fundamentally a transcript with metadata — the structured debate model (Layer 5) would only be built if Layers 1-3 prove the concept.

### Surfacing query (Layer 1)

```sql
-- Get active insights for a curriculum node
SELECT vt.transcript, vt.created_at, im.insight_type, im.attribution, im.confidence
FROM voice_transcripts vt
LEFT JOIN insight_metadata im ON im.transcript_id = vt.id
WHERE vt.source = 'insight'
  AND vt.node_id = ?
  AND (im.status IS NULL OR im.status = 'active')
ORDER BY vt.created_at DESC;
```

### Resolution flow (Layer 2+)

When the reader reviews a node and sees a surfaced insight, they should be able to:
- **Confirm**: "Yes, I now know this is correct" → `status='resolved'`, with a note
- **Revise**: "I've learned more, here's my updated view" → creates a new insight, supersedes the old one
- **Dismiss**: "This wasn't useful" → `status='superseded'`
- **Leave active**: No action — the insight continues surfacing

This is NOT FSRS scheduling. There's no "due date" for insights. They surface when relevant context appears, and the reader decides when they're done with them.

---

## 9. Interaction with Design Principles

| Principle | How this proposal respects it |
|---|---|
| #1 "Hooks, not facts" | Interpretive frameworks ARE hooks. But only surface them once the factual hooks are in place. |
| #2 "I'll manage your memory" | Extends the promise: "I'll also hold your theories until you're ready to evaluate them." |
| #3 "Comprehension before memory" | Insights are never quizzed — only surfaced for comprehension support. |
| #4 "Atomic claims" | Insights are NOT atomic claims. They're a parallel track. Don't merge them. |
| #5 "Curriculum as bridge" | Insights link TO curriculum nodes but don't become nodes. The curriculum stays factual. |
| #7 "Facts first" | Strict gating ensures interpretive content only appears after factual foundation is solid. |
| #8 "Books encode, system maintains" | Books will provide historiographic frameworks. The system holds the reader's hypotheses until a book confirms or challenges them. |
| #10 "Dim familiar, don't hide" | Insights already encountered could be dimmed in future surfacing. |

---

## 10. Open Questions

### 10.1 When does an insight graduate to a fact?

If the reader records "I think early caliphates prioritized Arab identity" as an insight, and later reads a book that confirms this, should the insight become a `key_fact` on the relevant curriculum node? Or does it remain forever in the insight layer?

**Tentative answer**: It remains an insight. The book creates its own facts via the normal pipeline. The insight gets marked `resolved` with a note referencing the book. This keeps the two layers cleanly separated.

### 10.2 Should insights from books be different from insights from voice?

A reader might type "Crone argues X" while reading, or say it in a voice capture. Should the system distinguish between "I read this" and "I thought this"?

**Tentative answer**: Yes, via `insight_type`. An `attributed_claim` ("Crone argues X") is different from a `hypothesis` ("I think X"). The attribution field captures the difference. But both live in the same infrastructure.

### 10.3 How many insights before the system becomes noisy?

If a reader records 50 insights across 10 domains, surfacing becomes noisy. Every review card could have 2-3 linked insights cluttering the experience.

**Tentative answer**: Limit surfacing to 1 insight per node per review session. Prefer recent insights and `hypothesis`-type over `question`-type. And always let the reader dismiss/resolve to reduce noise over time.

### 10.4 Should insights affect the knowledge atlas?

The knowledge atlas visualizes factual knowledge as a network. Should insights appear?

**Tentative answer**: Not on the main atlas. But a separate "insight map" overlay could be interesting — showing where the reader has open hypotheses and how they cluster. This is Layer 3 territory.

### 10.5 What about insights that span multiple domains?

"The Mediterranean was a single cultural zone, not divided into Christian and Islamic halves" spans every domain in the system. How to link it?

**Tentative answer**: Link to multiple nodes across multiple domains. The multi-domain linking already works in voice capture's node detection (phases 1-4). An insight can link to nodes in Sicily, Islamic Civilization, and Byzantine simultaneously.

### 10.6 How does this interact with the synthesis pipeline?

When generating a synthesis of articles, should the system inject the reader's insights as context? "You previously hypothesized X — this article addresses that hypothesis."

**Tentative answer**: Yes, this is exactly the right surfacing context. The synthesis pipeline already personalizes based on knowledge states. Adding "reader has insights about these nodes" is a natural extension. But implementation should wait until Layer 1 proves the concept.

---

## 11. Summary: What to Build and When

| Layer | Description | Risk | Dependencies | Recommendation |
|---|---|---|---|---|
| **0: Insight capture** | Save voice/text linked to nodes | None | None | **DONE** (session 67) |
| **1: Insight surfacing** | Show insights during elicitation, reading, review | Very low | Layer 0 | **Build next.** Proves the concept with zero new data model. |
| **2: Structured metadata** | Extract type/attribution/confidence | Low | Layer 0 | Build when 10+ insights accumulated. Background Gemini Flash job. |
| **3: Cross-insight connections** | Cluster related insights, generate synthesis | Medium | Layers 0+2 | Build when 3+ insights in a domain. Uses limbic embeddings. |
| **4: Review card annotations** | Badge on cards with linked insights | Medium-low | Layer 1 | Only after factual review is well-established per domain. |
| **5: Debate-structured review** | New card type for historiographic debates | High | Layers 1-4 | **Don't build unless proven necessary.** Reading more books may be a better intervention. |

**The key principle**: each layer is independently valuable and independently testable. Layer 1 is the critical next step — it takes the insights already being captured and makes them visible in the right context. Everything else can wait.

---

## 12. Relationship to Prior Art and Future Vision

This proposal sits at the intersection of several strands in the learning science literature:

**Zettelkasten / slip-box method**: Insights function like Luhmann's "permanent notes" — personal observations that connect to reference material. The linking to curriculum nodes serves the same function as Luhmann's indexing system.

**Bloom's Taxonomy progression**: The layered approach maps roughly to Bloom's levels. Factual scaffold = Remember/Understand. Insight capture = Analyze/Evaluate. Cross-insight synthesis = Create. The system naturally progresses the reader through these levels without forcing premature advancement.

**Vygotsky's Zone of Proximal Development**: The gating mechanism (insights only surface when factual knowledge is strong) directly implements ZPD. The insight is in the reader's ZPD only when they have enough scaffolding to engage with it meaningfully.

**Petrarca's vision (design-vision.md)**: The master design document describes "Done = able to PLACE new knowledge." Insights are things the reader can't yet place — they're tentative, unanchored, waiting for more context. The system holds them until the reader can place them. This is the "I'll manage your memory" promise (principle #2) extended to include "I'll also manage your theories."

---

*This document should be revisited after 20+ insights have been captured and Layer 1 has been tested. The key question will be: does surfacing insights during elicitation and reading actually improve the reader's engagement with historiographic knowledge? If yes, proceed to Layer 2. If no, the insight capture (Layer 0) may be sufficient on its own.*

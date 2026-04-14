# Proposal: Knowledge Growth Measurement System

**Created:** 2026-04-09
**Status:** Ready for implementation
**Builds on:** `knowledge-systems-deep-dive.md` (Apr 5), `knowledge-assessment-research.md` (Apr 4), `knowledge-profile-system-design.md` (Apr 6)

---

## Context: What Exists and What's Missing

### Already implemented (sessions 52-60)

1. **Knowledge profile system** (session 56): 786 transcript chunks with embeddings, 5 domain portraits, LEARNER CONTEXT injected into all 6 LLM templates. Transcripts are no longer write-only.
2. **FSRS-6 scheduling** (session 58): py-fsrs with `desired_retention=0.80`, proper grade mapping (knew→Easy, partly→Good, missed→Again).
3. **Voice capture pipeline** (session 52): Full knowledge graph ingestion — entity detection, node mapping, knowledge updates, quiz generation, wonderings→ML cards.
4. **Statistics dashboard** (session 53): Knowledge bars per curriculum, review/quiz stats, activity timeline.
5. **Card provenance** (session 60): Origin badges, scheduling state tracking, FSRS scheduling drift fix.

### The gap

All of the above tracks **current state**. None tracks **change over time**. We can say "you know 35/70 Sicily nodes at engaged level" but not "you knew 20/70 a month ago and your connectivity score has doubled." The fundamental measurement question — **is the system actually working?** — remains unanswered.

The `knowledge-systems-deep-dive.md` proposed 5 phases. Phase 5 (knowledge profiles) got partially built first because it was immediately useful for prompt quality. Phases 1-4 (baseline sweep, type-differentiated scheduling, monthly sweep + growth tracking, sweep variants) were never started.

---

## What to Build: Three Tiers

### Tier 1: Passive Growth Tracking (No New User Interaction Required)

This can be built entirely from existing data. The system already records knowledge level transitions, review scores, and timestamps. We're just not plotting them.

#### 1A. Knowledge State Timeline

Track when each node moved between levels (unknown → mentioned → engaged → anchored). The data already exists in `knowledge_items` — we just need to log transitions.

```sql
-- Add to db.py migrations
CREATE TABLE IF NOT EXISTS knowledge_transitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL,
    domain_id TEXT NOT NULL,
    from_level TEXT NOT NULL,  -- 'unknown', 'mentioned', 'engaged', 'anchored'
    to_level TEXT NOT NULL,
    source TEXT NOT NULL,      -- 'article', 'book', 'voice', 'review', 'quiz'
    source_id TEXT,            -- article_id, book_id, transcript_id, etc.
    created_at INTEGER NOT NULL DEFAULT (unixepoch())
);
CREATE INDEX IF NOT EXISTS idx_kt_domain ON knowledge_transitions(domain_id);
CREATE INDEX IF NOT EXISTS idx_kt_created ON knowledge_transitions(created_at);
```

Instrument `update_knowledge()` in `curriculum_db.py` to write a transition row whenever the level changes. Then build a timeline visualization: per domain, show the cumulative count of nodes at each level over time.

**This alone answers:** "Am I learning more over time?" with a concrete chart.

#### 1B. Network Density Over Time

Use existing curriculum prerequisite edges + knowledge states to compute Goldsmith's edge overlap metric weekly (or on every dashboard load). Store as a time series.

```python
import networkx as nx

def compute_network_metrics(domain_id: str, conn) -> dict:
    """Compute learner vs expert network similarity from existing data."""
    curriculum = load_curriculum(domain_id)
    states = {r[0]: r[1] for r in conn.execute(
        "SELECT node_id, knowledge FROM knowledge_items WHERE domain_id = ?",
        (domain_id,)
    ).fetchall()}

    expert_G = nx.DiGraph()
    learner_G = nx.DiGraph()
    for node in curriculum['nodes']:
        expert_G.add_node(node['id'])
        for prereq in node.get('prerequisites', []):
            expert_G.add_edge(prereq, node['id'])
        if states.get(node['id'], 'unknown') != 'unknown':
            learner_G.add_node(node['id'])
            for prereq in node.get('prerequisites', []):
                if states.get(prereq, 'unknown') != 'unknown':
                    learner_G.add_edge(prereq, node['id'])

    e_edges = set(expert_G.edges())
    l_edges = set(learner_G.edges())
    overlap = len(e_edges & l_edges) / len(e_edges) if e_edges else 0

    return {
        'node_coverage': len(learner_G.nodes()) / len(expert_G.nodes()) if expert_G.nodes() else 0,
        'edge_overlap': overlap,
        'density': nx.density(learner_G) if len(learner_G) > 1 else 0,
    }
```

```sql
CREATE TABLE IF NOT EXISTS network_metrics_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_id TEXT NOT NULL,
    node_coverage REAL NOT NULL,
    edge_overlap REAL NOT NULL,
    density REAL NOT NULL,
    nodes_known INTEGER NOT NULL,
    nodes_total INTEGER NOT NULL,
    computed_at INTEGER NOT NULL DEFAULT (unixepoch())
);
```

Log these metrics weekly (via cron) or on every dashboard load. The edge_overlap trajectory from 0.0 → 1.0 is the primary growth signal (Goldsmith's C metric correlated r=.74 with exam performance).

#### 1C. Review Performance Trend

Already have the data — `knowledge_items` has `last_score`, `stability_days`, `due_at`, `last_reviewed_at`. Plot:
- Average stability per domain over time (are items getting easier to retain?)
- Distribution shift: % knew vs % partly vs % missed per week
- Predicted vs actual retention (FSRS calibration): at review time, compute `retrievability = (1 + factor * elapsed/stability)^(-w20)`, then compare to the actual score. This validates whether FSRS is well-calibrated.

---

### Tier 2: Voice Knowledge Sweeps (New User Interaction)

This is the centerpiece from the deep-dive research. A "knowledge sweep" is a periodic (monthly) domain-wide voice assessment — 3 minutes of free recall scored against the curriculum.

#### 2A. Baseline Sweep

**Do this first.** Record a 3-minute Sicily timeline now. Score against the 70-node curriculum. This is ground truth.

The protocol:
1. Prompt: *"Tell me the history of Sicily — everything you can remember, in roughly chronological order. Speak for about 3 minutes."*
2. Transcribe via Soniox (already integrated)
3. Score via LLM against the full curriculum node list (scoring prompt in `knowledge-systems-deep-dive.md` section 4.4)
4. Store in `knowledge_sweeps` table (schema in section 4.3 of that doc)
5. Compute: coverage (nodes mentioned / total), accuracy (FActScore-style), connectivity (connections articulated), organization (chronological/thematic clustering)

#### 2B. Monthly Sweep + Delta Tracking

Repeat monthly. Each sweep links to the previous one. Compute deltas across all 5 metrics. This answers the deepest question: **is free recall improving?** — which is the ultimate test of whether the system works.

#### 2C. Sweep Variants

Rotate formats for variety and to test different knowledge dimensions:
- **Month 1**: Full timeline narrative (baseline)
- **Month 2**: Connection prompts ("What connects the Normans to Byzantium?")
- **Month 3**: Timeline again (for delta comparison)
- **Month 4**: Explain-to-a-friend (Feynman test)
- **Month 5**: Same-moment probe ("What was happening elsewhere when Frederick II ruled Sicily?")

#### UI Integration

Add a "Knowledge Sweep" option in the ✦ drawer or as a special mode in voice elicitation. The per-node elicitation already works — the sweep just uses a broader prompt and a different scoring pipeline.

After each sweep, show a results page:
- Coverage map: which nodes were mentioned (green), missed (red), new since last sweep (gold)
- Growth chart: line plot of composite score over time
- Key gaps: "The most important area you didn't mention"
- Framed positively (Michel Thomas principle): "Your knowledge of Sicily has grown from 35% to 52% coverage"

---

### Tier 3: Type-Differentiated Scheduling (Deeper System Change)

#### 3A. Different FSRS Parameters by Knowledge Type

Fuzzy-Trace Theory says verbatim traces (dates, names) decay faster than gist traces (frameworks, causal chains). Currently FSRS uses uniform parameters. The `key_facts` already have `type` (date/event/person/connection/significance).

Two implementation options:

**Option A: Separate `desired_retention` per type**
```python
TYPE_RETENTION = {
    'date': 0.85,        # Higher retention target → more frequent review
    'event': 0.82,
    'person': 0.82,
    'connection': 0.75,  # Lower target → less frequent review (gist persists)
    'significance': 0.75,
}
```

**Option B: Duolingo Half-Life Regression**
Replace FSRS entirely for review items with HLR: `log(h) = θ · x` where the feature vector includes knowledge type. Train on actual review data. This naturally learns different decay rates per type. But requires enough data (50+ reviews per type).

**Recommendation:** Start with Option A (trivial to implement), run for 2 months, then evaluate whether the type differentiation improves retention. Option B is more principled but needs data that may not exist yet.

#### 3B. Natural Spacing Credit

When reading an article that maps to curriculum nodes, those nodes get a passive "re-encounter." Currently this isn't tracked. Proposed: when article claims map to curriculum nodes, apply a small stability bump (×1.3) to those nodes' FSRS cards. Track whether article-reinforced nodes show higher retention than review-only nodes.

#### 3C. FSRS Calibration

After the current volume of reviews (likely 100+ by now), run a calibration check:

```python
def calibration_check(conn):
    """Compare FSRS-predicted retrievability to actual review outcomes."""
    rows = conn.execute("""
        SELECT stability_days, last_reviewed_at, due_at, last_score
        FROM knowledge_items
        WHERE last_score IS NOT NULL AND stability_days > 0
    """).fetchall()
    # For each review, compute predicted R at review time
    # Compare to actual score (knew=1.0, partly=0.5, missed=0.0)
    # Plot calibration curve: predicted R (binned) vs actual retention rate
```

This tells us whether FSRS is over-confident or under-confident, and whether type differentiation would help.

---

## Proposed Implementation Order

### Phase 1: Passive tracking (1-2 sessions, immediate value)

1. Add `knowledge_transitions` table, instrument `update_knowledge()`
2. Add `network_metrics_log` table, compute on dashboard load
3. Build growth visualization (standalone HTML like knowledge atlas, served at `/knowledge/growth`)
4. Add FSRS calibration script

**Why first:** Zero new user interaction needed. Uses existing data. Immediately answers "am I learning?"

### Phase 2: Baseline sweep (1 session)

1. Add `knowledge_sweeps` table
2. Add `run_knowledge_sweep()` in review_engine.py
3. Add sweep scoring prompt
4. Add endpoint `POST /api/knowledge-sweep`
5. Add UI entry point (✦ drawer or voice-elicitation variant)
6. **Record first sweep for Sicily**

**Why second:** The baseline must exist before monthly deltas mean anything. The longer we wait, the more growth we miss measuring.

### Phase 3: Monthly sweep + viz (1 session)

1. Sweep results page (coverage map, growth chart, gaps, positive framing)
2. Delta computation
3. Sweep variant prompts (connection, Feynman, same-moment)

### Phase 4: Type-differentiated scheduling (1 session)

1. Different `desired_retention` per knowledge type
2. Natural spacing credit from article reading
3. FSRS calibration analysis

---

## Key Design Decisions Needed

1. **Sweep frequency:** Monthly is proposed. More frequent risks the testing effect masking actual growth (you get better at the sweep, not at the knowledge). Less frequent means slower feedback. Monthly is the sweet spot per the research.

2. **Sweep scoring model:** Use Claude (Opus) for sweep scoring, or Gemini Flash? Sweeps are infrequent (monthly) so cost doesn't matter. Accuracy matters a lot. → **Recommend Opus via `claude -p`** since it's a batch task.

3. **Growth viz location:** Standalone HTML page (like knowledge atlas) at `/knowledge/growth`? Or integrated into the statistics dashboard? → **Recommend standalone** — it's a different mental model (longitudinal vs. snapshot).

4. **Passive tracking granularity:** Log network metrics weekly via cron, or compute on every dashboard load? → **Recommend on dashboard load + weekly cron snapshot** — dashboard gives fresh numbers, cron gives the time series.

---

## What's Genuinely Novel

From the `knowledge-assessment-research.md`: "No existing system does repeated domain-level voice free recall as a longitudinal growth metric." The combination of:
- Curriculum-aligned scoring of free voice recall
- Longitudinal comparison across sweeps
- Network structure analysis (not just fact counting)
- Type-differentiated scheduling based on Fuzzy-Trace Theory

...does not exist anywhere in the literature. The closest systems (ALEKS, GENCAT, SPARFA) all use item-response testing, not free recall. Pathfinder network comparison has been validated but never applied to voice transcript data. This is publishable.

---

## References

All references from `knowledge-systems-deep-dive.md` remain current. Key additions since April 5:
- The knowledge profile system (session 56) showed that LEARNER CONTEXT significantly improves question quality — this validates that growth measurement data will also improve prompts.
- The FSRS scheduling fix (session 60) showed 229/256 items had drift — any calibration analysis should use only post-fix data.
- Session 58's review overhaul added dual-layer logging (`interaction_log` + JSONL), providing richer data for calibration.

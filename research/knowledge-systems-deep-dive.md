# Deep Dive: Knowledge Mapping Systems, Scheduling, and Growth Measurement

**Created:** 2026-04-05
**Context:** Research synthesis on knowledge assessment researchers, their published tools/algorithms, implications for Petrarca's scheduling algorithm, and design of a longitudinal knowledge growth measurement system.

**User's guiding principle:** A rich network of factual knowledge (entities, places, times, persons, sequences, connections across them) is more important right now than higher-order frameworks. Build the factual scaffold first; the books that provide conceptual frameworks will be much more valuable when that scaffold exists.

---

## Table of Contents

1. [Researchers and Their Systems](#1-researchers-and-their-systems)
2. [Published Tools, Libraries, and Algorithms](#2-published-tools-libraries-and-algorithms)
3. [Scheduling Algorithm Recommendations](#3-scheduling-algorithm-recommendations)
4. [Knowledge Growth Measurement Design](#4-knowledge-growth-measurement-design)
5. [Implementation Plan](#5-implementation-plan)

---

## 1. Researchers and Their Systems

### 1.1 ALEKS / Knowledge Space Theory (Doignon & Falmagne)

**The theory:** Knowledge Space Theory (KST) models a domain as a set Q of items/concepts and a collection K of feasible "knowledge states" — the subsets of Q that a learner could plausibly know. Not all subsets are feasible: if you know calculus, you must know algebra. A **knowledge space** is closed under union (if states A and B are both feasible, so is A∪B). A **learning space** is additionally "well-graded" — you can always add or remove exactly one concept to move between adjacent states.

**The assessment algorithm (Continuous Markov Procedure):**
1. Start with uniform probability over all feasible knowledge states
2. **Question selection (half-split rule):** Pick the question q where the probability of states containing q is closest to 0.5 — maximally splits the distribution
3. **Bayesian update:** After observing response, update state probabilities incorporating careless error (β) and lucky guess (η) rates
4. **Terminate** when max probability exceeds threshold. Converges in ~25 questions even with millions of feasible states.

**Why it matters for Petrarca:** The curriculum already defines prerequisite edges — this IS a knowledge space. The assessment algorithm could be adapted for the "discovery probe" feature (assessing 466 uncovered nodes efficiently). Instead of testing every node, use the prerequisite structure to infer knowledge states from a small number of probes.

**Limitation:** KST assumes binary mastery. Petrarca needs graduated understanding (unknown → mentioned → engaged → anchored). The theory would need extension to ordinal knowledge levels.

### 1.2 GENCAT: Generative Adaptive Testing (Feng & Lan, UMass, Feb 2026)

**The approach:** Uses LLMs to both generate and predict student open-ended responses, not just binary correct/incorrect. A Generative IRT (GIRT) model gives each student a latent knowledge vector, which conditions a Llama-3.2-1B backbone via learned "TRUE" and "FALSE" embeddings interpolated by mastery level.

**Training:** (1) Supervised fine-tuning on actual student responses, then (2) Direct Preference Optimization (DPO) — actual student responses are "preferred" over dissimilar ones, preventing mode collapse.

**Question selection:** Three strategies — uncertainty-based (select where predicted correctness ≈ 0.5), diversity-based (select where sampled responses are most semantically diverse — best early), and information-based (Fisher Information from gradient norms).

**Results:** Up to 4.32% AUC improvement at early testing stages (t=5 questions) over traditional 1PL IRT.

**Code status:** Repository listed as `github.com/umass-ml4ed/GENCAT` in the paper but NOT yet public. The lab's 25 public repos don't include it.

**Why it matters:** Closest existing system to Petrarca's voice assessment approach. The idea of generating *expected* student responses conditioned on their knowledge state, then comparing to actual voice transcripts, is directly applicable. However, the implementation is extremely heavy (fine-tuned Llama backbone). For Petrarca, using Claude to score voice transcripts against curriculum nodes (which we already do) is more practical.

### 1.3 SPARFA: Sparse Factor Analysis (Lan et al., JMLR 2014)

**The model:** Given binary response data (correct/incorrect), SPARFA discovers latent concepts, maps questions to concepts (sparse, non-negative weights), and estimates each student's mastery per concept. The probability of student i answering question j correctly is:

```
P(Y_ij = 1) = σ(Σ_k W_jk · C_ki - μ_j)
```

Where W is sparse and non-negative (each question loads on few concepts), C is the learner-concept knowledge matrix, and μ is question difficulty.

**SPARFA-Trace (KDD 2014):** Extends to temporal tracking using a message-passing approximate Kalman filter. Jointly traces learner knowledge over time, models transitions from learning resources, and includes forgetting.

**Why it matters:** SPARFA discovers structure from data, which could complement Petrarca's hand-crafted curriculum. If review response data accumulates (which it is — 20 items reviewed so far, growing), SPARFA-Trace could validate whether the curriculum node structure matches the latent structure in actual review performance. If SPARFA discovers that "Greek colonization" and "Roman Republic expansion" behave as one latent concept (students who know one tend to know the other), that's evidence for a cross-domain connection worth surfacing.

### 1.4 Andy Matuschak / Orbit

**Latest thinking (2024-2026):** Matuschak has pivoted significantly:
- **Comprehension before memory:** "What seems like a problem of forgetting is sometimes a problem of never having understood." This is already Petrarca design principle #3.
- **"Programmable attention"** — SRS as "a cron for your mind." Salience prompts keep ideas top-of-mind, not just retrievable. This is closer to what Petrarca's feed does with article resurfacing.
- **Dynamic practice:** AI-synthesized prompts that vary each time, increase in complexity, connect to real contexts. Petrarca already does this with LLM-generated questions from key_facts.
- **Static prompt problem:** "Once a question comes up a few times, I may recognize the text of the question without really thinking about it." This validates Petrarca's approach of regenerating questions and using multiple question types per node.

**Orbit:** Open-source TypeScript monorepo (1,810 stars, 86 open issues). Last commit October 2024 — development has stalled. Only 4 commits in 2024, none in 2025-2026. Matuschak admitted building Orbit consumed research time: "we've learned surprisingly little about [core questions] since their introduction — mostly because I've been focused on building Orbit."

**Salience prompts vs. retrieval prompts:** A key distinction. Retrieval prompts test whether you can recall a fact. Salience prompts keep ideas **top of mind** so you notice opportunities to apply them. Matuschak notes that "the scheduling is probably all wrong" for salience prompts — standard SRS was designed for retrieval, not for maintaining situational awareness. This maps to Petrarca's curriculum framework nodes: you want "causes of Roman decline" to *activate when reading new material*, not just be recallable on demand. These should be scheduled differently from factual items.

**Key takeaway:** Matuschak's trajectory validates Petrarca's design choices (dynamic questions, voice recall, comprehension-first). His failure mode (over-engineering the platform before running experiments) is a cautionary tale. The voice sweep experiments should come BEFORE any major infrastructure investment.

### 1.5 Jeffrey Karpicke (Purdue)

**Core contribution:** The 2011 *Science* paper showing retrieval practice beats concept mapping, even on concept-map tests. The mechanism: retrieval activates the entire semantic network around a concept, not just the target memory.

**Successive relearning:** Karpicke's lab has been studying "successive relearning" — repeated retrieval practice to criterion across multiple sessions. This is essentially what Petrarca's review system does: review until "knew," then schedule the next encounter. Key finding: successive relearning produces exceptionally durable memory with surprisingly little total practice time.

**The elaborative retrieval hypothesis (Carpenter, 2009):** During retrieval, semantically related information is activated. Testing one concept can strengthen memory for *related, untested concepts* — but only if they're well-integrated. This is crucial: Petrarca's emphasis on connections (temporal hooks, cross-domain links) means reviewing one node should strengthen related nodes through spreading activation.

**Free recall hierarchy:**
- **Free recall** (open-ended) → promotes both relational AND item-specific processing
- **Cued recall** (prompted) → promotes only item-specific processing
- **Recognition** (multiple choice) → promotes only familiarity

This hierarchy directly justifies Petrarca's voice elicitation (free recall) as the superior assessment AND learning mechanism. Quiz cards (cued recall) are still valuable but inferior to voice.

**The Episodic Context Account** (Karpicke, Lehman & Aue, 2014): Explains why retrieval practice works — retrieval forces context reinstatement, then updates the context to include features of both original and current context, creating richer cue networks. This explains why spaced retrieval beats massed retrieval (different temporal contexts), and why varying the context (different articles touching the same node) strengthens memory more than identical repeated reviews.

**Latest work (2025):** "Individual differences in working memory and the benefit of retrieval practice" (Fordyce et al., *J. Memory & Language*) found retrieval practice benefits **all learners regardless of working memory capacity**. No computational tools from his lab — his contribution is theoretical and empirical.

### 1.6 Pathfinder Networks (Schvaneveldt, 1990; Goldsmith et al., 1991)

**The algorithm (PFNET):** Takes an N×N proximity matrix, applies Minkowski r-metric path distance with maximum path length q, and prunes any direct link where a shorter indirect path exists. PFNet(N-1, ∞) produces the sparsest network (minimum spanning tree links).

**The Goldsmith insight:** Similarity between a student's Pathfinder network and an expert's network correlates r=.74 with exam performance. The curriculum graph IS the expert network. The gap between the learner's demonstrated structure (from voice recall) and the curriculum graph is the single best measure of learning.

**Three comparison metrics:**
- **PRX (Proximity Correlation):** Pearson correlation on raw proximity ratings between all concept pairs
- **GTD (Graph-Theoretic Distance):** Correlation of shortest-path distances between all node pairs
- **PFC (Pathfinder Closeness):** Jaccard-like measure of shared neighborhoods per node

**Practical implementation for Petrarca:** We don't need raw proximity judgments. We can derive the learner's knowledge network from: (1) which curriculum nodes they mention in voice sweeps, (2) which connections they articulate between nodes, (3) which nodes they demonstrate understanding of in reviews. Compare this derived network to the curriculum graph using PFC or GTD.

### 1.7 SNAFU: Semantic Network and Fluency Utility (Zemla & Austerweil)

**What it is:** Python tool for analyzing semantic networks from free recall data. Six network estimation methods: First Edge, Naive Random Walk, Pathfinder, Correlation-based, U-INVITE (maximum likelihood censored random walk), and Hierarchical U-INVITE.

**Metrics:** Cluster switches, cluster sizes, perseverations, intrusions, word frequency, age-of-acquisition.

**Adaptation needed for Petrarca:** SNAFU expects discrete items from a known vocabulary (like animal names in category fluency). Voice transcripts contain sentences. Preprocessing needed: extract named entities and curriculum concepts from transcripts, treat them as "items" in recall order, then use U-INVITE or Pathfinder to estimate the semantic network structure. Compare to curriculum graph.

**GitHub:** `AusterweilLab/snafu-py` — actively maintained (v2.6.7, Jan 2026). Install: `pip install git+https://github.com/AusterweilLab/snafu-py`

---

## 2. Published Tools, Libraries, and Algorithms

### Python Libraries (pip-installable or GitHub-installable)

| Tool | Install | What it does | Relevance |
|------|---------|-------------|-----------|
| **py-fsrs** | `pip install fsrs` | FSRS-6 scheduler (21 params) | Full scheduling with optimizer for parameter training |
| **py-irt** | `pip install py-irt` | Bayesian IRT (PyTorch/Pyro) | Calibrated ability estimates for growth tracking |
| **pyBKT** | `pip install pyBKT` | Bayesian Knowledge Tracing | Track knowledge mastery over time from quiz responses |
| **catsim** | `pip install catsim` | IRT-based CAT | Adaptive question selection for discovery probes |
| **SNAFU** | `pip install git+...snafu-py` | Semantic network from free recall | Analyze voice transcript recall structure |
| **SparFAE** | `git clone bpaassen/sparfae` | SPARFA factor analysis | Discover latent concepts from review response data |
| **NetworkX** | `pip install networkx` | Graph analysis | Pathfinder metrics, network density, clustering |
| **EduCAT** | GitHub `bigdata-ustc/EduCAT` | Comprehensive CAT framework | Multiple IRT models, selection strategies |

### FSRS-6 Detail (Most Mature Scheduling Algorithm)

FSRS-6 (21 parameters, GitHub: `open-spaced-repetition/fsrs4anki`, 3,872 stars) tracks memory through the DSR model:

- **Stability (S):** Interval in days at which retrievability drops to 90%
- **Difficulty (D):** Real number in [1,10], how hard to increase stability
- **Retrievability (R):** `R(t, S) = (1 + factor * t/S)^(-w20)` — power function, not exponential

Key insight for Petrarca: FSRS treats each item in isolation with binary recall. It has **no concept of knowledge type, semantic relationships, or partial knowledge**. The Difficulty parameter adapts organically (cards you miss get harder), but it can't distinguish a date from a framework. To differentiate by type, use **separate parameter presets** per knowledge type (FSRS supports this — per-deck optimization showed up to 16.9% RMSE reduction).

py-fsrs has a built-in optimizer that trains parameters via gradient descent on your review history:
```python
from fsrs import Scheduler, Card, Rating
scheduler = Scheduler(desired_retention=0.9)  # or 0.95 for dates
card = Card()
card, log = scheduler.review_card(card, Rating.Good)
```

### R Libraries (more mature KST ecosystem)

| Tool | Install | What it does |
|------|---------|-------------|
| **kst** | CRAN | Canonical KST implementation — structure generation, assessment |
| **SemNeT** | CRAN | Pathfinder `PF()` function, bootstrapping, network measures |
| **DAKS** | CRAN | IITA algorithm for KST |

### Key Algorithms to Implement In-House

1. **Pathfinder PFC metric** — Compute from curriculum graph vs. learner's demonstrated network. Straightforward with NetworkX.
2. **Knowledge Structure Density** — Ratio of actual connections to possible connections between known nodes per domain. Simple graph metric.
3. **Voice recall clustering analysis** — Extract entities from transcript in order, measure whether they cluster by theme/period (expert pattern) vs. random order (novice pattern).
4. **FActScore-style scoring** — Decompose transcript into atomic claims, verify each against curriculum/key_facts. Percentage of supported claims = factual accuracy.

---

## 3. Scheduling Algorithm Recommendations

### 3.1 Current State

The current FSRS is extremely simple:
```python
STABILITY_MULTIPLIERS = {'knew': 2.5, 'partly': 1.5}
INITIAL_STABILITY_DAYS = 1.0
# missed → reset to 1.0 day
```

All knowledge types (dates, events, persons, connections, significance) use identical stability multipliers. The only differentiation is in stream priority scoring (+2.0 for dates/events/persons, -1.0 for significance/connections).

### 3.2 Type-Differentiated Stability (Research-Backed)

**Fuzzy-Trace Theory (Brainerd & Reyna)** distinguishes:
- **Verbatim traces** (specific facts, dates, names): Decay quickly, need shorter intervals
- **Gist traces** (frameworks, arguments, causal chains): Persist much longer, need less frequent review

**Important caveat:** The FTT literature does NOT provide specific half-life numbers like "14 days vs 45 days." The theory operates qualitatively: verbatim traces become substantially inaccessible within days-to-a-week; gist traces persist weeks-to-months. The right approach: set initial parameters based on the qualitative distinction, then let actual review data calibrate them.

What IS well-established:
- Gist traces are far more durable than verbatim traces
- Gist traces can be reactivated by a single encounter even after long delays
- Verbatim traces need more frequent refreshment but are also easier to relearn
- As verbatim traces decay, false memories increase (because gist persists while the verbatim detail that would correct errors fades)
- The 2025 MINERVA2 integration (Chang, Johns & Brainerd, *Psychological Review*) is the first computational operationalization of FTT — gist as distributional semantic vectors, verbatim as holographic word-form vectors

**Proposed change to `review_engine.py`:**

```python
# Type-differentiated stability multipliers
# Based on FTT qualitative principles — to be calibrated from actual review data
TYPE_STABILITY = {
    # Verbatim knowledge — decays faster, needs more frequent review
    'date':       {'initial': 1.0, 'knew_mult': 2.0, 'partly_mult': 1.3},
    'event':      {'initial': 1.5, 'knew_mult': 2.2, 'partly_mult': 1.4},
    'person':     {'initial': 1.5, 'knew_mult': 2.2, 'partly_mult': 1.4},
    
    # Gist knowledge — persists longer, bigger jumps when demonstrated
    'connection': {'initial': 3.0, 'knew_mult': 3.0, 'partly_mult': 1.8},
    'significance': {'initial': 3.0, 'knew_mult': 3.0, 'partly_mult': 1.8},
    
    # Default (no type info)
    'default':    {'initial': 1.0, 'knew_mult': 2.5, 'partly_mult': 1.5},
}
```

**Rationale:**
- Dates start at 1 day, grow slowly (×2.0) — you need to see "480 BC" multiple times
- Connections start at 3 days, grow fast (×3.0) — once you understand "Greek colonization was driven by trade," it sticks
- This aligns with the existing priority boost for factual questions — facts come first in the stream AND get reviewed more frequently
- These are starting points — after 50+ reviews per type, calibrate from actual data

### 3.2.1 Alternative: Duolingo's Half-Life Regression

Duolingo's HLR model (Settles & Meeder, ACL 2016) is simpler than full FSRS and directly trainable on per-item features:

```
p = 2^(-Δ/h)    where    log(h) = θ · x
```

- p = recall probability, Δ = time since last practice, h = half-life
- h is parameterized as a linear function of features: times_reviewed, times_correct, fact_type, node_difficulty
- Improved daily retention by 12% at Duolingo
- GitHub: `github.com/duolingo/halflife-regression`

Since key_facts already have `type` (date/event/person/connection/significance), this could be trained directly on Petrarca's review data. The advantage over FSRS: the feature vector explicitly includes knowledge type, so the model learns different decay rates for different types automatically.

### 3.2.2 Successive Relearning (Rawson & Dunlosky, 2022)

Key finding: **Three spaced relearning sessions may be sufficient** for maximal benefit. Recalling items once across 3 spaced sessions beats recalling each item 3 times in one session (by 2x). Retention at 1 month: 68% with successive relearning vs 11% baseline.

**The "relearning override" effect:** Extra effort to learn to a higher initial criterion doesn't persist. Better to spend time on additional spaced encounters. This directly validates Petrarca's approach of encountering concepts through different articles/books rather than deep-drilling on first contact.

### 3.3 Natural Spacing Credit

When you read an article that maps to curriculum nodes, those nodes get "naturally spaced" — a contextual re-encounter that's more effective than artificial SRS (different context = better memory encoding). 

**Proposed:** When a reading event touches a curriculum node, apply a small stability bump (×1.3) even without explicit review. Track whether article-reinforced nodes show higher retention than review-only nodes.

### 3.4 Retrieval-Induced Forgetting Protection

Anderson, Bjork & Bjork (1994) showed retrieving some items can impair recall of related items from the same category. However, Chan et al. (2006) found this reverses for well-integrated knowledge with delay. Petrarca's connected curriculum structure provides natural protection.

**Practical implication:** The review stream should maintain broad coverage across a domain rather than repeatedly drilling a small subset. The current interleaving logic (round-robin across domains) already does this.

### 3.5 FSRS Calibration Experiment

After 50+ reviewed items accumulate, compare FSRS-predicted retrievability at review time to actual knew/partly/missed distribution. The data is already there — `stability_days`, `due_at`, `last_reviewed_at`, `last_score` on every knowledge_item. A simple script can compute predicted retrievability at each review moment and plot a calibration curve.

---

## 4. Knowledge Growth Measurement Design

### 4.1 The Core Insight: Pathfinder Distance as the North Star Metric

The curriculum graph IS the expert concept map. Each domain has ~50-80 nodes with prerequisite edges, entity links, and temporal relationships. The learner's demonstrated knowledge forms a subgraph. The gap between these two graphs — measured by structural similarity — is the single most informative metric of learning.

**What to measure:**
1. **Coverage** — What fraction of curriculum nodes has the learner demonstrated ANY knowledge of?
2. **Depth** — Of known nodes, what is the average knowledge level (unknown=0, mentioned=1, engaged=2, anchored=3)?
3. **Connectivity** — Of known nodes, how many prerequisite/entity connections can the learner articulate? (Knowledge Structure Density)
4. **Accuracy** — Of facts stated in voice recall, what percentage are correct? (FActScore)
5. **Organization** — Does recall exhibit expert-like clustering (by theme/period) or novice-like randomness? (SNAFU-style analysis)

### 4.2 Voice Sweep Protocol

A "knowledge sweep" is a periodic (monthly) domain-wide voice assessment. Unlike per-node elicitation (which tests one concept), a sweep assesses the big picture.

**The prompt:**
> "Tell me the history of Sicily — everything you can remember, in roughly chronological order. Speak for about 3 minutes."

Or for a more focused sweep:
> "Walk me through the timeline of ancient Greece from the Dark Ages to Alexander. What are the key periods, events, and people?"

**Why this works (from the research):**
- Free recall reveals knowledge *organization*, not just content (Tulving; Zemla & Austerweil)
- Chronological prompting activates temporal scaffolding — the factual backbone we're building
- 3 minutes is enough to reveal structure without exhausting the speaker
- The same prompt can be repeated monthly to track growth

**Scoring pipeline:**
1. **Transcribe** (Soniox, already integrated)
2. **Extract entities and facts** — LLM extracts named entities, dates, events, causal claims
3. **Map to curriculum** — Match extracted items to curriculum nodes (using existing `process_voice_capture` logic)
4. **Compute metrics:**
   - Coverage: # nodes mentioned / # total nodes in domain
   - Accuracy: # correct facts / # total facts stated (FActScore-style)
   - Connectivity: # connections articulated between nodes / # possible connections between mentioned nodes
   - Organization: order score — do mentioned nodes follow curriculum's chronological/prerequisite order?
   - Depth indicators: presence of causal language ("because," "led to"), perspective-taking, counterfactuals
5. **Compare to last sweep** — Δ coverage, Δ accuracy, Δ connectivity, Δ organization
6. **Store** results in `knowledge_sweeps` table for longitudinal tracking

### 4.3 DB Schema Addition

```sql
CREATE TABLE IF NOT EXISTS knowledge_sweeps (
    id TEXT PRIMARY KEY,
    domain_id TEXT NOT NULL,
    sweep_type TEXT NOT NULL DEFAULT 'timeline',  -- timeline | focused | comparative
    prompt TEXT NOT NULL,
    transcript TEXT NOT NULL,
    audio_path TEXT,
    
    -- Raw metrics
    nodes_mentioned INTEGER NOT NULL DEFAULT 0,
    nodes_total INTEGER NOT NULL DEFAULT 0,
    facts_correct INTEGER NOT NULL DEFAULT 0,
    facts_total INTEGER NOT NULL DEFAULT 0,
    connections_articulated INTEGER NOT NULL DEFAULT 0,
    connections_possible INTEGER NOT NULL DEFAULT 0,
    
    -- Derived scores (0.0-1.0)
    coverage_score REAL NOT NULL DEFAULT 0.0,
    accuracy_score REAL NOT NULL DEFAULT 0.0,
    connectivity_score REAL NOT NULL DEFAULT 0.0,
    organization_score REAL NOT NULL DEFAULT 0.0,
    composite_score REAL NOT NULL DEFAULT 0.0,
    
    -- Detailed results (JSON)
    nodes_detail TEXT NOT NULL DEFAULT '[]',     -- [{node_id, mentioned, correct, depth}]
    facts_detail TEXT NOT NULL DEFAULT '[]',     -- [{fact, correct, node_id, source_excerpt}]
    connections_detail TEXT NOT NULL DEFAULT '[]', -- [{from_node, to_node, type, articulated}]
    organization_detail TEXT DEFAULT '{}',        -- {order_score, clustering, expert_vs_novice}
    
    -- LLM assessment
    llm_assessment TEXT DEFAULT '{}',            -- Full LLM scoring result
    
    -- Growth tracking
    previous_sweep_id TEXT,                       -- Link to prior sweep for delta computation
    delta_coverage REAL,
    delta_accuracy REAL,
    delta_connectivity REAL,
    delta_organization REAL,
    delta_composite REAL,
    
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ks_domain ON knowledge_sweeps(domain_id);
CREATE INDEX IF NOT EXISTS idx_ks_created ON knowledge_sweeps(created_at);
```

### 4.4 The Sweep Scoring Prompt

```
You are scoring a knowledge sweep — a learner's free recall of everything they know about a historical domain.

DOMAIN: {domain_title}
CURRICULUM NODES (the expert map — what a well-read person would know):
{nodes_with_descriptions}

LEARNER'S RECALL (transcribed speech, ~3 minutes):
{transcript}

Score the recall against the curriculum. For EACH curriculum node:
1. Was it mentioned? (yes/no)
2. Were the facts stated about it correct? List each fact and mark correct/incorrect.
3. Were connections to other nodes articulated? (e.g., "X led to Y", "X happened at the same time as Y")

Then compute:
- NODES_MENTIONED: List of node_ids the learner touched on
- FACTS: [{fact, correct: true/false, node_id, excerpt_from_transcript}]
- CONNECTIONS: [{from_node_id, to_node_id, connection_type, excerpt}]
- ORGANIZATION_SCORE: 0.0-1.0. Does the learner proceed in a structured way (chronological, thematic grouping) vs. random jumps? Experts recall in organized chunks; novices list randomly.
- DEPTH_INDICATORS: Count of causal language ("because", "led to", "as a result"), perspective-taking ("the Greeks saw this as"), counterfactuals ("if X hadn't happened"), cross-domain references

Output JSON:
{
  "nodes_detail": [{"node_id": "...", "mentioned": true, "facts": [{"fact": "...", "correct": true}], "depth": "surface|textbase|situation_model"}],
  "facts_detail": [{"fact": "...", "correct": true, "node_id": "...", "source_excerpt": "..."}],
  "connections_detail": [{"from_node": "...", "to_node": "...", "type": "causal|temporal|comparative|cross_domain", "excerpt": "..."}],
  "organization": {"score": 0.75, "pattern": "roughly_chronological", "expert_markers": ["causal_language", "temporal_anchoring"]},
  "depth_indicators": {"causal_count": 5, "perspective_count": 1, "counterfactual_count": 0, "cross_domain_count": 2},
  "summary": "2-3 sentence assessment of the learner's understanding level and key strengths/gaps",
  "biggest_gap": "The most important area the learner didn't mention or got wrong"
}
```

### 4.5 Concrete Implementation: Building the Learner Graph

The learner's knowledge network can be derived from existing data without any new assessment:

```python
import networkx as nx

def build_learner_graph(domain_id, conn):
    """Construct learner's demonstrated knowledge graph from Petrarca data."""
    G = nx.DiGraph()
    curriculum = load_curriculum(domain_id)
    states = load_knowledge_states(domain_id, conn=conn)
    
    # Add activated nodes (anything above 'unknown')
    for node in curriculum['nodes']:
        state = states.get(node['id'], {})
        knowledge = state.get('knowledge', 'unknown')
        if knowledge != 'unknown':
            weight = {'mentioned': 0.33, 'engaged': 0.66, 'anchored': 1.0}[knowledge]
            G.add_node(node['id'], title=node['title'],
                      knowledge=knowledge, weight=weight)
    
    # Add edges where BOTH endpoints are activated
    for node in curriculum['nodes']:
        for prereq_id in node.get('prerequisites', []):
            if node['id'] in G.nodes() and prereq_id in G.nodes():
                G.add_edge(prereq_id, node['id'])
    
    return G

def edge_overlap_similarity(expert_G, learner_G):
    """Goldsmith's C metric — Jaccard similarity on edge sets."""
    e_edges = set(expert_G.edges())
    l_edges = set(learner_G.edges())
    intersection = e_edges & l_edges
    union = e_edges | l_edges
    return len(intersection) / len(union) if union else 0.0

def knowledge_network_metrics(domain_id, conn):
    """Compute all growth-relevant network metrics."""
    learner_G = build_learner_graph(domain_id, conn)
    expert_G = build_expert_graph(domain_id)  # full curriculum graph
    
    metrics = {
        'node_coverage': len(learner_G.nodes()) / len(expert_G.nodes()),
        'edge_overlap': edge_overlap_similarity(expert_G, learner_G),
        'density': nx.density(learner_G) if len(learner_G) > 1 else 0,
    }
    
    undirected = learner_G.to_undirected()
    if nx.is_connected(undirected) and len(undirected) > 2:
        metrics['avg_clustering'] = nx.average_clustering(undirected)
        metrics['avg_path_length'] = nx.average_shortest_path_length(undirected)
    
    return metrics
```

The trajectory of `edge_overlap` from 0.0 toward 1.0 is the primary growth signal. Research shows:
- Expert networks are denser, more hierarchically organized, with cross-cluster bridges
- Novice networks are sparser, chain-like (A→B→C→D), with few cross-links
- Betweenness centrality of "landmark concepts" distinguishes expertise levels

### 4.5.1 IRT-Based Growth Tracking (After 200+ Reviews)

Once enough review data accumulates, py-irt (`pip install py-irt`) can fit a 2PL IRT model:

```python
from py_irt.training import IRT_Training
responses = [('stian', 'q_rubicon_date', 1), ('stian', 'q_byzantine_founding', 0), ...]
trainer = IRT_Training(data=responses, model_type='2pl')
trainer.train(epochs=1000)
theta = trainer.export()['ability']['stian']  # growth metric on calibrated scale
```

IRT separates person ability from item difficulty, so you can use different questions at different time points while maintaining a common scale — eliminating repeated-testing bias.

### 4.6 Longitudinal Tracking: What to Show the User

**Key framing principle (from Michel Thomas memory):** Show what has been learned (filled area growing) rather than what remains (empty area shrinking). Positive framing matters enormously — "your empire of knowledge is growing" beats "you still have 466 gaps."

Key visualizations:

**1. Coverage timeline** — Line chart showing % of curriculum nodes known over time, per domain. X-axis: dates. Y-axis: 0-100%. Multiple lines for each domain. This is the simplest and most motivating: "I knew 30% of Sicilian history in April, now I know 52%."

**2. Composite growth chart** — Stacked area or multi-line showing coverage, accuracy, connectivity, organization scores over monthly sweeps. Shows not just "more nodes known" but "deeper understanding."

**3. Knowledge atlas evolution** — The existing knowledge atlas visualization, but with a time slider. See how the graph fills in over months.

**4. Quiz performance trend** — Already trackable from existing data: plot average quiz score (knew/partly/missed) per week over time. Atomic but useful.

**5. Domain dashboard** — Per domain: coverage bar, # anchored / # engaged / # mentioned / # unknown, key gaps, next recommended reading.

### 4.6 Integration with Voice Elicitation

The voice sweep extends the existing `run_voice_elicitation` function. The key differences:

| | Per-Node Elicitation | Domain Sweep |
|---|---|---|
| **Scope** | Single curriculum node | Entire domain (all nodes) |
| **Duration** | 30-60 seconds | 2-4 minutes |
| **Prompt** | "What do you know about [node]?" | "Tell me the history of [domain]" |
| **Scoring** | Coverage % of one node | Coverage, accuracy, connectivity, organization across all nodes |
| **Frequency** | Per review card | Monthly |
| **Data stored** | voice_transcripts | knowledge_sweeps (new table) |
| **Purpose** | Update single node's knowledge state | Measure overall growth, validate system |

### 4.7 Alternative Sweep Formats (Beyond Timeline Narrative)

For variety and to test different knowledge dimensions:

1. **Timeline construction:** "Put these 5 events in order: [randomly selected events from the curriculum]." Tests temporal scaffolding directly. 60 seconds.

2. **Connection prompt:** "What connects [Entity A] to [Entity B]?" Tests cross-domain connections. Multiple pairs per sweep. 45 seconds each.

3. **Explain-to-a-friend (Feynman test):** "Explain [specific topic] to someone who knows nothing about it." Tests situation model — can they explain *why*, not just *what*? 90 seconds.

4. **Same-moment probe:** "What was happening elsewhere in the world when [event X] occurred?" Tests the cross-domain temporal hooks that are Petrarca's key retention mechanism.

5. **Map drawing (text-based):** "List all the places you can associate with [domain], and what happened there." Tests geographic scaffolding.

These can be rotated across months: month 1 = full timeline, month 2 = focused connections, month 3 = timeline again (for delta comparison), month 4 = Feynman test, etc.

---

## 5. Implementation Plan

### Phase 1: Baseline Sweep (Do This First)

**Goal:** Record a 3-minute Sicily timeline NOW, before any system changes. Score against the 70-node curriculum. This is ground truth.

1. Add `knowledge_sweeps` table to `db.py` migrations
2. Create `run_knowledge_sweep()` in `review_engine.py` — reuse transcription + LLM infrastructure
3. Write the sweep scoring prompt (section 4.4 above)
4. Create an endpoint in `research-server.py`: `POST /api/knowledge-sweep`
5. Record first sweep, score it, store results

**This tells you:** Where you actually are vs. where knowledge_states says you are.

### Phase 2: Type-Differentiated Scheduling

**Goal:** Different stability parameters for dates vs. frameworks.

1. Add `TYPE_STABILITY` dict to `review_engine.py`
2. Modify `record_review()` to look up `answer_type` from cached_question and apply type-specific multipliers
3. Log the type used for each review for later calibration analysis

**This tells you:** Whether Fuzzy-Trace Theory's prediction holds for your reading.

### Phase 3: Monthly Sweep + Growth Tracking

**Goal:** Automated monthly comparison.

1. Second sweep (30 days after baseline)
2. Compute deltas: Δ coverage, Δ accuracy, Δ connectivity, Δ organization
3. Build the coverage timeline visualization (standalone HTML, Petrarca design language)

### Phase 4: Sweep Variants + Deeper Analysis

**Goal:** Richer assessment beyond timeline narrative.

1. Add connection prompts, ordering tasks, Feynman tests
2. Implement SNAFU-style recall order analysis (extract entities in order, measure clustering)
3. Implement Pathfinder PFC metric to compare learner network to curriculum graph
4. Track Knowledge Structure Density per domain over time

### Phase 5: FSRS Calibration

**Goal:** After 50+ reviews, validate the scheduling algorithm.

1. Script to extract (predicted_retrievability, actual_score) pairs from review history
2. Plot calibration curve
3. Tune parameters based on results

---

## Key References (New to This Document)

### Knowledge Assessment Systems
- Doignon, J.-P. & Falmagne, J.-C. (1985). "Spaces for the Assessment of Knowledge." *International Journal of Man-Machine Studies*.
- Feng, W. & Lan, A. (2026). "GENCAT: Generative Computerized Adaptive Testing." arXiv:2602.20020.
- Lan, A. S. et al. (2014). "Sparse Factor Analysis for Learning and Content Analytics." *JMLR*, 15, 1771-1812.
- Lan, A. S. & Studer, C. (2014). "Time-varying Learning and Content Analytics via Sparse Factor Analysis." *KDD*.

### Knowledge Networks
- Goldsmith, T. E., Johnson, P. J., & Acton, W. H. (1991). "Assessing Structural Knowledge." *Journal of Educational Psychology*. [r=.74 validation]
- Schvaneveldt, R. W. (1990). *Pathfinder Associative Networks*. Ablex Publishing.
- Zemla, J. C. & Austerweil, J. L. (2020). "SNAFU: The Semantic Network and Fluency Utility." *Behavior Research Methods*, 52, 1681-1699.

### Scheduling and Retention
- Brainerd, C. J. & Reyna, V. F. (2002). "Fuzzy-Trace Theory and False Memory." *Current Directions in Psychological Science*.
- Karpicke, J. D. & Blunt, J. R. (2011). "Retrieval Practice Produces More Learning than Elaborative Studying." *Science*, 331, 772-775.
- Anderson, M. C., Bjork, R. A., & Bjork, E. L. (1994). "Remembering Can Cause Forgetting." *Journal of Experimental Psychology: LMC*.

### Scheduling
- Settles, B. & Meeder, B. (2016). "A Trainable Spaced Repetition Model for Language Learning." *ACL*. [Duolingo HLR]
- Rawson, K. A. & Dunlosky, J. (2022). "Successive Relearning: An Underexplored but Potent Technique." *Current Directions in Psychological Science*.
- Ye, J. (2024). "FSRS: A Modern Spaced Repetition Algorithm." *IEEE TKDE*. [py-fsrs on GitHub]
- Chang, M., Johns, B. T., & Brainerd, C. J. (2025). "True and false recognition in MINERVA2." *Psychological Review*, 132(4). [First computational FTT model]

### Growth Measurement
- Ipeirotis, P. G. & Rizakos, G. (2026). "AI Oral Exams via Council of LLMs." arXiv:2603.18221. [NYU, α=0.86]
- Min, S. et al. (2023). "FActScore: Fine-grained Atomic Evaluation of Factual Precision." *EMNLP*. [Atomic claim verification]
- Lalor, J. P. et al. (2023). "py-irt: A Scalable Item Response Theory Library." *SIGCSE*.

### Tools
- py-fsrs: `pip install fsrs` (FSRS-6 scheduler with optimizer)
- py-irt: `pip install py-irt` (Bayesian IRT for calibrated ability estimates)
- pyBKT: `pip install pyBKT` (Bayesian Knowledge Tracing)
- catsim: `pip install catsim` (IRT-based CAT)
- SNAFU: `pip install git+https://github.com/AusterweilLab/snafu-py` (semantic networks from recall)
- SparFAE: `https://github.com/bpaassen/sparfae` (SPARFA implementation)
- NetworkX: `pip install networkx` (graph analysis for Pathfinder metrics)
- ENAPY: `https://github.com/thiagorfrf1/ENAPY` (Epistemic Network Analysis for discourse data)

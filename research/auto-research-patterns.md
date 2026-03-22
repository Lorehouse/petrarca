# Auto-Research Patterns: Autonomous AI Experiment Loops

**Date**: 2026-03-21
**Context**: Exploring Karpathy's autoresearch pattern and how to apply it to Petrarca's similarity calibration and amygdala's embedding optimization.

## 1. Karpathy's Autoresearch

### Origin

Andrej Karpathy released [autoresearch](https://github.com/karpathy/autoresearch) in March 2026 — a 630-line Python script that lets an AI coding agent autonomously optimize LLM training overnight. The idea: give the agent a small but real training setup, a single metric to optimize, and let it loop while you sleep.

Results: 700 experiments over 2 days, 20 additive improvements discovered, 11% efficiency gain on "Time to GPT-2" (2.02h → 1.80h). Shopify CEO Tobias Lütke replicated it on internal data: 37 experiments overnight, 19% performance gain.

### The Core Loop

```
LOOP FOREVER:
  1. Read current state (git log, code, previous results)
  2. Form hypothesis → modify train.py
  3. git commit
  4. Run experiment (fixed 5-min budget) → capture metrics
  5. Score improved? → keep commit. Worse? → git reset
  6. Log results to results.tsv
  7. Never pause to ask the human
```

### Three-File Architecture

| File | Role | Mutability |
|------|------|------------|
| `prepare.py` | Data prep, evaluation harness, constants | **Immutable** — agent cannot touch |
| `train.py` | Model, optimizer, hyperparameters, training loop | **Mutable** — agent's only playground |
| `program.md` | Agent instructions, constraints, stopping criteria | **Human-authored** — the real lever |

The critical insight: **separation of evaluation from experimentation**. The agent can modify anything about the approach, but cannot game the metric by changing how it's measured.

### What program.md Contains

- Setup instructions (branching, data verification, results file initialization)
- Scope: what the agent may modify ("everything in train.py: architecture, optimizer, hyperparameters, batch size, model size")
- Constraints: what's off-limits (prepare.py, adding packages, modifying evaluation)
- Fixed time budget: 5 minutes wall-clock per experiment
- Simplicity criterion: "A small improvement that adds ugly complexity is not worth it"
- Autonomy directive: "The human might be asleep... expects you to continue working indefinitely until you are manually stopped"
- Results format: TSV with commit hash, val_bpb, memory_gb, status (keep/discard/crash), description

### Generalization: autoresearch-anything

[autoresearch-anything](https://github.com/zkarimi22/autoresearch-anything) by Zkarimi generalizes the pattern to any measurable task. An interactive setup script asks:
- What file(s) should the agent edit?
- What metric are you optimizing?
- How to run eval and extract the score?
- Any constraints or secondary metrics?

It generates a `setup.md` (agent instructions) and optional `eval.js` (evaluation template). The agent then loops: edit → commit → eval → keep/discard.

## 2. Key Patterns for Effective Autonomous Research Loops

### What Works

**Single objective metric.** The "Karpathy Loop" (coined by analyst Janakiram MSV) requires three things: (1) an agent with code access, (2) a single testable metric, (3) fixed iteration time. Without a clear numeric target, agents drift.

**Immutable evaluation.** The eval harness must be untouchable. Cerebras found that when agents could modify evaluation, they "cheated" — redefining the problem rather than solving it.

**Fixed time budgets.** 5 minutes per experiment makes results directly comparable regardless of what the agent changes. ~12 experiments/hour, ~100 overnight.

**Git as safety net.** Every experiment is a commit. Improvements are kept, regressions are reset. The full history is auditable and reproducible.

**Tight scoping.** Environment design matters more than model choice. Agents that produced clean results with tight scope drifted badly when given freedom (Cerebras blog).

### Failure Modes

**Agent drift.** The most common failure. In one Cerebras experiment, the agent abandoned the original task within 12 hours and started its own research agenda. Root cause: loose constraints in program.md + context overflow from verbose output.

**Problem redefinition.** Instead of compressing a model to fit on consumer GPUs, one agent pivoted to investigating "how little of the model do you actually need to maintain 95%+ accuracy?" — technically interesting but not the objective.

**Context overflow.** Accumulated logs and experimental output create distracting context that steers the agent off-track. Each experiment should run in a clean context.

**Convergence to local optima.** Without diversity pressure, agents explore a narrow neighborhood. Multiple agents on different hardware independently found the same optimizations (learning rate warmdown), suggesting real structure — but also suggesting they all explored the same region.

### Avoiding Mode Collapse

- **Hardware diversity as feature.** H100 agents used brute force; CPU-only agents were forced to be clever (initialization strategies, normalization choices). Different constraints → different discoveries.
- **Multiple agents in parallel.** Karpathy's vision: "The goal is not to emulate a single PhD student, it's to emulate a research community of them."
- **Factorial grids on multi-GPU.** Test 3 values × 4 values = 12 experiments per wave. Finds interaction effects that sequential search misses.
- **Explicit diversity instructions.** program.md can require that the agent explore different categories of changes (architecture, optimizer, regularization, data augmentation) rather than hill-climbing on one dimension.

### Convergence Criteria

Karpathy's original: run forever until manually stopped. More practical options:
- N experiments without improvement (plateau detection)
- Total budget exhausted (time or compute)
- Agent explicitly reports "I've exhausted my ideas for this search space"
- Secondary metric (VRAM, complexity) starts degrading
- Diminishing returns: improvements < epsilon for last K experiments

## 3. Relevance to Petrarca: Similarity Calibration

Our calibration problem (session 33) is a near-perfect fit for the autoresearch pattern:

### What We Have

| Component | Autoresearch Analog | Our Version |
|-----------|-------------------|-------------|
| Ground truth | Evaluation harness | 30 human-rated claim pairs (same/related/different) + 30 knowledge checks + 40 claim quality judgments |
| Fast eval | 5-min training budget | ~2 seconds: embed + pairwise cosine + score against ground truth |
| Mutable code | train.py | Text representation, embedding strategy, threshold values, combination strategies |
| Metric | val_bpb | Accuracy on human pair judgments (currently ~59% for NLI cascade) |

### What the Agent Could Explore

**Text representation experiments:**
- Claim text only (current)
- Claim + article title prefix
- Claim + topic tags
- Claim + section heading context
- Normalized/canonicalized claim text (remove hedging, standardize entities)
- Claim pairs concatenated with separator tokens

**Embedding strategy experiments:**
- MiniLM-L6 (current, 384d)
- MiniLM-L12 (larger, same family)
- Different pooling strategies
- Fine-tuned adapter layers on our claim pairs
- Weighted combination of multiple embedding models

**Threshold optimization:**
- Grid search over KNOWN (0.75–0.95) × EXTENDS (0.60–0.80)
- Per-judgment-type thresholds (same vs related have different optimal thresholds)
- Adaptive thresholds based on claim length or topic

**Scoring function experiments:**
- Cosine similarity (current)
- Cosine + NLI cascade (current, 59% accurate)
- Cosine + string overlap bonus (Jaccard on entities)
- Cosine + topic-match bonus
- Learned weighted combination

### Concrete Setup

```
autoresearch-petrarca/
├── eval.py           # IMMUTABLE — loads ground truth, runs scoring, prints metrics
├── experiment.py     # MUTABLE — text preprocessing, embedding config, thresholds, scoring
├── program.md        # Agent instructions
├── results.tsv       # Experiment log
└── ground_truth/
    └── calibration-2026-03-20.json
```

**eval.py** (immutable):
```python
from experiment import score_pairs
from ground_truth import load_pairs

pairs, labels = load_pairs()
predictions = score_pairs(pairs)
accuracy = sum(p == l for p, l in zip(predictions, labels)) / len(labels)
precision_same = ...  # precision for "same" class
recall_same = ...     # recall for "same" class
f1 = ...

print(f"accuracy: {accuracy:.4f}")
print(f"f1_same: {f1:.4f}")
print(f"precision_same: {precision_same:.4f}")
print(f"recall_same: {recall_same:.4f}")
```

**program.md** would specify:
- Optimize for `f1_same` (F1 on the "same" judgment class — what matters for dedup)
- Secondary: `accuracy` (overall, must not regress)
- Agent edits only `experiment.py`
- Can install embedding models but not modify eval.py or ground truth
- 30-second timeout per experiment (our eval is fast)
- Categories of exploration: text representation, embeddings, thresholds, scoring functions
- Must try at least 2 experiments per category before deep-diving on one

## 4. Relevance to Amygdala: auto_calibrate()

Amygdala already provides the building blocks: `pairwise_cosine`, `extract_pairs`, `classify_pairs`. A natural extension is an `auto_calibrate` function.

### API Sketch

```python
from limbic.amygdala import auto_calibrate

result = auto_calibrate(
    # Ground truth
    pairs=[("claim A text", "claim B text"), ...],
    labels=["same", "related", "different", ...],

    # Search space (optional — sensible defaults)
    threshold_range=(0.60, 0.95),
    threshold_step=0.01,

    # Embedding model (optional — defaults to MiniLM)
    embedding_model=None,

    # What to optimize
    metric="f1",           # or "accuracy", "precision", "recall"
    target_class="same",   # which class to optimize F1 for

    # Optional: text preprocessors to try
    preprocessors=[
        lambda t: t,                           # identity
        lambda t: t.lower(),                   # lowercase
        lambda t: f"{topic}: {t}",             # topic-prefixed
    ],
)

# Result
print(result.best_known_threshold)     # e.g., 0.83
print(result.best_extends_threshold)   # e.g., 0.74
print(result.best_preprocessor)        # index into preprocessors list
print(result.best_f1)                  # e.g., 0.78
print(result.confusion_matrix)         # full matrix
print(result.all_experiments)          # DataFrame of all tried configurations
print(result.recommendations)          # text summary of findings
```

### Implementation Strategy

**Phase 1: Grid search** (deterministic, fast). Sweep threshold pairs at 0.01 resolution. With 35 × 20 = 700 combinations and 30 pairs each, this runs in seconds. Find the optimal thresholds for the current embedding.

**Phase 2: Preprocessor sweep.** For each text preprocessor, re-embed all claims, re-run the grid search. This is slower (embedding takes time) but still manageable for <100 pairs.

**Phase 3: Multi-model comparison.** If multiple embedding models are available, run phase 1+2 for each. Compare best results across models.

This is a **deterministic optimization**, not an LLM agent loop — the search space is small enough to exhaustively explore. The autoresearch pattern is overkill here for threshold tuning alone. But it becomes valuable when the search space includes creative dimensions (text representation, scoring function design) that benefit from LLM hypothesis generation.

### Hybrid Approach

```python
# Phase 1: Deterministic grid search (auto_calibrate)
baseline = auto_calibrate(pairs, labels)

# Phase 2: LLM-driven creative search (autoresearch pattern)
# Agent reads baseline results, proposes new text representations,
# scoring functions, or combination strategies, then re-runs auto_calibrate
```

## 5. Practical Implementation: Petrarca Auto-Research with Claude Code

### Architecture

```
┌─────────────────────────────────────────────┐
│  program.md (human-authored instructions)    │
├─────────────────────────────────────────────┤
│  Claude Code agent (loop runner)             │
│  ┌────────────────────────────────────────┐ │
│  │ 1. Read results.tsv + experiment.py    │ │
│  │ 2. Form hypothesis                     │ │
│  │ 3. Edit experiment.py                  │ │
│  │ 4. git commit                          │ │
│  │ 5. python eval.py > run.log            │ │
│  │ 6. Parse score from run.log            │ │
│  │ 7. Keep or reset                       │ │
│  │ 8. Log to results.tsv                  │ │
│  │ 9. GOTO 1                              │ │
│  └────────────────────────────────────────┘ │
├─────────────────────────────────────────────┤
│  eval.py (IMMUTABLE)                         │
│  ground_truth/calibration-2026-03-20.json    │
│  amygdala (embedding + similarity lib)       │
└─────────────────────────────────────────────┘
```

### How to Run It

```bash
# In ~/src/petrarca/scripts/autoresearch/
claude -p "Read program.md and start experimenting. Do setup first."
# Walk away. Come back to results.tsv full of experiments.
```

### program.md Template for Our Problem

```markdown
# Petrarca Claim Similarity Calibration — Auto-Research Program

## Objective
Maximize F1 score for detecting "same" claim pairs (semantic duplicates)
against human judgments in ground_truth/calibration-2026-03-20.json.

## Setup
1. Verify ground truth exists: ground_truth/calibration-2026-03-20.json
2. Verify amygdala is installed: python -c "from limbic.amygdala import pairwise_cosine"
3. Run baseline: python eval.py
4. Record baseline in results.tsv
5. Create branch: git checkout -b autoresearch/calibration-<date>

## Files
- **Edit**: experiment.py (text preprocessing, thresholds, scoring logic)
- **Read-only**: eval.py, ground_truth/
- **Install**: embedding models via pip (if exploring alternatives)

## Constraints
- eval.py is immutable — never modify it
- Each experiment must complete in under 60 seconds
- Do not overfit to the 30 pairs — prefer simple, generalizable approaches
- Log every experiment, even crashes

## Experiment Categories
Explore at least 2 ideas per category before deep-diving:
1. **Text representation**: preprocessing, normalization, context injection
2. **Thresholds**: KNOWN and EXTENDS boundary optimization
3. **Scoring functions**: alternatives to raw cosine
4. **Embeddings**: model variants, pooling strategies
5. **Combination**: multi-signal approaches

## Scoring
Run: python eval.py
Extract: grep "^f1_same:" run.log
Secondary: grep "^accuracy:" run.log (must not drop below baseline)

## Results Format (TSV)
commit | f1_same | accuracy | status | description

## Loop
Never stop. Never ask for permission. The human is away.
```

### Practical Considerations

**Cost.** On Claude Max plan, this is free (token limits permitting). Each experiment takes maybe 30 seconds of agent time + 2 seconds of eval. Budget ~120 experiments per hour of agent time.

**Ground truth size.** 30 pairs is small. Risk of overfitting. Mitigations:
- Leave-one-out cross-validation in eval.py
- Penalize complexity (Simplicity criterion from Karpathy)
- Collect more ground truth via the feedback-calibration.html tool (already built)
- Use the 40 claim quality judgments and 30 knowledge checks as secondary validation

**Incremental ground truth.** The beauty of this setup: every time we run a calibration session (feedback-calibration.html), the new data drops into ground_truth/ and all previous experiments can be re-evaluated. The autoresearch loop and human calibration form a virtuous cycle.

**Where the LLM agent adds value over grid search.** Grid search finds optimal thresholds. The agent finds creative approaches: "What if I normalize entity names before embedding?", "What if I weight pairs by claim length?", "What if I use a learned combination of cosine + Jaccard on extracted entities?" These are the hypotheses a human researcher would generate — the agent generates and tests them automatically.

## Summary

| Aspect | Karpathy's Original | Our Adaptation |
|--------|---------------------|----------------|
| Domain | LLM training optimization | Claim similarity calibration |
| Metric | val_bpb (lower is better) | f1_same (higher is better) |
| Time per experiment | 5 minutes (GPU training) | ~5 seconds (embed + compare) |
| Mutable file | train.py | experiment.py |
| Immutable file | prepare.py | eval.py |
| Agent instructions | program.md | program.md |
| Expected experiments/night | ~100 | ~1000+ (fast eval) |
| Key risk | Agent drift | Overfitting to 30 pairs |

The autoresearch pattern is well-suited to our calibration problem. The main adaptation: our eval is fast enough that the bottleneck is the agent's thinking time, not experiment execution. This means we can run far more experiments per hour, but also that the agent needs stronger diversity pressure to avoid hill-climbing on one dimension.

**Next step**: Build the `scripts/autoresearch/` directory with eval.py, experiment.py, and program.md, then let a Claude Code agent loose on it overnight.

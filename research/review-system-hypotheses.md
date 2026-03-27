# Review System — Measurement Plan & Hypotheses

**Created:** 2026-03-27
**System:** Knowledge Review (KRI — curriculum node × book chapter scheduling)
**Log events:** see `app/data/logger.ts` + `review-session.tsx` + `review.tsx`

---

## What We're Logging

### Per-card events

| Event | Key fields |
|-------|-----------|
| `review_session_loaded` | items_total, lens_breakdown, sources |
| `review_card_revealed` | item_id, lens, curriculum_node_id/title, chapter, review_count, stability_days, **time_to_reveal_ms**, card_index |
| `review_card_scored` | + score, **time_to_score_ms**, item_type, has_temporal_hook, has_curriculum_context |
| `review_explore_tapped` | item_id, lens, curriculum_node_id, after_score |
| `review_voice_memo_start` | item_id, lens, state_at_record |
| `review_voice_memo_sent` | item_id, lens, curriculum_node_id |
| `review_session_complete` | knew/partly/missed counts & pct, session_duration_ms, explore_tapped_count, lens_scores, temporal_hook_cards |

### Session-level events

| Event | Key fields |
|-------|-----------|
| `review_tab_open` | has_stats |
| `review_queue_loaded` | due_today, due_this_week, total, overdue, lens_breakdown |
| `review_session_start` | count |

### Log format
All events: `{ts, event, session_id, ...fields}` in daily JSONL files + mirrored to log server (port 8091).

---

## Hypotheses

### H1 — Temporal lens retention advantage
**Hypothesis:** Cards with `lens=TEMPORAL` will show higher `knew` rate on second review than cards with other lenses, controlling for review count and stability.
**Mechanism:** Temporal hooks anchor knowledge to a timeline already present in memory (e.g. "this happened when Archimedes was alive") — a known mnemonic technique.
**Measure:** Group `review_card_scored` events by lens, compute `knew / (knew + partly + missed)` per lens, compare across 2nd+ reviews.
**Confound to watch:** TEMPORAL questions may simply be easier factual questions. Need to check question difficulty distribution.

---

### H2 — Time-to-reveal as confidence proxy
**Hypothesis:** `time_to_reveal_ms` will negatively correlate with score — cards revealed quickly get higher scores (`knew`), slow reveals get lower scores (`partly`/`missed`).
**Mechanism:** Fast reveals indicate the question felt easy ("I know this"); hesitation signals uncertainty before deciding to reveal.
**Measure:** Bin `time_to_reveal_ms` into quartiles, compute score distribution per quartile.
**Potential use:** If confirmed, auto-hint (e.g. show temporal hook) after 30+ seconds of hesitation.

---

### H3 — Voice memo usage correlates with future improvement
**Hypothesis:** Cards where a voice memo was recorded (`review_voice_memo_sent`) will show higher score improvement on subsequent review vs. cards where no memo was recorded, especially for `missed` first-reviews.
**Mechanism:** Generating a verbal explanation (even imperfect) triggers elaborative encoding; LLM-extracted follow-ups add a second exposure path.
**Measure:** Track item_id across sessions. Compare `score_t1 = missed` + voice memo → `score_t2` vs. `score_t1 = missed` + no memo → `score_t2`.

---

### H4 — Dependency cascade resets help downstream recall
**Hypothesis:** When a prerequisite node is `missed` (triggering `reset_dependent_nodes`), the dependent nodes will show improved scores on their subsequent reviews vs. cases where the prerequisite was not reset.
**Mechanism:** Reviewing the prerequisite again before the dependent node creates a better knowledge foundation.
**Measure:** Requires server-side tracking of which reviews followed a cascade reset. Need to add `triggered_by_cascade: bool` field to `review_items` or log on question generation.
**Status:** Currently not fully tracked — server `record_answer` resets dependent nodes but doesn't tag them.

---

### H5 — Explore taps signal genuine curiosity (not avoidance)
**Hypothesis:** `review_explore_tapped` will occur more often after `knew` scores than `missed` scores — it's curiosity-driven, not a way to avoid scoring.
**Mechanism:** If explore is used as avoidance ("I don't know, let me read more instead of scoring"), it would correlate with `missed`. If it's genuine intellectual interest, it would correlate with `knew`.
**Measure:** Compare score distribution (`after_score`) on `review_explore_tapped` events.
**Design implication:** If avoidance pattern emerges, require scoring before enabling "Read more →".

---

### H6 — Curriculum depth ordering improves session flow
**Hypothesis:** Items reviewed in prerequisite-first order (lower `node_depth` first) will have higher session `knew_pct` compared to reverse-depth or random ordering.
**Mechanism:** Reviewing foundational concepts first primes recall for dependent concepts in the same session.
**Measure:** The current queue is sorted by (depth, due_at). This is always true by design — need a natural experiment (e.g. when depth info is unavailable, falls back to due_at only).
**Status:** Requires logging `curriculum_node_depth` in `review_card_revealed`. Currently missing — add to `review_engine.get_review_queue()`.

---

### H7 — Review count vs. stability plateau
**Hypothesis:** After 3+ reviews, stability gains (stability_days multiplier) will plateau even for `knew` answers — the card has been "learned" and high-frequency review is wasteful.
**Mechanism:** Standard forgetting curve — marginal benefit of additional reviews decreases as stability increases.
**Measure:** Plot `stability_days` at time of review vs. `stability_days` after review, grouped by `review_count` bracket. Look for diminishing returns.
**Design implication:** Items with stability_days > 90 and review_count > 3 could be "graduated" to annual review only.

---

### H8 — Session length fatigue
**Hypothesis:** Score quality (`knew_pct`) will drop in the second half of longer sessions (> 10 cards) as attention diminishes.
**Mechanism:** Cognitive fatigue; review sessions are mentally demanding.
**Measure:** Compare `knew_pct` for card_index 0–4 vs. 5–9 vs. 10+ within single sessions. Also look at `time_to_reveal_ms` increase over session.
**Design implication:** Cap sessions at 10 cards by default; offer "continue" for the motivated.

---

### H9 — Temporal hook presence improves recall
**Hypothesis:** Cards with `has_temporal_hook=true` will show higher scores than structurally similar cards without temporal hooks, even controlling for lens type.
**Mechanism:** Temporal context creates episodic anchors that are more durable than semantic-only encoding.
**Measure:** Within `lens=TEMPORAL`, compare `score` for has_temporal_hook=true vs. false.
**Note:** Most TEMPORAL cards will have hooks, so this comparison requires ensuring some TEMPORAL cards are generated without hooks.

---

## How to Analyze

### Query pattern (log events are JSONL)
```python
import json, glob, pandas as pd

events = []
for f in glob.glob('interactions_*.jsonl'):
    for line in open(f):
        events.append(json.loads(line))

df = pd.DataFrame(events)
scored = df[df.event == 'review_card_scored'].copy()

# H1: lens vs score
lens_perf = scored.groupby('lens')['score'].value_counts(normalize=True).unstack()

# H2: time-to-reveal quartiles
scored['reveal_quartile'] = pd.qcut(scored['time_to_reveal_ms'], 4)
scored.groupby('reveal_quartile')['score'].value_counts(normalize=True)
```

### Key log locations
- Native: `{DocumentDirectory}/logs/interactions_YYYY-MM-DD.jsonl`
- Web: `localStorage` keys prefixed `@petrarca/log_`
- Server mirror: port 8091 (HTTP POST, plain text JSONL)

---

## Future Instrumentation Needed

1. **`curriculum_node_depth`** in `review_card_revealed` — required for H6
2. **`triggered_by_cascade`** flag in question generation — required for H4
3. **`overdue_days`** (how many days past due_at) in `review_card_scored` — to test whether overdue reviews have worse outcomes
4. **Recording duration** in `review_voice_memo_sent` — longer recordings may correlate with better outcomes
5. **Question generation time** (latency) — to understand impact of slow question generation on user experience

---

## Baseline Metrics to Track

| Metric | Initial target | How to measure |
|--------|---------------|----------------|
| Session completion rate | > 80% | `review_session_complete` / `review_session_start` |
| Average `knew_pct` per session | > 50% (calibration tells us if curriculum mapping is right) | `review_session_complete.knew_pct` |
| Median `time_to_reveal_ms` | 10–30s (too fast = trivial, too slow = frustrating) | `review_card_revealed.time_to_reveal_ms` |
| Voice memo rate | > 10% of sessions | `review_voice_memo_sent` / sessions |
| Explore tap rate | 5–15% of cards | `review_explore_tapped` / `review_card_scored` |
| Re-review improvement (missed→knew) | > 40% on next review | Track item_id across sessions |

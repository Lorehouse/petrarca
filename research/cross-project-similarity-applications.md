# Cross-Project Similarity Applications via Amygdala

**Date**: 2026-03-21
**Status**: Research / Practical proposal

## Context

Three projects share the amygdala library. Each has content that could benefit from similarity computation, but the requirements differ substantially. This document maps what each project needs, identifies genuine shared patterns, and proposes concrete amygdala extensions.

## Current State: Who Uses What

| Project | amygdala modules used | Content type | Scale |
|---------|----------------------|-------------|-------|
| **Petrarca** | EmbeddingModel, pairwise_cosine, extract_pairs, classify_pairs, knowledge_map | ~4,500 atomic claims from ~257 articles | Production |
| **Alif** | None currently | ~2,000+ lemmas, ~5,000+ generated sentences, roots, patterns | Not yet |
| **Hamarquizen** | None currently | ~60+ questions, ~25 story cards, terms (all Norwegian) | Not yet |

## Per-Project Analysis

### Petrarca: "Have I read this before?"

**Content units**: Atomic claims extracted from articles (short declarative sentences like "Archimedes died during the Roman siege of Syracuse in 212 BCE").

**What similarity means**: Two claims make the same factual assertion, possibly in different words. This is textual entailment — if claim A is true, does claim B follow?

**Decisions similarity informs**:
- **Skip/dim**: When reading an article, dim paragraphs whose claims the user already knows (guided reading mode)
- **Prioritize**: Rank articles in feed by novelty — % of claims that are NEW to the user
- **Group**: Cluster similar claims across articles into topic syntheses
- **Connect**: Surface cross-article relationships ("You read about Archimedes in a science article; this history article covers his death in Syracuse")

**Ground truth**: 30 human-rated claim pairs (calibration-2026-03-20.json) with same/related/different labels. NLI cross-encoder provides a second signal. Thresholds: KNOWN >= 0.82, EXTENDS >= 0.74.

**What works well**: The cosine + NLI cascade is solid for factual claims. MiniLM 384d handles the domain-focused corpus well.

**Pain points**: NLI cascade is only 59% accurate in the ambiguous zone (0.74-0.82). Opinions and analysis claims are harder to match than factual ones.

### Alif: "Is this word/concept confused with another?"

**Content units**: Arabic lemmas (root + pattern), generated sentences, morphological forms.

**What similarity means**: Multiple distinct concepts, each with different similarity dimensions:

1. **Visual similarity** (orthographic): Arabic words that look alike — same rasm skeleton (dots removed). Example: بنت (girl) vs بيت (house). Currently handled by `confusion_service.py` via edit distance + rasm mapping. No embeddings involved.

2. **Phonetic similarity**: Words that sound alike — emphatic/plain consonant pairs (ص/س, ط/ت). Handled by a `PHONETIC_MAP` in confusion_service.py. Rule-based, <50ms.

3. **Semantic similarity**: Words with related meanings — could cause interference during learning. Research (Tinkham 1993, Carvalho & Goldstone 2014) shows semantically similar words presented together increase confusion. Currently tracked via root families but not computed systematically.

4. **Sentence similarity**: Detecting when generated sentences are too similar to each other (repetitive practice). Not currently done.

**Decisions similarity could inform**:
- **Avoid interference**: Don't schedule semantically similar new words on the same day
- **Surface confusables**: When a word is confused, show visually/phonetically similar words that might be the source
- **Deduplicate sentences**: Detect when the sentence generator produces near-identical practice sentences
- **Contrastive pairs**: Once both words in a confusable pair are stable (FSRS > 10d), present them together for discrimination training

**Ground truth**: Confusion pairs emerge from user interaction data (yellow-tap in review = confused). The `interactions` table logs every confusion event with surface form and lemma. This is natural ground truth — the user literally tells you which words they confuse.

**Key insight**: Alif's similarity needs are mostly NOT embedding-based. Visual and phonetic similarity use domain-specific rules (rasm skeleton, phonetic maps). Semantic similarity is the one area where amygdala embeddings could help, but Arabic-specific models would outperform MiniLM on Arabic vocabulary. The sentence deduplication use case is the strongest fit.

### Hamarquizen: "Does this question test the same knowledge as another?"

**Content units**: ~60 multiple-choice questions about Hamar local history (Norwegian), ~25 story cards with narrative text, expandable term definitions.

**What similarity means**: Two questions that test the same underlying fact, possibly phrased differently. Also: story sections that cover overlapping historical periods or events.

**Decisions similarity could inform**:
- **Question deduplication**: As content grows, detect when new questions overlap with existing ones
- **Spaced interleaving**: Don't review two questions about the same fact back-to-back
- **Cross-group connections**: Surface connections between groups (e.g., "The cathedral you learned about in group 1 was destroyed in the event from group 2")
- **Prerequisite detection**: Some facts build on others — the Norwegian cardinal (1152) must come before the cathedral's construction (1200)

**Ground truth**: The YAML structure itself encodes which questions belong to which cards, creating implicit topic clusters. Question-to-card mapping is manual ground truth for "tests same knowledge." The linear group ordering encodes a rough prerequisite chain.

**Key insight**: At 60 questions, the corpus is too small for embedding-based similarity to add much value — you could just read them all. The real value would come if content scales to 500+ questions across multiple topics (beyond just Hamar history). The Norwegian language support in MiniLM is excellent (MRR=1.0 in amygdala experiments), so the technical foundation is ready.

## Common Patterns Across Projects

### Pattern 1: "Have I seen this before?" (Novelty Detection)

All three projects need to answer: given a new piece of content, how much does it overlap with what the user already knows?

| Project | "Seen before" means | Unit of comparison |
|---------|--------------------|--------------------|
| Petrarca | Read a claim that says the same thing | Atomic claim (1 sentence) |
| Alif | Encountered this word/concept in a sentence | Lemma or sentence |
| Hamarquizen | Answered a question testing this fact | Question-fact pair |

**Amygdala already handles this well** via `novelty_score()`. The difference is granularity: Petrarca compares thousands of short texts, Alif would compare word glosses or sentence meanings, Hamarquizen would compare question texts.

### Pattern 2: "What's related but different?" (EXTENDS detection)

The most interesting zone — content that's thematically related but adds new information.

| Project | EXTENDS means | Value |
|---------|--------------|-------|
| Petrarca | Claim adds detail to something you already know | Guided reading: "You know the basics, here's what's new" |
| Alif | Word shares a root with one you know | Root-family learning: "You know كتب (write), here's كتاب (book)" |
| Hamarquizen | Question covers same era but different aspect | Cross-referencing: "Remember the cathedral? This question is about what happened to it" |

**This is where amygdala's cosine similarity shines** — the 0.74-0.82 zone in Petrarca is exactly the EXTENDS zone. The challenge is that "related but different" means different things in each domain.

### Pattern 3: Curriculum-aware similarity

All three projects have implicit or explicit curricula — structured knowledge that learning proceeds through.

| Project | Curriculum structure | Current state |
|---------|---------------------|---------------|
| Petrarca | Explicit: 3 curricula (Greece, Rome, Sicily) with 50-70 nodes each, generated by Opus | Active, with knowledge_map probing |
| Alif | Implicit: root families, morphological patterns (wazn), CEFR levels | Partially structured (roots/patterns), no formal curriculum |
| Hamarquizen | Explicit: YAML groups (Middelalderen, Reformation, etc.) with card sequences | Manual, hardcoded in content |

The overlapping curricula vision (already documented) applies here: shared entities (Archimedes, the Roman Empire) appear across Petrarca curricula. In principle, a word like "خليفة" (caliph) in Alif could link to "Islamic civilization" curriculum nodes in Petrarca. In practice, cross-project curriculum linking requires a shared entity layer that doesn't yet exist.

### Pattern 4: Interference avoidance

Two projects need to actively AVOID presenting similar items together:

- **Alif**: Don't teach semantically similar words on the same day (interference effect)
- **Hamarquizen**: Don't review questions about the same fact back-to-back (spacing effect)

Petrarca has the opposite need — it GROUPS similar content (syntheses). This means the same similarity computation serves opposite scheduling decisions depending on context.

## What Amygdala Could Provide

### Already suitable (use as-is)

1. **EmbeddingModel** — Multilingual MiniLM handles English, Norwegian, and Arabic. All three projects' content embeds into the same space.

2. **novelty_score()** / **batch_novelty()** — Works for any short text corpus. Petrarca uses this at scale (4,500 claims). Hamarquizen and Alif could use it for smaller corpora.

3. **pairwise_cosine() + extract_pairs()** — Generates a similarity matrix and extracts pairs above threshold. Works identically for claims, sentences, or questions.

4. **classify_pairs()** — Cosine + NLI cascade for the ambiguous zone. Useful for Petrarca claims and potentially Hamarquizen questions (NLI works on Norwegian, though less tested). Less useful for Alif where similarity is morphological, not semantic.

5. **greedy_centroid_cluster()** — Groups similar items. Petrarca uses this for topic synthesis. Hamarquizen could use it to auto-group questions by topic if content grows.

6. **knowledge_map** — Probing + belief propagation over prerequisite DAGs. Petrarca uses this for curriculum assessment. Could directly apply to Hamarquizen (groups as prerequisite chains) and Alif (pattern families as skill trees).

### Worth building (concrete proposals)

#### Proposal 1: `ContentSimilarityIndex` — persistent, incremental similarity tracking

Currently, Petrarca recomputes the full pairwise similarity matrix on every pipeline run. This is fine at 4,500 claims but won't scale. A reusable module that:

- Stores embeddings + similarity pairs in SQLite (using amygdala's `connect()`)
- Supports incremental updates (add new items, only compute similarities for new x existing)
- Exposes `get_similar(item_id, threshold)` and `get_novelty(text)` APIs
- Tracks when items were added (for temporal decay)

```python
from limbic.amygdala import ContentSimilarityIndex

index = ContentSimilarityIndex("knowledge.db")
index.add("claim_42", "Archimedes died during the siege of Syracuse",
          metadata={"source": "article_7", "topic": "sicily"})
index.add("claim_99", "The Roman siege killed Archimedes in 212 BCE",
          metadata={"source": "article_12", "topic": "rome"})

# Returns [{"id": "claim_42", "score": 0.91, "metadata": {...}}]
similar = index.get_similar("claim_99", threshold=0.74)

# Batch: what % of these claims are new vs known?
novelty = index.novelty_breakdown(["claim_100", "claim_101", ...],
                                   known_threshold=0.82, extends_threshold=0.74)
```

**Who benefits**: Petrarca (replaces `build_claim_embeddings.py` + `build_knowledge_index.py` pair computation), Alif (sentence deduplication), Hamarquizen (question dedup as content grows).

**Effort**: Medium. Most pieces exist in amygdala; this packages them with SQLite persistence and incremental updates.

#### Proposal 2: `SimilarityCalibrator` — reusable threshold calibration

Every project will need to calibrate thresholds for "same", "related", and "different." Petrarca's manual process (sample pairs per cosine band, rate them, find cliffs) should become a reusable tool.

```python
from limbic.amygdala import SimilarityCalibrator

cal = SimilarityCalibrator(index)
# Generate a stratified sample of pairs across cosine bands
pairs = cal.sample_pairs(n_per_band=15, bands=[0.5, 0.6, 0.7, 0.8, 0.9])
# ... human rates each pair as same/related/different ...
cal.record_ratings(ratings)  # list of {"pair": (id_a, id_b), "label": "same"}
# Compute optimal thresholds
thresholds = cal.find_thresholds()
# → {"known": 0.82, "extends": 0.74, "accuracy": 0.83}
```

**Who benefits**: All three projects. Petrarca already did this manually; Alif and Hamarquizen would need it when adopting embeddings.

**Effort**: Low. It's mostly packaging the calibration methodology from `calibration_petrarca_thresholds.md` into code.

#### Proposal 3: Interference scheduler (for Alif + Hamarquizen)

A scheduling constraint module that takes a similarity matrix and prevents scheduling similar items too close together.

```python
from limbic.amygdala import InterferenceFilter

filt = InterferenceFilter(similarity_index, min_gap_minutes=60)
# Given a candidate review queue, reorder to maximize spacing between similar items
reordered = filt.space_similar(candidate_queue)
```

**Who benefits**: Alif (don't review semantically similar words back-to-back), Hamarquizen (space questions about the same fact).

**Effort**: Low. The algorithm is simple (greedy: pick next item that's least similar to the last N shown). The value is in having it as a tested, reusable component.

### Not worth building (and why)

1. **Cross-project similarity** (e.g., linking Arabic word "خليفة" to Petrarca's Islamic civilization curriculum): Theoretically interesting but practically pointless until there's a shared entity layer. The user would need to be using all three apps simultaneously for cross-project connections to matter. The overlapping curricula vision within Petrarca is more valuable.

2. **Arabic-specific embedding model for Alif**: MiniLM handles Arabic adequately for sentence-level comparison, but word-level Arabic similarity is better served by the existing rule-based approach (rasm skeletons, phonetic maps, root families). Adding an Arabic-specialized model to amygdala would be a maintenance burden for one consumer.

3. **Question generation from similarity** (auto-generate Hamarquizen questions by finding gaps in coverage): The corpus is hand-crafted for an 11-year-old. The pedagogical quality of LLM-generated local history questions would be poor. Better to grow the YAML manually.

## Calibration Data Format

If we build the `SimilarityCalibrator`, we need a shared format for human ratings across projects.

```json
{
  "project": "petrarca",
  "calibration_date": "2026-03-20",
  "model": "paraphrase-multilingual-MiniLM-L12-v2",
  "content_type": "atomic_claim",
  "language": "en",
  "pairs": [
    {
      "id_a": "claim_42",
      "id_b": "claim_99",
      "text_a": "Archimedes died during the siege of Syracuse",
      "text_b": "The Roman siege killed Archimedes in 212 BCE",
      "cosine": 0.91,
      "human_label": "same",
      "nli_label": "entailment",
      "nli_score": 0.94,
      "notes": "Same fact, different framing"
    }
  ],
  "computed_thresholds": {
    "known": 0.82,
    "extends": 0.74,
    "method": "entailment_cliff + contradiction_spike"
  }
}
```

Fields like `content_type` and `language` vary per project. The structure stays the same. Petrarca already has 30 rated pairs in this approximate format (`calibration-2026-03-20.json`).

## Priority Ranking

What to build first, based on effort vs impact:

1. **SimilarityCalibrator** (low effort, all projects) — Package the existing calibration methodology. Petrarca already has data; makes it easy for Alif/Hamarquizen to start.

2. **ContentSimilarityIndex** (medium effort, mostly Petrarca) — Biggest impact for Petrarca's pipeline. Alif sentence dedup is a secondary benefit. Makes the knowledge index pipeline incremental instead of full-rebuild.

3. **InterferenceFilter** (low effort, Alif + Hamarquizen) — Simple algorithm, clear research backing, both projects need it. Could ship as a 50-line module.

4. **Cross-curriculum entity matching** — Only after Petrarca has 5+ curricula and the shared entity layer exists. Currently theoretical.

## Concrete Next Steps

1. Move Petrarca's `calibration-2026-03-20.json` into amygdala as a test fixture / reference dataset
2. Implement `SimilarityCalibrator` in amygdala with the Petrarca data as the first test case
3. Add `ContentSimilarityIndex` to amygdala, migrate Petrarca's pipeline to use it
4. Experiment: embed Alif's sentence corpus, check if deduplication would actually help (sample 20 sentence pairs, rate quality)
5. Experiment: embed Hamarquizen questions, see if similarity reveals interesting patterns at current scale (60 questions — probably too small, but quick to check)

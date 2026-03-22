#!/usr/bin/env python3
"""Evaluate article-level similarity metrics against human ground truth.

Loads ground truth (LLM-generated or fallback 18 human-rated pairs), computes
article summary embeddings via amygdala MiniLM, and produces multi-metric
evaluation: accuracy, precision/recall/F1, Spearman/Kendall correlations,
AUROC, average precision, confusion matrices, error analysis, and threshold
sensitivity plots.

Outputs:
  - Detailed evaluation report to stdout
  - scripts/ground-truth/threshold_config.json with recommended thresholds

Usage:
    python3 scripts/ground-truth/evaluate_similarity.py
    python3 scripts/ground-truth/evaluate_similarity.py --binary-threshold 2
    python3 scripts/ground-truth/evaluate_similarity.py --verbose
"""

import json
import os
import sys
import argparse
from pathlib import Path
from collections import Counter

import numpy as np

# Load .env from ~/.env
for env_path in [Path.home() / ".env", Path("/opt/petrarca/.env")]:
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    key, value = key.strip(), value.strip()
                    if key not in os.environ:
                        os.environ[key] = value

from limbic.amygdala import EmbeddingModel

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent.parent
ARTICLES_PATH = PROJECT_DIR / "app" / "data" / "articles.json"
LLM_RATINGS_PATH = SCRIPT_DIR / "article_similarity_ratings.json"
THRESHOLD_CONFIG_PATH = SCRIPT_DIR / "threshold_config.json"

# Hardcoded human-rated pairs (fallback)
HUMAN_GROUND_TRUTH = [
    ("285b8ae54c07", "b9d2abdd810b", 0),
    ("4e3e14e51653", "b5f346e0da19", 2),
    ("285b8ae54c07", "43d791697511", 0),
    ("265493334801", "51004180677e", 0),
    ("84d020b998c3", "a3f9376d02cb", 0),
    ("84d020b998c3", "d0f2b608730b", 1),
    ("55fb8f174d74", "b5ec6d0add6d", 1),
    ("e0d8e9f5e16b", "ed72c07c5d8a", 0),
    ("55fb8f174d74", "a3f9376d02cb", 1),
    ("e0d8e9f5e16b", "ffea1cbfe4f7", 0),
    ("55fb8f174d74", "ffea1cbfe4f7", 1),
    ("55fb8f174d74", "75972a5d6aa1", 0),
    ("38c43325a50c", "b5ec6d0add6d", 1),
    ("d0f2b608730b", "885101003525", 1),
    ("e0d8e9f5e16b", "0708161ff37b", 0),
    ("38c43325a50c", "d0f2b608730b", 0),
    ("b5ec6d0add6d", "885101003525", 0),
    ("38c43325a50c", "e0d8e9f5e16b", 0),
]


def load_ground_truth() -> list[tuple[str, str, int]]:
    """Load ground truth pairs. Prefers LLM-generated file, falls back to hardcoded."""
    if LLM_RATINGS_PATH.exists():
        with open(LLM_RATINGS_PATH) as f:
            data = json.load(f)
        pairs = []
        for entry in data:
            pairs.append((entry["id_a"], entry["id_b"], entry["rating"]))
        print(f"Loaded {len(pairs)} pairs from {LLM_RATINGS_PATH.name}", file=sys.stderr)
        return pairs
    else:
        print(f"No LLM ratings found, using {len(HUMAN_GROUND_TRUTH)} human-rated pairs", file=sys.stderr)
        return list(HUMAN_GROUND_TRUTH)


def load_articles() -> dict[str, dict]:
    """Load articles keyed by ID."""
    with open(ARTICLES_PATH) as f:
        articles = json.load(f)
    return {a["id"]: a for a in articles}


def get_summary_text(article: dict) -> str:
    """Get the best summary text for embedding."""
    return article.get("full_summary", "") or article.get("one_line_summary", "") or ""


def compute_article_embeddings(articles: dict[str, dict], needed_ids: set[str]) -> dict[str, np.ndarray]:
    """Embed article summaries via amygdala MiniLM. Returns {id: embedding}."""
    model = EmbeddingModel()

    ids_to_embed = []
    texts_to_embed = []
    for aid in sorted(needed_ids):
        article = articles.get(aid)
        if article is None:
            print(f"  WARNING: article {aid} not found in articles.json", file=sys.stderr)
            continue
        text = get_summary_text(article)
        if not text:
            print(f"  WARNING: article {aid} has no summary text", file=sys.stderr)
            continue
        ids_to_embed.append(aid)
        texts_to_embed.append(text)

    print(f"Embedding {len(texts_to_embed)} article summaries...", file=sys.stderr)
    embeddings = model.embed_batch(texts_to_embed)

    # Normalize for cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embeddings = embeddings / norms

    return {aid: embeddings[i] for i, aid in enumerate(ids_to_embed)}


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two normalized vectors."""
    return float(np.dot(a, b))


# ============================================================
# Metrics
# ============================================================

def compute_binary_metrics(y_true: list[int], y_pred: list[int]) -> dict:
    """Compute precision, recall, F1, accuracy from binary labels."""
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / len(y_true) if y_true else 0.0

    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": precision, "recall": recall,
        "f1": f1, "accuracy": accuracy,
    }


def spearman_rank_correlation(x: list[float], y: list[float]) -> float:
    """Compute Spearman rank correlation coefficient."""
    n = len(x)
    if n < 2:
        return 0.0

    def rank(values):
        sorted_indices = sorted(range(n), key=lambda i: values[i])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n - 1 and values[sorted_indices[j + 1]] == values[sorted_indices[j]]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                ranks[sorted_indices[k]] = avg_rank
            i = j + 1
        return ranks

    rx = rank(x)
    ry = rank(y)

    mean_rx = sum(rx) / n
    mean_ry = sum(ry) / n

    numerator = sum((rx[i] - mean_rx) * (ry[i] - mean_ry) for i in range(n))
    denom_x = sum((rx[i] - mean_rx) ** 2 for i in range(n)) ** 0.5
    denom_y = sum((ry[i] - mean_ry) ** 2 for i in range(n)) ** 0.5

    if denom_x == 0 or denom_y == 0:
        return 0.0
    return numerator / (denom_x * denom_y)


def kendall_tau(x: list[float], y: list[float]) -> float:
    """Compute Kendall tau-b rank correlation coefficient."""
    n = len(x)
    if n < 2:
        return 0.0

    concordant = 0
    discordant = 0
    ties_x = 0
    ties_y = 0

    for i in range(n):
        for j in range(i + 1, n):
            dx = x[i] - x[j]
            dy = y[i] - y[j]

            if dx == 0 and dy == 0:
                ties_x += 1
                ties_y += 1
            elif dx == 0:
                ties_x += 1
            elif dy == 0:
                ties_y += 1
            elif (dx > 0 and dy > 0) or (dx < 0 and dy < 0):
                concordant += 1
            else:
                discordant += 1

    n_pairs = n * (n - 1) / 2
    denom = ((n_pairs - ties_x) * (n_pairs - ties_y)) ** 0.5
    if denom == 0:
        return 0.0
    return (concordant - discordant) / denom


def compute_auroc(scores: list[float], labels: list[int]) -> float:
    """Compute Area Under ROC Curve using the trapezoidal rule."""
    # Sort by score descending
    combined = sorted(zip(scores, labels), key=lambda x: -x[0])

    total_pos = sum(labels)
    total_neg = len(labels) - total_pos

    if total_pos == 0 or total_neg == 0:
        return 0.5

    tp = 0
    fp = 0
    prev_fpr = 0.0
    prev_tpr = 0.0
    auc = 0.0

    i = 0
    while i < len(combined):
        # Find all ties at this score level
        j = i
        while j < len(combined) and combined[j][0] == combined[i][0]:
            j += 1

        # Count positives and negatives in this tie group
        for k in range(i, j):
            if combined[k][1] == 1:
                tp += 1
            else:
                fp += 1

        fpr = fp / total_neg
        tpr = tp / total_pos

        # Trapezoidal area
        auc += (fpr - prev_fpr) * (tpr + prev_tpr) / 2.0

        prev_fpr = fpr
        prev_tpr = tpr
        i = j

    return auc


def compute_average_precision(scores: list[float], labels: list[int]) -> float:
    """Compute Average Precision (area under precision-recall curve)."""
    combined = sorted(zip(scores, labels), key=lambda x: -x[0])

    total_pos = sum(labels)
    if total_pos == 0:
        return 0.0

    tp = 0
    fp = 0
    ap = 0.0
    prev_recall = 0.0

    i = 0
    while i < len(combined):
        # Handle ties
        j = i
        while j < len(combined) and combined[j][0] == combined[i][0]:
            j += 1

        tie_tp = sum(1 for k in range(i, j) if combined[k][1] == 1)
        tie_fp = (j - i) - tie_tp
        tp += tie_tp
        fp += tie_fp

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / total_pos

        # Weight precision by change in recall
        ap += precision * (recall - prev_recall)
        prev_recall = recall
        i = j

    return ap


# ============================================================
# Threshold sweep
# ============================================================

def sweep_thresholds(scores: list[float], labels: list[int],
                     lo: float = 0.30, hi: float = 0.80, step: float = 0.01
                     ) -> list[dict]:
    """Sweep thresholds and compute metrics at each."""
    results = []
    threshold = lo
    while threshold <= hi + 1e-9:
        preds = [1 if s >= threshold else 0 for s in scores]
        metrics = compute_binary_metrics(labels, preds)
        metrics["threshold"] = round(threshold, 4)
        results.append(metrics)
        threshold += step
    return results


def find_optimal_thresholds(sweep_results: list[dict]) -> dict:
    """Find optimal thresholds for different use cases."""
    best_f1 = max(sweep_results, key=lambda r: r["f1"])
    best_accuracy = max(sweep_results, key=lambda r: r["accuracy"])

    # Briefing card: precision >= 0.85, maximize recall
    briefing_candidates = [r for r in sweep_results if r["precision"] >= 0.85]
    best_briefing = max(briefing_candidates, key=lambda r: r["recall"]) if briefing_candidates else best_f1

    # Feed ranking: recall >= 0.75, maximize precision
    feed_candidates = [r for r in sweep_results if r["recall"] >= 0.75]
    best_feed = max(feed_candidates, key=lambda r: r["precision"]) if feed_candidates else best_f1

    # Dedup: precision >= 0.95, maximize recall
    dedup_candidates = [r for r in sweep_results if r["precision"] >= 0.95]
    best_dedup = max(dedup_candidates, key=lambda r: r["recall"]) if dedup_candidates else None

    # If no threshold achieves 0.95 precision, take the highest precision available
    if best_dedup is None:
        best_dedup = max(sweep_results, key=lambda r: r["precision"])

    return {
        "best_f1": best_f1,
        "best_accuracy": best_accuracy,
        "briefing_card": best_briefing,
        "feed_ranking": best_feed,
        "deduplication": best_dedup,
    }


def find_knee_point(sweep_results: list[dict]) -> dict | None:
    """Find the threshold where raising it loses recall faster than it gains precision.

    We look for the point where d(precision)/d(threshold) < |d(recall)/d(threshold)|,
    i.e., where precision gains slow while recall drops fast.
    """
    # Only consider thresholds where both precision and recall are > 0
    valid = [r for r in sweep_results if r["precision"] > 0 and r["recall"] > 0]
    if len(valid) < 3:
        return None

    best_knee = None
    max_ratio = 0

    for i in range(1, len(valid) - 1):
        prev_r = valid[i - 1]
        curr = valid[i]
        next_r = valid[i + 1]

        d_precision = next_r["precision"] - prev_r["precision"]
        d_recall = next_r["recall"] - prev_r["recall"]

        # We want the point where recall starts dropping much faster than
        # precision is increasing. Recall should be negative (dropping),
        # precision should be positive or near zero.
        if d_recall < 0:
            ratio = abs(d_recall) / max(d_precision, 0.001)
            if ratio > max_ratio and curr["f1"] > 0.3:
                max_ratio = ratio
                best_knee = curr

    return best_knee


# ============================================================
# ASCII plotting
# ============================================================

def ascii_plot_prf(sweep_results: list[dict], width: int = 70):
    """Print an ASCII chart showing precision, recall, F1 across thresholds."""
    # Sample every 5th threshold to keep it readable
    sampled = sweep_results[::5]

    print("\n  Threshold Sensitivity: Precision (P), Recall (R), F1 (F)")
    print("  " + "-" * (width + 20))
    print(f"  {'Thresh':>6}  {'P':>5}  {'R':>5}  {'F1':>5}  |{'0%':<{width // 2}}{'100%':>{width // 2}}|")
    print("  " + "-" * (width + 20))

    for r in sampled:
        t = r["threshold"]
        p = r["precision"]
        rec = r["recall"]
        f1 = r["f1"]

        p_pos = int(p * width)
        r_pos = int(rec * width)
        f_pos = int(f1 * width)

        line = [" "] * (width + 1)
        # Draw in order: recall (most background), then precision, then F1 (foreground)
        if r_pos <= width:
            line[r_pos] = "R"
        if p_pos <= width:
            line[p_pos] = "P"
        if f_pos <= width:
            line[f_pos] = "F"

        bar = "".join(line)
        print(f"  {t:>6.2f}  {p:>5.2f}  {rec:>5.2f}  {f1:>5.2f}  |{bar}|")

    print("  " + "-" * (width + 20))
    print("  P=Precision  R=Recall  F=F1")


def ascii_plot_scores_vs_ratings(pairs_data: list[dict], width: int = 60):
    """Print an ASCII scatter of cosine scores vs. human ratings."""
    print("\n  Score Distribution by Human Rating")
    print("  " + "-" * (width + 15))

    # Group scores by rating
    by_rating: dict[int, list[float]] = {}
    for p in pairs_data:
        rating = p["rating"]
        if rating not in by_rating:
            by_rating[rating] = []
        by_rating[rating].append(p["score"])

    min_score = min(p["score"] for p in pairs_data)
    max_score = max(p["score"] for p in pairs_data)
    score_range = max_score - min_score if max_score > min_score else 1.0

    for rating in sorted(by_rating.keys()):
        scores = sorted(by_rating[rating])
        line = [" "] * (width + 1)
        for s in scores:
            pos = int((s - min_score) / score_range * width)
            pos = min(pos, width)
            if line[pos] == " ":
                line[pos] = "*"
            elif line[pos] == "*":
                line[pos] = "#"
            else:
                line[pos] = "#"

        bar = "".join(line)
        label = f"rating={rating}"
        print(f"  {label:>10}  [{bar}]  (n={len(scores)}, med={np.median(scores):.3f})")

    print(f"  {'':>10}   {min_score:<.2f}{' ' * (width - 8)}{max_score:.2f}")
    print("  " + "-" * (width + 15))


# ============================================================
# Error analysis
# ============================================================

def analyze_errors(pairs_data: list[dict], threshold: float,
                   articles: dict[str, dict]) -> tuple[list[dict], list[dict]]:
    """Identify and categorize false positives and false negatives."""
    false_positives = []
    false_negatives = []

    for p in pairs_data:
        predicted_overlap = p["score"] >= threshold
        actual_overlap = p["label"] == 1

        if predicted_overlap and not actual_overlap:
            fp_entry = {
                "id_a": p["id_a"],
                "id_b": p["id_b"],
                "title_a": articles.get(p["id_a"], {}).get("title", "?"),
                "title_b": articles.get(p["id_b"], {}).get("title", "?"),
                "summary_a": get_summary_text(articles.get(p["id_a"], {}))[:150],
                "summary_b": get_summary_text(articles.get(p["id_b"], {}))[:150],
                "score": p["score"],
                "rating": p["rating"],
                "category": categorize_error(p, articles, "fp"),
            }
            false_positives.append(fp_entry)

        elif not predicted_overlap and actual_overlap:
            fn_entry = {
                "id_a": p["id_a"],
                "id_b": p["id_b"],
                "title_a": articles.get(p["id_a"], {}).get("title", "?"),
                "title_b": articles.get(p["id_b"], {}).get("title", "?"),
                "summary_a": get_summary_text(articles.get(p["id_a"], {}))[:150],
                "summary_b": get_summary_text(articles.get(p["id_b"], {}))[:150],
                "score": p["score"],
                "rating": p["rating"],
                "category": categorize_error(p, articles, "fn"),
            }
            false_negatives.append(fn_entry)

    false_positives.sort(key=lambda x: -x["score"])
    false_negatives.sort(key=lambda x: x["score"])
    return false_positives, false_negatives


def categorize_error(pair: dict, articles: dict[str, dict], error_type: str) -> str:
    """Categorize a misclassification based on simple heuristics."""
    a = articles.get(pair["id_a"], {})
    b = articles.get(pair["id_b"], {})

    title_a = a.get("title", "").lower()
    title_b = b.get("title", "").lower()
    summary_a = get_summary_text(a).lower()
    summary_b = get_summary_text(b).lower()

    # Check for shared topic words (simple word overlap)
    words_a = set(title_a.split()) | set(summary_a.split())
    words_b = set(title_b.split()) | set(summary_b.split())
    # Remove common stopwords
    stopwords = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at",
                 "to", "for", "of", "and", "or", "with", "that", "this", "it",
                 "by", "from", "as", "be", "has", "have", "had", "not", "but",
                 "its", "their", "than", "who", "which", "what", "when", "where"}
    words_a -= stopwords
    words_b -= stopwords
    overlap = words_a & words_b
    jaccard = len(overlap) / len(words_a | words_b) if (words_a | words_b) else 0

    if error_type == "fp":
        if jaccard > 0.3:
            return "vocabulary_overlap_without_meaning"
        elif pair["score"] > 0.55:
            return "high_similarity_low_relevance"
        else:
            return "borderline_score"
    else:  # fn
        if jaccard < 0.1:
            return "meaning_overlap_without_vocabulary"
        elif pair["score"] > 0.35:
            return "borderline_score"
        else:
            return "low_embedding_similarity"


def suggest_fix(category: str) -> str:
    """Suggest what additional signal could fix a given error category."""
    fixes = {
        "vocabulary_overlap_without_meaning":
            "Add topic/entity matching as second signal; summaries share domain "
            "vocabulary but discuss different aspects. Cross-encoder reranking could help.",
        "high_similarity_low_relevance":
            "The embedding space conflates domain proximity with content overlap. "
            "Consider a trained cross-encoder or contrastive fine-tuning on article pairs.",
        "borderline_score":
            "Near-threshold pair. Claim-level overlap (% shared claims) would provide "
            "a more granular signal than summary-level embedding distance.",
        "meaning_overlap_without_vocabulary":
            "Articles discuss same concept with different framing/vocabulary. "
            "An LLM judge or claim-level cross-matching would detect semantic overlap.",
        "low_embedding_similarity":
            "The relationship is topical/thematic rather than content-level. "
            "Consider topic co-occurrence or entity overlap as supplementary features.",
    }
    return fixes.get(category, "Unknown error category.")


# ============================================================
# Main evaluation
# ============================================================

def run_evaluation(binary_threshold: int = 2, verbose: bool = False):
    """Run the full evaluation pipeline."""
    # 1. Load data
    ground_truth = load_ground_truth()
    articles = load_articles()

    # Collect all needed article IDs
    needed_ids = set()
    for id_a, id_b, _ in ground_truth:
        needed_ids.add(id_a)
        needed_ids.add(id_b)

    # 2. Compute embeddings
    embeddings = compute_article_embeddings(articles, needed_ids)

    # 3. Compute pairwise scores
    pairs_data = []
    skipped = 0
    for id_a, id_b, rating in ground_truth:
        if id_a not in embeddings or id_b not in embeddings:
            skipped += 1
            continue
        score = cosine_similarity(embeddings[id_a], embeddings[id_b])
        label = 1 if rating >= binary_threshold else 0
        pairs_data.append({
            "id_a": id_a, "id_b": id_b,
            "rating": rating, "label": label,
            "score": score,
        })

    if skipped:
        print(f"  Skipped {skipped} pairs (missing articles)", file=sys.stderr)

    scores = [p["score"] for p in pairs_data]
    labels = [p["label"] for p in pairs_data]
    ratings = [p["rating"] for p in pairs_data]

    n_positive = sum(labels)
    n_negative = len(labels) - n_positive

    # ========================================
    # PART 1: Multi-metric evaluation
    # ========================================
    print("\n" + "=" * 70)
    print("  ARTICLE SIMILARITY EVALUATION REPORT")
    print("=" * 70)
    print(f"\n  Ground truth: {len(pairs_data)} pairs ({n_positive} positive, {n_negative} negative)")
    print(f"  Binary threshold: rating >= {binary_threshold} is 'overlap'")
    print(f"  Score range: {min(scores):.4f} to {max(scores):.4f} (mean {np.mean(scores):.4f})")

    # Rating distribution
    rating_dist = Counter(ratings)
    print(f"  Rating distribution: {dict(sorted(rating_dist.items()))}")

    # Correlations
    spearman = spearman_rank_correlation(scores, [float(r) for r in ratings])
    tau = kendall_tau(scores, [float(r) for r in ratings])
    auroc = compute_auroc(scores, labels)
    avg_precision = compute_average_precision(scores, labels)

    print(f"\n  --- Rank Correlations (score vs. rating) ---")
    print(f"  Spearman rho:      {spearman:+.4f}")
    print(f"  Kendall tau:       {tau:+.4f}")

    print(f"\n  --- Ranking Metrics ---")
    print(f"  AUROC:             {auroc:.4f}")
    print(f"  Average Precision: {avg_precision:.4f}")

    # Threshold sweep
    sweep = sweep_thresholds(scores, labels, lo=0.30, hi=0.80, step=0.01)
    optimal = find_optimal_thresholds(sweep)

    print(f"\n  --- Optimal Thresholds ---")
    for name, result in optimal.items():
        t = result["threshold"]
        print(f"  {name:>20}: threshold={t:.2f}  "
              f"P={result['precision']:.3f}  R={result['recall']:.3f}  "
              f"F1={result['f1']:.3f}  Acc={result['accuracy']:.3f}")

    best_f1_result = optimal["best_f1"]
    best_t = best_f1_result["threshold"]

    print(f"\n  --- Confusion Matrix at Best F1 Threshold ({best_t:.2f}) ---")
    print(f"                  Predicted")
    print(f"                  Neg    Pos")
    print(f"  Actual Neg     {best_f1_result['tn']:>4}   {best_f1_result['fp']:>4}")
    print(f"  Actual Pos     {best_f1_result['fn']:>4}   {best_f1_result['tp']:>4}")

    # Knee point
    knee = find_knee_point(sweep)
    if knee:
        print(f"\n  --- Knee Point ---")
        print(f"  Threshold {knee['threshold']:.2f}: beyond this, recall drops faster than precision gains")
        print(f"    P={knee['precision']:.3f}  R={knee['recall']:.3f}  F1={knee['f1']:.3f}")

    # ========================================
    # PART 2: Threshold sensitivity
    # ========================================
    ascii_plot_prf(sweep)
    ascii_plot_scores_vs_ratings(pairs_data)

    print("\n  --- Use-Case Threshold Recommendations ---")
    print()

    rec_briefing = optimal["briefing_card"]
    rec_feed = optimal["feed_ranking"]
    rec_dedup = optimal["deduplication"]

    print(f"  BRIEFING CARD (\"similar articles you've read\") -- precision matters")
    print(f"    Threshold: {rec_briefing['threshold']:.2f}")
    print(f"    P={rec_briefing['precision']:.3f}  R={rec_briefing['recall']:.3f}  F1={rec_briefing['f1']:.3f}")
    print()
    print(f"  FEED RANKING (\"reduce priority of redundant articles\") -- recall matters")
    print(f"    Threshold: {rec_feed['threshold']:.2f}")
    print(f"    P={rec_feed['precision']:.3f}  R={rec_feed['recall']:.3f}  F1={rec_feed['f1']:.3f}")
    print()
    print(f"  DEDUPLICATION (\"skip this, you've read it\") -- very high precision")
    print(f"    Threshold: {rec_dedup['threshold']:.2f}")
    print(f"    P={rec_dedup['precision']:.3f}  R={rec_dedup['recall']:.3f}  F1={rec_dedup['f1']:.3f}")

    # ========================================
    # PART 3: Failure mode analysis
    # ========================================
    false_positives, false_negatives = analyze_errors(pairs_data, best_t, articles)

    print(f"\n  --- Error Analysis at Threshold {best_t:.2f} ---")
    print(f"  False positives: {len(false_positives)}")
    print(f"  False negatives: {len(false_negatives)}")

    if false_positives:
        print(f"\n  FALSE POSITIVES (predicted overlap, actually not):")
        for i, fp in enumerate(false_positives):
            print(f"\n  [{i+1}] score={fp['score']:.4f}, rating={fp['rating']}")
            print(f"      A: {fp['title_a']}")
            print(f"      B: {fp['title_b']}")
            if verbose:
                print(f"      Summary A: {fp['summary_a']}")
                print(f"      Summary B: {fp['summary_b']}")
            print(f"      Category: {fp['category']}")
            print(f"      Fix: {suggest_fix(fp['category'])}")

    if false_negatives:
        print(f"\n  FALSE NEGATIVES (predicted no overlap, actually overlapping):")
        for i, fn in enumerate(false_negatives):
            print(f"\n  [{i+1}] score={fn['score']:.4f}, rating={fn['rating']}")
            print(f"      A: {fn['title_a']}")
            print(f"      B: {fn['title_b']}")
            if verbose:
                print(f"      Summary A: {fn['summary_a']}")
                print(f"      Summary B: {fn['summary_b']}")
            print(f"      Category: {fn['category']}")
            print(f"      Fix: {suggest_fix(fn['category'])}")

    # Error category summary
    fp_cats = Counter(fp["category"] for fp in false_positives)
    fn_cats = Counter(fn["category"] for fn in false_negatives)
    if fp_cats or fn_cats:
        print(f"\n  Error Category Summary:")
        if fp_cats:
            print(f"    FP categories: {dict(fp_cats)}")
        if fn_cats:
            print(f"    FN categories: {dict(fn_cats)}")

    # ========================================
    # PART 4: Export threshold config
    # ========================================

    # Determine multi-level thresholds
    # Dedup > briefing > shared_themes > worth_mentioning
    t_dedup = rec_dedup["threshold"]
    t_briefing = rec_briefing["threshold"]
    t_shared = best_t  # best F1
    t_worth = max(0.30, best_t - 0.10)  # 10 points below best F1, floor at 0.30

    # Make sure they are properly ordered
    thresholds_ordered = sorted([t_dedup, t_briefing, t_shared, t_worth], reverse=True)
    # Assign names to the sorted thresholds
    t_dedup = thresholds_ordered[0]
    t_briefing = max(thresholds_ordered[1], t_briefing)
    t_shared = max(thresholds_ordered[2], t_shared) if len(thresholds_ordered) > 2 else t_shared

    config = {
        "thresholds": {
            "duplicate_detection": round(t_dedup, 2),
            "significant_overlap": round(t_briefing, 2),
            "shared_themes": round(t_shared, 2),
            "worth_mentioning": round(t_worth, 2),
        },
        "evaluation": {
            "n_pairs": len(pairs_data),
            "n_positive": n_positive,
            "n_negative": n_negative,
            "binary_threshold": f"rating >= {binary_threshold}",
            "accuracy": round(best_f1_result["accuracy"], 4),
            "precision": round(best_f1_result["precision"], 4),
            "recall": round(best_f1_result["recall"], 4),
            "f1": round(best_f1_result["f1"], 4),
            "auroc": round(auroc, 4),
            "average_precision": round(avg_precision, 4),
            "spearman_rho": round(spearman, 4),
            "kendall_tau": round(tau, 4),
            "optimal_f1_threshold": round(best_t, 2),
        },
        "use_case_thresholds": {
            "briefing_card": {
                "threshold": round(rec_briefing["threshold"], 2),
                "precision": round(rec_briefing["precision"], 4),
                "recall": round(rec_briefing["recall"], 4),
                "description": "Similar articles you've read -- precision matters",
            },
            "feed_ranking": {
                "threshold": round(rec_feed["threshold"], 2),
                "precision": round(rec_feed["precision"], 4),
                "recall": round(rec_feed["recall"], 4),
                "description": "Reduce priority of redundant articles -- recall matters",
            },
            "deduplication": {
                "threshold": round(rec_dedup["threshold"], 2),
                "precision": round(rec_dedup["precision"], 4),
                "recall": round(rec_dedup["recall"], 4),
                "description": "Skip this, you've read it -- very high precision needed",
            },
        },
    }

    with open(THRESHOLD_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n  --- Threshold Config ---")
    print(f"  Saved to {THRESHOLD_CONFIG_PATH}")
    print(json.dumps(config, indent=2))

    # All pairs detail (for reference)
    if verbose:
        print(f"\n  --- All Pairs Detail ---")
        for p in sorted(pairs_data, key=lambda x: -x["score"]):
            title_a = articles.get(p["id_a"], {}).get("title", "?")[:40]
            title_b = articles.get(p["id_b"], {}).get("title", "?")[:40]
            pred = "OVERLAP" if p["score"] >= best_t else "  none"
            actual = "OVERLAP" if p["label"] == 1 else "  none"
            match = "OK" if (p["score"] >= best_t) == (p["label"] == 1) else "MISS"
            print(f"  {p['score']:.4f}  r={p['rating']}  pred={pred}  actual={actual}  {match}")
            print(f"         {title_a}")
            print(f"         {title_b}")

    print("\n" + "=" * 70)
    print("  Done.")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Evaluate article similarity against ground truth")
    parser.add_argument("--binary-threshold", type=int, default=2,
                        help="Minimum rating to count as 'overlap' (default: 2)")
    parser.add_argument("--verbose", action="store_true",
                        help="Show full summaries and all-pairs detail")
    args = parser.parse_args()

    run_evaluation(binary_threshold=args.binary_threshold, verbose=args.verbose)


if __name__ == "__main__":
    main()

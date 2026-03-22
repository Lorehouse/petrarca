#!/usr/bin/env python3
"""Validate synthetic benchmark: recompute all mismatch flags and print analysis."""

import json
import numpy as np
from scipy.stats import spearmanr, pearsonr

benchmark_path = "/Users/stian/src/petrarca/scripts/ground-truth/synthetic_benchmark.json"

with open(benchmark_path) as f:
    benchmark = json.load(f)

# Expected cosine ranges per category
expected_ranges = {
    "near_duplicate": (0.65, 1.0),
    "shared_theme": (0.45, 0.80),
    "same_field": (0.20, 0.55),
    "cross_domain_connection": (0.20, 0.60),
    "unrelated": (-0.1, 0.35),
}

# Recompute mismatches
for pair in benchmark:
    cat = pair["category"]
    cos = pair["cosine_similarity"]
    lo, hi = expected_ranges[cat]
    pair["mismatch"] = cos < lo or cos > hi

# Save updated
with open(benchmark_path, "w") as f:
    json.dump(benchmark, f, indent=2)

# Print analysis
print("=" * 75)
print("SYNTHETIC BENCHMARK VALIDATION")
print(f"Total pairs: {len(benchmark)}")
print("=" * 75)

cat_order = ["near_duplicate", "shared_theme", "same_field", "cross_domain_connection", "unrelated"]

print(f"\n{'Category':<30} {'Expected':>8} {'Mean Cos':>9} {'Min':>7} {'Max':>7} {'StdDev':>7} {'N':>3}")
print("-" * 75)

all_expected = []
all_cosine = []

for cat_name in cat_order:
    cat_pairs = [p for p in benchmark if p["category"] == cat_name]
    if not cat_pairs:
        continue
    cosines = [p["cosine_similarity"] for p in cat_pairs]
    exp = cat_pairs[0]["expected_score"]
    print(f"{cat_name:<30} {exp:>8.1f} {np.mean(cosines):>9.4f} {np.min(cosines):>7.4f} {np.max(cosines):>7.4f} {np.std(cosines):>7.4f} {len(cat_pairs):>3}")
    all_expected.extend([exp] * len(cosines))
    all_cosine.extend(cosines)

spearman_r, spearman_p = spearmanr(all_expected, all_cosine)
pearson_r, pearson_p = pearsonr(all_expected, all_cosine)

print(f"\nCorrelations:")
print(f"  Spearman: r={spearman_r:.4f}, p={spearman_p:.2e}")
print(f"  Pearson:  r={pearson_r:.4f}, p={pearson_p:.2e}")

# Mismatches
mismatches = [p for p in benchmark if p.get("mismatch")]
print(f"\nMismatches: {len(mismatches)}/{len(benchmark)}")
if mismatches:
    for p in mismatches:
        lo, hi = expected_ranges[p["category"]]
        print(f"  [{p['category']}] cos={p['cosine_similarity']:.4f} (expected {lo:.2f}-{hi:.2f})")
        print(f"    A: {p['article_a']['title']}")
        print(f"    B: {p['article_b']['title']}")

# Check category separation
print("\nCategory separation (mean cosine differences between adjacent categories):")
means = {}
for cat_name in cat_order:
    cat_pairs = [p for p in benchmark if p["category"] == cat_name]
    if cat_pairs:
        means[cat_name] = np.mean([p["cosine_similarity"] for p in cat_pairs])

for i in range(len(cat_order) - 1):
    a = cat_order[i]
    b = cat_order[i + 1]
    if a in means and b in means:
        diff = means[a] - means[b]
        print(f"  {a} -> {b}: {diff:+.4f}")

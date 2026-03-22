#!/usr/bin/env python3
"""
Corpus analysis for Petrarca article collection.

Analyzes natural clustering, topic-embedding agreement, reading order novelty,
overlap density, and cross-domain bridges across all articles.
"""

import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/.env"))

PROJECT_ROOT = Path(__file__).parent.parent
ARTICLES_PATH = PROJECT_ROOT / "app" / "data" / "articles.json"
OUTPUT_PATH = PROJECT_ROOT / "scripts" / "ground-truth" / "corpus_analysis.json"


def load_articles():
    with open(ARTICLES_PATH) as f:
        articles = json.load(f)
    print(f"Loaded {len(articles)} articles")
    return articles


def embed_summaries(articles):
    from limbic.amygdala import EmbeddingModel

    model = EmbeddingModel()
    texts = [a["full_summary"] for a in articles]
    print(f"Embedding {len(texts)} summaries...")
    embs = model.embed_batch(texts)
    embs = np.array(embs)
    # Normalize for cosine similarity
    norms = np.linalg.norm(embs, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embs_normed = embs / norms
    print(f"Embeddings shape: {embs_normed.shape}")
    return embs_normed


def cosine_similarity_matrix(embs):
    """Compute full NxN cosine similarity matrix from normalized embeddings."""
    sim_matrix = embs @ embs.T
    return sim_matrix


def get_article_date(article):
    """Extract the best available date for ordering articles."""
    # Prefer ingested_at
    if article.get("ingested_at"):
        return article["ingested_at"]
    # Then bookmarked_at from sources
    for s in article.get("sources", []):
        if s.get("bookmarked_at"):
            return s["bookmarked_at"]
    # Fall back to article date
    return article.get("date", "2000-01-01")


def get_broad_topics(article):
    """Get set of broad topic tags for an article."""
    return set(t.get("broad", "") for t in article.get("interest_topics", []) if t.get("broad"))


# =============================================================================
# Analysis 1: Natural Clusters
# =============================================================================
def analysis_natural_clusters(articles, sim_matrix):
    print("\n" + "=" * 70)
    print("ANALYSIS 1: NATURAL CLUSTERS")
    print("=" * 70)

    from sklearn.cluster import HDBSCAN

    # Convert similarity to distance
    dist_matrix = 1 - sim_matrix
    np.fill_diagonal(dist_matrix, 0)
    dist_matrix = np.clip(dist_matrix, 0, None)

    # HDBSCAN clustering
    clusterer = HDBSCAN(
        min_cluster_size=3,
        min_samples=2,
        metric="precomputed",
    )
    labels = clusterer.fit_predict(dist_matrix)

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = (labels == -1).sum()
    print(f"Found {n_clusters} clusters, {n_noise} singletons/noise")

    clusters = {}
    for cluster_id in sorted(set(labels)):
        indices = np.where(labels == cluster_id)[0]
        cluster_articles = [articles[i] for i in indices]

        # Internal cohesion: mean pairwise similarity within cluster
        if len(indices) > 1:
            sub_sim = sim_matrix[np.ix_(indices, indices)]
            # Upper triangle only (exclude diagonal)
            triu_mask = np.triu(np.ones_like(sub_sim, dtype=bool), k=1)
            cohesion = float(sub_sim[triu_mask].mean())
        else:
            cohesion = 0.0

        # Dominant topics
        topic_counts = Counter()
        for a in cluster_articles:
            for t in get_broad_topics(a):
                topic_counts[t] += 1

        cluster_key = f"cluster_{cluster_id}" if cluster_id >= 0 else "noise"
        clusters[cluster_key] = {
            "size": len(indices),
            "cohesion": round(cohesion, 4),
            "article_indices": [int(i) for i in indices],
            "titles": [a["title"][:80] for a in cluster_articles[:10]],
            "dominant_topics": dict(topic_counts.most_common(5)),
        }

        if cluster_id >= 0:
            top_topics = ", ".join(f"{t}({c})" for t, c in topic_counts.most_common(3))
            print(f"\n  Cluster {cluster_id}: {len(indices)} articles, cohesion={cohesion:.3f}")
            print(f"    Topics: {top_topics}")
            for a in cluster_articles[:3]:
                print(f"    - {a['title'][:70]}")
            if len(cluster_articles) > 3:
                print(f"    ... and {len(cluster_articles) - 3} more")

    if n_noise > 0:
        print(f"\n  Noise/singletons: {n_noise} articles")
        noise_indices = np.where(labels == -1)[0]
        for i in noise_indices[:5]:
            print(f"    - {articles[i]['title'][:70]}")
        if n_noise > 5:
            print(f"    ... and {n_noise - 5} more")

    return {
        "n_clusters": n_clusters,
        "n_noise": int(n_noise),
        "clusters": clusters,
        "labels": [int(l) for l in labels],
    }


# =============================================================================
# Analysis 2: Topic vs Embedding Agreement
# =============================================================================
def analysis_topic_embedding_agreement(articles, sim_matrix):
    print("\n" + "=" * 70)
    print("ANALYSIS 2: TOPIC vs EMBEDDING AGREEMENT")
    print("=" * 70)

    # Build topic -> article index mapping
    topic_articles = defaultdict(list)
    for i, a in enumerate(articles):
        for t in get_broad_topics(a):
            topic_articles[t].append(i)

    topic_stats = {}
    for topic, indices in sorted(topic_articles.items(), key=lambda x: -len(x[1])):
        if len(indices) < 2:
            continue

        # Mean pairwise similarity within this topic
        idx_arr = np.array(indices)
        sub_sim = sim_matrix[np.ix_(idx_arr, idx_arr)]
        triu_mask = np.triu(np.ones_like(sub_sim, dtype=bool), k=1)
        sims = sub_sim[triu_mask]
        mean_sim = float(sims.mean())
        median_sim = float(np.median(sims))
        std_sim = float(sims.std())
        high_sim_frac = float((sims >= 0.5).mean())

        topic_stats[topic] = {
            "n_articles": len(indices),
            "mean_sim": round(mean_sim, 4),
            "median_sim": round(median_sim, 4),
            "std_sim": round(std_sim, 4),
            "high_sim_fraction": round(high_sim_frac, 4),
        }

        print(f"  {topic}: {len(indices)} articles, mean_sim={mean_sim:.3f}, "
              f"median={median_sim:.3f}, std={std_sim:.3f}, "
              f">0.5 sim: {high_sim_frac:.1%}")

    # Cross-topic comparison: similarity between different topic groups
    print("\n  Cross-topic mean similarities (top pairs):")
    cross_topic_sims = []
    topics_list = [t for t in topic_articles if len(topic_articles[t]) >= 5]
    for i_t, t1 in enumerate(topics_list):
        for t2 in topics_list[i_t + 1:]:
            idx1 = np.array(topic_articles[t1])
            idx2 = np.array(topic_articles[t2])
            cross_sim = sim_matrix[np.ix_(idx1, idx2)]
            mean_cross = float(cross_sim.mean())
            cross_topic_sims.append({
                "topic_1": t1,
                "topic_2": t2,
                "mean_sim": round(mean_cross, 4),
            })

    cross_topic_sims.sort(key=lambda x: -x["mean_sim"])
    for pair in cross_topic_sims[:10]:
        print(f"    {pair['topic_1']} <-> {pair['topic_2']}: {pair['mean_sim']:.3f}")

    # Find disagreements: same topic but low embedding similarity
    print("\n  Topic tag agrees, embedding disagrees (same broad topic, sim < 0.2):")
    disagreements_same_topic = []
    for topic, indices in topic_articles.items():
        for ii, i in enumerate(indices):
            for j in indices[ii + 1:]:
                s = sim_matrix[i, j]
                if s < 0.2:
                    disagreements_same_topic.append({
                        "topic": topic,
                        "article_1": articles[i]["title"][:60],
                        "article_2": articles[j]["title"][:60],
                        "similarity": round(float(s), 4),
                    })

    disagreements_same_topic.sort(key=lambda x: x["similarity"])
    for d in disagreements_same_topic[:10]:
        print(f"    [{d['topic']}] sim={d['similarity']:.3f}: "
              f"{d['article_1'][:40]} <-> {d['article_2'][:40]}")

    # Find cases: different topics but high embedding similarity
    print("\n  Embedding agrees, topic tags disagree (no shared broad, sim > 0.55):")
    disagreements_diff_topic = []
    for i in range(len(articles)):
        for j in range(i + 1, len(articles)):
            s = sim_matrix[i, j]
            if s > 0.55:
                topics_i = get_broad_topics(articles[i])
                topics_j = get_broad_topics(articles[j])
                if not topics_i.intersection(topics_j):
                    disagreements_diff_topic.append({
                        "article_1": articles[i]["title"][:60],
                        "article_2": articles[j]["title"][:60],
                        "topics_1": sorted(topics_i),
                        "topics_2": sorted(topics_j),
                        "similarity": round(float(s), 4),
                    })

    disagreements_diff_topic.sort(key=lambda x: -x["similarity"])
    for d in disagreements_diff_topic[:10]:
        print(f"    sim={d['similarity']:.3f}: {d['article_1'][:35]} ({','.join(d['topics_1'][:2])}) "
              f"<-> {d['article_2'][:35]} ({','.join(d['topics_2'][:2])})")

    return {
        "within_topic_stats": topic_stats,
        "cross_topic_sims": cross_topic_sims[:20],
        "same_topic_low_sim": disagreements_same_topic[:20],
        "diff_topic_high_sim": disagreements_diff_topic[:20],
    }


# =============================================================================
# Analysis 3: Reading Order Simulation
# =============================================================================
def analysis_reading_order(articles, sim_matrix):
    print("\n" + "=" * 70)
    print("ANALYSIS 3: READING ORDER SIMULATION")
    print("=" * 70)

    # Sort articles by date
    dated_articles = []
    for i, a in enumerate(articles):
        date_str = get_article_date(a)
        dated_articles.append((i, date_str, a))

    dated_articles.sort(key=lambda x: x[1])

    # Simulate reading in order
    read_indices = []
    novelty_curve = []
    max_sim_to_read = []

    for step, (idx, date_str, article) in enumerate(dated_articles):
        if not read_indices:
            novelty_curve.append({
                "step": step,
                "article_idx": int(idx),
                "title": article["title"][:60],
                "max_sim_to_prev": 0.0,
                "novelty": 1.0,
                "date": date_str[:10],
                "broad_topics": sorted(get_broad_topics(article)),
            })
            read_indices.append(idx)
            continue

        # Find most similar previously-read article
        sims_to_read = sim_matrix[idx, read_indices]
        max_sim = float(sims_to_read.max())
        most_similar_idx = read_indices[int(sims_to_read.argmax())]
        novelty = 1.0 - max_sim

        novelty_curve.append({
            "step": step,
            "article_idx": int(idx),
            "title": article["title"][:60],
            "max_sim_to_prev": round(max_sim, 4),
            "most_similar_title": articles[most_similar_idx]["title"][:60],
            "novelty": round(novelty, 4),
            "date": date_str[:10],
            "broad_topics": sorted(get_broad_topics(article)),
        })
        max_sim_to_read.append(max_sim)
        read_indices.append(idx)

    # Summary stats
    novelty_values = [n["novelty"] for n in novelty_curve[1:]]
    max_sim_values = [n["max_sim_to_prev"] for n in novelty_curve[1:]]

    # Compute running average in windows
    window = 20
    running_avg = []
    for i in range(len(novelty_values)):
        start = max(0, i - window + 1)
        running_avg.append(float(np.mean(novelty_values[start:i + 1])))

    print(f"  Total articles in order: {len(dated_articles)}")
    print(f"  Mean novelty: {np.mean(novelty_values):.3f}")
    print(f"  Mean max-sim to previously read: {np.mean(max_sim_values):.3f}")
    print(f"  Novelty at step 10: {running_avg[9]:.3f}")
    print(f"  Novelty at step 50: {running_avg[49]:.3f}")
    print(f"  Novelty at step 100: {running_avg[99]:.3f}")
    print(f"  Novelty at step 200: {running_avg[199]:.3f}")
    print(f"  Novelty at step 256: {running_avg[-1]:.3f}")

    # Biggest novelty drops
    print("\n  Most redundant articles (lowest novelty):")
    sorted_by_novelty = sorted(novelty_curve[1:], key=lambda x: x["novelty"])
    for n in sorted_by_novelty[:10]:
        print(f"    step={n['step']:3d} novelty={n['novelty']:.3f}: "
              f"{n['title'][:50]} (like: {n['most_similar_title'][:40]})")

    # Most novel articles (after first 20)
    print("\n  Most novel articles (after step 20):")
    late_novel = sorted([n for n in novelty_curve[20:]], key=lambda x: -x["novelty"])
    for n in late_novel[:10]:
        print(f"    step={n['step']:3d} novelty={n['novelty']:.3f}: {n['title'][:60]}")

    # Break down by topic cluster
    print("\n  Novelty curve by broad topic (mean novelty at each 50-article window):")
    topic_novelty = defaultdict(list)
    for n in novelty_curve[1:]:
        for t in n["broad_topics"]:
            topic_novelty[t].append(n["novelty"])

    for topic in sorted(topic_novelty.keys(), key=lambda t: -len(topic_novelty[t]))[:8]:
        vals = topic_novelty[topic]
        print(f"    {topic}: n={len(vals)}, mean_novelty={np.mean(vals):.3f}, "
              f"min={np.min(vals):.3f}, max={np.max(vals):.3f}")

    return {
        "novelty_curve": novelty_curve,
        "running_average_window": window,
        "running_average": [round(v, 4) for v in running_avg],
        "summary": {
            "mean_novelty": round(float(np.mean(novelty_values)), 4),
            "mean_max_sim": round(float(np.mean(max_sim_values)), 4),
            "novelty_at_10": round(running_avg[9], 4),
            "novelty_at_50": round(running_avg[49], 4),
            "novelty_at_100": round(running_avg[99], 4),
            "novelty_at_200": round(running_avg[199], 4),
            "novelty_at_256": round(running_avg[-1], 4),
        },
        "most_redundant": sorted_by_novelty[:20],
        "most_novel_late": late_novel[:20],
    }


# =============================================================================
# Analysis 4: Overlap Density Map
# =============================================================================
def analysis_overlap_density(articles, sim_matrix):
    print("\n" + "=" * 70)
    print("ANALYSIS 4: OVERLAP DENSITY MAP")
    print("=" * 70)

    threshold = 0.47
    n = len(articles)

    # For each article, count neighbors above threshold
    neighbor_counts = []
    for i in range(n):
        count = int((sim_matrix[i] >= threshold).sum()) - 1  # exclude self
        neighbor_counts.append({
            "article_idx": i,
            "title": articles[i]["title"][:70],
            "neighbor_count": count,
            "broad_topics": sorted(get_broad_topics(articles[i])),
            "mean_sim_to_neighbors": 0.0,
        })
        # Mean sim to neighbors
        neighbor_mask = (sim_matrix[i] >= threshold)
        neighbor_mask[i] = False
        if neighbor_mask.any():
            neighbor_counts[-1]["mean_sim_to_neighbors"] = round(
                float(sim_matrix[i, neighbor_mask].mean()), 4
            )

    neighbor_counts.sort(key=lambda x: -x["neighbor_count"])

    # Distribution
    counts = [n["neighbor_count"] for n in neighbor_counts]
    print(f"  Threshold: {threshold}")
    print(f"  Mean neighbors: {np.mean(counts):.1f}")
    print(f"  Median neighbors: {np.median(counts):.1f}")
    print(f"  Max neighbors: {max(counts)}")
    print(f"  Articles with 0 neighbors: {sum(1 for c in counts if c == 0)}")
    print(f"  Articles with 1-3 neighbors: {sum(1 for c in counts if 1 <= c <= 3)}")
    print(f"  Articles with 4-10 neighbors: {sum(1 for c in counts if 4 <= c <= 10)}")
    print(f"  Articles with 10+ neighbors: {sum(1 for c in counts if c > 10)}")

    # Histogram
    hist_bins = [0, 1, 2, 3, 5, 10, 20, 50, 100]
    hist = {}
    for i in range(len(hist_bins) - 1):
        lo, hi = hist_bins[i], hist_bins[i + 1]
        label = f"{lo}-{hi - 1}" if hi - lo > 1 else str(lo)
        hist[label] = sum(1 for c in counts if lo <= c < hi)
    hist[f"{hist_bins[-1]}+"] = sum(1 for c in counts if c >= hist_bins[-1])
    print(f"\n  Histogram: {hist}")

    print("\n  Most connected (highest overlap):")
    for n in neighbor_counts[:15]:
        topics = ", ".join(n["broad_topics"][:3])
        print(f"    {n['neighbor_count']:3d} neighbors: {n['title'][:55]} [{topics}]")

    print("\n  Most unique (lowest overlap):")
    unique = sorted(neighbor_counts, key=lambda x: x["neighbor_count"])
    for n in unique[:15]:
        topics = ", ".join(n["broad_topics"][:3])
        print(f"    {n['neighbor_count']:3d} neighbors: {n['title'][:55]} [{topics}]")

    return {
        "threshold": threshold,
        "distribution": {
            "mean": round(float(np.mean(counts)), 2),
            "median": round(float(np.median(counts)), 2),
            "max": int(max(counts)),
            "min": int(min(counts)),
            "histogram": hist,
        },
        "most_connected": neighbor_counts[:30],
        "most_unique": sorted(neighbor_counts, key=lambda x: x["neighbor_count"])[:30],
    }


# =============================================================================
# Analysis 5: Cross-Domain Bridges
# =============================================================================
def analysis_cross_domain_bridges(articles, sim_matrix):
    print("\n" + "=" * 70)
    print("ANALYSIS 5: CROSS-DOMAIN BRIDGES")
    print("=" * 70)

    threshold = 0.50
    n = len(articles)
    bridges = []

    for i in range(n):
        topics_i = get_broad_topics(articles[i])
        for j in range(i + 1, n):
            s = sim_matrix[i, j]
            if s >= threshold:
                topics_j = get_broad_topics(articles[j])
                shared = topics_i.intersection(topics_j)
                if not shared:
                    bridges.append({
                        "article_1_idx": int(i),
                        "article_1_title": articles[i]["title"][:70],
                        "article_1_topics": sorted(topics_i),
                        "article_2_idx": int(j),
                        "article_2_title": articles[j]["title"][:70],
                        "article_2_topics": sorted(topics_j),
                        "similarity": round(float(s), 4),
                    })

    bridges.sort(key=lambda x: -x["similarity"])

    print(f"  Found {len(bridges)} cross-domain pairs with sim >= {threshold}")
    print(f"\n  Top cross-domain bridges:")
    for b in bridges[:20]:
        t1 = ", ".join(b["article_1_topics"][:2])
        t2 = ", ".join(b["article_2_topics"][:2])
        print(f"    sim={b['similarity']:.3f}: [{t1}] {b['article_1_title'][:35]}")
        print(f"           <-> [{t2}] {b['article_2_title'][:35]}")

    # Which topic pairs bridge most?
    topic_pair_counts = Counter()
    for b in bridges:
        for t1 in b["article_1_topics"]:
            for t2 in b["article_2_topics"]:
                pair = tuple(sorted([t1, t2]))
                topic_pair_counts[pair] += 1

    print(f"\n  Most common bridging topic pairs:")
    for (t1, t2), count in topic_pair_counts.most_common(15):
        print(f"    {t1} <-> {t2}: {count} bridges")

    return {
        "threshold": threshold,
        "n_bridges": len(bridges),
        "bridges": bridges[:50],
        "topic_pair_counts": {f"{t1} <-> {t2}": c for (t1, t2), c in topic_pair_counts.most_common(30)},
    }


# =============================================================================
# Main
# =============================================================================
def main():
    articles = load_articles()
    embs = embed_summaries(articles)
    sim_matrix = cosine_similarity_matrix(embs)

    print(f"\nSimilarity matrix stats:")
    # Upper triangle values (excluding diagonal)
    triu_mask = np.triu(np.ones(sim_matrix.shape, dtype=bool), k=1)
    all_sims = sim_matrix[triu_mask]
    print(f"  Mean: {all_sims.mean():.4f}")
    print(f"  Median: {np.median(all_sims):.4f}")
    print(f"  Std: {all_sims.std():.4f}")
    print(f"  Min: {all_sims.min():.4f}")
    print(f"  Max: {all_sims.max():.4f}")
    print(f"  >0.5: {(all_sims > 0.5).sum()} pairs ({(all_sims > 0.5).mean():.2%})")
    print(f"  >0.6: {(all_sims > 0.6).sum()} pairs ({(all_sims > 0.6).mean():.2%})")
    print(f"  >0.7: {(all_sims > 0.7).sum()} pairs ({(all_sims > 0.7).mean():.2%})")
    print(f"  >0.8: {(all_sims > 0.8).sum()} pairs ({(all_sims > 0.8).mean():.2%})")

    results = {
        "metadata": {
            "n_articles": len(articles),
            "embedding_dim": int(embs.shape[1]),
            "generated_at": datetime.now().isoformat(),
            "similarity_stats": {
                "mean": round(float(all_sims.mean()), 4),
                "median": round(float(np.median(all_sims)), 4),
                "std": round(float(all_sims.std()), 4),
                "min": round(float(all_sims.min()), 4),
                "max": round(float(all_sims.max()), 4),
            },
        },
    }

    results["analysis_1_clusters"] = analysis_natural_clusters(articles, sim_matrix)
    results["analysis_2_topic_agreement"] = analysis_topic_embedding_agreement(articles, sim_matrix)
    results["analysis_3_reading_order"] = analysis_reading_order(articles, sim_matrix)
    results["analysis_4_overlap_density"] = analysis_overlap_density(articles, sim_matrix)
    results["analysis_5_cross_domain"] = analysis_cross_domain_bridges(articles, sim_matrix)

    # Save results
    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n{'=' * 70}")
    print(f"Results saved to {OUTPUT_PATH}")
    print(f"File size: {OUTPUT_PATH.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()

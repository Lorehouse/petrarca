#!/usr/bin/env python3
"""
Compare text representation strategies for article-level thematic similarity.

Uses 18 human-rated article pairs as ground truth.
Embeds different text representations via amygdala MiniLM,
computes cosine similarity, and evaluates accuracy + Spearman correlation.
"""

import json
import sys
import numpy as np
from pathlib import Path
from scipy.stats import spearmanr
from scipy.spatial.distance import cosine as cosine_dist

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from amygdala import EmbeddingModel

# ---------- Ground truth ----------
GROUND_TRUTH = [
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

# ---------- Load articles ----------
ARTICLES_PATH = Path(__file__).resolve().parent.parent.parent / "app" / "data" / "articles.json"


def load_articles():
    with open(ARTICLES_PATH) as f:
        articles = json.load(f)
    return {a["id"]: a for a in articles}


def format_topics(article):
    """Format interest_topics as a readable text string."""
    parts = []
    for t in article.get("interest_topics", []):
        broad = t.get("broad", "")
        specific = t.get("specific", "")
        entity = t.get("entity", "")
        if entity:
            parts.append(entity)
        if specific:
            parts.append(specific.replace("-", " "))
        if broad and broad != specific:
            parts.append(broad.replace("-", " "))
    # Also include simple topics
    for t in article.get("topics", []):
        parts.append(t.replace("-", " "))
    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for p in parts:
        pl = p.lower()
        if pl not in seen:
            seen.add(pl)
            deduped.append(p)
    return ", ".join(deduped)


def cosine_sim(a, b):
    return 1.0 - cosine_dist(a, b)


def best_threshold_accuracy(sims, ratings, binary_threshold_rating=1):
    """
    Find the best threshold for binary classification.
    Ratings >= binary_threshold_rating are 'related', otherwise 'unrelated'.
    """
    labels = [1 if r >= binary_threshold_rating else 0 for r in ratings]
    thresholds = np.arange(0.0, 1.001, 0.005)
    best_acc = 0.0
    best_t = 0.0
    for t in thresholds:
        preds = [1 if s >= t else 0 for s in sims]
        acc = sum(1 for p, l in zip(preds, labels) if p == l) / len(labels)
        if acc > best_acc or (acc == best_acc and t > best_t):
            best_acc = acc
            best_t = t
    return best_acc, best_t


def evaluate_strategy(sims, ratings):
    """Return accuracy, threshold, and Spearman rho."""
    acc, thresh = best_threshold_accuracy(sims, ratings)
    rho, p_value = spearmanr(sims, ratings)
    return {
        "accuracy": round(acc, 4),
        "threshold": round(thresh, 4),
        "spearman_rho": round(rho, 4),
        "spearman_p": round(p_value, 4),
    }


def main():
    print("Loading articles...")
    articles_by_id = load_articles()

    # Collect all article IDs needed
    needed_ids = set()
    for a, b, _ in GROUND_TRUTH:
        needed_ids.add(a)
        needed_ids.add(b)

    # Check all articles exist
    missing = needed_ids - set(articles_by_id.keys())
    if missing:
        # Try prefix matching
        full_ids = list(articles_by_id.keys())
        prefix_map = {}
        for short in missing:
            matches = [fid for fid in full_ids if fid.startswith(short)]
            if len(matches) == 1:
                prefix_map[short] = matches[0]
            else:
                print(f"ERROR: Article {short} not found (matches: {matches})")
                sys.exit(1)
        # Remap
        for short, full in prefix_map.items():
            articles_by_id[short] = articles_by_id[full]
        print(f"  Resolved {len(prefix_map)} prefix IDs")

    print(f"  Found all {len(needed_ids)} articles")

    model = EmbeddingModel()
    ratings = [r for _, _, r in GROUND_TRUTH]

    # ---------- Strategy functions ----------
    # Each returns a dict of {article_id: text} for embedding

    def strategy_full_summary():
        return {aid: articles_by_id[aid].get("full_summary", "") for aid in needed_ids}

    def strategy_one_line_summary():
        return {aid: articles_by_id[aid].get("one_line_summary", "") for aid in needed_ids}

    def strategy_title_one_line():
        return {
            aid: f"{articles_by_id[aid].get('title', '')}. {articles_by_id[aid].get('one_line_summary', '')}"
            for aid in needed_ids
        }

    def strategy_full_summary_claims():
        result = {}
        for aid in needed_ids:
            a = articles_by_id[aid]
            claims = "\n".join(a.get("key_claims", []))
            result[aid] = f"{a.get('full_summary', '')}\n\n{claims}"
        return result

    def strategy_key_claims_only():
        return {
            aid: "\n".join(articles_by_id[aid].get("key_claims", []))
            for aid in needed_ids
        }

    def strategy_topics_text():
        return {aid: format_topics(articles_by_id[aid]) for aid in needed_ids}

    def strategy_title_summary_topics():
        result = {}
        for aid in needed_ids:
            a = articles_by_id[aid]
            topics = format_topics(a)
            result[aid] = f"{a.get('title', '')}. {a.get('full_summary', '')}\nTopics: {topics}"
        return result

    # ---------- Run single-embedding strategies ----------
    single_strategies = {
        "1_full_summary": strategy_full_summary,
        "2_one_line_summary": strategy_one_line_summary,
        "3_title_one_line": strategy_title_one_line,
        "4_full_summary_claims": strategy_full_summary_claims,
        "5_key_claims_only": strategy_key_claims_only,
        "6_topics_text": strategy_topics_text,
        "7_title_summary_topics": strategy_title_summary_topics,
    }

    all_results = {}

    for name, strategy_fn in single_strategies.items():
        print(f"\nStrategy: {name}")
        texts_map = strategy_fn()

        # Show sample text length
        sample_id = list(texts_map.keys())[0]
        sample_text = texts_map[sample_id]
        print(f"  Sample text ({sample_id}): {len(sample_text)} chars")

        # Embed all unique articles
        aid_list = sorted(texts_map.keys())
        texts = [texts_map[aid] for aid in aid_list]
        embeddings = model.embed_batch(texts)
        emb_map = {aid: embeddings[i] for i, aid in enumerate(aid_list)}

        # Compute similarities
        sims = []
        pair_details = []
        for a_id, b_id, rating in GROUND_TRUTH:
            sim = cosine_sim(emb_map[a_id], emb_map[b_id])
            sims.append(sim)
            pair_details.append({
                "a": a_id,
                "b": b_id,
                "rating": rating,
                "similarity": round(float(sim), 4),
            })

        result = evaluate_strategy(sims, ratings)
        result["pairs"] = pair_details
        all_results[name] = result
        print(f"  Accuracy: {result['accuracy']:.1%} (threshold={result['threshold']:.3f})")
        print(f"  Spearman ρ: {result['spearman_rho']:.4f} (p={result['spearman_p']:.4f})")

    # ---------- Strategy 8: Weighted combination ----------
    print("\nStrategy: 8_weighted_combination")
    # Embed summaries and claims separately, try different weight combos
    summary_texts = {aid: articles_by_id[aid].get("full_summary", "") for aid in needed_ids}
    claims_texts = {
        aid: "\n".join(articles_by_id[aid].get("key_claims", []))
        for aid in needed_ids
    }
    aid_list = sorted(needed_ids)

    summary_embs = model.embed_batch([summary_texts[aid] for aid in aid_list])
    claims_embs = model.embed_batch([claims_texts[aid] for aid in aid_list])

    summary_map = {aid: summary_embs[i] for i, aid in enumerate(aid_list)}
    claims_map_emb = {aid: claims_embs[i] for i, aid in enumerate(aid_list)}

    best_weighted = None
    best_weighted_acc = 0
    best_weighted_rho = -1

    for w_summary in np.arange(0.1, 1.0, 0.1):
        w_claims = 1.0 - w_summary
        combined = {}
        for aid in aid_list:
            vec = w_summary * summary_map[aid] + w_claims * claims_map_emb[aid]
            vec = vec / np.linalg.norm(vec)  # re-normalize
            combined[aid] = vec

        sims = []
        for a_id, b_id, rating in GROUND_TRUTH:
            sims.append(cosine_sim(combined[a_id], combined[b_id]))

        result = evaluate_strategy(sims, ratings)
        if result["accuracy"] > best_weighted_acc or (
            result["accuracy"] == best_weighted_acc and result["spearman_rho"] > best_weighted_rho
        ):
            best_weighted_acc = result["accuracy"]
            best_weighted_rho = result["spearman_rho"]
            best_weighted = {
                "w_summary": round(w_summary, 2),
                "w_claims": round(w_claims, 2),
                **result,
            }
            best_weighted_sims = list(sims)

    # Recompute pair details for best weights
    w_s = best_weighted["w_summary"]
    w_c = best_weighted["w_claims"]
    combined = {}
    for aid in aid_list:
        vec = w_s * summary_map[aid] + w_c * claims_map_emb[aid]
        vec = vec / np.linalg.norm(vec)
        combined[aid] = vec

    pair_details = []
    for a_id, b_id, rating in GROUND_TRUTH:
        sim = cosine_sim(combined[a_id], combined[b_id])
        pair_details.append({
            "a": a_id, "b": b_id, "rating": rating,
            "similarity": round(float(sim), 4),
        })

    best_weighted["pairs"] = pair_details
    all_results["8_weighted_combination"] = best_weighted
    print(f"  Best weights: summary={best_weighted['w_summary']}, claims={best_weighted['w_claims']}")
    print(f"  Accuracy: {best_weighted['accuracy']:.1%} (threshold={best_weighted['threshold']:.3f})")
    print(f"  Spearman ρ: {best_weighted['spearman_rho']:.4f} (p={best_weighted['spearman_p']:.4f})")

    # ---------- Strategy 9: Max-sim of key claims (avg top-3) ----------
    print("\nStrategy: 9_maxsim_claims_top3")

    # Embed all claims individually
    all_claims_by_article = {}
    all_claim_texts = []
    claim_index = []  # (article_id, claim_idx)

    for aid in sorted(needed_ids):
        claims = articles_by_id[aid].get("key_claims", [])
        if not claims:
            claims = [articles_by_id[aid].get("one_line_summary", "")]
        all_claims_by_article[aid] = claims
        for i, c in enumerate(claims):
            all_claim_texts.append(c)
            claim_index.append((aid, i))

    print(f"  Total claims to embed: {len(all_claim_texts)}")
    claim_embeddings = model.embed_batch(all_claim_texts)

    # Build per-article claim embedding arrays
    article_claim_embs = {}
    for aid in needed_ids:
        indices = [i for i, (a, _) in enumerate(claim_index) if a == aid]
        article_claim_embs[aid] = claim_embeddings[indices]

    sims = []
    pair_details = []
    for a_id, b_id, rating in GROUND_TRUTH:
        embs_a = article_claim_embs[a_id]
        embs_b = article_claim_embs[b_id]

        # For each claim in A, find best match in B
        max_sims_a = []
        for ea in embs_a:
            best = max(cosine_sim(ea, eb) for eb in embs_b)
            max_sims_a.append(best)

        # For each claim in B, find best match in A
        max_sims_b = []
        for eb in embs_b:
            best = max(cosine_sim(eb, ea) for ea in embs_a)
            max_sims_b.append(best)

        # Average top-3 from each direction, then average both directions
        all_maxsims = sorted(max_sims_a + max_sims_b, reverse=True)
        top_k = min(3, len(all_maxsims))
        sim = np.mean(all_maxsims[:top_k])

        sims.append(sim)
        pair_details.append({
            "a": a_id, "b": b_id, "rating": rating,
            "similarity": round(float(sim), 4),
        })

    result_9 = evaluate_strategy(sims, ratings)
    result_9["pairs"] = pair_details
    all_results["9_maxsim_claims_top3"] = result_9
    print(f"  Accuracy: {result_9['accuracy']:.1%} (threshold={result_9['threshold']:.3f})")
    print(f"  Spearman ρ: {result_9['spearman_rho']:.4f} (p={result_9['spearman_p']:.4f})")

    # Also try top-1 and top-5 variants
    for top_k_val in [1, 5]:
        variant_name = f"9_maxsim_claims_top{top_k_val}"
        print(f"\nStrategy: {variant_name}")
        sims_v = []
        pair_details_v = []
        for a_id, b_id, rating in GROUND_TRUTH:
            embs_a = article_claim_embs[a_id]
            embs_b = article_claim_embs[b_id]

            max_sims_a = [max(cosine_sim(ea, eb) for eb in embs_b) for ea in embs_a]
            max_sims_b = [max(cosine_sim(eb, ea) for ea in embs_a) for eb in embs_b]

            all_maxsims = sorted(max_sims_a + max_sims_b, reverse=True)
            k = min(top_k_val, len(all_maxsims))
            sim = np.mean(all_maxsims[:k])

            sims_v.append(sim)
            pair_details_v.append({
                "a": a_id, "b": b_id, "rating": rating,
                "similarity": round(float(sim), 4),
            })

        result_v = evaluate_strategy(sims_v, ratings)
        result_v["pairs"] = pair_details_v
        all_results[variant_name] = result_v
        print(f"  Accuracy: {result_v['accuracy']:.1%} (threshold={result_v['threshold']:.3f})")
        print(f"  Spearman ρ: {result_v['spearman_rho']:.4f} (p={result_v['spearman_p']:.4f})")

    # ---------- Save results ----------
    output_path = Path(__file__).resolve().parent / "embedding_strategy_comparison.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {output_path}")

    # ---------- Final comparison table ----------
    print("\n" + "=" * 90)
    print(f"{'Strategy':<35} {'Accuracy':>10} {'Threshold':>10} {'Spearman ρ':>12} {'p-value':>10}")
    print("-" * 90)

    # Sort by accuracy desc, then spearman desc
    sorted_strategies = sorted(
        all_results.items(),
        key=lambda x: (x[1]["accuracy"], x[1]["spearman_rho"]),
        reverse=True,
    )

    for name, res in sorted_strategies:
        extra = ""
        if "w_summary" in res:
            extra = f" [s={res['w_summary']},c={res['w_claims']}]"
        print(
            f"  {name + extra:<33} {res['accuracy']:>9.1%} {res['threshold']:>10.3f} "
            f"{res['spearman_rho']:>11.4f} {res['spearman_p']:>10.4f}"
        )

    print("=" * 90)

    # ---------- Error analysis for top strategy ----------
    best_name, best_res = sorted_strategies[0]
    print(f"\nError analysis for best strategy: {best_name}")
    print(f"  Threshold: {best_res['threshold']:.3f}")
    print()

    for p in best_res["pairs"]:
        a = articles_by_id[p["a"]]
        b = articles_by_id[p["b"]]
        predicted = 1 if p["similarity"] >= best_res["threshold"] else 0
        actual = 1 if p["rating"] >= 1 else 0
        status = "OK" if predicted == actual else "MISS"
        if status == "MISS":
            print(f"  {status} sim={p['similarity']:.3f} rating={p['rating']}")
            print(f"       A: {a['title'][:60]}")
            print(f"       B: {b['title'][:60]}")
            print()


if __name__ == "__main__":
    main()

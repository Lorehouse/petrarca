#!/usr/bin/env python3
"""Embed curriculum node descriptions and map article claims to curriculum nodes.

Uses amygdala MiniLM (same 384d model as article claim embeddings) to:
1. Generate embeddings for all curriculum node descriptions
2. Compute cosine similarity between article claims and curriculum nodes
3. Output mappings usable by the knowledge index and client

Usage:
    python3 scripts/build_curriculum_embeddings.py              # embed + map
    python3 scripts/build_curriculum_embeddings.py --embed-only  # just embed nodes
    python3 scripts/build_curriculum_embeddings.py --stats       # show coverage stats
"""

import json
import sys
import time
import argparse
from pathlib import Path
from collections import defaultdict

import numpy as np

from amygdala import EmbeddingModel, pairwise_cosine

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
ARTICLES_PATH = DATA_DIR / "articles.json"
CLAIM_EMBEDDINGS_PATH = DATA_DIR / "claim_embeddings.npz"
CLAIMS_INDEX_PATH = DATA_DIR / "claims_index.json"

# Curricula live on the server; when running locally, point to local copies
CURRICULA_DIR = Path("/opt/petrarca/data/curricula")
if not CURRICULA_DIR.exists():
    CURRICULA_DIR = Path("/tmp/curricula")  # fallback for local dev

# Threshold for claim→node mapping (lower than claim-claim 0.74 because
# node descriptions are broader summaries, not atomic claims)
THRESHOLD_CLAIM_TO_NODE = 0.45

EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


def log(msg: str):
    print(msg, file=sys.stderr)


def load_curricula() -> list[dict]:
    """Load all curriculum files from the curricula directory."""
    curricula = []
    for path in sorted(CURRICULA_DIR.glob("*.json")):
        if path.stem.startswith(("knowledge_", "elicit_", "mappings_", "self_report_", "cross_curriculum", "embeddings_")):
            continue
        try:
            with open(path) as f:
                data = json.load(f)
            if "nodes" in data:
                curricula.append(data)
        except Exception as e:
            log(f"  Warning: could not load {path.name}: {e}")
    return curricula


def embed_curriculum_nodes(curricula: list[dict]) -> tuple[np.ndarray, list[dict]]:
    """Embed all curriculum node descriptions using amygdala MiniLM.

    Returns (embeddings array, flat list of node metadata).
    Embedding text: "{title}: {description}" for each node.
    """
    model = EmbeddingModel(model_name=EMBEDDING_MODEL_NAME)

    all_nodes = []
    texts = []
    for cur in curricula:
        domain_id = cur["id"]
        for node in cur["nodes"]:
            text = f"{node['title']}: {node['description']}"
            texts.append(text)
            all_nodes.append({
                "id": node["id"],
                "title": node["title"],
                "domain_id": domain_id,
                "level": node.get("level", 1),
                "date_start": node.get("date_start"),
                "date_end": node.get("date_end"),
            })

    log(f"  Embedding {len(texts)} curriculum nodes with {EMBEDDING_MODEL_NAME}...")
    t0 = time.time()
    embeddings = model.embed_batch(texts)
    elapsed = time.time() - t0
    log(f"  Embedded {len(texts)} nodes in {elapsed:.1f}s")

    return embeddings, all_nodes


def save_curriculum_embeddings(embeddings: np.ndarray, nodes: list[dict]):
    """Save embeddings and node index."""
    emb_path = CURRICULA_DIR / "curriculum_embeddings.npz"
    idx_path = CURRICULA_DIR / "curriculum_embeddings_index.json"

    np.savez_compressed(emb_path, embeddings=embeddings)
    with open(idx_path, "w") as f:
        json.dump(nodes, f, indent=2)

    log(f"  Saved {emb_path} ({embeddings.shape})")
    log(f"  Saved {idx_path} ({len(nodes)} nodes)")


def load_article_claims_and_embeddings() -> tuple[list[dict], np.ndarray]:
    """Load article claims and their MiniLM embeddings."""
    if not CLAIM_EMBEDDINGS_PATH.exists():
        log("ERROR: No claim embeddings found. Run build_claim_embeddings.py first.")
        sys.exit(1)

    with open(ARTICLES_PATH) as f:
        articles = json.load(f)

    claims = []
    for article in articles:
        article_id = article.get("id", "")
        article_title = article.get("title", "")
        for claim in article.get("atomic_claims", []):
            claims.append({
                "id": claim["id"],
                "text": claim["normalized_text"],
                "article_id": article_id,
                "article_title": article_title,
                "topics": claim.get("topics", []),
            })

    embeddings = np.load(CLAIM_EMBEDDINGS_PATH)["embeddings"]
    if len(embeddings) != len(claims):
        log(f"ERROR: Embedding count ({len(embeddings)}) != claim count ({len(claims)})")
        sys.exit(1)

    return claims, embeddings


def map_claims_to_nodes(
    claim_embeddings: np.ndarray,
    node_embeddings: np.ndarray,
    claims: list[dict],
    nodes: list[dict],
    threshold: float = THRESHOLD_CLAIM_TO_NODE,
) -> dict:
    """Compute claim→node mappings via cosine similarity.

    Returns a dict with:
    - node_claims: {domain_id: {node_id: [{claim_id, similarity, article_id}]}}
    - article_nodes: {article_id: [{node_id, domain_id, node_title, count, avg_similarity}]}
    """
    log(f"  Computing {len(claims)} claims × {len(nodes)} nodes similarity...")
    t0 = time.time()

    # Compute cross-source cosine similarity matrix
    # Shape: (n_claims, n_nodes)
    # Normalize both sets
    claim_norms = claim_embeddings / np.linalg.norm(claim_embeddings, axis=1, keepdims=True)
    node_norms = node_embeddings / np.linalg.norm(node_embeddings, axis=1, keepdims=True)
    sim_matrix = claim_norms @ node_norms.T

    elapsed = time.time() - t0
    log(f"  Similarity matrix computed in {elapsed:.1f}s")

    # Extract mappings above threshold
    node_claims = defaultdict(lambda: defaultdict(list))
    article_node_hits = defaultdict(lambda: defaultdict(list))

    for claim_idx in range(len(claims)):
        claim = claims[claim_idx]
        for node_idx in range(len(nodes)):
            sim = float(sim_matrix[claim_idx, node_idx])
            if sim >= threshold:
                node = nodes[node_idx]
                domain_id = node["domain_id"]
                node_id = node["id"]

                node_claims[domain_id][node_id].append({
                    "claim_id": claim["id"],
                    "similarity": round(sim, 3),
                    "article_id": claim["article_id"],
                })

                article_node_hits[claim["article_id"]][(domain_id, node_id)].append(sim)

    # Aggregate article→node mappings
    article_nodes = {}
    for article_id, node_hit_map in article_node_hits.items():
        nodes_list = []
        for (domain_id, node_id), sims in node_hit_map.items():
            node_meta = next((n for n in nodes if n["id"] == node_id), {})
            nodes_list.append({
                "node_id": node_id,
                "domain_id": domain_id,
                "node_title": node_meta.get("title", ""),
                "claim_count": len(sims),
                "avg_similarity": round(sum(sims) / len(sims), 3),
                "max_similarity": round(max(sims), 3),
            })
        # Sort by claim count (most relevant nodes first)
        nodes_list.sort(key=lambda x: (-x["claim_count"], -x["max_similarity"]))
        article_nodes[article_id] = nodes_list[:10]  # top 10 nodes per article

    # Count stats
    total_mappings = sum(
        len(claims_list)
        for domain in node_claims.values()
        for claims_list in domain.values()
    )
    articles_with_nodes = len(article_nodes)
    nodes_with_claims = sum(
        len(domain) for domain in node_claims.values()
    )

    log(f"  Mappings: {total_mappings} claim→node links")
    log(f"  Articles with curriculum nodes: {articles_with_nodes}")
    log(f"  Curriculum nodes with article claims: {nodes_with_claims}/{len(nodes)}")

    return {
        "node_claims": {d: dict(nc) for d, nc in node_claims.items()},
        "article_nodes": article_nodes,
        "stats": {
            "total_mappings": total_mappings,
            "articles_with_nodes": articles_with_nodes,
            "nodes_with_claims": nodes_with_claims,
            "total_nodes": len(nodes),
            "threshold": threshold,
        }
    }


def print_stats(mappings: dict, nodes: list[dict], claims: list[dict]):
    """Print coverage statistics."""
    stats = mappings["stats"]
    print(f"\n=== Curriculum ↔ Article Mapping Stats ===")
    print(f"Threshold: {stats['threshold']}")
    print(f"Total claim→node links: {stats['total_mappings']}")
    print(f"Articles with curriculum coverage: {stats['articles_with_nodes']}/{len(set(c['article_id'] for c in claims))}")
    print(f"Curriculum nodes with articles: {stats['nodes_with_claims']}/{stats['total_nodes']}")

    # Top articles by curriculum coverage
    print(f"\nTop articles by curriculum node coverage:")
    article_titles = {c["article_id"]: c["article_title"] for c in claims}
    sorted_articles = sorted(
        mappings["article_nodes"].items(),
        key=lambda x: len(x[1]),
        reverse=True
    )
    for article_id, nodes_list in sorted_articles[:10]:
        title = article_titles.get(article_id, article_id)[:60]
        node_names = [n["node_title"][:30] for n in nodes_list[:3]]
        print(f"  {title}")
        print(f"    → {len(nodes_list)} nodes: {', '.join(node_names)}")

    # Nodes with most article coverage
    print(f"\nCurriculum nodes with most article claims:")
    for domain_id, domain_nodes in mappings["node_claims"].items():
        sorted_nodes = sorted(domain_nodes.items(), key=lambda x: len(x[1]), reverse=True)
        for node_id, node_claims in sorted_nodes[:5]:
            node_meta = next((n for n in nodes if n["id"] == node_id), {})
            unique_articles = len(set(c["article_id"] for c in node_claims))
            print(f"  [{domain_id[:15]}] {node_meta.get('title', node_id)[:40]}: {len(node_claims)} claims from {unique_articles} articles")


def main():
    parser = argparse.ArgumentParser(description="Embed curriculum nodes and map to article claims")
    parser.add_argument("--embed-only", action="store_true", help="Only embed nodes, don't map claims")
    parser.add_argument("--stats", action="store_true", help="Show detailed coverage stats")
    parser.add_argument("--threshold", type=float, default=THRESHOLD_CLAIM_TO_NODE, help="Similarity threshold")
    args = parser.parse_args()

    # Load curricula
    log("Loading curricula...")
    curricula = load_curricula()
    if not curricula:
        log("ERROR: No curricula found")
        sys.exit(1)
    log(f"  Loaded {len(curricula)} curricula: {', '.join(c['title'][:30] for c in curricula)}")

    # Embed curriculum nodes
    log("Embedding curriculum nodes...")
    node_embeddings, nodes = embed_curriculum_nodes(curricula)
    save_curriculum_embeddings(node_embeddings, nodes)

    if args.embed_only:
        log("Done (embed-only mode)")
        return

    # Load article claims + embeddings
    log("Loading article claims and embeddings...")
    claims, claim_embeddings = load_article_claims_and_embeddings()
    log(f"  {len(claims)} claims, {claim_embeddings.shape}")

    # Map claims to curriculum nodes
    log("Mapping claims to curriculum nodes...")
    mappings = map_claims_to_nodes(
        claim_embeddings, node_embeddings, claims, nodes,
        threshold=args.threshold
    )

    # Save mappings
    output_path = CURRICULA_DIR / "article_curriculum_mappings.json"
    with open(output_path, "w") as f:
        json.dump(mappings, f, indent=2)
    log(f"  Saved {output_path}")

    if args.stats:
        print_stats(mappings, nodes, claims)


if __name__ == "__main__":
    main()

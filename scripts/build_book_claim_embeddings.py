"""Build embeddings for book claims (from research + captures) and compute cross-source matches.

Embeds book claims in the same vector space as article claims (Gemini embedding-001),
enabling cross-source similarity matching between books and articles.

Usage:
    python3 scripts/build_book_claim_embeddings.py              # incremental embed
    python3 scripts/build_book_claim_embeddings.py --force       # re-embed everything
    python3 scripts/build_book_claim_embeddings.py --cross-match # embed + cross-match with articles
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"

BOOK_EMBEDDINGS_PATH = DATA_DIR / "book_claim_embeddings.npz"
BOOK_CLAIMS_INDEX_PATH = DATA_DIR / "book_claims_index.json"
ARTICLE_EMBEDDINGS_PATH = DATA_DIR / "claim_embeddings.npz"
ARTICLE_CLAIMS_INDEX_PATH = DATA_DIR / "claims_index.json"
CROSS_MATCHES_PATH = DATA_DIR / "book_article_connections.json"

EMBEDDING_MODEL = "models/gemini-embedding-001"
BATCH_SIZE = 100

EXTENDS_THRESHOLD = 0.68
KNOWN_THRESHOLD = 0.78

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_KEY")


def log(msg: str):
    print(f"[book-embeddings] {msg}", flush=True)


def collect_book_claims() -> list[dict]:
    """Collect all claims from book research files and capture files."""
    from book_research_agent import get_all_book_claims
    claims = get_all_book_claims()
    log(f"  {len(claims)} claims from research files")
    return claims


def embed_claims(claims: list[dict], batch_size: int = BATCH_SIZE) -> np.ndarray:
    """Embed claims using Gemini embedding API."""
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)

    texts = [c['text'] for c in claims]
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        log(f"  Embedding batch {i // batch_size + 1}/{(len(texts) + batch_size - 1) // batch_size} ({len(batch)} claims)")

        result = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=batch,
            task_type="SEMANTIC_SIMILARITY",
        )
        all_embeddings.extend(result['embedding'])

        if i + batch_size < len(texts):
            time.sleep(0.5)

    return np.array(all_embeddings, dtype=np.float32)


def compute_cross_source_matches(book_embeddings: np.ndarray,
                                  book_claims: list[dict],
                                  article_embeddings: np.ndarray,
                                  article_claims: list[dict]) -> list[dict]:
    """Find book claims that match article claims above EXTENDS threshold."""
    # Normalize embeddings for cosine similarity
    book_norm = book_embeddings / np.linalg.norm(book_embeddings, axis=1, keepdims=True)
    article_norm = article_embeddings / np.linalg.norm(article_embeddings, axis=1, keepdims=True)

    # Compute similarity matrix (book_claims x article_claims)
    similarity = book_norm @ article_norm.T

    matches = []
    for i in range(len(book_claims)):
        for j in range(len(article_claims)):
            score = float(similarity[i, j])
            if score >= EXTENDS_THRESHOLD:
                matches.append({
                    'book_claim_id': book_claims[i]['id'],
                    'book_claim_text': book_claims[i]['text'],
                    'book_id': book_claims[i]['book_id'],
                    'book_title': book_claims[i].get('book_title', ''),
                    'chapter_number': book_claims[i].get('chapter_number', ''),
                    'article_claim_id': article_claims[j]['id'],
                    'article_claim_text': article_claims[j]['text'],
                    'article_id': article_claims[j].get('article_id', ''),
                    'similarity': round(score, 4),
                    'relationship': 'known' if score >= KNOWN_THRESHOLD else 'extends',
                })

    matches.sort(key=lambda x: x['similarity'], reverse=True)
    return matches


def main():
    parser = argparse.ArgumentParser(description="Build book claim embeddings")
    parser.add_argument("--force", action="store_true", help="Re-embed all claims")
    parser.add_argument("--cross-match", action="store_true",
                        help="Also compute cross-source matches with article claims")
    args = parser.parse_args()

    log("=== Building Book Claim Embeddings ===")

    # Collect claims
    log("Collecting book claims...")
    claims = collect_book_claims()

    if not claims:
        log("No book claims found. Add books and run research first.")
        sys.exit(0)

    log(f"  {len(claims)} total book claims")

    # Check for incremental mode
    existing_claims = []
    existing_embeddings = None
    if not args.force and BOOK_EMBEDDINGS_PATH.exists() and BOOK_CLAIMS_INDEX_PATH.exists():
        log("Loading existing embeddings for incremental update...")
        existing_embeddings = np.load(BOOK_EMBEDDINGS_PATH)['embeddings']
        existing_claims = json.loads(BOOK_CLAIMS_INDEX_PATH.read_text())
        existing_ids = {c['id'] for c in existing_claims}
        new_claims = [c for c in claims if c['id'] not in existing_ids]
        log(f"  {len(existing_claims)} existing, {len(new_claims)} new")

        if not new_claims:
            log("No new claims to embed.")
            if args.cross_match:
                log("Running cross-match with existing embeddings...")
            else:
                return
        else:
            claims_to_embed = new_claims
    else:
        claims_to_embed = claims
        log(f"  Embedding all {len(claims_to_embed)} claims (force={args.force})")

    # Embed new claims
    if claims_to_embed:
        if not GEMINI_API_KEY:
            log("ERROR: No GEMINI_API_KEY set")
            sys.exit(1)

        log(f"Embedding {len(claims_to_embed)} claims...")
        new_embeddings = embed_claims(claims_to_embed)

        # Merge with existing
        if existing_embeddings is not None and not args.force:
            # Build new index matching current claims order
            existing_id_to_idx = {c['id']: i for i, c in enumerate(existing_claims)}
            all_embeddings = []
            new_idx = 0
            for c in claims:
                if c['id'] in existing_id_to_idx:
                    all_embeddings.append(existing_embeddings[existing_id_to_idx[c['id']]])
                else:
                    all_embeddings.append(new_embeddings[new_idx])
                    new_idx += 1
            embeddings = np.array(all_embeddings, dtype=np.float32)
        else:
            embeddings = new_embeddings
    else:
        embeddings = existing_embeddings

    # Save
    log(f"Saving embeddings: {embeddings.shape}")
    np.savez_compressed(BOOK_EMBEDDINGS_PATH, embeddings=embeddings)
    BOOK_CLAIMS_INDEX_PATH.write_text(json.dumps(claims, indent=2, ensure_ascii=False))

    file_size = BOOK_EMBEDDINGS_PATH.stat().st_size
    log(f"  {file_size:,} bytes ({file_size / 1024:.1f} KB)")

    # Cross-source matching
    if args.cross_match:
        log("Computing cross-source matches...")

        if not ARTICLE_EMBEDDINGS_PATH.exists():
            log("  No article embeddings found, skipping cross-match")
            return

        article_embeddings = np.load(ARTICLE_EMBEDDINGS_PATH)['embeddings']
        article_claims = json.loads(ARTICLE_CLAIMS_INDEX_PATH.read_text())
        log(f"  {len(article_claims)} article claims loaded")

        matches = compute_cross_source_matches(
            embeddings, claims, article_embeddings, article_claims
        )
        log(f"  {len(matches)} cross-source matches found (>= {EXTENDS_THRESHOLD})")

        # Aggregate by book
        by_book = {}
        for m in matches:
            bid = m['book_id']
            if bid not in by_book:
                by_book[bid] = {'book_id': bid, 'book_title': m['book_title'], 'matches': []}
            by_book[bid]['matches'].append(m)

        output = {
            'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'total_matches': len(matches),
            'books': list(by_book.values()),
        }

        CROSS_MATCHES_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False))
        log(f"  Written to {CROSS_MATCHES_PATH}")

        # Summary
        for bid, bdata in by_book.items():
            extends = sum(1 for m in bdata['matches'] if m['relationship'] == 'extends')
            known = sum(1 for m in bdata['matches'] if m['relationship'] == 'known')
            unique_articles = len(set(m['article_id'] for m in bdata['matches']))
            log(f"  {bdata['book_title']}: {len(bdata['matches'])} matches "
                f"({extends} extends, {known} known) across {unique_articles} articles")

    log("Done.")


if __name__ == '__main__':
    main()

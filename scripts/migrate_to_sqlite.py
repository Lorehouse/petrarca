#!/usr/bin/env python3
"""One-time migration: read existing JSON files and populate SQLite tables.

Usage:
    PETRARCA_DB=data/petrarca_content.db python3 scripts/migrate_to_sqlite.py
    python3 scripts/migrate_to_sqlite.py --db data/petrarca_content.db
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"

sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, '/opt/limbic')
sys.path.insert(0, str(Path.home() / 'src' / 'limbic'))

from db import init_db, get_connection


def log(msg: str):
    print(f"[migrate] {msg}", flush=True)


# --- Article JSON field list (order matters for export fidelity) ---
# Fields that are always present in every article
ARTICLE_ALWAYS_FIELDS = [
    'id', 'title', 'author', 'source_url', 'hostname', 'date',
    'content_markdown', 'one_line_summary', 'full_summary',
    'key_claims', 'topics', 'interest_topics', 'novelty_claims',
    'entities', 'estimated_read_minutes', 'content_type', 'word_count',
    'sources', 'follow_up_questions',
]

# Fields that only exist on some articles (optional)
ARTICLE_OPTIONAL_FIELDS = [
    'fetch_method', 'exploration_tag', 'parent_id',
    'exploration_tier', 'exploration_order', 'ingested_at',
    'similar_articles',
]

# Fields stored as JSON text in SQLite
ARTICLE_JSON_FIELDS = {
    'key_claims', 'topics', 'interest_topics', 'novelty_claims',
    'entities', 'sources', 'follow_up_questions', 'similar_articles',
}


def migrate_articles(conn, articles_path: Path):
    """Migrate articles.json → articles + article_sections + atomic_claims."""
    if not articles_path.exists():
        log(f"No {articles_path.name} found, skipping")
        return 0

    articles = json.loads(articles_path.read_text())
    log(f"Migrating {len(articles)} articles...")

    conn.execute("DELETE FROM atomic_claims")
    conn.execute("DELETE FROM article_sections")
    conn.execute("DELETE FROM articles")

    for i, a in enumerate(articles):
        # Build column values — always fields
        values = {
            'id': a['id'],
            'title': a.get('title', ''),
            'author': a.get('author', ''),
            'source_url': a.get('source_url', ''),
            'hostname': a.get('hostname', ''),
            'date': a.get('date', ''),
            'content_markdown': a.get('content_markdown', ''),
            'one_line_summary': a.get('one_line_summary', ''),
            'full_summary': a.get('full_summary', ''),
            'estimated_read_minutes': a.get('estimated_read_minutes', 0),
            'content_type': a.get('content_type', 'unknown'),
            'word_count': a.get('word_count', 0),
        }

        # JSON array fields — store NULL if absent (not '[]') so export skips them
        for field in ARTICLE_JSON_FIELDS:
            if field in a:
                values[field] = json.dumps(a[field], ensure_ascii=False)
            elif field in ('similar_articles', 'entities', 'follow_up_questions',
                           'interest_topics', 'novelty_claims'):
                values[field] = None
            else:
                values[field] = '[]'

        # Optional scalar fields
        for field in ARTICLE_OPTIONAL_FIELDS:
            if field in ARTICLE_JSON_FIELDS:
                continue  # already handled
            if field in a:
                values[field] = a[field]
            else:
                values[field] = None

        cols = ', '.join(values.keys())
        placeholders = ', '.join(['?'] * len(values))
        conn.execute(f"INSERT INTO articles ({cols}) VALUES ({placeholders})", list(values.values()))

        # Sections
        for si, sec in enumerate(a.get('sections', [])):
            conn.execute(
                "INSERT INTO article_sections (article_id, section_index, heading, content, summary, key_claims) VALUES (?, ?, ?, ?, ?, ?)",
                (a['id'], si, sec.get('heading', ''), sec.get('content', ''),
                 sec.get('summary', ''), json.dumps(sec.get('key_claims', []), ensure_ascii=False)),
            )

        # Atomic claims (composite PK: article_id + id)
        for claim in a.get('atomic_claims', []):
            conn.execute(
                "INSERT INTO atomic_claims (id, article_id, normalized_text, original_text, claim_type, source_paragraphs, topics) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (claim['id'], a['id'], claim.get('normalized_text', ''),
                 claim.get('original_text', ''), claim.get('claim_type', 'factual'),
                 json.dumps(claim.get('source_paragraphs', [])),
                 json.dumps(claim.get('topics', []), ensure_ascii=False)),
            )

    conn.commit()
    log(f"  {len(articles)} articles migrated")
    return len(articles)


def migrate_knowledge_index(conn, ki_path: Path):
    """Migrate knowledge_index.json → multiple tables."""
    if not ki_path.exists():
        log(f"No {ki_path.name} found, skipping")
        return

    ki = json.loads(ki_path.read_text())
    log(f"Migrating knowledge index (v{ki.get('version', '?')})...")

    # Pipeline meta
    conn.execute("DELETE FROM pipeline_meta")
    for key in ('version', 'generated_at'):
        if key in ki:
            conn.execute(
                "INSERT INTO pipeline_meta (key, value) VALUES (?, ?)",
                (f"knowledge_index_{key}", str(ki[key])),
            )
    if ki.get('stats'):
        conn.execute(
            "INSERT INTO pipeline_meta (key, value) VALUES (?, ?)",
            ("knowledge_index_stats", json.dumps(ki['stats'])),
        )

    # Claim similarities
    conn.execute("DELETE FROM claim_similarities")
    sims = ki.get('similarities', [])
    if sims:
        conn.executemany(
            "INSERT INTO claim_similarities (claim_a, claim_b, score) VALUES (?, ?, ?)",
            [(p['a'], p['b'], p['score']) for p in sims],
        )
    log(f"  {len(sims)} claim similarity pairs")

    # NLI verdicts
    conn.execute("DELETE FROM nli_verdicts")
    verdicts = ki.get('nli_verdicts', {})
    if verdicts:
        rows = []
        for key, verdict in verdicts.items():
            parts = key.split('::')
            if len(parts) == 2:
                rows.append((parts[0], parts[1], verdict))
        conn.executemany(
            "INSERT INTO nli_verdicts (claim_a, claim_b, verdict) VALUES (?, ?, ?)",
            rows,
        )
    log(f"  {len(verdicts)} NLI verdicts")

    # Article similarities
    conn.execute("DELETE FROM article_similarities")
    asims = ki.get('article_similarities', [])
    if asims:
        conn.executemany(
            "INSERT INTO article_similarities (article_a, article_b, score) VALUES (?, ?, ?)",
            [(p['a'], p['b'], p['score']) for p in asims],
        )
    log(f"  {len(asims)} article similarity pairs")

    # Article novelty matrix
    conn.execute("DELETE FROM article_novelty_matrix")
    anm = ki.get('article_novelty_matrix', {})
    rows = []
    for target_id, read_map in anm.items():
        for read_id, counts in read_map.items():
            rows.append((target_id, read_id, counts['new'], counts['extends'], counts['known']))
    if rows:
        conn.executemany(
            "INSERT INTO article_novelty_matrix (target_article_id, read_article_id, new_count, extends_count, known_count) VALUES (?, ?, ?, ?, ?)",
            rows,
        )
    log(f"  {len(rows)} novelty matrix entries")

    # Paragraph claim map
    conn.execute("DELETE FROM paragraph_claim_map")
    pmap = ki.get('paragraph_map', {})
    rows = []
    for article_id, para_map in pmap.items():
        for para_idx_str, claim_ids in para_map.items():
            for claim_id in claim_ids:
                rows.append((article_id, int(para_idx_str), claim_id))
    if rows:
        conn.executemany(
            "INSERT INTO paragraph_claim_map (article_id, paragraph_index, claim_id) VALUES (?, ?, ?)",
            rows,
        )
    log(f"  {len(rows)} paragraph-claim mappings")

    # Article curriculum nodes
    conn.execute("DELETE FROM article_curriculum_nodes")
    acn = ki.get('article_curriculum_nodes', {})
    rows = []
    for article_id, nodes in acn.items():
        for node in nodes:
            rows.append((
                article_id,
                node.get('domain_id', node.get('curriculum', '')),
                node['node_id'],
                node.get('node_title', ''),
                node.get('claim_count', 0),
                node.get('avg_similarity', 0),
                node.get('max_similarity', 0),
            ))
    if rows:
        conn.executemany(
            "INSERT INTO article_curriculum_nodes (article_id, domain_id, node_id, node_title, claim_count, avg_similarity, max_similarity) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
    log(f"  {len(rows)} curriculum node mappings")

    # Delta reports
    conn.execute("DELETE FROM delta_reports")
    dr = ki.get('delta_reports', {})
    for topic, report in dr.items():
        conn.execute(
            "INSERT INTO delta_reports (topic, summary, claim_count, article_count, top_claims, subtopics) VALUES (?, ?, ?, ?, ?, ?)",
            (topic, report.get('summary', ''), report.get('claim_count', 0),
             report.get('article_count', 0),
             json.dumps(report.get('top_claims', []), ensure_ascii=False),
             json.dumps(report.get('subtopics'), ensure_ascii=False) if report.get('subtopics') else None),
        )
    log(f"  {len(dr)} delta reports")

    conn.commit()


def migrate_clusters(conn, clusters_path: Path):
    """Migrate concept_clusters.json → concept_clusters + near_duplicates + cluster_meta."""
    if not clusters_path.exists():
        log(f"No {clusters_path.name} found, skipping")
        return

    data = json.loads(clusters_path.read_text())
    log(f"Migrating {len(data.get('clusters', []))} clusters...")

    # Cluster meta
    conn.execute("DELETE FROM cluster_meta")
    for key in ('version', 'generated_at'):
        if key in data:
            conn.execute("INSERT INTO cluster_meta (key, value) VALUES (?, ?)",
                         (key, str(data[key])))
    if data.get('parameters'):
        conn.execute("INSERT INTO cluster_meta (key, value) VALUES (?, ?)",
                     ('parameters', json.dumps(data['parameters'])))
    if data.get('stats'):
        conn.execute("INSERT INTO cluster_meta (key, value) VALUES (?, ?)",
                     ('stats', json.dumps(data['stats'])))

    # Clusters
    conn.execute("DELETE FROM concept_clusters")
    for c in data.get('clusters', []):
        conn.execute(
            """INSERT INTO concept_clusters
               (cluster_id, label, size, articles, core_article_ids, peripheral_article_ids,
                top_topics, total_unique_claims, total_shared_claims, key_shared_claims,
                internal_edges, avg_edge_weight)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (c['cluster_id'], c.get('label', ''), c.get('size', 0),
             json.dumps(c.get('articles', []), ensure_ascii=False),
             json.dumps(c.get('core_article_ids', []), ensure_ascii=False),
             json.dumps(c.get('peripheral_article_ids', []), ensure_ascii=False),
             json.dumps(c.get('top_topics', []), ensure_ascii=False),
             c.get('total_unique_claims', 0), c.get('total_shared_claims', 0),
             json.dumps(c.get('key_shared_claims', []), ensure_ascii=False),
             c.get('internal_edges', 0), c.get('avg_edge_weight', 0)),
        )

    # Near duplicates
    conn.execute("DELETE FROM near_duplicates")
    for nd in data.get('near_duplicates', []):
        conn.execute(
            "INSERT INTO near_duplicates (article_a, article_b, title_a, title_b, known_claims, total_claims_a, overlap_ratio) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (nd['article_a'], nd['article_b'], nd.get('title_a', ''),
             nd.get('title_b', ''), nd.get('known_claims', 0),
             nd.get('total_claims_a', 0), nd.get('overlap_ratio', 0)),
        )

    conn.commit()
    log(f"  {len(data.get('clusters', []))} clusters, {len(data.get('near_duplicates', []))} near-dupes")


def migrate_syntheses(conn, syntheses_path: Path):
    """Migrate syntheses.json → syntheses table."""
    if not syntheses_path.exists():
        log(f"No {syntheses_path.name} found, skipping")
        return

    data = json.loads(syntheses_path.read_text())
    synths = data.get('syntheses', []) if isinstance(data, dict) else data
    log(f"Migrating {len(synths)} syntheses...")

    # Store envelope meta
    if isinstance(data, dict):
        for key in ('version', 'generated_at'):
            if key in data:
                conn.execute(
                    "INSERT OR REPLACE INTO pipeline_meta (key, value) VALUES (?, ?)",
                    (f"syntheses_{key}", str(data[key])),
                )
        if data.get('stats'):
            conn.execute(
                "INSERT OR REPLACE INTO pipeline_meta (key, value) VALUES (?, ?)",
                ("syntheses_stats", json.dumps(data['stats'])),
            )

    conn.execute("DELETE FROM syntheses")
    for s in synths:
        conn.execute(
            """INSERT INTO syntheses
               (cluster_id, label, synthesis_markdown, article_ids, article_coverage,
                claims_covered, unique_per_article, follow_up_questions, tensions,
                generated_at, total_articles, total_claims_covered, total_claims_in_cluster)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(s['cluster_id']), s.get('label', ''), s.get('synthesis_markdown', ''),
             json.dumps(s.get('article_ids', []), ensure_ascii=False),
             json.dumps(s.get('article_coverage', {}), ensure_ascii=False),
             json.dumps(s.get('claims_covered', []), ensure_ascii=False),
             json.dumps(s.get('unique_per_article', {}), ensure_ascii=False),
             json.dumps(s.get('follow_up_questions', []), ensure_ascii=False),
             json.dumps(s.get('tensions', []), ensure_ascii=False),
             s.get('generated_at', ''),
             s.get('total_articles', 0), s.get('total_claims_covered', 0),
             s.get('total_claims_in_cluster', 0)),
        )

    conn.commit()
    log(f"  {len(synths)} syntheses migrated")


def main():
    parser = argparse.ArgumentParser(description='Migrate JSON files to SQLite')
    parser.add_argument('--db', help='Database path (or set PETRARCA_DB env)')
    parser.add_argument('--data-dir', default=str(DATA_DIR), help='Data directory with JSON files')
    args = parser.parse_args()

    if args.db:
        os.environ['PETRARCA_DB'] = args.db

    data_dir = Path(args.data_dir)
    t0 = time.time()

    init_db()
    conn = get_connection()

    try:
        n = migrate_articles(conn, data_dir / 'articles.json')
        migrate_knowledge_index(conn, data_dir / 'knowledge_index.json')
        migrate_clusters(conn, data_dir / 'concept_clusters.json')
        migrate_syntheses(conn, data_dir / 'syntheses.json')
    finally:
        conn.close()

    elapsed = time.time() - t0
    log(f"Migration complete in {elapsed:.1f}s")


if __name__ == '__main__':
    main()

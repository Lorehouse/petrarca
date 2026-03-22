#!/usr/bin/env python3
"""Export SQLite content tables to JSON files for client consumption.

Reads from petrarca.db and produces:
  - articles.json (indent=2, ensure_ascii=False)
  - knowledge_index.json (compact, no indent)
  - concept_clusters.json (indent=2)
  - syntheses.json (indent=2)
  - manifest.json (indent=2, with hashes)

Usage:
    python3 scripts/export_content_json.py
    python3 scripts/export_content_json.py --output-dir data/exported
    python3 scripts/export_content_json.py --db data/petrarca_content.db
"""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"

sys.path.insert(0, str(SCRIPT_DIR))
from db import get_connection


def log(msg: str):
    print(f"[export] {msg}", flush=True)


def _json_col(val, default=None):
    """Parse a JSON text column, returning default if NULL or empty."""
    if val is None:
        return default
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return default


def export_articles(conn) -> list[dict]:
    """Export articles + sections + claims from SQLite, matching original JSON structure."""
    articles = []

    rows = conn.execute(
        "SELECT * FROM articles ORDER BY rowid"
    ).fetchall()

    for row in rows:
        row = dict(row)
        article_id = row['id']

        # Build article dict — base fields always present
        a = {
            'id': row['id'],
            'title': row['title'],
            'author': row['author'],
            'source_url': row['source_url'],
            'hostname': row['hostname'],
            'date': row['date'],
            'content_markdown': row['content_markdown'],
        }

        # Sections
        sec_rows = conn.execute(
            "SELECT heading, content, summary, key_claims FROM article_sections WHERE article_id = ? ORDER BY section_index",
            (article_id,),
        ).fetchall()
        sections = []
        for sr in sec_rows:
            sec = {'heading': sr['heading'], 'content': sr['content']}
            # Always include summary and key_claims (even if empty)
            sec['summary'] = sr['summary'] or ''
            sec['key_claims'] = _json_col(sr['key_claims'], [])
            sections.append(sec)
        a['sections'] = sections

        a['one_line_summary'] = row['one_line_summary']
        a['full_summary'] = row['full_summary']
        a['key_claims'] = _json_col(row['key_claims'], [])
        a['topics'] = _json_col(row['topics'], [])

        # These fields may appear in different positions depending on article
        # We put them in a canonical order; semantic comparison handles the rest
        interest_topics = _json_col(row['interest_topics'], [])
        novelty_claims = _json_col(row['novelty_claims'], [])
        entities = _json_col(row['entities'], [])
        follow_up_questions = _json_col(row['follow_up_questions'], [])

        a['estimated_read_minutes'] = row['estimated_read_minutes']
        a['content_type'] = row['content_type']
        a['word_count'] = row['word_count']
        a['sources'] = _json_col(row['sources'], [])

        # Optional fields — only include if they were stored (non-NULL)
        if row['exploration_tag'] is not None:
            a['exploration_tag'] = row['exploration_tag']
        if row['parent_id'] is not None:
            a['parent_id'] = row['parent_id']
        if row['exploration_tier'] is not None:
            a['exploration_tier'] = row['exploration_tier']
        if row['exploration_order'] is not None:
            a['exploration_order'] = row['exploration_order']
        if row['similar_articles'] is not None:
            a['similar_articles'] = _json_col(row['similar_articles'], [])
        if row['fetch_method'] is not None:
            a['fetch_method'] = row['fetch_method']
        if row['ingested_at'] is not None:
            a['ingested_at'] = row['ingested_at']

        # Atomic claims
        claim_rows = conn.execute(
            "SELECT id, normalized_text, original_text, claim_type, source_paragraphs, topics FROM atomic_claims WHERE article_id = ? ORDER BY rowid",
            (article_id,),
        ).fetchall()
        a['atomic_claims'] = [
            {
                'normalized_text': cr['normalized_text'],
                'original_text': cr['original_text'],
                'claim_type': cr['claim_type'],
                'source_paragraphs': _json_col(cr['source_paragraphs'], []),
                'topics': _json_col(cr['topics'], []),
                'id': cr['id'],
            }
            for cr in claim_rows
        ]

        # Remaining always-present fields
        a['entities'] = entities
        a['follow_up_questions'] = follow_up_questions
        a['interest_topics'] = interest_topics
        a['novelty_claims'] = novelty_claims

        articles.append(a)

    return articles


def _normalize_topic(topic: str) -> str:
    """Normalize topic: hyphens to spaces, lowercase, collapse whitespace."""
    import re
    return re.sub(r"\s+", " ", topic.replace("-", " ")).strip().lower()


def export_knowledge_index(conn) -> dict:
    """Export knowledge index from SQLite, matching original JSON structure."""
    ki = {}

    # Pipeline meta
    meta_rows = conn.execute(
        "SELECT key, value FROM pipeline_meta WHERE key LIKE 'knowledge_index_%'"
    ).fetchall()
    meta = {r['key'].replace('knowledge_index_', ''): r['value'] for r in meta_rows}

    ki['version'] = int(meta.get('version', 1))
    ki['generated_at'] = meta.get('generated_at', '')
    ki['stats'] = _json_col(meta.get('stats'), {})

    # Find which articles are in the knowledge index (have paragraph_map entries)
    ki_article_ids = set()
    pm_rows_all = conn.execute(
        "SELECT DISTINCT article_id FROM paragraph_claim_map"
    ).fetchall()
    for r in pm_rows_all:
        ki_article_ids.add(r['article_id'])

    # Claims — only from articles in the knowledge index, with normalized topics.
    # For duplicate claim IDs across articles, the pipeline's dict overwrites with
    # the later article (iteration order), so we do the same: ORDER BY rowid means
    # later articles' claims overwrite earlier ones in the dict.
    claims = {}
    article_claims = {}
    claim_rows = conn.execute(
        "SELECT id, normalized_text, article_id, claim_type, source_paragraphs, topics FROM atomic_claims ORDER BY rowid"
    ).fetchall()
    for cr in claim_rows:
        if cr['article_id'] not in ki_article_ids:
            continue
        raw_topics = _json_col(cr['topics'], [])
        normalized_topics = [_normalize_topic(t) for t in raw_topics]
        claims[cr['id']] = {
            'text': cr['normalized_text'],
            'article_id': cr['article_id'],
            'claim_type': cr['claim_type'],
            'source_paragraphs': _json_col(cr['source_paragraphs'], []),
            'topics': normalized_topics,
        }
        article_claims.setdefault(cr['article_id'], []).append(cr['id'])

    # Note: article_claims keeps a claim ID in BOTH articles even when
    # the claims dict attributes it to only one (the last-seen article).
    # This matches the original pipeline behavior.
    ki['claims'] = claims
    ki['article_claims'] = article_claims

    # Paragraph map — preserve claim order from original insertion
    paragraph_map = {}
    pm_rows = conn.execute(
        "SELECT article_id, paragraph_index, claim_id FROM paragraph_claim_map ORDER BY article_id, paragraph_index, rowid"
    ).fetchall()
    for r in pm_rows:
        article_map = paragraph_map.setdefault(r['article_id'], {})
        para_key = str(r['paragraph_index'])
        article_map.setdefault(para_key, []).append(r['claim_id'])
    ki['paragraph_map'] = paragraph_map

    # Similarities
    sim_rows = conn.execute(
        "SELECT claim_a, claim_b, score FROM claim_similarities ORDER BY rowid"
    ).fetchall()
    ki['similarities'] = [
        {'a': r['claim_a'], 'b': r['claim_b'], 'score': r['score']}
        for r in sim_rows
    ]

    # NLI verdicts
    nli_rows = conn.execute(
        "SELECT claim_a, claim_b, verdict FROM nli_verdicts ORDER BY rowid"
    ).fetchall()
    ki['nli_verdicts'] = {
        f"{r['claim_a']}::{r['claim_b']}": r['verdict']
        for r in nli_rows
    }

    # Article novelty matrix
    anm_rows = conn.execute(
        "SELECT target_article_id, read_article_id, new_count, extends_count, known_count FROM article_novelty_matrix ORDER BY target_article_id, read_article_id"
    ).fetchall()
    anm = {}
    for r in anm_rows:
        target = anm.setdefault(r['target_article_id'], {})
        target[r['read_article_id']] = {
            'new': r['new_count'],
            'extends': r['extends_count'],
            'known': r['known_count'],
        }
    ki['article_novelty_matrix'] = anm

    # Delta reports
    dr_rows = conn.execute(
        "SELECT topic, summary, claim_count, article_count, top_claims, subtopics FROM delta_reports ORDER BY topic"
    ).fetchall()
    delta_reports = {}
    for r in dr_rows:
        entry = {
            'topic': r['topic'],
            'summary': r['summary'],
            'claim_count': r['claim_count'],
            'article_count': r['article_count'],
            'top_claims': _json_col(r['top_claims'], []),
        }
        subtopics = _json_col(r['subtopics'])
        if subtopics is not None:
            entry['subtopics'] = subtopics
        delta_reports[r['topic']] = entry
    ki['delta_reports'] = delta_reports

    # Article similarities (may be empty)
    asim_rows = conn.execute(
        "SELECT article_a, article_b, score FROM article_similarities ORDER BY rowid"
    ).fetchall()
    if asim_rows:
        ki['article_similarities'] = [
            {'a': r['article_a'], 'b': r['article_b'], 'score': r['score']}
            for r in asim_rows
        ]

    # Article curriculum nodes (may be empty)
    acn_rows = conn.execute(
        "SELECT article_id, domain_id, node_id, node_title, claim_count, avg_similarity, max_similarity FROM article_curriculum_nodes ORDER BY article_id, domain_id, node_id"
    ).fetchall()
    if acn_rows:
        acn = {}
        for r in acn_rows:
            acn.setdefault(r['article_id'], []).append({
                'domain_id': r['domain_id'],
                'node_id': r['node_id'],
                'node_title': r['node_title'],
                'claim_count': r['claim_count'],
                'avg_similarity': r['avg_similarity'],
                'max_similarity': r['max_similarity'],
            })
        ki['article_curriculum_nodes'] = acn

    return ki


def export_clusters(conn) -> dict:
    """Export concept clusters from SQLite, matching original JSON structure."""
    # Envelope meta
    meta_rows = conn.execute("SELECT key, value FROM cluster_meta").fetchall()
    meta = {r['key']: r['value'] for r in meta_rows}

    result = {}
    if 'version' in meta:
        result['version'] = int(meta['version'])
    if 'generated_at' in meta:
        result['generated_at'] = meta['generated_at']
    if 'parameters' in meta:
        result['parameters'] = _json_col(meta['parameters'], {})
    if 'stats' in meta:
        result['stats'] = _json_col(meta['stats'], {})

    # Clusters
    cluster_rows = conn.execute(
        "SELECT * FROM concept_clusters ORDER BY cluster_id"
    ).fetchall()
    clusters = []
    for r in cluster_rows:
        r = dict(r)
        clusters.append({
            'cluster_id': r['cluster_id'],
            'label': r['label'],
            'size': r['size'],
            'articles': _json_col(r['articles'], []),
            'core_article_ids': _json_col(r['core_article_ids'], []),
            'peripheral_article_ids': _json_col(r['peripheral_article_ids'], []),
            'top_topics': _json_col(r['top_topics'], []),
            'total_unique_claims': r['total_unique_claims'],
            'total_shared_claims': r['total_shared_claims'],
            'key_shared_claims': _json_col(r['key_shared_claims'], []),
            'internal_edges': r['internal_edges'],
            'avg_edge_weight': r['avg_edge_weight'],
        })
    result['clusters'] = clusters

    # Near duplicates
    nd_rows = conn.execute(
        "SELECT * FROM near_duplicates ORDER BY article_a, article_b"
    ).fetchall()
    result['near_duplicates'] = [
        {
            'article_a': r['article_a'],
            'article_b': r['article_b'],
            'title_a': r['title_a'],
            'title_b': r['title_b'],
            'known_claims': r['known_claims'],
            'total_claims_a': r['total_claims_a'],
            'overlap_ratio': r['overlap_ratio'],
        }
        for r in nd_rows
    ]

    return result


def export_syntheses(conn) -> dict:
    """Export syntheses from SQLite, matching original JSON structure."""
    # Envelope meta
    meta_rows = conn.execute(
        "SELECT key, value FROM pipeline_meta WHERE key LIKE 'syntheses_%'"
    ).fetchall()
    meta = {r['key'].replace('syntheses_', ''): r['value'] for r in meta_rows}

    result = {}
    if 'version' in meta:
        result['version'] = int(meta['version'])
    if 'generated_at' in meta:
        result['generated_at'] = meta['generated_at']
    if 'stats' in meta:
        result['stats'] = _json_col(meta['stats'], {})

    synth_rows = conn.execute(
        "SELECT * FROM syntheses ORDER BY cluster_id"
    ).fetchall()
    syntheses = []
    for r in synth_rows:
        r = dict(r)
        syntheses.append({
            'cluster_id': r['cluster_id'],
            'label': r['label'],
            'synthesis_markdown': r['synthesis_markdown'],
            'article_coverage': _json_col(r['article_coverage'], {}),
            'article_ids': _json_col(r['article_ids'], []),
            'claims_covered': _json_col(r['claims_covered'], []),
            'unique_per_article': _json_col(r['unique_per_article'], {}),
            'follow_up_questions': _json_col(r['follow_up_questions'], []),
            'tensions': _json_col(r['tensions'], []),
            'generated_at': r['generated_at'],
            'total_articles': r['total_articles'],
            'total_claims_covered': r['total_claims_covered'],
            'total_claims_in_cluster': r['total_claims_in_cluster'],
        })
    result['syntheses'] = syntheses

    return result


def write_with_hash(data, path: Path, indent=None, compact=False) -> str:
    """Write JSON and return sha256 hash prefix."""
    if compact:
        text = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    else:
        text = json.dumps(data, indent=indent, ensure_ascii=False)
    path.write_text(text, encoding='utf-8')
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def main():
    parser = argparse.ArgumentParser(description='Export SQLite to JSON files')
    parser.add_argument('--db', help='Database path (or set PETRARCA_DB env)')
    parser.add_argument('--output-dir', default=None, help='Output directory (default: same as DATA_DIR)')
    args = parser.parse_args()

    if args.db:
        os.environ['PETRARCA_DB'] = args.db

    output_dir = Path(args.output_dir) if args.output_dir else DATA_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    conn = get_connection(readonly=True)

    try:
        # Articles
        articles = export_articles(conn)
        h_articles = write_with_hash(articles, output_dir / 'articles.json', indent=2)
        log(f"articles.json: {len(articles)} articles (hash={h_articles})")

        # Knowledge index
        ki = export_knowledge_index(conn)
        h_ki = write_with_hash(ki, output_dir / 'knowledge_index.json', compact=True)
        log(f"knowledge_index.json: {len(ki.get('claims', {}))} claims, "
            f"{len(ki.get('similarities', []))} pairs (hash={h_ki})")

        # Clusters
        clusters = export_clusters(conn)
        h_clusters = write_with_hash(clusters, output_dir / 'concept_clusters.json', indent=2)
        log(f"concept_clusters.json: {len(clusters.get('clusters', []))} clusters (hash={h_clusters})")

        # Syntheses
        syntheses = export_syntheses(conn)
        h_syntheses = write_with_hash(syntheses, output_dir / 'syntheses.json', indent=2)
        log(f"syntheses.json: {len(syntheses.get('syntheses', []))} syntheses (hash={h_syntheses})")

        # Manifest
        manifest = {
            'articles_hash': h_articles,
            'knowledge_index_hash': h_ki,
            'clusters_hash': h_clusters,
            'syntheses_hash': h_syntheses,
        }
        (output_dir / 'manifest.json').write_text(
            json.dumps(manifest, indent=2), encoding='utf-8'
        )
        log(f"manifest.json written")

    finally:
        conn.close()

    elapsed = time.time() - t0
    log(f"Export complete in {elapsed:.1f}s")


if __name__ == '__main__':
    main()

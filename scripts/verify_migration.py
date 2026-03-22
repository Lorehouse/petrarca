#!/usr/bin/env python3
"""Verify SQLite-exported JSON matches original JSON files.

Performs deep semantic comparison (values match, key ordering ignored).

Usage:
    python3 scripts/verify_migration.py
    python3 scripts/verify_migration.py --original data --exported data/exported
    python3 scripts/verify_migration.py --warn-only  # log diffs but exit 0
"""

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"


class Verifier:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, msg: str):
        self.errors.append(msg)
        print(f"  ERROR: {msg}", flush=True)

    def warn(self, msg: str):
        self.warnings.append(msg)
        print(f"  WARN:  {msg}", flush=True)

    def ok(self, msg: str):
        print(f"  OK:    {msg}", flush=True)


def _approx_equal(a, b, tol=1e-6):
    """Compare floats with tolerance."""
    if isinstance(a, float) and isinstance(b, float):
        return abs(a - b) < tol
    return a == b


def _deep_equal(a, b, path="", tol=1e-6):
    """Deep comparison returning list of difference descriptions."""
    diffs = []

    if type(a) != type(b):
        # Allow int/float comparison
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            if not _approx_equal(float(a), float(b), tol):
                diffs.append(f"{path}: {a!r} != {b!r}")
            return diffs
        diffs.append(f"{path}: type mismatch {type(a).__name__} vs {type(b).__name__}")
        return diffs

    if isinstance(a, dict):
        keys_a = set(a.keys())
        keys_b = set(b.keys())
        for k in keys_a - keys_b:
            diffs.append(f"{path}.{k}: missing in exported")
        for k in keys_b - keys_a:
            diffs.append(f"{path}.{k}: extra in exported")
        for k in keys_a & keys_b:
            diffs.extend(_deep_equal(a[k], b[k], f"{path}.{k}", tol))
    elif isinstance(a, list):
        if len(a) != len(b):
            diffs.append(f"{path}: list length {len(a)} vs {len(b)}")
            # Compare up to min length
            for i in range(min(len(a), len(b))):
                diffs.extend(_deep_equal(a[i], b[i], f"{path}[{i}]", tol))
        else:
            for i in range(len(a)):
                diffs.extend(_deep_equal(a[i], b[i], f"{path}[{i}]", tol))
    elif isinstance(a, float):
        if not _approx_equal(a, b, tol):
            diffs.append(f"{path}: {a} != {b}")
    elif a != b:
        if isinstance(a, str) and isinstance(b, str) and len(a) > 100:
            # For long strings, show truncated diff
            diffs.append(f"{path}: strings differ (len {len(a)} vs {len(b)})")
        else:
            diffs.append(f"{path}: {a!r} != {b!r}")

    return diffs


def verify_articles(v: Verifier, orig_path: Path, exp_path: Path):
    print("\n--- Articles ---", flush=True)

    orig = json.loads(orig_path.read_text())
    exp = json.loads(exp_path.read_text())

    if len(orig) != len(exp):
        v.error(f"Count mismatch: {len(orig)} original vs {len(exp)} exported")
        return

    v.ok(f"Count: {len(orig)} articles")

    # Build lookup by ID
    orig_by_id = {a['id']: a for a in orig}
    exp_by_id = {a['id']: a for a in exp}

    missing = set(orig_by_id) - set(exp_by_id)
    extra = set(exp_by_id) - set(orig_by_id)
    if missing:
        v.error(f"Missing articles: {missing}")
    if extra:
        v.error(f"Extra articles: {extra}")

    # Compare each article
    diff_count = 0
    for article_id in sorted(orig_by_id.keys() & exp_by_id.keys()):
        diffs = _deep_equal(orig_by_id[article_id], exp_by_id[article_id],
                            f"article[{article_id}]")
        if diffs:
            diff_count += 1
            if diff_count <= 5:  # Show first 5 articles with diffs
                for d in diffs[:10]:
                    v.error(d)
                if len(diffs) > 10:
                    v.error(f"  ... and {len(diffs) - 10} more diffs in this article")

    if diff_count == 0:
        v.ok("All articles match")
    else:
        v.error(f"{diff_count} articles have differences")

    # Verify order preserved
    orig_ids = [a['id'] for a in orig]
    exp_ids = [a['id'] for a in exp]
    if orig_ids == exp_ids:
        v.ok("Article order preserved")
    else:
        v.warn("Article order differs (not critical)")


def verify_knowledge_index(v: Verifier, orig_path: Path, exp_path: Path):
    print("\n--- Knowledge Index ---", flush=True)

    orig = json.loads(orig_path.read_text())
    exp = json.loads(exp_path.read_text())

    # Version and meta
    if orig.get('version') != exp.get('version'):
        v.error(f"Version: {orig.get('version')} vs {exp.get('version')}")
    else:
        v.ok(f"Version: {orig.get('version')}")

    if orig.get('generated_at') != exp.get('generated_at'):
        v.error(f"generated_at: {orig.get('generated_at')} vs {exp.get('generated_at')}")

    # Stats
    diffs = _deep_equal(orig.get('stats', {}), exp.get('stats', {}), 'stats')
    if diffs:
        for d in diffs:
            v.error(d)
    else:
        v.ok(f"Stats match")

    # Claims
    orig_claims = orig.get('claims', {})
    exp_claims = exp.get('claims', {})
    if len(orig_claims) != len(exp_claims):
        v.error(f"Claim count: {len(orig_claims)} vs {len(exp_claims)}")
    else:
        v.ok(f"Claim count: {len(orig_claims)}")

    claim_diffs = 0
    for cid in sorted(orig_claims.keys() & exp_claims.keys()):
        diffs = _deep_equal(orig_claims[cid], exp_claims[cid], f"claims[{cid}]")
        if diffs:
            claim_diffs += 1
            if claim_diffs <= 3:
                for d in diffs:
                    v.error(d)

    if claim_diffs == 0:
        v.ok("All claims match")
    else:
        v.error(f"{claim_diffs} claims have differences")

    # Article claims
    orig_ac = orig.get('article_claims', {})
    exp_ac = exp.get('article_claims', {})
    if len(orig_ac) != len(exp_ac):
        v.error(f"Article-claims count: {len(orig_ac)} vs {len(exp_ac)}")
    ac_diffs = 0
    for aid in sorted(orig_ac.keys() & exp_ac.keys()):
        if sorted(orig_ac[aid]) != sorted(exp_ac[aid]):
            ac_diffs += 1
            if ac_diffs <= 3:
                v.error(f"article_claims[{aid}]: {len(orig_ac[aid])} vs {len(exp_ac[aid])} claims")
    if ac_diffs == 0:
        v.ok(f"Article-claims match ({len(orig_ac)} articles)")
    else:
        v.error(f"{ac_diffs} article-claim mappings differ")

    # Paragraph map
    orig_pm = orig.get('paragraph_map', {})
    exp_pm = exp.get('paragraph_map', {})
    pm_diffs = _deep_equal(orig_pm, exp_pm, 'paragraph_map')
    if pm_diffs:
        v.error(f"Paragraph map: {len(pm_diffs)} differences")
        for d in pm_diffs[:5]:
            v.error(f"  {d}")
    else:
        v.ok(f"Paragraph map match ({len(orig_pm)} articles)")

    # Similarities
    orig_sims = orig.get('similarities', [])
    exp_sims = exp.get('similarities', [])
    if len(orig_sims) != len(exp_sims):
        v.error(f"Similarities: {len(orig_sims)} vs {len(exp_sims)} pairs")
    else:
        sim_diffs = 0
        for i, (os, es) in enumerate(zip(orig_sims, exp_sims)):
            if os['a'] != es['a'] or os['b'] != es['b'] or not _approx_equal(os['score'], es['score'], 0.001):
                sim_diffs += 1
                if sim_diffs <= 3:
                    v.error(f"similarities[{i}]: {os} vs {es}")
        if sim_diffs == 0:
            v.ok(f"Similarities match ({len(orig_sims)} pairs)")
        else:
            v.error(f"{sim_diffs} similarity pairs differ")

    # NLI verdicts
    orig_nli = orig.get('nli_verdicts', {})
    exp_nli = exp.get('nli_verdicts', {})
    if orig_nli != exp_nli:
        missing = set(orig_nli) - set(exp_nli)
        extra = set(exp_nli) - set(orig_nli)
        diff_vals = {k for k in orig_nli.keys() & exp_nli.keys() if orig_nli[k] != exp_nli[k]}
        v.error(f"NLI verdicts: {len(missing)} missing, {len(extra)} extra, {len(diff_vals)} changed")
    else:
        v.ok(f"NLI verdicts match ({len(orig_nli)} entries)")

    # Article novelty matrix
    orig_anm = orig.get('article_novelty_matrix', {})
    exp_anm = exp.get('article_novelty_matrix', {})
    anm_diffs = _deep_equal(orig_anm, exp_anm, 'article_novelty_matrix')
    if anm_diffs:
        v.error(f"Novelty matrix: {len(anm_diffs)} differences")
        for d in anm_diffs[:5]:
            v.error(f"  {d}")
    else:
        v.ok(f"Novelty matrix match ({len(orig_anm)} targets)")

    # Delta reports
    orig_dr = orig.get('delta_reports', {})
    exp_dr = exp.get('delta_reports', {})
    if orig_dr != exp_dr:
        v.error(f"Delta reports differ: {len(orig_dr)} vs {len(exp_dr)}")
    else:
        v.ok(f"Delta reports match ({len(orig_dr)} topics)")

    # Article similarities (may be absent in original)
    orig_as = orig.get('article_similarities', [])
    exp_as = exp.get('article_similarities', [])
    if len(orig_as) != len(exp_as):
        v.warn(f"Article similarities: {len(orig_as)} vs {len(exp_as)} (may differ if field absent)")
    elif orig_as == exp_as:
        v.ok(f"Article similarities match ({len(orig_as)} pairs)")

    # Article curriculum nodes (may be absent)
    orig_acn = orig.get('article_curriculum_nodes', {})
    exp_acn = exp.get('article_curriculum_nodes', {})
    if orig_acn != exp_acn:
        v.warn(f"Article curriculum nodes: {len(orig_acn)} vs {len(exp_acn)}")
    else:
        v.ok(f"Article curriculum nodes match ({len(orig_acn)} articles)")

    # Check for extra/missing top-level keys
    orig_keys = set(orig.keys())
    exp_keys = set(exp.keys())
    missing_keys = orig_keys - exp_keys
    extra_keys = exp_keys - orig_keys
    if missing_keys:
        v.error(f"Missing top-level keys: {missing_keys}")
    if extra_keys:
        v.warn(f"Extra top-level keys in export: {extra_keys}")


def verify_clusters(v: Verifier, orig_path: Path, exp_path: Path):
    print("\n--- Concept Clusters ---", flush=True)

    orig = json.loads(orig_path.read_text())
    exp = json.loads(exp_path.read_text())

    # Envelope
    for key in ('version', 'generated_at'):
        if orig.get(key) != exp.get(key):
            v.error(f"{key}: {orig.get(key)} vs {exp.get(key)}")

    diffs = _deep_equal(orig.get('parameters', {}), exp.get('parameters', {}), 'parameters')
    if diffs:
        for d in diffs:
            v.error(d)
    else:
        v.ok("Parameters match")

    # Clusters
    orig_clusters = orig.get('clusters', [])
    exp_clusters = exp.get('clusters', [])
    if len(orig_clusters) != len(exp_clusters):
        v.error(f"Cluster count: {len(orig_clusters)} vs {len(exp_clusters)}")
    else:
        cluster_diffs = 0
        for i, (oc, ec) in enumerate(zip(orig_clusters, exp_clusters)):
            diffs = _deep_equal(oc, ec, f"clusters[{i}]")
            if diffs:
                cluster_diffs += 1
                if cluster_diffs <= 3:
                    for d in diffs[:5]:
                        v.error(d)
        if cluster_diffs == 0:
            v.ok(f"All {len(orig_clusters)} clusters match")
        else:
            v.error(f"{cluster_diffs} clusters have differences")

    # Near duplicates
    orig_nd = orig.get('near_duplicates', [])
    exp_nd = exp.get('near_duplicates', [])
    if len(orig_nd) != len(exp_nd):
        v.error(f"Near-dupe count: {len(orig_nd)} vs {len(exp_nd)}")
    else:
        # Compare as sets of (a,b) tuples
        orig_set = {(nd['article_a'], nd['article_b']) for nd in orig_nd}
        exp_set = {(nd['article_a'], nd['article_b']) for nd in exp_nd}
        if orig_set == exp_set:
            v.ok(f"Near duplicates match ({len(orig_nd)} pairs)")
        else:
            v.error(f"Near-dupe pairs differ")


def verify_syntheses(v: Verifier, orig_path: Path, exp_path: Path):
    print("\n--- Syntheses ---", flush=True)

    orig_data = json.loads(orig_path.read_text())
    exp_data = json.loads(exp_path.read_text())

    orig = orig_data.get('syntheses', orig_data) if isinstance(orig_data, dict) else orig_data
    exp = exp_data.get('syntheses', exp_data) if isinstance(exp_data, dict) else exp_data

    if len(orig) != len(exp):
        v.error(f"Synthesis count: {len(orig)} vs {len(exp)}")
        return

    v.ok(f"Count: {len(orig)} syntheses")

    # Compare by cluster_id
    orig_by_id = {str(s['cluster_id']): s for s in orig}
    exp_by_id = {str(s['cluster_id']): s for s in exp}

    synth_diffs = 0
    for cid in sorted(orig_by_id.keys() & exp_by_id.keys()):
        diffs = _deep_equal(orig_by_id[cid], exp_by_id[cid], f"syntheses[{cid}]")
        if diffs:
            synth_diffs += 1
            if synth_diffs <= 3:
                for d in diffs[:5]:
                    v.error(d)
    if synth_diffs == 0:
        v.ok("All syntheses match")
    else:
        v.error(f"{synth_diffs} syntheses have differences")

    # Envelope meta
    for key in ('version', 'generated_at'):
        if isinstance(orig_data, dict) and isinstance(exp_data, dict):
            if orig_data.get(key) != exp_data.get(key):
                v.error(f"Envelope {key}: {orig_data.get(key)} vs {exp_data.get(key)}")


def main():
    parser = argparse.ArgumentParser(description='Verify migration: original vs exported JSON')
    parser.add_argument('--original', default=str(DATA_DIR), help='Original JSON directory')
    parser.add_argument('--exported', default=str(DATA_DIR / 'exported'), help='Exported JSON directory')
    parser.add_argument('--warn-only', action='store_true', help='Exit 0 even with errors')
    args = parser.parse_args()

    orig_dir = Path(args.original)
    exp_dir = Path(args.exported)

    v = Verifier()

    files = [
        ('articles.json', verify_articles),
        ('knowledge_index.json', verify_knowledge_index),
        ('concept_clusters.json', verify_clusters),
        ('syntheses.json', verify_syntheses),
    ]

    for filename, verify_fn in files:
        orig_path = orig_dir / filename
        exp_path = exp_dir / filename
        if not orig_path.exists():
            v.warn(f"{filename}: original not found, skipping")
            continue
        if not exp_path.exists():
            v.error(f"{filename}: exported not found")
            continue
        verify_fn(v, orig_path, exp_path)

    # Summary
    print(f"\n{'=' * 50}", flush=True)
    print(f"Errors:   {len(v.errors)}", flush=True)
    print(f"Warnings: {len(v.warnings)}", flush=True)

    if v.errors:
        print("\nFailed verification!", flush=True)
        if not args.warn_only:
            sys.exit(1)
    else:
        print("\nVerification PASSED!", flush=True)


if __name__ == '__main__':
    main()

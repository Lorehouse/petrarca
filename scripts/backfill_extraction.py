#!/usr/bin/env python3
"""Backfill existing articles with updated extraction prompts.

Re-runs the LLM extraction on all articles using the current prompt from
build_articles.py (insights/patterns focus, gemini-3.1-flash-lite-preview).

Preserves: id, source_url, hostname, date, content_markdown, sources,
           atomic_claims, word_count, fetch_method, ingested_at, author

Re-extracts: title, one_line_summary, full_summary, key_claims, sections,
             topics, interest_topics, novelty_claims, entities,
             follow_up_questions, estimated_read_minutes, content_type

Usage:
    python3 backfill_extraction.py                     # re-extract all
    python3 backfill_extraction.py --limit 5           # test on 5 articles
    python3 backfill_extraction.py --dry-run            # show what would happen
    python3 backfill_extraction.py --workers 5          # parallel workers (default 8)
    python3 backfill_extraction.py --offset 100         # start from article index 100
"""

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

# Load env vars
from dotenv import load_dotenv
load_dotenv(Path.home() / ".env")
load_dotenv(Path(__file__).parent.parent / ".env")

# Bridge GEMINI_KEY -> GEMINI_API_KEY
if os.environ.get("GEMINI_KEY") and not os.environ.get("GEMINI_API_KEY"):
    os.environ["GEMINI_API_KEY"] = os.environ["GEMINI_KEY"]

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
APP_DATA_DIR = PROJECT_DIR / "app" / "data"
DATA_DIR = PROJECT_DIR / "data"
ARTICLES_PATH = APP_DATA_DIR / "articles.json"
BACKUP_DIR = DATA_DIR / "backups"

# Import from sibling modules
sys.path.insert(0, str(SCRIPT_DIR))
from build_articles import (
    _build_article_prompt,
    _call_llm,
    _split_into_sections,
    clean_markdown,
    normalize_interest_topics,
)


def backfill_article(article: dict, index: int, total: int, dry_run: bool = False) -> dict | None:
    """Re-extract LLM fields for a single article. Returns updated article or None on skip/error."""
    title = article.get("title", "Untitled")
    content = article.get("content_markdown", "")

    if not content or len(content.split()) < 30:
        print(f"  [{index}/{total}] SKIP (no/short content): {title[:60]}", file=sys.stderr)
        return None

    if dry_run:
        print(f"  [{index}/{total}] Would re-extract: {title[:60]} ({article.get('word_count', 0)} words)", file=sys.stderr)
        return None

    print(f"  [{index}/{total}] Re-extracting: {title[:60]} ({article.get('word_count', 0)} words)", file=sys.stderr)

    prompt = _build_article_prompt(content, title)
    response = _call_llm(prompt, purpose="backfill")

    if not response:
        print(f"    FAILED: no LLM response", file=sys.stderr)
        return None

    try:
        cleaned = response
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned)
        llm = json.loads(cleaned)
    except json.JSONDecodeError:
        print(f"    FAILED: JSON parse error", file=sys.stderr)
        return None

    # Re-split sections using LLM headings + article content
    section_contents = _split_into_sections(content, llm.get("sections", []))

    # Update LLM-derived fields, preserve everything else
    article["title"] = llm.get("title", title) or title
    article["one_line_summary"] = llm.get("one_line_summary", "")
    article["full_summary"] = llm.get("full_summary", "")
    article["key_claims"] = llm.get("key_claims", [])
    article["sections"] = section_contents
    article["topics"] = llm.get("topics", [])
    article["interest_topics"] = normalize_interest_topics(llm.get("interest_topics", []), article["title"])
    article["novelty_claims"] = llm.get("novelty_claims", [])
    article["entities"] = llm.get("entities", [])
    article["follow_up_questions"] = llm.get("follow_up_questions", [])
    article["estimated_read_minutes"] = llm.get("estimated_read_minutes", max(1, article.get("word_count", 200) // 200))
    article["content_type"] = llm.get("content_type", "unknown")

    n_sections = len(section_contents)
    n_claims = len(article["key_claims"])
    n_novelty = len(article["novelty_claims"])
    print(f"    OK: {article['content_type']}, {n_sections} sections, {n_claims} claims, {n_novelty} novelty", file=sys.stderr)

    return article


def main():
    parser = argparse.ArgumentParser(description="Backfill articles with updated extraction prompts")
    parser.add_argument("--limit", type=int, default=0, help="Max articles to process (0=all)")
    parser.add_argument("--offset", type=int, default=0, help="Start from this article index")
    parser.add_argument("--workers", type=int, default=8, help="Parallel workers (default: 8)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without calling LLM")
    args = parser.parse_args()

    # Load articles
    if not ARTICLES_PATH.exists():
        print(f"ERROR: No articles at {ARTICLES_PATH}", file=sys.stderr)
        sys.exit(1)

    articles = json.loads(ARTICLES_PATH.read_text())
    print(f"Loaded {len(articles)} articles from {ARTICLES_PATH}", file=sys.stderr)

    # Create backup
    if not args.dry_run:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        backup_name = f"articles_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_path = BACKUP_DIR / backup_name
        backup_path.write_text(json.dumps(articles, indent=2, ensure_ascii=False))
        print(f"Backup saved to {backup_path}", file=sys.stderr)

    # Select slice
    to_process = articles[args.offset:]
    if args.limit:
        to_process = to_process[:args.limit]
    print(f"Processing {len(to_process)} articles (offset={args.offset}, limit={args.limit or 'all'})", file=sys.stderr)

    if args.dry_run:
        for i, article in enumerate(to_process):
            backfill_article(article, i + 1 + args.offset, len(articles), dry_run=True)
        return

    # Collect before stats
    before_stats = {
        "avg_claims": sum(len(a.get("key_claims", [])) for a in to_process) / max(1, len(to_process)),
        "with_novelty": sum(1 for a in to_process if a.get("novelty_claims")),
        "with_entities": sum(1 for a in to_process if a.get("entities")),
        "with_follow_up": sum(1 for a in to_process if a.get("follow_up_questions")),
    }

    # Process with thread pool
    updated_count = 0
    failed_count = 0
    skipped_count = 0

    # We need to track index mapping for thread-safe updates
    index_map = {}
    for i, article in enumerate(to_process):
        real_idx = args.offset + i
        index_map[id(article)] = real_idx

    def _process_one(article, local_idx, total):
        return backfill_article(article, local_idx, total)

    max_workers = min(args.workers, len(to_process))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for i, article in enumerate(to_process):
            display_idx = args.offset + i + 1
            future = executor.submit(_process_one, article, display_idx, len(articles))
            futures[future] = (article, args.offset + i)

        for future in as_completed(futures):
            article, real_idx = futures[future]
            try:
                result = future.result()
                if result is not None:
                    # article was modified in-place, also update in main list
                    articles[real_idx] = result
                    updated_count += 1
                else:
                    skipped_count += 1
            except Exception as e:
                print(f"    ERROR on {article.get('title', '')[:40]}: {e}", file=sys.stderr)
                failed_count += 1

            # Save incrementally every 20 articles
            if (updated_count + failed_count) % 20 == 0 and updated_count > 0:
                ARTICLES_PATH.write_text(json.dumps(articles, indent=2, ensure_ascii=False))

    # Final save
    ARTICLES_PATH.write_text(json.dumps(articles, indent=2, ensure_ascii=False))
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    (APP_DATA_DIR / "articles.json").write_text(json.dumps(articles, indent=2, ensure_ascii=False))

    # After stats
    after_stats = {
        "avg_claims": sum(len(a.get("key_claims", [])) for a in to_process) / max(1, len(to_process)),
        "with_novelty": sum(1 for a in to_process if a.get("novelty_claims")),
        "with_entities": sum(1 for a in to_process if a.get("entities")),
        "with_follow_up": sum(1 for a in to_process if a.get("follow_up_questions")),
    }

    print(f"\n=== Backfill Complete ===", file=sys.stderr)
    print(f"  Updated: {updated_count}, Skipped: {skipped_count}, Failed: {failed_count}", file=sys.stderr)
    print(f"\n  Before → After:", file=sys.stderr)
    print(f"    Avg key_claims:     {before_stats['avg_claims']:.1f} → {after_stats['avg_claims']:.1f}", file=sys.stderr)
    print(f"    With novelty_claims: {before_stats['with_novelty']} → {after_stats['with_novelty']}", file=sys.stderr)
    print(f"    With entities:       {before_stats['with_entities']} → {after_stats['with_entities']}", file=sys.stderr)
    print(f"    With follow_up:      {before_stats['with_follow_up']} → {after_stats['with_follow_up']}", file=sys.stderr)

    # Show a few sample comparisons
    print(f"\n=== Sample Results ===", file=sys.stderr)
    shown = 0
    for a in articles[args.offset:args.offset + len(to_process)]:
        if a.get("key_claims") and shown < 3:
            print(f"\n  {a['title'][:70]}", file=sys.stderr)
            print(f"    Summary: {a.get('one_line_summary', '')[:100]}", file=sys.stderr)
            print(f"    Claims ({len(a['key_claims'])}):", file=sys.stderr)
            for c in a["key_claims"][:3]:
                print(f"      • {c[:100]}", file=sys.stderr)
            shown += 1


if __name__ == "__main__":
    main()

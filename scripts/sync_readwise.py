#!/usr/bin/env python3
"""
Sync Readwise Reader articles into Petrarca.

This script runs the full pipeline in one command:
  1. FETCH: Pull your Readwise Reader data (articles + highlights)
  2. FILTER: Find articles you've actually started reading
  3. EXTRACT: Download the full article content from each URL
  4. PROCESS: Run LLM to extract claims, summary, topics
  5. SAVE: Add to Petrarca's article database

USAGE:
    python3 scripts/sync_readwise.py              # Normal sync (40 articles max)
    python3 scripts/sync_readwise.py --limit 10   # Smaller batch for testing
    python3 scripts/sync_readwise.py --full       # Process ALL engaged articles (slow!)
    python3 scripts/sync_readwise.py --dry-run    # See what would happen, no LLM calls

PREREQUISITES:
    1. Get a Readwise access token: https://readwise.io/access_token
    2. Add to .env: READWISE_ACCESS_TOKEN=xxx

WHAT GETS SYNCED:
    - Articles from Readwise Reader that you've started reading (reading_progress > 0)
    - Only articles with valid URLs (pdfs, videos, tweets are skipped)
    - For --full mode: ALL engaged articles, otherwise a diverse sample

HOW THE SAMPLING WORKS:
    By default, we sample 40 articles using a "diverse" strategy:
    - Group articles by their source site (nytimes.com, substack.com, etc.)
    - Pick high-engagement articles from each group
    - This gives you variety instead of 40 articles from one site

WHY THIS MATTERS:
    Readwise Reader is where you save things to read later.
    Petrarca is where you actually learn and retain what you read.
    This script bridges them: it takes your "started reading" pile from Readwise
    and turns it into processed articles in Petrarca with extracted claims.

DATA FLOW:
    Readwise API → data/sources/readwise_reader.json → LLM processing → articles.json

Written for Sarah to understand the pipeline.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# PATHS - Where everything lives
# ---------------------------------------------------------------------------

# The directory containing this script
SCRIPT_DIR = Path(__file__).parent

# Project root (one level up from scripts/)
PROJECT_DIR = SCRIPT_DIR.parent

# Where we store the raw Readwise data
# This is the OUTPUT of fetch_readwise_reader.py
SOURCES_DIR = PROJECT_DIR / "data" / "sources"
READWISE_JSON = SOURCES_DIR / "readwise_reader.json"

# Where processed articles end up
ARTICLES_JSON = PROJECT_DIR / "data" / "articles.json"

# The actual scripts we'll call (they do the heavy lifting)
FETCH_SCRIPT = SCRIPT_DIR / "fetch_readwise_reader.py"
BUILD_SCRIPT = SCRIPT_DIR / "build_articles.py"


# ---------------------------------------------------------------------------
# STEP 1: Fetch from Readwise API
# ---------------------------------------------------------------------------

def fetch_readwise_data(incremental: bool = True) -> bool:
    """
    Call fetch_readwise_reader.py to pull your Readwise data.
    
    WHAT THIS DOES:
        - Connects to Readwise Reader API (https://readwise.io/api/v3)
        - Downloads ALL your saved documents (articles, PDFs, highlights, etc.)
        - Saves to data/sources/readwise_reader.json
    
    THE JSON STRUCTURE:
        [
            {
                "id": "abc123",
                "title": "The Art of Reading",
                "source_url": "https://example.com/article",
                "category": "article",  # or "pdf", "tweet", "video", etc.
                "reading_progress": 0.5,  # 0.0 = not started, 1.0 = finished
                "saved_at": "2024-01-15T10:30:00Z",
                "highlights": [
                    {"text": "Important passage...", "notes": "My note"}
                ]
            },
            ...
        ]
    
    INCREMENTAL MODE:
        If True, only fetch documents updated since our last fetch.
        Much faster if you've synced before.
    
    RETURNS:
        True if successful, False if error.
    """
    print("\n" + "=" * 60)
    print("STEP 1: FETCH FROM READWISE API")
    print("=" * 60)
    
    # Check that the fetch script exists
    if not FETCH_SCRIPT.exists():
        print(f"ERROR: Fetch script not found at {FETCH_SCRIPT}", file=sys.stderr)
        return False
    
    # Check for the access token (fetch script will also check, but we can give a clearer error)
    token = os.environ.get("READWISE_ACCESS_TOKEN")
    if not token:
        # Try loading from .env
        env_path = PROJECT_DIR / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("READWISE_ACCESS_TOKEN="):
                    token = line.split("=", 1)[1].strip().strip("'\"")
                    break
    
    if not token:
        print("ERROR: No READWISE_ACCESS_TOKEN found.", file=sys.stderr)
        print("\nTo fix:", file=sys.stderr)
        print("  1. Go to https://readwise.io/access_token", file=sys.stderr)
        print("  2. Copy your token", file=sys.stderr)
        print("  3. Add to .env: READWISE_ACCESS_TOKEN=xxx", file=sys.stderr)
        return False
    
    print(f"Token found: {token[:8]}...")
    
    # Build the command
    cmd = ["python3", str(FETCH_SCRIPT), "--save"]
    if incremental and READWISE_JSON.exists():
        # Only fetch updates since last sync
        cmd.append("--incremental")
        print("Mode: INCREMENTAL (only updates since last fetch)")
    else:
        print("Mode: FULL (fetching everything)")
    
    print(f"Running: {' '.join(cmd)}")
    print()
    
    # Run the fetch script
    # capture_output=False means we see the progress in real-time
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode != 0:
        print(f"ERROR: Fetch failed with exit code {result.returncode}", file=sys.stderr)
        return False
    
    # Verify we got data
    if not READWISE_JSON.exists():
        print(f"ERROR: Fetch completed but no data at {READWISE_JSON}", file=sys.stderr)
        return False
    
    # Count what we got
    data = json.loads(READWISE_JSON.read_text())
    total_docs = len(data)
    articles = [d for d in data if d.get("category") in ("article", "rss")]
    engaged = [a for a in articles if (a.get("reading_progress") or 0) > 0]
    
    print(f"\n✓ Fetched {total_docs} total items")
    print(f"  - {len(articles)} are articles/rss items")
    print(f"  - {len(engaged)} have been started reading (will be processed)")
    
    return True


# ---------------------------------------------------------------------------
# STEP 2: Process into Petrarca articles
# ---------------------------------------------------------------------------

def process_articles(limit: int = 40, dry_run: bool = False) -> bool:
    """
    Call build_articles.py to process Readwise articles.
    
    WHAT THIS DOES:
        1. LOADS readwise_reader.json (from Step 1)
        2. FILTERS to articles you've started reading
        3. SAMPLES for diversity (more sites = more variety)
        4. DOWNLOADS full article content from each URL
        5. RUNS LLM to extract:
           - Sections (article structure)
           - Summary (short version)
           - Claims (key facts/ideas)
           - Topics (what it's about)
        6. SAVES to articles.json
    
    THE LLM PROCESSING:
        Each article gets analyzed by Claude or Gemini.
        The prompt looks roughly like:
        
        "Given this article:
         - Break it into logical sections
         - Write a 2-3 sentence summary
         - Extract the main claims/ideas
         - Tag with relevant topics"
        
        This is the expensive/slow part. Each article takes ~5-15 seconds.
    
    DIVERSITY SAMPLING:
        We group articles by their "site_name" (nytimes, substack, etc.)
        Then pick from each group round-robin style.
        This prevents you from getting 40 articles all from the same source.
    
    RETURNS:
        True if successful, False if error.
    """
    print("\n" + "=" * 60)
    print("STEP 2: PROCESS ARTICLES INTO PETRARCA")
    print("=" * 60)
    
    # Check that we have data to process
    if not READWISE_JSON.exists():
        print(f"ERROR: No Readwise data at {READWISE_JSON}", file=sys.stderr)
        print("Run Step 1 first (or use --fetch)", file=sys.stderr)
        return False
    
    # Check that the build script exists
    if not BUILD_SCRIPT.exists():
        print(f"ERROR: Build script not found at {BUILD_SCRIPT}", file=sys.stderr)
        return False
    
    print(f"Input: {READWISE_JSON}")
    print(f"Output: {ARTICLES_JSON}")
    print(f"Max articles: {limit}")
    print(f"Dry run: {dry_run}")
    print()
    
    # Build the command
    # --source readwise    : Only process Readwise, skip Twitter
    # --readwise-sample N  : Take N diverse articles
    # --dry-run            : Skip LLM calls (for testing)
    cmd = [
        "python3", str(BUILD_SCRIPT),
        "--source", "readwise",
        "--readwise-sample", str(limit),
    ]
    if dry_run:
        cmd.append("--dry-run")
    
    print(f"Running: {' '.join(cmd)}")
    print("\nThis will:")
    print("  1. Load your Readwise data")
    print("  2. Filter to articles you've started reading")
    print("  3. Download full content from each URL")
    print("  4. Run LLM to extract claims, summary, topics")
    print("  5. Save processed articles")
    print()
    print("Depending on how many articles, this can take several minutes.")
    print()
    
    # Run the build script
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode != 0:
        print(f"ERROR: Build failed with exit code {result.returncode}", file=sys.stderr)
        return False
    
    # Check what we produced
    if ARTICLES_JSON.exists():
        articles = json.loads(ARTICLES_JSON.read_text())
        print(f"\n✓ Total articles in database: {len(articles)}")
    else:
        print(f"\n✓ Processing complete (articles might be in intermediate files)")
    
    return True


# ---------------------------------------------------------------------------
# MAIN: Combine both steps
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Sync Readwise Reader articles into Petrarca",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
    # Normal sync - fetch updates, process 40 diverse articles
    python3 scripts/sync_readwise.py

    # First-time full sync - fetch EVERYTHING, process 100 articles
    python3 scripts/sync_readwise.py --full --limit 100

    # Test run - see what would happen without LLM calls
    python3 scripts/sync_readwise.py --dry-run

    # Just fetch, don't process yet
    python3 scripts/sync_readwise.py --fetch-only

    # Already fetched, just process
    python3 scripts/sync_readwise.py --process-only --limit 20
"""
    )
    parser.add_argument("--limit", type=int, default=40,
                        help="Max articles to process (default: 40)")
    parser.add_argument("--full", action="store_true",
                        help="Process ALL engaged articles, not just a sample")
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip LLM calls (for testing)")
    parser.add_argument("--fetch-only", action="store_true",
                        help="Only fetch from Readwise, don't process")
    parser.add_argument("--process-only", action="store_true",
                        help="Only process, skip fetching")
    parser.add_argument("--no-incremental", action="store_true",
                        help="Force full fetch (ignore last sync time)")
    args = parser.parse_args()
    
    print("=" * 60)
    print("PETRARCA READWISE SYNC")
    print("=" * 60)
    print()
    print("What this does:")
    print("  1. Fetches your Readwise Reader data (articles you saved)")
    print("  2. Processes articles you've started reading")
    print("  3. Extracts claims, summary, topics using LLM")
    print("  4. Adds to your Petrarca article database")
    print()
    
    # Determine the limit for processing
    # --full means no limit (use a very large number)
    process_limit = 99999 if args.full else args.limit
    
    # Step 1: Fetch (unless --process-only)
    if not args.process_only:
        success = fetch_readwise_data(incremental=not args.no_incremental)
        if not success:
            sys.exit(1)
        
        if args.fetch_only:
            print("\n✓ Fetch complete. Run without --fetch-only to process.")
            sys.exit(0)
    
    # Step 2: Process (unless --fetch-only)
    if not args.fetch_only:
        success = process_articles(limit=process_limit, dry_run=args.dry_run)
        if not success:
            sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✓ SYNC COMPLETE")
    print("=" * 60)
    print()
    print("What happens next:")
    print("  - Articles appear in Petrarca's Library tab")
    print("  - You can read them with the Reader")
    print("  - Claims get added to your review queue")
    print()
    print("Tips:")
    print("  - Run this weekly or when you want to sync fresh content")
    print("  - Use --dry-run to test without using LLM credits")
    print("  - The first run takes longest; subsequent runs are incremental")
    print()


if __name__ == "__main__":
    main()

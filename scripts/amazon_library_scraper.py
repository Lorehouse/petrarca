#!/usr/bin/env python3
"""
Amazon Kindle Library Scraper — extracts full book library from Amazon Content & Devices.

Uses agent-browser with Chrome auto-connect to leverage existing Amazon login.
Pushes results to the Petrarca server via POST /kindle/sync.

Usage:
  python3 amazon_library_scraper.py              # scrape and sync
  python3 amazon_library_scraper.py --dump       # scrape and print only
  python3 amazon_library_scraper.py --count      # just count books on page
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen

SERVER_URL = os.environ.get("PETRARCA_SERVER", "http://localhost:8090")
AUTH_TOKEN = os.environ.get("PETRARCA_TOKEN", "")
AMAZON_BOOKS_URL = "https://www.amazon.com/hz/mycd/digital-console/contentlist/booksAll/dateDsc/"

# JS to extract book data from Amazon Content & Devices page
EXTRACT_JS = r"""
(() => {
  const books = [];
  // Amazon Content & Devices lists books in content items
  const items = document.querySelectorAll('[id^="content-"] .digital_entity_title, .CONTENT_LIST_ITEM');

  // Try the data attributes approach first (modern Amazon UI)
  const rows = document.querySelectorAll('[data-asin], .contentTableRow_myx, [id^="contentTabList_"]');
  if (rows.length > 0) {
    rows.forEach(row => {
      const asin = row.getAttribute('data-asin') || '';
      const titleEl = row.querySelector('.digital_entity_title, .title_myx, [id*="title"]');
      const authorEl = row.querySelector('.information_row .value, .author_myx, [id*="author"]');
      const dateEl = row.querySelector('[id*="date"], .date_myx');
      if (titleEl) {
        books.push({
          asin: asin,
          title: titleEl.textContent?.trim() || '',
          author: authorEl?.textContent?.trim() || '',
          purchase_date: dateEl?.textContent?.trim() || '',
        });
      }
    });
  }

  // Fallback: try the newer React-based UI
  if (books.length === 0) {
    const allText = document.querySelectorAll('[class*="ListItem"], [class*="content_list"]');
    allText.forEach(el => {
      const links = el.querySelectorAll('a[href*="/dp/"], a[href*="asin"]');
      links.forEach(link => {
        const href = link.getAttribute('href') || '';
        const asinMatch = href.match(/\/dp\/([A-Z0-9]{10})/i) || href.match(/asin=([A-Z0-9]{10})/i);
        if (asinMatch) {
          books.push({
            asin: asinMatch[1],
            title: link.textContent?.trim() || '',
            author: '',
          });
        }
      });
    });
  }

  return JSON.stringify({ count: books.length, books });
})()
""".strip()

# Simpler extraction that reads the accessibility tree snapshot
EXTRACT_FROM_SNAPSHOT_JS = r"""
(() => {
  // Get all book titles and ASINs from the page
  const books = [];
  const seen = new Set();

  // Find all links that contain /dp/ (book detail pages)
  document.querySelectorAll('a[href*="/dp/"]').forEach(a => {
    const href = a.getAttribute('href') || '';
    const match = href.match(/\/dp\/([A-Z0-9]{10})/i);
    if (match && !seen.has(match[1])) {
      seen.add(match[1]);
      // Walk up to find the row container
      let row = a.closest('tr, [role="row"], div[class*="row"], div[class*="content"]');
      let author = '';
      let date = '';
      if (row) {
        const texts = Array.from(row.querySelectorAll('td, span, div'))
          .map(el => el.textContent?.trim())
          .filter(t => t && t.length > 0 && t.length < 200);
        // Author is usually the 2nd or 3rd text item
        for (const t of texts) {
          if (t !== a.textContent?.trim() && !t.match(/^\d/) && t.length > 2 && t.length < 100) {
            if (!author) author = t;
          }
          // Date pattern
          if (t.match(/^\w+ \d+, \d{4}$/)) {
            date = t;
          }
        }
      }
      books.push({
        asin: match[1],
        title: a.textContent?.trim() || '',
        author: author,
        purchase_date: date,
      });
    }
  });

  return JSON.stringify({ count: books.length, books });
})()
""".strip()


def ab(*args, timeout=30):
    """Run an agent-browser command and return stdout."""
    cmd = ["agent-browser", "--auto-connect"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"agent-browser error (exit {result.returncode}): {result.stderr[:500]}")
    return result.stdout.strip()


def scrape_amazon_library() -> list[dict]:
    """Navigate to Amazon Content & Devices and extract book data."""
    print(f"Opening {AMAZON_BOOKS_URL}...")
    ab("open", AMAZON_BOOKS_URL, timeout=20)

    # Wait for page to load
    print("Waiting for page load...")
    time.sleep(3)
    try:
        ab("wait", "--load", "networkidle", timeout=15)
    except Exception:
        print("  Network idle timeout, proceeding anyway")

    all_books = []
    page = 1

    while True:
        print(f"Extracting books (page {page})...")

        # Try primary extraction
        try:
            raw = ab("eval", EXTRACT_JS, timeout=10)
            data = json.loads(raw)
        except (json.JSONDecodeError, RuntimeError):
            # Fall back to snapshot-based extraction
            try:
                raw = ab("eval", EXTRACT_FROM_SNAPSHOT_JS, timeout=10)
                data = json.loads(raw)
            except Exception as e:
                print(f"  Extraction failed: {e}")
                break

        books = data.get("books", [])
        print(f"  Found {len(books)} books on page {page}")

        if not books:
            # Try taking a screenshot for debugging
            try:
                ab("screenshot", "/tmp/amazon-scraper-debug.png")
                print("  Debug screenshot saved to /tmp/amazon-scraper-debug.png")
            except Exception:
                pass
            break

        all_books.extend(books)

        # Try to find and click "Show more" or pagination
        try:
            # Look for pagination or "Show more" button
            ab("eval", """
                const btn = document.querySelector('[class*="show_more"], [class*="pagination"] a:last-child, button[class*="next"]');
                if (btn) { btn.click(); 'clicked'; } else { 'none'; }
            """, timeout=5)
            time.sleep(2)
            page += 1
        except Exception:
            break

        # Safety limit
        if page > 50:
            break

    # Deduplicate by ASIN
    seen = set()
    unique = []
    for book in all_books:
        asin = book.get("asin", "")
        if asin and asin in seen:
            continue
        if asin:
            seen.add(asin)
        unique.append(book)

    return unique


def sync_to_server(books: list[dict]):
    """Push scraped book data to Petrarca server."""
    payload = {
        "data_type": "amazon_library",
        "source": "agent-browser/amazon",
        "books": books,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "total_books": len(books),
    }

    headers = {"Content-Type": "application/json"}
    if AUTH_TOKEN:
        headers["X-Petrarca-Token"] = AUTH_TOKEN

    data = json.dumps(payload).encode()
    req = Request(f"{SERVER_URL}/kindle/sync", data=data, headers=headers, method="POST")

    try:
        with urlopen(req) as resp:
            result = json.loads(resp.read())
            print(f"Synced to server: {result}")
    except Exception as e:
        print(f"Sync failed: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Scrape Amazon Kindle library")
    parser.add_argument("--dump", action="store_true", help="Print books instead of syncing")
    parser.add_argument("--count", action="store_true", help="Just count books")
    args = parser.parse_args()

    try:
        books = scrape_amazon_library()
    except RuntimeError as e:
        print(f"Error: {e}")
        print("Make sure Chrome is running and logged into Amazon.")
        sys.exit(1)

    print(f"\nTotal books found: {len(books)}")

    if args.count:
        return

    if args.dump:
        for b in books[:30]:
            print(f"  {b.get('asin', '???'):12s}  {b.get('title', '?')[:55]:55s}  {b.get('author', '')[:25]}")
        if len(books) > 30:
            print(f"  ... and {len(books) - 30} more")
        return

    if not books:
        print("No books found. Nothing to sync.")
        return

    sync_to_server(books)


if __name__ == "__main__":
    main()

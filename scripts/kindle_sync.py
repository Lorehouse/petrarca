#!/usr/bin/env python3
"""
Kindle Library Sync — reads the Kindle Mac app's local SQLite database
and pushes library + reading progress data to the Petrarca server.

The Kindle Mac app (com.amazon.Lassen) stores all synced book data in:
  ~/Library/Containers/com.amazon.Lassen/Data/Library/Protected/BookData.sqlite

This includes ALL books (purchased + sideloaded) with Whispersync progress.

Usage:
  python3 kindle_sync.py              # sync to server
  python3 kindle_sync.py --dump       # just print what we'd sync
  python3 kindle_sync.py --dump-csv   # export full library as CSV
  python3 kindle_sync.py --reading    # show currently reading
  python3 kindle_sync.py --read       # show finished books
"""

import argparse
import csv
import json
import os
import plistlib
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

BOOKDATA_PATH = Path.home() / "Library/Containers/com.amazon.Lassen/Data/Library/Protected/BookData.sqlite"
SERVER_URL = os.environ.get("PETRARCA_SERVER", "http://localhost:8090")
AUTH_TOKEN = os.environ.get("PETRARCA_TOKEN", "")


def decode_sync_meta(blob) -> dict:
    """Decode NSKeyedArchiver plist into a flat dict of key->value.

    The Kindle app stores book metadata as NSKeyedArchiver-encoded plists.
    The structure is: root -> attributes (NSDictionary) with keys like
    'title', 'authors', 'publishers', 'ASIN', 'cde_contenttype', etc.
    """
    if not blob:
        return {}
    try:
        arch = plistlib.loads(blob)
        objects = arch.get('$objects', [])
        if len(objects) < 3:
            return {}

        # obj[2] is the attributes NSDictionary with NS.keys and NS.objects
        attrs = objects[2] if len(objects) > 2 and isinstance(objects[2], dict) else {}
        keys_uids = attrs.get('NS.keys', [])
        vals_uids = attrs.get('NS.objects', [])

        result = {}
        for k_uid, v_uid in zip(keys_uids, vals_uids):
            k_idx = k_uid if isinstance(k_uid, int) else getattr(k_uid, 'data', 0)
            v_idx = v_uid if isinstance(v_uid, int) else getattr(v_uid, 'data', 0)

            key = objects[k_idx] if k_idx < len(objects) else None
            val_obj = objects[v_idx] if v_idx < len(objects) else None

            if not isinstance(key, str):
                continue

            if isinstance(val_obj, str):
                result[key] = val_obj
            elif isinstance(val_obj, dict):
                # Nested NSDictionary — extract first string value
                inner_vals = val_obj.get('NS.objects', [])
                for iv_uid in inner_vals:
                    iv_idx = iv_uid if isinstance(iv_uid, int) else getattr(iv_uid, 'data', 0)
                    if iv_idx < len(objects) and isinstance(objects[iv_idx], str):
                        result[key] = objects[iv_idx]
                        break
        return result
    except Exception:
        return {}


def clean_sideloaded_title(raw_title: str) -> tuple[str, str]:
    """Parse sideloaded book titles which often contain embedded metadata.
    Format: "Title -- Author -- Year -- Publisher -- ISBN -- hash -- Source"
    """
    if " -- " in raw_title:
        parts = [p.strip() for p in raw_title.split(" -- ")]
        title = parts[0]
        author = parts[1] if len(parts) > 1 else ""
        author = author.replace("(EDT)", "").replace("(TRN)", "").strip().rstrip(";,").strip()
        return title, author
    return raw_title, ""


def read_kindle_db() -> list[dict]:
    """Read all books from the Kindle Mac app database."""
    if not BOOKDATA_PATH.exists():
        print(f"Error: Kindle database not found at {BOOKDATA_PATH}")
        print("Make sure the Kindle Mac app is installed and has been opened at least once.")
        sys.exit(1)

    conn = sqlite3.connect(f"file:{BOOKDATA_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    cursor = conn.execute("""
        SELECT
            ZBOOKID,
            ZDISPLAYTITLE,
            ZSYNCMETADATAATTRIBUTES,
            ZRAWCURRENTPOSITION,
            ZRAWMAXPOSITION,
            ZRAWREADSTATE,
            ZRAWISUNREAD,
            ZRAWLASTACCESSTIME,
            ZRAWFILESIZE,
            ZRAWBOOKTYPE,
            ZLANGUAGE,
            ZISHIDDENBYUSER
        FROM ZBOOK
        WHERE ZISHIDDENBYUSER = 0
        ORDER BY ZRAWLASTACCESSTIME DESC
    """)

    books = []
    for row in cursor:
        book_id = row["ZBOOKID"] or ""
        raw_title = row["ZDISPLAYTITLE"] or ""

        # Decode metadata from NSKeyedArchiver blob
        meta = decode_sync_meta(row["ZSYNCMETADATAATTRIBUTES"])

        # Title: prefer metadata title, fall back to display title
        meta_title = meta.get('title', '')
        if meta_title and meta_title != raw_title:
            title = meta_title
        else:
            # For sideloaded books, clean up the filename-based title
            title, _ = clean_sideloaded_title(raw_title)

        # Author: from metadata
        author = meta.get('authors', '')
        if not author:
            _, parsed_author = clean_sideloaded_title(raw_title)
            author = parsed_author

        # Publisher
        publisher = meta.get('publishers', '')

        # ASIN: from metadata or book_id
        asin = meta.get('ASIN', '')
        if not asin and book_id:
            inner = book_id.removeprefix("A:").split("-")[0]
            if inner.startswith("B0") and len(inner) == 10:
                asin = inner

        # Content type: EBOK = purchased, PDOC = sideloaded
        cde_type = meta.get('cde_contenttype', '')
        is_sideloaded = cde_type == 'PDOC'

        # Progress
        cur_pos = row["ZRAWCURRENTPOSITION"] or 0
        max_pos = row["ZRAWMAXPOSITION"] or 0
        progress_pct = round(100.0 * cur_pos / max_pos, 1) if max_pos > 0 and cur_pos > 0 else 0.0

        # Last access time
        last_access = row["ZRAWLASTACCESSTIME"] or 0
        last_read = datetime.fromtimestamp(last_access, tz=timezone.utc).isoformat() if last_access > 0 else None

        # Status + finished_date
        read_state = row["ZRAWREADSTATE"]
        finished_date = None
        if read_state == 1:
            status = "read"
            # Best approximation: last access time is when they finished
            finished_date = last_read
        elif cur_pos > 0 and progress_pct > 1:
            status = "reading"
        else:
            status = "unread"

        # Purchase date from metadata
        purchase_date = meta.get('purchase_date', '')

        books.append({
            "book_id": book_id,
            "asin": asin,
            "title": title,
            "author": author,
            "publisher": publisher,
            "progress_pct": progress_pct,
            "current_position": cur_pos,
            "max_position": max_pos,
            "status": status,
            "finished_date": finished_date,
            "last_read": last_read,
            "purchase_date": purchase_date,
            "language": row["ZLANGUAGE"] or "",
            "content_type": cde_type,
            "file_size": row["ZRAWFILESIZE"] or 0,
            "is_sideloaded": is_sideloaded,
        })

    conn.close()
    return books


def needs_title_resolution(book: dict) -> bool:
    """Check if a book's title looks like a filename that needs resolving."""
    title = book.get("title", "")
    if not title:
        return True
    # Project Gutenberg pattern
    if title.startswith("pg") and title.endswith("-3"):
        return True
    # No spaces and short = likely a filename
    if " " not in title and len(title) < 30:
        return True
    # DOI pattern
    if title.startswith("10."):
        return True
    return False


def resolve_titles_via_llm(books: list[dict]) -> dict[str, str]:
    """Use the Petrarca server's LLM to resolve filename-based titles.

    Sends batches of (filename, author) pairs and gets back real titles.
    Returns a dict mapping book_id -> resolved title.
    """
    to_resolve = [(b["book_id"], b["title"], b["author"]) for b in books if needs_title_resolution(b) and b["author"]]

    if not to_resolve:
        return {}

    print(f"Resolving {len(to_resolve)} titles via LLM...")

    resolved = {}
    # Process in batches of 40
    for i in range(0, len(to_resolve), 40):
        batch = to_resolve[i:i+40]
        book_list = "\n".join(
            f'{j+1}. Filename: "{bid_title_author[1]}" | Author: "{bid_title_author[2]}"'
            for j, bid_title_author in enumerate(batch)
        )

        prompt = f"""Given these book filenames and their authors, identify the actual book title.
For Project Gutenberg files (pg*-images-3), the author is the key clue.
For other filenames, use the filename + author to determine the book.

Return ONLY a JSON array of objects with "index" (1-based) and "title" (the real book title).
If you cannot determine the title with confidence, set title to null.

Books:
{book_list}

Return JSON array only, no markdown fences:"""

        headers = {"Content-Type": "application/json"}
        if AUTH_TOKEN:
            headers["X-Petrarca-Token"] = AUTH_TOKEN

        payload = json.dumps({"prompt": prompt}).encode()
        req = Request(f"{SERVER_URL}/chat", data=payload, headers=headers, method="POST")

        try:
            with urlopen(req) as resp:
                result = json.loads(resp.read())
                answer = result.get("answer", "").strip()
                if answer.startswith("```"):
                    answer = answer.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                titles = json.loads(answer)

                for item in titles:
                    idx = item.get("index", 0) - 1
                    title = item.get("title")
                    if 0 <= idx < len(batch) and title:
                        book_id = batch[idx][0]
                        resolved[book_id] = title
                        print(f"  {batch[idx][1]} → {title}")
        except Exception as e:
            print(f"  Batch {i//40} LLM error: {e}")
            continue

    return resolved


def sync_to_server(books: list[dict]):
    """Push book data to the Petrarca server."""
    payload = {
        "data_type": "kindle_mac_app",
        "source": "BookData.sqlite",
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
    parser = argparse.ArgumentParser(description="Sync Kindle library to Petrarca")
    parser.add_argument("--dump", action="store_true", help="Print books instead of syncing")
    parser.add_argument("--dump-csv", action="store_true", help="Export full library as CSV")
    parser.add_argument("--reading", action="store_true", help="Show only currently-reading books")
    parser.add_argument("--read", action="store_true", help="Show only read books")
    parser.add_argument("--resolve-titles", action="store_true", help="Use LLM to resolve filename-based titles")
    args = parser.parse_args()

    books = read_kindle_db()
    print(f"Found {len(books)} books in Kindle database")

    statuses = {}
    for b in books:
        statuses[b["status"]] = statuses.get(b["status"], 0) + 1
    print(f"Status: {statuses}")

    sideloaded = sum(1 for b in books if b["is_sideloaded"])
    purchased = len(books) - sideloaded
    print(f"Purchased: {purchased}, Sideloaded: {sideloaded}")

    if args.resolve_titles:
        bad = [b for b in books if needs_title_resolution(b) and b["author"]]
        print(f"\nBooks needing title resolution: {len(bad)}")
        resolved = resolve_titles_via_llm(bad)
        print(f"\nResolved {len(resolved)} titles")
        # Apply resolved titles
        for b in books:
            if b["book_id"] in resolved:
                b["title"] = resolved[b["book_id"]]
        # Show results
        for b in bad[:30]:
            new_title = resolved.get(b["book_id"], "???")
            print(f"  {b['title'][:30]:30s} → {new_title}")
        return

    if args.reading:
        filtered = [b for b in books if b["status"] == "reading"]
        print(f"\nCurrently reading ({len(filtered)} books):")
        for b in filtered:
            print(f"  {b['progress_pct']:5.1f}%  {b['title'][:55]:55s}  by {b['author'][:30]}")
        return

    if args.read:
        filtered = [b for b in books if b["status"] == "read"]
        print(f"\nFinished ({len(filtered)} books):")
        for b in filtered:
            lr = b['last_read'][:10] if b['last_read'] else '          '
            print(f"  {lr}  {b['title'][:55]:55s}  by {b['author'][:30]}")
        return

    if args.dump_csv:
        writer = csv.DictWriter(sys.stdout, fieldnames=[
            "book_id", "asin", "title", "author", "publisher", "progress_pct",
            "status", "last_read", "language", "content_type", "is_sideloaded"
        ])
        writer.writeheader()
        for b in books:
            writer.writerow({k: b[k] for k in writer.fieldnames})
        return

    if args.dump:
        for b in books[:30]:
            flag = "📖" if b["status"] == "reading" else ("✅" if b["status"] == "read" else "  ")
            print(f"  {flag} {b['progress_pct']:5.1f}%  {b['title'][:50]:50s}  {b['author'][:25]}")
        if len(books) > 30:
            print(f"  ... and {len(books) - 30} more")
        return

    sync_to_server(books)


if __name__ == "__main__":
    main()

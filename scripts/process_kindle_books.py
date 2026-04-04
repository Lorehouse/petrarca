"""Process Kindle library into unified book system.

Reads kindle_books from SQLite, filters non-fiction, creates unified book records,
runs research agent, converts highlights to captures, triggers embedding.

Usage:
    python3 process_kindle_books.py                    # process all unprocessed non-fiction
    python3 process_kindle_books.py --research-only    # research but don't embed
    python3 process_kindle_books.py --key B00XXXX      # process specific book
    python3 process_kindle_books.py --list              # list unprocessed books
    python3 process_kindle_books.py --stats             # show processing stats
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
KINDLE_HIGHLIGHTS_PATH = Path(os.environ.get('KINDLE_HIGHLIGHTS_PATH', '/opt/petrarca/data/kindle_highlights.json'))
BOOK_RESEARCH_DIR = DATA_DIR / "book_research"

BOOK_RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

# Categories to include for knowledge experiments (from session 23 classification)
RELEVANT_CATEGORIES = {'non-fiction', 'classical-literature', 'literary-fiction', 'language-learning'}


def log(msg: str):
    print(f"[kindle-process] {msg}", flush=True)


def load_kindle_library() -> dict:
    """Load kindle books from SQLite as a dict keyed by key."""
    from db import get_connection
    conn = get_connection(readonly=True)
    rows = conn.execute('SELECT * FROM kindle_books').fetchall()
    conn.close()
    books = {}
    for row in rows:
        book = dict(row)
        book['added_to_petrarca'] = bool(book.get('added_to_petrarca'))
        book['is_sideloaded'] = bool(book.get('is_sideloaded'))
        # Reconstruct progress object for backward compat with kindle_to_unified_book
        book['progress'] = {
            'pct': book.get('progress_pct', 0),
            'text': book.get('progress_text', ''),
            'current_position': book.get('current_position', 0),
            'max_position': book.get('max_position', 0),
        }
        books[book['key']] = book
    return {'books': books}


def load_kindle_highlights() -> dict:
    if not KINDLE_HIGHLIGHTS_PATH.exists():
        return {'books': {}}
    return json.loads(KINDLE_HIGHLIGHTS_PATH.read_text())


def load_physical_books() -> dict:
    """Load physical books from SQLite."""
    from db import load_all_books_and_captures
    return load_all_books_and_captures()


def save_physical_books(data: dict):
    """Save physical books to SQLite."""
    from db import get_connection, upsert_books, upsert_captures
    conn = get_connection()
    upsert_books(data.get('books', []), conn)
    upsert_captures(data.get('captures', []), conn)
    conn.commit()
    conn.close()


def is_already_unified(key: str, physical_data: dict = None) -> bool:
    """Check if a Kindle book (by ASIN or book_id key) is already unified."""
    if physical_data:
        return any(
            b.get('kindle_asin') == key
            or b.get('kindle_book_id') == key
            or b.get('id') == f'kindle_{key}'
            for b in physical_data.get('books', [])
        )
    # Check directly in SQLite
    from db import get_connection
    conn = get_connection(readonly=True)
    row = conn.execute(
        "SELECT id FROM physical_books WHERE kindle_asin=? OR kindle_book_id=? OR id=?",
        (key, key, f'kindle_{key}')
    ).fetchone()
    conn.close()
    return row is not None


def is_already_researched(book_id: str) -> bool:
    return (BOOK_RESEARCH_DIR / f'{book_id}.json').exists()


def kindle_to_unified_book(key: str, kindle_book: dict) -> dict:
    """Convert a Kindle book record to a unified PhysicalBook record.

    Key can be an ASIN (purchased) or book_id (sideloaded).
    Uses title_resolved for sideloaded books with filename-based titles.
    """
    progress = kindle_book.get('progress', {})
    progress_pct = progress.get('pct') or progress.get('percent')

    # Parse progress from text if needed
    if progress_pct is None:
        progress_text = progress.get('text', '')
        if progress_text:
            try:
                progress_pct = int(str(progress_text).replace('%', '').strip())
            except (ValueError, AttributeError):
                pass

    # Determine reading status from Kindle status
    status = kindle_book.get('status', 'unreviewed')
    if status == 'read' or (progress_pct and progress_pct >= 95):
        reading_status = 'finished'
    elif status == 'reading' or (progress_pct and progress_pct > 0 and progress_pct < 95):
        reading_status = 'reading'
    elif status == 'skipped':
        reading_status = 'archived'
    else:
        reading_status = 'want_to_read'

    # Use resolved title for sideloaded books
    title = kindle_book.get('title_resolved') or kindle_book.get('title', '')
    asin = kindle_book.get('asin', '')
    book_id_raw = kindle_book.get('book_id', '')

    return {
        'id': f'kindle_{asin or book_id_raw or key}',
        'kindle_asin': asin,
        'kindle_book_id': book_id_raw,
        'title': title,
        'author': kindle_book.get('author', ''),
        'cover_url': kindle_book.get('cover_url'),
        'isbn': kindle_book.get('isbn'),
        'publisher': kindle_book.get('publisher'),
        'page_count': kindle_book.get('page_count'),
        'language': kindle_book.get('language', 'en'),
        'topics': kindle_book.get('topics', []),
        'chapters': kindle_book.get('chapters', []),
        'current_page': None,
        'current_chapter': None,
        'reading_status': reading_status,
        'added_at': _parse_timestamp(kindle_book.get('first_seen') or kindle_book.get('purchase_date', '')),
        'last_interaction_at': _parse_timestamp(kindle_book.get('last_seen') or kindle_book.get('last_read', '')),
        'metadata_source': 'kindle',
        'category': kindle_book.get('category'),
        'progress_percent': progress_pct,
        'finished_date': kindle_book.get('finished_date'),
        'is_sideloaded': kindle_book.get('is_sideloaded', False),
        'epub_path': kindle_book.get('epub_path'),
    }


def _parse_timestamp(ts_str: str) -> int:
    """Parse ISO timestamp to epoch ms, default to now."""
    if not ts_str:
        return int(time.time() * 1000)
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        return int(dt.timestamp() * 1000)
    except (ValueError, AttributeError):
        return int(time.time() * 1000)


def highlights_to_captures(key: str, book_id: str, highlights_data: dict) -> list[dict]:
    """Convert Kindle highlights for a book into BookCapture records.

    Highlights are keyed by ASIN or book_id in kindle_highlights.json.
    """
    # Try both key formats
    book_highlights = highlights_data.get('books', {}).get(key, {})
    highlight_list = book_highlights.get('highlights', [])

    captures = []
    for i, hl in enumerate(highlight_list):
        text = hl.get('text', '').strip()
        if not text:
            continue

        capture = {
            'id': f'kh_{key}_{i}',
            'book_id': book_id,
            'type': 'kindle_highlight',
            'created_at': _parse_timestamp(hl.get('timestamp') or hl.get('synced_at', '')),
            'text': text,
            'page_number': hl.get('page'),
            'chapter': hl.get('chapter'),
            'upload_status': 'uploaded',
            # Kindle-specific
            'kindle_location': hl.get('location'),
            'highlight_color': hl.get('color'),
            'user_note': hl.get('note'),
        }
        captures.append(capture)

    return captures


def research_book_if_needed(book_id: str, title: str, author: str,
                             chapters: list, topics: list) -> dict | None:
    """Run research agent if not already researched."""
    if is_already_researched(book_id):
        log(f"  Already researched: {title}")
        return json.loads((BOOK_RESEARCH_DIR / f'{book_id}.json').read_text())

    from book_research_agent import research_book
    log(f"  Researching: {title}...")
    return research_book(book_id, title, author, None, chapters, topics)


def process_single_book(key: str, kindle_book: dict, highlights_data: dict,
                         physical_data: dict, do_research: bool = True) -> bool:
    """Process one Kindle book: unify, convert highlights, research.

    Key is the dict key from kindle_library.json (ASIN or book_id).
    Returns True if book was processed (new), False if already existed.
    """
    title = kindle_book.get('title_resolved') or kindle_book.get('title', 'Unknown')

    # Skip if already unified
    if is_already_unified(key, physical_data):
        log(f"  Skip (already unified): {title}")
        return False

    # Create unified book record
    unified = kindle_to_unified_book(key, kindle_book)
    book_id = unified['id']
    physical_data['books'].append(unified)

    # Convert highlights to captures
    captures = highlights_to_captures(key, book_id, highlights_data)
    if captures:
        physical_data['captures'].extend(captures)
        log(f"  {len(captures)} highlights → captures")

    # Research
    if do_research:
        topics = unified.get('topics', [])
        if not topics:
            # Try to get topics from category
            cat = kindle_book.get('category', '')
            if cat:
                topics = [cat]
        research_book_if_needed(book_id, title, unified['author'],
                                 unified.get('chapters', []), topics)

    log(f"  Unified: {title} ({unified['reading_status']}, {len(captures)} highlights)")
    return True


def process_all(do_research: bool = True, max_books: int | None = None):
    """Process all unprocessed non-fiction Kindle books."""
    kindle_data = load_kindle_library()
    highlights_data = load_kindle_highlights()
    physical_data = load_physical_books()

    books = kindle_data.get('books', {})
    relevant = {
        key: book for key, book in books.items()
        if book.get('category') in RELEVANT_CATEGORIES
        and book.get('status') == 'read'
        and not is_already_unified(key, physical_data)
    }

    log(f"Kindle library: {len(books)} total, {len(relevant)} relevant+read unprocessed")

    if not relevant:
        log("Nothing to process.")
        return

    processed = 0
    for key, book in sorted(relevant.items(), key=lambda x: (x[1].get('title_resolved') or x[1].get('title', ''))):
        if max_books and processed >= max_books:
            log(f"Reached max_books limit ({max_books})")
            break

        success = process_single_book(key, book, highlights_data, physical_data, do_research)
        if success:
            processed += 1
            # Save after each book in case of interruption
            save_physical_books(physical_data)

    log(f"Done: {processed} books processed")

    # Final save
    save_physical_books(physical_data)


def show_stats():
    """Show processing statistics."""
    from db import get_connection
    conn = get_connection(readonly=True)

    total = conn.execute('SELECT COUNT(*) FROM kindle_books').fetchone()[0]
    cat_rows = conn.execute(
        "SELECT COALESCE(category, 'unclassified') as cat, COUNT(*) as cnt FROM kindle_books GROUP BY category"
    ).fetchall()
    status_rows = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM kindle_books GROUP BY status"
    ).fetchall()
    unified_count = conn.execute(
        "SELECT COUNT(*) FROM physical_books WHERE kindle_asin IS NOT NULL OR kindle_book_id IS NOT NULL"
    ).fetchone()[0]
    capture_count = conn.execute(
        "SELECT COUNT(*) FROM book_captures WHERE type='kindle_highlight'"
    ).fetchone()[0]
    conn.close()

    highlights_data = load_kindle_highlights()
    highlight_books = highlights_data.get('books', {})
    total_highlights = sum(len(b.get('highlights', [])) for b in highlight_books.values())

    print(f"\n{'='*50}")
    print(f"  Kindle Book Processing Stats")
    print(f"{'='*50}")
    print(f"  Kindle library:     {total} books")
    print(f"  By category:        {json.dumps({r['cat']: r['cnt'] for r in cat_rows}, indent=2)}")
    print(f"  By status:          {json.dumps({r['status']: r['cnt'] for r in status_rows}, indent=2)}")
    print(f"  Highlights:         {total_highlights} across {len(highlight_books)} books")
    print(f"  Unified (Kindle):   {unified_count} books")
    print(f"  Kindle captures:    {capture_count}")
    print()


def list_unprocessed():
    """List Kindle books that are read + relevant category but not yet processed."""
    from db import get_connection
    conn = get_connection(readonly=True)
    cats = ','.join(f"'{c}'" for c in RELEVANT_CATEGORIES)
    rows = conn.execute(f'''
        SELECT key, title, title_resolved, category, progress_pct
        FROM kindle_books
        WHERE category IN ({cats})
          AND status = 'read'
        ORDER BY COALESCE(title_resolved, title)
    ''').fetchall()
    conn.close()

    for r in rows:
        key = r['key']
        if is_already_unified(key):
            continue
        title = r['title_resolved'] or r['title'] or '?'
        cat = r['category'] or '?'
        pct = r['progress_pct'] or '?'
        print(f"  {key[:15]:15s} {title[:55]:55s} [{cat}, {pct}%]")


def main():
    parser = argparse.ArgumentParser(description="Process Kindle books into unified book system")
    parser.add_argument("--research-only", action="store_true",
                        help="Research but don't run embeddings")
    parser.add_argument("--key", type=str, help="Process specific book by key (ASIN or book_id)")
    parser.add_argument("--list", action="store_true", help="List unprocessed books")
    parser.add_argument("--stats", action="store_true", help="Show processing stats")
    parser.add_argument("--max", type=int, help="Max books to process")
    parser.add_argument("--no-research", action="store_true",
                        help="Unify and convert highlights but skip research")
    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    if args.list:
        list_unprocessed()
        return

    if args.key:
        kindle_data = load_kindle_library()
        highlights_data = load_kindle_highlights()
        physical_data = load_physical_books()
        book = kindle_data.get('books', {}).get(args.key)
        if not book:
            print(f"Key {args.key} not found in Kindle library")
            sys.exit(1)
        process_single_book(args.key, book, highlights_data, physical_data,
                            do_research=not args.no_research)
        save_physical_books(physical_data)
        return

    process_all(do_research=not args.no_research, max_books=args.max)


if __name__ == '__main__':
    main()

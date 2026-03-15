"""Process Kindle library into unified book system.

Reads kindle_library.json, filters non-fiction, creates unified book records,
runs research agent, converts highlights to captures, triggers embedding.

Usage:
    python3 process_kindle_books.py                    # process all unprocessed non-fiction
    python3 process_kindle_books.py --research-only    # research but don't embed
    python3 process_kindle_books.py --asin B00XXXX     # process specific book
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
KINDLE_DATA_PATH = Path(os.environ.get('KINDLE_DATA_PATH', '/opt/petrarca/data/kindle_library.json'))
KINDLE_HIGHLIGHTS_PATH = Path(os.environ.get('KINDLE_HIGHLIGHTS_PATH', '/opt/petrarca/data/kindle_highlights.json'))
PHYSICAL_BOOKS_PATH = Path(os.environ.get('PHYSICAL_BOOKS_PATH', '/opt/petrarca/data/physical_books.json'))
BOOK_RESEARCH_DIR = DATA_DIR / "book_research"

BOOK_RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

RELEVANT_CATEGORIES = {'non-fiction', 'historical-novel'}


def log(msg: str):
    print(f"[kindle-process] {msg}", flush=True)


def load_kindle_library() -> dict:
    if not KINDLE_DATA_PATH.exists():
        return {'books': {}}
    return json.loads(KINDLE_DATA_PATH.read_text())


def load_kindle_highlights() -> dict:
    if not KINDLE_HIGHLIGHTS_PATH.exists():
        return {'books': {}}
    return json.loads(KINDLE_HIGHLIGHTS_PATH.read_text())


def load_physical_books() -> dict:
    if not PHYSICAL_BOOKS_PATH.exists():
        return {'books': [], 'captures': []}
    try:
        return json.loads(PHYSICAL_BOOKS_PATH.read_text())
    except json.JSONDecodeError:
        return {'books': [], 'captures': []}


def save_physical_books(data: dict):
    PHYSICAL_BOOKS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def is_already_unified(asin: str, physical_data: dict) -> bool:
    """Check if a Kindle book is already in the unified book system."""
    return any(
        b.get('kindle_asin') == asin or b.get('id') == f'kindle_{asin}'
        for b in physical_data.get('books', [])
    )


def is_already_researched(book_id: str) -> bool:
    return (BOOK_RESEARCH_DIR / f'{book_id}.json').exists()


def kindle_to_unified_book(asin: str, kindle_book: dict) -> dict:
    """Convert a Kindle book record to a unified PhysicalBook record."""
    progress_text = kindle_book.get('progress', {}).get('text', '')
    progress_pct = kindle_book.get('progress', {}).get('percent')

    # Parse progress percentage
    if progress_pct is None and progress_text:
        try:
            progress_pct = int(progress_text.replace('%', '').strip())
        except (ValueError, AttributeError):
            pass

    # Determine reading status
    status = kindle_book.get('status', 'unreviewed')
    if status == 'read' or (progress_pct and progress_pct >= 95):
        reading_status = 'finished'
    elif status == 'reading' or (progress_pct and progress_pct > 0):
        reading_status = 'reading'
    elif status == 'skipped':
        reading_status = 'archived'
    else:
        reading_status = 'want_to_read'

    return {
        'id': f'kindle_{asin}',
        'kindle_asin': asin,
        'title': kindle_book.get('title', ''),
        'author': kindle_book.get('author', ''),
        'cover_url': kindle_book.get('cover_url'),
        'isbn': kindle_book.get('isbn'),
        'page_count': kindle_book.get('page_count'),
        'language': 'en',
        'topics': kindle_book.get('topics', []),
        'chapters': kindle_book.get('chapters', []),
        'current_page': None,
        'current_chapter': None,
        'reading_status': reading_status,
        'added_at': _parse_timestamp(kindle_book.get('first_seen', '')),
        'last_interaction_at': _parse_timestamp(kindle_book.get('last_seen', '')),
        'metadata_source': 'kindle',
        'category': kindle_book.get('category'),
        'progress_percent': progress_pct,
        'finished_date': kindle_book.get('finished_date'),
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


def highlights_to_captures(asin: str, book_id: str, highlights_data: dict) -> list[dict]:
    """Convert Kindle highlights for a book into BookCapture records."""
    book_highlights = highlights_data.get('books', {}).get(asin, {})
    highlight_list = book_highlights.get('highlights', [])

    captures = []
    for i, hl in enumerate(highlight_list):
        text = hl.get('text', '').strip()
        if not text:
            continue

        capture = {
            'id': f'kh_{asin}_{i}',
            'book_id': book_id,
            'type': 'kindle_highlight',
            'created_at': _parse_timestamp(hl.get('timestamp', '')),
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


def process_single_book(asin: str, kindle_book: dict, highlights_data: dict,
                         physical_data: dict, do_research: bool = True) -> bool:
    """Process one Kindle book: unify, convert highlights, research.
    Returns True if book was processed (new), False if already existed."""

    book_id = f'kindle_{asin}'
    title = kindle_book.get('title', 'Unknown')

    # Skip if already unified
    if is_already_unified(asin, physical_data):
        log(f"  Skip (already unified): {title}")
        return False

    # Create unified book record
    unified = kindle_to_unified_book(asin, kindle_book)
    physical_data['books'].append(unified)

    # Convert highlights to captures
    captures = highlights_to_captures(asin, book_id, highlights_data)
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
        asin: book for asin, book in books.items()
        if book.get('category') in RELEVANT_CATEGORIES
        and not is_already_unified(asin, physical_data)
    }

    log(f"Kindle library: {len(books)} total, {len(relevant)} relevant unprocessed")

    if not relevant:
        log("Nothing to process.")
        return

    processed = 0
    for asin, book in sorted(relevant.items(), key=lambda x: x[1].get('title', '')):
        if max_books and processed >= max_books:
            log(f"Reached max_books limit ({max_books})")
            break

        success = process_single_book(asin, book, highlights_data, physical_data, do_research)
        if success:
            processed += 1
            # Save after each book in case of interruption
            save_physical_books(physical_data)

    log(f"Done: {processed} books processed")

    # Final save
    save_physical_books(physical_data)


def show_stats():
    """Show processing statistics."""
    kindle_data = load_kindle_library()
    highlights_data = load_kindle_highlights()
    physical_data = load_physical_books()

    books = kindle_data.get('books', {})

    by_category = {}
    for book in books.values():
        cat = book.get('category', 'unclassified')
        by_category[cat] = by_category.get(cat, 0) + 1

    by_status = {}
    for book in books.values():
        st = book.get('status', 'unreviewed')
        by_status[st] = by_status.get(st, 0) + 1

    unified_kindle = [b for b in physical_data.get('books', []) if b.get('kindle_asin')]
    researched = sum(1 for b in unified_kindle if is_already_researched(b['id']))
    total_captures = len([c for c in physical_data.get('captures', []) if c.get('type') == 'kindle_highlight'])

    highlight_books = highlights_data.get('books', {})
    total_highlights = sum(len(b.get('highlights', [])) for b in highlight_books.values())

    print(f"\n{'='*50}")
    print(f"  Kindle Book Processing Stats")
    print(f"{'='*50}")
    print(f"  Kindle library:     {len(books)} books")
    print(f"  By category:        {json.dumps(by_category, indent=2)}")
    print(f"  By status:          {json.dumps(by_status, indent=2)}")
    print(f"  Highlights:         {total_highlights} across {len(highlight_books)} books")
    print(f"  Unified (Kindle):   {len(unified_kindle)} books")
    print(f"  Researched:         {researched} books")
    print(f"  Kindle captures:    {total_captures}")
    print()


def list_unprocessed():
    """List Kindle books that haven't been processed yet."""
    kindle_data = load_kindle_library()
    physical_data = load_physical_books()

    books = kindle_data.get('books', {})
    for asin, book in sorted(books.items(), key=lambda x: x[1].get('title', '')):
        if book.get('category') not in RELEVANT_CATEGORIES:
            continue
        if is_already_unified(asin, physical_data):
            continue
        status = book.get('status', '?')
        progress = book.get('progress', {}).get('text', '?')
        print(f"  {asin}: {book.get('title', '?')[:60]} [{status}, {progress}]")


def main():
    parser = argparse.ArgumentParser(description="Process Kindle books into unified book system")
    parser.add_argument("--research-only", action="store_true",
                        help="Research but don't run embeddings")
    parser.add_argument("--asin", type=str, help="Process specific book by ASIN")
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

    if args.asin:
        kindle_data = load_kindle_library()
        highlights_data = load_kindle_highlights()
        physical_data = load_physical_books()
        book = kindle_data.get('books', {}).get(args.asin)
        if not book:
            print(f"ASIN {args.asin} not found in Kindle library")
            sys.exit(1)
        process_single_book(args.asin, book, highlights_data, physical_data,
                            do_research=not args.no_research)
        save_physical_books(physical_data)
        return

    process_all(do_research=not args.no_research, max_books=args.max)


if __name__ == '__main__':
    main()

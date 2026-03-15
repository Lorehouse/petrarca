#!/usr/bin/env python3
"""
Find and upload EPUBs to the Petrarca server for text extraction.

Scans local directories for EPUB files, matches them to Kindle books
by title/author, and uploads to /opt/petrarca/data/epubs/ on the server.

Usage:
  python3 upload_epubs.py --scan          # find all EPUBs and show matches
  python3 upload_epubs.py --upload        # upload matched EPUBs to server
  python3 upload_epubs.py --upload FILE   # upload a specific EPUB
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

# Directories to scan for EPUBs
SCAN_DIRS = [
    Path.home() / "Downloads",
    Path.home() / "Calibre Library",
    Path.home() / "Dropbox",
    Path.home() / "Documents",
]

SERVER = "alif"  # SSH alias
SERVER_EPUB_DIR = "/opt/petrarca/data/epubs"


def find_epubs() -> list[dict]:
    """Find all EPUB files in scan directories."""
    epubs = []
    seen_paths = set()

    for scan_dir in SCAN_DIRS:
        if not scan_dir.exists():
            continue
        for epub_path in scan_dir.rglob("*.epub"):
            real = epub_path.resolve()
            if real in seen_paths:
                continue
            seen_paths.add(real)

            # Extract metadata from EPUB
            meta = extract_epub_metadata(epub_path)
            epubs.append({
                "path": str(epub_path),
                "filename": epub_path.name,
                "size_mb": round(epub_path.stat().st_size / 1024 / 1024, 1),
                "title": meta.get("title", epub_path.stem),
                "author": meta.get("author", ""),
            })

    # Also check loose EPUBs in home directory (max depth 2)
    for epub_path in Path.home().glob("*.epub"):
        real = epub_path.resolve()
        if real not in seen_paths:
            seen_paths.add(real)
            meta = extract_epub_metadata(epub_path)
            epubs.append({
                "path": str(epub_path),
                "filename": epub_path.name,
                "size_mb": round(epub_path.stat().st_size / 1024 / 1024, 1),
                "title": meta.get("title", epub_path.stem),
                "author": meta.get("author", ""),
            })

    return epubs


def extract_epub_metadata(epub_path: Path) -> dict:
    """Extract title and author from EPUB's OPF metadata."""
    try:
        with ZipFile(epub_path) as z:
            # Find the OPF file
            opf_path = None
            for name in z.namelist():
                if name.endswith(".opf"):
                    opf_path = name
                    break

            if not opf_path:
                return {}

            content = z.read(opf_path).decode("utf-8", errors="replace")

            title_match = re.search(r"<dc:title[^>]*>([^<]+)</dc:title>", content)
            author_match = re.search(r"<dc:creator[^>]*>([^<]+)</dc:creator>", content)

            return {
                "title": title_match.group(1).strip() if title_match else "",
                "author": author_match.group(1).strip() if author_match else "",
            }
    except Exception:
        return {}


def upload_epub(epub_path: str, book_id: str = ""):
    """Upload an EPUB to the server via SCP."""
    path = Path(epub_path)
    if not path.exists():
        print(f"  Error: {epub_path} not found")
        return False

    # Clean filename for server
    dest_name = path.name
    if book_id:
        # Prefix with book_id for easy matching
        dest_name = f"{book_id}__{path.name}"

    dest = f"{SERVER}:{SERVER_EPUB_DIR}/{dest_name}"
    print(f"  Uploading {path.name} ({path.stat().st_size // 1024}KB) → {dest}")

    result = subprocess.run(
        ["scp", str(path), dest],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"  SCP failed: {result.stderr.strip()}")
        return False

    print(f"  Uploaded successfully")
    return True


def main():
    parser = argparse.ArgumentParser(description="Find and upload EPUBs to Petrarca server")
    parser.add_argument("--scan", action="store_true", help="Find all EPUBs and show them")
    parser.add_argument("--upload", nargs="?", const="all", help="Upload EPUBs (optionally specify a file path)")
    args = parser.parse_args()

    if args.scan or not args.upload:
        epubs = find_epubs()
        print(f"Found {len(epubs)} EPUBs:\n")
        total_mb = 0
        for e in sorted(epubs, key=lambda x: x["title"].lower()):
            total_mb += e["size_mb"]
            print(f"  {e['size_mb']:5.1f}MB  {e['title'][:55]:55s}  {e['author'][:25]}")
            print(f"          {e['path']}")
        print(f"\nTotal: {total_mb:.0f}MB across {len(epubs)} files")

        if not args.upload:
            return

    if args.upload and args.upload != "all":
        # Upload a specific file
        upload_epub(args.upload)
        return

    if args.upload == "all":
        # Ensure server directory exists
        subprocess.run(["ssh", SERVER, f"mkdir -p {SERVER_EPUB_DIR}"], check=True)

        epubs = find_epubs()
        print(f"\nUploading {len(epubs)} EPUBs to {SERVER}:{SERVER_EPUB_DIR}/")
        uploaded = 0
        for e in epubs:
            if upload_epub(e["path"]):
                uploaded += 1
        print(f"\nUploaded {uploaded}/{len(epubs)} EPUBs")


if __name__ == "__main__":
    main()

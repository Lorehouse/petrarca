#!/usr/bin/env python3
"""
Podcast sync — exports Overcast listening history and syncs to Petrarca server.

Uses overcast-to-sqlite to fetch the extended OPML export, then filters
for played episodes from selected podcasts and syncs to the server.

Usage:
  python3 podcast_sync.py --auth           # authenticate with Overcast (first time)
  python3 podcast_sync.py --list-podcasts  # show all subscribed podcasts
  python3 podcast_sync.py --list-played    # show recently played episodes
  python3 podcast_sync.py --sync           # sync played episodes to server
  python3 podcast_sync.py --transcript EP  # fetch transcript for an episode

First run: authenticate with your Overcast credentials.
"""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

DB_PATH = Path.home() / "src/petrarca/overcast.db"
AUTH_PATH = Path.home() / ".config/overcast-to-sqlite/auth.json"
SERVER_URL = os.environ.get("PETRARCA_SERVER", "http://localhost:8090")

# Podcasts to include (empty = all played episodes)
# Add podcast titles here to filter, or leave empty for everything
INCLUDE_PODCASTS = []  # e.g., ["The Rest is History", "In Our Time"]


def run_overcast_cmd(*args):
    """Run overcast-to-sqlite via uvx."""
    cmd = ["uvx", "overcast-to-sqlite"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr.strip()}")
    return result


def authenticate():
    """Authenticate with Overcast."""
    print("Authenticating with Overcast...")
    print("You'll be prompted for your Overcast email and password.")
    # Run interactively
    subprocess.run(["uvx", "overcast-to-sqlite", "auth"])


def fetch_data():
    """Fetch latest data from Overcast."""
    print("Fetching Overcast data...")
    result = run_overcast_cmd("save", str(DB_PATH))
    if result.returncode == 0:
        print("Data saved to", DB_PATH)
    return result.returncode == 0


def list_podcasts():
    """List all subscribed podcasts."""
    if not DB_PATH.exists():
        print("No database. Run --sync first to fetch data.")
        return

    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute("""
        SELECT title, COUNT(*) as ep_count
        FROM episodes
        GROUP BY feedTitle
        ORDER BY ep_count DESC
    """).fetchall()

    # Try different column names since schema may vary
    try:
        rows = conn.execute("""
            SELECT DISTINCT feedTitle, COUNT(*) as cnt
            FROM episodes
            GROUP BY feedTitle
            ORDER BY cnt DESC
        """).fetchall()
    except:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        print("Tables:", [r[0] for r in rows])
        for table in [r[0] for r in rows]:
            cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
            print(f"  {table}: {[c[1] for c in cols]}")
        conn.close()
        return

    print(f"\n{len(rows)} podcasts:\n")
    for title, count in rows:
        print(f"  {count:4d} episodes  {title}")
    conn.close()


def list_played():
    """List recently played episodes."""
    if not DB_PATH.exists():
        if not fetch_data():
            return

    conn = sqlite3.connect(str(DB_PATH))

    # Discover schema
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

    # overcast-to-sqlite creates 'episodes' and 'feeds' tables (or 'podcasts' view)
    if 'episodes' not in tables:
        print(f"Tables: {tables}")
        for t in tables:
            cols = conn.execute(f"PRAGMA table_info({t})").fetchall()
            print(f"  {t}: {[c[1] for c in cols]}")
        conn.close()
        return

    cols = [c[1] for c in conn.execute("PRAGMA table_info(episodes)").fetchall()]
    print(f"Episode columns: {cols}")

    # Try to find played episodes
    played_col = 'played' if 'played' in cols else None
    title_col = 'title' if 'title' in cols else None
    feed_col = 'feedTitle' if 'feedTitle' in cols else ('podcast' if 'podcast' in cols else None)
    date_col = 'userUpdatedDate' if 'userUpdatedDate' in cols else ('pubDate' if 'pubDate' in cols else None)

    if played_col:
        query = f"SELECT {title_col}, {feed_col}, {date_col} FROM episodes WHERE {played_col} = 1 ORDER BY {date_col} DESC LIMIT 30"
    else:
        query = f"SELECT {title_col}, {feed_col}, {date_col} FROM episodes ORDER BY {date_col} DESC LIMIT 30"

    rows = conn.execute(query).fetchall()
    print(f"\nPlayed episodes ({len(rows)}):\n")
    for title, feed, date in rows:
        print(f"  {str(date)[:10]:10s}  {str(feed)[:30]:30s}  {str(title)[:50]}")

    conn.close()


def sync_to_server():
    """Sync played podcast episodes to Petrarca server."""
    if not DB_PATH.exists():
        if not fetch_data():
            return

    conn = sqlite3.connect(str(DB_PATH))
    cols = [c[1] for c in conn.execute("PRAGMA table_info(episodes)").fetchall()]

    # Build query for played episodes
    where = "played = 1" if 'played' in cols else "1=1"
    if INCLUDE_PODCASTS:
        feed_col = 'feedTitle' if 'feedTitle' in cols else 'podcast'
        placeholders = ','.join('?' * len(INCLUDE_PODCASTS))
        where += f" AND {feed_col} IN ({placeholders})"

    query = f"SELECT * FROM episodes WHERE {where} ORDER BY userUpdatedDate DESC"
    conn.row_factory = sqlite3.Row
    rows = conn.execute(query, INCLUDE_PODCASTS if INCLUDE_PODCASTS else []).fetchall()

    episodes = []
    for row in rows:
        episodes.append({
            'id': f'pod_{row["overcastId"]}' if 'overcastId' in row.keys() else f'pod_{hash(row["title"])}',
            'type': 'podcast',
            'title': row.get('title', ''),
            'source': row.get('feedTitle', row.get('podcast', '')),
            'url': row.get('overcastUrl', row.get('url', '')),
            'date_consumed': row.get('userUpdatedDate', ''),
            'duration': row.get('duration', 0),
            'enclosure_url': row.get('enclosureUrl', ''),
            'transcript_status': 'none',
            'claims_extracted': False,
        })

    conn.close()

    if not episodes:
        print("No played episodes to sync")
        return

    print(f"Syncing {len(episodes)} played episodes to server...")

    # POST to server
    payload = json.dumps({
        'items': episodes,
        'source': 'overcast',
        'synced_at': datetime.now(timezone.utc).isoformat(),
    }).encode()

    req = Request(
        f"{SERVER_URL}/media/sync",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(req) as resp:
            result = json.loads(resp.read())
            print(f"Synced: {result}")
    except Exception as e:
        print(f"Sync failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="Sync Overcast podcast history to Petrarca")
    parser.add_argument("--auth", action="store_true", help="Authenticate with Overcast")
    parser.add_argument("--list-podcasts", action="store_true", help="List subscribed podcasts")
    parser.add_argument("--list-played", action="store_true", help="List recently played episodes")
    parser.add_argument("--sync", action="store_true", help="Sync played episodes to server")
    parser.add_argument("--fetch", action="store_true", help="Fetch latest data from Overcast")
    args = parser.parse_args()

    if args.auth:
        authenticate()
        return

    if args.fetch or args.sync:
        fetch_data()

    if args.list_podcasts:
        list_podcasts()
    elif args.list_played:
        list_played()
    elif args.sync:
        sync_to_server()
    elif not args.auth and not args.fetch:
        # Default: show status
        if DB_PATH.exists():
            conn = sqlite3.connect(str(DB_PATH))
            try:
                ep_count = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
                played = conn.execute("SELECT COUNT(*) FROM episodes WHERE played = 1").fetchone()[0]
                print(f"Database: {ep_count} episodes, {played} played")
            except:
                print(f"Database exists at {DB_PATH}")
            conn.close()
        else:
            print("No data yet. Run: python3 podcast_sync.py --auth")


if __name__ == "__main__":
    main()

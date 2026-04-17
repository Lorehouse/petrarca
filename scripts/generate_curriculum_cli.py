#!/usr/bin/env python3
"""
CLI helper for curriculum generation with progress display.

Usage:
    python3 scripts/generate_curriculum_cli.py "History of Rome"
    python3 scripts/generate_curriculum_cli.py "Byzantine Empire" --depth intermediate
"""

import argparse
import requests
import time
import sys
import os

# Load .env if it exists
from pathlib import Path
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if '=' in line and not line.startswith('#'):
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip())

SERVER_URL = os.environ.get('PETRARCA_SERVER', 'http://localhost:8090')

# Check for tqdm
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("Tip: Install tqdm for a progress bar: pip install tqdm", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description='Generate a curriculum with progress display')
    parser.add_argument('domain', help='Domain/topic for the curriculum')
    parser.add_argument('--depth', default='introductory', choices=['introductory', 'intermediate', 'advanced'],
                        help='Curriculum depth (default: introductory)')
    parser.add_argument('--server', default=SERVER_URL, help='Server URL')
    args = parser.parse_args()

    # Start generation
    print(f"Starting curriculum generation for: {args.domain}")
    print(f"Depth: {args.depth}")
    print()

    try:
        resp = requests.post(
            f"{args.server}/curriculum/generate",
            json={'domain': args.domain, 'depth': args.depth, 'background': True},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        job_id = data.get('job_id')
        if not job_id:
            print(f"Error: No job_id returned: {data}")
            sys.exit(1)
        print(f"Job started: {job_id}")
    except requests.RequestException as e:
        print(f"Error starting generation: {e}")
        sys.exit(1)

    # Poll for status with progress display
    status_map = {
        'running': ('Generating curriculum', 0.3),
        'tagging': ('Tagging entities', 0.6),
        'bootstrapping_entities': ('Bootstrapping entities', 0.8),
        'done': ('Complete', 1.0),
        'failed': ('Failed', 0),
    }

    if HAS_TQDM:
        pbar = tqdm(total=100, desc="Generating", bar_format='{l_bar}{bar}| {desc}')
    
    last_status = None
    
    while True:
        try:
            resp = requests.get(f"{args.server}/curriculum/generate/status?id={job_id}", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            status = data.get('status', 'unknown')
            
            # Update progress display
            if status != last_status:
                if HAS_TQDM:
                    label, progress = status_map.get(status, (status, 0))
                    pbar.set_description(label)
                    pbar.update(int(progress * 100) - pbar.n)
                else:
                    print(f"Status: {status}")
                last_status = status
            
            if status == 'done':
                if HAS_TQDM:
                    pbar.update(100 - pbar.n)
                    pbar.close()
                print()
                print(f"Curriculum created: {data.get('domain_id', args.domain)}")
                print(f"Nodes: {data.get('node_count', 'unknown')}")
                if data.get('tagged'):
                    print(f"Entities tagged: {data.get('tagged')}")
                sys.exit(0)
            
            if status == 'failed':
                if HAS_TQDM:
                    pbar.close()
                print(f"\nGeneration failed: {data.get('error', 'unknown error')}")
                sys.exit(1)
            
            time.sleep(2)
            
        except requests.RequestException as e:
            if HAS_TQDM:
                pbar.close()
            print(f"\nError checking status: {e}")
            sys.exit(1)


if __name__ == '__main__':
    main()

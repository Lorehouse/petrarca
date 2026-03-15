#!/usr/bin/env python3
"""
Petrarca Research Agent Server

Simple HTTP server that accepts research requests from the app,
spawns `claude -p` in the background to find diverse perspectives,
and serves completed results back to the app.

Run: python3 research-server.py
Port: 8090
Results stored in: /opt/petrarca/research-results/
"""

import asyncio
import email
import email.policy
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, urlencode, parse_qs, unquote

RESULTS_DIR = Path(os.environ.get('RESEARCH_RESULTS_DIR', '/opt/petrarca/research-results'))
INGEST_DIR = Path(os.environ.get('INGEST_DIR', '/opt/petrarca/ingest'))
PORT = int(os.environ.get('RESEARCH_PORT', '8090'))
INGEST_TOKEN = os.environ.get('PETRARCA_INGEST_TOKEN', '')
BOOKS_OUTPUT_DIR = Path(os.environ.get('BOOKS_OUTPUT_DIR', '/opt/petrarca/data/books'))
CROSS_MATCH_DIR = Path(os.environ.get('CROSS_MATCH_DIR', '/opt/petrarca/data'))
SCRIPTS_DIR = Path(__file__).parent
VENV_PYTHON = '/opt/petrarca/.venv/bin/python3'

EMAILS_DIR = INGEST_DIR / 'emails'

CHAT_DIR = Path(os.environ.get('CHAT_DIR', '/opt/petrarca/data/chats'))
NOTES_DIR = Path(os.environ.get('NOTES_DIR', '/opt/petrarca/data/notes'))
AUDIO_DIR = Path(os.environ.get('AUDIO_DIR', '/opt/petrarca/data/audio'))
BOOK_UPLOADS_DIR = Path(os.environ.get('BOOK_UPLOADS_DIR', '/opt/petrarca/data/book-uploads'))
PHYSICAL_BOOKS_PATH = Path(os.environ.get('PHYSICAL_BOOKS_PATH', '/opt/petrarca/data/physical_books.json'))
LOG_DIR = Path(os.environ.get('LOG_DIR', '/opt/petrarca/data/logs'))
ARTICLES_PATH = Path(os.environ.get('ARTICLES_PATH', '/opt/petrarca/data/articles.json'))
SCRAPE_REPORTS_PATH = Path(os.environ.get('SCRAPE_REPORTS_PATH', '/opt/petrarca/data/scrape_reports.json'))
KINDLE_DATA_PATH = Path(os.environ.get('KINDLE_DATA_PATH', '/opt/petrarca/data/kindle_library.json'))
KINDLE_HIGHLIGHTS_PATH = Path(os.environ.get('KINDLE_HIGHLIGHTS_PATH', '/opt/petrarca/data/kindle_highlights.json'))
KINDLE_SYNC_LOG_PATH = Path(os.environ.get('KINDLE_SYNC_LOG_PATH', '/opt/petrarca/data/kindle_sync_log.jsonl'))
FEEDBACK_DIR = Path(os.environ.get('FEEDBACK_DIR', '/opt/petrarca/data/feedback'))

from server_log import log_server_event

SONIOX_API_KEY = os.environ.get('SONIOX_API_KEY', '557c7c5a86a2f5b8fa734ddbbe179f0f21fd342c762768c9af4f4ffff8c58e1f')
SONIOX_BASE_URL = 'https://api.soniox.com/v1'

TWIKIT_COOKIES_DIR = Path.home() / '.config' / 'twikit'
TWIKIT_COOKIES_PATH = TWIKIT_COOKIES_DIR / 'cookies.json'

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
INGEST_DIR.mkdir(parents=True, exist_ok=True)
EMAILS_DIR.mkdir(parents=True, exist_ok=True)
CHAT_DIR.mkdir(parents=True, exist_ok=True)
NOTES_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
BOOK_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Email processing (server-side)
# ---------------------------------------------------------------------------

def parse_email(raw_text: str) -> dict:
    """Parse raw email using Python email stdlib. Returns dict with subject, from, text_plain, text_html."""
    msg = email.message_from_string(raw_text, policy=email.policy.default)
    result = {
        'subject': str(msg.get('subject', '')).strip(),
        'from': str(msg.get('from', '')),
        'to': str(msg.get('to', '')),
        'date': str(msg.get('date', '')),
        'text_plain': '',
        'text_html': '',
    }

    # Strip Fwd:/Fw: prefixes
    result['subject'] = re.sub(r'^(Fwd?|Fw):\s*', '', result['subject'], flags=re.IGNORECASE).strip()

    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == 'text/plain' and not result['text_plain']:
                result['text_plain'] = part.get_content() or ''
            elif ct == 'text/html' and not result['text_html']:
                result['text_html'] = part.get_content() or ''
    else:
        ct = msg.get_content_type()
        body = msg.get_content() or ''
        if ct == 'text/html':
            result['text_html'] = body
        else:
            result['text_plain'] = body

    return result


def score_url(url: str) -> int:
    """Score a URL for likelihood of being an article. Returns -1 for rejects, 0+ for candidates."""
    try:
        parsed = urlparse(url)
    except Exception:
        return -1

    hostname = (parsed.hostname or '').lower()
    pathname = (parsed.path or '').lower()
    full = url.lower()

    # --- Hard rejects ---
    if re.search(r'\.(png|jpg|jpeg|gif|svg|webp|ico|avif|mp3|mp4|css|js|woff2?|ttf|eot|zip|pdf)(\?|$)', pathname):
        return -1
    if 'substackcdn.com' in hostname:
        return -1
    if 'cdn.' in hostname and re.search(r'\.(png|jpg|jpeg|gif|svg|webp)', pathname):
        return -1
    reject_hosts = ['doubleclick.net', 'google-analytics.com', 'googleusercontent.com',
                    'mailchimp.com', 'sendgrid.net', 'list-manage.com', 'mandrillapp.com',
                    'mailgun.org', 'constantcontact.com', 'campaign-archive.com',
                    'apps.apple.com', 'play.google.com']
    if any(h in hostname for h in reject_hosts):
        return -1
    if re.match(r'^(click|track|open|pixel|beacon|email|links?)\.', hostname):
        return -1
    if re.search(r'unsub|opt-out|optout|manage.preferences|email-preferences', full):
        return -1
    if 'substack.com' in hostname and re.match(r'^/(sign-in|account|app-link|embed|profile)', pathname):
        return -1
    if pathname in ('/', '/subscribe', '/publish', ''):
        return -1
    if re.match(r'^/@[^/]+/?$', pathname):
        return -1
    if re.search(r'1x1|beacon|pixel|\.gif\?', full):
        return -1
    if hostname == 't.co':
        return -1
    if re.match(r'^https?://(www\.)?(twitter|x)\.com/[^/]+/?$', url, re.IGNORECASE):
        return -1

    # --- Scoring ---
    score = 0
    segments = [s for s in pathname.split('/') if s]
    score += min(len(segments) * 2, 10)
    if len(pathname) > 20: score += 3
    if len(pathname) > 40: score += 2

    if re.search(r'substack\.com/p/', full): score += 15
    if re.search(r'open\.substack\.com/pub/[^/]+/p/', full): score += 20
    if re.search(r'medium\.com/.+/.+-[a-f0-9]{8,}', full): score += 15
    if re.search(r'/\d{4}/\d{2}/\d{2}/', pathname): score += 12
    if 'wordpress.com' in hostname and len(segments) >= 2: score += 10
    if re.search(r'/(article|post|blog|story|news|p)/', pathname, re.IGNORECASE): score += 8
    if re.search(r'substack\.com/redirect/', full): score -= 5

    last_seg = segments[-1] if segments else ''
    if '-' in last_seg and len(last_seg) > 10: score += 5

    return score


def clean_url(url: str) -> str | None:
    """Clean tracking params and trailing punctuation from a URL."""
    cleaned = re.sub(r'[.,;:!?)\]}\'"]+$', '', url)
    cleaned = re.sub(r'#$', '', cleaned)
    try:
        parsed = urlparse(cleaned)
        qs = parse_qs(parsed.query, keep_blank_values=False)
        remove = {'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
                  'mc_cid', 'mc_eid', 'ref', 'referer', 'fbclid', 'gclid'}
        filtered = {k: v for k, v in qs.items() if k not in remove}
        new_query = urlencode(filtered, doseq=True) if filtered else ''
        cleaned = parsed._replace(query=new_query).geturl()
        return cleaned
    except Exception:
        return None


def canonicalize_url(url: str) -> str:
    """Normalize URL for dedup: lowercase host, strip trailing slash and query."""
    try:
        parsed = urlparse(url)
        return f'{parsed.scheme}://{parsed.hostname.lower()}{parsed.path.rstrip("/")}'
    except Exception:
        return url


def decode_substack_redirect(url: str) -> str | None:
    """Try to decode Substack redirect URLs to get the real destination."""
    import base64
    m = re.search(r'substack\.com/redirect/\d+/([A-Za-z0-9_-]+)', url)
    if not m:
        return None
    try:
        b64 = m.group(1).replace('-', '+').replace('_', '/')
        while len(b64) % 4:
            b64 += '='
        decoded = base64.b64decode(b64).decode('utf-8', errors='replace')
        if decoded.startswith('http'):
            return decoded
        try:
            data = json.loads(decoded)
            return data.get('url') or data.get('r')
        except json.JSONDecodeError:
            return None
    except Exception:
        return None


def find_article_urls(html: str, plain_text: str) -> list[dict]:
    """Extract and rank article URLs from email content. Returns list of {url, score}."""
    url_scores: dict[str, int] = {}

    # Extract from HTML href attributes
    if html:
        for m in re.finditer(r'href=["\']?(https?://[^"\'>\s]+)', html, re.IGNORECASE):
            url = clean_url(m.group(1))
            if url:
                url_scores[url] = max(url_scores.get(url, 0), score_url(url))

    # Extract from plain text
    if plain_text:
        for m in re.finditer(r'https?://[^\s<>"{}|\\^`\[\]()]+', plain_text):
            url = clean_url(m.group(0))
            if url:
                url_scores[url] = max(url_scores.get(url, 0), score_url(url))

    # Decode Substack redirect URLs
    for url in list(url_scores.keys()):
        if 'substack.com/redirect/' in url:
            real = decode_substack_redirect(url)
            if real:
                cleaned = clean_url(real)
                if cleaned:
                    s = score_url(cleaned)
                    if s > 0:
                        url_scores[cleaned] = max(url_scores.get(cleaned, 0), s)

    # Filter, sort, dedup
    candidates = [{'url': u, 'score': s} for u, s in url_scores.items() if s > 0]
    candidates.sort(key=lambda c: c['score'], reverse=True)

    seen = set()
    deduped = []
    for c in candidates:
        canon = canonicalize_url(c['url'])
        if canon not in seen:
            seen.add(canon)
            deduped.append(c)

    return deduped


def strip_html(html: str) -> str:
    """Convert HTML to plain text."""
    text = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', html, flags=re.IGNORECASE)
    text = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</(p|div|tr|li|blockquote|h[1-6])>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    # Decode common HTML entities
    for entity, char in [('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'), ('&quot;', '"'),
                         ('&#39;', "'"), ('&nbsp;', ' '), ('&mdash;', '\u2014'),
                         ('&ndash;', '\u2013'), ('&hellip;', '\u2026')]:
        text = text.replace(entity, char)
    text = re.sub(r'&#x([0-9A-Fa-f]+);', lambda m: chr(int(m.group(1), 16)), text)
    text = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n[ \t]+', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def extract_clean_content(html: str, plain_text: str) -> str:
    """Extract clean article content from email body."""
    text = strip_html(html) if html else plain_text
    if not text:
        return ''

    # Remove forwarded email headers
    text = re.sub(r'^[-\s]*(From|To|Cc|Bcc|Date|Sent|Subject|Reply-To):.*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'^[-=*\s]*(Forwarded|Original) (message|email|mail)[-=*\s]*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'^Begin forwarded message:$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    # Remove reply chains
    text = re.sub(r'^>+.*$', '', text, flags=re.MULTILINE)
    # Remove unsubscribe/footer lines
    text = re.sub(r'^.*\b(unsubscribe|manage\s+preferences|opt[- ]out|view\s+in\s+browser|view\s+online|email\s+preferences|privacy\s+policy)\b.*$',
                  '', text, flags=re.MULTILINE | re.IGNORECASE)
    # Remove social media remnants
    text = re.sub(r'^\s*(Facebook|Twitter|Instagram|LinkedIn|YouTube|TikTok|Share|Like|Comment)\s*$',
                  '', text, flags=re.MULTILINE | re.IGNORECASE)
    # Remove "powered by" footers
    text = re.sub(r'^.*\b(powered by|built with)\s+(substack|mailchimp|convertkit|ghost|buttondown|beehiiv)\b.*$',
                  '', text, flags=re.MULTILINE | re.IGNORECASE)
    # Cut email signatures if in last 30%
    for pattern in [r'^--\s*$', r'^Sent from my ', r'^Sent from Mail for ', r'^Get Outlook for ']:
        m = re.search(pattern, text, re.MULTILINE)
        if m and m.start() > len(text) * 0.7:
            text = text[:m.start()]

    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def process_email(raw_text: str) -> None:
    """Process a raw email: save it, extract URLs or content, and ingest."""
    # Save raw email for replay
    ts = int(time.time())
    raw_path = EMAILS_DIR / f'email_{ts}.eml'
    raw_path.write_text(raw_text, encoding='utf-8')
    print(f'[email] Saved raw email to {raw_path.name}', flush=True)

    parsed = parse_email(raw_text)
    subject = parsed['subject']
    print(f'[email] Subject: "{subject}", from: {parsed["from"]}', flush=True)
    print(f'[email] HTML: {len(parsed["text_html"])} chars, Plain: {len(parsed["text_plain"])} chars', flush=True)

    # Strategy 1: Find article URLs
    candidates = find_article_urls(parsed['text_html'], parsed['text_plain'])
    top5 = candidates[:5]
    print(f'[email] Found {len(candidates)} candidate URLs', flush=True)
    for c in top5:
        print(f'  [{c["score"]:3d}] {c["url"][:100]}', flush=True)

    if candidates:
        top_score = candidates[0]['score']
        strong = [c for c in candidates if c['score'] >= top_score * 0.5]
        to_send = strong[:5]
        for c in to_send:
            print(f'[email] Ingesting URL: {c["url"][:100]}', flush=True)
            run_ingest(c['url'], subject, '', '', '', 'email')
        return

    # Strategy 2: Extract clean body text
    clean = extract_clean_content(parsed['text_html'], parsed['text_plain'])
    print(f'[email] No strong URLs found. Clean content: {len(clean)} chars', flush=True)

    if len(clean) > 200:
        pseudo_url = f'mailto:{parsed["from"]}?subject={subject}'
        print(f'[email] Ingesting email body as content: "{subject}"', flush=True)
        run_ingest(pseudo_url, subject, clean, '', '', 'email-body')
    else:
        print(f'[email] No usable content found in email', flush=True)


def build_research_prompt(query: str, article_title: str, article_summary: str, concepts: list[str]) -> str:
    concept_str = ', '.join(concepts[:15]) if concepts else 'none provided'
    return f"""You are a research assistant for a reader who is exploring ideas while reading articles. They recorded a voice note with a question or thought, and want you to find diverse perspectives and connections.

CONTEXT:
- Article being read: "{article_title}"
- Article summary: {article_summary}
- Related concepts the reader is tracking: {concept_str}

READER'S QUESTION/THOUGHT:
{query}

Please provide your response as a JSON object with exactly these three arrays of strings:

1. "perspectives" - 3-5 diverse perspectives on this question or topic. Each should be a concise paragraph (2-3 sentences) presenting a distinct viewpoint, school of thought, or angle. Include perspectives the reader might not have considered.

2. "recommendations" - 3-5 specific article, book, or paper recommendations. Each should be a single string like "Title by Author - brief description of why it's relevant".

3. "connections" - 2-3 connections to the reader's existing reading context (the article and concepts listed above). Each should explain how this question connects to or extends what they're already reading about.

Respond ONLY with valid JSON, no other text."""


def build_explore_prompt(subtopic: str, exploration_tag: str, triage_signals: dict, existing_concepts: list[str]) -> str:
    concept_str = ', '.join(existing_concepts[:20]) if existing_concepts else 'none'
    liked = ', '.join(triage_signals.get('liked', [])) or 'none yet'
    skipped = ', '.join(triage_signals.get('skipped', [])) or 'none yet'
    return f"""You are a research assistant helping a reader explore "{exploration_tag}".

The reader has shown interest in the subtopic: "{subtopic}"

READER CONTEXT:
- Exploration topic: {exploration_tag}
- Subtopics they liked/read: {liked}
- Subtopics they skipped: {skipped}
- Concepts they already track: {concept_str}

Find 3-5 high-quality articles or sources about "{subtopic}" in the context of {exploration_tag}. Look for:
- Mix of overview and in-depth content
- Diverse perspectives (academic, journalistic, personal essays)
- Sources that connect to what the reader already knows

Respond ONLY with valid JSON:
{{
  "articles": [
    {{
      "title": "Article or source title",
      "url": "Full URL",
      "description": "1-2 sentence description of why this is worth reading",
      "depth": "overview|intermediate|deep"
    }}
  ],
  "connections": ["1-2 sentences connecting this subtopic to reader's existing knowledge"]
}}"""


def run_explore(request_id: str, subtopic: str, exploration_tag: str, triage_signals: dict, existing_concepts: list[str]):
    result_path = RESULTS_DIR / f'{request_id}.json'
    result = {
        'id': request_id,
        'type': 'explore',
        'status': 'processing',
        'subtopic': subtopic,
        'exploration_tag': exploration_tag,
    }

    try:
        prompt = build_explore_prompt(subtopic, exploration_tag, triage_signals, existing_concepts)
        proc = subprocess.run(
            ['claude', '-p', prompt],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if proc.returncode != 0:
            result['status'] = 'failed'
            result['error'] = f'claude exited with code {proc.returncode}: {proc.stderr[:500]}'
        else:
            output = proc.stdout.strip()
            json_start = output.find('{')
            json_end = output.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                parsed = json.loads(output[json_start:json_end])
                result['status'] = 'completed'
                result['completed_at'] = int(time.time() * 1000)
                result['articles'] = parsed.get('articles', [])
                result['connections'] = parsed.get('connections', [])
            else:
                result['status'] = 'failed'
                result['error'] = 'Could not parse JSON from claude output'

    except subprocess.TimeoutExpired:
        result['status'] = 'failed'
        result['error'] = 'Explore research timed out after 5 minutes'
    except json.JSONDecodeError as e:
        result['status'] = 'failed'
        result['error'] = f'JSON parse error: {e}'
    except Exception as e:
        result['status'] = 'failed'
        result['error'] = str(e)

    result_path.write_text(json.dumps(result, indent=2))
    print(f'[explore] {request_id} -> {result["status"]}')


def run_research(request_id: str, query: str, article_title: str, article_summary: str, concepts: list[str]):
    result_path = RESULTS_DIR / f'{request_id}.json'
    result = {
        'id': request_id,
        'status': 'processing',
        'query': query,
        'article_title': article_title,
    }

    try:
        prompt = build_research_prompt(query, article_title, article_summary, concepts)
        proc = subprocess.run(
            ['claude', '-p', prompt],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if proc.returncode != 0:
            result['status'] = 'failed'
            result['error'] = f'claude exited with code {proc.returncode}: {proc.stderr[:500]}'
        else:
            output = proc.stdout.strip()
            # Extract JSON from the response (claude might wrap it in markdown)
            json_start = output.find('{')
            json_end = output.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                parsed = json.loads(output[json_start:json_end])
                result['status'] = 'completed'
                result['completed_at'] = int(time.time() * 1000)
                result['perspectives'] = parsed.get('perspectives', [])
                result['recommendations'] = parsed.get('recommendations', [])
                result['connections'] = parsed.get('connections', [])
            else:
                result['status'] = 'failed'
                result['error'] = 'Could not parse JSON from claude output'

    except subprocess.TimeoutExpired:
        result['status'] = 'failed'
        result['error'] = 'Research timed out after 5 minutes'
    except json.JSONDecodeError as e:
        result['status'] = 'failed'
        result['error'] = f'JSON parse error: {e}'
    except Exception as e:
        result['status'] = 'failed'
        result['error'] = str(e)

    result_path.write_text(json.dumps(result, indent=2))
    print(f'[research] {request_id} -> {result["status"]}')


# ---------------------------------------------------------------------------
# Twitter/X tweet ingestion via twikit
# ---------------------------------------------------------------------------

_TWEET_URL_RE = re.compile(r'https?://(?:twitter\.com|x\.com)/(\w+)/status/(\d+)')

def _is_tweet_url(url: str) -> bool:
    return bool(_TWEET_URL_RE.match(url))

def _extract_tweet_id(url: str) -> str | None:
    m = re.search(r'/status/(\d+)', url)
    return m.group(1) if m else None


async def _fetch_tweet_via_twikit(tweet_id: str) -> dict | None:
    """Fetch a single tweet by ID, reconstruct thread if applicable."""
    # Lazy imports — twikit may not be available in all environments
    sys.path.insert(0, str(SCRIPTS_DIR))
    from twikit import Client, Unauthorized
    from fetch_twitter_bookmarks import tweet_to_dict, reconstruct_thread

    if not TWIKIT_COOKIES_PATH.exists():
        print('[tweet] No twikit cookies found', flush=True)
        return None

    client = Client('en-US')
    client.load_cookies(str(TWIKIT_COOKIES_PATH))

    try:
        tweet = await client.get_tweet_by_id(tweet_id)
    except Unauthorized:
        print('[tweet] Cookies expired — cannot fetch tweet', flush=True)
        return None
    except Exception as e:
        print(f'[tweet] Failed to fetch tweet {tweet_id}: {e}', flush=True)
        return None

    if not tweet:
        return None

    tweet_dict = tweet_to_dict(tweet)

    # Reconstruct thread if this is a reply
    if tweet_dict.get('in_reply_to_tweet_id'):
        try:
            thread_texts = await reconstruct_thread(client, tweet_dict)
            if len(thread_texts) > 1:
                tweet_dict['thread_texts'] = thread_texts
                tweet_dict['thread_full_text'] = '\n\n---\n\n'.join(thread_texts)
                print(f'[tweet] Reconstructed thread: {len(thread_texts)} tweets', flush=True)
        except Exception as e:
            print(f'[tweet] Thread reconstruction failed: {e}', flush=True)

    return tweet_dict


def _extract_urls_from_tweet(tweet_dict: dict) -> list[str]:
    """Extract article-worthy URLs from a tweet, resolving t.co shortlinks."""
    sys.path.insert(0, str(SCRIPTS_DIR))
    from build_articles import _collect_urls_from_bookmark
    return _collect_urls_from_bookmark(tweet_dict)


def run_ingest_tweet(url: str, comment: str, ingest_id: str):
    """Fetch a tweet via twikit and ingest through the normal pipeline."""
    tweet_id = _extract_tweet_id(url)
    article_id = hashlib.sha256(url.encode()).hexdigest()[:12]
    log_path = INGEST_DIR / f'{ingest_id}.json'

    log_entry = {
        'id': ingest_id,
        'article_id': article_id,
        'status': 'processing',
        'url': url,
        'source': 'twitter_clip',
        'requested_at': int(time.time() * 1000),
    }
    log_path.write_text(json.dumps(log_entry, indent=2))

    if not tweet_id:
        log_entry['status'] = 'failed'
        log_entry['error'] = 'Could not extract tweet ID from URL'
        log_path.write_text(json.dumps(log_entry, indent=2))
        return

    # Fetch tweet (async → sync bridge)
    try:
        tweet_dict = asyncio.run(_fetch_tweet_via_twikit(tweet_id))
    except Exception as e:
        print(f'[tweet] twikit fetch error: {e}', flush=True)
        tweet_dict = None

    if not tweet_dict:
        # Fallback: try normal URL ingest (will likely fail for twitter.com but worth trying)
        print(f'[tweet] Falling back to normal URL ingest for {url[:60]}', flush=True)
        run_ingest(url, '', '', '', comment, 'twitter_clip', ingest_id)
        return

    author = tweet_dict.get('author_username', '')
    thread_text = tweet_dict.get('thread_full_text', tweet_dict.get('text', ''))
    # Normalize single newlines to paragraph breaks for non-thread tweets
    # (raw tweet text uses \n for visual breaks, but markdown needs \n\n)
    if not tweet_dict.get('thread_full_text') and '\n\n' not in thread_text:
        thread_text = '\n\n'.join(line for line in thread_text.split('\n') if line.strip())

    # Try to extract article URLs from the tweet
    try:
        article_urls = _extract_urls_from_tweet(tweet_dict)
    except Exception as e:
        print(f'[tweet] URL extraction failed: {e}', flush=True)
        article_urls = []

    if article_urls:
        # Ingest the linked article, with tweet context
        target_url = article_urls[0]
        tweet_context = f'Shared by @{author}: {tweet_dict["text"][:500]}'
        combined_comment = f'{tweet_context}\n\n{comment}' if comment else tweet_context
        print(f'[tweet] Found linked article: {target_url[:80]}', flush=True)
        run_ingest(target_url, '', '', '', combined_comment, 'twitter_clip', ingest_id)
    else:
        # Use tweet text/thread as article content
        title = f'Thread by @{author}' if tweet_dict.get('thread_full_text') else f'Tweet by @{author}'
        content = f'# {title}\n\n{thread_text}'
        print(f'[tweet] Using tweet text as content ({len(thread_text.split())} words)', flush=True)
        run_ingest(url, title, content, '', comment, 'twitter_clip', ingest_id)


async def _check_twikit_cookies() -> dict:
    """Check if twikit cookies are valid. Returns status dict."""
    if not TWIKIT_COOKIES_PATH.exists():
        return {'valid': False, 'error': 'No cookies file found'}

    try:
        cookies_mtime = TWIKIT_COOKIES_PATH.stat().st_mtime
        age_days = (time.time() - cookies_mtime) / 86400
    except Exception:
        age_days = -1

    sys.path.insert(0, str(SCRIPTS_DIR))
    from twikit import Client, Unauthorized

    client = Client('en-US')
    client.load_cookies(str(TWIKIT_COOKIES_PATH))

    try:
        await client.get_bookmarks(count=1)
        return {'valid': True, 'age_days': round(age_days, 1)}
    except Unauthorized:
        return {'valid': False, 'error': 'Cookies expired', 'age_days': round(age_days, 1)}
    except Exception as e:
        return {'valid': False, 'error': str(e), 'age_days': round(age_days, 1)}


# ---------------------------------------------------------------------------
# Standard URL ingestion
# ---------------------------------------------------------------------------

def _process_youtube_video(video_id, title, channel, url, description, chapters):
    """Background: fetch YouTube transcript, build article content, process through pipeline."""
    try:
        transcript_text = ''
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            ytt = YouTubeTranscriptApi()
            transcript_data = ytt.fetch(video_id)
            transcript_text = ' '.join(snippet.text for snippet in transcript_data)
            print(f'[youtube] Transcript: {len(transcript_text)} chars for {video_id}', flush=True)
        except Exception as e:
            print(f'[youtube] Transcript fetch failed for {video_id}: {e}', flush=True)
            transcript_text = description

        if not transcript_text:
            print(f'[youtube] No content for {video_id}', flush=True)
            return

        content = f'# {title}\n\n**Channel**: {channel}\n\n'
        if chapters:
            content += '**Chapters**:\n'
            for ch in chapters:
                content += f'- {ch.get("time", "")} {ch.get("title", "")}\n'
            content += '\n'
        content += '## Transcript\n\n' + transcript_text

        # Process through standard article pipeline
        from build_articles import process_single_article
        process_single_article(
            url=url,
            title=f'{title} — {channel} (YouTube)',
            content=content,
            source='youtube',
        )
        print(f'[youtube] Processed: "{title}" ({len(transcript_text)} chars)', flush=True)

        # Update media log status
        media_log_path = Path(os.environ.get('MEDIA_LOG_PATH', '/opt/petrarca/data/media_log.json'))
        try:
            media_log = json.loads(media_log_path.read_text())
            for item in media_log['items']:
                if item['id'] == f'yt_{video_id}':
                    item['transcript_status'] = 'available'
                    item['claims_extracted'] = True
                    break
            media_log_path.write_text(json.dumps(media_log, indent=2, ensure_ascii=False))
        except Exception:
            pass
    except Exception as e:
        print(f'[youtube] Error processing {video_id}: {e}', flush=True)
        import traceback
        traceback.print_exc()


def run_ingest(url: str, title: str, content: str, selected_text: str, comment: str, source: str, ingest_id: str | None = None):
    """Import a URL via import_url.py, optionally with pre-extracted content."""
    if not ingest_id:
        ingest_id = f'ingest_{int(time.time())}_{hash(url) % 10000:04d}'
    article_id = hashlib.sha256(url.encode()).hexdigest()[:12]
    log_path = INGEST_DIR / f'{ingest_id}.json'

    log_entry = {
        'id': ingest_id,
        'article_id': article_id,
        'status': 'processing',
        'url': url,
        'title': title,
        'source': source,
        'requested_at': int(time.time() * 1000),
    }
    log_path.write_text(json.dumps(log_entry, indent=2))

    content_file = None
    try:
        cmd = [VENV_PYTHON, str(SCRIPTS_DIR / 'import_url.py'), url, '--tag', 'manual']

        # If content was provided by the clipper, write it to a temp file
        if content and len(content.strip()) > 100:
            content_file = tempfile.NamedTemporaryFile(
                mode='w', suffix='.txt', prefix='petrarca_clip_',
                dir=str(INGEST_DIR), delete=False
            )
            content_file.write(content)
            content_file.close()
            cmd.extend(['--content-file', content_file.name])

        print(f'[ingest] Running: {" ".join(cmd[:5])}...', flush=True)
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            cwd=str(SCRIPTS_DIR),
        )

        if proc.returncode != 0:
            log_entry['status'] = 'failed'
            log_entry['error'] = proc.stderr[:1000]
            print(f'[ingest] {ingest_id} FAILED: {proc.stderr[:200]}', flush=True)
        else:
            log_entry['status'] = 'completed'
            log_entry['completed_at'] = int(time.time() * 1000)
            print(f'[ingest] {ingest_id} completed', flush=True)

        if proc.stdout:
            log_entry['stdout'] = proc.stdout[:2000]
        if proc.stderr:
            log_entry['stderr'] = proc.stderr[:2000]

    except subprocess.TimeoutExpired:
        log_entry['status'] = 'failed'
        log_entry['error'] = 'import_url.py timed out after 10 minutes'
        print(f'[ingest] {ingest_id} TIMEOUT', flush=True)
    except Exception as e:
        log_entry['status'] = 'failed'
        log_entry['error'] = str(e)
        print(f'[ingest] {ingest_id} ERROR: {e}', flush=True)
    finally:
        # Clean up temp content file
        if content_file and os.path.exists(content_file.name):
            os.unlink(content_file.name)

    # Save highlights and comments as sidecar data
    if selected_text or comment:
        sidecar = {
            'url': url,
            'title': title,
            'source': source,
            'created_at': int(time.time() * 1000),
        }
        if selected_text:
            sidecar['highlights'] = [{'text': selected_text, 'source': 'clipper'}]
        if comment:
            sidecar['notes'] = [{'text': comment, 'source': source}]
        sidecar_path = INGEST_DIR / f'{ingest_id}_sidecar.json'
        sidecar_path.write_text(json.dumps(sidecar, indent=2))
        log_entry['sidecar'] = str(sidecar_path)

    log_path.write_text(json.dumps(log_entry, indent=2))


def run_ingest_book(book_path: str, chapter: int | None, request_id: str):
    """Run ingest_book_petrarca.py to process a book."""
    result_path = RESULTS_DIR / f'{request_id}.json'
    result = {
        'id': request_id,
        'type': 'book_ingest',
        'status': 'processing',
        'book_path': book_path,
        'chapter': chapter,
        'requested_at': int(time.time() * 1000),
    }
    result_path.write_text(json.dumps(result, indent=2))

    try:
        cmd = [
            VENV_PYTHON,
            str(SCRIPTS_DIR / 'ingest_book_petrarca.py'),
            book_path,
            '--output-dir', str(BOOKS_OUTPUT_DIR),
            '--cross-match-dir', str(CROSS_MATCH_DIR),
        ]
        if chapter is not None:
            cmd.extend(['--chapter', str(chapter)])

        print(f'[book-ingest] Running: {" ".join(cmd[:6])}...', flush=True)
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800,  # 30 min for full book
            cwd=str(SCRIPTS_DIR),
        )

        if proc.returncode != 0:
            result['status'] = 'failed'
            result['error'] = proc.stderr[:2000]
            print(f'[book-ingest] {request_id} FAILED: {proc.stderr[:200]}', flush=True)
        else:
            result['status'] = 'completed'
            result['completed_at'] = int(time.time() * 1000)
            print(f'[book-ingest] {request_id} completed', flush=True)

        if proc.stdout:
            result['stdout'] = proc.stdout[:5000]
        if proc.stderr:
            result['stderr'] = proc.stderr[:2000]

    except subprocess.TimeoutExpired:
        result['status'] = 'failed'
        result['error'] = 'Book ingestion timed out after 30 minutes'
        print(f'[book-ingest] {request_id} TIMEOUT', flush=True)
    except Exception as e:
        result['status'] = 'failed'
        result['error'] = str(e)
        print(f'[book-ingest] {request_id} ERROR: {e}', flush=True)

    result_path.write_text(json.dumps(result, indent=2))


def build_explore_batch_prompt(concepts: list[dict]) -> str:
    concept_lines = '\n'.join(
        f'- "{c["name"]}" (context: {c.get("context_article_title", "N/A")})'
        for c in concepts
    )
    return f"""You are a research assistant. A reader wants to explore these concepts further. For each concept, find 2-3 high-quality URLs from diverse sources (academic, journalism, essays, Wikipedia).

CONCEPTS TO EXPLORE:
{concept_lines}

For each concept, find articles that would help a curious reader understand it better. Look for diverse perspectives and reliable sources.

Return ONLY valid JSON:
{{
  "results": [
    {{
      "concept_name": "the concept name",
      "urls": [
        {{
          "url": "https://...",
          "title": "Article title",
          "description": "Why this is worth reading"
        }}
      ]
    }}
  ]
}}"""


def run_explore_batch(request_id: str, concepts: list[dict]):
    result_path = RESULTS_DIR / f'{request_id}.json'
    result = {
        'id': request_id,
        'type': 'explore_batch',
        'status': 'processing',
        'concept_count': len(concepts),
        'requested_at': int(time.time() * 1000),
    }
    result_path.write_text(json.dumps(result, indent=2))

    try:
        prompt = build_explore_batch_prompt(concepts)
        proc = subprocess.run(
            ['claude', '-p', prompt],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if proc.returncode != 0:
            result['status'] = 'failed'
            result['error'] = f'claude exited with code {proc.returncode}: {proc.stderr[:500]}'
        else:
            output = proc.stdout.strip()
            json_start = output.find('{')
            json_end = output.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                parsed = json.loads(output[json_start:json_end])
                result['status'] = 'completed'
                result['completed_at'] = int(time.time() * 1000)
                result['results'] = parsed.get('results', [])

                # Auto-import top 2 URLs per concept
                for concept_result in result.get('results', []):
                    for url_entry in concept_result.get('urls', [])[:2]:
                        url = url_entry.get('url', '')
                        if url:
                            print(f'[explore-batch] Auto-importing: {url[:80]}', flush=True)
                            threading.Thread(
                                target=run_ingest,
                                args=(url, url_entry.get('title', ''), '', '', '', 'explore-batch'),
                                daemon=True,
                            ).start()
            else:
                result['status'] = 'failed'
                result['error'] = 'Could not parse JSON from claude output'

    except subprocess.TimeoutExpired:
        result['status'] = 'failed'
        result['error'] = 'Explore batch timed out after 5 minutes'
    except json.JSONDecodeError as e:
        result['status'] = 'failed'
        result['error'] = f'JSON parse error: {e}'
    except Exception as e:
        result['status'] = 'failed'
        result['error'] = str(e)

    result_path.write_text(json.dumps(result, indent=2))
    print(f'[explore-batch] {request_id} -> {result["status"]} ({len(concepts)} concepts)', flush=True)


# --- Voice notes: backend transcription + storage ---

def transcribe_on_server(audio_path: Path) -> str:
    """Upload audio to Soniox, transcribe, return text."""
    import requests as req

    headers = {'Authorization': f'Bearer {SONIOX_API_KEY}'}

    # Upload file
    with open(audio_path, 'rb') as f:
        resp = req.post(f'{SONIOX_BASE_URL}/files', headers=headers,
                        files={'file': ('note.m4a', f, 'audio/m4a')})
    resp.raise_for_status()
    file_id = resp.json()['id']

    # Create transcription
    resp = req.post(f'{SONIOX_BASE_URL}/transcriptions', headers=headers,
                    json={'model': 'stt-async-v4', 'file_id': file_id,
                          'language_hints': ['en', 'no', 'sv', 'da', 'it', 'de', 'es', 'fr', 'zh', 'id']})
    resp.raise_for_status()
    txn_id = resp.json()['id']

    # Poll
    for _ in range(90):  # 3 min max
        time.sleep(2)
        resp = req.get(f'{SONIOX_BASE_URL}/transcriptions/{txn_id}', headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if data['status'] == 'completed':
            break
        if data['status'] == 'error':
            raise RuntimeError(f'Soniox error: {data.get("error_message", "unknown")}')

    # Get transcript
    resp = req.get(f'{SONIOX_BASE_URL}/transcriptions/{txn_id}/transcript', headers=headers)
    resp.raise_for_status()
    data = resp.json()
    text = ''
    if data.get('tokens'):
        text = ''.join(t['text'] for t in data['tokens']).strip()
    elif data.get('text'):
        text = data['text'].strip()

    # Cleanup
    try:
        req.delete(f'{SONIOX_BASE_URL}/transcriptions/{txn_id}', headers=headers)
        req.delete(f'{SONIOX_BASE_URL}/files/{file_id}', headers=headers)
    except Exception:
        pass

    return text


def extract_note_actions(transcript: str, article_title: str, topics: list[str]) -> list[dict]:
    """Use Gemini to extract actionable intents from a voice note transcript."""
    import uuid
    from gemini_llm import call_llm

    prompt = f"""Analyze this voice note transcript and extract actionable intents.

Voice note transcript: "{transcript}"
Article being read: "{article_title}"
Article topics: {', '.join(topics[:5])}

Extract any of these intent types:
- "research": User wants to look up or explore a topic further
- "tag": User wants to tag or categorize something
- "remember": User wants to remember a specific insight or fact

Return a JSON array of actions. Each action has:
- "type": one of "research", "tag", "remember"
- "description": brief human-readable description
- "topic": (for research) the topic to research
- "tag": (for tag) the tag name
- "note_text": (for remember) the text to remember

If no clear actions are found, return an empty array.
Return ONLY the JSON array, no other text."""

    try:
        raw = call_llm(prompt, max_tokens=1000)
        if not raw:
            return []
        # Strip markdown code fences if present
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1] if '\n' in raw else raw[3:]
            if raw.endswith('```'):
                raw = raw[:-3].strip()

        json_start = raw.find('[')
        json_end = raw.rfind(']') + 1
        if json_start >= 0 and json_end > json_start:
            actions = json.loads(raw[json_start:json_end])
            for action in actions:
                action['id'] = f'act_{uuid.uuid4().hex[:8]}'
                action['status'] = 'pending'
            return actions
    except Exception as e:
        print(f'[note] Action extraction failed: {e}', flush=True)

    return []


def process_voice_note(note_id: str, audio_path: Path, article_id: str, topics: list[str],
                       article_title: str, article_context: str):
    """Background: transcribe audio, store note, extract actions."""
    note_path = NOTES_DIR / f'{note_id}.json'
    note = {
        'id': note_id,
        'article_id': article_id,
        'article_title': article_title,
        'topics': topics,
        'status': 'transcribing',
        'created_at': int(time.time()),
    }
    note_path.write_text(json.dumps(note, indent=2))

    try:
        transcript = transcribe_on_server(audio_path)
        note['transcript'] = transcript
        note['status'] = 'complete'
        note_path.write_text(json.dumps(note, indent=2))
        print(f'[note] {note_id} transcribed: {transcript[:80]}...', flush=True)

        # Extract actions from transcript
        actions = extract_note_actions(transcript, article_title, topics)
        if actions:
            note['actions'] = actions
            note_path.write_text(json.dumps(note, indent=2))
            print(f'[note] {note_id} extracted {len(actions)} actions', flush=True)
    except Exception as e:
        note['status'] = 'failed'
        note['error'] = str(e)
        note_path.write_text(json.dumps(note, indent=2))
        print(f'[note] {note_id} transcription failed: {e}', flush=True)


def run_topic_research(request_id: str, topic: str, context: str, article_titles: list[str]):
    """Background: use Gemini with search grounding to find articles on a topic, then ingest them."""
    from gemini_llm import call_with_search

    result_path = RESULTS_DIR / f'{request_id}.json'
    result = {
        'id': request_id,
        'type': 'topic_research',
        'status': 'processing',
        'topic': topic,
        'requested_at': int(time.time() * 1000),
    }
    result_path.write_text(json.dumps(result, indent=2))

    prompt = f"""You are a research assistant for Petrarca, a read-later app. The user is interested in the topic "{topic}".

Context about what they've been reading:
{context}

Articles they already have on this topic:
{chr(10).join(f'- {t}' for t in article_titles[:10])}

Search the web and find 3-5 high-quality articles, blog posts, or papers that would give the user genuinely NEW perspectives on this topic. Prioritize:
- Diverse viewpoints (not just the same take rehashed)
- Primary sources over aggregators
- Recent and substantive pieces
- Content that complements rather than duplicates what they already have

Return ONLY valid JSON (no markdown fences):
{{
  "articles": [
    {{"url": "https://...", "title": "...", "why": "One sentence on why this is valuable"}}
  ]
}}"""

    try:
        output = call_with_search(prompt)
        if not output:
            result['status'] = 'failed'
            result['error'] = 'No response from Gemini'
        else:
            json_start = output.find('{')
            json_end = output.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                parsed = json.loads(output[json_start:json_end])
                articles = parsed.get('articles', [])
                result['status'] = 'completed'
                result['completed_at'] = int(time.time() * 1000)
                result['found_articles'] = articles

                # Auto-ingest top articles sequentially (import_url.py uses file locking)
                for art in articles[:3]:
                    url = art.get('url', '')
                    if url:
                        print(f'[topic_research] Ingesting: {url}', flush=True)
                        run_ingest(url, art.get('title', ''), '', '', art.get('why', ''), f'research:{topic}')
            else:
                result['status'] = 'failed'
                result['error'] = 'Could not parse JSON from Gemini response'
                result['raw_output'] = output[:1000]
    except Exception as e:
        result['status'] = 'failed'
        result['error'] = str(e)

    result_path.write_text(json.dumps(result, indent=2))
    print(f'[topic_research] {request_id} -> {result["status"]}', flush=True)


# --- Generate more follow-up questions ---

def generate_more_questions(article_id: str, existing_questions: list[str]) -> list[dict]:
    """Generate additional follow-up questions for an article using Gemini."""
    from gemini_llm import call_llm

    # Load article data
    try:
        articles = json.loads(ARTICLES_PATH.read_text())
        article = next((a for a in articles if a.get('id') == article_id), None)
    except (OSError, json.JSONDecodeError):
        article = None

    if not article:
        return []

    title = article.get('title', 'Untitled')
    summary = article.get('one_line_summary', '') or article.get('full_summary', '')
    claims = article.get('key_claims', [])
    topics = article.get('topics', [])
    entities = [e.get('name', '') for e in article.get('entities', [])]

    existing_list = '\n'.join(f'- {q}' for q in existing_questions) if existing_questions else '(none)'

    prompt = f"""Given this article, generate 3 NEW follow-up questions that a curious, well-read person would want to explore.

Article: "{title}"
Summary: {summary}
Key claims: {json.dumps(claims[:6])}
Topics: {', '.join(topics[:8])}
Entities: {', '.join(entities[:8])}

Already-shown questions (do NOT repeat or rephrase these):
{existing_list}

Generate 3 diverse questions that:
- Connect to adjacent domains, historical parallels, or contrasting perspectives
- Are genuinely curiosity-driven — the kind that lead to interesting rabbit holes
- Span different angles: one might be comparative, one might be historical/contextual, one might challenge assumptions
- Each has a "connects_to" field naming the broader topic area it relates to

Return ONLY a JSON array:
[
  {{"question": "...", "connects_to": "..."}},
  {{"question": "...", "connects_to": "..."}},
  {{"question": "...", "connects_to": "..."}}
]"""

    result = call_llm(prompt, max_tokens=1024)
    if not result:
        return []

    # Parse JSON from response
    try:
        cleaned = result.strip()
        if cleaned.startswith('```'):
            cleaned = re.sub(r'^```\w*\n?', '', cleaned)
            cleaned = re.sub(r'\n?```$', '', cleaned)
        questions = json.loads(cleaned)
        if isinstance(questions, list):
            return [q for q in questions if isinstance(q, dict) and 'question' in q and 'connects_to' in q]
    except json.JSONDecodeError:
        print(f'[generate-questions] JSON parse failed for article {article_id}', flush=True)

    return []


# --- Chat with article context ---

def handle_chat(question: str, context: str, conversation_id: str | None = None) -> dict:
    """Synchronous chat using Gemini via google.genai SDK."""
    import uuid
    from gemini_llm import call_chat

    if not conversation_id:
        conversation_id = str(uuid.uuid4())[:12]

    # Load conversation history
    chat_file = CHAT_DIR / f'{conversation_id}.json'
    history = []
    if chat_file.exists():
        try:
            history = json.loads(chat_file.read_text())
        except (json.JSONDecodeError, OSError):
            history = []

    # Build messages
    messages = [
        {'role': 'system', 'content': (
            'You are a helpful reading assistant for Petrarca, an intelligent read-later app. '
            'The user is reading an article and has a question. You have the article\'s metadata, '
            'summary, key claims, topics, and text as context. Answer concisely and helpfully. '
            'If the user asks about claims, topics, or connections to other knowledge, be specific.'
        )},
    ]

    # Add context as first user message if this is a new conversation
    if not history:
        messages.append({'role': 'user', 'content': f'[Article context]\n{context}'})
        messages.append({'role': 'assistant', 'content': 'I have the article context. What would you like to know?'})

    # Add conversation history
    for msg in history:
        messages.append({'role': msg['role'], 'content': msg['content']})

    # Add current question
    messages.append({'role': 'user', 'content': question})

    answer = call_chat(messages)
    if not answer:
        answer = 'Error: could not get response from Gemini'

    # Save to history
    history.append({'role': 'user', 'content': question, 'timestamp': int(time.time())})
    history.append({'role': 'assistant', 'content': answer, 'timestamp': int(time.time())})
    chat_file.write_text(json.dumps(history, indent=2))

    return {'answer': answer, 'conversation_id': conversation_id}


# ---------------------------------------------------------------------------
# Physical book endpoints — processing functions
# ---------------------------------------------------------------------------

def process_book_identify(image_path: Path) -> dict:
    """Identify a book from a cover/title page photo using Gemini Vision + web search."""
    from gemini_llm import call_vision, call_with_search

    image_data = image_path.read_bytes()
    mime_type = 'image/png' if str(image_path).endswith('.png') else 'image/jpeg'

    # Step 1: Extract title/author from photo
    vision_result = call_vision(
        image_data,
        """Identify this book from the cover or title page photo.
Return a JSON object with:
{
  "title": "exact book title",
  "author": "author name(s)",
  "isbn": "ISBN if visible, else null",
  "publisher": "publisher if visible, else null",
  "year": null
}
Return ONLY valid JSON.""",
        mime_type=mime_type,
        response_mime_type="application/json",
    )

    if not vision_result:
        return {'error': 'Could not identify book from image'}

    try:
        cleaned = vision_result.strip()
        if cleaned.startswith('```'):
            cleaned = re.sub(r'^```(?:json)?\n?', '', cleaned)
            cleaned = re.sub(r'\n?```$', '', cleaned)
        book_info = json.loads(cleaned)
    except json.JSONDecodeError:
        return {'error': f'Failed to parse vision result: {vision_result[:200]}'}

    title = book_info.get('title', '')
    author = book_info.get('author', '')
    if not title:
        return {'error': 'Could not extract title from image'}

    # Step 2: Web search for metadata and cover
    search_result = call_with_search(
        f"""Find metadata for this book:
Title: {title}
Author: {author}

Return a JSON object with:
{{
  "title": "full official title",
  "author": "full author name(s)",
  "cover_url": "URL to a high-quality cover image (Amazon, Google Books, or publisher)",
  "isbn": "ISBN-13 if available",
  "publisher": "publisher name",
  "year": publication year as integer,
  "page_count": total pages as integer,
  "topics": ["3-5 topic tags for this book"]
}}
Return ONLY valid JSON.""",
    )

    if search_result:
        try:
            cleaned = search_result.strip()
            if cleaned.startswith('```'):
                cleaned = re.sub(r'^```(?:json)?\n?', '', cleaned)
                cleaned = re.sub(r'\n?```$', '', cleaned)
            metadata = json.loads(cleaned)
            # Merge vision result with search metadata (search wins for richer data)
            for key in ('title', 'author', 'isbn', 'publisher', 'year', 'page_count', 'cover_url', 'topics'):
                if metadata.get(key) and not book_info.get(key):
                    book_info[key] = metadata[key]
                elif metadata.get(key):
                    book_info[key] = metadata[key]
        except json.JSONDecodeError:
            pass  # Use vision result as-is

    # Ensure topics is a list
    if not isinstance(book_info.get('topics'), list):
        book_info['topics'] = []

    # Step 3: Try to find table of contents via web search
    chapters = _find_toc_online(title, author)
    if chapters:
        book_info['chapters'] = chapters

    # Step 4: Find cover image via book APIs (much more reliable than LLM-generated URLs)
    cover_url = _find_cover_image(book_info.get('isbn'), title, author)
    if cover_url:
        book_info['cover_url'] = cover_url
    elif book_info.get('cover_url'):
        # Verify LLM-provided URL actually works before trusting it
        if not _url_returns_image(book_info['cover_url']):
            del book_info['cover_url']

    print(f'[book/identify] Identified: {book_info.get("title")} by {book_info.get("author")} (cover: {bool(book_info.get("cover_url"))})', flush=True)
    return book_info


def _find_cover_image(isbn: str | None, title: str, author: str) -> str | None:
    """Find a book cover image URL via Open Library (ISBN) then Google Books (title/author)."""
    import urllib.request
    import urllib.error

    # Try Open Library by ISBN first (direct image URL, no API key needed)
    if isbn:
        clean_isbn = re.sub(r'[^0-9X]', '', isbn.upper())
        if clean_isbn:
            ol_url = f'https://covers.openlibrary.org/b/isbn/{clean_isbn}-L.jpg?default=false'
            try:
                req = urllib.request.Request(ol_url, method='HEAD')
                req.add_header('User-Agent', 'Petrarca/1.0')
                resp = urllib.request.urlopen(req, timeout=5)
                if resp.status == 200 and 'image' in resp.headers.get('Content-Type', ''):
                    print(f'[cover] Found via Open Library ISBN: {clean_isbn}', flush=True)
                    return ol_url
            except (urllib.error.HTTPError, urllib.error.URLError, OSError):
                pass

    # Try Google Books API (free, no key needed for low volume)
    try:
        query = urllib.parse.quote(f'intitle:{title} inauthor:{author}')
        gb_url = f'https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=1'
        req = urllib.request.Request(gb_url)
        req.add_header('User-Agent', 'Petrarca/1.0')
        resp = urllib.request.urlopen(req, timeout=8)
        data = json.loads(resp.read().decode())
        items = data.get('items', [])
        if items:
            image_links = items[0].get('volumeInfo', {}).get('imageLinks', {})
            # Prefer larger images, upgrade HTTP to HTTPS
            for key in ('extraLarge', 'large', 'medium', 'thumbnail', 'smallThumbnail'):
                if key in image_links:
                    url = image_links[key].replace('http://', 'https://')
                    # Remove edge=curl parameter for cleaner image
                    url = re.sub(r'&edge=curl', '', url)
                    print(f'[cover] Found via Google Books ({key})', flush=True)
                    return url
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        print(f'[cover] Google Books lookup failed: {e}', flush=True)

    # Try Open Library by title search as last resort
    try:
        query = urllib.parse.quote(f'{title} {author}')
        ol_search = f'https://openlibrary.org/search.json?q={query}&limit=1&fields=isbn'
        req = urllib.request.Request(ol_search)
        req.add_header('User-Agent', 'Petrarca/1.0')
        resp = urllib.request.urlopen(req, timeout=8)
        data = json.loads(resp.read().decode())
        docs = data.get('docs', [])
        if docs:
            isbns = docs[0].get('isbn', [])
            for found_isbn in isbns[:3]:
                ol_url = f'https://covers.openlibrary.org/b/isbn/{found_isbn}-L.jpg?default=false'
                try:
                    req2 = urllib.request.Request(ol_url, method='HEAD')
                    req2.add_header('User-Agent', 'Petrarca/1.0')
                    resp2 = urllib.request.urlopen(req2, timeout=5)
                    if resp2.status == 200 and 'image' in resp2.headers.get('Content-Type', ''):
                        print(f'[cover] Found via Open Library search → ISBN {found_isbn}', flush=True)
                        return ol_url
                except (urllib.error.HTTPError, urllib.error.URLError, OSError):
                    continue
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        print(f'[cover] Open Library search failed: {e}', flush=True)

    print(f'[cover] No cover found for "{title}" by {author}', flush=True)
    return None


def _url_returns_image(url: str) -> bool:
    """Check if a URL actually returns an image (HEAD request)."""
    import urllib.request
    import urllib.error
    try:
        req = urllib.request.Request(url, method='HEAD')
        req.add_header('User-Agent', 'Petrarca/1.0')
        resp = urllib.request.urlopen(req, timeout=5)
        return resp.status == 200 and 'image' in resp.headers.get('Content-Type', '')
    except (urllib.error.HTTPError, urllib.error.URLError, OSError):
        return False


def _find_toc_online(title: str, author: str) -> list[dict] | None:
    """Try to find a book's table of contents via Gemini + Google Search."""
    from gemini_llm import call_with_search

    result = call_with_search(
        f"""Find the table of contents / chapter list for this book:
"{title}" by {author}

Return a JSON array of chapters:
[{{"number": 1, "title": "Chapter Title"}}, {{"number": 2, "title": "Chapter Title"}}]

Only include actual chapter titles, not preface/index/bibliography.
If you cannot find the chapter list, return an empty array [].
Return ONLY the JSON array.""",
    )

    if not result:
        return None

    try:
        cleaned = result.strip()
        if cleaned.startswith('```'):
            cleaned = re.sub(r'^```(?:json)?\n?', '', cleaned)
            cleaned = re.sub(r'\n?```$', '', cleaned)
        chapters = json.loads(cleaned)
        if isinstance(chapters, list) and len(chapters) >= 2:
            print(f'[toc] Found {len(chapters)} chapters online for "{title}"', flush=True)
            return chapters
    except json.JSONDecodeError:
        pass

    return None


def process_book_ocr_toc(image_path: Path) -> dict:
    """OCR a table of contents photo and parse chapter structure."""
    from gemini_llm import call_vision

    image_data = image_path.read_bytes()
    mime_type = 'image/png' if str(image_path).endswith('.png') else 'image/jpeg'

    result = call_vision(
        image_data,
        """Extract the table of contents from this image.
Return a JSON object:
{
  "chapters": [
    {"number": 1, "title": "Chapter Title", "start_page": 1},
    {"number": 2, "title": "Chapter Title", "start_page": 25}
  ]
}
Include chapter numbers, titles, and page numbers. If sections/parts have sub-chapters, include them.
Return ONLY valid JSON.""",
        mime_type=mime_type,
        response_mime_type="application/json",
    )

    if not result:
        return {'chapters': []}

    try:
        cleaned = result.strip()
        if cleaned.startswith('```'):
            cleaned = re.sub(r'^```(?:json)?\n?', '', cleaned)
            cleaned = re.sub(r'\n?```$', '', cleaned)
        parsed = json.loads(cleaned)
        return {'chapters': parsed.get('chapters', [])}
    except json.JSONDecodeError:
        return {'chapters': []}


def process_book_ocr_page(image_path: Path, book_title: str,
                          page_number: int | None = None,
                          chapter: str | None = None) -> dict:
    """OCR a page photo, extract page number and core ideas."""
    from gemini_llm import call_vision

    image_data = image_path.read_bytes()
    mime_type = 'image/png' if str(image_path).endswith('.png') else 'image/jpeg'

    context = f"Book: {book_title}"
    if chapter:
        context += f"\nChapter: {chapter}"
    if page_number:
        context += f"\nExpected page: {page_number}"

    result = call_vision(
        image_data,
        f"""{context}

OCR this book page and extract:
1. The full text on the page
2. The page number (from header/footer if visible)
3. 1-3 core ideas or claims from this page
4. Relevant topic tags
5. The single most important sentence on this page (key passage)
6. A thought-provoking "why" question about the content

Return a JSON object:
{{
  "text": "full OCR text of the page",
  "detected_page_number": page_number_or_null,
  "extracted_ideas": ["idea 1", "idea 2"],
  "topics": ["topic1", "topic2"],
  "key_passage": "the single most important sentence on this page",
  "elaborative_question": "a why/how question about the content that would deepen understanding"
}}
Return ONLY valid JSON.""",
        mime_type=mime_type,
        response_mime_type="application/json",
        max_tokens=8192,
    )

    if not result:
        return {'text': '', 'extracted_ideas': [], 'topics': []}

    try:
        cleaned = result.strip()
        if cleaned.startswith('```'):
            cleaned = re.sub(r'^```(?:json)?\n?', '', cleaned)
            cleaned = re.sub(r'\n?```$', '', cleaned)
        parsed = json.loads(cleaned)
        return {
            'text': parsed.get('text', ''),
            'detected_page_number': parsed.get('detected_page_number'),
            'extracted_ideas': parsed.get('extracted_ideas', []),
            'topics': parsed.get('topics', []),
            'key_passage': parsed.get('key_passage'),
            'elaborative_question': parsed.get('elaborative_question'),
        }
    except json.JSONDecodeError:
        return {'text': result, 'extracted_ideas': [], 'topics': []}


class ResearchHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Petrarca-Token')

    def _read_json_body(self) -> dict | None:
        """Read and parse JSON from request body. Sends 400 on failure, returns None."""
        content_length = int(self.headers.get('Content-Length', 0))
        if not content_length:
            self._send_json_response(400, {'error': 'Empty request body'})
            return None
        try:
            return json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, ValueError) as e:
            self._send_json_response(400, {'error': f'Invalid JSON: {e}'})
            return None

    def _send_json_response(self, status: int, data: dict):
        self.send_response(status)
        self._send_cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def _handle_explore_batch(self):
        body = self._read_json_body()
        if body is None:
            return
        concepts = body.get('concepts', [])
        if not concepts:
            self._send_json_response(400, {'error': 'No concepts provided'})
            return

        request_id = f'expb_{int(time.time())}'
        print(f'[explore-batch] Received {len(concepts)} concepts', flush=True)

        thread = threading.Thread(
            target=run_explore_batch,
            args=(request_id, concepts),
            daemon=True,
        )
        thread.start()

        self.send_response(202)
        self._send_cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'id': request_id, 'status': 'processing', 'concept_count': len(concepts)}).encode())

    def _handle_ingest_email(self):
        """Accept raw email from Cloudflare Worker, process server-side."""
        if INGEST_TOKEN:
            token = self.headers.get('X-Petrarca-Token', '')
            if token != INGEST_TOKEN:
                self.send_response(401)
                self._send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Invalid or missing auth token'}).encode())
                return

        content_length = int(self.headers.get('Content-Length', 0))
        if not content_length:
            self.send_response(400)
            self._send_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Empty request body'}).encode())
            return

        raw_email = self.rfile.read(content_length).decode('utf-8', errors='replace')
        sender = self.headers.get('X-From', 'unknown')

        print(f'[ingest-email] Received {len(raw_email)} bytes from {sender}', flush=True)
        log_server_event('ingest_email', sender=sender)

        thread = threading.Thread(target=process_email, args=(raw_email,), daemon=True)
        thread.start()

        self.send_response(202)
        self._send_cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'queued', 'source': 'email'}).encode())

    def _handle_note(self):
        """Receive audio file + metadata, transcribe in background, store note."""
        import cgi
        content_type = self.headers.get('Content-Type', '')

        if 'multipart/form-data' in content_type:
            # Parse multipart form data
            environ = {
                'REQUEST_METHOD': 'POST',
                'CONTENT_TYPE': content_type,
                'CONTENT_LENGTH': self.headers.get('Content-Length', '0'),
            }
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ=environ)

            article_id = form.getvalue('article_id', '')
            topics_raw = form.getvalue('topics', '[]')
            article_title = form.getvalue('article_title', '')
            article_context = form.getvalue('article_context', '')

            try:
                topics = json.loads(topics_raw) if isinstance(topics_raw, str) else []
            except json.JSONDecodeError:
                topics = []

            # Save audio file
            note_id = f'note_{int(time.time())}_{article_id[:8]}'
            audio_path = AUDIO_DIR / f'{note_id}.m4a'

            file_item = form['audio']
            audio_path.write_bytes(file_item.file.read())
        else:
            self.send_response(400)
            self._send_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error": "Expected multipart/form-data"}')
            return

        # Spawn background transcription
        thread = threading.Thread(
            target=process_voice_note,
            args=(note_id, audio_path, article_id, topics, article_title, article_context),
            daemon=True,
        )
        thread.start()

        print(f'[note] Started {note_id} for article {article_id}', flush=True)

        self.send_response(202)
        self._send_cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'id': note_id, 'status': 'transcribing'}).encode())

    def _handle_execute_action(self):
        """Execute an action extracted from a voice note."""
        parts = self.path.split('/')
        note_id = parts[2] if len(parts) >= 4 else ''

        note_path = NOTES_DIR / f'{note_id}.json'
        if not note_path.exists():
            self._send_json_response(404, {'error': 'Note not found'})
            return

        body = self._read_json_body()
        if body is None:
            return
        action_id = body.get('action_id', '')

        try:
            note = json.loads(note_path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            self._send_json_response(500, {'error': f'Failed to read note: {e}'})
            return
        actions = note.get('actions', [])
        target_action = next((a for a in actions if a.get('id') == action_id), None)

        if not target_action:
            self._send_json_response(404, {'error': 'Action not found'})
            return

        if target_action['type'] == 'research':
            topic = target_action.get('topic', target_action.get('description', ''))
            request_id = f'topres_{int(time.time())}_{hash(topic) % 10000:04d}'
            thread = threading.Thread(
                target=run_topic_research,
                args=(request_id, topic, f'From voice note on: {note.get("article_title", "")}',
                      [note.get('article_title', '')]),
                daemon=True,
            )
            thread.start()
            target_action['status'] = 'running'
            print(f'[action] Spawned research for: {topic}', flush=True)
        else:
            target_action['status'] = 'done'

        note_path.write_text(json.dumps(note, indent=2))

        self.send_response(200)
        self._send_cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'action_id': action_id, 'status': target_action['status']}).encode())

    def _handle_topic_research(self):
        body = self._read_json_body()
        if body is None:
            return
        topic = body.get('topic', '').strip()
        context = body.get('context', '')
        article_titles = body.get('article_titles', [])

        if not topic:
            self._send_json_response(400, {'error': 'Missing topic'})
            return

        request_id = f'topres_{int(time.time())}_{hash(topic) % 10000:04d}'

        thread = threading.Thread(
            target=run_topic_research,
            args=(request_id, topic, context, article_titles),
            daemon=True,
        )
        thread.start()

        print(f'[topic_research] Started {request_id}: {topic}', flush=True)

        self.send_response(202)
        self._send_cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'id': request_id, 'status': 'processing'}).encode())

    def _handle_generate_questions(self):
        body = self._read_json_body()
        if body is None:
            return
        article_id = body.get('article_id', '').strip()
        existing_questions = body.get('existing_questions', [])

        if not article_id:
            self._send_json_response(400, {'error': 'Missing article_id'})
            return

        print(f'[generate-questions] Generating for article {article_id}, {len(existing_questions)} existing', flush=True)
        questions = generate_more_questions(article_id, existing_questions)
        print(f'[generate-questions] Generated {len(questions)} new questions', flush=True)

        self._send_json_response(200, {'questions': questions})

    def _handle_chat(self):
        body = self._read_json_body()
        if body is None:
            return
        question = body.get('question', '').strip()
        context = body.get('context', '')
        conversation_id = body.get('conversation_id')

        if not question:
            self._send_json_response(400, {'error': 'Missing question'})
            return

        print(f'[chat] Q: {question[:80]}...', flush=True)
        result = handle_chat(question, context, conversation_id)
        print(f'[chat] A: {result["answer"][:80]}...', flush=True)

        self.send_response(200)
        self._send_cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def _handle_ingest(self):
        body = self._read_json_body()
        if body is None:
            return

        source = body.get('source', 'unknown')

        # App-originated ingests (reader links) skip auth; external sources need a token
        if INGEST_TOKEN and source not in ('reader_link',):
            token = self.headers.get('X-Petrarca-Token', '')
            if token != INGEST_TOKEN:
                self._send_json_response(401, {'error': 'Invalid or missing auth token'})
                return

        url = body.get('url', '').strip()
        if not url:
            self._send_json_response(400, {'error': 'Missing required field: url'})
            return

        title = body.get('title', '')
        content = body.get('content', '')
        selected_text = body.get('selected_text', '')
        comment = body.get('comment', '')

        # Generate IDs before spawning thread so we can return them
        ingest_id = f'ingest_{int(time.time())}_{hash(url) % 10000:04d}'
        article_id = hashlib.sha256(url.encode()).hexdigest()[:12]

        # Route tweet URLs through twikit for full metadata + thread reconstruction
        if _is_tweet_url(url):
            thread = threading.Thread(
                target=run_ingest_tweet,
                args=(url, comment, ingest_id),
                daemon=True,
            )
            thread.start()
            print(f'[ingest] Tweet detected, fetching via twikit: {url[:80]} (id={ingest_id})')
        else:
            thread = threading.Thread(
                target=run_ingest,
                args=(url, title, content, selected_text, comment, source, ingest_id),
                daemon=True,
            )
            thread.start()
            print(f'[ingest] Queued: {url[:80]} (source={source}, id={ingest_id})')

        log_server_event('ingest_queued',
                         url=url[:200],
                         title=(title or url)[:100],
                         ingest_source=source,
                         article_id=article_id)

        self._send_json_response(202, {
            'status': 'queued',
            'url': url,
            'ingest_id': ingest_id,
            'article_id': article_id,
        })

    def _handle_ingest_youtube(self):
        """POST /ingest-youtube — save YouTube video, fetch transcript, process as article."""
        body = self._read_json_body()
        if body is None:
            return
        video_id = body.get('video_id', '')
        if not video_id:
            self._send_json_response(400, {'error': 'Missing video_id'})
            return
        title = body.get('title', '')
        channel = body.get('channel', '')
        url = body.get('url', f'https://www.youtube.com/watch?v={video_id}')
        duration = body.get('duration', 0)
        description = body.get('description', '')
        keywords = body.get('keywords', [])
        chapters = body.get('chapters', [])

        # Save to media log
        media_log_path = Path(os.environ.get('MEDIA_LOG_PATH', '/opt/petrarca/data/media_log.json'))
        try:
            media_log = json.loads(media_log_path.read_text()) if media_log_path.exists() else {'items': []}
        except json.JSONDecodeError:
            media_log = {'items': []}
        existing_ids = {item['id'] for item in media_log['items']}
        article_id = f'yt_{video_id}'
        if article_id not in existing_ids:
            media_log['items'].append({
                'id': article_id, 'type': 'youtube', 'title': title,
                'source': channel, 'url': url,
                'date_consumed': datetime.now(timezone.utc).isoformat(),
                'duration': duration, 'description': description[:500],
                'keywords': keywords, 'chapters': chapters,
                'transcript_status': 'pending', 'claims_extracted': False,
            })
            media_log_path.write_text(json.dumps(media_log, indent=2, ensure_ascii=False))

        thread = threading.Thread(
            target=_process_youtube_video,
            args=(video_id, title, channel, url, description, chapters),
            daemon=True,
        )
        thread.start()
        print(f'[ingest-youtube] Queued: "{title}" by {channel} ({video_id})', flush=True)
        log_server_event('ingest_youtube', video_id=video_id, title=title[:100], channel=channel)
        self._send_json_response(202, {'status': 'queued', 'video_id': video_id})

    def _handle_ingest_note(self):
        """Add a note/comment to an already-ingested article (sidecar file)."""
        if INGEST_TOKEN:
            token = self.headers.get('X-Petrarca-Token', '')
            if token != INGEST_TOKEN:
                self._send_json_response(401, {'error': 'Invalid or missing auth token'})
                return

        body = self._read_json_body()
        if body is None:
            return

        url = body.get('url', '').strip()
        comment = body.get('comment', '').strip()
        if not url or not comment:
            self._send_json_response(400, {'error': 'Missing url or comment'})
            return

        sidecar = {
            'url': url,
            'title': body.get('title', ''),
            'source': body.get('source', 'clipper'),
            'created_at': int(time.time() * 1000),
            'notes': [{'text': comment, 'source': body.get('source', 'clipper')}],
        }
        sidecar_id = f'note_{int(time.time())}_{hash(url) % 10000:04d}'
        sidecar_path = INGEST_DIR / f'{sidecar_id}_sidecar.json'
        sidecar_path.write_text(json.dumps(sidecar, indent=2))
        print(f'[ingest-note] Saved note for {url[:60]}', flush=True)
        self._send_json_response(200, {'status': 'ok', 'sidecar_id': sidecar_id})

    def _handle_ingest_cancel(self):
        """Remove a recently-ingested article by URL (best-effort)."""
        if INGEST_TOKEN:
            token = self.headers.get('X-Petrarca-Token', '')
            if token != INGEST_TOKEN:
                self._send_json_response(401, {'error': 'Invalid or missing auth token'})
                return

        body = self._read_json_body()
        if body is None:
            return

        url = body.get('url', '').strip()
        if not url:
            self._send_json_response(400, {'error': 'Missing url'})
            return

        article_id = hashlib.sha256(url.encode()).hexdigest()[:12]
        removed = False

        try:
            articles = json.loads(ARTICLES_PATH.read_text())
            before = len(articles)
            articles = [a for a in articles if a.get('id') != article_id]
            if len(articles) < before:
                ARTICLES_PATH.write_text(json.dumps(articles, indent=2))
                removed = True
                print(f'[ingest-cancel] Removed {article_id} ({url[:60]})', flush=True)
            else:
                print(f'[ingest-cancel] Article {article_id} not found (may still be processing)', flush=True)
        except (json.JSONDecodeError, OSError) as e:
            print(f'[ingest-cancel] Error: {e}', flush=True)

        self._send_json_response(200, {
            'status': 'removed' if removed else 'not_found',
            'article_id': article_id,
        })

    def _handle_report_scrape(self):
        body = self._read_json_body()
        if body is None:
            return

        article_id = body.get('article_id', '')
        url = body.get('url', '')
        title = body.get('title', '')
        if not article_id:
            self._send_json_response(400, {'error': 'Missing article_id'})
            return

        try:
            reports = json.loads(SCRAPE_REPORTS_PATH.read_text()) if SCRAPE_REPORTS_PATH.exists() else []
        except (json.JSONDecodeError, OSError):
            reports = []

        # Skip if already reported
        if any(r['article_id'] == article_id for r in reports):
            self._send_json_response(200, {'status': 'already_reported'})
            return

        reports.append({
            'article_id': article_id,
            'url': url,
            'title': title,
            'reported_at': datetime.now(timezone.utc).isoformat(),
            'status': 'pending',
        })
        SCRAPE_REPORTS_PATH.write_text(json.dumps(reports, indent=2))
        print(f'[scrape-report] Reported {article_id}: {title[:60]}', flush=True)
        self._send_json_response(200, {'status': 'reported'})

    def _handle_feedback(self):
        """Receive feedback with optional screenshot, audio, text, and context."""
        import cgi
        content_type = self.headers.get('Content-Type', '')

        if 'multipart/form-data' not in content_type:
            self._send_json_response(400, {'error': 'Expected multipart/form-data'})
            return

        environ = {
            'REQUEST_METHOD': 'POST',
            'CONTENT_TYPE': content_type,
            'CONTENT_LENGTH': self.headers.get('Content-Length', '0'),
        }
        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ=environ)

        context_raw = form.getvalue('context', '')
        if not context_raw:
            self._send_json_response(400, {'error': 'Missing required field: context'})
            return

        try:
            context = json.loads(context_raw) if isinstance(context_raw, str) else context_raw
        except json.JSONDecodeError:
            self._send_json_response(400, {'error': 'Invalid JSON in context field'})
            return

        text = form.getvalue('text', '')
        ts = datetime.now(timezone.utc)
        feedback_id = f'feedback_{ts.strftime("%Y%m%d_%H%M%S")}'

        saved_files = {}

        # Save screenshot if present
        if 'screenshot' in form and form['screenshot'].file:
            screenshot_path = FEEDBACK_DIR / f'{feedback_id}_screenshot.png'
            data = form['screenshot'].file.read()
            screenshot_path.write_bytes(data if isinstance(data, bytes) else data.encode('latin-1'))
            saved_files['screenshot'] = screenshot_path.name
            print(f'[feedback] Saved screenshot: {screenshot_path.name}', flush=True)

        # Save audio if present
        audio_path = None
        if 'audio' in form and form['audio'].file:
            audio_path = FEEDBACK_DIR / f'{feedback_id}_audio.m4a'
            data = form['audio'].file.read()
            audio_path.write_bytes(data if isinstance(data, bytes) else data.encode('latin-1'))
            saved_files['audio'] = audio_path.name
            print(f'[feedback] Saved audio: {audio_path.name}', flush=True)

        # Build metadata
        metadata = {
            'id': feedback_id,
            'timestamp': ts.isoformat(),
            'context': context,
            'text': text if isinstance(text, str) else '',
            'files': saved_files,
        }

        # Transcribe audio in background if present
        if audio_path:
            def _transcribe_and_update():
                try:
                    transcript = transcribe_on_server(audio_path)
                    metadata['transcript'] = transcript
                    print(f'[feedback] {feedback_id} transcribed: {transcript[:80]}...', flush=True)
                except Exception as e:
                    metadata['transcript_error'] = str(e)
                    print(f'[feedback] {feedback_id} transcription failed: {e}', flush=True)
                finally:
                    meta_path = FEEDBACK_DIR / f'{feedback_id}.json'
                    meta_path.write_text(json.dumps(metadata, indent=2))

            thread = threading.Thread(target=_transcribe_and_update, daemon=True)
            thread.start()
        else:
            # No audio — save metadata immediately
            meta_path = FEEDBACK_DIR / f'{feedback_id}.json'
            meta_path.write_text(json.dumps(metadata, indent=2))

        print(f'[feedback] Received {feedback_id} (text={bool(text)}, audio={bool(audio_path)}, screenshot={"screenshot" in saved_files})', flush=True)
        log_server_event('feedback_received', feedback_id=feedback_id)

        self._send_json_response(200, {'status': 'saved', 'id': feedback_id})

    # --- Physical book handlers ---

    def _parse_multipart_form(self):
        """Parse multipart form data, returning (form, error_response_sent)."""
        import cgi
        content_type = self.headers.get('Content-Type', '')
        if 'multipart/form-data' not in content_type:
            self._send_json_response(400, {'error': 'Expected multipart/form-data'})
            return None, True
        environ = {
            'REQUEST_METHOD': 'POST',
            'CONTENT_TYPE': content_type,
            'CONTENT_LENGTH': self.headers.get('Content-Length', '0'),
        }
        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ=environ)
        return form, False

    def _save_upload_photo(self, form, field_name: str, prefix: str) -> Path | None:
        """Save an uploaded photo from multipart form to BOOK_UPLOADS_DIR."""
        if field_name not in form or not form[field_name].file:
            return None
        ext = 'jpg'
        if form[field_name].filename and form[field_name].filename.endswith('.png'):
            ext = 'png'
        photo_path = BOOK_UPLOADS_DIR / f'{prefix}_{int(time.time())}.{ext}'
        data = form[field_name].file.read()
        photo_path.write_bytes(data if isinstance(data, bytes) else data.encode('latin-1'))
        return photo_path

    def _handle_book_identify(self):
        """Identify a book from a cover/title page photo."""
        form, err = self._parse_multipart_form()
        if err:
            return

        photo_path = self._save_upload_photo(form, 'photo', 'cover')
        if not photo_path:
            self._send_json_response(400, {'error': 'Missing photo field'})
            return

        print(f'[book/identify] Received cover photo: {photo_path.name}', flush=True)

        try:
            result = process_book_identify(photo_path)
            if 'error' in result:
                self._send_json_response(422, result)
            else:
                self._send_json_response(200, result)
        except Exception as e:
            print(f'[book/identify] Error: {e}', flush=True)
            self._send_json_response(500, {'error': str(e)})

    def _handle_book_ocr_toc(self):
        """OCR a table of contents photo."""
        form, err = self._parse_multipart_form()
        if err:
            return

        photo_path = self._save_upload_photo(form, 'photo', 'toc')
        if not photo_path:
            self._send_json_response(400, {'error': 'Missing photo field'})
            return

        book_id = form.getvalue('book_id', '')
        print(f'[book/ocr-toc] Received TOC photo for book {book_id}: {photo_path.name}', flush=True)

        try:
            result = process_book_ocr_toc(photo_path)
            self._send_json_response(200, result)
        except Exception as e:
            print(f'[book/ocr-toc] Error: {e}', flush=True)
            self._send_json_response(500, {'error': str(e)})

    def _handle_book_ocr_page(self):
        """OCR a book page photo and extract core ideas."""
        form, err = self._parse_multipart_form()
        if err:
            return

        photo_path = self._save_upload_photo(form, 'photo', 'page')
        if not photo_path:
            self._send_json_response(400, {'error': 'Missing photo field'})
            return

        book_id = form.getvalue('book_id', '')
        book_title = form.getvalue('book_title', '')
        page_str = form.getvalue('page_number', '')
        chapter = form.getvalue('chapter', '')
        page_number = int(page_str) if page_str and page_str.isdigit() else None

        print(f'[book/ocr-page] Received page photo for {book_title}: {photo_path.name}', flush=True)

        try:
            result = process_book_ocr_page(photo_path, book_title, page_number, chapter)
            self._send_json_response(200, result)
        except Exception as e:
            print(f'[book/ocr-page] Error: {e}', flush=True)
            self._send_json_response(500, {'error': str(e)})

    def _handle_book_voice_note(self):
        """Receive a voice note about a physical book, transcribe and extract ideas."""
        form, err = self._parse_multipart_form()
        if err:
            return

        if 'audio' not in form or not form['audio'].file:
            self._send_json_response(400, {'error': 'Missing audio field'})
            return

        book_id = form.getvalue('book_id', '')
        book_title = form.getvalue('book_title', '')
        chapter = form.getvalue('chapter', '')
        page_str = form.getvalue('page_number', '')
        page_number = int(page_str) if page_str and page_str.isdigit() else None

        note_id = f'bnote_{int(time.time())}_{book_id[:8]}'
        audio_path = AUDIO_DIR / f'{note_id}.m4a'
        data = form['audio'].file.read()
        audio_path.write_bytes(data if isinstance(data, bytes) else data.encode('latin-1'))

        print(f'[book/voice-note] Received note {note_id} for {book_title}', flush=True)

        def _process_book_note():
            from gemini_llm import call_llm
            result = {'id': note_id, 'transcript': '', 'extracted_ideas': [], 'topics': []}
            try:
                transcript = transcribe_on_server(audio_path)
                result['transcript'] = transcript

                # Extract ideas from transcript
                extraction = call_llm(
                    f"""Extract key ideas from this voice note about the book "{book_title}".
{f'Chapter: {chapter}' if chapter else ''}
{f'Page: {page_number}' if page_number else ''}

Transcript: {transcript}

Return a JSON object:
{{"extracted_ideas": ["idea 1", "idea 2"], "topics": ["topic1", "topic2"]}}
Return ONLY valid JSON.""",
                    response_mime_type="application/json",
                )
                if extraction:
                    try:
                        cleaned = extraction.strip()
                        if cleaned.startswith('```'):
                            cleaned = re.sub(r'^```(?:json)?\n?', '', cleaned)
                            cleaned = re.sub(r'\n?```$', '', cleaned)
                        parsed = json.loads(cleaned)
                        result['extracted_ideas'] = parsed.get('extracted_ideas', [])
                        result['topics'] = parsed.get('topics', [])
                    except json.JSONDecodeError:
                        pass

                print(f'[book/voice-note] {note_id} processed: {len(result["extracted_ideas"])} ideas', flush=True)
            except Exception as e:
                print(f'[book/voice-note] {note_id} error: {e}', flush=True)

            # Save note result
            note_path = NOTES_DIR / f'{note_id}.json'
            note_path.write_text(json.dumps({
                **result,
                'book_id': book_id,
                'book_title': book_title,
                'chapter': chapter,
                'page_number': page_number,
                'audio_path': str(audio_path),
                'created_at': int(time.time() * 1000),
            }, indent=2))

        # Process in background
        thread = threading.Thread(target=_process_book_note, daemon=True)
        thread.start()

        self._send_json_response(202, {'id': note_id, 'status': 'processing'})

    def _handle_book_research(self):
        """Trigger background research for a physical book."""
        content_length = int(self.headers.get('Content-Length', 0))
        if not content_length:
            self._send_json_response(400, {'error': 'Missing request body'})
            return

        try:
            body = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, ValueError):
            self._send_json_response(400, {'error': 'Invalid JSON'})
            return

        book_id = body.get('book_id', '')
        title = body.get('title', '')
        author = body.get('author', '')
        if not title:
            self._send_json_response(400, {'error': 'Missing title'})
            return

        isbn = body.get('isbn')
        chapters = body.get('chapters', [])
        topics = body.get('topics', [])

        print(f'[book/research] Starting research for "{title}" by {author}', flush=True)

        def _do_research():
            try:
                from book_research_agent import research_book
                research_book(book_id, title, author, isbn, chapters, topics)
            except Exception as e:
                print(f'[book/research] Error: {e}', flush=True)

        thread = threading.Thread(target=_do_research, daemon=True)
        thread.start()

        self._send_json_response(202, {'status': 'researching', 'book_id': book_id})

    def _handle_book_chapter_insights(self):
        """Get research and connections for a specific chapter."""
        content_length = int(self.headers.get('Content-Length', 0))
        if not content_length:
            self._send_json_response(400, {'error': 'Missing request body'})
            return

        try:
            body = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, ValueError):
            self._send_json_response(400, {'error': 'Invalid JSON'})
            return

        book_id = body.get('book_id', '')
        chapter_number = body.get('chapter_number', 1)
        chapter_title = body.get('chapter_title', '')
        captures = body.get('captures', [])

        print(f'[book/chapter-insights] Ch {chapter_number} of {book_id}', flush=True)

        try:
            from book_research_agent import get_chapter_insights
            result = get_chapter_insights(book_id, chapter_number, chapter_title, captures)
            self._send_json_response(200, result)
        except Exception as e:
            print(f'[book/chapter-insights] Error: {e}', flush=True)
            self._send_json_response(500, {'error': str(e)})

    def _handle_book_story_so_far(self):
        """Generate a 'Story So Far' briefing for returning to a book."""
        content_length = int(self.headers.get('Content-Length', 0))
        if not content_length:
            self._send_json_response(400, {'error': 'Missing request body'})
            return

        try:
            body = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, ValueError):
            self._send_json_response(400, {'error': 'Invalid JSON'})
            return

        book_id = body.get('book_id', '')
        title = body.get('title', '')
        author = body.get('author', '')
        current_chapter = body.get('current_chapter')
        current_page = body.get('current_page')
        page_count = body.get('page_count')
        captures = body.get('captures', [])

        print(f'[book/story-so-far] Generating briefing for "{title}"', flush=True)

        try:
            from book_research_agent import generate_story_so_far
            result = generate_story_so_far(
                book_id, title, author,
                current_chapter, current_page, page_count,
                captures,
            )
            self._send_json_response(200, result)
        except Exception as e:
            print(f'[book/story-so-far] Error: {e}', flush=True)
            self._send_json_response(500, {'error': str(e)})

    def _handle_book_research_get(self):
        """GET /book/research/{book_id} — retrieve cached research."""
        book_id = self.path.split('/')[-1]
        from book_research_agent import load_book_research
        research = load_book_research(book_id)
        if research:
            self._send_json_response(200, research)
        else:
            self._send_json_response(404, {'error': 'No research found for this book'})

    # -----------------------------------------------------------------------
    # Kindle library sync
    # -----------------------------------------------------------------------

    def _handle_kindle_sync(self):
        """POST /kindle/sync — receive Kindle library/notebook data from Chrome extension.

        Data model (kindle_library.json):
        {
            "books": {
                "<asin>": {
                    "asin": "B00...",
                    "title": "...",
                    "author": "...",
                    "cover_url": "...",
                    "progress": { "text": "42%", "position": ..., "location": ... },
                    "first_seen": "2026-03-15T...",
                    "last_seen": "2026-03-15T...",
                    "status": "unreviewed",  # unreviewed | reading | read | skipped
                    "category": null,        # non-fiction | classical-literature | literary-fiction | genre-fiction | language-learning | reference
                    "added_to_petrarca": false
                }
            },
            "sync_count": 42,
            "last_sync": "2026-03-15T..."
        }
        """
        body = self._read_json_body()
        if body is None:
            return

        data_type = body.get('data_type', 'library')
        now = datetime.now(timezone.utc).isoformat()

        # Log every sync event
        log_entry = json.dumps({
            'ts': now,
            'data_type': data_type,
            'source': body.get('source', 'unknown'),
            'url': body.get('url', ''),
            'book_count': len(body.get('books', [])),
        })
        with open(KINDLE_SYNC_LOG_PATH, 'a') as f:
            f.write(log_entry + '\n')

        if data_type == 'notebook':
            return self._handle_kindle_notebook_sync(body, now)

        # Library sync — merge books into existing data
        existing = {'books': {}, 'sync_count': 0, 'last_sync': None}
        if KINDLE_DATA_PATH.exists():
            try:
                existing = json.loads(KINDLE_DATA_PATH.read_text())
            except json.JSONDecodeError:
                pass

        books_dict = existing.get('books', {})
        new_count = 0
        updated_count = 0

        incoming_books = body.get('books', [])
        for book in incoming_books:
            asin = book.get('asin', '')
            title = book.get('title', '')
            book_id = book.get('book_id', '')
            if not asin and not title and not book_id:
                continue

            # Use ASIN as key, then book_id, then title
            key = asin if asin else (book_id if book_id else f'title:{title[:80]}')

            if key in books_dict:
                # Update existing — keep our curation fields, update progress
                entry = books_dict[key]
                entry['last_seen'] = now
                # Update progress from Chrome extension (text-based)
                if book.get('progress_text'):
                    entry.setdefault('progress', {})
                    entry['progress']['text'] = book['progress_text']
                    entry['progress']['updated'] = now
                # Update progress from Mac app (numeric)
                if book.get('progress_pct') is not None:
                    entry.setdefault('progress', {})
                    entry['progress']['pct'] = book['progress_pct']
                    entry['progress']['current_position'] = book.get('current_position', 0)
                    entry['progress']['max_position'] = book.get('max_position', 0)
                    entry['progress']['updated'] = now
                if book.get('cover_url') and not entry.get('cover_url'):
                    entry['cover_url'] = book['cover_url']
                if book.get('author') and not entry.get('author'):
                    entry['author'] = book['author']
                if book.get('last_read'):
                    entry['last_read'] = book['last_read']
                if book.get('status') and book['status'] != 'unread':
                    entry['status'] = book['status']
                if book.get('finished_date') and not entry.get('finished_date'):
                    entry['finished_date'] = book['finished_date']
                if book.get('purchase_date') and not entry.get('purchase_date'):
                    entry['purchase_date'] = book['purchase_date']
                if book.get('publisher') and not entry.get('publisher'):
                    entry['publisher'] = book['publisher']
                updated_count += 1
            else:
                # New book
                progress = {}
                if book.get('progress_text'):
                    progress['text'] = book['progress_text']
                if book.get('progress_pct') is not None:
                    progress['pct'] = book['progress_pct']
                    progress['current_position'] = book.get('current_position', 0)
                    progress['max_position'] = book.get('max_position', 0)
                progress['updated'] = now

                books_dict[key] = {
                    'asin': asin,
                    'book_id': book_id,
                    'title': title,
                    'author': book.get('author', ''),
                    'cover_url': book.get('cover_url', ''),
                    'progress': progress,
                    'first_seen': now,
                    'last_seen': now,
                    'status': book.get('status', 'unreviewed'),
                    'finished_date': book.get('finished_date'),
                    'last_read': book.get('last_read'),
                    'purchase_date': book.get('purchase_date', ''),
                    'language': book.get('language', ''),
                    'publisher': book.get('publisher', ''),
                    'is_sideloaded': book.get('is_sideloaded', False),
                    'category': None,
                    'added_to_petrarca': False,
                    'epub_path': None,
                }
                new_count += 1

        result = {
            'books': books_dict,
            'sync_count': existing.get('sync_count', 0) + 1,
            'last_sync': now,
        }
        KINDLE_DATA_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False))

        print(f'[kindle/sync] Library: {new_count} new, {updated_count} updated, {len(books_dict)} total', flush=True)
        self._send_json_response(200, {
            'status': 'ok',
            'new_books': new_count,
            'updated_books': updated_count,
            'total_books': len(books_dict),
        })

    def _handle_kindle_notebook_sync(self, body, now):
        """Handle notebook (highlights/notes) data."""
        existing = {'books': {}, 'last_sync': None}
        if KINDLE_HIGHLIGHTS_PATH.exists():
            try:
                existing = json.loads(KINDLE_HIGHLIGHTS_PATH.read_text())
            except json.JSONDecodeError:
                pass

        books_dict = existing.get('books', {})
        total_highlights = 0
        total_notes = 0

        for book in body.get('books', []):
            asin = book.get('asin', '')
            title = book.get('title', '')
            key = asin if asin else f'title:{title[:80]}'

            if not key:
                continue

            highlights = book.get('highlights', [])
            notes = book.get('notes', [])
            total_highlights += len(highlights)
            total_notes += len(notes)

            if key in books_dict:
                entry = books_dict[key]
                # Merge highlights (deduplicate by text)
                existing_texts = {h['text'] for h in entry.get('highlights', [])}
                for h in highlights:
                    if h.get('text') and h['text'] not in existing_texts:
                        entry.setdefault('highlights', []).append({**h, 'synced_at': now})
                        existing_texts.add(h['text'])
                # Merge notes
                existing_note_texts = {n['text'] for n in entry.get('notes', [])}
                for n in notes:
                    if n.get('text') and n['text'] not in existing_note_texts:
                        entry.setdefault('notes', []).append({**n, 'synced_at': now})
                        existing_note_texts.add(n['text'])
                entry['last_sync'] = now
            else:
                books_dict[key] = {
                    'asin': asin,
                    'title': title,
                    'author': book.get('author', ''),
                    'cover_url': book.get('cover_url', ''),
                    'highlights': [{**h, 'synced_at': now} for h in highlights],
                    'notes': [{**n, 'synced_at': now} for n in notes],
                    'first_sync': now,
                    'last_sync': now,
                }

        result = {
            'books': books_dict,
            'last_sync': now,
        }
        KINDLE_HIGHLIGHTS_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False))

        print(f'[kindle/sync] Notebook: {total_highlights} highlights, {total_notes} notes across {len(body.get("books", []))} books', flush=True)
        self._send_json_response(200, {
            'status': 'ok',
            'highlights': total_highlights,
            'notes': total_notes,
        })

    def _handle_kindle_library_get(self):
        """GET /kindle/library — return Kindle library with curation status.

        Query params:
            exclude_processed=true — omit books with added_to_petrarca=true (server-side filter)
        """
        if not KINDLE_DATA_PATH.exists():
            self._send_json_response(200, {'books': {}, 'sync_count': 0})
            return
        try:
            data = json.loads(KINDLE_DATA_PATH.read_text())
        except json.JSONDecodeError:
            self._send_json_response(200, {'books': {}, 'sync_count': 0})
            return

        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        exclude_processed = params.get('exclude_processed', [''])[0] == 'true'

        books = data.get('books', {})
        if exclude_processed:
            books = {k: v for k, v in books.items() if not v.get('added_to_petrarca')}

        # Use title_resolved as display title where available
        for book in books.values():
            resolved = book.get('title_resolved')
            if resolved and resolved != book.get('title'):
                book['title_display'] = resolved

        self._send_json_response(200, {'books': books, 'sync_count': data.get('sync_count', 0)})

    def _handle_kindle_highlights_get(self):
        """GET /kindle/highlights or /kindle/highlights?asin=X — return highlights."""
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        asin_filter = params.get('asin', [None])[0]

        if not KINDLE_HIGHLIGHTS_PATH.exists():
            self._send_json_response(200, {'books': {}})
            return
        try:
            data = json.loads(KINDLE_HIGHLIGHTS_PATH.read_text())
            if asin_filter:
                book = data.get('books', {}).get(asin_filter, {})
                self._send_json_response(200, {'book': book})
            else:
                self._send_json_response(200, data)
        except json.JSONDecodeError:
            self._send_json_response(200, {'books': {}})

    def _handle_kindle_curate(self):
        """POST /kindle/curate — update curation fields for Kindle books.

        Body: { "updates": [ { "key": "<asin or title:...>", "status": "read", "category": "non-fiction", "added_to_petrarca": true } ] }
        """
        body = self._read_json_body()
        if body is None:
            return

        if not KINDLE_DATA_PATH.exists():
            self._send_json_response(404, {'error': 'No Kindle library data yet'})
            return

        try:
            data = json.loads(KINDLE_DATA_PATH.read_text())
        except json.JSONDecodeError:
            self._send_json_response(500, {'error': 'Corrupt Kindle data'})
            return

        books_dict = data.get('books', {})
        updates = body.get('updates', [])
        updated = 0

        for update in updates:
            key = update.get('key', '')
            if key not in books_dict:
                continue

            entry = books_dict[key]
            if 'status' in update:
                entry['status'] = update['status']
            if 'category' in update:
                entry['category'] = update['category']
            if 'added_to_petrarca' in update:
                entry['added_to_petrarca'] = update['added_to_petrarca']
            if 'epub_path' in update:
                entry['epub_path'] = update['epub_path']
            if 'title_resolved' in update:
                entry['title_resolved'] = update['title_resolved']
            if 'finished_date' in update:
                entry['finished_date'] = update['finished_date']
            updated += 1

        data['books'] = books_dict
        KINDLE_DATA_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))

        print(f'[kindle/curate] Updated {updated} books', flush=True)
        self._send_json_response(200, {'status': 'ok', 'updated': updated})

    def _handle_kindle_include(self):
        """POST /kindle/include — include a specific Kindle book in the Library.

        Body: { "key": "<asin or book_id>" }

        Creates a unified PhysicalBook record immediately, converts highlights
        to captures, marks added_to_petrarca in kindle_library.json, and starts
        book research in a background thread.

        Returns the unified book record so client can add it instantly.
        """
        body = self._read_json_body()
        if body is None:
            return

        key = body.get('key', '').strip()
        if not key:
            self._send_json_response(400, {'error': 'Missing required field: key'})
            return

        # Load Kindle library
        if not KINDLE_DATA_PATH.exists():
            self._send_json_response(404, {'error': 'No Kindle library data'})
            return

        try:
            kindle_data = json.loads(KINDLE_DATA_PATH.read_text())
        except json.JSONDecodeError:
            self._send_json_response(500, {'error': 'Corrupt Kindle data'})
            return

        kindle_book = kindle_data.get('books', {}).get(key)
        if not kindle_book:
            self._send_json_response(404, {'error': f'Book key not found: {key}'})
            return

        # Import processing functions from process_kindle_books
        from process_kindle_books import (
            kindle_to_unified_book, highlights_to_captures,
            load_kindle_highlights, load_physical_books, save_physical_books,
            is_already_unified,
        )

        physical_data = load_physical_books()

        if is_already_unified(key, physical_data):
            # Already included — find and return the existing record
            for b in physical_data.get('books', []):
                if b.get('kindle_asin') == key or b.get('kindle_book_id') == key or b.get('id') == f'kindle_{key}':
                    self._send_json_response(200, {'book': b, 'captures': [], 'already_existed': True})
                    return
            self._send_json_response(200, {'book': None, 'already_existed': True})
            return

        # Create unified record
        unified = kindle_to_unified_book(key, kindle_book)
        physical_data['books'].append(unified)

        # Convert highlights
        highlights_data = load_kindle_highlights()
        captures = highlights_to_captures(key, unified['id'], highlights_data)
        if captures:
            physical_data['captures'].extend(captures)

        # Save immediately so the book appears in Library
        save_physical_books(physical_data)

        # Mark as added in kindle_library.json
        kindle_data['books'][key]['added_to_petrarca'] = True
        kindle_data['books'][key]['status'] = 'read'
        KINDLE_DATA_PATH.write_text(json.dumps(kindle_data, indent=2, ensure_ascii=False))

        title = unified['title']
        print(f'[kindle/include] Included: {title} ({len(captures)} highlights)', flush=True)

        # Start research in background
        def _research():
            try:
                from process_kindle_books import research_book_if_needed
                topics = unified.get('topics', [])
                if not topics:
                    cat = kindle_book.get('category', '')
                    if cat:
                        topics = [cat]
                research_book_if_needed(
                    unified['id'], title, unified['author'],
                    unified.get('chapters', []), topics,
                )
                print(f'[kindle/include] Research done: {title}', flush=True)
            except Exception as e:
                print(f'[kindle/include] Research error for {title}: {e}', flush=True)
                import traceback; traceback.print_exc()

        thread = threading.Thread(target=_research, daemon=True)
        thread.start()

        self._send_json_response(200, {
            'book': unified,
            'captures': captures,
            'already_existed': False,
        })

    def _handle_kindle_classify(self):
        """POST /kindle/classify — use LLM to classify unreviewed books by category.

        Sends book titles/authors to Gemini and classifies each as:
        non-fiction, historical-novel, novel, or other.
        Then auto-updates the category field in kindle_library.json.
        """
        if not KINDLE_DATA_PATH.exists():
            self._send_json_response(404, {'error': 'No Kindle library data yet'})
            return

        try:
            data = json.loads(KINDLE_DATA_PATH.read_text())
        except json.JSONDecodeError:
            self._send_json_response(500, {'error': 'Corrupt Kindle data'})
            return

        books_dict = data.get('books', {})

        # Find books that haven't been classified yet
        unclassified = []
        for key, book in books_dict.items():
            if book.get('category') is None:
                unclassified.append({
                    'key': key,
                    'title': book.get('title', ''),
                    'author': book.get('author', ''),
                })

        if not unclassified:
            self._send_json_response(200, {'status': 'ok', 'message': 'All books already classified', 'classified': 0})
            return

        # Classify in batches of 50
        from gemini_llm import call_llm
        classified_count = 0

        for i in range(0, len(unclassified), 50):
            batch = unclassified[i:i+50]
            book_list = '\n'.join(
                f'{j+1}. "{b["title"]}" by {b["author"] or "unknown"}'
                for j, b in enumerate(batch)
            )

            prompt = f"""Classify each of these books into exactly one category. Return ONLY a JSON array of objects with "index" (1-based) and "category" fields.

Categories (classify each book into EXACTLY ONE):
- "non-fiction" — history, science, philosophy, biography, essays, politics, technical, academic, etc.
- "classical-literature" — ancient/medieval/early-modern literature: Greek, Latin, Shakespeare, Dante, Cervantes, Goethe, etc. Also poetry collections from any era.
- "literary-fiction" — modern literary fiction, historical novels, and serious/ambitious fiction: Fowles, Eco, Marquez, Ibsen, Camus, etc.
- "genre-fiction" — crime, thriller, spy, romance, military fiction, sci-fi, fantasy — popular/commercial fiction
- "language-learning" — language textbooks, readers, bilingual editions, grammars, dictionaries
- "reference" — dictionaries, encyclopedias, collected works, anthologies, textbooks

Books:
{book_list}

Return JSON array only, no markdown fences:"""

            try:
                result = call_llm(prompt)
                # Parse the JSON response
                result_text = result.strip()
                if result_text.startswith('```'):
                    result_text = result_text.split('\n', 1)[1].rsplit('```', 1)[0].strip()
                classifications = json.loads(result_text)

                for item in classifications:
                    idx = item.get('index', 0) - 1
                    category = item.get('category', '')
                    if 0 <= idx < len(batch) and category in ('non-fiction', 'classical-literature', 'literary-fiction', 'genre-fiction', 'language-learning', 'reference'):
                        key = batch[idx]['key']
                        books_dict[key]['category'] = category
                        classified_count += 1

            except (json.JSONDecodeError, Exception) as e:
                print(f'[kindle/classify] Batch {i//50} error: {e}', flush=True)
                continue

        data['books'] = books_dict
        KINDLE_DATA_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))

        # Summary
        categories = {}
        for book in books_dict.values():
            cat = book.get('category', 'unclassified')
            categories[cat] = categories.get(cat, 0) + 1

        print(f'[kindle/classify] Classified {classified_count} books: {categories}', flush=True)
        self._send_json_response(200, {
            'status': 'ok',
            'classified': classified_count,
            'categories': categories,
        })

    def _handle_kindle_resolve_titles(self):
        """POST /kindle/resolve-titles — use LLM to identify real titles from filenames.

        Body: { "books": [ { "key": "...", "filename": "pg37452-images-3", "author": "Elizabeth Barrett Browning" } ] }
        Resolves filenames to real book titles using Gemini with search grounding.
        """
        body = self._read_json_body()
        if body is None:
            return

        if not KINDLE_DATA_PATH.exists():
            self._send_json_response(404, {'error': 'No Kindle library data yet'})
            return

        books_to_resolve = body.get('books', [])
        if not books_to_resolve:
            self._send_json_response(400, {'error': 'No books to resolve'})
            return

        from gemini_llm import call_llm

        resolved = {}
        # Process in batches of 30
        for i in range(0, len(books_to_resolve), 30):
            batch = books_to_resolve[i:i+30]
            book_list = '\n'.join(
                f'{j+1}. Filename: "{b["filename"]}" | Author: "{b.get("author", "unknown")}"'
                for j, b in enumerate(batch)
            )

            prompt = f"""Identify the real book title for each of these ebook files.
Clues: "pg*-images-3" = Project Gutenberg file. Use the author to find the specific work.
Other filenames may be abbreviations or slugs of the title.

Return ONLY a JSON array with "index" (1-based) and "title" (the canonical book title).
If unsure, set title to null.

{book_list}

JSON array only:"""

            try:
                result = call_llm(prompt)
                result_text = result.strip()
                if result_text.startswith('```'):
                    result_text = result_text.split('\n', 1)[1].rsplit('```', 1)[0].strip()
                titles = json.loads(result_text)

                for item in titles:
                    idx = item.get('index', 0) - 1
                    title = item.get('title')
                    if 0 <= idx < len(batch) and title:
                        key = batch[idx].get('key', '')
                        resolved[key] = title
            except Exception as e:
                print(f'[kindle/resolve-titles] Batch {i//30} error: {e}', flush=True)

        # Update kindle_library.json with resolved titles
        if resolved:
            try:
                data = json.loads(KINDLE_DATA_PATH.read_text())
                books_dict = data.get('books', {})
                matched = 0
                for key, title in resolved.items():
                    # Try direct key match first
                    if key in books_dict:
                        books_dict[key]['title_resolved'] = title
                        matched += 1
                    else:
                        # Key might be full book_id (A:XXX-0) but server key is inner part (XXX)
                        inner = key.removeprefix('A:').removesuffix('-0')
                        if inner in books_dict:
                            books_dict[inner]['title_resolved'] = title
                            matched += 1
                        else:
                            # Search by book_id field
                            for sk, sv in books_dict.items():
                                if sv.get('book_id') == key:
                                    sv['title_resolved'] = title
                                    matched += 1
                                    break
                print(f'[kindle/resolve-titles] Wrote {matched} resolved titles to kindle_library.json', flush=True)
                KINDLE_DATA_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            except Exception as e:
                print(f'[kindle/resolve-titles] Write error: {e}', flush=True)

        print(f'[kindle/resolve-titles] Resolved {len(resolved)} of {len(books_to_resolve)} titles', flush=True)
        self._send_json_response(200, {'status': 'ok', 'resolved': resolved})

    def _handle_book_sync_save(self):
        """POST /book/sync — save books + captures to server (client → server)."""
        content_length = int(self.headers.get('Content-Length', 0))
        if not content_length:
            self._send_json_response(400, {'error': 'Missing request body'})
            return
        try:
            body = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, ValueError):
            self._send_json_response(400, {'error': 'Invalid JSON'})
            return

        books = body.get('books', [])
        captures = body.get('captures', [])

        # Load existing server data and merge (client wins for same ID)
        existing = {'books': [], 'captures': []}
        if PHYSICAL_BOOKS_PATH.exists():
            try:
                existing = json.loads(PHYSICAL_BOOKS_PATH.read_text())
            except json.JSONDecodeError:
                pass

        # Merge books: client version wins for same ID
        existing_book_ids = {b['id']: i for i, b in enumerate(existing.get('books', []))}
        merged_books = list(existing.get('books', []))
        for book in books:
            if book['id'] in existing_book_ids:
                merged_books[existing_book_ids[book['id']]] = book
            else:
                merged_books.append(book)

        # Merge captures: client version wins for same ID
        existing_cap_ids = {c['id']: i for i, c in enumerate(existing.get('captures', []))}
        merged_captures = list(existing.get('captures', []))
        for cap in captures:
            if cap['id'] in existing_cap_ids:
                merged_captures[existing_cap_ids[cap['id']]] = cap
            else:
                merged_captures.append(cap)

        result = {'books': merged_books, 'captures': merged_captures}
        PHYSICAL_BOOKS_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False))

        print(f'[book/sync] Saved {len(merged_books)} books, {len(merged_captures)} captures', flush=True)
        self._send_json_response(200, {
            'status': 'ok',
            'books_count': len(merged_books),
            'captures_count': len(merged_captures),
        })

    def _handle_book_sync_load(self):
        """GET /book/sync — load books + captures from server (server → client)."""
        if PHYSICAL_BOOKS_PATH.exists():
            try:
                data = json.loads(PHYSICAL_BOOKS_PATH.read_text())
                self._send_json_response(200, data)
            except json.JSONDecodeError:
                self._send_json_response(200, {'books': [], 'captures': []})
        else:
            self._send_json_response(200, {'books': [], 'captures': []})

    def _handle_resurfacing_generate(self):
        """POST /book/resurfacing/generate — generate a resurfacing session."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = {}
        if content_length:
            try:
                body = json.loads(self.rfile.read(content_length))
            except (json.JSONDecodeError, ValueError):
                pass
        include_dialogues = body.get('include_dialogues', True)
        try:
            from resurfacing_engine import generate_session
            session = generate_session(include_dialogues=include_dialogues)
            self._send_json_response(200, session)
        except Exception as e:
            print(f'[resurfacing/generate] Error: {e}', flush=True)
            import traceback; traceback.print_exc()
            self._send_json_response(500, {'error': str(e)})

    def _handle_resurfacing_respond(self):
        """POST /book/resurfacing/respond — record response to a resurfacing prompt."""
        content_length = int(self.headers.get('Content-Length', 0))
        if not content_length:
            self._send_json_response(400, {'error': 'Missing body'})
            return
        try:
            body = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, ValueError):
            self._send_json_response(400, {'error': 'Invalid JSON'})
            return

        capture_id = body.get('capture_id', '')
        response_text = body.get('response_text', '')
        response_type = body.get('response_type', 'text')
        if not capture_id or not response_text:
            self._send_json_response(400, {'error': 'Missing capture_id or response_text'})
            return

        from resurfacing_engine import record_response
        record_response(capture_id, response_text, response_type)
        self._send_json_response(200, {'status': 'ok'})

    def _handle_resurfacing_skip(self):
        """POST /book/resurfacing/skip — record skip for a resurfacing prompt."""
        content_length = int(self.headers.get('Content-Length', 0))
        if not content_length:
            self._send_json_response(400, {'error': 'Missing body'})
            return
        try:
            body = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, ValueError):
            self._send_json_response(400, {'error': 'Invalid JSON'})
            return

        capture_id = body.get('capture_id', '')
        if not capture_id:
            self._send_json_response(400, {'error': 'Missing capture_id'})
            return

        from resurfacing_engine import record_skip
        record_skip(capture_id)
        self._send_json_response(200, {'status': 'ok'})

    def _handle_resurfacing_status(self):
        """GET /book/resurfacing/status — get resurfacing stats."""
        from resurfacing_engine import get_status
        self._send_json_response(200, get_status())

    def _handle_process_kindle(self):
        """POST /book/process-kindle — trigger Kindle book processing."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = {}
        if content_length:
            try:
                body = json.loads(self.rfile.read(content_length))
            except (json.JSONDecodeError, ValueError):
                pass

        max_books = body.get('max', 10)
        print(f'[process-kindle] Processing up to {max_books} books', flush=True)

        def _process():
            try:
                from process_kindle_books import process_all
                process_all(do_research=True, max_books=max_books)
            except Exception as e:
                print(f'[process-kindle] Error: {e}', flush=True)
                import traceback; traceback.print_exc()

        thread = threading.Thread(target=_process, daemon=True)
        thread.start()
        self._send_json_response(202, {'status': 'processing', 'max_books': max_books})

    def _handle_ingest_book(self):
        if INGEST_TOKEN:
            token = self.headers.get('X-Petrarca-Token', '')
            if token != INGEST_TOKEN:
                self._send_json_response(401, {'error': 'Invalid or missing auth token'})
                return

        body = self._read_json_body()
        if body is None:
            return
        book_path = body.get('path', '').strip()
        if not book_path:
            self._send_json_response(400, {'error': 'Missing required field: path'})
            return

        chapter = body.get('chapter')
        request_id = f'book_{int(time.time())}_{hash(book_path) % 10000:04d}'

        thread = threading.Thread(
            target=run_ingest_book,
            args=(book_path, chapter, request_id),
            daemon=True,
        )
        thread.start()

        print(f'[book-ingest] Queued: {book_path} (chapter={chapter})', flush=True)

        self.send_response(202)
        self._send_cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'id': request_id, 'status': 'processing', 'path': book_path}).encode())

    def _handle_twitter_cookies(self):
        """Update twikit cookies via API. Expects {auth_token, ct0}."""
        if INGEST_TOKEN:
            token = self.headers.get('X-Petrarca-Token', '')
            if token != INGEST_TOKEN:
                self._send_json_response(401, {'error': 'Invalid auth token'})
                return

        body = self._read_json_body()
        if body is None:
            return

        auth_token = body.get('auth_token', '').strip()
        ct0 = body.get('ct0', '').strip()

        if not auth_token or not ct0:
            self._send_json_response(400, {'error': 'Both auth_token and ct0 are required'})
            return

        TWIKIT_COOKIES_DIR.mkdir(parents=True, exist_ok=True)
        cookies = {'auth_token': auth_token, 'ct0': ct0}

        # twikit's save_cookies format is a dict of cookie dicts
        # but the simplest approach: use twikit Client to set and save
        try:
            sys.path.insert(0, str(SCRIPTS_DIR))
            from twikit import Client
            client = Client('en-US')
            client.set_cookies(cookies)
            client.save_cookies(str(TWIKIT_COOKIES_PATH))
            print(f'[twitter] Cookies updated via API', flush=True)
            self._send_json_response(200, {'status': 'ok', 'message': 'Cookies saved'})
        except Exception as e:
            self._send_json_response(500, {'error': f'Failed to save cookies: {e}'})

    def do_POST(self):
        if self.path == '/chat':
            return self._handle_chat()
        if self.path == '/note':
            return self._handle_note()
        if self.path == '/research/topic':
            return self._handle_topic_research()
        if self.path == '/generate-questions':
            return self._handle_generate_questions()
        if self.path == '/ingest':
            return self._handle_ingest()
        if self.path == '/ingest-youtube':
            return self._handle_ingest_youtube()
        if self.path == '/ingest-email':
            return self._handle_ingest_email()
        if self.path == '/ingest-book':
            return self._handle_ingest_book()
        if self.path == '/twitter/cookies':
            return self._handle_twitter_cookies()
        if self.path == '/ingest-note':
            return self._handle_ingest_note()
        if self.path == '/ingest-cancel':
            return self._handle_ingest_cancel()
        if self.path == '/report-scrape':
            return self._handle_report_scrape()
        if self.path == '/feedback':
            return self._handle_feedback()
        if self.path == '/book/identify':
            return self._handle_book_identify()
        if self.path == '/book/ocr-toc':
            return self._handle_book_ocr_toc()
        if self.path == '/book/ocr-page':
            return self._handle_book_ocr_page()
        if self.path == '/book/voice-note':
            return self._handle_book_voice_note()
        if self.path == '/book/research':
            return self._handle_book_research()
        if self.path == '/book/chapter-insights':
            return self._handle_book_chapter_insights()
        if self.path == '/book/story-so-far':
            return self._handle_book_story_so_far()
        if self.path == '/book/sync':
            return self._handle_book_sync_save()
        if self.path == '/book/resurfacing/generate':
            return self._handle_resurfacing_generate()
        if self.path == '/book/resurfacing/respond':
            return self._handle_resurfacing_respond()
        if self.path == '/book/resurfacing/skip':
            return self._handle_resurfacing_skip()
        if self.path == '/book/process-kindle':
            return self._handle_process_kindle()
        if self.path == '/kindle/sync':
            return self._handle_kindle_sync()
        if self.path == '/kindle/curate':
            return self._handle_kindle_curate()
        if self.path == '/kindle/include':
            return self._handle_kindle_include()
        if self.path == '/kindle/classify':
            return self._handle_kindle_classify()
        if self.path == '/kindle/resolve-titles':
            return self._handle_kindle_resolve_titles()

        if self.path == '/research/explore-batch':
            return self._handle_explore_batch()

        # /notes/{note_id}/execute-action
        if self.path.startswith('/notes/') and self.path.endswith('/execute-action'):
            return self._handle_execute_action()

        if self.path not in ('/research', '/research/explore'):
            self.send_error(404)
            return

        content_length = int(self.headers.get('Content-Length', 0))
        if content_length:
            try:
                body = json.loads(self.rfile.read(content_length))
            except (json.JSONDecodeError, ValueError) as e:
                self._send_json_response(400, {'error': f'Invalid JSON: {e}'})
                return
        else:
            body = {}

        if self.path == '/research/explore':
            request_id = body.get('id', f'exp_{int(time.time())}')
            subtopic = body.get('subtopic', '')
            exploration_tag = body.get('exploration_tag', '')
            triage_signals = body.get('triage_signals', {})
            existing_concepts = body.get('concepts', [])

            if not subtopic or not exploration_tag:
                self.send_error(400, 'Missing subtopic or exploration_tag')
                return

            result_path = RESULTS_DIR / f'{request_id}.json'
            result_path.write_text(json.dumps({
                'id': request_id,
                'type': 'explore',
                'status': 'processing',
                'subtopic': subtopic,
                'exploration_tag': exploration_tag,
                'requested_at': int(time.time() * 1000),
            }, indent=2))

            thread = threading.Thread(
                target=run_explore,
                args=(request_id, subtopic, exploration_tag, triage_signals, existing_concepts),
                daemon=True,
            )
            thread.start()

            print(f'[explore] Started {request_id}: {subtopic[:80]}...')

            self.send_response(202)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'id': request_id, 'status': 'processing'}).encode())
            return

        request_id = body.get('id', f'res_{int(time.time())}')
        query = body.get('query', '')
        article_title = body.get('article_title', '')
        article_summary = body.get('article_summary', '')
        concepts = body.get('concepts', [])

        if not query:
            self.send_error(400, 'Missing query')
            return

        # Save initial pending state
        result_path = RESULTS_DIR / f'{request_id}.json'
        result_path.write_text(json.dumps({
            'id': request_id,
            'status': 'processing',
            'query': query,
            'article_title': article_title,
            'requested_at': int(time.time() * 1000),
        }, indent=2))

        # Spawn background thread
        thread = threading.Thread(
            target=run_research,
            args=(request_id, query, article_title, article_summary, concepts),
            daemon=True,
        )
        thread.start()

        print(f'[research] Started {request_id}: {query[:80]}...')

        self.send_response(202)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'id': request_id, 'status': 'processing'}).encode())

    def _load_articles_map(self) -> dict:
        """Load articles.json and return {id: title} map."""
        try:
            articles = json.loads(ARTICLES_PATH.read_text())
            return {a['id']: a.get('title', 'Untitled') for a in articles}
        except (OSError, json.JSONDecodeError, KeyError):
            return {}

    def _load_log_events(self, days: int) -> list[dict]:
        """Load interaction log events for the last N days."""
        events = []
        today = datetime.now(timezone.utc).date()
        for i in range(days):
            d = today - timedelta(days=i)
            log_file = LOG_DIR / f'interactions_{d.isoformat()}.jsonl'
            if not log_file.exists():
                continue
            try:
                for line in log_file.read_text().splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            except OSError:
                continue
        return events

    def _load_research_results(self) -> list[dict]:
        """Load all research result files."""
        results = []
        if not RESULTS_DIR.exists():
            return results
        for f in RESULTS_DIR.glob('*.json'):
            try:
                results.append(json.loads(f.read_text()))
            except (OSError, json.JSONDecodeError):
                continue
        return results

    def _handle_activity_feed(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        days = int(params.get('days', ['1'])[0])

        articles_map = self._load_articles_map()
        raw_events = self._load_log_events(days)
        research_results = self._load_research_results()

        # Build lookup: research_id -> result
        research_by_id = {r['id']: r for r in research_results if 'id' in r}

        timeline = []

        # --- Group reading sessions ---
        # Collect reader_* events by (session_id, article_id)
        reading_sessions = {}  # (session_id, article_id) -> list of events
        for ev in raw_events:
            event_name = ev.get('event', '')
            if event_name.startswith('reader_') and ev.get('article_id'):
                key = (ev.get('session_id', ''), ev['article_id'])
                reading_sessions.setdefault(key, []).append(ev)

        for (session_id, article_id), evts in reading_sessions.items():
            evts.sort(key=lambda e: e.get('ts', ''))
            anchor = next((e for e in evts if e['event'] == 'reader_open'), evts[0])

            finished = any(e['event'] == 'reader_done' for e in evts)
            highlights = sum(1 for e in evts if e['event'] == 'reader_highlight_add')
            close_evt = next((e for e in evts if e['event'] == 'reader_close'), None)
            time_spent_ms = close_evt.get('time_spent_ms', 0) if close_evt else 0
            scroll_pct = 0
            for e in evts:
                if e['event'] == 'reader_scroll_milestone':
                    scroll_pct = max(scroll_pct, e.get('pct', 0))

            title = articles_map.get(article_id, anchor.get('title', article_id[:12]))
            subtype = 'finished' if finished else 'in_progress'

            # Build subtitle
            parts = []
            if time_spent_ms > 0:
                mins = round(time_spent_ms / 60000)
                parts.append(f'{mins} min' if mins > 0 else '<1 min')
            if highlights:
                parts.append(f'{highlights} highlight{"s" if highlights != 1 else ""}')
            subtitle = ' · '.join(parts) if parts else None

            prefix = 'Finished reading' if finished else 'Reading'
            timeline.append({
                'id': f'evt_{anchor["ts"]}_{article_id[:8]}',
                'type': 'reading',
                'subtype': subtype,
                'ts': anchor.get('ts'),
                'title': f'{prefix}: {title}',
                'subtitle': subtitle,
                'article_id': article_id,
                'meta': {
                    'time_spent_ms': time_spent_ms,
                    'highlights': highlights,
                    'scroll_pct': scroll_pct,
                },
            })

        # --- Dismissals ---
        for ev in raw_events:
            if ev.get('event') == 'article_dismissed' and ev.get('article_id'):
                aid = ev['article_id']
                title = articles_map.get(aid, aid[:12])
                reason = ev.get('reason', '')
                timeline.append({
                    'id': f'evt_{ev["ts"]}_{aid[:8]}',
                    'type': 'reading',
                    'subtype': 'dismissed',
                    'ts': ev.get('ts'),
                    'title': f'Dismissed: {title}',
                    'subtitle': reason if reason else None,
                    'article_id': aid,
                })

        # --- Interest signals ---
        # Group interest_chip_tap events within 60s of each other for same article
        interest_events = [e for e in raw_events if e.get('event') == 'interest_chip_tap']
        interest_events.sort(key=lambda e: e.get('ts', ''))
        interest_groups = []
        for ev in interest_events:
            ev_ts = ev.get('ts', '')
            merged = False
            for group in interest_groups:
                last_ts = group[-1].get('ts', '')
                # Check same article or within 60s
                try:
                    t1 = datetime.fromisoformat(last_ts.replace('Z', '+00:00'))
                    t2 = datetime.fromisoformat(ev_ts.replace('Z', '+00:00'))
                    if abs((t2 - t1).total_seconds()) <= 60:
                        group.append(ev)
                        merged = True
                        break
                except (ValueError, TypeError):
                    pass
            if not merged:
                interest_groups.append([ev])

        for group in interest_groups:
            positive = []
            negative = []
            for ev in group:
                topic = ev.get('topic', '')
                if ev.get('positive', True):
                    positive.append(topic)
                else:
                    negative.append(topic)

            parts = []
            for t in positive:
                parts.append(f'+{t}')
            for t in negative:
                parts.append(f'-{t}')

            timeline.append({
                'id': f'evt_{group[0]["ts"]}_interest',
                'type': 'interest',
                'subtype': 'signal',
                'ts': group[0].get('ts'),
                'title': 'Signaled interest',
                'subtitle': ' '.join(parts) if parts else None,
                'topics_positive': positive,
                'topics_negative': negative,
            })

        # --- Pipeline runs ---
        pipeline_events = [e for e in raw_events if e.get('source') == 'pipeline']
        pipeline_events.sort(key=lambda e: e.get('ts', ''))
        pipeline_runs = []
        for ev in pipeline_events:
            ev_ts = ev.get('ts', '')
            merged = False
            for run in pipeline_runs:
                last_ts = run[-1].get('ts', '')
                try:
                    t1 = datetime.fromisoformat(last_ts.replace('Z', '+00:00'))
                    t2 = datetime.fromisoformat(ev_ts.replace('Z', '+00:00'))
                    if abs((t2 - t1).total_seconds()) <= 900:
                        run.append(ev)
                        merged = True
                        break
                except (ValueError, TypeError):
                    pass
            if not merged:
                pipeline_runs.append([ev])

        STEP_LABELS = {
            'pipeline_fetch_twitter': 'Fetched Twitter bookmarks',
            'pipeline_fetch_readwise': 'Fetched Readwise articles',
            'pipeline_build_articles': 'Built articles',
            'pipeline_defrag_topics': 'Defragmented topics',
            'pipeline_extract_claims': 'Extracted claims',
            'pipeline_build_index': 'Built knowledge index',
        }

        for run in pipeline_runs:
            event_names = [e.get('event', '') for e in run]
            completed = 'pipeline_complete' in event_names
            complete_ev = next((e for e in run if e.get('event') == 'pipeline_complete'), None)
            elapsed = complete_ev.get('elapsed_seconds') if complete_ev else None

            if completed and elapsed:
                mins, secs = divmod(int(elapsed), 60)
                run_title = f'Content refresh ({mins}m {secs}s)' if mins else f'Content refresh ({secs}s)'
            elif completed:
                run_title = 'Content refresh complete'
            else:
                run_title = 'Content refresh running'

            steps = len([n for n in event_names if n in STEP_LABELS])
            timeline.append({
                'id': f'evt_{run[0]["ts"]}_pipeline',
                'type': 'system',
                'subtype': 'pipeline',
                'ts': run[-1].get('ts') if completed else run[0].get('ts'),
                'title': run_title,
                'subtitle': f'{steps} steps' if steps else None,
            })

            # Also emit individual step events for granular view
            for ev in run:
                name = ev.get('event', '')
                if name in STEP_LABELS:
                    timeline.append({
                        'id': f'evt_{ev["ts"]}_{name}',
                        'type': 'system',
                        'subtype': 'pipeline_step',
                        'ts': ev.get('ts'),
                        'title': STEP_LABELS[name],
                    })

        # --- Server-side events (ingestion, article processing) ---
        INGEST_LABELS = {
            'clipper': 'Clipped',
            'reader_link': 'From reader',
        }
        for ev in raw_events:
            if ev.get('source') != 'server':
                continue
            event_name = ev.get('event', '')

            if event_name == 'ingest_queued':
                title = ev.get('title') or ev.get('url', 'Unknown')[:60]
                src = ev.get('ingest_source', 'unknown')
                label = INGEST_LABELS.get(src, 'Ingested')
                timeline.append({
                    'id': f'evt_{ev["ts"]}_ingest',
                    'type': 'system',
                    'subtype': 'ingest',
                    'ts': ev.get('ts'),
                    'title': f'{label}: {title}',
                    'article_id': ev.get('article_id'),
                })

            elif event_name == 'ingest_email':
                timeline.append({
                    'id': f'evt_{ev["ts"]}_email',
                    'type': 'system',
                    'subtype': 'ingest',
                    'ts': ev.get('ts'),
                    'title': f'Email from {ev.get("sender", "unknown")}',
                })

            elif event_name == 'article_processed':
                title = ev.get('title', 'Unknown')
                wc = ev.get('word_count', 0)
                wc_str = f' ({wc} words)' if wc else ''
                timeline.append({
                    'id': f'evt_{ev["ts"]}_processed',
                    'type': 'system',
                    'subtype': 'processed',
                    'ts': ev.get('ts'),
                    'title': f'Processed: {title}{wc_str}',
                    'article_id': ev.get('article_id'),
                })

            elif event_name == 'bookmarks_fetched':
                count = ev.get('count', 0)
                if count > 0:
                    timeline.append({
                        'id': f'evt_{ev["ts"]}_twitter',
                        'type': 'system',
                        'subtype': 'fetch',
                        'ts': ev.get('ts'),
                        'title': f'Fetched {count} Twitter bookmarks',
                    })

            elif event_name == 'readwise_fetched':
                count = ev.get('count', 0)
                docs = ev.get('documents', count)
                if count > 0:
                    timeline.append({
                        'id': f'evt_{ev["ts"]}_readwise',
                        'type': 'system',
                        'subtype': 'fetch',
                        'ts': ev.get('ts'),
                        'title': f'Fetched {count} Readwise items → {docs} docs',
                    })

        # --- Research events ---
        for ev in raw_events:
            event_name = ev.get('event', '')
            if event_name in ('research_spawned', 'topic_research_spawned'):
                topic = ev.get('topic', '')
                aid = ev.get('article_id')

                # Try to match with a completed result
                matched_result = None
                for rid, res in research_by_id.items():
                    if res.get('query') == topic or res.get('article_title') == articles_map.get(aid, ''):
                        matched_result = res
                        break

                if event_name == 'topic_research_spawned':
                    title_text = f'Research: {topic}'
                else:
                    article_title = articles_map.get(aid, '') if aid else ''
                    title_text = f'Research: {topic}' if topic else f'Research on {article_title}'

                subtype = 'dispatched'
                subtitle = 'Pending'
                if matched_result:
                    if matched_result.get('status') == 'completed':
                        subtype = 'completed'
                        subtitle = 'Results ready'
                    elif matched_result.get('status') == 'failed':
                        subtype = 'completed'
                        subtitle = 'Failed'

                node = {
                    'id': f'evt_{ev["ts"]}_research',
                    'type': 'research',
                    'subtype': subtype,
                    'ts': ev.get('ts'),
                    'title': title_text,
                    'subtitle': subtitle,
                }
                if aid:
                    node['article_id'] = aid
                timeline.append(node)

        # --- Queue actions ---
        for ev in raw_events:
            if ev.get('event') == 'queue_add' and ev.get('article_id'):
                aid = ev['article_id']
                title = articles_map.get(aid, aid[:12])
                timeline.append({
                    'id': f'evt_{ev["ts"]}_{aid[:8]}',
                    'type': 'reading',
                    'subtype': 'queued',
                    'ts': ev.get('ts'),
                    'title': f'Queued: {title}',
                    'article_id': aid,
                })

        # Sort newest-first
        timeline.sort(key=lambda e: e.get('ts', ''), reverse=True)

        self._send_json_response(200, {'events': timeline})

    def do_GET(self):
        if self.path.startswith('/book/research/'):
            return self._handle_book_research_get()
        if self.path == '/book/sync':
            return self._handle_book_sync_load()
        if self.path == '/book/resurfacing/status':
            return self._handle_resurfacing_status()
        if self.path.startswith('/kindle/library'):
            return self._handle_kindle_library_get()
        if self.path.startswith('/kindle/highlights'):
            return self._handle_kindle_highlights_get()

        if self.path.startswith('/activity/feed'):
            return self._handle_activity_feed()

        elif self.path == '/research/results':
            results = []
            for f in sorted(RESULTS_DIR.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True):
                try:
                    data = json.loads(f.read_text())
                    if data.get('status') == 'completed':
                        results.append(data)
                except (json.JSONDecodeError, OSError):
                    continue

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(results).encode())

        elif self.path.startswith('/notes'):
            # /notes?article_id=X or /notes (all)
            from urllib.parse import parse_qs, urlparse
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            article_filter = params.get('article_id', [None])[0]

            notes = []
            for f in sorted(NOTES_DIR.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True):
                try:
                    note = json.loads(f.read_text())
                    if article_filter and note.get('article_id') != article_filter:
                        continue
                    notes.append(note)
                except (json.JSONDecodeError, OSError):
                    continue

            self.send_response(200)
            self._send_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(notes).encode())

        elif self.path.startswith('/ingest-status'):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            ingest_id = params.get('id', [None])[0]
            if not ingest_id:
                self._send_json_response(400, {'error': 'Missing id parameter'})
                return
            log_path = INGEST_DIR / f'{ingest_id}.json'
            if not log_path.exists():
                self._send_json_response(404, {'error': 'Ingest not found', 'id': ingest_id})
                return
            try:
                data = json.loads(log_path.read_text())
                self._send_json_response(200, {
                    'id': data.get('id'),
                    'status': data.get('status', 'unknown'),
                    'article_id': data.get('article_id'),
                    'url': data.get('url'),
                })
            except (json.JSONDecodeError, OSError) as e:
                self._send_json_response(500, {'error': str(e)})

        elif self.path == '/twitter/status':
            try:
                result = asyncio.run(_check_twikit_cookies())
            except Exception as e:
                result = {'valid': False, 'error': f'Check failed: {e}'}
            self._send_json_response(200, result)

        elif self.path == '/scrape-reports':
            try:
                reports = json.loads(SCRAPE_REPORTS_PATH.read_text()) if SCRAPE_REPORTS_PATH.exists() else []
                # Only show pending reports
                pending = [r for r in reports if r.get('status', 'pending') == 'pending']
                self._send_json_response(200, pending)
            except (json.JSONDecodeError, OSError):
                self._send_json_response(200, [])

        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode())

        else:
            self.send_error(404)

    def log_message(self, format, *args):
        print(f'[http] {args[0]}')


if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', PORT), ResearchHandler)
    print(f'Research server listening on port {PORT}')
    print(f'Results directory: {RESULTS_DIR}')
    server.serve_forever()

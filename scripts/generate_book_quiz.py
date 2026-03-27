#!/usr/bin/env python3
"""Generate a Matuschak-style retrieval quiz from a book EPUB.

For each chapter, uses Claude to generate understanding-lens questions
(causal, comparative, significance, temporal) — not surface recall.
Outputs a self-contained HTML card-stack quiz.

Usage:
    python generate_book_quiz.py path/to/book.epub
    python generate_book_quiz.py path/to/book.epub --chapters 1-5
    python generate_book_quiz.py path/to/book.epub --output quiz.html
    python generate_book_quiz.py path/to/book.epub --curriculum sicily
"""

import argparse
import glob
import json
import re
import subprocess
import sys
from pathlib import Path

import pymupdf

SCRIPT_DIR = Path(__file__).parent
CURRICULA_DIR = SCRIPT_DIR.parent / "data" / "curricula"

QUESTION_GENERATION_PROMPT = """You are generating a post-reading quiz for someone who just finished this chapter of a history book.

Book: {book_title}
Chapter: {chapter_title}
Chapter text (first 4000 chars):
{chapter_text}

Generate exactly {n_questions} retrieval questions that test UNDERSTANDING, not surface recall.

Use these understanding lenses — vary across your questions:
- CAUSAL: "Why did X happen?" / "What caused X to fail?" / "What sequence of events led to X?"
- COMPARATIVE: "How was Syracuse different from mainland Greek cities in X?" / "What distinguished X from Y?"
- SIGNIFICANCE: "Why was X historically significant?" / "What made X a turning point for Syracuse?"
- TEMPORAL: "What was happening elsewhere in the Mediterranean during X?" / "How does X relate to events in Rome/Athens/Carthage at this time?"
- PATTERN: "How does X reflect a recurring dynamic in Sicilian history?" / "What precedent did X set?"
- CONSEQUENCE: "What were the long-term effects of X?" / "How did X shape what came after?"

For each question provide:
- "question": the retrieval question (open-ended, requires thinking)
- "answer": 3-5 sentences giving the key insight (this is the BACK of the card — the model answer)
- "lens": one of CAUSAL / COMPARATIVE / SIGNIFICANCE / TEMPORAL / PATTERN / CONSEQUENCE
- "temporal_hook": optional — if any dates/people cross-reference with wider history (e.g. "This is contemporaneous with the Second Punic War"), provide a one-sentence anchor

Output JSON array only, no markdown:
[
  {{"question": "...", "answer": "...", "lens": "...", "temporal_hook": "..." }},
  ...
]"""


def parse_epub_chapters(epub_path: str) -> tuple[str, str, list[dict]]:
    """Parse EPUB into chapters. Returns (title, author, chapters)."""
    doc = pymupdf.open(epub_path)
    toc = doc.get_toc()
    meta = doc.metadata or {}
    title = meta.get("title", "") or Path(epub_path).stem
    author = meta.get("author", "") or ""

    if not toc:
        full_text = "".join(page.get_text() for page in doc)
        doc.close()
        return title, author, [{"number": 1, "title": title, "text": full_text.strip()}]

    # Only level-1 TOC entries
    l1 = [(t, p) for level, t, p in toc if level == 1]
    chapters = []
    for i, (ch_title, start_page) in enumerate(l1):
        end_page = l1[i + 1][1] if i + 1 < len(l1) else doc.page_count + 1
        text = ""
        for pg in range(start_page - 1, end_page - 1):
            if 0 <= pg < doc.page_count:
                text += doc[pg].get_text()
        chapters.append({
            "number": i + 1,
            "title": ch_title,
            "text": text.strip(),
        })

    doc.close()
    # Filter out front-matter and short chapters (< 500 chars)
    content_chapters = [
        ch for ch in chapters
        if len(ch["text"]) > 500 and not any(
            skip in ch["title"].lower()
            for skip in ["contents", "copyright", "author bio", "dedication",
                         "acknowledgements", "bibliography", "notes", "index",
                         "illustrations", "further reading", "glossary", "cover",
                         "title page", "chronological"]
        )
    ]
    # Re-number sequentially after filtering
    for i, ch in enumerate(content_chapters):
        ch["number"] = i + 1
    return title, author, content_chapters


def call_claude(prompt: str) -> str | None:
    """Call claude -p for question generation."""
    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        print(f"  claude -p error: {result.stderr[:200]}", file=sys.stderr)
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"  claude -p failed: {e}", file=sys.stderr)
    return None


def parse_json_response(text: str) -> list | None:
    """Parse JSON array from LLM response, stripping markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    # Find the JSON array
    match = re.search(r'\[[\s\S]*\]', cleaned)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"  JSON parse error: {e}\n  Raw: {cleaned[:200]}", file=sys.stderr)
        return None


def generate_questions_for_chapter(book_title: str, chapter: dict, n: int = 4) -> list[dict]:
    """Generate retrieval questions for a chapter using Claude."""
    chapter_text = chapter["text"][:4000]
    prompt = QUESTION_GENERATION_PROMPT.format(
        book_title=book_title,
        chapter_title=chapter["title"],
        chapter_text=chapter_text,
        n_questions=n,
    )
    print(f"  Generating {n} questions for: {chapter['title'][:60]}")
    raw = call_claude(prompt)
    if not raw:
        print(f"  WARNING: failed to generate questions for chapter {chapter['number']}", file=sys.stderr)
        return []

    questions = parse_json_response(raw)
    if not questions:
        return []

    # Annotate with chapter info
    for q in questions:
        q["chapter_title"] = chapter["title"]
        q["chapter_number"] = chapter["number"]
        q.setdefault("temporal_hook", "")
        q.setdefault("lens", "")

    return questions


LENS_COLORS = {
    "CAUSAL":       ("#7a3000", "#fff0e8"),
    "COMPARATIVE":  ("#1a4a7a", "#e8f0ff"),
    "SIGNIFICANCE": ("#2a6a3a", "#e8f5ec"),
    "TEMPORAL":     ("#5a3a7a", "#f0e8ff"),
    "PATTERN":      ("#7a6a00", "#fff8e0"),
    "CONSEQUENCE":  ("#5a0a0a", "#ffe8e8"),
}

LENS_LABELS = {
    "CAUSAL":       "Why?",
    "COMPARATIVE":  "Compare",
    "SIGNIFICANCE": "Why it matters",
    "TEMPORAL":     "Timing",
    "PATTERN":      "Pattern",
    "CONSEQUENCE":  "What followed",
}


def build_html(book_title: str, author: str, all_questions: list[dict]) -> str:
    cards_json = json.dumps(all_questions, ensure_ascii=False)
    lens_colors_json = json.dumps({k: list(v) for k, v in LENS_COLORS.items()})
    lens_labels_json = json.dumps(LENS_LABELS)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Quiz — {book_title}</title>
<style>
  :root {{
    --parchment: #f7f4ec;
    --parchment-dark: #f0ece2;
    --ink: #2a2420;
    --rubric: #8b2500;
    --text-body: #333333;
    --text-secondary: #6a6458;
    --text-muted: #b0a898;
    --rule: #e4dfd4;
    --claim-new: #2a7a4a;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--parchment);
    color: var(--ink);
    font-family: 'EB Garamond', Georgia, serif;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 32px 16px;
  }}
  .header {{
    text-align: center;
    margin-bottom: 32px;
    max-width: 640px;
    width: 100%;
  }}
  .title {{ font-size: 22px; font-weight: 600; color: var(--ink); margin-bottom: 4px; }}
  .author {{ font-size: 14px; color: var(--text-secondary); font-style: italic; margin-bottom: 12px; }}
  .double-rule {{
    border: none;
    height: 5px;
    background: linear-gradient(
      to bottom,
      var(--rubric) 0px, var(--rubric) 2px,
      transparent 2px, transparent 4px,
      var(--rubric) 4px, var(--rubric) 5px
    );
    margin: 8px 0 16px;
  }}
  .progress-bar-outer {{
    width: 100%;
    max-width: 640px;
    height: 4px;
    background: var(--rule);
    border-radius: 2px;
    margin-bottom: 24px;
  }}
  .progress-bar-inner {{
    height: 4px;
    background: var(--rubric);
    border-radius: 2px;
    transition: width 0.4s ease;
  }}
  .counter {{
    font-family: 'DM Sans', system-ui, sans-serif;
    font-size: 13px;
    color: var(--text-muted);
    text-align: center;
    margin-bottom: 16px;
  }}
  .card-container {{
    width: 100%;
    max-width: 640px;
    perspective: 1000px;
  }}
  .card {{
    background: white;
    border: 1px solid var(--rule);
    border-radius: 4px;
    padding: 28px 28px 24px;
    min-height: 240px;
    display: flex;
    flex-direction: column;
    cursor: pointer;
    user-select: none;
    position: relative;
    transition: box-shadow 0.15s;
  }}
  .card:hover {{ box-shadow: 0 2px 12px rgba(42,36,32,0.08); }}
  .card-chapter {{
    font-family: 'DM Sans', system-ui, sans-serif;
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-bottom: 12px;
  }}
  .lens-badge {{
    display: inline-block;
    font-family: 'DM Sans', system-ui, sans-serif;
    font-size: 10px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 2px 7px;
    border-radius: 2px;
    margin-left: 8px;
    vertical-align: middle;
    font-weight: 500;
  }}
  .card-question {{
    font-size: 20px;
    line-height: 1.45;
    color: var(--ink);
    flex: 1;
    margin-bottom: 16px;
  }}
  .card-tap-hint {{
    font-family: 'DM Sans', system-ui, sans-serif;
    font-size: 12px;
    color: var(--text-muted);
    text-align: center;
    margin-top: auto;
    padding-top: 12px;
  }}
  .card-answer {{
    display: none;
    border-top: 1px solid var(--rule);
    padding-top: 16px;
    margin-top: 16px;
    font-size: 16px;
    line-height: 1.65;
    color: var(--text-body);
  }}
  .card-answer.visible {{ display: block; }}
  .temporal-hook {{
    margin-top: 12px;
    padding: 8px 12px;
    background: var(--parchment);
    border-left: 2px solid var(--rubric);
    font-size: 14px;
    color: var(--text-secondary);
    font-style: italic;
  }}
  .temporal-hook::before {{
    content: "✦ ";
    color: var(--rubric);
    font-style: normal;
  }}
  .self-assess {{
    display: none;
    margin-top: 20px;
    gap: 10px;
    justify-content: center;
  }}
  .self-assess.visible {{ display: flex; }}
  .assess-btn {{
    font-family: 'DM Sans', system-ui, sans-serif;
    font-size: 13px;
    padding: 8px 20px;
    border-radius: 3px;
    border: 1px solid var(--rule);
    background: var(--parchment);
    cursor: pointer;
    transition: all 0.15s;
    color: var(--ink);
  }}
  .assess-btn:hover {{ border-color: var(--rubric); color: var(--rubric); }}
  .assess-btn.knew {{ border-color: var(--claim-new); color: var(--claim-new); }}
  .assess-btn.partly {{ border-color: #c9a84c; color: #8a6a00; }}
  .assess-btn.missed {{ border-color: #cc4444; color: #cc4444; }}

  .summary-screen {{
    display: none;
    max-width: 640px;
    width: 100%;
  }}
  .summary-screen.visible {{ display: block; }}
  .summary-title {{
    font-size: 22px;
    margin-bottom: 8px;
    color: var(--ink);
  }}
  .summary-subtitle {{
    font-size: 15px;
    color: var(--text-secondary);
    margin-bottom: 24px;
  }}
  .summary-bars {{ margin-bottom: 28px; }}
  .summary-row {{
    display: grid;
    grid-template-columns: 120px 1fr 36px;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
    font-size: 13px;
    font-family: 'DM Sans', system-ui, sans-serif;
  }}
  .bar-outer {{
    height: 8px;
    background: var(--rule);
    border-radius: 4px;
    overflow: hidden;
  }}
  .bar-inner {{
    height: 8px;
    border-radius: 4px;
    transition: width 0.6s ease 0.2s;
  }}
  .summary-questions {{ margin-top: 20px; }}
  .summary-q {{
    padding: 10px 0;
    border-bottom: 1px solid var(--rule);
    font-size: 14px;
    display: grid;
    grid-template-columns: 24px 1fr;
    gap: 8px;
    align-items: start;
  }}
  .summary-q .icon {{ font-size: 16px; }}
  .restart-btn {{
    margin-top: 28px;
    font-family: 'DM Sans', system-ui, sans-serif;
    font-size: 13px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    padding: 10px 28px;
    border-radius: 3px;
    border: 1px solid var(--rubric);
    background: transparent;
    color: var(--rubric);
    cursor: pointer;
  }}
  .restart-btn:hover {{ background: var(--rubric); color: white; }}
</style>
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400;600&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
</head>
<body>
<div class="header">
  <div class="title">{book_title}</div>
  <div class="author">{author}</div>
  <div class="double-rule"></div>
  <div style="font-family:'DM Sans',sans-serif;font-size:13px;color:var(--text-secondary);">
    Retrieval quiz — {len(all_questions)} questions across {len(set(q['chapter_title'] for q in all_questions))} chapters
  </div>
</div>

<div class="progress-bar-outer">
  <div class="progress-bar-inner" id="progress-bar" style="width:0%"></div>
</div>
<div class="counter" id="counter">Question 1 of {len(all_questions)}</div>

<div class="card-container" id="card-container">
  <div class="card" id="card" onclick="revealAnswer()">
    <div class="card-chapter" id="card-chapter"></div>
    <div class="card-question" id="card-question"></div>
    <div class="card-tap-hint" id="tap-hint">Tap to reveal answer</div>
    <div class="card-answer" id="card-answer">
      <div id="answer-text"></div>
      <div class="temporal-hook" id="temporal-hook" style="display:none"></div>
    </div>
    <div class="self-assess" id="self-assess">
      <button class="assess-btn knew" onclick="score('knew', event)">✓ Knew it</button>
      <button class="assess-btn partly" onclick="score('partly', event)">~ Partly</button>
      <button class="assess-btn missed" onclick="score('missed', event)">✗ Missed it</button>
    </div>
  </div>
</div>

<div class="summary-screen" id="summary">
  <div class="summary-title">✦ Quiz complete</div>
  <div class="summary-subtitle" id="summary-subtitle"></div>
  <div class="summary-bars" id="summary-bars"></div>
  <div class="summary-questions" id="summary-questions"></div>
  <button class="restart-btn" onclick="restart()">Start over</button>
</div>

<script>
const CARDS = {cards_json};
const LENS_COLORS = {lens_colors_json};
const LENS_LABELS = {lens_labels_json};

let current = 0;
let revealed = false;
let scores = []; // 'knew'|'partly'|'missed'

function showCard(idx) {{
  const q = CARDS[idx];
  const [fg, bg] = LENS_COLORS[q.lens] || ['#666', '#f5f5f5'];
  const label = LENS_LABELS[q.lens] || q.lens;

  document.getElementById('card-chapter').innerHTML =
    `Chapter ${{q.chapter_number}}: ${{q.chapter_title}}&nbsp;&nbsp;<span class="lens-badge" style="color:${{fg}};background:${{bg}}">${{label}}</span>`;
  document.getElementById('card-question').textContent = q.question;
  document.getElementById('answer-text').textContent = q.answer;

  const hookEl = document.getElementById('temporal-hook');
  if (q.temporal_hook) {{
    hookEl.textContent = q.temporal_hook;
    hookEl.style.display = 'block';
  }} else {{
    hookEl.style.display = 'none';
  }}

  document.getElementById('card-answer').classList.remove('visible');
  document.getElementById('self-assess').classList.remove('visible');
  document.getElementById('tap-hint').style.display = 'block';
  revealed = false;

  const pct = Math.round(idx / CARDS.length * 100);
  document.getElementById('progress-bar').style.width = pct + '%';
  document.getElementById('counter').textContent = `Question ${{idx+1}} of ${{CARDS.length}}`;
}}

function revealAnswer() {{
  if (revealed) return;
  revealed = true;
  document.getElementById('card-answer').classList.add('visible');
  document.getElementById('self-assess').classList.add('visible');
  document.getElementById('tap-hint').style.display = 'none';
}}

function score(val, event) {{
  event.stopPropagation();
  scores.push({{ idx: current, val, q: CARDS[current] }});
  current++;
  if (current >= CARDS.length) {{
    showSummary();
  }} else {{
    showCard(current);
  }}
}}

function showSummary() {{
  document.getElementById('card-container').style.display = 'none';
  document.getElementById('counter').style.display = 'none';
  document.getElementById('progress-bar').style.width = '100%';

  const knew = scores.filter(s => s.val === 'knew').length;
  const partly = scores.filter(s => s.val === 'partly').length;
  const missed = scores.filter(s => s.val === 'missed').length;
  const total = scores.length;

  document.getElementById('summary-subtitle').textContent =
    `${{knew}} knew · ${{partly}} partly · ${{missed}} missed — out of ${{total}} questions`;

  const bars = [
    ['Knew it', knew, '#2a7a4a'],
    ['Partly', partly, '#c9a84c'],
    ['Missed', missed, '#cc4444'],
  ];
  document.getElementById('summary-bars').innerHTML = bars.map(([label, n, color]) => `
    <div class="summary-row">
      <span style="color:var(--text-secondary)">${{label}}</span>
      <div class="bar-outer"><div class="bar-inner" style="width:${{Math.round(n/total*100)}}%;background:${{color}}"></div></div>
      <span style="color:var(--text-muted)">${{n}}</span>
    </div>
  `).join('');

  const icons = {{ knew: '✓', partly: '~', missed: '✗' }};
  const colors = {{ knew: '#2a7a4a', partly: '#8a6a00', missed: '#cc4444' }};
  document.getElementById('summary-questions').innerHTML =
    '<div style="font-family:DM Sans,sans-serif;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--text-muted);margin-bottom:8px">All questions</div>' +
    scores.map(s => `
      <div class="summary-q">
        <span class="icon" style="color:${{colors[s.val]}}">${{icons[s.val]}}</span>
        <span style="color:var(--text-body)">${{s.q.question}}</span>
      </div>
    `).join('');

  document.getElementById('summary').classList.add('visible');
}}

function restart() {{
  scores = [];
  current = 0;
  document.getElementById('summary').classList.remove('visible');
  document.getElementById('card-container').style.display = 'block';
  document.getElementById('counter').style.display = 'block';
  showCard(0);
}}

showCard(0);
</script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="Generate retrieval quiz from EPUB")
    parser.add_argument("epub", help="Path to EPUB file (or glob pattern)")
    parser.add_argument("--chapters", help="Chapter range to include, e.g. 1-5 or 3,5,7")
    parser.add_argument("--questions-per-chapter", type=int, default=4)
    parser.add_argument("--output", default="quiz.html", help="Output HTML file")
    args = parser.parse_args()

    # Resolve glob
    epub_path = args.epub
    if not Path(epub_path).exists():
        matches = glob.glob(epub_path)
        if not matches:
            print(f"Error: no file found matching: {epub_path}", file=sys.stderr)
            sys.exit(1)
        epub_path = matches[0]

    print(f"Parsing: {Path(epub_path).name}")
    book_title, author, chapters = parse_epub_chapters(epub_path)
    print(f"Book: {book_title} by {author}")
    print(f"Chapters found: {len(chapters)}")
    for ch in chapters:
        print(f"  Ch {ch['number']:2d}: {ch['title'][:60]}  ({len(ch['text'])} chars)")

    # Filter chapters if requested
    if args.chapters:
        if '-' in args.chapters:
            lo, hi = map(int, args.chapters.split('-'))
            chapter_range = set(range(lo, hi + 1))
        else:
            chapter_range = set(map(int, args.chapters.split(',')))
        chapters = [ch for ch in chapters if ch['number'] in chapter_range]
        print(f"\nFiltered to {len(chapters)} chapters: {[ch['number'] for ch in chapters]}")

    print(f"\nGenerating questions ({args.questions_per_chapter} per chapter)...")
    all_questions = []
    for ch in chapters:
        qs = generate_questions_for_chapter(book_title, ch, n=args.questions_per_chapter)
        all_questions.extend(qs)
        print(f"    → {len(qs)} questions generated")

    if not all_questions:
        print("Error: no questions generated", file=sys.stderr)
        sys.exit(1)

    print(f"\nTotal: {len(all_questions)} questions across {len(chapters)} chapters")

    html = build_html(book_title, author, all_questions)

    output = Path(args.output)
    output.write_text(html, encoding="utf-8")
    print(f"\nQuiz saved → {output.resolve()}")
    print(f"Open with: open {output}")


if __name__ == "__main__":
    main()

"""Claude LLM wrapper using `claude -p` CLI (Max plan — free).

Primary LLM for all text generation. Falls back to Gemini only for
search-grounded and vision tasks.

Usage:
    from claude_llm import call_claude, call_claude_json

    # Free-form text
    answer = call_claude("Explain the Battle of Himera")

    # Structured JSON response
    data = call_claude_json("Extract key facts...", timeout=300)
"""

import json
import os
import re
import subprocess
import time


def call_claude(prompt: str, *, timeout: int = 180, retries: int = 1,
                model: str | None = None) -> str | None:
    """Call Claude via `claude -p`. Returns text or None on failure.

    Uses the Max plan subscription (free). Opus quality by default.
    Runs on both local dev and server (claude installed at /usr/bin/claude).

    Args:
        prompt: The prompt text
        timeout: Seconds before giving up (default 180 — Opus can be slow)
        retries: Number of retries on failure (default 1)
        model: Optional model override (e.g. 'sonnet' for faster responses)
    """
    cmd = ['claude', '-p', '--output-format', 'text']
    if model:
        cmd.extend(['--model', model])

    for attempt in range(1 + retries):
        try:
            result = subprocess.run(
                cmd, input=prompt, capture_output=True, text=True,
                timeout=timeout,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            if result.stderr:
                print(f'[claude] stderr (attempt {attempt+1}): {result.stderr[:200]}',
                      flush=True)
        except subprocess.TimeoutExpired:
            print(f'[claude] timeout after {timeout}s (attempt {attempt+1})', flush=True)
        except FileNotFoundError:
            print('[claude] CLI not found — is claude installed?', flush=True)
            return None

        if attempt < retries:
            time.sleep(2)

    return None


def call_claude_json(prompt: str, *, timeout: int = 180, retries: int = 1,
                     model: str | None = None) -> dict | list | None:
    """Call Claude and parse JSON from the response.

    Claude doesn't have a JSON-only output mode, so this:
    1. Appends "Output JSON only." if not already in the prompt
    2. Extracts JSON from the response (handles markdown fences, preamble text)
    3. Returns parsed dict/list or None on failure
    """
    # Nudge toward JSON if the prompt doesn't already ask for it
    if 'json' not in prompt.lower()[-100:]:
        prompt = prompt.rstrip() + '\n\nOutput JSON only.'

    raw = call_claude(prompt, timeout=timeout, retries=retries, model=model)
    if not raw:
        return None

    return extract_json(raw)


def extract_json(text: str) -> dict | list | None:
    """Extract JSON from text that may contain markdown fences or preamble."""
    cleaned = text.strip()

    # Strip markdown code fences
    if '```' in cleaned:
        # Find content between first ``` and last ```
        match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?\s*```', cleaned)
        if match:
            cleaned = match.group(1).strip()

    # Try parsing directly first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Find the largest JSON structure (array or object)
    for pattern in [r'\[[\s\S]*\]', r'\{[\s\S]*\}']:
        match = re.search(pattern, cleaned)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                # Try fixing trailing commas
                fixed = re.sub(r',\s*([}\]])', r'\1', match.group())
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    continue

    print(f'[claude] could not extract JSON from response ({len(text)} chars)',
          flush=True)
    return None


def call_claude_search(prompt: str, *, timeout: int = 180,
                       model: str | None = None) -> str | None:
    """Call Claude with web search enabled. Replaces Gemini's call_with_search."""
    cmd = ['claude', '-p', '--output-format', 'text',
           '--tools', 'WebSearch,WebFetch']
    if model:
        cmd.extend(['--model', model])

    try:
        result = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True,
            timeout=timeout,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        if result.stderr:
            print(f'[claude-search] stderr: {result.stderr[:200]}', flush=True)
    except subprocess.TimeoutExpired:
        print(f'[claude-search] timeout after {timeout}s', flush=True)
    except FileNotFoundError:
        print('[claude-search] CLI not found', flush=True)
    return None


def call_claude_or_gemini(prompt: str, *, timeout: int = 180,
                          json_mode: bool = False,
                          model: str | None = None) -> str | dict | list | None:
    """Try Claude first, fall back to Gemini if Claude fails.

    For the transition period — gradually remove Gemini fallbacks as
    Claude proves reliable for each use case.
    """
    if json_mode:
        result = call_claude_json(prompt, timeout=timeout, model=model)
        if result is not None:
            return result
    else:
        result = call_claude(prompt, timeout=timeout, model=model)
        if result is not None:
            return result

    # Fallback to Gemini
    print('[claude] falling back to Gemini', flush=True)
    try:
        from gemini_llm import call_llm
        kwargs = {'max_tokens': 4096}
        if json_mode:
            kwargs['response_mime_type'] = 'application/json'
        raw = call_llm(prompt, **kwargs)
        if raw and json_mode:
            return extract_json(raw)
        return raw
    except Exception as e:
        print(f'[claude] Gemini fallback also failed: {e}', flush=True)
        return None

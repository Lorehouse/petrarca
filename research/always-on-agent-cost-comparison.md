# Always-On Personal Agent: Architecture & Cost Comparison

**Date**: 2026-03-15
**Goal**: Compare legitimate, ToS-compliant approaches to building a personal always-on agent on a Hetzner VM with Telegram interface and cross-project codebase access.

---

## Approach Summary

| # | Architecture | Monthly Cost (est.) | Latency | Custom Code | ToS Status |
|---|-------------|--------------------:|---------|-------------|------------|
| 1 | Pure `claude -p` wrapper | $0 (Max plan) | 3-15s | Low | **Gray area** |
| 2 | Claude Agent SDK + API keys | $30-150 | 2-10s | Medium | **Fully blessed** |
| 3 | Gemini Flash quick + `claude -p` heavy | $1-5 | 1-3s / 5-15s | Medium | **Clean** |
| 4 | Hybrid: Gemini + Haiku + `claude -p` | $15-40 | 1-15s | Medium-High | **Clean** |
| 5 | OpenRouter multi-model | $30-150 | 2-10s | Medium | **Clean** |
| 6 | Local model triage + cloud fallback | $0-30 | 0.5-3s / 5-15s | High | **Clean** |
| 7 | Claude Code as long-lived session | N/A | N/A | N/A | **Not viable** |

---

## 1. Pure `claude -p` Wrapper

A Python service receives Telegram messages and spawns `claude -p` for each request.

### How It Works
```python
import subprocess, json

result = subprocess.run(
    ["claude", "-p", prompt,
     "--output-format", "json",
     "--max-turns", "3",
     "--model", "sonnet",
     "--allowedTools", "Read", "Grep", "Glob", "Bash"],
    capture_output=True, text=True, timeout=120,
    cwd="/Users/stian/src/petrarca"
)
response = json.loads(result.stdout)
```

### Key CLI Flags Available
- `--output-format json` -- structured output for parsing
- `--max-turns N` -- limit agentic turns (cost control)
- `--max-budget-usd N` -- hard dollar cap per invocation
- `--model sonnet|opus|haiku` -- per-request model selection
- `--allowedTools "Read,Grep,Glob"` -- restrict tool access
- `--dangerously-skip-permissions` -- no interactive prompts (for sandboxed use)
- `--system-prompt "..."` -- custom system prompt per request
- `--add-dir ../alif ../otak` -- cross-project access
- `--no-session-persistence` -- don't save sessions to disk

### ToS Analysis
**This is the critical question.** The consumer ToS (governing Max plan) says:

> "Except when you are accessing our Services via an Anthropic API Key or where we otherwise **explicitly permit** it, [you may not] access the Services through automated or non-human means, whether through a bot, script, or otherwise."

Claude Code's `-p` flag is explicitly designed for scripted, automated use ("useful for pipes"). The documentation shows examples like `tail -f app.log | claude -p "Slack me if you see any anomalies"` and CI/CD automation. Anthropic also explicitly supports GitHub Actions integration and the Slack bot integration -- both automated, non-human access.

**However**, the documentation says Claude Code requires "a Claude subscription or Anthropic Console account." The `-p` flag docs link to the Agent SDK for "programmatic usage details." The Agent SDK docs explicitly state: "Unless previously approved, Anthropic does not allow third party developers to offer claude.ai login or rate limits for their products, including agents built on the Claude Agent SDK. Please use the API key authentication methods described in this document instead."

**Assessment: Gray area for personal use, not allowed for products.**
- Using `claude -p` in your own scripts/workflows: almost certainly fine (it's what `-p` is for)
- Wrapping it in a Telegram bot for personal use only: probably fine in practice, but the consumer ToS technically prohibits "bots" and "scripts" accessing the service
- Building a product/service around it: explicitly not allowed without approval
- The Max plan has usage caps (not unlimited), so heavy automated use could hit limits
- **Risk**: Anthropic could restrict automated access patterns in the future

### Cost
$0 beyond existing Max subscription ($100/month or $200/month for the Max tier you're already paying for).

### Latency
- Cold start: 3-8 seconds (spawning claude process, loading CLAUDE.md)
- With `--max-turns 1` (no tool use): 3-5 seconds
- With tool use (file reads, grep): 8-15 seconds
- No way to keep a warm process between requests

### Pros
- Zero additional cost
- Full Claude Code capabilities (file access, grep, edit, bash)
- CLAUDE.md project context loaded automatically
- Can use `--add-dir` for cross-project awareness
- Structured JSON output for easy parsing
- Budget caps available (`--max-budget-usd`)

### Cons
- Cold start on every request (no persistent connection)
- ToS gray area for automated/bot usage
- Max plan has usage limits (may throttle under heavy use)
- Cannot maintain conversation state across requests (each `-p` is a fresh session, though `--continue` exists)
- Process spawning overhead adds latency

---

## 2. Claude Agent SDK with API Keys

The officially blessed way to build custom agents. Uses `ANTHROPIC_API_KEY` (pay-per-token).

### How It Works
```python
from claude_agent_sdk import query, ClaudeAgentOptions

async def handle_message(prompt: str):
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Grep", "Glob", "Bash"],
            permission_mode="bypassPermissions",
            model="claude-haiku-4-5"  # cheap for triage
        ),
    ):
        if hasattr(message, "result"):
            return message.result
```

### Current API Pricing (March 2026)

| Model | Input/MTok | Output/MTok | Cache Hit | Batch Input | Batch Output |
|-------|-----------|-------------|-----------|-------------|--------------|
| Claude Opus 4.6 | $5.00 | $25.00 | $0.50 | $2.50 | $12.50 |
| Claude Sonnet 4.6 | $3.00 | $15.00 | $0.30 | $1.50 | $7.50 |
| Claude Haiku 4.5 | $1.00 | $5.00 | $0.10 | $0.50 | $2.50 |

### Cost Estimates (50-100 queries/day)

Assumptions: average query = 2K input tokens + 1K output tokens (quick Q&A), with 10% of queries being "heavy" (8K input + 4K output).

**All Haiku (100 queries/day):**
- Quick: 90 queries x (2K x $1 + 1K x $5) / 1M = $0.00063/query = $0.057/day
- Heavy: 10 queries x (8K x $1 + 4K x $5) / 1M = $0.028/query = $0.28/day
- **Monthly: ~$10**

**Haiku triage + Sonnet for medium (70/20/10 split):**
- 70 Haiku quick: $0.040/day
- 20 Sonnet medium: 20 x (4K x $3 + 2K x $15) / 1M = $0.012 + $0.060 = $0.072/query x 20 = $1.44/day
- 10 Opus heavy: 10 x (8K x $5 + 4K x $25) / 1M = $0.14/query x 10 = $1.40/day
- **Monthly: ~$60-90**

**All Sonnet (100 queries/day):**
- Average: 100 x (3K x $3 + 1.5K x $15) / 1M = $0.0315/query
- **Monthly: ~$95**

**All Opus (100 queries/day):**
- Average: 100 x (3K x $5 + 1.5K x $25) / 1M = $0.0525/query
- **Monthly: ~$160**

**With prompt caching** (reuse cross-project context): cache hits are 10% of input price. If you cache a 10K-token system prompt with project context:
- 10K cached tokens x $0.10/MTok = $0.001/query (Haiku) vs $0.01 uncached
- Saves ~50% on input costs for repeated queries

### ToS
**Fully within ToS.** The Agent SDK docs explicitly say to use API keys. The commercial ToS governs API usage and permits building products and services on top of Claude. No restrictions on bots, scripts, or automated usage via the API.

### Latency
- First token: 1-3 seconds (Haiku), 2-5 seconds (Sonnet), 3-8 seconds (Opus)
- Full response (short answer): 2-5 seconds (Haiku), 3-8 seconds (Sonnet)
- With tool use: add 2-5 seconds per tool call
- **No cold start** -- the SDK runs within your process

### Pros
- Officially supported, no ToS concerns
- Full programmatic control (hooks, subagents, sessions, MCP)
- Session persistence and resumption across requests
- Model selection per request (Haiku for quick, Opus for complex)
- Prompt caching reduces costs for repeated context
- Subagents with different models (Haiku for exploration, Sonnet for edits)
- Same built-in tools as Claude Code (Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch)
- Can run on Hetzner VM with no issues

### Cons
- Pay-per-token costs ($10-160/month depending on model mix)
- Claude-only (cannot route to Gemini, GPT, etc.)
- Still requires Claude Code CLI to be installed (SDK wraps it internally)
- Need to manage API key securely on server

---

## 3. Gemini Flash (Quick) + `claude -p` (Heavy)

Use Gemini 2.5 Flash for rapid Q&A, triage, and routing. Fall back to `claude -p` only for code changes and deep research.

### How It Works
```python
# Telegram bot handler
async def handle_message(text: str):
    # Step 1: Gemini Flash classifies the request
    classification = await gemini_classify(text)  # uses existing gemini_llm.py

    if classification["tier"] == "quick":
        # Gemini handles directly -- fast, cheap
        return await gemini_answer(text, context=project_summaries)
    elif classification["tier"] == "code":
        # Claude Code for file operations
        return await run_claude_p(text, cwd=classification["project"])
    elif classification["tier"] == "research":
        # Claude Code with web search
        return await run_claude_p(text, tools=["WebSearch", "WebFetch", "Read"])
```

### Gemini 2.5 Flash Pricing

| Tier | Input/MTok | Output/MTok | Notes |
|------|-----------|-------------|-------|
| Free | $0 | $0 | 500 RPD, 15 RPM |
| Paid | $0.30 | $2.50 | 2000 RPM |
| Flash-Lite (paid) | $0.10 | $0.40 | Fastest, cheapest |

### Cost Estimates (100 queries/day)

**80% Gemini Flash + 20% claude -p:**
- 80 Gemini Flash queries: 80 x (2K x $0.30 + 1K x $2.50) / 1M = $0.000248/query = $0.60/day
- 20 `claude -p` queries: $0 (Max plan)
- **Monthly: ~$18 (paid Gemini) or $0 (free tier, within 500 RPD limit)**

**Using Gemini free tier:** If your 80 quick queries/day fit within 500 RPD (they do), and you stay under 15 RPM, you can run the entire Gemini layer **for free**.

**Monthly cost: $0-18** (Gemini) + $0 (Max plan for claude -p)

### Existing Infrastructure
You already have `gemini_llm.py` with `call_llm()`, `call_chat()`, `call_with_search()`, `call_vision()`, and `call_llm_tool()`. The default model is `gemini-3.1-flash-lite-preview`. You have a working Gemini API key on the server.

### ToS
- **Gemini API**: Fully within ToS. Google explicitly supports automated API usage.
- **`claude -p`**: Same gray area as Approach 1, but significantly reduced exposure since it's only used for 20% of requests.
- **Practical risk**: Very low. You're using `claude -p` exactly as designed (piped automation), just less frequently.

### Latency
- Gemini Flash quick answer: 1-3 seconds
- Gemini Flash-Lite: 0.5-1.5 seconds
- `claude -p` code work: 5-15 seconds (cold start + tool use)

### Pros
- Near-zero cost if Gemini free tier suffices
- Very fast for quick answers (Gemini Flash is extremely low-latency)
- Leverages existing Gemini infrastructure
- `claude -p` only when you genuinely need Claude Code capabilities
- Gemini has web search grounding built in (500 free/day)

### Cons
- Two separate systems to maintain
- Gemini quality lower than Claude for nuanced questions
- Routing logic needs tuning (which queries go where?)
- `claude -p` still has ToS gray area
- No unified conversation history across Gemini and Claude

---

## 4. Hybrid: Gemini Flash + Claude API Haiku + `claude -p`

Three-tier cost optimization with clean separation of concerns.

### Architecture
```
Telegram message
    ↓
[Gemini Flash-Lite: classify + route]  ← $0.10/MTok in, $0.40/MTok out
    ↓
┌──────────────────────────────────────────┐
│ Tier 1 (60%): Gemini 2.5 Flash          │ Quick Q&A, summaries, lookups
│ Tier 2 (30%): Claude Haiku 4.5 (API)    │ Code review, analysis, medium tasks
│ Tier 3 (10%): claude -p Sonnet/Opus     │ Multi-file edits, deep research
└──────────────────────────────────────────┘
```

### Cost Estimate (100 queries/day)

| Tier | Queries/day | Model | Cost/query | Daily | Monthly |
|------|------------|-------|-----------|-------|---------|
| Router | 100 | Gemini Flash-Lite | $0.0001 | $0.01 | $0.30 |
| Tier 1 | 60 | Gemini 2.5 Flash | $0.003 | $0.18 | $5.40 |
| Tier 2 | 30 | Claude Haiku 4.5 | $0.007 | $0.21 | $6.30 |
| Tier 3 | 10 | claude -p (Max) | $0 | $0 | $0 |
| **Total** | | | | **$0.40** | **~$12** |

Using Gemini free tier for Tier 1 and routing: **~$6/month** (just the Haiku API costs).

### ToS
- Gemini API: Fully clean
- Claude Haiku API: Fully clean (API key, commercial ToS)
- `claude -p`: Gray area, but only 10% of traffic (10 queries/day)

### Pros
- Very cost-effective (~$6-12/month)
- Best quality for each task tier
- Clean ToS for 90% of queries
- Gemini for speed, Haiku for Claude-quality analysis, `claude -p` for heavy lifting
- Prompt caching on Haiku reduces costs further

### Cons
- Three systems to integrate and maintain
- Routing logic complexity
- Three different response formats/quality levels
- No unified conversation state

---

## 5. OpenRouter Multi-Model

### How It Works
OpenRouter provides a single API endpoint that routes to multiple model providers. You pay the same per-token price as going direct (no inference markup), plus a small fee on credit purchases.

```python
import openai  # OpenRouter uses OpenAI-compatible API

client = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="sk-or-..."
)

response = client.chat.completions.create(
    model="anthropic/claude-haiku-4-5",  # or any model
    messages=[{"role": "user", "content": prompt}]
)
```

### Pricing
OpenRouter passes through provider pricing with **no markup on inference**. Fees are only on credit purchases (via Stripe). This means:
- Claude Haiku 4.5: $1/MTok in, $5/MTok out (same as direct)
- Claude Sonnet 4.6: $3/MTok in, $15/MTok out (same as direct)
- Claude Opus 4.6: $5/MTok in, $25/MTok out (same as direct)
- Plus Stripe processing fee on credit top-ups

### Advantages Over Direct API
- Single API key for all providers (Anthropic, OpenAI, Google, Mistral, etc.)
- Automatic fallback if a provider is down
- Model routing based on task (you choose per-request)
- OpenAI-compatible SDK (works with existing OpenAI client code)
- No need to manage multiple API keys

### Cost Estimate
Same as Approach 2, since pricing is pass-through. The main advantage is operational simplicity, not cost savings.

### ToS
Fully clean. You're using API keys and paying per token.

### Pros
- Single API for everything
- Can mix Claude + Gemini + GPT + open-source models
- Automatic provider fallback
- Easy to A/B test models
- OpenAI-compatible SDK (massive ecosystem support)

### Cons
- **No built-in tools** (no file access, bash, grep). You must implement all tool use yourself or use a framework like LangChain
- Stripe fee on credit purchases
- Adds a network hop (slightly higher latency)
- No prompt caching (or limited -- depends on provider)
- You lose Claude Agent SDK's built-in agentic capabilities
- Essentially just a chat API -- you'd need to build the agent loop yourself

### Verdict
OpenRouter is good for chat-style Q&A but **not** for an agent that needs file system access and code execution. For that, you'd still need Claude Agent SDK or `claude -p`. OpenRouter could serve as the "quick answer" tier in a hybrid architecture.

---

## 6. Local Models (Ollama)

Run a small model locally on the Hetzner VM for triage, routing, and quick answers.

### Recommended Models for Hetzner VM

Assuming your Hetzner VM has ~16-32 GB RAM and no GPU:

| Model | Size | RAM Needed | Speed (CPU) | Quality | Best For |
|-------|------|-----------|-------------|---------|---------|
| Qwen 2.5 3B | 3B | 4 GB | ~20 tok/s | Good for size | Triage, routing, simple Q&A |
| Phi-4 3.8B | 3.8B | 5 GB | ~15 tok/s | Excellent for size | Routing, classification, quick answers |
| Gemma 3 4B | 4B | 5 GB | ~12 tok/s | Good multilingual | Routing with multilingual input |
| Llama 3.2 3B | 3B | 4 GB | ~20 tok/s | Good general | General routing |
| Qwen 2.5 7B | 7B | 8 GB | ~8 tok/s | Strong | Complex routing, medium Q&A |
| Mistral 7B | 7B | 8 GB | ~8 tok/s | Strong coding | Code-related triage |

### How It Works
```python
import ollama

# Fast local classification (no network latency, no cost)
response = ollama.chat(
    model="qwen2.5:3b",
    messages=[{
        "role": "user",
        "content": f"Classify this request: {text}\n\nCategories: quick_answer, code_task, research, project_question"
    }]
)
tier = parse_classification(response["message"]["content"])
```

### Cost
**$0** -- runs on existing Hetzner VM. No API costs.

### Performance on CPU
- 3B model: generates ~20 tokens/second on modern CPU (no GPU needed)
- 7B model: generates ~8 tokens/second on CPU
- For classification/routing (short outputs): response in 0.5-2 seconds
- For full answers (longer outputs): 5-20 seconds (too slow for primary use)

### Realistic Use Case
Local models work best as a **router/classifier**, not as the primary answering model. Use it to:
1. Classify incoming messages (quick/medium/heavy)
2. Extract project name from query ("fix the bug in petrarca" -> cwd=/Users/stian/src/petrarca)
3. Generate embeddings for semantic routing
4. Handle truly trivial queries ("what time is it?", "remind me later")

Fall back to Gemini Flash or Claude API for actual answers.

### Memory/Resource Requirements
- Ollama daemon: ~100 MB base memory
- 3B model loaded: ~4 GB RAM
- 7B model loaded: ~8 GB RAM
- Models are loaded/unloaded on demand (configurable keep-alive)
- CPU usage: spikes during inference, idle otherwise
- Disk: 2-5 GB per model

### ToS
**Fully clean.** These are open-source models running on your own hardware.

### Pros
- Zero cost
- Zero latency for classification (local, no network)
- No privacy concerns (all local)
- Good enough for routing/classification
- Can run alongside everything else on the VM

### Cons
- Too slow for primary use on CPU (need GPU for 7B+ models to be responsive)
- Quality significantly below Claude/Gemini for nuanced answers
- Need to download and manage models
- Uses VM RAM that could go to other services
- Extra complexity in the stack

---

## 7. Claude Code as Long-Lived Session

Could the always-on agent BE a persistent Claude Code session?

### Analysis
Claude Code sessions are designed for interactive development work, not as long-running daemons.

**What hooks could do:**
- `SessionStart` hook: inject cross-project context, set environment variables
- `Stop` hook: write memories, send notifications
- `PreToolUse` / `PostToolUse`: audit logging, security validation
- Custom skills: define reusable workflows like `/check-projects`, `/daily-summary`

**What doesn't work:**
- Claude Code sessions are request-response, not persistent daemons
- There's no way to send a new message to an existing Claude Code session from an external process (except Remote Control, which is designed for human use via claude.ai)
- Sessions time out and don't listen for external events
- `-p` mode processes one prompt and exits
- Interactive mode requires a terminal with stdin/stdout
- No webhook/HTTP endpoint to push messages to a running session

**Remote Control?** Claude Code has a Remote Control feature (`claude remote-control`) that creates a server, but it's designed for controlling from claude.ai or the Claude app, not from a Telegram bot.

### Verdict
**Not viable as a daemon.** Claude Code is a tool, not a service. The correct pattern is to build a service (Python/FastAPI) that spawns Claude Code (via Agent SDK or `claude -p`) on demand. This is exactly what Approaches 1-4 describe.

---

## Recommended Architecture

Based on all the research, the best approach for your specific situation is:

### **Approach 3+6 Hybrid: Local Router + Gemini Flash + Claude Agent SDK**

```
┌─────────────────┐
│  Telegram Bot    │  python-telegram-bot (async)
│  (always-on)     │  receives text + voice messages
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Router          │  Local Qwen 3B or Gemini Flash-Lite
│  (classify)      │  → quick / medium / heavy / project?
└────────┬────────┘
         │
    ┌────┼────┐
    ▼    ▼    ▼
┌──────┐┌──────┐┌─────────────────┐
│Gemini││Claude ││ Claude Agent SDK│
│Flash ││Haiku  ││ (Sonnet/Opus)   │
│(Q&A) ││(API)  ││ full tool access │
│ 60%  ││ 25%   ││      15%        │
└──────┘└──────┘└─────────────────┘
```

### Why This Combination

1. **Gemini Flash for quick answers (60%)**: You already have `gemini_llm.py`. The free tier gives you 500 queries/day. Sub-second latency. Handles: "what's the status of X?", "explain this concept", "translate this", summaries.

2. **Claude Haiku 4.5 via API for medium tasks (25%)**: Fully ToS-compliant. $1/$5 per MTok. Handles: code review, analysis, "what does this function do?", "find all TODOs in petrarca". Cost: ~$5/month.

3. **Claude Agent SDK with Sonnet for heavy work (15%)**: Full file access, multi-file edits, deep research. Handles: "fix this bug", "add a new endpoint", "research X and write a summary". Cost: ~$15/month. **This is the officially blessed approach.**

4. **Local model for routing** (optional): Qwen 3B on the VM for zero-latency classification. Or just use Gemini Flash-Lite for routing ($0.10/MTok, effectively free at this volume).

### Estimated Monthly Cost
- Router: $0 (local or Gemini free tier)
- Gemini Flash (60 queries/day): $0 (free tier) to $5 (paid tier)
- Claude Haiku API (25 queries/day): ~$5
- Claude Agent SDK Sonnet (15 queries/day): ~$15
- **Total: $5-25/month**

### What You Need to Build

1. **Telegram bot** (~100 lines): Use `python-telegram-bot`. Handle text and voice messages. Voice -> Soniox transcription (already built). Restrict to your user ID.

2. **Router** (~50 lines): Classify incoming messages into tiers. Can be rule-based initially (contains "fix"/"edit"/"change" -> heavy; contains "what is"/"explain" -> quick; etc.), upgraded to LLM-based later.

3. **Gemini handler** (~30 lines): Already exists in `gemini_llm.py`. Add a system prompt with cross-project context summaries.

4. **Claude handler** (~80 lines): Use Claude Agent SDK's `query()` function. Set `allowed_tools`, `permission_mode="bypassPermissions"`, and `cwd` per project.

5. **Project context** (~50 lines): Load CLAUDE.md from each project, maintain a summary index. Inject relevant context into the system prompt based on the detected project.

6. **Conversation memory** (~50 lines): Simple JSON/SQLite store of recent messages for continuity. Not full session management -- just enough context for follow-up questions.

**Total: ~360 lines of Python.** All running as a single `systemd` service on the Hetzner VM.

### Cross-Project Awareness

The agent can access 10+ codebases by:
- Reading each project's `CLAUDE.md` at startup for context
- Using `--add-dir` (for `claude -p`) or setting `cwd` (for Agent SDK) to the relevant project
- Maintaining a project index: `{name: path, summary: "...", keywords: [...]}`
- Router detects project from query ("in petrarca, ..." / "alif bug" / etc.)

### Key Decision: Agent SDK vs `claude -p`

For the heavy tier, prefer the **Claude Agent SDK** over `claude -p`:
- **Agent SDK** uses API keys (fully ToS-compliant), gives you programmatic control, session persistence, hooks, subagents, and runs within your process (no cold start)
- **`claude -p`** uses Max plan tokens (ToS gray area), has cold start overhead, but gives you CLAUDE.md auto-loading and the full Claude Code experience

You can start with `claude -p` for rapid prototyping, then migrate the heavy tier to Claude Agent SDK when you want clean ToS compliance. The routing layer stays the same.

---

## Appendix: Pricing Reference

### Claude API (March 2026)

| Model | Input | Output | Cache Hit | Batch (50% off) |
|-------|-------|--------|-----------|------------------|
| Opus 4.6 | $5/MTok | $25/MTok | $0.50/MTok | $2.50/$12.50 |
| Sonnet 4.6 | $3/MTok | $15/MTok | $0.30/MTok | $1.50/$7.50 |
| Haiku 4.5 | $1/MTok | $5/MTok | $0.10/MTok | $0.50/$2.50 |

### Gemini API (March 2026)

| Model | Input | Output | Free Tier |
|-------|-------|--------|-----------|
| Gemini 2.5 Flash | $0.30/MTok | $2.50/MTok | 500 RPD, 15 RPM |
| Gemini 2.5 Flash-Lite | $0.10/MTok | $0.40/MTok | 500 RPD |
| Gemini 2.5 Pro | $1.25/MTok | $10.00/MTok | Free (limited) |

### OpenRouter
Pass-through pricing (no inference markup). Stripe fee on credit purchases only.

### Local Models (Ollama, free)
Qwen 2.5 3B (4 GB RAM), Phi-4 3.8B (5 GB), Llama 3.2 3B (4 GB), Mistral 7B (8 GB).

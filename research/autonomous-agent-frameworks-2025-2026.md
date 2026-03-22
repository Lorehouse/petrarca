# Autonomous AI Coding/Agent Frameworks: Comprehensive Comparison (2025-2026)

Research date: March 15, 2026

## Executive Summary

This document surveys the landscape of open-source and semi-open AI coding and agent frameworks that could serve as an always-running autonomous agent on a Linux VM. The evaluation focuses on daemon/service capabilities, LLM provider flexibility, persistent memory, filesystem/command access, API/webhook triggers, security, and multi-agent orchestration.

**Key finding:** The Claude Agent SDK (Python/TypeScript) is the strongest option for building a custom always-running agent backed by Claude. It provides the same tools as Claude Code (Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch) as a library, with full programmatic control. For a more turnkey solution, OpenHands offers a mature headless mode with Docker sandboxing and multi-provider LLM support.

---

## 1. Claude Agent SDK

**Repository:** `anthropics/claude-agent-sdk-python`, `anthropics/claude-agent-sdk-typescript`
**Stars:** ~3k (Python SDK repo) | **License:** Commercial ToS | **Status:** Actively maintained (v1.68+ as of March 2026)

The Claude Agent SDK (formerly "Claude Code SDK") gives you the same tools, agent loop, and context management that power Claude Code, programmable in Python and TypeScript. It is the official way to build custom agents on Claude.

### Architecture
- Python package (`pip install claude-agent-sdk`) and TypeScript (`npm install @anthropic-ai/claude-agent-sdk`)
- Bundles the Claude Code CLI internally; the SDK wraps it with a programmatic interface
- Core function: `query(prompt, options)` returns an async iterator of messages
- Also provides `ClaudeSDKClient` for bidirectional, multi-turn conversations

### Can it run as a long-running daemon?
**Yes, with wrapper.** The SDK itself is a library, not a daemon. You wrap it in a FastAPI/Flask service, a cron job, or any long-running Python/TS process. Example:

```python
from fastapi import FastAPI
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

app = FastAPI()

@app.post("/task")
async def handle_task(prompt: str):
    async with ClaudeSDKClient(options=ClaudeAgentOptions(
        allowed_tools=["Read", "Edit", "Bash"],
        permission_mode="bypassPermissions"
    )) as client:
        await client.query(prompt)
        results = []
        async for msg in client.receive_response():
            results.append(msg)
        return {"response": results}
```

### LLM Provider Support
- Anthropic API (primary)
- Amazon Bedrock (`CLAUDE_CODE_USE_BEDROCK=1`)
- Google Vertex AI (`CLAUDE_CODE_USE_VERTEX=1`)
- Microsoft Azure Foundry (`CLAUDE_CODE_USE_FOUNDRY=1`)
- **Claude-only** -- cannot use GPT, Gemini, etc.

### Persistent Memory
- Session management: capture `session_id` from init message, resume with `options.resume = session_id`
- Sessions persist on disk by default (can disable with `no_session_persistence`)
- CLAUDE.md files are read automatically at session start
- Subagents can have persistent memory directories (`user`, `project`, `local` scopes)
- No built-in cross-process memory database; you'd implement that in your wrapper

### Filesystem & Command Access
Full access via built-in tools: Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch

### API/Webhook Triggers
Not built-in. You build the trigger layer (HTTP endpoints, message queues, cron, GitHub webhooks) and call the SDK.

### Security Model
- Fine-grained permission rules: allow/ask/deny per tool, with glob patterns
- Permission modes: `default`, `acceptEdits`, `plan`, `dontAsk`, `bypassPermissions`
- Sandboxing for Bash commands (OS-level filesystem/network isolation)
- Hook system for pre/post tool use validation
- MCP server scoping per subagent

### Sub-agents
- Full subagent support: define custom agents with specialized prompts, tool restrictions, and model selection
- Subagents can use Haiku, Sonnet, or Opus independently
- Agent Teams (experimental): multiple Claude Code instances coordinating via shared task lists and messaging
- Subagents cannot spawn further subagents (one level of nesting)

### Verdict
**Best choice if you're committed to Claude.** The SDK gives you everything Claude Code can do, as a library. You'd wrap it in a simple Python service on your Hetzner VM. The main limitation is Claude-only (no multi-provider support).

---

## 2. Claude Code CLI (`claude -p`)

**Repository:** `anthropics/claude-code` | **Stars:** 78.1k | **License:** Proprietary | **Status:** Very active

### Programmatic / Headless Usage
`claude -p "prompt"` runs a query non-interactively and exits. This is the CLI equivalent of the Agent SDK. Key flags:

| Flag | Purpose |
|------|---------|
| `claude -p "query"` | Run single query, print result, exit |
| `--output-format json/stream-json` | Structured output |
| `--json-schema '{...}'` | Validated structured output |
| `--allowedTools "Read,Edit,Bash"` | Auto-approve tools |
| `--dangerously-skip-permissions` | Skip all permission prompts |
| `--max-turns N` | Limit agentic turns |
| `--max-budget-usd N` | Cost cap |
| `--continue` / `--resume ID` | Continue previous session |
| `--model sonnet/opus` | Select model |
| `--fallback-model` | Auto-fallback on overload |
| `--system-prompt` | Replace system prompt |
| `--append-system-prompt` | Add to system prompt |
| `--agents '{json}'` | Define subagents inline |

### Can it run as a backend engine?
**Yes.** You can spawn `claude -p` from a wrapper script/service, pass prompts, get JSON output back. The `--output-format stream-json` flag enables real-time streaming. Session IDs enable multi-turn conversations. The Agent SDK is the more robust version of this pattern.

### Claude Code on the Web
Claude Code can also run as a cloud service at `claude.ai/code`:
- Runs in isolated Anthropic-managed VMs
- Can be kicked off from terminal with `--remote`
- Long-running tasks that persist even if you close your laptop
- Can run multiple tasks in parallel
- Available on iOS/Android apps
- Sessions can be teleported back to local terminal

### Claude Max Usage Limits
Claude Code works with Pro, Max, Teams, and Enterprise subscriptions, or with API keys. For Max subscribers:
- Usage is included in subscription (no per-token billing)
- Rate limits are shared across all Claude usage
- No explicit prohibition on programmatic `claude -p` usage with Max subscription
- The Agent SDK documentation states: "Unless previously approved, Anthropic does not allow third party developers to offer claude.ai login or rate limits for their products"
- This means you can use `claude -p` yourself, but cannot build a product that authenticates via claude.ai for others
- For sustained automated usage, API keys with per-token billing give more predictable capacity

### Verdict
**Practical for personal automation.** Spawning `claude -p` from a cron job or webhook handler on your VM works well. For more control, use the Agent SDK directly.

---

## 3. OpenHands (formerly OpenDevin)

**Repository:** `All-Hands-AI/OpenHands` | **Stars:** 69.1k | **License:** MIT | **Status:** Very active

### Architecture
- Python-based with Docker sandboxing for code execution
- Multiple interfaces: CLI, local GUI (React + FastAPI REST API), cloud (app.all-hands.dev)
- Agent SDK as a composable Python library

### Can it run as a daemon/service?
**Yes.** Multiple modes:
- **Headless mode**: `openhands --headless -t "task"` -- runs without UI, always-approve mode, JSON output
- **REST API**: FastAPI server with endpoints for chat and task management
- **Docker deployment**: designed for containerized operation
- Suitable for CI/CD pipelines, automated scripting, batch processing

### LLM Provider Support
**Broad.** Claude, GPT-4, Gemini, local models, and "any other LLM" via configurable providers.

### Persistent Memory
Not explicitly documented in the core architecture. Tasks appear to be stateless per invocation.

### Filesystem & Command Access
Full access within Docker sandbox. Agent can install packages, run tests, edit files.

### API/Webhook Triggers
REST API available. Integrations with Slack, Jira, Linear in cloud version.

### Security Model
- Docker container sandboxing (strong isolation)
- Network access controls
- Headless mode always runs in auto-approve (no human-in-the-loop)

### Sub-agents
Not explicitly documented. Single-agent architecture per task.

### Verdict
**Strong option for multi-provider, sandboxed agent.** The Docker sandboxing is more robust than most alternatives. Headless mode with REST API makes it easy to run as a service. Multi-LLM support is a significant advantage.

---

## 4. SWE-agent (Princeton/Stanford)

**Repository:** `SWE-agent/SWE-agent` | **Stars:** 18.7k | **License:** MIT | **Status:** Active (NeurIPS 2024)

### Architecture
- Python-based, configurable via YAML
- Takes GitHub issues and attempts automatic fixes
- Two versions: original SWE-agent and simplified mini-SWE-agent

### Daemon/Service Capability
**No.** Designed as a CLI tool for one-shot issue resolution. No built-in daemon or API mode.

### LLM Support
GPT-4o, Claude Sonnet 4, and others. Achieved SoTA on SWE-Bench with Claude 3.7.

### Persistent Memory
None. Stateless per execution.

### Security
Docker containerization. MIT licensed.

### Verdict
**Research tool, not a production daemon.** Excellent for benchmarking and one-shot bug fixing, but not designed for always-on operation. Would require significant wrapping to use as a service.

---

## 5. Aider

**Repository:** `Aider-AI/aider` | **Stars:** 42k | **License:** Apache 2.0 | **Status:** Very active (v0.86+, 5.3M PyPI installs)

### Architecture
- Terminal-based AI pair programming tool in Python
- Git-native: auto-commits with generated messages
- Repo-map for codebase understanding

### Daemon/Service Capability
**Limited.** Primarily interactive. Has `--message` flag for single-shot non-interactive use, and watch mode for IDE integration. No built-in API server or daemon mode.

### LLM Support
**Excellent.** Claude 3.7 Sonnet, DeepSeek R1/Chat V3, OpenAI o1/o3/GPT-4o, local models, "almost any LLM."

### Persistent Memory
Codebase maps persist context. Chat history within session. No cross-session memory database.

### Filesystem & Command Access
Full filesystem access in project directory. Can run lint/test commands.

### Verdict
**Best multi-LLM pair programmer, but not daemon-friendly.** You could wrap `aider --message "task"` in a service, but it's not designed for it. No API, no webhook support.

---

## 6. Open Interpreter

**Repository:** `OpenInterpreter/open-interpreter` | **Stars:** 62.7k | **License:** AGPL-3.0 | **Status:** Active

### Architecture
- Natural language interface to computer
- Executes code (Python, JavaScript, shell) via `exec()`
- Streams output as Markdown

### Daemon/Service Capability
**Yes.** Has `interpreter.server()` providing FastAPI HTTP endpoints. Can also be called programmatically via `interpreter.chat(message)`.

### LLM Support
**Excellent.** Via LiteLLM: OpenAI, Claude, local models (LM Studio, Ollama, Llamafile), Azure, and more.

### Persistent Memory
Conversation history in `interpreter.messages`, can be saved/restored programmatically.

### Filesystem & Command Access
Full local system access. Can create/edit files, run shell commands, control browsers.

### Security
User approval before code execution (can be disabled with `auto_run = True`). No sandboxing by default.

### Verdict
**Versatile but risky without sandboxing.** The built-in FastAPI server makes it easy to run as a service. Multi-LLM via LiteLLM. But the AGPL license and lack of sandboxing are concerns for production use.

---

## 7. Cline (formerly Claude Dev)

**Repository:** `cline/cline` | **Stars:** 59k | **License:** Apache 2.0 | **Status:** Very active

### Architecture
VS Code extension with TypeScript/JavaScript core. Uses VS Code terminal and file system APIs.

### Daemon/Service Capability
**No.** Requires VS Code. Cannot run headless. Enterprise version may offer server deployment, but the open-source version is VS Code-only.

### LLM Support
OpenRouter, Anthropic, OpenAI, Google Gemini, AWS Bedrock, Azure, GCP Vertex, Cerebras, Groq, local models via LM Studio/Ollama.

### Unique Features
- MCP server creation/installation
- Browser automation via Computer Use
- Checkpoint/restore system
- Human-in-the-loop GUI

### Verdict
**Not suitable for headless daemon.** Excellent VS Code extension but architecturally tied to the editor. Cannot run on a Linux VM without a desktop environment.

---

## 8. Goose (Block/Square)

**Repository:** `block/goose` | **Stars:** 33k | **License:** Apache 2.0 | **Status:** Very active (v1.27+, 123 releases)

### Architecture
Written primarily in Rust (58.5%) with TypeScript (33.5%). Available as desktop app and CLI.

### Daemon/Service Capability
**Partially.** CLI mode works, but no explicit daemon or API server documented. MCP integration for external tool access.

### LLM Support
"Works with any LLM." Multi-model configuration for optimizing performance and cost.

### Unique Features
- MCP server integration (seamless)
- Sub-agent support (feature flags reference `copilot_swe_agent_use_subagents`)
- Custom distributions with preconfigured providers
- Rust-based (fast, low memory)

### Security
Apache 2.0. Responsible AI coding guide. Security policy documented.

### Verdict
**Promising but lacking daemon infrastructure.** The Rust core makes it fast and efficient. MCP integration is strong. But no built-in API server or webhook handler for automated triggering.

---

## 9. Sweep AI

**Repository:** `sweepai/sweep` | **Stars:** 7.6k | **License:** Mixed | **Status:** Pivot to JetBrains plugin

### Architecture
Originally a GitHub bot that auto-fixes issues. Has pivoted to a JetBrains plugin.

### Daemon/Service Capability
**Originally yes** (GitHub App/webhook-triggered), now focused on IDE plugin.

### Verdict
**Not recommended.** The project has pivoted away from the autonomous agent model. The original GitHub bot architecture is no longer the focus.

---

## 10. AutoCodeRover

**Repository:** `nus-apr/auto-code-rover` | **Stars:** 3.1k | **License:** GPL-3.0 | **Status:** Active (research)

### Architecture
Two-stage: (1) AST-aware context retrieval, (2) patch generation. Runs via Docker or conda.

### Daemon/Service Capability
**No.** CLI tool for one-shot issue fixing. No API or daemon mode.

### LLM Support
OpenAI, Anthropic Claude, Meta Llama 3, AWS Bedrock, Groq, LiteLLM.

### Verdict
**Research tool only.** Excellent SWE-Bench scores (46.2%) but not designed for production daemon use.

---

## 11. Mentat (AbanteAI)

**Repository:** `AbanteAI/mentat` | **Stars:** ~3k | **License:** Apache 2.0 | **Status:** Appears unmaintained (404 on repo)

### Verdict
**Likely abandoned.** Repository returned 404. Not recommended.

---

## 12. GPT-Engineer

**Repository:** `gpt-engineer-org/gpt-engineer` | **Stars:** 55.2k | **License:** MIT | **Status:** Maintenance mode

### Architecture
CLI-based code generation. Generates entire codebases from prompts.

### Daemon/Service Capability
**No.** CLI-only. No API, no daemon mode.

### LLM Support
Primarily OpenAI (GPT-4). Some Anthropic support.

### Verdict
**Historical significance, not for daemon use.** "The OG code generation platform." Last stable release June 2024. The commercial variant (gptengineer.app) has evolved separately.

---

## 13. Smol Developer

**Repository:** `smol-ai/developer` | **Stars:** 12.2k | **License:** MIT | **Status:** Minimal maintenance

### Architecture
Multi-step synthesis: plan -> file list -> code generation. CLI, library, and Agent Protocol API modes.

### Daemon/Service Capability
**Partially** via Agent Protocol mode, but limited.

### LLM Support
GPT-4 (primary), GPT-3.5, some Claude support.

### Verdict
**Proof of concept, not production-ready.** Interesting ideas but not actively maintained.

---

## 14. Bolt.new / Lovable

### Bolt.new
**Repository:** `stackblitz/bolt.new` | **Stars:** 16.3k | **License:** MIT | **Status:** Active (beta)

Entirely browser-based. AI gets full control over filesystem, node server, package manager, terminal within WebContainers. Cannot run on a Linux VM as a daemon -- it's a web IDE.

### Lovable
Repository returned 404. Web-based AI app builder (lovable.dev). Not open-source in a way that can be self-hosted.

### Verdict
**Not applicable.** Both are web-based development platforms, not frameworks for building autonomous agents on a VM.

---

## 15. Computer Use Agents (Claude)

**Repository:** `anthropics/anthropic-quickstarts/computer-use-demo` | **Status:** Beta

### Architecture
Docker container with VNC desktop. Claude controls mouse, keyboard, screenshots. Supports Claude API, Bedrock, Vertex.

### Daemon/Service Capability
**Partially.** Runs as a Docker container. Single-session, must be restarted between tasks. Not designed for continuous operation.

### Security
Significant risks: prompt injection via web content, credential exposure. Must use in isolated VM/container.

### Verdict
**Specialized for GUI automation, not general coding.** Useful for browser testing or desktop automation tasks, but too heavyweight and risky for general autonomous coding. Better to use Claude Code's built-in Chrome integration for web automation.

---

## 16. Multi-Agent Orchestration Frameworks

### CrewAI
**Repository:** `crewAIInc/crewAI` | **Stars:** 46.1k | **License:** MIT | **Status:** Very active

- **Architecture:** Autonomous agent teams ("Crews") + event-driven workflows ("Flows")
- **Daemon:** No built-in daemon. Discrete workflow execution via `crewai run` or programmatic invocation
- **LLM:** Multi-provider via environment variables
- **Memory:** Pydantic BaseModel state in Flows; no built-in persistent storage
- **Sub-agents:** Yes -- Crews contain multiple collaborative agents
- **Verdict:** Good for orchestrating multi-agent workflows, but you'd need to build the daemon/trigger layer yourself. More suited to business process automation than coding tasks.

### AutoGen (Microsoft)
**Repository:** `microsoft/autogen` | **Stars:** 55.6k | **License:** MIT | **Status:** Active

- **Architecture:** Layered -- Core (event-driven agents), AgentChat (rapid prototyping), Extensions
- **Daemon:** No explicit daemon mode. Task-based execution
- **LLM:** OpenAI, Azure, others via Extensions
- **Memory:** Not documented
- **Sub-agents:** Yes via AgentTool (agents calling other agents)
- **Unique:** Magentic-One application for web browsing, code execution, file handling
- **Verdict:** Strong multi-agent framework but lacks daemon infrastructure and filesystem tools. Better for research and prototyping than production autonomous agents.

### LangGraph (LangChain)
**Repository:** `langchain-ai/langgraph` | **Stars:** 26.4k | **License:** MIT | **Status:** Very active (v0.4.17+)

- **Architecture:** Graph-based orchestration with StateGraph pattern. Nodes connected by edges
- **Daemon:** Not natively. Wrap in FastAPI or deploy via LangSmith
- **LLM:** Provider-agnostic via LangChain (OpenAI, Gemini, Claude, etc.)
- **Memory:** **Best-in-class.** Short-term working memory + long-term persistent memory across sessions. Checkpointing for state persistence and failure recovery
- **Sub-agents:** Subgraph patterns and node composition
- **Deployment:** Standalone, LangSmith platform, LangGraph Studio, custom web framework
- **Verdict:** Most mature orchestration framework with excellent persistence. If you want to build a complex multi-step agent with memory, LangGraph + a custom tool layer is a strong choice. But you'd need to implement filesystem/command tools yourself.

---

## 17. Pydantic AI

**Repository:** `pydantic/pydantic-ai` | **Stars:** 15.5k | **License:** MIT | **Status:** Very active (v1.68+, 405 contributors)

### Architecture
Python agent framework by the Pydantic team. Type-safe dependency injection, structured outputs with Pydantic validation.

### Daemon/Service Capability
**No built-in daemon.** But designed to be embedded in Python services.

### LLM Support
**Excellent.** "Virtually every model and provider": OpenAI, Anthropic, Gemini, DeepSeek, Grok, Cohere, Mistral, Ollama, LiteLLM, Bedrock, Vertex, Groq, OpenRouter, and many more.

### Unique Features
- Durable execution: preserves progress across API failures and restarts
- Human-in-the-loop tool approval
- MCP integration
- Agent2Agent (A2A) for inter-agent communication
- Evals framework
- OpenTelemetry integration via Pydantic Logfire

### Verdict
**Excellent foundation for building custom agents.** Type-safe, multi-provider, with durable execution. You'd pair it with your own tool implementations (file editing, command execution) to build an autonomous coding agent. The durable execution feature is particularly valuable for long-running daemon scenarios.

---

## Comparison Matrix

| Framework | Daemon-Ready | Multi-LLM | Memory | FS/Cmd Access | API Trigger | Sub-agents | Security | Stars |
|-----------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Claude Agent SDK** | Wrap | Claude-only | Sessions | Full (built-in) | Build | Yes | Excellent | ~3k |
| **Claude Code CLI** | Wrap | Claude-only | Sessions | Full (built-in) | Build | Yes | Excellent | 78k |
| **OpenHands** | Yes | Yes | No | Docker sandbox | REST API | No | Docker | 69k |
| **SWE-agent** | No | Yes | No | Docker | No | No | Docker | 19k |
| **Aider** | Wrap | Excellent | Repo map | Project dir | No | No | None | 42k |
| **Open Interpreter** | Yes | Excellent | Save/restore | Full (risky) | FastAPI | No | Minimal | 63k |
| **Cline** | No (VS Code) | Excellent | Checkpoints | Via VS Code | No | No | HITL | 59k |
| **Goose** | Partial | Yes | No | Yes | No | Partial | Apache | 33k |
| **CrewAI** | Wrap | Yes | Flows state | Tool-based | Build | Yes | Basic | 46k |
| **AutoGen** | No | Yes | No | Magentic-One | No | Yes | Basic | 56k |
| **LangGraph** | Wrap | Yes | Excellent | Build tools | Build | Subgraphs | Basic | 26k |
| **Pydantic AI** | Wrap | Excellent | Durable exec | Build tools | Build | A2A | Type-safe | 16k |
| **Computer Use** | Partial | Claude-only | No | Desktop | No | No | Risky | N/A |

Legend: "Wrap" = no built-in daemon but easily wrapped in a service. "Build" = you implement the trigger/tool layer.

---

## Recommendations for Your Use Case

You want an always-running autonomous agent on your Hetzner VM that can:
- Monitor for triggers (webhooks, cron, messages)
- Access the filesystem, run commands, deploy code
- Maintain memory across sessions
- Work with Claude (since you have Max plan)

### Option A: Claude Agent SDK + Custom Service (Recommended)

Build a small Python service that:
1. Runs on your Hetzner VM as a systemd service
2. Exposes a simple HTTP API for triggering tasks
3. Uses the Claude Agent SDK for all agent work
4. Stores task history and memory in SQLite or filesystem

```
[Triggers]          [Your Service]        [Claude Agent SDK]
  Webhook  ------>   FastAPI/Flask  ---->   query(prompt, options)
  Cron     ------>   Task queue     ---->   Built-in tools (Read, Write, Edit, Bash...)
  Email    ------>   Session mgmt   ---->   Sub-agents, MCP servers
```

**Pros:** Full Claude Code capabilities, sub-agents, MCP, hooks, strong security model, official support
**Cons:** Claude-only, requires API key (Max plan for subscription or API key for pay-per-token)

### Option B: OpenHands Headless

Deploy OpenHands in Docker on your VM:
1. Run in headless mode for automated tasks
2. Use the REST API for triggering
3. Multi-LLM support (Claude + GPT fallback)
4. Docker sandboxing for security

**Pros:** Multi-LLM, Docker sandboxing, REST API out of the box
**Cons:** Less mature tooling than Claude Code, no persistent memory, no sub-agents

### Option C: Custom Agent with Pydantic AI + LangGraph

Build a more sophisticated agent using:
1. Pydantic AI for the agent framework (multi-LLM, type-safe, durable execution)
2. LangGraph for orchestration and persistent memory/checkpointing
3. Custom tools for filesystem access and command execution

**Pros:** Multi-LLM, excellent persistence, most flexible
**Cons:** Most work to build, no built-in coding tools (must implement file editing, etc.)

### Claude Max Limits for Programmatic Use

Key points about using Claude Max for daemon-style operation:
- Claude Code with Max subscription works in `-p` mode and with the Agent SDK
- Rate limits are shared across all Claude usage on your account
- There is no explicit prohibition on personal programmatic use
- However, Anthropic does not allow third parties to build products that use claude.ai authentication
- For heavy automated usage, API keys (Console) give more predictable capacity and avoid sharing rate limits with your interactive Claude use
- Average Claude Code cost is ~$6/developer/day on API billing
- The `/stats` command shows usage patterns for subscribers

### Using Claude Code as a "Backend Engine"

Yes, this is fully supported. Two approaches:

1. **CLI wrapping**: Spawn `claude -p "task" --output-format json --allowedTools "Read,Edit,Bash" --dangerously-skip-permissions` from any process. Parse JSON output. Use `--resume SESSION_ID` for multi-turn.

2. **Agent SDK** (preferred): Use the Python/TypeScript SDK directly in your service code. Benefits over CLI wrapping:
   - Native async/await
   - Streaming with callbacks
   - In-process MCP servers (no subprocess overhead)
   - Hook callbacks as Python functions (not shell scripts)
   - Type-safe structured outputs
   - Session management via API

Both approaches work with Claude Max subscription or API keys.

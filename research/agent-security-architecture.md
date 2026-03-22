# Security Architecture for Autonomous AI Agent on Production VM

**Date**: March 15, 2026
**Context**: Petrarca runs on a Hetzner VM (via `ssh alif`) with multiple codebases, a 4-hour cron pipeline, a research server (port 8090), a log server (port 8091), and Expo/web deployments. The goal is to add an autonomous AI agent that can perform development tasks, run the pipeline, and deploy code — safely.

---

## 1. Sandboxing and Isolation

### Current State (Problems)

The existing `petrarca-research.service` runs as `User=root` with no filesystem or network restrictions. The cron pipeline (`content-refresh.sh`) sources `/opt/petrarca/.env` (containing `GEMINI_KEY`, `ANTHROPIC_KEY`) and runs with full filesystem access. Any agent added to this environment inherits all these privileges.

### Recommended Isolation Layers (from lightest to heaviest)

#### Layer 1: Systemd Hardening (immediate, no extra infra)

Systemd provides production-grade sandboxing with zero infrastructure overhead. Apply to all existing services (`petrarca-research`, `petrarca-expo`, cron jobs) and any new agent service:

```ini
[Service]
# Never run as root
User=petrarca
Group=petrarca

# Filesystem isolation
ProtectSystem=strict          # Entire FS read-only except /dev, /proc, /sys
ProtectHome=yes               # /home, /root, /run/user inaccessible
PrivateTmp=yes                # Isolated /tmp per service
ReadWritePaths=/opt/petrarca/data /opt/petrarca/research-results
ReadOnlyPaths=/opt/petrarca/scripts /opt/petrarca/app

# Privilege restrictions
NoNewPrivileges=yes           # Cannot gain privileges via setuid/setgid
PrivateDevices=yes            # No access to physical devices
ProtectKernelTunables=yes     # Cannot modify /proc/sys, /sys
ProtectKernelModules=yes      # Cannot load kernel modules
ProtectControlGroups=yes      # Cannot modify cgroups
RestrictSUIDSGID=yes          # Cannot create setuid/setgid files

# Network restrictions (optional, per service)
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
IPAddressAllow=any            # Or restrict to specific CIDRs

# System call filtering
SystemCallFilter=@system-service
SystemCallArchitectures=native
```

This alone eliminates the largest risks: the agent cannot read SSH keys, modify system binaries, load kernel modules, or escape its data directory.

#### Layer 2: Bubblewrap (for agent command execution)

This is what Claude Code uses on Linux via Anthropic's open-source [`sandbox-runtime`](https://github.com/anthropic-experimental/sandbox-runtime). It wraps individual commands in a bubblewrap sandbox with:

- **Filesystem**: deny-then-allow pattern. Allowlisted read directories take precedence over denylists; denylisted write directories take precedence over allowlists.
- **Network**: All traffic routed through HTTP/SOCKS5 proxy that filters by domain allowlist. Network namespace is removed from the bwrap container, so there is no way to bypass the proxy.
- **Violation detection**: Blocked operations are logged with details about what was attempted.

For the Petrarca agent, use bubblewrap to sandbox every shell command the agent executes:

```bash
# Example: agent runs a python script
bwrap \
  --ro-bind / / \
  --bind /opt/petrarca/data /opt/petrarca/data \
  --tmpfs /tmp \
  --unshare-net \
  --dev /dev \
  --proc /proc \
  -- python3 /opt/petrarca/scripts/build_articles.py --limit 5
```

#### Layer 3: Docker (for full task isolation)

Use Docker containers for tasks that need more complex environments (e.g., npm builds, Expo exports). Each agent task gets an ephemeral container:

```dockerfile
FROM python:3.12-slim
COPY scripts/ /app/scripts/
COPY data/ /app/data/
# No .env baked in — secrets injected at runtime via --env-file
WORKDIR /app
```

Run with strict limits:
```bash
docker run --rm \
  --read-only \
  --tmpfs /tmp \
  --memory=2g \
  --cpus=1 \
  --network=none \        # No network by default
  --security-opt=no-new-privileges \
  -v /opt/petrarca/data:/app/data \
  petrarca-agent python3 scripts/build_articles.py
```

#### Layer 4: Firecracker microVMs (for maximum isolation, future)

Firecracker boots a full VM in ~125ms with <5 MiB overhead. Each agent task runs in a dedicated microVM with its own kernel. This is what AWS Lambda and Fly.io use. It's the strongest isolation boundary available, but adds operational complexity (TAP interfaces, IP tables, rootfs images).

Recommended only if the agent starts executing arbitrary code from external sources (e.g., running code from ingested articles, or third-party MCP servers).

Tools to simplify Firecracker management:
- [vmsan](https://github.com/angelorc/vmsan) — one-command microVM from CLI
- [BunkerVM](https://github.com/AshishChoudhary/bunkervm) — Firecracker wrapper for AI agents

### How Claude Code Sandboxes Bash Commands

Claude Code uses Anthropic's `sandbox-runtime` package, which:
1. On **macOS**: Uses `sandbox-exec` with dynamically generated Seatbelt profiles
2. On **Linux**: Uses `bubblewrap` for filesystem isolation with network namespace removal
3. **Network**: Runs HTTP + SOCKS5 proxy servers on the host; all sandboxed traffic must go through these proxies, which enforce domain allowlists
4. **Result**: 84% reduction in permission prompts while maintaining security — a compromised Claude Code cannot steal SSH keys or exfiltrate data

### Recommendation for Petrarca

**Start with Layer 1 + Layer 2.** Systemd hardening is free and covers all existing services. Bubblewrap (via `sandbox-runtime` or direct `bwrap` calls) covers agent-executed commands. Docker is useful for build tasks. Firecracker is overkill for a single-user system until the agent starts running untrusted code.

---

## 2. Permission Model

### Principle of Least Privilege for the Agent

Define three permission tiers:

| Tier | Access | Examples |
|------|--------|----------|
| **Read-only** | Can read code, data, logs. Cannot modify anything. | Investigating bugs, reading logs, answering questions about the codebase |
| **Development** | Can modify code in working branches, run tests, build. Cannot deploy or modify production data. | Feature development, fixing bugs, running the pipeline locally |
| **Deploy** | Can push to remote, restart services, copy files to production paths. | Deploying web, restarting research server, running content-refresh |

The agent should operate at the **Development** tier by default and require explicit human approval to escalate to **Deploy**.

### File System Access Control

```
READ-ONLY:
  /opt/petrarca/scripts/       # Pipeline code
  /opt/petrarca/app/           # App code
  /opt/petrarca/.env           # NEVER — use systemd EnvironmentFile instead
  ~/.ssh/                      # NEVER

READ-WRITE:
  /opt/petrarca/data/          # Pipeline output (articles, embeddings, etc.)
  /opt/petrarca/research-results/
  /opt/petrarca/data/logs/     # Interaction logs
  /tmp/petrarca-agent/         # Scratch space

DENIED:
  /etc/                        # System config
  /root/                       # Root home
  /home/                       # User homes (ProtectHome=yes)
  /opt/petrarca/.env           # Secrets file
```

### Network Access Control

Use an egress allowlist (via bubblewrap proxy or Docker network policies):

```
ALLOWED OUTBOUND:
  generativelanguage.googleapis.com   # Gemini API
  api.anthropic.com                    # Anthropic API
  api.soniox.com                       # Voice transcription
  api.github.com / github.com         # Git operations
  readwise.io / api.readwise.io       # Readwise sync
  openlibrary.org                      # Book covers

DENIED:
  Everything else (especially: metadata services 169.254.169.254,
  internal network ranges, arbitrary domains)
```

### Deploy Permissions — How to Gate Deployments

Deployments should never be automatic. Use a human-approval gate:

1. Agent prepares the deployment (builds, runs checks)
2. Agent posts a summary to a notification channel (Telegram bot, email, or a simple webhook)
3. Human reviews and sends an approval token
4. Agent executes the deployment only with a valid, time-limited approval token

Implementation:
```python
# Agent requests deployment approval
approval_id = request_approval(
    action="deploy-web",
    summary="Built web export, 0 TypeScript errors, bundle size 2.1MB",
    ttl_minutes=30
)
# Human gets notification, clicks approve link
# Agent polls for approval
if check_approval(approval_id):
    execute_deploy()
```

---

## 3. Authentication and Authorization

### Authenticating the User Talking to the Agent

For a single-user system, keep it simple:

1. **SSH-based**: If communicating via SSH, the SSH key is the authentication. The agent only accepts commands from authenticated SSH sessions.
2. **Shared secret**: For HTTP-based communication (e.g., a webhook), use a pre-shared bearer token stored outside the agent's readable filesystem.
3. **mTLS**: For production multi-service setups, mutual TLS between services. Overkill for single-user but worth noting.

### API Key Management

**Current problem**: `/opt/petrarca/.env` contains all keys and is sourced directly by scripts. If the agent can read this file, it has all the keys.

**Solution**: Use systemd's `EnvironmentFile` or `LoadCredential`:

```ini
[Service]
# Option A: EnvironmentFile (simple)
EnvironmentFile=/etc/petrarca/secrets.env
# File owned by root:petrarca, mode 0640

# Option B: LoadCredential (more secure, systemd 250+)
LoadCredential=GEMINI_KEY:/etc/petrarca/credentials/gemini_key
# Accessible only via $CREDENTIALS_DIRECTORY/GEMINI_KEY at runtime
```

With `LoadCredential`, the secret is mounted read-only at a path known only to the service at runtime. The agent cannot access it from the filesystem — it is only available via the `$CREDENTIALS_DIRECTORY` environment variable within the service.

### SSH Key Management for Deployments

The agent should **not** have access to your personal SSH key. Instead:

1. Create a dedicated deploy key per repository (read-only by default)
2. For push access, create a separate deploy key with write access, stored in a location only accessible during approved deploy operations
3. Use `ssh-agent` forwarding only for interactive sessions, never for autonomous agents
4. Consider GitHub deploy tokens (fine-grained PATs) with repository-scoped, time-limited permissions

### Token Rotation

- **LLM API keys**: Rotate every 90 days. Use key versioning so the old key works during transition.
- **GitHub PATs**: Use fine-grained tokens with 30-day expiry. Automate rotation via GitHub API.
- **Deploy SSH keys**: Rotate every 6 months. Use `authorized_keys` with `from=` restrictions to limit source IPs.

---

## 4. Audit and Monitoring

### Logging All Agent Actions

Every agent action must produce an immutable log entry. Use the existing Petrarca logging pattern (`interactions_YYYY-MM-DD.jsonl`) extended with agent-specific fields:

```json
{
  "ts": "2026-03-15T14:30:00Z",
  "source": "agent",
  "action": "bash_exec",
  "command": "python3 scripts/build_articles.py --limit 5",
  "sandbox": "bubblewrap",
  "exit_code": 0,
  "duration_ms": 12340,
  "files_modified": ["data/articles.json"],
  "approval_id": null,
  "session_id": "agent-abc123"
}
```

Store agent logs separately from application logs:
```
/opt/petrarca/data/logs/agent_YYYY-MM-DD.jsonl    # Agent actions
/opt/petrarca/data/logs/interactions_YYYY-MM-DD.jsonl  # App interactions (existing)
/opt/petrarca/data/logs/pipeline_YYYY-MM-DD.jsonl  # Pipeline runs (existing)
```

### Alerting on Destructive Operations

Define a "destructive operations" allowlist and alert on anything outside it:

```python
DESTRUCTIVE_OPS = [
    "git push", "git reset", "git rebase",
    "rm -rf", "rm -r",
    "systemctl restart", "systemctl stop",
    "scp", "rsync",
    "docker rm", "docker rmi",
    "DROP TABLE", "DELETE FROM",
]

# Before executing any command:
if any(op in command for op in DESTRUCTIVE_OPS):
    send_alert(f"Agent wants to execute: {command}")
    require_approval()
```

### Cost Monitoring

Track all LLM API calls (the existing `llm_audit.py` pattern):

```json
{
  "ts": "2026-03-15T14:30:00Z",
  "model": "gemini-3.1-flash-lite-preview",
  "input_tokens": 1200,
  "output_tokens": 450,
  "cost_usd": 0.0003,
  "cache_hit": true,
  "caller": "agent:build_articles"
}
```

Set daily/weekly budgets with hard stops:
- Pipeline runs: ~$0.50/day (Gemini Flash Lite)
- Agent tasks: budget $5/day, hard stop at $10/day
- Alert at 80% of daily budget

### Git Commit Attribution

Use a dedicated bot identity for agent commits:

```bash
# In agent's git config (per-repo, not global)
git config user.name "Petrarca Agent"
git config user.email "agent@petrarca.local"

# Every commit includes Co-Authored-By for traceability
git commit -m "$(cat <<'EOF'
Fix article validation edge case

Co-Authored-By: Petrarca Agent <agent@petrarca.local>
Approved-By: stian
EOF
)"
```

Use `git log --author="Petrarca Agent"` to find all agent commits. Require GPG signing for human commits to clearly distinguish human vs. agent work.

---

## 5. Architecture Patterns

### Recommended: Supervisor + Worker with Message Queue

```
┌─────────────────────────────────────────────────┐
│                   Hetzner VM                     │
│                                                  │
│  ┌──────────────┐     ┌──────────────────────┐  │
│  │  Supervisor   │     │   Redis (queue +     │  │
│  │  (systemd)    │────▶│   state store)       │  │
│  │               │     └──────────────────────┘  │
│  │  - accepts    │              │                 │
│  │    tasks      │     ┌────────┴────────┐       │
│  │  - validates  │     │                 │       │
│  │  - approves   │  ┌──┴───┐        ┌───┴──┐    │
│  │  - monitors   │  │Worker│        │Worker│    │
│  └──────────────┘  │(bwrap)│        │(bwrap)│    │
│                     │      │        │      │    │
│                     └──────┘        └──────┘    │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │  Existing Services                          │  │
│  │  - petrarca-research (8090)                 │  │
│  │  - petrarca-expo (8082)                     │  │
│  │  - nginx (8083, 8084)                       │  │
│  │  - log-server (8091)                        │  │
│  │  - content-refresh (cron)                   │  │
│  └────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

#### Components

**Supervisor process** (Python, runs as systemd service):
- Accepts tasks via HTTP API or Redis pubsub
- Validates task parameters against allowlists
- Manages approval workflow for destructive operations
- Spawns worker processes in bubblewrap sandboxes
- Monitors worker health, enforces timeouts
- Writes all actions to audit log

**Redis** (task queue + state):
- Task queue: pending → running → completed/failed
- Agent state: current task, conversation history, file modifications
- Pub/sub for real-time notifications

**Worker processes** (bubblewrap-sandboxed):
- Each task gets a fresh sandbox
- Read-only access to code, read-write to designated output dirs
- Network filtered through proxy
- Killed after timeout (default: 30 minutes, max: 4 hours for pipeline)

#### Systemd Service for the Agent Supervisor

```ini
[Unit]
Description=Petrarca Agent Supervisor
After=network.target redis.service
Requires=redis.service

[Service]
Type=simple
User=petrarca
Group=petrarca
WorkingDirectory=/opt/petrarca
ExecStart=/opt/petrarca/.venv/bin/python3 /opt/petrarca/scripts/agent-supervisor.py
Restart=always
RestartSec=10
WatchdogSec=60

# Systemd hardening
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
NoNewPrivileges=yes
PrivateDevices=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ReadWritePaths=/opt/petrarca/data /opt/petrarca/research-results /tmp/petrarca-agent
ReadOnlyPaths=/opt/petrarca/scripts /opt/petrarca/app

# Secrets
EnvironmentFile=/etc/petrarca/secrets.env

# Resource limits
MemoryMax=4G
CPUQuota=200%
TasksMax=64

[Install]
WantedBy=multi-user.target
```

### Handling Long-Running Tasks

For tasks that can run for hours (full pipeline rebuild, large batch processing):

1. **Durable execution**: Save task state to Redis on every significant step. If the worker crashes, the supervisor can resume from the last checkpoint.
2. **Heartbeat monitoring**: Workers send heartbeats every 30 seconds. If 3 heartbeats are missed, the supervisor kills the worker and marks the task as failed.
3. **Progress reporting**: Workers write structured progress to Redis (`task:{id}:progress`), which the supervisor exposes via API.
4. **Graceful shutdown**: On SIGTERM, workers finish their current step, save state, and exit. The supervisor waits up to 60 seconds before SIGKILL.

---

## 6. How Existing Systems Handle This

### Devin (Cognition)

- Runs in a **sandboxed cloud container** with shell, editor, and browser
- **Two mandatory human checkpoints**: planning approval (before coding) and PR review (before merge)
- GitHub token cannot approve its own PRs, delete branches, or modify repo settings
- Network isolation: mock/staging endpoints instead of production APIs
- Treats all agent output as "external contractor" level of trust

### OpenAI Codex

- Each task runs in an **isolated cloud container** with no internet access by default
- Pre-installed dependencies configured via setup script; no runtime package installation
- Uses `seccomp` + `landlock` on Linux for syscall filtering
- Agent limited to editing files in its assigned folder/branch
- Recent updates allow optional internet access, but it's off by default

### GitHub Actions

- **GitHub-hosted runners**: Ephemeral VMs, destroyed after each job. Strong isolation.
- **Self-hosted runners**: Persistent machines — a known attack vector (the Shai-Hulud worm in Nov 2025 demonstrated installing rogue runners on compromised machines)
- **Harden-Runner** (StepSecurity): EDR-like agent that monitors network egress, file integrity, and process activity on runners in real-time
- **GitHub Agentic Workflows** (Feb 2026 preview): Read-only by default, sandboxed execution, network isolation, SHA-pinned dependencies

### Key Lessons

1. **Default to no network access** — allow specific endpoints only when needed
2. **Human approval for production actions** — every system that works well requires this
3. **Ephemeral environments** — destroy the sandbox after each task to prevent state leakage
4. **Treat agent output like untrusted contractor code** — review everything

---

## 7. Backup and Recovery

### What If the Agent Breaks Something?

The Replit incident (July 2025) is the cautionary tale: an AI agent ran unauthorized commands during a "code and action freeze," panicked in response to empty queries, and violated explicit instructions not to proceed without approval. Their database was wiped.

### Git-Based Recovery

```bash
# Branch protection rules (set on GitHub)
# - Require PR reviews for main
# - No force pushes to main
# - Require status checks to pass
# - No branch deletion for main

# Agent works on feature branches only
git checkout -b sh/agent/task-description

# If agent breaks a branch, recovery is trivial:
git checkout main
git branch -D sh/agent/broken-branch

# For data files, use git-lfs or versioned copies:
cp data/articles.json data/articles.json.backup-$(date +%Y%m%d%H%M)
```

### Snapshot/Rollback Strategy

For the Hetzner VM:

1. **Hetzner snapshots**: Take a VM snapshot before any major agent operation (automated via Hetzner API). Snapshots cost ~EUR 0.01/GB/month.
2. **Data directory versioning**: Before each pipeline run, create a timestamped copy of critical data files.
3. **Database backups**: If/when a database is introduced, automated backups before any agent write operation.

```bash
# Pre-task snapshot (called by supervisor before destructive tasks)
snapshot_data() {
    local backup_dir="/opt/petrarca/backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    cp data/articles.json "$backup_dir/"
    cp data/knowledge_index.json "$backup_dir/"
    cp data/manifest.json "$backup_dir/"
    # Keep last 10 backups
    ls -dt /opt/petrarca/backups/*/ | tail -n +11 | xargs rm -rf
}
```

### Human Approval Gates

Define three categories:

| Category | Approval Required | Example |
|----------|-------------------|---------|
| **Safe** | None | Read files, run analysis, generate reports, create branches |
| **Cautious** | Async notification (proceed unless vetoed in 5 min) | Modify data files, commit to feature branch, run pipeline steps |
| **Critical** | Explicit approval required | Deploy to production, push to remote, restart services, modify system config |

### Kill Switch

A simple, reliable kill switch:

```bash
# /opt/petrarca/scripts/agent-kill.sh
#!/bin/bash
# Immediately stop all agent activity
systemctl stop petrarca-agent
# Revoke agent's deploy permissions
rm -f /etc/petrarca/agent-deploy-token
# Drain Redis task queue
redis-cli DEL agent:tasks agent:state
echo "Agent stopped. All pending tasks cancelled."
```

Make this executable only by the human user (not the agent):
```bash
chown root:root /opt/petrarca/scripts/agent-kill.sh
chmod 700 /opt/petrarca/scripts/agent-kill.sh
```

---

## 8. Cost Optimization

### Claude Max vs API — When to Use Which

| Scenario | Recommendation | Rationale |
|----------|---------------|-----------|
| Interactive development (you're at keyboard) | **Claude Max ($100-200/mo)** | Unlimited use, no per-token cost, built-in sandbox |
| Autonomous background tasks | **API (Claude Haiku/Sonnet)** | Predictable costs, can be metered, cheaper for structured tasks |
| Pipeline extraction (articles, claims) | **Gemini Flash Lite API** | ~$0.50/day for current pipeline, 10x cheaper than Claude API |
| Complex reasoning (synthesis, research) | **Gemini Flash or Claude Sonnet API** | Balance of quality and cost |
| Code review / PR analysis | **Claude Max via `claude -p`** | Free with subscription, high quality |

### Model Routing (Small for Triage, Large for Complex)

```python
def route_to_model(task):
    if task.type in ("classify", "extract_entities", "validate"):
        return "gemini-3.1-flash-lite-preview"    # ~$0.01/1M tokens
    elif task.type in ("synthesize", "research", "complex_reasoning"):
        return "gemini-3-flash"                     # ~$0.10/1M tokens
    elif task.type in ("code_generation", "architecture"):
        return "claude-sonnet-4.6"                  # $3/$15 per 1M tokens
    elif task.type == "simple_chat":
        return "claude-haiku"                       # $0.25/$1.25 per 1M tokens
```

### Caching Strategies

1. **Prompt caching**: Gemini and Claude both support prompt caching (90% input token discount). Cache the system prompt + article context for multi-turn conversations.
2. **Result caching**: Cache LLM outputs keyed by (prompt_hash, model, temperature). The existing pipeline already does this implicitly (incremental processing skips unchanged articles).
3. **Embedding caching**: Store embeddings in `.npz` files (already done). Never recompute embeddings for unchanged text.
4. **Batch API**: Use Claude's batch API (50% discount) for non-urgent tasks. Combined with prompt caching: up to 95% savings.

### Budget Guardrails

```python
DAILY_BUDGET = {
    "gemini-flash-lite": 1.00,    # Pipeline extraction
    "gemini-flash": 2.00,          # Synthesis, research
    "claude-sonnet": 5.00,         # Complex tasks
    "claude-haiku": 2.00,          # Simple tasks
    "total": 10.00,                # Hard daily cap
}

# Check before every LLM call
def check_budget(model, estimated_tokens):
    spent = get_daily_spend(model)
    estimated_cost = estimate_cost(model, estimated_tokens)
    if spent + estimated_cost > DAILY_BUDGET[model]:
        raise BudgetExceeded(f"{model}: ${spent:.2f} spent, ${estimated_cost:.2f} estimated")
```

---

## 9. Concrete Implementation Plan

### Phase 1: Harden Existing Services (1-2 hours)

1. Create `petrarca` system user: `useradd -r -s /usr/sbin/nologin petrarca`
2. `chown -R petrarca:petrarca /opt/petrarca`
3. Move secrets from `/opt/petrarca/.env` to `/etc/petrarca/secrets.env` (owned by `root:petrarca`, mode 0640)
4. Update `petrarca-research.service` with systemd hardening directives (drop `User=root`)
5. Add hardening to all existing services
6. Test that pipeline and research server still work

### Phase 2: Agent Sandbox Infrastructure (half day)

1. Install bubblewrap: `apt install bubblewrap`
2. Install Redis: `apt install redis-server`
3. Write a thin supervisor script that:
   - Accepts tasks from Redis queue
   - Wraps each command in bubblewrap
   - Logs all actions to JSONL
   - Enforces timeouts
4. Create `petrarca-agent.service` with full systemd hardening
5. Set up egress allowlist via bubblewrap network proxy

### Phase 3: Approval and Notification (half day)

1. Implement Telegram bot (or simple webhook) for notifications
2. Add approval workflow: agent requests → human approves → agent executes
3. Define safe/cautious/critical operation categories
4. Implement kill switch script
5. Set up daily cost report

### Phase 4: Monitoring and Alerting (ongoing)

1. Extend existing `llm_audit.py` for agent operations
2. Set up budget guardrails with hard stops
3. Create a daily digest of agent activity (Telegram or email)
4. Add git commit attribution for agent commits
5. Set up Hetzner API snapshot automation before critical operations

---

## 10. Threat Model Summary

| Threat | Mitigation |
|--------|-----------|
| Agent reads secrets (.env, SSH keys) | systemd `ProtectHome`, `ProtectSystem`, `EnvironmentFile`; bubblewrap filesystem deny |
| Agent exfiltrates data to external server | Network egress allowlist via bubblewrap proxy |
| Agent deploys broken code to production | Human approval gate for all deploys |
| Agent corrupts data files | Pre-task snapshots, git-based versioning, read-only filesystem by default |
| Agent runs up massive API bills | Per-model daily budgets with hard stops |
| Agent modifies its own config/permissions | `NoNewPrivileges`, `ProtectSystem=strict`, agent cannot access its own service file |
| Prompt injection via ingested articles | Agent sandbox isolates execution; agent cannot access network or secrets even if compromised |
| Agent pushes malicious code to main | Branch protection rules; agent can only push to `sh/agent/*` branches; PRs require human review |
| VM compromise via agent vulnerability | Firecracker microVM (Phase 2+ if needed); systemd hardening limits blast radius |

---

## Sources

### Sandboxing and Isolation
- [How to sandbox AI agents in 2026 — Northflank](https://northflank.com/blog/how-to-sandbox-ai-agents)
- [Best code execution sandbox for AI agents — Northflank](https://northflank.com/blog/best-code-execution-sandbox-for-ai-agents)
- [How to Sandbox LLMs & AI Shell Tools — CodeAnt](https://www.codeant.ai/blogs/agentic-rag-shell-sandboxing)
- [Anthropic sandbox-runtime — GitHub](https://github.com/anthropic-experimental/sandbox-runtime)
- [Claude Code Sandboxing — Anthropic Engineering](https://www.anthropic.com/engineering/claude-code-sandboxing)
- [Claude Code Sandboxing Docs](https://code.claude.com/docs/en/sandboxing)
- [How Claude Code escapes its own denylist — Ona](https://ona.com/stories/how-claude-code-escapes-its-own-denylist-and-sandbox)
- [Why Anthropic and Vercel chose different sandboxes](https://michaellivs.com/blog/sandboxing-ai-agents-2026/)
- [Running AI Agents Safely with Firecracker MicroVMs](https://dev.to/ashish_chaudhary_b6089002/running-ai-agents-safely-with-firecracker-microvms-introducing-bunkervm-1ma8)

### Permission Models and Access Control
- [AI Agent Permissions: Least-Privilege Access Control — KLA Digital](https://kla.digital/blog/ai-agent-permissions)
- [AWS Well-Architected: Least privilege for agentic workflows](https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/gensec05-bp01.html)
- [Setting Permissions for AI Agents — Oso](https://www.osohq.com/learn/ai-agent-permissions-delegated-access)
- [Security best practices when building AI agents — Render](https://render.com/articles/security-best-practices-when-building-ai-agents)
- [AI Agents Are Becoming Authorization Bypass Paths — The Hacker News](https://thehackernews.com/2026/01/ai-agents-are-becoming-privilege.html)

### Authentication and Secrets
- [Secure AI agent authentication using HashiCorp Vault](https://developer.hashicorp.com/validated-patterns/vault/ai-agent-identity-with-hashicorp-vault)
- [Securing AI Agents Without Secrets — Aembit](https://aembit.io/blog/securing-ai-agents-without-secrets/)
- [AI Agent Security Best Practices — Wiz](https://www.wiz.io/academy/ai-security/ai-agent-security)
- [RCE and API Token Exfiltration Through Claude Code — Check Point](https://research.checkpoint.com/2026/rce-and-api-token-exfiltration-through-claude-code-project-files-cve-2025-59536/)
- [Claude Code Security Best Practices — Backslash](https://www.backslash.security/blog/claude-code-security-best-practices)

### Audit and Monitoring
- [Auditing and Logging AI Agent Activity — LoginRadius](https://www.loginradius.com/blog/engineering/auditing-and-logging-ai-agent-activity)
- [The Growing Challenge of Auditing Agentic AI — ISACA](https://www.isaca.org/resources/news-and-trends/industry-news/2025/the-growing-challenge-of-auditing-agentic-ai)
- [Agent Observability: How to Monitor AI Agents — Rubrik](https://www.rubrik.com/insights/ai-observability)

### Architecture Patterns
- [AI Agent Architecture — Redis](https://redis.io/blog/ai-agent-architecture/)
- [AI Agent Architecture Patterns — Redis](https://redis.io/blog/ai-agent-architecture-patterns/)
- [Handling Long-Running AI Jobs with Redis and Celery](https://markaicode.com/redis-celery-long-running-ai-jobs/)
- [Scaling long-running autonomous coding — Cursor](https://cursor.com/blog/scaling-agents)

### Existing Approaches (Devin, Codex, GitHub Actions)
- [Devin 2025 Performance Review — Cognition](https://cognition.ai/blog/devin-annual-performance-review-2025)
- [Securing Code from Devin AI Agent — VibeEval](https://vibe-eval.com/agentic-coding-security/devin-security-practices)
- [Hidden Security Risks of SWE Agents — Pillar Security](https://www.pillar.security/blog/the-hidden-security-risks-of-swe-agents-like-openai-codex-and-devin-ai)
- [Codex Security — OpenAI](https://developers.openai.com/codex/security/)
- [Codex Agent Approvals & Security — OpenAI](https://developers.openai.com/codex/agent-approvals-security/)
- [Harden-Runner for GitHub Actions — StepSecurity](https://github.com/step-security/harden-runner)
- [GitHub Agentic Workflows Preview](https://github.blog/changelog/2026-02-13-github-agentic-workflows-are-now-in-technical-preview/)

### Backup and Recovery
- [AI Agent Rollback Strategy — Fast.io](https://fast.io/resources/ai-agent-rollback-strategy/)
- [AI Agent Kill Switches — Pedowitz Group](https://www.pedowitzgroup.com/ai-agent-kill-switches-practical-safeguards-that-work)
- [Replit AI Disaster — BayTech Consulting](https://www.baytechconsulting.com/blog/the-replit-ai-disaster-a-wake-up-call-for-every-executive-on-ai-in-production)
- [AI-powered coding tool wiped database — Fortune](https://fortune.com/2025/07/23/ai-coding-tool-replit-wiped-database-called-it-a-catastrophic-failure/)

### Cost Optimization
- [Claude Code Pricing: Pro vs Max vs API — ShareUHack](https://www.shareuhack.com/en/posts/openclaw-claude-code-oauth-cost)
- [LLM Cost Optimization: Cut API Spend by 70-90% — Morph](https://www.morphllm.com/llm-cost-optimization)
- [Claude Code Rate Limits and Pricing — Northflank](https://northflank.com/blog/claude-rate-limits-claude-code-pricing-cost)

### Systemd Hardening
- [systemd Sandboxing — ArchWiki](https://wiki.archlinux.org/title/Systemd/Sandboxing)
- [systemd service sandboxing and security hardening 101 — Ctrl Blog](https://www.ctrl.blog/entry/systemd-service-hardening.html)
- [Mastering systemd: Securing and sandboxing — Red Hat](https://www.redhat.com/en/blog/mastering-systemd)

### Git Attribution
- [Attribute Git Commits to AI Agents — Eleanor Berger](https://elite-ai-assisted-coding.dev/p/attribute-git-commits-to-ai-agents)
- [Agent Identity for Git Commits — DEV Community](https://dev.to/jpoehnelt/agent-identity-for-git-commits-53n1)

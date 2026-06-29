# OClaw Project Overview Report

> Open-Source Super Agent Runtime Platform — Giving AI Real Execution Capabilities

---

## I. Project Positioning

OClaw is an open-source **Super Agent Harness** built on LangGraph + LangChain. It deeply integrates sub-agents, long-term memory, sandbox execution environments, and an extensible skill system, enabling AI agents to autonomously complete complex, multi-step real-world tasks.

**Core Value**: Out-of-the-box, highly extensible, supporting multiple models and channels — a single platform covering AI execution needs from research analysis to content generation.

---

## II. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   Client / Browser / IM Channels              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  Nginx :9191 │
                    └──┬──────┬───┘
              /api/*     │      │  /*
         ┌──────────────▼┐  ┌──▼──────────┐
         │  Gateway :9193 │  │ Frontend     │
         │  (FastAPI)     │  │ (Next.js)    │
         └───────┬────────┘  │ :9192        │
                 │            └──────────────┘
     ┌───────────▼────────────┐
     │  Embedded LangGraph Runtime │
     │  ┌─────────────────┐   │
     │  │   Lead Agent     │   │
     │  │  18-Layer Middleware Chain │
     │  │  ┌─────┐ ┌─────┐│   │
     │  │  │Sub-  │ │Tool  ││   │
     │  │  │Agent │ │System││   │
     │  │  │System│ │      ││   │
     │  │  └──┬──┘ └──┬──┘│   │
     │  │     │       │    │   │
     │  │  ┌──▼──┐ ┌──▼──┐ │   │
     │  │  │Sandbox│ │MCP │ │   │
     │  │  │Exec Env│ │Tools│ │   │
     │  │  └─────┘ └─────┘ │   │
     │  └─────────────────┘   │
     └────────────────────────┘
```

**Key Design Decisions**:
- Gateway embeds LangGraph runtime (no separate process), zero network overhead
- 18-layer middleware chain handles all cross-cutting concerns (security, audit, rate limiting, memory, etc.)
- Sandbox system supports three isolation modes: local / Docker / K8s
- Dual thread pool (scheduler pool + execution pool) drives parallel sub-agent execution

---

## III. Core Capability Matrix

### 3.1 Agent System

| Capability | Description |
|------|------|
| **Lead Agent** | Main agent, responsible for understanding intent, decomposing tasks, scheduling sub-agents, and synthesizing results |
| **Sub-Agents** | Dynamic parallel sub-agents, max 3 concurrent, 15-minute timeout |
| **Custom Agents** | Support defining specialized sub-agents via configuration, with customizable prompts, tool whitelists, and independent models |
| **SSE Streaming** | Real-time event stream: task_started → task_running → task_completed/failed |

### 3.2 Sandbox Execution Environment

| Mode | Use Case | Isolation Level |
|------|----------|----------|
| **LocalSandbox** | Local development | Process-level |
| **Docker Sandbox** | Production deployment | Container-level |
| **K8s Sandbox** | Multi-tenant | Pod-level |

The sandbox provides 7 core tools: `bash`, `ls`, `read_file`, `write_file`, `str_replace`, `glob`, `grep`, with automatic virtual path ↔ physical path mapping.

### 3.3 Skill System (25 Built-in Skills)

| Category | Skills |
|------|------|
| **Research & Analysis** | deep-research, github-deep-research, consulting-analysis, analysis-report |
| **Content Generation** | ppt-generation, podcast-generation, newsletter-generation, xlsx-creator |
| **Visual Creation** | image-generation, video-generation, music-generation, frontend-design |
| **Academic Tools** | academic-paper-review, systematic-literature-review |
| **Dev Tools** | code-documentation, bootstrap, skill-creator, find-skills |
| **Data Processing** | data-analysis, chart-visualization, pdf-processing |
| **Web Tools** | web-design-guidelines, vercel-deploy-claimable, claude-to-kkoclaw, surprise-me |

Skills use the Markdown format (SKILL.md) with progressive lazy loading to keep the context window lean.

### 3.4 Memory System

LLM-driven cross-session persistent memory:
- **Auto Extraction**: Extracts user preferences, knowledge background, and work habits from conversations
- **Confidence Scoring**: Each fact carries a 0–1 confidence score; those below threshold are automatically retired
- **Debounced Writes**: 30-second debounce + atomic file writes to avoid frequent LLM calls
- **Per-User Isolation**: Independent `memory.json` per user

### 3.5 Token Usage Monitoring

| Metric Dimension | Description |
|----------|------|
| **Task Count** | Number of executions per conversation |
| **API Call Count** | Actual LLM model calls (including sub-agents, middleware) |
| **Token Consumption** | By input/output/total, supporting breakdown by model and caller |
| **Time Series Trends** | Daily-granularity token consumption trend charts with monthly filtering |
| **5-Minute Auto Refresh** | Background silent refresh, does not affect user operations |

### 3.6 IM Channel Integration

Supports 5 major instant messaging platforms, **no public IP required**:

| Channel | Transport | Features |
|------|----------|------|
| Telegram | Bot API long polling | Simple deployment |
| Slack | Socket Mode | Moderate complexity |
| Feishu/Lark | WebSocket persistent connection | Streaming card updates |
| WeCom | WebSocket | Smart bot |
| DingTalk | Stream Push | AI card streaming |

---

## IV. Model Support

### Verified Model Providers

| Provider | Models | Feature Support |
|----------|------|----------|
| **DeepSeek** | V4-Flash, V4-Pro | Thinking + Vision |
| **MiniMax** | M2.7-HighSpeed | Thinking + Vision |
| **Zhipu GLM** | GLM-5-Turbo, GLM-5.1 | Thinking + Vision |
| **Google Gemini** | 2.5-Flash, 3.5-Flash | Thinking + Vision |

### Architecturally Supported (No Code Changes Required)

OpenAI, Anthropic Claude, Ollama, vLLM, OpenRouter, Novita, and all LangChain-compatible Chat Models.

**Model Configuration Features**:
- Environment variable references: API Keys referenced via `$ENV_VAR`, not hardcoded
- Thinking mode: Independently configured per model via `when_thinking_enabled/disabled`
- Display name mapping: `display_name` for frontend display
- Custom class paths: Load custom Model Wrappers via the `use` field

---

## V. Technology Stack

### Backend (413 Python Files, 154 Test Files)

| Technology | Version | Purpose |
|------|------|------|
| Python | 3.12+ | Primary programming language |
| LangGraph | 1.0.6+ | Agent framework and multi-agent orchestration |
| LangChain | 1.2.3+ | LLM abstraction and tool system |
| FastAPI | 0.115.0+ | Gateway REST API |
| Pydantic | — | Data validation and serialization |
| SQLAlchemy | — | ORM (SQLite / PostgreSQL) |
| uv | — | Python package manager |
| ruff | — | Lint + code formatting |

### Frontend (283 TS/TSX Files)

| Technology | Version | Purpose |
|------|------|------|
| Next.js | 16 | App Router framework |
| React | 19 | UI framework |
| Tailwind CSS | 4 | Styling system |
| Shadcn UI + MagicUI | — | Component library |
| Recharts | — | Data visualization charts |
| pnpm | — | Package manager |

### Infrastructure

| Technology | Purpose |
|------|------|
| Nginx | Reverse proxy (unified port 9191) |
| Docker / Docker Compose | Containerized deployment |
| SQLite / PostgreSQL | State persistence |

---

## VI. Frontend Management Features

### 6.1 Conversation Interface
- Multi-thread conversation management (create, switch, delete)
- SSE streaming response real-time display
- File upload with auto-conversion (PDF/PPT/Excel/Word → Markdown)
- Real-time sub-agent task status display
- Memory management (view, edit, delete)

### 6.2 Admin Pages

| Page | Function | Icon |
|------|------|----------|
| **Agent Management** | Custom sub-agent CRUD | BotIcon |
| **Channel Management** | IM channel configuration (Feishu, WeCom, DingTalk, etc.) | MessageCircleIcon |
| **Scheduled Tasks** | Cron task creation and scheduling | ClockIcon |
| **MCP Management** | MCP Server CRUD, enable/disable | TerminalIcon |
| **Model Management** | LLM model configuration CRUD | CpuIcon |
| **Skill Management** | Skill installation, enable/disable | SparklesIcon |
| **Token Usage** | Multi-dimensional token stats and trend charts | ZapIcon |
| **System Settings** | Account, appearance, memory, notifications, tool config | Various SettingsIcon |

### 6.3 UI Highlights
- Dark/light theme toggle
- Chinese/English bilingual (i18n)
- Responsive layout (mobile adapted)
- 5-minute auto silent refresh (Token Usage page)
- Admin page titles uniformly iconized
- Card to list unified UI specification

---

## VII. Security Design

| Layer | Measures |
|------|------|
| **Sandbox Isolation** | Docker/K8s container-level isolation, file operations anti-path-traversal |
| **Authentication System** | JWT + bcrypt, built-in user management |
| **CSRF Protection** | Gateway CSRF middleware |
| **XSS Protection** | HTML/SVG forced download instead of inline rendering |
| **Loop Detection** | 18-layer middleware includes LoopDetection to prevent tool call infinite loops |
| **Circuit Breaker** | Auto circuit-break when LLM call failures reach threshold |
| **Command Audit** | Shell/file operation security audit logs |
| **Key Security** | API Keys referenced via environment variables, not stored in config files |

---

## VIII. Middleware System (18 Layers)

Executed in strict order, covering all cross-cutting concerns:

```
ThreadData → Uploads → Sandbox → DanglingToolCall → LLMErrorHandling
→ Guardrail → SandboxAudit → ToolErrorHandling → Summarization
→ TodoList → TokenUsage → Title → Memory → ViewImage
→ DeferredToolFilter → SubagentLimit → LoopDetection → Clarification
```

Key middleware descriptions:
- **LoopDetectionMiddleware**: Three-tier loop protection (tool frequency → consecutive identical calls → forced termination + state cleanup)
- **LLMErrorHandlingMiddleware**: Distinguishes transient rate limits (429 retry) from hard quota exhaustion (insufficient_quota), supports Google retryDelay parsing
- **TokenUsageMiddleware**: Tracks tokens by model + caller (lead_agent / subagent / middleware)
- **SummarizationMiddleware**: Auto-compresses context when exceeding limits, preserves recent skill calls
- **MemoryMiddleware**: Async memory extraction, 30-second debounce

---

## IX. Deployment Guide

### Resource Recommendations

| Scenario | Starting Config | Recommended Config |
|------|----------|----------|
| Local Development | 4 vCPU / 8 GB RAM | 8 vCPU / 16 GB RAM |
| Docker Development | 4 vCPU / 8 GB RAM | 8 vCPU / 16 GB RAM |
| Production Service | 8 vCPU / 16 GB RAM | 16 vCPU / 32 GB RAM |

### Quick Start

```bash
# 1. Clone the project
git clone https://github.com/kkutysllb/kk_OClaw.git
cd kk_OClaw

# 2. Configure environment variables
cp env.example .env
# Edit .env, fill in API Key

# 3. Choose deployment method

# Docker method (recommended)
make docker-init    # Pull sandbox image
make docker-start   # Start services

# Local development method
make check          # Check environment
make install        # Install dependencies
make dev            # Start services

# 4. Access
# http://localhost:9191
```

### Command Reference

| Command | Description |
|------|------|
| `make dev` | Local development startup (foreground) |
| `make docker-start` | Docker development startup (hot reload) |
| `make up` | Docker production deployment |
| `make stop` | Stop all services |
| `make clean` | Clean up temporary resources |
| `make test` | Run backend tests |

---

## X. Project Scale

| Metric | Data |
|------|------|
| Git Commits | 47+ |
| Backend Python Files | 413 |
| Frontend TS/TSX Files | 283 |
| Test Files | 154 |
| Built-in Skills | 25 |
| Middleware Layers | 18 |
| Supported IM Channels | 5 |
| Supported LLM Providers | 10+ |
| Config Version | v8 |

---

## XI. Project Directory Structure

```
kk_OClaw/
├── config.yaml                    # Main configuration file
├── .env                           # Environment variables (API Key, etc.)
├── Makefile                       # Root-level build commands
├── backend/
│   ├── packages/harness/kkoclaw/  # Agent framework core
│   │   ├── agents/                # Agent system (lead_agent + 18 middleware)
│   │   ├── sandbox/               # Sandbox execution system
│   │   ├── subagents/             # Sub-agent system
│   │   ├── models/                # Model factory & adapters
│   │   ├── skills/                # Skill discovery & loading
│   │   ├── mcp/                   # MCP integration
│   │   ├── memory/                # Memory system
│   │   ├── persistence/           # Persistence layer (SQL + Memory)
│   │   └── community/             # Community tools
│   ├── app/
│   │   ├── gateway/               # FastAPI Gateway (10+ route modules)
│   │   └── channels/              # IM channels (7 platforms)
│   ├── tests/                     # 154 test files
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/                   # Next.js App Router
│   │   ├── components/workspace/  # Business components
│   │   └── core/                  # Core logic (API, i18n, hooks)
│   ├── tests/                     # Unit + E2E tests
│   └── package.json
├── skills/
│   ├── public/                    # 25 built-in skills
│   └── custom/                    # User custom skills
├── docker/
│   ├── docker-compose-dev.yaml    # Docker dev environment
│   ├── docker-compose.yaml        # Docker production environment
│   └── nginx/                     # Nginx configuration
└── scripts/                       # Operations scripts
```

---

## XII. Key Data Flows

### Request Processing

```
User message → Nginx → Gateway → LangGraph Runtime
  → ThreadState load → 18-layer middleware processing
  → Model call (with Tool selection)
  → Sandbox execution → SSE streaming return
```

### Sub-Agent Execution

```
Lead Agent identifies parallel tasks
  → Scheduler pool (3 workers) receives
  → Execution pool (3 workers) runs
  → Each sub-agent has independent Sandbox + Context
  → Results merged → Return to Lead Agent
```

### Memory Update

```
Conversation ends → MemoryMiddleware filters
  → 30s debounce enqueue → LLM extracts facts
  → Confidence evaluation → Atomic write to memory.json
  → Next conversation injects Top 15 facts
```

---

## XIII. Embedded Python Client

Use without starting an HTTP service:

```python
from kkoclaw.client import OClawClient

client = OClawClient()

# Chat
response = client.chat("Analyze this paper", thread_id="my-thread")

# Streaming response
for event in client.stream("Hello"):
    if event.type == "messages-tuple" and event.data.get("type") == "ai":
        print(event.data["content"])

# Management operations
models = client.list_models()
skills = client.list_skills()
client.upload_files("thread-1", ["./report.pdf"])
```

---

## XIV. License

MIT License

---

*This report is generated based on the actual OClaw project code, last updated: May 2026.*

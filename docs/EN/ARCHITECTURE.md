# Architecture Overview

This document provides a comprehensive overview of the OClaw backend architecture.

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          Client (Browser)                                 │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                       Nginx (Port 2026)                                   │
│                 Unified Reverse Proxy Entry Point                         │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  /api/langgraph/*  →  LangGraph Server (2024)                       │  │
│  │  /api/*            →  Gateway API (8001)                            │  │
│  │  /*                →  Frontend (3000)                               │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
          ▼                       ▼                       ▼
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│   LangGraph Server   │ │    Gateway API      │ │     Frontend        │
│    (Port 2024)       │ │   (Port 8001)        │ │   (Port 3000)       │
│                     │ │                     │ │                     │
│  - Agent runtime   │ │  - Model API        │ │  - Next.js app     │
│  - Thread mgmt     │ │  - MCP config       │ │  - React UI        │
│  - SSE streaming   │ │  - Skill mgmt       │ │  - Chat interface  │
│  - Checkpoints     │ │  - File uploads     │ │                     │
│                     │ │  - Thread cleanup   │ │                     │
│                     │ │  - Artifact mgmt    │ │                     │
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘
          │                       │
          │     ┌─────────────────┘
          │     │
          ▼     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         Shared Configuration                              │
│  ┌─────────────────────────┐  ┌────────────────────────────────────────┐ │
│  │      config.yaml        │  │      extensions_config.json            │ │
│  │  - Model config         │  │  - MCP servers                        │ │
│  │  - Tool config          │  │  - Skill status                       │ │
│  │  - Sandbox config       │  │                                        │ │
│  │  - Summarization config │  │                                        │ │
│  └─────────────────────────┘  └────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### LangGraph Server

The LangGraph Server is the core Agent runtime, built on LangGraph for robust multi-agent workflow orchestration.

**Entry Point**: `packages/harness/kkoclaw/agents/lead_agent/agent.py:make_lead_agent`

**Primary Responsibilities**:
- Agent creation and configuration
- Thread state management
- Middleware chain execution
- Tool execution orchestration
- SSE streaming for real-time responses

**Configuration**: `langgraph.json`

### Gateway API

A FastAPI-based application providing REST endpoints for non-Agent operations.

**Entry Point**: `app/gateway/app.py`

**Route Modules**:
- `models.py` — `/api/models` — Model listing and details
- `mcp.py` — `/api/mcp` — MCP server configuration
- `skills.py` — `/api/skills` — Skill management
- `uploads.py` — `/api/threads/{id}/uploads` — File uploads
- `threads.py` — `/api/threads/{id}` — Clean up local OClaw thread data after LangGraph deletion
- `artifacts.py` — `/api/threads/{id}/artifacts` — Artifact serving
- `suggestions.py` — `/api/threads/{id}/suggestions` — Follow-up suggestion generation

### Agent Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    make_lead_agent(config)                                │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          Middleware Chain                                 │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ 1. ThreadDataMiddleware   — Initialize workspace/upload/output    │   │
│  │ 2. UploadsMiddleware      — Handle uploaded files                 │   │
│  │ 3. SandboxMiddleware      — Acquire sandbox environment           │   │
│  │ 4. SummarizationMiddleware — Context reduction (if enabled)       │   │
│  │ 5. TitleMiddleware        — Auto-generate titles                  │   │
│  │ 6. TodoListMiddleware     — Task tracking (plan mode)             │   │
│  │ 7. ViewImageMiddleware    — Vision model support                  │   │
│  │ 8. ClarificationMiddleware — Handle clarification requests        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              Agent Core                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐   │
│  │      Model       │  │      Tools       │  │   System Prompt     │   │
│  │  (from factory)  │  │  (configured +    │  │  (with skills)      │   │
│  │                  │  │   MCP + built-in) │  │                      │   │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Thread State

`ThreadState` extends LangGraph's `AgentState` with additional fields:

```python
class ThreadState(AgentState):
    messages: list[BaseMessage]      # Core state inherited from AgentState

    # OClaw extensions
    sandbox: dict             # Sandbox environment info
    artifacts: list[str]      # Generated file paths (real host absolute paths)
    thread_data: dict         # {workspace, uploads, outputs} real host paths
    title: str | None         # Auto-generated conversation title
    todos: list[dict]         # Task tracking (plan mode)
    viewed_images: dict       # Vision model image data
```

### Sandbox System

```
┌─────────────────────────┐
│  LocalSandboxProvider   │
│                         │
│  - Singleton instance   │
│  - Direct execution     │
│  - Local environment    │
└─────────────────────────┘
```

**Path Layout**:

After the sandbox refactor (phase 3), the `/mnt/user-data/{workspace,uploads,outputs}` virtual path layer was removed. Agents, tools, and APIs now use real host absolute paths directly. The thread data root is `{KKOCLAW_HOME}/threads/{thread_id}/user-data/` (or `{KKOCLAW_HOME}/users/{user_id}/threads/{thread_id}/user-data/` with user isolation enabled), where `KKOCLAW_HOME` resolves to `~/.kkoclaw` by default.

| Category | Real Host Path |
|---------|---------|
| Workspace | `{KKOCLAW_HOME}/threads/{thread_id}/user-data/workspace/` |
| Uploaded files | `{KKOCLAW_HOME}/threads/{thread_id}/user-data/uploads/` |
| Generated artifacts | `{KKOCLAW_HOME}/threads/{thread_id}/user-data/outputs/` |

`ThreadState.artifacts` now stores these real host absolute paths directly (e.g. `/home/user/.kkoclaw/threads/abc/user-data/outputs/report.pdf`), and `Paths.resolve_thread_artifact_path` validates that a path falls inside the thread's `user-data/` root.

Directories that remain virtual paths:

| Virtual Path | Physical Path | Description |
|---------|---------|---------|
| `/mnt/skills` | `kk-oclaw/skills/` | Global read-only skill library |
| `/mnt/acp-workspace` | `{KKOCLAW_HOME}/threads/{thread_id}/acp-workspace/` | ACP subagent workspace (per-thread isolated) |
| `/mnt/xxx` (custom) | configured in `config.yaml` | Custom mounts configured via config |

### Tool System

Tools come from three sources: **Built-in** (`packages/harness/kkoclaw/tools/`), **Configured** (`config.yaml`), and **MCP** (`extensions.json`). They are assembled by `get_available_tools()`.

### Model Factory

```
config.yaml → create_chat_model() → resolve_class() → BaseChatModel (LangChain instance)
```

**Supported Providers**: OpenAI, Anthropic, DeepSeek, and custom via LangChain integrations.

### MCP Integration

Uses `MultiServerMCPClient` (langchain-mcp-adapters) with stdio, SSE, and HTTP transports configured via `extensions_config.json`.

### Skill System

```
skills/
├── public/    # Public skills (committed to repo)
│   ├── pdf-processing/SKILL.md
│   ├── frontend-design/SKILL.md
│   └── ...
└── custom/    # Custom skills (gitignored)
    └── user-installed/SKILL.md
```

### Request Flow

```
1. Client → Nginx → POST /api/langgraph/threads/{thread_id}/runs
2. Nginx → LangGraph Server (2024)
3. LangGraph Server:
   a. Load/create thread state
   b. Execute middleware chain
   c. Execute Agent (model processes messages, may call tools, sandbox execution)
   d. Stream response via SSE
4. Client receives streaming response
```

### Data Flows

**File Upload**: Client POST → Gateway validates → store to `{KKOCLAW_HOME}/threads/{thread_id}/user-data/uploads/` → optional Markdown conversion → return real host path + artifact URL → next Agent run auto-lists files via UploadsMiddleware. The Agent accesses files directly via the real host path (no virtual path layer).

**Thread Cleanup**: DELETE LangGraph thread → Web UI calls Gateway cleanup → remove `{KKOCLAW_HOME}/threads/{thread_id}/`.

**Config Reload**: PUT MCP config → Gateway writes `extensions_config.json` → MCP manager detects mtime change → reinitialize client → next Agent run uses new tools.

## Security Considerations

- **Sandbox Isolation**: Agent code executes within sandbox boundaries (local execution mode).
- **API Security**: Thread-isolated data directories, path traversal protection, env var secrets.
- **MCP Security**: Each MCP server runs in its own process, runtime resolution of env vars, independent enable/disable.

## Performance Considerations

- **Caching**: MCP tools cached with file mtime invalidation; config loaded once, reloaded on change; skills parsed on startup, cached in memory.
- **Streaming**: SSE for real-time response streaming, reducing time-to-first-byte.
- **Context Management**: Summarization middleware reduces context near limits; configurable triggers (tokens, messages, or fraction).

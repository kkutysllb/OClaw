# API Reference

This document provides a complete reference for the OClaw backend API.

## Overview

The OClaw backend provides two sets of APIs:

1. **LangGraph API** — Agent interaction, threads, and streaming (`/api/langgraph/*`)
2. **Gateway API** — Models, MCP, skills, uploads, and artifacts (`/api/*`)

All APIs are accessible via the Nginx reverse proxy (port 2026).

## LangGraph API

Base URL: `/api/langgraph`

### Threads

#### Create Thread
```http
POST /api/langgraph/threads
Content-Type: application/json
```
**Request Body:** `{"metadata": {}}`

#### Get Thread State
```http
GET /api/langgraph/threads/{thread_id}/state
```

### Runs

#### Create Run
Execute Agent with input.

```http
POST /api/langgraph/threads/{thread_id}/runs
Content-Type: application/json
```

**Request Body:**
```json
{
  "input": {"messages": [{"role": "user", "content": "Hello, can you help me?"}]},
  "config": {
    "recursion_limit": 100,
    "configurable": {"model_name": "gpt-4", "thinking_enabled": false, "is_plan_mode": false}
  },
  "stream_mode": ["values", "messages-tuple", "custom"]
}
```

**Stream Mode Compatibility:** Available: `values`, `messages-tuple`, `custom`, `updates`, `events`, `debug`, `tasks`, `checkpoints`. Do not use `tools` (deprecated/invalid in current `langgraph-api`, triggers schema validation error).

**Recursion Limit:** `/api/langgraph/*` endpoints directly access LangGraph Server, inheriting the native default of **25**, which is too low for plan mode or sub-agent-intensive runs. OClaw's own Gateway and IM channel paths mitigate this by defaulting to `100` in `build_run_config`. Clients directly calling the LangGraph API must explicitly set `recursion_limit` in the request body.

**Configurable Options:**
- `model_name` (string): Override default model
- `thinking_enabled` (boolean): Enable extended thinking for supported models
- `is_plan_mode` (boolean): Enable TodoList middleware for task tracking

**Response:** Server-Sent Events (SSE) stream

#### Stream Run
Real-time streaming of responses.
```http
POST /api/langgraph/threads/{thread_id}/runs/stream
Content-Type: application/json
```
Same request body as Create Run. Returns SSE stream.

---

## Gateway API

Base URL: `/api`

### Models

#### List Models
```http
GET /api/models
```
Returns all available LLM models from configuration.

#### Get Model Details
```http
GET /api/models/{model_name}
```

### MCP Configuration

#### Get MCP Config
```http
GET /api/mcp/config
```

#### Update MCP Config
```http
PUT /api/mcp/config
Content-Type: application/json
```
**Request Body:** `{"mcpServers": {...}}`

### Skills

#### List Skills
```http
GET /api/skills
```

#### Get Skill Details
```http
GET /api/skills/{skill_name}
```

#### Enable Skill
```http
POST /api/skills/{skill_name}/enable
```

#### Disable Skill
```http
POST /api/skills/{skill_name}/disable
```

#### Install Skill
Install a `.skill` file from a thread artifact path. A `.skill` file is a ZIP archive; install validates `SKILL.md`, runs the security scanner, and injects requested `work_modes` when the archive does not declare them.
```http
POST /api/skills/install
Content-Type: application/json
```
**Request Body:**
```json
{
  "thread_id": "thread_abc",
  "path": "mnt/user-data/outputs/my-skill.skill",
  "work_modes": ["coding"]
}
```

- `thread_id`: thread containing the `.skill` artifact
- `path`: virtual path to the artifact
- `work_modes`: optional work-mode bindings; defaults to `task` when omitted and the archive has no `work_modes` frontmatter

### File Uploads

#### Upload Files
Upload one or more files to a thread.
```http
POST /api/threads/{thread_id}/uploads
Content-Type: multipart/form-data
```
**Request Body:** `files` — one or more files to upload

**Response** includes `path`, `virtual_path`, `artifact_url`, and optional `markdown_*` fields for converted documents.

**Supported document formats** (auto-converted to Markdown): PDF (`.pdf`), PowerPoint (`.ppt`, `.pptx`), Excel (`.xls`, `.xlsx`), Word (`.doc`, `.docx`)

#### List Uploaded Files
```http
GET /api/threads/{thread_id}/uploads/list
```

#### Delete File
```http
DELETE /api/threads/{thread_id}/uploads/{filename}
```

### Thread Cleanup

Remove OClaw-managed local thread files after deleting the LangGraph thread.
```http
DELETE /api/threads/{thread_id}
```

**Error behavior:**
- Invalid thread ID returns `422`
- `500` returns generic `{"detail": "Failed to delete local thread data."}` response; full exception details retained in server logs

### Artifacts

#### Get Artifact
Download or view Agent-generated artifacts.
```http
GET /api/threads/{thread_id}/artifacts/{path}
```

**Path examples:**
- `/api/threads/abc123/artifacts/mnt/user-data/outputs/result.txt`
- `/api/threads/abc123/artifacts/mnt/user-data/uploads/document.pdf`

**Query Parameters:**
- `download` (boolean): If `true`, force download with Content-Disposition header

**Response:** File content with appropriate Content-Type

---

## Error Responses

All APIs return errors in a unified format:
```json
{"detail": "Error message describing the issue"}
```

**HTTP Status Codes:**
- `400` — Bad Request: invalid input
- `404` — Not Found: resource does not exist
- `422` — Validation Error: request validation failed
- `500` — Internal Server Error: server-side error

---

## Authentication

Currently, OClaw does not implement an authentication mechanism. All APIs are accessible without credentials.

Note: This refers to OClaw API authentication. MCP outbound connections can still use OAuth for configured HTTP/SSE MCP servers.

For production deployments, it is recommended to:
1. Use Nginx to implement basic auth or OAuth integration
2. Deploy behind a VPN or private network
3. Implement custom authentication middleware

---

## Rate Limiting

Rate limiting is not implemented by default. For production deployments, configure rate limiting in Nginx:

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

location /api/ {
    limit_req zone=api burst=20 nodelay;
    proxy_pass http://backend;
}
```

---

## WebSocket Support

The LangGraph Server supports WebSocket connections for real-time streaming. Connect to:
```
ws://localhost:2026/api/langgraph/threads/{thread_id}/runs/stream
```

---

## SDK Usage

### Python (LangGraph SDK)

```python
from langgraph_sdk import get_client

client = get_client(url="http://localhost:2026/api/langgraph")

# Create thread
thread = await client.threads.create()

# Run Agent
async for event in client.runs.stream(
    thread["thread_id"], "lead_agent",
    input={"messages": [{"role": "user", "content": "Hello"}]},
    config={"configurable": {"model_name": "gpt-4"}},
    stream_mode=["values", "messages-tuple", "custom"],
):
    print(event)
```

### JavaScript/TypeScript

```typescript
// Use fetch for Gateway API
const response = await fetch('/api/models');
const data = await response.json();
console.log(data.models);

// Use EventSource for streaming
const eventSource = new EventSource(
  `/api/langgraph/threads/${threadId}/runs/stream`
);
eventSource.onmessage = (event) => {
  console.log(JSON.parse(event.data));
};
```

### cURL Examples

```bash
# List models
curl http://localhost:2026/api/models

# Get MCP config
curl http://localhost:2026/api/mcp/config

# Upload file
curl -X POST http://localhost:2026/api/threads/abc123/uploads \
  -F "files=@document.pdf"

# Enable skill
curl -X POST http://localhost:2026/api/skills/pdf-processing/enable

# Create thread and run Agent
curl -X POST http://localhost:2026/api/langgraph/threads \
  -H "Content-Type: application/json" -d '{}'

curl -X POST http://localhost:2026/api/langgraph/threads/abc123/runs \
  -H "Content-Type: application/json" \
  -d '{"input": {"messages": [{"role": "user", "content": "Hello"}]}, "config": {"recursion_limit": 100, "configurable": {"model_name": "gpt-4"}}}'
```

> `/api/langgraph/*` endpoints bypass OClaw's gateway and inherit LangGraph's native `recursion_limit` default of 25, which is too low for plan mode or sub-agent runs. Always explicitly set `config.recursion_limit` — see the [Create Run](#create-run) section for details.

# Guardrails: Pre-Execution Tool Call Authorization

> **Context:** [Issue #1213](https://github.com/bytedance/kk-oclaw/issues/1213) — OClaw has Docker sandboxing and human approval via `ask_clarification`, but no deterministic, policy-driven tool call authorization layer. Agents running autonomous multi-step tasks can execute any loaded tool with any arguments. Guardrails adds a middleware that evaluates each tool call against policy **before execution**.

## Why Guardrails Are Needed

```
Without guardrails:                 With guardrails:

  Agent                                Agent
    │                                    │
    ▼                                    ▼
  ┌──────────┐                         ┌──────────┐
  │ bash     │──▶ Execute immediately   │ bash     │──▶ GuardrailMiddleware
  │ rm -rf / │                         │ rm -rf / │        │
  └──────────┘                         └──────────┘        ▼
                                                     ┌──────────────┐
                                                     │  Provider    │
                                                     │  Evaluates   │
                                                     │  by policy   │
                                                     └──────┬───────┘
                                                            │
                                                      ┌─────┴─────┐
                                                      │           │
                                                    ALLOW       DENY
                                                      │           │
                                                      ▼           ▼
                                                 Tool runs    Agent sees:
                                                 normally     "Guardrail denied:
                                                              rm -rf blocked"
```

- **Sandbox** provides process isolation but not semantic authorization. A sandboxed `bash` can still `curl` data out.
- **Human approval** (`ask_clarification`) requires human involvement for every operation. Not suitable for autonomous workflows.
- **Guardrails** provide deterministic, policy-driven authorization that works without human intervention.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Middleware Chain                              │
│                                                                      │
│  1. ThreadDataMiddleware     ─── Per-thread directory                │
│  2. UploadsMiddleware        ─── File upload tracking                │
│  3. SandboxMiddleware        ─── Sandbox acquisition                 │
│  4. DanglingToolCallMiddleware ── Fix incomplete tool calls          │
│  5. GuardrailMiddleware ◄──── Evaluates each tool call               │
│  6. ToolErrorHandlingMiddleware ── Converts exceptions to messages   │
│  7-12. (Summarization, Title, Memory, Vision, Subagent, Clarify)    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                         │
                         ▼
           ┌──────────────────────────┐
           │    GuardrailProvider     │  ◄── Pluggable: any class with
           │    (configured in YAML)   │      evaluate/aevaluate
           └────────────┬─────────────┘
                        │
              ┌─────────┼──────────────┐
              │         │              │
              ▼         ▼              ▼
         Built-in     OAP Passport    Custom
         Allowlist    Provider        Provider
         (zero deps)  (open standard) (your code)
                        │
                  Any implementation
                  (e.g., APort, or
                   your own evaluator)
```

`GuardrailMiddleware` implements `wrap_tool_call` / `awrap_tool_call` (same `AgentMiddleware` pattern used by `ToolErrorHandlingMiddleware`). It:

1. Builds a `GuardrailRequest` with tool name, arguments, and passport reference
2. Calls `provider.evaluate(request)` on the configured arbitrary provider
3. If **denied**: returns `ToolMessage(status="error")` with reason — Agent sees the denial and adjusts
4. If **allowed**: passes through to the actual tool handler
5. If **provider error** and `fail_closed=true` (default): blocks the call
6. `GraphBubbleUp` exceptions (LangGraph control signals) always propagate, never caught

## Three Provider Options

### Option 1: Built-in AllowlistProvider (Zero Dependencies)

Simplest option. Ships with OClaw. Blocks or allows tools by name. No external packages, no passports, no network.

**config.yaml:**
```yaml
guardrails:
  enabled: true
  provider:
    use: kkoclaw.guardrails.builtin:AllowlistProvider
    config:
      denied_tools: ["bash", "write_file"]
```

This blocks all requested `bash` and `write_file`. All other tools pass.

You can also use an allowlist (only allow these tools):
```yaml
guardrails:
  enabled: true
  provider:
    use: kkoclaw.guardrails.builtin:AllowlistProvider
    config:
      allowed_tools: ["web_search", "read_file", "ls"]
```

**Try it:**
1. Add the above config to your `config.yaml`
2. Start OClaw: `make dev`
3. Ask the agent: "Use bash to run echo hello"
4. Agent sees: `Guardrail denied: tool 'bash' was blocked (oap.tool_not_allowed)`

### Option 2: OAP Passport Provider (Policy-Based)

Policy enforcement based on the [Open Agent Passport (OAP)](https://github.com/aporthq/aport-spec) open standard. An OAP passport is a JSON document declaring the agent's identity, capabilities, and operational restrictions. Any provider that reads OAP passports and returns OAP-compliant decisions can be used with OClaw.

```
┌─────────────────────────────────────────────────────────────┐
│                    OAP Passport (JSON)                        │
│                   (Open standard, any provider)               │
│  {                                                           │
│    "spec_version": "oap/1.0",                                │
│    "status": "active",                                       │
│    "capabilities": [                                         │
│      {"id": "system.command.execute"},                       │
│      {"id": "data.file.read"},                               │
│      {"id": "data.file.write"},                              │
│      {"id": "web.fetch"},                                    │
│      {"id": "mcp.tool.execute"}                              │
│    ],                                                        │
│    "limits": {                                               │
│      "system.command.execute": {                             │
│        "allowed_commands": ["git", "npm", "node", "ls"],     │
│        "blocked_patterns": ["rm -rf", "sudo", "chmod 777"]   │
│      }                                                       │
│    }                                                         │
│  }                                                           │
└──────────────────────────┬──────────────────────────────────┘
                           │
              Any OAP-compliant provider
          ┌────────────────┼────────────────┐
          │                │                │
      Your own         APort (reference   Other future
      evaluator        implementation)    implementations
```

**Creating passports manually:**

An OAP passport is just a JSON file. You can create it manually following the [OAP spec](https://github.com/aporthq/aport-spec/blob/main/oap/oap-spec.md) and validate against the [JSON schema](https://github.com/aporthq/aport-spec/blob/main/oap/passport-schema.json). See the [examples](https://github.com/aporthq/aport-spec/tree/main/oap/examples) directory for templates.

**Using APort as reference implementation:**

[APort Agent Guardrails](https://github.com/aporthq/aport-agent-guardrails) is an open-source (Apache 2.0) implementation of an OAP provider. It handles passport creation, local evaluation, and optional hosted API evaluation.

```bash
pip install aport-agent-guardrails
aport setup --framework kkoclaw
```

This creates:
- `~/.aport/kkoclaw/config.yaml` — Evaluator configuration (local or API mode)
- `~/.aport/kkoclaw/aport/passport.json` — OAP passport with capabilities and limits

**config.yaml (using APort as provider):**
```yaml
guardrails:
  enabled: true
  provider:
    use: aport_guardrails.providers.generic:OAPGuardrailProvider
```

**config.yaml (using your own OAP provider):**
```yaml
guardrails:
  enabled: true
  provider:
    use: my_oap_provider:MyOAPProvider
    config:
      passport_path: ./my-passport.json
```

Any provider that accepts `framework` as kwargs and implements `evaluate`/`aevaluate` can be used. The OAP standard defines passport format and decision codes; OClaw doesn't care which provider reads them.

**What the passport controls:**

| Passport Field | Effect | Example |
|---|---|---|
| `capabilities[].id` | Which tool categories the agent can use | `system.command.execute`, `data.file.write` |
| `limits.*.allowed_commands` | Which commands are allowed | `["git", "npm", "node"]` or `["*"]` for all |
| `limits.*.blocked_patterns` | Patterns that are always denied | `["rm -rf", "sudo", "chmod 777"]` |
| `status` | Kill switch | `active`, `suspended`, `revoked` |

**Evaluation modes (depends on provider):**

OAP providers may support different evaluation modes. For example, the APort reference implementation supports:

| Mode | How it works | Network | Latency |
|---|---|---|---|
| **Local** | Evaluates passport locally (bash script). | None | ~300ms |
| **API** | Sends passport + context to hosted evaluator. Signed decisions. | Yes | ~65ms |

Custom OAP providers can implement any evaluation strategy — OClaw middleware doesn't care how the provider makes decisions.

**Try it:**
1. Install and set up as above
2. Start OClaw and ask: "Create a file called test.txt with content hello"
3. Then ask: "Now delete it using bash rm -rf"
4. Guardrail blocks it: `oap.blocked_pattern: Command contains blocked pattern: rm -rf`

### Option 3: Custom Provider (Bring Your Own)

Any Python class with `evaluate(request)` and `aevaluate(request)` methods can be used. No base class or inheritance needed — it's a structural protocol.

```python
# my_guardrail.py

class MyGuardrailProvider:
    name = "my-company"

    def evaluate(self, request):
        from kkoclaw.guardrails.provider import GuardrailDecision, GuardrailReason

        # Example: block any bash command containing "delete"
        if request.tool_name == "bash" and "delete" in str(request.tool_input):
            return GuardrailDecision(
                allow=False,
                reasons=[GuardrailReason(code="custom.blocked", message="delete not allowed")],
                policy_id="custom.v1",
            )
        return GuardrailDecision(allow=True, reasons=[GuardrailReason(code="oap.allowed")])

    async def aevaluate(self, request):
        return self.evaluate(request)
```

**config.yaml:**
```yaml
guardrails:
  enabled: true
  provider:
    use: my_guardrail:MyGuardrailProvider
```

Ensure `my_guardrail.py` is on the Python path (e.g., in the backend directory or installed as a package).

**Try it:**
1. Create `my_guardrail.py` in the backend directory
2. Add the config
3. Start OClaw and ask: "Use bash to delete test.txt"
4. Your provider blocks it

## Implementing a Provider

### Required Interface

```
┌──────────────────────────────────────────────────┐
│              GuardrailProvider Protocol            │
│                                                   │
│  name: str                                        │
│                                                   │
│  evaluate(request: GuardrailRequest)              │
│      -> GuardrailDecision                         │
│                                                   │
│  aevaluate(request: GuardrailRequest)   (async)   │
│      -> GuardrailDecision                         │
└──────────────────────────────────────────────────┘

┌──────────────────────────┐    ┌──────────────────────────┐
│     GuardrailRequest      │    │    GuardrailDecision      │
│                           │    │                           │
│  tool_name: str           │    │  allow: bool              │
│  tool_input: dict         │    │  reasons: [GuardrailReason]│
│  agent_id: str | None     │    │  policy_id: str | None    │
│  thread_id: str | None    │    │  metadata: dict           │
│  is_subagent: bool        │    │                           │
│  timestamp: str           │    │  GuardrailReason:         │
│                           │    │    code: str              │
└──────────────────────────┘    │    message: str           │
                                └──────────────────────────┘
```

### OClaw Tool Names

These are the tool names your provider will see in `request.tool_name`:

| Tool | What it does |
|---|---|
| `bash` | Shell command execution |
| `write_file` | Create/overwrite files |
| `str_replace` | Edit files (find and replace) |
| `read_file` | Read file contents |
| `ls` | List directory |
| `web_search` | Web search queries |
| `web_fetch` | Fetch URL content |
| `image_search` | Image search |
| `present_files` | Show files to user |
| `view_image` | Display images |
| `ask_clarification` | Ask user questions |
| `task` | Delegate to subagent |
| `mcp__*` | MCP tools (dynamic) |

### OAP Reason Codes

Standard codes used by the [OAP specification](https://github.com/aporthq/aport-spec):

| Code | Meaning |
|---|---|
| `oap.allowed` | Tool call authorized |
| `oap.tool_not_allowed` | Tool not in allowlist |
| `oap.command_not_allowed` | Command not in allowed_commands |
| `oap.blocked_pattern` | Command matches a blocked pattern |
| `oap.limit_exceeded` | Operation exceeds limits |
| `oap.passport_suspended` | Passport status is suspended/revoked |
| `oap.evaluator_error` | Provider crashed (fail-closed) |

### Provider Loading

OClaw loads providers via `resolve_variable()` — the same mechanism used for models, tools, and sandbox providers. The `use:` field is a Python class path: `package.module:ClassName`.

If `config:` is set, the provider is instantiated with `**config` kwargs, always injecting `framework="kkoclaw"`. Accept `**kwargs` for forward compatibility:

```python
class YourProvider:
    def __init__(self, framework: str = "generic", **kwargs):
        # framework="kkoclaw" tells you which config directory to use
        ...
```

## Configuration Reference

```yaml
guardrails:
  # Enable/disable guardrail middleware (default: false)
  enabled: true

  # Block tool calls if provider throws exception (default: true)
  fail_closed: true

  # Passport reference — passed to provider as request.agent_id.
  # File path, hosted agent ID, or null (provider resolves from its config).
  passport: null

  # Provider: loaded via class path by resolve_variable
  provider:
    use: kkoclaw.guardrails.builtin:AllowlistProvider
    config:  # Optional kwargs passed to provider.__init__
      denied_tools: ["bash"]
```

## Testing

```bash
cd backend
uv run python -m pytest tests/test_guardrail_middleware.py -v
```

25 tests covering:
- AllowlistProvider: allow, deny, allowlist+denylist coexistence, async
- GuardrailMiddleware: allow pass-through, deny with OAP codes, fail-closed, fail-open, passport forwarding, empty reason fallback, empty tool name, protocol isinstance check
- Async paths: awrap_tool_call for allow, deny, fail-closed, fail-open
- GraphBubbleUp: LangGraph control signal propagation (not captured)
- Configuration: defaults, from_dict, singleton load/reset

## Files

```
packages/harness/kkoclaw/guardrails/
    __init__.py              # Public exports
    provider.py              # GuardrailProvider protocol, GuardrailRequest, GuardrailDecision
    middleware.py             # GuardrailMiddleware (AgentMiddleware subclass)
    builtin.py               # AllowlistProvider (zero dependencies)

packages/harness/kkoclaw/config/
    guardrails_config.py     # GuardrailsConfig Pydantic model + singleton

packages/harness/kkoclaw/agents/middlewares/
    tool_error_handling_middleware.py  # Registers GuardrailMiddleware in chain

config.example.yaml          # Documents all three provider options
tests/test_guardrail_middleware.py  # 25 tests
docs/GUARDRAILS.md           # This file
```

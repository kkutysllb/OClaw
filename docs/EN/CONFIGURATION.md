# Configuration Guide

This guide explains how to configure OClaw for your environment.

## Configuration Versioning

`config.example.yaml` contains a `config_version` field for tracking schema changes. When the example version is higher than your local `config.yaml`, the app warns at startup:

```
WARNING - Your config.yaml (version 0) is outdated — the latest version is 1.
Run `make config-upgrade` to merge new fields into your configuration.
```

- A config **missing `config_version`** is treated as version 0.
- Run `make config-upgrade` to automatically merge missing fields (your existing values are preserved, a `.bak` backup is created).
- When changing the config schema, update `config_version` in `config.example.yaml`.

## Configuration Sections

### Models

Configure the LLM models available to Agents:

```yaml
models:
  - name: gpt-4                    # Internal identifier
    display_name: GPT-4            # Human-readable name
    use: langchain_openai:ChatOpenAI  # LangChain class path
    model: gpt-4                   # Model identifier for the API
    api_key: $OPENAI_API_KEY       # API key (use environment variable)
    max_tokens: 4096               # Max tokens per request
    temperature: 0.7               # Sampling temperature
```

**Supported Providers**:
- OpenAI (`langchain_openai:ChatOpenAI`)
- Anthropic (`langchain_anthropic:ChatAnthropic`)
- DeepSeek (`langchain_deepseek:ChatDeepSeek`)
- Claude Code OAuth (`kkoclaw.models.claude_provider:ClaudeChatModel`)
- Codex CLI (`kkoclaw.models.openai_codex_provider:CodexChatModel`)
- Any LangChain-compatible provider

CLI-supported provider examples:

```yaml
models:
  - name: gpt-5.4
    display_name: GPT-5.4 (Codex CLI)
    use: kkoclaw.models.openai_codex_provider:CodexChatModel
    model: gpt-5.4
    supports_thinking: true
    supports_reasoning_effort: true

  - name: claude-sonnet-4.6
    display_name: Claude Sonnet 4.6 (Claude Code OAuth)
    use: kkoclaw.models.claude_provider:ClaudeChatModel
    model: claude-sonnet-4-6
    max_tokens: 4096
    supports_thinking: true
```

**Authentication Behavior for CLI-Supported Providers**:
- `CodexChatModel` loads Codex CLI credentials from `~/.codex/auth.json`
- The Codex Responses endpoint currently rejects `max_tokens` and `max_output_tokens`, so `CodexChatModel` does not expose a request-level token cap
- `ClaudeChatModel` accepts `CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR`, `CLAUDE_CODE_CREDENTIALS_PATH`, or plain `~/.claude/.credentials.json`
- On macOS, OClaw does not automatically probe Keychain. Use `scripts/export_claude_code_oauth.py` to explicitly export Claude Code credentials when needed

To use OpenAI's `/v1/responses` endpoint with LangChain, continue using `langchain_openai:ChatOpenAI` and set:

```yaml
models:
  - name: gpt-5-responses
    display_name: GPT-5 (Responses API)
    use: langchain_openai:ChatOpenAI
    model: gpt-5
    api_key: $OPENAI_API_KEY
    use_responses_api: true
    output_version: responses/v1
```

For OpenAI-compatible gateways (e.g., Novita or OpenRouter), continue using `langchain_openai:ChatOpenAI` and set `base_url`:

```yaml
models:
  - name: novita-deepseek-v3.2
    display_name: Novita DeepSeek V3.2
    use: langchain_openai:ChatOpenAI
    model: deepseek/deepseek-v3.2
    api_key: $NOVITA_API_KEY
    base_url: https://api.novita.ai/openai
    supports_thinking: true
    when_thinking_enabled:
      extra_body:
        thinking:
          type: enabled

  - name: minimax-m2.5
    display_name: MiniMax M2.5
    use: langchain_openai:ChatOpenAI
    model: MiniMax-M2.5
    api_key: $MINIMAX_API_KEY
    base_url: https://api.minimax.io/v1
    max_tokens: 4096
    temperature: 1.0  # MiniMax requires temperature in (0.0, 1.0]
    supports_vision: true

  - name: openrouter-gemini-2.5-flash
    display_name: Gemini 2.5 Flash (OpenRouter)
    use: langchain_openai:ChatOpenAI
    model: google/gemini-2.5-flash-preview
    api_key: $OPENAI_API_KEY
    base_url: https://openrouter.ai/api/v1
```

If your OpenRouter key is in a different env var name, point `api_key` to that variable explicitly (e.g., `api_key: $OPENROUTER_API_KEY`).

**Thinking Models**:
Some models support "thinking" mode for complex reasoning:

```yaml
models:
  - name: deepseek-v3
    supports_thinking: true
    when_thinking_enabled:
      extra_body:
        thinking:
          type: enabled
```

**Using Gemini with Thinking via OpenAI-Compatible Gateway**:

When routing Gemini through an OpenAI-compatible proxy (Vertex AI OpenAI-compatible endpoint, AI Studio, or third-party gateway) with thinking enabled, the API attaches a `thought_signature` to each tool call object in the response. Every subsequent request that replays those assistant messages **must** echo these signatures on the tool call entries, otherwise the API returns:

```
HTTP 400 INVALID_ARGUMENT: function call `<tool>` in the N. content block is
missing a `thought_signature`.
```

Standard `langchain_openai:ChatOpenAI` silently drops `thought_signature` when serializing messages. Use `kkoclaw.models.patched_openai:PatchedChatOpenAI` instead — it re-injects tool call signatures (sourced from `AIMessage.additional_kwargs["tool_calls"]`) into each outgoing payload:

```yaml
models:
  - name: gemini-2.5-pro-thinking
    display_name: Gemini 2.5 Pro (Thinking)
    use: kkoclaw.models.patched_openai:PatchedChatOpenAI
    model: google/gemini-2.5-pro-preview   # Model name expected by your gateway
    api_key: $GEMINI_API_KEY
    base_url: https://<your-openai-compat-gateway>/v1
    max_tokens: 16384
    supports_thinking: true
    supports_vision: true
    when_thinking_enabled:
      extra_body:
        thinking:
          type: enabled
```

For accessing Gemini **without** thinking enabled (e.g., via OpenRouter with thinking inactive), use plain `langchain_openai:ChatOpenAI` with `supports_thinking: false` — no patch needed.

### Tool Groups

Organize tools into logical groups:

```yaml
tool_groups:
  - name: web          # Web browsing and search
  - name: file:read    # Read-only file operations
  - name: file:write   # Write file operations
  - name: bash         # Shell command execution
```

### Tools

Configure specific tools available to Agents:

```yaml
tools:
  - name: web_search
    group: web
    use: kkoclaw.community.tavily.tools:web_search_tool
    max_results: 5
    # api_key: $TAVILY_API_KEY  # Optional
```

**Built-in Tools**:
- `web_search` - Search the web (DuckDuckGo, Tavily, Exa, InfoQuest, Firecrawl)
- `web_fetch` - Fetch web page content (Jina AI, Exa, InfoQuest, Firecrawl)
- `ls` - List directory contents
- `read_file` - Read file contents
- `write_file` - Write file contents
- `str_replace` - String replacement in files
- `bash` - Execute bash commands

### Sandbox

OClaw runs sandbox code directly on the host (local execution mode). Configure it in `config.yaml`:

```yaml
sandbox:
   use: kkoclaw.sandbox.local:LocalSandboxProvider
   allow_host_bash: false # Default; disables host bash unless explicitly re-enabled
```

`allow_host_bash` defaults to `false` intentionally. OClaw's local sandbox is a host-side convenience mode, not a secure shell isolation boundary. Only set `allow_host_bash: true` for fully trusted single-user local workflows.

### Skills

Configure skill directories for specialized workflows:

```yaml
skills:
  # Host path (optional, default: ../skills)
  path: /custom/path/to/skills

  # Container mount path (default: /mnt/skills)
  container_path: /mnt/skills
```

**How Skills Work**:
- Skills are stored in `kk-oclaw/skills/{public,custom}/`
- Each skill has a `SKILL.md` file containing metadata
- Skills are automatically discovered and loaded
- Available in the local sandbox via path mapping

**Per-Agent Skill Filtering**:
Custom agents can restrict loaded skills by defining a `skills` field in their `config.yaml` (located at `workspace/agents/<agent_name>/config.yaml`):
- **Omitted or `null`**: Load all globally enabled skills (default fallback).
- **`[]` (empty list)**: Disable all skills for this specific agent.
- **`["skill-name"]`**: Only load the explicitly specified skills.

### Title Generation

Automatic conversation title generation:

```yaml
title:
  enabled: true
  max_words: 6
  max_chars: 60
  model_name: null  # Use the first model in the list
```

### GitHub API Token (Optional for GitHub Deep Research Skill)

Default GitHub API rate limits are quite restrictive. For frequent project research, we recommend configuring a read-only Personal Access Token (PAT).

**Configuration Steps**:
1. Uncomment the `GITHUB_TOKEN` line in the `.env` file and add your PAT
2. Restart OClaw service to apply changes

## Environment Variables

OClaw supports environment variable substitution using the `$` prefix:

```yaml
models:
  - api_key: $OPENAI_API_KEY  # Read from environment
```

**Common Environment Variables**:
- `OPENAI_API_KEY` — OpenAI API key
- `ANTHROPIC_API_KEY` — Anthropic API key
- `DEEPSEEK_API_KEY` — DeepSeek API key
- `NOVITA_API_KEY` — Novita API key (OpenAI-compatible endpoint)
- `TAVILY_API_KEY` — Tavily Search API key
- `OClaw_PROJECT_ROOT` — Project root for relative runtime paths
- `OClaw_CONFIG_PATH` — Custom config file path
- `OClaw_EXTENSIONS_CONFIG_PATH` — Custom extensions config file path
- `OClaw_HOME` — Runtime state directory (defaults to `.kkoclaw` under project root)
- `OClaw_SKILLS_PATH` — Skills directory when `skills.path` is omitted
- `GATEWAY_ENABLE_DOCS` — Set to `false` to disable Swagger UI (`/docs`), ReDoc (`/redoc`), and OpenAPI schema (`/openapi.json`) endpoints (default: `true`)

## Configuration Location

The configuration file should be placed in the **project root** (`kk-oclaw/config.yaml`). Set `OClaw_PROJECT_ROOT` when processes may start from other working directories, or set `OClaw_CONFIG_PATH` to point to a specific file.

## Configuration Priority

OClaw searches for configuration in this order:

1. Path specified via the `config_path` parameter in code
2. Path from the `OClaw_CONFIG_PATH` environment variable
3. `config.yaml` under `OClaw_PROJECT_ROOT`, or under the current working directory if `OClaw_PROJECT_ROOT` is not set
4. Legacy backend/repository-root locations for monorepo compatibility

## Best Practices

1. **Place `config.yaml` in the project root** — set `OClaw_PROJECT_ROOT` if launching from elsewhere
2. **Never commit `config.yaml`** — it is already in `.gitignore`
3. **Use environment variables for secrets** — don't hardcode API keys
4. **Keep `config.example.yaml` up to date** — document all new options
5. **Test configuration changes locally** — before deploying

## Troubleshooting

### "Configuration file not found"
- Ensure `config.yaml` exists in the **project root** (`kk-oclaw/config.yaml`)
- Set `OClaw_PROJECT_ROOT` if launching from outside the project root
- Or set the `OClaw_CONFIG_PATH` environment variable to point to a custom location

### "Invalid API key"
- Verify environment variables are correctly set
- Check that environment variable references use the `$` prefix

### "Skills not loading"
- Check if the `kk-oclaw/skills/` directory exists
- Verify skills have valid `SKILL.md` files
- If using a custom path, check `skills.path` or `OClaw_SKILLS_PATH`

## Examples

See `config.example.yaml` for a complete example of all configuration options.

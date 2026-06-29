# MCP (Model Context Protocol) Configuration

OClaw supports configurable MCP servers and skills to extend its capabilities, loaded from a dedicated `extensions_config.json` file in the project root.

## Setup

1. Copy `extensions_config.example.json` to `extensions_config.json` in the project root.
   ```bash
   # Copy example configuration
   cp extensions_config.example.json extensions_config.json
   ```

2. Enable desired MCP servers or skills by setting `"enabled": true`.
3. Configure each server's command, arguments, and environment variables as needed.
4. Restart the application to load and register MCP tools.

## OAuth Support (HTTP/SSE MCP Servers)

For `http` and `sse` MCP servers, OClaw supports OAuth token acquisition and automatic token refresh.

- Supported grant types: `client_credentials`, `refresh_token`
- Configure the `oauth` block per server in `extensions_config.json`
- Secrets should be provided via environment variables (e.g., `$MCP_OAUTH_CLIENT_SECRET`)

Example:

```json
{
   "mcpServers": {
      "secure-http-server": {
         "enabled": true,
         "type": "http",
         "url": "https://api.example.com/mcp",
         "oauth": {
            "enabled": true,
            "token_url": "https://auth.example.com/oauth/token",
            "grant_type": "client_credentials",
            "client_id": "$MCP_OAUTH_CLIENT_ID",
            "client_secret": "$MCP_OAUTH_CLIENT_SECRET",
            "scope": "mcp.read",
            "refresh_skew_seconds": 60
         }
      }
   }
}
```

## Custom Tool Interceptors

You can register custom interceptors that run before each MCP tool invocation. This is useful for injecting per-request headers (e.g., user auth tokens from LangGraph execution context), logging, or metrics collection.

Declare interceptors using the `mcpInterceptors` field in `extensions_config.json`:

```json
{
  "mcpInterceptors": [
    "my_package.mcp.auth:build_auth_interceptor"
  ],
  "mcpServers": { ... }
}
```

Each entry is a Python import path in `module:variable` format (resolved via `resolve_variable`). The variable must be a **parameterless builder function** that returns an async interceptor compatible with `MultiServerMCPClient`'s `tool_interceptors` interface, or returns `None` to skip.

Example interceptor that injects an auth header from LangGraph metadata:

```python
def build_auth_interceptor():
    async def interceptor(request, handler):
        from langgraph.config import get_config
        metadata = get_config().get("metadata", {})
        headers = dict(request.headers or {})
        if token := metadata.get("auth_token"):
            headers["X-Auth-Token"] = token
        return await handler(request.override(headers=headers))
    return interceptor
```

- Single string values are accepted and normalized to single-element lists.
- Invalid paths or builder function failures log a warning without blocking other interceptors.
- Builder function return values must be `callable`; non-callable values are skipped with a warning.

## How It Works

Tools exposed by MCP servers are automatically discovered and integrated into OClaw's Agent system at runtime. Once enabled, these tools become available to Agents without additional code changes.

## Capability Examples

MCP servers can provide access to:

- **File systems**
- **Databases** (e.g., PostgreSQL)
- **External APIs** (e.g., GitHub, Brave Search)
- **Browser automation** (e.g., Puppeteer)
- **Custom MCP server implementations**

## Learn More

For detailed documentation on the Model Context Protocol, visit:
https://modelcontextprotocol.io

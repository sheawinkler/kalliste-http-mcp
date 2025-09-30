# kalliste-alpha (memory service)

Runs an MCP stack with HTTP-only endpoints.
- Primary proxy: `http://127.0.0.1:8011/mcp/` (POST JSON-RPC)
- MCP headers: `Accept: application/json, text/event-stream`, `Content-Type: application/json`, `MCP-Protocol-Version: 2025-06-18`

Quickstart:
```bash
gmake mem          # restart → ping → ps → short logs
gmake mem-ping     # initialize + tools/list to :8011/mcp/
More details: See docs/README.mcp-http.md.

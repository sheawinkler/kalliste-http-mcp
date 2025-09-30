# MCP (HTTP-only) quickstart

This project exposes a Model Context Protocol server over **Streamable HTTP**.
**Send each JSON-RPC message as an HTTP POST** to the MCP endpoint, and include:

- `Accept: application/json, text/event-stream`
- `Content-Type: application/json`
- `MCP-Protocol-Version: 2025-06-18`

**Endpoint:** `http://127.0.0.1:8011/mcp/`

Examples: curl -fsS http://127.0.0.1:8011/mcp/ \
  -H 'accept: application/json, text/event-stream' \
  -H 'content-type: application/json' \
  -H 'MCP-Protocol-Version: 2025-06-18' \
  -d '{"jsonrpc":"2.0","id":"init-1","method":"initialize","params":{"protocolVersion":"2025-06-18","clientInfo":{"name":"kalliste-alpha","version":"dev"}}}}'

# list tools
curl -fsS http://127.0.0.1:8011/mcp/ \
  -H 'accept: application/json, text/event-stream' \
  -H 'content-type: application/json' \
  -H 'MCP-Protocol-Version: 2025-06-18' \
  -d '{"jsonrpc":"2.0","id":"tools-1","method":"tools/list","params":{}}'
Notes:
	•	MCP spec (v2025-06-18) requires POST to the single MCP endpoint, with Accept listing both JSON and event-stream.  ￼
	•	MindsDB’s MCP is enabled at path /mcp/ by default; your proxy mirrors that path on :8011.  ￼
	•	Supergateway’s Streamable HTTP path defaults to /mcp but is configurable; we standardized to /mcp/ to eliminate trailing-slash gotchas.  ￼

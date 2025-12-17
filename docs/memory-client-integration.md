# Client Integration Guide

Use the MCP hub (`http://127.0.0.1:53130/mcp`) as the single endpoint for every IDE agent or CLI. It fans out to Memory Bank, Qdrant, MindsDB, and future tools without reconfiguring each client.

### Fast install

Run `scripts/install_mcp_clients.sh` to copy the templates in `configs/` to all default locations (Windsurf, Cline, Cursor, Claude). Set `WINDSURF_CONF`, `CLINE_CONF`, etc., before running if you keep configs elsewhere. Restart each IDE afterward.

## Shared MCP settings

```
Base URL: http://127.0.0.1:53130/mcp
Transport: streamable-http (accept: application/json, text/event-stream)
Headers:
  MCP-Protocol-Version: 2024-11-05
  MCP-Transport: streamable-http
```

If a client does not expose raw headers, point it to the orchestrator HTTP shim instead: `http://127.0.0.1:8075` (see the Trae example below).

## Windsurf

1. Open `~/.codeium/windsurf/mcp_config.json` (path from `.env:WINDSURF_CONF`).
2. Add an entry:
   ```json
   {
     "name": "memmcp",
     "transport": "streamable-http",
     "url": "http://127.0.0.1:53130/mcp"
   }
   ```
3. Restart Windsurf or reload MCP servers.

## Cline (VS Code)

1. Open the `cline.mcp.json` (command palette → “Cline: Open MCP Config”).
2. Append:
   ```json
   {
     "name": "memmcp",
     "type": "http",
     "serverUrl": "http://127.0.0.1:53130/mcp"
   }
   ```
3. Save and run `Cline: Reload MCP Servers`.

## Cursor IDE

1. Edit `~/Library/Application Support/Cursor/User/globalStorage/mcp-servers.json` (or use the MCP UI panel).
2. Add the same HTTP entry as above. Cursor v0.42+ autodetects streamable-http and will reuse the single endpoint for every workspace.

## Claude Code / Claude Desktop

Claude’s MCP beta looks for `~/.mcp/servers.json`:
```json
{
  "servers": [
    {
      "name": "memmcp",
      "type": "http",
      "serverUrl": "http://127.0.0.1:53130/mcp"
    }
  ]
}
```
Restart Claude Code and verify the “memmcp” toolset appears in the MCP panel.

## Trae Agent + Ollama (lightweight)

1. Edit `~/.trae_agent/trae_config.yaml` (or copy from `trae_config.template.yaml`).
2. Set the default client to the local Ollama shim via the `ollama_openai` provider:
   ```yaml
   model_providers:
     ollama_openai:
       provider: openai
       api_key: local-demo
       base_url: http://127.0.0.1:11434/v1
     lmstudio:
       provider: openai
       api_key: local
       base_url: http://localhost:1234/v1

   models:
     qwen_small:
       model_provider: ollama_openai
       model: llama3.2:1b
   ```
   - Use `llama3.2:1b` or any other model you have pulled (`ollama pull llama3.2:1b`).
   - Increase `max_steps` in the task block if Trae needs more thinking time.
3. Point the MCP target at the hub:
   ```yaml
   mcp_servers:
     memory:
       transport: http
       url: http://127.0.0.1:53130/mcp
   ```
4. To switch back to LM Studio or a hosted OpenAI-compatible API, change the `base_url` under `model_providers.lmstudio` (or add another provider) and point the desired model at it.
5. Run `trae-cli run --config ~/.trae_agent/trae_config.yaml`.

## Self-test checklist

- `curl -fsS http://127.0.0.1:8075/status | jq` → memory-bank + qdrant healthy.
- `curl -fsS http://127.0.0.1:59081/mcp/tools/list` (with MCP headers) → shows memory-bank toolset.
- From each IDE, run a “list projects” tool and ensure results match `~/Documents/Projects` memories.

Keep this file updated as we bring more clients online.

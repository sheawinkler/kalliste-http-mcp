# Memory Supergateway Startup

The stack now runs entirely from the project root via Docker Compose.

## 1. Bring everything up

```bash
docker compose up -d --build
```

If you need a clean slate before starting:

```bash
docker compose down --remove-orphans
```

## 2. Watch health

```bash
docker compose ps
```

Key services and ports:

- Qdrant API: `http://127.0.0.1:6333/readyz`
- Memory MCP (supergateway): `http://127.0.0.1:59081/mcp`
- MindsDB HTTP proxy (FastMCP): `http://127.0.0.1:8004/mcp`
- Langfuse UI: `http://127.0.0.1:15510`
- Promptfoo UI: `http://127.0.0.1:15500`
- MCP hub (tbxark proxy): `http://127.0.0.1:53130`

## 3. Logs & debugging

```bash
docker compose logs -f <service>
```

Useful log targets: `mcp-hub`, `memorymcp-http`, `mindsdb-http-proxy`, `langfuse`, `promptfoo`.

## 4. Tear down

```bash
docker compose down
```

Volumes are persisted for Qdrant, MindsDB, Langfuse Postgres/ClickHouse, Mongo (memory bank), and Letta.

## Memory MCP troubleshooting note

If the memory MCP gateway crashes with repeated `write EPIPE` errors immediately after clients call `initialize`, ensure the container launches the MCP server via `npx`. The fixed `Dockerfile.memorymcp` now runs:

```
supergateway \
  --stdio 'npx -y @allpepper/memory-bank-mcp' \
  --outputTransport streamableHttp \
  --port ${MEMORYMCP_HTTP_PORT:-59081} \
  --streamableHttpPath /mcp
```

The previous command (`--stdio 'memory-bank-mcp'`) referenced a non-existent binary inside the image, causing the stdio pipe to close and supergateway to exit. Rebuild the image and restart the service to pick up the fix:

```bash
docker compose build memorymcp-http
docker compose up -d memorymcp-http
```

To validate the endpoint, send an `initialize` request with both `accept: application/json, text/event-stream` and `MCP-Transport: streamable-http` headers, then call `tools/list` to ensure the five memory-bank tools load correctly.

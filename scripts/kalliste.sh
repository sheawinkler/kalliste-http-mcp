#!/usr/bin/env bash
set -euo pipefail

echo ">> writing configs/mcp-proxy.config.json"
cat > configs/mcp-proxy.config.json <<'JSON'
{
  "listen": "0.0.0.0:9090",
  "servers": [
    { "name": "qdrant-adv", "transportType": "streamable-http", "url": "http://mcp-qdrant-adv:8022/mcp" },
    { "name": "qdrant",     "transportType": "streamable-http", "url": "http://mcp-qdrant:8000/mcp" },
    { "name": "mindsdb",    "transportType": "streamable-http", "url": "http://mindsdb-http-proxy:8011/mcp" }
  ]
}
JSON

echo ">> writing docker-compose.override.yml (adds mcp-proxy service)"
cat > docker-compose.override.yml <<'YML'
services:
  mcp-proxy:
    image: ghcr.io/tbxark/mcp-proxy:latest
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./configs/mcp-proxy.config.json:/config/config.json:ro
    command: ["--config", "/config/config.json"]
YML

echo ">> bringing up mcp-proxy ..."
docker compose up -d --build --remove-orphans mcp-proxy

echo ">> probing proxy status on :9090"
if ! curl -fsS http://127.0.0.1:9090/status >/dev/null 2>&1; then
  echo "WARN: proxy status endpoint unavailable; continuing"
fi

echo ">> All set. Point IDE/agents at: http://127.0.0.1:9090/servers/<name>/mcp"

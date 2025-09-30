.RECIPEPREFIX := >
SHELL := /bin/bash
COMPOSE := docker compose

MEM_FILES := \
  -f docker-compose.yml \
  -f docker-compose.override.http.yml \
  -f docker-compose.override.vols.yml \
  -f docker-compose.override.stackfix.yml \
  -f docker-compose.mcp-qdrant.http.yml \
  -f docker-compose.memorymcp-http.build.yml \
  -f docker-compose.mcp-proxy.yml \
  -f docker-compose.mindsdb.yml \
  -f docker-compose.mindsdb-http-proxy.yml \
  -f docker-compose.mindsdb.volumes.yml \
  -f docker-compose.volumes.fix.yml \
  -f docker-compose.disable.legacy.yml \
  -f docker-compose.memorymcp-http.cmdforce.yml \
  -f docker-compose.mcp-proxy.depfix.yml \
  -f docker-compose.health.disable.yml

.PHONY: mem-up
mem-up:
> $(COMPOSE) $(MEM_FILES) up -d --remove-orphans
> @$(COMPOSE) $(MEM_FILES) ps

.PHONY: mem-restart
mem-restart:
> $(COMPOSE) $(MEM_FILES) up -d --force-recreate --remove-orphans

.PHONY: mem-down
mem-down:
> $(COMPOSE) $(MEM_FILES) down

.PHONY: mem-ps
mem-ps:
> $(COMPOSE) $(MEM_FILES) ps

.PHONY: mem-logs
mem-logs:
> $(COMPOSE) $(MEM_FILES) logs -f --tail=200

MEM_FILES += \
  -f docker-compose.memorymcp-http.port.yml

.PHONY: mem-smoke
mem-smoke:
> @echo "→ MCP /mcp POST ping"
> @curl -sS -o /dev/null -w "%{http_code}\n" \
>   -H 'accept: application/json' -H 'content-type: application/json' \
>   -d '{"jsonrpc":"2.0","id":"ping","method":"ping","params":{}}' \
>   http://127.0.0.1:59081/mcp
> @echo "→ mcp-proxy :9090"
> @curl -sS -o /dev/null -D - http://127.0.0.1:9090/ | head -n 1 || true

MEM_FILES += \
  -f docker-compose.memorymcp-http.port.yml

.PHONY: mem
mem: mem-restart mem-smoke mem-ps mem-logs-short

.PHONY: mem-smoke
mem-smoke:
> @echo "→ MCP /mcp POST ping (expect 200/204/404 but not connection refused)"
> @curl -sS -o /dev/null -w "%{http_code}\n" \
>   -H 'accept: application/json' -H 'content-type: application/json' \
>   -d '{"jsonrpc":"2.0","id":"ping","method":"ping","params":{}}' \
>   http://127.0.0.1:59081/mcp || true
> @echo "→ mcp-proxy :9090 (expect HTTP/1.1 line)"
> @curl -sS -o /dev/null -D - http://127.0.0.1:9090/ | head -n 1 || true

.PHONY: mem-logs-short
mem-logs-short:
> @$(COMPOSE) $(MEM_FILES) logs --tail=60 memorymcp-http

.PHONY: mem-status
mem-status:
> @$(COMPOSE) $(MEM_FILES) ps
> @for s in memorymcp-http mcp-qdrant mindsdb-http-proxy mcp-proxy; do \
>   cid="$$(docker ps -q --filter label=com.docker.compose.service=$$s)"; \
>   if [ -n "$$cid" ]; then \
>     echo "=== $$s :: files ==="; \
>     docker inspect -f '{{json .Config.Labels}}' "$$cid" | jq -r '."com.docker.compose.config-files"'; \
>   fi; \
> done

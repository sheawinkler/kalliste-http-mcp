# kalliste-alpha

> **Elevator pitch**  
> Kalliste-alpha is a **local-first memory service** for AI agents that exposes a **clean HTTP-only Model Context Protocol (MCP)** endpoint at `/mcp/`. It stitches together a fast vector store (Qdrant), an MCP super-gateway (streamable HTTP), and a lightweight MindsDB HTTP proxy so tools & memory feel like one coherent service—launchable with one command.  
> **Business plan:** the repo is open for **local use**, and we’ll offer **Kalliste Cloud** — a hosted, subscription service with seat-based plans, metered usage (requests/bytes/storage), SSO/SAML, RBAC, SLAs, and managed upgrades. Local remains free; the cloud adds enterprise-grade features.

---

## Why this exists

Most “agent memory” stacks sprawl across stdio, SSE, and bespoke ports. Kalliste-alpha standardizes on **HTTP-only MCP** so any client can POST JSON-RPC to one endpoint and get JSON or event streams—no shell transports, minimal glue. It’s designed for **macOS-friendly** local dev and a straight path to **cloud-hosted** subscriptions.

---

## Key capabilities

- **HTTP-only MCP** at `http://127.0.0.1:8011/mcp/` (no direct stdio/SSE wiring)  
- **Super-gateway (streamable HTTP)** wraps stdio MCP servers behind HTTP when needed  
- **MindsDB HTTP proxy** that surfaces MCP actions for orchestration  
- **Qdrant** as the vector memory backend (internal service DNS: `http://qdrant:6333`)  
- **mcp-proxy** routing with JSON config under `configs/`  
- **One-liner bring-up** via Docker Compose and `gmake mem`  
- **macOS-friendly scripts** (avoid bash-only `shopt`; no sed/awk required)  
- **Consistent env management**: Compose loads `.env` from the project dir (we symlink it into `infra/compose/`)  
- **Health checks & smoke pings** (HTTP only)  
- **Roadmap scaffolding** for metering, quotas, billing, SSO/SAML, RBAC, and observability  
- **Dev ergonomics**: Make targets for `up`, `ps`, logs, foreground mode, and HTTP pings

> **Qdrant host port policy (final decision):**  
> We **do not publish** Qdrant on the host. Qdrant listens on **:6333 inside the Compose network** as `http://qdrant:6333`.  
> - On Compose ≥ 2.24.4 we remove host port publishing entirely (ports reset).  
> - On older Compose we fallback to **host `6334:6333`** (no host `:6333`).  
> If you really need host access, add a local override that publishes a port explicitly.

---

## Quickstart

### Prerequisites
- Docker Desktop (Compose v2)
- `gmake`, `jq`, `rg` (ripgrep), `python3`, `curl`
- macOS 13+ (tested)
- GitHub CLI `gh` (optional, for publishing)

### 1) Configure env

Create a **root** `.env`:

~~~ini
# .env
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=windsurf-memory
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
MINDSDB_APIS=http,mysql
MINDS_HTTP_PORT=47334
MINDSDB_MCP_PORT=47337
~~~

Make sure Compose sees it from the project dir:

~~~bash
ln -svf ../../.env infra/compose/.env
~~~

### 2) Run the stack

~~~bash
gmake mem         # detached
gmake mem-ps      # status
gmake mem-logs    # follow logs
gmake mem-up-fg   # foreground (CTRL-C to stop)
~~~

### 3) Verify HTTP-only MCP

~~~bash
curl -fsS http://127.0.0.1:8011/mcp/ \
  -H 'accept: application/json, text/event-stream' \
  -H 'content-type: application/json' \
  -H 'MCP-Protocol-Version: 2025-06-18' \
  -d '{"jsonrpc":"2.0","id":"tools-1","method":"tools/list","params":{}}' | jq .
~~~

---

## Project layout

~~~
infra/compose/          # compose files (the first -f defines project dir)
configs/                # runtime configs (e.g., mcp-proxy.config.json)
scripts/                # helper scripts (e.g., mindsdb_http_proxy.py)
data/memory-bank/       # on-disk memory (bind mounted)
docs/                   # roadmap, notes
mk/memory.mk            # make targets (mem, mem-ps, mem-logs, mem-up-fg, mem-ping)
.compose.args           # auto-generated: ordered -f list for compose
~~~

## Make targets (selection)

- `mem` — compose up (detached)  
- `mem-ps` — service status  
- `mem-logs` — follow logs (`-f --tail=200`)  
- `mem-up-fg` — foreground up (dev)  
- `mem-ping` — HTTP JSON-RPC ping to `/mcp/` with headers

> If Make warns “overriding recipe,” you have duplicate targets—keep the **last** definition in `mk/memory.mk`.

---

## Troubleshooting

- **“.env variables defaulting to blank”** — Compose reads `.env` from the **project directory** (folder of the **first** `-f` file). We symlink `infra/compose/.env → ../../.env`. Alternatively run with `--project-directory . --env-file .env`.  
- **“Port 6333 already allocated”** — We ship an override to **remove** host publishing of `6333` (Compose `!reset`) or remap to `6334:6333` on older Compose. Internally, keep using `http://qdrant:6333`.  
- **Services stuck at “created/starting”** — `docker compose $(cat .compose.args) logs -f memorymcp-http mcp-qdrant mindsdb-http-proxy` and look for healthcheck errors or missing deps.

---

## Roadmap (abridged; see `docs/ROADMAP.md` for step-by-step)

- **Metering & quotas:** per-call/byte/storage, WAL → rollups → Stripe meters  
- **Auth & RBAC:** OAuth/OIDC, SAML, project API keys, roles (owner/admin/member/viewer)  
- **Billing:** seat + org + usage overages, dunning, entitlements cache  
- **Observability:** Prometheus exporter, Grafana dashboards, alerting  
- **Enterprise ops:** backups/restore (S3/GCS), retention, audit export, on-prem profile, SLA runbooks

---

## Business & licensing

- **Open core:** repo open for local usage; hosted **Kalliste Cloud** on subscription  
  - Free local: HTTP MCP, vector memory, proxy, single-node  
  - Pro/Team: SSO/SAML, RBAC, metering/quotas, managed scaling, SLAs, priority support  
- **License:** recommend **BSL 1.1** (converts to Apache-2.0 at a future change date). If you need OSI copyleft for the repo, consider **AGPLv3** with commercial exceptions for hosted use.  
  > The `LICENSE` file in this repo is the source of truth.

---

## Security & privacy (initial posture)

- Project-scoped API tokens; least-privilege defaults  
- Rate-limits per token and IP; structured audit logs  
- Secrets in `.env` locally; cloud uses a secret manager

---

## Contributing

PRs welcome for docs, examples, adapters, MCP tool shims, and observability. Please run `gmake mem` + the HTTP smoke ping before submitting.

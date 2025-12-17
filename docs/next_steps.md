# Next Steps

1. **Roll MCP wiring to every client**  
   - Run `scripts/install_mcp_clients.sh` (override `WINDSURF_CONF`, `CLINE_CONF`, etc. if your configs live elsewhere).  
   - Restart Windsurf, Cline, Cursor, and Claude Code; from each, call the `list_projects` tool against `http://127.0.0.1:53130/mcp` to verify they share the same memory service.

2. **Exercise Trae on the lightweight Ollama endpoint**  
   - Copy `trae_config.template.yaml` to `~/.trae_agent/trae_config.yaml` if needed.  
   - Confirm Ollama has `llama3.2:1b` pulled (`ollama pull llama3.2:1b`).  
   - Run `trae-cli run --config ~/.trae_agent/trae_config.yaml` and check that memories and trajectories log via the memMCP hub.

3. **Dry-run the hosted deployment path**  
   - On a spare VM (or locally via kind), run `scripts/deploy_hosted_core.sh <domain> <email>` to launch the `core` profile and the Caddy proxy.  
   - Point a test domain (or `/etc/hosts` entry) to the VM and `curl https://<domain>/mcp/tools/list` to ensure TLS + routing works.  
   - Once satisfied, add the `observability` profile (Langfuse + Promptfoo) with `docker compose --profile core --profile observability up -d` for a full paid-tier rehearsal.

4. **Document & publish**  
   - Capture screenshots or recordings of the above flows for your portfolio.  
   - When ready to share publicly, push `dev/low-cost-deployment` to GitHub (already synced) and tag a release candidate for reviewers.

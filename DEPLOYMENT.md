# CyberGuard AI — Deployment Guide

## Architecture overview

| Layer | Technology | Notes |
|-------|-----------|-------|
| Frontend | Next.js → Cloudflare Pages | Auto-deploys on push to `main` |
| Backend API | .NET 8 (ASP.NET Core) | Port 8000, behind Caddy |
| Python services | 5 FastAPI microservices | Agentic RAG, embeddings, PDF, search, advisory |
| LLM | Ollama (`llama3.2:1b`) | Runs inside Docker |
| Vector / full-text search | OpenSearch | Port 9200 (internal only in prod) |
| Observability | Langfuse | Port 3001 (internal only in prod) |
| Reverse proxy | Caddy | Terminates TLS, routes traffic |
| Server access | Tailscale VPN | GitHub Actions SSHs in via ephemeral key |

---

## Prerequisites (production server)

```bash
# Install Docker + Compose plugin
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Install Caddy
sudo apt install -y caddy    # or follow https://caddyserver.com/docs/install

# Clone repo
git clone https://github.com/LakshayBot/AgenticRAG.git
cd AgenticRAG

# Create external network (only needed once)
docker network create rag-network
```

---

## Environment file

Copy and fill in `.env`:

```bash
cp .env.example .env
nano .env
```

**Required variables:**

| Variable | Description |
|----------|-------------|
| `JWT_SECRET_KEY` | Long random string for JWT signing |
| `POSTGRES_DATABASE_URL` | PostgreSQL connection string |
| `LANGFUSE_NEXTAUTH_SECRET` | Langfuse auth secret |
| `LANGFUSE_SALT` | Langfuse password hash salt |
| `LANGFUSE_ENCRYPTION_KEY` | Langfuse encryption key |
| `ENVIRONMENT` | Set to `Production` for .NET JWT config |
| `OLLAMA_MODEL` | Default: `llama3.2:1b` |
| `API_PUBLIC_URL` | e.g. `cyberguardapi.lakshaycodes.dev` |

Secrets that need rotation before first deploy:
- `JINA_API_KEY` — get a new key at jina.ai
- `GITHUB_TOKEN` — generate a new PAT
- `TELEGRAM__BOT_TOKEN` — rotate via @BotFather
- `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` — regenerate in Langfuse UI

---

## Manual deployment

```bash
./deploy.sh
# Choose: 2 (Production)
```

The script will:
1. Validate `.env` and check for placeholder secrets
2. Ensure `rag-network` exists
3. Build all Docker images in parallel
4. Stop existing containers gracefully
5. Start all services
6. Wait for health checks on 6 critical containers
7. Pull the Ollama model if not present
8. Run OpenSearch index setup
9. Verify Caddy is running

---

## Caddy configuration

`/etc/caddy/Caddyfile`:

```
cyberguardapi.lakshaycodes.dev {
    reverse_proxy localhost:8000
}

# Optional: Langfuse UI behind auth / private subdomain
langfuse.yourdomain.dev {
    reverse_proxy localhost:3001
}
```

```bash
sudo systemctl reload caddy
```

---

## CI/CD (GitHub Actions)

Workflow file: `.github/workflows/deploy.yml`

Triggers on every push to `main`. The frontend is **not** part of this workflow — Cloudflare Pages handles it automatically.

### Required GitHub Secrets

Go to **Settings → Secrets → Actions** and add:

| Secret | Value |
|--------|-------|
| `TAILSCALE_OAUTH_CLIENT_ID` | Tailscale OAuth client ID (from tailscale.com/settings/oauth) |
| `TAILSCALE_OAUTH_CLIENT_SECRET` | Tailscale OAuth client secret |
| `PROD_HOST` | Tailscale IP of your server (e.g. `100.x.x.x`) |
| `PROD_USER` | SSH user on the server (e.g. `ubuntu`) |
| `PROD_SSH_KEY` | Private SSH key (the server must have the matching public key in `~/.ssh/authorized_keys`) |
| `PROD_REPO_DIR` | Absolute path to the cloned repo (e.g. `/home/ubuntu/AgenticRAG`) |

### Setting up Tailscale OAuth for CI

1. Go to https://login.tailscale.com/admin/settings/oauth
2. Create a new OAuth client with the `devices:write` scope and tag `tag:ci`
3. Add `"tag:ci"` to your ACL's `tagOwners` in the Tailscale admin console
4. Store the client ID and secret as GitHub secrets

### How the deploy works

1. GitHub Actions runner connects to Tailscale using an ephemeral OAuth key (no key rotation needed)
2. SSH into the private server via its Tailscale IP
3. `git reset --hard origin/main` — pulls latest code
4. `docker compose build --parallel` — rebuilds only changed images
5. `docker compose up -d` — recreates only containers whose image/config changed (zero-downtime for unchanged services)
6. Health checks confirm all critical services are up before the job completes

---

## Useful commands

```bash
# View logs for all services
docker compose -f docker-compose.yml logs -f

# View logs for a specific service
docker compose -f docker-compose.yml logs -f agentic-rag-service

# Restart a single service
docker compose -f docker-compose.yml restart dotnet-api

# Check container health
docker ps --format "table {{.Names}}\t{{.Status}}"

# Pull a new Ollama model
docker exec rag-ollama ollama pull llama3.2:3b

# Re-run OpenSearch index setup
docker exec rag-agentic-service python /app/scripts/setup_opensearch_index.py
```

---

## Troubleshooting

**agentic-rag-service unhealthy**
```bash
docker logs rag-agentic-service --tail 50
# Common cause: OpenSearch not ready yet — wait 30s and run deploy.sh again
```

**advisory-service unhealthy**
```bash
docker logs rag-advisory-service --tail 50
# Health endpoint: GET /api/v1/advisories/health
```

**JINA_API_KEY 403 errors**
BM25 fallback is active — hybrid search is degraded but still functional. Rotate the key at jina.ai to restore full quality.

**JWT auth failures**
Ensure `ENVIRONMENT=Production` is set in `.env` so ASP.NET Core reads `appsettings.Production.json` (contains OAuth credentials).

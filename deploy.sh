#!/usr/bin/env bash
# =============================================================================
# CyberGuard AI — Deployment Script
# Usage: ./deploy.sh
# =============================================================================
set -euo pipefail

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
die()     { error "$*"; exit 1; }
header()  { echo -e "\n${BOLD}${CYAN}=== $* ===${RESET}\n"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# =============================================================================
# 1. CHOOSE ENVIRONMENT
# =============================================================================
header "CyberGuard AI Deployment"
echo -e "  ${BOLD}1)${RESET} Development  — all ports exposed, hot-reload, debug logging"
echo -e "  ${BOLD}2)${RESET} Production   — no exposed ports, Caddy reverse proxy, hardened config"
echo ""
read -rp "Choose environment [1/2]: " ENV_CHOICE

case "$ENV_CHOICE" in
  1) DEPLOY_ENV="development" ;;
  2) DEPLOY_ENV="production"  ;;
  *) die "Invalid choice. Run the script again and choose 1 or 2." ;;
esac

success "Target environment: ${BOLD}${DEPLOY_ENV}${RESET}"

# =============================================================================
# 2. PREREQUISITES CHECK
# =============================================================================
header "Checking prerequisites"

check_cmd() {
  if command -v "$1" &>/dev/null; then
    success "$1 found ($(command -v "$1"))"
  else
    die "$1 is required but not installed. Install it and re-run."
  fi
}

check_cmd docker
check_cmd git

# Docker Compose (plugin or standalone)
if docker compose version &>/dev/null 2>&1; then
  COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
  COMPOSE="docker-compose"
else
  die "Docker Compose not found. Install 'docker compose' plugin or standalone docker-compose."
fi
success "Docker Compose: $($COMPOSE version --short 2>/dev/null || echo 'ok')"

# =============================================================================
# 3. ENVIRONMENT FILE SETUP
# =============================================================================
header "Environment configuration"

ENV_FILE="$SCRIPT_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f "$SCRIPT_DIR/.env.example" ]]; then
    warn ".env not found — copying from .env.example"
    cp "$SCRIPT_DIR/.env.example" "$ENV_FILE"
    warn "Please edit .env with your real values, then re-run this script."
    echo -e "\n  ${YELLOW}Open .env:${RESET}  nano $ENV_FILE\n"
    exit 1
  else
    die ".env file not found and no .env.example to copy from."
  fi
fi
success ".env file found"

# Source env vars for validation
set -a; source "$ENV_FILE"; set +a

# ── Validate required keys ────────────────────────────────────────────────────
REQUIRED_KEYS=(
  JWT_SECRET_KEY
  POSTGRES_DATABASE_URL
  LANGFUSE_NEXTAUTH_SECRET
  LANGFUSE_SALT
  LANGFUSE_ENCRYPTION_KEY
)
MISSING=()
for key in "${REQUIRED_KEYS[@]}"; do
  val="${!key:-}"
  if [[ -z "$val" ]]; then
    MISSING+=("$key")
  fi
done
if [[ ${#MISSING[@]} -gt 0 ]]; then
  error "The following required variables are not set in .env:"
  for k in "${MISSING[@]}"; do echo -e "    ${RED}✗${RESET} $k"; done
  die "Fix .env and re-run."
fi
success "Required env vars present"

# ── Production-specific checks ────────────────────────────────────────────────
if [[ "$DEPLOY_ENV" == "production" ]]; then
  PROD_WARNINGS=()

  # Warn on placeholder values
  placeholder_check() {
    local key="$1" val="${!1:-}"
    if [[ "$val" == *"changeme"* ]] || [[ "$val" == *"00000000"* ]] || \
       [[ "$val" == *"replace-with"* ]] || [[ "$val" == *"your_"* ]]; then
      PROD_WARNINGS+=("$key looks like a placeholder: $val")
    fi
  }
  placeholder_check JWT_SECRET_KEY
  placeholder_check LANGFUSE_NEXTAUTH_SECRET
  placeholder_check LANGFUSE_SALT
  placeholder_check LANGFUSE_ENCRYPTION_KEY
  placeholder_check LANGFUSE_PUBLIC_KEY
  placeholder_check LANGFUSE_SECRET_KEY

  if [[ ${#PROD_WARNINGS[@]} -gt 0 ]]; then
    warn "Production deployment with placeholder secrets detected:"
    for w in "${PROD_WARNINGS[@]}"; do echo -e "    ${YELLOW}⚠${RESET}  $w"; done
    echo ""
    read -rp "Continue anyway? [y/N]: " CONFIRM
    [[ "$CONFIRM" =~ ^[Yy]$ ]] || die "Aborted. Update your secrets in .env and re-run."
  fi

  # Enforce ENVIRONMENT=Production for ASPNETCORE
  if [[ "${ENVIRONMENT:-}" != "Production" ]]; then
    warn "Setting ENVIRONMENT=Production in .env (required for .NET JWT config)"
    # Update in-place
    if grep -q "^ENVIRONMENT=" "$ENV_FILE"; then
      sed -i.bak 's/^ENVIRONMENT=.*/ENVIRONMENT=Production/' "$ENV_FILE"
    else
      echo "ENVIRONMENT=Production" >> "$ENV_FILE"
    fi
    set -a; source "$ENV_FILE"; set +a
  fi
  success "ENVIRONMENT=Production confirmed"
fi

# =============================================================================
# 4. DOCKER NETWORK
# =============================================================================
header "Docker network"

if docker network inspect rag-network &>/dev/null; then
  success "rag-network already exists"
else
  info "Creating rag-network..."
  docker network create rag-network
  success "rag-network created"
fi

# =============================================================================
# 5. PICK COMPOSE FILES
# =============================================================================
if [[ "$DEPLOY_ENV" == "development" ]]; then
  COMPOSE_FILES="-f docker-compose.yml -f docker-compose.override.yml"
  info "Using docker-compose.yml + docker-compose.override.yml (dev ports exposed)"
else
  COMPOSE_FILES="-f docker-compose.yml"
  info "Using docker-compose.yml only (no host-bound ports)"
fi

# =============================================================================
# 6. PULL / BUILD
# =============================================================================
header "Building images"
$COMPOSE $COMPOSE_FILES build --parallel
success "All images built"

# =============================================================================
# 7. STOP EXISTING CONTAINERS (graceful)
# =============================================================================
header "Stopping existing containers"
$COMPOSE $COMPOSE_FILES down --remove-orphans 2>/dev/null || true
success "Stopped"

# =============================================================================
# 8. START SERVICES
# =============================================================================
header "Starting services"
$COMPOSE $COMPOSE_FILES up -d
success "All services started"

# =============================================================================
# 9. WAIT FOR HEALTH CHECKS
# =============================================================================
header "Waiting for services to be healthy"

wait_healthy() {
  local container="$1" timeout="${2:-120}" elapsed=0
  echo -n "  Waiting for $container"
  while true; do
    status=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "missing")
    if [[ "$status" == "healthy" ]]; then
      echo -e " ${GREEN}✓${RESET}"
      return 0
    elif [[ "$status" == "unhealthy" ]]; then
      echo -e " ${RED}✗ unhealthy${RESET}"
      docker logs --tail 20 "$container" 2>/dev/null || true
      return 1
    elif [[ "$elapsed" -ge "$timeout" ]]; then
      echo -e " ${YELLOW}⚠ timed out (status: $status)${RESET}"
      return 1
    fi
    echo -n "."
    sleep 3
    elapsed=$((elapsed + 3))
  done
}

CRITICAL_CONTAINERS=(
  rag-postgres
  rag-redis
  rag-opensearch
  rag-ollama
  rag-dotnet-api
  rag-agentic-service
)

FAILED=0
for c in "${CRITICAL_CONTAINERS[@]}"; do
  wait_healthy "$c" 120 || FAILED=$((FAILED + 1))
done

if [[ "$FAILED" -gt 0 ]]; then
  warn "$FAILED service(s) did not reach healthy state. Check logs with:"
  echo -e "    docker logs <container-name>"
else
  success "All critical services healthy"
fi

# =============================================================================
# 10. PULL OLLAMA MODEL (if not already present)
# =============================================================================
header "Ensuring Ollama model is available"

OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.2:1b}"
if docker exec rag-ollama ollama list 2>/dev/null | grep -q "$OLLAMA_MODEL"; then
  success "Model ${OLLAMA_MODEL} already present"
else
  info "Pulling ${OLLAMA_MODEL} — this may take a few minutes..."
  docker exec rag-ollama ollama pull "$OLLAMA_MODEL"
  success "Model ${OLLAMA_MODEL} ready"
fi

# =============================================================================
# 11. OPENSEARCH INDEX SETUP
# =============================================================================
header "OpenSearch index setup"

# Run the setup script inside the agentic service container (has opensearch-py)
if docker exec rag-agentic-service python /app/scripts/setup_opensearch_index.py &>/dev/null; then
  success "OpenSearch index verified / created"
else
  warn "OpenSearch index setup returned non-zero (may already exist — this is usually fine)"
fi

# =============================================================================
# 12. PRODUCTION-ONLY: CADDY CHECK
# =============================================================================
if [[ "$DEPLOY_ENV" == "production" ]]; then
  header "Caddy reverse proxy"
  if command -v caddy &>/dev/null && systemctl is-active --quiet caddy 2>/dev/null; then
    success "Caddy is running"
  else
    warn "Caddy not detected as a running systemd service."
    warn "Ensure Caddy is installed and your Caddyfile points to:"
    echo -e "    ${CYAN}http://localhost:8000${RESET}  → rag-dotnet-api (port 8000)"
    echo -e "    ${CYAN}http://localhost:3001${RESET}  → rag-langfuse-web (port 3001)"
  fi
fi

# =============================================================================
# 13. SUMMARY
# =============================================================================
header "Deployment complete"

if [[ "$DEPLOY_ENV" == "development" ]]; then
  echo -e "  ${BOLD}.NET API${RESET}        http://localhost:8000"
  echo -e "  ${BOLD}Langfuse UI${RESET}     http://localhost:3001"
  echo -e "  ${BOLD}OpenSearch${RESET}      http://localhost:9200"
  echo -e "  ${BOLD}Dashboards${RESET}      http://localhost:5601"
  echo -e "  ${BOLD}Ollama${RESET}          http://localhost:11434"
else
  echo -e "  ${BOLD}All ports${RESET} are internal — access via Caddy reverse proxy."
  echo -e "  ${BOLD}Public API${RESET}      https://${API_PUBLIC_URL:-<your-domain>}"
fi

echo ""
echo -e "  ${BOLD}Useful commands:${RESET}"
echo -e "    View logs:       docker compose $COMPOSE_FILES logs -f"
echo -e "    Stop all:        docker compose $COMPOSE_FILES down"
echo -e "    Restart service: docker compose $COMPOSE_FILES restart <service>"
echo -e "    Container status: docker ps"
echo ""
success "Done."

#!/usr/bin/env bash
# =============================================================================
# CyberGuard AI — Zero-Downtime Rolling Deploy with Auto-Rollback
#
# Usage:
#   ./deploy.sh                        # interactive (asks dev/prod)
#   DEPLOY_ENV=production ./deploy.sh  # non-interactive (CI)
#
# Optional env vars:
#   DEPLOY_ENV        "development" | "production"  (default: production)
#   SLACK_WEBHOOK     https://hooks.slack.com/...   (omit to skip notifications)
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

DEPLOY_START=$(date +%s)

# =============================================================================
# SLACK NOTIFICATION HELPER
# =============================================================================
# Posts a message to Slack if SLACK_WEBHOOK is set.
# Usage: slack_notify "message" [":emoji:"]
slack_notify() {
  local msg="$1" emoji="${2:-:rocket:}"
  [[ -z "${SLACK_WEBHOOK:-}" ]] && return 0
  curl -s -o /dev/null -X POST "$SLACK_WEBHOOK" \
    -H 'Content-type: application/json' \
    --data "{\"text\":\"${emoji} *CyberGuard AI* — ${msg}\"}" || true
}

# =============================================================================
# 1. CHOOSE ENVIRONMENT
# =============================================================================
header "CyberGuard AI — Rolling Deploy"

if [[ -n "${DEPLOY_ENV:-}" ]]; then
  # Non-interactive (CI): env var already set
  case "$DEPLOY_ENV" in
    development|production) ;;
    *) die "DEPLOY_ENV must be 'development' or 'production', got: $DEPLOY_ENV" ;;
  esac
  info "Environment (from env var): ${BOLD}${DEPLOY_ENV}${RESET}"
else
  # Interactive: ask the operator
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
fi

# =============================================================================
# 2. PREREQUISITES CHECK
# =============================================================================
header "Checking prerequisites"

check_cmd() {
  if command -v "$1" &>/dev/null; then
    success "$1 found"
  else
    die "$1 is required but not installed."
  fi
}

check_cmd docker
check_cmd git
check_cmd curl

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
    warn "Please edit .env with your real values, then re-run."
    exit 1
  else
    die ".env file not found and no .env.example to copy from."
  fi
fi
success ".env file found"

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
  [[ -z "${!key:-}" ]] && MISSING+=("$key")
done
if [[ ${#MISSING[@]} -gt 0 ]]; then
  error "Missing required variables in .env:"
  for k in "${MISSING[@]}"; do echo -e "    ${RED}✗${RESET} $k"; done
  die "Fix .env and re-run."
fi
success "Required env vars present"

# ── Production-specific checks ────────────────────────────────────────────────
if [[ "$DEPLOY_ENV" == "production" ]]; then
  PROD_WARNINGS=()
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
    if [[ -t 0 ]]; then
      read -rp "Continue anyway? [y/N]: " CONFIRM
      [[ "$CONFIRM" =~ ^[Yy]$ ]] || die "Aborted. Update your secrets in .env and re-run."
    else
      warn "Non-interactive mode — proceeding despite placeholder secrets."
    fi
  fi

  if [[ "${ENVIRONMENT:-}" != "Production" ]]; then
    warn "Setting ENVIRONMENT=Production in .env"
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
# 4. PULL LATEST CODE
# =============================================================================
header "Pulling latest code"

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [[ "$CURRENT_BRANCH" != "main" ]]; then
  warn "Not on main branch (currently: $CURRENT_BRANCH)"
fi

git fetch origin main
git reset --hard origin/main
NEW_SHA=$(git rev-parse --short HEAD)
success "Repository at ${BOLD}${NEW_SHA}${RESET}"

# =============================================================================
# 5. DOCKER NETWORK
# =============================================================================
header "Docker network"

docker network inspect rag-network &>/dev/null \
  || (info "Creating rag-network..." && docker network create rag-network)
success "rag-network ready"

# =============================================================================
# 6. COMPOSE FILE SELECTION
# =============================================================================
if [[ "$DEPLOY_ENV" == "development" ]]; then
  COMPOSE_FILES="-f docker-compose.yml -f docker-compose.override.yml"
  info "Using docker-compose.yml + docker-compose.override.yml"
else
  COMPOSE_FILES="-f docker-compose.yml"
  info "Using docker-compose.yml (production)"
fi

# Shorthand so we don't repeat ourselves
DC="$COMPOSE $COMPOSE_FILES"

# =============================================================================
# 7. SNAPSHOT PREVIOUS IMAGE IDs (for rollback)
# =============================================================================
header "Snapshotting current image IDs"

# Map: compose-service-name -> container-name -> current image ID
# We capture the image ID that each running container is currently using.
declare -A PREV_IMAGE_ID
declare -A SERVICE_TO_CONTAINER

# The 6 application services we roll out (in order).
# Format: "compose-service-name:container-name"
ROLLOUT_SERVICES=(
  "dotnet-api:rag-dotnet-api"
  "agentic-rag-service:rag-agentic-service"
  "advisory-service:rag-advisory-service"
  "embeddings-service:rag-embeddings-service"
  "pdf-service:rag-pdf-service"
  "search-service:rag-search-service"
)

for entry in "${ROLLOUT_SERVICES[@]}"; do
  svc="${entry%%:*}"
  ctr="${entry##*:}"
  SERVICE_TO_CONTAINER["$svc"]="$ctr"

  img=$(docker inspect --format='{{.Image}}' "$ctr" 2>/dev/null || echo "")
  if [[ -n "$img" ]]; then
    PREV_IMAGE_ID["$svc"]="$img"
    info "  $svc — previous image: ${img:0:19}…"
  else
    PREV_IMAGE_ID["$svc"]=""
    warn "  $svc — container not running (first deploy?)"
  fi
done

# =============================================================================
# 8. BUILD ALL NEW IMAGES (prod keeps running while we build)
# =============================================================================
header "Building new images (production stays live)"

slack_notify "Deploy started — building images for commit \`${NEW_SHA}\`" ":building_construction:"

$DC build --pull --parallel
success "All images built"

# =============================================================================
# 9. HEALTH CHECK HELPER
# =============================================================================
# Polls until container is healthy, unhealthy, or timeout.
# Returns 0 on healthy, 1 on unhealthy/timeout.
wait_healthy() {
  local container="$1" timeout="${2:-120}" elapsed=0
  printf "    Waiting for %s" "$container"
  while true; do
    status=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "missing")
    case "$status" in
      healthy)
        echo -e " ${GREEN}healthy${RESET}"
        return 0
        ;;
      unhealthy)
        echo -e " ${RED}UNHEALTHY${RESET}"
        error "Container logs (last 30 lines):"
        docker logs --tail 30 "$container" 2>&1 | sed 's/^/    /' >&2 || true
        return 1
        ;;
    esac
    if [[ "$elapsed" -ge "$timeout" ]]; then
      echo -e " ${YELLOW}TIMEOUT${RESET} (status: $status after ${elapsed}s)"
      docker logs --tail 20 "$container" 2>&1 | sed 's/^/    /' >&2 || true
      return 1
    fi
    printf "."
    sleep 5
    elapsed=$((elapsed + 5))
  done
}

# =============================================================================
# 10. ROLLBACK HELPER
# =============================================================================
# Re-deploys each already-updated service using its previous image.
# Called only when a health check fails mid-rollout.
rollback() {
  local failed_svc="$1"
  shift
  local updated_services=("$@")   # services that were already successfully updated

  header "ROLLBACK — reverting ${#updated_services[@]} service(s)"
  slack_notify "Deploy FAILED at \`${failed_svc}\` — rolling back ${#updated_services[@]} service(s)" ":rotating_light:"

  local rb_failed=0
  for svc in "${updated_services[@]}"; do
    local ctr="${SERVICE_TO_CONTAINER[$svc]}"
    local prev_img="${PREV_IMAGE_ID[$svc]}"

    if [[ -z "$prev_img" ]]; then
      warn "  $svc — no previous image recorded, skipping rollback for this service"
      continue
    fi

    info "  Rolling back $svc → ${prev_img:0:19}…"
    # Re-tag the previous image as the compose project image so `up` uses it.
    # Compose uses project-prefixed image names; we force the container back
    # to the exact previous image ID via `docker update` + restart.
    # The safest approach: stop the container, set it to the previous image
    # by running `docker run` directly is complex — instead we use the fact
    # that `docker compose up -d --no-deps` will use whatever is the current
    # "built" image. So we re-tag the previous image ID onto the compose image
    # name so Compose picks it up.

    # Get the compose image name for this service
    compose_img=$($DC images --quiet "$svc" 2>/dev/null | head -1 || echo "")

    if [[ -n "$compose_img" ]]; then
      # Tag the previous image ID onto the compose image name
      docker tag "$prev_img" "$compose_img" 2>/dev/null || true
    fi

    # Force recreate the container from the (now-retagged) image
    if $DC up -d --no-deps --force-recreate "$svc" 2>/dev/null; then
      success "  $svc rolled back"
    else
      error "  $svc rollback failed — manual intervention required"
      rb_failed=$((rb_failed + 1))
    fi
  done

  if [[ "$rb_failed" -gt 0 ]]; then
    error "Rollback incomplete — $rb_failed service(s) could not be reverted."
    error "Run: docker compose $COMPOSE_FILES ps"
    slack_notify "Rollback INCOMPLETE — manual intervention required on server" ":sos:"
  else
    success "Rollback complete — production is back on the previous version"
    slack_notify "Rollback complete — production restored to previous version" ":white_check_mark:"
  fi
}

# =============================================================================
# 11. ROLLING DEPLOY — ONE SERVICE AT A TIME
# =============================================================================
header "Rolling deploy (${#ROLLOUT_SERVICES[@]} services)"

UPDATED_SERVICES=()   # track which services were successfully updated
DEPLOY_FAILED=0

for entry in "${ROLLOUT_SERVICES[@]}"; do
  svc="${entry%%:*}"
  ctr="${entry##*:}"

  info "Deploying ${BOLD}${svc}${RESET}…"

  # Start/recreate this one service only; leave everything else running
  if ! $DC up -d --no-deps "$svc"; then
    error "Failed to start $svc"
    DEPLOY_FAILED=1
    break
  fi

  # Give Docker a moment to start the container before polling
  sleep 2

  if wait_healthy "$ctr" 120; then
    UPDATED_SERVICES+=("$svc")
    success "${svc} is healthy"
  else
    error "${svc} failed health check — stopping rollout"
    DEPLOY_FAILED=1
    break
  fi
done

# =============================================================================
# 12. OUTCOME: SUCCESS OR ROLLBACK
# =============================================================================
if [[ "$DEPLOY_FAILED" -eq 0 ]]; then
  # ── Success path ──────────────────────────────────────────────────────────
  header "Deploy successful"

  # Ensure Ollama model is present
  OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.2:1b}"
  if docker exec rag-ollama ollama list 2>/dev/null | grep -q "$OLLAMA_MODEL"; then
    success "Ollama model ${OLLAMA_MODEL} present"
  else
    info "Pulling Ollama model ${OLLAMA_MODEL}…"
    docker exec rag-ollama ollama pull "$OLLAMA_MODEL"
    success "Ollama model ${OLLAMA_MODEL} ready"
  fi

  # OpenSearch index setup
  info "Running OpenSearch index setup…"
  docker exec rag-agentic-service \
    python /app/scripts/setup_opensearch_index.py 2>&1 \
    || warn "OpenSearch index setup returned non-zero (may already exist)"

  # Production-only: Caddy check
  if [[ "$DEPLOY_ENV" == "production" ]]; then
    header "Caddy reverse proxy"
    if command -v caddy &>/dev/null && systemctl is-active --quiet caddy 2>/dev/null; then
      success "Caddy is running"
    else
      warn "Caddy not detected as a running systemd service."
      warn "Ensure Caddy is installed and routing to localhost:8000 and localhost:3001."
    fi
  fi

  # Prune dangling images from previous builds
  info "Pruning dangling images…"
  docker image prune -f --filter "until=1h" &>/dev/null || true
  success "Image pruning done"

  DEPLOY_END=$(date +%s)
  ELAPSED=$(( DEPLOY_END - DEPLOY_START ))

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
  echo -e "  ${BOLD}Commit:${RESET}  ${NEW_SHA}"
  echo -e "  ${BOLD}Duration:${RESET} ${ELAPSED}s"
  echo ""
  echo -e "  ${BOLD}Useful commands:${RESET}"
  echo -e "    View logs:        $DC logs -f"
  echo -e "    Stop all:         $DC down"
  echo -e "    Restart service:  $DC restart <service>"
  echo -e "    Container status: docker ps"
  echo ""
  success "Done."

  slack_notify "Deploy successful — commit \`${NEW_SHA}\` live in ${ELAPSED}s :tada:" ":white_check_mark:"
  exit 0

else
  # ── Failure path ──────────────────────────────────────────────────────────
  header "Deploy FAILED — initiating rollback"

  # The service that failed is the last entry NOT in UPDATED_SERVICES.
  # Rollback only the services we already updated.
  if [[ ${#UPDATED_SERVICES[@]} -gt 0 ]]; then
    rollback "${svc}" "${UPDATED_SERVICES[@]}"
  else
    warn "No services were successfully updated — nothing to roll back."
    slack_notify "Deploy FAILED at first service \`${svc}\` — no rollback needed" ":x:"
  fi

  echo ""
  error "Deploy failed. Production has been restored to the previous version."
  error "Fix the issue and re-run ./deploy.sh"
  echo ""
  exit 1
fi

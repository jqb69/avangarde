#!/bin/bash
# dos/rundos.sh
set -e

# ===================== CONFIG =====================
if [ -f "/home/openclaw/openclaw/.env" ]; then
    export $(cat /home/openclaw/openclaw/.env | xargs)
fi

DOCKER_HUB_USER="${DOCKER_HUB_USER:-openclaw}"
DOCKER_IMAGE="${DOCKER_HUB_USER}/openclaw:latest"
COMPOSE_FILE="docker-compose.yml"
APP_DIR="/home/openclaw/openclaw"

# ===================== FUNCTIONS =====================
check_prerequisites() {
    echo "→ Checking prerequisites..."
    [ -z "$DOCKER_HUB_USER" ] && { echo "Error: DOCKER_HUB_USER is not set"; exit 1; }
    command -v docker >/dev/null 2>&1 || { echo "Error: docker not found"; exit 1; }
    command -v docker-compose >/dev/null 2>&1 || { echo "Error: docker-compose not found"; exit 1; }
}

pull_and_deploy() {
    echo "→ Pulling latest image: $DOCKER_IMAGE"
    docker pull "$DOCKER_IMAGE"

    echo "→ Deploying with docker-compose..."
    docker-compose -f "$COMPOSE_FILE" up -d --force-recreate
}

show_status() {
    echo "→ Deployment status:"
    docker-compose -f "$COMPOSE_FILE" ps
    echo "→ Logs:"
    docker-compose -f "$COMPOSE_FILE" logs --tail=20
}

# ===================== MAIN =====================
main() {
    echo "=== OpenClaw Deployment Started ==="
    cd "$APP_DIR"

    check_prerequisites
    pull_and_deploy
    show_status

    echo "=== Deployment completed successfully ==="
}

main

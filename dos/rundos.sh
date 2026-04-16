#!/bin/bash

# dos/rundos.sh
set -e

APP_DIR="/home/openclaw/openclaw"
COMPOSE_FILE="docker-compose.yml"

setup_environment() {
    echo "→ Synchronizing Environment..."

    # Ensure we are in the right place
    mkdir -p "$APP_DIR"
    cd "$APP_DIR" || exit 1

    # Fallback values
    local DEFAULT_USER="openclaw"
    local DEFAULT_REDIS="redis://redis:6379/0"

    # Merge Logic: 
    # Use $DOCKER_HUB_USER (passed from GitHub)
    # OR Use existing .env value
    # OR Use the Fallback
    
    # Load current .env if it exists
    [ -f .env ] && source .env

    {
        echo "DOCKER_HUB_USER=${DOCKER_HUB_USER:-${DOCKER_HUB_USER:-$DEFAULT_USER}}"
        echo "REDIS_URL=${REDIS_URL:-${REDIS_URL:-$DEFAULT_REDIS}}"
        echo "PYTHONUNBUFFERED=1"
    } > .env

    echo "  └─ Environment set. (User: ${DOCKER_HUB_USER:-$DEFAULT_USER})"
    mkdir -p data logs
}

pull_latest_image() {
    local hub_user="${DOCKER_HUB_USER:-openclaw}"
    local image="${hub_user}/openclaw:latest"
    echo "→ Pulling: $image"
    docker pull "$image"
}

deploy_services() {
    echo "→ Deploying..."
    # Changed from docker-compose to docker compose
    docker compose -f "$COMPOSE_FILE" pull
    docker compose -f "$COMPOSE_FILE" up -d --force-recreate --remove-orphans
}

verify_status() {
    echo "→ Waiting..."
    sleep 3
    # Changed from docker-compose to docker compose
    docker compose ps
    docker compose logs --tail=20
}

main() {
    echo "=== OpenClaw Deployment Started ==="
    setup_environment
    pull_latest_image
    deploy_services
    verify_status
    echo "=== Completed ==="
}

main

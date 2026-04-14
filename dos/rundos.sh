#!/bin/bash

# dos/rundos.sh
set -e

# ===================== CONFIG =====================
APP_DIR="/home/openclaw/openclaw"
COMPOSE_FILE="docker-compose.yml"

# ===================== FUNCTIONS =====================
setup_environment() {
    echo "→ Setting up environment..."
    
    cd "$APP_DIR" || { echo "Error: Directory $APP_DIR not found."; exit 1; }

    # Safely load environment variables
    if [ -f .env ]; then
        echo "  └─ Loading .env file..."
        set -a
        source .env
        set +a
    else
        echo "  └─ Warning: .env file not found."
    fi

    # Create persistence directories
    echo "  └─ Ensuring directories exist (data/, logs/)..."
    mkdir -p data logs
}

pull_latest_image() {
    local hub_user="${DOCKER_HUB_USER:-openclaw}"
    local image="${hub_user}/openclaw:latest"

    echo "→ Pulling latest image: $image"
    docker pull "$image"
}

deploy_services() {
    echo "→ Deploying containers..."
    docker-compose -f "$COMPOSE_FILE" pull  # Ensure latest
    docker-compose -f "$COMPOSE_FILE" up -d --force-recreate --remove-orphans
}

verify_status() {
    echo "→ Waiting for services..."
    sleep 3
    
    echo "→ Container Status:"
    docker-compose -f "$COMPOSE_FILE" ps
    
    echo "→ Logs (last 20 lines):"
    docker-compose -f "$COMPOSE_FILE" logs --tail=20
}

# ===================== MAIN =====================
main() {
    echo "=== OpenClaw Deployment Started ==="
    
    setup_environment
    pull_latest_image
    deploy_services
    verify_status

    echo "=== Deployment completed ==="
}

main

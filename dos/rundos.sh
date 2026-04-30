#!/bin/bash
# do/rundos.sh
# --- Global Settings ---
# -e: Exit on error, -u: Error on unset vars, -o pipefail: Catch errors in pipes
set -euo pipefail

# --- Configuration ---
ENV_FILE=".env"


# --- Functions ---

load_env() {
    echo "📂 Step 1: Handling Environment..."
    
    # Lowercase the actor name for the image path
    local ACTOR_LOWER=$(echo "$GH_ACTOR" | tr '[:upper:]' '[:lower:]')
    export IMAGE_NAME="ghcr.io/${ACTOR_LOWER}/avangarde:latest"

    if [ ! -f "$ENV_FILE" ]; then
        echo "⚠️ .env not found. Creating..."
        {
            echo "TG_SESSION_STR=${TG_SESSION_STR}"
            echo "TG_API_ID=${TG_API_ID}"
            echo "TG_API_HASH=${TG_API_HASH}"
            echo "IMAGE_NAME=${IMAGE_NAME}"
            echo "GH_TOKEN=${GH_TOKEN}"
            echo "GH_ACTOR=${GH_ACTOR}"
            # FOR HOST MODE, USE 127.0.0.1
            echo "REDIS_URL=redis://127.0.0.1:6379/0"
        } > "$ENV_FILE"
        chmod 600 "$ENV_FILE"
        echo "✅ .env created successfully."
    else
        echo "✅ Existing .env found. Using preserved session data."
    fi
    
    # Export for Docker Compose to see
    set -a; source "$ENV_FILE"; set +a
}

check_system() {
    echo "🔍 Step 2: System Integrity Check..."
    
    # 1. Install Docker if missing
    if ! [ -x "$(command -v docker)" ]; then
        echo "Docker not found. Installing..."
        curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh
    fi
    
    # 2. Lowercase the actor for Docker login
    local LOGIN_USER=$(echo "$GH_ACTOR" | tr '[:upper:]' '[:lower:]')
    
    # 3. Login to GHCR
    echo "🔑 Authenticating with GHCR as $LOGIN_USER..."
    if [ -z "$GH_TOKEN" ]; then
        echo "❌ Error: GH_TOKEN is empty. Check your GitHub Secrets."
        exit 1
    fi
    echo "$GH_TOKEN" | docker login ghcr.io -u "$LOGIN_USER" --password-stdin
}

deploy_openclaw() {
    echo "🧹 Step 3: Cleaning up legacy manual containers..."
    # Kill the manual ones that conflict with Compose
    docker stop openclaw-agent openclaw-api claw-redis 2>/dev/null || true
    docker rm openclaw-agent openclaw-api claw-redis 2>/dev/null || true

    # FIX: Corrected 'ecd' to 'cd'
    cd "$(dirname "$0")/.." 
    
    echo "🏗️ Step 4: Orchestrating with Docker Compose..."
    # Force pull to ensure we have the latest GHCR image
    docker-compose pull
    
    # Start the stack
    docker-compose up -d --remove-orphans --force-recreate
}

deploy_containers() {
    echo "🚀 Step 4: Deploying OpenClaw..."
    
    # Always pull the latest image before restarting
    docker pull "$IMAGE_NAME"

    # --- Start Sniper Agent ---
    echo "🎯 Refreshing Sniper Agent..."
    docker stop openclaw-agent 2>/dev/null || true
    docker rm openclaw-agent 2>/dev/null || true
    docker run -d \
      --name openclaw-agent \
      --env MODE=agent \
      --env-file "$ENV_FILE" \
      --network host \
      --restart unless-stopped \
      "$IMAGE_NAME" python3 main.py

    # --- Start Web API ---
    echo "🌐 Refreshing Web API..."
    docker stop openclaw-api 2>/dev/null || true
    docker rm openclaw-api 2>/dev/null || true
    docker run -d \
      --name openclaw-api \
      --env MODE=api \
      --env-file "$ENV_FILE" \
      --network host \
      -p 80:80 \
      --restart unless-stopped \
      "$IMAGE_NAME" gunicorn -w 4 -b 0.0.0.0:80 main:app
}

cleanup() {
    echo "🧹 Step 5: Post-Deployment Cleanup..."
    # Remove old images to save disk space on the Droplet
    docker image prune -f
}

# --- Main Logic Loop ---

main() {
    echo "🏁 Starting Deployment..."
    
    load_env
    check_system
    #deploy_redis
    deploy_openclaw
    cleanup
    echo "=============================================="
    echo "🎉 SUCCESS: Compose stack is up and running."
    echo "Check logs with: docker-compose logs -f"
    echo "🎉 SUCCESS: OpenClaw Sniper and API are running."
}

# Execute main
main

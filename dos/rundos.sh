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
    
    # If the .env file is missing, we build it from the variables 
    # passed from the GitHub 'envs:' block.
    if [ ! -f "$ENV_FILE" ]; then
        echo "⚠️ .env not found. Creating from GitHub environment variables..."
        {
            echo "TG_SESSION_STR=${TG_SESSION_STR}"
            echo "TG_API_ID=${TG_API_ID}"
            echo "TG_API_HASH=${TG_API_HASH}"
            echo "IMAGE_NAME=${IMAGE_NAME}"
            echo "GH_TOKEN=${GH_TOKEN}"
            echo "GH_ACTOR=${GH_ACTOR}"
            echo "REDIS_URL=redis://127.0.0.1:6379/0"
        } > "$ENV_FILE"
        chmod 600 "$ENV_FILE"
        echo "✅ .env created successfully."
    else
        echo "✅ Existing .env found. Using preserved session data."
    fi

    # Load variables into the current shell session
    set -a; source "$ENV_FILE"; set +a
}

check_system() {
    echo "🔍 Step 2: System Integrity Check..."
    
    # Check for Docker
    if ! [ -x "$(command -v docker)" ]; then
        echo "Docker not found. Installing..."
        curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh
    fi
    
    # Login to GHCR (required to pull the private image)
    echo "🔑 Authenticating with GHCR..."
    echo "$GH_TOKEN" | docker login ghcr.io -u "$GH_ACTOR" --password-stdin
}

deploy_redis() {
    echo "🗄️ Step 3: Managing Redis..."
    # Start Redis if not exists; restart if it does
    docker run -d --name claw-redis --restart always -p 6379:6379 redis:alpine 2>/dev/null || docker start claw-redis
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
    deploy_redis
    deploy_containers
    cleanup
    
    echo "🎉 SUCCESS: OpenClaw Sniper and API are running."
}

# Execute main
main

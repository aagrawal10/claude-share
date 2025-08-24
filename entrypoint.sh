#!/bin/bash
set -e

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [entrypoint] $1"
}

log "Starting Claude Share application..."

# Ensure claude_sessions directory exists
mkdir -p /app/claude_sessions

# Set proper permissions
chmod 755 /app/claude_sessions

log "Directory setup complete"

# Execute the main command
exec "$@"

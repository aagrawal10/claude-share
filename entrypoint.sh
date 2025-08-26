#!/bin/bash
set -e

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [entrypoint] $1"
}

log "Starting Claude Share application..."

# Ensure claude_sessions directory exists
mkdir -p /app/claude_sessions

# Set proper permissions (only if not a mounted volume)
if [ ! -z "$(ls -A /app/claude_sessions 2>/dev/null)" ] || ! chmod 755 /app/claude_sessions 2>/dev/null; then
    log "Using existing directory permissions (likely mounted volume)"
else
    log "Set directory permissions to 755"
fi

log "Directory setup complete"

# Execute the main command
exec "$@"

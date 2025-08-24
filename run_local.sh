#!/bin/bash

# Local development script for claude-share
# Builds and starts the application using development Docker Compose

set -e  # Exit on any error

echo "🚀 Starting claude-share development environment..."
echo

# Change to repo root
REPO_ROOT=`git rev-parse --show-toplevel`
cd $REPO_ROOT

# Stop any existing containers
echo "🛑 Stopping any existing containers..."
docker-compose -f docker-compose.dev.yml down

# Build the latest image
echo "🔨 Building latest Docker image..."
docker-compose -f docker-compose.dev.yml build --no-cache

# Start the services
echo "🔥 Starting claude-share in development mode..."
docker-compose -f docker-compose.dev.yml up

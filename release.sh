#!/bin/bash

# Function to create and push a new release tag
create_and_push_release_tag() {
    local tag_prefix="claude-share"
    
    echo "Fetching latest tags from remote for prefix $tag_prefix..."
    git fetch --tags || { echo "Error: Failed to fetch tags." >&2; return 1; }

    echo "Determining next tag for prefix: $tag_prefix"
    local last_tag=$(git tag -l "${tag_prefix}-[0-9][0-9][0-9][0-9]" | sort -V | tail -n 1)
    local tag_number=1 # Default to 1 if no previous tag

    if [ -n "$last_tag" ]; then
        local last_tag_number=$(echo "$last_tag" | sed "s/^${tag_prefix}-//")
        # Ensure base 10 for numbers like 0009, handle potential leading zeros correctly
        tag_number=$((10#$last_tag_number + 1))
    fi

    local new_tag_number_formatted=$(printf "%04d" "$tag_number")
    local NEW_RELEASE_TAG="${tag_prefix}-${new_tag_number_formatted}"

    echo "Creating new tag: $NEW_RELEASE_TAG"
    git tag "$NEW_RELEASE_TAG" || { echo "Error: Failed to create tag $NEW_RELEASE_TAG." >&2; return 1; }

    echo "Pushing tag $NEW_RELEASE_TAG to origin..."
    git push --no-verify origin "$NEW_RELEASE_TAG" || { echo "Error: Failed to push tag $NEW_RELEASE_TAG." >&2; return 1; }
    echo "Successfully tagged and pushed $NEW_RELEASE_TAG."
    echo
    return 0
}

# Change to repo root
REPO_ROOT=`git rev-parse --show-toplevel`
cd $REPO_ROOT

# Get current commit hash for image tagging
IMAGE_TAG=`git rev-parse HEAD` || exit 1

# Configuration - modify these for your registry
REGISTRY_USER="akashgolpuria"
REGISTRY_NAME="poacher"
IMAGE_NAME="claude-share"

echo "Building claude-share image for production (linux/amd64)..."
docker buildx build --platform linux/amd64 -t claude-share:latest .

echo "Tagging image with commit hash: ${IMAGE_TAG}"
docker tag claude-share:latest ${REGISTRY_USER}/${REGISTRY_NAME}:${IMAGE_NAME}_${IMAGE_TAG}

echo "Built claude-share image successfully"

# Login to registry (assumes credentials are available)
# Modify this section based on your registry (Docker Hub, AWS ECR, etc.)
echo "Logging into registry..."
cat ~/.docker_hub/credentials | docker login -u ${REGISTRY_USER} --password-stdin

echo "Pushing docker image..."
docker push ${REGISTRY_USER}/${REGISTRY_NAME}:${IMAGE_NAME}_${IMAGE_TAG} && \
  create_and_push_release_tag || \
  echo "Warning: Image pushed but failed to tag release."

echo "Done! Image pushed as: ${REGISTRY_USER}/${REGISTRY_NAME}:${IMAGE_NAME}_${IMAGE_TAG}"

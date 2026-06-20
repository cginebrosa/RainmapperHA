#!/usr/bin/env bash
set -euo pipefail

# Build and publish the Home Assistant app image before exposing a new version in
# Git. Home Assistant reads config.yaml from the repository, so the normal release
# flow is: build/push this image first, then commit/push the version bump.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# These variables allow one-off overrides without editing the script.
IMAGE_NAME="${IMAGE_NAME:-ghcr.io/cginebrosa/rainmapperha}"
PLATFORMS="${PLATFORMS:-linux/amd64,linux/arm64}"
APP_DIR="${APP_DIR:-rainmapper-app}"
LOCAL_IMAGE_KEEP="${LOCAL_IMAGE_KEEP:-2}"
LOCAL_IMAGE_CLEANUP="${LOCAL_IMAGE_CLEANUP:-1}"

# The HA version is the image tag that Home Assistant will request.
version="$(sed -n 's/^version:[[:space:]]*"\([^"]*\)".*/\1/p' "$APP_DIR/config.yaml" | head -n 1)"
if [ -z "$version" ]; then
  printf 'Could not read version from %s/config.yaml\n' "$APP_DIR" >&2
  exit 1
fi

# Buildx is required for the multi-architecture image used by HA/RPi and local tests.
if ! docker buildx version >/dev/null 2>&1; then
  printf 'Docker Buildx is required.\n' >&2
  exit 1
fi

# Publish both the immutable version tag and latest. HA uses the version tag;
# latest is kept only as an operational convenience.
printf 'Building and pushing %s:%s for %s\n' "$IMAGE_NAME" "$version" "$PLATFORMS"
docker buildx build \
  --platform "$PLATFORMS" \
  --file "$APP_DIR/Dockerfile" \
  --tag "$IMAGE_NAME:$version" \
  --tag "$IMAGE_NAME:latest" \
  --push \
  "$ROOT_DIR"

printf 'Published %s:%s and %s:latest\n' "$IMAGE_NAME" "$version" "$IMAGE_NAME"

# Keep Docker Desktop tidy after repeated local releases. Remote GHCR package tags
# are not deleted here; this cleanup only removes local image tags.
if [ "$LOCAL_IMAGE_CLEANUP" = "1" ]; then
  if ! [[ "$LOCAL_IMAGE_KEEP" =~ ^[0-9]+$ ]]; then
    printf 'LOCAL_IMAGE_KEEP must be a non-negative integer, got: %s\n' "$LOCAL_IMAGE_KEEP" >&2
    exit 1
  fi

  local_tags=()
  # Collect only semantic version tags for this image, sorted oldest to newest.
  while IFS= read -r tag; do
    local_tags+=("$tag")
  done < <(
    docker image ls "$IMAGE_NAME" --format '{{.Repository}} {{.Tag}}' \
      | awk -v image="$IMAGE_NAME" '$1 == image && $2 ~ /^[0-9]+\.[0-9]+\.[0-9]+$/ { print $2 }' \
      | sort -t. -k1,1n -k2,2n -k3,3n
  )

  remove_count=$((${#local_tags[@]} - LOCAL_IMAGE_KEEP))
  if [ "$remove_count" -gt 0 ]; then
    printf 'Cleaning local %s image tags, keeping the latest %s version tag(s) plus latest\n' "$IMAGE_NAME" "$LOCAL_IMAGE_KEEP"
    for ((i = 0; i < remove_count; i++)); do
      old_tag="${local_tags[$i]}"
      printf 'Removing local image tag %s:%s\n' "$IMAGE_NAME" "$old_tag"
      docker image rm "$IMAGE_NAME:$old_tag" >/dev/null || true
    done
  fi
fi

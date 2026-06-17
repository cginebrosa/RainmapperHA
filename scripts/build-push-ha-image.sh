#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

IMAGE_NAME="${IMAGE_NAME:-ghcr.io/cginebrosa/rainmapperha}"
PLATFORMS="${PLATFORMS:-linux/amd64,linux/arm64}"
APP_DIR="${APP_DIR:-rainmapper-app}"

version="$(sed -n 's/^version:[[:space:]]*"\([^"]*\)".*/\1/p' "$APP_DIR/config.yaml" | head -n 1)"
if [ -z "$version" ]; then
  printf 'Could not read version from %s/config.yaml\n' "$APP_DIR" >&2
  exit 1
fi

if ! docker buildx version >/dev/null 2>&1; then
  printf 'Docker Buildx is required.\n' >&2
  exit 1
fi

printf 'Building and pushing %s:%s for %s\n' "$IMAGE_NAME" "$version" "$PLATFORMS"
docker buildx build \
  --platform "$PLATFORMS" \
  --file "$APP_DIR/Dockerfile" \
  --tag "$IMAGE_NAME:$version" \
  --tag "$IMAGE_NAME:latest" \
  --push \
  "$APP_DIR"

printf 'Published %s:%s and %s:latest\n' "$IMAGE_NAME" "$version" "$IMAGE_NAME"

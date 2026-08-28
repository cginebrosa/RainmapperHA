#!/usr/bin/env bash
set -euo pipefail

# Configure and start the portable Rainmapper worker without deleting its data.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${REPO_ROOT}/rainmapper-local/docker-compose.worker.yml"
RAINMAPPER_WORKER_VERSION="$(sed -n 's/^ARG RAINMAPPER_WORKER_VERSION=\([^[:space:]]*\).*/\1/p' "${REPO_ROOT}/rainmapper-worker/Dockerfile" | head -n 1)"
if [[ ! "${RAINMAPPER_WORKER_VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    printf 'Error: rainmapper-worker/Dockerfile does not define a valid semantic worker version.\n' >&2
    exit 2
fi
export RAINMAPPER_WORKER_VERSION
WORKER_IMAGE="rainmapper-worker:${RAINMAPPER_WORKER_VERSION}"
WORKER_VOLUME="rainmapper-worker-data"
WORKER_NETWORK="rainmapper-local-compute"
WORKER_DATA_DIR="/var/lib/rainmapper-worker"
WORKER_HEALTH_URL="http://127.0.0.1:8110/health"
LAB_COORDINATOR_URL="http://rainmapper-ha-ui:8100"
LOCAL_WORKER_IMAGE_CLEANUP="${LOCAL_WORKER_IMAGE_CLEANUP:-1}"
LOCAL_WORKER_BUILD_CACHE_CLEANUP="${LOCAL_WORKER_BUILD_CACHE_CLEANUP:-1}"
LOCAL_WORKER_BUILD_CACHE_MAX_BYTES="${LOCAL_WORKER_BUILD_CACHE_MAX_BYTES:-8589934592}"

if [[ ! "${LOCAL_WORKER_IMAGE_CLEANUP}" =~ ^[01]$ || ! "${LOCAL_WORKER_BUILD_CACHE_CLEANUP}" =~ ^[01]$ ]]; then
    printf 'Error: local cleanup flags must be 0 or 1.\n' >&2
    exit 2
fi
if [[ ! "${LOCAL_WORKER_BUILD_CACHE_MAX_BYTES}" =~ ^[1-9][0-9]*$ ]]; then
    printf 'Error: LOCAL_WORKER_BUILD_CACHE_MAX_BYTES must be a positive integer.\n' >&2
    exit 2
fi

DISPLAY_NAME=""
RAINMAPPER_URL=""
TOKEN_VALUE=""
TOKEN_MODE="keep"
PAIRING_CODE_VALUE=""
PAIRING_MODE="keep"
NON_INTERACTIVE=false

usage() {
    printf '%s\n' \
        'Usage:' \
        '  ./mushroom_worker_start.sh [options]' \
        '' \
        'Configure and start the portable Rainmapper worker. Supplied values are' \
        'validated and persisted in the Docker volume rainmapper-worker-data.' \
        'Future starts can omit them.' \
        '' \
        'Options:' \
        '  --name NAME             Visible worker name. Persisted with its identity.' \
        '  --rainmapper-url URL    Rainmapper coordinator this worker must contact.' \
        '  --token-stdin           Read the coordinator token from standard input.' \
        '  --token-file FILE       Read the coordinator token from a private file.' \
        '  --clear-token           Remove the currently persisted coordinator token.' \
        '  --pairing-code-stdin    Read a temporary one-time pairing code from stdin.' \
        '  --non-interactive       Never ask questions; fail with instructions instead.' \
        '  -h, --help              Show this help and exit without using Docker.' \
        '' \
        'Behaviour:' \
        '  * Builds and runs the independently versioned worker image.' \
        '  * After a healthy start, removes old versioned worker images and caps' \
        '    unused local BuildKit cache at 8 GiB by default; volumes are untouched.' \
        '  * Passed parameters override and persist the corresponding saved values.' \
        '  * Missing parameters are loaded from rainmapper-worker-data.' \
        '  * If Rainmapper requires authentication and no token is stored, generate' \
        '    a code in Workers and jobs; interactive start will ask for it.' \
        '  * If the URL is missing or unreachable, an interactive terminal offers' \
        '    retry, URL/token changes, or cancellation.' \
        '  * Without an interactive terminal, missing or invalid configuration fails.' \
        '' \
        'Local laboratory example:' \
        '  ./mushroom_worker_start.sh --rainmapper-url http://rainmapper-ha-ui:8100' \
        '' \
        'The laboratory UI for a browser is http://127.0.0.1:8101.' \
        'That browser URL is not the worker URL.' \
        "Worker image: ${WORKER_IMAGE}." \
        '' \
        'Home Assistant/Tailscale example:' \
        '  ./mushroom_worker_start.sh --name "Worker M1" \' \
        '      --rainmapper-url http://homeassistant:8100'
}

require_value() {
    local option="$1"
    local value="${2:-}"
    if [[ -z "${value}" || "${value}" == --* ]]; then
        printf 'Error: %s requires a value.\n\n' "${option}" >&2
        usage >&2
        exit 2
    fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --name)
            require_value "$1" "${2:-}"
            DISPLAY_NAME="$2"
            shift 2
            ;;
        --rainmapper-url)
            require_value "$1" "${2:-}"
            RAINMAPPER_URL="$2"
            shift 2
            ;;
        --token-stdin)
            if [[ "${TOKEN_MODE}" != "keep" || "${PAIRING_MODE}" != "keep" ]]; then
                printf 'Error: choose only one token option.\n' >&2
                exit 2
            fi
            TOKEN_MODE="stdin"
            shift
            ;;
        --token-file)
            require_value "$1" "${2:-}"
            if [[ "${TOKEN_MODE}" != "keep" || "${PAIRING_MODE}" != "keep" ]]; then
                printf 'Error: choose only one token option.\n' >&2
                exit 2
            fi
            if [[ ! -r "$2" ]]; then
                printf 'Error: token file is not readable: %s\n' "$2" >&2
                exit 2
            fi
            IFS= read -r TOKEN_VALUE < "$2" || true
            TOKEN_MODE="replace"
            shift 2
            ;;
        --clear-token)
            if [[ "${TOKEN_MODE}" != "keep" || "${PAIRING_MODE}" != "keep" ]]; then
                printf 'Error: choose only one token option.\n' >&2
                exit 2
            fi
            TOKEN_MODE="clear"
            shift
            ;;
        --pairing-code-stdin)
            if [[ "${TOKEN_MODE}" != "keep" || "${PAIRING_MODE}" != "keep" ]]; then
                printf 'Error: pairing and token options cannot be combined.\n' >&2
                exit 2
            fi
            PAIRING_MODE="stdin"
            shift
            ;;
        --non-interactive)
            NON_INTERACTIVE=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            printf 'Error: unknown option: %s\n\n' "$1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ "${TOKEN_MODE}" == "stdin" ]]; then
    IFS= read -r TOKEN_VALUE || true
    TOKEN_MODE="replace"
fi
if [[ "${PAIRING_MODE}" == "stdin" ]]; then
    IFS= read -r PAIRING_CODE_VALUE || true
    PAIRING_MODE="replace"
fi

CAN_PROMPT=true
if [[ "${NON_INTERACTIVE}" == true || ! -t 0 || ! -t 1 ]]; then
    CAN_PROMPT=false
fi

if command -v scutil >/dev/null 2>&1; then
    RAINMAPPER_PHYSICAL_HOST_NAME="$(scutil --get ComputerName 2>/dev/null || true)"
else
    RAINMAPPER_PHYSICAL_HOST_NAME=""
fi
if [[ -z "${RAINMAPPER_PHYSICAL_HOST_NAME}" ]]; then
    RAINMAPPER_PHYSICAL_HOST_NAME="$(hostname)"
fi
export RAINMAPPER_WORKER_HOST_NAME="${RAINMAPPER_PHYSICAL_HOST_NAME}"
if [[ -n "${DISPLAY_NAME}" ]]; then
    export RAINMAPPER_WORKER_DISPLAY_NAME="${DISPLAY_NAME}"
fi

cd "${REPO_ROOT}"

docker volume create "${WORKER_VOLUME}" >/dev/null
docker network create "${WORKER_NETWORK}" >/dev/null 2>&1 || true
docker compose -f "${COMPOSE_FILE}" build rainmapper-worker

cleanup_local_worker_build_artifacts() {
    local tag

    if [[ "${LOCAL_WORKER_IMAGE_CLEANUP}" == "1" ]]; then
        while IFS= read -r tag; do
            if [[ "${tag}" == "${RAINMAPPER_WORKER_VERSION}" || ! "${tag}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
                continue
            fi
            printf 'Removing obsolete local worker image rainmapper-worker:%s.\n' "${tag}"
            if ! docker image rm "rainmapper-worker:${tag}" >/dev/null; then
                printf 'Warning: could not remove rainmapper-worker:%s; it may still be in use.\n' "${tag}" >&2
            fi
        done < <(docker image ls rainmapper-worker --format '{{.Tag}}')
    fi

    if [[ "${LOCAL_WORKER_BUILD_CACHE_CLEANUP}" == "1" ]]; then
        printf 'Bounding unused local BuildKit cache to %s bytes.\n' "${LOCAL_WORKER_BUILD_CACHE_MAX_BYTES}"
        if ! docker buildx prune --force --max-used-space "${LOCAL_WORKER_BUILD_CACHE_MAX_BYTES}" >/dev/null; then
            printf 'Warning: could not prune unused local BuildKit cache.\n' >&2
        fi
    fi
}

worker_config() {
    docker run --rm --interactive \
        --network "${WORKER_NETWORK}" \
        --volume "${WORKER_VOLUME}:${WORKER_DATA_DIR}" \
        "${WORKER_IMAGE}" \
        config --worker-data-dir "${WORKER_DATA_DIR}" "$@"
}

PERSISTED_URL="$(worker_config get-url)"
if [[ -z "${RAINMAPPER_URL}" ]]; then
    if [[ "${PERSISTED_URL}" == "http://rainmapper-ha-ui:8099" ]]; then
        RAINMAPPER_URL="${LAB_COORDINATOR_URL}"
        printf 'Migrating the saved local laboratory coordinator to %s.\n' "${LAB_COORDINATOR_URL}"
    else
        RAINMAPPER_URL="${PERSISTED_URL}"
    fi
fi

prompt_for_url() {
    printf '\nNo Rainmapper coordinator URL is configured.\n'
    printf 'Enter the URL exposed for worker communication, including http:// or https://.\n'
    printf 'For the local laboratory use: %s\n' "${LAB_COORDINATOR_URL}"
    printf 'Enter c to cancel the worker start.\n'
    while true; do
        printf 'Rainmapper URL: '
        IFS= read -r RAINMAPPER_URL
        case "${RAINMAPPER_URL}" in
            c|C|cancel|Cancelar|cancelar)
                printf 'Worker start cancelled. Existing configuration and data were preserved.\n'
                exit 0
                ;;
            '')
                printf 'A URL is required. Enter a URL or c to cancel.\n'
                ;;
            *)
                return
                ;;
        esac
    done
}

if [[ -z "${RAINMAPPER_URL}" ]]; then
    if [[ "${CAN_PROMPT}" == true ]]; then
        prompt_for_url
    else
        printf 'Error: no Rainmapper coordinator URL is configured.\n' >&2
        printf 'Run this command with --rainmapper-url URL, for example:\n' >&2
        printf '  ./mushroom_worker_start.sh --rainmapper-url %s\n' "${LAB_COORDINATOR_URL}" >&2
        printf 'Use --help for all options. The worker was not started.\n' >&2
        exit 2
    fi
fi

pair_worker() {
    local output
    local -a pair_args
    pair_args=(
        pair
        --rainmapper-url "${RAINMAPPER_URL}"
        --pairing-code-stdin
        --host-name "${RAINMAPPER_PHYSICAL_HOST_NAME}"
    )
    if [[ -n "${DISPLAY_NAME}" ]]; then
        pair_args+=(--display-name "${DISPLAY_NAME}")
    fi
    if output="$(printf '%s\n' "${PAIRING_CODE_VALUE}" | worker_config "${pair_args[@]}" 2>&1)"; then
        PERSISTED_URL="$(worker_config get-url)"
        RAINMAPPER_URL="${PERSISTED_URL}"
        TOKEN_MODE="keep"
        CONFIGURATION_CHANGED=false
        return 0
    fi
    CONFIGURATION_ERROR="${output}"
    return 1
}

if [[ "${TOKEN_MODE}" == "clear" ]]; then
    worker_config clear-token >/dev/null
    TOKEN_MODE="keep"
fi

CONFIGURATION_CHANGED=false
if [[ "${RAINMAPPER_URL}" != "${PERSISTED_URL}" || "${TOKEN_MODE}" != "keep" ]]; then
    CONFIGURATION_CHANGED=true
fi

if [[ "${PAIRING_MODE}" == "replace" ]]; then
    if ! pair_worker; then
        printf '\nCannot pair this worker with Rainmapper.\n%s\n' "${CONFIGURATION_ERROR}" >&2
        printf 'Generate a new code in Workers and jobs, then retry. Existing configuration was preserved.\n' >&2
        exit 2
    fi
fi

validate_or_save_configuration() {
    local output
    if [[ "${CONFIGURATION_CHANGED}" == false ]]; then
        if output="$(worker_config check 2>&1)"; then
            return 0
        fi
    elif [[ "${TOKEN_MODE}" == "replace" ]]; then
        if output="$(printf '%s\n' "${TOKEN_VALUE}" | worker_config configure --rainmapper-url "${RAINMAPPER_URL}" --token-stdin 2>&1)"; then
            return 0
        fi
    elif output="$(worker_config configure --rainmapper-url "${RAINMAPPER_URL}" 2>&1)"; then
        return 0
    fi
    CONFIGURATION_ERROR="${output}"
    return 1
}

while ! validate_or_save_configuration; do
    printf '\nCannot validate the Rainmapper coordinator.\n%s\n' "${CONFIGURATION_ERROR}" >&2
    if [[ "${CAN_PROMPT}" != true ]]; then
        printf 'Check the URL/network or provide corrected parameters. The worker was not started.\n' >&2
        exit 2
    fi
    printf '\nChoose an action:\n'
    printf '  r  Retry the current URL\n'
    printf '  u  Enter a different Rainmapper URL\n'
    printf '  t  Enter or replace the coordinator token\n'
    printf '  p  Enter a temporary pairing code\n'
    printf '  x  Remove the persisted token\n'
    printf '  c  Cancel the worker start\n'
    printf 'Selection: '
    IFS= read -r choice
    case "${choice}" in
        r|R)
            ;;
        u|U)
            prompt_for_url
            CONFIGURATION_CHANGED=true
            ;;
        t|T)
            printf 'Coordinator token (input hidden): '
            IFS= read -r -s TOKEN_VALUE
            printf '\n'
            TOKEN_MODE="replace"
            CONFIGURATION_CHANGED=true
            ;;
        p|P)
            printf 'Temporary pairing code (input hidden): '
            IFS= read -r -s PAIRING_CODE_VALUE
            printf '\n'
            if pair_worker; then
                printf 'Worker paired successfully. The permanent credential is stored in rainmapper-worker-data.\n'
            else
                printf 'Pairing failed: %s\n' "${CONFIGURATION_ERROR}" >&2
            fi
            ;;
        x|X)
            TOKEN_MODE="clear"
            CONFIGURATION_CHANGED=true
            ;;
        c|C)
            printf 'Worker start cancelled. Existing configuration and data were preserved.\n'
            exit 0
            ;;
        *)
            printf 'Unknown selection. Choose r, u, t, p, x or c.\n'
            ;;
    esac
done

PERSISTED_URL="$(worker_config get-url)"
docker compose -f "${COMPOSE_FILE}" up --force-recreate -d rainmapper-worker

for attempt in {1..30}; do
    if WORKER_STATUS_JSON="$(curl --fail --silent --show-error "${WORKER_HEALTH_URL}" 2>/dev/null)"; then
        cleanup_local_worker_build_artifacts
        if [[ "${WORKER_STATUS_JSON}" == *'"status": "needs_dataset"'* ]]; then
            printf '\nRainmapper worker is running and needs its GIS dataset.\n'
            printf 'The first compatible job will download, verify and persist it automatically.\n'
        else
            printf '\nRainmapper worker is running and its dataset cache is ready.\n'
        fi
        printf 'Coordinator: %s\n' "${PERSISTED_URL}"
        printf 'Status: %s\n' "${WORKER_HEALTH_URL}"
        printf 'Physical host: %s\n' "${RAINMAPPER_PHYSICAL_HOST_NAME}"
        printf 'Worker image: %s\n' "${WORKER_IMAGE}"
        printf 'Stop it with: ./mushroom_worker_stop.sh\n'
        exit 0
    fi
    sleep 1
done

printf '\nRainmapper worker started, but its health endpoint did not respond within 30 seconds.\n' >&2
printf 'Inspect it with: docker compose -f %s logs rainmapper-worker\n' "${COMPOSE_FILE}" >&2
exit 1

#!/usr/bin/env bash
# Wrapper: sources .env, builds the shim (if needed), starts the fake grader
# (if not running), and launches the bomb with LD_PRELOAD set.
#
# Usage:
#   ./run.sh                 # interactive
#   ./run.sh solutions.txt   # batch-feed answers from a file

set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -f .env ]]; then
    echo "[run.sh] no .env found. Copy .env.example to .env and fill it in." >&2
    exit 1
fi

# auto-export everything sourced from .env so the LD_PRELOADed shim inherits it
set -a
# shellcheck disable=SC1091
source .env
set +a

if [[ -z "${BOMB_USERID:-}" ]]; then
    echo "[run.sh] BOMB_USERID is unset. See .env.example." >&2
    exit 1
fi

if [[ ! -x ./bomb ]]; then
    echo "[run.sh] no ./bomb binary found in $(pwd). Drop your bomb here." >&2
    exit 1
fi

make -s -C shim libbombshim.so

if ! ss -tln 2>/dev/null | grep -q ':27054\b'; then
    echo "[run.sh] starting fake grader in background..."
    python3 shim/fake_server.py &
    SRV_PID=$!
    trap 'kill "$SRV_PID" 2>/dev/null || true' EXIT
    sleep 0.2
fi

export LD_PRELOAD="$PWD/shim/libbombshim.so"
exec ./bomb "$@"

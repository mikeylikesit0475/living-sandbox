#!/usr/bin/env bash
# Sprint 0 — E1-3 spike runner (shell wrapper)
# Delegates to Python spike which does 20 structured-output calls per candidate.
# Usage: ./scripts/model-spike.sh [--candidates qwen2.5:7b-instruct,llama3.1:8b] [--runs 20]
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$DIR/scripts/model-spike.py" "$@"

#!/usr/bin/env bash
# Import workflows from ./workflows/*.json into n8n via the REST API.
# Usage: N8N_API_KEY=... ./scripts/import-workflows.sh
set -euo pipefail

N8N_URL="${N8N_URL:-http://localhost:5678}"
SRC_DIR="$(cd "$(dirname "$0")/.." && pwd)/workflows"

if [[ -z "${N8N_API_KEY:-}" ]]; then
  echo "Set N8N_API_KEY first."
  exit 1
fi

shopt -s nullglob
for file in "$SRC_DIR"/wf*.json "$SRC_DIR"/*.json; do
  [[ -f "$file" ]] || continue
  name=$(jq -r '.name // "unknown"' "$file")
  echo "→ Importing $name ← $(basename "$file")"
  # n8n API: POST /api/v1/workflows creates; strip id/versionId so n8n assigns new ones
  payload=$(jq 'del(.id, .versionId, .createdAt, .updatedAt)' "$file")
  curl -sf -H "X-N8N-API-KEY: $N8N_API_KEY" -H "Content-Type: application/json" \
    -X POST "$N8N_URL/api/v1/workflows" -d "$payload" | jq '{id, name}'
done

echo "✓ Done."

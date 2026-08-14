#!/usr/bin/env bash
# Export all n8n workflows to ./workflows/ via the n8n REST API.
# Usage: N8N_API_KEY=... ./scripts/export-workflows.sh
set -euo pipefail

N8N_URL="${N8N_URL:-http://localhost:5678}"
OUT_DIR="$(cd "$(dirname "$0")/.." && pwd)/workflows"

if [[ -z "${N8N_API_KEY:-}" ]]; then
  echo "Set N8N_API_KEY first: export N8N_API_KEY=\$(cat ~/.n8n_api_key 2>/dev/null || echo YOUR_KEY)"
  echo "Create a key at: n8n → Settings → API → Create API key"
  exit 1
fi

mkdir -p "$OUT_DIR"
echo "→ Exporting from $N8N_URL/api/v1/workflows → $OUT_DIR"

# List then fetch each workflow individually (n8n API paginates / filters)
curl -sf -H "X-N8N-API-KEY: $N8N_API_KEY" "$N8N_URL/api/v1/workflows?limit=100" \
  | jq -r '.data[] | "\(.id) \(.name)"' | while read -r id name; do
  slug=$(echo "$name" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//;s/-$//')
  file="$OUT_DIR/${slug:-workflow-$id}.json"
  echo "  • $name ($id) → $(basename "$file")"
  curl -sf -H "X-N8N-API-KEY: $N8N_API_KEY" "$N8N_URL/api/v1/workflows/$id" | jq '.' > "$file"
done

echo "✓ Done. Commit with: git add workflows/*.json && git commit -m 'chore: export workflows'"

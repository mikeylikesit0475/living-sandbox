# workflows — n8n workflow JSON exports (source of truth)

Per 05 Definition of Done #2, every touched workflow is re-exported here and committed.

## Inventory (02_ARCHITECTURE §2)

| # | File | Workflow | Trigger |
|---|------|----------|---------|
| WF-1 | `wf1-main-router.json` | `main-router` | Webhook |
| WF-2 | `wf2-squad-lab.json` | `squad-lab` | Execute Sub-workflow |
| WF-3 | `wf3-squad-audit.json` | `squad-audit` | Execute Sub-workflow |
| WF-4 | `wf4-tool-factory.json` | `tool-factory` | Execute Sub-workflow |
| WF-5 | `wf5-sandbox-exec.json` | `sandbox-exec` | Execute Sub-workflow |
| WF-6 | `wf6-memory-write.json` | `memory-write` | Execute Sub-workflow |
| WF-7 | `wf7-memory-recall.json` | `memory-recall` | Execute Sub-workflow |
| WF-8 | `wf8-eval-harness.json` | `eval-harness` | Manual/Schedule |

## Round-trip (E1-2)

### Export (n8n → git)
```bash
./scripts/export-workflows.sh
# or via n8n API:
#   curl -H "X-N8N-API-KEY: $N8N_API_KEY" http://localhost:5678/api/v1/workflows | jq .
```

### Import (git → n8n)
```bash
./scripts/import-workflows.sh
```

A smoke workflow `wf0-smoke.json` lives here first (E1-2) to prove
`NODE_FUNCTION_ALLOW_EXTERNAL=@langchain/core,zod` works inside a Code Node.

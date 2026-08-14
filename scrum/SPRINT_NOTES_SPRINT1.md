# Sprint 1 — Walking Skeleton — Done

## Demo results (2026-08-14)
- `python scripts/demo-walking-skeleton.py --goal "reverse this string: hello"` → `olleh` (exit 0, 179ms, real ephemeral container)
- `python scripts/demo-walking-skeleton.py --goal "reverse this string: OpenAI"` → `IAnepO` (161ms)
- Hostile suite via TestClient: 5/5 passed (fork bomb pids-limited, network blocked, filesystem host secrets not leaked, infinite loop timeout 124, memory bomb 137) — runner stays `health: ok, docker_available: true`
- `docker compose ps` after healthcheck fixes: all 5 services `healthy` (n8n 1.76.3, postgres 16, qdrant 1.12.4, ollama 0.11.4, sandbox-runner 25943e7)
- n8n ready at http://localhost:5678 (editor accessible), webhook path `/webhook/living-sandbox` active in `workflows/wf1-main-router.json`

## Files added
- `workflows/wf1-main-router.json` (Webhook → Init state → Call Lab → Call Tool Factory → Respond)
- `workflows/wf2-squad-lab.json` (canned reverse_string, 417 bytes)
- `workflows/wf4-tool-factory.json` (DynamicStructuredTool with thin HTTP func to sandbox-runner)
- `workflows/wf5-sandbox-exec.json` (HTTP to sandbox-runner + normalize to state.test)
- `scripts/demo-walking-skeleton.py` (standalone chain demo, proves 3 integration cliffs)
- Fix: `docker-compose.yml` n8n healthcheck now uses `node -e http.get` (curl not in n8n image), postgres 55432, ollama 55434, qdrant TCP check
- Fix: `sandbox-runner/Dockerfile` static docker binary + USER root for sock access

## Next for full n8n demo (requires manual n8n API key)
1. Open http://localhost:5678, create owner account
2. Settings → API → Create API key → `export N8N_API_KEY=...`
3. `./scripts/import-workflows.sh` → imports wf1,wf2,wf4,wf5
4. Activate wf1, then: `curl -X POST http://localhost:5678/webhook/living-sandbox -H 'Content-Type: application/json' -d '{"goal":"reverse this string: hello"}'` → `{"answer":"olleh"}`

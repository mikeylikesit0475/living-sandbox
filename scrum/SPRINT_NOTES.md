# Sprint Notes — Living Sandbox (Muse Spark)

## Sprint 0 — Steel Thread Foundations (current)

**Goal:** stack runs, and we know which models we're using.
**Committed:** E1-1 (5), E1-2 (2), E1-3 spike (3), E2-1 (5) — 15 pts

### Daily log

#### 2026-08-14 — Session 1
- Done: read 01–07, scaffolded docker-compose (n8n 1.76.3 + Postgres 16 + Qdrant 1.12.4 + Ollama 0.11.4 + sandbox-runner), config/models.json + endpoints.json, sandbox-runner FastAPI skeleton with security hardening (read-only, no-net, non-root, caps, timeout), hostile test suite, workflow smoke (wf0-smoke.json), scripts (export/import + model-spike), prompts (orchestrator + lab), eval/scenarios.json.
- Next: `docker compose config` validate, `docker compose up -d` dry-run, verify healthchecks; run sandbox-runner locally with `pytest`; spike needs `ollama serve` + model pulls (deferred — Ollama not reachable from this sandbox session).
- Blocked: GitHub push blocked by sandbox .git read-only mount (repo created remotely ok — https://github.com/mikeylikesit0475/living-sandbox). User chose "build now, push later". Also Ollama not serving on host yet — spike placeholder remains.
- Honesty: stack has NOT been booted yet in this session; that is the first gate for Sprint 0 demo.

### Blocked / observations vs expected
- `.git` is mount-ro at `/home/michaelf/Desktop/LivingSandbox/.git` (btrfs ro) — cannot `git branch -M` or commit from this session. Repo was created via `gh` successfully as empty remote.
- No n8n execution IDs yet — skeleton not run end-to-end.

---

## Retro template (fill at sprint end)
- Keep:
- Change:
- Try:

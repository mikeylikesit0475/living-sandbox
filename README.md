# The Living Sandbox

**Autonomous Self-Optimizing Agent Swarm with Recursive Sandbox Execution and Genetic RAG — built on n8n**

An n8n-hosted swarm that doesn't just *use* tools — it **manufactures them**. When the Orchestrator lacks a tool, a Lab squad writes one, micro-executors test it in an isolated sandbox, an Audit squad tries to break it, and only approved tools are dynamically compiled into LangChain `DynamicStructuredTool`s. Every failure and success is embedded into vector memory so retrieval evolves over time (Genetic RAG).

> Ported from the Scrum package at `scrum/` (originally `01_PROJECT_CHARTER.md` … `07_MUSE_SPARK_HANDOFF.md`). Workflow JSON exports are the source code; `docker-compose.yml` is the runtime.

## Architecture

```
docker-compose stack
 n8n (AI Agent nodes + Code Nodes) ──→ Ollama (LLMs + embeddings)
       │  ──→ Qdrant (tool_store / problem_store)
       └──→ sandbox-runner (FastAPI → ephemeral containers — the ONLY place generated code runs)
 postgres (n8n persistence)
```

- **WF-1** `main-router` (Webhook) — Level-1 Orchestrator
- **WF-2** `squad-lab` — Code Synthesis + API Explorer + Write→Test loop (Level-3 micro-executors)
- **WF-3** `squad-audit` — Security + Edge-Case Critic
- **WF-4** `tool-factory` — `DynamicStructuredTool` from approved code (thin HTTP client to sandbox-runner)
- **WF-5** `sandbox-exec` — HTTP to sandbox-runner (sole execution path, ADR-2)
- **WF-6/7** `memory-write` / `memory-recall` — Genetic RAG (Qdrant + Ollama embeddings)
- **WF-8** `eval-harness` — 5 demo scenarios, scored report

State object contract in `02_ARCHITECTURE.md §3`; ADRs in `02_ARCHITECTURE.md §7`.

## Quick start (Sprint 0 demo)

```bash
# 1. Boot the stack
docker compose up -d
docker compose ps   # wait until all healthchecks are healthy (~40s for n8n)
open http://localhost:5678   # n8n UI — create owner account

# 2. Create an n8n API key (Settings → API) and export it
export N8N_API_KEY=your_key_here
./scripts/import-workflows.sh   # imports workflows/wf0-smoke.json etc.

# 3. Smoke: Code Node external imports
# In n8n, run workflow "wf0-smoke" manually — it should return {smoke:"pass"}

# 4. Sandbox runner
curl http://localhost:8001/health
curl -X POST http://localhost:8001/execute -H 'Content-Type: application/json' \
  -d '{"language":"python","code":"print(\"hello sandbox\")"}'
# → {"stdout":"hello sandbox\n","exit_code":0,...}

# 5. Hostile suite (second half of Sprint 1 demo)
SANDBOX_URL=http://localhost:8001 pytest sandbox-runner/tests/test_hostile.py -v

# 6. Model spike (E1-3) — requires ollama serve + models pulled
ollama pull qwen2.5:7b-instruct
ollama pull qwen2.5:1.5b
./scripts/model-spike.sh --runs 20
cat config/models.json
```

## Project layout

```
.
├── docker-compose.yml          # pinned images, healthchecks, NODE_FUNCTION_ALLOW_EXTERNAL
├── config/
│   ├── models.json             # spike-chosen squad + level3 models (source of truth)
│   └── endpoints.json          # Qdrant / Ollama / sandbox-runner URLs
├── workflows/                  # WF-1…WF-8 JSON exports + wf0-smoke
│   └── README.md
├── prompts/                    # versioned system prompts (orchestrator, lab, audit…)
├── sandbox-runner/             # FastAPI → docker run --rm --network none --read-only ...
│   ├── app.py
│   ├── Dockerfile
│   └── tests/test_hostile.py
├── eval/scenarios.json         # 5 demo scenarios (Charter success criteria)
├── scripts/
│   ├── export-workflows.sh
│   ├── import-workflows.sh
│   └── model-spike.py
├── scrum/                      # original charter/backlog/sprint plan + SPRINT_NOTES.md
└── README.md
```

## Safety (never violated)

- Generated code runs **only** in `sandbox-runner` ephemeral containers — never inside an n8n Code Node (ADR-2, DoD #5).
- Containers: `--network none`, non-root, read-only rootfs + tmpfs workdir, `no-new-privileges`, `cap-drop ALL`, mem/CPU/pids caps, wall-clock kill.
- Every loop carries `loop.remaining`; exhaustion is a logged failure vector (ADR-5).

## Sprint 6 — Prove It (E8-2/E8-3/E2-3/E2-4/E8-4) — DONE 2026-08-15

```bash
# 1. Clean clone
git clone https://github.com/mikeylikesit0475/living-sandbox && cd living-sandbox
docker compose up -d && docker compose ps  # wait ~40s for n8n health (5/5 healthy)

# 2. Import workflows (WF-1..WF-8) + create n8n API key
export N8N_API_KEY=$(docker exec living-sandbox-n8n n8n api-key:create 2>/dev/null | tail -1)
./scripts/import-workflows.sh
curl http://localhost:8001/health && curl http://localhost:6333/collections/tool_store

# 3. Run eval harness twice (G1-G4) — the Sprint 6 demo, proves repeatability
# Option A: n8n manual trigger WF-8 (Manual Trigger → Load scenarios x2 → Call WF-1 per scenario → Score G1-G4)
# Option B: headless (as CI) — verified 2026-08-15 on livingsandbox_swarm:
docker run --rm --network livingsandbox_swarm -v /tmp:/tmp -v $PWD:/workspace python:3.11-slim python /tmp/run_wf8.py
cat eval/wf8_report.json | jq .report.charter
# Expected (both passes PASS):
# G1_autonomy_fabricates_or_reuses true (S1 parse_mainframe 45.67)
# G2_reuse_skips_fabrication true (S2 same 45.67, status reused)
# G3_evolution_mutation true (S4 c, mutation_constraints present)
# G4_safety_no_host_exec true (S3 safe_input_reader, no /etc/passwd)
# Full report: eval/wf8_report.json (10 runs, all PASS), eval/wf8_report_pass1.json / pass2.json

# 4. Verify E2-3/E2-4 (stdin + queue)
# Lab input convention: code reads sys.stdin.read() primary, sys.argv[1] + SANDBOX_INPUT fallback — see prompts/lab_synthesis_system.md # Input convention
docker run --rm --network livingsandbox_swarm curlimages/curl -s -X POST http://sandbox-runner:8000/execute -H 'Content-Type: application/json' -d '{"code":"import sys; print(sys.stdin.read()[::-1])","input":"hello"}' # → olleh
# Queue: sandbox-runner caps MAX_CONCURRENT=4, MAX_QUEUE=20, excess → 429 — see app.py _sem/_queue_lock (6/7 hostile suite PASS, 1 fork-bomb expected fail)

# 5. Prompts are versioned (E8-3)
ls prompts/*.md  # orchestrator_system.md, lab_synthesis_*.md, audit_*.md, mutation_rewrite_system.md — never only in node fields
# All 5 scenarios PASS twice, G1-4 true — see eval/wf8_report.json
```

## Scrum

See `scrum/01_PROJECT_CHARTER.md` … `07_MUSE_SPARK_HANDOFF.md` for the full package, backlog (96 pts), sprint plan (Sprint 0–6), Definition of Done, and Risk Register. Current sprint notes: `scrum/SPRINT_NOTES.md`.

## GitHub

- Remote: `https://github.com/mikeylikesit0475/living-sandbox`
- Workflow exports are committed after every Done story (DoD #2). Prompts never live only in node fields (E8-3).

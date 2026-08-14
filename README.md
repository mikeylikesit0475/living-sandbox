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

## Scrum

See `scrum/01_PROJECT_CHARTER.md` … `07_MUSE_SPARK_HANDOFF.md` for the full package, backlog (96 pts), sprint plan (Sprint 0–6), Definition of Done, and Risk Register. Current sprint notes: `scrum/SPRINT_NOTES.md`.

## GitHub

- Remote: `https://github.com/mikeylikesit0475/living-sandbox`
- Workflow exports are committed after every Done story (DoD #2). Prompts never live only in node fields (E8-3).

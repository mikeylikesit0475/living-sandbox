# 07 — Handoff Brief for Muse Spark (Development Agent)

You are building **The Living Sandbox** — an n8n-hosted, self-tool-manufacturing agent swarm. This file is your entry point; the other six documents are binding context. Read them in this order: 01 (scope), 02 (architecture — normative), 03 (backlog), 04 (your sprint order), 05 (what "Done" means), 06 (what must never happen).

## What you are actually delivering

Not an app. You deliver:
1. **A docker-compose stack** — n8n (self-hosted, Postgres-backed), Qdrant, Ollama, and `sandbox-runner`.
2. **Eight n8n workflows** (WF-1…WF-8 per 02_ARCHITECTURE §2), exported as JSON into `workflows/` in git after every change.
3. **One small conventional service**: `sandbox-runner` (FastAPI + Docker-in-Docker or socket-mounted ephemeral containers). This is the only place you write a traditional codebase, and it is the security boundary — build it like one.
4. **Versioned prompts** in `prompts/` and **config** in `config/`.

## Build order (do not reorder)

Follow 04_SPRINT_PLAN.md exactly. The non-negotiable sequencing rule: **Sprint 1's walking skeleton — webhook → Orchestrator → stub Lab with canned code → Tool Factory → sandboxed execution → webhook response — must run before you write any real squad prompt.** It front-loads the three integration cliffs (Call n8n Workflow Tool state round-tripping, dynamic `DynamicStructuredTool` instantiation, sandbox HTTP wiring). If any cliff is impassable, stop and report exactly what n8n did vs. what was expected — there is a pre-approved fallback for the Tool Factory in Risk R4.

## n8n specifics you must honor

- **Self-hosted only.** Set `NODE_FUNCTION_ALLOW_EXTERNAL=@langchain/core,zod` (extend the list in config as needed) so Code Nodes can import LangChain and zod. Verify with a smoke workflow in Sprint 0 before anything else.
- **Pin the n8n image tag.** AI/LangChain nodes evolve fast; upgrades are deliberate stories gated by the eval harness, never drive-by.
- **Sub-teams are workflows.** The Orchestrator's `Invoke_Lab` / `Invoke_Audit` are *Call n8n Workflow Tool* tools pointing at WF-2/WF-3. Squad-internal routing (rework loops, approval gates) is Switch nodes reading the state object.
- **The state object (02 §3) is the law.** Every workflow boundary gets a Code Node guard that validates the incoming state (shape + `schema_version`) and fails loudly with a descriptive error. Squads communicate through it — never through free prose fields you invent ad hoc.
- **Prompts and model names never live only inside node fields.** Files in `prompts/` and `config/models.json` are the source of truth (sync mechanism is yours to design; document it).

## Red lines (from 06 — violating one stops the sprint)

1. Agent-generated code must ONLY execute inside `sandbox-runner`'s ephemeral containers. Never in a Code Node, never via `eval`/`vm` in the n8n process, not even "temporarily while debugging." The `DynamicStructuredTool.func` you build is a thin HTTP client, nothing more.
2. Sandbox containers: no network, non-root, read-only rootfs, mem/CPU/pids caps, hard timeout. Keep the hostile test suite (fork bomb, network attempt, filesystem read, infinite loop, memory bomb) green on every execution-path change.
3. Every loop carries `loop.remaining`; exhaustion is a logged, first-class outcome that writes a failure vector. No unbounded retries.
4. No host secrets/env reachable from sandbox containers.

## Working style expected of you

- **Honesty over optimism.** Status reports state what you actually executed (n8n execution IDs, curl transcripts). "Should work" ≠ Done. If an acceptance criterion wasn't run, the story isn't Done — say so.
- **Demo-driven.** Each sprint ends by literally performing that sprint's demo script from 04.
- **When blocked >2 attempts** on an n8n behavior, record observed-vs-expected in `scrum/SPRINT_NOTES.md` and move on; the Architect rules on it.
- **Architecture deviations need an ADR first.** If reality contradicts 02_ARCHITECTURE, propose a new ADR entry with reasoning before building around it.
- **Commit discipline:** workflow JSON re-exported and committed with every Done story; sandbox-runner changes always land with their tests.

## Your first three tasks (Sprint 0, in order)

1. `docker-compose.yml` for n8n+Postgres, Qdrant, Ollama, sandbox-runner skeleton — healthchecks on all four (E1-1).
2. Git round-trip for workflows: export/import scripts + smoke workflow proving `@langchain/core` and `zod` import inside a Code Node (E1-2).
3. Model spike (E1-3): test 3 local Ollama candidates for structured-JSON reliability (20 calls each, report % valid + latency); write the winners into `config/models.json` — one "squad" model (JSON-reliable instruct) and one "level3" model (small, fast). Disable thinking modes where the API allows; reasoning-heavy models have already proven too slow for loop workloads on this hardware.

Good luck. Build the skeleton first; make it think later.

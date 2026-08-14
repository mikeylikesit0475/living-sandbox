# 06 — Risk Register

Ranked by (likelihood × impact). Owner is who watches it; every mitigation is wired into a backlog story or ADR so it can't be silently skipped.

| # | Risk | L | I | Mitigation | Wired into |
|---|---|---|---|---|---|
| R1 | **Agent-generated code escapes the sandbox** (or someone "temporarily" runs it in a Code Node while debugging) | M | Critical | Single execution path (WF-5 → sandbox-runner); hostile test suite run on every execution-path change; no-network, non-root, read-only, resource-capped containers; DoD item 5 | ADR-2, E2-2, DoD#5 |
| R2 | **Local models can't reliably emit the structured JSON the state object needs**, corrupting inter-squad handoffs | H | High | Sprint 0 spike measures JSON validity per model before we build on it; boundary-validation Code Nodes reject bad state and trigger one repair-retry; known: reasoning-heavy local models are too slow and need thinking disabled | E1-3, ADR-6, DoD#4 |
| R3 | **Infinite/expensive rework loops** — Lab↔Audit ping-pong or agent retry storms | H | High | `loop.remaining` budget on every loop, exhaustion is a first-class logged outcome; sandbox concurrency cap + queue | ADR-5, E2-4, DoD#6 |
| R4 | **The dynamic Tool Factory doesn't work as sketched in n8n** (LangChain Code node limits, tool array injection quirks, version drift between n8n's bundled LangChain and docs) | M | High | It's the Sprint 1 centerpiece with canned inputs — we hit this cliff earliest, with the simplest possible payload; fallback ruling if truly blocked: the tool becomes a generic `run_approved_tool(tool_name, input)` tool that dispatches by name through WF-4, preserving the architecture with one static wrapper | E4-1, Sprint 1 |
| R5 | **Tool "persistence" misunderstanding** — n8n rebuilds agents per execution, so runtime-appended tools vanish next run | H | M | Already ruled: persistence = stored code + re-instantiation on demand; demoed explicitly in Sprint 4 | ADR-3, E4-2 |
| R6 | **Genetic RAG retrieves noise** — failure vectors match superficially, mutation constraints mislead the Lab | M | M | Similarity threshold tuned during Sprint 5 demo scenarios; constraints capped (top-3); constraints are advisory in the prompt, not hard filters; fitness decay kills bad genes | E7-3, E7-4 |
| R7 | **Prompt sprawl** — prompts buried in node fields drift, can't be diffed, silently regress | H | M | All prompts in `prompts/` under git from Sprint 2; DoD item 3 | E8-3, DoD#3 |
| R8 | **Single-machine resource contention** — Ollama inference + sandbox containers + n8n on one box; big models starve the loop | M | M | Small fast model for Level 3; sandbox mem/CPU caps; concurrency cap; if squad-model latency makes loops unbearable, drop model size before dropping loop bounds | E1-3, E2-4 |
| R9 | **Scope creep toward production features** (auth, scaling, cloud LLMs, networked tools) | H | M | Charter "Out of scope" list + working-agreement scope guard; PoC framing is deliberate | Charter, WA |
| R10 | **Demo scenarios overfit** — system passes the 5 scripted scenarios but nothing else | M | L→M | One free-form scenario in the eval set (E8-1); retro after Sprint 6 decides whether to expand the set before showing the project publicly | E8-1 |
| R11 | **n8n upgrade breaks workflows** (AI nodes are actively evolving) | M | M | Pin the n8n image tag in docker-compose; upgrades are a deliberate story with the eval harness as the regression gate | E1-1, E8-2 |

## Standing red lines (violating any of these stops the sprint)

1. Generated code executing anywhere but sandbox-runner.
2. Sandbox containers with network access "just for this one tool."
3. An unbounded loop merged "temporarily."
4. Secrets/env vars from the host reachable inside sandbox containers.

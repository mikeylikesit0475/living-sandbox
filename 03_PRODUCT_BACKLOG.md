# 03 — Product Backlog

Estimates in story points (1, 2, 3, 5, 8). Priority: P0 (walking skeleton path), P1 (core value), P2 (evolution features), P3 (polish). Status column is maintained by Muse Spark each sprint.

## Epic E1 — Infrastructure & Stack

| ID | Story | AC (acceptance criteria) | Pts | Pri | Status |
|---|---|---|---|---|---|
| E1-1 | As a developer, I have a docker-compose stack (n8n+Postgres, Qdrant, Ollama, sandbox-runner) that starts with one command | `docker compose up -d` → all healthchecks green; n8n UI reachable; `NODE_FUNCTION_ALLOW_EXTERNAL=@langchain/core,zod` set and verified by a smoke Code Node that imports both | 5 | P0 | ☐ |
| E1-2 | As a developer, workflow JSONs live in git | `workflows/` dir; export/import scripts (n8n CLI or API); README with the round-trip procedure; first commit contains the smoke workflow | 2 | P0 | ☐ |
| E1-3 | **Spike:** pick the squad model and Level-3 model | Report: 3 candidate Ollama models tested for JSON reliability (20 structured-output calls each, % valid) and latency; decision recorded in `config/models.json` which all workflows read | 3 | P0 | ☐ |
| E1-4 | As the system, I have a `swarm_log` table and a shared logging sub-workflow | Any workflow can call `log-event`; row appears with task_id/workflow/gate/verdict/duration | 2 | P1 | ☐ |

## Epic E2 — Sandbox Runner (the security boundary)

| ID | Story | AC | Pts | Pri | Status |
|---|---|---|---|---|---|
| E2-1 | As the swarm, I can execute a Python code string in an ephemeral container | `POST /execute` returns stdout/stderr/exit_code/duration; container is removed after run | 5 | P0 | ☐ |
| E2-2 | As the operator, sandbox containers cannot hurt the host | No network (`--network none`), non-root, read-only rootfs + tmpfs workdir, mem/CPU/pids limits, wall-clock timeout kill. AC = a hostile test suite (fork bomb, `requests.get`, `open('/etc/passwd')`, infinite loop, 2GB alloc) all fail safely with clean error payloads | 5 | P0 | ☐ |
| E2-3 | As the Lab, I can pass stdin-style `input` to the code under test | Runner injects `input` as argv/stdin per a documented convention; convention is stated in the Lab's system prompt | 2 | P1 | ☐ |
| E2-4 | As the operator, the runner is rate-limited and queued | Max N concurrent containers; excess requests queue with backpressure; 429 beyond queue depth | 3 | P2 | ☐ |

## Epic E3 — Main Router & Orchestrator

| ID | Story | AC | Pts | Pri | Status |
|---|---|---|---|---|---|
| E3-1 | As a user, I can POST a task to a webhook and get a final answer | WF-1 exists: Webhook → Orchestrator AI Agent → Respond to Webhook; echo-level intelligence acceptable at this stage | 3 | P0 | ☐ |
| E3-2 | As the Orchestrator, I can invoke sub-teams as tools | `Invoke_Lab`, `Invoke_Audit` Call n8n Workflow Tools wired to WF-2/WF-3 stubs; state object round-trips intact (schema-validated at both boundaries) | 5 | P0 | ☐ |
| E3-3 | As the Orchestrator, I decompose big goals into milestones | Planner prompt produces a JSON milestone list; milestones executed sequentially with state threaded through | 5 | P1 | ☐ |
| E3-4 | As the Orchestrator, I always check the tool store before commissioning the Lab | On a repeat task, execution log shows `Search_Tool_Store` hit and Lab NOT invoked (Charter G2) | 3 | P1 | ☐ |

## Epic E4 — Tool Factory

| ID | Story | AC | Pts | Pri | Status |
|---|---|---|---|---|---|
| E4-1 | As the swarm, an approved code string becomes a live LangChain tool | WF-4 LangChain Code node builds `DynamicStructuredTool` (zod schema from `candidate.input_schema`); its `func` calls WF-5/sandbox-runner via HTTP; Orchestrator successfully calls the tool and uses its output in the final answer | 8 | P0 | ☐ |
| E4-2 | As the swarm, a stored tool can be re-instantiated from the Tool Vector Store | Given a `tool_store` payload, WF-4 produces a working tool without Lab involvement (ADR-3) | 3 | P1 | ☐ |
| E4-3 | As the operator, tool `func` failures are contained | Sandbox errors surface to the agent as tool-error strings, not workflow crashes; agent can react (retry/give up) | 2 | P1 | ☐ |

## Epic E5 — Squad A: The Lab

| ID | Story | AC | Pts | Pri | Status |
|---|---|---|---|---|---|
| E5-1 | As the Orchestrator, I can commission the Lab and get a candidate tool back | Code Synthesis Agent fills `state.candidate` (name/description/schema/code) as valid JSON | 5 | P0 | ☐ |
| E5-2 | As the Lab, I iterate Write→Test against the sandbox until tests pass or budget exhausts | Internal Switch loop: test failure routes stderr back to Synthesis Agent; `loop.remaining` decrements; exhaustion exits with `outcome.status=failed` | 5 | P1 | ☐ |
| E5-3 | As the Lab, my API Explorer Agent enriches candidates with library knowledge | For a task naming a known library, Explorer output (usage notes) demonstrably appears in Synthesis context | 3 | P2 | ☐ |
| E5-4 | As the Lab, Level-3 micro-checks gate cheap validations before full sandbox runs | Fast-model checks (e.g., "does this JSON schema parse?") run first; sandbox invoked only after micro-checks pass | 3 | P2 | ☐ |

## Epic E6 — Squad B: The Audit

| ID | Story | AC | Pts | Pri | Status |
|---|---|---|---|---|---|
| E6-1 | As the swarm, candidate tools are security-reviewed before deploy | Security Agent emits `audit.security_pass` + objections; a seeded-malicious candidate (env-var exfil attempt) is rejected | 5 | P1 | ☐ |
| E6-2 | As the swarm, candidates are edge-case-criticized | Critic proposes ≥3 adversarial inputs; they are actually run via WF-5; failures produce `edge_case_pass=false` with the failing input attached | 5 | P1 | ☐ |
| E6-3 | As the swarm, rejected candidates route back to the Lab with objections | Switch on `security_pass/edge_case_pass`; Lab's rework prompt contains the objections verbatim; loop bounded per ADR-5 | 3 | P1 | ☐ |

## Epic E7 — Memory: Tool Store & Genetic RAG

| ID | Story | AC | Pts | Pri | Status |
|---|---|---|---|---|---|
| E7-1 | As the swarm, deployed tools are indexed in `tool_store` | WF-6 upserts on deploy; payload holds code + schema + fitness=1 | 3 | P1 | ☐ |
| E7-2 | As the swarm, terminal failures are indexed in `problem_store` | Loop-exhaustion and audit-final-reject paths both write failure vectors | 3 | P2 | ☐ |
| E7-3 | As the Lab, I receive mutation constraints derived from similar past failures | WF-7 retrieves failures, rewrites them into "do not X / mutate by Y" lines, injects into Lab prompt; visible in execution log (Charter G3) | 5 | P2 | ☐ |
| E7-4 | As the swarm, tool fitness updates on reuse outcomes | Successful reuse increments fitness; reuse-failure decrements; recall ranking uses `similarity × log(1+fitness)` | 3 | P3 | ☐ |

## Epic E8 — Eval, Hardening, Demo

| ID | Story | AC | Pts | Pri | Status |
|---|---|---|---|---|---|
| E8-1 | As the PO, I have 5 scripted demo scenarios | Scenario specs incl. the four Charter success-criteria scenarios + one free-form; stored in `eval/scenarios.json` | 2 | P1 | ☐ |
| E8-2 | As the PO, an eval workflow runs all scenarios and reports pass/fail | WF-8 report incl. per-scenario gate trace from `swarm_log` | 5 | P2 | ☐ |
| E8-3 | As the operator, every prompt/system message lives in versioned files, not node fields | Prompts in `prompts/` loaded at runtime (or a documented sync script); no prompt exists only inside a node | 3 | P2 | ☐ |
| E8-4 | As a viewer, there's a README walkthrough with a recorded demo run | Step-by-step reproduction from `git clone` to passing eval | 2 | P3 | ☐ |

**Total: ~96 points across 8 epics.** P0 path = E1-1, E1-2, E1-3, E2-1, E2-2, E3-1, E3-2, E4-1, E5-1 (39 pts) — this is the walking skeleton and Sprint 0–1 territory.

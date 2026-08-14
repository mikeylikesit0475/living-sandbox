# 02 — Architecture (Senior Architect's ruling document)

This document is normative. Where it conflicts with the original concept sketch, this document wins — each deviation is recorded as an ADR with reasoning.

## 1. System topology

```
                        docker-compose stack
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  ┌────────────┐   ┌──────────┐   ┌────────┐   ┌───────────────┐  │
│  │ n8n        │──▶│ Ollama   │   │ Qdrant │   │ sandbox-runner│  │
│  │ (main +    │   │ (LLMs +  │   │ (vector│   │ (FastAPI +    │  │
│  │  workers)  │──▶│ embeds)  │   │ stores)│   │  ephemeral    │  │
│  │            │──▶└──────────┘   └────────┘   │  containers)  │  │
│  │            │─────────────────────▲─────────▶───────────────┘  │
│  └────────────┘                     │                            │
│  ┌────────────┐                     │                            │
│  │ Postgres   │ (n8n persistence)   │                            │
│  └────────────┘                     │                            │
└──────────────────────────────────────────────────────────────────┘
```

## 2. n8n workflow inventory

| # | Workflow | Trigger | Contents |
|---|---|---|---|
| WF-1 | `main-router` | Webhook | Level 1 Orchestrator AI Agent. Tools: `Invoke_Lab`, `Invoke_Audit`, `Search_Tool_Store`, `Use_Deployed_Tool` (Tool Factory output), `Log_Outcome` |
| WF-2 | `squad-lab` | Execute Sub-workflow | Code Synthesis Agent + API Explorer Agent + internal Write-Test loop against Level 3 executors |
| WF-3 | `squad-audit` | Execute Sub-workflow | Security Agent + Edge-Case Critic; emits verdict + structured objections |
| WF-4 | `tool-factory` | Execute Sub-workflow | Code Node + LangChain Code node: wraps approved code string into `DynamicStructuredTool` whose `func` calls sandbox-runner over HTTP |
| WF-5 | `sandbox-exec` | Execute Sub-workflow | HTTP Request to sandbox-runner + result normalization. The ONLY path by which generated code runs |
| WF-6 | `memory-write` | Execute Sub-workflow | Embeds + upserts into Qdrant (`tool_store` or `problem_store` collection, by payload type) |
| WF-7 | `memory-recall` | Execute Sub-workflow | Genetic RAG: query both collections, assemble successes + failure/mutation constraints into a prompt block |
| WF-8 | `eval-harness` | Manual/Schedule | Runs the 5 demo scenarios through WF-1, scores results, writes report |

Routing inside WF-2/WF-3 uses **Switch nodes on the state object** (e.g. `audit.security_pass == false` → route back to Lab with objections attached). Rework loops are bounded by `state.loop.remaining` decremented in a Set node — a Switch sends exhausted loops to a failure-logging branch (WF-6), never to infinity.

## 3. The state object (the contract between all workflows)

Squads do not pass prose; they pass this JSON. Every sub-workflow receives and returns it. Muse Spark: version it, validate it at every workflow boundary with a Code Node guard.

```json
{
  "schema_version": 1,
  "task_id": "uuid",
  "goal": "user's decomposed milestone, plain text",
  "loop": { "gate": "test|audit", "remaining": 3 },
  "recall": {
    "reusable_tools": [ { "tool_name": "", "code": "", "score": 0.0 } ],
    "mutation_constraints": [ "Do not use X approach: failed on 2026-08-01 with <error>. Mutate by changing Y." ]
  },
  "candidate": {
    "tool_name": "snake_case_name",
    "description": "",
    "input_schema": { "input": "string" },
    "code": "python source string",
    "language": "python"
  },
  "test": { "passed": false, "runs": [ { "input": "", "stdout": "", "stderr": "", "exit_code": 0, "duration_ms": 0 } ] },
  "audit": {
    "security_pass": false,
    "edge_case_pass": false,
    "objections": [ { "agent": "security|critic", "severity": "block|warn", "detail": "" } ]
  },
  "outcome": { "status": "deployed|failed|reused", "final_answer": "" }
}
```

## 4. The three levels, concretely

**Level 1 — Orchestrator (WF-1).** One AI Agent node, strong local instruct model, system prompt = planner/decomposer. Its tools are Call n8n Workflow Tools pointing at WF-2/3/4/7. Decision policy baked into the prompt: *always call `Search_Tool_Store` (WF-7) before `Invoke_Lab`* — reuse beats fabrication.

**Level 2 — Squads (WF-2, WF-3).** Each squad = 2 AI Agent nodes wired in sequence with Switch-node loops. Lab agents may call WF-5 (sandbox) as a tool to try snippets. Audit agents get the candidate code as *data in the prompt*, never as an executable — they read, they do not run (running is Level 3's job, and only through WF-5).

**Level 3 — Micro-executors.** Two kinds: (a) a small, fast Ollama model for narrow judgments ("is this regex syntactically valid? answer JSON `{valid: bool}`"), and (b) the sandbox-runner itself for ground-truth execution. Prefer (b) whenever the question is empirically checkable — a container run beats an LLM guess.

## 5. sandbox-runner (the one conventional service)

Small FastAPI service. `POST /execute` → `{language, code, input, timeout_s, memory_mb}` → spins an **ephemeral container** (no network, read-only rootfs, non-root user, CPU/mem/pids limits, hard wall-clock kill) → returns `{stdout, stderr, exit_code, duration_ms}`. Containers are single-use; nothing persists between runs. This service is the entire security boundary — see ADR-2 and the Risk Register.

## 6. Genetic RAG mechanics

- **Problem Vector Store** (`problem_store`): on terminal failure, WF-6 embeds `goal + error + attempted code summary` with payload `{type: "failure", code_summary, error, date}`.
- **Tool Vector Store** (`tool_store`): on deploy, WF-6 embeds `tool description + goal it solved` with payload `{type: "tool", tool_name, code, input_schema}`.
- **Recall (WF-7)** queries both. Successes above a similarity threshold → offered as reusable tools. Failures above threshold → rewritten by a small model into imperative mutation constraints: *"A similar attempt failed because &lt;error&gt;. Do not repeat &lt;pattern&gt;. Mutate by &lt;suggested change&gt;."* These constraints are injected verbatim into the Lab's system prompt.
- **Selection pressure:** each reuse bumps a `fitness` counter on the tool's payload; recall ranks by `similarity × log(1+fitness)`. Failed-in-reuse tools get fitness decremented — bad genes die out.

## 7. Architectural Decision Records

**ADR-1: Self-hosted n8n only.** The Tool Factory needs external imports (`@langchain/core/tools`, `zod`) in Code Nodes via `NODE_FUNCTION_ALLOW_EXTERNAL`, and the LangChain Code node — both unavailable/restricted on n8n Cloud. *Status: accepted.*

**ADR-2: No eval/vm inside n8n — ever.** The concept sketch executes generated code "inside an isolated sandbox" from within the Code Node. Ruling: the n8n process must never execute agent-generated code, even wrapped in `vm`. Node's `vm` is not a security boundary. The `DynamicStructuredTool.func` is a thin HTTP client to sandbox-runner. *Status: accepted; non-negotiable (Charter G4).*

**ADR-3: Tools live for the session; code lives forever.** n8n agents are rebuilt per execution, so "appending to the live tool array" only persists within one execution. Persistence is the Tool Vector Store: deployed tool *code* is stored, and WF-4 re-instantiates any stored tool on demand in later runs. This is a feature — the store is the genome, instantiation is expression. *Status: accepted.*

**ADR-4: Qdrant for both stores.** Native n8n node, local, supports payload filtering (needed for `type` and `fitness`). Embeddings via local Ollama embedding model. *Status: accepted.*

**ADR-5: Bounded loops with explicit budget.** Every rework loop carries `loop.remaining`; exhaustion is a *first-class outcome* that feeds the Problem Vector Store. Infinite refinement is a failure mode, not diligence. *Status: accepted.*

**ADR-6: Model selection is config, decided by Sprint 0 spike.** Squad/orchestrator model must reliably emit JSON on Ollama; Level 3 model must be fast. Known from prior local work: reasoning-mode models are too slow for this loop shape and `think:false`-style options matter; the spike verifies current best picks rather than hard-coding one. *Status: accepted.*

**ADR-7: Python as the generated-tool language.** Lab generates Python (best model competence for scripts/parsers); sandbox-runner runs Python containers. The Tool Factory wrapper itself is JS/TS because that's what n8n Code Nodes speak. *Status: accepted.*

## 8. Observability

Every workflow writes a one-line JSON event (`task_id, workflow, gate, verdict, duration`) to a `swarm_log` Postgres table via a shared sub-workflow call. The eval harness reads this to score runs. n8n's own execution log is the debugging view; `swarm_log` is the metrics view.

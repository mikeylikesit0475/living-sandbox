# 01 — Project Charter

## Vision

Build an n8n-hosted agent swarm that, when it lacks a tool to solve a problem, **manufactures one**: a Lab squad writes it, micro-executors test it in an isolated sandbox, an Audit squad tries to break it, and only approved tools are dynamically compiled into LangChain `DynamicStructuredTool`s and used by the Orchestrator. Every failure and success is embedded into vector memory so retrieval evolves over time (Genetic RAG).

## Why n8n

n8n is the runtime, the orchestration layer, and the source of truth. The nested-team hierarchy maps 1:1 onto n8n primitives:

| Architecture concept | n8n primitive |
|---|---|
| Level 1 Orchestrator | AI Agent node in the Main Router workflow |
| `Invoke_Sub_Team` tool | Call n8n Workflow Tool (agent tool that runs a sub-workflow) |
| Level 2 squads (Lab, Audit) | Separate workflows started by Execute Sub-workflow, each containing AI Agent nodes |
| Approval routing / rework loops | Switch nodes routing on `state.audit.security_pass` etc. |
| Tool Factory | Code Node (JS) + LangChain Code node building `DynamicStructuredTool` at runtime |
| Level 3 micro-executors | Small/fast Ollama models behind lightweight AI nodes; sandbox calls via HTTP Request node |
| Problem/Tool vector stores | Qdrant vector store nodes + Ollama embeddings nodes |

## Goals (measurable)

1. **G1 — Autonomy:** given a task requiring a tool that does not exist, the system produces, tests, audits, and deploys that tool with zero human intervention, within a bounded loop (max 3 rework cycles per gate).
2. **G2 — Reuse:** on a second, similar task, the system retrieves the existing tool from the Tool Vector Store and skips fabrication entirely (measured: fabrication path not entered).
3. **G3 — Evolution:** after a logged failure, a retry of a similar problem includes the failure in the prompt as a mutation constraint, and first-attempt success rate on the demo problem set improves between eval runs.
4. **G4 — Safety:** no agent-generated code ever executes in the n8n process. All generated code runs in the ephemeral sandbox runner. Zero exceptions.

## In scope (PoC)

- Self-hosted n8n stack via docker-compose (n8n, Qdrant, Ollama, sandbox runner, Postgres for n8n).
- Main Router workflow + 2 sub-team workflows (Lab, Audit) + shared utility sub-workflows.
- Tool Factory Code Node; sandbox runner microservice (the ONE piece of conventional code we write).
- Tool Vector Store (successes) and Problem Vector Store (failures) in Qdrant.
- Genetic RAG retrieval + mutation prompting.
- A demo problem set of 5 scripted scenarios and an eval workflow that runs them.

## Out of scope (PoC) — change requests, not bugs

- Multi-user / auth / production hardening beyond sandbox isolation.
- Horizontal scaling, queue mode, HA.
- UI beyond n8n's own canvas + webhook responses.
- Cloud LLM providers (local Ollama first; provider swap is a config concern, not a feature).
- Agent-generated tools that require network egress or persistent state (v2 candidates).

## Success criteria for the PoC demo

Run the eval workflow twice. The demo passes if:
1. Scenario "obscure parser" fabricates a tool end-to-end (G1) — visible in the execution log as Write → Test → Audit → Deploy.
2. Re-running the same scenario reuses the stored tool (G2).
3. A deliberately-poisoned scenario (Audit rejects insecure code) shows the rework loop firing and converging (G4 + loop bounds).
4. The failure-then-retry scenario shows the mutation constraint appearing in the Lab prompt (G3).

## Constraints & assumptions

- Hardware: single Linux workstation; Ollama local models (JSON-reliable instruct model for squads; a small fast model for Level 3). Model choice is a Sprint 0 spike, not a hard-coded assumption.
- n8n must run self-hosted with `NODE_FUNCTION_ALLOW_EXTERNAL` set for `@langchain/core` and `zod` — the Tool Factory is impossible on n8n Cloud.
- Workflow JSON exports are committed to git after every sprint. n8n's DB is not the backup.

## Stakeholders

- **Product Owner:** Michael — owns scope, accepts stories.
- **Architect/Scrum Master:** Claude — owns architecture rulings (see ADRs in 02), unblocks, guards scope.
- **Development:** Muse Spark — builds workflows, Code Nodes, sandbox runner. Bound by 07_MUSE_SPARK_HANDOFF.md.

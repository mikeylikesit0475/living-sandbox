# 05 — Definition of Ready, Definition of Done, Working Agreement

## Definition of Ready (a story may enter a sprint when…)

1. Acceptance criteria are written and testable by running something — a workflow, a curl, a script — not by reading code.
2. The state-object fields it touches are identified (schema change? bump `schema_version` and note migration).
3. Dependencies on other stories are listed and those stories are Done or in the same sprint.
4. It names which workflow(s) (WF-1…WF-8) it modifies.

## Definition of Done (a story is Done only when ALL hold)

1. **AC demonstrated** — the acceptance criterion was actually executed, and the execution is reproducible (n8n execution ID or command noted in the story's status).
2. **Exported to git** — every touched workflow JSON is re-exported to `workflows/` and committed; sandbox-runner changes committed with tests.
3. **Prompts versioned** — any new/changed agent prompt exists in `prompts/` (E8-3 discipline applies from Sprint 2 onward).
4. **State contract intact** — the boundary-validation Code Nodes pass; no workflow emits fields outside the schema.
5. **Safety invariant intact** — no path executes generated code outside sandbox-runner (Charter G4 / ADR-2). If a story touched execution paths, the hostile test suite (E2-2) was re-run.
6. **Loops bounded** — any new loop carries `loop.remaining` handling with a tested exhaustion branch.
7. **Logged** — new gates/verdicts emit `swarm_log` events (from Sprint 2 onward).
8. **No orphan config** — model names, URLs, collection names read from `config/`, never hard-coded in node fields.

## Working agreement (Muse Spark ⇄ PO ⇄ Architect)

- **Honesty rule:** report what actually ran. "Should work" is not a status. If an AC was not executed, the story is not Done — say so plainly.
- **Architecture changes** (anything contradicting an ADR in 02) require a new ADR entry *before* implementation, approved by the PO.
- **Scope guard:** if a task looks like it needs something from "Out of scope" in the Charter, stop and raise it — do not quietly build it.
- **Model swaps** are config edits + a rerun of the E1-3 spike measurements, recorded in `config/models.json`.
- **When stuck >2 attempts** on an n8n node behavior, write down the exact observed behavior vs. expected in the sprint notes and move to the next story — the PO/Architect will rule on it rather than burning the sprint.

## Ceremonies (lightweight, solo-PO edition)

| Ceremony | When | Form |
|---|---|---|
| Sprint planning | Sprint start | PO confirms committed stories from 04; Muse Spark flags anything not Ready |
| Daily standup | Each working session start | 3 lines in `SPRINT_NOTES.md`: done / next / blocked |
| Sprint review | Sprint end | Run the sprint's demo script from 04, literally |
| Retro | Sprint end | 3 bullets in `SPRINT_NOTES.md`: keep / change / try |
| Backlog refinement | Mid-sprint, 15 min | Re-estimate next sprint's stories against what was learned |

## Artifacts layout (repo root)

```
living-sandbox/
├── docker-compose.yml
├── config/            # models.json, endpoints, collection names
├── workflows/         # WF-1..WF-8 JSON exports (source of truth)
├── prompts/           # every agent system prompt, versioned
├── sandbox-runner/    # FastAPI service + Dockerfile + hostile test suite
├── eval/              # scenarios.json + expected outcomes
├── scrum/             # this package, copied in; SPRINT_NOTES.md lives here
└── README.md
```

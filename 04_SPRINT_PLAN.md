# 04 — Sprint Plan

One-week sprints (solo PO + AI dev; short cycles, hard demos). Velocity assumption ~13–16 pts/sprint; recalibrate after Sprint 1. **Sequencing rule: no squad intelligence before the skeleton runs end-to-end.**

---

## Sprint 0 — "Steel Thread Foundations"
**Goal:** the stack runs, and we know which models we're using.
**Committed:** E1-1 (5), E1-2 (2), E1-3 spike (3), E2-1 (5) — 15 pts

**Demo script:** `docker compose up -d`; open n8n; run smoke workflow that imports `@langchain/core` + `zod` in a Code Node; `curl` sandbox-runner with `print("hello")` and get stdout back; show `config/models.json` with spike results.

**Notes from the architect:** Do E1-3 honestly — 20 structured-output calls per candidate model, count valid JSON. If the best local model is only ~80% JSON-valid, we add a repair-retry Code Node in Sprint 2 rather than pretending it's 100%.

---

## Sprint 1 — "Walking Skeleton"
**Goal:** webhook → Orchestrator → stub Lab (canned code) → Tool Factory → sandboxed execution → answer. Dumb but REAL, end to end.
**Committed:** E2-2 (5), E3-1 (3), E3-2 (5), E4-1 start (8, may spill) — 13–21 pts; E4-1 is the sprint's centerpiece and allowed to consume everything else's slack.

**Demo script:** POST `{"goal": "reverse this string: hello"}`; stub Lab returns a hard-coded reverse-string Python snippet; Tool Factory wraps it; Orchestrator calls the tool; sandbox executes; webhook responds `"olleh"`. Then run the hostile suite against the sandbox and show every attack contained.

**Why this sprint matters most:** it derisks the three integration cliffs at once — Call n8n Workflow Tool state round-tripping, dynamic tool instantiation in the LangChain Code node, and sandbox HTTP wiring. Everything after this sprint is prompt engineering and plumbing on proven rails.

---

## Sprint 2 — "The Lab Goes Live"
**Goal:** replace the stub — the Lab genuinely writes and self-tests tools.
**Committed:** E4-1 finish (if spilled), E5-1 (5), E5-2 (5), E4-3 (2), E1-4 (2) — ~14 pts

**Demo script:** POST a task the model can't do without code (e.g., "parse this fixed-width 1990s mainframe record format and extract field 3"). Watch the Lab write a parser, fail a test, read its own stderr, fix it, and hand a passing candidate to the Tool Factory. Show `swarm_log` rows for the whole journey.

---

## Sprint 3 — "The Audit Gate"
**Goal:** full Write-Test-Audit-Deploy loop with adversarial review.
**Committed:** E6-1 (5), E6-2 (5), E6-3 (3) — 13 pts

**Demo script:** two runs. (1) Clean task flows Write→Test→Audit→Deploy. (2) Seeded scenario where the Lab is prompted into insecure code (reads `os.environ`); Security Agent blocks it; Switch routes back; Lab rewrites; second audit passes. Show `loop.remaining` decrementing.

---

## Sprint 4 — "Tools That Persist"
**Goal:** the swarm stops rebuilding what it already owns.
**Committed:** E7-1 (3), E4-2 (3), E3-4 (3), E8-1 (2), E3-3 (5) — 16 pts (drop E3-3 to Sprint 5 if tight)

**Demo script:** run the mainframe-parser task from Sprint 2's demo *twice*. First run fabricates and indexes. Second run: `Search_Tool_Store` hits, Lab never spins up, answer arrives in a fraction of the time. Charter G2 achieved on camera.

---

## Sprint 5 — "Genetic RAG"
**Goal:** failures become instructions; the system evolves.
**Committed:** E7-2 (3), E7-3 (5), E7-4 (3), E3-3 (5 if deferred) — 11–16 pts

**Demo script:** run a scenario engineered to fail (budget exhaustion). Show the failure vector land in `problem_store`. Re-run a similar task; show the Lab's prompt now contains "A similar attempt failed because… mutate by…" and the run succeeds. Charter G3.

---

## Sprint 6 — "Prove It" (hardening + eval)
**Goal:** repeatable evidence, not vibes.
**Committed:** E8-2 (5), E8-3 (3), E2-3 (2), E2-4 (3), E8-4 (2) — 15 pts

**Demo script:** run WF-8 eval harness end-to-end twice; show the scored report hitting all four Charter success criteria; walk the README from clean clone.

---

## Backlog discipline

- Anything discovered mid-sprint goes to the backlog, not into the sprint — unless it blocks the sprint goal.
- A story is only "Done" per 05_DEFINITION_OF_DONE.md (including workflow JSON exported to git).
- Spillover is normal; silent scope-shrinking of ACs is not. If an AC must change, it changes in this document with a note.

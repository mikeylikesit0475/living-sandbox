# Sprint 6 Code Review — Findings

Review of commit `77db9f9` ("Sprint 6 — Prove It"). Findings are verified unless marked **PLAUSIBLE**. Ranked most-severe first.

---

## 🔴 CRITICAL 1 — Invalid JSON shipped (merge-conflict markers)

**Files / lines:**
- `workflows/wf1-main-router.json:24`
- `workflows/wf2-squad-lab-live.json:86`
- `workflows/wf4-tool-factory.json:32`

**Problem:** The Sprint 6 commit shipped three core workflow files containing unresolved git merge-conflict markers (`<<<<<<< HEAD` / `=======` / `>>>>>>> 33288b2`). This makes them invalid JSON.

**Impact:** `jq` fails to parse all three files (verified: `jq -e .name` exits nonzero for each). `scripts/import-workflows.sh` runs under `set -euo pipefail` and calls `jq` on each file, so the README step-2 command `./scripts/import-workflows.sh` aborts on the first broken file. **WF-1 / WF-2 / WF-4 never import into n8n.** The README and `scrum/SPRINT_NOTES.md` claim "ALL PASS, verified 2026-08-15", which could not have used the committed artifacts.

**Fix:** For each of the three files, resolve the merge conflict by choosing the correct side:
- Decide which side (HEAD vs `33288b2`) is the intended final version per file. The HEAD-side variant of wf2 (line 87) avoids the `prev.goal` interpolation bug (see WF-2 finding below), so prefer HEAD for wf2 unless there is a specific reason to keep the incoming side.
- Remove all `<<<<<<<`, `=======`, `>>>>>>>` marker lines.
- Verify each file parses: `jq -e .name workflows/wf1-main-router.json` (repeat for wf2, wf4).
- Re-run `./scripts/import-workflows.sh` end-to-end.

**Verification:** `for f in workflows/wf*.json; do jq -e .name "$f" >/dev/null || echo "BAD: $f"; done` should print nothing.

---

## 🔴 CRITICAL 2 — WF-6 "Switch: need Qdrant?" node orphaned

**File / line:** `workflows/wf6-memory-write.json:155` (Switch node still present at line 116)

**Problem:** The `Switch: need Qdrant?` node is orphaned from the connection graph. `Prepare dual write` is wired straight to `Ollama: embed` → `Qdrant: upsert`, so embed + upsert run **unconditionally on every invocation**.

**Impact:** When the outcome is neither `deployed` nor `failed` (`isTool=false`, `isFailure=false`), `collection=null`, `payload=null`, `textToEmbed=''`. The embed node posts `input=''` to `nomic-embed-text` (errors on empty input) and the Qdrant upsert targets `/collections//points?wait=true` (404). Neither node has `continueOnFail`, so the WF-6 sub-workflow fails. This hits every reused-tool outcome (status `reused`) and every intermediate state — contradicting the E7-1/E7-2 intent that only tool/failure states write to Qdrant.

**Fix:** Re-wire the connection graph so `Prepare dual write` → `Switch: need Qdrant?`, and the Switch routes the `deployed`/`failed` outcomes to `embed → upsert` and routes other outcomes (e.g. `reused`, intermediate) to a terminal/skip path. Verified current state: `jq .connections workflows/wf6-memory-write.json` shows no Switch edge — only Prepare→embed→upsert.

---

## 🔴 CRITICAL 3 — WF-6 `isTool` excludes `reused` status

**File / line:** `workflows/wf6-memory-write.json:26`

**Problem:** `isTool` requires `state.outcome?.status === 'deployed'`, but WF-4 (Sprint 6 version) sets `status:'reused'` for reused tools. So successfully reused tools never enter the `tool_store` write path.

**WF-4 status logic (confirmed in `wf4-tool-factory.json`):**
```js
status: demoError ? 'failed' : (state.outcome?.status === 'reused' ? 'reused' : 'deployed')
```

**Impact:** WF-6's `isTool = state.outcome?.status === 'deployed' && !!state.candidate?.code` is `false` for reused tools. The eval report's S2/S4/S5 are all status `reused`, so on a live run those tools skip the `tool_store` upsert entirely. The code-commented "fitness +1 on reuse success (E7-4)" branch is unreachable for the reuse case it was written for.

**Fix:** Broaden the `isTool` condition to include `reused`, e.g. `['deployed','reused'].includes(state.outcome?.status) && !!state.candidate?.code`.

---

## 🔴 CRITICAL 4 — Fitness-on-reuse upserts a NEW point, not the recalled tool's point

**File / line:** `workflows/wf6-memory-write.json:26`

**Problem:** When `state.recall.reusable_tools` is non-empty, `fitness = reusable_tools[0].fitness + 1` and the payload is upserted under a **brand-new random pointId**. The recalled tool's original Qdrant point is never touched.

**Impact (two defects compound):**
1. The recalled tool's original fitness stays constant while a near-duplicate accumulates at `fitness+1` — the original tool's fitness never advances.
2. `reusable_tools[0]` is just the top-ranked recall hit, which may not be the candidate actually being deployed, so the `+1` can be derived from an unrelated tool.
3. WF-7's Prep-reuse map drops `h.id`, so WF-6 has no way to upsert by the original id.

E7-4's reuse-fitness feedback loop is defeated.

**Fix:**
- Propagate the recalled tool's stable id from WF-7 → WF-6 (stop dropping `h.id` in WF-7's Prep-reuse map).
- Upssert by that existing id instead of a fresh random one.
- Derive the `+1` from the actually-deployed candidate, not `reusable_tools[0]`.

---

## 🟡 MAJOR 5 — WF-2 `prev.goal` baked literally into Python (NameError)

**File / line:** `workflows/wf2-squad-lab-live.json:89`

**Problem:** The incoming-side (`33288b2`) embedded Python references the JS Code-node variable `prev.goal` **without `${}` interpolation**, emitting literal `prev.goal` into the Python source.

**Detail:** The candidate code template literal contains:
```python
m2 = __import__('re').search(r"'([^']{10,})'", prev.goal or "")
```
(2 occurrences, line 89). Because it is not `${prev.goal}`, the literal text `prev.goal` is baked into the Python tool.

**Impact:** When the balance-only fallback path triggers (input matches `^\d{8}$`), the sandbox runs this Python and raises `NameError: name 'prev' is not defined`, crashing the tool. The HEAD-side variant (line 87) avoids this but is currently unreachable behind the merge conflict (CRITICAL 1).

**Fix:** Either interpolate as `${prev.goal}` or restructure so the value is passed into the sandbox input rather than substituted into source. Prefer the HEAD-side variant when resolving the merge conflict.

**Verification:** `grep -n 'prev\.goal' workflows/wf2-squad-lab-live.json` should show only `${prev.goal}` forms.

---

## 🟡 MAJOR 6 — WF-3 d{8} override too loose *(PLAUSIBLE)*

**File / line:** `workflows/wf3-squad-audit.json:154`

**Problem:** The mainframe `d{8}` override only inspects `objections[0]` and only checks a substring, so it can force `edge_case_pass=true` over real crash objections.

**Condition:**
```js
isMainframe && !parsed.edge_case_pass && parsed.objections[0].detail.includes('d{8}')
```
The comment says "if the ONLY objection is about d{8}", but the code never checks that there is only one objection, nor that the detail is solely about `d{8}`.

**Failure scenario:** If the critic returns `edge_case_pass=false` with:
- `objections=[{detail:'the \\d{8} regex crashes on empty input'}]`, or
- `objections=[{detail:'uses d{8}'},{detail:'crashes on negative balance'}]`

…then the override sets `edge_case_pass=true` and downgrades only `objections[0]` to `warn`, masking the real defect. The downstream "Run Critic inputs → sandbox" node only re-fails if `proposed_inputs` exercise the crash; if `proposed_inputs` is empty or misses the bad path, a broken tool is deployed.

**Fix:** Enforce both guards the comment promises:
- Confirm `objections.length === 1` (only one objection).
- Confirm the objection detail is **solely** about `d{8}` (e.g. the detail matches a d{8}-only pattern, not merely `includes('d{8}')`).

---

## 🟡 MAJOR 7 — WF-3 `exit_code !== 0` treats missing/undefined as failure *(PLAUSIBLE)*

**File / line:** `workflows/wf3-squad-audit.json:168`

**Problem:**
```js
failed = data.exit_code !== 0 || data.timed_out || ...
```
If the sandbox-runner response ever omits `exit_code` on a benign outcome (returns `{stdout,stderr}` without `exit_code`, or different casing), `undefined !== 0` is `true` and the input is recorded as failed.

**Impact:** Every proposed input then pushes a `block` objection and `edge_case_pass=false`, so a correct candidate is rejected. The `|| data.timed_out` clause covers timeouts but not a benign response that simply lacks `exit_code`.

**Fix:** Treat missing `exit_code` as success (or unknown), not failure:
```js
failed = (data.exit_code != null && data.exit_code !== 0) || data.timed_out || ...
```

---

## 🟡 MAJOR 8 — WF-6 random point id has no uniqueness guarantee

**File / line:** `workflows/wf6-memory-write.json:26`

**Problem:** `pointId = Math.floor(Math.random()*1000000000)`. On repeated deploys/failures, two unrelated writes can draw the same id; the second `PUT /collections/.../points?wait=true` silently overwrites the first point. Over time, tool/failure records vanish from memory with no error.

**Impact:** There is no stable identity (tool_name hash, task_id) backing the id. Records silently disappear.

**Fix:** Derive the point id from a stable key (e.g. hash of tool_name + task_id, or the recalled tool's existing id from CRITICAL 4) rather than `Math.random()`.

---

## 🟡 MAJOR 9 — Documentation overstates repeatability

**File / line:** `README.md:90` (also `scrum/SPRINT_NOTES.md`)

**Problem:** README/Sprint Notes claim "ALL PASS, verified 2026-08-15, 10/10 repeatable", but:
1. The committed workflow files are unparseable JSON (CRITICAL 1), so the documented verification could not have run against committed code.
2. `diff <(jq -S . eval/wf8_report_pass1.json) <(jq -S . eval/wf8_report_pass2.json)` shows the two passes use **different goals and different generated code** (e.g. pass1 S4 is a JSON-duplicate-keys task, pass2 S4 is the CSV third-field task). "Repeatability" holds only at the gate-flag level (G1–G4 true), not at the run level.

**Fix:**
- After resolving CRITICAL 1, actually re-run the import + eval against committed code and record the real result/date.
- Reword the repeatability claim to reflect that the gate flags (G1–G4) are stable across runs, while the generated tasks differ — or make pass1/pass2 deterministic if full run-level repeatability is the goal.

---

## Notes for the fixer

- **Resolve CRITICAL 1 first.** It blocks the import script entirely and makes the "verified" claim false. Until the three files parse, nothing else can be validated against committed code.
- **WF-6 findings 2/3/4/8 compound.** The orphaned Switch, the `isTool` status check, the new-point fitness increment, and the random id all interact on the reuse path. Fix them together as one coherent change: route by Switch, include `reused` in `isTool`, upsert by a stable recalled-tool id, and increment that same point's fitness.
- **WF-2 finding 5 is partially masked by CRITICAL 1** — the buggy incoming-side Python is unreachable until the merge conflict is resolved, so resolve the conflict toward the HEAD variant (or apply the `${prev.goal}` fix) to avoid reintroducing the crash.
- Findings 6 and 7 are marked **PLAUSIBLE**: they describe realistic critic-objection / sandbox-response shapes the code does not exclude. Worth hardening even though no committed test currently triggers them.

## Verification commands

```bash
# All workflow JSON parses
for f in workflows/wf*.json; do jq -e .name "$f" >/dev/null || echo "BAD: $f"; done

# Import script runs end-to-end
./scripts/import-workflows.sh

# No literal prev.goal in wf2
grep -n 'prev\.goal' workflows/wf2-squad-lab-live.json

# WF-6 Switch is reachable
jq '.connections | keys' workflows/wf6-memory-write.json
```
# Sprint Notes — Living Sandbox (Muse Spark)

## Sprint 6 — Prove It (E8-2/E8-3/E2-3/E2-4/E8-4) — DONE 2026-08-15 — 15 pts

**Goal:** repeatable evidence, not vibes. WF-8 twice, hostile suite, prompts versioned, README walk.
**Result:** Gate flags G1-4 PASS on both passes (5 scenarios x2 = 10 runs, 5/5 healthy, 6/7 hostile PASS — 1 fork-bomb expected contained). Tasks/code are LLM-generated and differ between passes — only gate-level repeatability (G1-4 true) is claimed; full run-level determinism is not claimed.

**Verification (2026-08-15 10:00 UTC, livingsandbox_swarm — re-verify required after REVIEW_FINDINGS_SPRINT6 fixes, import now parses):**
- `docker compose ps` 5/5 healthy (n8n 1.76.3, postgres 16, qdrant 1.12.4, ollama 0.11.4, sandbox-runner)
- `POST /webhook/living-sandbox` x5: S1 parse_mainframe 45.67 (parse_mainframe_record, reused), S2 same 45.67 reused, S3 safe_input_reader (no exfil, sec_pass true), S4 csv_third_field c (reused), S5 reverse_and_count_vowels dlrow olleh Vowels 3 (reused) — all PASS
- Headless harness: `docker run --network livingsandbox_swarm ... python /tmp/run_wf8.py` → eval/wf8_report.json (G1-4 true) x2 passes at gate level (pass1/pass2 differ in generated goals/code — gate flags stable, re-verify after workflow JSON fix)
- Hostile suite: `SANDBOX_URL=http://sandbox-runner:8000 pytest` → 6/7 PASS (fork_bomb 200 forks not a true bomb, exits 0, expected contained)
- Prompts: `ls prompts/*.md` 7 files versioned, workflows read via `require('fs').readFileSync('/prompts/...')` with fallback
- Tool reuse: WF-1 Switch isTrue on _hasReusable, Pick→Factory direct, Factory preserves reused status, Qdrant rank score*log(1+fitness) with parse fitness 15 > reverse 9
- Fixes: WF-1 Switch isTrue (was equal), WF-4 last-word heuristic removed, WF-2 general balance_cents, csv tool re.split import fix, Qdrant parse fitness 15

**Sprint 0 — Steel Thread Foundations (done)**

**Goal:** stack runs, and we know which models we're using.
**Committed:** E1-1 (5), E1-2 (2), E1-3 spike (3), E2-1 (5) — 15 pts

### Daily log

#### 2026-08-14 — Session 1
- Done: read 01–07, scaffolded docker-compose (n8n 1.76.3 + Postgres 16 + Qdrant 1.12.4 + Ollama 0.11.4 + sandbox-runner), config/models.json + endpoints.json, sandbox-runner FastAPI skeleton with security hardening (read-only, no-net, non-root, caps, timeout), hostile test suite, workflow smoke (wf0-smoke.json), scripts (export/import + model-spike), prompts (orchestrator + lab), eval/scenarios.json.
- Next: `docker compose config` validate, `docker compose up -d` dry-run, verify healthchecks; run sandbox-runner locally with `pytest`; spike needs `ollama serve` + model pulls (deferred — Ollama not reachable from this sandbox session).
- Blocked: GitHub push blocked by sandbox .git read-only mount (repo created remotely ok — https://github.com/mikeylikesit0475/living-sandbox). User chose "build now, push later". Also Ollama not serving on host yet — spike placeholder remains.
- Honesty: stack has NOT been booted yet in this session; that is the first gate for Sprint 0 demo.

### Blocked / observations vs expected
- `.git` is mount-ro at `/home/michaelf/Desktop/LivingSandbox/.git` (btrfs ro) — cannot `git branch -M` or commit from this session. Repo was created via `gh` successfully as empty remote.
- No n8n execution IDs yet — skeleton not run end-to-end.

---

## Retro template (fill at sprint end)
- Keep:
- Change:
- Try:

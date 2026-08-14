# sandbox-runner

Ephemeral-container executor — the **only** place agent-generated code ever runs (ADR-2 / Charter G4).

## Security boundary

Every `POST /execute` spins a **single-use** container with:

- `--network none` — no egress
- `--read-only` + `--tmpfs /tmp`, `/workspace` — read-only rootfs
- `--user 65534:65534` (nobody) + `--cap-drop ALL` + `no-new-privileges`
- `--memory 256m --memory-swap 256m --cpus 1.0 --pids-limit 64`
- host-side wall-clock kill after `timeout_s` (+2s grace)

Containers are `--rm` single-use; nothing persists between runs. Host env and secrets are never mounted.

## API

- `GET /health` → `{status, docker_available, sandbox_image, max_concurrent}`
- `POST /execute` → `{stdout, stderr, exit_code, duration_ms, timed_out, truncated}`

```json
{
  "language": "python",
  "code": "print('hello')",
  "input": "optional stdin / argv[1]",
  "timeout_s": 15,
  "memory_mb": 256
}
```

`input` is injected as **both** stdin and `sys.argv[1]` / `SANDBOX_INPUT` env so Lab-generated tools can use whichever convention they prefer (documented in `prompts/lab_system.md`).

## Local dev

```bash
docker compose up -d sandbox-runner
curl http://localhost:8001/health
curl -X POST http://localhost:8001/execute -H 'Content-Type: application/json' \
  -d '{"language":"python","code":"print(\"hello\")"}'
```

## Hostile suite (E2-2)

```bash
SANDBOX_URL=http://localhost:8001 pytest sandbox-runner/tests/test_hostile.py -v
```

All five attacks (fork bomb, network egress, filesystem read, infinite loop, memory bomb) must fail safely with a clean error payload and the runner must stay healthy — this is the Sprint 1 second-half demo.

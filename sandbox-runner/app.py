"""
Living Sandbox — sandbox-runner (E2-1 / E2-2)

FastAPI service that executes agent-generated Python code inside ephemeral
containers. This is the ONLY place generated code ever runs (ADR-2 / G4).

Security invariants (06 Risk Register — red lines):
  - No network (--network none)
  - Non-root (--user 65534:nobody)
  - Read-only rootfs (--read-only) + tmpfs workdir
  - mem / cpu / pids caps
  - hard wall-clock timeout (host-side kill)
  - No host env/secrets mounted, no privileged caps

Endpoints:
  GET  /health          → {status, version, running}
  POST /execute         → run code in a fresh container, return stdout/stderr/exit_code/duration_ms
"""

import asyncio
import os
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(title="sandbox-runner", version="1.0.0")

# ---------------------------------------------------------------------------
# Config — env overrides, defaults per 02_ARCHITECTURE §5 and config/endpoints.json
# ---------------------------------------------------------------------------
SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "python:3.11-slim")
DEFAULT_TIMEOUT_S = int(os.getenv("DEFAULT_TIMEOUT_S", "15"))
DEFAULT_MEMORY_MB = int(os.getenv("DEFAULT_MEMORY_MB", "256"))
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "4"))
MAX_QUEUE = int(os.getenv("MAX_QUEUE", "20"))

# Semaphore for concurrency cap (E2-4)
_sem = asyncio.Semaphore(MAX_CONCURRENT)
_queue_depth = 0
_queue_lock = asyncio.Lock()

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class ExecuteRequest(BaseModel):
    language: str = Field(default="python", description="Only 'python' is supported in PoC (ADR-7)")
    code: str = Field(..., description="Python source to execute")
    input: str = Field(default="", description="Stdin-style input injected as argv/stdin per Lab convention")
    timeout_s: Optional[int] = Field(default=None, description="Wall-clock timeout seconds; defaults to server default")
    memory_mb: Optional[int] = Field(default=None, description="Memory limit MB; defaults to server default")

class ExecuteResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int
    timed_out: bool = False
    truncated: bool = False

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_VALID_LANG = {"python"}

def _sanitize_code(code: str) -> str:
    """Reject obviously empty payloads early; real security is the container boundary."""
    if not code or not code.strip():
        raise HTTPException(status_code=400, detail="code must not be empty")
    # 200 KB hard cap — prevents accidental 2GB alloc payloads from blowing up the runner's tmp
    if len(code.encode("utf-8")) > 200_000:
        raise HTTPException(status_code=400, detail="code too large (max 200KB)")
    return code

async def _run_in_container(code: str, stdin_input: str, timeout_s: int, memory_mb: int) -> dict:
    """
    Spin a one-shot container:
      docker run --rm --network none --read-only --user 65534:65534
                 --memory 256m --memory-swap 256m --cpus 1.0 --pids-limit 64
                 --tmpfs /tmp:rw,noexec,nosuid,size=64m
                 python:3.11-slim python -c "<code>"  (with stdin piped)

    Input convention (E2-3): the runner injects `input` two ways so Lab code can
    use either:
      - as stdin (most natural for parser tools)
      - as sys.argv[1] (handy for one-liners)

    Returns raw result dict.
    """
    start = time.monotonic()
    # Use base64 to inject code inside the container (avoids host/tmp bind-mount
    # which breaks under docker.sock mapping where /tmp is not shared with host).
    import base64
    code_b64 = base64.b64encode(code.encode("utf-8")).decode("ascii")

    # Container name for reliable cleanup on timeout
    cname = f"sb-{uuid.uuid4().hex[:12]}"

    # Build docker run command — every flag is a security decision, comment it.
    cmd = [
        "docker", "run",
        "--rm",
        "--name", cname,
        "--network", "none",
        "--read-only",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
        "--tmpfs", "/workspace:rw,noexec,nosuid,size=64m",
        "--user", "65534:65534",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--memory", f"{memory_mb}m",
        "--memory-swap", f"{memory_mb}m",
        "--cpus", "1.0",
        "--pids-limit", "64",
        "-i",
        SANDBOX_IMAGE,
        "sh", "-c",
        f"echo '{code_b64}' | base64 -d > /workspace/code.py && python /workspace/code.py \"$1\"",
        "--",
    ]

    # Pass `input` as both stdin and as argv[1] (Lab convention documented in prompts/lab_system.md)
    # We supply argv[1] by wrapping; simplest: set env + let code read either.
    # Instead, we feed stdin and also expose via env var SANDBOX_INPUT
    env_extra = ["--env", f"SANDBOX_INPUT={stdin_input[:8192]}"] if stdin_input else []
    # Insert env before image name: docker run [opts] --env K=V IMAGE cmd
    if env_extra:
        # splice before image
        idx = cmd.index(SANDBOX_IMAGE)
        cmd = cmd[:idx] + env_extra + cmd[idx:]

    # For argv[1] convenience, append input as extra arg — code can read sys.argv[1] if it wants
    if stdin_input:
        # Avoid oversized argv: cap at 8KB
        cmd.append(stdin_input[:8192])

    proc = None
    timed_out = False
    stdout_b = b""
    stderr_b = b""
    exit_code = -1

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE if stdin_input else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdin_bytes = stdin_input.encode("utf-8") if stdin_input else None
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(input=stdin_bytes),
                timeout=timeout_s + 2,  # grace beyond container's own wall
            )
            exit_code = proc.returncode if proc.returncode is not None else -1
        except asyncio.TimeoutError:
            timed_out = True
            # Hard kill: docker kill + wait
            try:
                subprocess.run(["docker", "kill", cname], timeout=3, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
            try:
                proc.kill()
            except Exception:
                pass
            try:
                await asyncio.wait_for(proc.wait(), timeout=3)
            except Exception:
                pass
            # Collect whatever output exists
            # proc.communicate would hang, so just set markers
            stdout_b = b""
            stderr_b = f"[sandbox-runner] wall-clock timeout after {timeout_s}s — container killed\n".encode()
            exit_code = 124
    finally:
        # Ensure container is gone even on runner crash path
        try:
            subprocess.run(["docker", "rm", "-f", cname], timeout=3, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    duration_ms = int((time.monotonic() - start) * 1000)

    # Truncate huge outputs (defense against memory-bomb stdout spam)
    max_out = 64 * 1024
    truncated = False
    if len(stdout_b) > max_out:
        stdout_b = stdout_b[:max_out]
        truncated = True
    if len(stderr_b) > max_out:
        stderr_b = stderr_b[:max_out]
        truncated = True

    return {
        "stdout": stdout_b.decode("utf-8", errors="replace"),
        "stderr": stderr_b.decode("utf-8", errors="replace"),
        "exit_code": exit_code,
        "duration_ms": duration_ms,
        "timed_out": timed_out,
        "truncated": truncated,
    }

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    # Check docker availability as part of health (but don't require an actual run)
    docker_ok = True
    try:
        subprocess.run(["docker", "info"], timeout=3, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except Exception:
        docker_ok = False
    return {
        "status": "ok" if docker_ok else "degraded",
        "version": app.version,
        "docker_available": docker_ok,
        "sandbox_image": SANDBOX_IMAGE,
        "max_concurrent": MAX_CONCURRENT,
    }

@app.post("/execute", response_model=ExecuteResponse)
async def execute(req: ExecuteRequest):
    global _queue_depth

    if req.language not in _VALID_LANG:
        raise HTTPException(status_code=400, detail=f"unsupported language '{req.language}'; only {sorted(_VALID_LANG)} in PoC")

    code = _sanitize_code(req.code)
    timeout_s = req.timeout_s if req.timeout_s is not None else DEFAULT_TIMEOUT_S
    memory_mb = req.memory_mb if req.memory_mb is not None else DEFAULT_MEMORY_MB

    if timeout_s < 1 or timeout_s > 60:
        raise HTTPException(status_code=400, detail="timeout_s must be 1..60")
    if memory_mb < 64 or memory_mb > 1024:
        raise HTTPException(status_code=400, detail="memory_mb must be 64..1024")

    # Queue / concurrency guard (E2-4)
    async with _queue_lock:
        if _queue_depth >= MAX_QUEUE and _sem.locked():
            # Approximation: if semaphore saturated and queue full, 429
            raise HTTPException(status_code=429, detail="sandbox-runner overloaded — queue full, retry later")
        _queue_depth += 1

    # Try to acquire semaphore without indefinite wait — queued requests wait up to 30s
    try:
        try:
            await asyncio.wait_for(_sem.acquire(), timeout=30)
        except asyncio.TimeoutError:
            raise HTTPException(status_code=429, detail="sandbox-runner overloaded — timed out waiting for slot")
        try:
            result = await _run_in_container(code, req.input, timeout_s, memory_mb)
        finally:
            _sem.release()
    finally:
        async with _queue_lock:
            _queue_depth = max(0, _queue_depth - 1)

    return JSONResponse(content=result)

@app.get("/")
async def root():
    return {"service": "sandbox-runner", "version": app.version, "health": "/health", "execute": "POST /execute"}

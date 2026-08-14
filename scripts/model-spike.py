#!/usr/bin/env python3
"""
E1-3 Spike: measure structured-JSON reliability + latency for Ollama candidates.

For each candidate model (default from config/models.json):
  - 20 calls with a fixed prompt that demands JSON matching `candidate` schema
  - counts valid JSON + required fields (tool_name, description, input_schema, code)
  - records p50/p95 latency

Writes results back into config/models.json (spike_result) and picks winners
for `squad_model` (best % valid) and `level3_model` (best % valid among small models, tie → fastest p50).

Requires: ollama serve running, models pulled.
  ollama pull qwen2.5:7b-instruct   # etc.

Usage:
  python scripts/model-spike.py
  python scripts/model-spike.py --candidates qwen2.5:7b-instruct,llama3.1:8b --runs 20
"""

import argparse
import json
import os
import statistics
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "models.json"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

PROMPT = """You are a tool-making agent. Output ONLY JSON, no prose, no markdown.
Schema:
{
  "tool_name": "snake_case string",
  "description": "one line",
  "input_schema": {"input": "string"},
  "code": "python function code as a string with a function called run(input: str) -> str"
}

Task: write a tool that reverses a string.

Return exactly one JSON object matching the schema above.
"""

REQUIRED_FIELDS = {"tool_name", "description", "input_schema", "code"}

def call_ollama(model: str, prompt: str, opts: dict | None = None) -> tuple[str, float]:
    url = f"{OLLAMA_URL}/api/generate"
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.2, "num_predict": 1024, "think": False, **(opts or {})},
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode())
            latency = time.monotonic() - t0
            return body.get("response", ""), latency
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode()[:500]}") from e
    except Exception as e:
        raise RuntimeError(str(e)) from e

def score_response(text: str) -> tuple[bool, str]:
    text = text.strip()
    # Strip markdown fences if model adds them despite instructions
    if text.startswith("```"):
        lines = text.splitlines()
        # remove first and last fence lines
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        obj = json.loads(text)
    except Exception as e:
        return False, f"invalid JSON: {e} — head: {text[:300]!r}"
    missing = REQUIRED_FIELDS - set(obj.keys())
    if missing:
        return False, f"missing fields {missing} — got keys {list(obj.keys())}"
    if not isinstance(obj.get("tool_name"), str) or not obj["tool_name"]:
        return False, "tool_name not a non-empty string"
    if not isinstance(obj.get("code"), str) or "def " not in obj["code"]:
        return False, "code missing 'def '"
    return True, "ok"

def test_model(model: str, runs: int) -> dict:
    latencies = []
    valid = 0
    failures: list[str] = []
    print(f"\n— Testing {model} ({runs} runs) —")
    for i in range(runs):
        sys.stdout.write(f"  {i+1}/{runs}... ")
        sys.stdout.flush()
        try:
            text, lat = call_ollama(model, PROMPT)
            latencies.append(lat)
            ok, reason = score_response(text)
            if ok:
                valid += 1
                print(f"✓ {lat:.1f}s")
            else:
                failures.append(reason)
                print(f"✗ {lat:.1f}s — {reason[:100]}")
        except Exception as e:
            print(f"✗ error: {e}")
            failures.append(str(e))
            latencies.append(0)
    pct = valid / runs * 100 if runs else 0
    p50 = statistics.median(latencies) if latencies else 0
    p95 = sorted(latencies)[int(len(latencies)*0.95)] if latencies else 0
    print(f"  ⇒ {model}: {valid}/{runs} valid ({pct:.0f}%), p50 {p50:.1f}s p95 {p95:.1f}s")
    if failures:
        print(f"     sample failures: {failures[:3]}")
    return {"model": model, "runs": runs, "valid": valid, "pct_valid": round(pct, 1),
            "p50_s": round(p50, 2), "p95_s": round(p95, 2), "failures_sample": failures[:3]}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", default=None, help="comma-separated model names; default reads config/models.json candidates")
    ap.add_argument("--runs", type=int, default=20)
    args = ap.parse_args()

    cfg = json.loads(CONFIG.read_text())
    if args.candidates:
        squad_candidates = [s.strip() for s in args.candidates.split(",") if s.strip()]
        level3_candidates = []
    else:
        squad_candidates = [c["name"] for c in cfg.get("candidates_tested", [])]
        level3_candidates = [c["name"] for c in cfg.get("level3_candidates", [])]

    all_candidates = squad_candidates + level3_candidates
    if not all_candidates:
        print("No candidates found — check config/models.json", file=sys.stderr)
        sys.exit(2)

    print(f"Ollama: {OLLAMA_URL}")
    print(f"Candidates: {all_candidates}")

    # Check connectivity first
    try:
        urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=5).read()
    except Exception as e:
        print(f"Cannot reach Ollama at {OLLAMA_URL}: {e}", file=sys.stderr)
        print("Start it with: ollama serve  (and pull models first)", file=sys.stderr)
        sys.exit(2)

    results = []
    for m in all_candidates:
        results.append(test_model(m, args.runs))

    # Pick winners
    squad_results = [r for r in results if r["model"] in squad_candidates]
    level3_results = [r for r in results if r["model"] in (level3_candidates or [])]

    def best_by_valid_then_speed(rows):
        return sorted(rows, key=lambda r: (-r["pct_valid"], r["p50_s"]))[0] if rows else None

    squad_winner = best_by_valid_then_speed(squad_results)
    level3_winner = best_by_valid_then_speed(level3_results) or best_by_valid_then_speed(results)

    print("\n" + "="*60)
    print("RESULTS")
    for r in results:
        print(f"  {r['model']:30s} {r['valid']:2d}/{r['runs']:2d} ({r['pct_valid']:4.0f}%)  p50 {r['p50_s']:4.1f}s  p95 {r['p95_s']:4.1f}s")
    print(f"\nSquad winner : {squad_winner['model'] if squad_winner else '—'}")
    print(f"Level-3 winner: {level3_winner['model'] if level3_winner else '—'}")
    print("="*60)

    # Write back to config
    import datetime
    cfg["spike_status"] = "done"
    cfg["spike_date"] = datetime.datetime.utcnow().isoformat() + "Z"
    cfg["spike_notes"] = f"Spike: {args.runs} runs per model, JSON validity + p50/p95 measured"
    for r in results:
        # annotate candidates
        for c in cfg.get("candidates_tested", []):
            if c["name"] == r["model"]:
                c["spike_result"] = r
        for c in cfg.get("level3_candidates", []):
            if c["name"] == r["model"]:
                c["spike_result"] = r
    if squad_winner:
        cfg["squad_model"]["name"] = squad_winner["model"]
        cfg["squad_model"]["spike_result"] = squad_winner
    if level3_winner:
        cfg["level3_model"]["name"] = level3_winner["model"]
        cfg["level3_model"]["spike_result"] = level3_winner

    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"\n✓ Wrote results to {CONFIG}")

if __name__ == "__main__":
    main()

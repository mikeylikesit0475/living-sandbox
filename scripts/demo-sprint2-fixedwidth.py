#!/usr/bin/env python3
"""
Sprint 2 — Full Lab live demo: fixed-width mainframe parser with Write→Test loop.
Uses Ollama qwen2.5:7b via docker network and sandbox via TestClient.
Shows: first attempt may fail (e.g., python prefix), stderr fed back, second attempt passes.
"""

import json, pathlib, subprocess, sys, textwrap, os

GOAL = "Parse this fixed-width 1990s mainframe record: '00123JOHN DOE  00004567' — fields are 0:5 id, 5:14 name, 14:22 balance_cents. Extract all three as JSON and return the balance as dollars (4567 cents → 45.67). Keep input convention: read stdin/argv/SANDBOX_INPUT."

def ollama_generate(prompt: str, model="qwen2.5:7b") -> str:
    import subprocess, json as js, tempfile, os
    # Use docker run with python + requests via swarm network (proven pattern)
    payload = {"model": model, "prompt": prompt, "stream": False, "format": "json", "options": {"temperature": 0.2, "num_predict": 2048, "think": False}}
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, dir='/tmp') as f:
        js.dump(payload, f)
        fname = f.name
    # Use python container to call Ollama (curl payload via volume is tricky with quoting)
    cmd = [
        "docker","run","--rm","--network","livingsandbox_swarm",
        "-v", f"{fname}:/tmp/payload.json:ro",
        "curlimages/curl:8.4.0","-s","-X","POST","http://ollama:11434/api/generate",
        "-H","Content-Type: application/json","-d","@/tmp/payload.json","--max-time","90"
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=100)
    os.unlink(fname)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[:1000] + r.stdout[:500])
    j = js.loads(r.stdout)
    return j.get("response","")

def call_sandbox(code: str, inp: str):
    sys.path.insert(0, "sandbox-runner")
    from fastapi.testclient import TestClient
    from app import app
    c = TestClient(app)
    return c.post("/execute", json={"language":"python","code":code,"input":inp,"timeout_s":10}).json()

def parse_candidate(raw: str) -> dict:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    start = cleaned.find('{')
    end = cleaned.rfind('}')
    js = cleaned[start:end+1]
    cand = json.loads(js)
    return cand

def main():
    print(f"Goal: {GOAL}\n")
    system_prompt = pathlib.Path("prompts/lab_synthesis_live.md").read_text()
    prompt = system_prompt + f"\n\nGoal: {GOAL}\n\nReturn ONLY JSON."
    print("→ Lab Synthesis attempt 1 (qwen2.5:7b)")
    raw1 = ollama_generate(prompt)
    print(f"Raw preview: {raw1[:800]!r}\n")
    try:
        cand1 = parse_candidate(raw1)
        print(f"Candidate 1: {cand1['tool_name']} — {cand1['description'][:100]}")
        print(f"Code preview: {cand1['code'][:600]!r}\n")
    except Exception as e:
        print(f"Parse failed: {e}\nRaw: {raw1[:1500]!r}")
        cand1 = None
        # Repair prompt
        prompt2 = prompt + f"\n\nPrevious attempt failed JSON parse: {e}. Fix it and return ONLY valid JSON."
        raw1 = ollama_generate(prompt2)
        cand1 = parse_candidate(raw1)
        print(f"Repaired candidate: {cand1['tool_name']}")

    test_input = "00123JOHN DOE  00004567"
    print(f"→ Test 1 in sandbox with input {test_input!r}")
    j1 = call_sandbox(cand1["code"], test_input)
    print(f"exit={j1['exit_code']} stdout={j1['stdout'][:800]!r} stderr={j1['stderr'][:600]!r}")
    if j1["exit_code"] == 0:
        print("\n✅ First attempt PASSED — would deploy (Tool Factory thin HTTP client, E4-3)")
        try:
            out = json.loads(j1["stdout"])
            print(f"Parsed output: {out}")
        except: pass
        return

    print("\n→ Test 1 FAILED — feeding stderr back to Synthesis (loop.remaining 2)")
    prompt2 = system_prompt + f"\n\nGoal: {GOAL}\n\nPrevious attempt produced candidate with tool_name {cand1['tool_name']} but sandbox failed:\nstderr: {j1['stderr'][:800]}\nstdout: {j1['stdout'][:500]}\nFix the code (watch for 'python' prefix, missing imports, off-by-one slices) and return corrected JSON.\n\nReturn ONLY JSON."
    raw2 = ollama_generate(prompt2)
    print(f"Raw2 preview: {raw2[:800]!r}\n")
    cand2 = parse_candidate(raw2)
    print(f"Candidate 2: {cand2['tool_name']}")
    print(f"Code preview: {cand2['code'][:600]!r}\n")
    j2 = call_sandbox(cand2["code"], test_input)
    print(f"exit={j2['exit_code']} stdout={j2['stdout'][:800]!r} stderr={j2['stderr'][:600]!r}")
    if j2["exit_code"] == 0:
        print("\n✅ Second attempt PASSED after loop — Write→Test loop works (E5-2), remaining 2 → 1")
        try:
            out = json.loads(j2["stdout"])
            print(f"Parsed output: {out}")
            if "45.67" in j2["stdout"] or "45.67" in str(out):
                print("✅ Balance dollars correct (45.67)")
        except: pass
    else:
        print("\n❌ Second attempt still failed — would exhaust loop after 3 tries (E5-2, ADR-5)")

if __name__ == "__main__":
    main()

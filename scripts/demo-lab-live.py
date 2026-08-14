#!/usr/bin/env python3
"""
Sprint 2 demo — Lab writes a fixed-width parser, tests in sandbox, shows Write→Test loop.
Uses Ollama via docker network (ollama:11434) and sandbox via TestClient (host docker).
"""

import json, sys, pathlib, subprocess, os, textwrap

GOAL = "Parse this fixed-width 1990s mainframe record: '00123JOHN DOE  00004567' — fields are 0:5 id, 5:14 name, 14:22 balance_cents. Extract all three as JSON and return the balance as dollars (4567 cents → 45.67)."

PROMPT_FILE = pathlib.Path("prompts/lab_synthesis_live.md")

def call_ollama_via_docker(prompt: str) -> dict:
    # Run a small python inside docker network to call Ollama (bypasses host proxy/netns)
    import tempfile, json as js
    script = textwrap.dedent(f"""
        import json, requests
        prompt = open('/workspace/prompts/lab_synthesis_live.md').read() + "\\n\\nGoal: {GOAL}\\n\\nReturn ONLY JSON."
        resp = requests.post('http://ollama:11434/api/generate', json={{
            'model': 'qwen2.5:1.5b',
            'prompt': prompt,
            'stream': False,
            'format': 'json',
            'options': {{'temperature': 0.2, 'num_predict': 2048, 'think': False}}
        }}, timeout=90)
        js = resp.json()
        raw = js.get('response','')
        print(raw)
    """)
    # Use docker run with python:3.11-slim + requests
    cmd = [
        "docker","run","--rm","--network","livingsandbox_swarm",
        "-v", f"{pathlib.Path.cwd()}:/workspace","-w","/workspace",
        "python:3.11-slim","bash","-c",
        "pip install -q requests >/dev/null 2>&1; python3 << 'PY'\n" + script + "\nPY"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print("Docker Ollama call failed:", result.stderr[:1000], result.stdout[:1000])
        raise RuntimeError(f"docker ollama call failed {result.returncode}")
    raw = result.stdout.strip()
    # The python script prints only raw; it may contain extra pip noise - take last json-looking block
    # Find first { to last }
    start = raw.find('{')
    end = raw.rfind('}')
    if start == -1:
        print("No JSON in LLM raw:", raw[:2000])
        raise ValueError("No JSON")
    raw_json = raw[start:end+1]
    # Sometimes LLM wraps in markdown fences - strip
    if raw_json.startswith("```"):
        lines = raw_json.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines = lines[:-1]
        raw_json = "\n".join(lines)
    return json.loads(raw_json), raw

def call_sandbox(code: str, inp: str):
    sys.path.insert(0, "sandbox-runner")
    from fastapi.testclient import TestClient
    from app import app
    c = TestClient(app)
    r = c.post("/execute", json={"language":"python","code":code,"input":inp,"timeout_s":10})
    return r.json()

def main():
    print(f"Goal: {GOAL}\n")
    print("→ Step 1: Lab Synthesis (Ollama qwen2.5:1.5b)")
    # Direct call via docker exec (simpler, bypasses python container)
    import subprocess, json as js
    # Use docker exec living-sandbox-ollama to call via localhost inside container
    prompt_text = PROMPT_FILE.read_text() + f"\n\nGoal: {GOAL}\n\nReturn ONLY JSON."
    # Use curl via docker network container
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"model":"qwen2.5:1.5b","prompt":prompt_text,"stream":False,"format":"json","options":{"temperature":0.2,"num_predict":2048,"think":False}}, f)
        fname = f.name
    # Use docker run curl to call Ollama
    cmd = ["docker","run","--rm","--network","livingsandbox_swarm","-v",f"{fname}:/tmp/payload.json","curlimages/curl:8.4.0","-s","-X","POST","http://ollama:11434/api/generate","-H","Content-Type: application/json","-d",f"@{fname}"]
    # Simpler: use docker exec on ollama container with curl (it has curl? maybe not)
    # Let's just use the docker run python approach but fix it
    cmd2 = [
        "docker","run","--rm","--network","livingsandbox_swarm",
        "-v", f"{pathlib.Path.cwd()}:/workspace","-w","/workspace",
        "python:3.11-slim","bash","-c",
        "pip install -q requests >/dev/null 2>&1\n"
        "python3 << 'PY'\n"
        "import json, requests\n"
        f"prompt = open('prompts/lab_synthesis_live.md').read() + '''\\n\\nGoal: {GOAL}\\n\\nReturn ONLY JSON.'''\n"
        "resp = requests.post('http://ollama:11434/api/generate', json={'model':'qwen2.5:1.5b','prompt':prompt,'stream':False,'format':'json','options':{'temperature':0.2,'num_predict':2048,'think':False}}, timeout=90)\n"
        "j = resp.json()\n"
        "print(j.get('response',''))\n"
        "PY\n"
    ]
    result = subprocess.run(cmd2, capture_output=True, text=True, timeout=120)
    raw = result.stdout.strip()
    if result.returncode != 0:
        print("Ollama call failed:", result.stderr[:2000])
        print("stdout:", raw[:2000])
        sys.exit(1)
    print(f"LLM raw (first 800): {raw[:800]!r}\n")
    # Parse JSON
    # Find JSON object
    import re
    # LLM may output markdown fences
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines[-1] = ""
        cleaned = "\n".join(lines).strip()
    # Extract JSON
    start = cleaned.find('{')
    end = cleaned.rfind('}')
    json_str = cleaned[start:end+1] if start!=-1 else cleaned
    try:
        cand = json.loads(json_str)
        print("Candidate:", json.dumps(cand, indent=2)[:2500])
    except Exception as e:
        print(f"JSON parse failed: {e}\nRaw was: {cleaned[:2000]!r}")
        sys.exit(1)

    print("\n→ Step 2: Test candidate in sandbox (real ephemeral container)")
    code = cand["code"]
    test_input = "00123JOHN DOE  00004567"
    print(f"Test input: {test_input!r}")
    print(f"Code preview: {code[:700]!r}\n")
    j = call_sandbox(code, test_input)
    print(f"Sandbox exit={j['exit_code']} timed_out={j['timed_out']} duration={j['duration_ms']}ms")
    print(f"stdout: {j['stdout'][:2000]!r}")
    print(f"stderr: {j['stderr'][:800]!r}")
    if j['exit_code']==0:
        print("\n✅ First attempt PASSED — would deploy via WF-4")
        # Try to parse stdout as JSON to verify fields
        try:
            out = json.loads(j['stdout'])
            print(f"Parsed output: {out}")
            if "balance" in str(out).lower() or "45.67" in j['stdout']:
                print("✅ Output contains balance dollars as expected")
        except:
            pass
    else:
        print("\n❌ First attempt FAILED — stderr would be fed back to Synthesis (E5-2 loop, remaining--)")
        print("Would retry with prompt: 'Previous attempt failed with:' + stderr")

    print("\n→ Step 3: swarm_log rows")
    import subprocess as sp
    r = sp.run(["docker","exec","living-sandbox-postgres","psql","-U","n8n","-d","n8n","-c","SELECT task_id, workflow, gate, verdict FROM swarm_log ORDER BY id DESC LIMIT 5;"], capture_output=True, text=True)
    print(r.stdout[:1000])

if __name__ == "__main__":
    main()

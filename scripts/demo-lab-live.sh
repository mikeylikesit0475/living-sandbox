#!/usr/bin/env bash
# Sprint 2 demo — Lab writes a fixed-width parser, fails, fixes, passes
# Uses Ollama via docker network (ollama:11434) and sandbox-runner via host mount
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"

# The fixed-width demo goal (from eval/scenarios.json S1)
GOAL='Parse this fixed-width 1990s mainframe record: '\''00123JOHN DOE  00004567'\'' — fields are 0:5 id, 5:14 name, 14:22 balance_cents. Extract all three as JSON and return the balance as dollars (4567 cents → 45.67).'

echo "Goal: $GOAL"
echo ""
echo "→ Step 1: Lab Synthesis (Ollama qwen2.5:1.5b) — generate candidate"
docker run --rm --network livingsandbox_swarm -v "$DIR:/workspace" -w /workspace python:3.11-slim bash -c "
pip install -q requests 2>&1 | tail -n 5
python3 << 'PY'
import json, requests, textwrap, sys
prompt = open('prompts/lab_synthesis_live.md').read() + '\n\nGoal: $GOAL\n\nReturn ONLY JSON.'
# Call Ollama via internal network
resp = requests.post('http://ollama:11434/api/generate', json={
    'model': 'qwen2.5:1.5b',
    'prompt': prompt,
    'stream': False,
    'format': 'json',
    'options': {'temperature': 0.2, 'num_predict': 2048, 'think': False}
}, timeout=60)
j = resp.json()
raw = j.get('response','')
print('LLM raw:', raw[:800])
try:
    cand = json.loads(raw)
    # fix markdown fences if present
    if isinstance(cand, str):
        cand = json.loads(cand)
    print('Candidate:', json.dumps(cand, indent=2)[:2000])
    open('/tmp/candidate.json','w').write(json.dumps(cand))
except Exception as e:
    print('JSON parse fail:', e)
    sys.exit(1)
PY
"
cat /tmp/candidate.json 2>/dev/null | head -n 50

echo ""
echo "→ Step 2: Test candidate in sandbox (real container)"
docker run --rm --network livingsandbox_swarm -v "$DIR:/workspace" -w /workspace python:3.11-slim bash -c "
import json, requests
cand = json.load(open('/tmp/candidate.json'))
code = cand['code']
# Test input is the record line
test_input = '00123JOHN DOE  00004567'
print('Test input:', repr(test_input))
# Call sandbox via internal network (sandbox-runner:8000) — but sandbox-runner runs on host's docker, not inside swarm? Use host gateway
# Instead use the host's 8001 via docker host
import subprocess, json as js
# Use the Python FastAPI TestClient fallback: directly call sandbox via host's docker exec
print('Code preview:', code[:600])
"
# Direct sandbox test via host's TestClient (since sandbox-runner is on host docker)
python3 << 'PY'
import json, sys
sys.path.insert(0, 'sandbox-runner')
from fastapi.testclient import TestClient
from app import app
c = TestClient(app)
cand = json.load(open('/tmp/candidate.json'))
code = cand['code']
test_input = '00123JOHN DOE  00004567'
r = c.post('/execute', json={'language':'python','code':code,'input':test_input,'timeout_s':10})
j = r.json()
print(f\"Sandbox exit={j['exit_code']} timed_out={j['timed_out']} duration={j['duration_ms']}ms\")
print(f\"stdout: {j['stdout'][:2000]!r}\")
print(f\"stderr: {j['stderr'][:800]!r}\")
if j['exit_code']==0:
    print('✅ First attempt passed — would deploy via WF-4')
else:
    print('❌ First attempt failed — stderr would be fed back to Synthesis for loop iteration (loop.remaining--, E5-2)')
    open('/tmp/first_stderr.txt','w').write(j['stderr']+j['stdout'])
PY

echo ""
echo "→ Step 3: swarm_log (E1-4) — check postgres"
docker exec living-sandbox-postgres psql -U n8n -d n8n -c "SELECT task_id, workflow, gate, verdict, duration_ms FROM swarm_log ORDER BY id DESC LIMIT 5;" 2>&1 | head -n 20

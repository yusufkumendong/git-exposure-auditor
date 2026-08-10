#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d -t gea-v32-test.XXXXXX)"
SERVER_PID=""
cleanup() { [[ -n "$SERVER_PID" ]] && kill "$SERVER_PID" 2>/dev/null || true; rm -rf "$TMP_DIR"; }
trap cleanup EXIT INT TERM

python3 "$ROOT_DIR/tests/mock_server.py" &
SERVER_PID=$!
for _ in {1..30}; do curl -s http://127.0.0.1:18765/ >/dev/null && break; sleep 0.1; done

python3 - "$ROOT_DIR" "$TMP_DIR" <<'PY'
import json, subprocess, sys
from pathlib import Path
root=Path(sys.argv[1]); tmp=Path(sys.argv[2])

def run(*args, expect=0):
    p=subprocess.run([str(root/'bin/gea'), *args], text=True, capture_output=True)
    if p.returncode != expect:
        raise AssertionError(f"command failed {p.returncode}: {p.stderr}\n{p.stdout}")
    return p

def jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]

# Exposure fixture expands through all tiers.
report=tmp/'exposed'
run('--mode','best-practice','--target','http://127.0.0.1:18765','--authorized','--allow-private',
    '--concurrency','2','--rate','5','--retries','1','--report-dir',str(report),'--quiet')
endpoints=jsonl(report/'endpoint-results.jsonl'); hosts=jsonl(report/'host-summary.jsonl')
assert len(endpoints)==8
assert hosts[0]['verdict']=='valid_exposure'
assert hosts[0]['endpoint_requests']==8 and hosts[0]['baseline_requests']>=1
assert any(x['classification']=='waf_challenge' for x in endpoints)
assert any(x['classification']=='rate_limited' and x['retries']==1 for x in endpoints)
assert (report/'results.jsonl').exists() and (report/'report.html').exists()
assert (report/'hackerone-findings.md').read_text(encoding='utf-8').count('## Candidate ')==1

# Clean SPA fixture stops after tier 1 and saves six endpoint requests.
clean=tmp/'clean'
run('--mode','best-practice','--target','http://127.0.0.1:18765/clean','--authorized','--allow-private',
    '--report-dir',str(clean),'--quiet')
clean_endpoints=jsonl(clean/'endpoint-results.jsonl'); clean_hosts=jsonl(clean/'host-summary.jsonl')
assert len(clean_endpoints)==2
assert clean_hosts[0]['verdict']=='not_exposed'
assert clean_hosts[0]['saved_endpoint_requests']==6
assert 'Endpoint request dihemat: 6' in (clean/'summary.txt').read_text(encoding='utf-8')

# Resume does not duplicate completed targets and rebuilds reports from persisted JSONL.
run('--mode','best-practice','--target','http://127.0.0.1:18765/clean','--authorized','--allow-private',
    '--report-dir',str(clean),'--resume','--quiet')
assert len(jsonl(clean/'endpoint-results.jsonl'))==2
assert len(jsonl(clean/'host-summary.jsonl'))==1
# Resume with changed scan semantics is rejected.
p=run('--mode','best-practice','--target','http://127.0.0.1:18765/clean','--authorized','--allow-private',
    '--report-dir',str(clean),'--resume','--full-scan','--quiet', expect=1)
assert 'resume' in p.stderr.lower()

# Full scan override checks all eight endpoints.
full=tmp/'full'
run('--mode','best-practice','--target','http://127.0.0.1:18765/clean','--authorized','--allow-private',
    '--full-scan','--report-dir',str(full),'--quiet')
assert len(jsonl(full/'endpoint-results.jsonl'))==8
assert jsonl(full/'host-summary.jsonl')[0]['saved_endpoint_requests']==0

# Authorized advanced requires policy metadata and remains non-evasive.
scope=tmp/'scope.txt'; scope.write_text('include 127.0.0.1\n', encoding='utf-8')
policy=tmp/'policy.json'; policy.write_text(json.dumps({
  'program': {'name':'Local Test','policy_reference':'local-fixture','authorization_confirmed':True,'bypass_permission_confirmed':True},
  'permissions': {'advanced_validation':True,'waf_bypass_testing':True,'repository_download':False,'credential_testing':False}
}), encoding='utf-8')
advanced=tmp/'advanced'
run('--mode','authorized-advanced','--target','http://127.0.0.1:18765','--scope',str(scope),
    '--policy-file',str(policy),'--authorized','--bypass-permitted','--allow-private','--report-dir',str(advanced),'--quiet')
meta=json.loads((advanced/'run-metadata.json').read_text(encoding='utf-8'))
assert meta['policy']['program_name']=='Local Test'
assert meta['automatic_evasion'] is False

# Missing policy gates the advanced mode.
p=run('--mode','authorized-advanced','--target','http://127.0.0.1:18765','--authorized','--bypass-permitted', expect=1)
assert 'wajib' in p.stderr.lower()

# Explicit scope must not be widened by target input.
out_scope=tmp/'out-scope.txt'; out_scope.write_text('include example.com\n', encoding='utf-8')
p=run('--mode','best-practice','--target','http://127.0.0.1:18765','--scope',str(out_scope),'--authorized','--allow-private', expect=1)
assert 'in-scope' in p.stderr.lower()

# Explain is local and deterministic.
p=run('explain','--report-dir',str(clean))
assert 'Verdict host' in p.stdout and 'not_exposed' in p.stdout
print('Integration test: PASS')
PY

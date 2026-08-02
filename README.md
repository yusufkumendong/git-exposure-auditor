# Git Exposure Auditor

**Current release: v2.0.0**

Git Exposure Auditor is a scope-aware, non-destructive toolkit for detecting publicly exposed Git metadata with automated discovery, soft-404 reduction, confidence scoring, safe evidence collection, and report drafting.

> **Important:** This tool can automate a strong research workflow, but it cannot guarantee report acceptance or a bounty. Bounty decisions depend on program policy, scope, impact, duplication, report quality, and triage decisions.

## What v2 automates

- Authorized target preparation.
- Passive subdomain discovery.
- Scope include/exclude enforcement.
- HTTP reachability inventory.
- `/.git/HEAD` validation.
- Randomized missing-path comparison.
- Optional bounded confirmation of additional Git metadata signatures.
- Confidence scoring and classification.
- Sanitized evidence files.
- A manual-review queue.
- A Markdown summary and responsible-disclosure draft.
- New-finding history and resume support.

## What v2 intentionally does not do

- Dump or reconstruct repositories.
- Enumerate Git objects.
- Extract source code or commit history.
- Harvest or test secrets and credentials.
- Bypass authentication or authorization.
- Evade a WAF or rotate proxies.
- Perform denial-of-service testing.
- Submit reports automatically.

The objective is **maximum confidence with minimum requests and minimum retained data**.

## Weakness classification

The primary weakness is:

```text
CWE-527 — Exposure of Version-Control Repository to an Unauthorized Control Sphere
```

A valid Git repository normally has a `HEAD` file containing either a symbolic reference such as `ref: refs/heads/main` or a detached object identifier. The toolkit distinguishes this signature from generic error pages before producing a positive result.

## Architecture

```text
Authorized Input
      ↓
Scope Policy
      ↓
Passive Discovery or Exact Target List
      ↓
Scope Filtering and Normalization
      ↓
ProjectDiscovery httpx Reachability Inventory
      ↓
Randomized Missing-Path Baseline
      ↓
Git HEAD Signature Validation
      ↓
Optional Safe Metadata Confirmation
      ↓
Confidence Scoring and Classification
      ↓
Sanitized JSONL / CSV / Markdown / Report Draft
      ↓
Manual Validation and Responsible Disclosure
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for details.

## Repository structure

```text
git-exposure-auditor/
├── bin/
│   └── git-exposure-auditor
├── lib/
│   ├── common.sh
│   ├── scope.py
│   ├── validator.py
│   └── report.py
├── scripts/
│   ├── easy.sh
│   ├── medium.sh
│   ├── hard.sh
│   └── best-practice.sh
├── config/
│   └── scope.example.json
├── examples/
│   ├── targets.example.txt
│   └── paths.example.txt
├── docs/
│   ├── ARCHITECTURE.md
│   ├── GITHUB_RELEASE_v2.0.0.md
│   ├── MIGRATION_v1_TO_v2.md
│   ├── REMEDIATION.md
│   ├── REPORT_TEMPLATE.md
│   ├── SCORING.md
│   ├── TROUBLESHOOTING.md
│   └── WORKFLOWS.md
├── tests/
│   ├── mock_httpx.sh
│   ├── mock_server.py
│   └── run-tests.sh
├── .github/workflows/ci.yml
├── install.sh
├── VERSION
├── CHANGELOG.md
├── SECURITY.md
├── CONTRIBUTING.md
└── LICENSE
```

## Requirements

Core:

- Linux, WSL, or another Unix-like environment.
- Bash 4+.
- Python 3.9+.
- `curl`.
- `jq`.
- ProjectDiscovery `httpx`.

Recommended:

- `assetfinder` for additional passive discovery.
- Go for installing ProjectDiscovery and Tomnomnom tools.

Optional:

- `anew`; v2 also includes built-in history tracking.
- `shellcheck` for development checks.

## Kali Linux installation

Kali packages ProjectDiscovery httpx as `httpx-toolkit` to avoid a name collision with the unrelated Python HTTPX CLI.

```bash
sudo apt update
sudo apt install -y bash curl jq python3 git unzip golang-go httpx-toolkit
```

Install `assetfinder`:

```bash
go install -v github.com/tomnomnom/assetfinder@latest
export PATH="$(go env GOPATH)/bin:$PATH"
hash -r
```

Verify:

```bash
httpx-toolkit -version
assetfinder --help
```

Run the installer check and create a global command:

```bash
chmod +x install.sh
./install.sh --check --link
```

The global command becomes:

```bash
git-exposure-auditor --help
```

## Generic Go installation

```bash
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
go install -v github.com/tomnomnom/assetfinder@latest
export PATH="$(go env GOPATH)/bin:$PATH"
hash -r
```

When multiple commands are named `httpx`, select ProjectDiscovery explicitly:

```bash
HTTPX_BIN=/usr/bin/httpx-toolkit \
  ./bin/git-exposure-auditor --domain example.com --authorized
```

## Quick start

### Domain mode

Use domain mode only when passive subdomain discovery and automated probing are allowed.

```bash
./bin/git-exposure-auditor \
  --domain example.com \
  --authorized
```

### Target-list mode

```bash
./bin/git-exposure-auditor \
  --targets examples/targets.example.txt \
  --authorized
```

### High-confidence safe confirmation

```bash
./bin/git-exposure-auditor \
  --domain example.com \
  --authorized \
  --confirm \
  --threads 10 \
  --rate-limit 5
```

Safe confirmation checks a small allowlist:

```text
/.git/config
/.git/packed-refs
/.git/index
/.git/logs/HEAD
```

It reads at most the configured response-size limit, checks signatures in memory, does not save response bodies, and stops after two additional signatures.

### Strict scope policy

Copy the example:

```bash
cp config/scope.example.json config/scope.local.json
```

Edit the include, exclude, port, and limit rules. Then run:

```bash
./bin/git-exposure-auditor \
  --domain example.com \
  --scope config/scope.local.json \
  --authorized \
  --confirm
```

Do not commit private program details in `scope.local.json`.

### Approved nested application paths

```bash
./bin/git-exposure-auditor \
  --domain example.com \
  --paths examples/paths.example.txt \
  --authorized
```

Use only paths already known and permitted by the program. Do not provide a large directory-brute-force wordlist.

### Conservative run

```bash
./bin/git-exposure-auditor \
  --domain example.com \
  --authorized \
  --threads 5 \
  --rate-limit 2 \
  --timeout 10
```

### Dry run

Validate the scope and prepare inputs without probing HTTP services:

```bash
./bin/git-exposure-auditor \
  --domain example.com \
  --authorized \
  --dry-run
```

### History tracking

```bash
./bin/git-exposure-auditor \
  --domain example.com \
  --authorized \
  --history results/finding-history.txt
```

The run writes newly observed confirmed or probable URLs to `new-findings.txt`.

### Resume a prior validation run

```bash
./bin/git-exposure-auditor \
  --targets authorized-targets.txt \
  --authorized \
  --resume-from results/previous-run/findings.jsonl
```

Completed task IDs are reused and only missing URL/path combinations are validated.

## Easy, Medium, Hard, and Best Practice

The level names describe workflow complexity, not permission to become more aggressive.

### Easy

One explicit target with one worker and one request per second:

```bash
./scripts/easy.sh https://example.com --authorized
```

### Medium

A prepared target list:

```bash
./scripts/medium.sh examples/targets.example.txt --authorized
```

### Hard

Passive discovery and controlled validation:

```bash
./scripts/hard.sh example.com --authorized
```

Enable safe confirmation through the wrapper:

```bash
SAFE_CONFIRM=1 THREADS=10 RATE_LIMIT=5 \
  ./scripts/hard.sh example.com --authorized
```

### Best Practice

The complete CLI:

```bash
./scripts/best-practice.sh \
  --domain example.com \
  --scope config/scope.local.json \
  --paths approved-paths.txt \
  --confirm \
  --authorized
```

See [`docs/WORKFLOWS.md`](docs/WORKFLOWS.md) for advantages, disadvantages, and selection guidance.

## Scope policy

Example:

```json
{
  "program": "example-authorized-program",
  "authorized": true,
  "include": ["example.com", "*.example.com"],
  "exclude": ["status.example.com"],
  "allowed_ports": ["http:80", "https:443"],
  "application_paths": ["/"],
  "max_threads": 20,
  "max_rate_limit": 10,
  "max_tasks": 10000,
  "max_response_bytes": 65536
}
```

Rules:

- Exclusions override inclusions.
- Wildcard `*.example.com` does not automatically include the root `example.com`.
- Explicit CLI ports must exist in `allowed_ports`.
- CLI concurrency cannot exceed the scope maximum.
- Application paths reject query strings, fragments, and traversal segments.
- Every request host is checked against scope again by the validator.

## Classification model

| Classification | Meaning |
|---|---|
| `CONFIRMED` | Valid Git `HEAD` signature and a distinct missing-path baseline |
| `PROBABLE` | Git-like evidence exists, but confidence is incomplete |
| `SOFT_404` | Response resembles the site's generic missing-page behavior |
| `BLOCKED` | HTTP 401/403 or equivalent access denial |
| `REDIRECTED` | Endpoint redirected; redirects were not followed |
| `NOT_EXPOSED` | No valid Git `HEAD` signature was found |
| `ERROR` | Network, TLS, timeout, or processing error |

The score is a prioritization aid, not a CVSS score. See [`docs/SCORING.md`](docs/SCORING.md).

## Output files

Every successful run creates an isolated directory such as:

```text
results/example.com-v2-20260802-190000/
```

Important files:

| File | Purpose |
|---|---|
| `scope-snapshot.json` | Exact scope policy used for the run |
| `scan-input.txt` | Normalized in-scope hosts or URLs |
| `application-paths.txt` | Approved application base paths |
| `reachable.jsonl` | ProjectDiscovery reachability inventory |
| `reachable-urls.txt` | Unique reachable base URLs |
| `findings.jsonl` | Complete sanitized validation results |
| `findings.csv` | Spreadsheet-friendly review data |
| `confirmed.txt` | Confirmed Git metadata endpoints |
| `probable.txt` | Probable endpoints requiring review |
| `manual-review.txt` | Combined confirmed and probable queue |
| `scan-summary.json` | Machine-readable aggregate summary |
| `summary.md` | Human-readable audit summary |
| `report-draft.md` | Draft disclosure report for the highest-ranked result |
| `metadata.json` | Run settings, timing, versions, and coverage |
| `versions.txt` | Dependency versions |
| `command.txt` | Reproducible command invocation |
| `crtsh-errors.log` | Certificate Transparency diagnostics |
| `assetfinder-errors.log` | Passive-source diagnostics |

Response bodies are not intentionally stored by the validator.

## Example output

```text
[*] Using ProjectDiscovery httpx: /usr/local/bin/httpx-pd
[*] Querying Certificate Transparency data.
[*] crt.sh names collected: 390
[*] Running assetfinder.
[*] In-scope scan inputs: 26
[*] Approved application paths: 1
[*] Probing reachable HTTP services.
[*] Reachable base URLs: 23
[*] Running soft-404-aware Git metadata validation.
[*] Confirmed candidates: 0
[*] Probable candidates: 0
[*] Manual review queue: results/example.com-v2-.../manual-review.txt
[*] Markdown summary: results/example.com-v2-.../summary.md
[*] Disclosure draft: results/example.com-v2-.../report-draft.md
```

A zero result means no tested endpoint met the configured evidence rules. It does not prove that every application path, port, hostname, or deployment is safe.

## Why this is more powerful than v1

v1 primarily matched a valid `/.git/HEAD` body. v2 adds:

1. Strict scope policy and repeated scope checks.
2. Separate reachability and evidence stages.
3. Randomized soft-404 comparison.
4. Approved nested application paths.
5. Optional additional metadata signatures.
6. Bounded response reads and no redirect following.
7. Confidence scoring and reason lists.
8. Complete negative, blocked, redirected, and error classifications.
9. Sanitized reporting artifacts.
10. History, resume, automated tests, and CI.

## Limitations

- Passive sources can be stale, incomplete, or unavailable.
- WAFs and authentication controls can hide the real application behavior.
- Non-standard ports are tested only when explicitly allowed.
- Nested paths are tested only when supplied or present in the scope policy.
- Virtual hosts requiring special routing may be missed.
- A valid `HEAD` response does not automatically prove source-code or secret exposure.
- Program policies may classify Git metadata exposure as informative or ineligible.
- Duplicate findings may receive no reward.
- Manual impact analysis remains necessary.

## Manual validation checklist

Before reporting a positive result:

1. Confirm the asset and exact path are in scope.
2. Re-read the program's automation and data-handling rules.
3. Reproduce the smallest possible request manually.
4. Confirm the response is not a soft-404, cache artifact, login page, or generic fallback.
5. Do not dump the repository unless the program explicitly permits it.
6. Do not use any credential or secret.
7. Redact sensitive values from screenshots and attachments.
8. Describe confirmed impact separately from potential impact.
9. Check for duplicates and known exclusions.
10. Submit a concise, reproducible report.

## Testing the project

```bash
bash -n install.sh bin/git-exposure-auditor lib/common.sh scripts/*.sh tests/*.sh
python3 -m py_compile lib/*.py tests/*.py
./tests/run-tests.sh
```

The tests verify:

- Confirmed Git `HEAD` detection.
- Additional safe confirmation signatures.
- Soft-404 rejection.
- HTTP 403 classification.
- Sanitized Markdown and CSV report generation.

## Troubleshooting

The most common Kali issue is running Python HTTPX instead of ProjectDiscovery httpx:

```text
Usage: httpx [OPTIONS] URL
Error: No such option: -l
```

Install and select:

```bash
sudo apt install -y httpx-toolkit
HTTPX_BIN=/usr/bin/httpx-toolkit \
  ./bin/git-exposure-auditor --domain example.com --authorized
```

See [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md).

## Responsible remediation

Application owners should remove version-control metadata from production, deploy only required build artifacts, add web-server deny rules as defense in depth, review logs, inspect repository history for secrets, and rotate potentially exposed credentials.

See [`docs/REMEDIATION.md`](docs/REMEDIATION.md).

## References

- MITRE CWE-527: https://cwe.mitre.org/data/definitions/527.html
- ProjectDiscovery httpx usage: https://docs.projectdiscovery.io/opensource/httpx/usage
- Git repository layout: https://git-scm.com/docs/gitrepository-layout

## License

MIT License. See [`LICENSE`](LICENSE).

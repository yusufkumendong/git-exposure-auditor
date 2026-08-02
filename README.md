# Git Exposure Auditor

**Current release: v1.0.2**

A scope-aware Bash toolkit for **non-destructive detection of publicly exposed Git metadata**. It provides four learning workflows—**Easy, Medium, Hard, and Best Practice**—for validating `/.git/HEAD` exposure without automatically downloading a repository.

> **Authorized use only:** Run this toolkit only against systems you own or are explicitly permitted to test. Always follow the target's scope, rate limits, prohibited-test rules, and disclosure policy.

## Why this project exists

A production web server may accidentally expose its `.git` directory. Git metadata can reveal repository structure, branch names, historical changes, developer information, and—in higher-impact cases—source code or secrets that should never be public.

The specific weakness is **CWE-527: Exposure of Version-Control Repository to an Unauthorized Control Sphere**. A valid Git repository normally has a `HEAD` file that points to a branch such as `refs/heads/main`, or directly contains an object identifier when the repository is in a detached-HEAD state.

This project intentionally stops at a minimal metadata check. It does **not** include repository dumping, credential validation, secret use, authentication bypass, or destructive testing.

## Repository name and GitHub description

**Recommended repository name**

```text
git-exposure-auditor
```

**Recommended description**

```text
A scope-aware Bash toolkit for non-destructive detection of exposed Git metadata (CWE-527), with Easy, Medium, Hard, and Best Practice workflows.
```

**Suggested topics**

```text
cybersecurity bash bug-bounty git-exposure cwe-527 responsible-disclosure httpx assetfinder security-audit
```

## Workflow levels

| Level | Input | Main tools | Purpose | Recommended for |
|---|---|---|---|---|
| Easy | One URL or host | `curl` | Manually validate one target | First-time learners and manual reproduction |
| Medium | A target list | `httpx` | Safely check an authorized list | Small scoped assessments |
| Hard | One root domain | `crt.sh`, `assetfinder`, `httpx` | Passive hostname discovery plus controlled probing | Broader programs that explicitly allow subdomain discovery |
| Best Practice | Domain or target list | All supported tools | Authorization gate, validation, scope control, rate limits, JSONL evidence, optional history | Repeatable and professional research workflows |

Detailed comparisons are available in [`docs/LEVELS.md`](docs/LEVELS.md).

## Project structure

```text
git-exposure-auditor/
├── README.md
├── LICENSE
├── CHANGELOG.md
├── SECURITY.md
├── CONTRIBUTING.md
├── VERSION
├── install.sh
├── scripts/
│   ├── common.sh
│   ├── easy.sh
│   ├── medium.sh
│   ├── hard.sh
│   └── best-practice.sh
├── docs/
│   ├── LEVELS.md
│   ├── REMEDIATION.md
│   ├── REPORT_TEMPLATE.md
│   └── TROUBLESHOOTING.md
├── examples/
│   └── targets.example.txt
└── results/
    └── .gitkeep
```

## Requirements

The toolkit is designed for Linux environments such as Ubuntu, Debian, Kali Linux, and WSL.

Core commands:

- Bash 4+
- `curl`
- `jq`
- Go
- ProjectDiscovery `httpx`
- `assetfinder`
- Optional: `anew`

### Kali Linux installation

Kali packages ProjectDiscovery httpx under the distinct command name `httpx-toolkit`, which avoids a collision with the unrelated Python HTTPX CLI:

```bash
sudo apt update
sudo apt install -y curl jq golang-go unzip git httpx-toolkit
httpx-toolkit -version
```

Install the remaining Go tools:

```bash
chmod +x install.sh
./install.sh
```

Version 1.0.2 detects `httpx-toolkit` automatically. A manual `httpx-pd` symlink is no longer required.

### Generic Go installation

```bash
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
go install -v github.com/tomnomnom/assetfinder@latest
go install -v github.com/tomnomnom/anew@latest
export PATH="$(go env GOPATH)/bin:$PATH"
hash -r
```

Verify the commands:

```bash
"$(go env GOPATH)/bin/httpx" -version
assetfinder --help
anew -h
```

When more than one command named `httpx` is installed, select ProjectDiscovery explicitly:

```bash
HTTPX_BIN=/usr/bin/httpx-toolkit ./scripts/hard.sh example.com
```

See [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) for command-collision and `crt.sh` recovery guidance.

## Dependency resolution

The batch workflows validate candidate binaries before use and print the selected ProjectDiscovery executable. The lookup order is `HTTPX_BIN`, `httpx-pd`, `httpx-toolkit`, common Go binary directories, and finally `httpx` only when its flags match ProjectDiscovery.

A Python HTTPX error such as `Usage: httpx [OPTIONS] URL` with `No such option: -l` indicates the wrong CLI. Follow [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md).

## Usage

### Easy — one target with curl

```bash
./scripts/easy.sh https://example.com
```

What it does:

1. Requests `https://example.com/.git/HEAD`.
2. Does not follow redirects.
3. Requires HTTP `200`.
4. Checks for a symbolic branch reference or a 40/64-character hexadecimal object identifier.

**Advantages**

- Minimal dependencies and traffic.
- Easy to understand and reproduce.
- Good for validating a single report candidate.

**Disadvantages**

- One target at a time.
- Does not discover subdomains.
- A negative result does not prove that no Git metadata is exposed elsewhere.

### Medium — authorized target list

Create a file containing one hostname or URL per line:

```text
example.com
https://app.example.com
http://staging.example.com:8080
```

Run:

```bash
./scripts/medium.sh examples/targets.example.txt results/medium.txt
```

**Advantages**

- Efficient for a small, known scope.
- Uses response-body matching instead of status code alone.
- Applies conservative concurrency and rate limits.

**Disadvantages**

- Accuracy depends on the quality of the input list.
- Does not perform passive discovery.
- Only checks the exact `/.git/HEAD` path.

### Hard — passive discovery and controlled probing

```bash
./scripts/hard.sh example.com
```

Optional conservative overrides:

```bash
THREADS=10 RATE_LIMIT=5 PORTS='http:80,https:443' \
  ./scripts/hard.sh example.com results/example-hard
```

Select Kali's ProjectDiscovery binary explicitly when needed:

```bash
HTTPX_BIN=/usr/bin/httpx-toolkit ./scripts/hard.sh example.com
```

Increase the Certificate Transparency timeout for unusually large responses:

```bash
CRT_MAX_TIME=120 CRT_RETRIES=1 ./scripts/hard.sh example.com
```

The script downloads Certificate Transparency JSON before parsing it. A timeout, HTTP 502, or malformed response is recorded in `crtsh-errors.log`, and the workflow continues with the root domain and `assetfinder` output.

**Advantages**

- Combines Certificate Transparency data and `assetfinder`.
- Normalizes wildcard names and removes duplicates.
- Filters discovered names to the requested root domain.
- Produces a reusable subdomain inventory.

**Disadvantages**

- Passive sources can be incomplete, stale, or unavailable.
- `assetfinder` already uses several public sources, including Certificate Transparency, so some source overlap is expected.
- Broader discovery may be prohibited by some programs.
- More requests are generated than in Easy or Medium mode.

### Best Practice — professional workflow

Domain mode:

```bash
./scripts/best-practice.sh \
  --domain example.com \
  --authorized
```

Target-list mode:

```bash
./scripts/best-practice.sh \
  --targets authorized-targets.txt \
  --authorized \
  --threads 10 \
  --rate-limit 5
```

Track only newly observed candidate URLs:

```bash
./scripts/best-practice.sh \
  --domain example.com \
  --authorized \
  --history results/history.txt
```

**Best Practice controls**

- Refuses to run without the explicit `--authorized` acknowledgement.
- Accepts exactly one input mode.
- Validates root-domain syntax.
- Restricts domain-mode discoveries to the selected root domain.
- Caps user-configurable concurrency and request rate at 50.
- Preserves target-file port choices unless explicit port expansion is requested.
- Uses one minimal path: `/.git/HEAD`.
- Does not follow redirects.
- Does not store response bodies.
- Produces JSONL metadata and a clean candidate URL list.
- Supports new-only result tracking through `anew`.

## Detection logic

A response is treated as a **high-confidence candidate**, not a final impact statement, when all of the following are true:

1. `/.git/HEAD` returns HTTP `200`.
2. The body contains a Git symbolic reference such as:

   ```text
   ref: refs/heads/main
   ```

   or consists of a valid-looking 40- or 64-character hexadecimal object identifier.

This is stronger than filtering on `200`, `301`, or `302` alone. A custom error page can return `200`, while a redirect merely indicates another location and does not prove exposure.

## Important limitations

- The scripts check only `/.git/HEAD` at the supplied base path.
- Nested repositories such as `/app/.git/HEAD` are not discovered automatically.
- Hard mode and Best Practice domain mode default to HTTP 80 and HTTPS 443. Best Practice target-list mode does not expand ports unless requested.
- WAFs, authentication, network errors, HSTS behavior, or custom routing can cause false negatives.
- A readable `HEAD` file does not prove that the full repository can be reconstructed.
- Passive hostname sources are not authoritative asset inventories.
- A high-confidence candidate still requires scope verification and minimal manual reproduction.

## Responsible validation workflow

1. Read the program policy before scanning.
2. Build a clean in-scope target list.
3. Start with the lowest request rate that is practical.
4. Stop after confirming the minimum evidence.
5. Never use discovered tokens, passwords, or keys.
6. Never access unrelated accounts, data, or systems.
7. Do not dump a repository unless the owner explicitly permits it and the additional access is necessary.
8. Redact secrets and personal information from screenshots and reports.
9. Report the observed behavior without overstating impact.

## Reporting

Use the provided template:

[`docs/REPORT_TEMPLATE.md`](docs/REPORT_TEMPLATE.md)

A careful report should distinguish between:

- **Confirmed observation:** `/.git/HEAD` is publicly readable.
- **Potential impact:** additional Git metadata may expose source history or secrets.
- **Unverified claim:** the complete repository can be reconstructed.

Do not claim full source-code disclosure unless that impact was safely demonstrated under explicit authorization.

## Remediation

The primary fix is to remove Git metadata from the production web root and deploy only the required build artifacts. Blocking `/.git` at the web-server layer is useful defense in depth, but it should not replace correct deployment hygiene.

See [`docs/REMEDIATION.md`](docs/REMEDIATION.md).

## References

- [MITRE CWE-527](https://cwe.mitre.org/data/definitions/527.html)
- [Git repository layout documentation](https://git-scm.com/docs/gitrepository-layout)
- [ProjectDiscovery httpx](https://github.com/projectdiscovery/httpx)
- [ProjectDiscovery httpx usage](https://docs.projectdiscovery.io/opensource/httpx/usage)
- [tomnomnom/assetfinder](https://github.com/tomnomnom/assetfinder)
- [tomnomnom/anew](https://github.com/tomnomnom/anew)

## License

Released under the [MIT License](LICENSE).

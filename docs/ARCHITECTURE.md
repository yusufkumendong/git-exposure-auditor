# Architecture

## Design objective

Git Exposure Auditor v2 is designed around one principle:

> Maximum confidence with minimum requests and minimum retained data.

It is an evidence-prioritization tool, not a repository-dumping framework and not an automatic bounty guarantee.

## Pipeline

### 1. Authorized input

The operator supplies either:

- One root domain, or
- One prepared file of authorized hosts and URLs.

The main CLI refuses to run without `--authorized`.

### 2. Scope policy

A JSON policy controls:

- Included exact hosts and wildcard subdomains.
- Excluded hosts.
- Allowed protocol/port combinations.
- Approved application base paths.
- Maximum threads.
- Maximum request rate.
- Maximum validation tasks.
- Maximum response bytes read in memory.

Exclusions always override inclusions. Every validator request performs a fresh host-in-scope check.

### 3. Discovery and normalization

Domain mode can collect names from:

- The selected root domain.
- Certificate Transparency through `crt.sh`.
- `assetfinder`, when installed.

Names are lowercased, wildcard prefixes are removed, invalid hosts are discarded, duplicates are removed, and the final list is filtered through the scope policy.

Target-list mode normalizes each explicit host or HTTP URL and removes query strings and fragments. URL credentials are rejected.

### 4. Reachability inventory

ProjectDiscovery `httpx` identifies reachable HTTP services and records metadata such as:

- URL.
- Status code.
- Content type and length.
- Redirect location.
- Body hash.
- Server, IP, CNAME, CDN, and probe status when available.

This stage does not decide whether Git metadata is exposed. It creates the base URL inventory for the evidence validator.

### 5. Randomized missing-path baseline

For every reachable base URL and approved application path, the validator requests a randomized path such as:

```text
/.gea-not-found-<task-id>
```

The response is compared with the result from:

```text
/.git/HEAD
```

Comparison includes:

- HTTP status.
- SHA-256 body hash.
- Normalized text similarity.
- Content type.
- Response length tolerance.

This reduces false positives caused by catch-all pages and custom HTTP 200 error pages.

### 6. Git HEAD signature validation

A high-confidence signature is either:

```text
ref: refs/heads/<branch>
```

or an exact 40/64-character hexadecimal object identifier representing a detached HEAD.

The tool does not treat HTTP 200 alone as evidence.

### 7. Optional safe confirmation

When `--confirm` is enabled and the HEAD result is already confirmed or probable, the tool checks a bounded allowlist:

```text
/.git/config
/.git/packed-refs
/.git/index
/.git/logs/HEAD
```

It checks only metadata signatures:

- `[core]` and `repositoryformatversion` for Git config.
- Packed-ref headers or reference lines.
- `DIRC` magic for the Git index.
- Reflog record structure for logs/HEAD.

The body remains in memory only. The output stores status, content type, length, hash, timing, and signature result. Confirmation stops after two additional signatures.

### 8. Classification and scoring

The validator emits one result per URL/path task with:

- Classification.
- Score.
- Confidence.
- Evidence level.
- Reasons.
- HEAD response metadata.
- Missing-path baseline metadata.
- Optional confirmation metadata.

The score is a review-priority signal and is not a CVSS score.

### 9. Sanitized reporting

The reporting layer generates:

- JSONL findings.
- CSV findings.
- Confirmed and probable URL queues.
- Aggregate JSON summary.
- Markdown summary.
- A responsible-disclosure draft.
- Dependency and command metadata.

The tool does not intentionally store response bodies, cookies, authorization headers, credentials, or secrets.

## Trust boundaries

The operator remains responsible for:

- Confirming written authorization.
- Interpreting program scope.
- Choosing allowed paths and ports.
- Reviewing third-party infrastructure.
- Performing manual impact analysis.
- Redacting sensitive evidence.
- Deciding whether a report is valid and eligible.

## Failure model

The tool is designed to continue safely when:

- `crt.sh` times out or returns malformed data.
- `assetfinder` is missing or fails.
- Some hosts are unreachable.
- A WAF returns 401/403.
- Endpoints redirect.
- TLS or network errors occur.

These outcomes are recorded rather than silently treated as safe.

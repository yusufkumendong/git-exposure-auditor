# Changelog

All notable changes to this project are documented here. The project follows semantic versioning.

## [Unreleased]

## [2.0.0] - 2026-08-02

### Added

- A unified `bin/git-exposure-auditor` command.
- Strict JSON scope policies with include, exclude, port, concurrency, task, response-size, and application-path controls.
- Passive domain discovery through Certificate Transparency and optional `assetfinder`.
- Reachability inventory through ProjectDiscovery `httpx`.
- Randomized missing-path baselines for soft-404 detection.
- High-confidence Git `HEAD` validation using symbolic refs and detached object identifiers.
- Optional safe confirmation for `.git/config`, `.git/packed-refs`, `.git/index`, and `.git/logs/HEAD`.
- Response-size caps, no-redirect behavior, and no response-body storage.
- Confidence scoring and classifications: `CONFIRMED`, `PROBABLE`, `SOFT_404`, `BLOCKED`, `REDIRECTED`, `NOT_EXPOSED`, and `ERROR`.
- Sanitized JSONL, CSV, Markdown, and disclosure-draft outputs.
- Built-in history tracking and a manual-review queue.
- Resume support using a prior `findings.jsonl` file.
- Local mock-server tests and GitHub Actions CI.
- Compatibility wrappers for Easy, Medium, Hard, and Best Practice workflows.

### Changed

- Hard mode now requires an explicit `--authorized` acknowledgement.
- The main workflow separates reachability probing from evidence validation.
- Target-list mode preserves explicit input behavior unless ports are intentionally supplied.
- A zero-result run now includes complete coverage and classification artifacts.

### Security boundaries

- No repository dumping or reconstruction.
- No Git object enumeration.
- No secret extraction or credential validation.
- No authentication bypass, WAF evasion, proxy rotation, or denial-of-service behavior.
- No automatic submission to bug-bounty platforms.

## [1.0.2] - 2026-08-02

- Added Kali `httpx-toolkit` detection.
- Fixed Certificate Transparency timeout and malformed-JSON handling.
- Added runtime dependency diagnostics and troubleshooting documentation.

## [1.0.0] - 2026-08-02

- Initial Easy, Medium, Hard, and Best Practice Bash workflows.

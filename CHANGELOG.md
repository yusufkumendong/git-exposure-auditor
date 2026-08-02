# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project intends to use semantic versioning.

## [Unreleased]

## [1.0.2] - 2026-08-02

### Fixed

- Detects Kali Linux's `httpx-toolkit` command directly without requiring a symlink.
- Ensures all batch workflows execute the resolved ProjectDiscovery binary through `HTTPX_BIN`.
- Downloads Certificate Transparency JSON before parsing it, preventing truncated responses from being streamed into `jq`.
- Writes `crt.sh` diagnostics to `crtsh-errors.log` and continues with other passive sources.
- Adds configurable `CRT_MAX_TIME` and `CRT_RETRIES` values.
- Validates Hard-mode concurrency and rate-limit overrides.

### Added

- Prints the selected ProjectDiscovery httpx binary at runtime.
- Adds `docs/TROUBLESHOOTING.md` with Kali, Python HTTPX collision, and `crt.sh` recovery guidance.
- Adds a repository `VERSION` file.

### Changed

- The installer reuses an existing valid ProjectDiscovery httpx installation before installing another copy with Go.
- Certificate Transparency requests now use a 90-second default per-attempt timeout and one retry.

## [1.0.1] - 2026-08-02

### Fixed

- Detects and rejects the unrelated Python HTTPX CLI.
- Resolves ProjectDiscovery httpx from `HTTPX_BIN`, `httpx-pd`, or the Go binary directory.
- Prepends the Go binary directory to `PATH` in installation guidance.
- Adds Kali Zsh installation instructions.
- Normalizes the Hard workflow domain before constructing the default output directory.
- Initializes output files before counting results.

## [1.0.0] - 2026-08-02

### Added

- Easy single-target validation with `curl`.
- Medium authorized-list scanning with `httpx`.
- Hard passive discovery and controlled probing workflow.
- Best Practice workflow with authorization acknowledgement, bounded rate limits, JSONL evidence, and optional `anew` history.
- Responsible disclosure report template.
- Defensive remediation guidance.
- Contribution and security policies.

# GitHub Release: v2.0.0

## Release title

```text
Git Exposure Auditor v2.0.0 — High-Confidence Validation and Reporting
```

## Release description

```markdown
## Git Exposure Auditor v2.0.0

Version 2.0.0 transforms the project from a Git HEAD detector into a scope-aware, soft-404-resistant, evidence-scoring, and report-generating audit workflow.

### Major features

- Unified `git-exposure-auditor` CLI.
- Strict JSON scope policies with include and exclude rules.
- Passive domain discovery through `crt.sh` and optional `assetfinder`.
- ProjectDiscovery httpx reachability inventory.
- Randomized missing-path baselines for soft-404 detection.
- High-confidence symbolic-ref and detached-HEAD validation.
- Optional bounded confirmation of Git config, packed refs, index, and reflog signatures.
- Response-size caps, no redirects, and no response-body storage.
- Confidence scoring and complete result classifications.
- Sanitized JSONL, CSV, Markdown, and disclosure-draft outputs.
- Built-in history tracking and resume support.
- Easy, Medium, Hard, and Best Practice compatibility wrappers.
- Automated local tests and GitHub Actions CI.

### Safety boundaries

- No repository dumping or reconstruction.
- No Git object enumeration.
- No source-code or secret extraction.
- No credential validation.
- No authentication bypass or WAF evasion.
- No denial-of-service behavior.
- No automatic bug-bounty submission.

### Important note

This tool automates discovery, false-positive reduction, prioritization, evidence organization, and report drafting. It cannot guarantee that a program will accept a report or award a bounty. Manual scope and impact validation remain required.

Only use this toolkit against systems you own or are explicitly authorized to test.
```

## Suggested GitHub description

```text
A scope-aware, non-destructive Git metadata exposure auditor with passive discovery, soft-404 detection, confidence scoring, safe confirmation, and report generation.
```

## Suggested topics

```text
cybersecurity
bug-bounty
bash
python
httpx
git-exposure
cwe-527
responsible-disclosure
security-audit
infosec
```

## Suggested release assets

```text
git-exposure-auditor-v2.0.0.zip
git-exposure-auditor-v2.0.0-SHA256SUMS.txt
```

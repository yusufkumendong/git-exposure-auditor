# Migration from v1 to v2

## Major changes

v2 replaces direct Git-path matching as the main workflow with a staged architecture:

1. Scope policy.
2. Passive discovery or exact inputs.
3. Reachability inventory.
4. Soft-404-aware evidence validation.
5. Optional safe confirmation.
6. Sanitized reporting.

## Command changes

### v1 Hard

```bash
./scripts/hard.sh example.com
```

### v2 Hard

```bash
./scripts/hard.sh example.com --authorized
```

The authorization acknowledgement is now mandatory.

### v1 Best Practice

```bash
./scripts/best-practice.sh --domain example.com --authorized
```

### v2 Best Practice

The same style remains valid:

```bash
./scripts/best-practice.sh --domain example.com --authorized
```

Optional v2 controls:

```bash
./scripts/best-practice.sh \
  --domain example.com \
  --scope config/scope.local.json \
  --paths approved-paths.txt \
  --confirm \
  --history results/history.txt \
  --authorized
```

## Recommended upgrade procedure

```bash
cd /home/i7k
mv git-exposure-auditor git-exposure-auditor-v1-backup
unzip git-exposure-auditor-v2.0.0.zip
cd git-exposure-auditor
chmod +x install.sh bin/git-exposure-auditor scripts/*.sh lib/*.py tests/*.sh tests/*.py
./install.sh --check
./tests/run-tests.sh
```

Preserve private scope files and history files manually. Do not copy old runtime results into the repository root unless needed for local review.

## Output changes

v1 candidate files become v2 structured artifacts:

| v1 | v2 |
|---|---|
| `candidates.txt` | `confirmed.txt`, `probable.txt`, `manual-review.txt` |
| `candidates.jsonl` | `findings.jsonl` |
| Basic counts | `scan-summary.json` and `summary.md` |
| Manual report writing | Generated `report-draft.md` |

## Compatibility

The Easy, Medium, Hard, and Best Practice wrapper names are preserved. The main implementation is now `bin/git-exposure-auditor`.

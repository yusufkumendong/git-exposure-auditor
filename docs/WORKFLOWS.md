# Workflow Levels

The level names describe complexity and automation. They do not grant permission to increase traffic or test assets outside written scope.

## Comparison

| Property | Easy | Medium | Hard | Best Practice |
|---|---:|---:|---:|---:|
| One explicit target | Yes | Yes | No | Yes |
| Target list | No | Yes | Generated | Yes |
| Passive discovery | No | No | Yes | Optional |
| JSON scope policy | Auto-derived | Auto-derived | Auto-derived | Recommended |
| Soft-404 baseline | Yes | Yes | Yes | Yes |
| Confidence scoring | Yes | Yes | Yes | Yes |
| Safe confirmation | No by default | No by default | Optional environment flag | Explicit `--confirm` |
| Nested application paths | Root only | Root only | Root only by default | Approved path file or scope policy |
| Structured evidence | Yes | Yes | Yes | Yes |
| Markdown report draft | Yes | Yes | Yes | Yes |
| History and resume | Main CLI only | Main CLI only | Main CLI only | Yes |

## Easy

```bash
./scripts/easy.sh https://example.com --authorized
```

### Advantages

- Lowest setup and traffic.
- One worker and one request per second.
- Good for manual reproduction and learning.
- Still benefits from the v2 soft-404 and reporting engine.

### Disadvantages

- No passive discovery.
- No additional application paths.
- No safe confirmation by default.
- A negative result applies only to the exact tested service and path.

## Medium

```bash
./scripts/medium.sh examples/targets.example.txt --authorized
```

### Advantages

- Efficient for an exact program-supplied asset list.
- Preserves explicit URLs and ports unless expansion is requested.
- Produces a complete manual-review queue and report artifacts.

### Disadvantages

- Input quality determines coverage.
- The auto-derived scope contains only hosts from the file.
- Passive discovery and additional application paths are not enabled.

## Hard

```bash
./scripts/hard.sh example.com --authorized
```

### Advantages

- Combines root-domain, Certificate Transparency, and optional `assetfinder` data.
- Performs normalization and root-domain scope filtering.
- Produces a reusable host and reachability inventory.
- Can enable safe confirmation through `SAFE_CONFIRM=1`.

### Disadvantages

- Passive data can be incomplete or stale.
- Broader enumeration creates more requests and review work.
- Some programs prohibit testing unspecified subdomains.
- Root-only path coverage remains the default.

## Best Practice

```bash
./scripts/best-practice.sh \
  --domain example.com \
  --scope config/scope.local.json \
  --paths approved-paths.txt \
  --confirm \
  --history results/history.txt \
  --authorized
```

### Advantages

- Strongest scope controls.
- Explicit include and exclude lists.
- Operator-defined port, path, rate, task, and response-size limits.
- Safe additional metadata validation.
- Resume and new-finding history.
- Complete evidence and disclosure-draft outputs.

### Disadvantages

- Requires more setup and policy review.
- More code and dependencies need maintenance.
- Safe confirmation creates additional requests.
- Automated confidence still requires human validation.

## Recommended selection

- Use **Easy** for one manual candidate.
- Use **Medium** for an exact authorized asset list.
- Use **Hard** when passive discovery and subdomain probing are explicitly allowed.
- Use **Best Practice** for repeatable research with documented scope and reporting.

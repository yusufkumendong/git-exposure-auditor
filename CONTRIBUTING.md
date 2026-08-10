# Contributing

## Development rules

- Keep requests non-destructive, bounded, and scope-aware.
- Do not add repository dumping, secret extraction, credential testing, automatic auth/WAF bypass, brute force, DoS, or exploit chaining.
- Every classification or expansion change must include a unit or integration fixture.
- Preserve host-level aggregation and compatibility report names.
- Persisted evidence must be redacted.
- Explicit scope must never be widened silently by target input.
- Core classification must remain deterministic.

## Local checks

```bash
./tests/run_all.sh
```

Optional:

```bash
shellcheck -S error -x bin/gea scripts/*.sh tests/*.sh install.sh
```

## Versioning

Use Semantic Versioning. Release Candidate tags use `vX.Y.Z-rcN`. Do not use an LTS label until the documented quality gate has passed.

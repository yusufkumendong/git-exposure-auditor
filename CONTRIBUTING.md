# Contributing

## Development rules

- Keep requests non-destructive and bounded.
- Do not add dumping, secret extraction, authentication/WAF bypass, brute force, or exploit chaining.
- New classification logic must include a fixture or integration assertion.
- Do not persist raw response bodies.
- Preserve direct input and scope validation behavior.

## Local checks

```bash
shellcheck -S error -x bin/gea lib/*.sh scripts/*.sh tests/*.sh install.sh
./tests/syntax.sh
./tests/input.sh
./tests/integration.sh
```

## Versioning

Use Semantic Versioning. Release Candidate tags use `vX.Y.Z-rcN`. Do not use an LTS label unless `docs/SUPPORT.md` explicitly defines the support window and the compatibility quality gate has passed.

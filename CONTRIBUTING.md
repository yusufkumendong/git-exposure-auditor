# Contributing

Contributions that improve safety, correctness, portability, documentation, evidence quality, and false-positive handling are welcome.

## Development principles

- Keep default rates conservative and enforce hard upper bounds.
- Preserve strict scope validation.
- Minimize requests and collected data.
- Do not add repository dumping, object reconstruction, secret use, credential testing, WAF evasion, or destructive behavior.
- Prefer official documentation for third-party command behavior.
- Treat a finding as a review candidate, not a guaranteed bounty.
- Keep output sanitized and reproducible.

## Before opening a pull request

```bash
bash -n install.sh bin/git-exposure-auditor lib/common.sh scripts/*.sh tests/*.sh
python3 -m py_compile lib/*.py tests/*.py
./tests/run-tests.sh
```

When available:

```bash
shellcheck install.sh bin/git-exposure-auditor lib/common.sh scripts/*.sh tests/*.sh
```

Update the README and changelog when behavior, dependencies, request volume, scope handling, or output formats change.

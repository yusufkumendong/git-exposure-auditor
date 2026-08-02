## Summary

Describe the change and the problem it solves.

## Safety impact

- [ ] Scope enforcement is unchanged or stronger.
- [ ] Default request volume is unchanged or lower.
- [ ] No repository dumping, object reconstruction, secret use, credential testing, WAF evasion, or destructive behavior was added.
- [ ] Output does not retain sensitive response bodies.

## Testing

- [ ] `bash -n install.sh bin/git-exposure-auditor lib/common.sh scripts/*.sh tests/*.sh`
- [ ] `python3 -m py_compile lib/*.py tests/*.py`
- [ ] `./tests/run-tests.sh`
- [ ] `shellcheck` when available

## Documentation

- [ ] README updated when behavior changed.
- [ ] CHANGELOG updated.

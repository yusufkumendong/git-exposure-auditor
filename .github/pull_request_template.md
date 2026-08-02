## Summary

Describe the change and why it is needed.

## Safety impact

- [ ] Default request volume does not increase unexpectedly.
- [ ] Scope handling remains explicit.
- [ ] No repository dumping, credential use, destructive behavior, or access-control bypass was added.
- [ ] Test data contains no real third-party secrets or unauthorized targets.

## Validation

- [ ] `bash -n install.sh scripts/*.sh`
- [ ] `shellcheck install.sh scripts/*.sh` when available
- [ ] Documentation was updated when behavior or flags changed

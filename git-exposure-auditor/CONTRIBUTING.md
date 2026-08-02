# Contributing

Contributions that improve safety, correctness, portability, documentation, and false-positive handling are welcome.

## Development principles

- Keep default request rates conservative.
- Do not add destructive behavior.
- Do not add automatic repository dumping or secret use.
- Preserve explicit authorization messaging.
- Prefer official documentation for third-party CLI behavior.
- Keep scripts compatible with Bash and common Linux environments.
- Use clear exit codes and actionable errors.

## Before opening a pull request

1. Run syntax checks:

   ```bash
   bash -n install.sh scripts/*.sh
   ```

2. Run `shellcheck` when available:

   ```bash
   shellcheck install.sh scripts/*.sh
   ```

3. Update the README when behavior or flags change.
4. Do not include real target data in test fixtures, logs, screenshots, or commits.
5. Explain any effect on request volume or scope handling.

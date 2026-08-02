# Security Policy

## Authorized use

Git Exposure Auditor is designed only for systems you own or are explicitly authorized to assess. The operator is responsible for reading and following the exact asset scope, rate limits, prohibited-testing rules, data-handling rules, and disclosure policy of every program.

An `--authorized` flag is an operator acknowledgement; it cannot prove permission.

## Intentional safety boundaries

The project does not include:

- Repository dumping or reconstruction.
- Git object enumeration or source-code extraction.
- Secret harvesting or credential validation.
- Authentication or authorization bypass.
- WAF evasion, proxy rotation, or identity hiding.
- Denial-of-service testing or unlimited concurrency.
- Automatic report submission.

Safe confirmation reads only a bounded prefix of a small allowlist of Git metadata files, checks signatures in memory, and records metadata rather than response bodies.

## Reporting a vulnerability in this project

Do not publish a working exploit for a vulnerability in the toolkit before the maintainer has had a reasonable opportunity to investigate and release a fix.

Include:

- Affected version or commit.
- Operating system and dependency versions.
- Minimal reproduction steps.
- Expected and actual behavior.
- Security impact.
- A suggested fix when available.

Never include real third-party credentials, secrets, personal data, or private program scope in a public issue.

# Responsible Disclosure Report Template

## Title

Publicly accessible Git metadata at `[URL]`

## Weakness

- **CWE:** CWE-527 — Exposure of Version-Control Repository to an Unauthorized Control Sphere
- **Category:** Security misconfiguration / sensitive metadata exposure

## Asset

```text
https://[HOST]
```

## Summary

The web server exposes a valid Git `HEAD` metadata signature without authentication. I compared the result with a randomized missing path to reduce the possibility of a custom HTTP 200 error page.

I stopped after the minimum non-destructive validation. I did not reconstruct the repository, enumerate Git objects, use credentials, bypass authentication, or access unrelated data.

## Steps to reproduce

1. Send:

   ```http
   GET /.git/HEAD HTTP/1.1
   Host: [HOST]
   Connection: close
   ```

2. Observe a response such as:

   ```http
   HTTP/1.1 200 OK
   Content-Type: text/plain

   ref: refs/heads/main
   ```

3. Request a randomized nonexistent path and confirm that it produces a different response profile.

## Minimal command

```bash
curl --silent --show-error --include --max-time 10 \
  'https://[HOST]/.git/HEAD'
```

## Automated evidence

- Classification: `[CONFIRMED/PROBABLE]`
- Confidence score: `[SCORE]/100`
- HEAD signature: `[SIGNATURE]`
- HTTP status: `[STATUS]`
- Content type: `[CONTENT TYPE]`
- Response length: `[LENGTH]`
- SHA-256: `[HASH]`
- Soft-404 similarity: `[VALUE]`
- Additional metadata signatures: `[REDACTED SUMMARY]`

## Confirmed impact

- Git metadata is publicly readable without authentication.

## Potential impact

Additional repository metadata may expose implementation details, file paths, commit history, developer information, source code, or secrets if more repository data is accessible. Do not state these as confirmed unless safely demonstrated and permitted by program policy.

## Research boundaries

- No repository dump or reconstruction.
- No Git object enumeration.
- No credential or secret use.
- No authentication bypass.
- No destructive testing.
- No third-party redirect following.
- No response body retained by the automated tool.

## Recommended remediation

1. Remove `.git` and all version-control metadata from the production web root.
2. Deploy only required build artifacts.
3. Add web-server deny rules for version-control paths as defense in depth.
4. Review archives, backups, alternate paths, and other deployments.
5. Inspect repository history for secrets and rotate potentially exposed credentials.
6. Review access logs for requests to `.git` paths.

## Evidence attachments

- Sanitized request and response screenshot.
- `summary.md` excerpt.
- Relevant `findings.csv` row.
- Timestamp and asset scope evidence.

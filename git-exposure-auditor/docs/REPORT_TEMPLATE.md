# Responsible Disclosure Report Template

## Title

Publicly accessible Git metadata at `/.git/HEAD` on `[HOST]`

## Weakness

- **CWE:** CWE-527 — Exposure of Version-Control Repository to an Unauthorized Control Sphere
- **Category:** Sensitive metadata exposure / security misconfiguration

## Asset

```text
https://[HOST]
```

## Summary

The web server exposes the Git `HEAD` metadata file without authentication. An unauthenticated request to `/.git/HEAD` returns a valid Git reference. This confirms that at least part of the repository metadata is publicly accessible.

I stopped after the minimum non-destructive validation and did not download repository objects, inspect source history, use credentials, or access unrelated data.

## Steps to reproduce

1. Send the following request:

   ```http
   GET /.git/HEAD HTTP/1.1
   Host: [HOST]
   Connection: close
   ```

2. Observe the response:

   ```http
   HTTP/1.1 200 OK
   Content-Type: [CONTENT-TYPE]

   ref: refs/heads/[BRANCH]
   ```

3. Confirm that the response is not a custom error page and that the hostname is in scope.

## Minimal command

```bash
curl --silent --show-error --include --max-time 10 \
  https://[HOST]/.git/HEAD
```

## Observed impact

Confirmed:

- Git branch metadata is publicly readable without authentication.

Potential, not automatically assumed:

- Additional repository metadata may reveal file paths, commit history, developer information, source code, or secrets if other Git files are also exposed.

## Security impact statement

Exposed version-control metadata can provide attackers with internal implementation details that reduce the effort required to discover additional vulnerabilities. The final severity depends on whether other repository objects are accessible and whether sensitive data exists in the repository history.

## Research boundaries

- No repository dump was performed.
- No credentials, tokens, or API keys were used.
- No authentication controls were bypassed.
- No destructive or availability-impacting test was performed.

## Recommended remediation

1. Remove `.git` and all version-control metadata from the production web root.
2. Deploy only required build artifacts.
3. Block requests to hidden version-control paths as defense in depth.
4. Review deployment archives and backups for similar exposure.
5. Inspect repository history for secrets and rotate any potentially exposed credential.
6. Review access logs for requests to `/.git/` paths.

## Evidence

- Timestamp: `[UTC TIMESTAMP]`
- Request URL: `[REDACTED OR FULL IN-SCOPE URL]`
- HTTP status: `[STATUS]`
- Response signature: `[REDACTED MINIMAL SIGNATURE]`
- Screenshot or request/response attachment: `[ATTACHMENT]`

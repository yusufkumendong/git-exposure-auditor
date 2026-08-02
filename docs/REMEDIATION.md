# Defensive Remediation

## Primary fix

Do not deploy a Git working directory to a publicly served production path. Build and deploy only the files required by the application.

## Immediate containment

1. Remove `.git` and other version-control metadata from the web root.
2. Add web-server rules denying access to hidden version-control directories.
3. Purge affected CDN and reverse-proxy caches.
4. Review access logs for historical requests to `.git` paths.
5. Identify every related hostname, port, backup, archive, and deployment path.

## Secret response

If repository history may have contained secrets:

1. Treat exposed values as compromised.
2. Rotate API keys, tokens, passwords, certificates, and deployment credentials.
3. Revoke old credentials instead of only deleting them from the latest commit.
4. Review audit logs for unauthorized use.
5. Remove secrets from history using an approved repository-cleaning process.

## Deployment controls

- Use CI/CD to create immutable build artifacts.
- Exclude `.git`, `.svn`, `.hg`, editor files, backups, and local environment files.
- Add release checks that fail when version-control metadata is present.
- Use container multi-stage builds and copy only production artifacts.
- Separate source checkout locations from public document roots.
- Test production and staging deployments after every pipeline change.

## Defense-in-depth examples

### Nginx

```nginx
location ~ /\.git(?:/|$) {
    deny all;
    return 404;
}
```

### Apache

```apache
RedirectMatch 404 /\.git(?:/|$)
```

These rules are secondary controls. The preferred fix is to remove repository metadata from the deployment entirely.

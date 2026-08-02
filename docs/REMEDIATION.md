# Remediation Guidance

## Primary remediation

The safest solution is to ensure that version-control metadata never reaches the production web root.

1. Build the application in a controlled CI/CD environment.
2. Publish only the required runtime or static artifacts.
3. Exclude `.git`, `.svn`, `.hg`, editor files, backups, and temporary archives from deployment packages.
4. Verify the final artifact before release.

A `.gitignore` file does not protect a deployed `.git` directory. `.gitignore` controls which working-tree files Git tracks; it does not make the repository metadata inaccessible to a web server.

## Defense in depth

Web-server rules can block accidental exposure, but they should supplement—not replace—clean deployment artifacts.

### Nginx example

```nginx
location ~ (^|/)\.git(?:/|$) {
    return 404;
}
```

Reload only after validating the configuration:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### Apache HTTP Server example

Place an appropriate rule in the virtual host configuration:

```apache
<DirectoryMatch "(^|/)\.git/">
    Require all denied
</DirectoryMatch>
```

Validate and reload according to the operating system and deployment process.

### IIS guidance

Use Request Filtering or URL Rewrite to deny `.git` path segments, and remove the directory from the application root. Test the rule in a staging environment before production rollout.

## Incident response after exposure

1. Remove the exposed metadata immediately.
2. Search access logs for requests containing `/.git/`.
3. Review current and historical commits for secrets.
4. Rotate exposed or potentially exposed passwords, API keys, certificates, and tokens.
5. Revoke obsolete credentials rather than only deleting them from the latest commit.
6. Review related systems for unauthorized use.
7. Add automated deployment checks to prevent recurrence.

## Verification

After remediation, verify that representative paths no longer return repository data:

```bash
curl --include --max-time 10 https://example.com/.git/HEAD
curl --include --max-time 10 https://example.com/.git/config
```

A generic `404` is preferable to revealing whether a hidden repository path exists. Also confirm that the `.git` directory is absent from the deployed filesystem or container image.

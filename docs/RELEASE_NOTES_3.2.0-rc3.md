# Git Exposure Auditor v3.2.0-rc3

## CI compatibility hotfix

This release candidate fixes the Rocky Linux 9 container CI job. Rocky 9 container images may include `curl-minimal`; installing the full `curl` RPM in the same transaction can produce a package conflict. The workflow now installs the remaining runtime dependencies first and keeps `curl-minimal` when it already supplies the `curl` command.

No scanner detection logic, scope logic, or authorization behavior is changed by this hotfix.

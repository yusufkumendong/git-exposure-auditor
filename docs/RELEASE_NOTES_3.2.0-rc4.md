# Git Exposure Auditor v3.2.0-rc4

Installer/runtime hotfix.

- Fixes `/usr/local/bin/gea` resolving its root as `/usr/local` when installed as a symbolic link.
- The wrapper now resolves symlinks safely.
- `sudo ./install.sh` installs a self-contained runtime at `/usr/local/lib/git-exposure-auditor` and links `/usr/local/bin/gea` to it.
- Keeps Python >= 3.10 runtime selection and existing safety behavior unchanged.
- Aligns VERSION, Python package version, and HTTP User-Agent at `3.2.0-rc4`.

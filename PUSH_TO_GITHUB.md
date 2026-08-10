# Push to GitHub

```bash
cd git-exposure-auditor-v3.2.0-rc2
git init
git branch -M main
git add .
git commit -m "release: Git Exposure Auditor v3.2.0-rc2"
git remote add origin https://github.com/USERNAME/git-exposure-auditor.git
git push -u origin main
```

Tag Release Candidate:

```bash
git tag -a v3.2.0-rc2 -m "Git Exposure Auditor v3.2.0-rc2"
git push origin v3.2.0-rc2
```

Sebelum push:

```bash
./tests/run_all.sh
sha256sum ../git-exposure-auditor-v3.2.0-rc2.zip
```

Jangan memakai label LTS pada release ini.

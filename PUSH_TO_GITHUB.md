# Push to GitHub

```bash
cd git-exposure-auditor-v3.2.0-rc1
git init
git branch -M main
git add .
git commit -m "release: Git Exposure Auditor v3.2.0-rc1"
git remote add origin https://github.com/USERNAME/git-exposure-auditor.git
git push -u origin main
```

Tag Release Candidate:

```bash
git tag -a v3.2.0-rc1 -m "Git Exposure Auditor v3.2.0-rc1"
git push origin v3.2.0-rc1
```

Sebelum push:

```bash
./tests/run_all.sh
sha256sum ../git-exposure-auditor-v3.2.0-rc1.zip
```

Jangan memakai label LTS pada release ini.

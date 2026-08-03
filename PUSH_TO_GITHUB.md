# Push to GitHub

```bash
cd git-exposure-auditor-v3
git init
git branch -M main
git add .
git commit -m "release: Git Exposure Auditor v3.1.0-rc1"
git remote add origin https://github.com/USERNAME/git-exposure-auditor.git
git push -u origin main
```

Tag Release Candidate:

```bash
git tag -a v3.1.0-rc1 -m "Git Exposure Auditor v3.1.0-rc1"
git push origin v3.1.0-rc1
```

Jangan memakai label LTS pada release ini. Cantumkan bahwa pengujian otomatis tidak menjamin kompatibilitas dengan seluruh WAF/CDN/custom configuration di internet.

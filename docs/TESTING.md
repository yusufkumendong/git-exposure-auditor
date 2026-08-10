# Testing Status — 3.2.0-rc2

Tanggal pengujian lokal: **2026-08-04**

Environment build:

```text
GNU Bash 5.2.37
curl 8.10.1
Python 3.13.5
Linux x86_64
```

Hasil lokal:

```text
Syntax Bash                 PASS
Python compile              PASS
Unit test                   PASS
Integration test            PASS
Adaptive phase stop         PASS
Full-scan override          PASS
Resume without duplication  PASS
Host aggregation            PASS
Report compatibility        PASS
Authorized policy gate      PASS
Local report explainer      PASS
```

Fixture mencakup:

- valid Git HEAD;
- valid branch ref;
- valid Git index `DIRC`;
- SPA fallback HTTP 200;
- protected HTTP 404;
- Cloudflare-like HTTP 403;
- HTTP 429 dan retry;
- HTTP 503 dan retry;
- clean host yang berhenti setelah Tier 1;
- authorized-advanced policy metadata;
- scope include/exclude;
- evidence redaction;
- network error mapping unit test.

Belum diklaim lulus lokal:

- GitHub Actions container matrix sebelum workflow benar-benar dijalankan di GitHub;
- ShellCheck karena binary tidak tersedia pada environment build ini;
- live compatibility terhadap seluruh WAF/CDN/proxy di internet;
- LTS qualification.

Test dilakukan terhadap mock server lokal. Tidak ada target internet yang dipindai selama proses build ini.

## rc2 CI hardening

Workflow utama menggunakan Python 3.12 secara eksplisit. Container matrix menggunakan interpreter yang memenuhi Python >= 3.10; Rocky Linux 9 memakai Python 3.11. Test entry point dipanggil melalui `bash tests/run_all.sh` agar permission bit dari Windows tidak menjadi sumber false failure.

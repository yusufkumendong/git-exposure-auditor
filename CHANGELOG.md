# Changelog

## 3.2.0-rc2 — 2026-08-10

- Memperbaiki GitHub Actions yang gagal saat file executable bit hilang setelah update dari Windows.
- CI menjalankan test script melalui `bash` sehingga tidak bergantung pada permission bit lokal.
- Menambahkan explicit Python 3.12 pada job utama dan Python 3.11 untuk Rocky Linux 9.
- Wrapper `bin/gea` sekarang memilih runtime Python >= 3.10 dan mendukung `GEA_PYTHON`.
- Installer memvalidasi versi Python, bukan hanya keberadaan command `python3`.
- Makefile menggunakan VERSION secara dinamis dan target test/install tidak bergantung pada executable bit.

## 3.2.0-rc1 — 2026-08-04

### Architecture

- Mengganti orchestration Bash-heavy menjadi Python modular dengan Bash compatibility wrapper.
- Menambahkan modul terpisah untuk CLI, HTTP client, scope, policy, discovery, analyzer, scanner, reporter, model, dan utility.

### Scanning

- Two-phase adaptive scanning dan smart endpoint tiers.
- Full-scan override untuk seluruh delapan endpoint.
- Adaptive multi-baseline hingga tiga baseline.
- Global rate limiter untuk concurrent target processing.
- Selective retry dan `Retry-After` handling.
- Resume, checkpoint, dan optional canonical hostname deduplication.

### Analysis

- Host-level aggregation dan verdict priority.
- Explainable heuristic score dengan evidence points.
- Network error taxonomy.
- Custom read-only JSON signatures.
- Redirect scope/IP revalidation tanpa auto-follow.

### Authorization

- Mode `authorized-advanced` dan alias `bypass-authorized`.
- Wajib `--authorized`, `--bypass-permitted`, explicit scope, dan JSON policy.
- Policy snapshot disimpan ke metadata.
- Automatic evasion, dumping, dan credential testing tetap tidak diimplementasikan.

### Reporting

- Endpoint JSONL/CSV dan host JSONL/CSV.
- Summary dengan request saving metrics dan priority recommendations.
- Static HTML dashboard.
- Redacted evidence bundle.
- Historical comparison.
- Deterministic local report explainer.
- Compatibility output `results.jsonl` dan `results.csv`.

### Tests

- Unit dan integration test untuk adaptive scan, resume, full scan, policy gate, reports, redaction, scope, signature, dan taxonomy.

## 3.1.0-rc1

- Direct input domain, subdomain, target, dan wildcard.
- Passive wildcard discovery.
- Random baseline dan Git signature validation.
- JSONL, CSV, TXT, dan HackerOne candidate report.

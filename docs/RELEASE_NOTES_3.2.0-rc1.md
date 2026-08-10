# Release Notes — Git Exposure Auditor v3.2.0-rc1

## Highlight

Release ini memindahkan fokus dari "mencetak setiap response" menjadi "membuat keputusan host yang dapat dijelaskan".

Peningkatan utama:

- adaptive endpoint expansion;
- request saving metrics;
- host verdict;
- network error taxonomy;
- explainable evidence score;
- policy-aware authorized advanced mode;
- scope exclusion dan redirect revalidation;
- resume/checkpoint;
- redacted evidence bundle;
- static HTML dashboard;
- historical report comparison;
- custom signatures;
- local deterministic report explainer.

## Safety boundary

Release ini tidak menambahkan repository dumping, credential testing, recursive object enumeration, automatic authentication bypass, atau automatic WAF evasion.

## Local verification

Pada build 2026-08-04, seluruh syntax, unit, dan integration test lokal lulus. Test memakai mock server pada loopback dan tidak memindai target internet.

## Known limitations

- Release Candidate, bukan LTS.
- Live WAF/CDN behavior dapat berbeda dari fixture.
- `crt.sh` dan subfinder tergantung availability eksternal saat digunakan.
- CNAME deduplication bersifat opt-in karena virtual host berbeda dapat berbagi canonical infrastructure.
- HTTP/2 bergantung pada build curl.

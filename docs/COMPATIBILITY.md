# Compatibility

## Status

Versi `3.1.0-rc1` adalah Release Candidate, bukan LTS. Kompatibilitas berarti tool berusaha mengklasifikasikan respons secara stabil; bukan kemampuan membypass WAF, CDN, proxy, CAPTCHA, atau access control.

## Kapabilitas yang tersedia

- HTTP/1.1 dan HTTP/2 melalui curl.
- gzip/brotli/zstd sesuai build curl melalui `--compressed`.
- TLS validation dan opsi `--insecure` eksplisit.
- HTTP/SOCKS proxy melalui curl.
- 3xx dicatat tanpa auto-follow.
- Retry untuk network error, 429, 502, 503, dan 504.
- `Retry-After` numerik dihormati hingga batas backoff.
- Baseline comparison untuk soft-404 dan SPA fallback.
- Fingerprint hint untuk Cloudflare, Akamai, Imperva, Sucuri, CloudFront, Fastly/Varnish, serta generic Server/Via.

## Test fixture lokal

| Kondisi | Expected classification |
|---|---|
| Valid `/.git/HEAD` | `confirmed_exposure` |
| Git index `DIRC` | `confirmed_exposure` |
| SPA fallback 200 | `spa_fallback` |
| Custom missing page 200 | `soft_404` atau `custom_error` |
| Cloudflare-like 403 | `waf_challenge` |
| HTTP 429 | `rate_limited` |
| HTTP 503 | `upstream_error` |
| Missing path 404 | `protected` |

## Belum dapat dijamin

- Seluruh custom WAF/CDN signatures.
- Halaman sangat dinamis yang berubah pada setiap request.
- Target yang memerlukan browser JavaScript.
- Mutual TLS, HTTP/3, atau custom authentication flow.
- Semua versi Bash/curl pada setiap distribusi.
- Ketersediaan `crt.sh` dan completeness Certificate Transparency.

## Target LTS

Label LTS hanya akan digunakan setelah:

- matrix CI stabil pada Ubuntu, Debian, Kali, AlmaLinux, dan Rocky Linux;
- ShellCheck tanpa error kritis;
- regression fixture bertambah;
- release stabil dipakai dan menerima perbaikan nyata;
- support window dan patch policy diterapkan.

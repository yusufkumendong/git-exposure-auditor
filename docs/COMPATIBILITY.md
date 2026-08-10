# Compatibility

## Status

`3.2.0-rc2` adalah Release Candidate, bukan LTS.

## Runtime

- Bash 4.3+
- Python 3.10+
- curl dengan HTTP/HTTPS support

## Supported behavior

- HTTP/1.1 dan HTTP/2 sesuai build curl.
- gzip/brotli/zstd sesuai build curl melalui `--compressed`.
- TLS validation dan explicit `--insecure`.
- HTTP/SOCKS proxy melalui curl.
- 3xx dicatat tanpa auto-follow.
- Retry selektif dan numeric `Retry-After`.
- IPv4/IPv6 resolution guard.
- IDNA hostname normalization.
- Exact dan wildcard scope.
- Static HTML report tanpa JavaScript dependency.

## Tested fixture classifications

| Kondisi | Expected |
|---|---|
| Valid `/.git/HEAD` | `confirmed_exposure` |
| Valid branch ref | `confirmed_exposure` |
| Git index `DIRC` | `confirmed_exposure` |
| SPA fallback | `spa_fallback` |
| HTTP 404 | `protected` |
| Cloudflare-like HTTP 403 | `waf_challenge` |
| HTTP 429 | `rate_limited` |
| HTTP 503 | `upstream_error` |
| Clean adaptive host | Stop setelah Tier 1 |
| Full-scan override | Seluruh delapan endpoint |

## Belum dijamin

- Seluruh custom WAF/CDN signatures.
- Browser JavaScript challenge.
- Mutual TLS.
- HTTP/3.
- Custom authentication flows.
- Semua edge case DNS rebinding.
- Semua konfigurasi virtual hosting ketika CNAME deduplication aktif.
- Availability dan completeness `crt.sh`/subfinder.

## LTS gate

Label LTS hanya diberikan setelah CI matrix stabil, regression fixture bertambah, compatibility feedback nyata diterima, dan support window terdokumentasi.

## Catatan Rocky Linux 9

Rocky Linux 9 pada matrix CI menggunakan Python 3.11 (`python3.11`) agar memenuhi minimum runtime Python 3.10+. Wrapper `bin/gea` dapat memilih interpreter versioned yang kompatibel secara otomatis.


## Rocky Linux 9 container note

Rocky Linux 9 minimal/container images can ship `curl-minimal` by default. GEA only requires the `curl` command, so the CI job keeps `curl-minimal` instead of forcing installation of the mutually exclusive full `curl` RPM. If a user specifically needs full curl features, replace it explicitly with `dnf -y swap curl-minimal curl`.

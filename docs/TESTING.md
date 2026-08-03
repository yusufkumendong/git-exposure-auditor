# Testing Status — 3.1.0-rc1

Tanggal pengujian lokal: 2026-08-03

Environment:

```text
GNU Bash 5.2.37
curl 8.10.1 (HTTP/2 enabled)
Python 3.13.5
jq 1.7
```

Hasil:

```text
Syntax test                 PASS
Python compile test         PASS
Direct input parser test    PASS
Integration classification  PASS
Direct --domain test        PASS
Direct --subdomain test     PASS
Direct --wildcard test      PASS
```

Integration fixture mencakup:

- valid Git HEAD;
- valid branch ref;
- valid Git index DIRC;
- SPA fallback HTTP 200;
- protected HTTP 404;
- Cloudflare-like HTTP 403 challenge;
- HTTP 429 rate limit;
- HTTP 503 upstream error dan retry.

Belum diklaim lulus secara lokal:

- ShellCheck (dikonfigurasi pada GitHub Actions, tetapi binary tidak tersedia pada environment build lokal);
- seluruh matrix container GitHub Actions;
- live compatibility terhadap semua WAF/CDN/proxy/custom error page;
- LTS qualification.

Status test ini membuktikan fixture dan jalur eksekusi yang disebutkan, bukan jaminan bahwa semua target internet akan memberikan klasifikasi sempurna.

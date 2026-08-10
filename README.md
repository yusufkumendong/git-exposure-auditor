# Git Exposure Auditor v3.2

Git Exposure Auditor adalah validator exposure `.git` yang **non-destruktif, adaptive, signature-aware, scope-aware, dan rendah false positive** untuk aset yang berada dalam scope pengujian resmi.

> Versi paket ini: **3.2.0-rc2**. Statusnya Release Candidate, belum LTS.

Tool tidak menganggap HTTP 200 sebagai vulnerability. Setiap respons dibandingkan dengan random-path baseline, divalidasi menggunakan signature Git, lalu diagregasi menjadi satu verdict per host.

## Batas keselamatan

Gunakan hanya pada aset milik sendiri atau aset yang tercantum dalam scope program bug bounty/VDP dan mengizinkan automated testing.

Tool ini tidak melakukan:

- repository dumping atau reconstruction;
- recursive object enumeration;
- credential/secret testing;
- brute force;
- denial of service;
- exploit chaining;
- perubahan data atau konfigurasi target;
- automatic authentication bypass;
- automatic WAF/CDN evasion;
- redirect follow otomatis keluar scope.

Mode `authorized-advanced` mencatat izin program dan mengaktifkan validasi lanjutan yang tetap non-destruktif. Mode tersebut **bukan bypass engine**.

## Perubahan utama v3.2

- Two-phase adaptive scanning untuk menghemat request.
- Smart endpoint tiers: Tier 1, Tier 2, dan Tier 3.
- Multi-baseline adaptif, maksimal tiga baseline per host.
- Host-level verdict: `valid_exposure`, `potential_exposure`, `manual_review`, `waf_blocked`, `not_exposed`, `unreachable`, atau `out_of_scope`.
- Explainable heuristic score dengan evidence breakdown.
- Network error taxonomy: DNS, timeout, TLS, refused, reset, proxy, oversized body, dan lainnya.
- Recommendation engine yang selalu menghasilkan action untuk host prioritas.
- Scope Engine v2 dengan include, exclude, DNS/IP validation, dan redirect revalidation.
- Resume dan checkpoint tanpa menduplikasi target yang sudah selesai.
- Optional CNAME deduplication.
- Redacted evidence bundle.
- JSONL, CSV, TXT, HTML dashboard, dan candidate HackerOne Markdown.
- Historical comparison melalui `--compare-report`.
- Custom read-only signature melalui JSON.
- Local deterministic report explainer melalui `gea explain`.
- Mode `authorized-advanced` dan alias `bypass-authorized` dengan authorization gate yang ketat.

## Dependency

Wajib:

- Bash 4.3+
- curl
- Python 3.10+

Opsional:

- `subfinder` untuk passive wildcard discovery yang lebih baik.
- `shellcheck` untuk development validation.

### Debian, Ubuntu, dan Kali

```bash
sudo apt update
sudo apt install -y bash curl python3 git
```

### AlmaLinux, Rocky Linux, dan RHEL

AlmaLinux 10:

```bash
sudo dnf install -y bash curl python3 git
```

Rocky Linux 9 / RHEL 9 (gunakan Python 3.11 agar memenuhi minimum Python 3.10+):

```bash
sudo dnf install -y bash python3.11 git ca-certificates
# Rocky 9 minimal/container images usually already provide curl-minimal.
# If `curl` is missing: sudo dnf install -y curl-minimal
```

## CI dan kompatibilitas

GitHub Actions menguji Ubuntu 24.04, Debian 12 slim, AlmaLinux 10, Rocky Linux 9 dengan Python 3.11, dan Kali rolling. Test suite dipanggil melalui `bash` agar checkout/update dari Windows tidak membuat CI gagal hanya karena executable bit lokal hilang.

## Instalasi

```bash
git clone https://github.com/USERNAME/git-exposure-auditor.git
cd git-exposure-auditor
chmod +x install.sh
./install.sh
```

System-wide:

```bash
sudo ./install.sh
gea --version
```

## Mode

### Easy

- Satu random baseline.
- Hanya `/.git/HEAD`.
- Concurrency 1.
- Tanpa retry default.

```bash
gea --mode easy --domain example.com
```

### Medium

- `/.git/HEAD`
- `/.git/config`
- `/.git/packed-refs`
- Baseline validation dan satu retry default.

```bash
gea --mode medium --subdomain app.example.com
```

### Hard

Memeriksa seluruh delapan endpoint metadata terbatas. Tidak melakukan crawling atau repository reconstruction.

```bash
gea --mode hard --target https://app.example.com
```

### Best Practice

- `--authorized` wajib.
- Scope eksplisit wajib, atau otomatis dibentuk dari direct input.
- Default concurrency 3 dan rate 2 request/detik.
- Maksimal concurrency dan rate 5.
- Adaptive scan aktif secara default.
- Multi-baseline adaptif.

```bash
gea \
  --mode best-practice \
  --wildcard '*.example.com' \
  --authorized \
  --enumerator subfinder \
  --max-discovered 100 \
  --report-dir reports/example-program
```

### Authorized Advanced

Mode ini hanya untuk program yang secara tertulis mengizinkan advanced/bypass-related validation. Mode ini mencatat policy metadata tetapi tidak menjalankan evasion otomatis.

Persyaratan wajib:

- `--authorized`
- `--bypass-permitted`
- `--scope FILE`
- `--policy-file FILE`

```bash
gea \
  --mode authorized-advanced \
  --target https://app.example.com \
  --scope examples/scope.txt \
  --policy-file examples/policy.example.json \
  --authorized \
  --bypass-permitted \
  --concurrency 2 \
  --rate 2 \
  --report-dir reports/example-advanced
```

Alias berikut tersedia:

```bash
gea --mode bypass-authorized ...
```

Alias tersebut tetap memakai engine dan safety gate yang sama.

## Two-phase adaptive scanning

Untuk `best-practice` dan `authorized-advanced`, scanner tidak langsung mengirim delapan endpoint ke setiap host.

### Phase 1 — High-value validation

```text
/.git/HEAD
/.git/config
```

Jika hasil Phase 1 adalah soft-404, SPA fallback, protected, WAF-only, atau network failure tanpa bukti menarik, scanner berhenti pada host tersebut.

### Phase 2 — Evidence expansion

```text
/.git/packed-refs
/.git/logs/HEAD
```

Phase 2 hanya dijalankan ketika Phase 1 menghasilkan signature, suspicious response, in-scope redirect, rate limit, atau upstream response yang memerlukan review.

### Phase 3 — Deep metadata validation

```text
/.git/refs/heads/main
/.git/refs/heads/master
/.git/index
/.git/objects/info/packs
```

Gunakan `--full-scan` untuk memaksa seluruh tier pada `best-practice`.

```bash
gea --mode best-practice --domain example.com --authorized --full-scan
```

## Input

Opsi dapat diulang atau dipisahkan dengan koma.

```bash
gea --mode hard \
  --domain example.com,example.org \
  --subdomain api.example.com \
  --subdomain app.example.com
```

URL dengan port:

```bash
gea --mode medium --target http://dev.example.com:8080
```

Input file tetap didukung:

```bash
gea --mode best-practice \
  --list examples/targets.txt \
  --scope examples/scope.txt \
  --authorized
```

## Scope Engine v2

Format `scope.txt`:

```text
include example.com
include *.example.com
exclude status.example.com
exclude *.internal.example.com
```

Format singkat juga didukung:

```text
example.com
*.example.com
!status.example.com
```

Aturan exclude dievaluasi lebih dahulu. Saat explicit scope file atau `--scope-rule` digunakan, target input **tidak otomatis memperluas scope**.

Tambahkan exclude dari CLI:

```bash
gea \
  --mode best-practice \
  --wildcard '*.example.com' \
  --exclude-scope '*.internal.example.com' \
  --authorized
```

Private, loopback, link-local, reserved, unspecified, dan multicast IP diblokir secara default. `--allow-private` wajib disertai `--authorized` dan hanya digunakan untuk lab atau aset internal yang benar-benar berizin.

Gunakan strict canonical validation untuk menolak CNAME/canonical hostname yang berada di luar scope:

```bash
--scope-strict
```

Mode ini konservatif dan dapat memblokir aset in-scope yang secara sah memakai CDN pihak ketiga, sehingga harus disesuaikan dengan policy program.

## Wildcard discovery

```bash
gea \
  --mode best-practice \
  --wildcard '*.example.com' \
  --authorized \
  --enumerator auto \
  --max-discovered 200
```

Enumerator:

- `auto`: memakai `subfinder`, fallback ke `crt.sh`.
- `subfinder`: mewajibkan binary `subfinder`.
- `crtsh`: memakai Certificate Transparency.
- `none`: hanya root wildcard.

Tanpa discovery:

```bash
gea --mode best-practice --wildcard '*.example.com' --authorized --no-discover
```

## Scope dan scheme

```bash
gea --mode medium --domain example.com --scheme https
gea --mode medium --domain example.com --scheme http
gea --mode medium --domain example.com --scheme both
```

## Request control

```bash
gea \
  --mode best-practice \
  --domain example.com \
  --authorized \
  --concurrency 3 \
  --rate 2 \
  --retries 1 \
  --retry-delay 1 \
  --retry-max-delay 10 \
  --connect-timeout 5 \
  --max-time 15
```

Retry hanya dilakukan secara selektif untuk:

- connect/read timeout;
- connection reset;
- proxy error;
- HTTP 429;
- HTTP 502, 503, dan 504.

DNS no-record, connection refused, dan TLS hostname mismatch tidak di-retry berulang.

## HTTP, TLS, proxy, dan header

```bash
gea --mode medium --domain example.com --http-version 1.1
gea --mode medium --domain example.com --http-version 2
```

```bash
gea \
  --mode best-practice \
  --domain example.com \
  --authorized \
  --proxy http://127.0.0.1:8080 \
  --header 'X-Bug-Bounty: researcher@example.test'
```

`--insecure` tersedia, tetapi hanya digunakan ketika policy dan konfigurasi target memang mengharuskan.

## Multi-baseline

Default dimulai dari satu baseline. Scanner dapat menambah baseline kedua ketika halaman terlihat HTML/dynamic, lalu baseline ketiga jika dua baseline awal tidak konsisten.

```bash
gea \
  --mode best-practice \
  --domain example.com \
  --authorized \
  --baseline-count 1 \
  --max-baselines 3
```

## Resume dan checkpoint

```bash
gea \
  --mode best-practice \
  --wildcard '*.example.com' \
  --authorized \
  --report-dir reports/example \
  --resume
```

Target yang sudah memiliki checkpoint `completed=true` tidak dipindai ulang. Reporter dibangun kembali dari JSONL yang sudah tersimpan sehingga hasil lama tidak hilang dan tidak diduplikasi.

```bash
--checkpoint-every 1
```

Checkpoint di-flush ke disk sesuai interval host tersebut.

## CNAME deduplication

```bash
gea \
  --mode best-practice \
  --wildcard '*.example.com' \
  --authorized \
  --deduplicate-cname
```

Fitur ini mengurangi scan alias yang memiliki canonical hostname sama. Gunakan dengan hati-hati karena hostname berbeda tetap dapat menjalankan virtual host yang berbeda.

## Custom signature

```bash
gea \
  --mode hard \
  --domain example.com \
  --signature-file examples/signatures.example.json
```

Custom signature hanya menambah regex validasi terhadap endpoint yang sudah diizinkan. Fitur ini tidak menambah crawling atau exploit action.

## Evidence storage dan redaction

Mode penyimpanan:

```text
--store-body none
--store-body snippet   # default
--store-body full
```

Semua text evidence yang disimpan selalu melewati redaction untuk pola umum password, secret, token, authorization header, URL userinfo, dan private key block.

Batasi evidence snippet:

```bash
--evidence-max-bytes 2048
```

Default maksimum body yang diambil curl adalah 262144 byte.

## Laporan

Struktur laporan:

```text
reports/example/
├── run-metadata.json
├── scope-snapshot.json
├── checkpoint.jsonl
├── endpoint-results.jsonl
├── endpoint-results.csv
├── results.jsonl
├── results.csv
├── host-summary.jsonl
├── host-summary.csv
├── summary.txt
├── report.html
├── hackerone-findings.md
└── evidence/
    └── host-hash/
        ├── summary.json
        ├── response-metadata.jsonl
        └── *.redacted.txt
```

`results.jsonl` dan `results.csv` dipertahankan sebagai compatibility alias/copy untuk workflow v3.1.

`hackerone-findings.md` hanya menghasilkan kandidat finding untuk host dengan verdict `valid_exposure`. Hasil `not_exposed`, WAF-only, 404, 5xx, dan network error tidak dijadikan finding.

## Host verdict

| Verdict | Makna |
|---|---|
| `valid_exposure` | Terdapat signature Git kuat yang reportable setelah manual validation |
| `potential_exposure` | Signature cukup kuat, tetapi evidence masih ambigu |
| `manual_review` | Respons menarik, redirect in-scope, 5xx, rate limit, atau custom response |
| `waf_blocked` | WAF/access-control menghalangi validasi |
| `not_exposed` | Soft-404, SPA fallback, protected, atau tidak ada signature |
| `unreachable` | DNS/TLS/timeout/koneksi gagal |
| `out_of_scope` | Scope/IP/redirect validation menolak target |

Satu endpoint `valid_exposure` mengalahkan beberapa endpoint `not_exposed` pada host yang sama.

## Explainable score

Angka score adalah **heuristic score**, bukan probabilitas ilmiah.

Contoh evidence breakdown:

```text
+98 Git HEAD symbolic reference
 +4 Content-Type text/plain
 +5 Response berbeda dari baseline
-30 Response terlalu mirip baseline
```

Level:

- `HIGH`: 85–100
- `MEDIUM`: 60–84
- `LOW`: 0–59

## Network error taxonomy

Klasifikasi yang tersedia mencakup:

```text
dns_no_record
dns_error
connect_timeout
read_timeout
tls_error
tls_hostname_mismatch
connection_refused
connection_reset
proxy_error
unsupported_protocol
redirect_loop
body_too_large
network_error
```

## Historical comparison

```bash
gea \
  --mode best-practice \
  --domain example.com \
  --authorized \
  --compare-report reports/previous-run \
  --report-dir reports/current-run
```

Hasil perubahan ditulis ke `comparison.json`.

## Local report explainer

```bash
gea explain --report-dir reports/example
```

Explainer ini deterministic dan berjalan lokal. Tidak mengirim report, target, atau evidence ke API AI eksternal.

## Fail on findings

```bash
gea \
  --mode best-practice \
  --domain example.com \
  --authorized \
  --fail-on-findings
```

Exit code `10` diberikan ketika terdapat `valid_exposure` atau `potential_exposure`.

## Testing

```bash
./tests/run_all.sh
```

Test suite mencakup:

- syntax Bash/Python;
- scope include/exclude;
- policy gate;
- redaction;
- Git signature;
- network error taxonomy;
- adaptive phase stop;
- full-scan override;
- resume tanpa duplikasi;
- host aggregation;
- report compatibility;
- authorized-advanced metadata;
- local explainer.

Lihat `docs/TESTING.md` untuk status yang telah benar-benar diuji.

# Git Exposure Auditor V3.1

Git Exposure Auditor adalah validator `.git` exposure yang aman, signature-aware, dan rendah false positive untuk aset yang berada dalam scope pengujian resmi. Tool membandingkan respons endpoint Git dengan baseline path acak agar dapat membedakan exposure asli dari soft-404, SPA fallback, custom error page, WAF/CDN challenge, rate limit, redirect, dan upstream error.

> Versi saat ini: **3.1.0-rc1 (Release Candidate)**. Belum berstatus LTS.

## Batas keselamatan

Gunakan hanya pada aset milik sendiri atau aset yang tercantum dalam scope program bug bounty/VDP. Tool ini tidak melakukan repository dumping, credential testing, authentication bypass, WAF bypass, brute force, exploit chaining, atau perubahan pada target.

## Fitur utama

- Input langsung domain, subdomain, URL, dan wildcard—TXT tidak wajib.
- Wildcard memakai enumerasi pasif terbatas melalui `subfinder` atau `crt.sh`.
- Empat mode: Easy, Medium, Hard, dan Best Practice.
- Auto-calibration menggunakan random-path baseline.
- Deteksi soft-404, SPA fallback, custom error, WAF/CDN challenge, 429, redirect, 5xx, dan network error.
- Validasi signature `HEAD`, `config`, `packed-refs`, branch refs, reflog, index `DIRC`, dan object pack listing.
- Confidence score 0–100 dan alasan klasifikasi.
- Retry terbatas, exponential backoff, serta dukungan `Retry-After`.
- Rate limit, safe concurrency, proxy, custom header, HTTP/1.1 atau HTTP/2.
- Scope otomatis dari `--domain`, `--subdomain`, `--target`, dan `--wildcard`.
- Laporan JSONL, CSV, TXT, dan kandidat laporan Markdown untuk HackerOne.
- Response body hanya dipakai sementara untuk validasi lalu dihapus; laporan menyimpan hash, bukan body.

## Dependency

Wajib:

- Bash 4.3+
- curl
- jq
- Python 3

Opsional untuk wildcard discovery yang lebih baik:

- subfinder

### Debian, Ubuntu, dan Kali

```bash
sudo apt update
sudo apt install -y curl jq python3 git
```

### AlmaLinux, Rocky Linux, dan RHEL

```bash
sudo dnf install -y curl jq python3 git
```

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

## Penggunaan tanpa TXT

### Satu domain

```bash
gea --mode easy --domain example.com
```

### Satu subdomain

```bash
gea --mode medium --subdomain app.example.com
```

### Beberapa domain dan subdomain

Opsi dapat diulang:

```bash
gea --mode hard \
  --domain example.com \
  --subdomain app.example.com \
  --subdomain api.example.com
```

Atau dipisahkan koma:

```bash
gea --mode hard \
  --domain example.com,example.org \
  --subdomain app.example.com,api.example.com
```

### URL dengan port atau HTTP

```bash
gea --mode medium --target http://dev.example.com:8080
```

### Wildcard HackerOne

Wildcard harus memakai tanda kutip agar tidak dikembangkan oleh shell:

```bash
gea --mode best-practice \
  --wildcard '*.example.com' \
  --authorized
```

Perilaku wildcard:

1. Menambahkan `*.example.com` sebagai scope.
2. Menemukan subdomain secara pasif.
3. Memvalidasi setiap hasil agar tetap berada dalam wildcard.
4. Membatasi hasil default maksimal 300 host.
5. Memindai root domain dan host hasil discovery.

Gunakan `subfinder` secara eksplisit:

```bash
gea --mode best-practice \
  --wildcard '*.example.com' \
  --authorized \
  --enumerator subfinder \
  --max-discovered 200
```

Gunakan Certificate Transparency tanpa subfinder:

```bash
gea --mode best-practice \
  --wildcard '*.example.com' \
  --authorized \
  --enumerator crtsh
```

Tanpa discovery, hanya root domain yang diperiksa:

```bash
gea --mode best-practice \
  --wildcard '*.example.com' \
  --authorized \
  --no-discover
```

## Mode

### Easy

- `/.git/HEAD`
- Satu baseline path acak
- Concurrency 1
- Tanpa retry default

```bash
./scripts/easy.sh example.com
```

### Medium

- `/.git/HEAD`
- `/.git/config`
- `/.git/packed-refs`
- Baseline, content validation, retry 1

```bash
./scripts/medium.sh app.example.com
```

### Hard

Memeriksa delapan endpoint metadata terbatas tanpa recursive crawling atau dumping.

```bash
./scripts/hard.sh app.example.com
```

### Best Practice

- `--authorized` wajib.
- Scope otomatis dari input langsung.
- Concurrency maksimal 5.
- Rate maksimal 5 request/detik.
- Default concurrency 3 dan rate 2 request/detik.
- Wildcard discovery pasif dan dibatasi.

```bash
./scripts/best-practice.sh '*.example.com'
```

## Contoh aman untuk program bug bounty

```bash
gea --mode best-practice \
  --wildcard '*.example.com' \
  --authorized \
  --enumerator subfinder \
  --max-discovered 100 \
  --concurrency 3 \
  --rate 2 \
  --retries 1 \
  --report-dir reports/example-program
```

Selalu baca policy program terlebih dahulu. Wildcard pada halaman scope tidak selalu berarti seluruh jenis automated scanning diperbolehkan.

## Klasifikasi

| Klasifikasi | Makna |
|---|---|
| `confirmed_exposure` | Signature Git kuat dan berbeda dari baseline |
| `probable_exposure` | Indikasi Git kuat tetapi masih memerlukan validasi manual |
| `soft_404` | Respons sangat mirip dengan random-path baseline |
| `spa_fallback` | Halaman aplikasi yang sama dikembalikan untuk path berbeda |
| `custom_error` | Respons 2xx terlihat seperti halaman error/challenge |
| `waf_challenge` | Access denied atau challenge dari WAF/CDN |
| `rate_limited` | HTTP 429 |
| `protected` | Endpoint ditolak/tidak tersedia |
| `redirect_in_scope` | Redirect menuju aset yang masih in-scope |
| `redirect_out_of_scope` | Redirect keluar scope dan tidak diikuti |
| `upstream_error` | HTTP 5xx dari origin/CDN/proxy/WAF |
| `network_error` | DNS, TLS, timeout, atau koneksi gagal |
| `suspicious` | Respons menarik tetapi bukti tidak cukup |

HTTP 200 tidak otomatis dianggap vulnerable. HTTP 500 juga bukan bukti exposure dan hanya masuk rekomendasi validasi manual terbatas.

## Proxy dan custom header

```bash
gea --mode best-practice \
  --domain example.com \
  --authorized \
  --proxy http://127.0.0.1:8080 \
  --header 'X-Bug-Bounty: researcher@example.test'
```

Proxy hanya untuk routing resmi/observasi. Tool tidak menggunakan proxy untuk menyembunyikan identitas, melewati kontrol, atau menghindari rate limit.

## HTTP dan TLS

```bash
gea --mode medium --domain example.com --http-version 1.1
gea --mode medium --domain example.com --http-version 2
gea --mode medium --domain example.com --insecure
```

`--insecure` hanya digunakan saat policy dan kondisi target memang memerlukannya.

## Laporan

Setiap eksekusi menghasilkan:

```text
reports/YYYYMMDD-HHMMSS/
├── results.jsonl
├── results.csv
├── summary.txt
└── hackerone-findings.md
```

`hackerone-findings.md` hanya memasukkan `confirmed_exposure` dan `probable_exposure`. Tetap lakukan validasi manual serta sesuaikan title, impact, severity, dan reproduksi dengan policy program.

Filter hasil:

```bash
jq 'select(.classification=="confirmed_exposure")' reports/*/results.jsonl
```

Exit code untuk pipeline:

```bash
gea --mode medium --domain example.com --fail-on-findings
```

- `0`: selesai normal.
- `10`: ditemukan confirmed/probable exposure.
- `1`: konfigurasi atau eksekusi gagal.

## Pengujian lokal

```bash
./tests/syntax.sh
./tests/input.sh
./tests/integration.sh
```

Status pengujian RC ini menjelaskan test lokal/CI, bukan jaminan kompatibilitas dengan seluruh konfigurasi internet. Lihat `docs/COMPATIBILITY.md`.

## Dokumentasi

- `docs/ARCHITECTURE.md`
- `docs/COMPATIBILITY.md`
- `docs/SAFETY.md`
- `docs/SUPPORT.md`
- `docs/TESTING.md`
- `docs/CHANGELOG.md`
- `PUSH_TO_GITHUB.md`

# Release Notes — Git Exposure Auditor v3.2.0-rc2

`v3.2.0-rc2` adalah compatibility/CI release candidate untuk menutup masalah packaging Windows dan runtime Linux matrix yang ditemukan setelah `rc1` dipush ke GitHub.

## Perbaikan utama

- GitHub Actions tidak lagi mengeksekusi `tests/run_all.sh` secara langsung; workflow memanggilnya melalui `bash`.
- `tests/run_all.sh`, syntax test, dan integration test menghormati `GEA_PYTHON`.
- Job utama memakai Python 3.12 secara eksplisit.
- Rocky Linux 9 diuji menggunakan Python 3.11 karena project mensyaratkan Python 3.10+.
- `bin/gea` mencari runtime Python kompatibel secara otomatis dan memberi error yang jelas bila tidak ada.
- `install.sh` memvalidasi versi Python sebelum instalasi.
- Mode executable untuk shell entry points tetap harus disimpan di Git; workflow kini lebih tahan terhadap checkout/update dari Windows.

## Catatan upgrade dari rc1

Pada repository yang di-update dari Windows, jalankan sebelum commit:

```bash
git update-index --chmod=+x bin/gea install.sh scripts/*.sh tests/*.sh
```

Tidak ada perubahan pada model safety: tool tetap non-destruktif dan tidak melakukan repository dumping, credential testing, brute force, automatic authentication bypass, atau automatic WAF evasion.

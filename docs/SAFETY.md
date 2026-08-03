# Safety

## Diizinkan oleh desain tool

- GET request terbatas ke endpoint metadata Git yang ditentukan.
- Random non-existent path untuk baseline.
- Passive subdomain discovery untuk wildcard.
- Minimal evidence hashing dan reporting.

## Tidak diimplementasikan

- Repository dumping atau reconstruction.
- Object enumeration recursive.
- Credential/secret extraction.
- Authentication atau WAF bypass.
- CAPTCHA/JavaScript challenge bypass.
- Brute force, denial of service, race flooding, atau exploit chaining.
- Follow redirect otomatis ke luar scope.

## Sebelum menjalankan

1. Pastikan aset benar-benar in-scope.
2. Baca bagian automation, rate limit, dan prohibited testing pada policy.
3. Gunakan rate/concurrency konservatif.
4. Jangan menguji third-party infrastructure yang muncul dari CNAME/redirect tanpa izin.
5. Hentikan saat menerima blocking, instability, atau permintaan dari program.

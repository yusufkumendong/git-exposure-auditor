# Safety

## Diizinkan oleh desain tool

- GET request terbatas ke endpoint metadata Git yang ditentukan.
- Random non-existent path untuk baseline.
- Passive subdomain discovery yang dibatasi.
- Signature, hash, header metadata, dan similarity validation.
- Manual-review recommendation.
- Authorized-advanced metadata recording untuk program yang mengizinkan.

## Tidak diimplementasikan

- Repository dumping atau reconstruction.
- Recursive object enumeration.
- Credential, token, atau secret testing.
- Authentication bypass otomatis.
- WAF/CDN evasion otomatis.
- CAPTCHA atau browser challenge bypass.
- Header mutation library untuk evasion.
- Identity rotation atau stealth.
- Brute force, DoS, race flooding, atau exploit chaining.
- Perubahan data target.
- Auto-follow redirect.

## Authorized Advanced

Mode `authorized-advanced` mewajibkan:

- explicit authorization flag;
- explicit bypass-permission flag;
- scope file;
- policy JSON yang menyatakan authorization dan advanced validation.

Metadata tersebut disimpan untuk auditability. Tool tetap hanya menjalankan endpoint validation yang sama dan tidak mengubah safety boundary.

## Sebelum menjalankan

1. Pastikan hostname dan jenis testing benar-benar in-scope.
2. Simpan snapshot policy program.
3. Baca automation, rate limit, prohibited testing, dan third-party rules.
4. Gunakan rate/concurrency konservatif.
5. Jangan mengizinkan private IP kecuali merupakan lab/aset internal yang sah.
6. Hentikan ketika target tidak stabil atau program meminta penghentian.
7. Jangan mengirim raw evidence ke layanan pihak ketiga tanpa izin.

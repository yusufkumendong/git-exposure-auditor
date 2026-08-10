# Security Policy

Laporkan vulnerability pada source tool melalui GitHub Security Advisory. Jangan membuka issue publik yang berisi credential, raw target evidence, policy privat, atau data sensitif.

Tool hanya ditujukan untuk good-faith security research pada aset yang memiliki authorization dan scope jelas.

## Safety invariants

Kontribusi tidak boleh menambahkan:

- repository dumping/reconstruction;
- credential atau secret testing;
- automatic authentication/WAF bypass;
- brute force, DoS, atau exploit chaining;
- auto-follow redirect keluar scope;
- persistence atau perubahan target.

`authorized-advanced` hanya mencatat dan memvalidasi metadata izin. Mode tersebut tidak menghapus safety invariants.

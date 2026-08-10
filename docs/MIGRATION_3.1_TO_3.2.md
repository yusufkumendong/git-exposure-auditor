# Migration from 3.1 to 3.2

## CLI compatibility

Perintah dasar tetap kompatibel:

```bash
gea --mode easy --domain example.com
gea --mode medium --subdomain app.example.com
gea --mode hard --target https://app.example.com
gea --mode best-practice --wildcard '*.example.com' --authorized
```

## Output changes

v3.1:

```text
results.jsonl
results.csv
summary.txt
hackerone-findings.md
```

v3.2 menambahkan:

```text
endpoint-results.jsonl
endpoint-results.csv
host-summary.jsonl
host-summary.csv
report.html
checkpoint.jsonl
scope-snapshot.json
run-metadata.json
evidence/
```

`results.jsonl` dan `results.csv` tetap dibuat sebagai compatibility copy.

## Classification versus verdict

v3.1 memakai endpoint classification sebagai output utama. v3.2 mempertahankan endpoint classification dan menambahkan verdict per host.

Contoh:

```text
classification: confirmed_exposure
verdict: valid_exposure
```

Automation baru sebaiknya membaca `host-summary.jsonl` untuk keputusan host dan `endpoint-results.jsonl` untuk evidence detail.

## Confidence field

v3.1 memakai `confidence`. v3.2 memakai:

```text
heuristic_score
confidence_level
evidence[]
```

Angka tersebut adalah heuristic, bukan probabilitas statistik.

## Best Practice behavior

v3.1 memeriksa seluruh endpoint yang dipilih. v3.2 memakai adaptive tiers dan dapat berhenti setelah dua endpoint. Gunakan `--full-scan` untuk perilaku exhaustive yang setara dengan hard endpoint coverage.

## Advanced mode

Mode baru memerlukan explicit policy metadata:

```bash
gea --mode authorized-advanced \
  --target https://app.example.com \
  --scope scope.txt \
  --policy-file policy.json \
  --authorized \
  --bypass-permitted
```

Tidak ada automatic bypass yang ditambahkan.

## Dependency

`jq` tidak lagi menjadi runtime dependency. Bash, curl, dan Python tetap wajib.

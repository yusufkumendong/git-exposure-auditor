# Architecture

## Alur utama

```text
Input langsung
  ├─ --target
  ├─ --domain
  ├─ --subdomain
  └─ --wildcard
        ↓
Scope normalization dan passive discovery
        ↓
Private/reserved address guard
        ↓
Random-path baseline per target
        ↓
HTTP client: compression, timeout, retry, backoff, Retry-After
        ↓
Endpoint metadata Git terbatas
        ↓
Signature + baseline similarity + header/body classification
        ↓
Confidence score dan recommendation
        ↓
JSONL, CSV, TXT, HackerOne Markdown
```

## Modul

- `bin/gea`: parsing CLI, mode defaults, authorization, orchestration.
- `lib/input.sh`: direct input, comma/repeated args, wildcard passive discovery.
- `lib/scope.sh`: exact dan wildcard scope matching.
- `lib/http_client.sh`: request, compression, retry, proxy, HTTP version.
- `lib/analyzer.py`: Git signatures, similarity, WAF/CDN/custom error classification.
- `lib/scanner.sh`: baseline dan bounded endpoint scheduling.
- `lib/reporter.sh`: terminal, JSONL, CSV, summary, report candidate.

## Prinsip desain

1. Status HTTP bukan bukti tunggal.
2. Baseline path acak wajib sebelum endpoint validation.
3. Redirect tidak diikuti otomatis.
4. Wildcard discovery bersifat pasif dan dibatasi.
5. Response body hanya disimpan sementara.
6. Scope berasal dari input dan diverifikasi kembali.
7. Tool berhenti pada metadata validation; tidak melakukan repository reconstruction.

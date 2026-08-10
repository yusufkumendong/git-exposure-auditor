# Architecture — v3.2

## Alur utama

```text
Direct input / list / wildcard
        ↓
Explicit scope + exclusions
        ↓
Passive discovery dan target normalization
        ↓
DNS, private/reserved IP, dan canonical-name guard
        ↓
Adaptive random-path baselines (1–3)
        ↓
Phase 1: HEAD + config
        ↓
Classification + expansion decision
        ├─ stop: fallback/protected/unreachable
        └─ expand: evidence/manual-review trigger
                ↓
Phase 2: packed-refs + logs/HEAD
                ↓
Phase 3: branch refs + index + packs
                ↓
Endpoint evidence + heuristic score
                ↓
Host-level verdict aggregation
                ↓
Checkpoint + redacted evidence
                ↓
JSONL / CSV / TXT / HTML / Markdown
```

## Modul

- `bin/gea`: compatibility launcher.
- `gea/cli.py`: parsing, mode defaults, authorization gate, orchestration.
- `gea/scope.py`: include/exclude, DNS/IP guard, redirect validation.
- `gea/policy.py`: authorized-advanced JSON policy validation.
- `gea/discovery.py`: bounded passive wildcard discovery.
- `gea/http_client.py`: curl client, rate limit, retry, error taxonomy.
- `gea/analyzer.py`: signature, baseline, provider, score, recommendation.
- `gea/scanner.py`: phases, expansion, concurrency, resume, checkpoint, aggregation.
- `gea/reporter.py`: endpoint/host reports, dashboard, comparison, explainer.
- `gea/models.py`: data model, endpoint tiers, verdict priority.
- `gea/util.py`: URL normalization, hashing, JSONL, evidence redaction.

## Adaptive decision

`best-practice` memulai Tier 1. Scanner memperluas ke tier berikutnya ketika terdapat:

- confirmed/probable signature;
- suspicious/custom response;
- in-scope redirect;
- upstream error;
- rate limit.

WAF/access-control tidak menyebabkan aggressive expansion pada best-practice. Pada `authorized-advanced`, WAF/access-control dapat memperluas paling jauh ke Phase 2 untuk mengumpulkan metadata konsistensi, tanpa evasion.

## Host aggregation

Endpoint verdict diprioritaskan sebagai berikut:

```text
valid_exposure
potential_exposure
manual_review
waf_blocked
not_exposed
unreachable
out_of_scope
```

Satu valid Git signature tidak boleh tertutup oleh endpoint 404 atau SPA fallback pada host yang sama.

## Persistence

Setiap host yang selesai langsung ditulis ke:

- `endpoint-results.jsonl`;
- `host-summary.jsonl`;
- `checkpoint.jsonl`;
- evidence directory per target.

`--resume` membaca checkpoint dan membangun ulang report dari persisted JSONL.

## Design principles

1. Status HTTP bukan bukti tunggal.
2. Signature Git dan baseline harus dapat dijelaskan.
3. Scope dievaluasi sebelum request dan pada redirect.
4. Redirect tidak diikuti otomatis.
5. Request harus bounded, rate-limited, dan resumable.
6. Evidence text selalu melalui redaction.
7. Advanced authorization tidak berarti automatic bypass.
8. Core classification harus deterministic; AI eksternal bukan dependency.

# Troubleshooting

## `No such option: -l`

Example:

```text
Usage: httpx [OPTIONS] URL
Error: No such option: -l
```

This is normally the unrelated Python HTTPX CLI, not ProjectDiscovery httpx.

Kali Linux:

```bash
sudo apt update
sudo apt install -y httpx-toolkit
httpx-toolkit -version
```

Run explicitly:

```bash
HTTPX_BIN=/usr/bin/httpx-toolkit \
  ./bin/git-exposure-auditor --domain example.com --authorized
```

The toolkit accepts `HTTPX_BIN`, `httpx-pd`, `httpx-toolkit`, common Go binary directories, and finally a compatible `httpx` command.

## `crt.sh` timeout, HTTP 502, or invalid JSON

Certificate Transparency is an external passive source and may be slow or unavailable.

Increase limits:

```bash
CRT_MAX_TIME=120 CRT_RETRIES=1 \
  ./bin/git-exposure-auditor --domain example.com --authorized
```

The failure is written to:

```text
<output>/crtsh-errors.log
```

The workflow continues with the root domain and `assetfinder` when available.

## `assetfinder is not installed`

Install with Go:

```bash
go install -v github.com/tomnomnom/assetfinder@latest
export PATH="$(go env GOPATH)/bin:$PATH"
hash -r
```

The tool can continue without it, but passive coverage may be lower.

## Scope rejection

Common messages:

```text
Requested ports are outside scope
No in-scope targets were produced
Requested threads exceed the scope maximum
```

Review:

```bash
jq . config/scope.local.json
```

Remember:

- Excludes override includes.
- `*.example.com` does not include `example.com`.
- CLI ports must appear in `allowed_ports`.
- CLI concurrency cannot exceed scope maximums.

## Zero confirmed candidates

A zero result means no tested URL/path pair met the evidence rules. Review:

```bash
jq . <output>/scan-summary.json
cat <output>/summary.md
```

Check counts for:

- `BLOCKED`.
- `REDIRECTED`.
- `SOFT_404`.
- `ERROR`.
- Reachable URL coverage.

A zero result does not prove every untested hostname, port, or nested path is safe.

## Too many planned tasks

Task count is:

```text
reachable base URLs × approved application paths
```

Reduce the target list or path file, or increase `max_tasks` only when the program permits the resulting request volume.

## TLS errors

TLS verification remains enabled. The tool does not provide an insecure mode. Investigate whether:

- The asset uses an invalid or expired certificate.
- The hostname requires a different SNI route.
- The asset is no longer active.
- The program permits testing the corresponding HTTP service.

Do not disable certificate validation merely to increase hit counts.

## Run project tests

```bash
./tests/run-tests.sh
```

A successful result is:

```text
All tests passed.
```

# Troubleshooting

## `Error: No such option: -l`

Example:

```text
Usage: httpx [OPTIONS] URL
Error: No such option: -l
```

This normally means the unrelated Python HTTPX CLI was executed instead of ProjectDiscovery httpx.

Check all matching commands:

```bash
type -a httpx
which -a httpx
```

### Kali Linux

Install and verify Kali's ProjectDiscovery package:

```bash
sudo apt update
sudo apt install -y httpx-toolkit
httpx-toolkit -version
httpx-toolkit -h | grep -F -- '-l, -list'
```

Version 1.0.2 automatically detects `httpx-toolkit`. A symlink is optional, not required.

Explicit selection is also supported:

```bash
HTTPX_BIN=/usr/bin/httpx-toolkit ./scripts/hard.sh example.com
```

### Go installation

```bash
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
export PATH="$(go env GOPATH)/bin:$PATH"
hash -r
"$(go env GOPATH)/bin/httpx" -version
```

## `crt.sh` timeout, HTTP 502, or invalid JSON

Certificate Transparency services are external dependencies and may be slow, unavailable, or rate limited.

Version 1.0.2 downloads the response to a temporary file before parsing it. This prevents truncated JSON from being streamed directly into `jq`. Failures are written to:

```text
results/<run-directory>/crtsh-errors.log
```

The workflow continues with the root domain and `assetfinder` results.

For a large Certificate Transparency response, increase the per-attempt timeout:

```bash
CRT_MAX_TIME=120 CRT_RETRIES=1 ./scripts/hard.sh example.com
```

A failed passive source does not mean the target has no subdomains. It only means that source did not provide usable data during that run.

## Confirm which binary the toolkit selected

Version 1.0.2 prints a line such as:

```text
[*] Using ProjectDiscovery httpx: /usr/bin/httpx-toolkit
```

The lookup order is:

1. `HTTPX_BIN`
2. `httpx-pd`
3. `httpx-toolkit`
4. common Go binary directories
5. `httpx`, only when its supported flags match ProjectDiscovery httpx

## Old local repository still calls Python HTTPX

Confirm the updated helper exists:

```bash
grep -n 'httpx-toolkit' scripts/common.sh
grep -n '"$HTTPX_BIN"' scripts/hard.sh
cat VERSION
```

Expected version:

```text
1.0.2
```

# Workflow Levels

The level names describe workflow complexity—not permission to become more aggressive. Every level must remain inside written scope and approved testing rules.

## Comparison

| Property | Easy | Medium | Hard | Best Practice |
|---|---:|---:|---:|---:|
| Single target | Yes | Yes | No | Yes |
| Target list | No | Yes | Generated | Yes |
| Passive discovery | No | No | Yes | Optional |
| Scope filtering | Manual | Manual | Root-domain filter | Root-domain filter in domain mode |
| Body signature check | Yes | Yes | Yes | Yes |
| Rate limiting | One request | 5 req/s | 10 req/s default | 8 req/s default, configurable |
| Structured JSONL | No | No | No | Yes |
| New-only history | No | No | No | Optional |
| Authorization gate | Documentation | Documentation | Documentation | Required CLI acknowledgement |

## Easy

### Goal

Teach the core concept through one transparent HTTP request.

### Request behavior

- One request to `/.git/HEAD`.
- No redirect following.
- TLS certificate verification remains enabled.
- Ten-second maximum request time.

### Advantages

- Easy to audit line by line.
- Lowest traffic profile.
- Best for manual report reproduction.

### Disadvantages

- No batching or discovery.
- A hostname without working HTTPS may need an explicit `http://` input.
- Does not produce structured evidence.

## Medium

### Goal

Check a curated and already authorized list.

### Request behavior

- Uses `httpx` path probing.
- Default limit: five requests per second.
- Default concurrency: ten workers.
- Matches Git-style `HEAD` content rather than status code alone.

### Advantages

- Good balance between simplicity and scale.
- Reusable input and output files.
- Lower false-positive risk than status-only pipelines.

### Disadvantages

- No automatic scope enforcement for arbitrary URLs in the file.
- The operator is responsible for ensuring every line is permitted.
- Does not create JSONL evidence.

## Hard

### Goal

Teach a broader reconnaissance pipeline while keeping probing controlled.

### Request behavior

- Queries Certificate Transparency data.
- Runs `assetfinder --subs-only <domain>` correctly with the domain as an argument.
- Removes wildcard prefixes, duplicates, and names outside the selected root domain.
- Probes only `/.git/HEAD` on configured ports.

### Advantages

- Demonstrates passive collection, normalization, scope filtering, and probing.
- Produces a host inventory for review.
- Useful for learning how tools connect in a pipeline.

### Disadvantages

- Public data sources may overlap, fail, or return stale names.
- Broader enumeration increases review time and traffic.
- Some bug-bounty programs restrict automated discovery or non-listed subdomains.

## Best Practice

### Goal

Provide a repeatable workflow suitable for careful research and documentation.

### Controls

- Requires `--authorized`.
- Accepts either one root domain or one prepared targets file.
- Preserves target-list port choices unless explicit expansion is requested.
- Validates numeric limits and domain syntax.
- Keeps concurrency and request rate bounded.
- Does not follow redirects.
- Does not dump Git objects.
- Saves metadata as JSONL without intentionally storing response bodies.
- Can track only newly observed candidates with `anew`.

### Advantages

- Strongest operational safeguards in the repository.
- Clear output for later review.
- Better reproducibility and change tracking.
- Safer defaults than a high-thread one-liner.

### Disadvantages

- More dependencies and setup.
- More code to maintain as third-party CLI flags evolve.
- An authorization flag cannot technically prove permission; the operator remains responsible.
- Results still require human scope and impact validation.

## Choosing a level

- Use **Easy** to understand the request and manually reproduce one finding.
- Use **Medium** when the program supplies an exact host list.
- Use **Hard** only when discovery of subdomains is permitted.
- Use **Best Practice** for repeatable assessments, evidence collection, and history tracking.

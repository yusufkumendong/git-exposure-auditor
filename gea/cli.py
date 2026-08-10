from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from urllib.parse import urlsplit

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from gea import __version__
    from gea.discovery import discover, wildcard_root
    from gea.http_client import HttpConfig
    from gea.policy import ProgramPolicy
    from gea.reporter import Reporter, explain_report
    from gea.scanner import ScanConfig, Scanner
    from gea.scope import ScopeEngine, normalize_host
    from gea.util import normalize_url, now_iso, sha256, write_json
else:
    from . import __version__
    from .discovery import discover, wildcard_root
    from .http_client import HttpConfig
    from .policy import ProgramPolicy
    from .reporter import Reporter, explain_report
    from .scanner import ScanConfig, Scanner
    from .scope import ScopeEngine, normalize_host
    from .util import normalize_url, now_iso, sha256, write_json

MODES = {"easy", "medium", "hard", "best-practice", "authorized-advanced", "bypass-authorized"}


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="gea",
        description="Safe, signature-aware, adaptive .git exposure validation for authorized assets.",
    )
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="command")
    explain = sub.add_parser("explain", help="Jelaskan laporan secara lokal dan deterministic")
    explain.add_argument("--report-dir", required=True)

    ap.add_argument("--mode", default="easy", choices=sorted(MODES))
    ap.add_argument("--target", action="append", default=[])
    ap.add_argument("--domain", action="append", default=[])
    ap.add_argument("--subdomain", action="append", default=[])
    ap.add_argument("--wildcard", action="append", default=[])
    ap.add_argument("--list", default="")
    ap.add_argument("--scope", dest="scope_file", default="")
    ap.add_argument("--scope-rule", action="append", default=[])
    ap.add_argument("--exclude-scope", action="append", default=[])
    ap.add_argument("--authorized", action="store_true")
    ap.add_argument("--bypass-permitted", action="store_true")
    ap.add_argument("--policy-file", default="")
    ap.add_argument("--allow-private", action="store_true")
    ap.add_argument("--scope-strict", action="store_true", help="Tolak canonical hostname yang berada di luar scope")
    ap.add_argument("--enumerator", choices=("auto", "subfinder", "crtsh", "none"), default="auto")
    ap.add_argument("--no-discover", action="store_true")
    ap.add_argument("--max-discovered", type=int, default=300)
    ap.add_argument("--scheme", choices=("https", "http", "both"), default="https")
    ap.add_argument("--concurrency", type=int)
    ap.add_argument("--rate", type=float)
    ap.add_argument("--retries", type=int)
    ap.add_argument("--retry-delay", type=float, default=1.0)
    ap.add_argument("--retry-max-delay", type=float, default=10.0)
    ap.add_argument("--no-retry-after", action="store_true")
    ap.add_argument("--connect-timeout", type=float, default=5.0)
    ap.add_argument("--max-time", type=float, default=15.0)
    ap.add_argument("--max-body-bytes", type=int, default=262_144)
    ap.add_argument("--proxy", default="")
    ap.add_argument("--header", action="append", default=[])
    ap.add_argument("--http-version", choices=("auto", "1.1", "2"), default="auto")
    ap.add_argument("--insecure", action="store_true")
    ap.add_argument("--report-dir", default="")
    ap.add_argument("--full-scan", action="store_true")
    ap.add_argument("--baseline-count", type=int, default=1)
    ap.add_argument("--max-baselines", type=int, default=3)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--checkpoint-every", type=int, default=1)
    ap.add_argument("--deduplicate-cname", action="store_true")
    ap.add_argument("--store-body", choices=("none", "snippet", "full"), default="snippet")
    ap.add_argument("--evidence-max-bytes", type=int, default=2048)
    ap.add_argument("--signature-file", default="")
    ap.add_argument("--compare-report", default="")
    ap.add_argument("--fail-on-findings", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--no-color", action="store_true")
    return ap


def split_values(values: list[str]) -> list[str]:
    output = []
    for raw in values:
        output.extend(item.strip() for item in raw.split(",") if item.strip())
    return output


def mode_defaults(args: argparse.Namespace) -> tuple[int, float, int]:
    defaults = {
        "easy": (1, 0.0, 0),
        "medium": (2, 3.0, 1),
        "hard": (5, 5.0, 1),
        "best-practice": (3, 2.0, 1),
        "authorized-advanced": (2, 2.0, 1),
        "bypass-authorized": (2, 2.0, 1),
    }
    dc, dr, dretries = defaults[args.mode]
    concurrency = args.concurrency if args.concurrency is not None else dc
    rate = args.rate if args.rate is not None else dr
    retries = args.retries if args.retries is not None else dretries
    if not 1 <= concurrency <= 20:
        raise ValueError("Concurrency harus 1-20")
    if not 0 <= rate <= 50:
        raise ValueError("Rate harus 0-50")
    if not 0 <= retries <= 5:
        raise ValueError("Retries harus 0-5")
    if args.mode in {"best-practice", "authorized-advanced", "bypass-authorized"}:
        if concurrency > 5 or rate > 5:
            raise ValueError("Mode aman: concurrency dan rate maksimal 5")
    if args.mode in {"authorized-advanced", "bypass-authorized"} and (concurrency > 3 or rate > 3):
        raise ValueError("Authorized Advanced: concurrency dan rate maksimal 3")
    return concurrency, rate, retries


def build_targets(args: argparse.Namespace, scope: ScopeEngine, user_agent: str, auto_scope: bool) -> list[str]:
    raw_targets = split_values(args.target)
    domains = split_values(args.domain)
    subdomains = split_values(args.subdomain)
    wildcards = split_values(args.wildcard)
    if auto_scope:
        for value in domains + subdomains:
            scope.add_include(value)
        for value in raw_targets:
            scope.add_include(normalize_host(value))
    candidates = [*raw_targets, *domains, *subdomains]
    if args.list:
        list_path = Path(args.list)
        if not list_path.is_file():
            raise ValueError(f"File target tidak ditemukan: {args.list}")
        list_values = [
            line.strip() for line in list_path.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        candidates.extend(list_values)
        if auto_scope:
            for value in list_values:
                scope.add_include(normalize_host(value))
    for wildcard in wildcards:
        normalized_wildcard = f"*.{wildcard_root(wildcard)}"
        if auto_scope:
            scope.add_include(normalized_wildcard)
        root = wildcard_root(wildcard)
        if not auto_scope and not scope.host_allowed(root):
            continue
        hosts = [root] if args.no_discover else discover(root, args.enumerator, user_agent)
        for host in hosts[: args.max_discovered]:
            if scope.host_allowed(host):
                candidates.append(host)
    if args.max_discovered < 1 or args.max_discovered > 2000:
        raise ValueError("--max-discovered harus 1-2000")
    if not candidates:
        raise ValueError("Berikan --target, --domain, --subdomain, --wildcard, atau --list")
    targets: list[str] = []
    seen = set()
    for raw in candidates:
        schemes = ("https", "http") if args.scheme == "both" and not raw.startswith(("http://", "https://")) else (args.scheme if args.scheme != "both" else "https",)
        for scheme in schemes:
            try:
                target = normalize_url(raw, default_scheme=scheme)
            except ValueError:
                continue
            host = urlsplit(target).hostname or ""
            if not scope.host_allowed(host):
                continue
            if target not in seen:
                seen.add(target)
                targets.append(target)
    return targets


def scan_command(args: argparse.Namespace) -> int:
    if shutil.which("curl") is None:
        raise ValueError("Dependency curl tidak ditemukan")
    advanced = args.mode in {"authorized-advanced", "bypass-authorized"}
    if args.mode == "best-practice" and not args.authorized:
        raise ValueError("Best Practice wajib memakai --authorized")
    if split_values(args.wildcard) and not args.authorized:
        raise ValueError("Wildcard wajib memakai --authorized")
    if args.allow_private and not args.authorized:
        raise ValueError("--allow-private wajib disertai --authorized")
    policy = None
    if advanced:
        if not args.authorized or not args.bypass_permitted or not args.scope_file or not args.policy_file:
            raise ValueError("Authorized Advanced wajib --authorized --bypass-permitted --scope FILE --policy-file FILE")
        policy = ProgramPolicy.from_file(args.policy_file)
    concurrency, rate, retries = mode_defaults(args)
    if not 0 < args.connect_timeout <= 120:
        raise ValueError("--connect-timeout harus >0 dan <=120 detik")
    if not 0 < args.max_time <= 300:
        raise ValueError("--max-time harus >0 dan <=300 detik")
    if not 1024 <= args.max_body_bytes <= 1_048_576:
        raise ValueError("--max-body-bytes harus 1024-1048576")
    if args.retry_delay < 0 or args.retry_max_delay < args.retry_delay:
        raise ValueError("Konfigurasi retry delay tidak valid")
    if any("\r" in header or "\n" in header or ":" not in header for header in args.header):
        raise ValueError("--header harus berbentuk 'Name: value' tanpa newline")
    scope = ScopeEngine(allow_private=args.allow_private, strict_canonical=args.scope_strict)
    if args.scope_file:
        scope.load_file(args.scope_file)
    for rule in args.scope_rule:
        scope.add_include(rule)
    for rule in args.exclude_scope:
        scope.add_exclude(rule)
    user_agent = f"Git-Exposure-Auditor/{__version__} (+authorized-security-research)"
    explicit_scope = bool(args.scope_file or args.scope_rule)
    targets = build_targets(args, scope, user_agent, auto_scope=not explicit_scope)
    if not targets:
        raise ValueError("Tidak ada target valid dan in-scope")
    if args.mode in {"best-practice", "authorized-advanced", "bypass-authorized"} and not scope.includes:
        raise ValueError("Mode ini membutuhkan scope eksplisit")
    report_dir = Path(args.report_dir or f"reports/{now_iso().replace(':', '').replace('+', '_')}")
    http = HttpConfig(
        connect_timeout=args.connect_timeout,
        max_time=args.max_time,
        max_body_bytes=args.max_body_bytes,
        retries=retries,
        retry_delay=args.retry_delay,
        retry_max_delay=args.retry_max_delay,
        respect_retry_after=not args.no_retry_after,
        insecure=args.insecure,
        proxy=args.proxy,
        http_version=args.http_version,
        user_agent=user_agent,
        headers=args.header,
        rate=rate,
    )
    metadata = {
        "version": __version__,
        "created_at": now_iso(),
        "mode": "authorized-advanced" if advanced else args.mode,
        "authorization_confirmed": bool(args.authorized),
        "bypass_permission_confirmed": bool(args.bypass_permitted),
        "automatic_evasion": False,
        "repository_dumping": False,
        "credential_testing": False,
        "scope": scope.snapshot(),
        "policy": policy.snapshot() if policy else {},
        "config": {
            "targets": len(targets), "concurrency": concurrency, "rate": rate, "retries": retries,
            "adaptive": not args.full_scan, "full_scan": args.full_scan, "store_body": args.store_body,
            "baseline_count": args.baseline_count, "max_baselines": args.max_baselines,
        },
    }
    signature_hash = ""
    if args.signature_file:
        signature_hash = sha256(Path(args.signature_file).read_bytes())
    fingerprint_payload = {
        "mode": metadata["mode"],
        "targets": sorted(targets),
        "scope": scope.snapshot(),
        "policy": policy.snapshot() if policy else {},
        "full_scan": args.full_scan,
        "baseline_count": max(1, min(args.baseline_count, 3)),
        "max_baselines": max(1, min(args.max_baselines, 3)),
        "http_version": args.http_version,
        "insecure": args.insecure,
        "max_body_bytes": args.max_body_bytes,
        "store_body": args.store_body,
        "signature_sha256": signature_hash,
        "headers_sha256": sha256(json.dumps(args.header, sort_keys=True).encode("utf-8")),
        "proxy_sha256": sha256(args.proxy.encode("utf-8")),
    }
    metadata["resume_fingerprint"] = sha256(json.dumps(fingerprint_payload, sort_keys=True).encode("utf-8"))
    existing_metadata_path = report_dir / "run-metadata.json"
    if args.resume and existing_metadata_path.exists():
        existing = json.loads(existing_metadata_path.read_text(encoding="utf-8"))
        if existing.get("resume_fingerprint") != metadata["resume_fingerprint"]:
            raise ValueError("Konfigurasi --resume berbeda dari run sebelumnya")
    if not args.resume and report_dir.exists():
        generated_files = (
            "endpoint-results.jsonl", "endpoint-results.csv", "results.jsonl", "results.csv",
            "host-summary.jsonl", "host-summary.csv", "checkpoint.jsonl", "summary.txt",
            "report.html", "hackerone-findings.md", "comparison.json", "run-metadata.json",
            "scope-snapshot.json",
        )
        for name in generated_files:
            path = report_dir / name
            if path.exists() and path.is_file():
                path.unlink()
        evidence_dir = report_dir / "evidence"
        if evidence_dir.exists():
            shutil.rmtree(evidence_dir)
    write_json(report_dir / "scope-snapshot.json", scope.snapshot())
    write_json(report_dir / "run-metadata.json", metadata)
    scanner = Scanner(
        ScanConfig(
            mode="authorized-advanced" if advanced else args.mode,
            targets=targets,
            report_dir=report_dir,
            scope=scope,
            http=http,
            concurrency=concurrency,
            adaptive=not args.full_scan,
            full_scan=args.full_scan,
            baseline_count=max(1, min(args.baseline_count, 3)),
            max_baselines=max(1, min(args.max_baselines, 3)),
            resume=args.resume,
            checkpoint_every=max(1, args.checkpoint_every),
            deduplicate_cname=args.deduplicate_cname,
            store_body=args.store_body,
            evidence_max_bytes=max(128, min(args.evidence_max_bytes, args.max_body_bytes)),
            custom_signature_file=args.signature_file,
            advanced_authorized=advanced,
            policy_snapshot=policy.snapshot() if policy else {},
        )
    )
    if not args.quiet:
        print(f"Git Exposure Auditor v{__version__}")
        print("Safe, adaptive, signature-aware .git exposure validation")
        print("Gunakan hanya pada aset dalam scope dan berizin.")
        print("Tidak melakukan repository dumping, credential testing, automatic WAF/auth bypass, brute force, atau perubahan target.")
        print(f"\nMode        : {'authorized-advanced' if advanced else args.mode}")
        print(f"Target      : {len(targets)}")
        print(f"Concurrency : {concurrency}")
        print(f"Rate        : {rate} req/s")
        print(f"Report      : {report_dir}\n")
    endpoints, hosts = scanner.run()
    Reporter(report_dir, __version__, metadata).build(endpoints, hosts, args.compare_report)
    if not args.quiet:
        for index, host in enumerate(sorted(hosts, key=lambda item: item.heuristic_score, reverse=True), 1):
            print(f"[{index:03d}] {host.verdict.upper():20} {host.heuristic_score:3d}/100 | {host.target} | {host.reason}")
        print(f"\nRingkasan : {report_dir / 'summary.txt'}")
        print(f"HTML      : {report_dir / 'report.html'}")
        print(f"HackerOne : {report_dir / 'hackerone-findings.md'}")
    if args.fail_on_findings and any(host.verdict in {"valid_exposure", "potential_exposure"} for host in hosts):
        return 10
    return 0


def main() -> int:
    ap = parser()
    args = ap.parse_args()
    try:
        if args.command == "explain":
            print(explain_report(Path(args.report_dir)), end="")
            return 0
        return scan_command(args)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

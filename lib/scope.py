#!/usr/bin/env python3
"""Scope parsing, normalization, and filtering for Git Exposure Auditor."""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import sys
from pathlib import Path
from typing import Iterable
from urllib.parse import urlsplit, urlunsplit

DOMAIN_RE = re.compile(
    r"^(?=.{1,253}\.?$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$",
    re.IGNORECASE,
)


def fail(message: str, code: int = 2) -> "None":
    print(f"[!] {message}", file=sys.stderr)
    raise SystemExit(code)


def is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def normalize_host(host: str) -> str:
    value = host.strip().rstrip(".").lower()
    if not value:
        raise ValueError("empty host")
    if is_ip(value):
        return value
    try:
        value = value.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValueError(f"invalid IDN host: {host}") from exc
    if not DOMAIN_RE.fullmatch(value):
        raise ValueError(f"invalid hostname: {host}")
    return value


def normalize_domain(value: str) -> str:
    raw = value.strip()
    if "://" in raw:
        parsed = urlsplit(raw)
        raw = parsed.hostname or ""
    else:
        raw = raw.split("/", 1)[0]
        if raw.count(":") == 1 and not is_ip(raw):
            raw = raw.split(":", 1)[0]
    return normalize_host(raw)


def pattern_matches(host: str, pattern: str) -> bool:
    pattern = pattern.strip().lower().rstrip(".")
    if pattern.startswith("*."):
        suffix = normalize_host(pattern[2:])
        return host.endswith("." + suffix) and host != suffix
    return host == normalize_host(pattern)


def load_scope(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"Scope file not found: {path}")
    except json.JSONDecodeError as exc:
        fail(f"Scope file is not valid JSON: {exc}")

    if not isinstance(data, dict):
        fail("Scope file must contain a JSON object.")
    if data.get("authorized") is not True:
        fail("Scope file must contain \"authorized\": true.")

    include = data.get("include")
    if not isinstance(include, list) or not include:
        fail("Scope file must contain a non-empty include array.")
    exclude = data.get("exclude", [])
    if not isinstance(exclude, list):
        fail("Scope exclude must be an array.")

    for key, values in (("include", include), ("exclude", exclude)):
        for value in values:
            if not isinstance(value, str) or not value.strip():
                fail(f"Every {key} entry must be a non-empty string.")
            candidate = value[2:] if value.startswith("*.") else value
            try:
                normalize_host(candidate)
            except ValueError as exc:
                fail(str(exc))

    ports = data.get("allowed_ports", ["http:80", "https:443"])
    if not isinstance(ports, list) or not ports:
        fail("allowed_ports must be a non-empty array.")
    port_re = re.compile(r"^(?:http|https):(?:[1-9][0-9]{0,4})$")
    for entry in ports:
        if not isinstance(entry, str) or not port_re.fullmatch(entry):
            fail(f"Invalid allowed_ports entry: {entry!r}")
        port = int(entry.rsplit(":", 1)[1])
        if port > 65535:
            fail(f"Port out of range: {entry}")

    for numeric_key, default, maximum in (
        ("max_threads", 20, 50),
        ("max_rate_limit", 10, 50),
        ("max_tasks", 10000, 50000),
        ("max_response_bytes", 65536, 262144),
    ):
        value = data.get(numeric_key, default)
        if not isinstance(value, int) or value < 1 or value > maximum:
            fail(f"{numeric_key} must be an integer from 1 to {maximum}.")

    paths = data.get("application_paths", ["/"])
    if not isinstance(paths, list) or not paths:
        fail("application_paths must be a non-empty array.")
    for entry in paths:
        normalize_path(entry)

    return data




def effective_port(scheme: str, port: int | None) -> int:
    if port is not None:
        return port
    return 443 if scheme.lower() == "https" else 80


def port_spec_allowed(scheme: str, port: int | None, scope: dict) -> bool:
    spec = f"{scheme.lower()}:{effective_port(scheme, port)}"
    return spec in set(scope.get("allowed_ports", []))


def target_port_specs(value: str) -> set[str]:
    raw = value.strip()
    if "://" in raw:
        parsed = urlsplit(raw)
        if parsed.scheme.lower() not in {"http", "https"}:
            raise ValueError(f"unsupported URL scheme: {parsed.scheme}")
        return {f"{parsed.scheme.lower()}:{effective_port(parsed.scheme, parsed.port)}"}
    parsed = urlsplit("//" + raw)
    if parsed.port is not None:
        return {f"http:{parsed.port}", f"https:{parsed.port}"}
    return {"http:80", "https:443"}

def host_in_scope(host: str, scope: dict) -> bool:
    normalized = normalize_host(host)
    included = any(pattern_matches(normalized, p) for p in scope["include"])
    excluded = any(pattern_matches(normalized, p) for p in scope.get("exclude", []))
    return included and not excluded


def normalize_target(line: str) -> tuple[str, str]:
    value = line.strip()
    if not value or value.startswith("#"):
        raise ValueError("skip")

    if "://" not in value:
        candidate = urlsplit("//" + value)
        host = candidate.hostname
        if not host:
            raise ValueError(f"invalid target: {value}")
        normalized_host = normalize_host(host)
        netloc = normalized_host
        if candidate.port:
            netloc = f"{normalized_host}:{candidate.port}"
        path = candidate.path or ""
        normalized = netloc + path.rstrip("/")
        return normalized, normalized_host

    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError(f"unsupported URL scheme: {parsed.scheme}")
    if parsed.username or parsed.password:
        raise ValueError("targets containing URL credentials are not allowed")
    if not parsed.hostname:
        raise ValueError(f"invalid target URL: {value}")
    host = normalize_host(parsed.hostname)
    netloc = host
    if parsed.port:
        netloc = f"{host}:{parsed.port}"
    path = parsed.path or ""
    if ".." in path.split("/"):
        raise ValueError("target paths containing '..' are not allowed")
    normalized = urlunsplit((parsed.scheme.lower(), netloc, path.rstrip("/"), "", ""))
    return normalized, host


def normalize_path(value: str) -> str:
    path = value.strip()
    if not path:
        raise ValueError("empty application path")
    if not path.startswith("/"):
        path = "/" + path
    if "?" in path or "#" in path:
        raise ValueError("application paths may not contain query strings or fragments")
    segments = [segment for segment in path.split("/") if segment]
    if any(segment in {".", ".."} for segment in segments):
        raise ValueError("application paths may not contain '.' or '..' segments")
    normalized = "/" + "/".join(segments)
    return normalized if normalized != "" else "/"


def read_lines(path: Path) -> Iterable[str]:
    try:
        yield from path.read_text(encoding="utf-8", errors="replace").splitlines()
    except FileNotFoundError:
        fail(f"Input file not found: {path}")


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def cmd_validate(args: argparse.Namespace) -> None:
    scope = load_scope(Path(args.scope))
    print(json.dumps(scope, sort_keys=True))


def cmd_normalize_domain(args: argparse.Namespace) -> None:
    print(normalize_domain(args.domain))


def cmd_derive_domain(args: argparse.Namespace) -> None:
    domain = normalize_domain(args.domain)
    ports = [p.strip() for p in args.ports.split(",") if p.strip()]
    data = {
        "program": args.program or "ad-hoc-domain-assessment",
        "authorized": True,
        "include": [domain, f"*.{domain}"],
        "exclude": [],
        "allowed_ports": ports,
        "application_paths": ["/"],
        "max_threads": args.max_threads,
        "max_rate_limit": args.max_rate_limit,
        "max_tasks": args.max_tasks,
        "max_response_bytes": args.max_response_bytes,
    }
    write_json(Path(args.output), data)
    print(domain)


def cmd_derive_targets(args: argparse.Namespace) -> None:
    hosts: set[str] = set()
    discovered_ports: set[str] = set()
    for line in read_lines(Path(args.targets)):
        try:
            _, host = normalize_target(line)
            discovered_ports.update(target_port_specs(line))
        except ValueError as exc:
            if str(exc) == "skip":
                continue
            fail(str(exc))
        hosts.add(host)
    if not hosts:
        fail("No usable targets were found.")
    ports = [p.strip() for p in args.ports.split(",") if p.strip()] or sorted(discovered_ports)
    data = {
        "program": args.program or "ad-hoc-target-list-assessment",
        "authorized": True,
        "include": sorted(hosts),
        "exclude": [],
        "allowed_ports": ports or ["http:80", "https:443"],
        "application_paths": ["/"],
        "max_threads": args.max_threads,
        "max_rate_limit": args.max_rate_limit,
        "max_tasks": args.max_tasks,
        "max_response_bytes": args.max_response_bytes,
    }
    write_json(Path(args.output), data)
    print(len(hosts))


def cmd_filter_hosts(args: argparse.Namespace) -> None:
    scope = load_scope(Path(args.scope))
    output: set[str] = set()
    rejected = 0
    for line in read_lines(Path(args.input)):
        raw = line.strip().lower().lstrip("*.").rstrip(".")
        if not raw or raw.startswith("#"):
            continue
        try:
            host = normalize_host(raw)
        except ValueError:
            rejected += 1
            continue
        if host_in_scope(host, scope):
            output.add(host)
        else:
            rejected += 1
    Path(args.output).write_text("".join(f"{h}\n" for h in sorted(output)), encoding="utf-8")
    print(json.dumps({"accepted": len(output), "rejected": rejected}))


def cmd_filter_targets(args: argparse.Namespace) -> None:
    scope = load_scope(Path(args.scope))
    output: set[str] = set()
    rejected = 0
    for line in read_lines(Path(args.input)):
        try:
            target, host = normalize_target(line)
        except ValueError as exc:
            if str(exc) == "skip":
                continue
            rejected += 1
            continue
        try:
            requested_specs = target_port_specs(line)
        except ValueError:
            rejected += 1
            continue
        allowed_specs = set(scope.get("allowed_ports", []))
        permitted_specs = sorted(requested_specs.intersection(allowed_specs))
        if not host_in_scope(host, scope) or not permitted_specs:
            rejected += 1
            continue

        raw = line.strip()
        if "://" in raw:
            output.add(target)
            continue

        parsed = urlsplit("//" + raw)
        path = (parsed.path or "").rstrip("/")
        for spec in permitted_specs:
            scheme, port_text = spec.split(":", 1)
            port = int(port_text)
            default_port = 443 if scheme == "https" else 80
            netloc = host if port == default_port else f"{host}:{port}"
            output.add(urlunsplit((scheme, netloc, path, "", "")))
    Path(args.output).write_text("".join(f"{t}\n" for t in sorted(output)), encoding="utf-8")
    print(json.dumps({"accepted": len(output), "rejected": rejected}))


def cmd_paths(args: argparse.Namespace) -> None:
    scope = load_scope(Path(args.scope))
    candidates: list[str] = []
    if args.input:
        for line in read_lines(Path(args.input)):
            value = line.strip()
            if not value or value.startswith("#"):
                continue
            candidates.append(value)
    else:
        candidates.extend(scope.get("application_paths", ["/"]))

    normalized: set[str] = set()
    for value in candidates:
        try:
            normalized.add(normalize_path(value))
        except ValueError as exc:
            fail(str(exc))
    if not normalized:
        fail("No usable application paths were produced.")
    if len(normalized) > args.max_paths:
        fail(f"Application path count exceeds the limit of {args.max_paths}.")
    Path(args.output).write_text("".join(f"{p}\n" for p in sorted(normalized)), encoding="utf-8")
    print(len(normalized))


def cmd_check_ports(args: argparse.Namespace) -> None:
    scope = load_scope(Path(args.scope))
    requested = [p.strip() for p in args.ports.split(",") if p.strip()]
    allowed = set(scope.get("allowed_ports", []))
    disallowed = [p for p in requested if p not in allowed]
    if disallowed:
        fail("Requested ports are outside scope: " + ", ".join(disallowed))
    print(",".join(requested))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate")
    p.add_argument("--scope", required=True)
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("normalize-domain")
    p.add_argument("--domain", required=True)
    p.set_defaults(func=cmd_normalize_domain)

    p = sub.add_parser("derive-domain")
    p.add_argument("--domain", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--ports", default="http:80,https:443")
    p.add_argument("--program")
    p.add_argument("--max-threads", type=int, default=20)
    p.add_argument("--max-rate-limit", type=int, default=10)
    p.add_argument("--max-tasks", type=int, default=10000)
    p.add_argument("--max-response-bytes", type=int, default=65536)
    p.set_defaults(func=cmd_derive_domain)

    p = sub.add_parser("derive-targets")
    p.add_argument("--targets", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--ports", default="")
    p.add_argument("--program")
    p.add_argument("--max-threads", type=int, default=20)
    p.add_argument("--max-rate-limit", type=int, default=10)
    p.add_argument("--max-tasks", type=int, default=10000)
    p.add_argument("--max-response-bytes", type=int, default=65536)
    p.set_defaults(func=cmd_derive_targets)

    p = sub.add_parser("filter-hosts")
    p.add_argument("--scope", required=True)
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_filter_hosts)

    p = sub.add_parser("filter-targets")
    p.add_argument("--scope", required=True)
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_filter_targets)

    p = sub.add_parser("paths")
    p.add_argument("--scope", required=True)
    p.add_argument("--input")
    p.add_argument("--output", required=True)
    p.add_argument("--max-paths", type=int, default=50)
    p.set_defaults(func=cmd_paths)

    p = sub.add_parser("check-ports")
    p.add_argument("--scope", required=True)
    p.add_argument("--ports", required=True)
    p.set_defaults(func=cmd_check_ports)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

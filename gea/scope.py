from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


def normalize_host(raw: str) -> str:
    value = raw.strip().lower()
    if value.startswith(("http://", "https://")):
        value = urlsplit(value).hostname or ""
    elif value.startswith("[") and "]" in value:
        value = value[1 : value.index("]")]
    elif value.count(":") <= 1:
        value = value.split("/", 1)[0].split(":", 1)[0]
    return value.rstrip(".").encode("idna").decode("ascii") if value else ""


def normalize_rule(raw: str) -> str:
    value = raw.strip()
    if value.startswith("!"):
        value = value[1:].strip()
    wildcard = value.startswith("*.")
    host = normalize_host(value[2:] if wildcard else value)
    return f"*.{host}" if wildcard and host else host


def rule_matches(host: str, rule: str) -> bool:
    host = normalize_host(host)
    rule = normalize_rule(rule)
    if rule.startswith("*."):
        suffix = rule[2:]
        return host == suffix or host.endswith("." + suffix)
    return host == rule


def resolve_host(host: str) -> tuple[list[str], str]:
    host = normalize_host(host)
    try:
        ipaddress.ip_address(host)
        return [host], host
    except ValueError:
        pass
    infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    ips = sorted({item[4][0] for item in infos})
    canonical = next((item[3] for item in infos if item[3]), host).rstrip(".").lower()
    return ips, canonical


def ip_is_private_or_reserved(value: str) -> bool:
    ip = ipaddress.ip_address(value)
    return any(
        (
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_reserved,
            ip.is_unspecified,
            ip.is_multicast,
        )
    )


@dataclass(slots=True)
class ScopeDecision:
    allowed: bool
    reason: str
    ips: list[str] = field(default_factory=list)
    canonical_name: str = ""


@dataclass(slots=True)
class ScopeEngine:
    includes: list[str] = field(default_factory=list)
    excludes: list[str] = field(default_factory=list)
    allow_private: bool = False
    strict_canonical: bool = False

    def add_include(self, value: str) -> None:
        rule = normalize_rule(value)
        if rule and rule not in self.includes:
            self.includes.append(rule)

    def add_exclude(self, value: str) -> None:
        rule = normalize_rule(value)
        if rule and rule not in self.excludes:
            self.excludes.append(rule)

    def load_file(self, path: str) -> None:
        file_path = Path(path)
        if not file_path.is_file():
            raise ValueError(f"File scope tidak ditemukan: {path}")
        for raw in file_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            lower = line.lower()
            if lower.startswith("exclude "):
                self.add_exclude(line.split(None, 1)[1])
            elif lower.startswith("include "):
                self.add_include(line.split(None, 1)[1])
            elif line.startswith("!"):
                self.add_exclude(line[1:])
            else:
                self.add_include(line)

    def host_allowed(self, host: str) -> bool:
        normalized = normalize_host(host)
        if any(rule_matches(normalized, rule) for rule in self.excludes):
            return False
        if not self.includes:
            return True
        return any(rule_matches(normalized, rule) for rule in self.includes)

    def validate_host(self, host: str, resolve: bool = True) -> ScopeDecision:
        normalized = normalize_host(host)
        if not normalized:
            return ScopeDecision(False, "Hostname tidak valid")
        if not self.host_allowed(normalized):
            return ScopeDecision(False, "Hostname berada di luar scope")
        if not resolve:
            return ScopeDecision(True, "Hostname berada dalam scope")
        try:
            ips, canonical = resolve_host(normalized)
        except socket.gaierror:
            return ScopeDecision(True, "DNS tidak memiliki record", [], normalized)
        except OSError as exc:
            return ScopeDecision(True, f"DNS error: {exc}", [], normalized)
        private_ips = [ip for ip in ips if ip_is_private_or_reserved(ip)]
        if private_ips and not self.allow_private:
            return ScopeDecision(False, f"Resolve ke private/reserved IP: {', '.join(private_ips)}", ips, canonical)
        if self.strict_canonical and canonical and canonical != normalized and not self.host_allowed(canonical):
            return ScopeDecision(False, f"Canonical hostname di luar scope: {canonical}", ips, canonical)
        return ScopeDecision(True, "Scope dan IP valid", ips, canonical)

    def redirect_allowed(self, location: str, base_url: str) -> tuple[bool, str]:
        from urllib.parse import urljoin

        destination = urljoin(base_url.rstrip("/") + "/", location)
        parsed = urlsplit(destination)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False, "Tujuan redirect tidak valid"
        decision = self.validate_host(parsed.hostname, resolve=True)
        return decision.allowed, decision.reason

    def snapshot(self) -> dict[str, object]:
        return {
            "include": sorted(self.includes),
            "exclude": sorted(self.excludes),
            "allow_private": self.allow_private,
            "strict_canonical": self.strict_canonical,
        }

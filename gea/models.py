from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

TIER_1 = ("/.git/HEAD", "/.git/config")
TIER_2 = ("/.git/packed-refs", "/.git/logs/HEAD")
TIER_3 = (
    "/.git/refs/heads/main",
    "/.git/refs/heads/master",
    "/.git/index",
    "/.git/objects/info/packs",
)
ALL_ENDPOINTS = TIER_1 + TIER_2 + TIER_3

VERDICT_PRIORITY = {
    "valid_exposure": 700,
    "potential_exposure": 600,
    "manual_review": 500,
    "waf_blocked": 400,
    "not_exposed": 300,
    "unreachable": 200,
    "out_of_scope": 100,
}

CLASS_TO_VERDICT = {
    "confirmed_exposure": "valid_exposure",
    "probable_exposure": "potential_exposure",
    "suspicious": "manual_review",
    "custom_error": "manual_review",
    "redirect_in_scope": "manual_review",
    "upstream_error": "manual_review",
    "rate_limited": "manual_review",
    "waf_challenge": "waf_blocked",
    "access_control_detected": "waf_blocked",
    "soft_404": "not_exposed",
    "spa_fallback": "not_exposed",
    "protected": "not_exposed",
    "not_exposed": "not_exposed",
    "redirect_out_of_scope": "out_of_scope",
    "dns_error": "unreachable",
    "dns_no_record": "unreachable",
    "connect_timeout": "unreachable",
    "read_timeout": "unreachable",
    "tls_error": "unreachable",
    "tls_hostname_mismatch": "unreachable",
    "connection_refused": "unreachable",
    "connection_reset": "unreachable",
    "proxy_error": "unreachable",
    "unsupported_protocol": "unreachable",
    "redirect_loop": "manual_review",
    "body_too_large": "manual_review",
    "network_error": "unreachable",
}


@dataclass(slots=True)
class EvidencePoint:
    factor: str
    points: int
    detail: str


@dataclass(slots=True)
class HttpResponse:
    url: str
    status: int = 0
    effective_url: str = ""
    content_type: str = ""
    size_bytes: int = 0
    time_seconds: float = 0.0
    remote_ip: str = ""
    http_version: str = ""
    curl_rc: int = 0
    retries: int = 0
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    error: str = ""
    network_error: str = ""


@dataclass(slots=True)
class EndpointResult:
    timestamp: str
    target: str
    host: str
    endpoint: str
    phase: int
    status: str
    classification: str
    verdict: str
    heuristic_score: int
    confidence_level: str
    reason: str
    recommendation: str
    provider_hint: str
    similarity: float
    baseline_consistency: float
    content_type: str
    size_bytes: int
    time_seconds: float
    remote_ip: str
    http_version: str
    curl_rc: int
    retries: int
    network_error: str
    effective_url: str
    location: str
    body_sha256: str
    baseline_sha256: list[str]
    evidence: list[EvidencePoint] = field(default_factory=list)
    redacted_snippet: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data


@dataclass(slots=True)
class HostSummary:
    timestamp: str
    target: str
    host: str
    verdict: str
    confidence_level: str
    heuristic_score: int
    reason: str
    recommendation: str
    provider_hint: str
    requests: int
    baseline_requests: int
    endpoint_requests: int
    planned_endpoint_requests: int
    saved_endpoint_requests: int
    phases_run: list[int]
    endpoint_counts: dict[str, int]
    status_counts: dict[str, int]
    network_error_counts: dict[str, int]
    evidence_endpoints: list[str]
    completed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

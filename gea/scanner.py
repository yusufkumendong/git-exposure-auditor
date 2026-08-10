from __future__ import annotations

import json
import os
import socket
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from .analyzer import analyze, load_custom_signatures, similarity
from .http_client import CurlClient, HttpConfig
from .models import ALL_ENDPOINTS, TIER_1, TIER_2, TIER_3, VERDICT_PRIORITY, EndpointResult, EvidencePoint, HostSummary
from .scope import ScopeEngine, normalize_host
from .util import append_jsonl, now_iso, random_token, safe_name, write_json


@dataclass(slots=True)
class ScanConfig:
    mode: str
    targets: list[str]
    report_dir: Path
    scope: ScopeEngine
    http: HttpConfig
    concurrency: int = 1
    adaptive: bool = True
    full_scan: bool = False
    baseline_count: int = 1
    max_baselines: int = 3
    resume: bool = False
    checkpoint_every: int = 1
    deduplicate_cname: bool = False
    store_body: str = "snippet"
    evidence_max_bytes: int = 2048
    custom_signature_file: str = ""
    advanced_authorized: bool = False
    policy_snapshot: dict[str, object] = field(default_factory=dict)


class Scanner:
    def __init__(self, config: ScanConfig) -> None:
        self.config = config
        self.client = CurlClient(config.http)
        self.custom_signatures = load_custom_signatures(config.custom_signature_file)
        self.endpoint_file = config.report_dir / "endpoint-results.jsonl"
        self.host_file = config.report_dir / "host-summary.jsonl"
        self.checkpoint_file = config.report_dir / "checkpoint.jsonl"
        self.write_lock = threading.Lock()
        self.completed = self._load_completed()
        self.persisted_count = 0

    def _load_completed(self) -> set[str]:
        completed: set[str] = set()
        if not self.config.resume or not self.checkpoint_file.exists():
            return completed
        for line in self.checkpoint_file.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("completed") and item.get("target"):
                completed.add(str(item["target"]))
        return completed

    def run(self) -> tuple[list[EndpointResult], list[HostSummary]]:
        self.config.report_dir.mkdir(parents=True, exist_ok=True)
        if not self.config.resume:
            for path in (self.endpoint_file, self.host_file, self.checkpoint_file):
                path.write_text("", encoding="utf-8")
        targets = self._deduplicate_targets(self.config.targets)
        targets = [target for target in targets if target not in self.completed]
        endpoint_results: list[EndpointResult] = []
        host_summaries: list[HostSummary] = []
        with ThreadPoolExecutor(max_workers=self.config.concurrency) as executor:
            futures = {executor.submit(self.scan_target, target): target for target in targets}
            for future in as_completed(futures):
                target = futures[future]
                try:
                    results, summary = future.result()
                except Exception as exc:  # isolate one host failure from the rest of the run
                    parsed = urlsplit(target)
                    host = normalize_host(parsed.hostname or "")
                    summary = HostSummary(
                        timestamp=now_iso(), target=target, host=host, verdict="unreachable",
                        confidence_level="LOW", heuristic_score=0,
                        reason=f"Internal scanner error: {type(exc).__name__}: {exc}",
                        recommendation="Tinjau log lokal dan ulangi hanya host ini setelah penyebab diperbaiki.",
                        provider_hint="unknown", requests=0, baseline_requests=0, endpoint_requests=0,
                        planned_endpoint_requests=self._planned_endpoint_requests(),
                        saved_endpoint_requests=self._planned_endpoint_requests(), phases_run=[],
                        endpoint_counts={}, status_counts={}, network_error_counts={"internal_error": 1},
                        evidence_endpoints=[], completed=True,
                    )
                    results = []
                endpoint_results.extend(results)
                host_summaries.append(summary)
                self._persist_host(results, summary)
        return self._load_persisted_results()


    def _load_persisted_results(self) -> tuple[list[EndpointResult], list[HostSummary]]:
        endpoints: list[EndpointResult] = []
        hosts: list[HostSummary] = []
        if self.endpoint_file.exists():
            for line in self.endpoint_file.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                    item["evidence"] = [EvidencePoint(**point) for point in item.get("evidence", [])]
                    endpoints.append(EndpointResult(**item))
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue
        if self.host_file.exists():
            for line in self.host_file.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.strip():
                    try:
                        hosts.append(HostSummary(**json.loads(line)))
                    except (json.JSONDecodeError, TypeError, ValueError):
                        continue
        return endpoints, hosts

    def _deduplicate_targets(self, targets: list[str]) -> list[str]:
        seen: set[tuple[str, str, int | None]] = set()
        output: list[str] = []
        for target in targets:
            parsed = urlsplit(target)
            host = normalize_host(parsed.hostname or "")
            key_host = host
            if self.config.deduplicate_cname:
                try:
                    key_host = socket.gethostbyname_ex(host)[0].rstrip(".").lower()
                except OSError:
                    key_host = host
            key = (parsed.scheme, key_host, parsed.port)
            if key in seen:
                continue
            seen.add(key)
            output.append(target)
        return output

    def _persist_host(self, results: list[EndpointResult], summary: HostSummary) -> None:
        with self.write_lock:
            for result in results:
                append_jsonl(self.endpoint_file, result.to_dict())
            append_jsonl(self.host_file, summary.to_dict())
            append_jsonl(self.checkpoint_file, {"target": summary.target, "completed": True, "timestamp": summary.timestamp})
            self.persisted_count += 1
            if self.persisted_count % max(1, self.config.checkpoint_every) == 0:
                for path in (self.endpoint_file, self.host_file, self.checkpoint_file):
                    with path.open("a", encoding="utf-8") as handle:
                        handle.flush()
                        os.fsync(handle.fileno())
        evidence_dir = self.config.report_dir / "evidence" / safe_name(summary.target)
        write_json(evidence_dir / "summary.json", summary.to_dict())
        metadata = []
        for result in results:
            item = result.to_dict()
            snippet = item.pop("redacted_snippet", "")
            metadata.append(item)
            if snippet and self.config.store_body in {"snippet", "full"}:
                suffix = result.endpoint.strip("/").replace("/", "_") or "root"
                (evidence_dir / f"{suffix}.redacted.txt").write_text(snippet, encoding="utf-8")
        with (evidence_dir / "response-metadata.jsonl").open("w", encoding="utf-8") as handle:
            for item in metadata:
                handle.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")

    def prepare_baselines(self, target: str) -> list:
        baselines = []
        minimum = max(1, self.config.baseline_count)
        for index in range(minimum):
            baselines.append(self.client.request(f"{target}/.gea-baseline-{random_token()}-{index}"))
        if len(baselines) == 1:
            first = baselines[0]
            html_like = "text/html" in first.content_type.lower() or b"<html" in first.body.lower()
            if self.config.mode in {"hard", "best-practice", "authorized-advanced"} and (html_like or first.status in range(200, 400)):
                baselines.append(self.client.request(f"{target}/.well-known/gea-{random_token()}"))
        if len(baselines) >= 2 and len(baselines) < self.config.max_baselines:
            if similarity(baselines[0].body, baselines[1].body) < 0.80:
                baselines.append(self.client.request(f"{target}/gea-{random_token()}/.git/HEAD"))
        return baselines[: self.config.max_baselines]

    def scan_target(self, target: str) -> tuple[list[EndpointResult], HostSummary]:
        parsed = urlsplit(target)
        host = normalize_host(parsed.hostname or "")
        decision = self.config.scope.validate_host(host, resolve=True)
        if not decision.allowed:
            summary = HostSummary(
                timestamp=now_iso(), target=target, host=host, verdict="out_of_scope", confidence_level="HIGH",
                heuristic_score=100, reason=decision.reason, recommendation="Target dilewati sebelum request.",
                provider_hint="unknown", requests=0, baseline_requests=0, endpoint_requests=0,
                planned_endpoint_requests=self._planned_endpoint_requests(), saved_endpoint_requests=self._planned_endpoint_requests(),
                phases_run=[], endpoint_counts={}, status_counts={},
                network_error_counts={}, evidence_endpoints=[], completed=True,
            )
            return [], summary
        baselines = self.prepare_baselines(target)
        results: list[EndpointResult] = []
        phases_run: list[int] = []
        phase_plan = self._phase_plan()
        for phase, endpoints in phase_plan:
            phases_run.append(phase)
            for endpoint in endpoints:
                response = self.client.request(target + endpoint)
                result = analyze(
                    target=target,
                    host=host,
                    endpoint=endpoint,
                    phase=phase,
                    response=response,
                    baselines=baselines,
                    scope=self.config.scope,
                    custom_signatures=self.custom_signatures,
                    advanced_authorized=self.config.advanced_authorized,
                    store_snippet=self.config.store_body in {"snippet", "full"},
                    snippet_bytes=self.config.evidence_max_bytes if self.config.store_body == "snippet" else self.config.http.max_body_bytes,
                )
                results.append(result)
            if not self._should_expand(phase, results):
                break
        summary = self.aggregate(target, host, results, phases_run, len(baselines))
        return results, summary

    def _phase_plan(self) -> list[tuple[int, tuple[str, ...]]]:
        if self.config.mode == "easy":
            return [(1, ("/.git/HEAD",))]
        if self.config.mode == "medium":
            return [(1, ("/.git/HEAD", "/.git/config", "/.git/packed-refs"))]
        if self.config.full_scan or self.config.mode == "hard":
            return [(1, TIER_1), (2, TIER_2), (3, TIER_3)]
        return [(1, TIER_1), (2, TIER_2), (3, TIER_3)]

    def _should_expand(self, phase: int, results: list[EndpointResult]) -> bool:
        if self.config.full_scan or self.config.mode == "hard":
            return phase < 3
        if self.config.mode in {"easy", "medium"}:
            return False
        current = [item for item in results if item.phase == phase]
        interesting = {
            "confirmed_exposure", "probable_exposure", "suspicious", "custom_error",
            "redirect_in_scope", "upstream_error", "rate_limited",
        }
        if any(item.classification in interesting for item in current):
            return phase < 3
        if self.config.advanced_authorized and any(item.classification in {"waf_challenge", "access_control_detected"} for item in current):
            return phase < 2
        return False

    def _planned_endpoint_requests(self) -> int:
        if self.config.mode == "easy":
            return 1
        if self.config.mode == "medium":
            return 3
        return len(ALL_ENDPOINTS)

    def aggregate(self, target: str, host: str, results: list[EndpointResult], phases_run: list[int], baseline_requests: int) -> HostSummary:
        if not results:
            return HostSummary(
                timestamp=now_iso(), target=target, host=host, verdict="unreachable", confidence_level="LOW",
                heuristic_score=0, reason="Tidak ada endpoint result", recommendation="Periksa target dan konfigurasi.",
                provider_hint="unknown", requests=baseline_requests, baseline_requests=baseline_requests, endpoint_requests=0,
                planned_endpoint_requests=self._planned_endpoint_requests(), saved_endpoint_requests=self._planned_endpoint_requests(),
                phases_run=phases_run, endpoint_counts={}, status_counts={},
                network_error_counts={}, evidence_endpoints=[], completed=True,
            )
        best = max(results, key=lambda item: (VERDICT_PRIORITY.get(item.verdict, 0), item.heuristic_score))
        classification_counts = Counter(item.classification for item in results)
        status_counts = Counter(item.status for item in results)
        network_counts = Counter(item.network_error for item in results if item.network_error)
        provider_counts = Counter(item.provider_hint for item in results if item.provider_hint != "unknown")
        provider = provider_counts.most_common(1)[0][0] if provider_counts else "unknown"
        evidence_endpoints = [item.endpoint for item in results if item.verdict in {"valid_exposure", "potential_exposure", "manual_review"}]
        return HostSummary(
            timestamp=now_iso(),
            target=target,
            host=host,
            verdict=best.verdict,
            confidence_level=best.confidence_level,
            heuristic_score=best.heuristic_score,
            reason=best.reason,
            recommendation=best.recommendation,
            provider_hint=provider,
            requests=len(results) + baseline_requests,
            baseline_requests=baseline_requests,
            endpoint_requests=len(results),
            planned_endpoint_requests=self._planned_endpoint_requests(),
            saved_endpoint_requests=max(0, self._planned_endpoint_requests() - len(results)),
            phases_run=phases_run,
            endpoint_counts=dict(sorted(classification_counts.items())),
            status_counts=dict(sorted(status_counts.items())),
            network_error_counts=dict(sorted(network_counts.items())),
            evidence_endpoints=evidence_endpoints,
            completed=True,
        )

from __future__ import annotations

import csv
import html
import json
from collections import Counter
from pathlib import Path
from .models import VERDICT_PRIORITY, EndpointResult, HostSummary
from .util import now_iso, write_json


class Reporter:
    def __init__(self, report_dir: Path, version: str, metadata: dict[str, object]) -> None:
        self.report_dir = report_dir
        self.version = version
        self.metadata = metadata

    def build(self, endpoints: list[EndpointResult], hosts: list[HostSummary], compare_report: str = "") -> None:
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self._endpoint_csv(endpoints)
        self._host_csv(hosts)
        (self.report_dir / "results.jsonl").write_bytes((self.report_dir / "endpoint-results.jsonl").read_bytes() if (self.report_dir / "endpoint-results.jsonl").exists() else b"")
        (self.report_dir / "results.csv").write_bytes((self.report_dir / "endpoint-results.csv").read_bytes())
        self._summary(endpoints, hosts)
        self._markdown(endpoints, hosts)
        self._html(endpoints, hosts)
        write_json(self.report_dir / "run-metadata.json", self.metadata)
        if compare_report:
            self._comparison(hosts, Path(compare_report))

    def _endpoint_csv(self, endpoints: list[EndpointResult]) -> None:
        fields = [
            "timestamp", "target", "host", "endpoint", "phase", "status", "classification", "verdict",
            "heuristic_score", "confidence_level", "provider_hint", "similarity", "baseline_consistency",
            "content_type", "size_bytes", "time_seconds", "http_version", "retries", "network_error",
            "location", "reason", "recommendation", "body_sha256",
        ]
        with (self.report_dir / "endpoint-results.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for item in endpoints:
                writer.writerow(item.to_dict())

    def _host_csv(self, hosts: list[HostSummary]) -> None:
        fields = [
            "timestamp", "target", "host", "verdict", "confidence_level", "heuristic_score", "reason",
            "recommendation", "provider_hint", "requests", "baseline_requests", "endpoint_requests",
            "planned_endpoint_requests", "saved_endpoint_requests", "phases_run", "endpoint_counts", "status_counts",
            "network_error_counts", "evidence_endpoints", "completed",
        ]
        with (self.report_dir / "host-summary.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for item in hosts:
                row = item.to_dict()
                for key in ("phases_run", "endpoint_counts", "status_counts", "network_error_counts", "evidence_endpoints"):
                    row[key] = json.dumps(row[key], ensure_ascii=False, separators=(",", ":"))
                writer.writerow(row)

    def _summary(self, endpoints: list[EndpointResult], hosts: list[HostSummary]) -> None:
        verdicts = Counter(item.verdict for item in hosts)
        classes = Counter(item.classification for item in endpoints)
        statuses = Counter(item.status for item in endpoints)
        network = Counter(item.network_error for item in endpoints if item.network_error)
        providers = Counter(item.provider_hint for item in endpoints)
        lines = [
            f"Git Exposure Auditor v{self.version} - Ringkasan",
            f"Dibuat: {now_iso()}",
            "",
            f"Total host: {len(hosts)}",
            f"Total endpoint request: {len(endpoints)}",
            f"Total baseline request: {sum(item.baseline_requests for item in hosts)}",
            f"Total request aktual: {sum(item.requests for item in hosts)}",
            f"Endpoint request dihemat: {sum(item.saved_endpoint_requests for item in hosts)}",
            "",
            "Verdict host:",
        ]
        lines += [f"  {key}: {value} host" for key, value in sorted(verdicts.items())]
        lines += ["", "Klasifikasi endpoint:"]
        lines += [f"  {key}: {value} respons" for key, value in sorted(classes.items())]
        lines += ["", "HTTP status:"]
        lines += [f"  HTTP {key}: {value} respons" for key, value in sorted(statuses.items())]
        lines += ["", "Network error taxonomy:"]
        lines += [f"  {key}: {value} respons" for key, value in sorted(network.items())] or ["  tidak ada"]
        lines += ["", "Provider hint:"]
        lines += [f"  {key}: {value} respons" for key, value in sorted(providers.items())]
        lines += ["", "Rekomendasi prioritas:"]
        priority = [item for item in hosts if item.verdict in {"valid_exposure", "potential_exposure", "manual_review", "waf_blocked"}]
        priority.sort(key=lambda item: item.heuristic_score, reverse=True)
        if not priority:
            lines.append("  Tidak ada host yang memerlukan validasi lanjutan.")
        else:
            for index, item in enumerate(priority, 1):
                lines.append(f"  {index}. {item.target} [{item.verdict}, {item.confidence_level}, {item.heuristic_score}/100]")
                lines.append(f"     Alasan: {item.reason}")
                lines.append(f"     Action: {item.recommendation}")
        (self.report_dir / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _markdown(self, endpoints: list[EndpointResult], hosts: list[HostSummary]) -> None:
        valid_hosts = {item.target: item for item in hosts if item.verdict == "valid_exposure"}
        grouped: dict[str, list[EndpointResult]] = {}
        for item in endpoints:
            if item.target in valid_hosts and item.classification == "confirmed_exposure":
                grouped.setdefault(item.target, []).append(item)
        lines = [
            "# Git Exposure Auditor — Candidate Findings",
            "",
            f"> Generated by Git Exposure Auditor v{self.version}. Manual validation is required before submission.",
            "",
            "## Safety note",
            "",
            "No repository dumping, credential testing, automatic authentication/WAF bypass, brute force, or destructive action was performed. Stored snippets are redacted.",
            "",
        ]
        if not grouped:
            lines += ["## Result", "", "NO REPORTABLE FINDINGS GENERATED", ""]
        else:
            for index, target in enumerate(sorted(grouped), 1):
                items = sorted(grouped[target], key=lambda item: item.heuristic_score, reverse=True)
                primary = items[0]
                endpoint_lines = "\n".join(
                    f"- `{item.endpoint}` — HTTP {item.status}, {item.reason}, hash `{item.body_sha256}`"
                    for item in items
                )
                evidence = "; ".join(point.detail for point in primary.evidence)
                lines += [
                    f"## Candidate {index}: Publicly Accessible Git Metadata",
                    "",
                    f"**Affected asset:** `{target}`  ",
                    f"**Primary endpoint:** `{target}{primary.endpoint}`  ",
                    f"**Host verdict:** `valid_exposure`  ",
                    f"**Heuristic score:** `{primary.heuristic_score}/100 ({primary.confidence_level})`  ",
                    f"**Primary validation reason:** {primary.reason}  ",
                    f"**Evidence breakdown:** {evidence}  ",
                    "",
                    "### Confirmed metadata endpoints",
                    "",
                    endpoint_lines,
                    "",
                    "### Reproduction",
                    "",
                    f"1. Send one GET request to `{target}{primary.endpoint}`.",
                    "2. Confirm the response matches the described Git metadata signature.",
                    "3. Compare against random non-existent paths to rule out soft-404 or SPA fallback behavior.",
                    "4. Do not reconstruct or download the repository unless the program separately and explicitly authorizes it.",
                    "",
                    "### Impact",
                    "",
                    "Accessible Git metadata may disclose branch references, repository configuration, index metadata, or development history. Actual impact depends on the exposed repository content.",
                    "",
                    "### Remediation",
                    "",
                    "Block `/.git` and all paths below it at origin, reverse proxy, and CDN layers. Review repository history for secrets and rotate exposed credentials if necessary.",
                    "",
                    "---",
                    "",
                ]
        (self.report_dir / "hackerone-findings.md").write_text("\n".join(lines), encoding="utf-8")

    def _html(self, endpoints: list[EndpointResult], hosts: list[HostSummary]) -> None:
        rows = []
        for item in sorted(hosts, key=lambda x: x.heuristic_score, reverse=True):
            rows.append(
                "<tr>"
                f"<td>{html.escape(item.target)}</td><td>{html.escape(item.verdict)}</td>"
                f"<td>{item.heuristic_score}/100</td><td>{html.escape(item.provider_hint)}</td>"
                f"<td>{item.requests} total / {item.saved_endpoint_requests} saved</td><td>{html.escape(item.reason)}</td>"
                "</tr>"
            )
        page = f"""<!doctype html><html><head><meta charset='utf-8'><title>GEA Report</title>
<style>body{{font-family:system-ui;margin:2rem;max-width:1400px}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccc;padding:.5rem;text-align:left}}th{{background:#eee}}code{{background:#eee;padding:.1rem .3rem}}</style></head>
<body><h1>Git Exposure Auditor v{html.escape(self.version)}</h1><p>Hosts: {len(hosts)} · Endpoint results: {len(endpoints)}</p>
<table><thead><tr><th>Target</th><th>Verdict</th><th>Score</th><th>Provider</th><th>Requests</th><th>Reason</th></tr></thead><tbody>{''.join(rows)}</tbody></table></body></html>"""
        (self.report_dir / "report.html").write_text(page, encoding="utf-8")

    def _comparison(self, hosts: list[HostSummary], previous_dir: Path) -> None:
        previous_file = previous_dir / "host-summary.jsonl"
        previous: dict[str, dict] = {}
        if previous_file.exists():
            for line in previous_file.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                previous[str(item.get("target", ""))] = item
        current = {item.target: item.to_dict() for item in hosts}
        changes = []
        for target in sorted(set(previous) | set(current)):
            old = previous.get(target)
            new = current.get(target)
            if old is None:
                changes.append({"target": target, "change": "added", "current": new})
            elif new is None:
                changes.append({"target": target, "change": "missing_in_current", "previous": old})
            elif old.get("verdict") != new.get("verdict") or old.get("heuristic_score") != new.get("heuristic_score"):
                changes.append({"target": target, "change": "changed", "previous": old, "current": new})
        write_json(self.report_dir / "comparison.json", {"previous_report": str(previous_dir), "changes": changes})


def explain_report(report_dir: Path) -> str:
    host_file = report_dir / "host-summary.jsonl"
    if not host_file.exists():
        raise ValueError(f"host-summary.jsonl tidak ditemukan di {report_dir}")
    hosts = []
    for line in host_file.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip():
            hosts.append(json.loads(line))
    verdicts = Counter(item.get("verdict", "unknown") for item in hosts)
    priority = sorted(hosts, key=lambda item: (VERDICT_PRIORITY.get(str(item.get("verdict", "")), 0), int(item.get("heuristic_score", 0))), reverse=True)[:10]
    lines = ["Penjelasan laporan Git Exposure Auditor", "", "Verdict host:"]
    lines += [f"- {key}: {value}" for key, value in sorted(verdicts.items())]
    lines += ["", "Prioritas:"]
    for item in priority:
        lines.append(f"- {item.get('target')}: {item.get('verdict')} {item.get('heuristic_score')}/100 — {item.get('reason')}")
    return "\n".join(lines) + "\n"

#!/usr/bin/env python3
"""Generate sanitized JSON, CSV, Markdown, and report-draft outputs."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ORDER = {
    "CONFIRMED": 0,
    "PROBABLE": 1,
    "BLOCKED": 2,
    "REDIRECTED": 3,
    "SOFT_404": 4,
    "NOT_EXPOSED": 5,
    "ERROR": 6,
}


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except FileNotFoundError:
        return items
    for line in lines:
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            items.append(value)
    return items


def safe_text(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def write_lines(path: Path, values: list[str]) -> None:
    unique = sorted({value for value in values if value})
    path.write_text("".join(f"{value}\n" for value in unique), encoding="utf-8")


def report_draft(findings: list[dict[str, Any]], metadata: dict[str, Any]) -> str:
    positives = [f for f in findings if f.get("classification") in {"CONFIRMED", "PROBABLE"}]
    if not positives:
        return """# Responsible Disclosure Draft\n\nNo confirmed or probable Git metadata exposure was produced by this run. Manual review may still be appropriate for blocked, redirected, or unreachable assets.\n"""

    finding = sorted(positives, key=lambda f: (-int(f.get("score", 0)), str(f.get("head_url", ""))))[0]
    head = finding.get("head_response", {})
    confirmations = [
        item for item in finding.get("confirmation", []) if item.get("signature_confirmed")
    ]
    confirmation_text = "\n".join(
        f"- `{item.get('path')}`: {item.get('signature_name')}"
        for item in confirmations
    ) or "- No additional Git metadata file was confirmed by safe confirmation mode."

    return f"""# Responsible Disclosure Draft\n\n## Title\n\nPublicly accessible Git metadata on `{finding.get('head_url', '[URL]')}`\n\n## Weakness\n\n- **CWE:** CWE-527 — Exposure of Version-Control Repository to an Unauthorized Control Sphere\n- **Category:** Security misconfiguration / sensitive metadata exposure\n\n## Summary\n\nThe web server returned a valid Git `HEAD` signature without authentication. The response was compared with a randomized missing-path baseline to reduce false positives. Automated validation did not follow redirects, reconstruct the repository, use credentials, or store response bodies.\n\n## Asset\n\n```text\n{finding.get('base_url', '[ASSET]')}\n```\n\n## Minimal reproduction\n\n```bash\ncurl --silent --show-error --include --max-time 10 \\\n  '{finding.get('head_url', '[URL]')}'\n```\n\n## Automated evidence summary\n\n- Classification: **{finding.get('classification')}**\n- Confidence score: **{finding.get('score')}/100**\n- Git HEAD signature: `{finding.get('head_signature') or 'not recorded'}`\n- HTTP status: `{head.get('status')}`\n- Content type: `{head.get('content_type')}`\n- Response length inspected: `{head.get('content_length')}` bytes\n- Response SHA-256: `{head.get('body_sha256')}`\n- Soft-404 similarity: `{finding.get('soft404_similarity')}`\n\n### Additional safe confirmation\n\n{confirmation_text}\n\n## Impact\n\nPublic Git metadata can expose internal repository structure and implementation details. The final severity depends on what additional repository data is accessible and whether sensitive information exists. Perform only the minimum manual validation allowed by the program policy.\n\n## Research boundaries\n\n- No repository dump was performed.\n- No Git objects were reconstructed.\n- No credentials, tokens, or secrets were used.\n- No authentication or authorization control was bypassed.\n- No redirects to another host were followed.\n- No response body was retained by the tool.\n\n## Recommended remediation\n\n1. Remove `.git` and all version-control metadata from the production web root.\n2. Deploy build artifacts instead of the repository working directory.\n3. Block access to version-control paths as defense in depth.\n4. Review deployment archives, backups, and alternate application paths.\n5. Review repository history for secrets and rotate any potentially exposed credentials.\n6. Review web access logs for requests to `.git` paths.\n\n## Run metadata\n\n- Tool version: `{metadata.get('tool_version', '2.0.0')}`\n- Started: `{metadata.get('started_at', '')}`\n- Finished: `{metadata.get('finished_at', '')}`\n- Output directory: `{metadata.get('output_directory', '')}`\n\n> Manual verification and program-specific impact analysis are required before submission. This tool cannot guarantee report acceptance or a bounty.\n"""


def build_summary(findings: list[dict[str, Any]], metadata: dict[str, Any], live_count: int) -> dict[str, Any]:
    counts = Counter(str(item.get("classification", "UNKNOWN")) for item in findings)
    confirmed = [item for item in findings if item.get("classification") == "CONFIRMED"]
    probable = [item for item in findings if item.get("classification") == "PROBABLE"]
    top = sorted(
        confirmed + probable,
        key=lambda item: (-int(item.get("score", 0)), str(item.get("head_url", ""))),
    )[:20]
    return {
        "tool": "git-exposure-auditor",
        "version": metadata.get("tool_version", "2.0.0"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_mode": metadata.get("input_mode", "unknown"),
        "reachable_base_urls": live_count,
        "validation_tasks": len(findings),
        "classifications": dict(sorted(counts.items())),
        "confirmed_count": len(confirmed),
        "probable_count": len(probable),
        "manual_review_count": len(confirmed) + len(probable),
        "top_candidates": [
            {
                "head_url": item.get("head_url"),
                "classification": item.get("classification"),
                "score": item.get("score"),
                "evidence_level": item.get("evidence_level"),
            }
            for item in top
        ],
        "guarantees_bounty": False,
    }


def render_markdown(summary: dict[str, Any], metadata: dict[str, Any], findings: list[dict[str, Any]]) -> str:
    counts = summary["classifications"]
    rows = []
    for name in sorted(counts, key=lambda key: ORDER.get(key, 99)):
        rows.append(f"| {name} | {counts[name]} |")
    classification_table = "\n".join(rows) or "| No tasks | 0 |"

    positives = [item for item in findings if item.get("classification") in {"CONFIRMED", "PROBABLE"}]
    positives = sorted(positives, key=lambda item: (-int(item.get("score", 0)), str(item.get("head_url", ""))))
    candidate_rows = []
    for item in positives[:50]:
        candidate_rows.append(
            "| {classification} | {score} | `{url}` | {evidence} |".format(
                classification=safe_text(item.get("classification")),
                score=safe_text(item.get("score")),
                url=safe_text(item.get("head_url")),
                evidence=safe_text(item.get("evidence_level")),
            )
        )
    candidate_table = "\n".join(candidate_rows) or "| — | — | No confirmed or probable candidates | — |"

    return f"""# Git Exposure Audit Summary\n\n## Run overview\n\n- **Tool:** Git Exposure Auditor v{summary.get('version')}\n- **Input mode:** {safe_text(summary.get('input_mode'))}\n- **Started:** {safe_text(metadata.get('started_at'))}\n- **Finished:** {safe_text(metadata.get('finished_at'))}\n- **Reachable base URLs:** {summary.get('reachable_base_urls')}\n- **Validation tasks:** {summary.get('validation_tasks')}\n- **Confirmed:** {summary.get('confirmed_count')}\n- **Probable:** {summary.get('probable_count')}\n- **Safe confirmation enabled:** {safe_text(metadata.get('safe_confirmation'))}\n\n## Classification totals\n\n| Classification | Count |\n|---|---:|\n{classification_table}\n\n## Manual-review queue\n\n| Classification | Score | Endpoint | Evidence level |\n|---|---:|---|---|\n{candidate_table}\n\n## Interpretation\n\n- **CONFIRMED** means a valid Git `HEAD` signature was distinguished from a randomized missing-path baseline.\n- **PROBABLE** means Git-like evidence exists but one or more confidence checks were inconclusive.\n- **SOFT_404** means the response resembled the site's generic missing-page behavior.\n- **BLOCKED** means the path returned an access-control response such as HTTP 401 or 403.\n- **REDIRECTED** means the endpoint redirected; the tool intentionally did not follow it.\n- **NOT_EXPOSED** means no valid Git `HEAD` signature was detected for the tested endpoint.\n- **ERROR** means the request did not produce a usable HTTP result.\n\n## Safety boundaries\n\nThis run did not dump or reconstruct a repository, use credentials, bypass authentication, evade a WAF, or retain response bodies. Every positive result requires manual scope review and program-specific impact validation.\n\n## Bounty expectation\n\nThe workflow automates discovery, false-positive reduction, prioritization, and report drafting. It cannot guarantee that a program will accept a report or pay a bounty.\n"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--findings", required=True)
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--live-urls", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    findings = load_jsonl(Path(args.findings))
    metadata = load_json(Path(args.metadata), {})
    try:
        live_count = len({line.strip() for line in Path(args.live_urls).read_text().splitlines() if line.strip()})
    except FileNotFoundError:
        live_count = 0

    summary = build_summary(findings, metadata, live_count)
    (output_dir / "scan-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "summary.md").write_text(
        render_markdown(summary, metadata, findings), encoding="utf-8"
    )
    (output_dir / "report-draft.md").write_text(
        report_draft(findings, metadata), encoding="utf-8"
    )

    confirmed = [str(item.get("head_url", "")) for item in findings if item.get("classification") == "CONFIRMED"]
    probable = [str(item.get("head_url", "")) for item in findings if item.get("classification") == "PROBABLE"]
    write_lines(output_dir / "confirmed.txt", confirmed)
    write_lines(output_dir / "probable.txt", probable)
    write_lines(output_dir / "manual-review.txt", confirmed + probable)

    with (output_dir / "findings.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "classification",
                "score",
                "confidence",
                "evidence_level",
                "base_url",
                "application_path",
                "head_url",
                "status",
                "content_type",
                "content_length",
                "body_sha256",
                "soft404_similarity",
                "manual_validation_required",
            ],
        )
        writer.writeheader()
        for item in sorted(findings, key=lambda f: (ORDER.get(str(f.get("classification")), 99), -int(f.get("score", 0)))):
            head = item.get("head_response", {}) if isinstance(item.get("head_response"), dict) else {}
            writer.writerow(
                {
                    "classification": item.get("classification"),
                    "score": item.get("score"),
                    "confidence": item.get("confidence"),
                    "evidence_level": item.get("evidence_level"),
                    "base_url": item.get("base_url"),
                    "application_path": item.get("application_path"),
                    "head_url": item.get("head_url"),
                    "status": head.get("status"),
                    "content_type": head.get("content_type"),
                    "content_length": head.get("content_length"),
                    "body_sha256": head.get("body_sha256"),
                    "soft404_similarity": item.get("soft404_similarity"),
                    "manual_validation_required": item.get("manual_validation_required"),
                }
            )

    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()

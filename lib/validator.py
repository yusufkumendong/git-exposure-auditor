#!/usr/bin/env python3
"""Minimal, non-destructive Git metadata validator with soft-404 detection."""

from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import difflib
import hashlib
import json
import re
import ssl
import sys
import threading
import time
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from scope import host_in_scope, load_scope, normalize_path, port_spec_allowed

BRANCH_REF_RE = re.compile(r"^ref:\s+refs/heads/[A-Za-z0-9._/-]+$", re.ASCII)
OBJECT_ID_RE = re.compile(r"^(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})$", re.ASCII)
PACKED_REFS_LINE_RE = re.compile(r"^[0-9a-fA-F]{40,64}\s+refs/(?:heads|tags|remotes)/", re.MULTILINE)
LOG_HEAD_RE = re.compile(
    r"^[0-9a-fA-F]{40,64}\s+[0-9a-fA-F]{40,64}\s+.+?<[^>]+>\s+[0-9]{9,}\s+[+-][0-9]{4}",
    re.MULTILINE,
)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        return None


@dataclasses.dataclass
class ResponseMetadata:
    url: str
    status: int | None
    content_type: str
    content_length: int
    body_sha256: str
    elapsed_ms: int
    location: str
    truncated: bool
    error: str
    body: bytes = dataclasses.field(repr=False, default=b"")

    def public(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "status": self.status,
            "content_type": self.content_type,
            "content_length": self.content_length,
            "body_sha256": self.body_sha256,
            "elapsed_ms": self.elapsed_ms,
            "location": self.location,
            "truncated": self.truncated,
            "error": self.error,
        }


class GlobalRateLimiter:
    def __init__(self, rate_per_second: int) -> None:
        self.interval = 1.0 / max(rate_per_second, 1)
        self.lock = threading.Lock()
        self.next_allowed = 0.0

    def wait(self) -> None:
        with self.lock:
            now = time.monotonic()
            wait_for = self.next_allowed - now
            if wait_for > 0:
                time.sleep(wait_for)
            self.next_allowed = max(now, self.next_allowed) + self.interval


class HttpClient:
    def __init__(self, timeout: int, max_body: int, user_agent: str, rate_limiter: GlobalRateLimiter) -> None:
        self.timeout = timeout
        self.max_body = max_body
        self.user_agent = user_agent
        self.rate_limiter = rate_limiter
        self.ssl_context = ssl.create_default_context()

    def request(self, url: str) -> ResponseMetadata:
        self.rate_limiter.wait()
        started = time.monotonic()
        request = Request(
            url,
            method="GET",
            headers={
                "User-Agent": self.user_agent,
                "Accept": "*/*",
                "Connection": "close",
                "Cache-Control": "no-cache",
            },
        )
        try:
            opener = build_opener(NoRedirect())
            response = opener.open(request, timeout=self.timeout)
            status = getattr(response, "status", response.getcode())
            headers = response.headers
            body = response.read(self.max_body + 1)
        except HTTPError as exc:
            status = exc.code
            headers = exc.headers
            try:
                body = exc.read(self.max_body + 1)
            except Exception:
                body = b""
        except (URLError, TimeoutError, ssl.SSLError, OSError) as exc:
            return ResponseMetadata(
                url=url,
                status=None,
                content_type="",
                content_length=0,
                body_sha256="",
                elapsed_ms=round((time.monotonic() - started) * 1000),
                location="",
                truncated=False,
                error=f"{type(exc).__name__}: {exc}",
                body=b"",
            )

        truncated = len(body) > self.max_body
        if truncated:
            body = body[: self.max_body]
        content_type = headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        location = headers.get("Location", "").strip()
        return ResponseMetadata(
            url=url,
            status=int(status),
            content_type=content_type,
            content_length=len(body),
            body_sha256=hashlib.sha256(body).hexdigest(),
            elapsed_ms=round((time.monotonic() - started) * 1000),
            location=location,
            truncated=truncated,
            error="",
            body=body,
        )


def read_nonempty_lines(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except FileNotFoundError:
        raise SystemExit(f"[!] File not found: {path}")
    return sorted({line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")})


def normalize_base_url(value: str, scope: dict) -> str:
    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"Invalid reachable URL: {value}")
    if parsed.username or parsed.password:
        raise ValueError("URL credentials are not allowed")
    if not host_in_scope(parsed.hostname, scope):
        raise ValueError(f"URL is outside scope: {value}")
    if not port_spec_allowed(parsed.scheme, parsed.port, scope):
        raise ValueError(f"URL port is outside scope: {value}")
    netloc = parsed.hostname.lower()
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme.lower(), netloc, path, "", ""))


def combine_app_path(base_url: str, app_path: str) -> str:
    parsed = urlsplit(base_url)
    existing = parsed.path.rstrip("/")
    normalized_app = normalize_path(app_path)
    if normalized_app == "/":
        combined = existing or ""
    else:
        combined = f"{existing}/{normalized_app.lstrip('/')}"
    combined = "/" + "/".join(segment for segment in combined.split("/") if segment)
    if combined == "/":
        combined = ""
    return urlunsplit((parsed.scheme, parsed.netloc, combined, "", ""))


def endpoint(base: str, relative: str) -> str:
    return base.rstrip("/") + "/" + relative.lstrip("/")


def body_text(body: bytes) -> str:
    return body.decode("utf-8", errors="replace").strip()


def normalized_similarity_text(body: bytes) -> str:
    text = body[:8192].decode("utf-8", errors="replace").lower()
    text = re.sub(r"[0-9a-f]{8,}", "<token>", text)
    text = re.sub(r"\d{6,}", "<number>", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def is_soft_404(head: ResponseMetadata, baseline: ResponseMetadata) -> tuple[bool, float]:
    if head.status is None or baseline.status is None:
        return False, 0.0
    if head.status != baseline.status:
        return False, 0.0
    if head.body_sha256 and head.body_sha256 == baseline.body_sha256:
        return True, 1.0
    a = normalized_similarity_text(head.body)
    b = normalized_similarity_text(baseline.body)
    if not a and not b:
        return True, 1.0
    similarity = difflib.SequenceMatcher(None, a, b).ratio()
    length_gap = abs(head.content_length - baseline.content_length)
    length_tolerance = max(32, int(max(head.content_length, baseline.content_length) * 0.05))
    same_type = head.content_type == baseline.content_type
    return bool(similarity >= 0.95 and length_gap <= length_tolerance and same_type), similarity


def detect_head_signature(body: bytes) -> tuple[str, str]:
    text = body_text(body)
    if BRANCH_REF_RE.fullmatch(text):
        return "symbolic-ref", "Git HEAD contains a refs/heads symbolic reference."
    if OBJECT_ID_RE.fullmatch(text):
        return "detached-object-id", "Git HEAD contains a detached 40/64-character object identifier."
    return "", ""


def confirmation_signature(path: str, body: bytes) -> tuple[bool, str]:
    text = body.decode("utf-8", errors="replace")
    if path == ".git/config":
        valid = "[core]" in text and "repositoryformatversion" in text
        return valid, "Git repository configuration signature" if valid else ""
    if path == ".git/packed-refs":
        valid = text.startswith("# pack-refs with:") or bool(PACKED_REFS_LINE_RE.search(text))
        return valid, "Git packed references signature" if valid else ""
    if path == ".git/index":
        valid = body.startswith(b"DIRC")
        return valid, "Git index DIRC signature" if valid else ""
    if path == ".git/logs/HEAD":
        valid = bool(LOG_HEAD_RE.search(text))
        return valid, "Git reflog HEAD signature" if valid else ""
    return False, ""


def status_classification(response: ResponseMetadata) -> str:
    if response.status is None:
        return "ERROR"
    if response.status in {401, 403}:
        return "BLOCKED"
    if 300 <= response.status <= 399:
        return "REDIRECTED"
    return "NOT_EXPOSED"


def validate_task(
    base_url: str,
    app_path: str,
    client: HttpClient,
    confirm: bool,
) -> dict[str, Any]:
    application_base = combine_app_path(base_url, app_path)
    task_id = hashlib.sha256(f"{application_base}\n".encode()).hexdigest()[:20]
    head_url = endpoint(application_base, ".git/HEAD")
    baseline_url = endpoint(application_base, f".gea-not-found-{task_id}")

    baseline = client.request(baseline_url)
    head = client.request(head_url)
    soft404, similarity = is_soft_404(head, baseline)
    signature, signature_reason = detect_head_signature(head.body)
    reasons: list[str] = []
    confirmation: list[dict[str, Any]] = []
    score = 0
    classification = status_classification(head)

    if head.status == 200 and signature:
        if soft404:
            classification = "SOFT_404"
            reasons.append("The Git HEAD response is indistinguishable from a randomized missing path.")
        else:
            score = 70
            reasons.append(signature_reason)
            if baseline.status is not None:
                reasons.append("The randomized missing-path baseline returned a different response profile.")
                score += 15
            else:
                reasons.append("The randomized missing-path baseline could not be completed; manual comparison is required.")
            if head.content_length <= 512 and not head.truncated:
                score += 5
                reasons.append("The response size is consistent with a small Git HEAD file.")
            if head.content_type in {
                "text/plain",
                "application/octet-stream",
                "application/x-git",
                "",
            }:
                score += 5
                reasons.append("The response content type is compatible with Git metadata.")
            classification = "CONFIRMED" if score >= 85 else "PROBABLE"
    elif head.status == 200 and soft404:
        classification = "SOFT_404"
        reasons.append("The response matches the randomized missing-path baseline.")
    elif head.status == 200:
        classification = "NOT_EXPOSED"
        reasons.append("HTTP 200 was returned, but no valid Git HEAD signature was detected.")
    elif head.status in {401, 403}:
        reasons.append("Access to the Git HEAD path was denied.")
    elif head.status is not None and 300 <= head.status <= 399:
        reasons.append("The endpoint redirected; redirects were not followed.")
    elif head.status is None:
        reasons.append("The request failed before an HTTP response was received.")
    else:
        reasons.append("The endpoint did not return a valid Git HEAD response.")

    if confirm and classification in {"CONFIRMED", "PROBABLE"}:
        for confirm_path in (
            ".git/config",
            ".git/packed-refs",
            ".git/index",
            ".git/logs/HEAD",
        ):
            response = client.request(endpoint(application_base, confirm_path))
            valid, reason = confirmation_signature(confirm_path, response.body)
            confirmation.append(
                {
                    "path": "/" + confirm_path,
                    "signature_confirmed": valid,
                    "signature_name": reason,
                    "response": response.public(),
                }
            )
            if valid:
                score = min(100, score + 5)
                reasons.append(f"Additional confirmation: {reason}.")
            if sum(1 for item in confirmation if item["signature_confirmed"]) >= 2:
                reasons.append("Safe confirmation stopped after two additional Git signatures.")
                break
        if any(item["signature_confirmed"] for item in confirmation):
            classification = "CONFIRMED"

    confidence = "high" if score >= 85 else "medium" if score >= 60 else "low"
    positive_confirmation_count = sum(1 for item in confirmation if item["signature_confirmed"])
    evidence_level = (
        "multi-file-metadata"
        if positive_confirmation_count >= 1
        else "head-metadata-only"
        if classification == "CONFIRMED"
        else "unconfirmed"
    )

    result = {
        "task_id": task_id,
        "base_url": base_url,
        "application_path": normalize_path(app_path),
        "application_base": application_base or base_url,
        "head_url": head_url,
        "classification": classification,
        "confidence": confidence,
        "score": score,
        "evidence_level": evidence_level,
        "head_signature": signature,
        "soft404_similarity": round(similarity, 4),
        "manual_validation_required": True,
        "reasons": reasons,
        "head_response": head.public(),
        "baseline_response": baseline.public(),
        "confirmation": confirmation,
    }
    return result


def load_resume(path: Path | None) -> tuple[list[dict[str, Any]], set[str]]:
    if path is None:
        return [], set()
    previous: list[dict[str, Any]] = []
    completed: set[str] = set()
    for line in read_nonempty_lines(path):
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict) and item.get("task_id"):
            previous.append(item)
            completed.add(str(item["task_id"]))
    return previous, completed


def make_task_id(base_url: str, app_path: str) -> str:
    application_base = combine_app_path(base_url, app_path)
    return hashlib.sha256(f"{application_base}\n".encode()).hexdigest()[:20]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--urls", required=True, help="File of reachable base URLs")
    parser.add_argument("--paths", required=True, help="File of approved application base paths")
    parser.add_argument("--scope", required=True, help="Validated JSON scope file")
    parser.add_argument("--output", required=True, help="Output JSONL path")
    parser.add_argument("--threads", type=int, default=15)
    parser.add_argument("--rate-limit", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=8)
    parser.add_argument("--max-body", type=int, default=65536)
    parser.add_argument("--max-tasks", type=int, default=10000)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--resume-from")
    parser.add_argument("--user-agent", default="git-exposure-auditor/2.0.0")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not 1 <= args.threads <= 50:
        raise SystemExit("[!] --threads must be from 1 to 50.")
    if not 1 <= args.rate_limit <= 50:
        raise SystemExit("[!] --rate-limit must be from 1 to 50.")
    if not 1 <= args.timeout <= 30:
        raise SystemExit("[!] --timeout must be from 1 to 30 seconds.")
    if not 1 <= args.max_body <= 262144:
        raise SystemExit("[!] --max-body must be from 1 to 262144 bytes.")
    if not 1 <= args.max_tasks <= 50000:
        raise SystemExit("[!] --max-tasks must be from 1 to 50000.")

    scope = load_scope(Path(args.scope))
    raw_urls = read_nonempty_lines(Path(args.urls))
    paths = [normalize_path(value) for value in read_nonempty_lines(Path(args.paths))]

    urls: list[str] = []
    for value in raw_urls:
        try:
            urls.append(normalize_base_url(value, scope))
        except ValueError as exc:
            print(f"[!] Skipping URL: {exc}", file=sys.stderr)
    urls = sorted(set(urls))
    paths = sorted(set(paths))

    planned_tasks = [(url, path) for url in urls for path in paths]
    task_count = len(planned_tasks)
    if task_count > args.max_tasks:
        raise SystemExit(
            f"[!] Planned task count {task_count} exceeds the configured maximum of {args.max_tasks}."
        )

    planned_ids = {make_task_id(url, path) for url, path in planned_tasks}
    previous_raw, _ = load_resume(Path(args.resume_from) if args.resume_from else None)
    previous = [item for item in previous_raw if str(item.get("task_id", "")) in planned_ids]
    completed = {str(item.get("task_id")) for item in previous}
    tasks = [
        (url, path)
        for url, path in planned_tasks
        if make_task_id(url, path) not in completed
    ]

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    limiter = GlobalRateLimiter(args.rate_limit)
    client = HttpClient(args.timeout, args.max_body, args.user_agent, limiter)

    counters: dict[str, int] = {}
    with output_path.open("w", encoding="utf-8") as handle:
        for item in previous:
            handle.write(json.dumps(item, sort_keys=True) + "\n")
            counters[item.get("classification", "UNKNOWN")] = counters.get(item.get("classification", "UNKNOWN"), 0) + 1

        with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
            futures = {
                executor.submit(validate_task, url, path, client, args.confirm): (url, path)
                for url, path in tasks
            }
            for future in concurrent.futures.as_completed(futures):
                url, path = futures[future]
                try:
                    result = future.result()
                except Exception as exc:  # Defensive isolation between tasks.
                    result = {
                        "task_id": make_task_id(url, path),
                        "base_url": url,
                        "application_path": path,
                        "classification": "ERROR",
                        "confidence": "low",
                        "score": 0,
                        "manual_validation_required": True,
                        "reasons": [f"Unhandled validation error: {type(exc).__name__}: {exc}"],
                        "confirmation": [],
                    }
                handle.write(json.dumps(result, sort_keys=True) + "\n")
                handle.flush()
                classification = str(result.get("classification", "UNKNOWN"))
                counters[classification] = counters.get(classification, 0) + 1

    print(
        json.dumps(
            {
                "reachable_urls": len(urls),
                "application_paths": len(paths),
                "planned_tasks": task_count,
                "resumed_tasks": len(previous),
                "new_tasks": len(tasks),
                "classifications": counters,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

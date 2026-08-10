from __future__ import annotations

import os
import re
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from .models import HttpResponse


CURL_ERROR_MAP = {
    1: "unsupported_protocol",
    5: "proxy_error",
    6: "dns_no_record",
    7: "connection_refused",
    18: "connection_reset",
    28: "connect_timeout",
    35: "tls_error",
    47: "redirect_loop",
    51: "tls_hostname_mismatch",
    52: "connection_reset",
    55: "connection_reset",
    56: "connection_reset",
    58: "tls_error",
    60: "tls_hostname_mismatch",
    63: "body_too_large",
    77: "tls_error",
    92: "unsupported_protocol",
}


def parse_headers(raw: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    blocks = re.split(r"\r?\n\r?\n", raw.strip()) if raw.strip() else []
    block = blocks[-1] if blocks else ""
    for line in block.splitlines():
        if ":" not in line:
            continue
        name, value = line.split(":", 1)
        headers[name.strip().lower()] = value.strip()
    return headers


def classify_network_error(returncode: int, stderr: str, status: int) -> str:
    if status > 0 and returncode == 0:
        return ""
    lower = stderr.lower()
    if "operation timed out" in lower:
        return "read_timeout" if "bytes received" in lower else "connect_timeout"
    if "could not resolve host" in lower:
        return "dns_no_record"
    if "ssl" in lower or "certificate" in lower or "tls" in lower:
        if "subject name" in lower or "no alternative certificate" in lower:
            return "tls_hostname_mismatch"
        return "tls_error"
    return CURL_ERROR_MAP.get(returncode, "network_error")


class RateLimiter:
    def __init__(self, rate: float) -> None:
        self.interval = 1.0 / rate if rate > 0 else 0.0
        self.lock = threading.Lock()
        self.next_allowed = 0.0

    def wait(self) -> None:
        if self.interval <= 0:
            return
        with self.lock:
            now = time.monotonic()
            if now < self.next_allowed:
                time.sleep(self.next_allowed - now)
            self.next_allowed = max(now, self.next_allowed) + self.interval


@dataclass(slots=True)
class HttpConfig:
    connect_timeout: float = 5.0
    max_time: float = 15.0
    max_body_bytes: int = 262_144
    retries: int = 0
    retry_delay: float = 1.0
    retry_max_delay: float = 10.0
    respect_retry_after: bool = True
    insecure: bool = False
    proxy: str = ""
    http_version: str = "auto"
    user_agent: str = "Git-Exposure-Auditor/3.2.0-rc4 (+authorized-security-research)"
    headers: list[str] = field(default_factory=list)
    rate: float = 0.0


class CurlClient:
    def __init__(self, config: HttpConfig) -> None:
        self.config = config
        self.rate_limiter = RateLimiter(config.rate)

    def request(self, url: str) -> HttpResponse:
        attempt = 0
        delay = self.config.retry_delay
        last = HttpResponse(url=url, effective_url=url)
        while True:
            self.rate_limiter.wait()
            last = self._request_once(url)
            last.retries = attempt
            if attempt >= self.config.retries or not self._should_retry(last):
                return last
            sleep_for = delay
            retry_after = last.headers.get("retry-after", "")
            if self.config.respect_retry_after and retry_after.isdigit():
                sleep_for = min(float(retry_after), self.config.retry_max_delay)
            time.sleep(max(0.0, sleep_for))
            delay = min(delay * 2, self.config.retry_max_delay)
            attempt += 1

    def _should_retry(self, response: HttpResponse) -> bool:
        if response.status in {429, 502, 503, 504}:
            return True
        return response.network_error in {"connect_timeout", "read_timeout", "connection_reset", "proxy_error"}

    def _request_once(self, url: str) -> HttpResponse:
        with tempfile.TemporaryDirectory(prefix="gea-http-") as temp_dir:
            body_path = Path(temp_dir) / "body"
            headers_path = Path(temp_dir) / "headers"
            args = [
                "curl",
                "--disable",
                "--request",
                "GET",
                "--silent",
                "--show-error",
                "--compressed",
                "--path-as-is",
                "--max-redirs",
                "0",
                "--connect-timeout",
                str(self.config.connect_timeout),
                "--max-time",
                str(self.config.max_time),
                "--max-filesize",
                str(self.config.max_body_bytes),
                "--user-agent",
                self.config.user_agent,
                "--dump-header",
                str(headers_path),
                "--output",
                str(body_path),
                "--write-out",
                "%{http_code}\t%{url_effective}\t%{content_type}\t%{size_download}\t%{time_total}\t%{remote_ip}\t%{http_version}",
                "--proto",
                "=http,https",
            ]
            if self.config.insecure:
                args.append("--insecure")
            if self.config.proxy:
                args.extend(["--proxy", self.config.proxy])
            if self.config.http_version == "1.1":
                args.append("--http1.1")
            elif self.config.http_version == "2":
                args.append("--http2")
            for header in self.config.headers:
                args.extend(["--header", header])
            args.append(url)
            process = subprocess.run(args, capture_output=True, text=False, check=False)
            meta = process.stdout.decode("utf-8", errors="replace")
            parts = meta.split("\t")
            while len(parts) < 7:
                parts.append("")
            status_text, effective, content_type, size, duration, remote_ip, http_version = parts[:7]
            try:
                status = int(status_text)
            except ValueError:
                status = 0
            try:
                size_bytes = int(float(size or "0"))
            except ValueError:
                size_bytes = 0
            try:
                time_seconds = float(duration or "0")
            except ValueError:
                time_seconds = 0.0
            body = body_path.read_bytes()[: self.config.max_body_bytes] if body_path.exists() else b""
            raw_headers = headers_path.read_text(encoding="latin-1", errors="replace") if headers_path.exists() else ""
            error = process.stderr.decode("utf-8", errors="replace").replace("\n", " ").strip()[:500]
            network_error = classify_network_error(process.returncode, error, status)
            return HttpResponse(
                url=url,
                status=status,
                effective_url=effective or url,
                content_type=content_type or "",
                size_bytes=size_bytes,
                time_seconds=time_seconds,
                remote_ip=remote_ip,
                http_version=http_version,
                curl_rc=process.returncode,
                headers=parse_headers(raw_headers),
                body=body,
                error=error,
                network_error=network_error,
            )

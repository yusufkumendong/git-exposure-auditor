from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def random_token() -> str:
    return secrets.token_hex(10)


def normalize_url(raw: str, default_scheme: str = "https") -> str:
    value = raw.strip()
    if not value.lower().startswith(("http://", "https://")):
        value = f"{default_scheme}://{value}"
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"URL tidak valid: {raw}")
    if parsed.username or parsed.password:
        raise ValueError("URL dengan userinfo tidak diizinkan")
    host = parsed.hostname.encode("idna").decode("ascii").lower()
    try:
        display_host = f"[{host}]" if ipaddress.ip_address(host).version == 6 else host
    except ValueError:
        display_host = host
    port = f":{parsed.port}" if parsed.port else ""
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme.lower(), display_host + port, path, "", ""))


def safe_name(value: str) -> str:
    text = re.sub(r"^https?://", "", value, flags=re.I)
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("_")
    digest = hashlib.sha256(value.encode()).hexdigest()[:8]
    return f"{text[:80]}-{digest}"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest() if data else ""


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n")


_SECRET_PATTERNS = [
    (re.compile(r"(?i)(authorization\s*:\s*)([^\s]+)"), r"\1<redacted>"),
    (re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key)(\s*[=:]\s*)([^\s\"']+)"), r"\1\2<redacted>"),
    (re.compile(r"(?i)(https?://)([^/@\s:]+):([^/@\s]+)@"), r"\1<redacted>@"),
    (re.compile(r"(?i)(-----BEGIN [A-Z ]+PRIVATE KEY-----).*?(-----END [A-Z ]+PRIVATE KEY-----)", re.S), r"\1<redacted>\2"),
]


def redact_text(value: str) -> str:
    output = value
    for pattern, replacement in _SECRET_PATTERNS:
        output = pattern.sub(replacement, output)
    return output

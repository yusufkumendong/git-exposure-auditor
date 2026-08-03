#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urljoin, urlsplit

WAF_MARKERS = {
    "cloudflare": ["cf-ray", "cloudflare", "checking your browser", "attention required"],
    "akamai": ["akamai", "x-akamai", "reference #"],
    "imperva": ["x-iinfo", "incapsula", "imperva", "incident id"],
    "sucuri": ["x-sucuri", "sucuri website firewall", "access denied - sucuri"],
    "cloudfront": ["x-amz-cf-id", "cloudfront"],
    "fastly": ["x-served-by", "fastly", "varnish"],
}
ERROR_MARKERS = [
    "not found", "page not found", "access denied", "forbidden", "request blocked",
    "security verification", "enable javascript", "captcha", "service unavailable",
    "bad gateway", "gateway timeout", "upstream error", "temporarily unavailable",
]


def read_bytes(path: str) -> bytes:
    try:
        return Path(path).read_bytes()
    except OSError:
        return b""


def parse_headers(path: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    try:
        raw = Path(path).read_text(encoding="latin-1", errors="replace")
    except OSError:
        return headers
    for line in raw.splitlines():
        if ":" not in line:
            continue
        name, value = line.split(":", 1)
        headers[name.strip().lower()] = value.strip()
    return headers


def normalize_text(data: bytes) -> str:
    text = data.decode("utf-8", errors="replace").lower()
    text = re.sub(r"[0-9a-f]{16,}", "<hex>", text)
    text = re.sub(r"\b\d{5,}\b", "<number>", text)
    text = re.sub(r"\s+", " ", text)
    return text[:200_000].strip()


def title_of(text: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    return html.unescape(re.sub(r"\s+", " ", match.group(1)).strip()) if match else ""


def similarity(a: bytes, b: bytes) -> float:
    na, nb = normalize_text(a), normalize_text(b)
    if not na and not nb:
        return 1.0
    if not na or not nb:
        return 0.0
    return round(SequenceMatcher(None, na, nb).ratio(), 4)


def git_signature(endpoint: str, body: bytes) -> tuple[bool, str, int]:
    text = body.decode("utf-8", errors="replace")
    first = text.splitlines()[0].strip() if text.splitlines() else ""
    oid = r"[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?"
    if endpoint == "/.git/HEAD":
        if re.fullmatch(r"ref:\s+refs/heads/[A-Za-z0-9._/-]+", first):
            return True, "Git HEAD symbolic reference", 98
        if re.fullmatch(oid, first):
            return True, "Git detached HEAD object ID", 96
    elif endpoint == "/.git/config":
        if re.search(r"(?mi)^\s*\[core\]\s*$", text) and re.search(r"repositoryformatversion\s*=", text, re.I):
            return True, "Git config core section", 98
        if re.search(r"(?mi)^\s*\[remote\s+\"[^\"]+\"\]\s*$", text):
            return True, "Git config remote section", 92
    elif endpoint == "/.git/packed-refs":
        if re.search(r"(?m)^# pack-refs with:", text) or re.search(rf"(?m)^{oid}\s+refs/", text):
            return True, "Git packed-refs format", 97
    elif endpoint.startswith("/.git/refs/"):
        if re.fullmatch(oid, first):
            return True, "Git ref object ID", 96
    elif endpoint == "/.git/logs/HEAD":
        if re.search(rf"(?m)^{oid}\s+{oid}\s+.+", text):
            return True, "Git reflog entry", 95
    elif endpoint == "/.git/index":
        if body.startswith(b"DIRC"):
            return True, "Git index DIRC magic", 99
    elif endpoint == "/.git/objects/info/packs":
        if re.search(rf"(?m)^P pack-{oid}\.pack$", text):
            return True, "Git object pack listing", 96
    return False, "", 0


def provider_hint(headers: dict[str, str], text: str) -> str:
    haystack = "\n".join(f"{k}: {v}" for k, v in headers.items()).lower() + "\n" + text[:10_000]
    for provider, markers in WAF_MARKERS.items():
        if any(marker in haystack for marker in markers):
            return provider
    server = headers.get("server", "").strip()
    via = headers.get("via", "").strip()
    if via:
        return f"proxy:{via[:50]}"
    return server[:50].lower() if server else "unknown"


def recommend(classification: str) -> str:
    actions = {
        "confirmed_exposure": "Validasi manual minimum, jangan dumping repository, dokumentasikan bukti, lalu laporkan sesuai kebijakan program.",
        "probable_exposure": "Tinjau manual signature dan header secara non-destruktif sebelum membuat laporan.",
        "soft_404": "Abaikan sebagai exposure; respons sangat mirip dengan halaman path acak/custom error.",
        "spa_fallback": "Abaikan sebagai exposure; server kemungkinan mengembalikan halaman aplikasi yang sama untuk semua path.",
        "custom_error": "Tinjau singkat header/body; jangan laporkan hanya berdasarkan status HTTP.",
        "waf_challenge": "Jangan bypass WAF. Kurangi rate dan pastikan metode pengujian diperbolehkan program.",
        "rate_limited": "Hentikan atau perlambat request dan hormati Retry-After sebelum mengulang.",
        "protected": "Proteksi terlihat aktif; pastikan konsisten pada seluruh domain/subdomain in-scope.",
        "redirect_in_scope": "Validasi tujuan redirect secara terpisah bila tetap berada dalam scope.",
        "redirect_out_of_scope": "Jangan ikuti redirect karena tujuan berada di luar scope.",
        "upstream_error": "Validasi manual secara terbatas; 5xx dapat berasal dari CDN, proxy, WAF, atau origin.",
        "network_error": "Periksa DNS, TLS, konektivitas, proxy, dan timeout sebelum mengulang.",
        "suspicious": "Tinjau manual secara non-destruktif; bukti belum cukup untuk menyatakan exposure.",
        "not_exposed": "Tidak ada signature Git yang valid pada respons ini.",
    }
    return actions.get(classification, actions["suspicious"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--body", required=True)
    ap.add_argument("--headers", required=True)
    ap.add_argument("--status", required=True)
    ap.add_argument("--content-type", default="")
    ap.add_argument("--target", required=True)
    ap.add_argument("--baseline-body", required=True)
    ap.add_argument("--baseline-status", default="000")
    ap.add_argument("--scope", action="append", default=[])
    args = ap.parse_args()

    body = read_bytes(args.body)
    baseline = read_bytes(args.baseline_body)
    headers = parse_headers(args.headers)
    status = int(args.status) if args.status.isdigit() else 0
    text = normalize_text(body)
    baseline_text = normalize_text(baseline)
    sim = similarity(body, baseline)
    html_like = "<html" in text or "<!doctype" in text or "text/html" in args.content_type.lower()
    same_title = bool(title_of(text)) and title_of(text) == title_of(baseline_text)
    provider = provider_hint(headers, text)
    location = headers.get("location", "")
    signature, signature_reason, signature_score = git_signature(args.endpoint, body)

    classification = "not_exposed"
    confidence = 5
    reason = "Tidak ada signature Git yang cocok"

    if status == 0:
        classification, confidence, reason = "network_error", 0, "Tidak memperoleh respons HTTP"
    elif 300 <= status < 400:
        destination = urljoin(args.target + "/", location) if location else ""
        dest_host = (urlsplit(destination).hostname or "").lower()
        in_scope = False
        for rule in args.scope:
            rule = rule.lower()
            if rule.startswith("*."):
                suffix = rule[2:]
                in_scope = dest_host == suffix or dest_host.endswith("." + suffix)
            elif dest_host == rule:
                in_scope = True
            if in_scope:
                break
        classification = "redirect_in_scope" if in_scope else "redirect_out_of_scope"
        confidence = 90 if location else 50
        reason = f"Redirect ke {location or 'tujuan tidak tersedia'}"
    elif status == 429:
        classification, confidence, reason = "rate_limited", 95, "Server menerapkan rate limit"
    elif status in {502, 503, 504} or 500 <= status < 600:
        classification, confidence, reason = "upstream_error", 75, "Respons 5xx dari origin/CDN/proxy/WAF"
    elif signature and 200 <= status < 300:
        classification = "confirmed_exposure" if signature_score >= 96 else "probable_exposure"
        confidence = signature_score
        reason = signature_reason
        if sim >= 0.92:
            confidence = max(55, confidence - 30)
            classification = "probable_exposure"
            reason += "; namun respons mirip baseline"
    elif status in {401, 403}:
        known_edge = provider in {"cloudflare", "akamai", "imperva", "sucuri", "cloudfront", "fastly"}
        challenge_markers = ["checking your browser", "security verification", "captcha", "request blocked", "incident id", "ray id"]
        if known_edge or any(marker in text for marker in challenge_markers):
            classification, confidence, reason = "waf_challenge", 85, f"Access denied/challenge terdeteksi ({provider})"
        else:
            classification, confidence, reason = "protected", 90, "Endpoint ditolak oleh server"
    elif status in {404, 405, 410}:
        classification, confidence, reason = "protected", 90, "Endpoint tidak tersedia atau ditolak"
    elif 200 <= status < 300:
        if sim >= 0.94 and html_like and same_title:
            classification, confidence, reason = "spa_fallback", 96, "HTML dan title sangat mirip dengan baseline path acak"
        elif sim >= 0.90:
            classification, confidence, reason = "soft_404", 94, "Respons sangat mirip dengan baseline path acak"
        elif html_like and any(marker in text for marker in ERROR_MARKERS):
            classification, confidence, reason = "custom_error", 88, "Respons 2xx terlihat seperti halaman error/challenge"
        else:
            classification, confidence, reason = "suspicious", 45, "Respons 2xx tanpa signature Git yang kuat"
    elif 400 <= status < 500:
        classification, confidence, reason = "protected", 80, "Respons 4xx tanpa signature Git"

    result = {
        "classification": classification,
        "confidence": confidence,
        "reason": reason,
        "recommendation": recommend(classification),
        "provider_hint": provider,
        "similarity": sim,
        "body_sha256": hashlib.sha256(body).hexdigest() if body else "",
        "baseline_sha256": hashlib.sha256(baseline).hexdigest() if baseline else "",
        "location": location,
        "title": title_of(text),
        "baseline_title": title_of(baseline_text),
    }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

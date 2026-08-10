from __future__ import annotations

import html
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from .models import CLASS_TO_VERDICT, EndpointResult, EvidencePoint, HttpResponse
from .scope import ScopeEngine
from .util import now_iso, redact_text, sha256

WAF_MARKERS = {
    "cloudflare": ["cf-ray", "cloudflare", "checking your browser", "attention required"],
    "akamai": ["akamai", "x-akamai", "reference #"],
    "imperva": ["x-iinfo", "incapsula", "imperva", "incident id"],
    "sucuri": ["x-sucuri", "sucuri website firewall", "access denied - sucuri"],
    "cloudfront": ["x-amz-cf-id", "cloudfront"],
    "fastly": ["x-served-by", "fastly", "varnish"],
}
ERROR_MARKERS = (
    "not found",
    "page not found",
    "access denied",
    "forbidden",
    "request blocked",
    "security verification",
    "enable javascript",
    "captcha",
    "service unavailable",
    "bad gateway",
    "gateway timeout",
    "temporarily unavailable",
)


def normalize_text(data: bytes) -> str:
    text = data.decode("utf-8", errors="replace").lower()
    text = re.sub(r"[0-9a-f]{16,}", "<hex>", text)
    text = re.sub(r"\b\d{5,}\b", "<number>", text)
    text = re.sub(r"\s+", " ", text)
    return text[:200_000].strip()


def similarity(a: bytes, b: bytes) -> float:
    left, right = normalize_text(a), normalize_text(b)
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return round(SequenceMatcher(None, left, right).ratio(), 4)


def title_of(text: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    return html.unescape(re.sub(r"\s+", " ", match.group(1)).strip()) if match else ""


def provider_hint(response: HttpResponse, text: str) -> str:
    haystack = "\n".join(f"{k}: {v}" for k, v in response.headers.items()).lower() + "\n" + text[:10_000]
    for provider, markers in WAF_MARKERS.items():
        if any(marker in haystack for marker in markers):
            return provider
    via = response.headers.get("via", "").strip()
    server = response.headers.get("server", "").strip()
    if via:
        return f"proxy:{via[:50]}"
    return server[:50].lower() if server else "unknown"


def load_custom_signatures(path: str) -> list[dict[str, Any]]:
    if not path:
        return []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Signature file harus berupa JSON array")
    output = []
    for item in data:
        if not isinstance(item, dict) or not item.get("endpoint") or not item.get("pattern"):
            raise ValueError("Setiap signature membutuhkan endpoint dan pattern")
        re.compile(str(item["pattern"]))
        output.append(item)
    return output


def git_signature(endpoint: str, body: bytes, custom: list[dict[str, Any]]) -> tuple[bool, str, int]:
    text = body.decode("utf-8", errors="replace")
    first = text.splitlines()[0].strip() if text.splitlines() else ""
    oid = r"[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?"
    builtins = [
        (endpoint == "/.git/HEAD" and bool(re.fullmatch(r"ref:\s+refs/heads/[A-Za-z0-9._/-]+", first)), "Git HEAD symbolic reference", 98),
        (endpoint == "/.git/HEAD" and bool(re.fullmatch(oid, first)), "Git detached HEAD object ID", 96),
        (endpoint == "/.git/config" and bool(re.search(r"(?mi)^\s*\[core\]\s*$", text)) and bool(re.search(r"repositoryformatversion\s*=", text, re.I)), "Git config core section", 98),
        (endpoint == "/.git/config" and bool(re.search(r"(?mi)^\s*\[remote\s+\"[^\"]+\"\]\s*$", text)), "Git config remote section", 92),
        (endpoint == "/.git/packed-refs" and (bool(re.search(r"(?m)^# pack-refs with:", text)) or bool(re.search(rf"(?m)^{oid}\s+refs/", text))), "Git packed-refs format", 97),
        (endpoint.startswith("/.git/refs/") and bool(re.fullmatch(oid, first)), "Git ref object ID", 96),
        (endpoint == "/.git/logs/HEAD" and bool(re.search(rf"(?m)^{oid}\s+{oid}\s+.+", text)), "Git reflog entry", 95),
        (endpoint == "/.git/index" and body.startswith(b"DIRC"), "Git index DIRC magic", 99),
        (endpoint == "/.git/objects/info/packs" and bool(re.search(rf"(?m)^P pack-{oid}\.pack$", text)), "Git object pack listing", 96),
    ]
    for matched, reason, score in builtins:
        if matched:
            return True, reason, score
    for item in custom:
        endpoint_rule = str(item["endpoint"])
        if endpoint_rule not in {"*", endpoint}:
            continue
        if re.search(str(item["pattern"]), text, re.M):
            score = max(1, min(int(item.get("score", 80)), 100))
            return True, str(item.get("reason", "Custom Git signature")), score
    return False, "", 0


def confidence_level(score: int) -> str:
    if score >= 85:
        return "HIGH"
    if score >= 60:
        return "MEDIUM"
    return "LOW"


def recommendation(classification: str, advanced_authorized: bool = False) -> str:
    actions = {
        "confirmed_exposure": "Validasi manual minimum tanpa repository dumping; dokumentasikan signature, hash, scope, lalu laporkan sesuai kebijakan program.",
        "probable_exposure": "Tinjau signature dan header secara non-destruktif sebelum membuat laporan.",
        "soft_404": "Tidak perlu tindakan; respons sangat mirip dengan baseline path acak.",
        "spa_fallback": "Tidak perlu tindakan; aplikasi mengembalikan shell HTML yang sama untuk path berbeda.",
        "custom_error": "Validasi manual singkat; jangan menyimpulkan hanya dari HTTP 2xx.",
        "waf_challenge": "Kurangi rate. Tool tidak menjalankan evasion otomatis; gunakan hanya variasi yang tertulis dalam policy program.",
        "access_control_detected": "Kontrol akses aktif. Validasi lanjutan hanya jika policy program mengizinkannya secara tertulis.",
        "rate_limited": "Hentikan atau perlambat request dan hormati Retry-After.",
        "protected": "Tidak ada bukti exposure; endpoint tidak tersedia atau ditolak.",
        "redirect_in_scope": "Tujuan redirect masih in-scope; validasi sebagai target terpisah tanpa mengikuti redirect otomatis.",
        "redirect_out_of_scope": "Jangan ikuti redirect karena tujuan berada di luar scope atau resolve ke alamat terlarang.",
        "upstream_error": "Lakukan retest tunggal dengan backoff; 5xx bukan bukti exposure.",
        "suspicious": "Tinjau manual secara non-destruktif; bukti belum cukup.",
        "not_exposed": "Tidak ada signature Git yang valid.",
        "dns_no_record": "Tidak ada DNS record; jangan retry pada run ini.",
        "dns_error": "Periksa resolver dan konektivitas sebelum mengulang.",
        "connect_timeout": "Satu retest dengan timeout lebih longgar dapat dilakukan jika policy mengizinkan.",
        "read_timeout": "Satu retest dengan max-time lebih longgar dapat dilakukan.",
        "tls_error": "Periksa konfigurasi TLS; jangan menonaktifkan validasi kecuali policy dan target mengharuskan.",
        "tls_hostname_mismatch": "Periksa hostname/SNI; gunakan --insecure hanya jika diizinkan dan diperlukan.",
        "connection_refused": "Tidak ada layanan pada port tersebut; jangan retry berulang.",
        "connection_reset": "Lakukan paling banyak satu retest dengan rate rendah.",
        "proxy_error": "Periksa konfigurasi proxy sebelum mengulang.",
        "unsupported_protocol": "Gunakan hanya HTTP/HTTPS yang didukung.",
        "redirect_loop": "Jangan follow redirect otomatis; tinjau rantai redirect secara manual dan tetap dalam scope.",
        "body_too_large": "Respons melebihi batas body. Jangan menaikkan batas tanpa alasan; tinjau metadata dan content type.",
        "network_error": "Periksa DNS, TLS, koneksi, dan timeout sebelum mengulang.",
    }
    result = actions.get(classification, actions["suspicious"])
    if advanced_authorized and classification in {"waf_challenge", "access_control_detected"}:
        result += " Mode authorized-advanced aktif dan metadata izin dicatat, tetapi tidak ada bypass otomatis."
    return result


def analyze(
    *,
    target: str,
    host: str,
    endpoint: str,
    phase: int,
    response: HttpResponse,
    baselines: list[HttpResponse],
    scope: ScopeEngine,
    custom_signatures: list[dict[str, Any]],
    advanced_authorized: bool,
    store_snippet: bool,
    snippet_bytes: int,
) -> EndpointResult:
    body = response.body
    text = normalize_text(body)
    provider = provider_hint(response, text)
    location = response.headers.get("location", "")
    baseline_similarities = [similarity(body, item.body) for item in baselines if item.body or item.status]
    max_similarity = max(baseline_similarities, default=0.0)
    baseline_pair_similarity = 1.0
    if len(baselines) >= 2:
        baseline_pair_similarity = similarity(baselines[0].body, baselines[1].body)
    baseline_titles = [title_of(normalize_text(item.body)) for item in baselines]
    response_title = title_of(text)
    same_title = bool(response_title) and any(response_title == title for title in baseline_titles if title)
    html_like = "<html" in text or "<!doctype" in text or "text/html" in response.content_type.lower()
    signature, signature_reason, signature_score = git_signature(endpoint, body, custom_signatures)
    evidence: list[EvidencePoint] = []
    classification = "not_exposed"
    score = 10
    reason = "Tidak ada signature Git yang cocok"

    if response.network_error:
        classification = response.network_error
        score = 0
        reason = response.error or "Tidak memperoleh respons HTTP"
        evidence.append(EvidencePoint("network", 0, classification))
    elif 300 <= response.status < 400:
        allowed, scope_reason = scope.redirect_allowed(location, target) if location else (False, "Location header tidak tersedia")
        classification = "redirect_in_scope" if allowed else "redirect_out_of_scope"
        score = 85 if location else 40
        reason = f"Redirect ke {location or 'tujuan tidak tersedia'}; {scope_reason}"
        evidence.append(EvidencePoint("redirect", score, scope_reason))
    elif response.status == 429:
        classification, score, reason = "rate_limited", 90, "Server menerapkan rate limit"
        evidence.append(EvidencePoint("http_status", 90, "HTTP 429"))
    elif 500 <= response.status < 600:
        classification, score, reason = "upstream_error", 65, "Respons 5xx dari origin/CDN/proxy/WAF"
        evidence.append(EvidencePoint("http_status", 65, f"HTTP {response.status}"))
    elif signature and 200 <= response.status < 300:
        classification = "confirmed_exposure" if signature_score >= 96 else "probable_exposure"
        score = signature_score
        reason = signature_reason
        evidence.append(EvidencePoint("git_signature", signature_score, signature_reason))
        if response.content_type.lower().startswith(("text/plain", "application/octet-stream")):
            applied = min(1, 100 - score)
            if applied:
                evidence.append(EvidencePoint("content_type", applied, response.content_type))
                score += applied
        if max_similarity < 0.45:
            applied = min(1, 100 - score)
            if applied:
                evidence.append(EvidencePoint("baseline_difference", applied, f"Similarity {max_similarity:.2f}"))
                score += applied
        elif max_similarity >= 0.92:
            evidence.append(EvidencePoint("baseline_similarity", -30, f"Similarity {max_similarity:.2f}"))
            score = max(55, score - 30)
            classification = "probable_exposure"
            reason += "; namun respons mirip baseline"
    elif response.status in {401, 403}:
        known_edge = provider in WAF_MARKERS
        challenge = any(marker in text for marker in ("checking your browser", "security verification", "captcha", "request blocked", "ray id"))
        if known_edge or challenge:
            classification, score, reason = "waf_challenge", 80, f"Access denied/challenge terdeteksi ({provider})"
        else:
            classification, score, reason = "access_control_detected", 80, "Kontrol akses menolak endpoint"
        evidence.append(EvidencePoint("access_control", score, reason))
    elif response.status in {404, 405, 410}:
        classification, score, reason = "protected", 90, "Endpoint tidak tersedia atau ditolak"
        evidence.append(EvidencePoint("http_status", 90, f"HTTP {response.status}"))
    elif 200 <= response.status < 300:
        if max_similarity >= 0.94 and html_like and same_title:
            classification, score, reason = "spa_fallback", 96, "HTML dan title sangat mirip dengan baseline"
        elif max_similarity >= 0.90:
            classification, score, reason = "soft_404", 94, "Respons sangat mirip dengan baseline"
        elif html_like and any(marker in text for marker in ERROR_MARKERS):
            classification, score, reason = "custom_error", 82, "Respons 2xx terlihat seperti halaman error/challenge"
        else:
            classification, score, reason = "suspicious", 45, "Respons 2xx tanpa signature Git yang kuat"
        evidence.append(EvidencePoint("baseline_similarity", score, f"Max similarity {max_similarity:.2f}"))
    elif 400 <= response.status < 500:
        classification, score, reason = "protected", 80, "Respons 4xx tanpa signature Git"
        evidence.append(EvidencePoint("http_status", 80, f"HTTP {response.status}"))

    snippet = ""
    if store_snippet and body:
        snippet = redact_text(body[:snippet_bytes].decode("utf-8", errors="replace"))
    verdict = CLASS_TO_VERDICT.get(classification, "manual_review")
    return EndpointResult(
        timestamp=now_iso(),
        target=target,
        host=host,
        endpoint=endpoint,
        phase=phase,
        status=f"{response.status:03d}" if response.status else "000",
        classification=classification,
        verdict=verdict,
        heuristic_score=score,
        confidence_level=confidence_level(score),
        reason=reason,
        recommendation=recommendation(classification, advanced_authorized),
        provider_hint=provider,
        similarity=max_similarity,
        baseline_consistency=baseline_pair_similarity,
        content_type=response.content_type or "unknown",
        size_bytes=response.size_bytes,
        time_seconds=response.time_seconds,
        remote_ip=response.remote_ip,
        http_version=response.http_version,
        curl_rc=response.curl_rc,
        retries=response.retries,
        network_error=response.network_error,
        effective_url=response.effective_url,
        location=location,
        body_sha256=sha256(body),
        baseline_sha256=[sha256(item.body) for item in baselines],
        evidence=evidence,
        redacted_snippet=snippet,
    )

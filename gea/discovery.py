from __future__ import annotations

import json
import shutil
import subprocess
from urllib.parse import quote

from .scope import normalize_host


def wildcard_root(value: str) -> str:
    host = normalize_host(value[2:] if value.strip().startswith("*.") else value)
    return host


def discover_subfinder(root: str) -> list[str]:
    if not shutil.which("subfinder"):
        raise ValueError("subfinder tidak ditemukan")
    process = subprocess.run(["subfinder", "-silent", "-d", root], capture_output=True, text=True, check=False)
    return [normalize_host(line) for line in process.stdout.splitlines() if normalize_host(line)]


def discover_crtsh(root: str, user_agent: str) -> list[str]:
    url = f"https://crt.sh/?q={quote('%.' + root)}&output=json"
    process = subprocess.run(
        ["curl", "--silent", "--show-error", "--fail", "--compressed", "--max-time", "30", "--user-agent", user_agent, url],
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        return []
    try:
        data = json.loads(process.stdout)
    except json.JSONDecodeError:
        return []
    hosts: list[str] = []
    for item in data:
        for name in str(item.get("name_value", "")).splitlines():
            host = normalize_host(name.removeprefix("*."))
            if host:
                hosts.append(host)
    return hosts


def discover(root: str, method: str, user_agent: str) -> list[str]:
    if method == "none":
        return [root]
    if method == "subfinder":
        return [root, *discover_subfinder(root)]
    if method == "crtsh":
        return [root, *discover_crtsh(root, user_agent)]
    if method == "auto":
        if shutil.which("subfinder"):
            return [root, *discover_subfinder(root)]
        return [root, *discover_crtsh(root, user_agent)]
    raise ValueError(f"Enumerator tidak valid: {method}")

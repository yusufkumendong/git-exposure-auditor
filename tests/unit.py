#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from gea.analyzer import git_signature, similarity
from gea.http_client import classify_network_error
from gea.policy import ProgramPolicy
from gea.scope import ScopeEngine, rule_matches
from gea.util import redact_text


def main() -> None:
    assert rule_matches("api.example.com", "*.example.com")
    assert not rule_matches("example.net", "*.example.com")
    scope = ScopeEngine(includes=["*.example.com"], excludes=["admin.example.com"])
    assert scope.host_allowed("api.example.com")
    assert not scope.host_allowed("admin.example.com")
    assert classify_network_error(6, "Could not resolve host", 0) == "dns_no_record"
    assert classify_network_error(60, "certificate subject name mismatch", 0) == "tls_hostname_mismatch"
    assert git_signature("/.git/HEAD", b"ref: refs/heads/main\n", [])[0]
    assert similarity(b"hello 123456", b"hello 987654") == 1.0
    assert "hunter2" not in redact_text("password=hunter2")
    with tempfile.TemporaryDirectory() as tmp:
        policy = Path(tmp) / "policy.json"
        policy.write_text(json.dumps({
            "program": {
                "name": "Unit Program",
                "policy_reference": "snapshot-1",
                "authorization_confirmed": True,
                "bypass_permission_confirmed": True,
            },
            "permissions": {"advanced_validation": True},
        }), encoding="utf-8")
        loaded = ProgramPolicy.from_file(str(policy))
        assert loaded.program_name == "Unit Program"
        assert loaded.snapshot()["automatic_evasion"] is False
    print("Unit test: PASS")


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ProgramPolicy:
    program_name: str
    policy_reference: str
    authorization_confirmed: bool
    bypass_permission_confirmed: bool
    permissions: dict[str, bool] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_file(cls, path: str) -> "ProgramPolicy":
        file_path = Path(path)
        if not file_path.is_file():
            raise ValueError(f"Policy file tidak ditemukan: {path}")
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Policy file harus JSON valid: {exc}") from exc
        program = data.get("program", {})
        permissions = data.get("permissions", {})
        policy = cls(
            program_name=str(program.get("name", "")).strip(),
            policy_reference=str(program.get("policy_reference", "")).strip(),
            authorization_confirmed=bool(program.get("authorization_confirmed", False)),
            bypass_permission_confirmed=bool(program.get("bypass_permission_confirmed", False)),
            permissions={str(k): bool(v) for k, v in permissions.items()},
            raw=data,
        )
        policy.validate()
        return policy

    def validate(self) -> None:
        missing = []
        if not self.program_name:
            missing.append("program.name")
        if not self.policy_reference:
            missing.append("program.policy_reference")
        if not self.authorization_confirmed:
            missing.append("program.authorization_confirmed=true")
        if not self.bypass_permission_confirmed:
            missing.append("program.bypass_permission_confirmed=true")
        if not self.permissions.get("advanced_validation", False):
            missing.append("permissions.advanced_validation=true")
        if missing:
            raise ValueError("Policy advanced tidak lengkap: " + ", ".join(missing))

    def snapshot(self) -> dict[str, Any]:
        return {
            "program_name": self.program_name,
            "policy_reference": self.policy_reference,
            "authorization_confirmed": self.authorization_confirmed,
            "bypass_permission_confirmed": self.bypass_permission_confirmed,
            "permissions": self.permissions,
            "automatic_evasion": False,
            "repository_dumping": False,
            "credential_testing": False,
        }

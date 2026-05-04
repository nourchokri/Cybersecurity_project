from __future__ import annotations

from dataclasses import dataclass

from .config import CertDbConfig
from .identity import IdentityTool
from .policy import PolicyTool
from .rule_library import RuleLibraryTool
from .telemetry import TelemetryTool


@dataclass(frozen=True)
class CertTools:
    """Convenience container that matches the grouped tool names you want."""

    identity: IdentityTool
    telemetry: TelemetryTool
    policy: PolicyTool
    rule_library: RuleLibraryTool

    @staticmethod
    def from_db(config: CertDbConfig) -> "CertTools":
        cfg = config.resolve()
        return CertTools(
            identity=IdentityTool(cfg),
            telemetry=TelemetryTool(cfg),
            policy=PolicyTool(cfg),
            rule_library=RuleLibraryTool(cfg),
        )

    @staticmethod
    def from_env() -> "CertTools":
        return CertTools.from_db(CertDbConfig.from_env())

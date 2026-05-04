"""CERT + LDAP tool layer.

This package implements the grouped tools intended for the CERT insider-threat dataset:
- identity.get_user_context
- telemetry.get_user_summary
- telemetry.get_user_baseline
- telemetry.get_deviations
- policy.get_thresholds
- rule_library.explain

The design goal is to keep tool outputs compact and LLM-friendly (aggregations, not raw rows).
"""

from .config import CertDbConfig
from .tool_accessor import CertTools

__all__ = ["CertDbConfig", "CertTools"]

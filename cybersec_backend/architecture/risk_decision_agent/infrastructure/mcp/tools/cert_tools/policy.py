from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from .config import CertDbConfig


@dataclass
class PolicyTool:
    config: CertDbConfig

    def __post_init__(self) -> None:
        self.config = self.config.resolve()

    def get_thresholds(self) -> Dict[str, float]:
        """policy.get_thresholds()

        By default, reuses the existing mock JSON policy thresholds if configured.
        Otherwise returns safe defaults.
        """

        if self.config.policy_json is None:
            return {"low_max": 0.4, "medium_max": 0.7}

        p = Path(self.config.policy_json)
        with open(p, "r", encoding="utf-8") as f:
            obj = json.load(f)

        return {
            "low_max": float(obj.get("low_max", 0.4)),
            "medium_max": float(obj.get("medium_max", 0.7)),
        }

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import CertDbConfig


@dataclass
class RuleLibraryTool:
    config: CertDbConfig

    def __post_init__(self) -> None:
        self.config = self.config.resolve()
        self._rules: Optional[Dict[str, Any]] = None

    def _load(self) -> Dict[str, Any]:
        if self._rules is not None:
            return self._rules
        if self.config.rule_library_json is None:
            self._rules = {}
            return self._rules

        p = Path(self.config.rule_library_json)
        with open(p, "r", encoding="utf-8") as f:
            self._rules = json.load(f)
        return self._rules

    def explain(self, rule_ids: List[str]) -> Dict[str, Optional[str]]:
        """rule_library.explain(rule_ids[])

        Returns a mapping of rule_id -> description (or None if unknown).
        """

        rules = self._load()
        out: Dict[str, Optional[str]] = {}
        for rid in rule_ids or []:
            r = rules.get(rid)
            if isinstance(r, dict):
                out[rid] = r.get("description")
            elif isinstance(r, str):
                out[rid] = r
            else:
                out[rid] = None
        return out

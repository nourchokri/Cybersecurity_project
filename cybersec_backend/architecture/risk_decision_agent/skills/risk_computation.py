"""Deterministic risk helpers.

This project uses the LLM for contextual analysis and then applies bounded math
in the Decision Agent. This skill provides deterministic, policy-like helpers
used by the agent (risk level classification, decision fallback, and recommended
action text).
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class RiskComputationSkill:
    """Internal skill: deterministic helpers for scoring/decision."""
    
    def classify_risk_level(
        self,
        risk_score: float,
        thresholds: Optional[Dict[str, float]] = None
    ) -> str:
        """
        Classify risk score into LOW/MEDIUM/HIGH.
        
        Default thresholds:
        - LOW: risk_score <= 0.4
        - MEDIUM: 0.4 < risk_score <= 0.7
        - HIGH: risk_score > 0.7
        
        Returns: "LOW", "MEDIUM", or "HIGH"
        """
        if thresholds is None:
            thresholds = {"low_max": 0.4, "medium_max": 0.7}
        
        low_max = thresholds.get("low_max", 0.4)
        medium_max = thresholds.get("medium_max", 0.7)
        
        if risk_score <= low_max:
            return "LOW"
        elif risk_score <= medium_max:
            return "MEDIUM"
        else:
            return "HIGH"
    
    def generate_decision(
        self,
        risk_level: str,
        user_context: Optional[Dict[str, Any]] = None,
        asset_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate decision based on risk level with context overrides.
        
        Base mapping:
        - LOW → ALLOW
        - MEDIUM → MONITOR
        - HIGH → ESCALATE
        
        Overrides:
        - MEDIUM + high privilege user → ALLOW
        - MEDIUM + high sensitivity asset → ESCALATE
        
        Returns: "ALLOW", "MONITOR", "ESCALATE", or "BLOCK"
        """
        # Base decision mapping
        decision_map = {
            "LOW": "ALLOW",
            "MEDIUM": "MONITOR",
            "HIGH": "ESCALATE"
        }
        
        decision = decision_map.get(risk_level, "MONITOR")
        
        # Apply overrides for MEDIUM risk
        if risk_level == "MEDIUM":
            # High privilege user override
            if user_context and user_context.get("privilege_level") == "high":
                decision = "ALLOW"
            
            # High sensitivity asset override (takes precedence)
            if asset_context and asset_context.get("sensitivity_level") == "high":
                decision = "ESCALATE"
        
        return decision
    
    def recommend_action(self, risk_level: str, threat_classification: str) -> str:
        """
        Generate recommended action based on risk level and threat type.
        
        Returns: Human-readable action recommendation string
        """
        if risk_level == "LOW":
            return "log event for audit trail"
        
        elif risk_level == "MEDIUM":
            if threat_classification == "insider_threat":
                return "increase monitoring and notify team lead"
            elif threat_classification == "external_compromise":
                return "enable enhanced logging and alert security team"
            else:
                return "monitor closely and prepare incident response"
        
        else:  # HIGH
            if threat_classification == "insider_threat":
                return "restrict account and notify SOC analyst"
            elif threat_classification == "external_compromise":
                return "isolate affected systems and initiate incident response"
            else:
                return "escalate to security operations center immediately"

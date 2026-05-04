from __future__ import annotations

import json
import os
import ast
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
from openai import OpenAI


def _maybe_load_dotenv() -> None:
    """Load environment variables from a local .env file if present.

    This keeps setup simple on Windows where users often prefer a `.env` file.
    It does not override environment variables that are already set.
    """

    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[3] / ".env",  # cybersec_backend/.env
        Path(__file__).resolve().parent / ".env",
    ]
    env_path = next((p for p in candidates if p.exists()), None)
    if env_path is None:
        return

    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if not key:
                continue
            os.environ.setdefault(key, value)
    except Exception:
        # If the .env can't be read/parsed, we fall back to normal env var behavior.
        return


@dataclass(frozen=True)
class LLMConfig:
    
    base_url: str = "https://tokenfactory.esprit.tn/api"
    model: str = "hosted_vllm/Llama-3.1-70B-Instruct"
    api_key_env: str = "ESPRIT_API_KEY"
    #base_url: str = "https://api.groq.com/openai/v1"
    #model: str = "llama-3.3-70b-versatile"
    #api_key_env: str = "GROQ_API_KEY"
    insecure_tls: bool = False
    temperature: float = 0.0


class LLMReasoner:
    """Small wrapper to generate ReAct thoughts/summaries via an LLM.

    This is intentionally optional: the agent logic and tool calls can remain
    deterministic; the LLM is used to produce human-readable reasoning text.
    """

    def __init__(self, config: LLMConfig):
        _maybe_load_dotenv()
        api_key = os.getenv(config.api_key_env)
        if not api_key:
            raise RuntimeError(
                f"Missing API key. Set env var {config.api_key_env} (or put it in a .env file) to your TokenFactory key."
            )

        # NOTE: insecure_tls=True disables TLS certificate validation.
        # Use only if your environment requires it.
        http_client = httpx.Client(verify=not config.insecure_tls, timeout=60.0)
        self._client = OpenAI(api_key=api_key, base_url=config.base_url, http_client=http_client)
        self._model = config.model
        self._temperature = float(config.temperature)
        self._supports_response_format: Optional[bool] = None

    def analyze_contextual_risk(
        self,
        *,
        event: Dict[str, Any],
        context: Dict[str, Any],
        language: str = "en",
    ) -> Dict[str, Any]:
        """Analyze risk with full context and provide adjustment reasoning.
        
        This is the core intelligence - LLM reasons about context and adjusts risk.
        
        Returns:
          {
            "base_score_analysis": "...",
            "risk_factors": ["...", "..."],
            "mitigating_factors": ["...", "..."],
            "risk_adjustment": float,  # -0.3 to +0.3
            "adjustment_reasoning": "...",
            "recommended_decision": "ALLOW|MONITOR|ESCALATE|BLOCK",
            "decision_reasoning": "...",
            "confidence": "high|medium|low"
          }
        """
        sys_prompt = (
            "You are an expert SOC analyst in a Decision Agent. "
            "Your job is to analyze security events with full business context and make intelligent risk adjustments. "
            "You receive a base anomaly score from the Pattern Agent, plus context about the user, asset, and history. "
            "Your task: Decide if the base score should be adjusted up or down based on context. "
            "Return strict JSON only."
        )
        
        user_payload = {
            "event": event,
            "context": context,
            "task": (
                "Analyze this security event with full context. "
                "Identify risk factors (increase risk) and mitigating factors (decrease risk). "
                "Recommend a risk adjustment (-0.3 to +0.3) and explain your reasoning. "
                "Make a decision (ALLOW/MONITOR/ESCALATE/BLOCK) with justification."
            ),
            "guidelines": {
                "risk_factors": [
                    "Crown jewel asset access",
                    "After-hours timing without on-call",
                    "Recent incidents or policy violations",
                    "Unusual behavior vs baseline",
                    "High privilege + high sensitivity combination",
                    "Bulk data transfer or exfiltration patterns"
                ],
                "mitigating_factors": [
                    "High user trust score (>0.8)",
                    "Legitimate business justification",
                    "On-call or approved maintenance window",
                    "Consistent with user's role and responsibilities"
                ],
                "adjustment_range": "-0.3 to +0.3 (cannot adjust more than this)"
            },
            "output_schema": {
                "base_score_analysis": "string (analyze the base score from Pattern Agent)",
                "risk_factors": ["list of factors that increase risk"],
                "mitigating_factors": ["list of factors that decrease risk"],
                "risk_adjustment": "number (-0.3 to +0.3)",
                "adjustment_reasoning": "string (explain why this adjustment)",
                "recommended_decision": "ALLOW|MONITOR|ESCALATE|BLOCK",
                "decision_reasoning": "string (justify the decision with evidence)",
                "confidence": "high|medium|low"
            }
        }
        
        resp = self._chat_completion(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": "Analyze and return strict JSON: " + json.dumps(user_payload, ensure_ascii=False)},
            ],
            temperature=self._temperature,
            max_tokens=2048,
        )
        
        text = _message_to_text(resp.choices[0].message)
        parsed = _parse_json_loose(text)
        
        if not isinstance(parsed, dict) or "risk_adjustment" not in parsed:
            _maybe_debug_dump_raw("analyze_contextual_risk", text)
            return {
                "base_score_analysis": "Analysis failed",
                "risk_factors": ["LLM analysis failed"],
                "mitigating_factors": [],
                "risk_adjustment": 0.0,
                "adjustment_reasoning": "Unable to analyze context",
                "recommended_decision": "MONITOR",
                "decision_reasoning": "Defaulting to MONITOR due to analysis failure",
                "confidence": "low"
            }
        return parsed

    def generate_reasoning(
        self,
        *,
        event: Dict[str, Any],
        context: Dict[str, Any],
        computed: Dict[str, Any],
        language: str = "en",
    ) -> Dict[str, Any]:
        """Ask the LLM for a concise reasoning trace + summary.

        Returns a dict:
          {
            "thoughts": {"1": "...", "2": "...", ...},
            "reasoning_summary": "..."
          }
        """

        # English-only prompts (French removed by design).
        sys_prompt = (
            "You are a helpful, concise cybersecurity assistant. "
            "Explain the reasoning of a Risk & Decision agent in ReAct style (Thought/Action/Observation). "
            "Do not invent data: rely only on the provided event, context, and computed values."
        )
        thought_steps = [
            "1: receive the event",
            "2: need asset context",
            "3: need user context",
            "4: need policy thresholds",
            "5: incident history (depending on cold_start)",
            "6: explain triggered rules",
            "7: compute likelihood",
            "8: compute impact",
            "9: compute risk + decision",
        ]
        constraints = [
            "Short answers (1-2 sentences per thought)",
            "Do not add extra steps",
            "Do not mention tools that are not present",
        ]
        user_instruction = "Generate strict JSON with keys thoughts and reasoning_summary. Data: "

        user_payload = {
            "event": event,
            "context": context,
            "computed": computed,
            "request": {
                "format": "json",
                "thought_steps": thought_steps,
                "constraints": constraints,
            },
        }

        resp = self._chat_completion(
            messages=[
                {"role": "system", "content": sys_prompt},
                {
                    "role": "user",
                    "content": user_instruction + json.dumps(user_payload, ensure_ascii=False),
                },
            ],
            temperature=self._temperature,
            max_tokens=2048,
        )

        text = _message_to_text(resp.choices[0].message)

        # Try to parse strict JSON; if the model wraps it in text, extract the first JSON object.
        parsed = _parse_json_loose(text)
        if not isinstance(parsed, dict) or "thoughts" not in parsed:
            _maybe_debug_dump_raw("generate_reasoning", text)
            raise RuntimeError(
                "LLM did not return the expected JSON format (expected an object with key 'thoughts'). "
                f"Raw (truncated): { _truncate(text) }"
            )
        return parsed

    def next_react_step(
        self,
        *,
        event: Dict[str, Any],
        history: List[Dict[str, Any]],
        allowed_tools: List[str],
        policy: Dict[str, Any],
        language: str = "en",
    ) -> Dict[str, Any]:
        """Produce the next ReAct step.

        The model must return strict JSON:
          - Tool step:
              {"type":"tool","thought":"...","tool":"asset_db.lookup","args":{...}}
          - Final step:
              {"type":"final","thought":"...","assessment":{...}}

        The executor (Python) will only run tools from allowed_tools.
        """

        sys_prompt = (
            "You are a Risk & Decision cybersecurity agent operating in ReAct (Thought->Action->Observation). "
            "Each turn choose ONE action: call an allowed tool, or return the final assessment. "
            "The 'thought' field is REQUIRED and must never be empty (one concise sentence). "
            "Do not invent observations; call tools when needed. "
            "Tool names must match EXACTLY one of allowed_tools (no other tools). "
            "There is NO tool named 'risk_matrix.get_impact_likelihood' (never call it). "
            "As soon as you have enough context (asset, user, policy_thresholds, and incident_history if cold_start=false), produce the FINAL answer. "
            "IMPORTANT: There is NO tool for 'threat severity' and NO tool named 'produce_final_assessment'. "
            "Threat severity must be computed using the provided mapping (threat_severity). "
            "IMPORTANT MATH: risk_score MUST equal risk R where R = likelihood * impact (after clamping). "
            "In the final assessment, include a decision_explanation that explicitly justifies the decision using the computed risk_score, policy thresholds, and key evidence. "
            "Return strict JSON only."
        )

        instructions = {
            "allowed_tools": allowed_tools,
            "tools_contracts": {
                "asset_db.lookup": {"args": {"entity_id": "string"}},
                "user_db.lookup": {"args": {"user_id": "string"}},
                "policy_db.get_thresholds": {"args": {}},
                "incident_history.lookup": {"args": {"user_id": "string"}},
                "risk_matrix.get_risk_matrix": {"args": {}},
                "rule_library.get_rule_explanation": {"args": {"rule_id": "string"}},
            },
            "final_assessment_schema": {
                "event_id": "string",
                "risk_score": "number [0,1] (MUST equal likelihood*impact)",
                "risk_level": "LOW|MEDIUM|HIGH",
                "decision": "ALLOW|MONITOR|ESCALATE|BLOCK",
                "likelihood": "number [0,1]",
                "impact": "number [0,1]",
                "reasoning_summary": "string",
                "recommended_action": "string",
                "decision_explanation": "string",
                "likelihood_breakdown": {
                    "Sc": "number (event.combined_score)",
                    "Nd": "number (default 0 if missing)",
                    "Nr": "number (default 0 if missing)",
                    "base": "number",
                    "confidence_multiplier": "number",
                    "cold_start_multiplier": "number",
                    "likelihood": "number",
                },
                "impact_breakdown": {
                    "T": "number (from threat_severity mapping using event.threat_classification)",
                    "S": "number (event.dimension_scores.sensitivity)",
                    "impact": "number",
                },
                "risk_breakdown": {
                    "formula": "string (must be 'risk_score = likelihood * impact')",
                    "product": "number",
                },
                "threshold_comparison": {
                    "low_max": "number",
                    "medium_max": "number",
                    "rule": "string (LOW if risk_score<=low_max; MEDIUM if <=medium_max; else HIGH)",
                },
            },
            "decision_policy": {
                "LOW": {"decision": "ALLOW", "recommended_action": "allow activity and log for audit"},
                "MEDIUM": {"decision": "MONITOR", "recommended_action": "monitor activity and request user verification"},
                "HIGH": {"decision": "ESCALATE", "recommended_action": "restrict account and notify SOC analyst"},
                "note": "Decision should match risk_level unless explicitly justified; prefer this mapping.",
            },
            "math_requirements": {
                "likelihood": (
                    "Let Sc = event.combined_score. Let Nd = event.Nd if present else 0. Let Nr = event.Nr if present else 0. "
                    "Compute base = Sc + 0.05*Nd + 0.05*log(Nr+1). "
                    "Then: if confidence=='low' multiply by 0.8, otherwise multiply by 1.0. "
                    "Then: if cold_start==true multiply by 0.85, otherwise multiply by 1.0. "
                    "Clamp L to [0,1]."
                ),
                "impact": "I = 0.6*T + 0.4*S where T is threat severity mapping and S is dimension_scores.sensitivity; clamp to [0,1]",
                "threat_severity": {
                    "insider_threat": 0.85,
                    "external_compromise": 0.8,
                    "recon_preceded_action": 0.6,
                    "correlated_unknown": 0.5,
                    "default": 0.4,
                },
                "risk": "R = L * I",
            },
        }

        user_payload = {
            "event": event,
            "history": history,
            "policy": policy,
            "instructions": instructions,
        }

        resp = self._chat_completion(
            messages=[
                {"role": "system", "content": sys_prompt},
                {
                    "role": "user",
                    "content": (
                        "Return ONLY strict JSON for the next step (no markdown, no extra keys). "
                        "Valid shapes:\n"
                        "- Tool: {\"type\":\"tool\",\"thought\":\"...\",\"tool\":\"asset_db.lookup\",\"args\":{...}}\n"
                        "- Final: {\"type\":\"final\",\"thought\":\"...\",\"assessment\":{...}}\n"
                        "Input: "
                        + json.dumps(user_payload, ensure_ascii=False)
                    ),
                },
            ],
            temperature=self._temperature,
            max_tokens=700,
        )

        text = _message_to_text(resp.choices[0].message)
        parsed = _parse_json_loose(text)
        normalized = _normalize_react_step(parsed)
        if normalized is None:
            _maybe_debug_dump_raw("next_react_step", text)
            raise RuntimeError(
                "LLM did not return the expected JSON step format. "
                "Tip: set env var LLM_DEBUG_RAW=1 to print the raw model output. "
                f"Raw (truncated): { _truncate(text) }"
            )
        return normalized

    def final_assessment(
        self,
        *,
        event: Dict[str, Any],
        history: List[Dict[str, Any]],
        policy: Dict[str, Any],
        language: str = "en",
    ) -> Dict[str, Any]:
        """Force the model to return the final assessment JSON (no tool calls)."""

        # English-only prompts (French removed by design).
        sys_prompt = (
            "You are a Risk & Decision cybersecurity agent. "
            "You must produce the FINAL assessment now, without calling any tools. "
            "Do not invent data; use the event and the observations already collected. "
            "IMPORTANT MATH: risk_score MUST equal risk R where R = likelihood * impact (after clamping). "
            "Include a decision_explanation that justifies the decision using risk_score, policy thresholds, and key evidence. "
            "Return strict JSON only."
        )

        user_payload = {
            "event": event,
            "history": history,
            "policy": policy,
            "decision_policy": {
                "LOW": {"decision": "ALLOW", "recommended_action": "allow activity and log for audit"},
                "MEDIUM": {"decision": "MONITOR", "recommended_action": "monitor activity and request user verification"},
                "HIGH": {"decision": "ESCALATE", "recommended_action": "restrict account and notify SOC analyst"},
            },
            "output_schema": {
                "event_id": "string",
                "risk_score": "number [0,1] (MUST equal likelihood*impact)",
                "risk_level": "LOW|MEDIUM|HIGH",
                "decision": "ALLOW|MONITOR|ESCALATE|BLOCK",
                "likelihood": "number [0,1]",
                "impact": "number [0,1]",
                "reasoning_summary": "string",
                "recommended_action": "string",
                "decision_explanation": "string",
                "likelihood_breakdown": {
                    "Sc": "number (event.combined_score)",
                    "Nd": "number (default 0 if missing)",
                    "Nr": "number (default 0 if missing)",
                    "base": "number",
                    "confidence_multiplier": "number",
                    "cold_start_multiplier": "number",
                    "likelihood": "number",
                },
                "impact_breakdown": {
                    "T": "number (from threat_severity mapping using event.threat_classification)",
                    "S": "number (event.dimension_scores.sensitivity)",
                    "impact": "number",
                },
                "risk_breakdown": {
                    "formula": "string (must be 'risk_score = likelihood * impact')",
                    "product": "number",
                },
                "threshold_comparison": {
                    "low_max": "number",
                    "medium_max": "number",
                    "rule": "string (LOW if risk_score<=low_max; MEDIUM if <=medium_max; else HIGH)",
                },
            },
        }

        resp = self._chat_completion(
            messages=[
                {"role": "system", "content": sys_prompt},
                {
                    "role": "user",
                    "content": "Return ONLY the final assessment as strict JSON. Input: "
                    + json.dumps(user_payload, ensure_ascii=False),
                },
            ],
            temperature=self._temperature,
            max_tokens=2048,
        )

        text = _message_to_text(resp.choices[0].message)
        parsed = _parse_json_loose(text)

        # Accept either a raw assessment object or a wrapped {type:'final', assessment:{...}}.
        if isinstance(parsed, dict) and "risk_score" in parsed and "risk_level" in parsed:
            return parsed

        normalized = _normalize_react_step(parsed)
        if (
            isinstance(normalized, dict)
            and normalized.get("type") == "final"
            and isinstance(normalized.get("assessment"), dict)
        ):
            return normalized["assessment"]

        _maybe_debug_dump_raw("final_assessment", text)
        raise RuntimeError(
            "LLM did not return a final assessment JSON. "
            f"Raw (truncated): { _truncate(text) }"
        )

    def _chat_completion(self, *, messages: List[Dict[str, str]], temperature: float, max_tokens: int):
        """Chat completion with best-effort JSON enforcement.

        Some OpenAI-compatible backends support response_format={"type":"json_object"}.
        We attempt it once and cache the result.
        """

        kwargs: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        }

        if self._supports_response_format is not False:
            try:
                resp = self._client.chat.completions.create(
                    **kwargs,
                    response_format={"type": "json_object"},
                )
                self._supports_response_format = True
                return resp
            except Exception as e:
                # If the backend doesn't support response_format, fall back without it.
                msg = str(e).lower()
                if "response_format" in msg or "unknown" in msg or "unsupported" in msg:
                    self._supports_response_format = False
                else:
                    # Could be transient; do not permanently disable.
                    pass

        resp = self._client.chat.completions.create(**kwargs)
        return resp


def _normalize_react_step(value: Any) -> Optional[Dict[str, Any]]:
    """Accept slightly-noncompliant model outputs and normalize them.

    Supported variants:
      - a dict with 'type'
      - a dict without 'type' but with 'tool' (=> tool) or 'assessment' (=> final)
      - a list containing a single dict
      - a list of dicts (we pick the first that looks like a step)
      - alternate keys: 'action' instead of 'tool', 'final' instead of 'assessment'
    """

    candidate: Any = value

    if isinstance(candidate, list):
        if len(candidate) == 1:
            candidate = candidate[0]
        else:
            for item in candidate:
                if isinstance(item, dict) and (
                    "type" in item or "tool" in item or "action" in item or "assessment" in item or "final" in item
                ):
                    candidate = item
                    break

    if not isinstance(candidate, dict):
        return None

    out: Dict[str, Any] = dict(candidate)

    step_type = (out.get("type") or out.get("step_type") or out.get("kind") or "").strip().lower()
    if not step_type:
        if "assessment" in out or "final" in out:
            step_type = "final"
        elif "tool" in out or "action" in out:
            step_type = "tool"

    if step_type not in {"tool", "final"}:
        # Some models might say "action" for tool steps.
        if step_type in {"action", "call_tool", "call"}:
            step_type = "tool"
        elif step_type in {"done", "answer", "finish"}:
            step_type = "final"
        else:
            step_type = ""

    if not step_type:
        return None
    out["type"] = step_type

    # Normalize tool fields.
    if out["type"] == "tool":
        if "tool" not in out and "action" in out:
            out["tool"] = out.get("action")
        if "args" not in out:
            out["args"] = out.get("arguments") or out.get("params") or {}
        if not isinstance(out.get("args"), dict):
            # If args came as a list of kv pairs, try to coerce.
            if isinstance(out.get("args"), list):
                try:
                    out["args"] = {str(k): v for k, v in out["args"]}  # type: ignore[misc]
                except Exception:
                    out["args"] = {}

    # Normalize final fields.
    if out["type"] == "final":
        if "assessment" not in out and "final" in out:
            out["assessment"] = out.get("final")

    return out


def _parse_json_loose(text: str) -> Any:
    original = text
    text = text.strip()

    # Strip Markdown code fences if present.
    fenced = _strip_code_fence(text)
    if fenced is not None:
        text = fenced.strip()

    # First try strict JSON.
    try:
        return json.loads(text)
    except Exception:
        pass

    # Extract first balanced JSON object/array from the text.
    snippet = _extract_first_json_snippet(text)
    if snippet is not None:
        try:
            return json.loads(snippet)
        except Exception:
            # As a last resort, accept Python-literal-ish dicts (single quotes) via literal_eval.
            try:
                value = ast.literal_eval(snippet)
                if isinstance(value, (dict, list)):
                    return value
            except Exception:
                pass

    # Final fallback: try scanning the original (pre-fence) text.
    snippet2 = _extract_first_json_snippet(original)
    if snippet2 is not None:
        try:
            return json.loads(snippet2)
        except Exception:
            pass

    raise ValueError("Could not parse JSON from model output")


def _message_to_text(message: Any) -> str:
    """Extract textual content from an OpenAI message object.

    Different OpenAI-compatible backends (and SDK versions) may return:
      - content as a string
      - content as a list of parts
      - content as a dict/object
    """

    content = getattr(message, "content", None)
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for p in content:
            if isinstance(p, str):
                parts.append(p)
            elif isinstance(p, dict):
                # Common shape: {"type":"text","text":"..."}
                if isinstance(p.get("text"), str):
                    parts.append(p["text"])
                else:
                    parts.append(json.dumps(p, ensure_ascii=False))
            else:
                parts.append(str(p))
        return "\n".join(parts)
    if isinstance(content, dict):
        return json.dumps(content, ensure_ascii=False)
    return str(content)


def _truncate(text: str, limit: int = 500) -> str:
    t = (text or "").strip().replace("\r", "")
    if len(t) <= limit:
        return t
    return t[:limit] + "…"


def _strip_code_fence(text: str) -> Optional[str]:
    # Handles ```json ...``` or ``` ...```
    if "```" not in text:
        return None
    parts = text.split("```")
    if len(parts) < 3:
        return None
    # The fenced content is the 2nd chunk.
    fenced = parts[1]
    # Drop an optional leading language tag on the first line.
    lines = fenced.splitlines()
    if lines and lines[0].strip().lower() in {"json", "javascript"}:
        return "\n".join(lines[1:])
    return fenced


def _extract_first_json_snippet(text: str) -> Optional[str]:
    text = text.strip()
    if not text:
        return None

    # Find the first opening brace/bracket.
    start_candidates = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if not start_candidates:
        return None
    start = min(start_candidates)

    opening = text[start]
    closing = "}" if opening == "{" else "]"

    depth = 0
    in_string = False
    string_quote = ""
    escape = False

    for idx in range(start, len(text)):
        ch = text[idx]

        if in_string:
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == string_quote:
                in_string = False
                string_quote = ""
            continue

        if ch in ("\"", "'"):
            in_string = True
            string_quote = ch
            continue

        if ch == opening:
            depth += 1
        elif ch == closing:
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]

    return None


def _maybe_debug_dump_raw(where: str, text: str) -> None:
    if os.getenv("LLM_DEBUG_RAW", "").strip() not in {"1", "true", "yes"}:
        return
    print(f"\n--- RAW LLM OUTPUT ({where}) ---\n{text}\n--- END RAW LLM OUTPUT ---\n", file=sys.stderr)

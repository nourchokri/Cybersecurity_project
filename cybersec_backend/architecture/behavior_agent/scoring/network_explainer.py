"""
LLM explanation generator for network attack detections.
Uses the same Llama-3.1-70B endpoint as your teammate.
Only called when a detection is flagged — never for normal traffic.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def explain(
    label: str,
    score: float,
    triggered_rules: list,
    meta: dict,
    prediction: dict,
) -> str:
    """
    Calls Llama-3.1-70B to generate a SOC analyst explanation.
    Falls back to template if LLM is unavailable.

    Input:
        label:           attack type e.g. "DrDoS_DNS"
        score:           combined score 0-1
        triggered_rules: list of rule strings
        meta:            first event's metadata dict
        prediction:      output from network_model.predict()
    """
    try:
        from django.conf import settings
        api_key  = getattr(settings, 'ESPRIT_API_KEY',  '')
        base_url = getattr(settings, 'ESPRIT_BASE_URL', '')
        model    = getattr(settings, 'ESPRIT_MODEL',
                           'hosted_vllm/Llama-3.1-70B-Instruct')

        if not api_key or not base_url:
            return _template(label, score, triggered_rules, meta)

        from openai import OpenAI
        import httpx

        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=httpx.Client(verify=False),
        )

        prompt = _build_prompt(label, score, triggered_rules, meta, prediction)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a SOC analyst writing concise attack explanations. "
                        "Write exactly 3 sentences. "
                        "Sentence 1: what the ML model detected and its confidence. "
                        "Sentence 2: what this attack does and why it is dangerous. "
                        "Sentence 3: one specific recommended mitigation action. "
                        "No preamble. No bullet points. Facts only."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=120,
        )

        explanation = response.choices[0].message.content.strip()
        logger.info(f"LLM explanation generated for {label} (score={score:.3f})")
        return explanation

    except Exception as e:
        logger.warning(f"LLM explanation failed, using template: {e}")
        return _template(label, score, triggered_rules, meta)


def _build_prompt(label, score, rules, meta, prediction) -> str:
    src_ip    = meta.get("src_ip",         "unknown")
    dst_ip    = meta.get("dst_ip",         "unknown")
    dst_port  = meta.get("dst_port",       "unknown")
    protocol  = meta.get("protocol",       "unknown")
    sent      = meta.get("bytes_sent",     0)
    recv      = meta.get("bytes_received", 0)
    ratio     = round(recv / sent, 1) if sent > 0 else 0

    verdict = (
        "CRITICAL" if score >= 0.85 else
        "HIGH"     if score >= 0.65 else
        "MEDIUM"
    )

    rules_str = ", ".join(rules[:5]) if rules else "none"

    return (
        f"Attack detected by hybrid ML model (Isolation Forest + CatBoost).\n\n"
        f"Detection summary:\n"
        f"  Attack type:          {label}\n"
        f"  Verdict:              {verdict}\n"
        f"  Combined score:       {score:.4f} (threshold: 0.40)\n"
        f"  Stage 1 IF score:     {prediction.get('anomaly_score', 0):.4f}\n"
        f"  Stage 2 CatBoost:     {prediction.get('cat_prob', 0):.4f}\n\n"
        f"Network context:\n"
        f"  Source IP:            {src_ip}\n"
        f"  Destination IP:       {dst_ip}:{dst_port}\n"
        f"  Protocol:             {protocol}\n"
        f"  Bytes sent:           {sent}\n"
        f"  Bytes received:       {recv}\n"
        f"  Amplification ratio:  {ratio}x\n\n"
        f"Triggered signals: {rules_str}\n\n"
        f"Write a 3-sentence SOC analyst explanation."
    )


def _template(label, score, rules, meta) -> str:
    """Fallback when LLM is unavailable."""
    src = meta.get("src_ip", "unknown")
    dst = meta.get("dst_ip", "unknown")
    port = meta.get("dst_port", "")
    verdict = (
        "CRITICAL" if score >= 0.85 else
        "HIGH"     if score >= 0.65 else
        "MEDIUM"
    )
    return (
        f"The hybrid model detected a {label} attack from {src} → {dst}:{port} "
        f"with score {score:.3f} ({verdict}). "
        f"Triggered signals: {', '.join(rules[:3])}."
    )
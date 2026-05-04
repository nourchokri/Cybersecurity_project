"""
LangGraph node functions for Behavior Agent.

Node execution order:
  load_baseline → score_session → update_baseline → generate_explanation → build_result

Design principles:
- All scoring is deterministic Python — LLM only generates explanations
- Baseline cache used for all reads (no per-session SQLite)
- Error short-circuit: any node failure propagates via state['error']
- Structured logging on every node
"""
import logging
import numpy as np
import pandas as pd

from ..scoring.features import extract_user_features
from ..scoring.model import run_IF_model_A
from ..scoring.dimensions import dim_scorer
from ..scoring.update import UPDATE_THRESHOLD, circular_mean, circular_std

logger = logging.getLogger('behavior_agent')


# ── Node 1: Load baseline ─────────────────────────────────────────────────────

def node_load_baseline(state: dict) -> dict:
    """Load baseline from in-memory cache. No SQLite read per session."""
    user_id = state['session'].get('user_id')
    logger.info(f'[load_baseline] user={user_id}')

    from ..application.cache import get_cached_baseline
    b = get_cached_baseline(user_id)

    if b is None:
        logger.warning(f'[load_baseline] No baseline for {user_id}')
        return {**state, 'error': f'No baseline found for user {user_id}'}

    from dataclasses import asdict
    return {**state, 'baseline': asdict(b), 'error': None}


# ── Node 2: Score session ─────────────────────────────────────────────────────

def node_score_session(state: dict) -> dict:
    """
    IF-only scoring — empirically best mode (98% recall at threshold 0.4).
    Dimension scores computed for explanation/rules but not used for final score.
    """
    if state.get('error'):
        return state

    from ..scoring.baseline import UserBaseline
    b       = UserBaseline(**state['baseline'])
    session = state['session']

    logger.info(f'[score_session] user={session["user_id"]} '
                f'hour={session.get("hour_of_day")} files={session.get("file_count")}')

    features = extract_user_features(session, b)
    if_score = run_IF_model_A(features)
    dims     = dim_scorer(session, b)

    logger.info(f'[score_session] if_score={if_score:.4f} rules={dims["triggered_rules"]}')

    return {
        **state,
        'features':        features,
        'if_score':        if_score,
        'dim_scores':      {k: v for k, v in dims.items() if k != 'triggered_rules'},
        'triggered_rules': dims['triggered_rules'],
        'final_score':     if_score,
    }


# ── Node 3: Update baseline ───────────────────────────────────────────────────

def node_update_baseline(state: dict) -> dict:
    """
    Score-gated baseline update.
    Always updates: recent_scores, observation_days, cold_start flag.
    Gated (score < 0.4): login hours, file volume, known devices.
    Writes to both in-memory cache and SQLite.
    """
    if state.get('error'):
        return state

    user_id     = state['session']['user_id']
    final_score = state['final_score']
    session     = state['session']

    try:
        from ..application.cache import get_cached_baseline, update_cached_baseline
        from ..scoring.baseline import get_connection, save_baseline

        b = get_cached_baseline(user_id)
        if b is None:
            return state

        # Always update
        b.recent_scores.append(float(final_score))
        if len(b.recent_scores) > 7:
            b.recent_scores = b.recent_scores[-7:]
        b.observation_days += 1
        if b.observation_days >= 5:
            b.cold_start = False

        # Gated update — only for normal sessions
        if final_score < UPDATE_THRESHOLD:
            b.login_hours_observed.append(session.get('hour_of_day', 9))
            if len(b.login_hours_observed) > 240:
                b.login_hours_observed = b.login_hours_observed[-240:]
            b.login_hour_mean = circular_mean(b.login_hours_observed)
            b.login_hour_std  = circular_std(b.login_hours_observed)

            b.daily_volume_history.append(float(session.get('file_count', 0)))
            if len(b.daily_volume_history) > 30:
                b.daily_volume_history = b.daily_volume_history[-30:]
            b.daily_file_access_mean = float(np.mean(b.daily_volume_history))
            b.daily_file_access_std  = max(float(np.std(b.daily_volume_history)), 1.0)

            pc = session.get('pc', '')
            if pc and pc not in b.known_devices:
                b.known_devices.append(pc)

        b.last_updated = str(pd.Timestamp.now().date())
        update_cached_baseline(user_id, b)

        conn = get_connection()
        save_baseline(conn, b)
        conn.close()

        gate_status = 'gated (anomalous)' if final_score >= UPDATE_THRESHOLD else 'full update'
        logger.info(f'[update_baseline] user={user_id} score={final_score:.4f} {gate_status}')

    except Exception as e:
        logger.error(f'[update_baseline] Failed for {user_id}: {e}')

    return state


# ── Node 4: Generate explanation ──────────────────────────────────────────────

def node_generate_explanation(state: dict) -> dict:
    """
    LLM explanation via university vLLM server (Llama-3.1-70B).
    Uses MCP tools to fetch context before calling the LLM.
    Mirrors the Risk Decision Agent's ReAct pattern:
      1. Call MCP tools to gather context (baseline, history, rule explanations)
      2. Pass context to LLM for explanation generation
      3. Fall back to template on any failure
    """
    if state.get('error'):
        return {**state, 'explanation': f"Error: {state['error']}"}

    score   = state['final_score']
    rules   = state['triggered_rules']
    user_id = state['session']['user_id']
    dims    = state['dim_scores']
    session = state['session']

    try:
        from django.conf import settings
        api_key = getattr(settings, 'ESPRIT_API_KEY', '')

        # ── Step 1: Gather context via MCP tools ──────────────────────────
        mcp_context = {}
        try:
            from ..infrastructure.mcp.client import get_mcp_client
            client = get_mcp_client()

            # Fetch user baseline context
            baseline_ctx = client.call_tool('behavior.baseline.get_user_baseline',
                                            {'user_id': user_id})
            if isinstance(baseline_ctx, dict) and 'error' not in baseline_ctx:
                mcp_context['baseline'] = baseline_ctx

            # Fetch score history and trend
            history_ctx = client.call_tool('behavior.baseline.get_user_history',
                                           {'user_id': user_id, 'limit': 5})
            if isinstance(history_ctx, dict) and 'error' not in history_ctx:
                mcp_context['history'] = history_ctx

            # Fetch rule explanations
            if rules:
                rules_ctx = client.call_tool('behavior.rules.explain_triggered_rules',
                                             {'rule_ids': rules})
                if isinstance(rules_ctx, dict):
                    mcp_context['rule_explanations'] = rules_ctx.get('explanations', {})

            logger.info(f'[generate_explanation] MCP context gathered for {user_id}: '
                        f'{list(mcp_context.keys())}')
        except Exception as mcp_err:
            logger.warning(f'[generate_explanation] MCP context failed for {user_id}: {mcp_err}')

        # ── Step 2: Call LLM with context ─────────────────────────────────
        if api_key:
            import httpx
            from openai import OpenAI

            http_client = httpx.Client(verify=False)
            client_llm = OpenAI(
                api_key=api_key,
                base_url=getattr(settings, 'ESPRIT_BASE_URL', ''),
                http_client=http_client,
            )

            prompt = _build_prompt_with_context(user_id, score, rules, dims, session, mcp_context)
            response = client_llm.chat.completions.create(
                model=getattr(settings, 'ESPRIT_MODEL', 'hosted_vllm/Llama-3.1-70B-Instruct'),
                messages=[
                    {
                        'role': 'system',
                        'content': (
                            'You are a SOC analyst explaining ML model results. '
                            'The Isolation Forest model has already scored this session. '
                            'Write exactly 2 sentences. '
                            'Sentence 1: explain what the ML model found and the score. '
                            'Sentence 2: interpret the likely threat scenario based on the model findings. '
                            'You are NOT detecting threats - you are explaining what the model detected. '
                            'No preamble. No hedging. No repetition. Facts only.'
                        ),
                    },
                    {'role': 'user', 'content': prompt},
                ],
                temperature=0.1,
                max_tokens=80,
                top_p=0.9,
            )
            explanation = response.choices[0].message.content.strip()
            logger.info(f'[generate_explanation] LLM explanation for {user_id}')
        else:
            explanation = _template_explanation(user_id, score, rules, dims)
            logger.info(f'[generate_explanation] Template explanation for {user_id}')

    except Exception as e:
        logger.warning(f'[generate_explanation] Failed for {user_id}: {e}')
        explanation = _template_explanation(user_id, score, rules, dims)

    return {**state, 'explanation': explanation}


# ── Node 5: Build result ──────────────────────────────────────────────────────

def node_build_result(state: dict) -> dict:
    """Assemble the final AnomalyResult dict (Contract 3 schema)."""
    if state.get('error'):
        return {**state, 'anomaly_result': {'error': state['error']}}

    session = state['session']
    dims    = state['dim_scores']
    b_data  = state['baseline']

    from django.conf import settings
    threshold = getattr(settings, 'ANOMALY_THRESHOLD', 0.4)

    confidence = (
        'low'    if b_data.get('cold_start') else
        'medium' if b_data.get('observation_days', 0) < 20 else
        'high'
    )
    verdict = (
        'CRITICAL' if state['final_score'] >= 0.8 else
        'HIGH'     if state['final_score'] >= 0.6 else
        'MEDIUM'   if state['final_score'] >= threshold else
        'LOW'
    )

    result = {
        'event_id':             session.get('event_id', f"{session['user_id']}_{session.get('session_start','')}"),
        'timestamp':            str(session.get('session_start', '')),
        'source':               ['user_behavior'],
        'user_anomaly_score':   state['final_score'],
        'network_anomaly_score':None,
        'combined_score':       state['final_score'],
        'user_id':              session['user_id'],
        'entity_id':            None,
        'dimension_scores':     dims,
        'triggered_rules':      state['triggered_rules'],
        'network_attack_category': None,
        'correlation': {
            'correlated':            False,
            'time_delta_seconds':    None,
            'threat_classification': 'insider_threat',
        },
        'explanation':       state['explanation'],
        'baseline_age_days': b_data.get('observation_days', 0),
        'confidence':        confidence,
        'cold_start':        b_data.get('cold_start', False),
        'simulated':         session.get('simulated', False),
        'flagged':           state['final_score'] >= threshold,
        'if_score':          state['if_score'],
        'detection_agent_analysis': {
            'model':           getattr(settings, 'ESPRIT_MODEL', 'template'),
            'llm_used':        bool(getattr(settings, 'ESPRIT_API_KEY', '')),
            'analyst_note':    state['explanation'],
            'scoring_mode':    'IF-only',
            'score':           round(state['final_score'], 4),
            'threshold':       threshold,
            'verdict':         verdict,
            'triggered_signals': state['triggered_rules'],
            'dimension_breakdown': {
                'time':        round(dims.get('time', 0), 4),
                'device':      round(dims.get('device', 0), 4),
                'volume':      round(dims.get('volume', 0), 4),
                'sensitivity': round(dims.get('sensitivity', 0), 4),
            },
            'session_summary': {
                'login_hour':       session.get('hour_of_day'),
                'outside_hours':    bool(session.get('is_outside_hours')),
                'file_count':       session.get('file_count'),
                'usb_connected':    bool(session.get('usb_connected')),
                'usb_first_time':   bool(session.get('usb_first_time')),
                'external_email':   bool(session.get('has_ext_email')),
                'exfil_domain':     bool(session.get('visited_exfil_domain')),
                'jobsearch_domain': bool(session.get('visited_jobsearch_domain')),
                'duration_minutes': round(session.get('duration_minutes', 0), 1),
            },
            'baseline_context': {
                'observation_days': b_data.get('observation_days', 0),
                'cold_start':       b_data.get('cold_start', False),
                'confidence':       confidence,
                'department':       b_data.get('department', 'unknown'),
                'recent_scores':    b_data.get('recent_scores', []),
            },
        },
    }

    logger.info(f'[build_result] user={session["user_id"]} score={state["final_score"]:.4f} verdict={verdict}')

    # Persist to session history DB for long-term memory across restarts
    try:
        from ..memory.checkpointer import save_session_result
        # thread_id not available here — will be saved by the CLI after invoke
        pass
    except Exception:
        pass

    return {**state, 'anomaly_result': result}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_prompt(user_id, score, rules, dims, session) -> str:
    rules_str = ', '.join(rules) if rules else 'none'
    return (
        f"The Isolation Forest model analyzed user {user_id} and produced this result:\n\n"
        f"Anomaly score: {score:.3f} (threshold: 0.4)\n"
        f"Triggered signals: {rules_str}\n"
        f"Dimensions: time={dims.get('time',0):.2f}, device={dims.get('device',0):.2f}, "
        f"volume={dims.get('volume',0):.2f}, sensitivity={dims.get('sensitivity',0):.2f}\n"
        f"Session: hour={session.get('hour_of_day')}, files={session.get('file_count')}, "
        f"USB={bool(session.get('usb_connected'))}, "
        f"external_email={bool(session.get('has_ext_email'))}, "
        f"exfil_domain={bool(session.get('visited_exfil_domain'))}\n\n"
        f"Explain what the ML model found and interpret the likely threat scenario."
    )


def _build_prompt_with_context(user_id, score, rules, dims, session, mcp_context: dict) -> str:
    """Tight, structured prompt — forces 2-sentence output explaining ML model findings."""
    rules_str = ', '.join(rules) if rules else 'none'

    # Pull key context facts only
    trend = ''
    if 'history' in mcp_context:
        trend = mcp_context['history'].get('trend_label', '')

    dept = ''
    if 'baseline' in mcp_context:
        dept = mcp_context['baseline'].get('department', '')

    return (
        f"The Isolation Forest model scored user {user_id} (Dept: {dept}) at {score:.3f}. "
        f"Verdict: {'FLAGGED' if score >= 0.4 else 'NORMAL'}\n"
        f"Model triggered signals: {rules_str}\n"
        f"Session details: hour={session.get('hour_of_day')}h, "
        f"files={session.get('file_count')}, "
        f"USB={'yes' if session.get('usb_connected') else 'no'}, "
        f"exfil={'yes' if session.get('visited_exfil_domain') else 'no'}, "
        f"ext_email={'yes' if session.get('has_ext_email') else 'no'}\n"
        f"Score trend: {trend if trend else 'unknown'}\n\n"
        f"Explain what the ML model found and interpret the threat scenario."
    )


def _template_explanation(user_id, score, rules, dims) -> str:
    if score >= 0.8:   level = 'CRITICAL'
    elif score >= 0.6: level = 'HIGH'
    elif score >= 0.4: level = 'MEDIUM'
    else:              level = 'LOW'
    parts = [f"The ML model scored user {user_id} at {score:.3f} ({level} risk)."]
    if rules:
        parts.append(f"Model triggered signals: {', '.join(rules)}.")
    if dims:
        top = max(dims, key=dims.get)
        if dims[top] > 0:
            parts.append(f"Strongest dimension: {top} ({dims[top]:.2f}).")
    return ' '.join(parts)
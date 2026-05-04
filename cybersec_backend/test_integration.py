"""
Integration test: Behavior Agent → Risk Decision Agent pipeline.

Tests the full flow:
  1. Behavior Agent (Monitor A) scores a session
  2. If flagged, forwards AnomalyResult to Risk Decision Agent
  3. Risk Decision Agent returns ALLOW/MONITOR/ESCALATE/BLOCK

Uses the same .env as monitor_a (ESPRIT_API_KEY, model paths, etc.)
Run from cybersec_backend/:
  python test_integration.py
"""
import warnings; warnings.filterwarnings('ignore')
import os, sys, json
from pathlib import Path

# ── Bootstrap Django with dev settings ───────────────────────────────────────
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

# Load monitor_a .env so ESPRIT_API_KEY etc. are available
_monitor_a_env = Path(__file__).resolve().parents[2] / 'monitor_a' / '.env'
if _monitor_a_env.exists():
    for line in _monitor_a_env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    print(f'Loaded .env from {_monitor_a_env}')

import django
django.setup()

# Explicitly add monitor_a to sys.path before importing behavior agent
_monitor_a = Path(__file__).resolve().parents[3] / 'monitor_a'
if _monitor_a.exists() and str(_monitor_a) not in sys.path:
    sys.path.insert(0, str(_monitor_a))
    print(f'Added monitor_a to sys.path: {_monitor_a}')
else:
    print(f'WARNING: monitor_a not found at {_monitor_a}')

from django.conf import settings

PASS = []
FAIL = []

def check(name, condition, detail=''):
    if condition:
        PASS.append(name)
        print(f'  PASS  {name}')
    else:
        FAIL.append(name)
        print(f'  FAIL  {name}  {detail}')

# ── Test sessions (same format as monitor_a) ─────────────────────────────────
HIGH_RISK_SESSION = {
    'user_id':                'AAM0658',
    'pc':                     'PC-9999',
    'session_start':          '2010-10-21T00:18:00',
    'hour_of_day':            0,
    'is_weekend':             0,
    'is_outside_hours':       1,
    'duration_minutes':       5.0,
    'file_count':             200,
    'max_sensitivity':        2,
    'usb_connected':          1,
    'usb_first_time':         1,
    'email_count':            0,
    'has_ext_email':          0,
    'visited_exfil_domain':   1,
    'visited_jobsearch_domain': 0,
    'simulated':              False,
}

NORMAL_SESSION = {
    'user_id':                'AAF0535',
    'pc':                     'PC-2408',
    'session_start':          '2010-06-15T09:00:00',
    'hour_of_day':            9,
    'is_weekend':             0,
    'is_outside_hours':       0,
    'duration_minutes':       480.0,
    'file_count':             3,
    'max_sensitivity':        0,
    'usb_connected':          0,
    'usb_first_time':         0,
    'email_count':            5,
    'has_ext_email':          0,
    'visited_exfil_domain':   0,
    'visited_jobsearch_domain': 0,
    'simulated':              False,
}

MEDIUM_RISK_SESSION = {
    'user_id':                'ABC0174',
    'pc':                     'PC-5555',
    'session_start':          '2010-05-08T13:18:00',
    'hour_of_day':            13,
    'is_weekend':             0,
    'is_outside_hours':       0,
    'duration_minutes':       148.7,
    'file_count':             0,
    'max_sensitivity':        0,
    'usb_connected':          1,
    'usb_first_time':         0,
    'email_count':            3,
    'has_ext_email':          1,
    'visited_exfil_domain':   0,
    'visited_jobsearch_domain': 1,
    'simulated':              False,
}

# ── Section 1: Behavior Agent (Monitor A) ────────────────────────────────────
print('\n' + '='*65)
print('  SECTION 1 — Behavior Agent (Monitor A)')
print('='*65)

from architecture.behavior_agent.application.orchestration_service import (
    get_orchestration_service
)

try:
    service = get_orchestration_service()
    health = service.health()
    check('Behavior agent initialised', health.get('status') == 'ok', str(health))
    check('Baselines loaded', health.get('baselines_cached', 0) > 0,
          f'cached={health.get("baselines_cached")}')
    check('18 features', health.get('features') == 18,
          f'features={health.get("features")}')
    print(f'  Health: {health}')
except Exception as e:
    check('Behavior agent initialised', False, str(e))
    print(f'  FATAL: {e}')
    sys.exit(1)

# Test 1: High-risk session (S1 malicious user)
print('\n[Test 1] High-risk session — AAM0658 (S1 WikiLeaks)')
result_high = service.score_session(HIGH_RISK_SESSION, thread_id='test_high_001')
check('No error', result_high.get('ok'), result_high.get('error'))
if result_high.get('ok'):
    ar = result_high['anomaly_result']
    check('Score > 0.4', ar['combined_score'] > 0.4, f'score={ar["combined_score"]:.4f}')
    check('Flagged=True', ar['flagged'] == True)
    check('Verdict is HIGH or CRITICAL', ar['detection_agent_analysis']['verdict'] in ['HIGH','CRITICAL'],
          f'verdict={ar["detection_agent_analysis"]["verdict"]}')
    check('Explanation non-empty', bool(ar.get('explanation')))
    check('detection_agent_analysis present', 'detection_agent_analysis' in ar)
    print(f'  Score:       {ar["combined_score"]:.4f}')
    print(f'  Verdict:     {ar["detection_agent_analysis"]["verdict"]}')
    print(f'  Rules:       {ar["triggered_rules"]}')
    print(f'  Explanation: {ar["explanation"]}')

# Test 2: Normal session
print('\n[Test 2] Normal session — AAF0535')
result_normal = service.score_session(NORMAL_SESSION, thread_id='test_normal_001')
check('No error', result_normal.get('ok'), result_normal.get('error'))
if result_normal.get('ok'):
    ar_n = result_normal['anomaly_result']
    check('Normal session not flagged or low score', not ar_n['flagged'] or ar_n['combined_score'] < 0.7,
          f'score={ar_n["combined_score"]:.4f} flagged={ar_n["flagged"]}')
    print(f'  Score:   {ar_n["combined_score"]:.4f}')
    print(f'  Verdict: {ar_n["detection_agent_analysis"]["verdict"]}')
    print(f'  Flagged: {ar_n["flagged"]}')

# Test 3: Medium-risk session (S2 malicious user)
print('\n[Test 3] Medium-risk session — ABC0174 (S2 IP Theft)')
result_med = service.score_session(MEDIUM_RISK_SESSION, thread_id='test_med_001')
check('No error', result_med.get('ok'), result_med.get('error'))
if result_med.get('ok'):
    ar_m = result_med['anomaly_result']
    print(f'  Score:   {ar_m["combined_score"]:.4f}')
    print(f'  Verdict: {ar_m["detection_agent_analysis"]["verdict"]}')
    print(f'  Flagged: {ar_m["flagged"]}')
    print(f'  Rules:   {ar_m["triggered_rules"]}')

# Test 4: Batch scoring
print('\n[Test 4] Batch scoring — 3 sessions')
batch_results = service.score_batch(
    [HIGH_RISK_SESSION, NORMAL_SESSION, MEDIUM_RISK_SESSION],
    thread_id='test_batch'
)
check('Batch returns 3 results', len(batch_results) == 3, f'got {len(batch_results)}')
check('All batch results ok', all(r.get('ok') for r in batch_results))
for i, r in enumerate(batch_results):
    if r.get('ok'):
        print(f'  Session {i+1}: score={r["anomaly_result"]["combined_score"]:.4f} '
              f'flagged={r["anomaly_result"]["flagged"]}')

# Test 5: Baseline retrieval
print('\n[Test 5] Baseline retrieval')
baseline = service.get_baseline('AAM0658')
check('Baseline returned', 'error' not in baseline, str(baseline.get('error')))
check('Baseline has department', 'department' in baseline)
print(f'  User: AAM0658  dept={baseline.get("department")}  '
      f'obs_days={baseline.get("observation_days")}')

# ── Section 2: Forward to Risk Decision Agent ─────────────────────────────────
print('\n' + '='*65)
print('  SECTION 2 — Forward to Risk Decision Agent (Team 3)')
print('='*65)

if result_high.get('ok') and result_high['anomaly_result']['flagged']:
    ar_flagged = result_high['anomaly_result']
    print(f'\nForwarding flagged session (score={ar_flagged["combined_score"]:.4f}) to Team 3...')

    from architecture.behavior_agent.integrations.risk_decision_client import RiskDecisionClient
    client = RiskDecisionClient()

    # Try to forward — Team 3 server may not be running
    fwd_result = client.forward_anomaly(ar_flagged)

    if fwd_result.get('ok'):
        decision = fwd_result.get('decision', {})
        check('Team 3 returned decision', 'decision' in decision, str(decision))
        check('Decision is valid', decision.get('decision') in
              ['ALLOW','MONITOR','ESCALATE','BLOCK'],
              f'decision={decision.get("decision")}')
        print(f'  Team 3 decision:    {decision.get("decision")}')
        print(f'  Adjusted score:     {decision.get("adjusted_risk_score")}')
        print(f'  Risk level:         {decision.get("risk_level")}')
        print(f'  Recommended action: {decision.get("recommended_action")}')
        print(f'  Reasoning:          {decision.get("decision_reasoning", "")[:120]}...')
    else:
        print(f'  Team 3 not reachable (server may not be running): {fwd_result.get("error")}')
        print('  This is expected if Team 3 server is not started.')
        print('  Start with: python manage.py runserver 8000')
        # Not a failure — Team 3 just needs to be running
        check('Team 3 forward attempted', True)
else:
    print('  Skipped — high-risk session not flagged or scoring failed.')

# ── Section 3: Output JSON verification ──────────────────────────────────────
print('\n' + '='*65)
print('  SECTION 3 — Output JSON Structure Verification')
print('='*65)

if result_high.get('ok'):
    ar = result_high['anomaly_result']
    required_fields = [
        'event_id', 'timestamp', 'user_id', 'combined_score', 'flagged',
        'triggered_rules', 'explanation', 'confidence', 'cold_start',
        'detection_agent_analysis', 'dimension_scores', 'correlation',
    ]
    for field in required_fields:
        check(f'Field present: {field}', field in ar, f'missing from output')

    daa = ar.get('detection_agent_analysis', {})
    daa_fields = ['model','llm_used','analyst_note','scoring_mode','score',
                  'verdict','triggered_signals','dimension_breakdown',
                  'session_summary','baseline_context']
    for field in daa_fields:
        check(f'DAA field: {field}', field in daa)

    # Save sample output
    out_path = Path(__file__).parent / 'test_integration_output.json'
    with open(out_path, 'w') as f:
        json.dump(ar, f, indent=2, default=str)
    print(f'\n  Sample output saved to: {out_path}')

# ── Summary ───────────────────────────────────────────────────────────────────
print('='*65)
print(f'  INTEGRATION TEST: {len(PASS)} PASS  {len(FAIL)} FAIL')
if FAIL:
    print(f'  Failed: {FAIL}')
print('='*65)
# Note: exit code 0 = all pass, 1 = some fail
raise SystemExit(0 if not FAIL else 1)

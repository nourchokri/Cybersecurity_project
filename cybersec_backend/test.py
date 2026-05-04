# test_real_pipeline.py
# Run from cybersec_backend/ with: python test_real_pipeline.py

import httpx
import json
import time

BEHAVIOR_BASE    = "http://127.0.0.1:8000"
DATA_AGENT_BASE  = "http://127.0.0.1:8000"  # All agents on same server

def separator(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

# ── Step 1: Health checks ─────────────────────────────────────────
separator("STEP 1 — Health checks")

r = httpx.get(f"{BEHAVIOR_BASE}/api/v1/network/health/", timeout=5)
print(f"Network agent:  {r.status_code} — {r.json().get('status')}")

r = httpx.get(f"{BEHAVIOR_BASE}/api/v1/risk-decision/health/", timeout=5)
print(f"Risk agent:     {r.status_code} — {r.json().get('status')}")

r = httpx.get(f"{DATA_AGENT_BASE}/api/v1/data/health/", timeout=5)
print(f"Data agent:     {r.status_code} — {r.json().get('status')}")

# ── Step 2: Cache baseline ────────────────────────────────────────
separator("STEP 2 — Team 3 cache BEFORE pipeline")
r = httpx.get(f"{BEHAVIOR_BASE}/api/v1/risk-decision/cache/stats/")
before = r.json()
print(f"Active entries before: {before.get('active_entries', 0)}")

# ── Step 3: Trigger real data collection ─────────────────────────
separator("STEP 3 — Trigger Team 1 pipeline (real data)")
print("Collecting real network events from this machine...")
print("This may take 30-60 seconds...\n")

try:
    r = httpx.post(
        f"{DATA_AGENT_BASE}/api/v1/data/collect/",
        json={"collectors": ["network", "dns"]},
        timeout=120,
    )
    pipeline_data = r.json()
    print(f"Status:          {r.status_code}")
    print(f"Total events:    {pipeline_data.get('total_events', 0)}")
    print(f"Sessions:        {pipeline_data.get('sessions_created', 0)}")
    print(f"Tools executed:  {pipeline_data.get('tools_executed', [])}")

    # Network agent results
    net_result = pipeline_data.get('network_result', {})
    print(f"\nNetwork agent:")
    print(f"  Sessions sent:   {net_result.get('sessions_sent', 0)}")
    print(f"  Flagged:         {net_result.get('flagged_count', 0)}")

    # Behavior agent results
    beh_result = pipeline_data.get('behavior_result', {})
    print(f"\nBehavior agent:")
    print(f"  Sessions sent:   {beh_result.get('sessions_sent', 0)}")
    print(f"  Flagged:         {beh_result.get('flagged_count', 0)}")

    # LLM reasoning from data agent
    llm_reasoning = pipeline_data.get('llm_reasoning', '')
    if llm_reasoning:
        print(f"\nData agent LLM reasoning:\n  {llm_reasoning[:200]}...")

except Exception as e:
    print(f"Pipeline call failed: {e}")
    print("Check that data agent is running on port 8001")

# ── Step 4: Check network agent results directly ──────────────────
separator("STEP 4 — Check if network agent got real events")
print("Sending real network events directly to network agent...")

# Collect real connections from your machine right now
try:
    import psutil
    import socket
    import getpass
    from datetime import datetime

    events = []
    username  = getpass.getuser()
    hostname  = socket.gethostname()
    timestamp = datetime.now().isoformat()

    for conn in psutil.net_connections(kind="inet"):
        if not conn.raddr:
            continue
        src_ip   = conn.laddr.ip   if conn.laddr else "0.0.0.0"
        src_port = conn.laddr.port if conn.laddr else 0
        dst_ip   = conn.raddr.ip
        dst_port = conn.raddr.port
        protocol = "TCP" if conn.type == socket.SOCK_STREAM else "UDP"

        events.append({
            "event_type":     "network_connection",
            "action":         "connect",
            "timestamp":      timestamp,
            "user_id":        username,
            "device_id":      hostname,
            "metadata": {
                "src_ip":         src_ip,
                "dst_ip":         dst_ip,
                "src_port":       src_port,
                "dst_port":       dst_port,
                "protocol":       protocol,
                "bytes_sent":     0,
                "bytes_received": 0,
                "process_name":   "unknown",
            }
        })

    print(f"Found {len(events)} active connections on your machine")

    if events:
        payload = {
            "sessions": [{
                "user_id":   username,
                "device_id": hostname,
                "events":    events,
            }]
        }

        r = httpx.post(
            f"{BEHAVIOR_BASE}/api/v1/network/analyze/batch/",
            json=payload,
            timeout=60,
        )
        print(f"Status: {r.status_code}")
        
        if r.status_code != 200:
            print(f"Error response: {r.text[:500]}")
            print("Skipping network analysis test due to error")
            data = {"results": []}
        else:
            try:
                data = r.json()
            except Exception as e:
                print(f"Failed to parse JSON response: {e}")
                print(f"Response text: {r.text[:500]}")
                data = {"results": []}

        for result in data.get("results", []):
            print(f"\n  user:       {result.get('user_id')}")
            print(f"  flagged:    {result.get('flagged')}")
            print(f"  score:      {result.get('combined_score')}")
            print(f"  verdict:    {result['detection_agent_analysis'].get('verdict')}")
            print(f"  attack:     {result.get('network_attack_category')}")
            print(f"  confidence: {result.get('confidence')}")

            # ── This is where LLM explanation appears ─────────────
            explanation = result.get("explanation", "")
            print(f"\n  LLM explanation:")
            print(f"  {explanation}")

            rules = result.get("triggered_rules", [])
            if rules:
                print(f"\n  Triggered rules:")
                for rule in rules:
                    print(f"    - {rule}")

except ImportError:
    print("psutil not installed — skipping real connection test")
    print("Run: pip install psutil")

# ── Step 5: Check Team 3 received detections ──────────────────────
separator("STEP 5 — Team 3 cache AFTER pipeline")
time.sleep(2)

r = httpx.get(f"{BEHAVIOR_BASE}/api/v1/risk-decision/cache/stats/")
after = r.json()
print(f"Active entries after:  {after.get('active_entries', 0)}")
print(f"New entries:           "
      f"{after.get('active_entries', 0) - before.get('active_entries', 0)}")

# ── Step 6: Test LLM explanation specifically ─────────────────────
separator("STEP 6 — Test LLM explanation directly")
print("Sending a known attack to verify LLM generates explanation...")

r = httpx.post(
    f"{BEHAVIOR_BASE}/api/v1/network/analyze/batch/",
    json={
        "sessions": [{
            "user_id":   "llm_test_user",
            "device_id": "TEST-LAPTOP",
            "events": [{
                "event_type": "network_connection",
                "action":     "connect",
                "timestamp":  "2026-04-05T10:00:00",
                "user_id":    "llm_test_user",
                "metadata": {
                    "src_ip":         "192.168.1.10",
                    "dst_ip":         "185.220.101.45",
                    "src_port":       54321,
                    "dst_port":       123,
                    "protocol":       "UDP",
                    "bytes_sent":     48,
                    "bytes_received": 4800,
                }
            }]
        }]
    },
    timeout=60,
)

if r.status_code == 200:
    try:
        result = r.json().get("results", [{}])[0]
        print(f"\nAttack detected:  {result.get('network_attack_category')}")
        print(f"Score:            {result.get('combined_score')}")
        print(f"Flagged:          {result.get('flagged')}")
        print(f"\nLLM Explanation:")
        print(f"{result.get('explanation', 'No explanation generated')}")
    except Exception as e:
        print(f"Failed to parse response: {e}")
        print(f"Response: {r.text[:500]}")
else:
    print(f"Request failed with status {r.status_code}")
    print(f"Response: {r.text[:500]}")
"""Quick smoke test for all API endpoints."""
import urllib.request
import json

BASE = "http://127.0.0.1:8000/api/v1/risk-decision"

def get(path):
    r = urllib.request.urlopen(f"{BASE}{path}")
    return json.loads(r.read())

def post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(f"{BASE}{path}", data=body, headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req, timeout=120)
    return json.loads(r.read())

print("1. Health check...")
h = get("/health/")
print(f"   Status: {h['status']}  Agent: {h['agent']}")

print("2. Sample events...")
s = get("/sample-events/")
print(f"   {len(s['events'])} event(s) available")

print("3. Cache stats...")
c = get("/cache/stats/")
print(f"   {c}")

print("4. Analyze event (POST)...")
decision = post("/analyze/", {
    "event_id": "evt-final-test",
    "user_id": "MOH0273",
    "entity_id": "{L9G8-J9QE34VM-2834VDPB}",
    "timestamp": "2010-01-02T07:23:14",
    "score": 0.87,
    "triggered_rules": ["login_outside_normal_hours", "unknown_device"],
    "confidence": "high",
    "cold_start": False,
})
print(f"   Decision: {decision['decision']}")
print(f"   Risk Level: {decision['risk_level']}")
print(f"   Adjusted Score: {decision['adjusted_risk_score']}")
print(f"   Confidence: {decision['confidence']}")

print("\nAll endpoints working!")

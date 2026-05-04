import requests

url = "http://127.0.0.1:8000/api/v1/behavior/sample-sessions/?n=30"
try:
    resp = requests.get(url)
    data = resp.json()
    sessions = data.get("sessions", [])
    print(f"Total returned: {len(sessions)}")
    for i, s in enumerate(sessions[:6]):
        print(f"#{i+1}: {s.get('user_id')} - {s.get('session_start')}")
except Exception as e:
    print(f"Error: {e}")

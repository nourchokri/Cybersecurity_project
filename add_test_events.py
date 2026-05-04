import pandas as pd
from datetime import datetime, timedelta

file_path = r"c:\Users\USER\Desktop\project_classe\cybersec_backend\data\test_sessions.parquet"
df = pd.read_parquet(file_path)

# Let's use an existing user so the baseline doesn't freak out with a cold-start
base_event = {
    'user_id': 'AAF0535',
    'pc': 'PC-2408',
    'hour_of_day': 18,
    'is_weekend': 0,
    'is_outside_hours': 1,  # Only one mild flag (after hours)
    'duration_minutes': 30.0,
    'file_count': 5,        # Normal
    'max_sensitivity': 0,   # Normal
    'usb_connected': 0,     # Normal
    'usb_first_time': 0,
    'email_count': 1,
    'has_ext_email': 0,
    'visited_exfil_domain': 0,
    'visited_jobsearch_domain': 0,
    'visited_threat_domain': 0
}

new_rows = []
# Give them all the same date so they hit the daily limit counter
base_time = datetime(2011, 3, 3, 22, 0, 0)

for i in range(4):
    event = base_event.copy()
    event['session_start'] = base_time + timedelta(minutes=i*15)
    new_rows.append(event)

new_df = pd.DataFrame(new_rows)
# Prepend so they appear at the very top of the frontend event dropdown
df = pd.concat([new_df, df], ignore_index=True)

df.to_parquet(file_path, engine='pyarrow', index=False)
print("Successfully injected 4 anomalous test events for AAF0535 to test_sessions.parquet!")

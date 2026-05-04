import sqlite3
import json

db_path = r"c:\Users\USER\Desktop\project_classe\cybersec_backend\decision_agent_cache.db"

try:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT key, value FROM cache WHERE key LIKE 'low_offenders%'")
    rows = cursor.fetchall()
    
    if not rows:
        print("No low_offenders keys found in cache!")
    else:
        for row in rows:
            print(f"Key: {row['key']}")
            print(f"Value: {row['value']}")
except Exception as e:
    print(f"Error reading cache DB: {e}")

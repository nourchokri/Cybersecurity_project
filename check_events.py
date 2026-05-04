import pandas as pd

file_path = r"c:\Users\USER\Desktop\project_classe\test_sessions.parquet"
df = pd.read_parquet(file_path)

test_events = df[df['user_id'] == 'AAF0535'].head(8)
for idx, row in test_events.iterrows():
    print(row['user_id'], row['session_start'])

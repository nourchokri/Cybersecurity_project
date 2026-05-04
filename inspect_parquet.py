import pandas as pd
file_path = r"c:\Users\USER\Desktop\project_classe\test_sessions.parquet"
df = pd.read_parquet(file_path)
print("Columns:", df.columns.tolist())
print("Total rows:", len(df))
print(df.head(1).to_dict(orient='records'))

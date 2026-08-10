import sqlite3
import pandas as pd

DB_PATH = "data/change-ringing.db"

def inspect():
    with sqlite3.connect(DB_PATH) as conn:
        print("--- Tables ---")
        tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)
        print(tables)
        
        for table in tables['name']:
            print(f"\n--- Schema for {table} ---")
            schema = pd.read_sql(f"PRAGMA table_info({table});", conn)
            print(schema[['name', 'type']])
            
            print(f"\n--- Sample for {table} ---")
            sample = pd.read_sql(f"SELECT * FROM {table} LIMIT 3;", conn)
            print(sample)
            
if __name__ == "__main__":
    inspect()

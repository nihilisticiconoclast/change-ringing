import sqlite3
import pandas as pd
import json

def check_stages():
    conn = sqlite3.connect("data/change-ringing.db")
    query = """
        SELECT p.perf_id, p.bb_id, p.place, p.method, p.perf_date, t.Lat, t.Long, m.stage
        FROM performances p
        LEFT JOIN towers t ON p.dove_tower_id = t.TowerID
        LEFT JOIN methods m ON p.method = m.title
        WHERE p.perf_date LIKE '2024%' 
        AND p.method IS NOT NULL
        AND p.method != ''
        LIMIT 20
    """
    df = pd.read_sql(query, conn)
    print(df['stage'].tolist())

if __name__ == "__main__":
    check_stages()

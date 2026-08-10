import sqlite3
import pandas as pd

def check_lat_long():
    conn = sqlite3.connect("data/change-ringing.db")
    
    query = """
        SELECT p.place, p.dove_tower_id, t.Lat, t.Long
        FROM performances p
        LEFT JOIN towers t ON p.dove_tower_id = t.TowerID
        WHERE p.perf_date LIKE '2024%'
        AND p.method IS NOT NULL
        AND p.method != ''
        LIMIT 20
    """
    df = pd.read_sql(query, conn)
    print(df)
    
if __name__ == "__main__":
    check_lat_long()

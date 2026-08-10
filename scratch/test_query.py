import sqlite3
import pandas as pd

def test_query():
    conn = sqlite3.connect("data/change-ringing.db")
    query = """
        SELECT p.method, m.stage, m.title
        FROM performances p
        LEFT JOIN methods m ON p.method = m.title
        WHERE p.perf_date LIKE '2024%' 
        AND p.method IS NOT NULL
        AND p.method != ''
        LIMIT 10
    """
    df = pd.read_sql(query, conn)
    print(df)
    
if __name__ == "__main__":
    test_query()

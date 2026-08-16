#!/usr/bin/env python3
"""
Novelty Checker: Validates if a generated composition exists in the local database.
"""

import sqlite3
from typing import List
from pathlib import Path

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "change-ringing.db"

def check_novelty(calls: List[str]) -> bool:
    """
    Checks if a composition defined by `calls` is novel.
    Returns True if likely novel, False if likely previously rung.
    """
    if not DB_PATH.exists():
        return True # Can't check
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Generate some common formatting variants for the calls
    # E.g. ["p", "p", "b", "p"] -> "p p b p"
    spaced = " ".join(calls)
    
    # Sometimes plains are omitted and we just list the bobs/singles
    # But for a strict match we should probably use the full sequence
    # Let's check for the exact spaced string in composition or details.
    
    query = """
    SELECT COUNT(*) FROM performances 
    WHERE composition LIKE ? OR details LIKE ?
    """
    
    # We use wildcards so it matches if it's embedded in other text
    like_str = f"%{spaced}%"
    
    cursor.execute(query, (like_str, like_str))
    count = cursor.fetchone()[0]
    
    # We can also check a comma separated variant "p, p, b, p"
    comma = ", ".join(calls)
    like_str_comma = f"%{comma}%"
    
    cursor.execute(query, (like_str_comma, like_str_comma))
    count += cursor.fetchone()[0]
    
    return count == 0

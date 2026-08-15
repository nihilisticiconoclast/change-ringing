#!/usr/bin/env python3
"""
Foundational utilities for the heuristic composition search engine.
"""

from typing import List, Set, Tuple
from scripts.notation import expand, apply_change, BELL_ORDER

def generate_lead(start_row: str, notation: str, call: str, rule: str = "mirror_drop_last") -> List[str]:
    """
    Generates the rows for a lead of a method, starting from `start_row`,
    and applying `call` at the lead end.
    
    Args:
        start_row: The row at the start of the lead (e.g., '12345678').
        notation: The method's place notation, using ',' for the lead end.
        call: The place notation for the lead end call (e.g., '12' for Plain, '14' for Bob).
        rule: Expansion rule for the method body.
        
    Returns:
        List of row strings generated in this lead. The first element is the row *after* start_row.
    """
    parts = notation.split(",")
    if len(parts) == 2:
        body = parts[0]
    else:
        body = notation # fallback if no comma
        
    full_notation = f"{body},{call}"
    changes = expand(full_notation, rule)
    
    rows = []
    current_row = list(start_row)
    for ch in changes:
        current_row = apply_change(current_row, ch)
        rows.append("".join(current_row))
        
    return rows

def check_truth(composition_rows: Set[str], new_rows: List[str]) -> bool:
    """
    Checks if appending `new_rows` to the existing `composition_rows` maintains truth.
    Updates `composition_rows` in-place if true.
    
    Returns:
        True if the new rows are all unique and not already in composition_rows.
        False if there is any duplication (composition_rows is not modified if False).
    """
    new_set = set(new_rows)
    if len(new_set) < len(new_rows):
        return False # Internal duplication in the new block
        
    if composition_rows.intersection(new_set):
        return False # Duplication with existing composition
        
    composition_rows.update(new_set)
    return True

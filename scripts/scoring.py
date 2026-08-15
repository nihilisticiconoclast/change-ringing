#!/usr/bin/env python3
"""
Musicality scoring function for heuristic composition search.
"""

from typing import List

class MusicalityScorer:
    def __init__(self, stage: int = 8):
        self.stage = stage
        if stage == 6:
            self.cru = "56"
            self.tittums = "142536"
        elif stage == 8:
            self.cru = "5678"
            self.tittums = "15263748"
        elif stage == 10:
            self.cru = "7890"
            self.tittums = "1627384950"
        else:
            self.cru = "567"
            self.tittums = "142536"
        
    def score_sequence(self, rows: List[str]) -> float:
        """
        Scores a sequence of rows based on musical properties.
        """
        score = 0.0
        parted_tenors_run = 0
        max_parted_run = 0
        
        for row in rows:
            # CRUs (Course ends, runs etc. e.g. *5678)
            if self.cru in row:
                score += 1.0
                
            # Runs off the front (1234...)
            if row.startswith("1234"):
                score += 2.0
                
            # Runs off the back (...8765 or ...5678)
            if row.endswith("8765") and self.stage == 8:
                score += 2.0
            elif row.endswith("5678") and self.stage == 8:
                score += 1.5
                
            # Tittums
            if row == self.tittums:
                score += 5.0
                
            # Parted tenors penalty (7 and 8 not adjacent)
            if self.stage >= 8:
                idx_7 = row.find('7')
                idx_8 = row.find('8')
                if abs(idx_7 - idx_8) > 1:
                    parted_tenors_run += 1
                else:
                    max_parted_run = max(max_parted_run, parted_tenors_run)
                    parted_tenors_run = 0
                    
        # Apply penalty for long periods of parted tenors
        max_parted_run = max(max_parted_run, parted_tenors_run)
        if max_parted_run > 50:
            score -= (max_parted_run - 50) * 0.1
            
        return score
        
    def precompute_musicality(self, graph, method_body: str, rule: str = "mirror_drop_last") -> Dict[str, float]:
        """
        Precomputes the musicality score for the plain lead of every course head.
        This is used for O(1) musicality scoring during graph search.
        """
        print("Precomputing musicality scores for all course heads...")
        from scripts.composition_core import generate_lead
        
        # We need the plain call notation, typically '12' for major
        plain_call = graph.available_calls.get("p", "12")
        rounds = graph.all_chs[0]
        
        # Generate plain lead transpositions from rounds
        plain_lead_rounds = generate_lead(rounds, method_body, plain_call, rule)
        lead_transpositions = []
        for r in plain_lead_rounds:
            lead_transpositions.append([rounds.index(b) for b in r])
            
        scores = {}
        for ch in graph.all_chs:
            # Reconstruct the rows for this CH's plain lead
            ch_rows = ["".join(ch[i] for i in t) for t in lead_transpositions]
            # Score it
            scores[ch] = self.score_sequence(ch_rows)
            
        print("Precomputation complete.")
        return scores

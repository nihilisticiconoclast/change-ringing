#!/usr/bin/env python3
"""
Pre-computes the directed transition graph and False Course Head (FCH) table
for heuristic composition search.
"""

from typing import List, Dict, Set, Tuple
import itertools
from scripts.composition_core import generate_lead
from scripts.notation import BELL_ORDER

class CourseHeadGraph:
    def __init__(self, stage: int, method_body: str, available_calls: Dict[str, str], rule: str = "mirror_drop_last"):
        self.stage = stage
        self.method_body = method_body
        self.available_calls = available_calls
        self.rule = rule
        
        # Will hold { CH: { call_name: next_CH } }
        self.transitions: Dict[str, Dict[str, str]] = {}
        
        # Will hold { CH: set(FCHs) }
        self.fch_table: Dict[str, Set[str]] = {}
        
        self.all_chs: List[str] = []
        
    def build(self):
        """Builds the graph and FCH tables in memory."""
        print(f"Building Course Head Graph for stage {self.stage}...")
        
        # 1. Generate all possible course heads (Treble fixed at 1st place)
        bells = BELL_ORDER[:self.stage]
        treble = bells[0]
        working_bells = bells[1:]
        
        for p in itertools.permutations(working_bells):
            self.all_chs.append(treble + "".join(p))
            
        print(f"Generated {len(self.all_chs)} possible course heads.")
        
        # 2. Build Transitions (using the transpositions from rounds)
        print("Building transitions...")
        rounds = self.all_chs[0]
        
        # Find the transposition for each call
        call_transpositions = {}
        for call_name, call_not in self.available_calls.items():
            rows = generate_lead(rounds, self.method_body, call_not, self.rule)
            lead_end = rows[-1]
            # Mapping from rounds -> lead end gives the transposition
            transposition = [rounds.index(b) for b in lead_end]
            call_transpositions[call_name] = transposition
            
        # Apply transpositions to all course heads
        for ch in self.all_chs:
            self.transitions[ch] = {}
            for call_name, trans in call_transpositions.items():
                next_ch = "".join(ch[i] for i in trans)
                self.transitions[ch][call_name] = next_ch
                
        # 3. Build FCH Table
        print("Building FCH table (this may take a moment)...")
        # Map every row to the course head(s) that produce it
        row_to_chs: Dict[str, List[str]] = {}
        
        # To avoid regenerating leads for every CH from scratch, we can just use transpositions!
        # First, generate the full plain lead from rounds.
        plain_lead_rounds = generate_lead(rounds, self.method_body, self.available_calls.get("p", "12"), self.rule)
        
        # For every row in the plain lead, find its transposition from rounds
        lead_transpositions = []
        for r in plain_lead_rounds:
            lead_transpositions.append([rounds.index(b) for b in r])
            
        # Now apply these transpositions to all CHs
        ch_to_rows: Dict[str, Set[str]] = {}
        
        for ch in self.all_chs:
            rows = set("".join(ch[i] for i in t) for t in lead_transpositions)
            ch_to_rows[ch] = rows
            for r in rows:
                if r not in row_to_chs:
                    row_to_chs[r] = []
                row_to_chs[r].append(ch)
                
        # Now build the FCH table: two CHs are false if they share a row
        for ch in self.all_chs:
            fchs = set()
            for r in ch_to_rows[ch]:
                for conflicting_ch in row_to_chs[r]:
                    if conflicting_ch != ch:
                        fchs.add(conflicting_ch)
            self.fch_table[ch] = fchs
            
        print("FCH table built.")

if __name__ == "__main__":
    # Quick test
    method_body = "-38-14-1258-36-14-58-16-78" # Cambridge Major
    calls = {"p": "12", "b": "14", "s": "1234"}
    graph = CourseHeadGraph(8, method_body, calls)
    graph.build()
    
    rounds = "12345678"
    print(f"\nTransitions from rounds:")
    for c, nch in graph.transitions[rounds].items():
        print(f"  {c}: {nch}")
        
    print(f"\nFCHs for rounds: {len(graph.fch_table[rounds])} false course heads")
    # For Cambridge Major, the plain course shares rows with some specific number of other courses.
    # We can print a few.
    print(f"Sample FCHs: {list(graph.fch_table[rounds])[:5]}")

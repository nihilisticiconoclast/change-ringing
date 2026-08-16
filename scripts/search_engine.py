#!/usr/bin/env python3
"""
Beam search engine for heuristic composition search, powered by a pre-computed
course head transition graph and False Course Head (FCH) truth table.
"""

from typing import List, Dict, Set, Tuple
from scripts.course_head_graph import CourseHeadGraph

class CompositionState:
    def __init__(self, current_ch: str, true_chs: Set[str], calls: List[str], score: float, length_leads: int):
        self.current_ch = current_ch
        # true_chs is the pool of course heads that are still mathematically true to use
        self.true_chs = true_chs
        self.calls = calls
        self.score = score
        self.length_leads = length_leads

def beam_search(
    graph: CourseHeadGraph,
    start_ch: str,
    min_leads: int,
    max_leads: int,
    precomputed_scores: Dict[str, float],
    beam_width: int = 50
) -> Tuple[List[CompositionState], List[CompositionState]]:
    """
    Performs a beam search to find musical, true compositions using the CH Graph.
    
    Args:
        graph: The pre-computed CourseHeadGraph.
        start_ch: The initial course head (usually rounds, e.g. '12345678').
        min_leads: Minimum number of leads for a valid composition.
        max_leads: Maximum number of leads to search before giving up.
        precomputed_scores: Dict mapping CH -> musical score for its lead.
        beam_width: How many paths to keep at each step.
    """
    
    # Initialize the true_chs pool.
    # It contains all course heads minus the FCHs of the starting course head.
    initial_fchs = graph.fch_table[start_ch]
    initial_true_chs = set(graph.all_chs) - initial_fchs - {start_ch}
    
    initial_state = CompositionState(
        current_ch=start_ch,
        true_chs=initial_true_chs,
        calls=[],
        score=precomputed_scores[start_ch],
        length_leads=1
    )
    
    beam = [initial_state]
    completed_compositions = []
    
    step = 0
    prev_beam = beam
    while beam and beam[0].length_leads < max_leads:
        step += 1
        next_beam = []
        
        for state in beam:
            for call_name, next_ch in graph.transitions[state.current_ch].items():
                
                # O(1) Truth Check: Is this next course head in our safe pool?
                if next_ch in state.true_chs:
                    # It's true! We can branch here.
                    
                    # Update true_chs pool: remove the new CH and all its FCHs
                    new_true_chs = set(state.true_chs) # Shallow copy
                    new_true_chs.remove(next_ch)
                    new_true_chs.difference_update(graph.fch_table[next_ch])
                    
                    new_score = state.score + precomputed_scores[next_ch]
                    
                    new_state = CompositionState(
                        current_ch=next_ch,
                        true_chs=new_true_chs,
                        calls=state.calls + [call_name],
                        score=new_score,
                        length_leads=state.length_leads + 1
                    )
                    
                    # Did we come round?
                    # The graph transition maps the CH to the NEXT CH.
                    # Coming round means the next_ch is the start_ch!
                    if next_ch == start_ch and new_state.length_leads >= min_leads:
                        completed_compositions.append(new_state)
                    else:
                        next_beam.append(new_state)
                        
        # Sort the next beam by score descending
        next_beam.sort(key=lambda x: x.score, reverse=True)
        
        # Prune to beam width
        if next_beam:
            prev_beam = next_beam[:beam_width]
            beam = next_beam[:beam_width]
        else:
            beam = []
            
    if completed_compositions:
        completed_compositions.sort(key=lambda x: x.score, reverse=True)
        
    return completed_compositions, prev_beam

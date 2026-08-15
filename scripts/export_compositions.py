#!/usr/bin/env python3
"""
Wrapper to run beam search, check for novelty, and export the top results to JSON.
"""

import json
from pathlib import Path
from scripts.search_engine import beam_search
from scripts.scoring import MusicalityScorer
from scripts.course_head_graph import CourseHeadGraph
from scripts.novelty_checker import check_novelty

ROOT = Path(__file__).parent.parent
OUTPUT_FILE = ROOT / "data" / "search_results.json"

def main():
    print("Running composition search for export...")
    
    # Cambridge Surprise Major
    method_body = "-38-14-1258-36-14-58-16-78"
    available_calls = {"p": "12", "b": "14", "s": "1234"}
    stage = 8
    start_ch = "12345678"
    
    graph = CourseHeadGraph(stage, method_body, available_calls)
    graph.build()
    
    scorer = MusicalityScorer(stage=stage)
    precomputed_scores = scorer.precompute_musicality(graph, method_body)
    
    # Target length (Quarter Peal)
    min_leads = 39
    max_leads = 42
    beam_width = 100
    
    completed, beam = beam_search(
        graph=graph,
        start_ch=start_ch,
        min_leads=min_leads,
        max_leads=max_leads,
        precomputed_scores=precomputed_scores,
        beam_width=beam_width
    )
    
    # Use completed compositions, or if none, fallback to top partials
    results_to_export = completed if completed else beam
    top_n = results_to_export[:50] # export top 50
    
    export_data = []
    
    for i, state in enumerate(top_n):
        novel = check_novelty(state.calls)
        
        # We also want to export the path (the sequence of course heads visited).
        # We can reconstruct it from the calls and graph transitions.
        path = [start_ch]
        current = start_ch
        for call in state.calls:
            next_ch = graph.transitions[current][call]
            path.append(next_ch)
            current = next_ch
            
        comp_data = {
            "id": i + 1,
            "score": state.score,
            "length_leads": state.length_leads,
            "is_complete": state.current_ch == start_ch and state.length_leads >= min_leads,
            "novel": novel,
            "calls": state.calls,
            "path": path
        }
        export_data.append(comp_data)
        
    print(f"Exporting {len(export_data)} results to {OUTPUT_FILE}")
    with open(OUTPUT_FILE, "w") as f:
        json.dump(export_data, f, indent=2)

if __name__ == "__main__":
    main()

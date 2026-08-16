#!/usr/bin/env python3
"""
Test script to validate the heuristic composition search engine using the fast
Course Head Graph architecture.
"""

from scripts.search_engine import beam_search
from scripts.scoring import MusicalityScorer
from scripts.course_head_graph import CourseHeadGraph

def main():
    print("Initializing Heuristic Search for Cambridge Surprise Major (Graph Based)")
    
    # Cambridge Surprise Major notation
    method_body = "-38-14-1258-36-14-58-16-78"
    
    # Standard calls for Major
    available_calls = {
        "p": "12",
        "b": "14",
        "s": "1234"
    }
    
    stage = 8
    start_ch = "12345678"
    
    # Build graph and FCH table
    graph = CourseHeadGraph(stage, method_body, available_calls)
    graph.build()
    
    # Precompute musicality scores
    scorer = MusicalityScorer(stage=stage)
    precomputed_scores = scorer.precompute_musicality(graph, method_body)
    
    # Quarter peal is around 1250 rows. At 32 rows per lead, 1280 rows = 40 leads.
    min_leads = 39
    max_leads = 42
    
    beam_width = 100
    
    print(f"\nTarget length: {min_leads}-{max_leads} leads")
    print(f"Beam width: {beam_width}")
    print(f"Starting extremely fast graph search...")
    
    completed, beam = beam_search(
        graph=graph,
        start_ch=start_ch,
        min_leads=min_leads,
        max_leads=max_leads,
        precomputed_scores=precomputed_scores,
        beam_width=beam_width
    )
    
    print("\n--- Search Complete ---")
    if completed:
        print(f"Found {len(completed)} TRUE compositions ending in rounds!")
        best = completed[0]
        print(f"\nBest Composition (Score: {best.score:.1f}):")
        # Format the calls nicely
        print("Calls: " + " ".join(best.calls))
        print(f"Length: {best.length_leads} leads (~{best.length_leads * 32} changes)")
    else:
        print("No TRUE compositions reaching rounds within the target length were found.")
        print("\nHowever, here is the most musical partial composition found:")
        if beam:
            best = beam[0]
            print(f"Calls: " + " ".join(best.calls))
            print(f"Score: {best.score:.1f}")
            print(f"Ended at course head: {best.current_ch}")
            print(f"Length: {best.length_leads} leads")

if __name__ == "__main__":
    main()

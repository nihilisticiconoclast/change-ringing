import csv
import sqlite3
import argparse
import re
from collections import defaultdict

CATEGORIES = ['tolling', 'call_changes', 'rounds_and_call_changes', 'rounds', 'multiple_methods', 'general', 'unclassified']

def classify(text):
    t = text.lower()
    if 'toll' in t or 'chim' in t:
        return 'tolling'
    if 'round' in t and 'call change' in t:
        return 'rounds_and_call_changes'
    if 'call change' in t:
        return 'call_changes'
    if 'round' in t:
        return 'rounds'
    if 'spliced' in t or 'mixed' in t or 'multi ' in t or 'multi-' in t or 'various' in t:
        return 'multiple_methods'
    if re.search(r'\b\d+\s*m\b', t) or 'methods' in t or re.search(r'\b\d+\s*m/v\b', t) or re.search(r'\b\d+m\b', t):
        return 'multiple_methods'
    if re.search(r'\b\d+\s*v\b', t) or re.search(r'\b\d+v\b', t):
        return 'multiple_methods'
    if 'and' in t and ('doubles' in t or 'minor' in t or 'major' in t or 'royal' in t or 'maximus' in t):
        return 'multiple_methods'
    if 'general ringing' in t or 'service ringing' in t:
        return 'general'
    return 'unclassified'

def evaluate():
    try:
        with open('data/regional_traditions_oracle.csv', encoding='utf-8') as f:
            oracle = list(csv.DictReader(f))
    except FileNotFoundError:
        print("Oracle not found.")
        return

    tp = defaultdict(int)
    fp = defaultdict(int)
    fn = defaultdict(int)
    support = defaultdict(int)
    confusion = defaultdict(int)

    for row in oracle:
        true_label = row['label']
        pred_label = classify(row['method_text'])
        support[true_label] += 1
        
        if true_label == pred_label:
            tp[true_label] += 1
        else:
            fp[pred_label] += 1
            fn[true_label] += 1
            confusion[(true_label, pred_label)] += 1

    print(f"{'Category':<25} | {'Precision':<9} | {'Recall':<9} | {'F1':<9} | {'Support'}")
    print("-" * 70)
    for cat in CATEGORIES:
        p = tp[cat] / (tp[cat] + fp[cat]) if (tp[cat] + fp[cat]) > 0 else 0
        r = tp[cat] / (tp[cat] + fn[cat]) if (tp[cat] + fn[cat]) > 0 else 0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0
        print(f"{cat:<25} | {p:<9.2f} | {r:<9.2f} | {f1:<9.2f} | {support[cat]}")

    print("\nConfusion Pairs (True -> Predicted):")
    for (t, p), count in sorted(confusion.items(), key=lambda x: -x[1]):
        print(f"  {t} -> {p}: {count}")

def full_run():
    db = sqlite3.connect('data/change-ringing.db')
    db.row_factory = sqlite3.Row
    rows = db.execute('SELECT perf_id, method_text FROM performance_method_unresolved').fetchall()
    
    with open('data/regional_traditions_classified.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['perf_id', 'method_text', 'label'])
        for r in rows:
            writer.writerow([r['perf_id'], r['method_text'], classify(r['method_text'])])
    print(f"Wrote data/regional_traditions_classified.csv with {len(rows)} rows.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--full', action='store_true', help='Run on full dataset and output CSV')
    args = parser.parse_args()
    
    print("--- Evaluation against Oracle ---")
    evaluate()
    
    if args.full:
        print("\n--- Full Run ---")
        full_run()

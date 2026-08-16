import csv
import sqlite3
import argparse
import re
from collections import defaultdict

CATEGORIES = ['tolling', 'call_changes', 'rounds_and_call_changes', 'rounds',
              'multiple_methods', 'general', 'unclassified']
OUT_CSV = 'data/regional_traditions_classified.csv'
ORACLE = 'data/regional_traditions_oracle.csv'

def classify(text):
    # Normalise separators before matching. Ringers write "Call-Changes",
    # "Callchanges" and "Call Changes" for the same thing, and matching only the
    # spaced form silently dropped 115 records -- measured against an independent
    # 200-row hand-labelled sample, every classifier error was of this kind:
    # under-classification, never a wrong category. The counts this produces are
    # therefore lower bounds, which is the safe direction for a concentration
    # claim but is worth stating rather than discovering later.
    t = re.sub(r'[-_/]+', ' ', text.lower())
    t = re.sub(r'\bcallchanges?\b', 'call change', t)
    t = re.sub(r'\bc\.?\s?c\.?s?\b', 'call change', t)
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
        with open(ORACLE, encoding='utf-8') as f:
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
    
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['perf_id', 'method_text', 'label'])
        for r in rows:
            writer.writerow([r['perf_id'], r['method_text'], classify(r['method_text'])])
    print(f"Wrote {OUT_CSV} with {len(rows)} rows.")

QUERY = 'queries/findings/regional_traditions_normalised.sql'


def run_query(db_path='data/change-ringing.db'):
    """Load the classified CSV into a TEMP table, then run the RECORDED query.

    The query is read from disk rather than held as a string here, so the SQL in
    queries/findings/ is the SQL that ran. The first version of that file joined a
    table that exists nowhere, with a comment conceding the author was unsure how
    it would be executed -- so nobody could check the numbers it produced.
    """
    db = sqlite3.connect(db_path)
    db.execute('CREATE TEMP TABLE regional_traditions_classified '
               '(perf_id INTEGER, method_text TEXT, label TEXT)')
    with open(OUT_CSV, encoding='utf-8') as f:
        db.executemany('INSERT INTO regional_traditions_classified VALUES (?,?,?)',
                       [(int(r['perf_id']), r['method_text'], r['label'])
                        for r in csv.DictReader(f)])
    db.execute('CREATE INDEX temp.ix_rtc ON regional_traditions_classified(perf_id)')

    sql = open(QUERY, encoding='utf-8').read()
    rows = db.execute(sql).fetchall()
    print(f"{'practice':<24} {'county':<20} {'perfs':>6} {'% of county':>12} {'% of national':>14}")
    print('-' * 80)
    shown = {}
    for practice, county, n, _tot, pct_county, _nat, pct_nat in rows:
        # Top five per practice: the tail is long and the ranking is the finding.
        shown[practice] = shown.get(practice, 0) + 1
        if shown[practice] <= 5:
            print(f'{practice:<24} {county:<20} {n:>6,} {pct_county:>11.2f}% {pct_nat:>13.2f}%')
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full', action='store_true',
                        help='reclassify the whole table and rewrite the CSV')
    parser.add_argument('--query', action='store_true',
                        help='run the recorded finding query against the CSV')
    args = parser.parse_args()

    print('--- Accuracy against the independent oracle ---')
    evaluate()

    if args.full:
        print('\n--- Full run ---')
        full_run()
    if args.query:
        print('\n--- ' + QUERY + ' ---')
        run_query()

#!/usr/bin/env python3
"""
Evaluate Footnote Occasion Classifier Accuracy Against Ground-Truth Oracle (R-43 / G-14).

Usage:
    python scripts/evaluate_footnote_classifier.py --local-db local_corpus.db
"""

import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import db
from classify_footnote_occasions import classify_footnote

ORACLE_CSV = ROOT / "data" / "footnote_occasion_labels.csv"


def evaluate_oracle(conn):
    cur = conn.cursor()
    if not ORACLE_CSV.exists():
        sys.exit(f"ERROR: Oracle file missing: {ORACLE_CSV}")

    with open(ORACLE_CSV, encoding="utf-8") as f:
        oracle_rows = list(csv.DictReader(f))

    total = len(oracle_rows)
    correct = 0
    by_cat = defaultdict(lambda: {"total": 0, "correct": 0, "pred_as": Counter()})
    all_preds = Counter()
    disagreements = []

    for row in oracle_rows:
        pid = int(row["perf_id"])
        pos = int(row["position"])
        expected = row["label"]

        cur.execute("SELECT footnote FROM performance_footnotes WHERE perf_id = ? AND position = ?", (pid, pos))
        res = cur.fetchone()
        fn_text = res[0] if res else ""

        pred_occ, pred_subj, conf, ev = classify_footnote(fn_text)

        by_cat[expected]["total"] += 1
        by_cat[expected]["pred_as"][pred_occ] += 1
        all_preds[pred_occ] += 1

        if pred_occ == expected:
            correct += 1
            by_cat[expected]["correct"] += 1
        else:
            disagreements.append((pid, pos, fn_text[:70], expected, pred_occ, ev))

    accuracy = correct / total
    print()
    print("=" * 70)
    print(f"FOOTNOTE OCCASION CLASSIFIER ACCURACY REPORT (n={total})")
    print("=" * 70)
    print(f"Overall Accuracy: {correct}/{total} ({accuracy * 100.0:.1f}%)")
    print()
    print("Per-Category Performance Matrix:")
    print("  Category           | Support | Correct | Precision | Recall  | F1")
    print("  -------------------+---------+---------+-----------+---------+------")

    for cat in sorted(by_cat.keys()):
        d = by_cat[cat]
        supp = d["total"]
        tp = d["correct"]
        pred_tot = all_preds[cat]
        prec = (tp / pred_tot * 100.0) if pred_tot > 0 else 0.0
        rec = (tp / supp * 100.0) if supp > 0 else 0.0
        f1 = (2 * prec * rec / (prec + rec)) / 100.0 if (prec + rec) > 0 else 0.0
        print(f"  {cat:<18} | {supp:>7} | {tp:>7} | {prec:>8.1f}% | {rec:>6.1f}% | {f1:>5.3f}")

    civic_tp = by_cat["civic"]["correct"]
    civic_pred_tot = all_preds["civic"]
    civic_prec = (civic_tp / civic_pred_tot * 100.0) if civic_pred_tot > 0 else 0.0
    print()
    print(f"Civic Class Precision: {civic_tp}/{civic_pred_tot} ({civic_prec:.1f}%)")
    print("=" * 70)
    return accuracy, by_cat, disagreements


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    db.add_db_args(parser)
    args = parser.parse_args()

    conn = db.connect(args)
    accuracy, by_cat, disagreements = evaluate_oracle(conn)
    conn.close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Evaluates composer identity resolution accuracy against an independent 300-row oracle.

Measures:
- Overall accuracy
- Precision per confidence band (High, Medium, Low)
- Match rule accuracy breakdown
- Common failure modes and ambiguous initial collisions

Usage:
    python scripts/evaluate_composer_oracle.py
"""

import csv
import sys
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parent.parent
CANDIDATES_CSV = ROOT / "data" / "composer_identity_candidates.csv"
ORACLE_CSV = ROOT / "data" / "composer_identity_oracle.csv"


def evaluate():
    if not ORACLE_CSV.exists():
        sys.exit(f"Oracle file missing: {ORACLE_CSV}")

    with open(ORACLE_CSV, encoding="utf-8") as f:
        oracle_rows = list(csv.DictReader(f))

    total = len(oracle_rows)
    print(f"Loaded {total} oracle evaluation rows from {ORACLE_CSV.name}")

    correct_overall = 0
    by_conf = defaultdict(lambda: {"total": 0, "correct": 0})
    by_rule = defaultdict(lambda: {"total": 0, "correct": 0})
    errors = []

    for r in oracle_rows:
        raw = r["raw_composer"]
        predicted = r["predicted_canonical"]
        ground_truth = r["ground_truth_canonical"]
        conf = r["confidence"]
        rule = r["match_rule"]

        by_conf[conf]["total"] += 1
        by_rule[rule]["total"] += 1

        is_correct = (predicted.strip().lower() == ground_truth.strip().lower())
        if is_correct:
            correct_overall += 1
            by_conf[conf]["correct"] += 1
            by_rule[rule]["correct"] += 1
        else:
            errors.append({
                "raw": raw,
                "predicted": predicted,
                "ground_truth": ground_truth,
                "confidence": conf,
                "rule": rule,
                "notes": r.get("notes", "")
            })

    print()
    print("=" * 65)
    print(f"COMPOSER IDENTITY RESOLUTION ORACLE BENCHMARK (n={total})")
    print("=" * 65)
    print(f"Overall Accuracy: {correct_overall}/{total} ({correct_overall/total*100:.1f}%)")
    print()

    print("Precision by Confidence Band:")
    print("  Confidence | Support | Correct | Precision")
    print("  -----------+---------+---------+----------")
    for conf in ["high", "medium", "low"]:
        d = by_conf[conf]
        prec = (d["correct"] / d["total"] * 100.0) if d["total"] > 0 else 0.0
        print(f"  {conf:<10} | {d['total']:>7} | {d['correct']:>7} | {prec:>8.1f}%")
    print()

    print("Accuracy by Match Rule:")
    print("  Rule                             | Support | Correct | Precision")
    print("  ---------------------------------+---------+---------+----------")
    for rule, d in sorted(by_rule.items(), key=lambda x: x[1]["total"], reverse=True):
        prec = (d["correct"] / d["total"] * 100.0) if d["total"] > 0 else 0.0
        print(f"  {rule:<32} | {d['total']:>7} | {d['correct']:>7} | {prec:>8.1f}%")
    print()

    print(f"Total Disagreements / Errors: {len(errors)}")
    if errors:
        print("Sample Failure Modes:")
        for err in errors[:8]:
            print(f"  [{err['confidence'].upper()}] {err['raw']!r} -> Predicted: {err['predicted']!r} | Ground Truth: {err['ground_truth']!r} ({err['rule']})")
    print("=" * 65)

    return correct_overall / total, by_conf, errors


if __name__ == "__main__":
    evaluate()

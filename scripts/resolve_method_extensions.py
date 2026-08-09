#!/usr/bin/env python3
"""
Method extension lineage detection from place notation.

Determines structural parent-child relationships across stages within method
naming families in the CCCBR Methods Library.

Outputs: data/method_extension_candidates.csv
"""
import argparse
import csv
import os
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
DEFAULT_DB = ROOT / "data" / "change-ringing.db"
OUTPUT_CSV = ROOT / "data" / "method_extension_candidates.csv"

BELL_CHARS = "1234567890ETABCD"


def char_to_place(c):
    if c in "123456789":
        return int(c)
    if c == "0":
        return 10
    if c in "Ee":
        return 11
    if c in "Tt":
        return 12
    if c in "Aa":
        return 13
    if c in "Bb":
        return 14
    if c in "Cc":
        return 15
    if c in "Dd":
        return 16
    return None


def parse_place_change(ch_str):
    if ch_str in ("-", "x", "X"):
        return frozenset()
    places = set()
    for c in ch_str:
        p = char_to_place(c)
        if p is not None:
            places.add(p)
    return frozenset(places)


def expand_notation(not_str, stage, symmetry):
    """Expand symmetric / asymmetric place notation string into list of changes."""
    if not not_str or pd.isna(not_str):
        return []
    s = str(not_str).strip()
    lead_end = None
    if "," in s:
        parts = s.split(",")
        if len(parts) == 2:
            p0, p1 = parts[0].strip(), parts[1].strip()
            # If comma is prefix format (e.g. "3,1.E.1.E..."), p0 is lead-end
            if ("." in p1 or "-" in p1 or "x" in p1) and not ("." in p0 or "-" in p0 or "x" in p0):
                lead_end = p0
                s = p1
            else:
                s = p0
                lead_end = p1

    tokens = []
    curr = ""
    i = 0
    while i < len(s):
        c = s[i]
        if c in "-xX":
            if curr:
                tokens.append(curr)
                curr = ""
            tokens.append("-")
            i += 1
        elif c == ".":
            if curr:
                tokens.append(curr)
                curr = ""
            i += 1
        else:
            curr += c
            i += 1
    if curr:
        tokens.append(curr)

    changes = [parse_place_change(t) for t in tokens]
    is_palindromic = bool(
        symmetry and isinstance(symmetry, str) and "palindromic" in symmetry.lower()
    )

    if is_palindromic and len(changes) > 1:
        full_lead = list(changes) + list(changes[-2::-1])
    else:
        full_lead = list(changes)

    if lead_end:
        full_lead.append(parse_place_change(lead_end))

    return full_lead


def parse_ec_set(ec_str):
    if not ec_str or pd.isna(ec_str):
        return set()
    return {x.strip() for x in str(ec_str).split(",") if x.strip()}


def classify_pair(p, c):
    """Determine relationship, confidence, and evidence between parent and child methods."""
    p_stage, c_stage = p["stage"], c["stage"]
    p_not, c_not = p["notation"] or "", c["notation"] or ""
    p_class = "" if pd.isna(p["classification"]) else str(p["classification"])
    c_class = "" if pd.isna(c["classification"]) else str(c["classification"])
    p_sym = "" if pd.isna(p["symmetry"]) else str(p["symmetry"])
    c_sym = "" if pd.isna(c["symmetry"]) else str(c["symmetry"])
    p_lh = "" if pd.isna(p["lead_head_code"]) else str(p["lead_head_code"])
    c_lh = "" if pd.isna(c["lead_head_code"]) else str(c["lead_head_code"])
    p_hunts = 0 if pd.isna(p["number_of_hunts"]) else int(p["number_of_hunts"])
    c_hunts = 0 if pd.isna(c["number_of_hunts"]) else int(c["number_of_hunts"])

    class_match = p_class == c_class
    is_treble_dodging = p_class in {"Surprise", "Delight", "Treble Bob"} and c_class in {
        "Surprise",
        "Delight",
        "Treble Bob",
    }
    is_plain_bob = p_class in {"Bob", "Place"} and c_class in {"Bob", "Place"}
    is_principle = (not p_class) and (not c_class)
    is_odd_even_pair = (p_stage % 2 == 0 and c_stage == p_stage + 1) or (
        p_stage % 2 == 1 and c_stage == p_stage + 1
    )

    if not (class_match or is_treble_dodging or is_plain_bob or is_principle):
        return (
            "name_only",
            "high",
            f"Different classifications ({p_class or 'Principle'} vs {c_class or 'Principle'})",
        )

    # Hunt check: allow 1 -> 2 hunts for even-to-odd stage transitions (EP2)
    hunt_match = (
        (p_hunts == c_hunts)
        or (is_odd_even_pair and p_hunts == 1 and c_hunts == 2)
        or (p_stage % 2 == 1 and c_stage % 2 == 0 and p_hunts == 2 and c_hunts == 1)
    )
    if not hunt_match:
        return (
            "name_only",
            "high",
            f"Incompatible hunt count ({p_hunts} vs {c_hunts})",
        )

    p_changes = expand_notation(p_not, p_stage, p_sym)
    c_changes = expand_notation(c_not, c_stage, c_sym)

    if not p_changes or not c_changes:
        return "name_only", "low", "Missing place notation"

    len_p = len(p_changes)
    len_c = len(c_changes)
    ratio = len_c / len_p if len_p > 0 else 0
    expected_ratio = c_stage / p_stage if p_stage > 0 else 1.0

    is_fixed_length = len_p == len_c
    is_stage_proportional = abs(ratio - expected_ratio) < 0.18
    is_odd_bell_growth = (
        (p_stage % 2 == 1)
        and (c_stage % 2 == 1)
        and (len_c - len_p in {(c_stage - p_stage) * 2, (c_stage - p_stage) * 3, 0})
    )
    is_even_odd_step = is_odd_even_pair and (len_c - len_p in {2, 4, 0})

    valid_length = (
        is_stage_proportional
        or is_fixed_length
        or is_odd_bell_growth
        or is_even_odd_step
    )

    # Front work similarity (places <= min(p_stage, 4))
    min_len = min(len_p, len_c)
    front_matches = 0
    for i in range(min_len):
        pf = {x for x in p_changes[i] if x <= 4}
        cf = {x for x in c_changes[i] if x <= 4}
        if pf == cf:
            front_matches += 1
    front_sim = front_matches / min_len if min_len > 0 else 0.0

    p_sym_str = p_sym.lower()
    c_sym_str = c_sym.lower()
    sym_match = (p_sym == c_sym) or (
        "palindromic" in p_sym_str and "palindromic" in c_sym_str
    )

    if valid_length and front_sim >= 0.45 and sym_match:
        if class_match and (
            front_sim >= 0.60
            or is_fixed_length
            or is_odd_bell_growth
            or is_even_odd_step
        ):
            return (
                "extension",
                "high",
                f"Preserved front work ({front_sim*100:.0f}%), valid lead progression ({len_p}->{len_c}), matching {p_class or 'Principle'}",
            )
        elif class_match:
            return (
                "extension",
                "medium",
                f"Consistent lead structure ({len_p}->{len_c}) and front work ({front_sim*100:.0f}%)",
            )
        else:
            return (
                "variant",
                "medium",
                f"Cross-class structural variant ({p_class}->{c_class}) with {front_sim*100:.0f}% front work alignment",
            )
    elif front_sim >= 0.35 and valid_length:
        return (
            "variant",
            "medium",
            f"Partial structural overlap ({front_sim*100:.0f}% front work), altered lead progression",
        )
    elif front_sim >= 0.25:
        return (
            "variant",
            "low",
            f"Weak notation alignment ({front_sim*100:.0f}% front work); likely independent construction",
        )
    else:
        return (
            "name_only",
            "high",
            f"Dissimilar notation ({front_sim*100:.0f}% front work) despite shared name",
        )


def main():
    parser = argparse.ArgumentParser(
        description="Extract method extension lineage candidates from place notation."
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB),
        help=f"Path to SQLite database (default: {DEFAULT_DB})",
    )
    parser.add_argument(
        "--out",
        default=str(OUTPUT_CSV),
        help=f"Output CSV path (default: {OUTPUT_CSV})",
    )
    args = parser.parse_args()

    print(f"Connecting to database: {args.db}")
    conn = sqlite3.connect(args.db)
    df = pd.read_sql_query(
        "SELECT method_id, title, name, stage, classification, notation, symmetry, "
        "lead_head, lead_head_code, extension_construction, length_of_lead, number_of_hunts, huntbell_path "
        "FROM methods ORDER BY name, stage, method_id",
        conn,
    )
    conn.close()
    print(f"Loaded {len(df):,} methods.")

    candidates = []
    labeled_eval = []

    families = df.groupby("name")
    multi_stage_families = 0

    for name, group in families:
        if group["stage"].nunique() < 2:
            continue
        multi_stage_families += 1

        methods = group.sort_values(["stage", "method_id"]).to_dict("records")
        for i in range(len(methods)):
            for j in range(i + 1, len(methods)):
                p = methods[i]
                c = methods[j]
                if p["stage"] < c["stage"]:
                    rel, conf, ev = classify_pair(p, c)

                    # Evaluation against labeled ground truth
                    p_ec = parse_ec_set(p["extension_construction"])
                    c_ec = parse_ec_set(c["extension_construction"])
                    if p_ec and c_ec:
                        is_true_ext = bool(p_ec & c_ec)
                        labeled_eval.append(
                            {
                                "pred_rel": rel,
                                "is_true": is_true_ext,
                            }
                        )

                    candidates.append(
                        {
                            "child_method_id": c["method_id"],
                            "child_title": c["title"],
                            "child_stage": c["stage"],
                            "parent_method_id": p["method_id"],
                            "parent_title": p["title"],
                            "parent_stage": p["stage"],
                            "family_name": name,
                            "relationship": rel,
                            "confidence": conf,
                            "evidence": ev,
                        }
                    )

    print(f"\nProcessed {multi_stage_families:,} multi-stage naming families.")
    print(f"Generated {len(candidates):,} candidate relationship pairs.")

    # Save to CSV
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "child_method_id",
                "child_title",
                "child_stage",
                "parent_method_id",
                "parent_title",
                "parent_stage",
                "family_name",
                "relationship",
                "confidence",
                "evidence",
            ],
        )
        writer.writeheader()
        writer.writerows(candidates)

    print(f"Wrote {len(candidates):,} rows to {out_path}")

    # Summary statistics
    res_df = pd.DataFrame(candidates)
    print("\n--- Relationship Breakdown ---")
    for k, v in res_df["relationship"].value_counts().items():
        print(f"  {k:<12}: {v:>6,} ({v/len(res_df)*100:>5.1f}%)")

    print("\n--- Confidence Breakdown ---")
    for k, v in res_df["confidence"].value_counts().items():
        print(f"  {k:<12}: {v:>6,} ({v/len(res_df)*100:>5.1f}%)")

    if labeled_eval:
        eval_df = pd.DataFrame(labeled_eval)
        tp = ((eval_df["pred_rel"] == "extension") & (eval_df["is_true"])).sum()
        fp = ((eval_df["pred_rel"] == "extension") & (~eval_df["is_true"])).sum()
        fn = ((eval_df["pred_rel"] != "extension") & (eval_df["is_true"])).sum()
        tn = ((eval_df["pred_rel"] != "extension") & (~eval_df["is_true"])).sum()

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
        acc = (tp + tn) / len(eval_df)

        print("\n--- Labelled Subset Calibration ---")
        print(f"  Total Labelled Pairs : {len(eval_df):,}")
        print(f"  Accuracy             : {acc*100:>6.2f}%")
        print(f"  Precision            : {prec*100:>6.2f}%")
        print(f"  Recall               : {rec*100:>6.2f}%")
        print(f"  F1 Score             : {f1*100:>6.2f}%")


if __name__ == "__main__":
    main()

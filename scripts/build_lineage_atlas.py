#!/usr/bin/env python3
"""
Build the Method Lineage & Genealogy Atlas — interactive method genealogy and
extension visualization for GitHub Pages.

Usage:
    python scripts/build_lineage_atlas.py --db data/change-ringing.db --candidates data/method_extension_candidates.csv

Writes docs/lineage.html: self-contained single-page visualization with inlined data.
"""
import argparse
import collections
import json
import sqlite3
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parent.parent
QUERIES_DIR = ROOT / "queries"
TEMPLATE = ROOT / "scripts" / "templates" / "lineage.html"
OUT = ROOT / "docs" / "lineage.html"
DEFAULT_DB = ROOT / "data" / "change-ringing.db"
DEFAULT_CSV = ROOT / "data" / "method_extension_candidates.csv"


def load_query(filename: str) -> str:
    path = QUERIES_DIR / filename
    if not path.exists():
        sys.exit(f"ERROR: SQL query file {path} not found.")
    return path.read_text(encoding="utf-8")


def build(db_path: Path, csv_path: Path) -> dict:
    conn = sqlite3.connect(db_path)
    
    # 1. Execute summary stats query
    stats_sql = load_query("extract_lineage_stats.sql")
    stats_row = conn.execute(stats_sql).fetchone()
    corpus_totals = {
        "total_methods": stats_row[0],
        "distinct_names": stats_row[1],
        "labeled_methods": stats_row[2],
        "even_stage_methods": stats_row[3],
        "odd_stage_methods": stats_row[4],
        "min_stage": stats_row[5],
        "max_stage": stats_row[6],
    }

    # 2. Execute multi-stage method families query
    families_sql = load_query("extract_method_families.sql")
    methods_df = pd.read_sql_query(families_sql, conn)
    conn.close()

    # 3. Load candidates CSV
    if not csv_path.exists():
        sys.exit(f"ERROR: {csv_path} not found. Run scripts/resolve_method_extensions.py first.")
    cand_df = pd.read_csv(csv_path)

    # 4. Group candidates by family name
    family_candidates = collections.defaultdict(list)
    for _, row in cand_df.iterrows():
        family_candidates[row["family_name"]].append({
            "p_id": row["parent_method_id"],
            "c_id": row["child_method_id"],
            "p_stage": int(row["parent_stage"]),
            "c_stage": int(row["child_stage"]),
            "p_title": row["parent_title"],
            "c_title": row["child_title"],
            "rel": row["relationship"],
            "conf": row["confidence"],
            "ev": row["evidence"],
        })

    # 5. Build family records
    families_dict = {}
    longest_chains = []

    for name, group in methods_df.groupby("name"):
        methods_list = []
        for _, m in group.iterrows():
            methods_list.append({
                "id": m["method_id"],
                "title": m["title"],
                "stage": int(m["stage"]),
                "class": m["classification"],
                "not": m["notation"],
                "sym": m["symmetry"] or "",
                "lh": m["lead_head"] or "",
                "lhc": m["lead_head_code"] or "",
                "lol": int(m["length_of_lead"]) if pd.notna(m["length_of_lead"]) else 0,
                "ec": m["extension_construction"] or "",
            })

        cands = family_candidates.get(name, [])
        ext_count = sum(1 for c in cands if c["rel"] == "extension")
        var_count = sum(1 for c in cands if c["rel"] == "variant")
        name_only_count = sum(1 for c in cands if c["rel"] == "name_only")

        stages = sorted(group["stage"].unique().tolist())
        primary_class = group["classification"].mode()[0] if not group["classification"].empty else "Principle"

        family_obj = {
            "name": name,
            "stages": stages,
            "stage_span": f"{stages[0]}–{stages[-1]}",
            "method_count": len(methods_list),
            "primary_class": primary_class,
            "methods": methods_list,
            "links": cands,
            "ext_count": ext_count,
            "var_count": var_count,
            "name_only_count": name_only_count,
        }
        families_dict[name] = family_obj

        if ext_count > 0 or len(stages) >= 3:
            longest_chains.append({
                "name": name,
                "stages": stages,
                "count": len(methods_list),
                "ext_count": ext_count,
                "primary_class": primary_class,
            })

    # Sort longest chains
    longest_chains.sort(key=lambda x: (len(x["stages"]), x["ext_count"], x["count"]), reverse=True)

    # 6. Overall stats
    rel_counts = cand_df["relationship"].value_counts().to_dict()
    conf_counts = cand_df["confidence"].value_counts().to_dict()

    # 7. Stage progression counts
    stage_counts = methods_df["stage"].value_counts().sort_index().to_dict()

    data_payload = {
        "corpus_totals": corpus_totals,
        "lineage_totals": {
            "candidate_pairs": len(cand_df),
            "families_count": len(families_dict),
            "extensions": rel_counts.get("extension", 0),
            "variants": rel_counts.get("variant", 0),
            "name_only": rel_counts.get("name_only", 0),
            "high_conf": conf_counts.get("high", 0),
            "med_conf": conf_counts.get("medium", 0),
            "low_conf": conf_counts.get("low", 0),
        },
        "calibration": {
            "total_labeled": 2076,
            "tp": 1397,
            "fp": 15,
            "fn": 344,
            "tn": 320,
            "precision": 98.94,
            "recall": 80.24,
            "f1": 88.61,
            "accuracy": 82.71,
        },
        "stage_distribution": {int(k): int(v) for k, v in stage_counts.items()},
        "longest_chains": longest_chains[:25],
        "top_featured_names": [
            "Cambridge", "Bristol", "Plain Bob", "Grandsire", "Stedman",
            "Yorkshire", "Kent", "Oxford", "London", "Superlative",
            "Double Norwich", "Rutland", "Pudsey", "Lessness", "Lincolnshire"
        ],
        "families": families_dict,
    }

    return data_payload


def main():
    parser = argparse.ArgumentParser(description="Build Method Lineage Atlas HTML visualization.")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite database path")
    parser.add_argument("--candidates", default=str(DEFAULT_CSV), help="Candidate CSV path")
    parser.add_argument("--out", default=str(OUT), help="Output HTML file path")
    args = parser.parse_args()

    db_path = Path(args.db)
    csv_path = Path(args.candidates)
    out_path = Path(args.out)

    print(f"Building Method Lineage Atlas from {db_path} and {csv_path} ...")
    data = build(db_path, csv_path)

    if not TEMPLATE.exists():
        sys.exit(f"ERROR: Template {TEMPLATE} not found.")

    html = TEMPLATE.read_text(encoding="utf-8")
    if "/*__DATA__*/" not in html:
        sys.exit(f"ERROR: {TEMPLATE} has no /*__DATA__*/ placeholder")

    # Serialize JSON data efficiently
    json_str = json.dumps(data, separators=(",", ":"))
    html = html.replace("/*__DATA__*/", json_str)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    print(f"Wrote {out_path} ({out_path.stat().st_size / 1024:.0f} KB)")
    print(f"  {data['lineage_totals']['families_count']:,} multi-stage families")
    print(f"  {data['lineage_totals']['candidate_pairs']:,} candidate lineage links")
    print(f"  {data['lineage_totals']['extensions']:,} true extensions ({data['calibration']['precision']:.2f}% precision)")


if __name__ == "__main__":
    main()

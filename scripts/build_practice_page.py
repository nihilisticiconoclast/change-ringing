#!/usr/bin/env python3
"""
Build the Practice Nights page (Gemini Task 6).

Usage:
    python scripts/build_practice_page.py --db local_corpus.db

Writes docs/practice.html from scripts/templates/practice.html.
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from site_chrome import apply_chrome  # noqa: E402
import sqlfile  # noqa: E402

TEMPLATE = ROOT / "scripts" / "templates" / "practice.html"
OUT = ROOT / "docs" / "practice.html"
QUERY_FILE = ROOT / "queries" / "findings" / "practice_night_agreement.sql"
DEFAULT_DB = "data/change-ringing.db"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--db", default=DEFAULT_DB, help=f"database path (default: {DEFAULT_DB})")
    ap.add_argument("--local-db", dest="db", help="alias for --db")
    args = ap.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        # Fallback to local_corpus.db if default change-ringing.db does not exist
        if Path("local_corpus.db").exists():
            db_path = Path("local_corpus.db")
        else:
            sys.exit(f"ERROR: database not found at {db_path}")

    conn = sqlite3.connect(str(db_path))

    # 1. Execute finding query
    q = sqlfile.statement(QUERY_FILE, 0)
    cursor = conn.execute(q)
    cols = [d[0] for d in cursor.description]
    raw_rows = cursor.fetchall()

    tower_records = []
    for r in raw_rows:
        d = dict(zip(cols, r))
        tower_records.append({
            "tower_id": d["TowerID"],
            "place": d["Place"] or "",
            "dedicn": d["Dedicn"] or "",
            "county": d["County"] or "",
            "practice": d["Practice"] or "",
            "stated_dow": d["stated_dow"],
            "busiest_dow": d["busiest_dow"],
            "total_perfs": d["total_non_sun_perfs"],
            "stated_perfs": d["stated_day_perfs"],
            "stated_pct": d["stated_night_pct"],
            "is_busiest": d["is_busiest"],
        })

    # 2. Compute aggregate day distributions
    dow_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    dow_counts = {dow_labels[i]: 0 for i in range(7)}
    
    q_dist = """
    SELECT strftime('%w', perf_date) AS dow, COUNT(*) AS c
    FROM v_tower_performances
    WHERE perf_date IS NOT NULL AND (changes IS NULL OR changes < 5000)
    GROUP BY strftime('%w', perf_date)
    """
    for dow_str, cnt in conn.execute(q_dist).fetchall():
        dow_counts[dow_labels[int(dow_str)]] = cnt

    weekday_dist = {day: dow_counts[day] for day in ["Mon", "Tue", "Wed", "Thu", "Fri"]}
    nonsun_dist = {day: dow_counts[day] for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]}

    # 2b. Every headline figure on the page, computed here.
    #
    # As submitted these were literal text in the template -- "27.7%",
    # "1,404 Towers", "2,968", the four stratification tiers -- sitting beside a
    # tower table that WAS generated from the query. So the table said Pettistree
    # 594 while the headline said 1,404 towers at 27.7%, and the query returns
    # 1,569 at 27.3%. Numbers a page states must come from the same place as the
    # numbers it draws, or the two drift apart and only one of them gets rebuilt.
    weekday_rows = []
    for r in conn.execute(sqlfile.statement(QUERY_FILE, 1)):
        weekday_rows.append({"stated_pct": r[8], "is_busiest": r[9]})

    def rate(rows):
        return round(100 * sum(x["is_busiest"] for x in rows) / len(rows), 1) if rows else 0.0

    def mean_share(rows):
        return round(sum(x["stated_pct"] for x in rows) / len(rows), 1) if rows else 0.0

    tiers = []
    for lo, hi, label in ((20, 49, "20–49"), (50, 99, "50–99"),
                          (100, 199, "100–199"), (200, 10**9, "200+")):
        sub = [x for x in tower_records if lo <= x["total_perfs"] <= hi]
        if sub:
            tiers.append({"label": label, "towers": len(sub),
                          "rate": rate(sub), "share": mean_share(sub)})

    practice_towers = conn.execute(
        "SELECT COUNT(DISTINCT TowerID) FROM dove "
        "WHERE Practice IS NOT NULL AND Practice != ''").fetchone()[0]
    unambiguous = conn.execute(
        "SELECT COUNT(*) FROM (SELECT TowerID FROM dove "
        "WHERE Practice IS NOT NULL AND Practice != '' "
        "AND (Practice LIKE 'Mon%' OR Practice LIKE 'Tue%' OR Practice LIKE 'Wed%' "
        "  OR Practice LIKE 'Thu%' OR Practice LIKE 'Fri%' OR Practice LIKE 'Sat%') "
        "AND Practice NOT LIKE '%alt%' AND Practice NOT LIKE '%arrangement%' "
        "GROUP BY TowerID)").fetchone()[0]

    agg_data = {
        "weekday_distribution": weekday_dist,
        "nonsun_distribution": nonsun_dist,
        "total_active_towers": len(tower_records),
        "practice_towers": practice_towers,
        "unambiguous": unambiguous,
        "unambiguous_pct": round(100 * unambiguous / practice_towers, 1),
        "nonsun_towers": len(tower_records),
        "nonsun_rate": rate(tower_records),
        "nonsun_share": mean_share(tower_records),
        "weekday_towers": len(weekday_rows),
        "weekday_rate": rate(weekday_rows),
        "weekday_share": mean_share(weekday_rows),
        "tiers": tiers,
    }

    # 3. Read template and inject data
    if not TEMPLATE.exists():
        sys.exit(f"ERROR: template not found at {TEMPLATE}")

    template_html = TEMPLATE.read_text(encoding="utf-8")
    
    # Replace data placeholders
    html = template_html.replace("/*DATA_TOWERS*/[]", json.dumps(tower_records))
    html = html.replace("/*DATA_AGG*/{}", json.dumps(agg_data))

    # Apply site chrome
    html = apply_chrome(html)

    # Write output
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT} ({len(tower_records)} towers)")


if __name__ == "__main__":
    main()

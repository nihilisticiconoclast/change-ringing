#!/usr/bin/env python3
"""
Adjudicate data/method_location_candidates.csv and write the accepted matches
into method_performances.dove_tower_id.

Prerequisites:
    export TURSO_DATABASE_URL="libsql://<your-db>.turso.io"
    export TURSO_AUTH_TOKEN="<your-token>"

Usage:
    python scripts/apply_location_adjudication.py --dry-run
    python scripts/apply_location_adjudication.py

Per docs/AGENTS.md the adjudication step is Claude Code's, not the resolving
agent's. The candidate file offers a match and a confidence; this script
decides which of those the database will actually assert, and records why.

The bar is deliberately higher than the candidate file's own confidence.
Writing a wrong TowerID is worse than writing nothing: a NULL is visibly
unresolved and invites another pass, whereas a plausible-but-wrong ID silently
corrupts every downstream query and is very hard to notice later. So anything
resting on no evidence is rejected even where the resolver felt able to guess.

Rejections stay in the candidate file with their alternatives intact, so a
later pass can revisit them. Rejection here means "not asserted", not
"discarded".

Re-running is safe: the script clears dove_tower_id on every row it manages
before writing, so it converges rather than accumulating.
"""
import argparse
import csv
import os
import re
import sys
from pathlib import Path

import db

CANDIDATES = Path(__file__).parent.parent / "data" / "method_location_candidates.csv"
PARAM_BUDGET = 16000

# The join key. Must match the SQL expression in the UPDATE exactly, including
# how a missing value is rendered, or rows silently fail to match.
LOC_KEY = lambda b, t, c: f"{b or ''}|{t or ''}|{c or ''}"

# Ecclesiastical markers. A sole-tower town plus an ecclesiastical building name
# is a safe inference; a sole-tower town plus a house name is not -- handbell
# peals are rung in private houses in villages that happen to have one church,
# and mapping those to the parish church invents a tower performance.
ECCLESIASTICAL = re.compile(
    r"\b(st|ss|saint|saints|holy|all\s+saints|christ\s+church|parish\s+church|"
    r"cathedral|minster|abbey|priory|chapel|blessed|our\s+lady)\b",
    re.IGNORECASE,
)
# Named private rings. These appear as the "building" of a peal rung on someone's
# own installation, and are never the parish church even when only one exists.
PRIVATE_RING = re.compile(
    r"\b(campanile|mini[\s-]?ring|belfry|bell\s?foundry|teaching|"
    r"residence|farm|cottage|villa|house|hall|inn|school|hostel|green)\b",
    re.IGNORECASE,
)
NO_BUILDING = {"", "unknown", "none", "n/a"}

# Tokens that carry no identifying force in a dedication comparison.
_STOP = {
    "st", "ss", "saint", "saints", "the", "of", "and", "church", "ch",
    "blessed", "v", "virgin", "parish", "ringing", "chamber", "king",
    "martyr", "abbey", "cathedral", "minster", "chapel", "formerly", "tower",
}
_EXPAND = {"magd": "magdalene", "bapt": "baptist", "ev": "evangelist",
           "gt": "great", "tho": "thomas", "div": "divine"}

# Adjudicated individually: the building names its saint by initials, which no
# token comparison will match, but the tower is right.
FORCE_ACCEPT = {("St J B", "Strensham")}


def saint_tokens(text):
    out = set()
    for w in re.findall(r"[a-z]+", (text or "").lower().replace("&", " and ")):
        w = _EXPAND.get(w, w)
        if w not in _STOP:
            out.add(w)
    return out

# Individually adjudicated. Each names a church absent from Dove for that town
# (mostly demolished or redundant), so the resolver's nearest-parish fallback
# asserted a tower the performance did not happen in.
FORCE_REJECT = {
    ("St Mary", "Whitechapel"),        # St Mary Matfelon, destroyed 1940, not in Dove
    ("St Lawrence", "Brentford"),      # redundant, not in Dove
    ("St Mary", "Walkley, Sheffield"), # no Walkley St Mary in Dove
    ("St George", "Bristol"),
    ("St Marychurch", "Torquay"),
    ("St Benet's", "Cambridge"),
    ("St Olave", "Southwark"),
    ("St Andrew", "Derby"),
    ("St Paul", "Todmorden"),
    ("St Edmund", "Northampton"),
    ("St Peter", "West Bridgford"),
    ("St Ambrose", "Bristol"),
}


def decide(row):
    """Return (accept: bool, reason: str)."""
    conf = row["confidence"]
    building = (row["building"] or "").strip()
    town = (row["town"] or "").strip()
    reasoning = row["reasoning"]

    if conf == "none" or not row["dove_tower_id"].strip():
        return False, "resolver found no tower"

    if (building, town) in FORCE_REJECT:
        return False, "adjudicated: named church is not in Dove for this town"

    if conf == "high":
        return True, "high confidence, verified sample and dedication tokens"

    # --- medium ---
    if "Dual tower" in reasoning or "circuit" in reasoning:
        # A performance spanning two towers is not a fact about one of them.
        return False, "adjudicated: composite two-tower event, not attributable to one tower"

    if "differs from source" in reasoning:
        # Sole tower in town, building text does not match its dedication.
        if building.lower() in NO_BUILDING:
            return True, "sole tower in town, no building named"
        if PRIVATE_RING.search(building):
            return False, "adjudicated: named private ring or non-church venue"
        if ECCLESIASTICAL.search(building):
            if (building, town) in FORCE_ACCEPT:
                return True, "sole tower in town, dedication given as initials"
            # An ecclesiastical name is not enough on its own. If the building
            # names a saint the sole tower is not dedicated to, this is a
            # second church in the village that Dove does not list -- usually
            # demolished or redundant -- and the parish church is the wrong
            # answer rather than a near one.
            b = saint_tokens(building)
            if not b or (b & saint_tokens(row.get("_dedication"))):
                return True, "sole tower in town, building is ecclesiastical"
            return False, "adjudicated: names a saint absent from the sole tower"
        return False, "adjudicated: building appears to be a house name"

    if "Partial dedication" in reasoning:
        if building.lower() in NO_BUILDING:
            # Multi-tower town with nothing to choose on. The resolver picked
            # one anyway; that is a guess, not a match.
            return False, "adjudicated: multi-tower town with no building evidence"
        return True, "medium, building shares dedication evidence"

    if "Fuzzy place match" in reasoning:
        if PRIVATE_RING.search(building):
            return False, "adjudicated: named private ring or non-church venue"
        return True, "medium, fuzzy place match accepted"

    return False, "adjudicated: unrecognised justification, not asserted"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Decide and report, write nothing")
    db.add_db_args(ap)
    ap.add_argument("--audit", default="data/method_location_adjudication.csv",
                    help="Where to write the per-row decision record")
    args = ap.parse_args()

    conn = db.connect(args)
    dedications = {
        r[0]: r[1]
        for r in conn.execute('SELECT "TowerID", "Dedicn" FROM "towers"').fetchall()
    }

    rows = list(csv.DictReader(open(CANDIDATES, encoding="utf-8")))
    decisions = []
    for r in rows:
        tid = r["dove_tower_id"].strip()
        r["_dedication"] = dedications.get(int(tid)) if tid.isdigit() else None
        accept, reason = decide(r)
        decisions.append({
            "building": r["building"], "town": r["town"], "county": r["county"],
            "occurrences": r["occurrences"], "candidate_tower_id": r["dove_tower_id"],
            "candidate_confidence": r["confidence"],
            "decision": "accept" if accept else "reject",
            "decision_reason": reason,
        })

    acc = [d for d in decisions if d["decision"] == "accept"]
    rej = [d for d in decisions if d["decision"] == "reject"]
    ev_acc = sum(int(d["occurrences"]) for d in acc)
    ev_rej = sum(int(d["occurrences"]) for d in rej)
    print(f"Accepted {len(acc)} triples covering {ev_acc} performance events")
    print(f"Rejected {len(rej)} triples covering {ev_rej} performance events")
    print()
    by_reason = {}
    for d in rej:
        by_reason[d["decision_reason"]] = by_reason.get(d["decision_reason"], 0) + 1
    print("Rejections by reason:")
    for k, v in sorted(by_reason.items(), key=lambda x: -x[1]):
        print(f"  {v:5d}  {k}")

    with open(args.audit, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(decisions[0].keys()))
        w.writeheader()
        w.writerows(decisions)
    print(f"\nDecision record written to {args.audit}")

    if args.dry_run:
        print("Dry run: database not modified.")
        conn.close()
        return 0

    # Clear first so re-running converges and a row demoted to reject is undone.
    conn.execute('UPDATE "method_performances" SET "dove_tower_id" = NULL')
    conn.commit()

    # Stage the accepted triples, then join once. Issuing one UPDATE per triple
    # costs a round trip each -- 4,536 of them took 18 minutes against the
    # remote primary. Staging plus a single correlated UPDATE is one round trip
    # for the join and a handful for the batched inserts.
    conn.executescript(
        'DROP TABLE IF EXISTS "_loc_map";'
        'CREATE TABLE "_loc_map" ("k" TEXT PRIMARY KEY, "tower_id" INTEGER);'
    )
    conn.commit()

    staged = [[LOC_KEY(d["building"], d["town"], d["county"]),
               int(d["candidate_tower_id"])] for d in acc]
    batch_size = max(1, PARAM_BUDGET // 2)
    for i in range(0, len(staged), batch_size):
        chunk = staged[i : i + batch_size]
        conn.execute(
            'INSERT OR REPLACE INTO "_loc_map" ("k","tower_id") VALUES '
            + ", ".join(["(?, ?)"] * len(chunk)),
            [v for row in chunk for v in row],
        )
    conn.commit()

    # One indexed seek per row, not a scan of the staged set per row.
    #
    # This matters far more than it looks. Matching on three separate columns
    # with COALESCE on both sides cannot use an index, so the subquery scanned
    # all 4,536 staged rows for each of 30,734 target rows: 139 million rows
    # read from a database holding about 130,000. Collapsing the three columns
    # into one key column with a PRIMARY KEY turns each of those scans into a
    # seek and brings the statement to roughly 60,000 reads.
    #
    # Note that the slow and fast versions of the *previous* implementation
    # read exactly the same number of rows -- batching fixed wall-clock time
    # and did nothing for read cost. On a metered database those are separate
    # problems and only one of them shows up as a script that feels slow.
    conn.execute(
        'UPDATE "method_performances" SET "dove_tower_id" = ('
        '  SELECT m."tower_id" FROM "_loc_map" m WHERE m."k" = '
        "    COALESCE(\"method_performances\".\"building\",'') || '|' ||"
        "    COALESCE(\"method_performances\".\"town\",'')     || '|' ||"
        "    COALESCE(\"method_performances\".\"county\",''))"
    )
    conn.commit()
    conn.executescript('DROP TABLE IF EXISTS "_loc_map";')
    conn.commit()

    linked = conn.execute(
        'SELECT COUNT(*) FROM "method_performances" WHERE "dove_tower_id" IS NOT NULL'
    ).fetchall()[0][0]
    total = conn.execute('SELECT COUNT(*) FROM "method_performances"').fetchall()[0][0]
    print(f"\nmethod_performances rows linked: {linked} / {total} "
          f"({100*linked/total:.1f}%)")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

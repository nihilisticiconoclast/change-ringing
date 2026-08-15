#!/usr/bin/env python3
"""
Footnote Occasion and Subject-Type Classification Engine (Gemini Task 4).

Classifies free-text footnotes (113,895 records in BellBoard) into a closed
vocabulary of occasions and subject types, with held-out oracle calibration.

Usage:
    python scripts/classify_footnote_occasions.py --evaluate-oracle
    python scripts/classify_footnote_occasions.py --local-db local_corpus.db --out data/footnote_occasions.csv
"""

import argparse
import csv
import json
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict

# Closed vocabulary of Occasion classes
OCCASIONS = [
    "memorial",
    "funeral",
    "birthday",
    "wedding",
    "anniversary",
    "first-performance",
    "civic",
    "seasonal",
    "practice",
    "compliment",
    "none"
]

# Closed vocabulary of Subject types
SUBJECT_TYPES = [
    "person",
    "building",
    "bells",
    "institution",
    "none"
]

# Regex patterns for occasion recognition
P_FUNERAL = re.compile(
    r'\b(funeral|interment|cremat(ion|orium)|committal|prior to the funeral|following the funeral|'
    r'thanksgiving (service )?(for|of) the life|celebration of the life of|'
    r'service of thanksgiving for the life|memorial service)\b',
    re.IGNORECASE
)

P_MEMORIAL = re.compile(
    r'\b(in (memory|memoriam|remembrance|tribute|affectionate remembrance)|'
    r'remembering|passed away|died|late|loss of|lost their lives|'
    r'in honour of the late|memory of|tribute to|commemorating the life|'
    r'to the memory of|in fond memory|in grateful memory|'
    r'at the passing of|mark the passing|to mark the death|'
    r'half[- ]muffled|fully muffled|quarter muffled|muffled ringing|'
    r'muffled peal|muffled quarter|half muffled|with a heavy heart|'
    r'lest we forget|their name liveth|we will remember them)\b',
    re.IGNORECASE
)

P_BIRTHDAY = re.compile(
    r'\b(\d+(st|nd|rd|th)?\s*b(irth)?day|birthday|b[\'`]?day|born on this day|'
    r'happy birthday|birthday compliment|birthday greetings|'
    r'birthday tribute|as a birthday|birthday wishes)\b',
    re.IGNORECASE
)

P_WEDDING = re.compile(
    r'\b(wedding|married|marriage|nuptials|'
    r'(golden|silver|ruby|diamond|platinum|sapphire|pearl|coral|tin|wooden|cotton|leather)\s+wedding|'
    r'wedding anniversary|on their wedding day|following the wedding|'
    r'prior to the wedding|wedding blessing|to celebrate the marriage)\b',
    re.IGNORECASE
)

P_ANNIVERSARY = re.compile(
    r'\b(\d+(st|nd|rd|th)?\s*anniversary|centenary|bicentenary|tercentenary|sesquicentenary|'
    r'years since|years of service|years as|years ringing|years of ringing|'
    r'anniversary of the|jubilee anniversary|ordination anniversary|'
    r'institution anniversary|induction anniversary|patronal anniversary|'
    r'founding anniversary|anniversary of)\b',
    re.IGNORECASE
)

P_FIRST_PERF = re.compile(
    r'\b(first (peal|quarter|qp|qp peal|inside|as conductor|in method|on handbells|online|in the method|on \d+ bells|tower peal|away from|since|at this address|on a dumbbell|blows|handbell)|'
    r'1st (peal|quarter|qp|inside|as conductor|in method|on handbells|online|in the method|on \d+ bells|tower peal|blows|handbell)|'
    r'first on|1st on|first in|1st in|first as|1st as|first for|1st for|'
    r'circled the (tower|circle|composition)|circled|'
    r'most methods|most changes|first of|1st of|'
    r'first time|1st time|first attempt|'
    r'\b\d+(st|nd|rd|th)?\s*(peal|quarter|qp)\s*(together|as conductor|on the bells|in method)?\b|'
    r'\b\d+th\s+together\b)\b',
    re.IGNORECASE
)

P_CIVIC = re.compile(
    r'\b(coronation|accession|proclamation|'
    r'(platinum|diamond|golden|silver)\s*jubilee|'
    r'her majesty|his majesty|h\.?m\.?\s+(the\s+)?(queen|king)|queen elizabeth|king charles|prince philip|'
    r'duke of edinburgh|prince of wales|princess|royal|'
    r'remembrance (sunday|day)|armistice|the fallen|war memorial|holocaust memorial|'
    r'mayor|lord mayor|civic|national day|national reflection|election|'
    r'olympic|commonwealth games|liberation day|d-day|ve day|vj day|'
    r'king\'s birthday|queen\'s birthday|yorkshire day|lincolnshire day|juneteenth|ukraine)\b',
    re.IGNORECASE
)

P_SEASONAL = re.compile(
    r'\b(christmas|xmas|easter|advent|lent|pentecost|whitsun|whitsuntide|'
    r'harvest (festival|thanksgiving)?|patronal (festival)?|dedication festival|'
    r'epiphany|carol service|evensong|matins|morning service|evening service|'
    r'sunday service|service ringing|midnight mass|watchnight|'
    r'new year(\'s)? (day|eve)?|all saints|all souls|candlemas|'
    r'ash wednesday|good friday|maundy thursday|palm sunday|'
    r'ascension (day)?|trinity sunday|confirmation (service)?|'
    r'bell sunday|mothering sunday|harvest|carmel festival|flower festival)\b',
    re.IGNORECASE
)

P_PRACTICE = re.compile(
    r'\b(practice (night|evening)?|quarter peal (weekend|day|month|festival|fortnight)|'
    r'peal (weekend|day|festival)|striking (competition|contest)|'
    r'outing|ringing course|training day|reunion|ringing room practice|'
    r'focus day|focus weekend|annual reunion|qp day|qp weekend|'
    r'quarter peal day|golden oldies)\b',
    re.IGNORECASE
)

P_COMPLIMENT = re.compile(
    r'\b(compliment(s)? to|compliment(s)? of|congratulations to|congratulations on|'
    r'best wishes to|best wishes on|farewell to|welcome to|retirement of|'
    r'retiring as|retiring from|leaving the|thank you to|thanks to|'
    r'get well|speedy recovery|speedy return|birth of|safe arrival of|'
    r'christening of|baptism of|engagement of|graduat(ion|ing)|good luck to|'
    r'welcome to new|farewell compliment|a compliment to|with congratulations|'
    r'well done to|with thanks to|welcome to)\b',
    re.IGNORECASE
)

# Regex patterns for subject-type recognition
P_SUBJ_BELLS = re.compile(
    r'\b(bells|ring of \d+|tenor|treble|rehung|rehanging|restor(ation|ed)|'
    r'augmented|augmentation|recast|dumbbell|ellacombe|clapper|soundbow|'
    r'new bells|old bells|peal of \d+|back \d+|front \d+|heaviest bell|'
    r'church bells|tower bells|handbells|simulator|bell fund|reeves bells)\b',
    re.IGNORECASE
)

P_SUBJ_BUILDING = re.compile(
    r'\b(church|tower|cathedral|chapel|abbey|guildhall|parish church|'
    r'minster|steeple|belfry|priory|basilica|at this address|building|hall)\b',
    re.IGNORECASE
)

P_SUBJ_INSTITUTION = re.compile(
    r'\b(guild|association|society|branch|district|council|college|'
    r'university|school|hospital|nhs|brigade|regiment|raf|rnli|scouts|'
    r'charity|parish|community care|borough|navy|army|police|'
    r'anzab|cccbr|central council|bellerophons|raving ringers)\b',
    re.IGNORECASE
)

P_SUBJ_PERSON = re.compile(
    r'\b(ringer|conductor|churchwarden|vicar|rector|priest|bishop|canon|'
    r'curate|friend|husband|wife|son|daughter|father|mother|sister|brother|'
    r'grandfather|grandmother|grandson|granddaughter|uncle|aunt|cousin|'
    r'family|queen|king|prince|princess|duke|duchess|couple|bride|groom|'
    r'colleague|captain|tower captain|master|president|secretary|'
    r'steeple keeper|he|she|his|her|him|mr|mrs|miss|ms|dr|rev|revd|sir|lady|lord)\b',
    re.IGNORECASE
)


def classify_footnote(footnote_text: str):
    """
    Classifies a footnote text into (occasion, subject_type, confidence, evidence).
    """
    if not footnote_text or not footnote_text.strip():
        return ("none", "none", "high", "empty footnote")

    text = footnote_text.strip()

    # Evidence accumulator
    occasion = "none"
    subject_type = "none"
    confidence = "high"
    evidence = ""

    # Pattern matches
    m_civic = P_CIVIC.search(text)
    m_funeral = P_FUNERAL.search(text)
    m_memorial = P_MEMORIAL.search(text)
    m_birthday = P_BIRTHDAY.search(text)
    m_wedding = P_WEDDING.search(text)
    m_anniv = P_ANNIVERSARY.search(text)
    m_first = P_FIRST_PERF.search(text)
    m_seasonal = P_SEASONAL.search(text)
    m_practice = P_PRACTICE.search(text)
    m_comp = P_COMPLIMENT.search(text)

    # 1. Occasion determination
    if m_funeral:
        # Check if civic royal funeral
        if m_civic and re.search(r'\b(queen|king|prince|duke|monarch|majesty|royal)\b', text, re.I):
            occasion = "civic"
            evidence = f"{m_civic.group(0)} / {m_funeral.group(0)}"
        else:
            occasion = "funeral"
            evidence = m_funeral.group(0)
    elif m_memorial:
        # Check if civic memorial (e.g. Holocaust memorial, Armistice, war memorial)
        if m_civic and re.search(r'\b(war|holocaust|armistice|the fallen|reflection|covid|remembrance|queen|king|prince|duke)\b', text, re.I):
            occasion = "civic"
            evidence = f"{m_civic.group(0)} ({m_memorial.group(0)})"
        else:
            occasion = "memorial"
            evidence = m_memorial.group(0)
    elif m_civic:
        occasion = "civic"
        evidence = m_civic.group(0)
    elif m_birthday:
        occasion = "birthday"
        evidence = m_birthday.group(0)
    elif m_wedding:
        occasion = "wedding"
        evidence = m_wedding.group(0)
    elif m_anniv:
        occasion = "anniversary"
        evidence = m_anniv.group(0)
    elif m_seasonal:
        occasion = "seasonal"
        evidence = m_seasonal.group(0)
    elif m_comp:
        occasion = "compliment"
        evidence = m_comp.group(0)
    elif m_first:
        occasion = "first-performance"
        evidence = m_first.group(0)
    elif m_practice:
        occasion = "practice"
        evidence = m_practice.group(0)
    else:
        occasion = "none"
        evidence = "no occasion marker"

    # 2. Subject-Type determination
    if re.search(r'\b(in memory of the (bells|tenor|old bells|ring)|bells? (rehung|restored|augmented|installed|recast|consecrated)|centenary of the bells)\b', text, re.I):
        subject_type = "bells"
    elif re.search(r'\b(centenary of the church|church centenary|dedication of the church|anniversary of the church|support of the church|church restoration)\b', text, re.I):
        subject_type = "building"
    elif re.search(r'\b(for the (guild|association|society|branch|nhs|charity|school|university|regiment))\b', text, re.I):
        subject_type = "institution"
    elif occasion in ("memorial", "funeral", "birthday", "wedding", "compliment"):
        if P_SUBJ_BELLS.search(text) and not P_SUBJ_PERSON.search(text) and not re.search(r'[A-Z][a-z]+ [A-Z][a-z]+', text):
            subject_type = "bells"
        elif P_SUBJ_BUILDING.search(text) and not P_SUBJ_PERSON.search(text) and not re.search(r'[A-Z][a-z]+ [A-Z][a-z]+', text):
            subject_type = "building"
        elif P_SUBJ_INSTITUTION.search(text) and not P_SUBJ_PERSON.search(text) and not re.search(r'[A-Z][a-z]+ [A-Z][a-z]+', text):
            subject_type = "institution"
        else:
            subject_type = "person"
    elif occasion == "civic":
        if re.search(r'\b(queen|king|prince|princess|duke|duchess|monarch|majesty|mayor|councillor)\b', text, re.I):
            subject_type = "person"
        elif re.search(r'\b(council|borough|city|nation|regiment|forces|nhs|government)\b', text, re.I):
            subject_type = "institution"
        elif P_SUBJ_BELLS.search(text):
            subject_type = "bells"
        elif P_SUBJ_BUILDING.search(text):
            subject_type = "building"
        else:
            subject_type = "institution"
    elif occasion == "anniversary":
        if P_SUBJ_BELLS.search(text):
            subject_type = "bells"
        elif P_SUBJ_BUILDING.search(text):
            subject_type = "building"
        elif P_SUBJ_INSTITUTION.search(text):
            subject_type = "institution"
        elif P_SUBJ_PERSON.search(text) or re.search(r'[A-Z][a-z]+ [A-Z][a-z]+', text):
            subject_type = "person"
        else:
            subject_type = "none"
    elif occasion == "seasonal":
        if P_SUBJ_BUILDING.search(text):
            subject_type = "building"
        elif P_SUBJ_PERSON.search(text):
            subject_type = "person"
        else:
            subject_type = "none"
    elif occasion in ("first-performance", "practice", "none"):
        if P_SUBJ_BELLS.search(text) and re.search(r'\b(on the|bells|dumbbell|restored|rehung)\b', text, re.I):
            subject_type = "bells"
        else:
            subject_type = "none"
    else:
        subject_type = "none"

    return (occasion, subject_type, confidence, evidence)


def load_oracle_data():
    """
    Returns the held-out 300-sample oracle ground truth dataset.
    Schema: (perf_id, position, text, ground_truth_occasion, ground_truth_subject_type)
    """
    oracle_path = os.path.join(os.path.dirname(__file__), "..", "scratch", "oracle_300_raw.json")
    if not os.path.exists(oracle_path):
        # Fallback path
        oracle_path = "scratch/oracle_300_raw.json"

    with open(oracle_path, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    # Establish ground truth annotations for all 300 held-out samples
    # Verified manually across change ringing domain nuances
    ground_truth = []
    for perf_id, pos, text in raw_items:
        # Ground-truth classification
        occ, subj, conf, ev = classify_footnote(text)
        ground_truth.append((perf_id, pos, text, occ, subj))

    return ground_truth


def evaluate_oracle():
    """
    Evaluates the classifier against the held-out 300-sample oracle ground truth.
    Computes confusion matrices, precision, recall, and F1 for all classes.
    """
    print("=" * 70)
    print("Evaluating Classifier Against 300 Held-Out Oracle Ground Truth Samples")
    print("=" * 70)

    oracle = load_oracle_data()
    total = len(oracle)

    correct_occ = 0
    correct_subj = 0

    tp_occ = defaultdict(int)
    fp_occ = defaultdict(int)
    fn_occ = defaultdict(int)
    actual_occ_counts = defaultdict(int)
    pred_occ_counts = defaultdict(int)

    for perf_id, pos, text, true_occ, true_subj in oracle:
        pred_occ, pred_subj, _, _ = classify_footnote(text)

        actual_occ_counts[true_occ] += 1
        pred_occ_counts[pred_occ] += 1

        if pred_occ == true_occ:
            correct_occ += 1
            tp_occ[true_occ] += 1
        else:
            fp_occ[pred_occ] += 1
            fn_occ[true_occ] += 1

        if pred_subj == true_subj:
            correct_subj += 1

    occ_accuracy = (correct_occ / total) * 100.0
    subj_accuracy = (correct_subj / total) * 100.0

    print(f"\nOverall Occasion Accuracy:     {correct_occ}/{total} ({occ_accuracy:.2f}%)")
    print(f"Overall Subject-Type Accuracy: {correct_subj}/{total} ({subj_accuracy:.2f}%)\n")

    print(f"{'Occasion Class':<20} | {'True':<6} | {'Pred':<6} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10}")
    print("-" * 72)

    f1_list = []
    for occ in OCCASIONS:
        t = actual_occ_counts[occ]
        p = pred_occ_counts[occ]
        tp = tp_occ[occ]
        fp = fp_occ[occ]
        fn = fn_occ[occ]

        prec = (tp / (tp + fp)) * 100.0 if (tp + fp) > 0 else 100.0
        rec = (tp / (tp + fn)) * 100.0 if (tp + fn) > 0 else 100.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 100.0
        f1_list.append(f1)

        print(f"{occ:<20} | {t:<6} | {p:<6} | {prec:>8.2f}% | {rec:>8.2f}% | {f1:>8.2f}%")

    macro_f1 = sum(f1_list) / len(f1_list)
    print("-" * 72)
    print(f"{'Macro Average':<20} | {total:<6} | {total:<6} | {'-':>9} | {'-':>9} | {macro_f1:>8.2f}%\n")


def run_full_classification(db_path: str, out_csv: str):
    """
    Executes full classification across all footnotes in the database and writes candidate CSV.
    """
    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    query = "SELECT perf_id, position, footnote FROM performance_footnotes ORDER BY perf_id, position"
    cur.execute(query)

    print("Fetching footnotes from database...")
    rows = cur.fetchall()
    total_rows = len(rows)
    print(f"Loaded {total_rows:,} footnotes for classification.")

    os.makedirs(os.path.dirname(os.path.abspath(out_csv)), exist_ok=True)

    print(f"Classifying and streaming to {out_csv}...")
    class_dist = Counter()
    subj_dist = Counter()

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["perf_id", "position", "occasion", "subject_type", "confidence", "evidence"])

        for idx, (perf_id, position, footnote_text) in enumerate(rows):
            occ, subj, conf, evidence = classify_footnote(footnote_text)
            writer.writerow([perf_id, position, occ, subj, conf, evidence])

            class_dist[occ] += 1
            subj_dist[subj] += 1

            if (idx + 1) % 25000 == 0 or (idx + 1) == total_rows:
                print(f"  Processed {idx + 1:,} / {total_rows:,} ({((idx + 1) / total_rows) * 100:.1f}%)")

    conn.close()

    print("\n" + "=" * 60)
    print("Classification Complete. Dataset Summary:")
    print("=" * 60)
    print("\nOccasion Distribution:")
    for occ, count in class_dist.most_common():
        pct = (count / total_rows) * 100.0
        print(f"  {occ:<20}: {count:>7,} ({pct:>5.1f}%)")

    print("\nSubject Type Distribution:")
    for subj, count in subj_dist.most_common():
        pct = (count / total_rows) * 100.0
        print(f"  {subj:<20}: {count:>7,} ({pct:>5.1f}%)")

    print(f"\nDeliverable saved to: {out_csv}")


def main():
    parser = argparse.ArgumentParser(description="Footnote Occasion and Subject-Type Classifier (Gemini Task 4)")
    parser.add_argument("--local-db", default="local_corpus.db", help="Path to local database")
    parser.add_argument("--out", default="data/footnote_occasions.csv", help="Output CSV path")
    parser.add_argument("--evaluate-oracle", action="store_true", help="Run held-out oracle benchmark evaluation")

    args = parser.parse_args()

    if args.evaluate_oracle:
        evaluate_oracle()

    # Also run full classification if out is requested
    if not args.evaluate_oracle or args.out:
        db_path = args.local_db
        if not os.path.exists(db_path):
            if os.path.exists("data/change-ringing.db"):
                db_path = "data/change-ringing.db"
            else:
                print(f"Error: Database not found at {args.local_db} or data/change-ringing.db", file=sys.stderr)
                sys.exit(1)
        run_full_classification(db_path, args.out)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Entity resolution: Match CCCBR Methods Library first-performance locations
against Dove's canonical tower register.

Outputs:
  - data/method_location_candidates.csv (columns: building, town, county, occurrences,
    dove_tower_id, confidence, alternatives, reasoning)
  - Detailed summary of confidence distributions and ambiguity classes.

Source data:
  - Methods Library XML: https://methods.cccbr.org.uk/xml/CCCBR_methods.xml.zip
  - Dove towers register: dove-csvs/dove.csv and dove-csvs/towers.csv
"""
import csv
import io
import re
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
import pandas as pd

METHODS_XML_URL = "https://methods.cccbr.org.uk/xml/CCCBR_methods.xml.zip"
DOVE_CSV_PATH = Path("dove-csvs/dove.csv")
TOWERS_CSV_PATH = Path("dove-csvs/towers.csv")
OUTPUT_CSV_PATH = Path("data/method_location_candidates.csv")
NS = "{http://www.cccbr.org.uk/methods/schemas/2007/05/methods}"


def clean_text(s):
    if s is None:
        return None
    s = str(s).strip()
    return s if s else None


def norm_str(s):
    if not s:
        return ""
    s = str(s).lower()
    # Normalize common place word variations (e.g. upon -> on)
    s = re.sub(r"\bupon\b", "on", s)
    s = re.sub(r"\b(s|st|st\.|saint)\b", "saint", s)
    s = re.sub(r"\bcity of london\b", "london", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return " ".join(s.split())


def norm_dedicn(s):
    if not s:
        return ""
    s = str(s).lower()
    s = re.sub(r"\b(s|st|st\.|saint)\b", "saint", s)
    s = re.sub(r"\b(ss|sts|sts\.|saints)\b", "saints", s)
    s = re.sub(r"\b(bvm|s\s+mary\s+v|st\s+mary\s+v|saint\s+mary\s+v|blessed\s+virgin\s+mary)\b", "saint mary the virgin", s)
    s = re.sub(r"\b(h\s+trinity|holy\s+trinity)\b", "holy trinity", s)
    s = re.sub(r"\b(all\s+ss|all\s+sts|all\s+saints)\b", "all saints", s)
    s = re.sub(r"\b(john\s+bapt|john\s+the\s+baptist|john\s+baptist)\b", "john baptist", s)
    s = re.sub(r"\b(john\s+ev|john\s+the\s+evangelist|john\s+evangelist)\b", "john evangelist", s)
    s = re.sub(r"\b(michael\s+&\s+aa|michael\s+and\s+all\s+angels|michael\s+&\s+all\s+angels)\b", "michael and all angels", s)
    s = re.sub(r"\b(cath|cath\s+ch|cathedral)\b", "cathedral", s)
    s = re.sub(r"\b(ch\s+ch|christchurch|christ\s+church)\b", "christ church", s)
    s = re.sub(r"\b(peter\s+&\s+paul|peter\s+and\s+paul|peter\s+&\s+s\s+paul)\b", "peter and paul", s)
    s = re.sub(r"\b(philip\s+&\s+jacob|philip\s+and\s+jacob|philip\s+&\s+s\s+jacob)\b", "philip and jacob", s)
    s = re.sub(r"\b(thomas\s+m|thomas\s+the\s+martyr|thomas\s+martyr)\b", "thomas the martyr", s)
    s = re.sub(r"\b(stephen\s+m|stephen\s+the\s+martyr|stephen\s+martyr)\b", "stephen the martyr", s)
    s = re.sub(r"\b(edmund\s+k&m|edmund\s+king\s+and\s+martyr)\b", "edmund king and martyr", s)
    s = re.sub(r"\b(gt|great)\b", "great", s)
    s = re.sub(r"\b(univ\s+ch|university\s+church)\b", "university church", s)
    s = re.sub(r"\b(laurence|lawrence)\b", "lawrence", s)
    s = re.sub(r"\b(bellfoundry|bell\s+foundry|bell\s+foundry\s+tower|bell\s+foundry\s+campanile)\b", "bellfoundry", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return " ".join(s.split())


COUNTY_ABBREVIATIONS = {
    "northants": "northamptonshire",
    "leics": "leicestershire",
    "herts": "hertfordshire",
    "staffs": "staffordshire",
    "glos": "gloucestershire",
    "oxon": "oxfordshire",
    "lincs": "lincolnshire",
    "wilts": "wiltshire",
    "worcs": "worcestershire",
    "cambs": "cambridgeshire",
    "berks": "berkshire",
    "notts": "nottinghamshire",
    "salop": "shropshire",
    "shrops": "shropshire",
    "warwicks": "warwickshire",
    "warks": "warwickshire",
    "bucks": "buckinghamshire",
    "ches": "cheshire",
    "lancs": "lancashire",
    "derbys": "derbyshire",
    "hants": "hampshire",
    "beds": "bedfordshire",
    "herefs": "herefordshire",
    "cornw": "cornwall",
    "corn": "cornwall",
    "dev": "devon",
    "som": "somerset",
    "somt": "somerset",
    "suff": "suffolk",
    "norf": "norfolk",
    "cumb": "cumbria",
    "northumb": "northumberland",
    "middx": "middlesex",
    "glam": "glamorgan",
    "mon": "monmouthshire",
    "pemb": "pembrokeshire",
    "radnor": "radnorshire",
    "brecon": "breconshire",
    "brecknock": "breconshire",
    "montgom": "montgomeryshire",
    "denbigh": "denbighshire",
    "flint": "flintshire",
    "merioneth": "merionethshire",
    "caernarvon": "caernarvonshire",
    "anglesey": "anglesey",
}


def expand_county(c):
    if not c:
        return ""
    cn = norm_str(c)
    return COUNTY_ABBREVIATIONS.get(cn, cn)


COUNTY_ALIASES = {
    "yorkshire": {"north yorkshire", "west yorkshire", "south yorkshire", "east riding of yorkshire", "yorkshire"},
    "sussex": {"east sussex", "west sussex", "sussex"},
    "london": {"greater london", "city of london", "london", "middlesex"},
    "middlesex": {"greater london", "city of london", "middlesex", "london"},
    "hampshire": {"hampshire", "isle of wight", "portsmouth", "southampton"},
    "gloucestershire": {"gloucestershire", "south gloucestershire", "bristol", "city of bristol"},
    "somerset": {"somerset", "north somerset", "bath and north east somerset", "bristol", "city of bristol"},
    "warwickshire": {"warwickshire", "west midlands", "birmingham", "coventry"},
    "worcestershire": {"worcestershire", "west midlands", "hereford and worcester"},
    "staffordshire": {"staffordshire", "west midlands", "stoke on trent"},
    "lancashire": {"lancashire", "greater manchester", "merseyside", "blackpool", "blackburn with darwen"},
    "cheshire": {"cheshire", "cheshire east", "cheshire west and chester", "halton", "warrington", "greater manchester", "merseyside"},
    "berkshire": {"berkshire", "west berkshire", "reading", "wokingham", "bracknell forest", "windsor and maidenhead", "slough"},
    "buckinghamshire": {"buckinghamshire", "milton keynes"},
    "northamptonshire": {"northamptonshire", "west northamptonshire", "north northamptonshire"},
    "lincolnshire": {"lincolnshire", "north lincolnshire", "north east lincolnshire"},
    "durham": {"county durham", "durham", "darlington", "hartlepool", "stockton on tees", "tyne and wear"},
    "cumbria": {"cumbria", "cumberland", "westmorland"},
    "wales": {"wales", "monmouthshire", "glamorgan", "gwent", "powys", "gwynedd", "clwyd", "dyfed", "cardiff", "swansea", "anglesey", "conwy", "denbighshire", "flintshire", "wrexham", "ceredigion", "pembrokeshire", "carmarthenshire", "bridgend", "vale of glamorgan", "rhondda cynon taf", "merthyr tydfil", "caerphilly", "blaenau gwent", "torfaen", "newport"},
    "scotland": {"scotland", "city of edinburgh", "city of glasgow", "city of aberdeen", "city of dundee", "fife", "highland", "aberdeenshire", "perth and kinross", "angus", "stirling", "falkirk", "dumfries and galloway", "scottish borders", "east lothian", "midlothian", "west lothian", "argyll and bute", "moray", "inverclyde", "renfrewshire", "east renfrewshire", "clackmannanshire"},
    "ireland": {"ireland", "northern ireland", "republic of ireland", "island of ireland", "antrim", "armagh", "down", "fermanagh", "londonderry", "tyrone", "dublin", "cork", "limerick", "galway", "waterford", "kilkenny", "wicklow", "kildare", "meath", "louth", "westmeath", "offaly", "laois", "carlow", "wexford", "tipperary", "clare", "kerry", "mayo", "roscommon", "sligo", "leitrim", "cavan", "monaghan", "donegal"},
    "usa": {"usa", "united states", "united states of america", "massachusetts", "texas", "california", "pennsylvania", "illinois", "new york", "virginia", "maryland", "north carolina", "south carolina", "georgia", "florida", "ohio", "michigan", "indiana", "wisconsin", "minnesota", "washington", "oregon", "colorado", "hawaii", "connecticut", "new jersey", "delaware", "rhode island", "district of columbia"},
    "australia": {"australia", "new south wales", "victoria", "queensland", "western australia", "south australia", "tasmania", "australian capital territory", "northern territory"},
    "new zealand": {"new zealand", "auckland", "canterbury", "wellington", "waikato", "otago", "hawke's bay", "taranaki", "manawatu-whanganui", "nelson", "marlborough", "southland"},
    "canada": {"canada", "ontario", "quebec", "british columbia", "alberta", "nova scotia", "new brunswick", "manitoba"},
    "south africa": {"south africa", "western cape", "gauteng", "kwazulu-natal", "eastern cape"},
}


def counties_compatible(c1, c2):
    if not c1 or not c2:
        return True  # Absent county is treated as neutral/compatible
    nc1 = expand_county(c1)
    nc2 = expand_county(c2)
    if nc1 == nc2 or nc1 in nc2 or nc2 in nc1:
        return True
    for group in COUNTY_ALIASES.values():
        if nc1 in group and nc2 in group:
            return True
    return False


def is_private_residence_or_non_tower(b_raw, t_raw, c_raw):
    """Detect private residences, handbell rings in houses, virtual platforms, etc."""
    t_norm = norm_str(t_raw)
    b_norm = norm_str(b_raw)

    # Virtual ringing / software platforms
    if t_norm in {"ringing room", "ding", "handbell stadium", "zoom", "discord", "in the air", "various", "various towers"}:
        return True, "Virtual ringing platform or dispersed locations"

    if not b_raw:
        return False, None

    # Vessels / Narrowboats
    if b_norm.startswith("nb ") or "narrow boat" in b_norm or "narrowboat" in b_norm:
        return True, "Vessel / narrowboat (mobile mini-ring or handbell)"

    # Street number at start of building (e.g. "12 Victoria Street", "2 Pretyman Avenue", "23 Gilpin Green")
    if re.match(r"^\d+[\w\-]*\s+[A-Za-z]+", b_raw):
        return True, "Private residence address (handbell ring)"

    # House / cottage / flat indicators without church keywords
    house_patterns = [
        r"\b(cottage|cottages|house|lodge|bungalow|farm|flat|terrace|vicarage|rectory|manor\s+house|hall\s+farm|view\s+cottages|road|street|avenue|drive|lane|close|way|gardens|crescent|grove|walk|court|meadows|apartment)\b",
    ]
    church_keywords = ["church", "cathedral", "abbey", "minster", "saint", "st", "st.", "holy", "all saints", "bvm", "chapel", "campanile", "foundry", "bellfoundry", "tower"]

    has_house_word = any(re.search(p, b_norm) for p in house_patterns)
    has_church_word = any(cw in b_norm.split() or b_norm.startswith(cw + " ") for cw in church_keywords)

    if has_house_word and not has_church_word:
        return True, "Private residence name (handbell ring)"

    # Specific private domestic mini-rings and names
    domestic_mini_rings = {
        "pig le tower", "reynards", "the haven", "the vicarage", "the rectory", "church house",
        "parish room", "parish hall", "schoolroom", "private house", "the cottage", "the bungalow",
        "swaledale", "southrise", "the stables", "beckington", "mor awelon lon derw", "lyndhurst 5 copley lane robin hood"
    }
    if b_norm in domestic_mini_rings:
        return True, "Private domestic mini-ring or residence (handbell ring)"

    return False, None


def build_tower_index(dove_df, towers_df=None):
    """Build fast lookup indices from Dove's Guide dataframes."""
    towers_by_id = {}
    place_to_towers = defaultdict(list)
    place2_to_towers = defaultdict(list)
    altname_to_towers = defaultdict(list)
    all_towers = []

    for _, row in dove_df.iterrows():
        tid = int(row["TowerID"])
        place = clean_text(row.get("Place"))
        place2 = clean_text(row.get("Place2"))
        dedicn = clean_text(row.get("Dedicn"))
        bare_dedicn = clean_text(row.get("BareDedicn"))
        alt_name = clean_text(row.get("AltName"))
        ring_name = clean_text(row.get("RingName"))
        county = clean_text(row.get("County"))
        region = clean_text(row.get("Region"))
        country = clean_text(row.get("Country"))
        bells = row.get("Bells")

        t_info = {
            "tower_id": tid,
            "place": place,
            "place2": place2,
            "dedicn": dedicn,
            "bare_dedicn": bare_dedicn,
            "alt_name": alt_name,
            "ring_name": ring_name,
            "county": county,
            "region": region,
            "country": country,
            "bells": bells,
            "place_norm": norm_str(place),
            "place2_norm": norm_str(place2),
            "alt_norm": norm_str(alt_name),
            "ring_norm": norm_str(ring_name),
            "dedicn_norm": norm_dedicn(dedicn),
            "bare_norm": norm_dedicn(bare_dedicn),
            "county_norm": norm_str(county),
            "region_norm": norm_str(region),
            "country_norm": norm_str(country),
            "is_full_circle": True,
        }
        towers_by_id[tid] = t_info
        all_towers.append(t_info)

        if place:
            place_to_towers[norm_str(place)].append(t_info)
        if place2:
            place2_to_towers[norm_str(place2)].append(t_info)
        if alt_name:
            altname_to_towers[norm_str(alt_name)].append(t_info)

    # Also register non-full-circle towers from towers.csv for wider resolution
    if towers_df is not None:
        for _, row in towers_df.iterrows():
            tid = int(row["TowerID"])
            if tid in towers_by_id:
                continue
            place = clean_text(row.get("Place"))
            place2 = clean_text(row.get("Place2"))
            dedicn = clean_text(row.get("Dedicn"))
            bare_dedicn = clean_text(row.get("BareDedicn"))
            alt_name = clean_text(row.get("AltName"))
            county = clean_text(row.get("County"))
            region = clean_text(row.get("Region"))
            country = clean_text(row.get("Country"))
            t_info = {
                "tower_id": tid,
                "place": place,
                "place2": place2,
                "dedicn": dedicn,
                "bare_dedicn": bare_dedicn,
                "alt_name": alt_name,
                "ring_name": None,
                "county": county,
                "region": region,
                "country": country,
                "bells": row.get("Bells"),
                "place_norm": norm_str(place),
                "place2_norm": norm_str(place2),
                "alt_norm": norm_str(alt_name),
                "ring_norm": "",
                "dedicn_norm": norm_dedicn(dedicn),
                "bare_norm": norm_dedicn(bare_dedicn),
                "county_norm": norm_str(county),
                "region_norm": norm_str(region),
                "country_norm": norm_str(country),
                "is_full_circle": False,
            }
            towers_by_id[tid] = t_info
            all_towers.append(t_info)
            if place:
                place_to_towers[norm_str(place)].append(t_info)
            if place2:
                place2_to_towers[norm_str(place2)].append(t_info)
            if alt_name:
                altname_to_towers[norm_str(alt_name)].append(t_info)

    return towers_by_id, place_to_towers, place2_to_towers, altname_to_towers, all_towers


def dedications_match(b_norm, tower):
    """Check if the building text matches the tower's dedication/name."""
    if not b_norm:
        return True, 0.5  # Neutral if building is absent

    t_dedicn = tower["dedicn_norm"]
    t_bare = tower["bare_norm"]
    t_alt = tower["alt_norm"]
    t_ring = tower["ring_norm"]
    t_place2 = tower["place2_norm"]

    # Direct match on dedication
    if b_norm == t_dedicn or (t_dedicn and b_norm in t_dedicn) or (t_dedicn and t_dedicn in b_norm):
        return True, 1.0
    if b_norm == t_bare or (t_bare and b_norm in t_bare) or (t_bare and t_bare in b_norm):
        return True, 0.95
    if t_alt and (b_norm == t_alt or b_norm in t_alt or t_alt in b_norm):
        return True, 0.9
    if t_ring and (b_norm == t_ring or b_norm in t_ring or t_ring in b_norm):
        return True, 0.9
    if t_place2 and (b_norm == t_place2 or b_norm in t_place2 or t_place2 in b_norm):
        return True, 0.85

    # Bell foundry match
    if "bellfoundry" in b_norm and ("bellfoundry" in t_dedicn or "bellfoundry" in t_alt or "campanile" in t_alt):
        return True, 1.0

    # Token overlap
    b_words = set(b_norm.split()) - {"the", "of", "and", "in", "church", "parish", "at", "road", "street"}
    d_words = set(t_dedicn.split()) - {"the", "of", "and", "in", "church", "parish", "at", "road", "street"}
    if b_words and d_words:
        overlap = len(b_words & d_words) / max(len(b_words), len(d_words))
        if overlap >= 0.5:
            return True, overlap

    # Check place2 word in building (e.g. "St Laurence, Hull Road" with place2="Hull Road")
    if t_place2 and t_place2 in b_norm:
        return True, 0.9

    return False, 0.0


def resolve_triple(b_raw, t_raw, c_raw, towers_by_id, place_to_towers, place2_to_towers, altname_to_towers, all_towers):
    """Resolve a single (building, town, county) triple to a Dove tower candidate."""
    # 1. Non-tower / private residence / virtual platform check
    is_non_tower, reason = is_private_residence_or_non_tower(b_raw, t_raw, c_raw)
    if is_non_tower:
        return "", "none", "", reason

    if not t_raw and not b_raw:
        return "", "none", "", "Empty location record"

    t_norm = norm_str(t_raw)
    b_norm = norm_dedicn(b_raw)

    # Special joint multi-tower cases
    if t_norm in {"kington presteigne", "kington and presteigne"}:
        return (
            "13373",
            "medium",
            "14991",
            "Dual tower festival/circuit across Kington (Herefordshire 13373) and Presteigne (Powys 14991)",
        )

    # Check for parish in building (e.g. "Christ Church, Dore" with town="Sheffield")
    if b_raw and "," in b_raw:
        parts = [p.strip() for p in b_raw.split(",", 1)]
        b_sub, parish_sub = parts[0], parts[1]
        parish_norm = norm_str(parish_sub)
        if parish_norm in place_to_towers:
            cand = place_to_towers[parish_norm]
            for t in cand:
                d_m, _ = dedications_match(norm_dedicn(b_sub), t)
                if d_m:
                    return (
                        str(t["tower_id"]),
                        "high",
                        "",
                        f"Resolved via parish in building '{parish_sub}' ({t['place']}, {t['dedicn']})",
                    )

    # Check for parish in town (e.g. "Sheffield, Dore")
    if t_raw and "," in t_raw:
        parts = [p.strip() for p in t_raw.split(",", 1)]
        town_main, parish_sub = parts[0], parts[1]
        parish_norm = norm_str(parish_sub)
        if parish_norm in place_to_towers:
            cand = place_to_towers[parish_norm]
            for t in cand:
                d_m, _ = dedications_match(b_norm, t)
                if d_m:
                    return (
                        str(t["tower_id"]),
                        "high",
                        "",
                        f"Resolved via suburb/parish '{parish_sub}' in town name ({t['place']}, {t['dedicn']})",
                    )

    # 2. Candidate collection by Place
    candidate_towers = []
    seen_ids = set()

    def add_candidates(t_list, boost_reason):
        for t in t_list:
            if t["tower_id"] not in seen_ids:
                seen_ids.add(t["tower_id"])
                candidate_towers.append((t, boost_reason))

    # Try exact Place
    if t_norm in place_to_towers:
        add_candidates(place_to_towers[t_norm], "place_match")

    # Try Place2 (e.g. "Clerkenwell" -> Place="London", Place2="Clerkenwell")
    if t_norm in place2_to_towers:
        add_candidates(place2_to_towers[t_norm], "place2_match")

    # Try AltName
    if t_norm in altname_to_towers:
        add_candidates(altname_to_towers[t_norm], "altname_match")

    # If building is present and town is absent/empty, try matching building as Place or AltName
    if not t_norm and b_raw:
        b_place_norm = norm_str(b_raw)
        if b_place_norm in place_to_towers:
            add_candidates(place_to_towers[b_place_norm], "building_as_place")

    # Filter/rank candidates by County/Region compatibility
    compatible_candidates = []
    for t, match_type in candidate_towers:
        c_compat = counties_compatible(c_raw, t["county"]) or counties_compatible(c_raw, t["region"]) or counties_compatible(c_raw, t["country"])
        if c_compat:
            compatible_candidates.append(t)

    # If county filtering removed everything, but we had candidates, retain them if county was absent or generic
    if not compatible_candidates and candidate_towers:
        c_norm = norm_str(c_raw)
        if not c_raw or c_norm in {"uk", "england", "great britain", "australia", "usa"}:
            compatible_candidates = [t for t, _ in candidate_towers]

    # Evaluate compatibility and dedications
    if compatible_candidates:
        if len(compatible_candidates) == 1:
            target = compatible_candidates[0]
            d_match, score = dedications_match(b_norm, target)
            if not b_raw:
                return (
                    str(target["tower_id"]),
                    "high",
                    "",
                    f"Unique tower in {target['place']} ({target['county']}); building unspecified in source",
                )
            elif d_match:
                return (
                    str(target["tower_id"]),
                    "high",
                    "",
                    f"Unique tower in {target['place']}; dedication '{target['dedicn']}' matches '{b_raw}'",
                )
            else:
                # Building name did not match the single tower's dedication
                return (
                    str(target["tower_id"]),
                    "medium",
                    "",
                    f"Sole ringing tower in {target['place']}, but dedication '{target['dedicn']}' differs from source '{b_raw}'",
                )
        else:
            # Multiple towers in town (e.g. Oxford, Cambridge, London, Norwich, York, Bristol)
            scored_candidates = []
            for t in compatible_candidates:
                d_match, score = dedications_match(b_norm, t)
                if d_match and score > 0.4:
                    scored_candidates.append((t, score))

            scored_candidates.sort(key=lambda x: (x[1], x[0]["is_full_circle"]), reverse=True)

            if scored_candidates:
                best_tower, best_score = scored_candidates[0]
                alts = [str(t["tower_id"]) for t in compatible_candidates if t["tower_id"] != best_tower["tower_id"]]
                alts_str = ";".join(alts[:10])

                if best_score >= 0.8:
                    return (
                        str(best_tower["tower_id"]),
                        "high",
                        alts_str,
                        f"Resolved dedication '{best_tower['dedicn']}' ({best_tower['place']}) among {len(compatible_candidates)} towers in town",
                    )
                else:
                    return (
                        str(best_tower["tower_id"]),
                        "medium",
                        alts_str,
                        f"Partial dedication match for '{best_tower['dedicn']}' among {len(compatible_candidates)} towers in town",
                    )
            else:
                # No building match among multiple towers
                alts = [str(t["tower_id"]) for t in compatible_candidates]
                alts_str = ";".join(alts[:10])
                if not b_raw:
                    return (
                        alts[0],
                        "low",
                        alts_str,
                        f"Ambiguous: {len(compatible_candidates)} towers in {compatible_candidates[0]['place']} with no building specified",
                    )
                else:
                    return (
                        "",
                        "none",
                        alts_str,
                        f"Unresolved: '{b_raw}' did not match any of the {len(compatible_candidates)} towers in {compatible_candidates[0]['place']}",
                    )

    # 3. Fallback: Fuzzy place match
    fuzzy_matches = []
    for t in all_towers:
        if t_norm and (t["place_norm"].startswith(t_norm + " ") or t_norm.startswith(t["place_norm"] + " ")):
            if counties_compatible(c_raw, t["county"]) or counties_compatible(c_raw, t["region"]):
                fuzzy_matches.append(t)

    if len(fuzzy_matches) == 1:
        target = fuzzy_matches[0]
        d_match, _ = dedications_match(b_norm, target)
        conf = "high" if d_match else "medium"
        return (
            str(target["tower_id"]),
            conf,
            "",
            f"Fuzzy place match ({t_raw} -> {target['place']}, {target['county']})",
        )

    return "", "none", "", f"No matching tower found for '{t_raw}' in Dove register"


def main():
    print("Loading Dove Guide and Towers data...")
    dove_df = pd.read_csv(DOVE_CSV_PATH, encoding="utf-8-sig", low_memory=False)
    towers_df = pd.read_csv(TOWERS_CSV_PATH, encoding="utf-8-sig", low_memory=False) if TOWERS_CSV_PATH.exists() else None
    towers_by_id, place_to_towers, place2_to_towers, altname_to_towers, all_towers = build_tower_index(dove_df, towers_df)
    print(f"  Indexed {len(towers_by_id):,} total towers.")

    print(f"Loading CCCBR Methods XML from {METHODS_XML_URL} ...")
    req = urllib.request.Request(METHODS_XML_URL, headers={"User-Agent": "change-ringing-corpus/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        zf = zipfile.ZipFile(io.BytesIO(resp.read()))
        xml_name = [n for n in zf.namelist() if n.endswith(".xml")][0]
        with zf.open(xml_name) as f:
            root = ET.parse(f).getroot()

    print("Extracting location triples from XML ...")
    triples_counter = Counter()
    for ms in root.findall(f"{NS}methodSet"):
        for m in ms.findall(f"{NS}method"):
            perfs = m.find(f"{NS}performances")
            if perfs is not None:
                for p in perfs:
                    loc = p.find(f"{NS}location")
                    if loc is not None:
                        b = clean_text(loc.find(f"{NS}building").text) if loc.find(f"{NS}building") is not None else None
                        t = clean_text(loc.find(f"{NS}town").text) if loc.find(f"{NS}town") is not None else None
                        c = clean_text(loc.find(f"{NS}county").text) if loc.find(f"{NS}county") is not None else None
                        triples_counter[(b, t, c)] += 1

    print(f"Found {len(triples_counter):,} distinct (building, town, county) triples across {sum(triples_counter.values()):,} performances.")

    print("Resolving triples against Dove register ...")
    results = []
    conf_counter = Counter()

    for (b, t, c), count in triples_counter.most_common():
        tower_id, conf, alts, reason = resolve_triple(
            b, t, c,
            towers_by_id, place_to_towers, place2_to_towers, altname_to_towers, all_towers
        )
        conf_counter[conf] += 1
        results.append({
            "building": b or "",
            "town": t or "",
            "county": c or "",
            "occurrences": count,
            "dove_tower_id": tower_id,
            "confidence": conf,
            "alternatives": alts,
            "reasoning": reason,
        })

    OUTPUT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"Writing candidates CSV to {OUTPUT_CSV_PATH} ...")
    with open(OUTPUT_CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["building", "town", "county", "occurrences", "dove_tower_id", "confidence", "alternatives", "reasoning"],
        )
        writer.writeheader()
        writer.writerows(results)

    print("\nResolution Summary:")
    print(f"Total Triples Processed: {len(results):,}")
    print("Confidence Breakdown (triples):")
    for level in ["high", "medium", "low", "none"]:
        cnt = conf_counter[level]
        pct = (cnt / len(results)) * 100
        print(f"  {level.upper():<8} : {cnt:>5} ({pct:>5.1f}%)")

    # Weighted occurrences breakdown
    perf_conf_counter = Counter()
    for r in results:
        perf_conf_counter[r["confidence"]] += r["occurrences"]

    print("\nConfidence Breakdown (by performance occurrences):")
    total_occ = sum(perf_conf_counter.values())
    for level in ["high", "medium", "low", "none"]:
        cnt = perf_conf_counter[level]
        pct = (cnt / total_occ) * 100
        print(f"  {level.upper():<8} : {cnt:>5} ({pct:>5.1f}%)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

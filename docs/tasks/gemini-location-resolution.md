# Task brief: first-performance location resolution (Gemini CLI)

A large-context cross-referencing task: match free-text place names from the
CCCBR Methods Library against Dove's canonical tower register. This is the
one place in the project where fuzzy matching is genuinely required, so it is
worth doing carefully.

Everything below is verified against the live sources as of 2026-08-09.

Paste from the horizontal rule onward.

---

You are working on `nihilisticiconoclast/change-ringing`, a queryable corpus
for English change ringing built on a Turso (hosted libSQL, SQLite-compatible)
database. Read `README.md`, `docs/AGENTS.md` and `docs/CONNECTING.md` first.

## Why this task exists, and why it is yours

Most cross-corpus linking in this project turned out not to need inference.
BellBoard publishes a `dove-tower-id` on every performance, so linking
performances to towers is an integer join -- ~94% carry it, 99.5% of those
resolve. The CCCBR Methods Library is different: its first-performance records
name places only as free text, with no identifier of any kind.

That makes this the binding constraint your context window is actually good
for. There are **4,445 distinct (town, county) pairs** across **30,732
location records**, to be matched against Dove's **7,262 ringing towers**
(or 15,720 if the wider `towers` register is included). Seeing the whole field
at once beats pairwise comparison: the same tower recurs under several
spellings, and a candidate that looks plausible in isolation is often clearly
wrong once its neighbours are visible.

## The data

Methods Library side -- `https://methods.cccbr.org.uk/xml/CCCBR_methods.xml.zip`,
namespace `http://www.cccbr.org.uk/methods/schemas/2007/05/methods`. Inside
each `<method>`, a `<performances>` block holds events such as
`firstTowerbellPeal` and `firstInclusionInTowerbellPeal`, each with `<date>`,
optional `<society>`, and a `<location>` of `<building>`, `<town>`,
`<county>`. Example: `building="St Andrew"`, `town="Lismore"`,
`county="New South Wales"`.

Dove side -- query the live database. Useful columns on `dove`: `TowerID`,
`RingID`, `Place`, `Place2`, `PlaceCL`, `Dedicn`, `BareDedicn`, `AltName`,
`RingName`, `County`, `Region`, `RingType`. Connect as
`docs/CONNECTING.md` describes:

```python
import os, libsql
conn = libsql.connect(
    database=os.environ["TURSO_DATABASE_URL"],
    auth_token=os.environ["TURSO_AUTH_TOKEN"],
)
towers = conn.execute(
    'SELECT TowerID, Place, Place2, Dedicn, BareDedicn, AltName, County, Region '
    'FROM dove'
).fetchall()
```

Pull the Dove side from the database rather than from a committed file -- the
raw CSVs are deliberately not in the repo, for licensing reasons set out in
`data/SOURCES.md`.

## What makes this harder than string similarity

Read these before deciding on an approach; each is present in the real data.

- **Dove abbreviates dedications.** "S Paul" for "St Paul", "S Mark Ev" for
  "St Mark the Evangelist". The Methods Library writes them out.
- **The county field is unreliable on both sides.** It is sometimes absent
  entirely in the Methods Library (e.g. a "Finchampstead" record with no
  county), and Dove carries both a historic `County` and an administrative
  `Region` which disagree for many towers.
- **A great many towns have more than one ring.** Town alone is not
  identifying; `building` usually is, but not always, and it is the field most
  often abbreviated or informally written.
- **Not every location is a tower in Dove, and that is correct.** Handbell and
  keyboard first-performances happen in private houses. A confident "no match"
  is a valid and useful answer -- in the BellBoard corpus, records with no Dove
  tower were overwhelmingly handbell rings in front rooms, not resolution
  failures. Do not force those into a match.
- **Non-UK locations are in scope** (Australia, New Zealand, North America) and
  Dove does cover them, so do not filter them out as noise.

## Deliverable

A single CSV, `data/method_location_candidates.csv`, one row per distinct
(building, town, county) triple, with these columns:

| column | meaning |
| --- | --- |
| `building`, `town`, `county` | the source triple, verbatim |
| `occurrences` | how many location records use this triple |
| `dove_tower_id` | your best candidate, or blank for no match |
| `confidence` | `high`, `medium`, `low`, or `none` |
| `alternatives` | other plausible TowerIDs, semicolon-separated |
| `reasoning` | one line: what decided it |

Plus `docs/method_location_resolution.md` -- a short write-up of your method,
the ambiguity classes you found, and any systematic problem worth knowing
about. Prose, not a log.

Calibrate `confidence` honestly. `high` should mean you would be surprised to
be wrong; anything resting on town alone with multiple rings in that town is
`medium` at best. Over-confident rows are worse than no rows here, because the
adjudication step downstream samples rather than checks every line.

## Boundaries

- **Do not write to the database.** No inserts, no updates, no schema changes.
  This task produces a candidate file for review, nothing else.
- **Do not modify anything under `schema/` or `scripts/`.** A separate task is
  adding the methods-library loader and will collide with you. In particular
  there will be a nullable `dove_tower_id` column on the methods tables; it is
  not yours to populate.
- **Do not commit the downloaded XML or zip.**
- Work on a branch and open a pull request. Per `docs/AGENTS.md`, Claude Code
  adjudicates the ambiguous matches and owns the merge -- your job is to
  surface candidates with honest confidence, not to make the final call.

## Definition of done

`data/method_location_candidates.csv` covering all 4,445 distinct pairs (every
one gets a row, including the confident non-matches), plus the write-up, in a
PR. In the PR description give the distribution across confidence levels and
call out the ambiguity classes you think need a human or a second opinion.

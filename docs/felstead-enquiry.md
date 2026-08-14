# Draft enquiry: Felstead database

**Status: not sent.** Nothing has been fetched from Felstead beyond the 16
manual page loads described below. Do not run any bulk fetch until there is a
reply.

**To:** felstead@cccbr.org.uk — copy to the ICT Committee if there is a separate
address; the introduction page says responsibility is shared between the ICT and
Peal Records Committees.

**Subject:** Permission to index Felstead peal records for an open corpus project

---

Dear Felstead maintainers,

I maintain a small open-source project that builds a linked, queryable corpus of
English change ringing from the public sources: Dove's Guide, the CCCBR Methods
Library, and BellBoard. The code and the analyses are public at
https://github.com/nihilisticiconoclast/change-ringing, and the visualisations
are at https://nihilisticiconoclast.github.io/change-ringing/.

I would like to ask permission before going any further with Felstead, because it
is the one source I have found with no stated licence, and it is also the most
valuable: our BellBoard data only reaches back to 2021, whereas Felstead holds
150 years of peal history.

**What I would like to do**

Fetch the peal list for each tower in our corpus and store date, method, status
and the source citation, so that a peal in Felstead can be joined to the tower,
ring and method records we already hold. The link works without any name
matching, which is why this is worth doing at all: BellBoard publishes a
`towerbase-id` on each performance, and `tbid.php` accepts exactly that
identifier. We hold 79,918 performances carrying one, across 5,600 distinct
towers; I sampled twelve of those identifiers against Felstead and all twelve
resolved.

**How I would do it, if you are happy for me to**

- One request per tower, using `rpp=1000` so a tower's whole history arrives in a
  single page. That is roughly **5,600 requests in total**, not one per peal.
- One request at a time, with a deliberate delay between them — five seconds
  unless you would prefer slower, which puts the whole job at about eight hours,
  run overnight, once.
- A descriptive User-Agent identifying the project with a link, so you can see
  what it is in your logs and block it if it is a nuisance.
- Cached to disk, so a re-run or a bug on my side does not mean re-fetching.
- Only towers already present in our corpus. I am not trying to mirror the
  database.

I am happy to run it at whatever rate you specify, at a time of day you prefer,
or not at all. If you would rather supply an extract directly, that would be
better for both of us and I would gladly take a CSV instead.

**What I would do with it**

- Attribute Felstead and the Central Council explicitly on any page or dataset
  derived from it, in whatever form of words you would like.
- Publish only aggregate analysis. Our published work is deliberately
  aggregate-only where individuals are involved — for example, we classify
  BellBoard footnotes by occasion but never publish the text or any name,
  because many are funeral tributes written by people who did not anticipate
  republication. The same principle would apply here.
- Adopt whatever licence you specify. Our Dove-derived data is already CC BY-SA
  4.0 and carries a share-alike obligation we document and honour
  (`data/LICENCE-DATA.md`), so a share-alike condition is no obstacle.
- Send corrections back. Building a machine-readable copy is quite good at
  surfacing inconsistencies, and I would rather report them than sit on them.
  One I can already offer: BellBoard records TowerBase ID **7924** for
  Crowhurst, The Forewood Ring, East Sussex, whereas Felstead's place search
  returns **7898** for "Crowhurst, Forewood Ring, **Suffolk**" — the county looks
  wrong in one of the two databases, and possibly the identifier as well.

I am conscious that Felstead represents several thousand hours of volunteer
transcription of Canon Felstead's handwritten cards, and that the site exists to
serve ringers rather than to be scraped. If the answer is no, or not yet, that is
a completely reasonable answer and I will record it and leave the site alone.

With thanks for the database, which is remarkable,

[your name]

---

## Notes for us, not for them

**What has actually been fetched so far:** 16 page loads in total while
establishing whether a join was even possible — the index, `tower.php`,
`method.php`, `other.php`, `alltime.php`, `intro.html`, one place search, two
pages for TowerBase 2606, and twelve single-tower probes at 3-second intervals.
Nothing cached, nothing stored, nothing ingested.

**Verified facts, so the enquiry is accurate:**

| Claim | How it was checked |
| --- | --- |
| "over 360,000 towerbell peals" | Stated on `felstead.cccbr.org.uk` index, quoted verbatim |
| Peals back to 1875 for the tower sampled | First row of `tbid.php?tid=2606` is Tue, 2 Feb 1875, Grandsire Triples |
| `tbid.php` takes a TowerBase ID | Error text says "Invalid or missing TowerBase identifier"; Dove `TowerID` values all fail |
| We hold 79,918 with a `towerbase-id`, 5,600 distinct | `SELECT COUNT(*) … WHERE "towerbase-id" IS NOT NULL` |
| 12 of 12 sampled identifiers resolve | 12 requests, 3s apart, returning 41–783 peals each |
| `rpp=1000` returns a whole tower | One request returned "1 to 783 out of 783" |
| No robots.txt | `GET /robots.txt` → 404 |
| No stated licence | Not on the index, `intro.html`, or `other.php` |

**Fields available per peal:** peal number within the tower, PB-ID, status
(OK / invalid), full date rung, method — and a bibliographic citation such as
`CB v.127; BL 13.ii.75` or `RW 5009.0421`, i.e. *Church Bells*, *Bell News* and
*The Ringing World*. That citation chain is arguably as interesting as the peal
data: it is a provenance trail back to the printed record for each entry.

**Why this is worth waiting for.** It would take the corpus from a four-year
window to a century and a half, for peals specifically, and it is the only
source found so far that could support the "method survival" analysis (roadmap
item 8b) without completing the BellBoard backfill. It does not replace the
backfill: Felstead is peals only, so quarter peals, service ringing and tolling —
86% of what BellBoard holds — are not in it.

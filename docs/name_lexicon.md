# Canonical Dedication and Place-Name Lexicon

**Deliverable for Gemini Task 2:** Canonical lexicon mapping across 7,262 Dove towers, 15,720 towers records, and 30,734 method performances.

- **Lexicon Dataset:** [`data/name_lexicon.csv`](file:///c:/Users/james/Documents/Projects/change-ringing/data/name_lexicon.csv) (15,322 canonical mapping entries)
- **Extraction Query:** [`queries/extract_dedications_and_places.sql`](file:///c:/Users/james/Documents/Projects/change-ringing/queries/extract_dedications_and_places.sql)
- **Builder Script:** [`scripts/build_name_lexicon.py`](file:///c:/Users/james/Documents/Projects/change-ringing/scripts/build_name_lexicon.py)

---

## 1. Problem Overview & Rationale

Across change-ringing sources, church dedications and place names have historically been recorded using distinct conventions:
1. **Dove's Guide Abbreviation Conventions**: Dove uses dense shorthand to save printed space: `S Paul`, `SS Peter & Paul`, `S Mary V`, `S John Bapt`, `S Mary Magd`, `Cath & Abbey Ch of S Alban`, `H Trinity`, `All SS`, `S John Ev`.
2. **Peal Records & BellBoard Free-Text**: Historical peal accounts and BellBoard submissions write out dedications in full (`St Mary the Virgin`, `Holy Trinity`, `St John the Baptist`, `Cathedral and Abbey Church of Saint Alban`) or use colloquial forms.
3. **Orthographic & Dialect Variations**: English and Celtic saint names vary in spelling (`Laurence` vs `Lawrence`, `Katherine` vs `Catherine`, `Swithun` vs `Swithin`, `Alphege` vs `Alfege`, `Petroc` vs `Petrock`).
4. **Toponymic Variations**: Place names fluctuate between hyphenated and spaced forms (`Barrow-on-Soar` vs `Barrow upon Soar`, `Newcastle-upon-Tyne` vs `Newcastle upon Tyne`, `South Mymms` vs `South Mimms`).

### Preventing False Conflations
Previous entity resolution efforts risked conflating separate churches within the same parish (e.g., matching *St Mary, Whitechapel* with *Whitechapel S Paul*). The canonical lexicon explicitly preserves distinct dedications while normalizing lexical aliases.

---

## 2. Dataset Taxonomy & Breakdown

The generated lexicon contains **15,322 entries** categorized by domain and mapping type:

### Domain Breakdown
| Domain | Entries | Description |
| --- | --- | --- |
| `place_name` | 12,274 | Parish, town, and city names across UK and global towers |
| `dedication` | 3,014 | Church, cathedral, priory, and abbey dedications |
| `saint_name` | 34 | Canonical hagiographical cross-references |

### Category Breakdown
| Category | Entries | Examples |
| --- | --- | --- |
| `verbatim` | 13,058 | Canonical terms that require no expansion |
| `abbreviation_expansion` | 2,202 | `S Mary V` $\to$ `Saint Mary the Virgin`, `SS Peter & Paul` $\to$ `Saints Peter and Paul` |
| `spelling_variant` | 38 | `Laurence` $\to$ `Lawrence`, `Katherine` $\to$ `Catherine`, `Swithun` $\to$ `Swithin` |
| `toponym_variant` | 15 | `Barrow-on-Soar` $\to$ `Barrow upon Soar`, `Newcastle-upon-Tyne` $\to$ `Newcastle upon Tyne` |
| `alias` | 6 | `S Thomas of Canterbury` $\to$ `Saint Thomas Becket` |
| `honorific_expansion` | 7 | `K & M` $\to$ `King and Martyr`, `B & M` $\to$ `Bishop and Martyr` |
| `punctuation_variant` | 2 | `Bishop's Stortford` $\to$ `Bishops Stortford` |

---

## 3. Verified Sample Expansions

| Raw Term | Canonical Expansion | Category | Rule & Notes |
| --- | --- | --- | --- |
| `S Mary V` | `Saint Mary the Virgin` | `abbreviation_expansion` | Expands Marian Virgin qualifier |
| `SS Peter & Paul` | `Saints Peter and Paul` | `abbreviation_expansion` | Dual saint plural expansion |
| `S John Bapt` | `Saint John the Baptist` | `abbreviation_expansion` | Contraction expansion |
| `S John Ev` | `Saint John the Evangelist` | `abbreviation_expansion` | Evangelist contraction |
| `Cath & Abbey Ch of S Alban` | `Cathedral and Abbey Church of Saint Alban` | `abbreviation_expansion` | Collegiate prefix expansion |
| `All SS` | `All Saints` | `abbreviation_expansion` | Contraction expansion |
| `H Trinity` | `Holy Trinity` | `abbreviation_expansion` | Trinitarian prefix expansion |
| `S Thomas a Becket` | `Saint Thomas Becket` | `spelling_variant` | Anglo-Norman prefix standardization |
| `S Thomas of Canterbury` | `Saint Thomas Becket` | `alias` | Historic martyr dedication alias |
| `Barrow-on-Soar` | `Barrow upon Soar` | `toponym_variant` | River toponym standardization |
| `Newcastle-upon-Tyne` | `Newcastle upon Tyne` | `toponym_variant` | River toponym standardization |
| `South Mymms` | `South Mimms` | `spelling_variant` | Historic county parish spelling |
| `Bishop's Stortford` | `Bishops Stortford` | `punctuation_variant` | Toponymic apostrophe standardization |

---

## 4. How to Use the Lexicon

Downstream scripts (e.g. location resolution or composition entity linkage) can load `data/name_lexicon.csv` into an in-memory lookup dictionary:

```python
import pandas as pd

# Load lexicon dictionary
lexicon_df = pd.read_csv("data/name_lexicon.csv")
dedication_map = dict(zip(lexicon_df[lexicon_df['domain'] == 'dedication']['raw_term'],
                           lexicon_df[lexicon_df['domain'] == 'dedication']['canonical_term']))

# Normalize an incoming raw dedication string
canonical = dedication_map.get(raw_input, raw_input)
```

To rebuild the lexicon at any time from the local offline database:
```bash
python scripts/build_name_lexicon.py --db data/change-ringing.db --out data/name_lexicon.csv
```

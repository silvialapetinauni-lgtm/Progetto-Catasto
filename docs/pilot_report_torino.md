# Pilot report — Tav. 10, provincia di Torino

Date: 2026-09-15. Source: `torino.pdf` (ISTAT, 1° Censimento generale dell'agricoltura 1961, Vol. II, fasc. 1).

## Output
- `tav10_torino.dta` / `tav10_torino.xlsx`: 17 regioni agrarie × 76 variables in the Summary §0.4 layout.
  - `provincia, reg_agr, id`;
  - 35 × (`az_`, `sup_`) for 34 classes + totale;
  - then `zona, sigla, cod_prov`.
- Excel headers reproduce Figure 3 of the Summary. Row TO1 = `Torino, 1, TO1, 2, 0, 31, 2.47, 45, 7.7, 50, 12.89`, identical to the figure.
- `tav10_torino_long.csv`: one row per region × class, with the printed string of both readings and the status of each cell.

## What was read
| item | count |
|---|---|
| Tav. 10 blocks (regioni agrarie) | 17 (PDF pp. 43–51) |
| Tav. 10 cells (35 rows × aziende/superficie) | 1,190 |
| Tav. 1 cells (validation) | 70 |
| total cells, each read twice | 1,260 |

## Results
| step | result |
|---|---|
| automatic location of blocks and columns | 18/18 blocks found. On one page "oltre" was garbled by OCR and the fallback was used; columns were found on all pages despite horizontal shifts of up to 30 pt |
| pass 1 (full-block images) vs pass 2 (strip images, independent reader) | **1,259 of 1,260 cells identical** (99.92%) |
| unreadable / disagreeing cells | 1: TO2, class 12,51–15,00, superficie. Pass 1 left one digit as `?`; pass 2 read `643,97`. Zoomed re-read: a 9 with a broken stroke → `643,97` (logged in `work/torino/resolutions.csv`) |
| Σ 34 classes = TOTALE, per block (17 regions + Tav. 1; aziende, superficie) | 36/36 pass |
| Σ 17 regions = Tav. 1, per class incl. TOTALE (aziende, superficie) | 70/70 pass |
| average farm size inside class bounds | 511/511 non-empty class cells pass (50 class cells are empty `—`) |
| aziende = 0 ⇔ superficie = 0 | pass |
| Stata asserts in `03_build.do` (row sums, province totals = Tav. 1: 92,453 aziende, 554,814.01 ha) | pass |
| **error-detection test**: the same wrong digit planted in both passes, in 2 cells | both detected; both pinpointed to the exact cell |
| **human audit** of 200 random cells (`audit_torino.xlsx`) | **pending**: to be filled in, then `02_validate.py Torino --score` |

Doubtful glyphs reported by the second reader were all read the same way by both readings, and each passes both sums:
- broken 9s in TO2, TO6, TO8, TO11, TO12;
- a faint `532,16` in TO8;
- `3` in TO9;
- `402` in TO12.

## Source anomalies (not errors of the digitization)
- TO4: printed class label "1,51 - 20,0" for "1,51 - 2,00" (row position is correct).
- TO13, TO14: heavy speckling; some thousands separators look like colons.
- Errata slip: TO16 conduzione diretta superficie `.708,27` → `29.708,27`. That column is not part of the Summary layout, so nothing changes in the dataset.

## Residual risk
- Both readings were made by Claude models, so their errors can be correlated (the same broken glyph read the same wrong way).
- The arithmetic checks guard against this: a wrong class cell breaks its region sum **and** its Tav. 1 sum.
- An error survives only if other misreadings cancel it exactly in both sums. That is very unlikely, and the human audit measures it.

## Time and effort
- Scripts: rendering and cropping ~5 s; validation < 1 s; Stata build < 5 s.
- Pass 1 (in the main session): about 5–10 minutes.
- Pass 2 (separate reader): about 10 minutes, ~315k tokens for 18 blocks.
- One human decision was needed (the zoomed cell); the audit takes ~30–45 minutes.

## Recommendation for the other 91 books
The method works on Torino. Before scaling up:
1. **Complete the audit.** If it finds 0 errors in 200 cells, the residual error rate is below ~1.5% (95% confidence). Given the checks, the realistic rate is far lower.
2. **Pilot a bad scan next.** Potenza (fasc. 76) has faded digits and a cut margin. Expect more `?` cells and flags there, and check that block and column detection holds.
3. **Scale up.**
   - Download the 92 fascicoli from ISTAT eBiblio.
   - Fill `config/books.csv` from each Indice. Italy has roughly 800 regioni agrarie, about 47× Torino.
   - Pass 2 for all of Italy would cost on the order of 15M tokens in this setup. If that is too costly, run the same
     templates through an API batch job; the checks and audit stay the same.

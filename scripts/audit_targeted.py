"""Short human-audit sheet (20-40 cells) aimed at the cells where the OCR had trouble.

Cells are drawn from output/tav10_<prov>_long.csv in three strata:
  A  decided on a zoomed re-read or rebuilt from a row sum (resolutions.csv note: zoom / margin / row)
  B  the OCR read a different value than the one kept (pass 1 != final, pass 1 not '?')
  C  the OCR left the cell unreadable ('?')
plus a control stratum
  D  cells where OCR and visual reading agreed (random), to check that agreement means correct.
About 3/4 of the sheet comes from A > B > C (in that order of priority), 1/4 from D.
Size: 2 cells per block, between 20 and 40.

Writes output/audit_<prov>.xlsx in the layout read by `02_validate.py <Prov> --score`
(extra column K "motivo" says why each cell was chosen). Because the sample is targeted, the error
rate it measures is an upper bound for the hard cells, not an estimate for the whole table.

Usage:  python3 scripts/audit_targeted.py Torino [--force]
"""
import csv
import random
import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[1]
MOTIVO = {"A": "riletta su zoom / ricostruita da somma di riga",
          "B": "OCR aveva letto un valore diverso",
          "C": "OCR non leggibile",
          "D": "controllo: OCR e lettura visiva concordi"}


def strata(prov):
    work = ROOT / "work" / prov.lower().replace(" ", "")
    long = pd.read_csv(ROOT / "output" / f"tav10_{prov.lower().replace(' ', '')}_long.csv", dtype=str)
    notes = {}
    if (work / "resolutions.csv").exists():
        for r in csv.DictReader(open(work / "resolutions.csv")):
            if r["class_code"]:
                notes[(r["block"], int(r["class_code"]), r["var"])] = r["note"].lower()
    cells = {k: [] for k in "ABCD"}
    for r in long.itertuples():
        for var in ("az", "sup"):
            raw, p1, status = getattr(r, f"{var}_raw"), getattr(r, f"{var}_pass1"), getattr(r, f"{var}_status")
            note = notes.get((r.block, int(r.class_code), var), "")
            if any(k in note for k in ("zoom", "margin", "row")):
                s = "A"
            elif status == "resolved" and p1 == "?":
                s = "C"
            elif status == "resolved":
                s = "B"
            else:
                s = "D"
            cells[s].append((r.id, r.block, int(r.pdf_page), r.class_label, var, raw, int(r.class_code)))
    return cells


def draw(prov):
    cells = strata(prov)
    n_blocks = len({c[1] for s in cells.values() for c in s})
    n = max(20, min(40, 2 * n_blocks))
    n_ctrl = max(5, n // 4)
    rng = random.Random(1961)
    pick = []
    for s in "ABC":
        pool = cells[s][:]
        rng.shuffle(pool)
        pick += [(c, s) for c in pool[: n - n_ctrl - len(pick)]]
    ctrl = cells["D"][:]
    rng.shuffle(ctrl)
    pick += [(c, "D") for c in ctrl[: n - len(pick)]]
    pick.sort(key=lambda x: (x[0][1], x[0][6], x[0][4]))
    return pick, {s: len(v) for s, v in cells.items()}


def write(prov, pick, sizes):
    path = ROOT / "output" / f"audit_{prov.lower().replace(' ', '')}.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "audit"
    ws.append(["n", "id", "blocco", "pagina PDF", "classe (ettari)", "colonna TOTALE", "valore trascritto",
               "corretto? (si/no)", "valore corretto (se no)", "note", "motivo"])
    for i, ((id_, b, page, label, var, raw, _), s) in enumerate(pick, 1):
        ws.append([i, id_, b, page, label, "Aziende" if var == "az" else "Superficie", raw, "", "", "", MOTIVO[s]])
    for c in ws[1]:
        c.font, c.fill = Font(bold=True), PatternFill("solid", fgColor="DDEBF7")
    for col, w in zip("ABCDEFGHIJK", (5, 7, 8, 11, 20, 15, 18, 17, 22, 30, 44)):
        ws.column_dimensions[col].width = w
    for row in ws.iter_rows(min_row=2, min_col=8, max_col=9):
        for c in row:
            c.fill = PatternFill("solid", fgColor="FFF2CC")
    dv = DataValidation(type="list", formula1='"si,no"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"H2:H{len(pick) + 1}")
    ws.freeze_panes = "A2"

    sigla = pick[0][0][0].rstrip("0123456789")
    info = wb.create_sheet("istruzioni")
    counts = {s: sum(1 for _, x in pick if x == s) for s in "ABCD"}
    for line in [
        f"Audit mirato della digitalizzazione — Tav. 10, provincia di {prov} ({len(pick)} celle)",
        "",
        "Le celle sono scelte soprattutto dove l'OCR ha avuto problemi (colonna 'motivo'):",
        *[f"  - {MOTIVO[s]}: {counts[s]} celle (su {sizes[s]} di questo tipo nella provincia)" for s in "ABCD"],
        "",
        "1. Aprire il PDF della provincia alla 'pagina PDF' indicata (numero di pagina del file, non quello stampato).",
        f"2. Trovare il blocco 'REGIONE AGRARIA n' (colonna 'id': {sigla}1 = regione agraria 1) e la riga della 'classe'.",
        "3. Guardare solo le colonne TOTALE (Aziende o Superficie, come indicato).",
        "4. Confrontare con 'valore trascritto': scrivere si se identico, no se diverso.",
        "5. Se no, scrivere nella colonna successiva il valore come stampato (es. 1.451,79 oppure —).",
        "",
        "Il trattino — significa zero/nessuna azienda.",
        f"Alla fine: python3 scripts/02_validate.py {prov} --score",
    ]:
        info.append([line])
    info.column_dimensions["A"].width = 110
    info["A1"].font = Font(bold=True)
    wb.save(path)
    print(f"{path.name}: {len(pick)} celle " + ", ".join(f"{s}={counts[s]}/{sizes[s]}" for s in "ABCD"))


if __name__ == "__main__":
    prov = sys.argv[1]
    path = ROOT / "output" / f"audit_{prov.lower().replace(' ', '')}.xlsx"
    if path.exists() and "--force" not in sys.argv:
        sys.exit(f"{path.name} exists: use --force to replace it")
    write(prov, *draw(prov))

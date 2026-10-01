"""Pass 1 from the PDF's own OCR text layer (pdftotext -bbox), using the geometry in work/<prov>/blocks.csv
written by 01b_locate_senza_totale.py.

Rows: the 34 class rows are evenly spaced from "Senza" (row 1) to "oltre 2.500" (row 34); TOTALE sits ~2.1
pitches below "oltre". A first pitch (TOTALE - Senza) / 35.1 assigns each text line of the label column to a
row, then a least-squares line y = a + b*row gives the row centres.
Cells: OCR words inside the Totale aziende / superficie x-ranges within half a pitch of the row centre.
Only mechanical normalisation is applied (O->0, l/I/i->1, lost thousands separator restored). A cell that
is blank while the other cell of the row is not, or that does not match the printed format, is written "?":
the OCR left it unreadable and pass 2 / the zoomed re-read decide it.

Usage:  python3 scripts/01c_pass1_ocr.py Alessandria      (overwrites work/<prov>/pass1/*.csv)
"""
import csv
import importlib.util
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("rc", ROOT / "scripts" / "01_render_crop.py")
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)
_spec = importlib.util.spec_from_file_location("ps", ROOT / "scripts" / "pagesource.py")
ps = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ps)

OCR_MAP = str.maketrans({"O": "0", "o": "0", "Ò": "0", "l": "1", "I": "1", "i": "1", "!": "1", "|": "1"})
AZ_RE, SUP_RE = re.compile(r"\d{1,3}(\.\d{3})*"), re.compile(r"\d{1,3}(\.\d{3})*,\d{2}")
DASH_RE = re.compile(r"^[-—–−_~]+$")


def thousands(intpart):
    intpart = intpart.replace(".", "")
    return f"{int(intpart):,}".replace(",", ".") if intpart.isdigit() else intpart


def normalise(tokens, var):
    s = "".join(tokens).replace(" ", "")
    if s == "":
        return ""
    if DASH_RE.match(s):
        return "—"
    s = s.translate(OCR_MAP).rstrip(".")
    if var == "az":
        s = s.replace(",", ".")
        if re.fullmatch(r"[\d.]+", s):
            s = thousands(s)
        return s if AZ_RE.fullmatch(s) else "?"
    s = s.replace(";", ",")
    m = re.fullmatch(r"([\d.]+)[,.](\d{2})", s)
    if m:
        s = f"{thousands(m.group(1))},{m.group(2)}"
    return s if SUP_RE.fullmatch(s) else "?"


def lines(words):
    out = []
    for w in sorted(words, key=lambda w: (w[1] + w[3]) / 2):
        yc = (w[1] + w[3]) / 2
        if out and yc - out[-1][0] < 3.5:
            out[-1][1].append(w)
            out[-1][0] = np.mean([(v[1] + v[3]) / 2 for v in out[-1][1]])
        else:
            out.append([yc, [w]])
    return out


def read_block(words, b):
    s, t = float(b["senza_pt"]), float(b["totale_pt"])
    lx1, ax0, ax1, sx1 = (float(b[k]) for k in ("label_x1", "az_x0", "az_x1", "sup_x1"))
    s_c, t_c = s + 3, t + 3                                    # approximate text centres
    pitch0 = (t_c - s_c) / 35.1
    label = [w for w in words if w[2] <= lx1 + 2 and s - 4 < w[1] < t - 4]
    pts = []
    for yc, _ in lines(label):
        k = round((yc - s_c) / pitch0)
        if 0 <= k <= 33 and abs(yc - (s_c + k * pitch0)) < 0.35 * pitch0:
            pts.append((k, yc))
    if len(pts) >= 10:
        b1, a1 = np.polyfit([p[0] for p in pts], [p[1] for p in pts], 1)
    else:
        a1, b1 = s_c, pitch0
    centres = [a1 + b1 * k for k in range(34)]
    tot_line = [w for w in words if w[2] <= lx1 + 2 and abs(w[1] - t) < 2]
    centres.append(np.mean([(w[1] + w[3]) / 2 for w in tot_line]) if tot_line else t_c)

    # the Totale columns can sit lower/higher than the labels (slightly rotated scan): shift the row
    # centres by the offset of the TOTALE row measured in the Totale columns themselves
    col = [w for w in words if ax0 <= (w[0] + w[2]) / 2 <= sx1 + 4 and s - 6 < w[1] < t + 15]
    col_tot = [yc for yc, _ in lines(col) if abs(yc - centres[-1]) < b1]
    shift = min(col_tot, key=lambda yc: abs(yc - centres[-1])) - centres[-1] if col_tot else 0.0
    centres = [c + shift for c in centres]

    cells = {}
    for cc, yc in enumerate(centres, 1):
        row = sorted((w for w in col if abs((w[1] + w[3]) / 2 - yc) < 0.48 * b1), key=lambda w: w[0])
        groups = []                                  # tokens of one number are < 6 pt apart
        for w in row:
            if groups and w[0] - groups[-1][-1][2] < 6:
                groups[-1].append(w)
            else:
                groups.append([w])
        if len(groups) >= 2:
            az = [w[4] for g in groups[:-1] for w in g]
            sup = [w[4] for w in groups[-1]]
        elif groups and (groups[0][-1][2] > ax1 + 15 or "," in "".join(w[4] for w in groups[0])):
            az, sup = [], [w[4] for w in groups[0]]
        else:
            az, sup = [w[4] for g in groups for w in g], []
        cells[cc] = [normalise(az, "az"), normalise(sup, "sup")]
    for cc, (az, sup) in cells.items():
        if az == "" and sup == "":
            cells[cc] = ["—", "—"]
        elif az == "":
            cells[cc][0] = "?"
        elif sup == "":
            cells[cc][1] = "—" if cc == 1 else "?"         # senza terreno: superficie is always a dash
    return cells, round(b1, 2), len(pts), round(shift, 1)


def title(words, b):
    top, s = float(b["top_pt"]), float(b["senza_pt"])
    text = " ".join(w[4] for w in sorted((w for w in words if top - 2 < w[1] < s - 3), key=lambda w: w[0]))
    m = re.search(r"([0-9lIO]{1,2})\s*\(\s*([MCP])\s*\)", text)
    return (m.group(1).translate(OCR_MAP), m.group(2)) if m else ("?", "?")


def main(prov):
    book = next(b for b in csv.DictReader(open(ROOT / "config" / "books.csv")) if b["provincia"] == prov)
    work = ROOT / "work" / prov.lower()
    classes = list(csv.DictReader(open(ROOT / "config" / "classes.csv")))
    cache = {}
    for b in csv.DictReader(open(work / "blocks.csv")):
        page = int(b["pdf_page"])
        if page not in cache:
            cache[page] = ps.words(book, work, page)[2]
        words = cache[page]
        cells, pitch, n, shift = read_block(words, b)
        ra_num, zona = title(words, b) if b["block"].startswith("RA") else ("", "")
        with open(work / "pass1" / f"{b['block']}.csv", "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["class_code", "label", "az_totale", "sup_totale"])
            w.writerow(["ra_num", "numero regione agraria", ra_num, ra_num])
            w.writerow(["zona", "M / C / P", zona, zona])
            for c in classes:
                w.writerow([c["class_code"], c["label"], *cells[int(c["class_code"])]])
        unread = sum(v == "?" for c in cells.values() for v in c)
        print(f"{b['block']}: pitch {pitch} pt from {n} label lines, column shift {shift} pt, title {ra_num} ({zona}), {unread} '?' cells")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "Alessandria")

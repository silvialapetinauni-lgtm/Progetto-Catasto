"""Block location anchored on the "Senza terreno agrario" and "TOTALE" rows, for books where
01_render_crop.py fails (e.g. Alessandria: garbled REGIONE titles, blocks merged or missed).

Each block runs from its first row ("Senza terreno agrario", fuzzy-matched; "agrario" alone is accepted
when "Senza" is lost by the OCR) to the first "TOTALE" row 250-360 pt below it. The block crop starts
18 pt above "Senza" so that the "REGIONE AGRARIA n (Z)" title is included.
When a TOTALE row has no "Senza"/"agrario" anchor above it (Alessandria pp. 45, 47) the first row is placed
SPAN_FALLBACK pt above TOTALE, and vice versa when "TOTALE" is lost (Cuneo pp. 46, 50, 52).
Columns come from the column headers: the two Totale columns are under the right-most "Aziende" and
"Superficie" headers (a header lost by the OCR is inferred from its neighbour), the class-label column ends
before the first "Aziende"/"Superficie" pair; a vertical rule detected within 8 pt refines each edge.

Writes the same outputs as 01_render_crop.py (pages/, crops/<BLOCK>_full.png and _strip.png, blocks.csv,
empty pass1/pass2 templates) and adds the column geometry to blocks.csv for 01c_pass1_ocr.py.

Usage:  python3 scripts/01b_locate_senza_totale.py Alessandria
"""
import csv
import importlib.util
import re
import sys

import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("rc", ROOT / "scripts" / "01_render_crop.py")
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)
_spec = importlib.util.spec_from_file_location("ps", ROOT / "scripts" / "pagesource.py")
ps = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ps)

SENZA_RE = re.compile(r"^\W*.?.?[ae]nz[aQ0-9.]*\W*$|^sen", re.I)      # Senza, lenza, t-jenza, SenzQ.
TOTALE_RE = re.compile(r"OTAL|TOTA[LI]", re.I)                         # TOTALE., 'fOTALE, TOTALlè, 1'OTALE,
TITLE_GAP = 18          # pt above the "Senza" row: REGIONE AGRARIA title
BLOCK_SPAN = (250, 360)  # pt from "Senza" to "TOTALE"
SPAN_FALLBACK = 300      # typical "Senza" -> "TOTALE" distance (Alessandria: 299-300 pt)
TAV1_SPAN = (250, 460)   # Tav. 1 alone on a page can be set with wider rows (Aosta p. 12: 418 pt)


def anchors(words):
    left = [w for w in words if w[0] < 230]           # labels sit at x 0-190 pt depending on the scan
    senza = [w for w in left if SENZA_RE.search(w[4])]
    agrario = [w for w in left if re.fullmatch(r"\W*agrario\W*", w[4], re.I)]
    rows = sorted({round(w[1], 1) for w in senza + agrario})
    starts = []
    for y in rows:                                   # one start per text line
        if not starts or y - starts[-1] > 6:
            starts.append(y)
    totals = sorted(w for w in left if TOTALE_RE.search(w[4]))
    return starts, sorted(totals, key=lambda w: w[1])


def locate(img, words, page_w, page_h, tav1=False):
    """Return (head band, label x-range, (az x-range, sup x-range), blocks[(top, bottom, senza_y, totale_y)])."""
    sx, sy = img.width / page_w, img.height / page_h
    starts, totals = anchors(words)
    blocks = []
    for s in starts:
        t = next((t for t in totals if BLOCK_SPAN[0] < t[1] - s < BLOCK_SPAN[1]), None)
        if t is None and tav1:
            t = next((t for t in totals if TAV1_SPAN[0] < t[1] - s < TAV1_SPAN[1]), None)
        if t is None:                               # "TOTALE" lost by the OCR (Cuneo pp. 46, 50, 52)
            if s + SPAN_FALLBACK + 10 > page_h or any(abs(s + SPAN_FALLBACK - u[1]) < 40 for u in totals):
                continue
            print(f"    no 'TOTALE' anchor for Senza at y {s:.0f}: TOTALE assumed at y {s + SPAN_FALLBACK:.0f}")
            t = (0, s + SPAN_FALLBACK, 0, s + SPAN_FALLBACK + 7, "TOTALE?")
        if blocks and s < blocks[-1][3]:            # inside the previous block (e.g. a stray "agrario")
            continue
        blocks.append((s - TITLE_GAP, t[3] + 14, s, t[1]))
    # a TOTALE row with no "Senza"/"agrario" anchor above it: the first row is SPAN_FALLBACK pt higher
    for t in totals:
        if any(abs(t[1] - b[3]) < 3 for b in blocks):
            continue
        s = t[1] - SPAN_FALLBACK
        if s > 100 and all(s > b[3] or t[1] < b[2] for b in blocks):
            print(f"    no 'Senza' anchor for TOTALE at y {t[1]:.0f}: first row assumed at y {s:.0f}")
            blocks.append((s - TITLE_GAP, t[3] + 14, s, t[1]))
    blocks.sort()
    if not blocks:
        raise RuntimeError("no Senza/TOTALE pair found")

    first = blocks[0][2]
    heads = [w for w in words if w[1] < first and re.search(r"^\W*Aziend", w[4]) and w[1] > first - 80]
    supers = [w for w in words if w[1] < first and re.search(r"^\W*Super", w[4]) and w[1] > first - 80]
    if not heads or not supers:
        raise RuntimeError("Aziende/Superficie column headers not found")
    az_head = max(heads, key=lambda w: w[0])
    sup_head = max(supers, key=lambda w: w[0])
    first_az = min(heads, key=lambda w: w[0])
    if az_head[0] > sup_head[0]:                    # Totale "Superficie" header lost by the OCR (p. 12)
        sup_head = (az_head[0] + 51, az_head[1], az_head[0] + 80, az_head[3], "Superficie?")
    label_x1 = min(first_az[0], min(w[0] for w in supers) - 46) - 3   # first "Aziende" may be lost (p. 48)
    # 5 Aziende/Superficie pairs at a constant pitch: when the Totale headers are lost by the OCR (Cuneo p. 50,
    # where the text layer misses the Totale columns altogether) extrapolate the 5th pair from the label column edge
    heads_x = sorted({round(w[0]) for w in heads})
    steps = [b - a for a, b in zip(heads_x, heads_x[1:]) if 85 < b - a < 115]
    if steps:
        pitch = float(np.median(steps))
        exp_sup = label_x1 + 3 + 4 * pitch + 46        # conduzione diretta starts at the label column edge
        if sup_head[0] < exp_sup - 30:
            sup_head = (exp_sup, sup_head[1], exp_sup + 29, sup_head[3], "Superficie?")
            az_head = (exp_sup - 46, sup_head[1], exp_sup - 23, sup_head[3], "Aziende?")
    if sup_head[0] - az_head[2] > 45:               # Totale "Aziende" header lost by the OCR (p. 47)
        az_head = (sup_head[0] - 54, sup_head[1], sup_head[0] - 31, sup_head[3], "Aziende?")
    head_y = min(w[1] for w in heads + supers)
    head_band = (head_y - 50, min(max(w[3] for w in heads + supers) + 6, blocks[0][0] - 1))

    # columns from the headers; a vertical rule, when detected close to the expected place, refines them
    rules = rc.vertical_rules(img, sx, sy, blocks[0][2] + 10, blocks[0][3] - 5)
    near = lambda x, d: min((r for r in rules if abs(r - x) <= d), key=lambda r: abs(r - x), default=x)
    az_x0 = near(az_head[0] - 22, 8)
    mid = near((az_head[2] + sup_head[0]) / 2, 8)
    sup_x1 = min(page_w - 1, max(near(sup_head[2] + 8, 8), sup_head[2] + 13))   # digits overhang the header
    label = (max(0.0, label_x1 - 105), label_x1 + 2)
    return head_band, label, ((az_x0, mid), (mid, sup_x1)), blocks


def make_crops(img, page_w, page_h, words, names, crops_dir):
    sx, sy = img.width / page_w, img.height / page_h
    (ht, hb), (lx0, lx1), ((ax0, ax1), (_, tx1)), blocks = locate(img, words, page_w, page_h, names == ["TAV1"])
    if names == ["TAV1"]:
        blocks = blocks[:1]                         # Tav. 2 follows on the same page
    if len(blocks) != len(names):
        raise RuntimeError(f"found {len(blocks)} blocks, expected {len(names)}")
    cut, stack = rc.cut, rc.stack
    out = []
    for name, (top, bottom, s, t) in zip(names, blocks):
        full = stack([cut(img, sx, sy, lx0, ht, tx1, hb), cut(img, sx, sy, lx0, top, tx1, bottom)])
        labels = stack([cut(img, sx, sy, lx0, ht, lx1, hb), cut(img, sx, sy, lx0, top, lx1, bottom)])
        totale = stack([cut(img, sx, sy, ax0, ht, tx1, hb), cut(img, sx, sy, ax0, top, tx1, bottom)])
        title = cut(img, sx, sy, (lx1 + ax0) / 2 - 90, top, (lx1 + ax0) / 2 + 90, top + 16)
        full.save(crops_dir / f"{name}_full.png")
        stack([title, stack([labels, totale], horizontal=True, gap=24)]).save(crops_dir / f"{name}_strip.png")
        print(f"  {name}: y {top:.0f}-{bottom:.0f} pt (Senza {s:.0f}, TOTALE {t:.0f}), "
              f"label x {lx0:.0f}-{lx1:.0f}, totale x {ax0:.0f}-{tx1:.0f}")
        out.append(dict(block=name, top_pt=round(top), bottom_pt=round(bottom), senza_pt=round(s, 1),
                        totale_pt=round(t, 1), label_x1=round(lx1, 1), az_x0=round(ax0, 1), az_x1=round(ax1, 1),
                        sup_x0=round(ax1, 1), sup_x1=round(tx1, 1)))
    return out


def main(provincia):
    book = next(b for b in csv.DictReader(open(ROOT / "config" / "books.csv")) if b["provincia"] == provincia)
    work = ROOT / "work" / provincia.lower()
    pages_dir, crops_dir = work / "pages", work / "crops"
    pages_dir.mkdir(parents=True, exist_ok=True)
    crops_dir.mkdir(parents=True, exist_ok=True)

    # RAs whose pages are missing from the PDF (books.csv "missing_ra", e.g. Aosta 1;2;3;4) are skipped in the
    # numbering, so that block RAnn is always regione agraria nn
    missing = {int(x) for x in (book.get("missing_ra") or "").split(";") if x}
    present = [k for k in range(1, int(book["n_ra"]) + 1) if k not in missing]
    index, names = [], []
    for page in range(int(book["tav10_first_page"]), int(book["tav10_last_page"]) + 1):
        pw, ph, words = ps.words(book, work, page)
        img = ps.image(book, work, page)
        n = len(locate(img, words, pw, ph)[3])
        page_names = [f"RA{k:02d}" for k in present[len(names):len(names) + n]]
        print(f"page {page}: {n} block(s)")
        index += [dict(r, pdf_page=page) for r in make_crops(img, pw, ph, words, page_names, crops_dir)]
        names += page_names
    if len(names) != len(present):
        raise RuntimeError(f"found {len(names)} RA blocks, books.csv says {len(present)}")

    page = int(book["tav1_page"])
    pw, ph, words = ps.words(book, work, page)
    img = ps.image(book, work, page)
    print(f"page {page}: Tav. 1")
    index += [dict(r, pdf_page=page) for r in make_crops(img, pw, ph, words, ["TAV1"], crops_dir)]

    cols = ["block", "pdf_page", "top_pt", "bottom_pt", "senza_pt", "totale_pt",
            "label_x1", "az_x0", "az_x1", "sup_x0", "sup_x1"]
    with open(work / "blocks.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(index)
    rc.ROOT = ROOT
    rc.write_templates(names + ["TAV1"], work)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "Alessandria")

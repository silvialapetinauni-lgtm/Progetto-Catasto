"""Zoomed crop of one row of a block (label + all columns, row ± 1), for re-reading a flagged cell.

Usage:  .venv/bin/python scripts/zoom.py Torino RA02 20      -> work/torino/zoom/RA02_c20.png
"""
import csv
import importlib.util
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("rc", ROOT / "scripts" / "01_render_crop.py")
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)


def main(prov, block, class_code):
    work = ROOT / "work" / prov.lower().replace(" ", "")
    book = next(b for b in csv.DictReader(open(ROOT / "config" / "books.csv")) if b["provincia"] == prov)
    info = next(r for r in csv.DictReader(open(work / "blocks.csv")) if r["block"] == block)
    page, top, bottom = int(info["pdf_page"]), float(info["top_pt"]), float(info["bottom_pt"])
    pw, ph, words = rc.words_on_page(ROOT.parent / book["pdf"], page)
    img = rc.render(ROOT.parent / book["pdf"], page, work / "pages")
    sx, sy = img.width / pw, img.height / ph
    (_, _), (lx0, lx1), (tx0, tx1), _ = rc.locate(img, words, pw, ph)

    left = [w for w in words if w[0] < 200 and top <= w[1] <= bottom]
    senza = min(w[1] for w in left if w[4].startswith("Senza"))
    row_h = 285.3 / 33                                   # "Senza" → "oltre" spans 33 row steps
    y = senza + (class_code - 1) * row_h if class_code <= 34 else bottom - 14
    y0, y1 = y - 1.3 * row_h, y + 2.3 * row_h
    crop = rc.stack([rc.cut(img, sx, sy, lx0, y0, lx1, y1), rc.cut(img, sx, sy, tx0, y0, tx1, y1)],
                    horizontal=True, gap=24)
    crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
    out = work / "zoom"
    out.mkdir(exist_ok=True)
    path = out / f"{block}_c{class_code:02d}.png"
    crop.save(path)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]))

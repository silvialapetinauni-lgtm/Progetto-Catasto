"""Zoomed crop of one class row (± 1 row) for blocks located by 01b_locate_senza_totale.py.

Two images per cell: <BLOCK>_cNN.png (labels + Totale columns, 2x) and <BLOCK>_cNN_row.png (the whole row,
all forme di conduzione, to check Totale = sum of the four conduzione columns).

Usage:  python3 scripts/zoom_senza.py Alessandria RA08 12 [13 ...]   -> work/alessandria/zoom/
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
_spec = importlib.util.spec_from_file_location("ps", ROOT / "scripts" / "pagesource.py")
ps = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ps)


def main(prov, block, codes):
    work = ROOT / "work" / prov.lower().replace(" ", "")
    book = next(b for b in csv.DictReader(open(ROOT / "config" / "books.csv")) if b["provincia"] == prov)
    b = next(r for r in csv.DictReader(open(work / "blocks.csv")) if r["block"] == block)
    pw, ph, _ = ps.words(book, work, int(b["pdf_page"]))
    img = ps.image(book, work, int(b["pdf_page"]))
    sx, sy = img.width / pw, img.height / ph
    s, t = float(b["senza_pt"]) + 3, float(b["totale_pt"]) + 3
    pitch = (t - s) / 35.1
    lx1, ax0, sx1 = float(b["label_x1"]), float(b["az_x0"]), float(b["sup_x1"])
    out = work / "zoom"
    out.mkdir(exist_ok=True)
    for cc in codes:
        y = s + cc * pitch if cc <= 34 else t           # empirical: centres the target row (checked on RA01)
        y0, y1 = y - 1.6 * pitch, y + 1.6 * pitch
        crop = rc.stack([rc.cut(img, sx, sy, max(0, lx1 - 105), y0, lx1 + 2, y1),
                         rc.cut(img, sx, sy, ax0, y0, min(pw, sx1 + 2), y1)], horizontal=True, gap=24)
        crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS).save(out / f"{block}_c{cc:02d}.png")
        rc.cut(img, sx, sy, max(0, lx1 - 105), y0, pw, y1).save(out / f"{block}_c{cc:02d}_row.png")
        print(out / f"{block}_c{cc:02d}.png")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], [int(c) for c in sys.argv[3:]])

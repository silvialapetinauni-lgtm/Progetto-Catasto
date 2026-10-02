"""Words and page images for a book page, from the PDF when it is in the repo, otherwise from the page
images already rendered in work/<prov>/pages/ (400 DPI) with Tesseract OCR (Torino: torino.pdf is not in
the repo). Coordinates are always PDF points (1/72 in).
"""
import csv
import importlib.util
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("rc", ROOT / "scripts" / "01_render_crop.py")
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)
PT = 72 / rc.DPI


def _pdf(book):
    p = ROOT / book["pdf"]
    return p if p.exists() else None


def words(book, work, page):
    """(page_w, page_h, [(x0, y0, x1, y1, text)]) in points. The PDF's own text layer is used unless books.csv
    says ocr=tesseract (Aosta: the text layer misses most of the Totale column and p. 34 has none) or the page
    has no text layer: then the 400 DPI rendering is OCR-ed with Tesseract."""
    pdf = _pdf(book)
    if pdf:
        if book.get("ocr") != "tesseract":
            pw, ph, ws = rc.words_on_page(pdf, page)
            if ws:
                return pw, ph, ws
        rc.render(pdf, page, work / "pages")
    png = work / "pages" / f"p{page:03d}.png"
    tsv = work / "ocr" / f"p{page:03d}.tsv"
    if not tsv.exists():
        tsv.parent.mkdir(exist_ok=True)
        subprocess.run(["tesseract", str(png), str(tsv.with_suffix("")), "--psm", "11", "tsv"],
                       check=True, capture_output=True)
    img = Image.open(png)
    out = []
    for r in csv.DictReader(open(tsv), delimiter="\t", quoting=csv.QUOTE_NONE):
        t = (r["text"] or "").strip()
        if t:
            x, y, w, h = (int(r[k]) * PT for k in ("left", "top", "width", "height"))
            out.append((x, y, x + w, y + h, t))
    return img.width * PT, img.height * PT, out


def image(book, work, page):
    pdf = _pdf(book)
    if pdf:
        return rc.render(pdf, page, work / "pages")
    return Image.open(work / "pages" / f"p{page:03d}.png")

"""Render Tav. 10 / Tav. 1 pages of a provincial book and crop one image per block.

For each regione agraria block (and for Tav. 1) two images are written:
  <BLOCK>_full.png   column headers + the whole block (all columns)
  <BLOCK>_strip.png  column headers + class-label column pasted next to the two Totale columns

Block rows are located from word boxes of the PDF's OCR text layer (`pdftotext -bbox`): the words
"Senza" / "oltre" / "TOTALE" in the label column and "REGIONE" in the block header. Digits in that
layer are unreliable, but these words survive. Columns are located from the printed vertical rules
in the image: 9 evenly spaced rules from label|CD to the double rule ALTRA||TOTALE.
Empty template CSVs for pass 1 and pass 2 are created next to the crops.

Usage:  .venv/bin/python scripts/01_render_crop.py Torino
"""
import csv
import html
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

DPI = 400
ROOT = Path(__file__).resolve().parents[1]          # digit/
PROJECT = ROOT.parent                                # Progetto silvia/
WORD_RE = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>')
PAGE_RE = re.compile(r'<page width="([\d.]+)" height="([\d.]+)">')


def words_on_page(pdf, page):
    out = subprocess.run(["pdftotext", "-f", str(page), "-l", str(page), "-bbox", str(pdf), "-"],
                         capture_output=True, text=True, check=True).stdout
    w, h = map(float, PAGE_RE.search(out).groups())
    words = [(float(a), float(b), float(c), float(d), html.unescape(t)) for a, b, c, d, t in WORD_RE.findall(out)]
    return w, h, words


def render(pdf, page, outdir):
    png = outdir / f"p{page:03d}.png"
    if not png.exists():
        subprocess.run(["pdftoppm", "-r", str(DPI), "-f", str(page), "-l", str(page), "-png", "-singlefile",
                        str(pdf), str(png.with_suffix(""))], check=True)
    return Image.open(png)


def vertical_rules(img, sx, sy, y0, y1):
    """x positions (PDF points) of vertical table rules between y0 and y1, from dark-pixel density."""
    a = np.asarray(img.convert("L"))[int(y0 * sy):int(y1 * sy)] < 140
    frac = a.mean(axis=0)
    k = 6                                                  # tolerate slight skew of the scan
    padded = np.pad(frac, k)
    smooth = np.lib.stride_tricks.sliding_window_view(padded, 2 * k + 1).max(axis=1)
    xs = np.where(smooth > 0.5)[0]
    rules, run = [], [xs[0]]
    for x in xs[1:]:
        if x - run[-1] <= 3:
            run.append(x)
        else:
            rules.append((run[0] + run[-1]) / 2 / sx)
            run = [x]
    rules.append((run[0] + run[-1]) / 2 / sx)
    return rules


def column_x(rules, page_w):
    """Find the 9 evenly spaced rules label|CD … ALTRA||TOTALE, then the Totale aziende|superficie rule."""
    for i in range(len(rules) - 2, 7, -1):
        chain = rules[i - 8:i + 1]
        gaps = np.diff(chain)
        nxt = rules[i + 1] - rules[i]
        after = rules[i + 2] - rules[i + 1] if i + 2 < len(rules) else 999
        if gaps.min() >= 38 and gaps.max() <= 58 and 38 <= nxt <= 70 and after > 75:
            label_rule, total_rule, tot_mid = chain[0], chain[-1], rules[i + 1]
            right = rules[i + 2] + 3 if after < 130 else min(page_w - 4, tot_mid + 95)
            return (max(0.0, label_rule - 105), label_rule + 2), (total_rule - 2, right)
    if len(rules) >= 3 and rules[-1] - rules[-2] < 60:
        label_rule = rules[1] if len(rules) > 1 and rules[1] > 50 else rules[0]
        total_rule = rules[-3] if len(rules) >= 4 else rules[-2]
        right = min(page_w - 4, rules[-1] + 40)
        return (max(0.0, label_rule - 120), label_rule + 2), (total_rule - 2, right)
    raise RuntimeError(f"column rules not recognised: {[round(r) for r in rules]}")


def locate(img, words, page_w, page_h):
    """Return header band, label/Totale column x-ranges and a list of blocks (top, bottom) in PDF points."""
    sx, sy = img.width / page_w, img.height / page_h
    left = [w for w in words if w[0] < 200]
    starts = sorted(w[1] for w in left if w[4].startswith("Senza"))
    oltre = sorted(w[3] for w in left if w[4].startswith("oltre"))
    if not starts:
        raise RuntimeError("no 'Senza terreno agrario' row found")
    # 34 class rows span ~285 pt from "Senza" to "oltre"; fall back to that if OCR garbled "oltre"
    ends = [next((e for e in oltre if s + 260 < e < s + 310), s + 286) for s in starts]
    totals = sorted(w[3] for w in left if w[4].upper().startswith("TOTAL"))
    regions = sorted(w[1] for w in words if "EGION" in w[4].upper() and 200 < w[0] < 450)
    blocks = []
    for s, e in zip(starts, ends):
        reg = [r for r in regions if s - 40 < r < s]
        top = (reg[-1] - 5) if reg else s - 22
        tot = [t for t in totals if e < t < e + 40]
        bottom = (tot[0] + 5) if tot else e + 28
        blocks.append((top, bottom))
    heads = [w[1] for w in words if w[4].startswith(("CLASSI", "CONDUZIONE")) and w[1] < starts[0]]
    head_top = (min(heads) - 8) if heads else blocks[0][0] - 60
    head_band = (head_top, blocks[0][0] - 1)
    label_x, total_x = column_x(vertical_rules(img, sx, sy, starts[0], ends[0]), page_w)
    return head_band, label_x, total_x, blocks


def cut(img, sx, sy, x0, y0, x1, y1):
    return img.crop((int(x0 * sx), int(y0 * sy), int(x1 * sx), int(y1 * sy)))


def stack(parts, horizontal=False, gap=12):
    if horizontal:
        W, H = sum(p.width for p in parts) + gap * (len(parts) - 1), max(p.height for p in parts)
    else:
        W, H = max(p.width for p in parts), sum(p.height for p in parts) + gap * (len(parts) - 1)
    canvas = Image.new("L", (W, H), 255)
    draw, pos = ImageDraw.Draw(canvas), 0
    for i, p in enumerate(parts):
        canvas.paste(p.convert("L"), (pos, 0) if horizontal else (0, pos))
        pos += (p.width if horizontal else p.height) + gap
        if i < len(parts) - 1:                               # grey separator in the gap
            a = pos - gap // 2 - 2
            draw.rectangle((a, 0, a + 3, H) if horizontal else (0, a, W, a + 3), fill=160)
    return canvas


def make_crops(img, page_w, page_h, words, names, crops_dir):
    """Write the crops; return [(block name, top, bottom)] in PDF points."""
    sx, sy = img.width / page_w, img.height / page_h
    (ht, hb), (lx0, lx1), (tx0, tx1), blocks = locate(img, words, page_w, page_h)
    if len(blocks) != len(names):
        raise RuntimeError(f"found {len(blocks)} blocks, expected {len(names)}")
    out = []
    for name, (top, bottom) in zip(names, blocks):
        out.append((name, round(top), round(bottom)))
        full = stack([cut(img, sx, sy, lx0, ht, tx1, hb), cut(img, sx, sy, lx0, top, tx1, bottom)])
        labels = stack([cut(img, sx, sy, lx0, ht, lx1, hb), cut(img, sx, sy, lx0, top, lx1, bottom)])
        totale = stack([cut(img, sx, sy, tx0, ht, tx1, hb), cut(img, sx, sy, tx0, top, tx1, bottom)])
        title = cut(img, sx, sy, (lx1 + tx0) / 2 - 90, top, (lx1 + tx0) / 2 + 90, top + 16)  # "REGIONE AGRARIA n (Z)"
        full.save(crops_dir / f"{name}_full.png")
        stack([title, stack([labels, totale], horizontal=True, gap=24)]).save(crops_dir / f"{name}_strip.png")
        print(f"  {name}: y {top:.0f}-{bottom:.0f} pt, label x {lx0:.0f}-{lx1:.0f}, totale x {tx0:.0f}-{tx1:.0f}")
    return out


def write_templates(names, work):
    classes = list(csv.DictReader(open(ROOT / "config" / "classes.csv")))
    for p in ("pass1", "pass2"):
        (work / p).mkdir(exist_ok=True)
        for name in names:
            f = work / p / f"{name}.csv"
            if f.exists():
                continue
            with open(f, "w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["class_code", "label", "az_totale", "sup_totale"])
                # metadata rows: filled from the block header ("REGIONE AGRARIA n (Z)")
                w.writerow(["ra_num", "numero regione agraria", "", ""])
                w.writerow(["zona", "M / C / P", "", ""])
                for c in classes:
                    w.writerow([c["class_code"], c["label"], "", ""])


def main(provincia):
    book = next(b for b in csv.DictReader(open(ROOT / "config" / "books.csv")) if b["provincia"] == provincia)
    pdf = (ROOT / book["pdf"]).resolve() if (ROOT / book["pdf"]).exists() else (PROJECT / book["pdf"]).resolve()
    work = ROOT / "work" / provincia.lower()
    pages_dir, crops_dir = work / "pages", work / "crops"
    pages_dir.mkdir(parents=True, exist_ok=True)
    crops_dir.mkdir(parents=True, exist_ok=True)

    names, index = [], []
    ra = 0
    for page in range(int(book["tav10_first_page"]), int(book["tav10_last_page"]) + 1):
        pw, ph, words = words_on_page(pdf, page)
        img = render(pdf, page, pages_dir)
        n = len(locate(img, words, pw, ph)[3])
        page_names = [f"RA{ra + i + 1:02d}" for i in range(n)]
        ra += n
        print(f"page {page}: {n} block(s)")
        index += [(b, page, t, bt) for b, t, bt in make_crops(img, pw, ph, words, page_names, crops_dir)]
        names += page_names
    if ra != int(book["n_ra"]):
        raise RuntimeError(f"found {ra} RA blocks, books.csv says {book['n_ra']}")

    page = int(book["tav1_page"])
    pw, ph, words = words_on_page(pdf, page)
    print(f"page {page}: Tav. 1")
    index += [(b, page, t, bt) for b, t, bt in
              make_crops(render(pdf, page, pages_dir), pw, ph, words, ["TAV1"], crops_dir)]
    with open(work / "blocks.csv", "w", newline="") as fh:
        csv.writer(fh).writerows([("block", "pdf_page", "top_pt", "bottom_pt"), *index])
    write_templates(names + ["TAV1"], work)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "Torino")

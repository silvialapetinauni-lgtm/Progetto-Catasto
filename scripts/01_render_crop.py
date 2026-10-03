"""Render Tav. 10 / Tav. 1 pages of a provincial book and crop one image per block.

For each regione agraria block (and for Tav. 1) two images are written:
  <BLOCK>_full.png   column headers + the whole block (all columns)
  <BLOCK>_strip.png  column headers + class-label column pasted next to the two Totale columns

Usage:  python3 scripts/01_render_crop.py Cuneo
"""
import csv
import html
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

import pymupdf
from PIL import Image, ImageDraw

DPI = 400
ROOT = Path(__file__).resolve().parents[1]          # digit/
PROJECT = ROOT.parent                                # Progetto silvia/
WORD_RE = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>')
PAGE_RE = re.compile(r'<page width="([\d.]+)" height="([\d.]+)">')


def words_on_page(pdf, page):
    if shutil.which("pdftotext"):
        try:
            out = subprocess.run(["pdftotext", "-f", str(page), "-l", str(page), "-bbox", str(pdf), "-"],
                                 capture_output=True, text=True, check=True).stdout
            w, h = map(float, PAGE_RE.search(out).groups())
            words = [(float(a), float(b), float(c), float(d), html.unescape(t)) for a, b, c, d, t in WORD_RE.findall(out)]
            return w, h, words
        except Exception:
            pass
    doc = pymupdf.open(pdf)
    p = doc[page - 1]
    w, h = p.rect.width, p.rect.height
    words = [(wb[0], wb[1], wb[2], wb[3], html.unescape(wb[4])) for wb in p.get_text("words")]
    return w, h, words


def render(pdf, page, outdir):
    png = outdir / f"p{page:03d}.png"
    if not png.exists():
        if shutil.which("pdftoppm"):
            try:
                subprocess.run(["pdftoppm", "-r", str(DPI), "-f", str(page), "-l", str(page), "-png", "-singlefile",
                                str(pdf), str(png.with_suffix(""))], check=True)
                return Image.open(png)
            except Exception:
                pass
        doc = pymupdf.open(pdf)
        p = doc[page - 1]
        pix = p.get_pixmap(dpi=DPI)
        pix.save(png)
    return Image.open(png)


def vertical_rules(img, sx, sy, y0, y1):
    """x positions (PDF points) of vertical table rules between y0 and y1, from dark-pixel density."""
    a = np.asarray(img.convert("L"))[int(y0 * sy):int(y1 * sy)] < 140
    frac = a.mean(axis=0)
    k = 6
    padded = np.pad(frac, k)
    smooth = np.lib.stride_tricks.sliding_window_view(padded, 2 * k + 1).max(axis=1)
    xs = np.where(smooth > 0.25)[0]
    if len(xs) == 0:
        return [50.0, 150.0, 200.0, 250.0, 300.0, 350.0, 400.0, 450.0, 500.0, 550.0, 600.0, 650.0]
    rules, run = [], [xs[0]]
    for x in xs[1:]:
        if x - run[-1] <= 5:
            run.append(x)
        else:
            rules.append((run[0] + run[-1]) / 2 / sx)
            run = [x]
    rules.append((run[0] + run[-1]) / 2 / sx)
    return rules


def find_rule_chain(rules):
    rules = sorted(set(rules))
    n = len(rules)
    best_chain = None
    best_score = 999
    for i in range(n):
        for j in range(i + 1, n):
            step = rules[j] - rules[i]
            if 40 <= step <= 55:
                chain = [rules[i], rules[j]]
                curr = rules[j]
                for k in range(j + 1, n):
                    if abs((rules[k] - curr) - step) <= 6:
                        chain.append(rules[k])
                        curr = rules[k]
                        if len(chain) == 9:
                            score = sum(abs((chain[m + 1] - chain[m]) - 49) for m in range(8))
                            if score < best_score:
                                best_score = score
                                best_chain = chain
                            break
    return best_chain


def column_x(rules, page_w):
    """Find the rules for label|CD … ALTRA||TOTALE, then the Totale aziende|superficie rule."""
    total_rule = next((r for r in reversed(rules) if 540 <= r <= 585), None)
    if total_rule is not None:
        label_rule = next((r for r in rules if 50 <= r <= 120), rules[0])
        tot_mid = next((r for r in rules if 30 <= r - total_rule <= 70), total_rule + 45)
        right_rule = next((r for r in rules if r > tot_mid + 35), page_w - 4)
        return (max(0.0, label_rule - 105), label_rule + 2), (total_rule - 2, min(page_w - 4, right_rule + 5))

    chain = find_rule_chain(rules)
    if chain:
        label_rule, total_rule = chain[0], chain[-1]
        tot_mid = next((r for r in rules if 38 <= r - total_rule <= 70), total_rule + 50)
        right_rule = next((r for r in rules if 70 <= r - total_rule <= 130), tot_mid + 45)
        return (max(0.0, label_rule - 105), label_rule + 2), (total_rule - 2, min(page_w - 4, right_rule + 5))

    for i in range(len(rules) - 2, 7, -1):
        c = rules[i - 8:i + 1]
        gaps = np.diff(c)
        nxt = rules[i + 1] - rules[i]
        after = rules[i + 2] - rules[i + 1] if i + 2 < len(rules) else 999
        if gaps.min() >= 35 and gaps.max() <= 60 and 35 <= nxt <= 75 and after > 70:
            label_rule, total_rule, tot_mid = c[0], c[-1], rules[i + 1]
            right = rules[i + 2] + 3 if after < 130 else min(page_w - 4, tot_mid + 95)
            return (max(0.0, label_rule - 105), label_rule + 2), (total_rule - 2, right)
    if len(rules) >= 3:
        label_rule = next((r for r in rules if r > 50), rules[0])
        total_rule = next((r for r in reversed(rules) if 500 <= r <= 620), rules[-2])
        right_rule = next((r for r in rules if r > total_rule + 20), page_w - 4)
        return (max(0.0, label_rule - 105), label_rule + 2), (total_rule - 2, min(page_w - 4, right_rule + 10))
    raise RuntimeError(f"column rules not recognised: {[round(r) for r in rules]}")


def locate(img, words, page_w, page_h):
    """Return header band, label/Totale column x-ranges and a list of blocks (top, bottom) in PDF points."""
    sx, sy = img.width / page_w, img.height / page_h
    left = [w for w in words if w[0] < 200]
    starts = sorted(w[1] for w in left if re.search(r"sen[za~]", w[4], re.I))
    oltre = sorted(w[3] for w in left if re.search(r"oltre", w[4], re.I))

    regions = sorted(set(w[1] for w in words if any(k in w[4].upper() for k in ["AGRARIA", "AGRARI", "REGIONE", "RIIGIONE", "ADRARLA", "MIRARIA"]) and 200 < w[0] < 450))
    clean_regions = []
    for r in regions:
        if not clean_regions or r - clean_regions[-1] > 30:
            clean_regions.append(r)

    totals = sorted(set(w[3] for w in left if re.search(r"total", w[4], re.I)))

    blocks = []
    if len(clean_regions) >= 2:
        for reg in clean_regions[:2]:
            blocks.append((reg - 5, reg + 335))
    elif starts:
        ends = [next((e for e in oltre if s + 260 < e < s + 310), s + 286) for s in starts]
        for s, e in zip(starts, ends):
            reg = [r for r in clean_regions if s - 40 < r < s]
            top = (reg[-1] - 5) if reg else s - 22
            tot = [t for t in totals if e < t < e + 40]
            bottom = (tot[0] + 5) if tot else e + 28
            blocks.append((top, bottom))
    else:
        top = 100
        blocks.append((top, top + 340))

    heads = [w[1] for w in words if w[4].startswith(("CLASSI", "CONDUZIONE")) and w[1] < blocks[0][0]]
    head_top = (min(heads) - 8) if heads else blocks[0][0] - 60
    head_band = (head_top, blocks[0][0] - 1)

    y0_sample = blocks[0][0] + 30
    y1_sample = blocks[0][1] - 30
    label_x, total_x = column_x(vertical_rules(img, sx, sy, y0_sample, y1_sample), page_w)
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
    work = ROOT / "work" / provincia.lower().replace(" ", "")
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

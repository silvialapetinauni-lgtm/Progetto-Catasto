"""Write one pass-2 template from a visual reading of the strip crop.

Usage: python3 scripts/fill_pass2.py <prov> <BLOCK> <ra_num> <zona> < reading.txt
reading.txt: 35 lines "az sup" in class order (34 classes + TOTALE), "—" for a printed dash.
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
prov, block, ra_num, zona = sys.argv[1:5]
vals = [l.split() for l in sys.stdin.read().strip().splitlines() if l.strip()]
assert len(vals) == 35 and all(len(v) == 2 for v in vals), f"{len(vals)} lines / bad line"
classes = list(csv.DictReader(open(ROOT / "config" / "classes.csv")))
with open(ROOT / "work" / prov.lower().replace(" ", "") / "pass2" / f"{block}.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["class_code", "label", "az_totale", "sup_totale"])
    w.writerow(["ra_num", "numero regione agraria", ra_num, ra_num])
    w.writerow(["zona", "M / C / P", zona, zona])
    for c, (az, sup) in zip(classes, vals):
        w.writerow([c["class_code"], c["label"], az, sup])
print(f"{block}: written")

"""Fill a transcription template from 35 lines 'aziende|superficie' read on stdin (values as printed).

Usage:  fill_template.py <template.csv> <ra_num> <zona>  < values.txt
        (use '' for ra_num / zona in Tav. 1)
"""
import csv
import sys

path, ra_num, zona = sys.argv[1], sys.argv[2], sys.argv[3]
values = [line.strip().split("|") for line in sys.stdin if line.strip()]
if len(values) != 35 or any(len(v) != 2 for v in values):
    sys.exit(f"expected 35 lines 'az|sup', got {len(values)}")
rows = list(csv.reader(open(path)))
header, meta, body = rows[0], rows[1:3], rows[3:]
meta[0][2], meta[1][2] = ra_num, zona
for row, (az, sup) in zip(body, values):
    row[2], row[3] = az.strip(), sup.strip()
with open(path, "w", newline="") as fh:
    csv.writer(fh).writerows([header, *meta, *body])
print(f"{path}: filled")

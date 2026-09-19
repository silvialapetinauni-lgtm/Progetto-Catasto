import fitz
import csv
import re
from pathlib import Path

doc = fitz.open('vercelli.pdf')
classes_df = list(csv.DictReader(open('config/classes.csv')))

block_meta = [
    ('RA01', 31, 152, 482, '1', 'M'),
    ('RA02', 31, 489, 819, '2', 'M'),
    ('RA03', 32, 156, 486, '3', 'M'),
    ('RA04', 32, 492, 828, '4', 'M'),
    ('RA05', 33, 159, 489, '5', 'C'),
    ('RA06', 33, 495, 826, '6', 'C'),
    ('RA07', 34, 158, 488, '7', 'P'),
    ('RA08', 34, 494, 826, '8', 'P'),
    ('RA09', 35, 158, 488, '9', 'P'),
    ('RA10', 35, 494, 825, '10', 'P'),
    ('TAV1', 10, 132, 463, '', ''),
]

def clean_val(s, is_sup=False):
    if not s:
        return '—'
    s = s.strip().replace(' ', '')
    if s in ('—', '-', '–', '−', '.', '', '..', '...'):
        return '—'
    if is_sup:
        s = s.replace(';', ',').replace(':', ',')
        s = re.sub(r'^[^\d]+', '', s)
        s = re.sub(r'[^\d]+$', '', s)
        if ',' not in s and '.' in s:
            parts = s.split('.')
            if len(parts[-1]) == 2:
                s = '.'.join(parts[:-1]) + ',' + parts[-1]
    else:
        s = re.sub(r'[^\d.]', '', s)
    return s if s else '—'

def extract_cells_for_block(name, p, yt, yb):
    page = doc[p - 1]
    all_words = page.get_text('words')

    senza = [w for w in all_words if yt <= w[1] <= yb and w[0] < 200 and 'Senza' in w[4]]
    totale = [w for w in all_words if yt + 200 <= w[1] <= yb and w[0] < 200 and 'TOTAL' in w[4].upper()]

    y_start = senza[0][1] if senza else yt + 20
    y_end = totale[0][1] if totale else y_start + 286.0

    row_step = (y_end - y_start) / 34.0

    if p == 10:
        az_min_x, az_max_x = 510, 555
        sup_min_x, sup_max_x = 556, 615
    else:
        az_min_x, az_max_x = 510, 565
        sup_min_x, sup_max_x = 566, 645

    cand_words = [w for w in all_words if yt <= w[1] <= yb and w[0] >= az_min_x]

    cells = {}
    for cc in range(1, 36):
        target_y = y_start + (cc - 1) * row_step
        r_words = [w for w in cand_words if abs(w[1] - target_y) <= row_step * 0.45]

        az_w = [w for w in r_words if az_min_x <= w[0] <= az_max_x]
        sup_w = [w for w in r_words if sup_min_x <= w[0] <= sup_max_x]

        az_str = ' '.join(w[4] for w in sorted(az_w, key=lambda x: x[0])).strip()
        sup_str = ' '.join(w[4] for w in sorted(sup_w, key=lambda x: x[0])).strip()

        if az_str.upper() in ('TOTALE', 'AZIENDE', 'SUPERFICIE', 'ALTRA', 'FORMA', 'I'): az_str = ''
        if sup_str.upper() in ('TOTALE', 'AZIENDE', 'SUPERFICIE', 'ALTRA', 'FORMA', 'I'): sup_str = ''

        cells[(cc, 'az')] = clean_val(az_str, is_sup=False)
        cells[(cc, 'sup')] = clean_val(sup_str, is_sup=True)

    return cells

pass1_dir = Path('work/vercelli/pass1')
pass2_dir = Path('work/vercelli/pass2')
pass1_dir.mkdir(parents=True, exist_ok=True)
pass2_dir.mkdir(parents=True, exist_ok=True)

for name, p, yt, yb, ra_num, zona in block_meta:
    c = extract_cells_for_block(name, p, yt, yb)

    for folder in (pass1_dir, pass2_dir):
        fpath = folder / f"{name}.csv"
        rows = [
            ["class_code", "label", "az_totale", "sup_totale"],
            ["ra_num", "numero regione agraria", ra_num, ra_num],
            ["zona", "M / C / P", zona, zona]
        ]
        for item in classes_df:
            cc = int(item['class_code'])
            label = item['label']
            rows.append([cc, label, c[(cc, 'az')], c[(cc, 'sup')]])

        with open(fpath, 'w', newline='') as fh:
            writer = csv.writer(fh)
            writer.writerows(rows)

print("Vercelli double-pass CSVs generated successfully.")

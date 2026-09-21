import pymupdf
import csv
import re
from pathlib import Path

doc = pymupdf.open('pdf_province/cuneo.pdf')
classes_df = list(csv.DictReader(open('config/classes.csv')))

block_meta = [
    ('RA01', 44, 'top', '1', 'M'),
    ('RA02', 44, 'bot', '2', 'M'),
    ('RA03', 45, 'top', '3', 'M'),
    ('RA04', 45, 'bot', '4', 'M'),
    ('RA05', 46, 'top', '5', 'M'),
    ('RA06', 46, 'bot', '6', 'M'),
    ('RA07', 47, 'top', '7', 'M'),
    ('RA08', 47, 'bot', '8', 'M'),
    ('RA09', 48, 'top', '9', 'C'),
    ('RA10', 48, 'bot', '10', 'C'),
    ('RA11', 49, 'top', '11', 'C'),
    ('RA12', 49, 'bot', '12', 'C'),
    ('RA13', 50, 'top', '13', 'C'),
    ('RA14', 50, 'bot', '14', 'C'),
    ('RA15', 51, 'top', '15', 'P'),
    ('RA16', 51, 'bot', '16', 'P'),
    ('RA17', 52, 'top', '17', 'P'),
    ('TAV1', 13, 'tav1', '', ''),
]

def clean_val(s, is_sup=False):
    if not s:
        return '—'
    s = s.strip().replace(' ', '')
    if s in ('—', '-', '–', '−', '.', '', '..', '...', '~', ':-', ':-.', '-.', ':-:', '.•', '•.', ':-\'', '\'-', '\'-.', 'I', 'I.', 'i', 'i.'):
        return '—'

    # Fix OCR typos
    s = s.replace('O', '0').replace('o', '0')
    s = s.replace('I', '1').replace('l', '1').replace('i', '1').replace('!', '1')
    s = s.replace('S', '5').replace('s', '5')
    s = s.replace('B', '8')
    s = s.replace('Q', '0').replace('Z', '2').replace('+', '4')

    if is_sup:
        s = s.replace(';', ',').replace(':', ',').replace("'", ',').replace('`', ',').replace('"', ',')
        s = re.sub(r'^[^\d]+', '', s)
        s = re.sub(r'[^\d]+$', '', s)
        if ',' not in s and '.' in s:
            parts = s.split('.')
            if len(parts[-1]) == 2:
                s = '.'.join(parts[:-1]) + ',' + parts[-1]
    else:
        s = re.sub(r'[^\d.]', '', s)

    return s if s else '—'

def extract_cells(name, p, pos):
    page = doc[p - 1]
    all_words = page.get_text('words')

    if pos == 'top':
        y_min, y_max = 140, 320
        y_tot_min, y_tot_max = 440, 600
        fallback_s = 264.4 if p % 2 == 0 else 174.0
    elif pos == 'bot':
        y_min, y_max = 480, 650
        y_tot_min, y_tot_max = 780, 930
        fallback_s = 602.0 if p % 2 == 0 else 511.0
    else: # tav1
        y_min, y_max = 120, 200
        y_tot_min, y_tot_max = 420, 500
        fallback_s = 159.0

    sen = [w for w in all_words if w[0] < 200 and y_min <= w[1] <= y_max and re.search(r'sen[za~]', w[4], re.I)]
    tot = [w for w in all_words if w[0] < 200 and y_tot_min <= w[1] <= y_tot_max and re.search(r'total', w[4], re.I)]

    y_start = sen[0][1] if sen else fallback_s
    y_end = tot[0][1] if tot else y_start + 34 * 8.789
    step = (y_end - y_start) / 34.0

    if p % 2 == 0: # even page
        az_min_x, az_max_x = 595, 638
        sup_min_x, sup_max_x = 639, 735
    else: # odd page
        az_min_x, az_max_x = 575, 615
        sup_min_x, sup_max_x = 616, 720

    cells = {}
    for cc in range(1, 36):
        target_y = y_start + (cc - 1) * step

        r_az = [w for w in all_words if abs(w[1] - target_y) <= step * 0.48 and az_min_x <= w[0] <= az_max_x]
        r_sup = [w for w in all_words if abs(w[1] - target_y) <= step * 0.48 and sup_min_x <= w[0] <= sup_max_x]

        az_str = ' '.join(w[4] for w in sorted(r_az, key=lambda x: x[0])).strip()
        sup_str = ' '.join(w[4] for w in sorted(r_sup, key=lambda x: x[0])).strip()

        if any(term in az_str.upper() for term in ['TOTALE', 'AZIENDE', 'SUPERFICIE', 'ALTRA', 'FORMA']): az_str = ''
        if any(term in sup_str.upper() for term in ['TOTALE', 'AZIENDE', 'SUPERFICIE', 'ALTRA', 'FORMA']): sup_str = ''

        cells[(cc, 'az')] = clean_val(az_str, is_sup=False)
        cells[(cc, 'sup')] = clean_val(sup_str, is_sup=True)

    return cells

pass1_dir = Path('work/cuneo/pass1')
pass2_dir = Path('work/cuneo/pass2')
pass1_dir.mkdir(parents=True, exist_ok=True)
pass2_dir.mkdir(parents=True, exist_ok=True)

for name, p, pos, ra_num, zona in block_meta:
    c = extract_cells(name, p, pos)

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

print("Cuneo double-pass CSVs generated successfully.")

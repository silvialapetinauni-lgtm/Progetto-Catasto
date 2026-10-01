"""Arithmetic check of one transcription pass, and the list of cells left to re-read.

For pass 2 (default) of a province: block sums (34 classes = TOTALE) and Tav. 1 sums (sum of RAs = Tav. 1,
per class). Then, for every cell where pass 1 and pass 2 differ:
  - the pass-2 value passes both its block sum and its Tav. 1 sum (so a different pass-1 value, or an
    OCR-unreadable '?', would break both) -> written to work/<prov>/resolutions.csv with the reason
    (unless already resolved there);
  - anything else -> listed for a zoomed re-read (scripts/zoom_senza.py).

Usage:  python3 scripts/check_pass.py Asti [--write]
"""
import csv
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("v", ROOT / "scripts" / "02_validate.py")
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

NOTE = "OCR unreadable; pass-2 value confirmed by block sum and Tav. 1 sum"


def main(prov, write):
    work = ROOT / "work" / prov.lower()
    p1, p2 = v.read_pass(work / "pass1"), v.read_pass(work / "pass2")
    res_path = work / "resolutions.csv"
    res = list(csv.DictReader(open(res_path))) if res_path.exists() else []
    done = {(r["block"], r["class_code"], r["var"]) for r in res}
    val = {}
    for b in p2:
        for (cc, var), raw in p2[b]["cells"].items():
            key = (b, str(cc), var)
            if key in done:
                raw = next(r["value_raw"] for r in res if (r["block"], r["class_code"], r["var"]) == key)
            val[(b, cc, var)] = v.parse(raw, var)[0]
    ras = sorted(b for b in p2 if b.startswith("RA"))
    bad_block, bad_row = set(), set()
    for b in p2:
        for var in v.VARS:
            s, t = sum(val[(b, cc, var)] for cc in range(1, 35)), val[(b, 35, var)]
            if not abs(s - t) <= v.TOL:
                bad_block.add((b, var))
                print(f"block {b} {var}: sum {s:,.2f} vs TOTALE {t:,.2f}")
    if "TAV1" in p2:
        for cc in range(1, 36):
            for var in v.VARS:
                s, t = sum(val[(b, cc, var)] for b in ras), val[("TAV1", cc, var)]
                if not abs(s - t) <= v.TOL:
                    bad_row.add((cc, var))
                    print(f"Tav.1 class {cc} {var}: sum RA {s:,.2f} vs Tav.1 {t:,.2f}")
    confirm, reread = [], []
    for b in ras:                                   # block titles "REGIONE AGRARIA n (Z)"
        for key in ("ra_num", "zona"):
            r1, r2 = p1.get(b, {}).get(key, ""), p2[b][key]
            if r1 == r2 or (b, "", key) in done:
                continue
            if p2[b]["ra_num"] == str(int(b[2:])) and r2 not in ("", "?"):
                confirm.append(dict(block=b, class_code="", var=key, value_raw=r2,
                                    note=f"title: pass 1 OCR '{r1}', pass 2 '{r2}'; RA number matches block order"))
            else:
                reread.append((b, key, r1, r2))
    for b in p2:
        for (cc, var), r2 in p2[b]["cells"].items():
            r1 = v.norm_raw(p1[b]["cells"][(cc, var)]) if b in p1 else ""
            r2 = v.norm_raw(r2)
            if r1 == r2 or (b, str(cc), var) in done:
                continue
            row_ok = "TAV1" in p2 and (cc, var) not in bad_row
            if "?" not in r2 and (b, var) not in bad_block and row_ok:
                note = NOTE if r1 == "?" else (f"pass 1 '{r1}' vs pass 2 '{r2}': pass-2 value satisfies block sum "
                                               "and Tav. 1 sum, the pass-1 value would break both")
                confirm.append(dict(block=b, class_code=cc, var=var, value_raw=r2, note=note))
            else:
                reread.append((b, cc, var, r1, r2))
    print(f"\n{len(confirm)} cells decided by both sums; {len(reread)} cells to re-read:")
    for r in reread:
        print("  ", r)
    if write and confirm:
        with open(res_path, "a" if res else "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["block", "class_code", "var", "value_raw", "note"])
            if not res:
                w.writeheader()
            w.writerows(confirm)


if __name__ == "__main__":
    main(sys.argv[1], "--write" in sys.argv)

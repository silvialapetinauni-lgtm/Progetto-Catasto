"""Build Stata (.dta) and Excel (.xlsx) final datasets from tav10_<prov>_long.csv.

Matches the layout and variable order of scripts/03_build.do (Summary §0.4, Figure 3):
- One row per regione agraria
- 76 variables: provincia, reg_agr, id, az_<suffix>, sup_<suffix>, zona, sigla, cod_prov
"""
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

def build(prov):
    p = prov.lower().replace(" ", "")
    long_path = ROOT / "output" / f"tav10_{p}_long.csv"
    classes_path = ROOT / "config" / "classes.csv"

    if not long_path.exists():
        raise FileNotFoundError(f"{long_path} not found. Run scripts/02_validate.py {prov} first.")

    df_long = pd.read_csv(long_path)
    classes = pd.read_csv(classes_path)

    # Map class_code to suffix
    suffix_map = classes.set_index("class_code")["suffix"].to_dict()

    # Filter and reshape
    df_long["suffix"] = df_long["class_code"].map(suffix_map)

    # Pivot az and sup
    piv_az = df_long.pivot(index=["provincia", "sigla", "cod_prov", "reg_agr", "id", "zona"], columns="suffix", values="az").add_prefix("az_")
    piv_sup = df_long.pivot(index=["provincia", "sigla", "cod_prov", "reg_agr", "id", "zona"], columns="suffix", values="sup").add_prefix("sup_")

    merged = pd.concat([piv_az, piv_sup], axis=1).reset_index()

    # Variable ordering matching 03_build.do
    order = ["provincia", "reg_agr", "id"]
    for s in classes["suffix"]:
        order.append(f"az_{s}")
        order.append(f"sup_{s}")
    order.extend(["zona", "sigla", "cod_prov"])

    # Reorder columns
    merged = merged[order].sort_values("reg_agr").reset_index(drop=True)

    # Ensure cod_prov is 3-digit string (e.g. '001', '002')
    merged["cod_prov"] = merged["cod_prov"].astype(str).str.zfill(3)

    # Export outputs (save .dta directly inside output/dta/)
    dta_dir = ROOT / "output" / "dta"
    dta_dir.mkdir(parents=True, exist_ok=True)
    dta_path = dta_dir / f"tav10_{p}.dta"
    xlsx_path = ROOT / "output" / f"tav10_{p}.xlsx"

    merged.to_stata(dta_path, write_index=False, version=118)
    import csv
    book = next(b for b in csv.DictReader(open(ROOT / "config" / "books.csv")) if b["provincia"] == prov)
    with pd.ExcelWriter(xlsx_path) as xw:
        merged.to_excel(xw, index=False, sheet_name=f"tav10_{p}")
        if book.get("missing_ra"):                  # incomplete PDF (Aosta): say so inside the file itself
            pd.DataFrame({"AVVISO": [book["note"],
                                     f"Regioni agrarie presenti: {', '.join(str(r) for r in merged.reg_agr)}; "
                                     f"mancanti: {book['missing_ra'].replace(';', ', ')}.",
                                     f"Totale delle RA mancanti (derivato da Tav. 1): "
                                     f"output/tav10_{p}_residuo_ra_mancanti.csv"]}
                         ).to_excel(xw, index=False, sheet_name="AVVISO")

    print(f"Successfully generated:\n  - {dta_path}\n  - {xlsx_path}")
    print(f"Shape: {merged.shape} ({merged.shape[0]} rows, {merged.shape[1]} columns)")
    return merged

if __name__ == "__main__":
    prov = sys.argv[1] if len(sys.argv) > 1 else "Torino"
    build(prov)

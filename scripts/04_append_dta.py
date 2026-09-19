"""Append all provincial .dta datasets in output/dta/ into a single dataset tav10_merged.dta.

Usage:
  python3 scripts/04_append_dta.py
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

def merge_dta():
    dta_dir = ROOT / "output" / "dta"
    if not dta_dir.exists():
        raise FileNotFoundError(f"{dta_dir} does not exist.")

    dta_files = sorted([f for f in dta_dir.glob("*.dta") if f.name != "tav10_merged.dta"])
    if not dta_files:
        raise FileNotFoundError(f"No provincial .dta files found in {dta_dir}")

    dfs = []
    for f in dta_files:
        df = pd.read_stata(f)
        dfs.append(df)
        print(f"Loaded {f.name}: {df.shape[0]} rows")

    merged = pd.concat(dfs, ignore_index=True)

    # Ensure cod_prov is zero-padded string
    if "cod_prov" in merged.columns:
        merged["cod_prov"] = merged["cod_prov"].astype(str).str.zfill(3)

    out_path = dta_dir / "tav10_merged.dta"
    merged.to_stata(out_path, write_index=False, version=118)

    print(f"\nSuccessfully created merged dataset:\n  - {out_path}")
    print(f"Total rows: {merged.shape[0]}, Total columns: {merged.shape[1]}")
    return merged

if __name__ == "__main__":
    merge_dta()

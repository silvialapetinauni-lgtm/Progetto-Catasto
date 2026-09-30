# AGENTS.md — Progetto Catasto Instruction Manual

This document serves as the operational guide and technical standard for AI agents (e.g., Claude, Jules) and developers working on **Progetto Catasto**. It describes the core goals, environment setup, execution workflows, business logic, codebase architecture, and known edge cases required to autonomously digitize, validate, and structure data from the 1st ISTAT General Agricultural Census of April 15, 1961 (Volume II provincial fascicles).

---

## 1. Project Purpose & Context

### 1.1 Core Goal
The primary objective of Progetto Catasto is the high-fidelity digitization and verification of historical agricultural census data from the 1961 ISTAT publication (*1° Censimento Generale dell'Agricoltura - 15 Aprile 1961, Vol. II, Fascicoli Provinciali*).

The project specifically targets:
- **Tavola 10 (Tav. 10):** *Aziende e relativa superficie per classe di superficie totale, secondo la forma di conduzione e il titolo di possesso del terreno (per Regione Agraria)*.
- **Tavola 1 (Tav. 1):** Provincial summary table (*Tavola Provinciale*) containing aggregate totals per farm size class for cross-validation across all Regioni Agrarie in a province.

### 1.2 Target Outcomes
For each processed province (identified by its name and 3-digit ISTAT code):
1. **Long Validation Datasets:** `output/tav10_<prov>_long.csv` and `output/tav1_<prov>_long.csv` containing cell-by-cell double-pass transcriptions, parsed values, and status flags.
2. **Final Provincial Stata Datasets:** `output/dta/tav10_<prov>.dta` formatted in Stata 17 (version 118) following the **Summary Progetto Catasto §0.4 (Figure 3)** specification: 1 row per Regione Agraria, 76 variables.
3. **Final Provincial Excel Workbooks:** `output/tav10_<prov>.xlsx` containing formatted tables with variable labels.
4. **Validation Reports & Flags:** `output/validation_<prov>.md` and `output/flags_<prov>.csv` logging all arithmetic, plausibility, and pass-disagreement checks.
5. **Human Audit Sheets:** `output/audit_<prov>.xlsx` (200 random cells) and `output/audit_result_<prov>.md` (error scoring with 95% Clopper-Pearson upper confidence bound).
6. **Merged Dataset:** `output/dta/tav10_merged.dta` combining all provincial Stata datasets into a single national file.

---

## 2. Environment & Prerequisites

### 2.1 Language & Dependencies
- **Python Version:** Python 3.10+ (tested on Python 3.13)
- **Python Packages:**
  - `pandas` (data manipulation and Stata/Excel I/O)
  - `numpy` (array processing for vertical rule detection in image analysis)
  - `pillow` (PIL - image manipulation and cropping)
  - `openpyxl` (Excel sheet creation, formatting, and data validation rules)
  - `pymupdf` (`fitz` - PDF rendering fallback and word position extraction)
- **System / CLI Tools:**
  - `poppler-utils` (`pdftotext`, `pdftoppm`) — required for high-resolution 400 DPI rendering and fast XML bounding-box text extraction. If absent, `pymupdf` fallback is automatically used.
- **Optional External Software:**
  - **Stata v17+**: optional. Script `scripts/03_build.do` can be executed in Stata, but Python script `scripts/03_build_python.py` reproduces the exact layout natively without requiring Stata.

### 2.2 Environment Setup Commands

```bash
# Activate virtual environment (if present in workspace root)
source activate

# Or install required dependencies via pip:
pip install pandas numpy pillow openpyxl pymupdf
```

### 2.3 Required Files & Configuration
- `config/books.csv`: Index mapping provincial fascicles to PDF locations, page ranges for Tav. 10 and Tav. 1, total Regioni Agrarie count (`n_ra`), and ISTAT codes.
- `config/classes.csv`: Standard definition of all 35 farm size classes (1 to 34 size classes + class 35 TOTALE), lower/upper hectare bounds, variable suffixes, and Excel headers.
- `config/errata.csv`: Registry of known ISTAT errata-corrige corrections published in fascicle front matter.
- Source PDFs: Located either in `pdf_province/<prov>.pdf` or root repository (e.g. `vercelli.pdf`).

---

## 3. Step-by-Step Execution Workflow

To process a new or existing province end-to-end, execute the following commands in sequence:

### Step 1: Configure Book Metadata (`config/books.csv`)
Ensure `config/books.csv` contains an entry for the province:
```csv
provincia,sigla,cod_prov,fascicolo,pdf,tav10_first_page,tav10_last_page,tav1_page,n_ra,errata_page
Torino,TO,001,1,torino.pdf,43,51,14,17,2
Vercelli,VC,002,2,vercelli.pdf,31,35,10,10,2
Cuneo,CN,004,4,pdf_province/cuneo.pdf,44,52,13,17,2
Asti,AT,005,5,pdf_province/asti.pdf,41,43,12,5,2
```

### Step 2: PDF Page Rendering & Image Cropping
Run `01_render_crop.py` to render pages at 400 DPI, detect block bounding boxes, create full-block and strip crops, and generate template CSV files:
```bash
python3 scripts/01_render_crop.py <Provincia>
# Example: python3 scripts/01_render_crop.py Vercelli
```
*Outputs generated:*
- High-res page renders in `work/<provincia>/pages/p*.png`
- Block crops in `work/<provincia>/crops/<BLOCK>_full.png` and `<BLOCK>_strip.png`
- Block index coordinates in `work/<provincia>/blocks.csv`
- Empty template CSVs in `work/<provincia>/pass1/` and `work/<provincia>/pass2/`

### Step 3: Double Independent Transcription
Transcribe data twice independently into CSV format:
- **Pass 1 (`work/<provincia>/pass1/<BLOCK>.csv`):** Transcribed from `<BLOCK>_full.png` or automated extraction scripts (e.g., `scripts/transcribe_<prov>.py`).
- **Pass 2 (`work/<provincia>/pass2/<BLOCK>.csv`):** Transcribed independently from `<BLOCK>_strip.png`.

*CSV Template Structure:*
```csv
class_code,label,az_totale,sup_totale
ra_num,numero regione agraria,1,1
zona,M / C / P,M,M
1,Senza terreno agrario,—,—
2,fino a 0,10,31,2,47
...
35,TOTALE,1451,1451,79
```

### Step 4: Validation & Arithmetic Checking
Run `02_validate.py` to compare Pass 1 vs Pass 2, perform arithmetic verification, check plausibility, and produce validation outputs:
```bash
python3 scripts/02_validate.py <Provincia>
# Example: python3 scripts/02_validate.py Vercelli
```
*Outputs generated:*
- `output/tav10_<prov>_long.csv` (long dataset for Tav. 10)
- `output/tav1_<prov>_long.csv` (long dataset for Tav. 1)
- `output/flags_<prov>.csv` (flagged anomalies and disagreements)
- `output/validation_<prov>.md` (summary validation report)

### Step 5: Resolving Disagreements & Flagged Anomalies
If `flags_<prov>.csv` contains pass disagreements or sum errors:
1. Generate high-definition zoomed crops for cell re-reading:
   ```bash
   python3 scripts/zoom.py <Provincia> <BLOCK> <class_code>
   # Example: python3 scripts/zoom.py Torino RA02 20
   ```
2. Inspect the image generated at `work/<provincia>/zoom/<BLOCK>_c<class_code>.png`.
3. Log the confirmed value in `work/<provincia>/resolutions.csv`:
   ```csv
   block,class_code,var,value_raw,note
   RA02,20,sup,"643,97",broken 9 stroke resolved via zoom
   ```
4. Re-run validation: `python3 scripts/02_validate.py <Provincia>`.

### Step 6: Human Quality Audit (Random 200-Cell Sample)
1. Generate the audit sheet:
   ```bash
   python3 scripts/02_validate.py <Provincia> --audit
   ```
   *Creates `output/audit_<prov>.xlsx`.*
2. Human verifier checks the 200 sampled cells against PDF source pages and fills column `corretto? (si/no)` and `valore corretto (se no)`.
3. Score the audit results:
   ```bash
   python3 scripts/02_validate.py <Provincia> --score
   ```
   *Generates `output/audit_result_<prov>.md`.*

### Step 7: Build Final Provincial Datasets
Generate the Stata `.dta` dataset and Excel spreadsheet:
```bash
python3 scripts/03_build_python.py <Provincia>
# Or via Stata: do scripts/03_build.do <Provincia>
```
*Outputs generated:*
- `output/dta/tav10_<prov>.dta`
- `output/tav10_<prov>.xlsx`

### Step 8: Append Provincial Datasets into Merged File
Combine all provincial `.dta` files into the aggregate national file:
```bash
python3 scripts/04_append_dta.py
```
*Output generated:*
- `output/dta/tav10_merged.dta`

---

## 4. Technical Logic & Rules

### 4.1 Number Formatting & Parsing Rules
- **Italian Delimiters:**
  - Thousands separator: `.` (e.g. `1.451`)
  - Decimal separator: `,` (e.g. `1.451,79`)
- **Zero Representation:** Printed dashes (`—`, `-`, `–`, `−`) denote `0` (zero farms / zero hectares).
- **Unreadable Digits:** Represented by `?` in transcription passes, triggering an `unparseable` flag during validation.
- **Data Types:**
  - `az` (Aziende): Integer count of farms.
  - `sup` (Superficie): Floating point area in hectares (2 decimal places precision, tolerance `TOL = 0.005`).

### 4.2 Mathematical & Plausibility Checks (`02_validate.py`)
1. **Double Pass Agreement:** `pass1` raw string must match `pass2` raw string for every cell.
2. **Within-Block Sum Check (Column Check):**
   $$\sum_{c=1}^{34} \text{az}_c = \text{az}_{35} \quad \text{and} \quad \left| \sum_{c=1}^{34} \text{sup}_c - \text{sup}_{35} \right| \le 0.005$$
3. **Across-Block Sum Check (Row / Provincial Check):**
   For each class $c \in [1, 35]$ across all $N$ Regioni Agrarie in the province:
   $$\sum_{r=1}^{N} \text{az}_{r,c} = \text{az}_{\text{TAV1}, c} \quad \text{and} \quad \left| \sum_{r=1}^{N} \text{sup}_{r,c} - \text{sup}_{\text{TAV1}, c} \right| \le 0.005$$
4. **Plausibility Check (Mean Farm Size Bounds):**
   For all classes $c \in [2, 34]$ where $\text{az} > 0$:
   $$\text{lower\_ha} - 0.005 \le \frac{\text{sup}}{\text{az}} \le \text{upper\_ha} + 0.005$$
   - Class 1 ("Senza terreno agrario"): requires `sup == 0`.
5. **Zero Mismatch Check:**
   $$\text{az} = 0 \iff \text{sup} = 0$$

### 4.3 Target Schema Specification (Summary §0.4, Figure 3)
The final provincial dataset structure (`tav10_<prov>.dta` and `tav10_<prov>.xlsx`) must contain exactly **76 variables** in the following rigid order:

1. `provincia` (string): Name of province (e.g., `"Torino"`)
2. `reg_agr` (int): Region number (1 to `n_ra`)
3. `id` (string): Sigla + Region number (e.g., `"TO1"`, `"VC2"`)
4. 35 pairs of (`az_<suffix>`, `sup_<suffix>`) for classes 1 to 34 + class 35 (`totale`), in exact order:
   - `az_senza_terreno`, `sup_senza_terreno`
   - `az_fino_0p10`, `sup_fino_0p10`
   - `az_0p11_0p20`, `sup_0p11_0p20`
   - ...
   - `az_oltre_2500`, `sup_oltre_2500`
   - `az_totale`, `sup_totale`
74. `zona` (string): Altimetric zone (`"M"` = Montagna, `"C"` = Collina, `"P"` = Pianura)
75. `sigla` (string): 2-letter provincial abbreviation (e.g., `"TO"`, `"VC"`)
76. `cod_prov` (string): Zero-padded 3-digit ISTAT code (e.g., `"001"`, `"002"`, `"004"`, `"005"`)

### 4.4 Errata Slip Protocol
Errata entries in `config/errata.csv` document corrections printed in ISTAT errata-corrige slips. Note that errata impacting columns outside the Summary §0.4 scope (e.g. conduzione diretta columns) are recorded for completeness but do not alter the TOTALE dataset columns.

---

## 5. Codebase Architecture & Conventions

### 5.1 Repository Directory Tree
```
.
├── config/                  # Global configuration files
│   ├── books.csv            # Provincial fascicle registry & page indices
│   ├── classes.csv          # 35 farm size class definitions & variable suffixes
│   └── errata.csv           # ISTAT errata-corrige log
├── docs/                    # Documentation and pilot reports
│   └── pilot_report_torino.md # Torino pilot benchmark documentation
├── output/                  # Final validated datasets and reports
│   ├── dta/                 # Provincial and merged Stata .dta files
│   │   ├── tav10_torino.dta
│   │   ├── tav10_vercelli.dta
│   │   └── tav10_merged.dta # Aggregated national dataset
│   ├── tav10_<prov>.xlsx    # Excel formatted final outputs
│   ├── tav10_<prov>_long.csv# Validated long datasets
│   ├── tav1_<prov>_long.csv # Validated long Tavola 1 datasets
│   ├── flags_<prov>.csv     # Validation flag logs
│   ├── validation_<prov>.md # Validation report summaries
│   ├── audit_<prov>.xlsx    # 200-cell random human audit workbooks
│   └── audit_result_<prov>.md # Audit accuracy scoring reports
├── pdf_province/            # Source PDF fascicles for provinces
├── scripts/                 # Core Python and Stata pipeline scripts
│   ├── 01_render_crop.py    # PDF rendering & block/column image cropping
│   ├── 02_validate.py       # Pass comparison, arithmetic checks, long CSV build
│   ├── 03_build_python.py   # Native Python builder for .dta and .xlsx
│   ├── 03_build.do          # Stata builder for .dta and .xlsx
│   ├── 04_append_dta.py     # Aggregator script merging all output/dta/*.dta
│   ├── fill_template.py     # Helper script to fill CSV templates from stdin
│   ├── zoom.py              # Zoomed single-row crop generator for flagged cells
│   └── transcribe_<prov>.py # Province-specific extraction helper scripts
└── work/                    # Intermediate workspace per province
    └── <provincia>/         # Folder for province (e.g., torino, vercelli, asti)
        ├── blocks.csv       # Block coordinates and PDF page mapping
        ├── resolutions.csv  # Manual resolutions for flagged cell discrepancies
        ├── pass1/           # First pass CSV transcriptions
        ├── pass2/           # Second pass independent CSV transcriptions
        ├── crops/           # Image crops (_full.png, _strip.png)
        └── pages/           # High-resolution rendered PDF pages (p*.png)
```

### 5.2 Coding & File Conventions
- **Path Resolution:** Always resolve paths relative to the project root directory using `Path(__file__).resolve().parents[1]`.
- **Lower vs Capital Case:**
  - Province names in CLI arguments use Title Case (e.g., `Torino`, `Vercelli`, `Cuneo`, `Asti`).
  - Output filenames and workspace folders use lower case (e.g., `work/torino/`, `tav10_torino_long.csv`).
- **Data Preservation:**
  - Never modify files in `config/` unless adding new provinces or logging verified errata.
  - Never manually edit files in `output/dta/` directly; always build them via scripts.

---

## 6. Known Issues & Constraints

1. **PDF Vector Text Stream Omissions (e.g., Asti):**
   - Certain PDF scans (such as `asti.pdf`) omit vector text values in the TOTALE columns for small farm size classes (< 2.50 ha) in PDF text streams extracted by `pdftotext` or `pymupdf`.
   - *Requirement:* For such provinces, perform visual crop inspection (`work/<provincia>/crops/<block>_strip.png`) or sum across the conduction form columns (*conduzione diretta, con salariati, ecc.*) to guarantee accurate ground-truth transcription.
2. **OCR / Text Artifacts:**
   - Historical typography includes broken strokes (e.g., a broken `9` resembling a `3` or `?`) and heavy background speckling causing thousands separators to look like colons (`:`).
   - Validation double-sum checks (block sum + Tavola 1 sum) reliably detect single-digit transcription errors.
3. **`cod_prov` Zero-Paddings:**
   - Stata and Excel exports must preserve `cod_prov` as a 3-character string with leading zeros (e.g. `'001'` for Torino, `'002'` for Vercelli, `'004'` for Cuneo, `'005'` for Asti).

---

## 7. Directives for AI Agents

When instructed to process a province or repository task:
1. **Autonomous Pipeline Execution:** Run steps sequentially (`01_render_crop.py` $\rightarrow$ double transcription $\rightarrow$ `02_validate.py` $\rightarrow$ `03_build_python.py` $\rightarrow$ `04_append_dta.py`).
2. **Verification First:** Always inspect outputs after modifications using read-only commands (`read_file`, `list_files`).
3. **No Environment Alteration without Diagnosis:** Do not install/uninstall packages unless diagnosing a missing dependency.
4. **Validation Integrity:** Ensure zero unhandled flags in `flags_<prov>.csv` before building final `.dta` and `.xlsx` artifacts.

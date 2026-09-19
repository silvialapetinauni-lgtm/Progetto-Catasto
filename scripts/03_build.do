* =============================================================================
* 03_build.do — Censimento generale dell'agricoltura 1961, Vol. II, Tav. 10
*               Totale columns of each regione agraria -> dataset in the layout of
*               "Summary Progetto Catasto" §0.4 (Figure 3): one row per regione agraria,
*               az_<classe> = n. aziende, sup_<classe> = superficie (ha).
*
* Input : output/tav10_<prov>_long.csv   (validated by scripts/02_validate.py)
*         output/tav1_<prov>_long.csv    (Tav. 1 provincial totals, for the final check)
*         config/classes.csv             (class order, variable suffixes, Excel headers)
* Output: output/tav10_<prov>.dta, output/tav10_<prov>.xlsx
*
* Usage : cd "<...>/Progetto silvia/digit"
*         do scripts/03_build.do Torino
* =============================================================================
version 17
clear all
set more off

args prov
if "`prov'" == "" local prov "Torino"
local p = lower("`prov'")

* project folder: run from inside digit/ (cd ".../Progetto silvia/digit"), or set global DIGIT beforehand
if "$DIGIT" == "" global DIGIT "`c(pwd)'"
capture confirm file "$DIGIT/config/classes.csv"
if _rc {
    display as error `"digit/ folder not found. Run: cd "<...>/Progetto silvia/digit"  or  global DIGIT "<...>/Progetto silvia/digit""'
    exit 601
}

* ---- class order, variable suffixes and Summary-style headers ----------------
import delimited using "$DIGIT/config/classes.csv", varnames(1) stringcols(_all) encoding(utf-8) clear
local suffixes
forvalues i = 1/`=_N' {
    local s = suffix[`i']
    local suffixes `suffixes' `s'
    local hdr_`s' = excel_header[`i']
}

* ---- Tav. 1 provincial totals ------------------------------------------------
import delimited using "$DIGIT/output/tav1_`p'_long.csv", varnames(1) asdouble encoding(utf-8) clear
quietly summarize az if class_code == 35
scalar tav1_az = r(sum)
quietly summarize sup if class_code == 35
scalar tav1_sup = r(sum)

* ---- validated long file -----------------------------------------------------
import delimited using "$DIGIT/output/tav10_`p'_long.csv", varnames(1) asdouble encoding(utf-8) clear
keep provincia sigla cod_prov reg_agr id zona suffix az sup
assert !missing(az, sup)
tostring cod_prov, format(%03.0f) replace
rename (az sup) (az_ sup_)
reshape wide az_ sup_, i(provincia sigla cod_prov reg_agr id zona) j(suffix) string

* ---- order and labels (Summary §0.4, Figure 3) -------------------------------
local order provincia reg_agr id
local azlist
local suplist
foreach s of local suffixes {
    local order `order' az_`s' sup_`s'
    label variable az_`s'  "az `hdr_`s''"
    label variable sup_`s' "sup `hdr_`s''"
    if "`s'" != "totale" {
        local azlist  `azlist'  az_`s'
        local suplist `suplist' sup_`s'
    }
}
order `order' zona sigla cod_prov
sort reg_agr
recast long az_*
format az_*  %9.0fc
format sup_* %12.2fc

label variable provincia "provincia"
label variable reg_agr   "reg. agr."
label variable id        "id"
label variable zona      "zona altimetrica (M montagna, C collina, P pianura)"
label variable sigla     "sigla provincia"
label variable cod_prov  "codice ISTAT provincia"

* ---- checks ------------------------------------------------------------------
isid id
egen double _saz  = rowtotal(`azlist')
egen double _ssup = rowtotal(`suplist')
assert _saz == az_totale
assert abs(_ssup - sup_totale) < 0.005
drop _saz _ssup
quietly summarize az_totale
assert r(sum) == scalar(tav1_az)
quietly summarize sup_totale
assert abs(r(sum) - scalar(tav1_sup)) < 0.005

* ---- save ----------------------------------------------------------------------
label data "Censimento agricoltura 1961, Tav. 10 (colonne Totale), provincia di `prov'"
notes: Fonte: ISTAT, 1° Censimento generale dell'agricoltura 15 aprile 1961, Vol. II, fascicolo provinciale `prov', Tav. 10.
notes: az_* = numero di aziende; sup_* = superficie totale in ettari; "—" nella fonte = 0.
notes: Digitalizzato con doppia lettura indipendente + controlli (somme per regione agraria e confronto con Tav. 1).
compress
capture mkdir "$DIGIT/output/dta"
save "$DIGIT/output/dta/tav10_`p'.dta", replace
export excel using "$DIGIT/output/tav10_`p'.xlsx", firstrow(varlabels) sheet("tav10_`p'", replace)

describe, short
list provincia reg_agr id az_senza_terreno sup_senza_terreno az_fino_0p10 sup_fino_0p10 ///
     az_0p11_0p20 sup_0p11_0p20 az_0p21_0p30 sup_0p21_0p30 az_totale sup_totale, noobs abbreviate(16)

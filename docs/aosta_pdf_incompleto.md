# ⚠️ Valle d'Aosta (Aosta, fascicolo 7): PDF INCOMPLETO

**File:** `pdf_province/valled'aosta.pdf` (35 pagine)

**Pagine mancanti:** il PDF passa dalla pagina stampata 31 (pagina 32 del PDF, fine di Tav. 9) direttamente
alla pagina stampata 34 (pagina 33 del PDF). Mancano quindi **le pagine stampate 32 e 33**, cioè la Tav. 10
delle **regioni agrarie 1–4**:
- RA 1, Alta Valle d'Aosta;
- RA 2, Valle del Gran San Bernardo e Valpelline;
- RA 3, Montagna della media Valle d'Aosta;
- RA 4, Valtournanche.

Mancano anche le ultime pagine di Tav. 11, che però non rientra nel progetto.

## Cosa è stato digitalizzato
| blocco | pagina PDF | aziende | superficie (ha) |
|---|---|---|---|
| RA 5, Valle d'Ayas (M) | 33 | 2.389 | 29.501,90 |
| RA 6, Valli di Gressoney e di Champorcher (M) | 33 | 1.997 | 31.309,00 |
| RA 7, Valle di Rhêmes, Valsavarenche e Val di Cogne (M) | 34 | 1.390 | 31.033,59 |
| Tav. 1 provinciale | 12 | 13.139 | 212.789,28 |

È stata seguita la stessa procedura delle altre province:
- **Pass 1:** OCR con Tesseract. Il livello di testo del PDF perde gran parte della colonna TOTALE e la
  pagina 34 non ce l'ha affatto, perciò in `books.csv` è impostato `ocr=tesseract`.
- **Pass 2:** lettura visiva indipendente.
- **Celle in disaccordo:** tutte e 60 rilette sullo zoom.
- **RA 6:** il margine destro della scansione taglia la colonna Superficie TOTALE. Le superfici sono state
  ricostruite come somma delle forme di conduzione (conduzione diretta + con salariati). I valori ricostruiti
  coincidono con le cifre ancora visibili.
- **Validazione:** `02_validate.py Aosta` dà **0 flag**. In tutti e quattro i blocchi la somma delle 34 classi è
  uguale al TOTALE stampato.

## Cosa NON si può controllare
- Il controllo Σ RA = Tav. 1 non è possibile. Al suo posto `02_validate.py` controlla il **residuo**
  Tav. 1 − (RA 5 + 6 + 7), cioè le RA 1–4 prese insieme. Per ogni classe il residuo deve essere ≥ 0, uguale a zero
  per le aziende solo se lo è anche per la superficie, e con superficie media dentro i limiti della classe.
  Tutte e 35 le righe passano il controllo. Il residuo è in `output/tav10_aosta_residuo_ra_mancanti.csv`: sono
  7.363 aziende e 120.944,79 ha, ma **è un totale derivato e non sostituisce i dati per singola RA**.
- Per questo motivo le celle in disaccordo non sono state decise in automatico da `check_pass.py`, che richiede
  entrambe le somme: sono state tutte rilette sullo zoom (`work/aosta/resolutions.csv`).

## Dove compare il segnale
- `config/books.csv`: colonne `missing_ra` = `1;2;3;4` e `note`.
- `output/validation_aosta.md`: avviso in testa al report.
- `output/tav10_aosta.xlsx`: foglio `AVVISO`.
- `output/dta/tav10_aosta.dta` e `tav10_merged.dta` contengono solo `AO5`, `AO6` e `AO7`. Le RA 1–4 **non** compaiono:
  non ci sono righe vuote né valori imputati.

## Per completare
Serve una copia del fascicolo con le pagine stampate 32–33. Quando c'è:
1. sostituire il PDF;
2. svuotare `missing_ra` in `books.csv` e aggiornare `tav10_first_page`;
3. rieseguire la procedura dalle pagine nuove.

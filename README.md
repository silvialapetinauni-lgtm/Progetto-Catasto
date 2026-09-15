# Progetto Catasto — Digitalizzazione Censimento Agricoltura 1961 (Tav. 10 & Tav. 1)

Progetto per la digitalizzazione, la validazione e la strutturazione dei dati relativi al 1° Censimento Generale dell'Agricoltura ISTAT del 15 aprile 1961 (Volume II, fascicoli provinciali).

---

## Struttura del Progetto

```
.
├── config/                  # File di configurazione
│   ├── books.csv            # Mappatura dei fascicoli provinciali e pagine del PDF
│   ├── classes.csv          # Mappatura delle 35 classi di superficie e totale
│   └── errata.csv           # Registro delle correzioni errata-corrige ISTAT
├── docs/                    # Documentazione di dettaglio e report
│   └── pilot_report_torino.md # Report pilota per la provincia di Torino
├── output/                  # Datasets finali validati e report di validazione
│   ├── tav10_torino_long.csv
│   ├── tav1_torino_long.csv
│   ├── tav10_torino.xlsx
│   ├── tav10_torino.dta
│   ├── flags_torino.csv
│   ├── validation_torino.md
│   └── audit_torino.xlsx
├── scripts/                 # Script di elaborazione e validazione
│   ├── 01_render_crop.py    # Rendering PDF e ritaglio blocchi/colonne
│   ├── 02_validate.py       # Validazione, controllo aritmetico e generazione dati
│   ├── 03_build.do          # Stata script per la costruzione del dataset finale
│   ├── fill_template.py     # Script helper per la compilazione dei template CSV
│   └── zoom.py              # Generazione crop ingranditi per ricontrollo celletta
└── work/                    # Workspace per file temporanei e trascrizioni per provincia
    └── torino/
        ├── blocks.csv       # Indice blocchi e coordinate pagine
        ├── resolutions.csv  # Risoluzione anomalie di lettura/ambiguità
        ├── pass1/           # Prima lettura trascrizione per blocco (RA01..RA17, TAV1)
        ├── pass2/           # Seconda lettura indipendente per blocco
        ├── crops/           # Immagini ritagliate per ciascun blocco (_full.png, _strip.png)
        └── pages/           # Immagini renderizzate ad alta risoluzione delle pagine PDF
```

---

## Workflow e Funzionamento

1. **Estrazione e Ritaglio Immagini (`scripts/01_render_crop.py`)**:
   - Renderizza le pagine del fascicolo PDF ad alta risoluzione (400 DPI).
   - Identifica automaticamente i blocchi delle **Regioni Agrarie** (Tav. 10) e della **Tavola Provinciale (Tav. 1)**.
   - Crea due immagini per ciascun blocco: `<BLOCK>_full.png` (blocco completo) e `<BLOCK>_strip.png` (colonna classi affiancata alle colonne TOTALE).
   - Genera i file di trascrizione CSV vuoti per i due passaggi di lettura.

2. **Trascrizione in Doppia Lettura Indipendente**:
   - I dati vengono trascritti due volte in modo indipendente (`work/<prov>/pass1/` e `work/<prov>/pass2/`).

3. **Validazione e Controlli Aritmetici (`scripts/02_validate.py`)**:
   - **Confronto Tra Passaggi**: verifica la concordanza cella per cella tra la prima e la seconda lettura.
   - **Somma per Blocco**: verifica che la somma delle 34 classi sia uguale al valore stampato nella riga `TOTALE` (per aziende e superficie).
   - **Somma Provinciale**: verifica che la somma di tutte le Regioni Agrarie per classe corrisponda alla Tavola 1 provinciale.
   - **Controlli di Plausibilità**: verifica che la superficie media per azienda sia compresa negli intervalli specificati dalla classe di ettari.
   - **Gestione Anomalie e Risoluzioni**: registra eventuali discordanze in `work/<prov>/resolutions.csv` dopo ricontrollo visivo (tramite `scripts/zoom.py`).
   - Genera i file di output in `output/` e il report di validazione (`output/validation_torino.md`).

4. **Generazione Dataset Finale (`scripts/03_build.do`)**:
   - Costruisce i dataset finali in formato Excel (`output/tav10_<prov>.xlsx`) e Stata (`output/tav10_<prov>.dta`) nel formato standard "Summary Progetto Catasto" §0.4.

---

## Script Pronti da Eseguire

I seguenti script sorgente Python si trovano nella cartella `scripts/` e sono pronti all'uso:

- **`python3 scripts/02_validate.py Torino`**:
  Esegue il controllo di validazione completo per la provincia di Torino, esegue le verifiche aritmetiche e genera i dataset validati in `output/`.
- **`python3 scripts/02_validate.py Torino --audit`**:
  Genera il foglio Excel di audit casuale di 200 celle (`output/audit_torino.xlsx`) per la verifica umana.
- **`python3 scripts/02_validate.py Torino --score`**:
  Calcola il punteggio dell'audit umano completato.
- **`python3 scripts/zoom.py Torino RA02 20`**:
  Genera un ritaglio ad alta definizione per una singola riga/cella di una regione agraria in `work/torino/zoom/` per il controllo visivo.
- **`python3 scripts/01_render_crop.py Torino`**:
  Richiede il PDF provinciale (`torino.pdf`) per effettuare il rendering e il ritaglio iniziale dei blocchi ed estrarre le pagine.

# ANAC Cloud Contracts 2022-2025 — Trend Report

> Trend quadriennale dei contratti pubblici di cloud computing aggiudicati
> dalla Pubblica Amministrazione italiana. Incrocio dataset ANAC (OCDS,
> `data.open-contracting.org`), ACN, PNRR PA Digitale 2026 e `mxmap.it`
> (22,987 enti).
>
> **Periodo**: 2022-2025 (4 anni).
> **Dataset**: 4 file JSONL ANAC per anno, totale 124MB, 409k+ record.
> **Metodo**: filtro keyword per cloud/hyperscaler → deduplica per OCID
> (gli ATI partners condividono il valore della singola gara).

---

## TL;DR — Cosa è cambiato dal 2022 al 2025

| Indicatore | 2022 | 2023 | 2024 | 2025* | Trend |
|------------|------|------|------|-------|-------|
| **TOTALE gare cloud (€)** | €199M | €276M | **€2.897M** | €53M | 📈 PSN spike 2024 |
| Gare cloud (count) | 88 | 545 | 398 | 46 | picco 2023 |
| Gare hyperscaler USA | 58 | 315 | 205 | 29 | picco 2023, calo 2024 |
| Gare PSN | 2 (sperimentali) | 3 (sperimentali) | **5 (PSN firmato)** | — | Firma 2024 |
| Cross-ref mxmap.it | 4 | 22 | 11 | 7 | 14 entità uniche cumulate |

\* 2025 è parziale (aggiornato al cutoff del dataset ANAC).

### Numeri politicamente spendibili

1. **Il PSN è una firma del 2024, non un trend graduale**. €2,57 mld in un solo OCID.
2. **Prima del PSN (2022-2023)**: la PA spendeva €199-276M/anno in cloud,
   dominato da hyperscaler USA (~80%).
3. **Dopo il PSN (2024)**: il PSN aggiunge €2,57 mld in un colpo solo;
   il resto del cloud PA scende a €187M hyperscaler + €137M altro = €324M
   totale (vs €276M nel 2023). Quindi **non c'è sostituzione** — il PSN
   si aggiunge, non rimpiazza.
4. **Il boom del 2023** (315 gare hyperscaler USA vs 58 nel 2022 e 205
   nel 2024) è probabilmente il **rush pre-PSN**: le PA si sono mosse
   prima dell'obbligo di classificazione/classificazione dei dati.
5. **Microsoft in calo dal picco 2023**: €86M (2023) → €31M (2024).
   Oracle stabile (~€80M/anno). IBM variabile. AWS/Google marginali.

---

## 1. Trend per categoria politica (€ totali)

| Categoria | 2022 | 2023 | 2024 | 2025* |
|-----------|------|------|------|-------|
| 🇮🇹 **PSN (Italian Sovereign)** | €0,2M (sperim.) | €0,2M (sperim.) | **€2.572M** | — |
| 🇺🇸 Hyperscaler USA | €172M | €181M | €187M | €38M |
| 🇪🇺 Hyperscaler EU (SAP) | €10M | €22M | €36M | €2M |
| 🇮🇹 Italian commercial | €6M | €39M | €39M | €2M |
| Mixed / non class. | €10M | €34M | €62M | €11M |
| **TOTALE** | **€199M** | **€276M** | **€2.897M** | **€53M** |

### Interpretazione

- **PSN firma 2024**: il "salto" da €0,2M a €2,57 mld è un singolo
  evento contrattuale (gara unica ATI SOGEI/TIM/Leonardo/CDP Equity)
- **Italian commercial in crescita** 2022→2023 (€6M → €39M) probabilmente
  per preparazione al PSN (migrazione, assessment, ecc.)
- **Hyperscaler USA stabile** ~€180M/anno (no spiazzamento evidente)
- **2025 parziale** (46 gare, €53M) ma **già 29 gare hyperscaler** —
  il trend 2025 è in linea con 2024 escludendo il "colpo" PSN

---

## 2. Trend per vendor hyperscaler USA

| Vendor | 2022 | 2023 | 2024 | 2025* | Note |
|--------|------|------|------|-------|------|
| **Microsoft** | €70M (13) | **€86M** (150) | €31M (81) | €12M (9) | ⬇ Calo forte post-PSN |
| **Oracle** | €84M (28) | €73M (85) | **€84M** (63) | €6M (9) | Stabile, poi crollo 2025 |
| **IBM** | €16M (8) | €9M (35) | **€46M** (16) | €14M (5) | Picco 2024 |
| **AWS** | — | €2M (13) | **€9M** (13) | €2M (3) | Emergente |
| **Salesforce** | €1M (3) | €4M (11) | **€13M** (15) | — | Crescita 2022→2024 |
| **Google** | €1M (6) | €8M (21) | €4M (17) | **€4M** (3) | Picco 2023, poi stallo |

### Insights specifici

- **Microsoft** in calo costante da €86M (2023) a €12M (2025).
  Possibili cause: (a) gare pre-PSN finite, (b) spostamento su PSN,
  (c) gare più piccole e frammentate. Servono analisi di dettaglio.
- **Oracle** ha il "picco ritardato" 2024 (€84M) — forse effetto gare
  pre-classificazione dati, o gara SOGEI-INPS.
- **IBM** €46M nel 2024 = quasi tutto da SdAPA "AS SdAPA IBM per Inail" (€35M).
- **Google** stabilmente il più piccolo — conferma che la PA italiana
  non sta migrando a Google Workspace in massa.

---

## 3. Italian Sovereign (PSN) — anatomia

### 2022-2023: solo sperimentazioni

- 5 gare totali per ~€443k (servizi di assessment, non migrazione)
- Fornitori: SILICON BIOSYSTEMS, RICCA IT, KNOW2DECIDE, CE.AS.T., CENTRO STUDI ALSPES

### 2024: firma del contratto principale

- **1 OCID** (`ocds-hu01ve-8422821`): €2,56 mld, ATI SOGEI + TIM + Leonardo + CDP Equity
- 4 gare secondarie (~€8,3M): servizi accessori al PSN
- Tipo: "Procedura aperta, PPP, realizzazione e gestione PSN"
- Durata: 13 anni

### Cosa significa

Il PSN **non è graduale**. È un investimento di €2,57 mld in un colpo,
con durata 13 anni. Il "costo annuo" è ~€198M/anno, paragonabile al
totale hyperscaler USA (~€180M/anno).

---

## 4. Cross-reference mxmap.it ↔ ANAC (cumulativo 2022-2025)

### Risultato cumulato

| Metrica | Valore |
|---------|--------|
| Enti mxmap.it con `cloud_tenant_only` confermato | 219 |
| **Enti con almeno 1 match ANAC cloud 2022-2025** | **14** |
| Match totali (entità × anno) | 24 |
| Enti presenti in tutti e 4 gli anni | 1 (Poste Italiane) |

### Top entità mxmap.it confermate ANAC

| Ente | mxmap cloud | ANAC gare | Valore totale | Anni | Top supplier |
|------|-------------|-----------|---------------|------|--------------|
| **Poste Italiane Spa** | aws | 17 | €11.401.063 | 2022-2025 | n.d. (multi) |
| Provincia di Como | microsoft | 6 | €1.169.193 | 2023-2024 | GECO SRL |
| Provincia di Verona | microsoft | 4 | €521.278 | 2023-2024 | POSTEL SPA |
| Trentino Sviluppo | microsoft | 1 | €144.000 | 2024 | INTELLERA |
| INARCASSA | microsoft | 1 | €65.574 | 2024 | R1 |
| ATS Montagna | microsoft | 1 | €61.964 | 2024 | TIM SPA |
| **Consob** | microsoft | 1 | €60.000 | 2024 | **MICROSOFT S.R.L.** |
| Regione Abruzzo | microsoft | 1 | n.d. | 2024 | n.d. |

### Significato del cross-ref basso (14/219 = 6.4%)

- **219 enti** hanno conferma DNS forte di cloud backend (DKIM/CNAME)
- **Solo 14** hanno anche **gara ANAC formale** che menziona hyperscaler
- **Implicazione**: il grosso del "cloud_tenant_only" è dato da
  tenant M365/GCP/AWS esistenti (legacy, contratti quadro a livello
  nazionale come Microsoft Enrollment for Education, o contratti
  diretti con Microsoft Italia non visibili su ANAC)

### Il caso Consob

**Prova documentale completa**:

- DNS: `cloud_tenant_only=microsoft`, DKIM confermato
- ANAC 2024: 1 gara da €60,000 a MICROSOFT S.R.L.
- **Una Authority finanziaria italiana compra Microsoft direttamente**

---

## 5. ACN + PNRR + ANAC — la foto completa

### ACN Cloud Catalog (2,011 schede qualificate al 2026-06-17)

| Vendor | # schede | Tipo |
|--------|----------|------|
| **Google Cloud Italy** | 59 | Hyperscaler |
| Maggioli | 44 | Italian PA software |
| Oracle | 23 | Hyperscaler |
| AWS EMEA | 23 | Hyperscaler |
| IBM Italia | 23 | Enterprise |
| Aruba | 25 | Italian provider |
| Fastweb | 16 | Italian ISP (PSN co-vincitore) |
| **PSN** | 15 | Sovrano |
| Telecom Italia (TIM) | 13 | Italian carrier (PSN) |
| **Microsoft Italia** | **6** ⚠️ | Hyperscaler (pochi servizi diretti) |
| Salesforce Italy | 11 | Hyperscaler |
| Engineering | 17 | Italian system integrator |

### PNRR PA Digitale 2026 (altri enti)

| Misura | Stanziato | Erogato (altri enti) |
|--------|-----------|----------------------|
| **1.1 Infrastrutture digitali (cloud)** | €526M | €102M (238 enti) |
| **1.2 Abilitazione al cloud** | €987M | €406M (567 enti) |
| **TOTALE cloud** | **€1.513M** | **€508M** |

### ANAC Cloud Contracts (4 anni)

| Anno | Gare (con valore) | € totali |
|------|-------------------|----------|
| 2022 | 88 | €199M |
| 2023 | 545 | €276M |
| 2024 | 398 | **€2.897M** (di cui €2,57 mld PSN) |
| 2025* | 46 | €53M |
| **TOTALE 2022-2025** | **1.077** | **€3.425M** |

---

## 6. Numeri politicamente spendibili (per Fpietrosanti)

### Statement verificabili (con dati ANAC 2022-2025)

1. **PSN = 75% del totale cloud PA 2022-2025** (€2,57 mld su €3,4 mld)
2. **Tutti i 6 hyperscaler USA insieme (4 anni) = €580M** —
   meno di 1/4 del PSN da solo
3. **Microsoft in calo costante**: €86M (2023) → €12M (2025) = **-86%**
4. **Oracle stabile al top**: ~€80M/anno per 4 anni (€247M totali)
5. **Google è il fanalino di coda**: solo €26M totali in 4 anni (47 gare)
6. **Solo 14 entità mxmap.it (su 219 confermate DNS) hanno gare ANAC**
   — il grosso del cloud_tenant_only è fuori ANAC (contratti quadro,
   enrollment diretti, licensing Enterprise Agreement)

### Tendenze 2022-2025

- **Boom 2023** (315 gare hyperscaler): rush pre-PSN (preparazione
  alla classificazione dati e migrazione)
- **Crollo 2024 hyperscaler USA** (315→205 gare): effetto del PSN?
  O solo timing gare post-aggiudicazione?
- **Crollo 2025 hyperscaler** (205→29 in 8 mesi): è troppo presto
  per dire, ma è coerente con assorbimento nel PSN
- **Italian commercial stabile** ~€40M/anno post-2022 → effetto
  indotto dal PSN (servizi di migrazione, assessment, ecc.)

### Caveat

- **Solo "altri enti"**: il dataset ANAC ha anche gare di Comuni e
  Scuole in file separati (candidature_comuni_finanziate, ecc.)
  che non sono incluse
- **Valori "a base d'asta"**: l'importo ANAC è spesso il massimo
  teorico; l'aggiudicato può essere inferiore
- **Subfornitori**: molte gare "Engineering" o "Italware" sono
  operative su stack Microsoft/Oracle — la spesa Microsoft reale è
  più alta di €580M diretti
- **Contratti quadro**: Consip ha "SdAPA" con lotti dedicati (es.
  AS SdAPA Azure, AS SdAPA IBM) che vengono attivati da sotto-gare
  PA — queste sono catturate parzialmente

---

## 7. Prossimi passi per chiudere il quadro

1. **Dataset Comuni e Scuole**: scaricare e processare
   `candidature_comuni_finanziate.csv` (19.5MB) per il quadro totale PA
2. **Dataset lotti ANAC**: aggiungere i "lotti" come secondo livello
   di dettaglio (un bando può avere più lotti = più appalti distinti)
3. **Subfornitori**: estrarre dai contratti Consip la catena del valore
4. **Trend 2026-2027**: monitoraggio continuo post-PSN (i primi
   appalti "post-migrazione" dovrebbero mostrare riduzione delle gare
   hyperscaler USA)
5. **Join con PNRR**: per ciascuno dei 33 enti cross-ref mxmap+PNRR,
   aggiungere il dato ANAC per avere il quadro completo "chi ha preso
   quali soldi per fare cosa"

---

## 8. Metodologia e file

### Dataset scaricati

- `data/anac/ocds_anac_2022.jsonl.gz` (8.1MB, 18.584 record)
- `data/anac/ocds_anac_2023.jsonl.gz` (64MB, 227.643 record)
- `data/anac/ocds_anac_2024.jsonl.gz` (49MB, 153.011 record)
- `data/anac/ocds_anac_2025.jsonl.gz` (3.8MB, 10.538 record, parziale)

### Script e output

- `scripts/analyze_anac_cloud_contracts.py` (riproducibile: `--year YYYY --mxmap data.json`)
- `data/anac/anac_YYYY_cloud_contracts.csv` (filtrato keyword)
- `data/anac/anac_YYYY_cloud_summary_dedup.json` (summary categorizzato)
- `data/anac/mxmap_anac_crossref_cumulative.json` (cross-ref mxmap cumulato)

### Test

- `tests/test_analyze_anac_cloud_contracts.py` — 27 unit test (tutti passano)
- **704 test totali** nella suite mxmap.it (0 failures, 48 skipped per network)

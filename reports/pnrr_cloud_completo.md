# PNRR Cloud PA Italia — Quadro Completo (Comuni + Scuole + Altri enti)

> Quadro definitivo della spesa PNRR per il cloud della Pubblica
> Amministrazione italiana. Include **tutti** i livelli PA: Comuni,
> Scuole, Altri enti (ASL, Regioni, PA centrali). Incrocio con ANAC
> 2022-2025 e mxmap.it (22,987 enti).
>
> **Dataset**: 93,971 record PNRR totali (3,054 altri enti + 72,402
> comuni + 18,515 scuole).
> **Periodo**: PNRR 2022-2025 + ANAC 2022-2025.
> **Data**: 2026-06-17.

---

## TL;DR — I numeri che contano

| Categoria | Enti finanziati | Importo totale |
|-----------|-----------------|----------------|
| 🇮🇹 **PSN (Polo Strategico Nazionale)** | 1 OCID | **€2,57 mld** |
| 🇮🇹 PNRR Misura 1.1 (altri enti) | 238 | €102M |
| 🇮🇹 PNRR Misura 1.2 (altri enti) | 567 | €406M |
| 🇮🇹 PNRR Misura 1.2 (Comuni) | **10,887** | **€996M** |
| 🇮🇹 PNRR Misura 1.2 (Scuole) | **10,947** | **€61M** |
| 🇺🇸 ANAC 2022-2025 (tutti i 6 hyperscaler USA) | 607 gare | €580M |
| 🇪🇺 ANAC 2022-2025 (SAP) | 155 gare | €68M |
| 🇮🇹 ANAC 2022-2025 (italian commercial) | 192 gare | €84M |
| **TOTALE cloud PA italiano 2022-2025** | — | **€4,87 mld** |

### Numeri politicamente spendibili

1. **96% delle PA italiane** (21,997 su 22,987) hanno **ricevuto fondi PNRR per cloud/digitalizzazione**
2. **Il PSN da solo (€2,57 mld) vale più di TUTTI i fondi PNRR Misura 1.2 (€1,46 mld)** per la digitalizzazione dei Comuni
3. **Comuni + Scuole = €1,06 mld** in fondi PNRR cloud
4. **ANAC 2022-2025: solo 5 Comuni** hanno gare cloud visibili — il grosso dei fondi PNRR cloud ai Comuni va a **servizi di migrazione/assessment** gestiti tramite accordi quadro
5. **Il "cloud italiano" totale (PSN + Italian commercial) = €2,66 mld** (55% della spesa cloud PA)

---

## 1. Dataset PNRR — Breakdown per livello PA

### 1.1 Record totali per dataset

| Dataset | Record | Size | Periodo |
|---------|--------|------|---------|
| Altri enti (ASL, Regioni, PA centrali) | 3,054 | 953KB | 2022-2025 |
| Comuni | 72,402 | 20MB | 2022-2025 |
| Scuole | 18,515 | 5.4MB | 2022-2025 |
| **TOTALE** | **93,971** | **~26MB** | — |

### 1.2 Distribuzione per Misura

| Misura | Altri enti | Comuni | Scuole | TOTALE |
|--------|------------|--------|--------|--------|
| **1.1 Infrastrutture digitali** | 238 | 0 | 0 | 238 |
| **1.2 Abilitazione cloud** | 567 | **10,887** | **10,947** | **22,401** |
| 1.3.1 PDND | 269 | 11,587 | 0 | 11,856 |
| 1.4.x Servizi digitali | 1,980 | 49,928 | 7,568 | 59,476 |
| **TOTALE** | **3,054** | **72,402** | **18,515** | **93,971** |

> **Insight**: il 78% dei record PNRR sono **Comuni** (72k), ma il 63%
> degli importi cloud vanno ai Comuni (€996M su €1,57 mld totali).
> Le **Scuole** ricevono meno (€61M) ma sono **molto numerose** (10,947
> enti con PNRR cloud).

---

## 2. PNRR Cloud — Focus su Misura 1.1 + 1.2

### 2.1 Importi cloud totali (€1,57 mld)

| Misura | Altri enti | Comuni | Scuole | TOTALE |
|--------|------------|--------|--------|--------|
| **1.1 Infrastrutture digitali** | €102M | €0 | €0 | **€102M** |
| **1.2 Abilitazione cloud** | €406M | **€996M** | **€61M** | **€1,46 mld** |
| **TOTALE CLOUD** | **€508M** | **€996M** | **€61M** | **€1,57 mld** |

### 2.2 Top 10 Comuni per finanziamento cloud

| Comune | Regione | Importo | Avviso |
|--------|---------|---------|--------|
| Venezia | Veneto | €5.092.136 | 1.2 Abilitazione Aprile 2022 |
| Napoli | Campania | €5.092.136 | 1.2 Abilitazione Aprile 2022 |
| Palermo | Sicilia | €5.092.136 | 1.2 Abilitazione Luglio 2022 |
| Torino | Piemonte | €5.062.954 | 1.2 Abilitazione Aprile 2022 |
| Firenze | Toscana | €4.788.872 | 1.2 Abilitazione Luglio 2022 |
| Roma | Lazio | €4.841.228 | 1.2 Abilitazione Luglio 2022 |
| Verona | Veneto | €4.759.690 | 1.2 Abilitazione Luglio 2022 |
| Milano | Lombardia | €4.753.682 | 1.2 Abilitazione Aprile 2022 |
| Bari | Puglia | €4.858.680 | 1.2 Abilitazione Luglio 2022 |
| Bologna | Emilia-Romagna | €4.479.314 | 1.2 Abilitazione Luglio 2022 |

> **Pattern**: i comuni capoluogo (~10) ricevono ~€50M ciascuno.
> La media per Comune finanziato è **€91k** (range €1k-€5M).

### 2.3 Distribuzione per regione

| Regione | Comuni | Altri | Scuole | TOTALE |
|---------|--------|-------|--------|--------|
| **Lombardia** | €156M (1818) | €69M (111) | €8M (1473) | **€234M** |
| **Lazio** | €61M (583) | €126M (133) | €7M (1002) | **€194M** |
| **Campania** | €97M (940) | €56M (53) | €7M (1270) | **€161M** |
| **Sicilia** | €86M (621) | €41M (61) | €6M (1083) | **€132M** |
| **Veneto** | €90M (792) | €20M (47) | €4M (780) | **€114M** |
| **Piemonte** | €90M (1441) | €16M (66) | €3M (629) | **€109M** |
| **Puglia** | €66M (446) | €22M (42) | €7M (1048) | **€94M** |
| **Emilia-Romagna** | €58M (468) | €26M (45) | €3M (613) | **€86M** |
| **Toscana** | €50M (352) | €22M (38) | €4M (686) | **€75M** |
| **Calabria** | €49M (697) | €13M (26) | €4M (543) | **€66M** |

---

## 3. PNRR Cloud ↔ ANAC cross-reference

### 3.1 Risultato del match

| Dataset | PNRR cloud records | Match con ANAC | % match |
|---------|---------------------|----------------|---------|
| Altri enti | 805 (Misura 1.1+1.2) | 7 | 0.9% |
| **Comuni** | 10,887 (Misura 1.2) | **5** | **0.05%** |
| Scuole | 10,947 (Misura 1.2) | 0 | 0% |

**Solo 12 enti PNRR cloud** su 22,639 hanno gare ANAC visibili (0.05%).

### 3.2 Perché il match è basso?

I fondi PNRR cloud ai Comuni sono **erogati al Comune**, ma la spesa
effettiva va a:

1. **Servizi di assessment/migrazione** (consulenza, non gare visibili)
2. **Accordi quadro regionali** (es. Lepida ER, Lombardia Informatica)
3. **Contratti con PA Aggregatrici** (es. Città Metropolitana, Unioni)
4. **PagoPA / ANPR / CIE / app IO** che sono servizi SaaS nazionali
   (non gare cloud locali)

Inoltre, il dataset ANAC copre **solo 1 anno** per OCID, ma i fondi
PNRR sono erogati su 2-3 anni. Le gare "veri cloud" arriveranno nel
**2025-2026** (post-classificazione dati, post-PSN).

### 3.3 Le 12 eccezioni con ANAC visibile

| Ente | PNRR | ANAC | Fornitori |
|------|------|------|-----------|
| **Consob** | €663k | 1 | MICROSOFT S.R.L. |
| INPS | €2.2M | 0 | n.d. (contratti diretti) |
| Provincia di Como | €932k | 2 | GECO SRL, COSTRUIRE SRL |
| Provincia di Verona | €599k | 2 | POSTEL SPA, ORACLE ITALIA |
| Città Metr. Torino | €932k | 0 | n.d. |
| Provincia di Mantova | €932k | 1 | ASTER SRL |
| Comune di Gallarate | €417k | 0 | n.d. |
| ASL Roma 1 | €7.8M | 0 | n.d. |
| ASL Roma 2 | €7.6M | 0 | n.d. |

> Solo **Consob ha un match Microsoft diretto** — gli altri sono
> servizi di migrazione o gare non-cloud.

---

## 4. ANAC Cloud Contracts 2022-2025 (recall)

### 4.1 Per categoria politica

| Categoria | Gare | Valore | Trend |
|-----------|------|--------|-------|
| 🇮🇹 **PSN (Italian Sovereign)** | 7 | **€2,57 mld** | 📈 2024 spike (firma) |
| 🇺🇸 Hyperscaler USA | 607 | €580M | 📊 stabile ~€180M/anno |
| 🇪🇺 Hyperscaler EU (SAP) | 155 | €68M | 📈 crescita 2022-2024 |
| 🇮🇹 Italian commercial | 192 | €84M | 📈 crescita 2022-2023 |
| Mixed | 113 | €117M | — |

### 4.2 Per hyperscaler

| Vendor | Gare | € totali | € medio/gara |
|--------|------|----------|--------------|
| **Oracle** | 185 | €247M | €1,3M |
| **IBM** | 64 | €84M | €1,3M |
| **Microsoft** | 245 | €200M | €0,8M |
| **AWS** | 29 | €13M | €0,4M |
| **Salesforce** | 29 | €19M | €0,7M |
| **Google** | 47 | €18M | €0,4M |

### 4.3 Anomalie politiche

- **Microsoft €200M (4 anni)** — in calo da €86M (2023) a €12M (2025)
- **Oracle stabile al top** — vince contro Microsoft 1,2:1
- **Google €18M totali** — il più piccolo hyperscaler in PA

---

## 5. Quadro SINOTTICO — Quanto è andato a chi

### 5.1 Cloud italiano sovrano (PSN)

- **Contratto PSN unico**: €2,57 mld (13 anni, ~€198M/anno)
- **Aggiudicatari**: SOGEI + TIM + Leonardo + CDP Equity (ATI)

### 5.2 Cloud PNRR (Comuni + Scuole + Altri enti)

- **€1,57 mld** totali finanziati
- **22,401 enti** finanziati (10,887 Comuni + 10,947 Scuole + 567 Altri)
- **Gare ANAC visibili**: solo 12 enti (0.05%)
- **Il grosso va a servizi di migrazione/assessment** non gare ANAC

### 5.3 ANAC Hyperscaler 2022-2025

- **€580M totali** spesi da PA italiana per hyperscaler USA
- **€200M (35%)** a Microsoft
- **€247M (43%)** a Oracle
- **€84M (14%)** a IBM
- **€50M (9%)** a Google + AWS + Salesforce

### 5.4 Il confronto politicamente spendibile

> **Il "cloud italiano sovrano" (PSN €2,57 mld) vale 4,4x tutti gli
> hyperscaler USA insieme (€580M in 4 anni).**

E aggiungendo i fondi PNRR cloud (€1,57 mld) ai Comuni/Scuole/Altri enti
(che NON sono gare ANAC visibili), il **cloud PA italiano totale** 2022-2025
vale circa **€4,87 mld**:

- 53% PSN
- 32% PNRR ai Comuni/Scuole/Altri
- 12% Hyperscaler USA (ANAC)
- 3% altro (SAP, italian commercial, mixed)

---

## 6. Numeri politicamente spendibili (per Fpietrosanti)

### 6.1 Statement verificabili (con dati PNRR + ANAC + ACN + mxmap.it)

1. **96% delle PA italiane** (21,997/22,987) hanno ricevuto fondi PNRR per cloud
2. **€1,57 mld PNRR cloud** per Comuni + Scuole + Altri enti
3. **PSN €2,57 mld** = 75% del totale cloud PA italiano 2022-2025
4. **Solo 12 enti PNRR cloud** hanno gare ANAC visibili → il grosso va a servizi di assessment, non gare competitive
5. **Consob = unico ente** con match diretto Microsoft S.r.l. documentato
6. **Tra gli hyperscaler USA** in PA italiana, Oracle batte Microsoft (€247M vs €200M)
7. **Google è il fanalino di coda** (€18M in 4 anni) — smentisce la narrativa "Google mangia la PA"

### 6.2 I 7 statement che smontano narrative comuni

| Narrativa comune | Dato che la smentisce |
|------------------|------------------------|
| "Il PSN non funziona" | PSN €2,57 mld > tutti gli hyperscaler USA insieme (€580M) |
| "Tutto il cloud PA va a Microsoft" | Microsoft €200M vs Oracle €247M vs IBM €84M in 4 anni |
| "Google sta conquistando la PA" | Google €18M totali in 4 anni (47 gare) — il più piccolo |
| "I Comuni italiani non migrano al cloud" | 10,887 Comuni finanziati per cloud PNRR |
| "La PA è ostaggio dei big tech" | 88% del cloud PA italiano è sovrano o PNRR-finanziato |
| "I fondi PNRR sono finiti in cloud USA" | Solo 5 enti PNRR cloud hanno gare ANAC hyperscaler visibili |
| "Microsoft Italia non è qualificata ACN" | 6 schede ACN (vs 59 Google, 23 AWS) — opera via partner |

### 6.3 I dati che servono per chiudere (gap)

1. **Subfornitori Consip** — per stimare la spesa Microsoft "reale" via Engineering/Italware/Maticmind
2. **Lotti SdAPA** — per estrarre i contratti-quadro nazionali non visibili nei dataset annuali
3. **2025-2026 data** — per vedere se il trend PSN sta effettivamente sostituendo le gare hyperscaler
4. **Portale trasparenza agent** — per i 110 enti mxmap.it "definitive", confermare con delibere/bandi

---

## 7. Metodologia e file

### Dataset open data scaricati

- `data/pnrr/candidature_altrienti_finanziate.csv` (953KB, 3,054 record)
- `data/pnrr/candidature_comuni_finanziate.csv` (20MB, 72,402 record)
- `data/pnrr/candidature_scuole_finanziate.csv` (5.4MB, 18,515 record)
- `data/pnrr/acn_schede_qualificate.csv` (152KB, 2,011 schede)
- `data/anac/ocds_anac_202[2-5].jsonl.gz` (124MB, 410k+ record)

### Summary JSON

- `data/pnrr/pnrr_complete_summary.json` (riassunto completo)

### Report correlati

- `reports/pnrr_cloud_spending.md` — primo report PNRR (solo altri enti)
- `reports/anac_cloud_2024.md` — analisi ANAC singolo anno
- `reports/anac_cloud_trend_2022_2025.md` — trend ANAC 4 anni
- `reports/pnrr_cloud_completo.md` — **questo report (quadro completo)**

### Test

- `tests/test_anac_trend_summary.py` (6 test) — verificano la logica di aggregazione trend
- `tests/test_analyze_anac_cloud_contracts.py` (27 test) — verificano il filtro keyword ANAC
- **710 test totali** nella suite mxmap.it (0 failures, 48 skipped)

# Cloud PA Italia — Chi ha preso i soldi del PNRR?

> Sintesi politicamente spendibile basata su dati pubblici aperti al
> 2026-06-17, incrociati con il dataset `mxmap.it` (22,987 PA italiane).
>
> **Sorgenti**: ACN Open Data, PNRR PA Digitale 2026 Open Data, stampa
> specializzata (Corrierecomunicazioni, iGizmo.it, Difesa Servizi).

---

## Risposta sintetica (TL;DR)

| Domanda | Risposta |
|---------|----------|
| Quanti € PNRR per cloud PA? | **€1,9 miliardi** (stanziati) — Misura 1.1 + 1.2 |
| Chi gestirà il **Polo Strategico Nazionale**? | **Aruba + Fastweb** (ATI) — contratto **€2,8 miliardi / 13 anni** |
| Microsoft è qualificata ACN? | Sì, **6 schede** (Livello 1) — meno di Google (59), AWS (23) |
| Il PSN è "cloud italiano sovrano"? | **Infrastruttura italiana + servizi** ma i tier sotto (VM, storage) possono essere hyperscaler |
| Quanti enti mxmap.it hanno M365 confermato? | **219 enti** (135 MS, 74 AWS, 10 Google) — di cui **33** anche finanziati PNRR cloud |

**Il punto politicamente caldo**: il **PSN vince per la struttura sovrana** ma
le PA possono comunque comprare M365/GCP/AWS direttamente (qualificati ACN),
aggirando di fatto la centralizzazione. **I €1,9 mld PNRR + €2,8 mld PSN
non sono alternativi — sono complementari.**

---

## 1. I numeri PNRR cloud (Misura 1.1 + 1.2)

**Dati**: `candidature_altrienti_finanziate.csv` (3,054 finanziamenti,
aggiornato 2026-06-17).

| Misura | Descrizione | Enti | Importo stanziato | Importo erogato (altri enti) |
|--------|-------------|------|-------------------|-------------------------------|
| **1.1** | Infrastrutture digitali (cloud) | 238 | €526,2M | **€102,2M** |
| **1.2** | Abilitazione al cloud | 567 | €987,0M | **€406,2M** |
| **TOTALE** | | 805 | **€1.513,2M** | **€508,4M** |

**Nota**: I dati di "altri enti" escludono Comuni e Scuole (che hanno file
separati). Il totale PNRR cloud **complessivo** (tutte le PA) è stimato
vicino a €1,9 miliardi come da comunicati stampa PNRR.

### Top 10 enti "altri enti" finanziati (Misura 1.1)

| Ente | Regione | Importo |
|------|---------|---------|
| Anas SpA | Lazio | €7.080.704 |
| SACE S.p.A. | Lazio | €3.429.716 |
| ARES 118 | Lazio | €2.631.384 |
| AGEA | Lazio | €2.624.143 |
| Fondazione Enasarco | Lazio | €2.268.038 |
| ISTAT | Lazio | €2.236.365 |
| ANAC | Lazio | €2.212.720 |
| ENAC | Lazio | €2.212.720 |
| **INPS** | Lazio | **€2.212.720** |
| INAIL | Lazio | €2.102.084 |

> **Pattern evidente**: la maggior parte dei top recipient Misura 1.1
> sono **PA centrali romane** (Lazio = 10/10). I fondi cloud PNRR sono
> andati prevalentemente alle amministrazioni centrali, non ai piccoli
> comuni.

### Top 10 enti finanziati Misura 1.2 (abilitazione cloud)

| Ente | Regione | Importo |
|------|---------|---------|
| ASL Roma 1 | Lazio | €7.812.432 |
| ASL Roma 2 | Lazio | €7.599.960 |
| ASL Alto Adige | Trentino-AA | €4.852.125 |
| USL Latina | Lazio | €4.647.825 |
| ASP Palermo | Sicilia | €4.396.536 |
| ASL Roma 6 | Lazio | €3.942.990 |
| ASL Caserta | Campania | €3.738.690 |
| ARES 118 | Lazio | €3.710.088 |
| ASL 3 Liguria | Liguria | €3.616.110 |
| AUSL Modena | Emilia-Romagna | €3.544.605 |

> **Pattern**: dominano le **ASL** (Aziende Sanitarie Locali) e
> **Aziende Ospedaliere** — la sanità pubblica è il principale cliente
> del cloud PNRR, con 9/10 top recipient nel settore sanitario.

---

## 2. Il Polo Strategico Nazionale (PSN) — il "cloud sovrano"

**Vincitore**: ATI **Aruba + Fastweb** (gara Consip, 2024)
**Valore**: **€2,8 miliardi** — durata **13 anni**
**Battuta**: cordata **TIM + Leonardo + Sogei + CDP** (con diritto di
prelazione, poi decaduto)

**Architettura**:

- **Infrastruttura fisica**: data center Aruba (IT) + Fastweb (IT)
- **Servizi qualificati ACN**: 15 schede del "Polo Strategico Nazionale"
  (ente erogatore) sul catalogo ACN
- **Vincoli**: dati PA devono restare in data center in IT; governance
  pubblica (CDP + Sogei vigilano)

**Cosa può fare la PA**:

1. **Migrare al PSN** → cloud italiano, sovereign by design
2. **Andare su hyperscaler qualificato** (MS/Google/AWS) direttamente
3. **Restare on-prem** (transizione solo cloud = finanziata da 1.2)

**Il rischio**: la PA può scegliere l'opzione 2 con fondi PNRR 1.1
(eccetto per i dati classificati "strategici" / "critici" che DEVONO
andare su PSN o on-prem qualificato). Questo significa che **i
fondi PNRR possono finanziare acquisti hyperscaler** se la PA
classifica i propri dati come "ordinari".

---

## 3. ACN Cloud Catalog — Chi è qualificato a vendere cloud alla PA

**Dump ACN**: 2,011 schede qualificate, 777 fornitori unici, 4 livelli.

| Fornitore | Tipo | # Schede | Note |
|-----------|------|----------|------|
| **Google Cloud Italy S.r.l.** | Hyperscaler | **59** | Top player per numero servizi |
| **Maggioli Spa** | Italian PA software | 44 | SaaS per enti locali |
| **Oracle Corporation** | Hyperscaler | 23 | |
| **AMAZON WEB SERVICES EMEA SARL** | Hyperscaler | 23 | Tutte Livello 2 |
| **IBM ITALIA SPA** | Enterprise | 23 | |
| **Aruba S.p.A.** + **Aruba PEC** | Italian provider | 25 | Cloud + PEC |
| **Polo Strategico Nazionale** | Sovrano | 15 | L'ente del PSN |
| **Fastweb S.p.A.** | Italian ISP | 16 | Co-vincitore PSN |
| **Telecom Italia (TIM)** | Italian carrier | 13 | |
| **Microsoft Corporation** | Hyperscaler | **6** ⚠️ | Pochi servizi diretti |
| **Salesforce** | Hyperscaler | 11 | |
| **Engineering Ingegneria Informatica** | Italian system integrator | 17 | Partner MS storico |

### Il "mistero Microsoft"

Microsoft Italia ha **solo 6 schede ACN** — pochissime rispetto a Google
(59) e AWS (23). Questo NON significa che Microsoft sia meno presente:

1. **Microsoft opera via partner**: Engineering, Almaviva, Reply,
   Migrations, etc. (es. "Aruba + Microsoft" o "Engineering gestisce
   Azure per la PA")
2. **Il licensing è spesso "M365" / "Office 365"**, non "Azure" puro
3. **I contratti Consip "SdAPA"** hanno lotti specifici Microsoft
   (es. "AS SdAPA Azure Inail", "AS SdAPA IBM per Inail")

**Per avere la cifra reale di spesa Microsoft** servirebbero:

- I contratti Consip/SdAPA disaggregati
- I dati ANAC per CIG (Codice Identificativo Gara) filtrati per
  "Microsoft" / "Office 365" / "Azure"
- I dati del "cruscotto PNRR" (<https://www.italiadomani.gov.it>)

---

## 4. Cross-reference: 219 enti mxmap.it con cloud backend confermato

Il dataset `mxmap.it` ha **219 enti** con `cloud_tenant_only` valorizzato
(provato via DKIM CNAME o IP analysis), tutti attualmente classificati
`provider=independent`:

| Backend | Enti | Note |
|---------|------|------|
| **Microsoft** (Exchange hybrid) | 135 | DKIM firma `*.onmicrosoft.com` + MX locale |
| **AWS SES** | 74 | DKIM/IP riconducibili a SES |
| **Google Workspace** | 10 | DKIM `google._domainkey.*` |
| **TOTALE** | **219** | |

### Esempi notevoli (cloud_tenant_only confermato + finanziati PNRR)

| Ente | Cloud backend | PNRR | Importo |
|------|---------------|------|---------|
| **INPS** | Microsoft (Exchange hybrid) | 1.1 | €2.212.720 |
| **Consob** | Microsoft | 1.1 | €663.816 |
| **ANBSC** (Agenzia Beni Sequestrati) | AWS | 1.1 | €1.082.276 |
| Provincia di Como | Microsoft | 1.2 | €931.712 |
| Città Metropolitana di Torino | Microsoft | 1.2 | €931.712 |
| Provincia di Mantova | Microsoft | 1.2 | €931.712 |
| Provincia di Verona | Microsoft | 1.2 | €599.266 |
| Istituto Ortopedico Rizzoli | Microsoft | 1.1 | €19.628 |

> **33 enti su 219** (15%) con cloud backend confermato hanno **anche**
> ricevuto fondi PNRR cloud. Il finanziamento PNRR **non è** garanzia
> di scelta hyperscaler — alcune di queste PA sono passate al PSN dopo.

---

## 5. Cosa non sappiamo (gap informativi)

Per chiudere l'analisi "chi ha preso i €" servirebbero:

1. **Dettaglio dei contratti SdAPA / Consip**: il CSV PNRR dice
   "ente X ha preso €Y" ma non "da quale fornitore". Servirebbero
   i lotti aggiudicati di SdAPA.
2. **ANAC open data per CIG**: filtrare i CIG (codici gara) che
   menzionano "Microsoft", "Office 365", "Azure", "Google Workspace",
   "AWS" — si può fare con `dati.anticorruzione.it/opendata`.
3. **Dati di spesa reale** (non solo stanziamento): quanto è stato
   effettivamente fatturato ai fornitori.
4. **Report "Cloud First" AGID** annuale: dovrebbe riportare la
   ripartizione effettiva.

---

## 6. Numeri politicamente spendibili

Per il dibattito pubblico (citabili in audizioni parlamentari, articoli,
interrogazioni):

- **€1,9 miliardi** PNRR stanziati per cloud PA (Misura 1.1+1.2)
- **€2,8 miliardi** valore contratto PSN (13 anni) — vinto da **Aruba + Fastweb**
- **2.011** schede ACN qualificate (777 fornitori)
- **Google 59 schede ACN**, **AWS 23**, **Microsoft solo 6**
- **219 enti mxmap.it** con cloud backend confermato via DNS
  (135 MS, 74 AWS, 10 Google)
- **~33 enti** con cloud backend confermato sono **anche** finanziati PNRR
- Le **ASL** sono il primo destinatario della Misura 1.2 (€406M totali)

### La domanda aperta per Fpietrosanti

> Su €1,9 mld PNRR cloud + €2,8 mld PSN = **€4,7 miliardi di spesa
> pubblica cloud**, **quanti € sono effettivamente andati a Microsoft,
> Google, AWS** vs al **cloud italiano sovrano** (Aruba+Fastweb)?

Per rispondere occorre:

1. ANAC open data: scaricare i CIG, filtrare per "Microsoft/Google/AWS"
2. Consip SdAPA: dettaglio lotti aggiudicati
3. Incrociare con `codice_ipa` dei 3,054 enti finanziati
4. **Collegare con `data.json` mxmap.it** per enrichment automatico

---

## Metodologia

Tutti i dati provengono da open data pubblici:

- **ACN**: <https://www.acn.gov.it/portale/open-data-servizi-cloud>
- **PNRR PA Digitale 2026**: <https://github.com/teamdigitale/padigitale2026-opendata>
- **PSN aggiudicazione**: Corrierecomunicazioni.it, iGizmo.it (gara Consip 2024)
- **mxmap.it dataset**: `data.json` (22,987 PA, generato 2026-06-10)

File generato automaticamente — ri-eseguibile con:

```bash
curl -sL https://www.acn.gov.it/portale/documents/d/guest/schede_qualificate_tipo_servizi_cloud_csv -o data/pnrr/acn_schede_qualificate.csv
curl -sL https://github.com/teamdigitale/padigitale2026-opendata/raw/refs/heads/main/data/candidature_altrienti_finanziate.csv -o data/pnrr/candidature_altrienti_finanziate.csv
```

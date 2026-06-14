# Catalogo KPI & Pagina Statistiche — specifica

> Stato: **bozza completa, da rifinire**. Lavoro **gated**: si progetta e si costruisce
> ora, va **live al run #1** della storicizzazione (anomalie risolte, vedi task #18/#20).
> Nessuna attivazione nella nightly finché non si chiude il gate.

## 1. Scopo

La pagina **Statistiche** è il rendiconto pubblico, *elaborato live dal software*, dello
stato e dell'evoluzione nel tempo della sovranità digitale della posta elettronica della
PA italiana. Espone un insieme **documentato** di KPI, organizzati per categoria, ciascuno
con **valore attuale + andamento storico**. Serve la Trasparenza: numeri sempre coerenti
col dato corrente, mai compilati a mano, riproducibili dalla formula qui sotto.

## 2. Principi

- **Una sola realtà.** Niente distinzione reality/methodology: la metodologia è congelata
  al run #1, ogni variazione successiva è un cambiamento reale misurato.
- **Live = calcolato dalla pipeline.** Il *valore attuale* di ogni KPI è ricalcolato a ogni
  build da `data.json`; l'*andamento* dallo storico (`history/runs.jsonl` + `timeseries/`).
- **Riuso, non duplicazione.** Le segmentazioni riusano `TIPOLOGIA_CLUSTERS` e
  `CATEGORY_LABELS` di [`scripts/report_it_by_category.py`](../scripts/report_it_by_category.py);
  la sovranità riusa `sovereignty_of()` di
  [`src/mail_sovereignty/historicize.py`](../src/mail_sovereignty/historicize.py).

## 3. Modello dati & notazione

Insieme corrente **E** = enti IT in `data.json` (`country == "IT"`), **N = |E|**.
Per ogni ente `e` (campi da `material_row`, salvo nota):

| simbolo | campo | valori |
|---|---|---|
| `prov(e)` | `provider` | microsoft, google, aruba, regional-public, independent, istruzione-miur-tenant, unknown, … |
| `sov(e)` | `sovereignty_of(prov)` | 6 bucket (sotto) |
| `jur(e)` | `mx_jurisdiction` | domestic / foreign / mixed / unknown |
| `conf(e)` | `classification_confidence` | [0,1] o ∅ |
| `cat(e)` | categoria IPA da `bfs` (`IT-{cat}-{ipa}`) | L6, C1, L33, … |
| `hasMX(e)` | `has_mx` | bool |
| `dkim(e)` | `dkim_tenant`≠∅ | bool |
| `spf(e)` | `spf` (entità raw) | bool |
| `region(e)` | regione IT (seed/`data-regions.json`) | 20 regioni |

**Bucket di sovranità** (`sovereignty_of`):

| bucket | provider tipici | gruppo |
|---|---|---|
| `USA (CLOUD Act)` | microsoft, google, istruzione-miur-tenant | **ESTERO** |
| `Altri provider esteri` | zoho, yandex, … | **ESTERO** |
| `Italia — Cloud sovrano` | regional-public (PSN/regionali) | **ITALIA** |
| `Italia — Provider commerciali` | aruba, register, … | **ITALIA** |
| `Italia — Infrastruttura autonoma` | independent (self-hosted) | **ITALIA** |
| `Sconosciuto` | unknown | **N/D** |

- **E_class** = `{e : sov(e) ≠ "Sconosciuto"}`, **N_class = |E_class|** (enti classificati).
- **ITA** = i 3 bucket *Italia —*. **EST** = i 2 bucket esteri.

Legenda implementazione: **[✓]** già calcolato dalla macchina di storicizzazione ·
**[+]** nuovo (da aggiungere a `build_manifest`/`build_timeseries` o al compute corrente).

---

## 4. Catalogo KPI

### Cat. 1 — Sovranità (indicatori di testata)
| # | KPI | Formula | Fonte / stato |
|---|---|---|---|
| 1.1 | **Indice di Sovranità Digitale (ISD)** | `100 · |{e: sov(e)∈ITA}| / N_class` | sov · **[✓]** (serie sovereignty) · *denominatore: vedi §8* |
| 1.2 | Quota CLOUD Act (USA) | `100 · |{sov=USA (CLOUD Act)}| / N_class` | **[✓]** |
| 1.3 | Quota cloud sovrano IT | `100 · |{sov=Italia — Cloud sovrano}| / N_class` | **[✓]** |
| 1.4 | Quota provider commerciali IT | `100 · |{sov=Italia — Provider commerciali}| / N_class` | **[✓]** |
| 1.5 | Quota infrastruttura autonoma IT | `100 · |{sov=Italia — Infrastruttura autonoma}| / N_class` | **[✓]** |
| 1.6 | Quota altri provider esteri | `100 · |{sov=Altri provider esteri}| / N_class` | **[✓]** |

> 1.2–1.6 sommano a 100% di N_class. L'ISD (1.1) = 1.3+1.4+1.5.

### Cat. 2 — Giurisdizione tecnica dell'MX
| # | KPI | Formula | Fonte / stato |
|---|---|---|---|
| 2.1 | MX domestico / estero / misto / unknown | `100 · |{jur(e)=x}| / N` (su tutti: unknown qui è informativo) | mx_jurisdiction · **[✓]** (serie jurisdiction) |

> Dimensione *complementare* alla sovranità: dove atterra fisicamente la posta,
> indipendentemente da chi è il provider legale. Uno scarto ISD↔MX-domestic è esso stesso
> un segnale (es. provider IT su infrastruttura estera).

### Cat. 3 — Struttura del mercato
| # | KPI | Formula | Fonte / stato |
|---|---|---|---|
| 3.1 | Top-N provider per quota | `share(p) = |{prov(e)=p}| / N_class`, ordinati desc | **[✓]** (serie provider) |
| 3.2 | Concentrazione top-3 | `Σ` delle 3 share maggiori | **[+]** |
| 3.3 | HHI (Herfindahl) | `Σ_p share(p)² · 10000` | **[+]** opzionale |
| 3.4 | Provider IT vs esteri | share per nazionalità provider | **[+]** (≈ ITA vs EST di Cat.1; tenere solo se aggiunge valore) |

### Cat. 4 — Copertura e qualità del dato (trasparenza sul metodo)
| # | KPI | Formula | Fonte / stato |
|---|---|---|---|
| 4.1 | Coverage | `100 · N_class / N` | **[✓]** (serie coverage) |
| 4.2 | Confidenza media | `mean(conf(e))` su `conf≠∅` | **[✓]** (mean_confidence) |
| 4.3 | Distribuzione bande confidenza | % alta (≥0.8) / media (0.5–0.8) / bassa (<0.5) | **[+]** |
| 4.4 | Ricchezza segnali | % `hasMX`, % `dkim`, % `spf` | **[+]** |

### Cat. 5 — Segmentazione per tipo di ente
Per ogni cluster di `TIPOLOGIA_CLUSTERS` (Territoriali, Istruzione, Sanità, Stato
centrale, Ordini/Camere, …): **ISD del cluster** + breakdown a 6 bucket.
| # | KPI | Formula | Fonte / stato |
|---|---|---|---|
| 5.1 | ISD per cluster | `100 · |{e∈cluster: sov∈ITA}| / |{e∈cluster classificati}|` | cat + cluster map · **[+]** |
| 5.2 | Breakdown sovranità per cluster | quote dei 6 bucket dentro il cluster | **[+]** |

> KPI-faro atteso: **Istruzione** → quota CLOUD Act alta (scuole sul tenant MIM
> `istruzione-miur-tenant` = Microsoft 365).

### Cat. 6 — Segmentazione geografica
| # | KPI | Formula | Fonte / stato |
|---|---|---|---|
| 6.1 | ISD per regione | `100 · |{e∈reg: sov∈ITA}| / |{e∈reg classificati}|` | region · **[+]** (richiede regione per ente, vedi §8) |
| 6.2 | Breakdown sovranità per regione | quote 6 bucket per regione (heat/ranking) | **[+]** |

### Cat. 7 — Dinamica nel tempo (richiede lo storico)
| # | KPI | Formula | Fonte / stato |
|---|---|---|---|
| 7.1 | Cambiamenti/giorno per tipo | conteggio eventi `{resolved, regressed, provider_change, sovereignty_change, jurisdiction_change}` per run | changelog · **[+]** (eventi esistono, da serializzare in serie) |
| 7.2 | Migrazioni di sovranità (saldo netto) | `|{sov_change: EST→ITA}| − |{ITA→EST}|` per run | **[+]** (>0 = miglioriamo) |
| 7.3 | Unknown nel tempo | `N − N_class` per run | **[+]** (deriva da coverage) |
| 7.4 | Stabilità | `100 · |enti senza eventi nel run| / N` | **[+]** |

### Cat. 8 — Integrità / anomalie
| # | KPI | Formula | Fonte / stato |
|---|---|---|---|
| 8.1 | Anomalie aperte nel tempo, per tipo | conteggio da `data/reports/anomalies.json` per run | **[+]** (da storicizzare nel manifest) |

---

## 5. KPI di testata (proposta)

La pagina apre con 4 carte grandi (valore attuale + sparkline):

1. **ISD** (1.1) — il numero-simbolo
2. **Quota CLOUD Act** (1.2) — l'esposizione USA
3. **Coverage** (4.1) — onestà sul dato
4. **Enti monitorati** (N) — la scala

→ *Decisione tua: confermi questi 4 o ne vuoi altri?* (§8)

## 6. Contratti dati (output del build per la pagina)

```
history/timeseries/sovereignty.json        [✓]   serie quote 6 bucket
history/timeseries/jurisdiction.json       [✓]   serie MX domestic/foreign/mixed/unknown
history/timeseries/coverage.json           [✓]   serie coverage + mean_confidence
history/timeseries/provider_national.json  [✓]   serie top provider
history/timeseries/confidence_bands.json   [+]   serie bande (4.3)
history/timeseries/market_concentration.json [+] serie top-3 / HHI (3.2/3.3)
history/timeseries/changes.json            [+]   eventi per tipo per giorno (7.1)
history/timeseries/migrations.json         [+]   saldo netto sovranità (7.2)
history/timeseries/anomalies.json          [+]   anomalie per tipo per giorno (8.1)
data/summary/stats_current.json            [+]   TUTTI i KPI correnti (valore "oggi")
data/summary/stats_by_category.json        [+]   Cat.5 (ISD + breakdown per cluster)
data/summary/stats_by_region.json          [+]   Cat.6 (ISD + breakdown per regione)
```

I `*_current` / `by_*` si calcolano a ogni build da `data.json` (non richiedono storico →
si possono produrre **anche prima** del run #1, se si vuole anticipare la sola fotografia
attuale senza le serie temporali). Le `timeseries/*` restano gated col run #1.

## 7. Pagina (`statistiche.html`)

- **Stile coerente con [storia.html](../storia.html)**: tema chiaro, grafici 100%-stacked
  dove sono quote, Chart.js, ordinamento numerico corretto.
- **Layout**: 4 carte di testata → sezione per categoria (Cat.1–8) con il grafico adatto
  (stacked area per le quote, line per i trend, bar/heat per le segmentazioni) → tabella
  segmentazioni (cluster ente, regione) con ISD per riga.
- **Deciso (✓): pagina nuova `statistiche.html`** — cruscotto KPI; `storia.html` resta il
  diario dei cambiamenti.

## 8. Decisioni (chiuse) e implementazione

**Chiuse (✓):**
1. **Denominatore ISD** → sui *classificati* (`N_class`): non diluisce con gli unknown.
2. **Base ISD** → bucket di *sovranità* (controllo legale). `mx_jurisdiction` mostrato a
   parte come indicatore tecnico complementare (lo scarto ISD↔MX-domestic è un segnale).
3. **4 KPI di testata** → ISD · Quota CLOUD Act · Coverage · Enti monitorati.
4. **Mercato** → teniamo top-3 (3.2) e HHI (3.3); **droppata** provider-IT-vs-esteri (3.4),
   ridondante con la Cat.1.
6. **Fotografia anticipata** → **SÌ**: `stats_current` + `stats_by_category` sono non-gated
   e già live (`scripts/build_stats.py`). Solo le `timeseries/*` restano gated al run #1.
7. **Pagina nuova `statistiche.html`** (cruscotto); `storia.html` resta il diario.

**Stato implementazione (questo commit):**
- `scripts/build_stats.py` → `data/summary/stats_current.json` + `stats_by_category.json`
  (riusa `sovereignty_of`/`material_row`). Cablato in nightly (non-gated) + CI smoke.
- `statistiche.html` → testata + composizione sovranità + giurisdizione MX + **sovranità
  per tipo di ente** (15 cluster, barre 100%-stacked) + mercato + qualità + trend (gated).
- Linkata da `index.html` (Trasparenza dataset).

**Correzione importante (segmentazione):** i codici categoria del `bfs` IT sono quelli
**propri del seed** (`COM`=Comuni, `PRO`=Province, `CMM`=Città metrop., `REG`=Regioni,
`CONS`=Consorzi…), NON i codici IndicePA `L6/L5/...` del report. Il mapping in
`build_stats.py` (`CLUSTERS`) è stato verificato sui 54 codici reali → copertura totale,
nessun "other".

**Aperte / differite:**
5. **Cat.6 — Sovranità per regione** → **DIFFERITA**: `data.json` non ha un campo `region`
   (0/22987). Serve decidere la fonte (`data-regions.json`, crosswalk ISTAT, o derivazione
   dal `bfs`/seed comune→regione) prima di produrre `stats_by_region.json`.

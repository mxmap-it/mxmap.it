# Design — Storicizzazione, OpenData storico, Dashboard trend, Changelog, Storia per-ente

> Documento di studio per il Task #15. Da discutere insieme prima di
> implementare. Obiettivo: trasformare l'Osservatorio da *fotografia*
> (l'ultimo stato) a *film* (l'andamento nel tempo), con dati storici
> opendata, una dashboard interattiva, un changelog per ogni run, e la
> scheda storica di ogni singolo ente.

> **AGGIORNAMENTO (decisione utente).** La distinzione **reality vs
> methodology** (il campo `cause`) è stata **rimossa** dall'implementazione:
> esiste una sola realtà. Disciplina: i bug si risolvono *prima*, la
> metodologia si **congela** al primo scan ufficiale, e da lì ogni cambiamento
> è dato reale. Le sezioni §4.4, §6.2, §7 e la TL;DR che parlano di `cause` /
> due-serie sono conservate come **razionale storico**, ma non descrivono più
> il comportamento attuale.

---

## 0. TL;DR (la proposta in 8 righe)

1. Ad ogni run la pipeline produce uno **snapshot compatto** (~1 MB, non
   il blob da 86 MB) e calcola il **diff vs run precedente**.
2. I diff alimentano un **changelog append-only** (audit trail) e la
   **scheda storica per-ente**.
3. Aggregati pre-calcolati (KB) alimentano una **dashboard statica** di
   trend (nessun backend — gira su GitHub Pages).
4. Tutto pubblicato come **opendata statico** + metadati DCAT-AP_IT per
   l'harvesting su dati.gov.it.
5. **Insight chiave**: separare *"il dato è cambiato perché la PA è
   migrata"* da *"è cambiato perché abbiamo migliorato il rilevamento"*.

---

## 1. Stato attuale (da cui partiamo)

### 1.1 Cosa produce oggi un run

| artefatto | dimensione | natura |
|---|---|---|
| `data.json` | **86 MB** | snapshot completo, 84.444 enti (22.978 IT) |
| `data-summary.json` / `data-detail.json` | 19 + 23 MB | split per il frontend |
| `data-regions.json` | ~1 MB | aggregati regione/provincia |
| `dist/mxmap_it_dataset.{csv,json,xlsx}` | 10 / 24 / 3 MB | export opendata flat |
| `data/reports/*.json` | KB | audit del run corrente (cleanup, rejections, mx_discovery_stats) |

### 1.2 Schema di un'entità (campi materiali)

```
bfs (id)               IT-C1-m_it
name                   Ministero dell'Interno
country                IT
domain                 interno.gov.it          (Sito_istituzionale IndicePA)
domain_used            interno.it              (dominio email reale, se diverso)
mx[]                   [interno-it.mail.protection.outlook.com]
provider               microsoft               ← LA CLASSIFICAZIONE
reason                 "MX record matches Microsoft"
mx_discovery_method    aoo_uo_tier6            ← COME l'abbiamo trovato
mx_discovery_evidence  interno.it
spf / dkim / autodiscover / tenant            (segnali DNS)
mx_cnames / mx_asns / mx_countries / gateway
ipa_codice_ipa         m_it
ipa_codice_categoria   C1
ipa_codice_comune_istat 058091
```

### 1.3 Il problema: git "storicizza" ma in modo inutilizzabile

- **160 commit** toccano già `data.json` → git *conserva* la storia, ma:
  - sono blob da 86 MB: i diff git sono opachi e pesanti;
  - **non interrogabili per-ente** ("mostrami la storia di interno.gov.it"
    richiederebbe di fare `git show` e diff manuale su 160 versioni da 86 MB);
  - non c'è changelog strutturato;
  - mescolano re-run manuali e correzioni di bug — niente cadenza pulita;
  - nessun aggregato temporale per i grafici.

**Conclusione**: la storia *esiste* nei dati ma è prigioniera di un formato
sbagliato. Serve una rappresentazione dedicata, compatta e interrogabile.

---

## 2. Requisiti (dalle parole dell'utente)

| # | requisito | implica |
|---|---|---|
| R1 | dati opendata accessibili come **storico** | file statici versionati + metadati DCAT |
| R2 | **dashboard interattiva** con andamento storico | aggregati pre-calcolati + SPA statica |
| R3 | **changelog** dei cambiamenti a ogni run | diff strutturato run-vs-run |
| R4 | ogni **ente** ha il suo storico di cambiamento | event-log per-entità + scheda timeline |
| R5 | mostrare l'**andamento dei risultati** nel tempo | time-series per metrica |

---

## 3. Architettura proposta (hybrid "lambda" per opendata)

Quattro livelli di rappresentazione, dal più granulare al più aggregato.
Ognuno serve un requisito diverso e ha un costo di storage diverso.

```
┌─────────────────────────────────────────────────────────────────────┐
│ data.json (86 MB)  — snapshot "vivo", build artifact, NON storicizzato│
└───────────────┬─────────────────────────────────────────────────────┘
                │  scripts/historicize.py  (nuovo step pipeline)
                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ LIVELLO 1 — Snapshot compatto per run                                 │
│   history/snapshots/2026-05-30.jsonl.gz   (~1 MB, solo campi materiali)│
│   → opendata bulk (R1), base per ricostruire qualsiasi stato passato  │
├─────────────────────────────────────────────────────────────────────┤
│ LIVELLO 2 — Changelog append-only (eventi di cambiamento)             │
│   history/changelog/2026-05.jsonl   (partizionato per mese)           │
│   → changelog del run (R3) + storia per-ente (R4)                     │
├─────────────────────────────────────────────────────────────────────┤
│ LIVELLO 3 — Time-series aggregati (pre-calcolati)                     │
│   history/timeseries/provider_national.json   (~KB, 1 riga per run)   │
│   history/timeseries/sovereignty.json, coverage.json, by_region/*.json│
│   → dashboard trend (R2, R5) — caricati direttamente dai grafici      │
├─────────────────────────────────────────────────────────────────────┤
│ LIVELLO 4 — Indici di navigazione                                     │
│   history/runs.jsonl            (manifest di tutti i run)             │
│   history/entity/{codice_ipa}.json  (timeline pre-calcolata per ente) │
│   → "scheda storica" di ogni ente (R4)                                │
└─────────────────────────────────────────────────────────────────────┘
```

Perché *hybrid* e non una sola rappresentazione:
- gli **snapshot** servono per il bulk-download e per ricostruire il
  passato, ma sono troppo grossi per i grafici;
- il **changelog** è compatto e interrogabile per-ente, ma ricostruire
  un aggregato richiederebbe di replayarlo tutto;
- i **time-series** sono perfetti per i grafici (KB) ma perdono il
  dettaglio per-ente;
- gli **indici** rendono O(1) la navigazione ("dammi la storia di X").

Ogni livello è derivabile dal precedente → un solo punto di verità
(lo snapshot), il resto è materializzazione.

---

## 4. Schema dei dati (concreto)

### 4.1 Snapshot compatto — `history/snapshots/{YYYY-MM-DD}.jsonl.gz`

Una riga JSON per entità, **solo i campi materiali** (quelli la cui
variazione è un "cambiamento" reale). Niente DNS verboso (spf raw, cnames):

```json
{"id":"IT-C1-m_it","ipa":"m_it","cat":"C1","country":"IT",
 "provider":"microsoft","sovereignty":"USA (CLOUD Act)",
 "method":"aoo_uo_tier6","domain_used":"interno.it",
 "mx0":"interno-it.mail.protection.outlook.com","has_mx":true,
 "dkim_tenant":"miuristruzione.onmicrosoft.com","gateway":null,
 "confidence":0.95}
```

- ~23k righe IT (+ altri paesi) × ~12 campi.
- JSONL gzippato ≈ **1–2 MB/run**. (Parquet ≈ 0.5 MB ma aggiunge
  dipendenza; JSONL.gz è leggibile con strumenti standard e dataset-friendly.)
- `confidence` = lo score rule-based (vedi piano confidence Fase A-D) —
  così lo storico tiene traccia anche della qualità, non solo del verdetto.

### 4.2 Manifest dei run — `history/runs.jsonl`

Una riga per run (indice di tutto lo storico):

```json
{"run_id":"2026-05-30","git_sha":"29ea8ecd","generated":"2026-05-30T04:02:11Z",
 "pipeline_version":"1.3.0","n_entities_it":22978,
 "n_changed":47,"n_new":3,"n_resolved":12,"n_regressed":1,
 "provider_counts":{"google":6365,"aruba":5229,"microsoft":3418,...},
 "sovereignty":{"USA (CLOUD Act)":9783,"Italia — Cloud sovrano":917,...},
 "snapshot":"snapshots/2026-05-30.jsonl.gz",
 "changelog":"changelog/2026-05.jsonl#2026-05-30"}
```

### 4.3 Changelog (eventi) — `history/changelog/{YYYY-MM}.jsonl`

Append-only. **Una riga per (entità, campo) cambiato** in un run:

```json
{"run_id":"2026-05-30","ts":"2026-05-30T04:02Z","id":"IT-C1-m_it","ipa":"m_it",
 "name":"Ministero dell'Interno","cat":"C1",
 "change":"resolved","field":"provider","from":"unknown","to":"microsoft",
 "from_method":"unknown","to_method":"aoo_uo_tier6",
 "cause":"methodology","git_sha":"d462e76b",
 "note":"Tier-6 AOO/UO recovery: interno.it"}
```

Tipi di `change` (tassonomia):

| tipo | significato | esempio |
|---|---|---|
| `new` | ente comparso nel seed | nuovo comune da IndicePA |
| `removed` | ente sparito dal seed | fusione/soppressione |
| `resolved` | da `unknown` a classificato | recupero MX |
| `regressed` | da classificato a `unknown` | dominio defunto / bug |
| `provider_change` | provider A → B | migrazione cloud o correzione |
| `sovereignty_change` | bucket sovranità cambiato | il cuore della narrazione |
| `method_change` | stessa classificazione, metodo diverso | abbiamo trovato prova migliore |
| `domain_change` | domain_used cambiato | ente ha cambiato dominio email |
| `mx_change` | host MX primario cambiato | cambio server, stesso provider |

### 4.4 Il campo `cause` — RIMOSSO (decisione)

> **Aggiornamento (decisione utente):** il campo `cause` è stato **rimosso**.
> Disciplina adottata: i bug si risolvono *prima* del primo scan ufficiale e la
> metodologia si **congela** al run #1; da lì ogni cambiamento è dato reale.
> Niente attribuzione reality/methodology/uncertain, niente euristica su
> `git_sha`. Gli eventi del changelog sono `{change, field, from, to}`. Se in
> futuro si vorrà marcare un raro rilascio deliberato, si userà esplicitamente
> il bump di `pipeline_version` (§7). Il testo sotto è conservato come
> razionale storico della scelta.



Ogni evento porta una **causa attribuita**:

- `cause: "reality"` → il dato è cambiato perché **la PA è migrata**
  (es. un comune passa da Aruba a Microsoft). Stessa `method`, stesso
  `git_sha` della metodologia, ma MX/provider diverso da una run all'altra
  a parità di logica.
- `cause: "methodology"` → il dato è cambiato perché **abbiamo migliorato
  il rilevamento** (nuova regola, fix di bug, nuovo tier di recupero).
  Riconoscibile perché il `git_sha` del codice è cambiato e/o il
  `mx_discovery_method` è passato a un metodo nuovo.
- `cause: "source"` → cambiamento a monte (IndicePA ha aggiornato il
  Sito_istituzionale, ISTAT ha rinominato un comune).
- `cause: "uncertain"` → non attribuibile automaticamente → coda di review.

Euristica di attribuzione (in `historicize.py`):

```
se entità nuova/rimossa               → new / removed (cause: source)
altrimenti, confronta (provider, method, domain_used, mx0):
  se solo method è cambiato            → method_change (cause: methodology)
  se provider cambiato E method nuovo  → cause: methodology
       (es. unknown→microsoft via nuovo tier aoo_uo_tier6)
  se provider cambiato E method uguale E git_sha invariato
       → cause: reality   (la PA è migrata davvero)
  se provider cambiato E git_sha della pipeline cambiato dall'ultima run
       → cause: uncertain (potrebbe essere un nostro fix) → flag review
```

> Questa separazione è **fondamentale per la credibilità**: senza, ogni
> nostro bug-fix sembrerebbe una migrazione di massa della PA. La
> dashboard mostrerà due serie distinte: "andamento reale della sovranità"
> vs "miglioramento della copertura del rilevamento".

### 4.5 Time-series aggregati — `history/timeseries/*.json`

Pre-calcolati, una riga per run. Esempi:

`provider_national.json`:
```json
[{"date":"2026-05-29","google":6365,"aruba":5229,"microsoft":3418,
  "independent":2859,"local-isp":1708,"regional-public":917,
  "register-it":667,"unknown":655,...},
 {"date":"2026-05-30", ...}]
```

`sovereignty.json` (la serie-narrazione):
```json
[{"date":"2026-05-30","usa_cloud_act":9783,"italia_sovrano":917,
  "italia_commerciale":7604,"italia_autonoma":2859,"estero_altro":2,
  "sconosciuto":655,
  "_pct":{"usa_cloud_act":42.6,...}}]
```

`coverage.json` (la serie "nostro lavoro"):
```json
[{"date":"2026-05-30","resolved":22323,"unknown":655,
  "by_method":{"seed_primary_mx":21115,"aoo_uo_tier6":199,...},
  "coverage_pct":97.1}]
```

Più breakdown: `by_region/{regione}.json`, `by_category/{cat}.json`.
Tutti KB-sized → caricati direttamente dai grafici.

### 4.6 Scheda storica per-ente — `history/entity/{codice_ipa}.json`

Pre-calcolata per ogni ente che abbia ≥1 cambiamento (gli altri si
ricostruiscono dal primo snapshot):

```json
{"ipa":"m_it","name":"Ministero dell'Interno","cat":"C1",
 "current":{"provider":"microsoft","method":"aoo_uo_tier6",...},
 "timeline":[
   {"run_id":"2026-05-10","provider":"unknown","method":"unknown"},
   {"run_id":"2026-05-10","provider":"microsoft","method":"aoo_uo_tier6",
    "change":"resolved","cause":"methodology",
    "note":"Tier-6 AOO/UO: interno.it"},
   ...],
 "n_changes":2,"first_seen":"2026-05-04","last_change":"2026-05-10"}
```

→ alimenta una sezione "Storia di questo ente" nel popup/scheda del frontend.

---

## 5. Pubblicazione OpenData (R1)

Tutto statico, servito da GitHub Pages sotto `history/`:

| file | contenuto | consumatore |
|---|---|---|
| `history/runs.jsonl` | indice di tutti i run | API/script |
| `history/snapshots/{date}.jsonl.gz` | snapshot completo per run | bulk download, ricerca |
| `history/changelog/{month}.jsonl` | tutti gli eventi | audit, giornalisti |
| `history/timeseries/*.json` | aggregati | dashboard |
| `history/entity/{ipa}.json` | timeline per-ente | scheda ente |
| `history/CHANGELOG-{date}.md` | changelog leggibile del run | umani |
| `history/dcat.jsonld` | metadati DCAT-AP_IT | dati.gov.it harvesting |

**DCAT-AP_IT**: lo standard italiano per gli opendata (profilo di
DCAT-AP). Genera un `dcat.jsonld` che descrive il dataset, le
distribuzioni (CSV/JSON/snapshot storici), licenza (ODbL+CC-BY),
frequenza di aggiornamento (giornaliera), publisher. Rende il dataset
**harvestabile automaticamente da dati.gov.it** — valore istituzionale
enorme per un Osservatorio sulla PA.

**Licenza**: confermare ODbL-1.0 (dati) + CC-BY-4.0 (contenuti) come già
nel footer. Aggiungere un `history/LICENSE` esplicito.

---

## 6. Dashboard interattiva (R2, R5)

Nuova pagina statica `storia.html` (o sezione in index.html), zero backend,
legge i `timeseries/*.json`. Tech leggera: **uPlot** o **Chart.js**
(no framework pesante).

### 6.1 Sezioni

1. **Sovranità nel tempo** — area chart impilato (USA CLOUD Act / Cloud
   sovrano IT / Provider IT / Autonoma / Estero / Sconosciuto), in % e
   assoluto. Annotazioni verticali sui cambi di metodologia (vedi §7).
2. **Copertura del rilevamento** — quanti enti risolti vs unknown nel
   tempo, breakdown per metodo (la "campagna di bonifica"). Mostra il
   *nostro* lavoro, separato dalla realtà.
3. **Per categoria / regione** — small multiples selezionabili (comuni,
   ministeri, scuole, ASL, regioni…).
4. **Feed changelog** — gli eventi dell'ultimo run, filtrabili per tipo
   (`resolved`/`provider_change`/`regressed`/…) e per causa
   (reality/methodology). "Cosa è cambiato stanotte".
5. **Scheda storica ente** — cerca un ente → timeline della sua
   classificazione (riusa `entity/{ipa}.json`).
6. **Big numbers** — % PA sotto CLOUD Act oggi, delta vs 30/90/365 giorni,
   n. enti migrati verso provider sovrani nel periodo.

### 6.2 Distinzione visiva reality vs methodology

Le due serie (sovranità reale, copertura) hanno **palette e assi diversi**.
Sui grafici di sovranità, i salti dovuti a fix di metodologia sono marcati
con una linea tratteggiata + tooltip ("salto dovuto a v1.3: recupero
Tier-6 AOO/UO, +199 enti classificati"). Così un giornalista non legge un
nostro bug-fix come "migrazione di massa".

---

## 7. Versionamento della metodologia

File `history/methodology_versions.json`:

```json
[{"version":"1.3.0","date":"2026-05-30","git_sha":"29ea8ecd",
  "changes":["rule 6.6 label_concat (ACI)","fix L6 ISTAT-based",
             "gate is_legit su recover_it_unknowns"],
  "impact":{"resolved":+220,"reclassified":+90}},
 ...]
```

- Ogni run registra la `pipeline_version` nel manifest.
- I salti nei grafici si annotano da qui.
- Collega ogni versione al CHANGELOG git e ai commit.

`pipeline_version` va bumpata quando cambia la *logica di classificazione*
(non per i refresh dati). Semver: MAJOR = cambio schema, MINOR = nuova
regola/metodo, PATCH = fix.

---

## 8. Integrazione nella pipeline notturna

Nuovo step in `nightly.yml`, dopo `build_public_dataset`:

```yaml
- name: Historicize run (snapshot + diff + changelog + timeseries)
  run: |
    uv run python3 scripts/historicize.py \
      --run-id "$(date -u +%F)" \
      --git-sha "${{ github.sha }}" \
      --pipeline-version "$(cat VERSION)"
```

`scripts/historicize.py` (nuovo, ~300 righe):
1. carica `data.json` corrente + ultimo snapshot da `history/snapshots/`;
2. estrae i campi materiali → snapshot compatto del run;
3. diff per-entità → eventi changelog con attribuzione `cause`;
4. append a `history/changelog/{month}.jsonl`;
5. aggiorna `history/runs.jsonl`;
6. ricalcola i `timeseries/*.json` (append una riga);
7. aggiorna gli `entity/{ipa}.json` toccati;
8. genera `history/CHANGELOG-{date}.md` leggibile;
9. rigenera `history/dcat.jsonld`.

Commit: solo gli artefatti compatti di `history/` (KB–MB), **non** il
blob da 86 MB. Idempotente: ri-eseguire sullo stesso run-id sovrascrive.

Costo storage annuo stimato: snapshot 1.5 MB × 365 ≈ **550 MB/anno** +
changelog/timeseries trascurabili. Gestibile (vedi §9 per compaction).

---

## 9. Retention & compaction

- **Changelog & time-series**: per sempre (audit trail + grafici; crescono
  poco, solo i cambiamenti).
- **Snapshot**: rolling. Proposta: giornalieri per 90 giorni → settimanali
  per 1 anno → mensili oltre. Uno script `compact_history.py` mensile.
  (Si può sempre ricostruire uno stato intermedio replayando il changelog
  sull'ultimo snapshot precedente.)
- **Repo git**: il problema vero è `data.json` (86 MB × 160 commit già
  oggi). Due opzioni, da decidere:
  - (a) **smettere di committare `data.json`** nel repo principale; resta
    build artifact rigenerato, e lo storico ufficiale diventano gli
    snapshot compatti. Riduce il bloat futuro.
  - (b) repo separato `mxmap-history` (submodule) o Git LFS per i dati.
  Raccomando (a): gli snapshot compatti sostituiscono `data.json` come
  record storico canonico.

---

## 10. Piano di rollout (incrementale, basso rischio)

| fase | cosa | output | giorni |
|---|---|---|---|
| **F1** | `historicize.py`: snapshot + diff + changelog + runs.jsonl. Backfill dei 160 commit git esistenti come storia iniziale. | storico opendata navigabile (R1, R3, R4 dati) | 2–3 |
| **F2** | time-series aggregati + `entity/{ipa}.json` | base dashboard + schede (R4, R5 dati) | 1–2 |
| **F3** | dashboard `storia.html` (trend + funnel + feed) | R2 visivo | 3–4 |
| **F4** | scheda storica nel popup ente + ricerca | R4 visivo | 1–2 |
| **F5** | DCAT-AP_IT + retention/compaction + integrazione nightly | R1 istituzionale, automazione | 1–2 |
| | **totale** | sistema completo | **8–13** |

**F1 dà subito valore**: il backfill dei 160 `data.json` storici già in git
produce ~1 mese di storia reale al day-one (basta `git log` + estrazione
campi materiali da ogni versione committata). Quindi la dashboard nasce
già con una curva, non da zero.

---

## 11. Decisioni aperte (da concordare domani)

1. **Formato snapshot**: JSONL.gz (raccomandato, standard, leggibile) vs
   Parquet (più compatto, DuckDB-in-browser ma +dipendenza)?
2. **Scope**: solo IT o tutti gli 84k enti (92 paesi)? Propongo IT-first,
   schema estendibile.
3. **`data.json` in git**: smettere di committarlo (opzione 10a) o tenerlo?
4. **Granularità changelog**: per-campo (più righe, più preciso) o
   per-entità (una riga con tutti i delta)? Propongo per-campo.
5. **Dashboard**: pagina separata `storia.html` o tab nell'index?
6. **`confidence` nello snapshot**: richiede prima il sistema di scoring
   rule-based (piano Confidence Fase A). Storicizzare anche la confidence
   o solo provider/method? Propongo includere confidence appena disponibile.
7. **Cadenza**: lo storico ha senso giornaliero solo se la pipeline gira
   ogni notte in modo affidabile. Confermare che il nightly è stabile
   (oggi gira `fetch_indicepa` + `preprocess IT` + recovery completa).

---

## 12. Rischi e mitigazioni

| rischio | mitigazione |
|---|---|
| Rumore: micro-variazioni DNS (TTL, ordine MX) generano falsi "cambiamenti" | normalizzare i campi materiali (ordina MX, lowercase, dedup) prima del diff; ignorare cambi non-materiali |
| Bug-fix letti come migrazioni PA | campo `cause` + dashboard a due serie distinte (§4.4, §6.2) |
| Repo bloat | snapshot compatti + smettere di committare data.json (§9) |
| Run mancati / pipeline rotta | `runs.jsonl` rende espliciti i buchi; la dashboard interpola/segna i gap |
| Cambi di schema IndicePA/ISTAT | `cause: source` + i test invarianti seed (già esistenti) intercettano |
| Privacy | sono dati su enti pubblici e infrastruttura, non persone; nessun dato personale negli snapshot (mai email individuali — solo domini) |

---

## 13. Perché questo design è giusto per *questo* progetto

- **Statico-first**: gira su GitHub Pages senza backend, coerente con
  l'attuale deploy (zero costi infra, zero manutenzione server).
- **Git-native dove serve, non dove fa male**: usa git per versionare gli
  artefatti compatti, ma toglie il blob da 86 MB dal collo di bottiglia.
- **Opendata vero**: file standard, licenza chiara, DCAT per dati.gov.it →
  un Osservatorio sulla PA *deve* essere esso stesso opendata esemplare.
- **Narrazione onesta**: la separazione reality/methodology è ciò che
  distingue un osservatorio credibile da uno che gonfia i numeri. È anche
  la risposta pronta alla domanda "come so che i tuoi dati sono giusti?".
- **Incrementale**: F1 dà valore in 2 giorni col backfill dei dati git già
  esistenti; il resto si aggiunge senza rifacimenti.

---

---

## 14. Validazione del prototipo (fatta stanotte)

Per de-riskare la Fase 1 ho scritto e **testato su dati reali** i due
script chiave:

- `scripts/historicize.py` — snapshot + diff + changelog + runs.jsonl +
  time-series + CHANGELOG.md. Funzionante.
- `scripts/backfill_history.py` — estrae ogni versione storica di
  `data.json` da git e la storicizza in ordine cronologico.

**Test eseguito**: backfill di 12 commit campionati dai 160 esistenti
(da `initial commit` del 6 marzo al `full IT pipeline` del 5 maggio).
Risultati reali ricostruiti:

```
2026-03-15   USA-CloudAct=80     (Italia appena aggiunta)
2026-03-16   USA-CloudAct=143
2026-04-30   USA-CloudAct=100
2026-05-05   USA-CloudAct=10938  CloudSovrano=1088  Sconosciuto=12
                                  (pipeline IT completa, tutte le categorie)
```

Conferme empiriche:
- **Snapshot compatto**: 635 KB gzip per 22.947 enti → la stima "~1 MB/run"
  del §4.1 è corretta (vs 86 MB di data.json: **−99%**).
- **Backfill funziona**: i 160 commit git esistenti danno davvero ~2 mesi
  di storia al day-one, senza aspettare nuovi run (tesi §10 verificata).
- **Diff/changelog corretti**: il run 05-05 produce 22.947 eventi `new`
  (l'aggiunta della pipeline IT completa) con il CHANGELOG markdown
  leggibile (Min Interno → microsoft, PCM → microsoft, …).
- **Idempotenza**: ri-eseguire sullo stesso run-id sovrascrive senza
  duplicare.

Limiti noti del prototipo (da rifinire in F1):
- alcuni `ipa`/`cat` vuoti negli snapshot storici vecchi (i campi
  IndicePA non erano ancora popolati a marzo) — non un bug, è la storia;
- il backfill campiona 12 commit per il test; la F1 reale li processa
  tutti e 160;
- gli artefatti `history/` generati nel test NON sono committati (sono
  output di prova sul server) — la F1 reale li genera puliti dal backfill
  completo.

**Conclusione**: il design non è solo teoria — la spina dorsale (F1) è
già provata su dati veri. Manca da concordare le decisioni aperte (§11)
e costruire dashboard (F3) + scheda ente (F4).

---

*Prossimo passo: discutere le decisioni aperte (§11), poi partire da F1
(`historicize.py` + backfill dei 160 commit storici) — il prototipo è
già pronto.*

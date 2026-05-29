# Validazione del seed IT — Architettura e procedure

Documento di riferimento per la **catena di validazione** che protegge
il seed `data/municipalities_it.json` dagli errori di categorizzazione
upstream (IndicePA) e dai bug strutturali nostri (filtri, mapping,
id namespace).

> **Storia**: l'innesco fu il bug "UNCEM Delegazione Regionale del
> Lazio appare come polygon di Roma nella vista comuni" (commit
> `c26a7358`). Audit successivo rivelò 90 enti L6 mal-categorizzati
> in IndicePA. Da lì costruimmo l'architettura qui descritta.

---

## 1. Invarianti che proteggiamo

La vista comuni della mappa renderizza un polygon per ogni entry con
`id` che inizia con `IT-COM-`. Affinché la vista sia corretta:

| # | invariante | conseguenza in caso di violazione |
|---|---|---|
| **I1** | Ogni `IT-COM-XXX` è **unico** | due enti collidono sullo stesso polygon |
| **I2** | Ogni `IT-COM-XXX` corrisponde a un **vero comune italiano** (nome inizia per "Comune" o codice IPA esplicitamente whitelistato) | enti non-comuni (UNCEM, ANCI, ATS, ecc.) appaiono come comuni |
| **I3** | Ogni `IT-COM-XXX` ha `ipa_codice_categoria == "L6"` | namespace `IT-COM-*` riservato ai Comuni |
| **I4** | `id == "IT-COM-{X}"` ⇔ `ipa_codice_comune_istat == "X"` | id e campo di lookup divergenti → bug downstream |
| **I5** | Ogni `IT-COM-XXX` ha un codice ISTAT (numerico o catastale) presente nell'**elenco ufficiale ISTAT** | codice spurio o obsoleto → render sul polygon sbagliato |
| **I6** | Numero di `IT-COM-*` è ±50 da quello ISTAT (~7896) | filtro troppo permissivo (>>) o troppo stretto (<<) |
| **I7** | Solo entry territoriali (`IT-REG/PRO/CMM/COM`) hanno `osm_relation_id` | enti non-comuni renderizzati sul polygon del comune sede (bug UNCEM 2026-05-29) |

Analoghe invarianti su `IT-REG-*` (Regioni), `IT-PRO-*` (Province),
`IT-CMM-*` (Città Metropolitane). Non ancora applicate alle categorie
non-territoriali (`IT-C*-*`, `IT-L33-*`, `IT-L34-*`, ecc.) — vedi §6.

---

## 2. Architettura della catena di validazione

```
┌──────────────────────────────────────────────────────────────────────────┐
│ IndicePA (registro AgID, ~52 categorie, ~23k enti pubblici italiani)     │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │ HTTP CKAN datastore_search
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ scripts/fetch_indicepa.py                                                 │
│                                                                          │
│ 1.  fetch_category(L4/L5/L45/L6 + altre con --include-others)           │
│ 2.  is_territorial(name, categoria, codice_ipa)  ← FILTRO STRUTTURALE   │
│       • L4/L5/L45/L6: positive name pattern obbligatorio                │
│       • L6_NAME_EXCEPTIONS whitelist documentata                        │
│       • NON_TERRITORIAL_NAME_RE: backup negative match per L6           │
│ 3.  build_id(prefix, codice_istat, codice_comune_istat)                 │
│       • is_terr_for_id=False → IT-CONS-{codice_ipa}                     │
│       • is_terr_for_id=True  → IT-{REG|PRO|CMM|COM}-{istat}             │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ data/municipalities_it.json (seed)                                       │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ tests/test_seed_invariants.py  ← LAYER 2: regression tests                │
│                                                                          │
│   I1 → test_no_it_com_id_collisions                                     │
│   I2 → test_all_it_com_entries_have_comune_name                         │
│   I3 → test_no_it_com_for_non_l6_categorie                              │
│   I4 → test_no_orphan_it_com_istat_pairs                                │
│   I5 → test_all_it_com_cross_validate_against_istat                     │
│   I6 → test_seed_comuni_count_matches_istat                             │
│   analoghi per IT-REG-* / IT-PRO-* / IT-CMM-*                           │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ .github/workflows/nightly.yml  ← LAYER 3: CI gate                        │
│                                                                          │
│   step "Seed invariants" esegue pytest tests/test_seed_invariants.py    │
│   FAIL → workflow abortisce, niente commit, niente deploy.              │
└──────────────────────────────────────────────────────────────────────────┘
```

I tre layer **sono ridondanti per design**: il filtro a fetch-time
previene il bug, il test pytest lo rileva se passa, il workflow CI lo
blocca prima del deploy. Se IndicePA un domani introduce un nuovo
"UNCEM-tipo" e il filtro fetch-time non lo cattura (per una variante
non prevista del nome), il test pytest fallisce e il workflow
notturno blocca il commit.

---

## 3. Fonti dati

### 3.1 IndicePA (primaria)

- **URL**: https://indicepa.gov.it/ipa-dati/dataset/enti
- **Refresh**: notturno via `fetch_indicepa.py --include-others`
- **Categorie**: ~52 (vedi `LEVEL_MAP` per le 4 territoriali, `fetch_all_categories()` per le altre)
- **Qualità**: media. Anomalie categoria/nome documentate sotto.

### 3.2 ISTAT (cross-validation)

- **URL**: https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv
- **Refresh**: manuale via `fetch_istat_comuni.py` quando ISTAT pubblica
  una nuova edizione (in genere semestrale dopo variazioni amministrative)
- **Cardinalità**: 7,896 comuni (gennaio 2024)
- **Encoding**: ISO-8859-1
- **Snapshot**: `data/istat_comuni.json` (committato come ground truth)
- **Campi chiave salvati**:
  - `codice_istat` (es. `095001` = Abbasanta)
  - `codici_storici[]` (codici 110/107/103 province per gestire Sardegna pre-2016)
  - `codice_catastale` (es. `A007` — stabile nel tempo, non cambia con riforme province)
  - `denominazione_it`, `denominazione_full`
  - `codice_regione`, `codice_provincia`, `sigla_auto`, `codice_nuts3_2024`, `capoluogo`

---

## 4. Quirks IndicePA noti (documentati per future regressioni)

### Q1. Codici provincia Sardegna pre-2016

IndicePA per i comuni sardi usa ancora i codici provincia **pre-riforma 2016**:

| codice IndicePA | provincia (abolita) | codice ISTAT corrente |
|---|---|---|
| 111xxx | Carbonia-Iglesias | 111xxx (storico) → ora 105 Sud Sardegna |
| 112xxx | Olbia-Tempio | 112xxx (storico) → ora 104 Sassari |
| 115xxx | (storico Oristano allargato) | 095xxx |
| 116xxx | Ogliastra | 116xxx (storico) → ora 091 Nuoro |
| 117xxx | Medio Campidano | 117xxx (storico) → ora 105 Sud Sardegna |

**Mitigazione**: `istat_codes` include sia codici correnti che storici dal CSV ISTAT. Vedi `istat_codes` fixture.

### Q2. Codici catastali pre-fusione

Quando un comune si fonde con un altro (es. Bellagio + Civenna → Bellagio nel 2014), il **nuovo codice catastale** è diverso dal vecchio. IndicePA conserva il vecchio (`c_a744` per Bellagio), ISTAT pubblica solo il nuovo (`M335`).

**Mitigazione**: `test_all_it_com_cross_validate_against_istat` usa logica **OR**: matcha se il codice ISTAT numerico OR il codice catastale è in ISTAT. Coverage attesa:
- ~95% matcha per codice ISTAT numerico (Sardegna inclusa via codici storici)
- ~5% matcha per fallback catastale (Bellagio-like)

### Q3. Codici IPA opachi

Per comuni neo-fusi (2010+), IndicePA assegna `codice_ipa` UUID-like (es. `3BEP4ZAX` per Moransengo-Tonengo, `40B59AWR` per Sovizzo nuovo) invece del classico `c_<catastale>`. Anche codici storici tipo `B432` (Calto, pre-2010) o `c_0319` (4 digit invece di alfanum) sono presenti.

**Mitigazione**: la regex `c_[a-z][a-z0-9]{3}$` per estrarre il catastale gestisce esplicitamente questo:
- Match → cattura il catastale e si valida
- No match → ci si affida solo al codice ISTAT (campo `ipa_codice_comune_istat`)

### Q4. L6 falsi positivi (UNCEM-type)

IndicePA categorizza come `L6 = Comune` enti che NON sono comuni: UNCEM, ANCI Piemonte, Patrimonio Mobilita, ATS Madonie, Acquedotto Consortile, Federazione Regionale Agronomi, ecc. (~110 casi documentati).

**Mitigazione (3 livelli)**:
1. `LEVEL_NAME_RE["L6"]` = `^Comune\b` (positive filter — questi non passano)
2. `NON_TERRITORIAL_NAME_RE` (negative filter — backup)
3. `is_territorial()` richiede `pos.match()` AND `NOT negative.search()` per L6

Risultato: tutti reassegnati a `IT-CONS-{codice_ipa}`, namespace separato dal polygon comunale.

### Q5. Comuni ladini con nome non-standard

2 veri comuni italiani il cui Denominazione_ente IndicePA non inizia per "Comune":
- `c_m390` "San Giovanni di Fassa-Sen Jan" (Trento, bilingue ladino)
- `c_f392` "Montagna sulla strada del vino" (Bolzano)

Catturati dal positive filter L6 come "non comuni" → riassegnati erroneamente a `IT-CONS-*`.

**Mitigazione**: `L6_NAME_EXCEPTIONS` whitelist documentata. Ogni eccezione **deve** essere:
- Un `codice_ipa` esistente nel seed corrente (test #X verifica)
- Categoria `L6` in IndicePA
- Verificato manualmente come vero comune (link Wikipedia / ISTAT)

---

## 5. Inventario test

| test | layer | invariante | failure mode probabile |
|---|---|---|---|
| `test_no_it_com_id_collisions` | strutturale | I1 | due enti con stesso `ipa_codice_comune_istat` ed entrambi L6 |
| `test_all_it_com_entries_have_comune_name` | strutturale | I2 | nuovo "UNCEM-tipo" passa il filtro fetch-time |
| `test_no_it_com_for_non_l6_categorie` | strutturale | I3 | bug nel `build_id()` che genera IT-COM- per non-L6 |
| `test_no_orphan_it_com_istat_pairs` | strutturale | I4 | bug nel `build_id()` o nel parsing del codice ISTAT |
| `test_all_it_reg_entries_have_regione_name` | strutturale | I2 (REG) | nuovo "ANEA-tipo" |
| `test_all_it_pro_entries_have_provincia_name` | strutturale | I2 (PRO) | nuovo "UPI-tipo" |
| `test_all_it_cmm_entries_have_cmm_name` | strutturale | I2 (CMM) | analogo |
| `test_all_it_com_cross_validate_against_istat` | semantica | I5 | comune con codice spurio non in ISTAT |
| `test_seed_comuni_count_matches_istat` | aggregata | I6 | filtro fetch troppo restrittivo o ISTAT snapshot stale |
| `test_l6_exceptions_are_in_seed` | meta | self | whitelist con riferimenti morti |
| `test_l6_exceptions_are_actually_comuni` | meta | I2+I5 | whitelist con un non-comune (bypass del filtro) |
| `test_istat_snapshot_well_formed` | meta | dataset | CSV ISTAT cambiato formato |

---

## 6. Procedure di manutenzione

### 6.1 Aggiornare lo snapshot ISTAT

Quando ISTAT pubblica una nuova edizione (vedi
https://www.istat.it/it/archivio/6789):

```bash
uv run python3 scripts/fetch_istat_comuni.py --refresh
git add data/istat_comuni.json
git commit -m "data: refresh ISTAT snapshot $(date +%Y-%m-%d)"
```

Esegui poi `uv run pytest tests/test_seed_invariants.py -v` per
verificare che il nuovo snapshot non rompa nulla. Il count atteso
nel test #8 potrebbe richiedere aggiornamento se ISTAT ha più o
meno comuni (fusioni).

### 6.2 Aggiungere un comune a `L6_NAME_EXCEPTIONS`

Se il test `test_all_it_com_entries_have_comune_name` fallisce con
un ente che è **un vero comune** con nome non-standard:

1. Verifica che sia un vero comune (link Wikipedia, ISTAT)
2. Verifica che `codice_ipa` segua il pattern `c_<catastale>`
3. Aggiungi a `L6_NAME_EXCEPTIONS` in `scripts/fetch_indicepa.py` con commento esplicito:
   ```python
   L6_NAME_EXCEPTIONS = {
       "c_m390",   # San Giovanni di Fassa-Sen Jan (TN, comune ladino)
       "c_f392",   # Montagna sulla strada del vino (BZ, denominazione bilingue)
       # NEW: "c_xyzw",  # Nome del comune (provincia, ragione)
   }
   ```
4. Rigenera il seed e rilancia i test:
   ```bash
   uv run python3 scripts/fetch_indicepa.py --include-others
   uv run pytest tests/test_seed_invariants.py -v
   ```

### 6.3 Investigare una nuova violazione I5

Se `test_all_it_com_cross_validate_against_istat` fallisce con un
codice non in ISTAT:

1. Verifica se il comune è nel CSV ISTAT corrente:
   ```bash
   grep -i "<denominazione>" data/istat_raw/comuni.csv | head -3
   ```
2. Se è presente con codice diverso: probabilmente una variazione
   amministrativa recente. Aggiorna lo snapshot ISTAT (§6.1).
3. Se è assente: verifica se è davvero un comune (potrebbe essere
   un'unione di comuni mal-categorizzata in IndicePA). Aggiungi
   manualmente un override se necessario.

### 6.4 Aumentare la soglia di violazioni accettate

I test `test_all_it_com_cross_validate_against_istat` e
`test_seed_comuni_count_matches_istat` hanno soglie hard-coded (30 e
50 rispettivamente). Se IndicePA introduce molti nuovi comuni-fusione
in attesa che ISTAT li pubblichi, si possono temporaneamente alzare
(con commento esplicito sulla giustificazione e una scadenza per
riportarle al valore di default).

---

## 7. Limiti noti

### L1. Solo L4/L5/L45/L6 hanno test di nome

Le categorie non-territoriali (C1 ministeri, C13 ACI, C14 ordini, L33
scuole, L34 comunità montane, ecc.) non hanno test di nome perché la
loro denominazione è troppo eterogenea per un singolo regex. **Audit
periodico raccomandato** via `scripts/_audit_all_categorie_coherence.py`
per individuare anomalie nuove. Task #10 (whitelistare MIMIT, rilassare
pattern L33).

### L2. ISTAT è la sola fonte cross-validation autoritativa

Per le altre categorie non c'è un DB esterno migliore di IndicePA stesso.
Cross-validation analoga a quella ISTAT è proposta solo per:
- **L33 Scuole** ↔ MIUR opendata (Task #9 bis)

### L3. Snapshot ISTAT è committato come blob

`data/istat_comuni.json` è ~3MB committato. Cambia di rado (semestrale).
Se cresce molto, valutare gitignore + CI download on-the-fly.

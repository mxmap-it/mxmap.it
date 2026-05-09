# mxmap.it — Pipeline di recupero dominio email

> Documenta cosa succede quando un ente IndicePA **non ha un MX risolvibile sul
> proprio Sito_istituzionale**. La pipeline tenta più strategie in ordine di
> affidabilità decrescente. Mantieni questo file aggiornato a ogni modifica
> dei layer di recupero.

Ultimo aggiornamento: 2026-05-08

## Filosofia generale

1. **Le fonti autoritative vengono prima** — un dato hand-verified (IT_MANUAL_DOMAIN_OVERRIDES)
   non viene mai sovrascritto da uno auto-scoperto.
2. **L'email non-PEC IndicePA precede sempre lo scraping** — se l'ente ha già
   dichiarato un'email funzionante, ci fidiamo di quella prima di chiedere
   al motore di ricerca.
3. **Lo scraping è l'ultima risorsa** — solo dopo che IndicePA + Wikidata
   + ricerca Wikipedia hanno fallito.

## Schema della pipeline

```
                          ┌──────────────────────────────┐
                          │   IndicePA CKAN (CSV/JSON)   │
                          └──────────────┬───────────────┘
                                         │ scripts/fetch_indicepa.py
                                         │
                ┌────────────────────────┴──────────────────────────────┐
                │   SEED-TIME OVERRIDE LAYERS (decrescente priorità)    │
                ├───────────────────────────────────────────────────────┤
                │  Tier 1   IT_MANUAL_DOMAIN_OVERRIDES                  │
                │           hardcoded in fetch_indicepa.py              │
                │           hand-verified by human                      │
                │                                                       │
                │  Tier 2   data/manual_llm_enrichment.json             │
                │           committed JSON, prodotto da Claude Code     │
                │           via scripts/generate_llm_enrichment_prompt  │
                │                                                       │
                │  Tier 3   data/enrichment_pec_only.json               │
                │           auto-generato da scripts/enrich_pec_only.py │
                │           (Wikidata P856 + Italian Wikipedia)         │
                │                                                       │
                │  Tier 4   Sito_istituzionale  (IndicePA originale)    │
                │                                                       │
                │  Tier 5   email non-PEC fallback                      │
                │           Mail{1..5} con Tipo_Mail{n} != "pec"        │
                │           (populate seed.domain_fallbacks list)       │
                └───────────────────────────────────────────────────────┘
                                         │
                                         │ seed.domain = primo Tier che vince
                                         ▼
                          ┌──────────────────────────────┐
                          │  PREPROCESS  (DNS + classify)│
                          │  src/mail_sovereignty/cli.py │
                          └──────────────┬───────────────┘
                                         │ classify() → provider tag
                                         │
                       ┌─────────────────┴─────────────────┐
                       │                                   │
                  provider==                          provider in
                  unknown                             {microsoft, google,
                  (no MX)                              aruba, regional-…}
                       │                                   │
                       ▼                                   ▼
       ┌───────────────────────────────┐         ┌──────────────────┐
       │ RECOVERY (3 STAGE PIPELINE)   │         │  data.json fully │
       │                               │         │  classified — done│
       │ R1. recover_it_unknowns.py    │         └──────────────────┘
       │     For each unknown ente,
       │     try seed.domain_fallbacks
       │     (the non-PEC email hosts
       │     from Tier 5 above —
       │     IndicePA Mail{1..5}).
       │     First with MX wins.       │
       │                               │
       │ R2. probe_it_provincial_      │
       │     backends.py +             │
       │     reclassify_it_provincial.py
       │     For comuni on shared
       │     XX.it provincial mail:
       │     probe XX.it itself,
       │     propagate backend tag.    │
       │                               │
       │ R3. finalize_it_unknowns.py   │
       │     4 sub-strategies:         │
       │       S1. cert.ruparpiemonte. │
       │           it / asmepec.it →   │
       │           regional-public     │
       │       S2. Wikidata P856       │
       │           lookup by ISTAT     │
       │           comune              │
       │       S3. homepage scrape →   │
       │           extract emails →    │
       │           MX-test each        │
       │       S4. DuckDuckGo search → │
       │           top result → scrape │
       └───────────────┬───────────────┘
                       │
                       ▼
       ┌───────────────────────────────┐
       │ POSTPROCESS                    │
       │ src/mail_sovereignty/post-     │
       │ process.py (mxmap upstream)    │
       │                                │
       │ - MANUAL_OVERRIDES dict        │
       │ - SMTP banner check            │
       │ - process_unknown() scrape!    │
       │                                │
       │ ⚠️  KNOWN BUG (2026-05-08):     │
       │   process_unknown() scrapea    │
       │   il sito web e ASSEGNA MX     │
       │   senza validare che il        │
       │   dominio email corrisponda    │
       │   all'ente. Risultato: 1.112   │
       │   tenant Microsoft di altri    │
       │   enti assegnati erroneamente. │
       │   FIX in corso.                │
       └───────────────────────────────┘
```

## Cosa viene salvato per audit

Sul singolo ente, dopo tutta la pipeline:

| Campo | Valore | Significato |
|---|---|---|
| `seed.domain` | dominio finale al SEED-TIME | qualunque Tier 1-5 ha vinto |
| `seed.domain_source` | `manual_override`, `manual_llm_enrichment`, `pec_enrichment`, `sito_istituzionale`, `email_non_pec_fallback` | quale Tier ha popolato seed.domain |
| `seed.domain_fallbacks` | lista email non-PEC hosts | input per R1 |
| `seed.domain_override_source` | tag come sopra (manual/llm/pec) | esplicito quando un override sovrascrive il Sito_istituzionale |
| `m.domain` | dominio originale (IndicePA) | preservato come audit trail |
| `m.domain_used` | dominio che HA funzionato (post recovery) | popolato da R1/R3 |
| `m.domain_correction_source` | `recover_email`, `wikidata_p856`, `homepage_scrape`, `search_engine`, ecc. | quale stage del recovery ha vinto |
| `m.mx`, `m.spf`, ... | record DNS dell'ultimo dominio testato | classify input |
| `m.provider` | tag classificato | citizen-friendly via PROVIDER_DISPLAY |
| `m.reason` | string human-readable | "MX record (X) matches Microsoft" ecc. |

## Casi speciali noti

### *.gov.it (PA centrale dopo riforma)

Dal 2022 le PA centrali stanno migrando i siti a `<sigla>.gov.it`
(es. `interno.gov.it`, `esteri.gov.it`, `mef.gov.it`). MA l'email
spesso resta sul dominio storico (`interno.it`, `esteri.it`,
`mef.gov.it` con MX o `tesoro.it`).

**Strategia attuale**:
- Tier 5 (email non-PEC IndicePA) cattura il caso quando IndicePA
  contiene `protocollo@interno.it` come Mail1.
- Verifica manuale per le PA centrali: ~50 enti C1/C2/C5/C10/C11/L46.
  Aggiungere a `IT_MANUAL_DOMAIN_OVERRIDES` quelli che IndicePA non
  copre (es. `m_it: interno.it`).

### Comuni con Sito_istituzionale defunto / typo

- Tier 1 manual override (es. `c_h413: comune.roccagorga.lt.it`)
- Tier 2 LLM enrichment per casi noti
- Tier 3 enrichment automatico (Wikidata + Wikipedia)
- R3.S2 Wikidata P856 a runtime
- R3.S4 search engine a runtime

### Enti senza alcuna presenza web (PEC-only)

- Tier 3 enrichment cerca su Wikidata + Wikipedia
- Tier 2 LLM manuale per i 603 residui (vedi `data/llm_prompt_unmapped.md`)
- Resto resta unknown legitimo.

### Provider Italiani non in keyword set

Anche se l'MX risolve, classify potrebbe taggare come "independent" se l'ASN
o l'hostname non è catalogato. Mitigazione:
- `LOCAL_ISP_ASNS` in `constants.py` (~80 ASN italiani noti)
- `ITALIAN_PROVIDER_ASN_OVERRIDES` per casi specifici (Aruba, Register, ecc.)
- `ITALIAN_AIIP_ISP_KEYWORDS` (60 domini AIIP)

Vedere `docs/countries/ITALY.md` per il dettaglio per-keyword.

## Bug noti

### Bug #1 — postprocess.process_unknown() scrape-and-assign senza validazione

**Severità**: alta. **Stato**: da fixare.

`postprocess.py:147-219` per gli enti unknown scrapea il sito web,
estrae email, MX-testa e ASSEGNA il primo MX trovato all'ente — senza
verificare che il dominio email scrappato sia legittimo per l'ente.

Risultato: ~1.112 enti hanno tenant Microsoft di un'altra entità
(es. `interno.gov.it` ha ricevuto `comune-roma-it.mail.protection.outlook.com`).

**Fix proposto**: validatore `_is_legit_email_domain(email_dom, ente_dom)`:
- accetta solo se same registrable root (interno.gov.it ↔ interno.it)
- accetta se in `IT_MANUAL_DOMAIN_OVERRIDES`
- reject altrimenti

Anche `finalize_it_unknowns.py` (S3, S4) ha il pattern e va parimenti
validato.

### Bug #2 — finalize e postprocess fanno entrambi scraping (ridondante)

`finalize_it_unknowns.py` S3+S4 + `postprocess.process_unknown` fanno
entrambi homepage scrape → email extract → MX. Il secondo passa sopra
al primo nei casi limite. Da consolidare in un unico passaggio una
volta che il fix Bug #1 è stabile.

## Riproducibilità

Tutti gli output di ogni layer sono **committati in git**:

| File | Contenuto | Cache hit-rate al re-run |
|---|---|---:|
| `data/dns_cache/it.json` | DNS query result | ~99% (TTL 7 giorni) |
| `data/enrichment_pec_only.json` | Tier 3 auto enrichment | 100% (idempotente) |
| `data/manual_llm_enrichment.json` | Tier 2 hand-curated | 100% (committed) |
| `data/it_istruzione_points.json` | Geocoding scuole | 100% (idempotente) |

Tutto sopravvive a un clean redeploy: re-run da fresh clone genera
gli stessi artifacts modulo freshness DNS.

Vedi `scripts/run_it_pipeline.sh` per la sequenza completa runnable.

# Roadmap — MxMap.it / Osservatorio Nazionale Sovranità Digitale

Derivata dalle **issue GitHub aperte** + le **dipendenze sui dati** accumulate. Ordinata per
dipendenza e impatto. Stato: giugno 2026. Vedi il contesto in [`CLAUDE.md`](../CLAUDE.md)
(§"Project context: the Italian digital-sovereignty observatory").

Le issue vivono nel repo MxMap: <https://github.com/fpietrosanti/mxmap.it/issues>.

---

## ✅ Fatto — fondamenta live

- Motore dati IT (~22.987 PA), modello di sovranità (bucket 6→4, ISD), confidence scoring (ESORICS).
- Artefatti pubblici alla root: **`kpi.json`**, **`report.json`**; pagine `statistiche.html`,
  `report.html`, `methodology.html`, `anomalie.html`.
- Nightly robusta (deploy disaccoppiato dal git, CI smoke, auto-issue); regola "numeri sempre
  testati-verificati"; dominio custom `mxmap.it`.

## Fase 1 — Baseline del dato → sblocca lo storico
**Obiettivo:** un **run #1 pulito**, così serie storiche e sezione "andamento" del report vanno live.

- **[#4] Sistemare i ~700 record PA in anomalia** — iterare a mano + automatismi per gruppo.
  *Blocca il run #1.* (Vedi `anomalie.html` + `docs/LOW_CONFIDENCE_CASES.md`.)
- **Attivare la storicizzazione** — togliere il commento agli step `historicize`/`build_dcat` in
  `nightly.yml` quando #4 è chiusa → si popolano `storia.html`, le timeline per-ente e il trend del report.

## Fase 2 — Asse geografico → attiva gli amministratori locali
**Obiettivo:** analisi "per aree" (regione → comune), la leva politica più forte (sindaci).

- **Costruire il mapping `comune→regione`** (crosswalk ISTAT / campo regione del seed) e attaccare
  una regione a ogni ente → sezione "per aree" del report, classifiche regionali, pagine per-regione.
- *Dipende in parte da #2 (qualità della fonte per un comune/territorio puliti).*

## Fase 3 — Bonifica della fonte (fondazionale)
- **[#2] Software per un IndicePA ben manutenuto e bonificato** — misura autonoma della qualità del
  dato + cicli di segnalazione (PEC a enti e AgID). Riduce le anomalie (Fase 1) e sblocca dati
  comune/dominio puliti (Fase 2). **È la dipendenza più profonda.**

## Fase 4 — Irrobustire l'attendibilità
- **[#5] Metodo basato su Email Bounce** — il *bounce-verifier* (già **progettato**,
  `docs/BOUNCE_VERIFIER_DESIGN.md`; serve `config/bounce.toml` + **autorizzazione esplicita** all'invio).
  Valida le classificazioni a bassa confidenza via smarthost + analisi NDR.

## Fase 5 — Fiducia & diagnostica
- **[#6] Pagina di diagnostica** — mostra ogni dimensione di raccolta/classificazione da IndicePA in
  poi, con un pulsante di **rendiconto problema** per ente. Si lega alla *scheda per-ente* + al
  controllo "Segnala errore" pre-compilato (task #12).

## Fase 6 — Attivazione degli stakeholder (motore di advocacy)
- **Integrazione Osservatorio** — `update-report.yml` (fetch di `report.json`) + un layout Hugo
  `report`; più i moduli d'azione per audience.
- **[#3] Emailing agli stakeholder** — tipologia di email e di report **specifica per stakeholder**,
  mappata sui dati dell'Osservatorio → trasformare i finding segmentati in azione mirata
  (decisori, stampa, sindaci, …). È il motore di "azionabilità".

---

## Cammino critico (dipendenze trasversali)

```
[#2] bonifica IndicePA ──┬─→ meno anomalie [#4] ─→ run #1 ─→ storicizzazione live
                         └─→ comune→regione pulito ─→ asse "per aree" ─→ attivazione sindaci
[#5] email-bounce ─→ confidenza più alta ─→ numeri pubblici più solidi
[#6] diagnostica + scheda per-ente ─→ [#3] attivazione stakeholder
```

**In sintesi:** le anomalie (#4) e la qualità della fonte (#2) sono il collo di bottiglia che
sblocca sia lo **storico** sia l'asse **geografico**; #5 alza la confidenza; #6 e #3 chiudono il
cerchio trasformando la misura in **azione** degli stakeholder. La scelta di priorità raccomandata:
**#4 → mapping regione → #2** in parallelo, poi #6/#3 per l'attivazione.

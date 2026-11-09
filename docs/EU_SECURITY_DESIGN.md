# EU Security Map — sovranità email del settore sicurezza europeo (design)

> Richiesta del proprietario (2026-11-09): per **tutti i paesi europei + le
> istituzioni comunitarie**, censire polizie (anche duplici, es. Polizia +
> Carabinieri), servizi di intelligence, ministeri dell'Interno e della Difesa,
> agenzie di cybersecurity e altri organismi riconducibili alla "sicurezza
> nazionale"; costruirne una **directory** (sito web + domini email);
> **scansionarli col motore mxmap**; produrre un **rendiconto aggiuntivo in
> inglese**, organizzato per paese, con statistiche, ricercabilità, bandierine,
> traduzioni inglesi dei nomi, ed evidenza di quali paesi abbiano il maggior
> **rischio di sicurezza nazionale verso gli USA** e quali siano messi meglio.

## 1. Perimetro

**49 "paesi"**: UE-27 + EFTA (CH, NO, IS, LI) + UK + candidati/potenziali
(AL, BA, GE, MD, ME, MK, RS, TR, UA, XK) + microstati (AD, MC, SM, VA) +
**annex non allineato** (RU, BY — nella directory e nella scansione, fuori dal
ranking headline, che misura l'esposizione dell'Europa alleata/allineata) +
**EU** (istituzioni comunitarie: Europol, Frontex, ENISA, CERT-EU, EEAS, EDA,
SatCen, eu-LISA, EPPO, OLAF, ECCC, DG HOME/DEFIS, Consiglio). Armenia e
Azerbaigian esclusi (Caucaso; nota in metodologia).

**Categorie** (`type`): `police`, `gendarmerie`, `border_guard`,
`intelligence`, `interior_ministry`, `defence_ministry`, `cybersecurity`,
`other_natsec`. Target 5–12 enti/paese (~350–450 enti totali).

## 2. Dati

- `data/eu_security/research/{cc}.json` — output grezzo della ricerca (un file
  per paese, con `evidence` per ogni dominio email: URL ufficiale dove
  l'indirizzo è stato visto, `kind`, esempio). Committati: sono il lavoro
  costoso (restore, don't regenerate).
- `data/eu_security/entities.json` — directory consolidata e validata (merge +
  controlli: id unici, cc validi, type validi, domini sintatticamente validi e
  **risolvibili in DNS** — un dominio senza NS/MX resta ma marcato).
- `data/eu_security/results.json` — output scansione (per dominio: MX, SPF,
  DKIM, autodiscover, tenant, provider, reason, confidence, mx_countries) +
  verdetto per ente.
- `eu-security/kpi.json` — KPI aggregati per il rendiconto.

## 3. Scansione — riuso del motore, zero tocchi alla pipeline IT

`scripts/scan_eu_security.py` riusa `preprocess.scan_municipality` (accetta
qualunque ente con `website`; niente guessing: `name` non usato per indovinare
domini perché passiamo domini espliciti) con `DnsCache("EUSEC")`, concurrency
≤10. **Non tocca `data.json`**, né nightly, né KPI italiani: dataset, cache e
artefatti separati. Un ente con più domini email → si scansiona ogni dominio;
il verdetto dell'ente è il dominio "primario" (il primo evidenziato), gli altri
riportati.

## 4. Modello di sovranità (relativo al paese dell'ente)

Nuovo modulo `src/mail_sovereignty/eu_security.py` (unit-testato, integrità a
runtime come da regola KPI):

- `PROVIDER_COUNTRY`: mappa provider→paese sede legale (microsoft/google/aws →
  US; ovh/gandi/scaleway → FR; hetzner/ionos → DE; infomaniak → CH; aruba,
  register, seeweb, … → IT; zoho → IN; yandex → RU; …).
- Bucket per ente nel paese C: **`national`** (provider con sede in C, o
  `independent`/self-hosted con MX in C), **`us`** (provider USA → CLOUD Act),
  **`eu_other`** (provider UE di altro stato membro), **`other_foreign`**
  (estero non-UE non-USA), **`unknown`**. Per gli `independent` il paese viene
  da `mx_countries` (giurisdizione di hosting; per i provider noti è
  giurisdizione legale — distinzione dichiarata in metodologia).
- Per le istituzioni EU: `national` = self-hosted/provider UE in-house;
  qualunque provider UE commerciale → `eu_other`.
- **Indicatori**: per paese, `us_exposure_pct` (% enti classificati su provider
  USA) = metrica di rischio headline; `national_pct` = "best positioned".
  Ranking solo per paesi con ≥5 enti classificati.

## 5. Rendiconto (inglese) — `https://mxmap.it/eu-security/`

`scripts/build_eu_security_page.py` genera `eu-security/index.html`
(**committata**; il deploy la pubblica col sito):

- **Lingua inglese**; bandierine **SVG vendorizzate** in `eu-security/flags/`
  (da flag-icons, MIT — niente CDN, niente emoji: su Windows le flag emoji non
  renderizzano).
- Hero + **caveat box** (vedi §6), statistiche headline (bucket complessivi,
  per categoria di ente), **ranking**: "Highest US-exposure" e "Best
  positioned" con barre e bandierine; sezioni per paese (flag, nome, tabella
  enti: nome nativo, **nome inglese**, tipo, sito, dominio email, provider,
  bucket, confidence); **ricerca client-side** (filtro live su nome/paese/
  tipo/provider) + filtri per categoria e bucket; metodologia in calce con
  link a `methodology.html`.
- RU/BY in sezione annex separata, esclusi dal ranking.

## 6. Framing editoriale (vincolante)

Tono **policy/resilienza**, mai sensazionalistico (coerente con la regola
"security/defense via policy framing" di CLAUDE.md): il rischio misurato è
l'**esposizione giurisdizionale della posta elettronica pubblica/non
classificata** (CLOUD Act: accesso a contenuti e metadati su ordine USA).
Caveat obbligatorio in cima al report: *le reti classificate dei servizi sono
separate by design; questo osservatorio misura l'infrastruttura email
pubblica — che però veicola comunicazioni istituzionali reali, PNR/estradizioni/
cooperazione, e i cui metadati sono essi stessi sensibili*. Nessuna
"accusa": lettura comparativa, best practice in evidenza quanto i rischi.

## 7. Operatività

- Workflow `.github/workflows/eu-security.yml`: **settimanale** (lun 05:30
  UTC) + `workflow_dispatch`: scan → build KPI+pagina → commit (best-effort,
  stesso pattern tollerante della nightly; il deploy parte dal push). Script
  coperti dal job `smoke` di `ci.yml` (py_compile + coda deterministica su
  dati committati).
- Test: `tests/test_eu_security.py` — schema directory, matrice bucket
  (valori attesi a mano), `assert_integrity` (somme, ranking coerente,
  nessun paese perso), smoke del page-builder.

## 8. Fuori perimetro (per ora)

- Verifica attiva (bounce/DMARC/MDN) sui domini esteri: la specifica
  `docs/ACTIVE_VERIFICATION_DESIGN.md` nasce per il dataset IT; estenderla a
  servizi di sicurezza esteri è una **decisione del proprietario** caso per
  caso.
- Integrazione Osservatorio (news/pagina dedicata): dopo la prima
  pubblicazione del rendiconto.

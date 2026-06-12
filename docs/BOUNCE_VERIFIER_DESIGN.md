# Bounce-verifier — design (analisi e raffinamento, pre-implementazione)

Verifica attiva del backend di posta per i casi a bassa confidenza
(`docs/LOW_CONFIDENCE_CASES.md`): 69 enti / **67 domini**, regola
`frgn_mx_only` (MX presente, ma backend ignoto). Obiettivo: identificare l'MTA
reale e correggere `provider` / `mx_jurisdiction` / `classification_confidence`.

> **Stato: SOLO DESIGN.** Nessun invio, nessun probe eseguito. Da discutere
> prima di fare alcunché (anche la Fase 1 tocca gli MX di terzi).

## 1. Requisiti (dall'utente) → come li soddisfa il design

| # | Requisito | Sezione |
|---|---|---|
| R1 | Distinguere controllo destinatario a **RCPT TO** vs **ingestion + bounce** | §3 (due fasi) |
| R2 | Email con header/oggetto/contenuto forti anti-spam | §5 (deliverability) |
| R3 | Rate-limit per **MX e IP** di destinazione; preparare prima il **pool** | §6 (pool) |
| R4 | **Log** preciso | §7 (schema JSONL) |
| R5 | Accesso **IMAP** per le bounce | §8 (cattura NDR) |
| R6 | Rendiconto **sintetico** + **analitico** | §9 (report) |

## 2. Dati che guidano il design (concentrazione dei 67 domini)

- 51 MX-host distinti → **39 IP di destinazione** distinti (25/51 MX risolti dal
  laptop; **26 non risolvono** — MX vanity di micro-comuni).
- **Hotspot (vanno serializzati):** `relay-rupar-pri.regione.fvg.it` = 9 domini;
  blocco Aruba `62.149.128.0/24` = 2–3 domini/IP; `15.160.99.155` = 4 domini;
  Sophos-hydra su AWS `52.28/52.57`.
- **Riclassificazione attesa:** ASN 16509 (AWS) ×11, Google Cloud ×3 → diversi
  enti "foreign/independent" sono in realtà Aruba/Google/AWS → il probe corregge
  provider e sovranità. Questo è il guadagno principale.
- **26 MX non risolvibili** = esito "posta irraggiungibile/rotta" → il probe va
  eseguito **dal server** (vantage reale), perché risoluzione, reachability e
  reputazione IP dipendono dal punto di invio.

## 3. Architettura a due fasi (cuore del refinement, R1)

### Fase 1 — Probe SMTP RCPT TO (sincrono, NESSUNA email inviata)

Per ogni dominio: risolvi MX → `connect MX:25` → `EHLO` → `MAIL FROM:<probe>` →
`RCPT TO:<inesistente@dominio>` → leggi la risposta. **Non si invia mai DATA.**

Esiti possibili:

| risposta RCPT TO | significato | serve Fase 2? |
|---|---|---|
| **5xx** (user unknown) | il server **valida i destinatari** (mailstore integrato). Il banner EHLO + il testo 5xx spesso nominano il backend (Postfix virtual, Exchange, Zimbra, Aruba…) | **No** — risolto qui |
| **2xx** (accept) | accetta destinatari ignoti (catch-all / validazione differita / gateway che inoltra) | **Sì** → Fase 2 |
| **4xx / greylist** | rinvio temporaneo | retry |
| connect refused / timeout | MX irraggiungibile (i 26 non risolti?) | esito "unreachable" |

Fase 1 è un'estensione del probe SMTP già presente in MX Map (che legge solo il
banner): qui aggiungiamo il **comportamento di validazione destinatario** e il
**testo esatto del rifiuto**, che è ciò che identifica il backend. **La maggior
parte dei casi si chiude in Fase 1 senza inviare nulla.**

### Fase 2 — Invio reale + NDR asincrono (solo per i 2xx-at-RCPT)

Solo per i domini che in Fase 1 accettano il destinatario ignoto: si invia una
email ben formata (§5), si attende il bounce asincrono via IMAP (§8), si parsa
l'NDR per estrarre l'MTA reale. Se **nessun bounce** arriva entro la finestra →
esito "accept-silent" (ingerita e non rimbalzata → catch-all o drop silenzioso).

## 4. Tassonomia degli esiti (per i report)

`rcpt_rejected` (backend identificato dal 5xx) · `accept_then_bounce` (backend
dall'NDR) · `accept_silent` (nessun bounce) · `mx_unreachable` (no connect/no
DNS) · `tempfail` (4xx persistente). Ogni esito → eventuale nuovo
`provider`/`jurisdiction`/`confidence`.

## 5. Deliverability dell'email di Fase 2 (R2)

- **Mittente:** mailbox reale su dominio Workspace dedicato con **SPF + DKIM +
  DMARC** allineati (altrimenti molti MX rifiutano o filtrano).
- **Header:** `Message-ID` valido, `Date`, MIME multipart (text + HTML),
  `Auto-Submitted: auto-generated` (RFC 3834, evita loop di auto-risponditori),
  `Precedence: bulk`, `Return-Path` VERP (§8).
- **Oggetto/corpo:** trasparenti e non spammosi — es. oggetto *«Verifica tecnica
  di recapito — Osservatorio mxmap.it»*; corpo che spiega che è un probe
  automatico di un osservatorio di pubblico interesse, con link al progetto e
  contatto, e invito a ignorare. (Etica + se un catch-all lo fa leggere a un
  umano, è onesto + riduce il rischio spam/abuse-report.)
- **Un solo probe per dominio** (dedup: 67, non 69).

## 6. Pool di invio e rate-limit (R3) — da preparare PRIMA

Il pool è una **coda pianificata** costruita prima di qualsiasi invio:

- **Chiave di serializzazione = IP di destinazione** (non solo dominio): mai due
  connessioni concorrenti allo stesso IP; ritardo minimo (es. 30–60 s) tra hit
  sullo stesso IP/MX. Hotspot noti: l'IP Aruba con 4 domini, il blocco
  `62.149.128.x`, il relay `regione.fvg.it` (9 domini).
- **Tetto globale** (es. N invii/ora) per proteggere la reputazione del mittente
  Workspace; ordine randomizzato con jitter.
- La coda raggruppa per IP→MX→ASN e distanzia gli stessi gruppi nel tempo.
- Fase 1 (RCPT, no mail) ha vincoli più leggeri ma resta gentile (1 connessione
  per IP alla volta) per non farsi tarpittare/bloccare.

## 7. Logging (R4) — JSONL, un record per tentativo

Campi: `ts`, `domain`, `mx_host`, `mx_ip`, `phase` (`rcpt`|`send`),
`smtp_banner`, `ehlo_features`, `starttls`, `mail_from_resp`, `rcpt_code`,
`rcpt_text`, `outcome`, `message_id`, `verp_token`, `error`. Per gli NDR:
`ts_received`, `verp_token`, `ndr_action`, `ndr_status`, `diagnostic_code`,
`remote_mta`, `reporting_mta`, `identified_backend`. File:
`data/bounce/probe_log.jsonl` (append-only, idempotente per dominio+giorno).

## 8. Cattura NDR via IMAP (R5) + correlazione VERP

- **VERP** (Variable Envelope Return Path): envelope-from per ogni invio =
  `bounce+{token}@dominio-mittente`, dove `token` codifica il dominio target →
  il bounce si auto-correla senza dipendere dal parsing fragile del corpo.
- Poll IMAP della casella mittente; per ogni NDR: estrai il `token` dal
  destinatario/Original-Recipient, poi parsa la parte `message/delivery-status`
  (`Diagnostic-Code`, `Remote-MTA`, `Reporting-MTA`) → backend reale.
- Finestra d'attesa (es. 24–48 h) prima di marcare `accept_silent`.

## 9. Report (R6)

- **Sintetico** (`data/bounce/report_summary.{md,json}`): conteggi per esito,
  per backend identificato, n. enti **riclassificati** (foreign→domestic, o
  independent→provider reale), per infrastruttura MX. Headline tipo: «X/67
  risolti a un backend reale; Y riclassificati da estero a Aruba/Italia».
- **Analitico** (`data/bounce/report_detail.csv`): una riga per dominio con
  l'intera transazione SMTP, il backend identificato, e
  `old→new` di provider/jurisdiction/confidence + evidenza.

## 10. Esecuzione a stadi, vantage, prerequisiti, decisioni aperte

**Staging consigliato:**
1. **Fase 1 su tutti i 67** (RCPT, nessun invio) → quanti si chiudono senza mail.
2. Solo sul residuo `2xx-at-RCPT` → **Fase 2** (invio + NDR).

**Vantage:** eseguire **dal server** `mxmap.it@…` (non dal laptop): risoluzione,
reachability e reputazione IP dipendono dal punto di invio. La Fase 2 **invia
attraverso lo smarthost autenticato di Google Workspace** (SPF/DKIM allineati),
non in SMTP diretto dall'IP del server (reputazione scarsa).

**Prerequisiti per la Fase 2 (forniti dall'utente al momento giusto):** dominio
+ account Workspace mittente con SPF/DKIM/DMARC; credenziali SMTP submission +
IMAP (in un file di config non committato); autorizzazione esplicita all'invio.

**Decisioni aperte:**
- D1. Procediamo a stadi (Fase 1 prima, poi Fase 2 sul residuo)? *(consigliato)*
- D2. Fase 1 è accettabile come primo passo eseguibile (non invia email, ma apre
  connessioni SMTP verso MX di terzi)? Da dove la lanciamo?
- D3. Per i 26 MX non risolvibili: trattarli subito come `mx_unreachable`/verso
  unknown, o ritentare dal server prima di concludere?
- D4. Testo/branding dell'email di Fase 2: confermi il tono «osservatorio di
  pubblico interesse, ignorare»?

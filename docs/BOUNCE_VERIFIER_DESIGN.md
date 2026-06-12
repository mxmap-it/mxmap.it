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
| R1 | Invio via smarthost; la validazione destinatario emerge **dall'NDR** | §3 (smarthost + NDR) |
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

## 3. Flusso: invio via smarthost + analisi dei bounce/NDR (R1)

Si **invia** un'email di test a un indirizzo inesistente di ogni dominio
**attraverso lo smarthost autenticato** (Workspace, SPF/DKIM/DMARC allineati →
buona deliverability). **Niente direct-to-MX** (finirebbe in spam) e **niente
RCPT TO sincrono**. Gli esiti si leggono **dai bounce/NDR** che tornano alla
casella mittente.

Per ogni dominio: apri **una** connessione allo smarthost (riusata per tutti) →
`sendmail(<VERP>, <inesistente@dominio>, email)` → lo smarthost accetta e
rilancia → (asincrono) eventuale **NDR** alla casella VERP → IMAP + `parse_ndr`.

| esito | come si determina | il backend si legge da |
|---|---|---|
| `bounced` | è arrivato un NDR correlato al token VERP | `Diagnostic-Code`/`Remote-MTA` dell'NDR (es. «550 User unknown» da `mx.aruba.it`) |
| `no_bounce` | inviato, nessun NDR nella finestra | — (catch-all / accettato / drop silenzioso) |
| `not_submitted` | lo smarthost ha rifiutato l'invio | errore SMTP locale |

Nota (R1): il fatto che il destinatario validi o no l'indirizzo emerge
**comunque**, ma dall'NDR (asincrono) invece che da una RCPT TO sincrona. Un
«550 User unknown» nell'NDR dice che il backend valida i destinatari e ne nomina
l'MTA. Per i 26 MX non risolvibili, è lo smarthost stesso a generare subito un
NDR di «DNS/no route» → esito anomalo registrato.

## 4. Tassonomia degli esiti (per i report)

`bounced` (NDR ricevuto → backend identificato) · `no_bounce` (inviato, nessun
NDR → catch-all/accettato/silent) · `not_submitted` (smarthost ha rifiutato).
Ogni `bounced` con backend noto → eventuale nuovo
`provider`/`jurisdiction`/`confidence` (riconciliazione).

## 5. Deliverability dell'email di test (R2)

- **Mittente:** mailbox reale su dominio Workspace dedicato con **SPF + DKIM +
  DMARC** allineati (altrimenti molti MX rifiutano o filtrano).
- **Header:** `Message-ID` valido, `Date`, MIME multipart (text + HTML),
  `Auto-Submitted: auto-generated` (RFC 3834, evita loop di auto-risponditori),
  `Precedence: bulk`, `Return-Path` VERP (§8).
- **Oggetto/corpo:** trasparenti, non spammosi e che **dichiarano esplicitamente
  che è un test**. Oggetto: *«[TEST] Verifica tecnica di recapito — Osservatorio
  mxmap.it»*; corpo che spiega che è un **test automatico** di recapito di un
  osservatorio di pubblico interesse, con link al progetto e contatto, e invito
  a ignorare. (Etica + se un catch-all lo fa leggere a un umano è onesto +
  riduce il rischio spam/abuse-report.)
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

**Staging (un'unica passata di invii, non due fasi):**
1. Costruisci il **pool** serializzato per IP (§6).
2. **Invia sempre** (un tentativo per dominio, registrando `rcpt_validation`),
   rispettando il rate-limit; logga ogni transazione (§7).
3. **Finestra di raccolta NDR** (24–48 h) via IMAP per i casi `accepted_2xx`.
4. Riconcilia e genera i report (§9).

**Vantage:** eseguire **dal server** `mxmap.it@…` (non dal laptop): risoluzione,
reachability e reputazione IP dipendono dal punto di invio. L'invio passa
**attraverso lo smarthost autenticato di Google Workspace** (SPF/DKIM allineati),
non in SMTP diretto dall'IP del server (reputazione scarsa).

**Configurazione (predisposta):** `config/bounce.example.toml` → copiare in
`config/bounce.toml` (gitignorato) con login/password/host **SMTP (smtp+TLS)** e
**IMAP (imaps)**, mittente, VERP, rate-limit e `ndr_wait_hours`. Fornita
dall'utente al momento dell'invio.

**Decisioni — CHIUSE:**
- D1 ✅ **invio via smarthost + analisi NDR** (niente direct-to-MX né RCPT TO
  sincrono: finirebbe in spam — gli esiti si leggono dai bounce).
- D2 ✅ invio **dal server** via **smarthost Workspace autenticato** (smtp/TLS).
- D3 ✅ i non risolvibili → marcati `mx_unreachable` **e** confluiscono nel
  tracking trasversale delle **anomalie** (§11).
- D4 ✅ email trasparente che **dichiara esplicitamente che è un test**.
- D5 ✅ finestra NDR **48 h** (configurabile, `ndr_wait_hours`).

## 11. Anomalie — metadato trasversale (TODO, oltre il bounce)

Tutto ciò che è **non risolvibile / incoerente** non va perso: è un metadato da
**raccogliere, contare, e visualizzare anche sulla mappa**, non solo nel bounce.

**Quantificazione attuale (da `data.json`, senza nuovo DNS): ~767 enti (3,3%)**
= nessun MX (659) ∪ MX presente ma geo non risolta (77) ∪ bassa confidenza (99).
Di cui **138 classificati ma comunque anomali** (provider dato, evidenza debole).
Provider tra le anomalie: unknown 629, independent 101, regional-public 30,
microsoft 5, google 2.

**Piano (TODO):**
- Campo/metadato `anomaly` per ente (es. `no_mx`, `mx_unresolved`,
  `mx_unreachable` (dal bounce), `low_confidence`, `geo_unknown`).
- Il bounce-verifier **alimenta** questo metadato (i `mx_unreachable` reali).
- Conteggio aggregato + per-tipo, esposto come **report web di anomalie**
  dedicato (3,3% giustifica una pagina propria) e come **layer/filtro sulla
  mappa** (evidenziare gli enti anomali).
- Un vero conteggio di `mx_unresolved` su tutti i 22.987 richiede una passata DNS
  dedicata (il bounce la produce per i 67; estendibile a tutto il dataset).

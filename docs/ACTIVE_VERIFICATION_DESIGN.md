# Verifica attiva unificata — bounce, DSN, MDN, report DMARC, auto-reply (spec)

> Richiesta del proprietario (2026-11-09): riprendere i ticket di ricerca sulla
> verifica attiva (invio proattivo di email, stimolo di report DMARC, read
> notification, email a utente inesistente) e consolidarli in **un'unica
> modalità di analisi complessiva**: come funzionerebbe, cosa va verificato e
> testato sul campo, e quali livelli di confidenza permetterebbe
> ragionevolmente di risolvere o ridurre.
>
> Consolida: #5 (bounce), `docs/BOUNCE_VERIFier_DESIGN.md` (che resta il
> design di dettaglio del canale C1/invio), #32 R3 (roadmap Sconosciuto),
> #22/#23 (fingerprinting passivo, complementare). Stato: **SOLO DESIGN** —
> nessun invio senza decisione esplicita del proprietario.

## 1. Popolazioni target e guadagno atteso (dati live 2026-11-09)

| Coorte | n | Oggi | Guadagno possibile |
|---|---|---|---|
| `gateway_no_primary` (Sconosciuto con MX dietro security gateway) | **677** | confidence 0,0 | **il target principale**: identificare il backend reale dietro il gateway |
| `no_mx` (Sconosciuto senza MX) | 624 | confidence 0,0 | nessuna classificazione possibile; la verifica attiva **conferma** solo "posta irraggiungibile" (attendibilità del verdetto negativo, alimenta #2/outreach) |
| Banda bassa/media (0,4–0,79: fallback 0,40–0,42, spf_gw 0,70, dom_mx_only 0,70…) | ~2.000 | verdetto presunto | promozione a banda alta con evidenza misurata |
| `frgn_mx_only` (storico #5) | ~67 | backend ignoto | riclassificazione estero→reale (spesso Aruba/AWS/Google) |

## 2. Principio unificante: un invio, più canali di evidenza

**Un solo messaggio trasparente per dominio**, inviato via smarthost
autenticato (SPF/DKIM/DMARC allineati, design #5), progettato per
massimizzare le **risposte automatiche** che tornano; ogni risposta è
un'evidenza indipendente sul backend reale, letta **dagli header**. Nessuna
interazione umana richiesta; se avviene (MDN, auto-reply) è un canale in più.

| Canale | Meccanismo | Cosa torna | Chi si identifica | Vale anche se… |
|---|---|---|---|---|
| **C1 — NDR** (utente inesistente) | RCPT a `probe-{token}@dominio` inesistente | NDR/bounce RFC 3464 | `Remote-MTA`/`Diagnostic-Code` → MTA che valida le caselle | il gateway inoltra e il backend rifiuta |
| **C2 — DSN di consegna** | `NOTIFY=SUCCESS,FAILURE` (RFC 3461) su indirizzo istituzionale pubblico | DSN "delivered" | `Reporting-MTA` = MTA finale | la casella esiste (niente NDR) |
| **C3 — MDN / read notification** | header `Disposition-Notification-To` (RFC 8098) | MDN se MUA/utente conferma | `User-Agent`/`Received` del MDN → backend + client | solo con lettura umana (tasso basso: bonus, mai requisito) |
| **C4 — Report aggregati DMARC** | il **nostro** dominio mittente pubblica `rua=`; l'invio raggiunge il backend | XML aggregate report entro 24–72h | `org_name` del report (es. google.com, Microsoft, provider IT) = **chi ha ricevuto davvero** | **anche con catch-all, drop silenzioso o zero risposte** — il backend si auto-denuncia |
| **C5 — Auto-reply / OOO / ticket** | qualunque invio | risposta automatica | `Received` chain, pattern `Message-ID` (`*.prod.outlook.com`, `mail-sor-*.google.com`), firma DKIM | il dominio usa risponditori/ticketing |

**C4 è la chiave per i 677 `gateway_no_primary`**: distingue "dietro Sophos
c'è M365/Google" (entrambi generano report rua affidabilmente) da "dietro
Sophos c'è un MTA on-prem" (quasi mai genera rua → l'assenza, combinata con
un NDR C1 dal gateway stesso, è a sua volta indicativa). C1–C2–C4 non
richiedono alcun umano; C3–C5 sono opportunistici.

## 3. Analisi header comune (il cuore "di specificazione")

Un parser unico `analyze_response(message) -> Evidence` per tutto ciò che
arriva nella casella di raccolta:

1. **Classifica il tipo**: `ndr` (RFC 3464 `message/delivery-status`), `dsn`
   positivo, `mdn` (RFC 8098 `message/disposition-notification`), `dmarc_rua`
   (XML/zip su casella `rua`), `autoreply` (RFC 3834 / In-Reply-To), `other`.
2. **Correla** al probe via token VERP nell'envelope/Original-Recipient
   (design #5 §8) o, per i rua, via dominio sorgente nel report.
3. **Determina l'origine** (`sender` / `gateway` / `destination`): catena
   `Received`, `Reporting-MTA`, `Remote-MTA`, IP/ASN (riusa `resolve_mx_asns`)
   — solo `gateway`/`destination` valgono come evidenza del backend (regola
   già chiusa in #5 §8).
4. **Mappa a provider** riusando `PROVIDER_KEYWORDS`/`SMTP_BANNER_KEYWORDS` su
   hostname/Message-ID/firme DKIM; per i rua, mappa `org_name`→provider
   (tabella nuova, piccola: Microsoft, google.com, Yahoo, i provider IT che
   generano report).
5. Scrive un record JSONL per risposta (schema #5 §7 esteso con
   `channel` ∈ {ndr,dsn,mdn,dmarc_rua,autoreply} e `org_name`).

## 4. Fusione delle evidenze → livelli di confidenza

Riconciliazione per dominio al termine della finestra (72h):

| Evidenza disponibile | Esito | Confidence proposta |
|---|---|---|
| C4 `org_name` **oppure** C1/C2 con `Remote-MTA`/`Reporting-MTA` = provider noto (origine `destination`) | nuova regola **`active_verified`** | **0,90–0,95** (banda alta; scala attendibilità A-v: misurato da noi) |
| Solo C5/C3 (header chain concorde con un provider) | conferma `active_hint` | promozione di un gradino (es. 0,40→0,70; 0,70→0,80), mai oltre 0,85 |
| Canali **discordanti** (es. rua da Microsoft ma NDR destination Google) | anomalia dedicata `active_conflict` | nessuna promozione; review manuale (può essere split-delivery reale) |
| Nessuna risposta su nessun canale | `no_signal` | invariato; registrato (utile come denominatore dei tassi) |
| NDR `sender` (il nostro relay non instrada) | `mx_unreachable` | conferma anomalia, alimenta #2 |

Le nuove evidenze **non** entrano in `classify()` al volo: confluiscono in un
file `data/active_verification/evidence.json` che la pipeline consuma come
override documentato (pattern `MANUAL_OVERRIDES`/#31: evidenza committata,
ripetibile, con URL... qui con il record di risposta grezzo), così il nightly
resta deterministico e il meccanismo è auditabile.

**Riduzione ragionevolmente attesa degli Sconosciuto** (da validare col
pilota, §5): i 677 `gateway_no_primary` hanno per costruzione posta
funzionante; se la quota di backend cloud dietro gateway è simile alla coorte
risolta (dove M365/Google dominano), C4+C1 dovrebbero risolverne **~60–85%**
(400–575 enti → Sconosciuto dal 5,7% verso ~3,2–4,0%, coerente col target <3%
di #32 combinato con fingerprinting #22/#23 e IndicePA #2). I 624 `no_mx`
restano irrisolvibili per definizione (serve outreach, #32 R4).

## 5. Cosa va verificato e testato sul campo (prima di qualunque run di massa)

| # | Test | Domanda | Go/no-go |
|---|---|---|---|
| T1 | Smarthost | il relay Workspace preserva l'envelope-from **VERP** per-messaggio e propaga `NOTIFY=` (submission autenticata riscrive l'envelope; serve lo *SMTP relay service*, non smtp.gmail.com)? | VERP intatto nel bounce di un dominio di controllo |
| T2 | Controlli positivi/negativi | batteria su ~20 domini a verdetto GIÀ noto e solido (10 M365, 5 Google, 5 on-prem/vendor IT): C1 e C4 rispondono come atteso? | ≥80% dei controlli positivi produce evidenza corretta; **zero** evidenze sbagliate |
| T3 | Attraversamento gateway | su 10 `gateway_no_primary` campione: il probe supera il gateway (arriva NDR `destination` o report rua) o muore al gateway (NDR `gateway`/nulla)? | ≥50% produce segnale utilizzabile |
| T4 | Tassi C3/C5 | quanto rendono MDN e auto-reply su caselle istituzionali (URP/contatti pubblici)? | solo misura, nessun gate |
| T5 | Reputazione | pilota 50 domini, rate-limit per IP (design #5 §6): bounce-rate del mittente e reputazione restano sani? | nessun blocco/blacklist del dominio mittente |

Prerequisiti di T1–T5: dominio mittente dedicato con SPF/DKIM/DMARC `rua=`
già pubblicati **almeno una settimana prima** (i ricevitori diffidano dei
domini neonati), casella IMAP di raccolta, `config/bounce.toml`.

## 6. Etica, trasparenza, perimetro

- **Un solo messaggio per dominio**, oggetto e corpo che dichiarano
  esplicitamente il test (design #5 §5), contatto e link al progetto,
  invito a ignorare; rate-limit per IP/MX; log completo append-only.
- Perimetro: **solo PA italiane del dataset mxmap.it**. L'estensione ai
  domini del dataset EU Security (#33) — in particolare a servizi esteri —
  è una **decisione esplicita del proprietario**, caso per caso.
- Gli indirizzi reali usati per C2/C3 sono solo caselle istituzionali
  pubbliche (URP, uffici stampa), mai persone.

## 7. Decisioni aperte (proprietario)

- D1: smarthost e dominio mittente dedicato (chi lo fornisce, quale dominio).
- D2: go per la fase pilota T1–T5 (≈70 invii totali).
- D3: soglia di promozione automatica vs review manuale per `active_verified`.
- D4: estensione futura al dataset #33 (default: no).

# Casi a bassa confidenza — documentazione e piano di test (bounce)

Analisi dei casi dove la classificazione del provider email è **meno certa**,
con l'obiettivo di impostare la verifica attiva via **bounce-probing**.
Sorgente: `data.json` (campo `classification_confidence` del modello ESORICS).
Generato a mano da `scripts/report_confidence.py` + analisi dedicata.

## 1. Quantità — distribuzione della confidenza (22.987 enti IT)

| fascia | enti | % | ha MX? | bounce-testabile? |
|---|---:|---:|---|---|
| **alta** ≥ 0,80 | 21.002 | 91,4% | sì | non serve (già certa) |
| **media** 0,60–0,79 | 1.257 | 5,5% | sì (tutti) | sì, target secondario |
| **bassa** 0,01–0,59 | **99** | 0,4% | 69 sì / 30 no | **target primario (69)** |
| **unknown** 0,00 | 629 | 2,7% | no (nessun MX) | no → serve *discovery* |

Punto chiave: «bassa confidenza» e «non verificabile» **non coincidono**. Il
bounce funziona solo se l'ente **ha un MX** a cui inviare. Quindi i 629 unknown
(nessun MX) e 30 dei 99 «bassa» (nessun MX) **non** sono bounce-testabili —
sono un problema di *scoperta del dominio*, non di *verifica del backend*.

## 2. Qualità — i 99 «bassa» sono due problemi diversi

### 2a. `frgn_mx_only` — 69 enti, conf 0,50 — **IL target del bounce**

Hanno un **MX che risponde**, ma **nessun SPF e nessun DKIM** che corrobori chi
sta dietro. Vediamo *dove* va la posta (l'hostname MX) ma non possiamo provare
*chi* la gestisce → etichettati `independent` / "self-hosted, backend unknown".

- **Sotto-tipi:** 60 self-hosted puri · 9 dietro un gateway con backend ignoto.
- **Tipologia ente:** 37 comuni (piccolissimi), 25 enti vari, 6 ordini/collegi
  professionali, 1 unione.
- **Hoster MX ricorrenti:** `fvg.it` (16, infra regionale Friuli/Insiel),
  `mailspamprotection.com` (6), `sophos.com` (6), `firewallsrl.com` (6),
  `cn.it`/`vc.it` (infra provinciali), `gecomail.net`, `lonex.com`, `dcssrl.it`.
- **Cluster geografico evidente:** comuni della Valsesia (VC) su MX vanity
  `mail.comune.X.vc.it` (Cervatto, Fobello, Scopello, Vocca…).

Esempi:

| ente | dominio | MX | perché 0,50 |
|---|---|---|---|
| Consiglio Notarile di Padova | consiglionotarilepadova.it | mail.consiglionotarilepadova.it | self-hosted, no SPF/DKIM |
| Ordine Ostetriche (FNCO) | fnco.it | gateway mailspamprotection | backend dietro gateway ignoto |
| Ordine Avvocati Pinerolo | ordineavvocatipinerolo.it | mail.dcssrl.it | self-hosted su hoster terzo |
| Comune di Vocca | comune.vocca.vc.it | mail.comune.vocca.vc.it | MX vanity, nessuna corroborazione |

> **Nota giurisdizione:** solo 31/69 hanno `mx_countries` risolto (ASN). Gli
> altri 38 restano giurisdizione `unknown` ma sono **scorati conservativamente
> come foreign** (`frgn_*`), perché in dubbio il modello ESORICS non assume
> sovranità. Il bounce + un nuovo lookup ASN risolverebbe **sia** il backend
> **sia** la giurisdizione.

### 2b. `fallback` — 30 enti, conf 0,40 — **NON bounce-testabili**

**Nessun MX.** Sono entry «only-PEC»: l'unica evidenza di posta è una PEC su
`cert.ruparpiemonte.it`, da cui inferiamo `regional-public` (CSI Piemonte /
RUPAR). Piccoli comuni piemontesi (Massello, Salza di Pinerolo, Torre Canavese,
Vallo Torinese…): 20 comuni, 5 unioni, 5 vari.

Senza MX non c'è nulla a cui inviare → il bounce non si applica. La confidenza
è bassa perché l'attribuzione è **indiretta** (dalla PEC, non dai record di
posta operativa). Verifica possibile solo per altre vie (conferma che il
dominio non abbia davvero posta operativa propria).

## 3. Fascia media (1.257, conf 0,60–0,79) — target secondario

Tutti `independent` con **MX presente** → tutti bounce-testabili. Due regole:

- `frgn_mx_spf` (1.001, conf 0,60): MX + SPF ma backend estero/ignoto
  (es. Ordine Giornalisti VdA dietro Sophos; Collegio Geometri BZ su firma5.com).
- `dom_mx_only` (256, conf 0,70): MX domestico, no SPF (es. Notai Brindisi/
  Catanzaro su cbsolt.net; Periti Agrari PD su ezenia.it).

Sono già ragionevolmente caratterizzati; il bounce **confermerebbe** l'MTA reale
ma il guadagno informativo è minore che sui 69 a 0,50.

## 4. Cosa il bounce risolve (e cosa no)

| coorte | n | bounce serve? | cosa rivela |
|---|---:|---|---|
| `frgn_mx_only` 0,50 | 69 | **sì, prioritario** | banner/MTA reale del backend self-hosted/gateway |
| media 0,60–0,79 | 1.257 | sì, secondario | conferma MTA, raffina provider |
| `fallback` 0,40 (no MX) | 30 | no | niente a cui inviare; serve altra verifica |
| unknown 0,00 (no MX) | 629 | no | serve *discovery* del dominio, non verifica |

## 5. Piano di test proposto (pilota)

1. **Pilota sui 69 `frgn_mx_only`** — set piccolo, tutti con MX, backend
   genuinamente ignoto: massimo guadagno informativo.
2. Per ciascuno: invio a indirizzo inesistente `{random}@{dominio}` da Google
   Workspace (limite ~2000/giorno, ampiamente sufficiente), cattura dell'NDR.
3. Parsing dell'NDR: estrarre il **diagnostic-code / remote-MTA / Received**
   → identifica il software/host reale che rifiuta (Postfix, Exchange, Zimbra,
   il gateway, ecc.).
4. Riconciliazione: aggiornare `provider`/`mx_jurisdiction`/`confidence` se il
   backend reale emerge; loggare i casi inconcludenti.
5. Se il pilota funziona, estendere ai 1.257 media.

> Vincoli: l'invio email è un'azione esterna → va eseguita con il setup e
> l'autorizzazione dell'utente (account Google Workspace dedicato), non in
> automatico da qui. Vedi task #4 (bounce-verifier).

# Mailbox host (farm Zimbra/Carbonio) — meccanismo di validazione (#31)

Segnalazione esterna (Telegram, 2026-11-07): enti con MX Zimbra trattati come
security gateway, con "ipotesi Microsoft dietro". Fondata: **107 enti** erano
classificati microsoft/google (confidenza mostrata 0,90–0,96) con **zero SPF a
favore**, su soli token TXT / tenant `getuserrealm`. Questa pagina documenta il
principio, il fix e — soprattutto — **il meccanismo di validazione** che tiene
solida la lista `MAILBOX_HOST_GATEWAYS` nel tempo.

## Il principio

| Tipo di host in MX | Cosa significa | Look-through |
|---|---|---|
| **Security gateway** (Sophos, Libraesva, SeppMail…) | appliance antispam: le caselle sono *altrove* | sensato (SPF corroborato → autodiscover → DKIM → TXT → tenant) |
| **Mailbox host** (farm Zimbra/Carbonio: `carbonio`, `zimbraopen`, `zimbraoffice-gw`) | groupware: le caselle sono *lì* | **si ferma dopo il DKIM** — token TXT e tenant non attribuiscono mai un backend cloud |

Razionale probatorio (stessa filosofia del paper upstream / ESORICS):

- tenant `getuserrealm` **"Managed"** = il dominio è registrato in Azure AD
  (licenze Teams/Office — ce l'ha quasi ogni ente). **Non prova** caselle su
  Exchange Online.
- `*-site-verification` nel TXT = dominio verificato in Search Console /
  admin console. **Non prova** l'hosting della posta. Caso-limite osservato:
  due enti sulla **stessa farm** (`mx.carboniocloud.com`) classificati uno
  *microsoft* e uno *google* a seconda del token trovato.
- **DKIM del provider** (`selector1._domainkey → *.onmicrosoft.com` o
  `*.dkim.mail.microsoft`), **autodiscover del provider** o **SPF corroborato**
  = segnali primari: vincono anche su una farm (ibridi genuini, es.
  `cittametropolitana.pa.it`).
- pagina di **login Zimbra/Carbonio/Zextras** raggiungibile sul webmail
  dell'ente (o sul proxy della farm a cui punta il suo autodiscover) = le
  caselle vivono sulla farm. È il segnale positivo che il probe attivo
  raccoglie.

Implementazione: `MAILBOX_HOST_GATEWAYS` in
[`constants.py`](../src/mail_sovereignty/constants.py), guardia nel ramo
gateway di [`classify.py`](../src/mail_sovereignty/classify.py) (reason:
`"MX is <farm> mailbox host (Zimbra/Carbonio farm); mailboxes hosted at the
farm"`), logica pura in
[`mailbox_hosts.py`](../src/mail_sovereignty/mailbox_hosts.py) (unit-testata in
`tests/test_mailbox_hosts.py`, incluso il **negativo anti-falso-positivo**:
"impronta di carbonio" non è un marker). Il campo `gateway` resta popolato →
vista Ricerca Ente (#28), dataset pubblico e pavimenti dei test invariati.

## Il meccanismo di validazione (ripetibile)

```bash
uv run python3 scripts/verify_mailbox_hosts.py            # intera coorte
uv run python3 scripts/verify_mailbox_hosts.py --refresh  # ignora la cache host
```

Per ogni ente IT con gateway mailbox-host o MX `zimbra|carbonio|zextras`:
sonda via HTTPS i frontend candidati (autodiscover `cname`/`srv`, webmail
convenzionali `webmail.|mail.|posta.|zimbra.` sul dominio, l'MX stesso se di
farm) con marker **deliberatamente specifici** ("zimbra web client",
"carbonio authentication", "zextras authentication", `/zx/login/`…), e assegna:

| Verdetto | Significato |
|---|---|
| `mailbox_host_confirmed` | login Zimbra/Carbonio visto su un host dell'ente/farm |
| `farm_autodiscover` | autodiscover punta a una farm nota (evidenza DNS, senza HTTP) |
| `farm_mx_confirmed` | MX su una farm il cui frontend è confermato nel run |
| `hybrid_cloud` | DKIM/autodiscover del cloud: ibrido genuino, **il fix non lo tocca** |
| `unverified` | nessuna evidenza attiva → follow-up manuale |

Output committato (regola *restore, don't regenerate* — è l'evidenza):
[`data/reports/mailbox_host_verification.json`](../data/reports/mailbox_host_verification.json)
(+ `.md` leggibile). Ripartibile: la cache per-host nel JSON viene riusata.

## Risultati del run di validazione 2026-11-07

Coorte **191 enti**, 778 host sondati, **tutte e 4 le farm confermate** via
pagina di login (`proxy.zimbraopen.it`, `mail.zimbramail.it`,
`webmail.carboniocloud.com`, `webmail.zimbraoffice.it` + `mail.`):

| Verdetto | Enti |
|---|---:|
| mailbox_host_confirmed | 103 |
| farm_mx_confirmed | 79 |
| hybrid_cloud (preservati cloud) | 7 |
| unverified | 2 |

Punti chiave:

- **100/100 dei verdetti cloud deboli** (token TXT/tenant) hanno evidenza
  positiva di hosting sulla farm → il fix non demota nessun ente senza prova.
- I **7 ibridi** (CM Palermo, Montebello Vicentino, Segusino, Pineto, ITS
  Agroalimentare Veneto, Conservatorio di Verona, ASL Roma 4) hanno DKIM o
  autodiscover del cloud reali e **restano cloud**.
- I **2 unverified** (`amat.pa.it`, `arapservizi.it`) sono già
  independent/local-isp: **nessun rischio di falso positivo** dal fix.
- Attendibilità (scala `docs/ATTENDIBILITA-DATI.md`-style): software e
  funzione delle farm = **A-v** (verifica attiva live); identità societaria
  degli operatori = **B** (certificati DV senza campo Organization; non
  necessaria alla classificazione).

## Checklist per aggiungere una nuova farm a `MAILBOX_HOST_GATEWAYS`

1. L'MX keyword esiste già in `GATEWAY_KEYWORDS` (il campo `gateway` deve
   restare popolato) e la categoria #28 è `vendor-relay`.
2. **Evidenza attiva**: eseguire `scripts/verify_mailbox_hosts.py` dopo aver
   aggiunto il dominio-farm a `FARM_DOMAINS` in `mailbox_hosts.py`; serve
   almeno una pagina di login Zimbra/Carbonio confermata sul frontend della
   farm o sui webmail degli enti.
3. **Pattern DNS**: autodiscover degli enti che risolve sulla farm stessa
   corrobora (verdetto `farm_autodiscover`).
4. Commit del report aggiornato in `data/reports/` + aggiornamento della
   tabella qui sopra; i test di `tests/test_constants.py` e
   `tests/test_mailbox_hosts.py` devono restare verdi.
5. Gli enti con DKIM/autodiscover del cloud devono risultare `hybrid_cloud`
   (controllo anti-regressione sugli ibridi).

## Collegamenti

- Issue [#31](https://github.com/mxmap-it/mxmap.it/issues/31) (fattispecie,
  probe, risultati) · [#29](https://github.com/mxmap-it/mxmap.it/issues/29)
  (rami tenant/TXT in generale — questa coorte ne era il sottoinsieme più
  netto) · [#30](https://github.com/mxmap-it/mxmap.it/issues/30) (letture per
  banda di confidenza).
- Upstream `mxmap/secassure2026`: **non ha** Zimbra/Carbonio nei gateway (la
  fattispecie era una divergenza nostra); candidata segnalazione metodologica:
  concetto "mailbox-host exclusion" + autodiscover-same-farm come segnale
  positivo.

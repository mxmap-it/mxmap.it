# Report Confidence — Osservatorio Sovranità PA (IT)

Livelli di confidenza della classificazione email, analitici e aggregati. Metodologia: regole ESORICS 2026 (7 regole MX/SPF/DKIM + modello DOMESTIC/FOREIGN via ASN). Anticipazione per la futura validazione via **bounce-probing**: gli enti a confidenza bassa sono i candidati prioritari.

**22878 enti** analizzati. Confidenza media **0.85** (mediana 0.9; media esclusi unknown 0.874).

## 1. Distribuzione aggregata della confidenza

| fascia | enti | % |
|---|---:|---:|
| 0.90-1.00 (molto alta) | 17274 | 75.5% |
| 0.80-0.89 (alta) | 3656 | 16.0% |
| 0.60-0.79 (media) | 1242 | 5.4% |
| 0.01-0.59 (bassa) | 71 | 0.3% |
| 0.00 (nulla / unknown) | 635 | 2.8% |

## 2. Confidenza media per provider

| provider | enti | confidenza media | min | max |
|---|---:|---:|---:|---:|
| google | 6399 | 0.879 | 0.80 | 0.92 |
| aruba | 5167 | 0.896 | 0.80 | 0.92 |
| microsoft | 3384 | 0.928 | 0.80 | 0.96 |
| independent | 3040 | 0.720 | 0.50 | 0.80 |
| local-isp | 1567 | 0.892 | 0.80 | 0.92 |
| regional-public | 933 | 0.889 | 0.80 | 0.90 |
| istruzione-miur-tenant | 877 | 0.960 | 0.96 | 0.96 |
| register-it | 666 | 0.890 | 0.80 | 0.90 |
| unknown | 635 | 0.000 | 0.00 | 0.00 |
| seeweb | 77 | 0.899 | 0.80 | 0.90 |
| ovh | 77 | 0.900 | 0.90 | 0.90 |
| hetzner | 31 | 0.900 | 0.90 | 0.90 |
| ionos | 8 | 0.900 | 0.90 | 0.90 |
| aws | 7 | 0.900 | 0.90 | 0.90 |
| infomaniak | 5 | 0.900 | 0.90 | 0.90 |
| gandi | 2 | 0.900 | 0.90 | 0.90 |
| zoho | 2 | 0.900 | 0.90 | 0.90 |
| pa-contractor-private | 1 | 0.900 | 0.90 | 0.90 |

## 3. Regole di confidenza attivate

| regola | enti | % |
|---|---:|---:|
| `mx_spf` | 17274 | 75.5% |
| `mx_only` | 1929 | 8.4% |
| `dom_mx_spf` | 1727 | 7.5% |
| `frgn_mx_spf` | 985 | 4.3% |
| `no_mx` | 635 | 2.8% |
| `dom_mx_only` | 257 | 1.1% |
| `frgn_mx_only` | 71 | 0.3% |

## 4. Giurisdizione dell'infrastruttura MX (sovranità)

Dove risiede fisicamente il server di posta in entrata (Team Cymru ASN country):

| giurisdizione | enti | % |
|---|---:|---:|
| 🇮🇹 Domestica (IT) | 10568 | 46.2% |
| Mista (IT + estero) | 254 | 1.1% |
| 🌍 Estera | 11353 | 49.6% |
| Sconosciuta | 703 | 3.1% |

**Domestic MX override** applicato a **174** enti: classificati cloud (Microsoft/Google) per segnale tenant/DKIM, ma con MX in entrata self-hosted domestico → riclassificati `independent` (il tenant cloud riflette Teams/SharePoint, non la posta).

## 5. Anticipazione bounce-probing: candidati prioritari

**71 enti** hanno confidenza < 0.60 pur essendo classificati: sono i casi dove la verifica via bounce (invio a indirizzo inesistente + analisi NDR) aggiunge più valore. Priorità per provider:

| provider | enti a bassa confidenza |
|---|---:|
| independent | 71 |

Per giurisdizione: unknown=36, foreign=35

> La validazione bounce confermerà o smentirà queste classificazioni incerte analizzando il backend MTA reale dal messaggio di ritorno, chiudendo il gap di confidenza.

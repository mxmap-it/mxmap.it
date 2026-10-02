# Report Confidence — Osservatorio Sovranità PA (IT)

Livelli di confidenza della classificazione email, analitici e aggregati. Metodologia: regole ESORICS 2026 (7 regole MX/SPF/DKIM + modello DOMESTIC/FOREIGN via ASN). Anticipazione per la futura validazione via **bounce-probing**: gli enti a confidenza bassa sono i candidati prioritari.

**22908 enti** analizzati. Confidenza media **0.851** (mediana 0.9; media esclusi unknown 0.875).

## 1. Distribuzione aggregata della confidenza

| fascia | enti | % |
|---|---:|---:|
| 0.90-1.00 (molto alta) | 17365 | 75.8% |
| 0.80-0.89 (alta) | 3594 | 15.7% |
| 0.60-0.79 (media) | 1235 | 5.4% |
| 0.01-0.59 (bassa) | 65 | 0.3% |
| 0.00 (nulla / unknown) | 649 | 2.8% |

## 2. Confidenza media per provider

| provider | enti | confidenza media | min | max |
|---|---:|---:|---:|---:|
| google | 6453 | 0.883 | 0.80 | 0.92 |
| aruba | 5134 | 0.896 | 0.80 | 0.92 |
| microsoft | 3434 | 0.929 | 0.80 | 0.96 |
| independent | 3038 | 0.720 | 0.50 | 0.80 |
| local-isp | 1553 | 0.892 | 0.80 | 0.92 |
| regional-public | 915 | 0.895 | 0.80 | 0.90 |
| istruzione-miur-tenant | 860 | 0.960 | 0.96 | 0.96 |
| register-it | 664 | 0.890 | 0.80 | 0.90 |
| unknown | 649 | 0.000 | 0.00 | 0.00 |
| seeweb | 77 | 0.900 | 0.90 | 0.90 |
| ovh | 77 | 0.900 | 0.90 | 0.90 |
| hetzner | 30 | 0.900 | 0.90 | 0.90 |
| ionos | 8 | 0.900 | 0.90 | 0.90 |
| infomaniak | 6 | 0.900 | 0.90 | 0.90 |
| aws | 5 | 0.900 | 0.90 | 0.90 |
| gandi | 2 | 0.900 | 0.90 | 0.90 |
| zoho | 2 | 0.900 | 0.90 | 0.90 |
| pa-contractor-private | 1 | 0.900 | 0.90 | 0.90 |

## 3. Regole di confidenza attivate

| regola | enti | % |
|---|---:|---:|
| `mx_spf` | 17365 | 75.8% |
| `mx_only` | 1856 | 8.1% |
| `dom_mx_spf` | 1738 | 7.6% |
| `frgn_mx_spf` | 987 | 4.3% |
| `no_mx` | 649 | 2.8% |
| `dom_mx_only` | 248 | 1.1% |
| `frgn_mx_only` | 65 | 0.3% |

## 4. Giurisdizione dell'infrastruttura MX (sovranità)

Dove risiede fisicamente il server di posta in entrata (Team Cymru ASN country):

| giurisdizione | enti | % |
|---|---:|---:|
| 🇮🇹 Domestica (IT) | 10487 | 45.8% |
| Mista (IT + estero) | 248 | 1.1% |
| 🌍 Estera | 11453 | 50.0% |
| Sconosciuta | 720 | 3.1% |

**Domestic MX override** applicato a **196** enti: classificati cloud (Microsoft/Google) per segnale tenant/DKIM, ma con MX in entrata self-hosted domestico → riclassificati `independent` (il tenant cloud riflette Teams/SharePoint, non la posta).

## 5. Anticipazione bounce-probing: candidati prioritari

**65 enti** hanno confidenza < 0.60 pur essendo classificati: sono i casi dove la verifica via bounce (invio a indirizzo inesistente + analisi NDR) aggiunge più valore. Priorità per provider:

| provider | enti a bassa confidenza |
|---|---:|
| independent | 65 |

Per giurisdizione: unknown=36, foreign=29

> La validazione bounce confermerà o smentirà queste classificazioni incerte analizzando il backend MTA reale dal messaggio di ritorno, chiudendo il gap di confidenza.

# Report Confidence — Osservatorio Sovranità PA (IT)

Livelli di confidenza della classificazione email, analitici e aggregati. Metodologia: regole ESORICS 2026 (7 regole MX/SPF/DKIM + modello DOMESTIC/FOREIGN via ASN). Anticipazione per la futura validazione via **bounce-probing**: gli enti a confidenza bassa sono i candidati prioritari.

**22884 enti** analizzati. Confidenza media **0.851** (mediana 0.9; media esclusi unknown 0.875).

## 1. Distribuzione aggregata della confidenza

| fascia | enti | % |
|---|---:|---:|
| 0.90-1.00 (molto alta) | 17355 | 75.8% |
| 0.80-0.89 (alta) | 3610 | 15.8% |
| 0.60-0.79 (media) | 1227 | 5.4% |
| 0.01-0.59 (bassa) | 66 | 0.3% |
| 0.00 (nulla / unknown) | 626 | 2.7% |

## 2. Confidenza media per provider

| provider | enti | confidenza media | min | max |
|---|---:|---:|---:|---:|
| google | 6440 | 0.883 | 0.80 | 0.92 |
| aruba | 5141 | 0.896 | 0.80 | 0.92 |
| microsoft | 3426 | 0.929 | 0.80 | 0.96 |
| independent | 3037 | 0.721 | 0.50 | 0.80 |
| local-isp | 1551 | 0.892 | 0.80 | 0.92 |
| regional-public | 929 | 0.894 | 0.80 | 0.90 |
| istruzione-miur-tenant | 866 | 0.960 | 0.96 | 0.96 |
| register-it | 666 | 0.890 | 0.80 | 0.90 |
| unknown | 626 | 0.000 | 0.00 | 0.00 |
| ovh | 75 | 0.900 | 0.90 | 0.90 |
| seeweb | 74 | 0.899 | 0.80 | 0.90 |
| hetzner | 30 | 0.900 | 0.90 | 0.90 |
| ionos | 8 | 0.900 | 0.90 | 0.90 |
| aws | 5 | 0.900 | 0.90 | 0.90 |
| infomaniak | 5 | 0.900 | 0.90 | 0.90 |
| gandi | 2 | 0.900 | 0.90 | 0.90 |
| zoho | 2 | 0.900 | 0.90 | 0.90 |
| pa-contractor-private | 1 | 0.900 | 0.90 | 0.90 |

## 3. Regole di confidenza attivate

| regola | enti | % |
|---|---:|---:|
| `mx_spf` | 17355 | 75.8% |
| `mx_only` | 1866 | 8.2% |
| `dom_mx_spf` | 1744 | 7.6% |
| `frgn_mx_spf` | 978 | 4.3% |
| `no_mx` | 626 | 2.7% |
| `dom_mx_only` | 249 | 1.1% |
| `frgn_mx_only` | 66 | 0.3% |

## 4. Giurisdizione dell'infrastruttura MX (sovranità)

Dove risiede fisicamente il server di posta in entrata (Team Cymru ASN country):

| giurisdizione | enti | % |
|---|---:|---:|
| 🇮🇹 Domestica (IT) | 10513 | 45.9% |
| Mista (IT + estero) | 243 | 1.1% |
| 🌍 Estera | 11432 | 50.0% |
| Sconosciuta | 696 | 3.0% |

**Domestic MX override** applicato a **195** enti: classificati cloud (Microsoft/Google) per segnale tenant/DKIM, ma con MX in entrata self-hosted domestico → riclassificati `independent` (il tenant cloud riflette Teams/SharePoint, non la posta).

## 5. Anticipazione bounce-probing: candidati prioritari

**66 enti** hanno confidenza < 0.60 pur essendo classificati: sono i casi dove la verifica via bounce (invio a indirizzo inesistente + analisi NDR) aggiunge più valore. Priorità per provider:

| provider | enti a bassa confidenza |
|---|---:|
| independent | 66 |

Per giurisdizione: unknown=35, foreign=31

> La validazione bounce confermerà o smentirà queste classificazioni incerte analizzando il backend MTA reale dal messaggio di ritorno, chiudendo il gap di confidenza.

# Report Confidence — Osservatorio Sovranità PA (IT)

Livelli di confidenza della classificazione email, analitici e aggregati. Metodologia: regole ESORICS 2026 (7 regole MX/SPF/DKIM + modello DOMESTIC/FOREIGN via ASN). Anticipazione per la futura validazione via **bounce-probing**: gli enti a confidenza bassa sono i candidati prioritari.

**22915 enti** analizzati. Confidenza media **0.852** (mediana 0.9; media esclusi unknown 0.876).

## 1. Distribuzione aggregata della confidenza

| fascia | enti | % |
|---|---:|---:|
| 0.90-1.00 (molto alta) | 17394 | 75.9% |
| 0.80-0.89 (alta) | 3622 | 15.8% |
| 0.60-0.79 (media) | 1209 | 5.3% |
| 0.01-0.59 (bassa) | 62 | 0.3% |
| 0.00 (nulla / unknown) | 628 | 2.7% |

## 2. Confidenza media per provider

| provider | enti | confidenza media | min | max |
|---|---:|---:|---:|---:|
| google | 6468 | 0.883 | 0.80 | 0.92 |
| aruba | 5138 | 0.896 | 0.80 | 0.92 |
| microsoft | 3447 | 0.929 | 0.80 | 0.96 |
| independent | 3013 | 0.721 | 0.50 | 0.80 |
| local-isp | 1571 | 0.891 | 0.80 | 0.92 |
| regional-public | 918 | 0.895 | 0.80 | 0.90 |
| istruzione-miur-tenant | 861 | 0.960 | 0.96 | 0.96 |
| register-it | 664 | 0.890 | 0.80 | 0.90 |
| unknown | 628 | 0.000 | 0.00 | 0.00 |
| seeweb | 77 | 0.900 | 0.90 | 0.90 |
| ovh | 77 | 0.900 | 0.90 | 0.90 |
| hetzner | 29 | 0.900 | 0.90 | 0.90 |
| ionos | 8 | 0.900 | 0.90 | 0.90 |
| infomaniak | 6 | 0.900 | 0.90 | 0.90 |
| aws | 5 | 0.900 | 0.90 | 0.90 |
| gandi | 2 | 0.900 | 0.90 | 0.90 |
| zoho | 2 | 0.900 | 0.90 | 0.90 |
| pa-contractor-private | 1 | 0.900 | 0.90 | 0.90 |

## 3. Regole di confidenza attivate

| regola | enti | % |
|---|---:|---:|
| `mx_spf` | 17394 | 75.9% |
| `mx_only` | 1880 | 8.2% |
| `dom_mx_spf` | 1742 | 7.6% |
| `frgn_mx_spf` | 987 | 4.3% |
| `no_mx` | 628 | 2.7% |
| `dom_mx_only` | 222 | 1.0% |
| `frgn_mx_only` | 62 | 0.3% |

## 4. Giurisdizione dell'infrastruttura MX (sovranità)

Dove risiede fisicamente il server di posta in entrata (Team Cymru ASN country):

| giurisdizione | enti | % |
|---|---:|---:|
| 🇮🇹 Domestica (IT) | 10498 | 45.8% |
| Mista (IT + estero) | 247 | 1.1% |
| 🌍 Estera | 11469 | 50.1% |
| Sconosciuta | 701 | 3.1% |

**Domestic MX override** applicato a **196** enti: classificati cloud (Microsoft/Google) per segnale tenant/DKIM, ma con MX in entrata self-hosted domestico → riclassificati `independent` (il tenant cloud riflette Teams/SharePoint, non la posta).

## 5. Anticipazione bounce-probing: candidati prioritari

**62 enti** hanno confidenza < 0.60 pur essendo classificati: sono i casi dove la verifica via bounce (invio a indirizzo inesistente + analisi NDR) aggiunge più valore. Priorità per provider:

| provider | enti a bassa confidenza |
|---|---:|
| independent | 62 |

Per giurisdizione: unknown=37, foreign=25

> La validazione bounce confermerà o smentirà queste classificazioni incerte analizzando il backend MTA reale dal messaggio di ritorno, chiudendo il gap di confidenza.

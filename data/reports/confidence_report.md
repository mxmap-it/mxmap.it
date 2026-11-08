# Report Confidence — Osservatorio Sovranità PA (IT)

Livelli di confidenza della classificazione email, analitici e aggregati. Metodologia: regole ESORICS 2026 (7 regole MX/SPF/DKIM + modello DOMESTIC/FOREIGN via ASN). Anticipazione per la futura validazione via **bounce-probing**: gli enti a confidenza bassa sono i candidati prioritari.

**22922 enti** analizzati. Confidenza media **0.809** (mediana 0.9; media esclusi unknown 0.857).

## 1. Distribuzione aggregata della confidenza

| fascia | enti | % |
|---|---:|---:|
| 0.90-1.00 (molto alta) | 12062 | 52.6% |
| 0.80-0.89 (alta) | 8159 | 35.6% |
| 0.60-0.79 (media) | 1282 | 5.6% |
| 0.01-0.59 (bassa) | 114 | 0.5% |
| 0.00 (nulla / unknown) | 1305 | 5.7% |

## 2. Confidenza media per provider

| provider | enti | confidenza media | min | max |
|---|---:|---:|---:|---:|
| google | 6155 | 0.870 | 0.44 | 0.94 |
| aruba | 5122 | 0.884 | 0.40 | 0.90 |
| microsoft | 2907 | 0.923 | 0.44 | 0.98 |
| pa-contractor-private | 2425 | 0.745 | 0.40 | 0.80 |
| local-isp | 1559 | 0.801 | 0.80 | 0.90 |
| unknown | 1305 | 0.000 | 0.00 | 0.00 |
| regional-public | 905 | 0.866 | 0.80 | 0.90 |
| istruzione-miur-tenant | 845 | 0.980 | 0.98 | 0.98 |
| independent | 832 | 0.716 | 0.50 | 0.80 |
| register-it | 661 | 0.800 | 0.80 | 0.90 |
| ovh | 78 | 0.894 | 0.40 | 0.90 |
| seeweb | 76 | 0.842 | 0.80 | 0.90 |
| hetzner | 29 | 0.800 | 0.80 | 0.80 |
| ionos | 8 | 0.900 | 0.90 | 0.90 |
| infomaniak | 6 | 0.900 | 0.90 | 0.90 |
| aws | 5 | 0.860 | 0.80 | 0.90 |
| gandi | 2 | 0.900 | 0.90 | 0.90 |
| zoho | 2 | 0.900 | 0.90 | 0.90 |

## 3. Regole di confidenza attivate

| regola | enti | % |
|---|---:|---:|
| `mx_spf` | 12062 | 52.6% |
| `mx_only` | 5987 | 26.1% |
| `dom_mx_spf` | 2172 | 9.5% |
| `frgn_mx_spf` | 779 | 3.4% |
| `gateway_no_primary` | 677 | 3.0% |
| `no_mx` | 628 | 2.7% |
| `spf_gw` | 272 | 1.2% |
| `dom_mx_only` | 224 | 1.0% |
| `frgn_mx_only` | 65 | 0.3% |
| `fallback` | 49 | 0.2% |
| `dkim_gw` | 7 | 0.0% |

## 4. Giurisdizione dell'infrastruttura MX (sovranità)

Dove risiede fisicamente il server di posta in entrata (Team Cymru ASN country):

| giurisdizione | enti | % |
|---|---:|---:|
| 🇮🇹 Domestica (IT) | 10451 | 45.6% |
| Mista (IT + estero) | 244 | 1.1% |
| 🌍 Estera | 11528 | 50.3% |
| Sconosciuta | 699 | 3.0% |

**Domestic MX override** applicato a **198** enti: classificati cloud (Microsoft/Google) per segnale tenant/DKIM, ma con MX in entrata self-hosted domestico → riclassificati `independent` (il tenant cloud riflette Teams/SharePoint, non la posta).

## 5. Anticipazione bounce-probing: candidati prioritari

**114 enti** hanno confidenza < 0.60 pur essendo classificati: sono i casi dove la verifica via bounce (invio a indirizzo inesistente + analisi NDR) aggiunge più valore. Priorità per provider:

| provider | enti a bassa confidenza |
|---|---:|
| independent | 59 |
| aruba | 23 |
| pa-contractor-private | 22 |
| microsoft | 8 |
| ovh | 1 |
| google | 1 |

Per giurisdizione: foreign=39, unknown=38, domestic=37

> La validazione bounce confermerà o smentirà queste classificazioni incerte analizzando il backend MTA reale dal messaggio di ritorno, chiudendo il gap di confidenza.

# Cloud Tenant Confidence Score (2026-06-17)

Per ogni entry con `cloud_tenant_only` impostato, calcoliamo uno **score di confidenza** (0-1) che riflette quante evidenze DNS indipendenti puntano al cloud backend. La soglia per la reclassificazione automatica è **0.85** (etichetta `definitive`).

## Perché non basta il DKIM da solo

Un DKIM CNAME verso `*.onmicrosoft.com` **prova** che l'ente ha un tenant Microsoft 365 (per Teams, SharePoint, firma ibrida, ecc.) ma **NON** prova che le cassette postali siano hosted su M365. Configurazioni ibride (Exchange on-prem + EOP, M365 solo per calendario, MS Teams con mail altrove) sono frequentissime.

Per provare l'hosting esclusivo servono **≥3 segnali DNS coerenti**: DKIM + autodiscover + SPF + TXT verification.

## Distribuzione

| Confidence | Count | Significato |
|------------|-------|-------------|
| **definitive** (≥0.85) | 110 | Reclassificazione automatica sicura |
| **strong** (0.60-0.84) | 13 | Quasi certo, ma serve 1 segnale in più (portale trasparenza/ANAC) |
| **moderate** (0.40-0.59) | 10 | Tenant presente, hosting esclusivo dubbio |
| **weak** (<0.40) | 86 | Evidenza debole, NON reclassificare |

## Top `definitive` entries (reclassificabili)

Queste 110 entry hanno **≥3 segnali DNS coerenti** verso lo stesso hyperscaler — la reclassificazione è ragionevolmente sicura (es. M365 hybrid completo).

| BFS | Name | Regione | Provider | Score | Signals |
|-----|------|---------|----------|-------|---------|
| `IT-C14-oddc_024` | Ordine Dei Dottori Commercialisti e Degli Esperti  | Veneto | microsoft | 1.0 | dkim_cname, autodiscover_cname, spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-C14-odfpg` | Ordine Dei Farmacisti della Provincia di Genova | Liguria | microsoft | 1.0 | dkim_cname, autodiscover_cname, spf_include, upstream_cloud_tenant_only |
| `IT-C14-ordav_lc` | Consiglio dell'Ordine degli Avvocati di Lecco | Lombardia | microsoft | 1.0 | dkim_cname, autodiscover_cname, spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-C14-oring_tn` | Ordine degli Ingegneri della Provincia di Trento | Trentino-Alto Adige | microsoft | 1.0 | dkim_cname, autodiscover_cname, spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-C16-inps` | Istituto Nazionale Previdenza Sociale - INPS | Lazio | microsoft | 1.0 | dkim_cname, autodiscover_cname, spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-C2-corte_cost` | Corte Costituzionale | Lazio | microsoft | 1.0 | dkim_cname, autodiscover_cname, spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-C5-agpia` | Autorita Garante per L'Infanzia e L'Adolescenza | Lazio | microsoft | 1.0 | dkim_cname, autodiscover_cname, spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-C5-consob` | Commissione Nazionale per Le Societa' e La Borsa | Lazio | microsoft | 1.0 | dkim_cname, spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-C7-crsams` | Azienda di Servizi alla Persona disabile visiva S. | Lazio | microsoft | 1.0 | dkim_cname, autodiscover_cname, spf_include, upstream_cloud_tenant_only |
| `IT-CMM-001272` | Citta' Metropolitana di Torino | Piemonte | microsoft | 1.0 | dkim_cname, autodiscover_cname, spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-COM-010006` | Comune di Busalla | Liguria | microsoft | 1.0 | autodiscover_cname, spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-COM-012070` | Comune di Gallarate | Lombardia | microsoft | 1.0 | dkim_cname, autodiscover_cname, spf_include, upstream_cloud_tenant_only |
| `IT-COM-012086` | Comune di Lavena Ponte Tresa | Lombardia | microsoft | 1.0 | autodiscover_cname, spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-COM-012102` | Comune di Mesenzana | Lombardia | microsoft | 1.0 | dkim_cname, autodiscover_cname, spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-COM-013045` | Comune di Carbonate | Lombardia | microsoft | 1.0 | autodiscover_cname, spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-COM-015158` | Comune di Noviglio | Lombardia | microsoft | 1.0 | dkim_cname, autodiscover_cname, spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-COM-015194` | Comune di San Giorgio Su Legnano | Lombardia | microsoft | 1.0 | autodiscover_cname, spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-COM-017096` | Comune di Lumezzane | Lombardia | microsoft | 1.0 | dkim_cname, autodiscover_cname, spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-COM-018160` | Comune di Torrevecchia Pia | Lombardia | microsoft | 1.0 | dkim_cname, autodiscover_cname, spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-COM-018163` | Comune di Trivolzio | Lombardia | microsoft | 1.0 | dkim_cname, autodiscover_cname, spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-COM-018176` | Comune di Vidigulfo | Lombardia | microsoft | 1.0 | dkim_cname, autodiscover_cname, spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-COM-018192` | Comune di Corteolona e Genzone | Lombardia | microsoft | 1.0 | dkim_cname, autodiscover_cname, spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-COM-020035` | Comune di Moglia | Lombardia | microsoft | 1.0 | dkim_cname, spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-COM-023021` | Comune di Castel D'Azzano | Veneto | microsoft | 1.0 | dkim_cname, spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-COM-027042` | Comune di Venezia | Veneto | microsoft | 1.0 | dkim_cname, spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-COM-039001` | Comune di Alfonsine | Emilia-Romagna | microsoft | 1.0 | dkim_cname, autodiscover_cname, spf_include, upstream_cloud_tenant_only |
| `IT-COM-039002` | Comune di Bagnacavallo | Emilia-Romagna | microsoft | 1.0 | dkim_cname, autodiscover_cname, spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-COM-039003` | Comune di Bagnara di Romagna | Emilia-Romagna | microsoft | 1.0 | dkim_cname, autodiscover_cname, spf_include, upstream_cloud_tenant_only |
| `IT-COM-039004` | Comune di Brisighella | Emilia-Romagna | microsoft | 1.0 | dkim_cname, spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-COM-039005` | Comune di Casola Valsenio | Emilia-Romagna | microsoft | 1.0 | dkim_cname, spf_include, txt_verification, upstream_cloud_tenant_only |

## `strong` entries (servono 1 segnale in più)

Queste 13 entry hanno 2-3 segnali DNS. La reclassificazione è prudente solo dopo cross-reference con ANAC / portale trasparenza / PNRR.

| BFS | Name | Provider | Score | Signals |
|-----|------|----------|-------|---------|
| `IT-L37-basrl` | Brianzacque Srl | microsoft | 0.75 | dkim_cname, txt_verification, upstream_cloud_tenant_only |
| `IT-L37-fccors` | Farmacie Comunali Corsichesi Spa | microsoft | 0.75 | autodiscover_cname, txt_verification, upstream_cloud_tenant_only |
| `IT-PRO-702462` | Provincia di Como | microsoft | 0.75 | dkim_cname, autodiscover_cname, upstream_cloud_tenant_only |
| `IT-C17-iepad` | INARCASSA CASSA NAZIONALE PREVIDENZA ASSISTENZA IN | microsoft | 0.65 | dkim_cname, spf_include, upstream_cloud_tenant_only |
| `IT-COM-113009` | Comune di Budoni | microsoft | 0.65 | spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-COM-118007` | Comune di Capoterra | microsoft | 0.65 | spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-L31-eatsg` | Ente Autonomo Teatro Stabile di Genova | microsoft | 0.65 | spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-L33-isa_` | Emile Lexert | microsoft | 0.65 | spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-L33-isica` | Liceo Classico, Artistico e Musicale | microsoft | 0.65 | spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-L33-issf_` | Istituzione Scolastica San Francesco | microsoft | 0.65 | spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-L37-acerpfc` | Azienda Casa Emilia Romagna della Provincia di For | microsoft | 0.65 | spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-L7-as_PE` | Azienda USL Pescara | microsoft | 0.65 | spf_include, txt_verification, upstream_cloud_tenant_only |
| `IT-SAG-ED28KAEQ` | ACEA ATO5 SPA | microsoft | 0.65 | spf_include, txt_verification, upstream_cloud_tenant_only |

## `weak` entries (NON reclassificare)

Queste 86 entry hanno solo DKIM CNAME o l'upstream flag senza altri segnali. **Non c'è prova DNS sufficiente** per l'hosting esclusivo.

## Metodologia — Pesi per segnale

| Segnale | Peso |
|---------|------|
| `dkim_cname` | 0.3 |
| `autodiscover_cname` | 0.3 |
| `spf_include` | 0.2 |
| `txt_verification` | 0.3 |
| `mx_cname` | 0.2 |
| `upstream_cloud_tenant_only` | 0.15 |
| bonus 4+ segnali | +0.1 |

**Soglie di confidenza**:
- `definitive` ≥ 0.85 → reclassificazione automatica OK
- `strong` 0.60-0.84 → serve ANAC/portale trasparenza
- `moderate` 0.40-0.59 → solo `cloud_tenant_involvement`
- `weak` < 0.40 → no signal sufficiente

## Esempio reale: Corte Costituzionale (bfs IT-C2-corte_cost)

DKIM `cortecostituzionale.onmicrosoft.com` + autodiscover `autodiscover.outlook.com` + TXT verification `microsoft: ms53301331` = **score 1.0 (definitive)**, 5 segnali. Reclassificazione: `provider=microsoft`.

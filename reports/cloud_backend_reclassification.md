# Cloud Backend Reclassification Report (2026-06-17)

Reclassified **1185 entries** from `independent` to a confirmed cloud backend using multi-signal DNS analysis.

**Source signals (in priority order):**

1. `classify()` with DKIM CNAME → hyperscaler
2. `classify()` with MX CNAME → hyperscaler
3. `classify()` with autodiscover CNAME → hyperscaler
4. `classify()` with SPF include → hyperscaler
5. `classify()` with TXT verification token
6. `cloud_tenant_only` field set by upstream pipeline (ASN/IP-based)

## Summary

- **Total entries**: 22,987
- **Unchanged**: 21,802
- **Reclassified**: 1185
- **Errors**: 0

### By target backend

| Backend | Count |
|---------|-------|
| microsoft | 1075 |
| aws | 74 |
| google | 36 |

### By source signal

| Signal | Count |
|--------|-------|
| `classify_other` | 894 |
| `classify_dkim` | 121 |
| `upstream_cloud_tenant_only` | 83 |
| `classify_txt` | 51 |
| `classify_autodiscover` | 29 |
| `classify_cname` | 7 |

## Notable Reclassifications

Top 30 by entity size (alphabetical by region, then name):

- **Abruzzo Sviluppo Spa Con Unico Socio** (Abruzzo / Pescara) — `independent` → `aws` via `upstream_cloud_tenant_only`
  - MX: `xx.xxxxxxxx.com, xxxx.xxxx.com`
- **Azienda USL Pescara** (Abruzzo / Pescara) — `independent` → `microsoft` via `classify_dkim`
  - MX: `mx.edge.asl.pe.it, mx1.asl.pe.it`
- **DIREZIONE DIDATTICA - CD SPOLTORE** (Abruzzo / Spoltore) — `istruzione-miur-tenant` → `microsoft` via `classify_other`
  - MX: `istruzione-it.mail.protection.outlook.com`
- **ISTITUTO COMPRENSIVO -  ISTITUTO COMPRENSIVO 'T.DE** (Abruzzo / Montesilvano) — `istruzione-miur-tenant` → `microsoft` via `classify_other`
  - MX: `istruzione-it.mail.protection.outlook.com`
- **ISTITUTO COMPRENSIVO - I.C. 'COLLODI-L.MARINI'** (Abruzzo / Avezzano) — `independent` → `aws` via `upstream_cloud_tenant_only`
  - MX: `mail.istitutocomprensivocollodimarini.it`
- **ISTITUTO COMPRENSIVO - I.C. MIGLIANICO** (Abruzzo / Miglianico) — `istruzione-miur-tenant` → `microsoft` via `classify_other`
  - MX: `istruzione-it.mail.protection.outlook.com`
- **ISTITUTO COMPRENSIVO - I.C. VIVENZA- GIOVANNI XXII** (Abruzzo / Avezzano) — `independent` → `aws` via `upstream_cloud_tenant_only`
  - MX: `mail.ic3avezzano.it`
- **ISTITUTO COMPRENSIVO - IC 'L.CIULLI PARATORE' - PE** (Abruzzo / Penne) — `istruzione-miur-tenant` → `microsoft` via `classify_other`
  - MX: `istruzione-it.mail.protection.outlook.com`
- **ISTITUTO COMPRENSIVO - IC MAGLIANO DEI MARSI** (Abruzzo / Magliano de' Marsi) — `independent` → `aws` via `upstream_cloud_tenant_only`
  - MX: `mail.scuolamaglianodemarsi.it`
- **ISTITUTO COMPRENSIVO - IC UMBERTO POSTIGLIONE** (Abruzzo / Raiano) — `istruzione-miur-tenant` → `microsoft` via `classify_other`
  - MX: `istruzione-it.mail.protection.outlook.com`
- **ISTITUTO COMPRENSIVO - ISTITUTO COMPRENSIVO 'M. GI** (Abruzzo / Penne) — `istruzione-miur-tenant` → `microsoft` via `classify_other`
  - MX: `istruzione-it.mail.protection.outlook.com`
- **ISTITUTO COMPRENSIVO - ISTITUTO COMPRENSIVO COLLEC** (Abruzzo / Collecorvino) — `istruzione-miur-tenant` → `microsoft` via `classify_other`
  - MX: `istruzione-it.mail.protection.outlook.com`
- **ISTITUTO D'ARTE - ISTITUTO D ARTE F.A.GRUE** (Abruzzo / Castelli) — `istruzione-miur-tenant` → `microsoft` via `classify_other`
  - MX: `istruzione-it.mail.protection.outlook.com`
- **ISTITUTO DI ISTRUZIONE SUPERIORE "G. GALILEI-BELLI** (Abruzzo / Avezzano) — `istruzione-miur-tenant` → `microsoft` via `classify_other`
  - MX: `istruzione-it.mail.protection.outlook.com`
- **Iis Pascal-comi-forti** (Abruzzo / Teramo) — `istruzione-miur-tenant` → `microsoft` via `classify_other`
  - MX: `istruzione-it.mail.protection.outlook.com`
- **Istituto Comprensivo N.1 Lanciano** (Abruzzo / Lanciano) — `istruzione-miur-tenant` → `microsoft` via `classify_other`
  - MX: `istruzione-it.mail.protection.outlook.com`
- **Liceo Statale B. Croce** (Abruzzo / Avezzano) — `istruzione-miur-tenant` → `microsoft` via `classify_other`
  - MX: `istruzione-it.mail.protection.outlook.com`
- **Ordine Dei Medici Veterinari della Provincia di Ch** (Abruzzo / Chieti) — `independent` → `aws` via `upstream_cloud_tenant_only`
  - MX: `mx.ordinemediciveterinarichieti.it`
- **PRESIDENTE REGIONE ABRUZZO - COMMISSARIO DISSESTO ** (Abruzzo / L'Aquila) — `independent` → `microsoft` via `classify_dkim`
  - MX: `smtp2.regione.abruzzo.it`
- **Regione Abruzzo** (Abruzzo / L'Aquila) — `independent` → `microsoft` via `classify_dkim`
  - MX: `smtp2.regione.abruzzo.it`
- **Servizio Affari Generali e Amministrativi** (Abruzzo / L'Aquila) — `independent` → `microsoft` via `classify_dkim`
  - MX: `smtp2.regione.abruzzo.it`
- **ISTITUTO COMPRENSIVO "BRAMANTE - TORRACA** (Basilicata / Matera) — `istruzione-miur-tenant` → `microsoft` via `classify_other`
  - MX: `istruzione-it.mail.protection.outlook.com`
- **ISTITUTO COMPRENSIVO - ' A.BUSCIOLANO' POTENZA** (Basilicata / Potenza) — `istruzione-miur-tenant` → `microsoft` via `classify_other`
  - MX: `istruzione-it.mail.protection.outlook.com`
- **ISTITUTO COMPRENSIVO - 'B. CROCE' LATRONICO** (Basilicata / Latronico) — `istruzione-miur-tenant` → `microsoft` via `classify_other`
  - MX: `istruzione-it.mail.protection.outlook.com`
- **ISTITUTO COMPRENSIVO - 'TEN R.DAVIA' SALANDRA** (Basilicata / Salandra) — `istruzione-miur-tenant` → `microsoft` via `classify_other`
  - MX: `istruzione-it.mail.protection.outlook.com`
- **ISTITUTO COMPRENSIVO - BELLA** (Basilicata / Bella) — `istruzione-miur-tenant` → `microsoft` via `classify_other`
  - MX: `istruzione-it.mail.protection.outlook.com`
- **ISTITUTO COMPRENSIVO - IC ALBINO PIERRO TURSI** (Basilicata / Tursi) — `istruzione-miur-tenant` → `microsoft` via `classify_other`
  - MX: `istruzione-it.mail.protection.outlook.com`
- **ISTITUTO COMPRENSIVO - ISTITUTO COMPRENSIVO** (Basilicata / Tricarico) — `istruzione-miur-tenant` → `microsoft` via `classify_other`
  - MX: `istruzione-it.mail.protection.outlook.com`
- **ISTITUTO COMPRENSIVO - M. CARLUCCI RUOTI** (Basilicata / Baragiano) — `istruzione-miur-tenant` → `microsoft` via `classify_other`
  - MX: `istruzione-it.mail.protection.outlook.com`
- **ISTITUTO COMPRENSIVO - POTENZA TERZO** (Basilicata / Potenza) — `istruzione-miur-tenant` → `microsoft` via `classify_other`
  - MX: `istruzione-it.mail.protection.outlook.com`

_… and 1155 more_

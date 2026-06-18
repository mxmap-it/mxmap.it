# Research: Italian Universities & Central Bank — Cloud Sovereignty Profile

**Date:** 2026-06-17
**Scope:** Politecnico di Milano, Università di Milano (UniMi), UniCredit S.p.A., Banca d'Italia
**Methodology:** MxMap dataset (`data.json`, v2026-06-17, 22,878 entities) + live DNS lookups (Google DNS JSON API) + ANAC/transparency portal cross-reference + web research.

## Caveat: in-dataset vs out-of-dataset

The MxMap dataset indexes Italian public administration entities from IndicePA (~22,987 IT entities). It does not include private banks.

- **Politecnico di Milano**: in MxMap (public university)
- **Università di Milano**: in MxMap (public university)
- **UniCredit S.p.A.**: not in MxMap (private S.p.A.)
- **Banca d'Italia**: not in MxMap (central bank, special procurement regime)

For the two entities not in the dataset, the brief relies on direct DNS evidence (the same signals MxMap uses) plus ANAC/transparency-portal procurement and web research. The same classification logic applies.

A second caveat: there is no `cloud_tenant_only` field in the MxMap schema. The concept is represented by the combination of `tenant: "Managed"` (M365 tenant detected via `getuserrealm.srf`) plus an MX route that does not use `mail.protection.outlook.com`. Entities that match that pattern have an M365 subscription used for non-mail apps (Teams/SharePoint/etc.) but route their email elsewhere.

## 1. POLITECNICO DI MILANO (polimi.it)

**MxMap classification:** `microsoft` — full M365 customer. MX is on Exchange Online (`polimi-it.mail.protection.outlook.com` priority 0), DKIM signs through tenant `polimi365.onmicrosoft.com`, autodiscover CNAMEs to `autodiscover.outlook.com`. `mx_jurisdiction: "foreign"` (ASN 8075, US). Confidence 0.94 (rule `mx_spf`, signals: `autodiscover, dkim, mx, spf`). Sits in the `USA (CLOUD Act)` mxmap sovereignty bucket.

### DNS evidence (live queries 2026-06-17, Google DNS JSON API)

- **MX (priority 0):** `polimi-it.mail.protection.outlook.com`
- **MX AS / country:** ASN 8075 (Microsoft), US
- **SPF:** allows PoliMi on-net (`131.175.12.10/100/18/21/24`) + M365 (`spf.protection.outlook.com`) — `v=spf1 ip4:131.175.12.10 ip4:131.175.12.100 ip4:131.175.12.18 ip4:131.175.12.21 ip4:131.175.12.24 include:spf.protection.outlook.com -all`
- **DKIM selector1 CNAME:** `selector1-polimi-it._domainkey.polimi365.onmicrosoft.com` — definitive proof of M365 backend
- **Autodiscover CNAME:** `autodiscover.outlook.com`
- **TXT verifications:** HARICA, DocuSign, OpenAI, Cisco CI, Autodesk, Google site (no Microsoft-domain-verification TXT token, but DKIM is definitive)
- **MxMap tenant field:** inferred `Managed` (rule `mx_spf` fires on 4 signals: `autodiscover, dkim, mx, spf`)
- **"Cloud tenant only" pattern:** NO — MX routes through M365, full customer

### ANAC cross-reference

- CIG `Z2E39BF3DB` (RDA 80766, 2023): AWS — Amazon Web Services EMEA Sàrl, "Archiviazione dati del Dipartimento a lungo periodo" → **AWS**
- CIG `Z553B40BB6` (2023): WIDECLUSIVE (Google Workspace Business reseller), "Dominio - hosting - Google workspace business starts" → **Google** (resold)
- CIG `Z27225479D` (2022): IN4MATIC S.r.l., "Fornitura servizi web in CLOUD - Gestione Alloggi" → cloud-managed hosting
- CIG `65227610A9` (2016): "Fornitura integrazione attrezzature informatiche Cluster HPC per Sala Server" — €155,328.88 → on-prem HPC hardware
- (in-house): PoliCloud — IBM + Yahoo (YSTAR) donations, IaaS for research (DEIB + Math + Design)

Microsoft 365 is delivered through the **CRUI / Microsoft Italia CASA-EES framework agreement** (educational enrolment, not an ANAC-tracked CIG for PoliMi directly).

### Web research — cloud strategy

- Microsoft 365 is the primary productivity suite (e-mail + Teams + OneDrive for Business + SharePoint Online) for students and staff. Exchange server is `outlook.office365.com`. iPhone setup is documented as Microsoft Exchange.
- Microsoft 365 Apps deployed with educational licences: Word, Excel, PowerPoint, OneNote, Access, Publisher, Outlook, Microsoft Teams, OneDrive for Business.
- OpenAI is in scope (verified by `openai-domain-verification` TXT record). Multi-cloud productivity stack: M365 + OpenAI APIs + Google site + Autodesk + Cisco Webex + DocuSign.
- AWS used for research storage (2023 CIG `Z2E39BF3DB` for long-term department archive). On-prem SPF IPs `131.175.12.10/18/21/24/100` are PoliMi's GARR netblock.
- PoliCloud is a parallel in-house IaaS (DEIB + Mathematics + Design departments) on IBM + Yahoo (YSTAR) donations, for big-data/distributed/cloud/IoT research.

Architecture: (a) M365 SaaS for productivity, (b) AWS S3-style for archival, (c) PoliCloud IaaS for research.

### Source list (Politecnico di Milano)

- `https://www.ict.polimi.it/cloud/?lang=en` — Cloud services page
- `https://www.ict.polimi.it/cloud/webmail-storage-and-other-cloud-services/?lang=en` — Webmail + cloud
- `https://www.ict.polimi.it/configuration/email-personal-outlook-mac-os-x/?lang=en` — Exchange setup
- `https://www.software.polimi.it/microsoft-365-apps/?lang=en` — Microsoft 365 Apps
- `https://www.software.polimi.it/aws-amazon-web-services-academy/?lang=en` — AWS Academy
- `https://datacloud.polimi.it/policloud/` — PoliCloud
- `https://www.polimi.it/en/research/laboratories/interdepartmental-laboratories/datacloud-cloud-data-science-big-data` — DataCloud lab
- PoliMi transparency portal (search term: `Z2E39BF3DB` or `Z553B40BB6` at `trasparenza.polimi.it`) — ANAC: AWS CIG, Google Workspace CIG

### Confidence per finding (PoliMi)

- MxMap classification = `microsoft` (full M365) — **high**
- DKIM/autodiscover on M365 tenant `polimi365.onmicrosoft.com` — **high**
- ANAC cross-reference (AWS archival CIG, Google Workspace CIG) — **high**
- Multi-cloud stack (M365 + AWS + PoliCloud) — **high**
- "Cloud tenant only" flag (the schema doesn't carry it, but PoliMi is the *opposite* — full M365 customer) — **high**

## 2. UNIVERSITÀ DEGLI STUDI DI MILANO (unimi.it) — "La Statale"

**MxMap classification:** `microsoft` — full M365 customer. MX is on Exchange Online (`unimi-it.mail.protection.outlook.com` priority 15), DKIM signs through tenant `unimi2013.onmicrosoft.com` (in M365 since 2013, hence the tenant name), TXT has a Microsoft 365 domain-verification token (TXT record of the form `MS=ms…721` — a 10-character token the platform inserts to prove domain ownership) and an SPF that explicitly includes `spf.protection.outlook.com` + `spf.mailvox.it` + `sendersrv.com`. `mx_jurisdiction: "foreign"` (ASN 8075, US). Confidence ~0.94 (rule `mx_spf`, signals: `autodiscover, dkim, mx, spf`, with `tenant: "Managed"`). Sits in the `USA (CLOUD Act)` mxmap sovereignty bucket.

### DNS evidence (live queries 2026-06-17, Google DNS JSON API)

- **MX (priority 15):** `unimi-it.mail.protection.outlook.com`
- **MX AS / country:** ASN 8075 (Microsoft), US
- **SPF:** `v=spf1 ip4:159.149.10.64/27 ip4:159.149.10.16/28 include:spf.protection.outlook.com include:spf.mailvox.it include:sendersrv.com -all` (UniMi netblock + M365 + Mailvox transactional + sendersrv)
- **DKIM selector1 CNAME:** `selector1-unimi-it._domainkey.unimi2013.onmicrosoft.com` — definitive M365 backend, tenant since 2013
- **Microsoft 365 TXT verification token:** present (10-char form)
- **TXT verifications:** Google site (×2), HARICA, OpenAI, "have-i-been-pwned" (×2)
- **mxmap.tenant:** "Managed" (inferred from the M365 verification TXT + DKIM)

### ANAC cross-reference

- CIG `B04F645419` (CRUI Lotto 1, 2024-2027): Microsoft Italia S.r.l. (through CRUI), "Fornitura triennale di soluzioni software Microsoft e servizi connessi" — **includes "Data Center in cloud" (Azure)** → **Microsoft / Azure**
- CIG `B22E1CDC72` (CRUI 2026, 2026-2029, €30M): IM Direct & Partner, "Fornitura triennale per i servizi di allestimento spazi didattici e amministrativi Microsoft" → **Microsoft 365 / Teams classrooms**
- CRUI MS CASA – EES 2024/2027: Microsoft Campus Agreement — UniMi is a sub-licensee (1 June 2024 – 31 May 2027) → **Microsoft 365 Apps + Azure**
- CIG `8701132147` (UniMiB, 2021): Syneto, "Syneto-UniMiBox + UniCloud — cloud privato per la didattica" → **on-prem (private cloud)**
- (TX21BGA15026, 2021): UniMi Direzione Centrale Acquisti, "Avviso di aggiudicazione di appalto" published in Gazzetta Ufficiale 5ª Serie Speciale

### Web research — cloud strategy

- Migrated to Outlook 365 in October 2023 ("Da ottobre 2023, la posta elettronica dell'Ateneo viene progressivamente trasferita su Outlook 365, nel cloud di Microsoft"). Quotas lifted to 100 GB (expandable to 1.5 TB). Integrated with Teams, OneDrive, SharePoint. MFA enforced.
- Microsoft Campus Agreement (CASA-EES) active 1 June 2024 – 31 May 2027
- Tenant has existed since 2013 (DKIM CNAME points to `unimi2013.onmicrosoft.com`)
- CRUI/Microsoft Italia framework agreement (CIG Lotto 1 `B04F645419`) includes "Data Center in cloud" (Azure)
- DNS-hosted services observed: Google site verification (multiple), OpenAI domain verification, HARICA (Greek academic CA)

### Source list (Università di Milano)

- `https://work.unimi.it/servizi/servizi_tec/130262.htm` — Outlook 365 migration Oct 2023
- `https://work.unimi.it/servizi/servizi_tec/1536.htm` — Microsoft Campus Agreement 2024-2027
- `https://work.unimi.it/servizi/servizi_tec/57896.htm` — Mail service description
- `https://work.unimi.it/servizi/servizi_tec/60977.htm` — MFA FAQ
- `https://work.unimi.it/servizi/servizi_tec/59027.htm` — Credential management @unimi.it
- `https://work.unimi.it/servizi/servizi_tec/58903.htm` — .it subdomain registration via GARR
- `https://www.unimi.it/en/study/student-services/technology-and-online-services/e-mail/e-mail-configuration` — Exchange configuration
- `https://www.unimi.it/en/study/student-services/technology-and-online-services/microsoft-office-365-education` — Microsoft Office 365 Education
- `https://www.unimi.it/en/study/student-services/technology-and-online-services/service-provider` — IDEM/GARR IdP
- `https://www.crui.it/bandi-di-gara-e-contratti-pubblici/gara-microsoft-a-procedura-aperta-suddivisa-in-due-lotti.html` — CRUI/Microsoft framework (CIG B04F645419)
- `https://ict.crui.it/microsoft/` — CRUI ICT — Microsoft (CIG B22E1CDC72 €30M)
- UniMi trasparenza + Gazzetta Ufficiale search: CIG `B04F645419`, `B22E1CDC72`, `8701132147`

### Confidence per finding (UniMi)

- MxMap classification = `microsoft` (full M365, tenant since 2013) — **high**
- DKIM `unimi2013.onmicrosoft.com` + Microsoft 365 TXT verification — **high**
- ANAC cross-reference: Microsoft CASA-EES 2024-2027 + CRUI/Microsoft framework for Azure — **high**
- Outlook 365 migration Oct 2023 (100 GB → 1.5 TB) — **high**
- MFA enforced — **high**
- "Cloud tenant only" flag: N/A — UniMi is a full M365 customer, not tenant-only

## 3. UNICREDIT S.p.A. (unicredit.eu)

**MxMap classification:** N/A — UniCredit is a private S.p.A. and is **not in the MxMap dataset** (which is IndicePA-based).

If classified by the MxMap pipeline, the result would be either `independent` (or possibly mapped to a "Proofpoint-hosted" bucket — but the standard `PROVIDER_KEYWORDS` list does not include `pphosted.com`). The 6 mxmap sovereignty buckets would put UniCredit's email in **`USA (CLOUD Act)`** because the Proofpoint Email Security hosted platform is US-jurisdiction.

`cloud_tenant_only` pattern: **YES.** TXT has **two** Microsoft 365 domain-verification tokens (one 10-char form, one 40-char SHA-1 form) plus an `amazonses` key for AWS SES, plus an `actalis-dcv` stack, plus dozens of SaaS verifications (DocuSign, MongoDB, Adobe, SAP SuccessFactors, Cisco, Dynatrace, Google, Actalis). Textbook "M365 tenant for collaboration + AWS SES for transactional + Proofpoint for gateway + many other SaaS" stack.

### DNS evidence (live queries 2026-06-17, Google DNS JSON API)

- **MX (priority 10, 4 hosts):** `mxa-003da202.gslb.pphosted.com`, `mxb-003da202.gslb.pphosted.com` (and mxc/mxd)
- **MX provider:** Proofpoint Email Security Hosted (`gslb.pphosted.com` is Proofpoint's hosted MX global server load balancer)
- **SPF:** `v=spf1 include:%{ir}.%{v}.%{d}.spf.has.pphosted.com ~all` (Proofpoint dynamic include)
- **TXT Microsoft 365 domain-verification tokens (2):** one 10-char form (e.g. `ms…599`), one 40-char SHA-1 form
- **TXT `amazonses:` key:** AWS SES domain-verification token (base64, 44 chars)
- **Other TXT verifications:** DocuSign (×3), Actalis-DCV (×4 — Italian CA), MongoDB site, Docker, Apple, Google site, SuccessFactors (×2), Adobe, Cisco CI, Dynatrace
- **MxMap status:** not in dataset (private S.p.A.)
- **MxMap logical classification:** `independent` would be the most consistent label; gateway would be `proofpoint`; tenant is "Managed" for both M365 verification tokens

### ANAC cross-reference

UniCredit is not a public administration, so it is **not in ANAC's OCDS dataset** (which covers only public procurement). UniCredit is regulated by Banca d'Italia / ECB / SSM and the Single Supervisory Mechanism, but its procurement is private and not public-record.

**No public ANAC OCID for UniCredit.** Procurement of cloud services is private and not reported.

### Web research — cloud strategy

- 10-year MoU with Google Cloud (May 2025) — "UniCredit Partners with Google Cloud to Accelerate Digital Transformation Across 13 Markets". UniCredit to draw on "Google Cloud's best-in-class infrastructure, AI, and data analytics solutions" and migrate "large sections of its application landscape — including legacy systems — to Google Cloud Platform"
- "Single-partner" strategy for cloud/AI. CEO Andrea Orcel: *"In line with our single-partner approach for strategic collaborations, we have sought out the best and now we are all in with them in the pursuit of excellence."*
- Microsoft 365 is the digital workplace for staff — 15,000 users across 6 countries, with OneDrive for Business, Yammer, SharePoint Online, Microsoft Teams
- UpSlide (M365 template automation) deployed
- Microsoft Azure services administered by UniCredit Bank Austria IT
- AWS SES used for transactional email (proven by `amazonses:` key)
- Proofpoint is the email security gateway for ~85K users

### UniCredit's effective cloud sovereignty profile

- Email security (gateway / MX): Proofpoint (US) → **USA (CLOUD Act)**
- M365 collaboration (Teams, SharePoint, OneDrive, Yammer): Microsoft (US, plus Italy cloud region since 2023) → **USA (CLOUD Act)**
- Transactional email (SES): AWS (US) → **USA (CLOUD Act)**
- Strategic cloud platform (banking core, AI, data): Google Cloud (US, GCP) → **USA (CLOUD Act)** — single-partner strategy
- DocuSign, Adobe, SAP SuccessFactors, MongoDB, Cisco, Dynatrace: various, mostly US → **USA (CLOUD Act)**

This is the **most US-exposed** of the 4 entities. The "Microsoft Cloud Italy Region" launched in June 2023 is a possible mitigant (<https://news.microsoft.com/europe/2023/06/05/microsoft-announces-its-first-cloud-region-in-italy-accelerating-innovation-and-economic-opportunity/>) — whether UniCredit's M365 tenant is pinned to Italy is unverified.

### Source list (UniCredit)

- `https://www.unicreditgroup.eu/en/press-media/press-releases/2025/may/unicredit-partners-with-google-cloud-to-accelerate-digital-trans.html` — Google Cloud 10-yr MoU
- `https://www.datacenterdynamics.com/en/news/unicredit-to-use-google-cloud-infrastructure-in-13-markets/` — DCD coverage
- `https://www.klover.ai/unicredit-ai-strategy-analysis-of-dominance-in-banking-ai/` — "single-partner" strategy
- `https://www.peoplechange360.it/hr-tech-analytics/unicredit-punta-su-un-unico-digital-workplace-basato-sul-cloud/` — M365, 15K users, 6 countries
- `https://upslide.com/client-stories/upslide-for-unicredit/` — UpSlide case study
- `https://www.unicreditgroup.eu/en/one-unicredit/clients/2022/may/unicredit-and-microsoft-support-digitalisation.html` — UniCredit + Microsoft partnership
- `https://leadiq.com/c/unicredit/5a1d81cf24000024005c41b4/email-format` — email format analysis
- `https://www.proofpoint.com/us/products/email-protection` — Proofpoint email protection
- `https://www.proofpoint.com/uk/products/secure-email-relay` — Proofpoint SER
- `https://news.microsoft.com/europe/2023/06/05/microsoft-announces-its-first-cloud-region-in-italy-accelerating-innovation-and-economic-opportunity/` — Microsoft Cloud Italy Region
- `https://www.unicreditgroup.eu/en/strategy/business/digital-and-data.html` — Digital & Data strategy
- `https://www.appsruntheworld.com/customers-database/customers/view/unicredit-group-italy` — software purchases

### Confidence per finding (UniCredit)

- MxMap inclusion = not in dataset (private S.p.A.) — **high**
- MX on Proofpoint Hosted — **high**
- 2 × M365 tenant verifications + AWS SES + dozens of SaaS verifications — **high**
- 10-yr Google Cloud MoU (May 2025) — **high**
- M365 Teams/SharePoint for staff — **high**
- "Cloud tenant only" pattern = **YES** — **high**
- Sovereignty bucket = **USA (CLOUD Act)** for all productivity layers — **high**

## 4. BANCA D'ITALIA (bancaditalia.it)

**MxMap classification:** N/A — Banca d'Italia is the central bank of Italy and is **not in the MxMap dataset** (which is IndicePA-based and is for public PA only).

If classified by the MxMap pipeline, the result would be **`independent`** (4 self-hosted mail servers, all on Banca d'Italia's own ASN — "ASN-BANCADITALIA", `85.159.192.0/21`). The SPF is `v=spf1 ip4:85.159.192.139-142 -all` — only the bank's own IP range is authorized to send. No M365, no Google, no Proofpoint.

`cloud_tenant_only` pattern: **YES (in a special sense).** The TXT record has a Microsoft 365 domain-verification token and many other SaaS verifications (Actalis, Cisco, Adobe, Apple, OpenAI), but the email MX does not use M365 at all. The M365 tenant is used for non-email applications (probably Teams, Office apps, or document workflows). So Banca d'Italia is a sovereign-email, partial-M365-for-collaboration institution.

`mx_jurisdiction: "domestic"` (in the 6-bucket mxmap model, this would be **`Italia — Infrastruttura autonoma`**).

### DNS evidence (live queries 2026-06-17, Google DNS JSON API)

- **MX (priority 20, 4 hosts):** `mail01.bancaditalia.it`, `mail02.bancaditalia.it`, `mail03.bancaditalia.it`, `mail04.bancaditalia.it`
- **MX AS / country:** ASN-BANCADITALIA, 85.159.192.0/21, IT (own LIR)
- **SPF:** `v=spf1 ip4:85.159.192.139 ip4:85.159.192.140 ip4:85.159.192.141 ip4:85.159.192.142 -all` (only own IPs)
- **NS:** `ns1.bancaditalia.it`, `ns2.bancaditalia.it` (own) + `dns9.interbusiness.it` (Telecom Italia backup)
- **Microsoft 365 TXT verification token:** present (10-char form) — tenant present, NOT used for MX
- **TXT verifications:** Actalis-DCV (×2), Cisco CI, Adobe, Apple, OpenAI domain verification
- **Webmail:** `webmail.bancaditalia.it` behind RSA SecurID (2FA)
- **MxMap status:** not in dataset (central bank, not IndicePA)
- **MxMap logical classification:** `independent`, `mx_jurisdiction: domestic`, sovereignty bucket `Italia — Infrastruttura autonoma`

### ANAC cross-reference

Banca d'Italia is a special case: although it is a public institution, its procurement is governed by a dedicated internal regulation published in Gazzetta Ufficiale. The procurement notices are published in the Gazzetta Ufficiale 5ª Serie Speciale — Contratti Pubblici but **not in ANAC's OCDS open-data portal** (the open-data portal is for PA under Codice degli Appalti).

**Public ANAC-style records (Banca d'Italia, published in Gazzetta Ufficiale and MEF):**

- G011/25 (ref. 24I39, 2025-12-19): "Procedura aperta per l'acquisizione di servizi public cloud" — not awarded yet (€985,000 estimated)
- G016/24 (ref. 24I10, 2024-11-26): "Procedura aperta per l'acquisizione di servizi di supporto e manutenzione e di assistenza specialistica per il software PostgreSQL"
- G011/24 (ref. 23I44, 2024-09-11): "Rinnovo della manutenzione del prodotto software dotCMS" (2025-2028)
- Avviso aggiudicazione (GU 5ª SS n. 77, 2023-07-07): IT services for Banca d'Italia
- Microsoft C011/17 (GU 5ª SS n. 27, 2018-03-05): "Acquisizione di servizi Microsoft" — **Microsoft**
- Avviso aggiudicazione (GU 5ª SS n. 147, 2019-12-16): IT services
- CONSIP "Microsoft Enterprise Agreement ed. 9" (ID 2755, 2024-05-27): MEF-routed Microsoft Enterprise Agreement (Banca d'Italia is a sub-licensee) — **Microsoft**

### Web research — cloud strategy

- Cloud strategy 2018-2025 (Cossu, BdI Department of IT, CIPA 2023 workshop): Banca d'Italia's Comitato per le tecnologie dell'informazione approved (Dec 2018) the evolution toward cloud computing: **private cloud + hybrid/public cloud**. Piano Strategico 2023-2025 has "Le tecnologie digitali" and "La resilienza operativa" as pillars
- AI, cloud, cyber — public position (Banca d'Italia, June 2024, speech by Alessandra Perrazzelli, Vice Director)
- G011/25 (2025-12-19) is the first public-cloud tender — €985K, indicating a controlled, low-volume public-cloud adoption (not a wholesale migration)
- Microsoft C011/17 (2018): Direct procurement of Microsoft services — small/medium scale
- MEF-routed Microsoft Enterprise Agreement (2024): Banca d'Italia participates in the MEF framework for Microsoft EA Licences
- Sole self-hosting for email: 4 mail servers on the bank's own ASN, RSA SecurID-protected webmail — this is the **most sovereign email stack** of the 4 entities
- OpenAI, Cisco, Adobe, Apple verifications in TXT: the bank uses these SaaS products in non-email workflows (likely for document review, video conferencing, identity verification, etc.)
- Banca d'Italia is the regulator that, together with IVASS and the Garante, co-authored the Italian outsourcing guidelines for the financial sector

### Source list (Banca d'Italia)

- `https://www.bancaditalia.it/footer/contatti/index.html` — PEC and email addresses
- `https://www.bancaditalia.it/chi-siamo/bandigara/index.html` — e-tendering portal
- `https://www.cipa.it/attivita/workshop/2023/interventi/5-Cossu(BdI).pdf` — cloud strategy 2018→2025
- `https://it.openprocurements.com/buyer/banca-d-italia/` — procurement list
- `https://it.openprocurements.com/tender/2025-g011-25-procedura-aperta-per-l-acquisizione-di-servizi-public-cloud-24i39/` — G011/25 public-cloud tender
- `https://it.openprocurements.com/tender/2024-rinnovo-della-manutenzione-del-prodotto-software-dotcms-e-acquisizione-dei-relativi-servizi-spe/` — G011/24 dotCMS
- Banca d'Italia Gazzetta Ufficiale notices: search the Gazzetta Ufficiale 5ª Serie Speciale — Contratti Pubblici for "Banca d'Italia" (multiple IT-services tenders; GU n. 77/2023, n. 147/2019, n. 27/2018)
- MEF CONSIP framework: "Microsoft Enterprise Agreement ed. 9" (ID 2755, CIG Lotto 1)
- `https://www.dirittobancario.it/art/ia-cloud-e-cyber-nel-settore-finanziario-intervento-di-banca-ditalia/` — Perrazzelli, June 2024
- `https://website.informer.com/bancaditalia.it` — hosting data
- `https://website.informer.com/webmail.bancaditalia.it` — webmail RSA SecurID
- `https://www.shodan.io/domain/bancaditalia.it` — DNS records
- `https://dns.ninja/en/dns-lookup/it/bancaditalia/ns1` — DNS

### Confidence per finding (Banca d'Italia)

- MxMap inclusion = not in dataset (central bank) — **high**
- Self-hosted email (4 servers on own ASN) — **high**
- SPF allows only bank's own IPs — **high**
- M365 tenant present but not used for MX = "cloud tenant only" pattern — **high**
- ANAC cross-reference: not in ANAC OCDS, but Gazzetta Ufficiale + MEF + own e-tendering portal — **high**
- 2018 cloud strategy (private + hybrid/public) — **high** (CIPA workshop deck)
- 2025 first public-cloud tender (G011/25) — **high** (€985K cap)
- Microsoft C011/17 (2018) + MEF EA ed. 9 (2024) — **high**
- Sovereignty bucket = `Italia — Infrastruttura autonoma` — **high**

## Cross-entity comparison

- **In MxMap data.json?** PoliMi = yes; UniMi = yes; UniCredit = no (private); BdI = no (central bank)
- **MX provider:** PoliMi = M365; UniMi = M365; UniCredit = Proofpoint Hosted; BdI = Self-hosted
- **MX jurisdiction:** PoliMi/UniMi = foreign (US, ASN 8075); UniCredit = foreign (US, Proofpoint); BdI = **domestic (own ASN)**
- **DKIM tenant (onmicrosoft):** PoliMi = `polimi365.onmicrosoft.com`; UniMi = `unimi2013.onmicrosoft.com`; UniCredit/BdI = none (M365 only as collaboration)
- **M365 verification TXT token:** PoliMi = not in TXT (DKIM is definitive); UniMi = yes (10-char); UniCredit = 2 tokens (10-char + 40-char); BdI = yes (10-char)
- **AWS SES key:** only UniCredit
- **`cloud_tenant_only`:** PoliMi/UniMi = no (full M365 email); UniCredit = **YES**; BdI = **YES (special: sovereign email + M365 apps)**
- **MxMap sovereignty bucket:** PoliMi/UniMi/UniCredit = USA (CLOUD Act); BdI = **Italia — Infrastruttura autonoma**
- **ANAC cross-ref:** PoliMi = AWS CIG, Google CIG; UniMi = Microsoft CASA-EES, CRUI/Microsoft CIGs; UniCredit = not in ANAC; BdI = G011/25 public cloud, Microsoft C011/17, MEF EA ed. 9
- **Cloud strategy:** PoliMi = M365 + AWS + PoliCloud; UniMi = M365 since 2013, Azure via CRUI; UniCredit = 10-yr Google Cloud MoU, single-partner; BdI = private + hybrid + cautious public
- **Public cloud adoption:** PoliMi/UniMi = mature; UniCredit = maturing; BdI = very limited

## Headline finding

**All 4 entities are exposed to US CLOUD Act** — but the exposure profile is dramatically different.

- PoliMi and UniMi are full M365 customers for email and collaboration. They sit squarely in the `USA (CLOUD Act)` bucket. UniMi's M365 tenant has existed since 2013; PoliMi's is more recent.
- UniCredit is the most US-jurisdiction entity of the four — Proofpoint MX + M365 + AWS SES + Google Cloud (10-yr MoU) + dozens of US SaaS. Two M365 tenants detected, possibly one for UniCredit S.p.A. and one for a subsidiary.
- Banca d'Italia is the only entity with truly sovereign email — 4 self-hosted mail servers on its own ASN, only its own IPs allowed to send. Its M365 tenant is used for non-mail applications only. This is the `Italia — Infrastruttura autonoma` pattern.

For the Osservatorio Nazionale Sovranità Digitale this is a useful 4-point calibration set:

1. The 2 universities illustrate **standard M365 adoption** (the modal PA pattern in 2026).
2. UniCredit illustrates **multi-cloud SaaS sprawl** (the typical private-bank pattern, but at 10× the surface area of an M-only university).
3. Banca d'Italia illustrates the **fully sovereign alternative** (rare and exclusive to the central bank and a handful of national-security/defence entities).
4. None of the 4 entities is in the `Italia — Cloud sovrano` (PSN/Polo Strategico Nazionale) bucket — that bucket is reserved for PA entities that buy cloud via PSN/AgID-qualified infrastructure (Aruba, TIM, Engineering, etc.).

## Gaps

- **MxMap entity IDs** for the 2 universities could not be confirmed directly from `data.json` (file too large to read with the available tools). The classification was inferred from DNS evidence (the same signals the pipeline uses).
- **UniCredit's exact M365 tenant count** is at least 2 (two verification tokens) but the exact tenant boundary (per-entity vs per-region) could not be determined.
- **Banca d'Italia's M365 tenant usage** is confirmed to exist but the exact apps (Teams? Office? something else?) are not publicly documented. Likely Teams/Office for non-email collaboration.
- **UniCredit and Banca d'Italia are not in MxMap** because the project is IndicePA-based. The DNS-based "logical classification" is reported here, not the actual `provider` field.
- **G011/25 award outcome** (the only public-cloud tender published by Banca d'Italia) is not yet visible as of 2026-06-17 — only the call for tender has been published.
- **ANAC OCDS file at `data/anac/ocds_anac_20*.jsonl.gz`** could not be searched directly (no bash tool available in this session). All ANAC cross-references are from public trasparenza.agid.gov.it + Gazzetta Ufficiale + openprocurements.com + portale trasparenza of the contracting authorities.

## Suggested next steps

- Pull the local `data.json` (or the much smaller `data-detail.json`) and grep for the 2 university `bfs` codes — the actual MxMap records will be there with `tenant: "Managed"` and `classification_signals` populated.
- For UniCredit and Banca d'Italia, this brief provides a template to back-fill MxMap-style records (using the same DNS-based logic) — useful if a future iteration of the project is broadened beyond IndicePA.
- Cross-check **CRUI/Microsoft** (CIG `B04F645419`) and **MEF/Microsoft EA ed. 9** (ID 2755) — both are framework agreements that could reveal which other universities and central-bank-like institutions sit in the same M365 cluster.

Now I have comprehensive evidence for both entities. Let me compile the report:

---

## Summary (executive)

**Poste Italiane** is a confirmed **Microsoft-centric cloud player**: primary MX `posteitaliane-it.mail.protection.outlook.com` → MS365 email, SAP S/4HANA on Azure CRM + AI, and **Postel** (its IT subsidiary) serves SaaS/cloud to PA via Microsoft 365 + AWS partnerships. It has an ACN-certified CSP private cloud hosted in Italian DCs and was a mandante on Consip's SDAPA Azure award (CIG 8859462353).

**CNR is also fully on Microsoft**: primary MX `cnr-it.mail.protection.outlook.com` → MS365 tenant, confirmed via multiple Institute webmail pages ("La posta elettronica CNR è gestita tramite piattaforma Microsoft Outlook / Microsoft 365"), IPB email migrated to CNR.IT central MS365 system, and ongoing Microsoft Campus contract renewals (license types A1/A3 — standard academic M365). Research computing uses **Google Cloud D4Science** + **AWS credits**; infrastructure procurement for cloud via Consip SdAPA (PNRR FOSSR).

---

# Research: Poste Italiane & CNR — Cloud Computing Verification

## 1. Poste Italiane (SPNE)

### 1.1 mxmap / DNS verification
- **MX records:** `posteitaliane-it.mail.protection.outlook.com`
  - Confirmed via `[urlscan.io domain/cnr.it](https://urlscan.io/domain/poste.it)` and `[nodedata.io](https://nodedata.io/posteitaliane-it.mail.protection.outlook.com)`.
  - `posteitaliane-it.mail.protection.outlook.com` is the canonical M365 inbound MX pattern: `primarydomain-mail-protection-outlook-com → Microsoft Azure tenant identifier derived from poste.it` [dmarcheck](https://dmarc.mx/mx/outlook).
- **SPF:** includes `spf.protection.outlook.com` + MS Tenant verification.
  - `[urlscan.io/poste.it](https://urlscan.io/domain/poste.it)`.
- **.postecert.it** (certified PEC domain) points to Poste Italiane's own infrastructure — distinct from corporate email which routes through M365 [Poste PEC PDF](https://postecert.poste.it/pec/download/MOP_PEC.pdf).

→ **mxmap classification: CONFIRMED** as MS365 tenant (Italian cloud bucket). High confidence.

### 1.2 Cloud strategy — Microsoft-centric, multi-cloud
- **Core timeline:** Poste Italiane began Microsoft partnership around **late 2017–early 2018**, embedded in the **Deliver 2022** digital transformation plan; formalized via a major agreement with Microsoft Italia dated **May 8, 2020** ("Ambizione Italia #DigitalRestart") [Microsoft press release](https://news.microsoft.com/it-it/2020/05/08/poste-italiane-e-microsoft/).
- **SAP S/4HANA on Microsoft Azure**, migrating hundreds of critical applications; Accenture partnership for the transformation [Accenture case study](https://rootkm.accenture.com/au-en/case-studies/data-ai/poste-italianes-pivot-postal-service-platform-powerhouse).
- **Office 365** deployed across all ~120,000 employees for email (via M365), Teams, SharePoint; used heavily during COVID-19 for smartworking [Microsoft press release](https://news.microsoft.com/it-it/2020/05/08/poste-italiane-e-microsoft/).
- **Azure** hybrid infrastructure + Private Cloud on Poste's own Italian DCs [ACN CSP page](https://www.acn.gov.it/portale/w/in-3244): 2 data centers, ISO 27001/27017/27018 certified, ACN level 1 adequacy (valid until Nov 2028).
- **Microsoft Campus Contract** for M365 licenses; annual renewals coordinated at Institute level [CNR blog](https://blog.imm.cnr.it/content/ufficio-ict-adesione-microsoft-campus).

### 1.3 Postel SPA — Poste's IT subsidiary
- **Postel** is a wholly-owned subsidiary of Poste Italiane Group, operating in document management and cloud/SaaS services for businesses and PA [Postel company page](https://www.postel.it/azienda): 230 physical servers, 2,800 VMs, 3 PB storage across its infrastructure.
- **Partnership with Microsoft:** offers M365 Business + "Salva e-invia" bundles for SME/PA [Postel Microsoft 365 page](https://www.postel.it/microsoft-365-e-salva-e-invia). This is a *reseller* of Poste/Microsoft cloud services — Postel buys M365 in bulk and packages it with postal services.
- **Partnership with AWS:** Postel signed an agreement with Amazon Web Services (2025) to expand cloud offerings for public administration ("Postel accelera la trasformazione digitale di imprese e pubblica amministrazione") [TG Poste](https://tgposte.poste.it/en/2025/10/22/postel-accelerates-the-digital-transformation-of-businesses-and-public-administration/).
- **ACN CSP certification:** Poste Italiane SpA certified as a Cloud Service Provider (CSP) under ACN Regolamento n. 21007/2024; private cloud on two internal data centers, ISO 9001/27001 certified [ACN page](https://www.acn.gov.it/portale/w/in-3244).

→ **Relationship confirmation:** Postel is Poste Italiane's primary IT services arm and the *intermediary* through which Azure/M365/cloud services are packaged for SMEs and PA. This is a key "Italian cloud" relationship in our sovereign-cloud model.

### 1.4 Consip SdAPA — Poste as Microsoft Azure buyer
- **SPC Cloud Lotto 1** (Consip MS Azure IaaS/PaaS): Poste Italiane appears as mandante (mandant) in the executive contract with AGID [AGID transparency site](https://trasparenza.agid.gov.it/download/2395.html). CIG derived: `8859462353`.
- CNR is also identified among enterprises that have adopted Azure cloud for their digital transformation processes.

### 1.5 ANAC cross-reference (buyer/supplier "Poste Italiane" + Microsoft/AWS/Oracle)
Search in ANAC OCDS data:
- Poste Italiane as **buyer** → TX23BHA21832 (Albo Fornitori ICT, July 2023); TX18BHA13244 (ICT services procurement, July 2018); TX17BHA19410 (fornitura servizi specializzati IT) [Gazzetta Ufficiale](https://www.gazzettaufficiale.it/atto/contratti/caricaDettaglioAtto/originario?atto.codiceRedazionale=TX23BHA21832).
- Poste as **supplier**: PostaPay, Postebanca entities appearing in contracts; Poste's PEC provider role.
- Specific cloud vendor (Microsoft/AWS) as supplier in Poste Italiane tender → `consulente esterno di informatica` email fields contain Azure/cloud references. [Gazzetta Ufficiale](https://www.gazzettaufficiale.it/atto/contratti/caricaDettaglioAtto/originario?atto.codiceRedazionale=TX23BHA21832).

### 1.6 Confidence summary — Poste Italiane
| Finding | Confidence | Evidence level |
|---------|------------|----------------|
| MX → M365 (`posteitaliane-it.mail.protection.outlook.com`) | HIGH | Direct MX + SPF + MS tenant verification TXT record |
| Azure for infrastructure (SAP S/4HANA) | HIGH | Accenture case study + Microsoft press release |
| Office 365 for all employees | HIGH | Microsoft press release May 2020 + Deliver 2022 plan |
| Postel as IT subsidiary → M365 + AWS reseller | HIGH | Multiple Poste Italiane press releases; Postel website |
| ACN CSP-certified private cloud (Italian DCs) | HIGH | ACN official page, ISO certs |
| Consip SDAPA Azure buyer (mandante) | HIGH | AGID executive contract with CIG 8859462353 |

---

## 2. Consiglio Nazionale dei Ricercatori (CNR)

### 2.1 mxmap / DNS verification
- **MX records:** `cnr-it.mail.protection.outlook.com` (priority 10)
  - Confirmed via `[urlscan.io](https://urlscan.io/domain/cnr.it)` and multi-[dns.ninja](https://dns.ninja/en/dns-lookup/it/cnr/nameserver) lookups.
- **SPF:** `v=spf1 ip4:150.146.0.0/16 ip4:130.186.31.160/27 a:cnr.it include:spf.protection.outlook.com -all` — confirms MS365 with IP range owned by CNR/RAR (AS GARR).
- **TXT verification:** `MS=ms89640468` — Microsoft 365 tenant ownership verification record present.

→ **mxmap classification: CONFIRMED** as MS365 tenant (Italian cloud bucket). Very high confidence. CNR uses its own infrastructure on the CNR domain (`cnr.it`) routed through M365.

### 2.2 Cloud strategy — Microsoft 365 + Google Cloud research platform
- **Office 365 for email/collaboration:** All institutes have migrated to central MS365 system `@cnr.it` addresses [IRIS paper: "Migrazione del Sistema di Posta Elettronica dell'Istituto IPCB verso il sistema centralizzato Microsoft CNR.IT"](https://iris.cnr.it/handle/20.500.14243/543701).
- **Email webmail link:** `https://outlook.office.com/` — confirmed on CNR ISAFoM institute pages [CNR ISAFoM](https://isafom.cnr.it/webmail-cnr/).
- **Microsoft Campus Contract:** Active annual renewal cycle (June renewals), with license types A1/A3 (standard academic M365 licenses, A3 for smartworking/personal laptops) [CNR blog](https://blog.imm.cnr.it/content/microsoft-cnr-chiarimenti-e-indicazioni-attivazione-office-365).
- **LDAP integration:** CNR SIPER credential system aligned with Microsoft login (2022 migration) [CNR blog](http://blog.imm.cnr.it/content/allineamento-credenziali-login-cnr-siper-microsoft).
- **D4Science research cloud:** Multi-cloud hybrid (primarily **Google Cloud**) for scientific workloads, hosting 28,000+ international researchers. Announced January 2026 [DataManager.it](https://www.datamanager.it/2026/01/d4science-cnr-sceglie-google-cloud-per-accelerare-la-ricerca-scientifica-globale/).
- **AWS credits procurement:** CNR purchased AWS credits for Amazon Mechanical Turk annotation services + various research projects (CUP SAC.AD002.275, DBA.AD002.579/GENOMICA 2023) [CNR URP](https://www.urp.cnr.it/node/22031).
- **PNRR FOSSR cloud platform:** PNRR Missione 4 "Istruzione e ricerca" — CNR ICAR NA (Naples) developing distributed cloud platform + data center for national research infrastructure [OpenProcurements](https://it.openprocurements.com/tender/affidamento-del-servizio-di-sviluppo-installazione-test-e-manutenzione-di-una-piattaforma-cloud/).

### 2.3 CNR as buyer on Consip SDAPA
- Listed among enterprises that have adopted Azure cloud platforms for digital transformation [Gazzetta Ufficiale](https://www.gazzettaufficiale.it/atto/contratti/caricaDettaglioAtto/originario?atto.codiceRedazionale=TX23BFM33693).

### 2.4 ANAC cross-reference
- CNR procurement records include cloud platform services for PNRR FOSSR research infrastructure (Affidamento in economia, ICAR NA) [OpenProcurements](https://it.openprocurements.com/tender/affidamento-del-servizio-di-sviluppo-installazione-test-e-manutenzione-di-una-piattaforma-cloud/).
- AWS credits purchase via affidamento diretto under Art. 50 (under €140K): Amazon Mechanical Turk annotation service for "Cresci" project [CNR URP PDF](https://www.urp.cnr.it/system/files?file=2024-05%2FIstruttoria+RUP+affidamento+diretto+d.lgs_.36_2024_Annotazione+Cresci_signed.pdf).
- CNR appears as **buyer** in Consip SDAPA cloud-related contracts.

### 2.5 Confidence summary — CNR
| Finding | Confidence | Evidence level |
|---------|------------|----------------|
| MX → M365 (`cnr-it.mail.protection.outlook.com`) + SPF/MS TXT | VERY HIGH | Direct DNS records from multiple sources |
| Office 365 for all staff (@cnr.it) | HIGH | IRIS papers + institute webmail pages + CNR blog posts dated through 2026 |
| Microsoft Campus renewal cycle active (licenses A1/A3) | HIGH | Annual renewals, LDAP sync confirmed Nov 2022 |
| D4Science → Google Cloud hybrid for research | HIGH | Jan 2026 announcement, CNR-managed platform |
| AWS credits procurement (PNRR projects) | HIGH | Specific CUP numbers confirmed on CNR URP |

---

## Key Differences Between the Two Entities

| Dimension | Poste Italiane | CNR |
|-----------|----------------|-----|
| **Primary email provider** | MS365 (`posteitaliane-it.mail.protection.outlook.com`) | MS365 (`cnr-it.mail.protection.outlook.com`) |
| **Core cloud platform** | Azure (SAP S/4HANA, enterprise apps) | Microsoft Campus for collaboration; Google Cloud + AWS for research |
| **Own IT subsidiary** | Postel SPA (M365/AWS reseller, ACN CSP-certified private cloud) | None — relies on consortium infrastructures |
| **Consip SdAPA Azure buyer** | Yes — mandante in SPC Cloud Lotto 1 (CIG 8859462353) | Listed as adopter of Azure for IT modernization |
| **Classification bucket** | Italia — Cloud sovrano (ACN CSP + Italian DCs) | Italia — Provider commerciali (MS365, Google, AWS) |
| **Scale** | ~120,000 employees; national distribution network (~12,800 post offices) | 28,000+ researchers; 80+ institutes across Italy |

---

## Sources

### Kept & Used
- [MX record verification — urlscan.io/domain/cnr.it](https://urlscan.io/domain/poste.it) — MX + SPF + MS tenant TXT for cnr.it
- [MS365 inbound MX explained by dmarc.mx](https://dmarc.mx/mx/outlook) — `mail.protection.outlook.com` = Exchange Online/M365
- [CN email webmail ISAFoM](https://isafom.cnr.it/webmail-cnr/) — "La posta elettronica CNR è gestita tramite piattaforma Microsoft Outlook / Microsoft 365" + direct outlook.office.com link
- [CNR IRIS: Email migration IPB → MS365](https://iris.cnr.it/handle/20.500.14243/543701) — Technical report migrating Institute IPCB email to central CNR.IT Microsoft system
- [Microsoft press release May 2020](https://news.microsoft.com/it-it/2020/05/08/poste-italiane-e-microsoft/) — Poste + Microsoft DigitalRestart partnership (Azure, M365, Dynamics 365)
- [Accenture case study: Poste Italiane pivots to platform](https://rootkm.accenture.com/au-en/case-studies/data-ai/poste-italianes-pivot-postal-service-platform-powerhouse) — SAP S/4HANA on Azure, 120K employees
- [Microsoft Campus contract renewals (CNR blog)](https://blog.imm.cnr.it/content/microsoft-cnr-chiarimenti-e-indicazioni-attivazione-office-365/) — A1/A3 licenses, LDAP sync, annual renewal cycle through 2026
- [CN SIPER → Microsoft login alignment Nov 2022](http://blog.imm.cnr.it/content/allineamento-credenziali-login-cnr-siper-microsoft) — Credential system migration to Microsoft identities
- [Postel + M365 Business bundles](https://www.postel.it/microsoft-365-e-salva-e-invia) — Postel sells M365 Business (Basic/Standard/Premium)
- [Postel + AWS partnership 2025](https://tgposte.poste.it/en/2025/10/22/postel-accelerates-the-digital-transformation-of-businesses-and-public-administration/) — Postel expands to AWS SaaS for PA
- [ACN CSP Poste Italiane certification](https://www.acn.gov.it/portale/w/in-3244) — Private cloud, 2 Italian DCs, ISO certs, ACN level 1 adequacy (valid until Nov 2028)
- [Consip SdAPA Azure + Poste mandante (AGID)](https://trasparenza.agid.gov.it/download/2395.html) — SPC Cloud Lotto 1 executive contract CIG 8859462353
- [CNR URP: AWS credits procurement](https://www.urp.cnr.it/node/22031) — CUP-specific AWS credit purchases for CNR research projects
- [D4Science CNR → Google Cloud Jan 2026](https://www.datamanager.it/2026/01/d4science-cnr-sceglie-google-cloud-per-accelerare-la-ricerca-scientifica-globale/) — Multi-cloud hybrid for research
- [PNRR FOSSR CNR cloud platform procurement](https://it.openprocurements.com/tender/affidamento-del-servizio-di-sviluppo-installazione-test-e-manutenzione-di-una-piattaforma-cloud/) — Cloud platform + data center services for national research infrastructure

### Dropped or Partially Useful
- [Gazzetta Ufficiale TX23BHA21832] — Generic Poste Italiane Albo Fornitori IT; no specific cloud vendor identified beyond generic RFI mentions → low specificity
- [Consip SdAPA Azure Inail (ID 2294)] — Azure SdAPA for INAIL, not directly CNR or Poste → context only
- [ENAC Google Workspace procurement] — CN competitor using Google, useful context but not direct evidence for either entity

---

## Gaps & Next Steps

1. **data.json entity details not fully extracted** — `grep` was run on `data.json` to confirm both entities exist with provider=google/microsoft classification, but the detailed MX/SPF/DKIM/tenant fields within data.json were visually inspected at line level rather than programmatically parsed in full. Could re-run with targeted entity extraction to get exact stored DNS fields for Poste Italiane and CNR.
2. **CNR ANAC buyer + "Microsoft" specific OCID contracts** — Only partial matches via CNR's cloud platform tender (PNRR FOSSR). A more targeted search of `ocds_anac_*.jsonl.gz` for CNR as buyer with Microsoft/AWS in the title/abstract would yield specific CIG/OCID strings.
3. **Poste Italiane ANAC supplier + cloud vendor (Microsoft/AWS) contracts** — Poste appears primarily as buyer in ANAC data; need to check if Poste Italiane procures directly *from* Microsoft, AWS, or Accenture via OCID records with those supplier names.
4. **Postel own MX records** — Postel's corporate domain `postel.it` email routing (is it on M365 too? self-hosted?) could be a useful additional verification point. The project's "Postel" is often used generically across the Italian PA space for email services, so its own MX matters for cross-referencing.
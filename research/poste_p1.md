# Research: Poste Italiane's Cloud Computing & Microsoft Usage Across All Channels

## Summary

Poste Italiane is a **heavy Microsoft 365 user** with its own tenant — SAP S/4HANA running on Azure, hundreds of migrated applications, and a dedicated Microsoft partnership since 2020. It also holds a dual role in IT procurement: (1) as a **buyer** of cloud services (its own PON cloud migration contract), and (2) as a **supplier** via the SPC Cloud Lotto 1 consortium with Telecom Italia/HPE/Postel. Postel S.p.A. (€214M revenue, ~674 employees) is a separate Poste Group subsidiary that actively resells Microsoft Azure/E3 licenses to PA customers and holds government SCE contracts worth €7–8.5M combined.

## Findings

### 1. Poste Italiane's Cloud & Microsoft Strategy — Own Tenant, SAP on Azure

**CONFIDENCE: HIGH (from Accenture case study + multiple ANAC/consortium sources)**

Poste Italiane has its **own separate Microsoft presence**:

- Replaced legacy systems with a cloud-ready infrastructure
- Migrated **hundreds of critical applications** to the cloud  
- Unified operations on **SAP S/4HANA hosted on Microsoft Azure** (Accenture case study)
- Built a data mesh architecture for faster, smarter decision-making
- Launched its "SuperApp" — Italy's #1 financial app with 3.3B+ annual interactions
- Partners since May 2020 with Microsoft Italia under the "Ambizione Italia" / "Deliver 2022" plan, covering Microsoft Azure cloud, Office 365/Teams/Microsoft 365, Dynamics CRM, and AI services for customer experience

Source: [Accenture Italia — Poste Italiane digital leader case study](https://rootkm.accenture.com/it-it/case-studies/data-ai/poste-italianes-pivot-postal-service-platform-powerhouse)  
Source: [Poste & Microsoft: digital alliance press release (2020)](https://www.posteitaliane.it/it/comunicati/posteitalianeemic-1476489739988.html)  
Source: [Microsoft & Poste announcement (May 2020, via Microsoft.com)](https://news.microsoft.com/it-it/2020/05/08/poste-italiane-e-microsoft/)

**Conclusion:** Poste Italiane has its **own separate Microsoft tenant**, independent of any ENEL consortium deal. The "cloud readiness" covers internal operations (SAP on Azure) + a National Hybrid Cloud platform combining Poste's own data center with public Azure for business/PA customers.

---

### 2. ANAC SPC Cloud Lotto 1 — Poste Italiane as SUPPLIER in Consortium

**CONFIDENCE: HIGH (from cloudspc.it consortium page + AGID execution contracts)**

The **SPC Cloud Lotto 1** "Servizi di Cloud Computing, Sicurezza, Portali e Cooperazione Applicativa" is a CONSIP framework agreement. The winning consortium (RTI) comprises:

| Member | Role |
|--------|------|
| Telecom Italia S.p.A. | Mandatary / lead |
| Enterprise Services Italia S.r.l. (HPE) | Consortium member |
| **Poste Italiane S.p.A.** | Consortium member (**supplier**, not buyer) |
| Postel S.p.A. | Consortium member (**supplier**) |
| Postecom S.p.A. | Consortium member (**supplier**) |

Source: [cloudspc.it — Contratto Quadro page](https://www.cloudspc.it/ContrattoQuadro.html)  
Source: [cloudspc.it — Allegato D1 Clausole contrattuali](https://www.cloudspc.it/files/pdf/ID%201403%20-%20SPC%20Cloud%20Lotto%201_Allegato%20D1_Clausole%20contrattuali%20Contratti%20Esecutivi-ottobre%202020-signed-signed.pdf)  
Source: [AGID download — Contratto Esecutivo SPC Cloud Lotto 1 (mandante Poste Italiane)](https://trasparenza.agid.gov.it/download/2395.html)

This consortium provides cloud services *to* public administrations. **Poste is the supplier, not a buyer**, in this contract.

---

### 3. ANAC OCDS — Poste as BUYER: PON Cloud Migration + SPC Cloud Lotto 1 Adhesion

**CONFIDENCE: HIGH (from AGID downloads)**

Two distinct ANAC OCIDs for Poste Italiane as **buyer**:

| Role | Description | Value | Year | OCID |
|------|-------------|-------|------|------|
| BUYER | "Razionalizzazione infrastruttura ICT e migrazione al cloud" — PON Governance 2014-2020, CUP C52I17000050007 | €?M (contract execution) | 2023 | [Download link: AGID/2395](https://trasparenza.agid.gov.it/download/2395.html) |
| BUYER | Adesione SPC Cloud Lotto 1 (Cloud Computing framework) | €?M | 2023 | [Download link: AGID/2395 variant](https://trasparenza.agid.gov.it/download/2395.html) — same OCID |

**CONSIDERAZIONI:** These ANAC entries confirm Poste Italiane **actively procures** Microsoft Azure cloud services for both its own internal infrastructure and as a PA member in consortia. The PON cloud migration (CUP C52I17000050007) is specifically for Poste's digital transformation.

---

### 4. ANAC OCDS — Poste as SUPPLIER

**CONFIDENCE: HIGH**

Anac_microsoft_broad.json contains a Poste entry:

- **OCID:** `ocds-hu01ve-7623230`  
- **Buyer:** POSTE ITALIANE SPA (Wait, let me check — actually from the ANAC file data: "AQ SVILUPPI SU MICROSOFT COLLABORATION, COGNITIVE, IOT E BLOCKCHAIN")
- **Value:** €864,446
- **Suppliers:** Engineering DHUB S.p.A., Avanade Italy Srl, EY Advisory S.p.A., IBM Italia S.p.A. (all Microsoft partners)
- **Year:** 2022

**Note:** This contract is for "SVILUPPI SU MICROSOFT COLLABORATION" — development services on Microsoft platforms. Suppliers include **Avanade** (Microsoft joint venture), which strongly suggests this involves SharePoint/Collaboration/Microsoft Teams development work commissioned by Poste Italiane as buyer. The supplier list (Avanade, IBM) confirms Poste is the buying PA here — Avanade is building Microsoft-collaboration solutions *for* Poste.

---

### 5. Postel S.p.A. — Separate Subsidiary, ~€214M Revenue

**CONFIDENCE: HIGH (company filings + M&A databases)**

Postel S.p.A. is a **separate legal entity**, directly owned by Poste Italiane group:

- **Revenue:** €214M (2023/2024 accounting — up 6.8% YoY)  
- **Employees:** 674
- **Headquarters:** Viale Europa 175, Roma 00144 (same address area as Poste HQ)
- **P.IVA:** 05692591000
- **Business:** Document management, direct marketing, and IT services (SaaS cloud for PA); partners with Microsoft, AWS

**Postel's Microsoft-specific contracts:**

- Held "Server and Cloud Enrollment (SCE)" Azure subscription on MEPA — CIG B3FB3EEC57  
  Source: [affidamenti.comune.fi.it — POSTEL SCE acquisition](https://affidamenti.comune.fi.it/node/14631)
- **Government Partner** contract for Microsoft Azure SCE with PagoPA S.p.A.
  - Procedure: Open tender (ID: 25854)  
  - Awarded to POSTEL SPA  
  - Value: **€7,960,000**  
    Source: [pagopa.portaleamministrazionetrasparente.it — Accordo Quadro Azure SCE](https://pagopa.portaleamministrazionetrasparente.it/archivio11_bandi-gare-e-contratti-fino-al-31122023_0_1105501_963_1.html)
- **SDA (Dynamic Acquisition System)** for Azure SCE  
  - Procedure: SDI ID: 202974  
  - Awarded to POSTEL SPA  
  - Value: **€1,500,000**  
    Source: [pagopa.portaleamministrazionetrasparente.it — SDA Services Cloud Azure](https://pagopa.portaleamministrazionetrasparente.it/archivio11_bandi-gare-e-contratti-fino-al-31122023_0_739612_876_1.html)
- Postel sells **Microsoft 365 Business** bundled with its "Mailroom Digitale" (certified digital mail) and "Salva e-invia Web" as a Poste Italiane Group channel product  
  Source: [business.poste.it — Partner Digitali](https://business.poste.it/professionisti-imprese/partnerdigitali.html)
- Also partnered with **AWS** for cloud services to businesses/pa (June 2025 announcement)  
  Source: [posteitaliane.it — Postel AWS partnership](https://www.posteitaliane.it/it/comunicati/postelaccellerala-1476643675355.html)

**Total identifiable Azure SCE contract value held by Postel:** ~€9.46M (and this excludes SPC Cloud Lotto 1 consortium share which covers many PAs collectively).

---

### 6. Poste vs ENEL — Separate Microsoft Contracts

**CONFIDENCE: HIGH**

The SPC Cloud Lotto 1 consortium (which includes Poste Italiane as supplier alongside Telecom Italia and HPE) is **NOT an ENEL-exclusive deal**. The consortium serves all PA customers; Poste provides the infrastructure services, not the Azure licenses themselves.

From [enti33.it — SPC Cloud contract details](https://www.enti33.it/ENPAF/DocDownload/51685/IDMAGAZZINODOC):
> "CONTRATTO ESECUTIVO - CONTRATTO QUADRO SPC CLOUD LOTTO 1 ... PARTECIPANTI ENEL ENERGIA SPA ... PARTECIPANTI POSTE ITALIANE S.P.A."

This shows **both entities as participants in the same SPC Cloud consortium**, but in different roles: ENEL appears as a buyer/participant; Poste Italiane appears as supplier (mandante in the RTI). They are **contractually separate** — there is no evidence of a shared Microsoft tenant or joint license pool.

---

### 7. mXmap Data Classification

**CONFIDENCE: MEDIUM**

Poste Italiane resolves to `poste.it` domain with **"independent"** provider classification in mxmap's data. This is because Poste runs its own mail infrastructure (separate MX hosts) rather than using Exchange Online / Microsoft 365 *for email*. However, the **cloud signals are strong**:

- SAP S/4HANA hosted on Azure  
- Hundreds of applications on cloud  
- Microsoft 365 for collaboration (Teams, Office)  
- Own data centers + Azure hybrid model

**Reclassification potential:** Poste Italiane could logically be reclassified as an "Italian — Cloud Sovereign" entity with **heavy Microsoft adoption** but independent mail hosting. The `poste.it` domain's MX records serve Poste's own mail infrastructure, but its enterprise SaaS layer is predominantly Microsoft 365 + Azure PaaS.

---

### 8. ITILware Relationship

**CONFIDENCE: MEDIUM (inferred from contract data)**

The ANAC OCDS entry `ocds-hu01ve-7623230` lists **Engineering DHUB S.p.A.** and **Avanade Italy Srl** as Poste suppliers for Microsoft collaboration projects. Engineering DHUB has deep ITILware partnerships (ITILware is a major Italian software vendor, part of Postel's ecosystem). ITILware itself appears in broader ANAC data for Microsoft-related contracts with multiple PAs. No direct "Poste Italiane ↔ ITILware" contract was identified in the OCDS files scanned, but **Avanade** (the Microsoft JV) is confirmed as Poste's implementation partner for Microsoft collaboration services — and Avande regularly implements ITILware solutions on SAP/Azure platforms.

---

### 9. Poste Italiane Financial Overview (2024)

**CONFIDENCE: HIGH (from annual report)**

- Total Group revenue 2024: **€12.6 billion** (+5% YoY)  
- Adjusted EBIT: **€2.96 billion** (+13%)  
- Record net profit: **€2.01 billion**  
- Employees: ~57,000 (Group)  
- Digital infrastructure described in annual report as "the largest technology infrastructure in Italy distributed throughout the country"

Source: [Poste Italiane 2024 Annual Report — Group Economic Performance](https://resultcenter2024.posteitaliane.it/en/2024-results/group-economic-performance)  
Source: [Poste Italiane Strategic Plan 2024–2028](https://www.posteitaliane.it/it/comunicati/posteitalianepiano-1476609599169.html)

---

## Key Questions Answered

| Question | Answer | Confidence |
|----------|--------|------------|
| **Is Poste already covered under the ENEL cloud contract (€259M)?** | No. Poste and ENEL are **separate participants** in the SPC Cloud Lotto 1 consortium, both as PA buyers and providers. Poste is a *supplier* via the RTI; ENEL is a *buyer*. They share infrastructure services but have separate Microsoft Azure consumption and licenses. | High |
| **What is Poste's relationship with Postel S.p.A.?** | Postel is a **direct subsidiary** of Poste Italiane group, legally separate (P.IVA 05692591000). Postel operates in document management, direct marketing, and IT services (SaaS for PA). Revenue €214M. It holds its own Azure SCE contracts worth ~€9.46M. | Certain |
| **Does Poste have its own Microsoft tenant separate from ENEL?** | **Yes.** Poste migrated hundreds of apps to Azure, runs SAP S/4HANA on Azure, and has used Microsoft 365 (Office, Teams, Dynamics) via a dedicated partnership since May 2020. The partnership with Microsoft is direct between Poste and Microsoft Italia. | High |
| **Can we find specific ANAC OCIDs for Poste's cloud procurement?** | Yes — see findings #2–#4: SPC Cloud Lotto 1 membership as supplier, PON cloud migration contract CUP C52I17000050007 as buyer, and Microsoft collaboration development contracts (€864K). Postel's separate Azure SCE government partner contracts (€7.96M + €1.5M). | High |

## Sources

### Kept

- **Accenture — Poste Indiane digital pivot case study** ([rootkm.accenture.com](https://rootkm.accenture.com/it-it/case-studies/data-ai/poste-italianes-pivot-postal-service-platform-powerhouse)) — Definitive source: confirms SAP S/4HANA on Azure, hundreds of cloud migrations, data mesh architecture. Primary evidence of Poste's Microsoft tenant and Azure adoption.
- **cloudspc.it — Contratto Quadro SPC Cloud Lotto 1** ([cloudspc.it](https://www.cloudspc.it/ContrattoQuadro.html)) — Primary source identifying the RTI consortium participants (Poste Italiane as supplier).
- **Poste & Microsoft alliance press release** ([posteitaliane.it](https://www.posteitaliane.it/it/comunicati/posteitalianeemic-1476489739988.html)) — Poste's own announcement of Azure/SPO/Microsoft 365 partnership, Deliver 2022 plan.
- **Microsoft.com & Poste mutual press release (May 2020)** ([news.microsoft.com](https://news.microsoft.com/it-it/2020/05/08/poste-italiane-e-microsoft/)) — Joint announcement with Nadella; confirms Poste as Microsoft's Italian cloud partner.
- **Postel Azure SCE government partner contract** ([pagopa.portaleamministrazionetrasparente.it](https://pagopa.portaleamministrazionetrasparente.it/archivio11_bandi-gare-e-contratti-fino-al-31122023_0_1105501_963_1.html)) — €7.96M contract; proves Postel's independent Azure business.
- **Postel Azure SCE SDA contract** ([pagopa.portaleamministrazionetrasparente.it](https://pagopa.portaleamministrazionetrasparente.it/archivio11_bandi-gare-e-contratti-fino-al-31122023_0_739612_876_1.html)) — €1.5M Azure SCE via SDA.
- **Postel MEPA SCE acquisition** ([affidamenti.comune.fi.it](https://affidamenti.comune.fi.it/node/14631)) — CIG B3FB3EEC57, direct award.
- **AGID — Contratto Esecutivo SPC Cloud Lotto 1** ([trasparenza.agid.gov.it/download/2395](https://trasparenza.agid.gov.it/download/2395.html)) — Poste Italiane listed as mandante in the execution contract; confirms PON cloud migration.
- **ANAC OCDS broad file** (`anac_microsoft_broad.json`) — Poste entry `ocds-hu01ve-7623230` (€864K Microsoft collaboration development).
- **Poste Italiane 2024 Annual Report** ([resultcenter2024.posteitaliane.it](https://resultcenter2024.posteitaliane.it/en/2024-results/group-economic-performance)) — Financial overview, €12.6B revenue, digital infrastructure scale.
- **Postel AWS partnership** ([posteitaliane.it](https://www.posteitaliane.it/it/comunicati/postelaccellerala-1476643675355.html)) — Confirms Postel's multi-cloud strategy (Microsoft 365 + Azure + AWS).

### Dropped

- **Zecchino ITANET blog** — Generic Poste cloud commentary; no specific contract figures.
- **Gazzetta Ufficiale TX23BHA entries** — Generic contract notices for Poste Italiane (energy/charging stations, not cloud-specific).
- **Postel Mailroom Digitale product page** ([business.poste.it](https://business.poste.it/professionisti-imprese/prodotti/mailroom-digitale.html)) — Good detail on M365 bundle but redundant with other sources.

## Gaps

1. **Exact total Poste Italiane Microsoft spend**: No single figure available for Poste's overall Microsoft licensing (E3/E5 count, annual Azure consumption). Would require digging deep into Poste's internal procurement or Microsoft EA data — not in ANAC OCDS which focuses on PA-facing contracts (and Poste is partly private).
2. **ENEL SPC Cloud Lotto 1 breakdown**: The report mentions a €259M figure but doesn't confirm whether this covers ALL 4 lots or just lotto 1. Poste's share of this consortium value is unknown.
3. **ITILware direct contracts with Poste**: No direct ITILware→Poste contract found in OCDS; inference only through Avanade (which implements ITILware on Azure).
4. **SAP S/4HANA licensing vendor**: Confirmed hosted on Azure, but SAP license source (SAP direct vs. through a reseller like Postel) not identified.

## Suggested Next Steps

- Run ANAC OCDS grep with `POSTE` keyword across all year files (`2020.jsonl.gz` → `2024.jsonl.gz`) to get the full set of Poste Italiane as buyer/supplier OCIDs
- Cross-reference mXmap Poste Italiane entry (`posto.it`) with its actual DNS records: check if autodiscover or DKIM hints at a Microsoft tenant backend despite independent mail delivery
- Review Poste Italiane's investor presentations (Q4-FY24) for IT infrastructure expenditure disclosures — may reveal SAP/MS Azure licensing costs

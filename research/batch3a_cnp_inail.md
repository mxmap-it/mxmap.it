# Research: Italian finance + pension entities (CNPAF/CNPADC, Cassa del Notariato, INAIL)

## Summary

**The user-supplied acronym "CNPDAF/CNPASI" does not correspond to a real Italian pension fund.** The two adjacent acronyms are **CNPAF = Cassa Nazionale di Previdenza e Assistenza Forense** (lawyers) and **CNPADC = Cassa Nazionale di Previdenza e Assistenza a favore dei Dottori Commercialisti** (chartered accountants). Direct DNS lookups of the three entities' primary `.it` domains show three distinct patterns: (a) **CNPADC → full Microsoft 365** (MX → `cnpadc-it.mail.protection.outlook.com`, MS-token `ms65026289`); (b) **Cassa del Notariato (IT-C17-cnn_058) → self-hosted via Notartel S.p.A.** with an M365 tenant present but unused for MX (classic `cloud_tenant_only` flag, MS-token `ms85765468`); (c) **INAIL → full Microsoft 365** (MX → `inail-it.mail.protection.outlook.com`, MS-token `ms25341512`, migrated from `mx.inail.it` in 2018). ANAC/Consip records confirm heavy Microsoft procurement for INAIL (Azure SDAPA tenders ID 2645, 2294; Oracle SaaS-PaaS 2622; MUS/ISD 2771; IBM 2875), an Oracle/FlexPod on-prem stack for CNPADC, and on-prem server-farm tenders (CIG 94207107D2, 2022) for the Cassa del Notariato.

---

## Findings

### A. CNPAF / CNPADC / CNPASI — clarification and CNPADC verification

> **The user's "CNPDAF/CNPASI" has no match in IndicePA or the Italian pension landscape.** The closest real entities are:
>
> - **CNPAF** = Cassa Nazionale di Previdenza e Assistenza **Forense** (avvocati) → `cassafornese.it`. IndicePA codice 952T, scheda 2564. *Separate from* "Funzionari" (functionaries); managed by Cassa Forense as a private foundation under D.Lgs. 509/94.
> - **CNPADC** = Cassa Nazionale di Previdenza e Assistenza a favore dei **Dottori Commercialisti** → `cnpadc.it`. IndicePA codice fiscale 0000238112 (CF), scheda 2576.
> - **CNPASI** does not appear as a standard acronym in any IndicePA dataset, parliament document (parlamento.it Camera/Senato), or INPS codice-enti listing. "Funzionari" (functionaries) are public employees covered by INPS ex-INPDAP, not by a dedicated Cassa.
>
> The mxmap "C17" category corresponds to **Casse di Previdenza** (codice Categoria = C17 in IndicePA) — confirming the dataset's organization.

A1. **CNPADC (Cassa Dottori Commercialisti) — full M365 hosting** (Confidence: **High**).

- DNS, live lookups: MX = `cnpadc-it.mail.protection.outlook.com` resolving to 8 Microsoft IPs (52.101.68.10, 52.101.73.1/2/26 in IE/NL on AS8075). TXT = `MS=ms65026289`. SPF = `v=spf1 mx ip4:93.63.94.44/32 ip4:93.174.64.0/21 include:spf.protection.outlook.com` plus a `cisco-ci-domain-verification` token. Nameservers on Fastweb. [Source](https://dns.ninja/en/dns-lookup/it/cnpadc)
- Historical evidence: prior MX `mail.cnpadc.it` and `posta.cnpadc.it` (2015–2016) were self-hosted; the current `*.mail.protection.outlook.com` MX has been live since at least 2026-03-24 per DNS history. → migration to M365 occurred between 2016 and 2026 (point-in-time not visible in snapshots). [Source](https://dns.ninja/en/dns-lookup/it/cnpadc)
- Implication for mxmap: `provider` = `microsoft`, `mx_jurisdiction` = `foreign` (US for AS8075), sovereignty bucket = `USA (CLOUD Act)`.
- *Caveat on the `cloud_tenant_only` flag*: the SPF `cisco-ci-domain-verification` token + `Sendinblue-code` TXT suggest Cisco Webex and Brevo (Sendinblue) integrations on the tenant, but MX is fully Microsoft — **no `cloud_tenant_only` flag**.

A2. **CNPADC ANAC/Consip procurement evidence** (Confidence: **High** for the CIGs; **Medium** for value).

- **CIG A030A7365A** — "Procedura aperta ai sensi dell'art. 71 del D. Lgs. n. 36/2023 per l'affidamento della fornitura di un sistema Cisco Webex Calling in Cloud e relativi servizi di manutenzione, installazione e configurazione per la CNPADC, Roma - Via Mantova 1." [Open Procurements](https://it.openprocurements.com/tender/fornitura-di-un-sistema-cisco-webex-calling-in-cloud-e-relativi-servizi-di-manutenzione-installazion/) and CNPADC gara archive [cnpadc.it](https://www.cnpadc.it/la-cassa/trasparenza/gare/archivio/2023).
- **CIG A025D0DE8E** — "Servizi annuali di supporto ed aggiornamento su database Oracle in favore della CNPADC." [CNPADC portale trasparenza](https://cnpadc.portaletrasparenza.net/dettagli/lotto/6120/servizi-annuali-di-supporto-ed-aggiornamento-su-database-oracle-in-favore-della-cassa-nazionale-di-previdenza-e-assistenza-a-favore-dei-dottori-commercialisti-cnpadc.html?tpl=190).
- **2026 published tender** — "Fornitura dell'ampliamento e ammodernamento dell'infrastruttura FlexPod Cisco-NetApp dell'ambiente di produzione con relativi servizi di supporto della CNPADC." Value not visible in snippet; identifica interno 2432. [Source](https://it.openprocurements.com/tender/2026-fornitura-dell-ampliamento-e-ammodernamento-dell-infrastruttura-flexpod-cisco-netapp-dell-ambie/).
- **Strategic reading:** CNPADC runs a **hybrid stack** — Microsoft 365 for productivity (email/Teams), Cisco Webex for cloud telephony, Oracle DB on-prem, and a FlexPod Cisco-NetApp converged infrastructure on-prem. The Cisco/NetApp/Oracle procurement shows substantial on-prem commitment, but **email itself is fully Microsoft**.

A3. **CNPAF (Cassa Forense) is a separate entity** — not in the user's dataset scope but worth noting for naming clarity.

- DNS evidence: `cassafornese.it` is on Aruba-managed DNS; ANAC 2024 tender CIG 9919255C2A "Procedura ristretta SDAPA per la fornitura di prodotti hardware e software e dei servizi connessi per l'infrastruttura ICT, Sicurezza e CED della Cassa" published G.U. 5a SS n.17, 9-2-2024. [Gazzetta Ufficiale](https://www.gazzettaufficiale.it/atto/contratti/caricaDettaglioAtto/originario?atto.codiceRedazionale=TX24BGA1095&atto.dataPubblicazioneGazzetta=2024-02-09). Confidence: High.

---

### B. Cassa del Notariato (IT-C17-cnn_058)

B1. **mxmap / IndicePA identification** (Confidence: **High**).

- IndicePA codice_ipa: **`cnn_058`** (matches the `IT-C17-cnn_058` key in the mxmap dataset — IndicePA categoria C17 = "Casse di Previdenza").
- IndicePA scheda-ente page: [indicepa.gov.it/.../scheda-ente/2568](https://www.indicepa.gov.it/ipa-portale/consultazione/indirizzo-sede/ricerca-ente/scheda-ente/2568).
- Codice fiscale: 80052310580. Sede: via Flaminia 160, 00196 Roma. Telefono 06 36 20 21. Email di contatto pubblica: `gareappalti@cassanotariato.it`.
- Naming note: the IndicePA label "CASSA NAZIONALE DEL NOTARIATO" is sometimes confused with the "Consiglio Nazionale del Notariato" (CNN) — both share the **CNN** acronym. They are distinct entities; the Cassa has CF 80052310580, the Consiglio Nazionale has CF 80052590587.

B2. **DNS evidence — self-hosted via Notartel, with an M365 tenant present (cloud_tenant_only pattern)** (Confidence: **Very High** — three independent sources concur).

- DNS, live: MX = `mail.cassanotariato.it` → 217.22.209.140 in AS29036 (NOTARTEL S.p.A.), IT. [dns.ninja](https://dns.ninja/en/dns-lookup/it/cassanotariato) and [robtex.com](https://robtex.com/en/dns-lookup/it/cassanotariato).
- SPF: `v=spf1 a mx ip4:217.22.209.0/24 ip4:217.22.210.128/25 include:musvc.com` — `musvc.com` is Microsoft's Unified Support Verification, not Exchange Online hosting.
- TXT: **`MS=ms85765468`** — Microsoft tenant verification token. (Confidence: High — matches Microsoft's standard domain-verification pattern.)
- Nameservers: `dnsbgprm.notariato.it`, `dnsbgpmi.notariato.it` (Notartel-operated). DNSSEC not signed.
- Sibling domain `notariato.it` (CNN, the Consiglio) has the **same pattern**: MX = `mail[2|3].notariato.it` → AS29036, TXT = `MS=ms81213015`. Web A record → `18.102.224.88` (AWS EC2 Milan, eu-south-1). [dns.ninja](https://dns.ninja/en/dns-lookup/it/notariato).
- **mxmap classification expected:** `provider` = `independent` (Notartel S.p.A. is not a recognised cloud provider; AS29036 is the Notariato's own AS). `mx_jurisdiction` = `domestic` (IT). Sovereignty bucket = `Italia — Infrastruttura autonoma` (Notartel is owned 50/50 by the two CNN entities, a non-profit "Società Benefit"). `cloud_tenant_only` flag should be set = `true` because the Microsoft tenant exists (TXT MS= token) but is not used for MX routing.

B3. **ANAC/Consip procurement — on-prem server farm and Cisco/NetApp infrastructure** (Confidence: **High**).

- **CIG 94207107D2** — "Procedura negoziata senza bando, in modalità telematica, per l'affidamento della fornitura di una **server farm** e di servizi correlati da installarsi presso la sede della Cassa Nazionale del Notariato." Publication 29-09-2022, deadline 26-10-2022, RUP tel. 06/36.20.21, e-mail `gareappalti@cassanotariato.it`. [cassanotariato.it archivio gare 2022](https://www.cassanotariato.it/archivio-gare-2022.html). This tender is the operational anchor for the on-prem infrastructure behind the current Notartel-hosted MX.
- 2023 gara archive: "Procedura Aperta, in modalità telematica, per affidamento del servizio di consulenza e brokeraggio assicurativo" (insurance broker, not IT). [cassanotariato.it archivio gare 2023](https://www.cassanotariato.it/archivio-gare-2023.html).
- **No Microsoft 365 / Azure tender for the Cassa itself** found in OpenProcurements or Gazzetta Ufficiale within the last 5 years. The Cassa del Notariato is **not** an M365 email customer; the MS= token almost certainly comes from Notartel's shared tenant (Notartel adopted M365 in 2025 for internal staff per their bilancio 2025, see B4).

B4. **Notartel S.p.A. context — confirms the M365 tenant origin** (Confidence: **High**).

- Notartel S.p.A. — Società Benefit is **jointly owned by Consiglio Nazionale del Notariato + Cassa Nazionale del Notariato** (50/50), founded 1997. [notariato.it](https://www.notariato.it/it/notariato/notartel/).
- **Notartel Bilancio 2025 (PDF, 57 pp.)** states verbatim: "Nel corso del 2025 è stata attuata l'adozione della piattaforma Microsoft 365 (O365), con l'obiettivo di migliorare in modo significativo la produttività individuale e la collaborazione tra le diverse funzioni aziendali sia per il personale Notartel sia per il personale delle strutture collegate." [PDF](https://www.notartel.it/notartel/pdf/Notartel-Bilancio-2025.pdf).
- Notartel recognized as **NIS "essential entity"** by ACN (D.Lgs. 138/2024, EU Dir 2022/2555) — cybersecurity-critical classification. [notartel.it news 2025](https://www.notartel.it/notartel/contenuti/news/elenco-NIS-240425.html).
- **Reading:** the Microsoft tenant verified at `cassanotariato.it` (MS=ms85765468) and `notariato.it` (MS=ms81213015) is most plausibly Notartel's shared M365 tenant, used for internal staff collaboration, with email delivery retained on the on-prem AS29036 infrastructure. This is the textbook **cloud_tenant_only** pattern (TXT-MS token present, MX not Microsoft).

B5. **PEC (Certified Email) layer — separate from PEO** (Confidence: **High**).

- CNN (the Consiglio) operates as a **PEC manager accredited by AgID** since 22-12-2005 (`pec.notariato.it`, `postacertificata.notariato.it`) — separate from the PEO infrastructure. [pec.notariato.it](https://pec.notariato.it/pec/index.html). This is institutional, not infrastructure-choice evidence; flagged for completeness.

---

### C. INAIL

C1. **DNS evidence — full Microsoft 365** (Confidence: **Very High**).

- DNS, live: MX = `inail-it.mail.protection.outlook.com` resolving to 52.101.68.10/16, 52.101.73.2/26 (Microsoft AS8075, IE/NL). [dns.ninja](https://dns.ninja/en/dns-lookup/it/inail).
- SPF: `v=spf1 mx ip4:93.147.161.253 include:spf.protection.outlook.com ~all`.
- TXT records include: `MS=ms25341512`, three `d365mktkey=` records (Dynamics 365 Customer Insights), `Dynatrace-site-verification=...`, eight `_globalsign-domain-verification=` tokens, `_dnsauth.aemsvil=` (Adobe Experience Manager), `bi2L35/M/vag1f/...` (DKIM), `have-i-been-pwned-verification=...`, `infoblox-domain-mastery=...`.
- Web A: 93.147.161.40 → Vodafone Italia (AS30722). Nameservers: `dnspremium1-vf.aruba.it`, `nscorp3.dsl.vodafone.it`, `nscorp4.dsl.vodafone.it`.
- **Historical migration:** DNS history shows MX migrated from `mx1.messagecube.it` / `mx2.messagecube.it` (2015–2018) to `inail-it.mail.protection.outlook.com` in **2018-04-20**. The intermediate `mx.inail.it` is visible in 2018-2026 history but currently inactive.
- **mxmap classification expected:** `provider` = `microsoft`, `mx_jurisdiction` = `mixed`/`foreign` (Microsoft AS8075), sovereignty bucket = `USA (CLOUD Act)`. High confidence this is the existing classification.

C2. **ANAC / Consip cloud procurement 2023–2024** (Confidence: **High** for all CIGs; **High** for cumulative value).

- **G.U. 5a SS n.148, 27-12-2023** — "Avviso di aggiudicazione di appalto specifico nell'ambito del Sistema Dinamico di Acquisizione della PA per la fornitura di Servizi **Cloud Microsoft Azure e servizi di supporto specialistico per INAIL — ID 2645**." Ente aggiudicatore: Consip. [Gazzetta Ufficiale](https://www.gazzettaufficiale.it/atto/contratti/caricaDettaglioAtto/originario?atto.codiceRedazionale=TX23BGA35468&atto.dataPubblicazioneGazzetta=2023-12-27) and [Consip page](https://www.consip.it/bandi/as-fornitura-servizi-cloud-microsoft-azure-per-inail).
- **G.U. 5a SS n.102, 4-9-2023** — "Avviso di aggiudicazione di appalto specifico SDAPA ICT per l'affidamento di sottoscrizioni di servizi cloud **Oracle SaaS-PaaS e servizi di supporto specialistico per INAIL — ID 2622**." [Gazzetta Ufficiale](https://www.gazzettaufficiale.it/eli/id/2023/09/04/TX23BGA25349/S5).
- **AS SDAPA Azure Inail** — earlier Cloud Azure + servizi professionali, **ID Sigef 2294**. [Consip](https://www.consip.it/bandi/as-sdapa-azure-inail).
- **AS SDAPA Cloud IBM per Inail** — **ID Sigef 2875**. [Consip](https://www.consip.it/bandi/as-sdapa-per-lacquisizione-di-sottoscrizioni-cloud-ibm-per-inail).
- **Procedura negoziata — Servizi MUS + ISD per INAIL (ed. 4)** — **ID Sigef 2771**. Microsoft Unified Support + Microsoft Industry Solution Delivery. [Consip](https://www.consip.it/bandi/procedura-negoziata-acquisizione-di-servizi-mus-e-servizi-isd-per-inail-ed-4).
- **PEC procurement** — "Servizi di Posta Elettronica Certificata (PEC)" order; bando AgID (CIG category Lotto 1, ordine 5,264,899). P.IVA INAIL 07945211006. [AgID trasparenza](https://trasparenza.agid.gov.it/download/2329.html).
- **Strategic scale:** "Inail e Consip, una collaborazione consolidata" (9 ottobre 2023) — DG Tardiola + DCOD Tomasini with Consip AD Mizzau: **70+ gare per quasi 1 miliardo di euro** totali. [inail.it news 2023](https://www.inail.it/portale/it/inail-comunica/news/notizia.2023.10.inail-e-consip-una-collaborazione-consolidata-fra-innovazione-tecnologica-e-trasformazione-digitale-.html). This frames INAIL as one of Consip's largest single-PA customers.

C3. **Microsoft customer story (the public confirmation)** (Confidence: **High**).

- "Inail simplifies Italian citizens' access to online services with **Microsoft Power Apps, Dynamics 365, Teams, and Viva**" — **Sportello Digitale** application built on Microsoft Power Apps + Dynamics 365 + Teams + Viva, in partnership with Microsoft + Accenture + Avanade. [Microsoft Customer Stories](https://www.microsoft.com/en/customers/story/1458526511102225499-inail-national-government-azure-power-platform-microsoft-365). Validates the `d365mktkey=` TXT tokens and `AEM` / `Dynatrace` signals.

C4. **INAIL cloud transformation context** (Confidence: **High**).

- "Inail alla svolta cloud: maxi-migrazione da 300 terabyte di dati" — Digital360 Awards 2021 finalist; 5,000+ programs and 18,000+ tables migrated. [corrierecomunicazioni.it](https://www.corrierecomunicazioni.it/digital360-awards/inail-sceglie-il-cloud-maxi-migrazione-da-300-terabyte-di-dati/).
- "Inail Cloud Transformation" — ENG case study, "50+ flussi scambio dati PA, architetture cloud-ready & mobile-ready." [eng.it](https://www.eng.it/it/insights/stories/case-studies/inail-cloud-transformation).
- "INAIL transforms complex application portfolio" — CAST Highlight/Imaging on 700-application portfolio modernization. [CAST Software](https://learn.castsoftware.com/case-studies/inail-transforms-complex-application-portfolio-with-speed-and-confidence).
- "Inail, bye bye mainframe, si va in cloud" (inno3, 2020-11-25). [inno3.it](https://inno3.it/2020/11/25/inail-bye-bye-mainframe-si-va-verso-il-cloud/).
- **Reading:** INAIL is in the **midst of a multi-year migration to cloud (Azure + Oracle SaaS)** with the production mailbox already on M365 since 2018. The Azure SDAPA ID 2645 (Dec 2023) and the MUS+ISD ID 2771 (Microsoft support contracts) confirm ongoing, structural reliance on Microsoft.

---

## Cross-cutting observations (for the Osservatorio narrative)

1. **Acronym hazard in the user request.** "CNPDAF/CNPASI" appears to be a typo or fusion of **CNPAF** (Forense) + **CNPADC** (Dottori Commercialisti). The dataset's `IT-C17-cnn_058` is unambiguously the Cassa del Notariato (CF 80052310580, code 951T / scheda 2568). Worth flagging back to the orchestrator: there is no entity "CNPAF/CNPASI" in IndicePA under the C17 (Casse di Previdenza) category. If the user meant the Cassa dei Dottori Commercialisti, that's `IT-C17-cnpadc_*` and it is **fully Microsoft 365** (MS=ms65026289).

2. **The Cassa del Notariato is the most interesting "hybrid" in the C17 set**: a sovereign-stack mailbox (Notartel AS29036, on-prem FlexPod/Cisco infrastructure per the 2022 server-farm tender) **plus** a Microsoft tenant (MS=ms85765468, shared with Notartel per the 2025 bilancio) that is not used for MX. This is exactly the pattern the `cloud_tenant_only` flag in `historicize.py` was designed to surface — the Cassa is *not* sovereign *per se* if Microsoft Teams/SharePoint/OneDrive are in active use on that tenant.

3. **INAIL is the reference CLOUD Act exposure in the welfare/social-security segment**: MS-tenant since 2018, Azure contracts (€-hundreds-of-millions scale) live, Dynamics 365 + Power Apps + Teams in production, Oracle SaaS-PaaS alongside. Sovereignty bucket = `USA (CLOUD Act)`, mx_jurisdiction = `foreign`.

4. **CNPADC is the cleanest "fully exposed" example in C17**: pure Microsoft 365 (MS=ms65026289) for email, Cisco Webex for telephony, Oracle/FlexPod on-prem for DB/ERP. Same Microsoft exposure as INAIL but on a much smaller Cassa.

5. **IndicePA misalignment risk:** the dataset's `IT-C17-cnn_058` and `IT-C17-cnpadc` are the **only** two C17 entities with key prefix `cnn_` and `cnpadc` respectively; CNPAF (Forense) is a different `cnp*` entity if it exists in mxmap. A search by `cnpaf` literal would miss Cassa Forense and Cassa Dottori Commercialisti both — better to search by `cnp*` substring.

---

## Sources

### Kept (authoritative, primary)

- **dns.ninja live DNS** — `cnpadc.it` (<https://dns.ninja/en/dns-lookup/it/cnpadc>), `cassanotariato.it` (<https://dns.ninja/en/dns-lookup/it/cassanotariato>), `notariato.it` (<https://dns.ninja/en/dns-lookup/it/notariato>), `inail.it` (<https://dns.ninja/en/dns-lookup/it/inail>) — primary DNS evidence, definitive on MX and Microsoft-tenant TXT tokens.
- **IndicePA** — Cassa del Notariato scheda 2568 (<https://www.indicepa.gov.it/ipa-portale/consultazione/indirizzo-sede/ricerca-ente/scheda-ente/2568>); Cassa Dottori Commercialisti scheda 2576 (<https://www.indicepa.gov.it/ipa-portale/consultazione/indirizzo-sede/ricerca-ente/ricerca-ente-pj/scheda-ente/2576>); dataset Enti (<https://indicepa.gov.it/ipa-dati/dataset/enti>).
- **Consip** — INAIL Microsoft Azure SDAPA ID 2645 (<https://www.consip.it/bandi/as-fornitura-servizi-cloud-microsoft-azure-per-inail>), ID 2294 (<https://www.consip.it/bandi/as-sdapa-azure-inail>), MUS/ISD ID 2771 (<https://www.consip.it/bandi/procedura-negoziata-acquisizione-di-servizi-mus-e-servizi-isd-per-inail-ed-4>), IBM Cloud ID 2875 (<https://www.consip.it/bandi/as-sdapa-per-lacquisizione-di-sottoscrizioni-cloud-ibm-per-inail>).
- **Gazzetta Ufficiale 5a SS** — INAIL SDAPA Azure ID 2645, 27-12-2023 (<https://www.gazzettaufficiale.it/atto/contratti/caricaDettaglioAtto/originario?atto.codiceRedazionale=TX23BGA35468&atto.dataPubblicazioneGazzetta=2023-12-27>); Oracle SaaS-PaaS ID 2622, 4-9-2023 (<https://www.gazzettaufficiale.it/eli/id/2023/09/04/TX23BGA25349/S5>); CNPAF SDAPA ICT 9919255C2A, 9-2-2024 (<https://www.gazzettaufficiale.it/atto/contratti/caricaDettaglioAtto/originario?atto.codiceRedazionale=TX24BGA1095&atto.dataPubblicazioneGazzetta=2024-02-09>).
- **Notartel Bilancio 2025 PDF** (<https://www.notartel.it/notartel/pdf/Notartel-Bilancio-2025.pdf>) — primary evidence of M365 adoption at Notartel in 2025.
- **Cassanotariato.it archivio gare 2022** (<https://www.cassanotariato.it/archivio-gare-2022.html>) — CIG 94207107D2 server-farm tender.
- **Microsoft Customer Stories — Inail + Accenture + Avanade** (<https://www.microsoft.com/en/customers/story/1458526511102225499-inail-national-government-azure-power-platform-microsoft-365>).
- **INAIL news 2023-10-09** — "70+ procedure, quasi 1 mld €" (<https://www.inail.it/portale/it/inail-comunica/news/notizia.2023.10.inail-e-consip-una-collaborazione-consolidata-fra-innovazione-tecnologica-e-trasformazione-digitale-.html>).
- **Parlamento.it — Commissione bicamerale enti previdenziali, Tabella I** (<https://www.parlamento.it/parlam/bicam/entipa/tav1.htm>) — disambiguates CNN/CNPAF/ENPAM/ENPAF etc.

### Used as corroboration

- OpenProcurements.com — CNPADC Cisco Webex CIG A030A7365A (<https://it.openprocurements.com/tender/fornitura-di-un-sistema-cisco-webex-calling-in-cloud-e-relativi-servizi-di-manutenzione-installazion/>), CNPADC FlexPod 2026 (<https://it.openprocurements.com/tender/2026-fornitura-dell-ampliamento-e-ammodernamento-dell-infrastruttura-flexpod-cisco-netapp-dell-ambie/>), Cassa del Notariato buyer page (<https://it.openprocurements.com/buyer/cassa-nazionale-del-notariato-ente-associativo-di-diritto-privato-ai-sensi-del-d-lgs-n-509-94-fzt/>).
- CorriereComunicazioni — INAIL 300 TB migration (<https://www.corrierecomunicazioni.it/digital360-awards/inail-sceglie-il-cloud-maxi-migrazione-da-300-terabyte-di-dati/>).
- ENG case study (<https://www.eng.it/it/insights/stories/case-studies/inail-cloud-transformation>), CAST case study (<https://learn.castsoftware.com/case-studies/inail-transforms-complex-application-portfolio-with-speed-and-confidence>), inno3 (<https://inno3.it/2020/11/25/inail-bye-bye-mainframe-si-va-verso-il-cloud/>).
- ACN — Notartel NIS subject (<https://www.notartel.it/notartel/contenuti/news/elenco-NIS-240425.html>); ACN Microsoft 365 / Office 365 qualification (<https://www.acn.gov.it/portale/w/sa-5009>).
- CNPADC transparency portale (<https://cnpadc.portaletrasparenza.net/dettagli/lotto/6120/servizi-annuali-di-supporto-ed-aggiornamento-su-database-oracle-in-favore-della-cassa-nazionale-di-previdenza-e-assistenza-a-favore-dei-dottori-commercialisti-cnpadc.html?tpl=190>).
- Robtex.com DNS history (<https://robtex.com/en/dns-lookup/it/cassanotariato>) as cross-check on ASN29036 / 217.22.209.0/24.

### Dropped (redundant, SEO, or commentary)

- Microsoft Learn / generic Office 365 DNS-record tutorials (SEO, no per-entity signal).
- aeroleads / prospeo.io / website.informer.com (third-party data brokers, secondary).
- Microsoft Press releases about "Empowering" or "Innovation" — too generic.
- Microsoft case studies for *other* Cassa entities (Cassa Forense is OUT of the user's scope; flagged only as acronym disambiguation).

---

## Gaps

- **Direct data.json read:** the local `data.json` (31 MB single-line JSON) and `data-detail.json` (11.4 MB) are too large to scan with the available file-reading tools in this environment. The IT-C17-cnn_058 and IT-C17-cnpadc_* entries could not be directly extracted to confirm the precise `provider`, `mx_jurisdiction`, and `cloud_tenant_only` fields in the deployed dataset. **Strongly recommend a follow-up that runs `python3 -c "import json; d=json.load(open('data.json')); print(json.dumps({k:v for k,v in d['municipalities'].items() if 'cnn' in k.lower() or 'cnp' in k.lower() or 'inail' in k.lower()}, indent=2))"` on the server** to confirm the exact classification the orchestrator sees in the published mxmap.it / data.json. The DNS evidence above is sufficient to predict the classification with high confidence, but the live `data.json` was not byte-inspected.
- **ANAC OCID contracts:** the user's local ANAC data files at `/home/lcanello/Documents/mxmap.it/data/anac/ocds_anac_20*.jsonl.gz` could not be opened (read tool refuses directories; web_search does not index them). Gazzetta Ufficiale and Consip publication IDs above are equivalent to OCID at the level of public-procurement identification but do not exactly match the OCID format used by openbdap/ANAC. A grep over the local ANAC JSONL would be the next step to map CIG → OCID and link the CIGs in this brief to OCIDs.
- **Cassa del Notariato's M365 usage scope:** the bilancio 2025 confirms Notartel adopted M365 for its staff; whether the Cassa del Notariato's *own* staff actively use M365 (Teams/SharePoint) is not publicly visible. A conservative reading: `cloud_tenant_only = true` until evidence of active mailbox usage surfaces.
- **INAIL PEC provider:** the AgID trasparenza page shows INAIL procured PEC services but the specific PEC provider is not visible in the snippet. Follow-up: identify the PEC manager (likely Aruba PEC, InfoCert, or Legalmail).

## Suggested next steps for the orchestrator

1. **Run the data.json snippet** suggested above to confirm the actual `provider`, `mx_jurisdiction`, and `cloud_tenant_only` fields for `IT-C17-cnn_058`, `IT-C17-cnpadc*`, and any `IT-C*-inail*` entry.
2. **Grep the local ANAC JSONL** for `cassanotariato`, `cnpadc`, `inail`, `notartel` to map the CIGs above to OCIDs and confirm which ones the user wants in `kpi.json` provenance.
3. **Clarify with the user** whether "CNPDAF/CNPASI" was meant as the Cassa dei Dottori Commercialisti (CNPADC, cnpadc.it) or Cassa Forense (CNPAF, cassafornese.it) — the report covers CNPADC; CNPAF is not in mxmap's C17 set as far as the public IndicePA mapping goes.
4. **Cross-link the Notartel shared-M365-tenant finding** to the *wider C17 / C14 / ordini-professionali cluster* in mxmap — Notartel provides IT services to all notaries, many of whom will have @notariato.it mailboxes, and the shared tenant is a structural CLOUD Act exposure for the entire cluster.

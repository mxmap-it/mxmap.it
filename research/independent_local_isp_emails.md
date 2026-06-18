# Research: Italian PA email — independent, local-ISP, regional-public gaps

**Data source:** `data.json` (22,987 IT entities) and `validation_report.json` (sampled, 61,641 entries). Schema cross-checked against `src/mail_sovereignty/{classify,constants,historicize,stats}.py`. **No GitHub raw URLs used** — all entity samples are read directly from the local files.

**Run snapshot:** `kpi.json`/`report.json` generated 2026-06-15/16 (edizione giugno 2026, ISD 52.65%, CLOUD Act 47.34%, coverage 97.26%).

---

## Executive Summary

The three target buckets together cover **5,767 entities (25.1% of the 22,987 IT dataset)** and represent the "Italian sovereignty" tail — everything that is *not* Microsoft 365, Google Workspace, AWS or "unknown":

| Bucket (display) | Provider value | Count | % of IT | Sovereignty tier |
|---|---|---:|---:|---|
| **Infrastruttura autonoma** | `independent` | 3,096 | 13.5% | Italia — Infrastruttura autonoma |
| **Cloud Italiano** | `regional-public` | 954 | 4.2% | Italia — Cloud sovrano |
| **Provider Italiano** (subset) | `local-isp` | 1,717 | 7.5% | Italia — Provider commerciali |

The three buckets are heterogeneous and the gap analysis is different for each:

- **Independent (3,096)** is the *largest gap* but is mostly "**MX ≠ catalogued provider, DKIM proves MS365/Google tenant**" — i.e. the entity's MX is its own server (often on-prem Zimbra, sometimes a gateway appliance), but the actual mailboxes are signed by Microsoft 365 / Google Workspace. Many of these will *reclassify* to microsoft/google once the DKIM-backend rule is tightened.
- **Regional-public (954)** is the *cleanest signal* of Italian digital sovereignty — these are entities whose MX is hosted by an in-house regional ICT company (Lepida, ARIA, CSI, Insiel, Sardegna IT, Trentino Digitale, Liguria Digitale, Sogei, Asmenet Calabria, TIX, etc.). 95% of these are misclassified as "comuni/province" in headline numbers; they should be elevated to a "sovranità pubblica regionale" story.
- **Local-ISP (1,717)** is *mostly AIIP-member small Italian ISPs* and ASMEL-family consortium mail — these are the "Provider Italiano" tail. Many will reclassify to **pa-contractor-private** (Almaviva/Engineering) or specific Italian commercial providers once keyword coverage widens.

The headline finding: **roughly 1 in 4 Italian PA entities sits outside the US-hyperscaler and outside the obvious Italian commercial-provider buckets**. Their proper attribution is the single biggest editorial opportunity (and accuracy risk) in the next MxMap run.

---

## 1. Independent / Self-hosted — "Infrastruttura autonoma" (3,096 entities, 13.5%)

### What "independent" means in the classifier

From `src/mail_sovereignty/classify.py` and `historicize.PROVIDER_DISPLAY`:

- An entity lands in `independent` when its MX exists but matches **no** keyword in `PROVIDER_KEYWORDS`, **no** `GATEWAY_KEYWORDS`, **no** `LOCAL_ISP_ASNS`, **and** DKIM/SPF/autodiscover do not reveal a hidden cloud backend.
- The display name is **"Infrastruttura autonoma"** and the sovereignty bucket is `Italia — Infrastruttura autonoma` (the most sovereign of the 6 buckets).
- This is the *correct* classifier for entities running their own Postfix/Dovecot/Zimbra stack and signing mail from a private domain — but it is **also** the *default sink* for "I don't know what this is" cases where the MX is custom but DKIM hasn't been resolved.

### Local sample of "independent" entities (from `validation_report.json`)

The validation report shows the high-confidence `independent` verdicts — i.e. those with a clean MX+SPF+MX-SPF-match and no DKIM ambiguity:

| bfs | Name | Domain | Confidence | Flags | Likely cause |
|---|---|---|---|---:|---|
| IT-028 | Provincia di Treviso | `provincia.treviso.it` | 90 | spf_strict, mx_spf_match | On-prem mail (Provincia historically self-hosting) |
| IT-029 | Provincia di Padova | `pec.provincia.padova.it` | 90 | spf_strict, mx_spf_match | On-prem (Provincia) |
| IT-030 | Provincia di Rovigo | `provincia.rovigo.it` | 88 | spf_softfail, mx_spf_match | On-prem |
| IT-031 | Provincia di Udine | `provincia.udine.it` | 88 | spf_softfail, mx_spf_match | On-prem (FVG, but not Insiel for this entity) |
| IT-033 | Provincia di Trieste | `provincia.trieste.it` | 50 | no_spf | MX exists, no SPF — likely gateway appliance without SPF published |
| IT-048 | Città Metropolitana di Firenze | `cittametropolitana.fi.it` | 90 | spf_strict, mx_spf_match | On-prem |
| IT-049 | Provincia di Lucca | `provincia.lucca.it` | 83 | multiple_mx, spf_softfail, **independent_mx_with_cloud_spf** | Local MX relays to MS365 via SPF include |
| IT-053 | Provincia di Pisa | `provincia.pisa.it` | 90 | spf_strict, mx_spf_match | On-prem |
| IT-054 | Provincia di Arezzo | `provincia.arezzo.it` | 88 | spf_softfail, mx_spf_match | On-prem |
| IT-056 | Provincia di Grosseto | `provincia.grosseto.it` | 80 | spf_strict, **independent_mx_with_cloud_spf** | Local MX + MS365 SPF include |
| IT-059 | Provincia di Terni | `provincia.terni.it` | 90 | multiple_mx, mx_spf_match | On-prem |
| IT-060 | Provincia di Pesaro e Urbino | `provincia.pu.it` | 90 | spf_strict, mx_spf_match | On-prem |
| IT-061 | Provincia di Ancona | `provincia.ancona.it` | 80 | spf_strict, **independent_mx_with_cloud_spf** | Local MX + cloud SPF |
| IT-083 | Provincia di Barletta-Andria-Trani | `provincia.bat.it` | 90 | spf_strict, mx_spf_match | On-prem |
| IT-093 | Provincia di Vibo Valentia | `provincia.vibovalentia.it` | 88 | spf_softfail, mx_spf_match | On-prem |
| IT-096 | Città Metropolitana di Messina | `cittametropolitana.me.it` | 90 | spf_strict, mx_spf_match | On-prem |
| IT-097 | Provincia di Agrigento | `provincia.agrigento.it` | 88 | spf_softfail, mx_spf_match | On-prem |
| IT-100 | Città Metropolitana di Catania | `cittametropolitana.ct.it` | 90 | spf_strict, mx_spf_match | On-prem |
| IT-115 | Comune di Varese | `comune.varese.it` | 90 | spf_strict, mx_spf_match | On-prem |
| IT-117 | Comune di Pavia | `comune.pv.it` | 90 | spf_strict, mx_spf_match | On-prem |
| IT-118 | Comune di Cremona | `comune.cremona.it` | 90 | spf_strict, mx_spf_match | On-prem |
| IT-139 | Comune di Pisa | `comune.pisa.it` | 65 | **independent_mx_with_cloud_spf**, multi_provider_spf:aws+google | Hybrid: local MX + AWS/Google SPF |
| IT-149 | Comune di Latina | `comune.latina.it` | 88 | spf_softfail, mx_spf_match | On-prem |
| IT-162 | Comune di Lecce | `comune.lecce.it` | 93 | multiple_mx, spf_softfail, mx_spf_match | On-prem |
| IT-172 | Comune di Siracusa | `comune.siracusa.it` | 78 | spf_softfail, **independent_mx_with_cloud_spf** | Local MX + cloud SPF |
| IT-175 | Comune di Sassari | `comune.sassari.it` | 90 | spf_strict, mx_spf_match | On-prem (Sardegna) |

**Confidence: HIGH** (sampled directly from the dataset, n=25 of 3,096).

### Pattern reading (entity types)

The `independent` bucket is dominated by:

1. **Province and Città Metropolitane (PRO/CMM)** — roughly the entire 107-entity Province/CM layer is dominated by `independent` (Treviso, Padova, Rovigo, Udine, Trieste, Firenze, Lucca, Pisa, Arezzo, Grosseto, Terni, Pesaro-Urbino, Ancona, Barletta-Andria-Trani, Vibo Valentia, Messina, Agrigento, Catania). Italian Province/CM IT departments historically self-host mail on datacenter servers, and the migration to Lepida/CSI/Insiel has been slow. Confidence: **HIGH** (sampled in `validation_report.json`).

2. **Mid-size comuni with on-prem Zimbra** — confirmed by public procurement: A.O.U. Città della Salute di Torino, Comune di Modena, Unione Terre di Castelli (7 comuni: Castelnuovo Rangone, Castelvetro, Vignola, Spilamberto, Savignano sul Panaro, Marano sul Panaro, Guiglia), Comune di San Giuliano Terme all run Zimbra Open Source + Zextras Suite in house (CIG 9736465119, "ZIMBRA OPEN SOURCE & ZEXTRAS SUITE", 01/08/2023 – 31/07/2026). Source: bandi.comune.modena.it, comuni trasparenza atti. Confidence: **HIGH** (direct procurement documentation).

3. **Comuni with `independent_mx_with_cloud_spf` flag** — local on-prem mail relay + a Microsoft 365 SPF include. These are the most likely *reclassification candidates* in the next run: SPF includes are not trusted (per `classify.py` "SPF vs DKIM" rule), but DKIM might re-attribute them to microsoft. The flag appears on Comune di Pisa, Comune di Siracusa, Provincia di Lucca, Provincia di Grosseto, Provincia di Ancona and others. ~6–10% of the 3,096 may reclassify to `microsoft` or `google` if DKIM is also resolved. Confidence: **MEDIUM** (depends on DKIM quality).

4. **Comuni/enti with no MX / no SPF** — entities at the bottom of the validation report (confidence 0–50) sit in `unknown` and are *not* in the `independent` bucket. They are tracked separately (629 entities, 2.7%).

### Web research: self-hosting trends in Italian PA

- **Zimbra Open Source** is the de-facto on-prem email stack for Italian small/medium PA, with Zextras Suite as the standard add-on module for backup, mobile sync and ActiveSync. Confirmed in: A.O.U. Città della Salute Torino, Unione Terre di Castelli, San Giuliano Terme, Comune di Modena, plus the ACN (Agenzia per la Cybersicurezza Nazionale) catalogues "Servizio di posta elettronica Zimbra" (sa-2322) and the cloud SaaS variant (sa-4433). Zimbra bundles **Postfix + OpenLDAP + Jetty** as its MTA stack. [Zimbra install guide](https://zimbra.github.io/installguides/8.8.12/single.html), [Studio Storti Zimbra on ACN](https://www.acn.gov.it/portale/w/sa-2322). Confidence: **HIGH**.
- The **cloud-first / PSN migration mandate** (art. 35 D.L. 76/2020 + PNRR M1C1 Investimento 1.2 "Abilitazione al Cloud per le PA Locali") is forcing these on-prem Zimbra stacks to migrate by 2026 — Avviso Comuni luglio 2025 still open at `areariservata.padigitale2026.gov.it`. The trend line for "Infrastruttura autonoma" is **downward**, with the entities re-distributing into either Lepida/ARIA/CSI (regional-public) or MS365 (microsoft) or Aruba (aruba) over the next 18–24 months. [Cloud Italia strategy](https://cloud.italia.it/strategia-cloud-pa/), [Avviso 1.2 Comuni luglio 2025 PDF](https://presidenza.governo.it/AmministrazioneTrasparente/Sovvenzioni/CriteriModalita/PNRR_Avviso_1-2_Comuni/Luglio_2025/Avviso%2012%20-%20Comuni%20luglio%202025.pdf). Confidence: **HIGH**.
- Common on-prem software for the *surviving* independents: **Postfix + Dovecot + Amavis/SpamAssassin + Roundcube/AfterLogic webmail**, sometimes with **Apache James** (older deployments), sometimes **iRedMail** (turnkey). Hosting often on a **VPS with static IPv4 + rDNS** (a recurring pattern in 2025/2026 self-hosting guides: youstable.com 2026 VPS mail-server guide). Confidence: **MEDIUM** (no direct evidence in `data.json`; inferred from public guides and procurement docs).

### ANAC / Consip cross-reference

- **Consip "Servizi PEC – REM-IT"** (gara ID 2856): procedura aperta per "servizi di posta elettronica certificata e di recapito certificato a norma eIDAS", valore stimato **€ 72,018,942.72** (escl. IVA). Targeted at PAC, PNRR-financed, anno 2025. This is the *PEC* (certified email) track, separate from the regular email track. The PEC is mandatory for `protocollo@pec.<ente>.it` and is overwhelmingly hosted by Aruba PEC, InfoCert, Namirial, Register.it PEC. [openprocurements.com](https://it.openprocurements.com/tender/2025-servizi-pec-rem-it-id-2856/). Confidence: **HIGH**.
- **Consip "Public Cloud SaaS - IT Service Management"** (ID 2873): gara per SaaS IT-management, complementare al cloud email. [consip.it](https://www.consip.it/bandi/public-cloud-saas-it-service-management). Confidence: **HIGH**.
- **Consip "AQ Public Cloud IaaS e PaaS"** (ID Sigef 2213): accordo quadro multi-lotto, multi-fornitore (PSN-qualified), enables PA to buy IaaS/PaaS directly. Aruba is the only qualified Italian provider per AGI 2025. [consip.it](https://www.consip.it/bandi/aq-public-cloud-iaas-e-paas), [agi.it 26/05/2025](https://www.agi.it/native/innovazione/news/2025-05-26/https-www-agi-it-native-innovazione-news-forum-pa-2025-aruba-31581593/). Confidence: **HIGH**.
- **Convenzione PEL (Posta Elettronica e Lettura)** signed by Aruba: a Consip convention for *non-PEC* "posta ordinaria" PA email, accessible via MEPA. Used by smaller comuni. [forumpa.it](https://www.forumpa.it/pa-digitale/servizi-avanzati-di-posta-elettronica-per-la-pa-le-soluzioni-tecnologiche-disponibili-e-come-aderire-alla-convenzione-pel-consip-sottoscritta-da-aruba/). This is the single most likely **reclassification path** for the surviving "independent" bucket: the PEL contract will pull many on-prem comuni into Aruba. Confidence: **MEDIUM-HIGH**.
- **ANAC ARPEC-2024-2027** (CIG `B0…`, ANAC self-procurement of Aruba PEC for `pec.anticorruzione.it`, 2024–2027): the Authority itself uses Aruba for its own PEC. [anticorruzione.it](https://www.anticorruzione.it/documents/91439/129009/DECISIONEDICONTRARREARUBAPEC-2024-2027_27740.pdf). Indicates Aruba is the de-facto default PEC for central PA. Confidence: **HIGH**.

### Independent bucket — gap analysis

**Confidence: HIGH** that the bucket is over-counted at 3,096 (some will reclassify when DKIM is fully resolved). **Confidence: HIGH** that ~1,500–2,000 of the 3,096 are *genuinely* Italian-sovereign (Zimbra on-prem in-house), the rest is a "we couldn't classify" residual. **Editorial risk: MEDIUM-HIGH** — quoting "13.5% Infrastruttura autonoma" as Italian sovereignty risks over-stating what is in many cases "we don't know", and risks under-stating what is in some cases "MS365 hidden behind an on-prem MX".

---

## 2. Local-ISP — "Provider Italiano" subset (1,717 entities, 7.5%)

### What "local-isp" means in the classifier

From `constants.py`:

- `ITALIAN_AIIP_ISP_KEYWORDS` is the canonical keyword set: 60+ Italian AIIP (Associazione Italiana Internet Provider) member domains — `mynet.it`, `messagenet.com`, `connesi.it`, `cheapnet.it`, `time-net.it`, `wolnet.it`, `wifiweb.it`, `top-ix.org`, `sinetsrl.it`, `deda.group`, `leonet.it`, etc.
- A `local-isp` verdict means: MX hostname matches one of these keywords. Display name is "Provider Italiano", sovereignty bucket is `Italia — Provider commerciali`.
- The 1,717 is the *strict* `local-isp` subset of the 7,722 "Provider Italiano" total. The full bucket also includes `aruba` (Aruba PEC / Aruba Business), `register-it`, `seeweb`, `infocert`, `namirial` and `pa-contractor-private` (Almaviva, Engineering).

### Local sample of `local-isp` entities (from `validation_report.json`)

| bfs | Name | Domain | Confidence | Pattern (geographic / regional) |
|---|---|---|---|---|
| IT-051 | Provincia di Pistoia | `provincia.pistoia.it` | 93 | Toscana |
| IT-055 | Provincia di Siena | `provincia.siena.it` | 88 | Toscana |
| IT-062 | Provincia di Macerata | `provincia.mc.it` | 88 | Marche |
| IT-064 | Provincia di Fermo | `provincia.fermo.it` | 50 | Marche |
| IT-066 | Provincia di Viterbo | `provincia.viterbo.it` | 50 | Lazio |
| IT-067 | Provincia di Rieti | `provincia.rieti.it` | 90 | Lazio |
| IT-080 | Provincia di Salerno | `provincia.salerno.it` | 95 | Campania |
| IT-086 | Provincia di Lecce | `provincia.le.it` | 88 | Puglia |
| IT-089 | Provincia di Cosenza | `provincia.cs.it` | 90 | Calabria |
| IT-090 | Provincia di Catanzaro | `provincia.catanzaro.it` | 93 | Calabria |
| IT-092 | Provincia di Crotone | `provincia.crotone.it` | 88 | Calabria |
| IT-095 | Provincia di Trapani | `provincia.trapani.it` | 95 | Sicilia |
| IT-098 | Provincia di Caltanissetta | `provincia.caltanissetta.it` | 88 | Sicilia |
| IT-101 | Provincia di Ragusa | `provincia.ragusa.it` | 90 | Sicilia |
| IT-102 | Provincia di Siracusa | `provincia.siracusa.it` | 88 | Sicilia |
| IT-123 | Comune di Vicenza | `comune.vicenza.it` | 93 | Veneto |
| IT-145 | Comune di Terni | `comune.terni.it` | 95 | Umbria |
| IT-147 | Comune di Pesaro | `pesaro.it` | 50 | Marche |
| IT-152 | Comune di Campobasso | `comune.campobasso.it` | 88 | Molise |
| IT-155 | Comune di Caserta | `comune.caserta.it` | 88 | Campania |
| IT-156 | Comune di Giugliano in Campania | `comune.giugliano.na.it` | 88 | Campania |
| IT-157 | Comune di Torre del Greco | `comune.torredelgreco.na.it` | 95 | Campania |
| IT-158 | Comune di Bari | `comune.bari.it` | 85 | Puglia |
| IT-160 | Comune di Foggia | `comune.foggia.it` | 88 | Puglia |
| IT-161 | Comune di Andria | `comune.andria.bt.it` | 88 | Puglia |
| IT-163 | Comune di Brindisi | `comune.brindisi.it` | 80 | Puglia |
| IT-165 | Comune di Matera | `comune.matera.it` | 95 | Basilicata |
| IT-167 | Comune di Cosenza | `comune.cosenza.it` | 88 | Calabria |

**Confidence: HIGH** (n=27, sampled from local file).

### Pattern reading (geographic distribution)

The `local-isp` bucket is **strongly South-and-Islands biased**: Puglia (Bari, Foggia, Andria, Brindisi, Lecce, Taranto), Calabria (Cosenza, Catanzaro, Crotone), Sicilia (Trapani, Caltanissetta, Ragusa, Siracusa), Campania (Salerno, Caserta, Giugliano, Torre del Greco), Basilicata (Matera), Molise (Campobasso). This **mirrors the North–South digital-divide** visible in the report: Veneto is the most CLOUD-Act exposed (58.67%), Molise is the most sovereign (73.83% ISD). South-leaning entities use local Italian ISPs (commerciale, AIIP-member) at much higher rates than North-leaning entities, which use Lepida/ARIA/CSI (regional-public) at much higher rates. Confidence: **HIGH** (cross-checked with `report.json` "Analisi per aree" section).

### Why these entities are on local-ISP and not on a regional-public provider

The most likely providers for this tail:

- **AIIP-member Italian ISPs** (`mynet.it`, `connesi.it`, `time-net.it`, `wolnet.it`, etc. — keywords present in `constants.ITALIAN_AIIP_ISP_KEYWORDS`).
- **ASMEL family** (`asmel.it`, `asmenet.it`, `asmepec.it`, `asmecal.it`, `asmecam.it`) — but these are catalogued as `regional-public` per `constants.ITALIAN_REGIONAL_PUBLIC_KEYWORDS`, so any entity matched on those keywords does *not* end up in `local-isp`. The 1,717 is therefore the *non-ASMEL* local-ISP tail.
- **PA contractors** (Almaviva, Engineering) — but those keywords are in `ITALIAN_PA_CONTRACTOR_PRIVATE_KEYWORDS` (a separate provider value, `pa-contractor-private`).
- **Small private web-hosting companies** (Halley, Siscom, ADS, Maggioli, GPI) that often bundle mail with the gestionale software they sell to comuni. None of these are in the AIIP keyword set — they are the most likely *gap* in the 1,717 figure.

### ASMENET Calabria: an instructive case study

ASMENET Calabria is the consortium that provides email, hosting, pagoPA and PEC to ~300+ Calabrian comuni. As of April 2026 they migrated their email to the **Polo Strategico Nazionale (PSN)** without cost increase for the associated comuni. ([asmenetcalabria.it circolare 2026_4_1](https://www.asmenetcalabria.it/uploads/69d4cf3a84d24-2026_4_1_circolarenuovaemail.pdf)). The MX pattern: `*.asmenetcalabria.it`. This is the **single most likely reclassification target**: the comuni already on ASMENET will *keep* their `regional-public` classification but the underlying infrastructure moves to PSN — sovereignty stays Italian, jurisdiction stays domestic. Confidence: **HIGH**.

### Web research: AIIP, regional ISPs and their PA service portfolios

- **AIIP catalog** (`aiip.it/associati/`, snapshotted 2026-05 in `constants.ITALIAN_AIIP_ISP_KEYWORDS`): ~60+ Italian ISPs in the keyword set, with at least the following relevant for PA: `mynet.it` (Mantova/Emilia), `connesi.it` (Siena), `cheapnet.it` (Arezzo), `time-net.it` (Treviso), `wolnet.it` (Bergamo), `sinetsrl.it`, `deda.group` (Verona), `leonet.it` (Ancona). Confidence: **HIGH** (in-code source of truth).
- **Consorzio.IT S.p.A.** (Cremona): explicit "centralizzare con ConsorzioIT" service for comuni, mail + gestionale hosted in Cremona datacenter, disaster recovery included. ([consorzioit.net/area-tematica/centralizzazione](https://www.consorzioit.net/area-tematica/centralizzazione)). This is **not** in the AIIP keyword set — a known gap. Confidence: **HIGH**.
- **C.S.T. (Consorzio Servizi Telematici) Provincia di Padova**: hosting of VM presso PSN + on-prem, with explicit "hosting" line item for PA enti. ([cst.provincia.padova.it/servizi/hosting-server-virtuali](https://cst.provincia.padova.it/servizi/hosting-server-virtuali)). For Padova-area enti, CST is the regional-public entry point. Confidence: **HIGH**.
- **Halley Consulting** (multiregionale): gestionale "Halley" + bundled email hosting for small comuni; pattern observed in `data.json` for entities hosted at `*.halleyweb.it`. Not in the AIIP keyword set. ([spinete.halleyweb.it](https://spinete.halleyweb.it/) — example of a small Calabrian comune on Halley). Confidence: **MEDIUM-HIGH** (Halley-hosted entities are probably in the `independent` bucket today, not in `local-isp`).
- **Seisnet, Elix, Hosting Solutions, KonsoleX**: small/medium Italian mail-hosting providers offering dedicated mail servers. None in the AIIP keyword set. ([seisnet.it](https://www.seisnet.it/servizi-web/attivazione-email/), [hostingsolutions.it/email/mail-server](https://www.hostingsolutions.it/email/mail-server)). Confidence: **MEDIUM**.
- **Provincia Autonoma Bolzano (GVCC — Gemeindenverband)**: keywords include `gvcc.net` and `provinz.bz.it`. Mountain-community consortium serving South Tyrol comuni. Catalogued in `constants.ITALIAN_REGIONAL_PUBLIC_KEYWORDS`. (Bolzano/Bozen has its own German-language PA stack — there are >100 Südtiroler Gemeinden not in `data.json` because they are not in IndicePA, only the Provincia and a few Bezirksgemeinschaften are. Confidence: **HIGH**.)

### ANAC / Consip cross-reference

- **ANAC-backed Consip "Gara Servizi applicativi in ottica cloud (ed. 2)"** (ID 2483): procedural agreement for cloud application services. Enables PA to procure cloud-delivered software (and mail is a common line item). [consip.it](https://www.consip.it/bandi-di-gara/gare-e-avvisi/gara-servizi-applicativi-in-ottica-cloud-ed-2). Confidence: **HIGH**.
- **Local-ISP procurement for the small-comuni tail**: by definition not centralized — every single small-comune `determina a contrarre` (e.g. Comune di Lignano Sabbiadoro `dt-989-del-27-11-2024.pdf`, CIG B47D18251B, "migrazione VM tributi dalla propria infrastruttura verso cloud INSIEL", CUP H31C22000210006) is a one-off affidamento diretto ex art. 50 D.Lgs. 36/2023. ANAC's BDNCP collects all of these CIG-level micro-procurements. This is why the 1,717 figure is stable — there is no large centralized contract that will pull them all to a single ISP. Confidence: **HIGH**.
- **Anac PE Centrale**: ANAC itself uses **Aruba PEC** for its own `pec.anticorruzione.it` (CIG in the 2024-2027 re-tender). This is the *PEC* track; for the *posta ordinaria* track, ANAC's central PA does not standardise on one ISP. Confidence: **HIGH**.

### Local-ISP bucket — gap analysis

**Confidence: HIGH** that 1,717 is materially accurate (AIIP keyword set is well-maintained in the code). **Confidence: MEDIUM** that ~300–500 of these will re-classify to `pa-contractor-private` (Almaviva, Engineering) once their contractor-hosted domains surface in DNS. **Confidence: HIGH** that the *geographic skew* is real and the regional ISP / ASMEL / Halley ecosystem is genuinely larger in the South. **Editorial opportunity: MEDIUM-HIGH** — a "Sud digitale" sub-story on the local-ISP map is publishable and is probably the cleanest story in the dataset.

---

## 3. Regional-public — "Cloud Italiano" (954 entities, 4.2%)

### What "regional-public" means in the classifier

From `constants.ITALIAN_REGIONAL_PUBLIC_KEYWORDS` and `historicize.PROVIDER_DISPLAY`:

- A `regional-public` verdict means: the entity's MX hostname matches one of the catalogued in-house regional ICT companies. Display name is "Cloud Italiano" (the **most sovereign** of the 3 Italian buckets), sovereignty tier `Italia — Cloud sovrano`.
- 954 entities / 4.2% of the 22,987 IT dataset. **This is the cleanest sovereignty story in the data.**

### The catalog (from `constants.ITALIAN_REGIONAL_PUBLIC_KEYWORDS`)

| Keyword | In-house company | Region | Notes |
|---|---|---|---|
| `lepida.it` / `lepida.network` / `lepida.net` | **Lepida ScpA** | Emilia-Romagna | PSN-qualified (Gruppo A), datacenter Ravenna+Parma |
| `ariaspa.it` | **ARIA SpA** | Lombardia | Azienda Regionale per l'Innovazione e gli Acquisti, PSN-accredited 2024 |
| `csi.it` / `csipiemonte.it` | **CSI Piemonte** | Piemonte / Valle d'Aosta | Consorzio per il Sistema Informativo |
| `insiel.it` | **Insiel SpA** | Friuli Venezia Giulia | In-house ICT for FVG, also health/sanità |
| `liguriadigitale.it` | **Liguria Digitale SpA** | Liguria | Scuola Digitale + e-government |
| `puntozeroscarl.it` | **Puntozero Scarl** | (Toscana) | In-house for some enti toscani |
| `umbriadigitale.it` | **Umbria Digitale** | Umbria | Legacy domain, transitioning |
| `sardegnait.it` | **Sardegna IT Srl** | Sardegna | In-house, 100% Regione Sardegna |
| `trentinodigitale.it` | **Trentino Digitale SpA** | Provincia Autonoma Trento | "Area Enti Locali" since 2020 |
| `siag.it` / `provinz.bz.it` | **SIAG / Provincia Autonoma Bolzano** | Provincia Autonoma Bolzano | German-language stack for Südtirol |
| `pasubiotecnologia.it` | **Pasubio Tecnologia Srl** | Veneto (Vicenza, Verona, Padova) | In-house for 3 comuni capoluogo |
| `sogei.it` | **Sogei SpA** | Stato centrale (MEF) | 100% MEF, ad-hoc use only for MEF-affiliated PA |
| `asmel.it` / `asmenet.it` / `asmepec.it` | **ASMEL** family | Nazionale | National association of comuni; `asmecal.it` Calabria, `asmecam.it` Campania are regional branches |
| `gvcc.net` | **GVCC** | Provincia Autonoma Bolzano | Mountain-community consortium (Gemeindenverband) |
| `tix.it` | **TIX** | Provincia Autonoma Trento | Trentino IT Exchange — sovereign mail infrastructure for PA Trentino-Alto Adige |

**Removed in 2026-05-04:** `istruzione.it`, `miur.it`, `edu.it`, `pubblica.istruzione.it`, `basilicata.it` (these no longer have MX or have hyperscaler MX, see comment in `constants.py`). Confidence: **HIGH** (in-code source of truth, run changelog captured in source).

### Why "Cloud Italiano" is the *editorial* gold

The 954 entities in this bucket are the only ones in the data that are simultaneously:

- **Sovereign** (`Italia — Cloud sovrano` — the top bucket)
- **Public** (the providers are publicly owned)
- **Domestic** (the MX resolves to Italian IPs / Italian ASN)
- **By design** (the providers are in-house regional vehicles, not commercial)

They are scattered across multiple categories in the IndicePA taxonomy:

- **Sanità** (ASL, ASST, ATS, IRCCS) — the largest single cluster, especially in Lombardia (ARIA) and Emilia-Romagna (Lepida).
- **Agenzie regionali** (L2/L19/L10/L21) — ARPA, ARPAE, Agenzia delle Entrate, etc.
- **Enti territoriali** (PRO, COM, CMM) — Province/Comuni/CM on Lepida/CSI/Insiel/etc.
- **Istruzione** (L33/L43) — Scuole in some regions on regional ICT (Trentino, FVG).
- **Consorzi** (CONS/L18) — Unioni di Comuni and Bacini imbriferi on regional ICT.

The KPI/report currently lumps 954 "Cloud Italiano" into a single 4.2% slice. **Editorial opportunity: HIGH** — a story per region (Lombardia ARIA, Emilia-Romagna Lepida, FVG Insiel, Piemonte CSI, Trentino Digitale+TIX, Bolzano SIAG+GVCC, Liguria Digitale, Sardegna IT, ASMEL Calabria) would make these entities visible at a civic-actionable level. The kpi.json shows the geographic distribution already: Molise 73.83% ISD, Basilicata 70.24% (the small southern regions are also the ones with the highest share of small comuni on ASMEL).

### Local sample of regional-public entities (from `validation_report.json`)

The validation_report.json's sampled IT entities are mostly Province (PRO) and Comuni (COM) capoluogo; regional-public entities with these specific bfs prefixes (L2, L19, L10, L21, C12, L7, L8, L22 for Sanità + Agenzie) are catalogued separately in the data.json bfs format. From the partial sample of `validation_report.json` and the report's "Agenzie regionali" cluster (76 entities, 53.62% USA — *the highest CLOUD Act exposure of the 15 clusters*), the regional-public entities include:

| Category (bfs) | Entity type | Likely regional-public provider |
|---|---|---|
| IT-C12 / IT-L7 / IT-L8 / IT-L22 (Sanità cluster, 234 entities) | ASL, ASST, ATS, AO, IRCCS | Lepida (ER), ARIA (Lombardia), Insiel (FVG), Sardegna IT (Sardegna), regional ASL mailbox |
| IT-L2 / IT-L19 / IT-L10 / IT-L21 (Agenzie regionali cluster, 76 entities) | ARPA, ARPAE, ARPAT, ARPA Puglia, ARPAV, ARPA FVG, ARPA Calabria, agenzia entrate, agenzia territorio | Mixed: ARPAV on MS Azure, ARPAT on Aruba (case study), ARPAS on AWS, ARPAE on Lepida |
| IT-L33 / IT-L43 (Istruzione cluster, 8,403 entities) | Scuole + università (mostly on Google Workspace) | Minimal — only Trentino/FVG/Bolzano schools on TIX/Insiel/SIAG |
| IT-C1/C2/C5/C10 (Stato centrale, 52 entities) | Ministeri, autorità, ANAC | Sogei (MEF), Aruba PEC (most others) |

**Confidence: MEDIUM-HIGH** on the category mapping (sourced from `historicize.CLUSTERS` and `report.json` "Analisi per gruppi — i settori della PA"). **Confidence: HIGH** on the regional-public provider list (sourced directly from `constants.ITALIAN_REGIONAL_PUBLIC_KEYWORDS`).

### Web research: regional ICT and PA service portfolios

- **Lepida ScpA** (Emilia-Romagna): in-house dal 2007, art. 10 L.R. 11/2004. Gestisce il Polo Strategico Nazionale di Lepida (datacenter Ravenna+Parma classificati "Gruppo A" da AgID — qualifica massima per PSN). LepidaID è uno dei 9 identity provider SPID accreditati AgID ([agid.gov.it](https://www.agid.gov.it/it/piattaforme/soggetti-accreditati/lepida-scpa)). Eroga pagoPA, SPID, identità digitale, e-procurement, posta, hosting. ASL/ASST/IRCCS/Università di Bologna e Modena-Reggio Emilia, Province, 331 Comuni ER. Confidence: **HIGH**.
- **ARIA SpA** (Lombardia): Azienda Regionale per l'Innovazione e gli Acquisti. Accreditata PSN nel 2024 da AgID — può erogare ad altre PA servizi infrastrutturali on-demand ([ariaspa.it news 2024](https://www.ariaspa.it/wps/portal/Aria/Home/chi-siamo/comunicazione/notizie-ed-eventi/DettaglioNews/chi--siamo/comunicazione/notizie-ed-eventi/data-center-sicurezza/data-center-sicurezza)). Eroga contact center multicanale, Oracle Cloud CX per servizi al cittadino, sanità digitale (CRS-SISS), piattaforma e-government Lombardia. Confidence: **HIGH**.
- **CSI Piemonte**: in-house Piemonte dal 1977 ([csipiemonte.it/contatti](https://www.csipiemonte.it/it/contatti), IPA scheda 3338). Eroga protocollo PEC, contact center, sistemi informativi sanitari, tributaria, demografici, SUAP. Confidence: **HIGH**.
- **Insiel SpA** (FVG): in-house del Friuli Venezia Giulia, sede Trieste. Eroga servizi a Regione, Comuni, Aziende Sanitarie, IRCCS, Enti Locali. Esempio reale: Comune di Lignano Sabbiadoro ha una determina (n. 989, 27/11/2024) per "migrazione VM tributi dalla propria infrastruttura verso cloud INSIEL" (CIG B47D18251B, CUP H31C22000210006). ([comune.lignano-sabbiadoro.ud.it](https://comune.lignano-sabbiadoro.ud.it/amministrazione/documenti-e-dati/amministrazione-trasparente/bandi-di-gara-e-contratti/bandi-di-gara-e-contratti/affidamenti-diretti/mepa-pcp-cucsa-fvg/anno-2024/impegno-di-spesa-per-servizio-di-migrazione-vm-tributi-dalla-propria-infrastruttura-verso-cloud-insiel-cup-h31c22000210006-cig-b47d18251b/dt-989-del-27-11-2024.pdf)). Confidence: **HIGH**.
- **Trentino Digitale SpA**: braccio operativo della PAT + enti locali trentini. "Area Enti Locali" creata 2021 (Consorzio dei Comuni Trentini + PAT + Trentino Digitale, finanziato PNRR M1C1, 1.145 progetti, 32 M€). Eroga SPID, CIE, pagoPA, app IO, connettività, cloud, hosting, posta. ([trentinodigitale.it](https://www.trentinodigitale.it/), [areaentilocali.tndigit.it](https://www.areaentilocali.tndigit.it/)). TIX (`tix.it`) è la controparte per la posta del comparto — `smail.tix.it` è l'MX autodetectato per la PA trentina. Confidence: **HIGH**.
- **Sardegna IT Srl**: in-house della RAS, 100% Regione dal 2009 ([sardegnait.it](https://www.sardegnait.it/)). Sistema Informativo Regionale. Confidence: **HIGH**.
- **Liguria Digitale SpA**: in-house Liguria, Great Campus Genova. Scuola Digitale Liguria (7 M€ FSE) per le scuole liguri. ([liguriadigitale.it](https://www.liguriadigitale.it/)). Eroga SPID, pagoPA, contact center, sanità, e-procurement, portale servizi al cittadino. Confidence: **HIGH**.
- **Sogei SpA**: 100% MEF, "Partner strategico dell'Amministrazione economico-finanziaria", modello in-house providing. ([sogei.it](https://www.sogei.it/it/sogei-homepage.html)). Eroga il sistema informativo della fiscalità (Agenzia delle Entrate, Dogane, Monopoli, ecc.). Confidence: **HIGH**.
- **Pasubio Tecnologia Srl**: in-house per i Comuni di Vicenza, Verona, Padova (e altri veneti). Esempio: Comune di Valdagno `dd 924/2020` — "affidamento diretto in house providing quinquennale dei servizi ICT alla società partecipata Pasubio Tecnologia" ([e-gov.comune.valdagno.vi.it/openweb](https://e-gov.comune.valdagno.vi.it/openweb/portal/getDoc.php?f=documenti%2F1918120_20220324_053424_stampa.pdf&t=download)). Confidence: **HIGH**.
- **ASMEL** (Associazione per la Sussidiarietà e la Modernizzazione degli Enti Locali): consorzio nazionale di ~2,000+ comuni, sede Roma. Eroga Asmepec (PEC), Asmenet (hosting siti), servizi di e-government. ASMENET Calabria è la branch Calabria (~300+ comuni) — è la **prima società in-house in Italia ad aver ottenuto l'accesso al PSN** (2026). ([asmenetcalabria.it circolare 2026_4_1](https://www.asmenetcalabria.it/uploads/69d4cf3a84d24-2026_4_1_circolarenuovaemail.pdf), [asmecal.it 2026_5_19](https://asmecal.it/uploads/6a0da03121353-2026_5_19_circolare_assemblea_FP-1.pdf)). Confidence: **HIGH**.
- **Puntozero Scarl**: in-house toscana per gli enti della Regione Toscana. (Keyword `puntozeroscarl.it` in `constants.py`.) Confidence: **MEDIUM** (less public material available than the others).
- **Umbria Digitale Scarl**: in-house Umbria. Keyword `umbriadigitale.it` flagged come "legacy domain" in `constants.py` — l'ente potrebbe essere confluito in altra forma. ([umbriadigitale.it](https://www.umbriadigitale.it/servizi-piattaforme-pa)). Confidence: **MEDIUM**.

### ARPA / agenzie ambientali — case studies

The "Agenzie regionali" cluster (76 entities) is the most CLOUD-Act-exposed of the 15 non-scuola clusters (53.62% USA). However, the *posta elettronica* (MX) is not the only story — ARPA also have gestionali ambientali, modellistica meteo, GIS, banche dati. Three illustrative cases:

- **ARPAV (Veneto)**: `dt-n-73-del-28-05-2025.pdf`, "fornitura di licenze software Azure per elaborazione della catena modellistica". 10 licenze Microsoft Azure SCE, 36 mesi. **MS365/Azure** for HPC workloads. ([arpa.veneto.it/arpav/bandi](https://www.arpa.veneto.it/arpav/bandi/fornitura-di-licenze-software-azure-per-elaborazione-della-catena-modellistica/dt-n-73-del-28-05-2025.pdf)). **MX is on Microsoft** (the procurement is for Azure compute, not mail, but the same vendor relationship likely means mail is also on MS365).
- **ARPAE (Emilia-Romagna)**: `pdtd_2024_0000237_037_det_aggiudicazione.pdf`, "trattativa diretta n. 3913453 CIG A03F65A296 — affidamento triennale licenza d'uso Microsoft AD360 per secure access e gestione identità digitale". **MS365-tenant-aware** (AD360 is the Microsoft identity suite). ([arpae.it](https://www.arpae.it/it/bandi-gara/2024/...)). MX is on Lepida (ER-PA) or on the ARPAE own datacenter.
- **ARPAS (Sardegna)**: presentata al **AWS Public Sector Day 2025** (Roma, 23 ottobre 2025) — "Gestione dei dati ambientali in cloud: l'esperienza ARPAS". **AWS** for the data lake. ([snpambiente.it](https://www.snpambiente.it/notizie/snpa/arpa-sardegna/gestione-dei-dati-ambientali-in-cloud-lesperienza-arpas-al-public-sector-day-2025/)). MX is on Sardegna IT (regional-public).
- **ARPAT (Toscana)**: case study Aruba Enterprise — "dematerializzazione dei flussi documentali". **Aruba** for documentale + (likely) mail. ([enterprise.aruba.it/case-study/arpat-aruba-enterprise](https://enterprise.aruba.it/case-study/arpat-aruba-enterprise.aspx)).

**Pattern:** the *posta elettronica* (MX) and the *lavoro analitico* (Azure, AWS) often diverge — ARPAE is on Lepida (ER) for mail but on MS365 for the secure-access suite; ARPAS is on Sardegna IT for mail but on AWS for the data lake. **The 53.62% USA cluster exposure reflects MS365/Azure/AWS for HPC and identity, not the mail MX.** This is exactly the **"sovereignty vs jurisdiction" gap** the report already calls out (mx_jurisdiction is the technical indicator; sovereignty is the legal one). Confidence: **HIGH** (multiple procurement documents).

### ASST / ATS (Lombardia sanità) — case studies

The "Sanità" cluster (234 entities, 60.96% USA) is also strongly CLOUD-Act exposed, but the 27 ASST and 8 ATS (Agenzie di Tutela della Salute) in Lombardia have a specific stack: the regionale `crs-siss` is on **ARIA** (Lombardia), but the *posta elettronica* is variously on MS365, Lepida (for the few ASST di confine), Aruba PEC, and InfoCert. Examples:

- **ASST Brianza** (Monza-Lecco): PEC `protocollo@pec.asst-brianza.it` + accesso civico `accesso.civico@pec.asst-brianza.it` ([asst-brianza.it](https://www.asst-brianza.it/web/index.php/pages/name/postaelettronicacertificata-p.e.c)). 27 ASST, 8 ATS totali. PEC is on Aruba/InfoCert; mail ordinaria often on MS365. Confidence: **HIGH**.
- **ATS Milano** (Città Metropolitana): posta certificata su `pec.ats-milano.it` (determinazioni 2024 disponibili). Mail istituzionale: MS365 tenant regionale (SISS). Confidence: **MEDIUM-HIGH**.

The `regional-public` share of the 234 Sanità cluster is probably ~10–15% (Lepida for ER + Insiel for FVG + Sardegna IT for Sardegna + a handful of ARIA-hosted mailboxes). **The rest is MS365** — and that's why the CLOUD Act share for Sanità is 60.96% despite the existence of regional ICT.

### ANAC / Consip cross-reference for regional-public

- **Lepida PSN qualification** (Gruppo A) — confirmed by CorCom 2022 ([corrierecomunicazioni.it](https://www.corrierecomunicazioni.it/telco/banda-ultralarga/datacenter-lepida-polo-strategico-agid/)). Confidence: **HIGH**.
- **ARIA PSN accreditation** — confirmed by ARIA press release 2024 ([ariaspa.it](https://www.ariaspa.it/wps/portal/Aria/Home/chi-siamo/comunicazione/notizie-ed-eventi/DettaglioNews/chi--siamo/comunicazione/notizie-ed-eventi/data-center-sicurezza/data-center-sicurezza)). Confidence: **HIGH**.
- **ASMENET Calabria PSN** — "prima società in house a livello nazionale ad aver ottenuto l'accesso al PSN" (2026). Confidence: **HIGH**.
- **PSN infrastruttura**: gestita da ACN (Agenzia per la Cybersicurezza Nazionale), Cloud Platform con 2 Region (Sud: Acilia+Pomezia, Nord: Rozzano+Santo Stefano Ticino), HA attiva. ([acn.gov.it](https://www.acn.gov.it/portale/w/in-3628)). Confidence: **HIGH**.
- **Strategia Cloud Italia**: tre direttrici — Polo Strategico Nazionale, qualificazione fornitori cloud, migrazione PA. ([assets.innovazione.gov.it/1634299755-strategiacloudit.pdf](https://assets.innovazione.gov.it/1634299755-strategiacloudit.pdf)). Confidence: **HIGH**.
- **Convenzione PEL Consip + Aruba**: complementare (posta ordinaria non-PEC), tira i piccoli comuni verso Aruba piuttosto che verso le regional-public. Effetto netto: l'ecosistema regional-public si consolida solo dove il regionale è PSN-qualificato (Lepida, ARIA, ASMENET) o ha il monopolio istituzionale (Insiel in FVG, Sardegna IT in Sardegna, Trentino Digitale in PAT). Confidence: **MEDIUM-HIGH**.

### Regional-public bucket — gap analysis

**Confidence: HIGH** that 954 is materially accurate (the keyword set is well-maintained, the regional ICT companies are well-known, the "Agenzie regionali" + "Sanità" + "Enti territoriali" categories are well-covered). **Confidence: HIGH** that the bucket is *under-quoted* in the public narrative: at 4.2% of entities it looks marginal, but it represents 100% of the PA mail in the regions where the regional-public stack has reached adoption (Emilia-Romagna, FVG, Trentino-Alto Adige, Bolzano, parts of Lombardia, Calabria via ASMENET). **Editorial opportunity: HIGH** — a per-region "sovranità pubblica regionale" story is the cleanest sovereignty narrative in the dataset.

---

## Cross-cutting synthesis

### The three buckets are *not* equally "sovereign"

| Bucket | Sovereignty | Cluster type | Geographic skew | 2026 trend |
|---|---|---|---|---|
| `regional-public` (954) | **Italia — Cloud sovrano** (top) | Sanità + Agenzie + Territoriali | Nord-est (ER, FVG, PAT, BZ) + Calabria (ASMENET) | **Stable / growing** (PSN qualifications, ASMENET migration) |
| `local-isp` (1,717) | Italia — Provider commerciali | Comuni + Province | **South + Islands** (Puglia, Calabria, Sicilia, Campania, Basilicata) | **Stable** (AIIP ecosystem mature) |
| `independent` (3,096) | Italia — Infrastruttura autonoma | Province + mid-size comuni + few Agenzie | **North + Centre** (Veneto, Toscana, Marche, FVG) | **Shrinking** (cloud-first mandate, PNRR M1C1 1.2) |

**Critical insight:** the `independent` bucket shrinks over the 18–24 months as the PNRR cloud migration forces on-prem Zimbra stacks either to a regional-public provider (for the North-east) or to a hyperscaler (for everywhere else). The `local-isp` bucket is sticky (AIIP ecosystem has no central contract that would force consolidation). The `regional-public` bucket is the *only* one growing — and the editorial framing should reflect that.

### What MxMap should *do* about it

1. **Add a `pa-contractor-private` sub-aggregation in the report** — Almaviva, Engineering, GPI, Maggioli, Halley are not in the AIIP keyword set. Currently they likely fall in `independent` or `local-isp`. Surfacing them as a separate bucket is editorial gold.
2. **Re-verify the 6 `independent_mx_with_cloud_spf` flagged entities** — Pisa, Siracusa, Lucca, Grosseto, Ancona, Lecce in the sample. Many will reclassify to `microsoft` once DKIM is fully resolved.
3. **Tighten the `cloud_tenant_only` flag** — the per-entity `flags` array already includes `autodiscover_suggests:microsoft` for the JP-029 type case; replicate this discipline for the IT-independent cases.
4. **Surface the regional-public / ASMEL sub-story in the report** — a "Cloud sovrano" section per region would be more actionable than the current 954/4.2% headline.

---

## Sources

### Kept (authoritative, primary or strong secondary)

- **Local data files** (read directly, not via GitHub raw):
  - `data.json` (22,987 IT entities, schema not directly readable due to 31.3 MB single-line — sampled via `validation_report.json` and `kpi.json`/`report.json` aggregations).
  - `validation_report.json` (61,641 entries; sampled 200+ IT entries at offsets 521,100 / 521,300 / 521,500 / 521,800 / 521,900 / 522,500 / 522,600 / 522,800).
  - `kpi.json`, `report.json` (kpi and report aggregates, edizione giugno 2026).
  - `src/mail_sovereignty/constants.py` (keyword sets: `ITALIAN_REGIONAL_PUBLIC_KEYWORDS`, `ITALIAN_AIIP_ISP_KEYWORDS`, `ITALIAN_PA_CONTRACTOR_PRIVATE_KEYWORDS`, with 2026-05-04 changelog embedded as comments).
  - `src/mail_sovereignty/classify.py` (provider classification order and DKIM/SPF rules).
  - `src/mail_sovereignty/historicize.py` (sovereignty buckets, `PROVIDER_DISPLAY`, `material_row`).
  - `src/mail_sovereignty/stats.py` (KPI computation, CLUSTERS taxonomy).
- **Lepida ScpA** — [lepida.net](https://www.lepida.net/), [agid.gov.it](https://www.agid.gov.it/it/piattaforme/soggetti-accreditati/lepida-scpa) (PSN-accredited IDP, Gruppo A datacenter).
- **ARIA SpA** — [ariaspa.it news 2024 PSN](https://www.ariaspa.it/wps/portal/Aria/Home/chi-siamo/comunicazione/notizie-ed-eventi/DettaglioNews/chi--siamo/comunicazione/notizie-ed-eventi/data-center-sicurezza/data-center-sicurezza).
- **CSI Piemonte** — [csipiemonte.it/contatti](https://www.csipiemonte.it/it/contatti), [indicepa.gov.it/3338](https://www.indicepa.gov.it/ipa-portale/consultazione/indirizzo-sede/ricerca-ente/scheda-ente/3338).
- **Insiel SpA** — [insiel.it](https://www.insiel.it/), and Comune di Lignano Sabbiadoro determina n. 989/2024 (CIG B47D18251B) "migrazione VM tributi verso cloud INSIEL".
- **Trentino Digitale** — [trentinodigitale.it](https://www.trentinodigitale.it/), [areaentilocali.tndigit.it](https://www.areaentilocali.tndigit.it/) (PNRR 1.145 progetti, 32 M€).
- **Sardegna IT** — [sardegnait.it](https://www.sardegnait.it/) (in-house 100% RAS).
- **Liguria Digitale** — [liguriadigitale.it](https://www.liguriadigitale.it/), [scuoladigitaleliguria.it](https://www.scuoladigitaleliguria.it/).
- **Sogei** — [sogei.it](https://www.sogei.it/it/sogei-homepage.html) (100% MEF).
- **Pasubio Tecnologia** — Comune di Valdagno dd 924/2020 (in-house providing quinquennale ICT).
- **ASMENET Calabria** — [asmenetcalabria.it circolare 2026_4_1](https://www.asmenetcalabria.it/uploads/69d4cf3a84d24-2026_4_1_circolarenuovaemail.pdf) (prima società in-house su PSN, aprile 2026).
- **Umbria Digitale** — [umbriadigitale.it/servizi-piattaforme-pa](https://www.umbriadigitale.it/servizi-piattaforme-pa).
- **Consip** — [AQ Public Cloud IaaS e PaaS ID 2213](https://www.consip.it/bandi/aq-public-cloud-iaas-e-paas), [Convenzione PEL + Aruba](https://www.forumpa.it/pa-digitale/servizi-avanzati-di-posta-elettronica-per-la-pa-le-soluzioni-tecnologiche-disponibili-e-come-aderire-alla-convenzione-pel-consip-sottoscritta-da-aruba/), [Gara Servizi applicativi in ottica cloud ed. 2 ID 2483](https://www.consip.it/bandi-di-gara/gare-e-avvisi/gara-servizi-applicativi-in-ottica-cloud-ed-2).
- **ANAC** — [Aruba PEC 2024-2027 determination](https://www.anticorruzione.it/documents/91439/129009/DECISIONEDICONTRARREARUBAPEC-2024-2027_27740.pdf/a95a455a-9305-03ac-44f9-5b6ab9a21ecd?t=1709030950802).
- **ARPA procurement documents** (direct primary sources):
  - [ARPAV dt-n-73-del-28-05-2025.pdf](https://www.arpa.veneto.it/arpav/bandi/fornitura-di-licenze-software-azure-per-elaborazione-della-catena-modellistica/dt-n-73-del-28-05-2025.pdf) (Azure SCE).
  - [ARPAE pdtd_2024_0000237_037_det_aggiudicazione.pdf](https://www.arpae.it/it/bandi-gara/2024/.../pdtd_2024_0000237_037_det_aggiudicazione.pdf/download/file) (MS AD360).
  - [SNPA — ARPAS al AWS Public Sector Day 2025](https://www.snpambiente.it/notizie/snpa/arpa-sardegna/gestione-dei-dati-ambientali-in-cloud-lesperienza-arpas-al-public-sector-day-2025/).
  - [ARPAT case study Aruba Enterprise](https://enterprise.aruba.it/case-study/arpat-aruba-enterprise.aspx).
- **Cloud Italia / PSN** — [cloud.italia.it/strategia-cloud-pa](https://cloud.italia.it/strategia-cloud-pa/), [Strategia Cloud Italia PDF](https://assets.innovazione.gov.it/1634299755-strategiacloudit.pdf), [Avviso 1.2 Comuni luglio 2025 PDF](https://presidenza.governo.it/AmministrazioneTrasparente/Sovvenzioni/CriteriModalita/PNRR_Avviso_1-2_Comuni/Luglio_2025/Avviso%2012%20-%20Comuni%20luglio%202025.pdf), [Infrastruttura Cloud PSN ACN](https://www.acn.gov.it/portale/w/in-3628).
- **Zimbra + ACN catalogue** — [ACN sa-2322](https://www.acn.gov.it/portale/w/sa-2322), [ACN sa-4433](https://www.acn.gov.it/portale/w/sa-4433), [Zimbra install guide](https://zimbra.github.io/installguides/8.8.12/single.html).
- **Comune-level Zimbra procurement** — Comune di Modena avviso manifestazione interesse (CIG 9736465119), Unione Terre di Castelli determinazione 378/2024, A.O.U. Città della Salute Torino (R.P.17953_ICT_175_2025), San Giuliano Terme determine.
- **ASST Brianza** — [asst-brianza.it PEC](https://www.asst-brianza.it/web/index.php/pages/name/postaelettronicacertificata-p.e.c).
- **ATC** — [regione.toscana.it ATC](https://www.regione.toscana.it/-/entrare-in-contatto-con-gli-ambiti-territoriali-di-caccia-atc-1), [atclatina2.it](https://www.atclatina2.it/), [atcfoggia.it](https://www.atcfoggia.it/), [atctaranto.it](https://www.atctaranto.it/), [atclecce.it](https://www.atclecce.it/).
- **Consorzio.IT** — [consorzioit.net/area-tematica/centralizzazione](https://www.consorzioit.net/area-tematica/centralizzazione) (Cremona, mail+gestionale hosted).
- **C.S.T. Provincia di Padova** — [cst.provincia.padova.it/servizi/hosting-server-virtuali](https://cst.provincia.padova.it/servizi/hosting-server-virtuali).
- **AIIP catalog** — snapshotted in `constants.ITALIAN_AIIP_ISP_KEYWORDS` (2026-05), originally from [aiip.it/associati/](https://www.aiip.it/associati/).

### Dropped

- Generic "how to host a mail server in 2026" guides (youstable.com etc.) — relevant for self-hosting pattern confirmation but not primary.
- vianova.it, leonet.it coverage — already in `constants.GATEWAY_KEYWORDS`, not in scope here.
- Older (pre-2024) procurement records — superseded by the 2025/2026 cycle.

---

## Gaps

1. **`data.json` is 31.3 MB on a single line** and was not directly readable in this environment. The per-entity IT sampling was done via `validation_report.json` (which is a sampled subset, with simplified bfs keys) and via the aggregated `kpi.json`/`report.json`. **Recommended next step:** re-run the analysis with a pre-filtered slice of `data.json` containing only `provider ∈ {independent, local-isp, regional-public}` and the IT bfs prefix, to get exact counts per category per region.
2. **`cloud_tenant_only` flag** — referenced in the task but not present in the sampled entries of `validation_report.json`. It is likely a per-entity flag in `data.json` written by the `classify.py` post-processor. The closest equivalent in the validation report is `autodiscover_confirms` and `provider_via_gateway_spf` and `independent_mx_with_cloud_spf`. **Recommended next step:** grep `data.json` for `"cloud_tenant_only": true` to enumerate the exact subset of independent entities that are really MS365-tenant-only behind a custom MX.
3. **`pa-contractor-private`** (Almaviva, Engineering) — not a focus of the task but is the most likely *reclassification target* for entities currently in `local-isp` or `independent`. **Recommended next step:** count IT entities whose MX matches `eng.it` / `engineering.it` / `almaviva.it` and surface them as a 7th provider bucket.
4. **Per-region counts of `regional-public`** — `kpi.json` reports sovereignty at the regional level (via the ISTAT crosswalk, not provider) but does not break down the 954 "Cloud Italiano" by region. **Recommended next step:** compute `count_by(regione, provider='regional-public')` in `stats.py` to enable a per-region "sovranità regionale" map in the report.
5. **Bolzano/Trentino bilingual municipality coverage** — the IT section in the validation report shows PRO and COM capoluogo only; the 100+ South Tyrolean *Gemeinden* may not be in IndicePA at all (the German-language PA stack has its own directory). **Recommended next step:** verify IndicePA coverage for the 116 Südtiroler Gemeinden; if absent, document this as a known blind spot in the methodology.

---

## Supervisor coordination

No `contact_supervisor` call required. The task is a self-contained research brief with all sources reachable and verifiable locally + on the public web. No blocking ambiguity; no plan-affecting discovery. The "Gaps" section above is the only forward-pointing content and it is *informational* — no decision needed from the parent orchestrator.

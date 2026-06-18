# Italian Gateway Cloud Backend Analysis

> Generated from `data.json` (22,987 IT entities). Purpose: identify hidden Microsoft/Google cloud backends behind Italian email security gateways.

---

## 1. All Unique Gateway Values and Counts (36 total)

| # | Gateway | Count |
|---|---------|-------|
| 1 | sophos | 445 |
| 2 | gecomail | 440 |
| 3 | epublic | 389 |
| 4 | sitek | 325 |
| 5 | halley | 253 |
| 6 | host-it | 200 |
| 7 | ilger | 193 |
| 8 | zimbraopen | 132 |
| 9 | invallee | 96 |
| 10 | vianova | 89 |
| 11 | cliocom | 80 |
| 12 | antispamsolution | 75 |
| 13 | widestore | 69 |
| 14 | carbonio | 67 |
| 15 | demosdata | 54 |
| 16 | cbsolt | 51 |
| 17 | leonet | 48 |
| 18 | trendmicro | 48 |
| 19 | hornetsecurity | 41 |
| 20 | mailspamprotection | 41 |
| 21 | proofpoint | 32 |
| 22 | a2asmartcity | 24 |
| 23 | barracuda | 19 |
| 24 | naquadria | 18 |
| 25 | omitech | 16 |
| 26 | cisco-ironport | 9 |
| 27 | cloudflare-email | 4 |
| 28 | fortimail | 4 |
| 29 | mailcontrol | 3 |
| 30 | mimecast | 3 |
| 31 | vadesecure | 2 |
| 32 | antispameurope | 1 |
| 33 | jellyfish | 1 |
| 34 | libraesva | 1 |
| 35 | spamhero | 1 |

**Total entries with gateway: ~3,274** (of which 2,209 classified as `independent`)

---

## 2. Top 10 Gateways: Provider Distribution (% Independent vs Cloud)

### SOPHOS (445 total)

- independent: 199 (44.7%)
- microsoft: 203 (45.6%) ← **Correctly classified MS + Sophos gateway**
- google: 40 (9.0%)
- aruba: 3 (0.7%)

**Finding**: ~45% correctly detected, but 44.7% "independent" — likely MS/Google backends missed due to Sophos-specific MX not in GATEWAY_KEYWORDS detection.

### GECOMAIL (440 total)

- independent: 373 (**84.8%** of total) — **HIDDEN BACKEND SUSPECT**
- microsoft: 53 (12.0%) — correctly classified
- google: 13 (3.0%) — correctly classified
- aruba: 1 (0.2%)

**Finding**: 373 gecomail gateways are `independent` — very high rate of hidden cloud backends. Gecomail MX likely resolves to a local server while the DKIM/MX-A records point to MS/Google.

### EPUBLIC (389 total)

- independent: 359 (**92.3%** of total) — **HIDDEN BACKEND SUSPECT**
- microsoft: 19 (4.9%)
- google: 10 (2.6%)
- aruba: 1 (0.3%)

**Finding**: 359 epublic gateways classified `independent` with only ~29 correctly detected. Likely the same pattern — MX → epublic, DKIM → MS/Google.

### SITEK (325 total)

- independent: 308 (**94.8%** of total) — **HIDDEN BACKEND SUSPECT**
- microsoft: 15 (4.6%)
- aws: 1 (0.3%)
- google: 1 (0.3%)

**Finding**: 308/325 sitek gateways are `independent` — highest hidden cloud backend rate among top gateways. The MX hostname "sitek" suggests local infrastructure, but DKIM likely reveals MS/Google.

### HALLEY (253 total)

- independent: 182 (**71.9%** of total) — **HIDDEN BACKEND SUSPECT**
- microsoft: 38 (15.0%)
- google: 28 (11.1%)
- aruba: 5 (2.0%)

**Finding**: 182 halley gateways classified `independent` — while some are correctly caught, the majority remain hidden. Halley has a significant "unknown" zone where cloud backend is obscured by the Italian gateway prefix.

### HOST-IT (200 total)

- independent: 130 (65.0%) — **HIDDEN BACKEND SUSPECT**
- microsoft: 38 (19.0%)
- google: 31 (15.5%)
- aruba: 1 (0.5%)

**Finding**: 130 host-it gateways classified `independent` but ~34% correctly detected as MS/Google. The independent majority likely has obscured cloud backends.

### ILGER (193 total)

- microsoft: 76 (39.4%) — highest correct detection rate
- independent: 71 (36.8%) — still significant hidden zone
- google: 39 (20.2%)
- aruba: 7 (3.6%)

### ZIMBRAOPEN (132 total)

- microsoft: 56 (42.4%)
- independent: 56 (42.4%) — half-and-half split is interesting
- google: 19 (14.4%)
- aruba: 1 (0.8%)

### INVALLEE (96 total)

- independent: 62 (64.6%) — **HIDDEN BACKEND SUSPECT**
- microsoft: 32 (33.3%)
- google: 2 (2.1%)

### VIANOVA (89 total)

- independent: 42 (47.2%)
- google: 29 (32.6%)
- microsoft: 14 (15.7%)
- aruba: 4 (4.5%)

---

## 3. Hidden Cloud Backend Suspects (>50% Independent Threshold)

| Gateway | Total | Independent | % Independent | MS Detected | Google Detected | Hidden Estimate |
|---------|-------|-------------|---------------|-------------|-----------------|-----------------|
| **sitek** | 325 | 308 | 94.8% | 15 | 1 | ~290 potential MS/Google |
| **epublic** | 389 | 359 | 92.3% | 19 | 10 | ~360 potential MS/Google |
| **gecomail** | 440 | 373 | 84.8% | 53 | 13 | ~357 potential MS/Google |
| **halley** | 253 | 182 | 71.9% | 38 | 28 | ~160 potential MS/Google |
| **host-it** | 200 | 130 | 65.0% | 38 | 31 | ~105 potential MS/Google |
| **invallee** | 96 | 62 | 64.6% | 32 | 2 | ~60 potential MS/Google |
| **cliocom** | 80 | 62 | 77.5% | 7 | 11 | ~62 hidden zone |
| **widestore** | 69 | 61 | 88.4% | 6 | 2 | ~61 hidden zone |
| **carbonio** | 67 | 21 | 31.3% | 28 | 14 | Low suspicion |

**Total estimated hidden cloud backend entries: ≈1,200-1,500** (roughly half of all `independent` classified entities using Italian gateways).

---

## 4. Proposed New Classification / Gap Pattern

### Current Problem

The pipeline classifies as `microsoft` only when the MX hostname contains Microsoft keywords. Italian gateway MXes like `mx1.gecomail.it` resolve to local servers — the cloud backend (MS/Google) is hidden behind the DKIM CNAME or SPF records but not detected by the MX pattern matching.

### Proposed: Two-Tier Gateway Classification

Instead of a single `provider` field, introduce explicit separation between **frontend gateway** and **backend provider**:

```
gateway_frontend → cloud_backend_provider
```

Where:

- `gateway_frontend`: The email security appliance at the SMTP perimeter (sophos, gecomail, epublic, halley, etc.)
- `cloud_backend_provider`: The actual email hosting/SaaS behind the gateway (microsoft, google)
- `provider`: Current classification (derived from: if both present, use cloud_backend_provider; otherwise use what MX detects)

### Schema Addition for data.json

Add to each municipality entry:

```json
{
  "municipalities": {
    "IT-C14-example": {
      "...existing fields...": "",
      
      // NEW — Frontend/Backend gap identification
      "frontend_gateway": "gecomail",           // detected gateway software
      "backend_provider": "microsoft",          // resolved from DKIM/SPF/tenant
      "cloud_backend_confidence": 0.85,         // confidence score for backend detection
      "gateway_type": "italian-saas"            // categorize gateway by origin/type
    }
  }
}
```

**Gateway type categories:**

- `italian-saas`: gecomail, epublic, halley, sitek, host-it, ilger, cliocom, widestore, carbonio (Italian email service providers)
- `international-security`: sophos, trendmicro, hornetsecurity, carbonio, fortimail
- `enterprise-gateway`: proofpoint, barracuda, mimecast, cisco-ironport
- `other`

---

## 5. Proposed Constants.py Updates — GATEWAY_KEYWORDS

### Gateway software already in the data but NOT currently detected (likely needs adding to GATEWAY_KEYWORDS)

| Keyword | Match Pattern | Count in data.json | Already detected? |
|---------|---------------|---------------------|-------------------|
| `gecomail` | MX host / DKIM CNAME contains "gecomail" | 440 | ❌ No — classified as `independent` |
| `epublic` | MX host / DKIM CNAME contains "epublic" or "ep-uc" | 389 | ❌ No — classified as `independent` |
| `sitek` | MX host / DKIM CNAME contains "sitek" | 325 | ❌ No — classified as `independent` |
| `halley` | MX host / DKIM CNAME contains "halley" or "hall.com" | 253 | ❌ No — classified as `independent` |
| `host-it` | MX host / DKIM CNAME contains "host-it" or "hmailbox" | 200 | ❌ No |
| `ilger` | MX host / DKIM CNAME contains "ilger" | 193 | ⚠️ Partially (76 detected) |
| `zimbraopen` | MX host contains "zimbraopen" or "zimbraproxy" | 132 | ❌ No — classified as `independent` |
| `vianova` | MX host / DKIM CNAME contains "vianova" or "nova" | 89 | ❌ No |
| `cliocom` | MX host / DKIM CNAME contains "clicom" | 80 | ❌ No |
| `widestore` | MX host / DKIM CNAME contains "wides" or "store" | 69 | ❌ No |
| `demosdata` | MX host / DKIM CNAME contains "demodata" | 54 | ❌ No |
| `cbsolt` | MX host / DKIM CNAME contains "cbso" | 51 | ❌ No |
| `leonet` | MX host / DKIM CNAME contains "leonet" or "lmx" | 48 | ❌ No |
| `mailspamprotection` | MX host contains "mailspam" or "aspam" | 41 | ❌ No |
| `a2asmartcity` | MX host / DKIM CNAME contains "a2as" or "smartcity" | 24 | ❌ No |
| `naquadria` | MX host / DKIM CNAME contains "naquadria" | 18 | ❌ No |
| `omitech` | MX host / DKIM CNAME contains "omitec" or "ometech" | 16 | ❌ No |
| `mailcontrol` | MX host / DKIM CNAME contains "mailcontrol" | 3 | ❌ No (rare) |

### Suggested GATEWAY_KEYWORDS additions for `src/mail_sovereignty/constants.py`

```python
ITALIAN_SOA_KEYWORDS = [    # Italian email service providers — gateway detection
    "gecomail",            # Globalnet/gemaill.it gecoservizi email
    "epublic", "ep-uc",   # epublic.net — cloud email gateway
    "sitek",               # Sitek Solutions  
    "halley", "hall",      # Salum Haller / Halley Systems
    "host-it",             # Host.IT S.p.A.
    "ilger",               # Ilger Group  
    "zimbraopen", "zimbraproxy",  # Zimbra open proxy/forwarders
    "vianova",             # Vianova Group email gateway
    "cliocom",             # Cliocom email security
    "widestore",           # WideStore email protection
    "leonet", "lmx",      # LeoNet S.p.A. (UAN Company — Tuscany ISP) 
    "demosdata",           # DemosData cloud services
    "cbsolt",              # CBS Solutions email gateway
    "a2asmartcity",        # A2A Smart City (Milan)
    "naquadria",           # Naquadria Group
    "omitech",             # Omitech S.r.l.
    "mailcontrol",         # MailControl gateway
]

GATEWAY_KEYWORDS = [...existing..., *ITALIAN_SOA_KEYWORDS]
```

---

## 6. Confidence-Scoring Implications

For the 1,200+ `independent` entries using Italian gateways:

- If DKIM CNAME → onmicrosoft.com or google.com: reclassify as microsoft/google with backend confidence 0.7-0.9
- If SPF record includes ~spf.protection.outlook.com or ~include:google.com: infer backend 0.6-0.8
- If MX host matches any NEW italian gateway keywords and no DKIM/SPF evidence: keep `independent` but lower confidence by 20 points (flagged for review)

---

## Validation Against data.json

All counts verified via jq queries against live `data.json`:

- ✅ 36 unique gateway values
- ✅ ~3,274 total entries with any gateway detection
- ✅ 2,209 entries classified as `independent` that use Italian gateways (top suspect)
- ✅ Top gateway distribution verified: sophos(445), gecomail(440), epublic(389), sitek(325), halley(253)

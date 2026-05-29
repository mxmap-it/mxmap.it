"""Validator: is a scraped email domain legitimately associated with an
IndicePA entity?

Used by postprocess.process_unknown() and scripts/finalize_it_unknowns.py
to prevent the cross-tenant misattribution bug where scraping the website
of entity A finds an email referenced for entity B (event partner,
footer, hosted municipality, etc.) and the recovery code blindly
assigns B's MX to A.

Default verdict: REJECT. Only accept on positive signal that the
scraped domain genuinely belongs to / is operated for the entity.

Acceptance order:
  1. Exact match (scraped == ente_domain)
  2. Hand-verified manual override (codice_ipa -> domain mapping)
  3. PA-shared infrastructure whitelist (Lepida, ARIA, RUPAR, ASMEL, ...)
  4. Meaningful-label intersection (after stripping TLDs / Italian
     2-letter province codes / generic prefixes like "comune", "mail")
  5. PEC-host hard reject

Returns (is_legit: bool, reason: str). The reason is logged for audit
so that false negatives (e.g. hyphenation typos) can be promoted to
the manual override layer.
"""

from __future__ import annotations

# 2-letter Italian province codes used as 3rd-level subdomains
# (e.g. comune.roccagorga.lt.it). Source: ISTAT, all 110.
_ITALIAN_PROVINCE_CODES = {
    "ag",
    "al",
    "an",
    "ao",
    "ap",
    "aq",
    "ar",
    "at",
    "av",
    "ba",
    "bg",
    "bi",
    "bl",
    "bn",
    "bo",
    "br",
    "bs",
    "bt",
    "bz",
    "ca",
    "cb",
    "ce",
    "ch",
    "cl",
    "cn",
    "co",
    "cr",
    "cs",
    "ct",
    "cz",
    "en",
    "fc",
    "fe",
    "fg",
    "fi",
    "fm",
    "fr",
    "ge",
    "go",
    "gr",
    "im",
    "is",
    "kr",
    "lc",
    "le",
    "li",
    "lo",
    "lt",
    "lu",
    "mb",
    "mc",
    "me",
    "mi",
    "mn",
    "mo",
    "ms",
    "mt",
    "na",
    "no",
    "nu",
    "og",
    "or",
    "ot",
    "pa",
    "pc",
    "pd",
    "pe",
    "pg",
    "pi",
    "pn",
    "po",
    "pr",
    "pt",
    "pu",
    "pv",
    "pz",
    "ra",
    "rc",
    "re",
    "rg",
    "ri",
    "rm",
    "rn",
    "ro",
    "sa",
    "si",
    "so",
    "sp",
    "sr",
    "ss",
    "su",
    "sv",
    "ta",
    "te",
    "tn",
    "to",
    "tp",
    "tr",
    "ts",
    "tv",
    "ud",
    "va",
    "vb",
    "vc",
    "ve",
    "vi",
    "vr",
    "vs",
    "vt",
    "vv",
}

# Top-level / public-suffix labels we strip when comparing domain
# "core identity". Anything in this set is noise.
_NOISE_TLDS = {
    "it",
    "eu",
    "com",
    "org",
    "net",
    "gov",
    "edu",
    "co",
    "ac",
    "or",
    "info",
    "biz",
    "name",
}

# Generic structural prefixes that don't carry organizational identity.
_NOISE_PREFIXES = {
    "comune",
    "comuni",
    "comunedi",
    "comune-di",
    "provincia",
    "provincie",
    "regione",
    "asl",
    "ats",
    "azienda",
    "ausl",
    "aoo",
    "aos",
    "ato",
    "consorzio",
    "unione",
    "mail",
    "webmail",
    "posta",
    "cert",
    "pec",
    "smtp",
    "mx",
    "imap",
    "pop3",
    "in",
    "out",
    "spf",
    "dkim",
    "www",
    "wwww",
    "official",
    "sito",
    "site",
    "m",
    "m1",
    "m2",
    "m3",
    "ns",
    "ns1",
    "ns2",
    "protocollo",
    "ufficio",
    "uffici",
    "servizi",
    "servizio",
    "amministrazione",
    "transparenz",
    "rest",
    "api",
    "online",
}

NOISE_LABELS = _NOISE_TLDS | _ITALIAN_PROVINCE_CODES | _NOISE_PREFIXES

# PA-shared infrastructure — split into two scopes to prevent the
# "regione.vda.it accepted for Min Interno" class of bug.
#
# NATIONAL: cross-PA platforms with no jurisdictional restriction
# (research network, national consortia of comuni). Accepted for any
# Italian PA regardless of geography or category.
PA_SHARED_PLATFORMS_NATIONAL = {
    "garr.it",  # research network
    "sogei.it",  # state IT (MEF/AdE et al.)
    "asmel.it",
    "asmenet.it",
    "asmecal.it",
    "asmecam.it",  # comune consortia
}

# LOCAL-ONLY: platforms operated BY a regional/provincial entity FOR
# the local PAs in its jurisdiction. Each maps to its region key. The
# ente is accepted only when (a) it looks like a local PA, AND (b) it
# resides in that region (province code or region label in domain).
PA_SHARED_PLATFORMS_LOCAL_BY_REGION = {
    # Regional in-house IT
    "lepida.it": "emilia-romagna",
    "lepida.net": "emilia-romagna",
    "ariaspa.it": "lombardia",
    "aria.lombardia.it": "lombardia",
    "ruparpiemonte.it": "piemonte",
    "csi.it": "piemonte",
    "insiel.it": "friuli-venezia-giulia",
    "insiel.net": "friuli-venezia-giulia",
    "regione.emilia-romagna.it": "emilia-romagna",
    "regione.lombardia.it": "lombardia",
    "regione.toscana.it": "toscana",
    "regione.liguria.it": "liguria",
    "regione.veneto.it": "veneto",
    "regione.lazio.it": "lazio",
    "regione.campania.it": "campania",
    "regione.sardegna.it": "sardegna",
    "regione.fvg.it": "friuli-venezia-giulia",
    "regione.marche.it": "marche",
    "regione.umbria.it": "umbria",
    "regione.abruzzo.it": "abruzzo",
    "regione.molise.it": "molise",
    "regione.basilicata.it": "basilicata",
    "regione.calabria.it": "calabria",
    "regione.sicilia.it": "sicilia",
    "regione.puglia.it": "puglia",
    "regione.vda.it": "valle-d-aosta",
    # South Tyrol Gemeindenverband + schools
    "gvcc.net": "bolzano",
    "schule.suedtirol.it": "bolzano",
    "scuola.alto-adige.it": "bolzano",
    # Trentino IT Exchange
    "tix.it": "trento",
}
PA_SHARED_PLATFORMS_LOCAL_ONLY = set(PA_SHARED_PLATFORMS_LOCAL_BY_REGION)

# Province codes (lowercase ISO 3166-2:IT minus the IT- prefix) per region.
# Used to test "is this ente in the platform's region?".
REGION_PROVINCES: dict[str, set[str]] = {
    "piemonte": {"al", "at", "bi", "cn", "no", "to", "vb", "vc"},
    "valle-d-aosta": {"ao", "vda", "aosta"},
    "lombardia": {
        "bg",
        "bs",
        "co",
        "cr",
        "lc",
        "lo",
        "mn",
        "mi",
        "mb",
        "pv",
        "so",
        "va",
    },
    "trentino-alto-adige": {"tn", "bz"},
    "trento": {"tn"},
    "bolzano": {"bz", "suedtirol", "alto-adige", "altoadige"},
    "veneto": {"bl", "pd", "ro", "tv", "ve", "vi", "vr"},
    "friuli-venezia-giulia": {"go", "pn", "ts", "ud", "fvg"},
    "liguria": {"ge", "im", "sp", "sv"},
    "emilia-romagna": {"bo", "fc", "fe", "mo", "pc", "pr", "ra", "re", "rn"},
    "toscana": {"ar", "fi", "gr", "li", "lu", "ms", "pi", "po", "pt", "si"},
    "umbria": {"pg", "tr"},
    "marche": {"an", "ap", "fm", "mc", "pu"},
    "lazio": {"fr", "lt", "ri", "rm", "vt"},
    "abruzzo": {"aq", "ch", "pe", "te"},
    "molise": {"cb", "is"},
    "campania": {"av", "bn", "ce", "na", "sa"},
    "puglia": {"ba", "br", "bt", "fg", "le", "ta"},
    "basilicata": {"mt", "pz"},
    "calabria": {"cs", "cz", "kr", "rc", "vv"},
    "sicilia": {"ag", "cl", "ct", "en", "me", "pa", "rg", "sr", "tp"},
    "sardegna": {
        "ca",
        "ci",
        "nu",
        "or",
        "og",
        "ot",
        "ss",
        "su",
        "vs",
        "md",
        "sardegna",
    },
}

# Back-compat alias
PA_SHARED_PLATFORMS = PA_SHARED_PLATFORMS_NATIONAL | PA_SHARED_PLATFORMS_LOCAL_ONLY

# Markers that indicate "this domain belongs to a local Italian PA"
# (comune / provincia / regione / health authority / consortium / etc.)
LOCAL_PA_DOMAIN_MARKERS = {
    "comune",
    "comuni",
    "comunedi",
    "comune-di",
    "citta-metropolitana",
    "cittametropolitana",
    "provincia",
    "provincie",
    "regione",
    "asl",
    "ausl",
    "asp",
    "ats",
    "ato",
    "aoo",
    "consorzio",
    "unione",
    "gemeindenverband",
    "gvcc",
}

# PEC providers — by mxmap policy, never the basis for classification.
PEC_PROVIDERS = {
    "pec.it",
    "legalmail.it",
    "postecert.it",
    "arubapec.it",
    "aruba.it",
    "asmepec.it",
    "notariato.it",
    "pec.aruba.it",
    "kpec.it",
    "namirial.it",
    "namirialtsp.it",
    "sicurezzapostale.it",
    "fnofi.it",
    "conafpec.it",
    "ingpec.eu",
    "epap.sicurezzapostale.it",
    "pa.postecert.it",
}


def _domain_endswith(host: str, base: str) -> bool:
    """True if host == base or host has base as a strict suffix component."""
    return host == base or host.endswith("." + base)


# Provincia → capoluogo name → province-code (lowercase, no spaces).
# Used to resolve domains like comune.bologna.it (no province label) into
# their region. 107 capoluoghi (the 110 minus duplicates from BAT).
CAPOLUOGO_PROVINCE = {
    # Piemonte
    "torino": "to",
    "alessandria": "al",
    "asti": "at",
    "biella": "bi",
    "cuneo": "cn",
    "novara": "no",
    "verbania": "vb",
    "vercelli": "vc",
    # Valle d'Aosta
    "aosta": "ao",
    # Lombardia
    "milano": "mi",
    "bergamo": "bg",
    "brescia": "bs",
    "como": "co",
    "cremona": "cr",
    "lecco": "lc",
    "lodi": "lo",
    "mantova": "mn",
    "monza": "mb",
    "pavia": "pv",
    "sondrio": "so",
    "varese": "va",
    # Trentino-Alto Adige / Sudtirol
    "trento": "tn",
    "bolzano": "bz",
    "bozen": "bz",
    # Veneto
    "venezia": "ve",
    "belluno": "bl",
    "padova": "pd",
    "rovigo": "ro",
    "treviso": "tv",
    "verona": "vr",
    "vicenza": "vi",
    # FVG
    "trieste": "ts",
    "gorizia": "go",
    "pordenone": "pn",
    "udine": "ud",
    # Liguria
    "genova": "ge",
    "imperia": "im",
    "laspezia": "sp",
    "spezia": "sp",
    "savona": "sv",
    # Emilia-Romagna
    "bologna": "bo",
    "ferrara": "fe",
    "forli": "fc",
    "modena": "mo",
    "piacenza": "pc",
    "parma": "pr",
    "ravenna": "ra",
    "reggioemilia": "re",
    "rimini": "rn",
    # Toscana
    "firenze": "fi",
    "arezzo": "ar",
    "grosseto": "gr",
    "livorno": "li",
    "lucca": "lu",
    "massa": "ms",
    "pisa": "pi",
    "prato": "po",
    "pistoia": "pt",
    "siena": "si",
    # Umbria
    "perugia": "pg",
    "terni": "tr",
    # Marche
    "ancona": "an",
    "ascolipiceno": "ap",
    "fermo": "fm",
    "macerata": "mc",
    "pesaro": "pu",
    # Lazio
    "roma": "rm",
    "frosinone": "fr",
    "latina": "lt",
    "rieti": "ri",
    "viterbo": "vt",
    # Abruzzo
    "laquila": "aq",
    "chieti": "ch",
    "pescara": "pe",
    "teramo": "te",
    # Molise
    "campobasso": "cb",
    "isernia": "is",
    # Campania
    "napoli": "na",
    "avellino": "av",
    "benevento": "bn",
    "caserta": "ce",
    "salerno": "sa",
    # Puglia
    "bari": "ba",
    "brindisi": "br",
    "barletta": "bt",
    "foggia": "fg",
    "lecce": "le",
    "taranto": "ta",
    # Basilicata
    "potenza": "pz",
    "matera": "mt",
    # Calabria
    "catanzaro": "cz",
    "cosenza": "cs",
    "crotone": "kr",
    "reggiocalabria": "rc",
    "vibovalentia": "vv",
    # Sicilia
    "palermo": "pa",
    "agrigento": "ag",
    "caltanissetta": "cl",
    "catania": "ct",
    "enna": "en",
    "messina": "me",
    "ragusa": "rg",
    "siracusa": "sr",
    "trapani": "tp",
    # Sardegna
    "cagliari": "ca",
    "nuoro": "nu",
    "oristano": "or",
    "sassari": "ss",
}


def _ente_in_region(ente_domain: str, region: str) -> bool:
    """True if `ente_domain` indicates the ente is in `region`. Checks
    (1) any label is a province code of that region; (2) the region key
    or an alias label is present; (3) any label is a known capoluogo
    whose province belongs to that region."""
    if not ente_domain or not region:
        return False
    parts = ente_domain.lower().split(".")
    markers = REGION_PROVINCES.get(region, set()) | {region}
    if any(p in markers for p in parts):
        return True
    region_provs = REGION_PROVINCES.get(region, set())
    for p in parts:
        prov = CAPOLUOGO_PROVINCE.get(p)
        if prov and prov in region_provs:
            return True
    return False


def is_local_pa_domain(d: str) -> bool:
    """True iff `d` looks like a local Italian PA (comune / provincia /
    regione / ASL / etc.). FALSE for national centrali / .gov.it
    ministries / reserved-namespace national bodies.

    This gates whether a regional PA-shared platform (e.g. lepida.it,
    regione.vda.it) may be accepted as legitimate infrastructure for
    the parent ente — preventing the bug where AOO records of a
    ministry exposed a regional sub-unit's email and the regional
    platform ended up whitelisted for the central ministry.
    """
    if not d:
        return False
    d = d.lower().strip().rstrip(".")
    # gov.it is reserved by AGID for national PA / ministries — never local.
    if d == "gov.it" or d.endswith(".gov.it"):
        return False
    parts = d.split(".")
    if any(p in LOCAL_PA_DOMAIN_MARKERS for p in parts):
        return True
    if any(p in _ITALIAN_PROVINCE_CODES for p in parts):
        return True
    return False


def _damerau_levenshtein(s1: str, s2: str) -> int:
    """Distanza Damerau-Levenshtein (sostituzione/inserimento/eliminazione/
    trasposizione adiacenti) — usata per la rule 6.5 fuzzy.
    """
    if s1 == s2:
        return 0
    len1, len2 = len(s1), len(s2)
    if not len1:
        return len2
    if not len2:
        return len1
    d = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    for i in range(len1 + 1):
        d[i][0] = i
    for j in range(len2 + 1):
        d[0][j] = j
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and s1[i - 1] == s2[j - 2] and s1[i - 2] == s2[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + cost)
    return d[len1][len2]


# Soglia conservativa fuzzy: 1 modifica (typo singolo, char extra/mancante,
# trasposizione adiacente). Solo su label di almeno 6 caratteri per evitare
# che parole brevi (es. "roma" / "noma") generino falsi positivi.
FUZZY_MAX_DISTANCE = 1
FUZZY_MIN_LEN = 6


def _label_concatenation_match(
    s_labels: set[str], e_labels: set[str]
) -> tuple[bool, str]:
    """Vero se un label significativo del candidato (lunghezza >= 5)
    CONTIENE come substring 2 o più label significativi dell'ente
    (ciascuno >= 3 caratteri), e la copertura totale (non sovrapposta)
    è >= 80% della lunghezza del label candidato.

    Cattura il pattern molto comune in IndicePA:
      seed (Sito_istituzionale): arezzo.aci.it  -> labels {arezzo, aci}
      candidato (email/scrape):  aciarezzo.it   -> label  {aciarezzo}
      → 'aciarezzo' contiene 'arezzo'+'aci' che coprono 9/9 caratteri (100%)
      → match.

    Non cattura coincidenze: 'comune.roma.it' (labels {roma}) vs 'somali.it'
    (labels {somali}) — 'somali' contiene 'roma' ? No (rom non si trova).
    Inoltre richiede 2+ label dell'ente, quindi single-label cross-tenant
    non passano (es. comune.roma.it vs interno.gov.it).
    """
    cand_labels = [lbl for lbl in s_labels if len(lbl) >= 5]
    ente_labels_lst = [lbl for lbl in e_labels if len(lbl) >= 3]
    if not cand_labels or len(ente_labels_lst) < 2:
        return False, ""
    for c in cand_labels:
        # trova tutti i label dell'ente presenti come substring in c
        covers = [e for e in ente_labels_lst if e in c]
        if len(covers) < 2:
            continue
        # ordina per lunghezza decrescente per coprire prima
        covers.sort(key=len, reverse=True)
        covered = [False] * len(c)
        used = []
        for e in covers:
            idx = c.find(e)
            if idx < 0:
                continue
            # accetta solo se la nuova substring non è completamente
            # già coperta (evita di contare "aci" dentro "aci-something")
            if all(covered[i] for i in range(idx, idx + len(e))):
                continue
            for i in range(idx, idx + len(e)):
                covered[i] = True
            used.append(e)
        if len(used) >= 2 and (sum(covered) / len(c)) >= 0.80:
            return True, f"{c}={'+'.join(used)}"
    return False, ""


def _fuzzy_label_match(s_labels: set[str], e_labels: set[str]) -> tuple[bool, str]:
    """True se esiste una coppia (lbl_s, lbl_e) con DL <= FUZZY_MAX_DISTANCE
    e entrambi i label di lunghezza >= FUZZY_MIN_LEN. Ritorna anche la
    coppia per audit/reason."""
    sl = {lbl for lbl in s_labels if len(lbl) >= FUZZY_MIN_LEN}
    el = {lbl for lbl in e_labels if len(lbl) >= FUZZY_MIN_LEN}
    if not sl or not el:
        return False, ""
    for a in sl:
        for b in el:
            if _damerau_levenshtein(a, b) <= FUZZY_MAX_DISTANCE:
                return True, f"{a}~{b}"
    return False, ""


def meaningful_labels(domain: str) -> set[str]:
    """Extract the identity-bearing labels of a domain.

    interno.gov.it           -> {'interno'}
    comune.roccagorga.lt.it  -> {'roccagorga'}
    mail.comune.padova.it    -> {'padova'}
    aslroma1.it              -> {'aslroma1'}
    interno.it               -> {'interno'}

    Length filter (>2) prevents 'tn' / 'mi' shorthand from being identity
    when they're really region/province codes that slipped through.
    """
    if not domain:
        return set()
    parts = domain.lower().split(".")
    return {p for p in parts if p not in NOISE_LABELS and len(p) > 2}


def is_legit_email_domain(
    scraped: str,
    ente_domain: str,
    *,
    codice_ipa: str | None = None,
    manual_overrides: dict | None = None,
) -> tuple[bool, str]:
    """Return (is_legit, reason).

    Conservative: returns False unless one of the positive signals fires.
    """
    if not scraped or not ente_domain:
        return False, "empty_input"
    s = scraped.lower().strip().rstrip(".")
    e = ente_domain.lower().strip().rstrip(".")

    # 1. Exact match
    if s == e:
        return True, "exact_match"

    # 2. PEC reject (hard)
    for pec in PEC_PROVIDERS:
        if _domain_endswith(s, pec):
            return False, f"pec_provider:{pec}"

    # 3. Hand-verified override match
    if codice_ipa and manual_overrides:
        ipa_l = codice_ipa.strip().lower()
        if manual_overrides.get(ipa_l) == s:
            return True, "manual_override"

    # 4a. PA-shared infrastructure (NATIONAL scope — accepted for any PA)
    for plat in PA_SHARED_PLATFORMS_NATIONAL:
        if _domain_endswith(s, plat):
            return True, f"pa_shared_national:{plat}"

    # 4b. PA-shared infrastructure (LOCAL-ONLY scope — only accepted
    #     when the ente is itself a local PA; reject for national
    #     centrali / ministries / .gov.it bodies). Falls through to
    #     subdomain / shared-label rules so the platform domain is
    #     still subject to identity matching when it doesn't apply.
    matched_local_plat = None
    for plat in PA_SHARED_PLATFORMS_LOCAL_ONLY:
        if _domain_endswith(s, plat):
            matched_local_plat = plat
            break
    if matched_local_plat:
        if is_local_pa_domain(e):
            # Local PA — the platform is offered to it; require region match.
            region = PA_SHARED_PLATFORMS_LOCAL_BY_REGION.get(matched_local_plat)
            if region and _ente_in_region(e, region):
                return True, f"pa_shared_local:{matched_local_plat}"
            # else: fall through — platform region doesn't match ente region.
        # else (national ente): fall through to remaining rules; if
        # none accept, this becomes a region-out-of-scope reject.

    # 5. Subdomain relationship (one is descendant of the other)
    if _domain_endswith(s, e) or _domain_endswith(e, s):
        return True, "subdomain_or_parent"

    # 6. Meaningful-label intersection
    s_labels = meaningful_labels(s)
    e_labels = meaningful_labels(e)
    common = s_labels & e_labels
    if common:
        return True, "shared_label:" + ",".join(sorted(common))

    # 6.5 Fuzzy match (Damerau-Levenshtein <= 1) sui label significativi
    #     lunghi almeno 6 caratteri. Cattura typo singoli (sostituzione,
    #     inserimento, cancellazione, trasposizione adiacente) come:
    #       consorfarm.it ↔ consofarm.it
    #       consorziolagodibracciano.it ↔ consorziolagodibraciano.it
    #     Conservativo: NON cattura coppie brevi (roma/noma) né distanze >1.
    fuzzy_ok, pair = _fuzzy_label_match(s_labels, e_labels)
    if fuzzy_ok:
        return True, f"fuzzy_match:{pair}"

    # 6.6 Label concatenation: un singolo label del candidato contiene
    #     2+ label dell'ente come substring, con copertura non-sovrapposta
    #     >= 80%. Cattura pattern come:
    #       arezzo.aci.it (ente) ↔ aciarezzo.it (candidato)
    #         → aciarezzo = arezzo + aci (cov 100%)
    #     Recupera ~16 enti C13/C14 (ACI provinciali + ordini professionali)
    #     che il pattern shared_label non trova perché un lato è un singolo
    #     label concatenato.
    concat_ok, concat_pair = _label_concatenation_match(s_labels, e_labels)
    if concat_ok:
        return True, f"label_concat:{concat_pair}"

    if matched_local_plat:
        return False, f"pa_shared_platform_out_of_scope:{matched_local_plat}"
    return False, "unrelated"


# Convenience for testing
__all__ = [
    "is_legit_email_domain",
    "meaningful_labels",
    "is_local_pa_domain",
    "NOISE_LABELS",
    "PA_SHARED_PLATFORMS",
    "PA_SHARED_PLATFORMS_NATIONAL",
    "PA_SHARED_PLATFORMS_LOCAL_ONLY",
    "PEC_PROVIDERS",
]

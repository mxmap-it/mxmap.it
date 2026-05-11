"""Canonical taxonomy of MX-discovery methods.

Every pipeline stage that lands MX records on an entry MUST set
`m["mx_discovery_method"]` (one of `METHODS`) and ideally
`m["mx_discovery_evidence"]` (short proof string). The frontend reads
these two fields to display "scoperto via X — Y" badges with tooltips
and a deep link to the methodology page.

Keep tags STABLE — they are public anchors on methodology.html.
"""
from __future__ import annotations

# (tag, italian_short_label, italian_tooltip)
METHODS: dict[str, tuple[str, str]] = {
    "seed_primary_mx": (
        "Dominio IndicePA (diretto)",
        "Il dominio del Sito_istituzionale dichiarato in IndicePA ha record MX validi. "
        "Nessun recupero necessario.",
    ),
    "domain_guess": (
        "Dominio dedotto dal nome",
        "L'ente non aveva dominio in IndicePA. Il dominio è stato generato dal nome "
        "(traslitterazione + TLD nazionale) e ha risolto MX.",
    ),
    "manual_override": (
        "Override manuale",
        "Dominio corretto a mano dal mantenitore del dataset (typo IndicePA, "
        "dominio defunto, migrazione *.gov.it ecc.). Vedi IT_MANUAL_DOMAIN_OVERRIDES.",
    ),
    "manual_llm_enrichment": (
        "Curatela LLM (revisione umana)",
        "Dominio proposto da una sessione LLM su prompt strutturato dei mantenitori, "
        "validato a mano e committato in data/manual_llm_enrichment.json.",
    ),
    "pec_only_enrichment": (
        "Enrichment PEC-only (Wikidata)",
        "Ente con solo PEC su IndicePA. Dominio recuperato da Wikidata (P856) "
        "e/o Wikipedia, verificato via MX.",
    ),
    "aoo_uo_tier6": (
        "AOO/UO IndicePA (Tier-6)",
        "Dominio non-PEC estratto dai record AOO (Aree Organizzative Omogenee) "
        "e UO (Unità Organizzative) di IndicePA, filtrato dal validatore "
        "is_legit_email_domain per evitare attribuzioni cross-ente.",
    ),
    "domain_fallback": (
        "Mail IndicePA non-PEC (fallback ente)",
        "Dominio derivato dai campi Mail1..5 del record IndicePA dell'ente "
        "(esclusa la PEC), validato da is_legit_email_domain.",
    ),
    "istruzione_miur_tenant": (
        "Tenant centrale MIM (istruzione.it)",
        "Scuola statale (categoria IndicePA L33): la posta dei dirigenti è "
        "ospitata sul tenant centrale del Ministero (miuristruzione.onmicrosoft.com), "
        "verificato crittograficamente via DKIM.",
    ),
    "wikidata_p856": (
        "Wikidata (P856 — sito ufficiale)",
        "Dominio corretto recuperato dalla proprietà P856 di Wikidata, indicizzato "
        "per codice ISTAT del comune. Cattura tipici typo IndicePA e migrazioni "
        "*.gov.it → comune.*.it.",
    ),
    "public_pec_inference": (
        "Inferenza da PEC pubblica (RUPAR/ASMEPEC)",
        "Ente con solo PEC su infrastruttura pubblica (cert.ruparpiemonte.it = "
        "CSI Piemonte, asmepec.it = consorzio comuni ASMEL). Classificato come "
        "regional-public senza necessità di MX proprio.",
    ),
    "homepage_scrape": (
        "Scraping sito istituzionale",
        "Email estratte dall'homepage / pagine contatti dell'ente, validate da "
        "is_legit_email_domain (default REJECT: solo domini esattamente collegati "
        "all'ente, condivisi via piattaforma PA o per label significative).",
    ),
    "search_engine_scrape": (
        "Ricerca DuckDuckGo + scraping",
        "Ricerca web per il nome dell'ente, candidati filtrati per dominio simile, "
        "scraping email e validazione is_legit. Ultima risorsa quando il dominio "
        "primario è defunto.",
    ),
    "smtp_banner": (
        "Banner SMTP",
        "Identificazione provider dal banner SMTP del primo MX (es. Postfix, "
        "Exchange, Plesk). Usato per enti su infrastruttura indipendente.",
    ),
    "unknown": (
        "Non risolto",
        "Nessuno dei percorsi di recupero ha prodotto un MX valido associabile "
        "all'ente nel rispetto delle regole del validatore. L'entità resta unknown "
        "per integrità — meglio non classificato che classificato male.",
    ),
}


def set_discovery(entry: dict, method: str, evidence: str | None = None) -> None:
    """Helper: set the canonical fields on an entry dict.

    `entry` is the per-municipality record in data.json.
    """
    if method not in METHODS:
        raise ValueError(f"unknown mx_discovery_method tag: {method!r}")
    entry["mx_discovery_method"] = method
    if evidence:
        entry["mx_discovery_evidence"] = evidence


def infer_method_from_entry(entry: dict) -> tuple[str, str | None]:
    """Backfill heuristic: infer (method, evidence) from existing fields on
    a data.json entry whose pipeline ran before this taxonomy existed.

    Order matters: most specific signals first.
    """
    if entry.get("miur_tenant_dependency"):
        return "istruzione_miur_tenant", "dkim:miuristruzione.onmicrosoft.com"
    src = (entry.get("domain_correction_source") or "").lower()
    if src == "indicepa_aoo_uo_tier6":
        return "aoo_uo_tier6", entry.get("domain_used")
    if src == "wikidata_p856":
        return "wikidata_p856", entry.get("domain_used")
    if src == "homepage_scrape_primary":
        return "homepage_scrape", entry.get("domain_used")
    if src == "search_engine":
        return "search_engine_scrape", entry.get("domain_used")
    if entry.get("public_pec_match"):
        return "public_pec_inference", entry.get("public_pec_match")
    if entry.get("scraped_email"):
        return "homepage_scrape", entry.get("scraped_email")
    if entry.get("recovery_legit_reason"):
        # recover_it_unknowns wrote a domain_fallback that passed is_legit
        return "domain_fallback", entry.get("domain_used")
    if entry.get("domain_used"):
        # generic recovery — best guess
        return "domain_fallback", entry["domain_used"]
    if entry.get("provider") == "unknown":
        return "unknown", None
    if entry.get("mx"):
        return "seed_primary_mx", entry.get("domain")
    return "unknown", None

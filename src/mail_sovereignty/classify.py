from mail_sovereignty.constants import (
    AWS_KEYWORDS,
    ELKDATA_KEYWORDS,
    FOREIGN_SENDER_KEYWORDS,
    GATEWAY_KEYWORDS,
    GOOGLE_KEYWORDS,
    TELIA_KEYWORDS,
    TET_KEYWORDS,
    YANDEX_KEYWORDS,
    ZONE_KEYWORDS,
    ZOHO_KEYWORDS,
    MICROSOFT_KEYWORDS,
    PROVIDER_KEYWORDS,
    SMTP_BANNER_KEYWORDS,
    LOCAL_ISP_ASNS,
    ARUBA_KEYWORDS,
    REGISTER_IT_KEYWORDS,
    SEEWEB_KEYWORDS,
    INFOCERT_KEYWORDS,
    NAMIRIAL_KEYWORDS,
    ITALIAN_REGIONAL_PUBLIC_KEYWORDS,
    ITALIAN_PA_CONTRACTOR_PRIVATE_KEYWORDS,
    ITALIAN_PROVIDER_ASN_OVERRIDES,
)


def classify_from_smtp_banner(banner: str, ehlo: str = "") -> str | None:
    """Classify provider from SMTP banner/EHLO. Returns provider or None."""
    if not banner and not ehlo:
        return None
    blob = f"{banner} {ehlo}".lower()
    for provider, keywords in SMTP_BANNER_KEYWORDS.items():
        if any(k in blob for k in keywords):
            return provider
    return None


def classify_from_autodiscover(autodiscover: dict[str, str] | None) -> str | None:
    """Classify provider from autodiscover DNS records."""
    if not autodiscover:
        return None
    blob = " ".join(autodiscover.values()).lower()
    for provider, keywords in PROVIDER_KEYWORDS.items():
        if any(k in blob for k in keywords):
            return provider
    return None


def detect_gateway(mx_records: list[str]) -> str | None:
    """Return gateway provider name if MX matches a known gateway, else None."""
    mx_blob = " ".join(mx_records).lower()
    for gateway, keywords in GATEWAY_KEYWORDS.items():
        if any(k in mx_blob for k in keywords):
            return gateway
    return None


def classify_from_dkim(dkim: dict[str, str] | None) -> str | None:
    """Classify provider from DKIM CNAME targets."""
    if not dkim:
        return None
    blob = " ".join(dkim.values()).lower()
    # Microsoft: selector1/2 -> *.onmicrosoft.com
    if "onmicrosoft.com" in blob:
        return "microsoft"
    # Google: google._domainkey -> *.googlemail.com or *.google.com
    if "google" in blob or "googlemail" in blob:
        return "google"
    for provider, keywords in PROVIDER_KEYWORDS.items():
        if any(k in blob for k in keywords):
            return provider
    return None


def _check_spf_for_provider(spf_blob: str) -> str | None:
    """Check an SPF blob for hyperscaler keywords, return provider or None."""
    for provider, keywords in PROVIDER_KEYWORDS.items():
        if any(k in spf_blob for k in keywords):
            return provider
    return None


def _check_spf_all(spf_record: str | None, resolved_spf: str | None) -> str | None:
    """Check raw and resolved SPF for a provider keyword."""
    spf_blob = (spf_record or "").lower()
    provider = _check_spf_for_provider(spf_blob)
    if not provider and resolved_spf:
        provider = _check_spf_for_provider(resolved_spf.lower())
    return provider


def classify_from_txt_verifications(
    txt_verifications: dict[str, str] | None,
) -> str | None:
    """Classify provider from TXT domain verification tokens.

    Only considers mail-hosting providers (microsoft, google).
    """
    if not txt_verifications:
        return None
    # MS= token proves a Microsoft 365 tenant exists
    if "microsoft" in txt_verifications:
        return "microsoft"
    # google-site-verification= proves Google Workspace
    if "google" in txt_verifications:
        return "google"
    return None


def classify(
    mx_records: list[str],
    spf_record: str | None,
    mx_cnames: dict[str, str] | None = None,
    mx_asns: set[int] | None = None,
    resolved_spf: str | None = None,
    autodiscover: dict[str, str] | None = None,
    dkim: dict[str, str] | None = None,
    txt_verifications: dict[str, str] | None = None,
    tenant: str | None = None,
) -> tuple[str, str]:
    """Classify email provider based on MX, CNAME targets, SPF, autodiscover, and DKIM.

    Returns (provider, reason) where reason explains the classification decision.

    Classification order:
    1. MX hostname matches a known provider directly
    2. CNAME of MX host resolves to a known provider
    3. MX is a known gateway (spam filter) → check SPF/autodiscover/DKIM for backend
    4. MX exists but unrecognized → check DKIM, then independent or Local ISP (by ASN)
    5. No MX → unknown
    """
    mx_blob = " ".join(mx_records).lower()
    mx_display = ", ".join(mx_records[:2])

    # 1. Direct MX hostname match
    # Italian providers and aruba/register-it act like Telia: many comuni
    # land on them as MX yet sign DKIM via a hyperscaler tenant (hybrid
    # setups). Treat them as "local providers" so DKIM look-through fires.
    local_providers = {
        "zone",
        "telia",
        "tet",
        "elkdata",
        "yandex",
        "aruba",
        "register-it",
        "seeweb",
        "infocert",
        "namirial",
        "regional-public",
        "pa-contractor-private",
    }
    for provider, keywords, label in [
        ("microsoft", MICROSOFT_KEYWORDS, "Microsoft"),
        ("google", GOOGLE_KEYWORDS, "Google"),
        ("zone", ZONE_KEYWORDS, "Zone.eu"),
        ("telia", TELIA_KEYWORDS, "Telia"),
        ("tet", TET_KEYWORDS, "TET"),
        ("aws", AWS_KEYWORDS, "AWS"),
        ("zoho", ZOHO_KEYWORDS, "Zoho"),
        ("elkdata", ELKDATA_KEYWORDS, "Elkdata"),
        ("yandex", YANDEX_KEYWORDS, "Yandex"),
        # Italian providers (mxmap.it Phase 3)
        ("aruba", ARUBA_KEYWORDS, "Aruba"),
        ("register-it", REGISTER_IT_KEYWORDS, "Register.it"),
        ("seeweb", SEEWEB_KEYWORDS, "Seeweb"),
        ("infocert", INFOCERT_KEYWORDS, "InfoCert"),
        ("namirial", NAMIRIAL_KEYWORDS, "Namirial"),
        (
            "regional-public",
            ITALIAN_REGIONAL_PUBLIC_KEYWORDS,
            "Italian regional public ICT",
        ),
        (
            "pa-contractor-private",
            ITALIAN_PA_CONTRACTOR_PRIVATE_KEYWORDS,
            "Italian private PA contractor",
        ),
    ]:
        if any(k in mx_blob for k in keywords):
            # For local providers, DKIM may reveal a cloud backend
            # (e.g., Telia MX relaying to Microsoft 365; comune on Aruba MX
            # but DKIM signed via *.onmicrosoft.com)
            if provider in local_providers:
                dkim_provider = classify_from_dkim(dkim)
                if dkim_provider and dkim_provider not in local_providers:
                    return dkim_provider, (
                        f"MX ({mx_display}) via {label}; "
                        f"DKIM reveals {dkim_provider} backend"
                    )
            return provider, f"MX record ({mx_display}) matches {label}"

    # 2. CNAME resolution of MX hosts
    if mx_records and mx_cnames:
        cname_blob = " ".join(mx_cnames.values()).lower()
        for provider, keywords, label in [
            ("microsoft", MICROSOFT_KEYWORDS, "Microsoft"),
            ("google", GOOGLE_KEYWORDS, "Google"),
            ("zone", ZONE_KEYWORDS, "Zone.eu"),
            ("telia", TELIA_KEYWORDS, "Telia"),
            ("tet", TET_KEYWORDS, "TET"),
            ("aws", AWS_KEYWORDS, "AWS"),
            ("elkdata", ELKDATA_KEYWORDS, "Elkdata"),
            ("aruba", ARUBA_KEYWORDS, "Aruba"),
            ("register-it", REGISTER_IT_KEYWORDS, "Register.it"),
            ("seeweb", SEEWEB_KEYWORDS, "Seeweb"),
            ("infocert", INFOCERT_KEYWORDS, "InfoCert"),
            ("namirial", NAMIRIAL_KEYWORDS, "Namirial"),
            (
                "regional-public",
                ITALIAN_REGIONAL_PUBLIC_KEYWORDS,
                "Italian regional public ICT",
            ),
            (
                "pa-contractor-private",
                ITALIAN_PA_CONTRACTOR_PRIVATE_KEYWORDS,
                "Italian private PA contractor",
            ),
        ]:
            if any(k in cname_blob for k in keywords):
                cname_target = next(iter(mx_cnames.values()), "?")
                return provider, f"MX CNAME ({cname_target}) resolves to {label}"

    # 3. Known email gateway → look through to backend provider
    gateway = detect_gateway(mx_records) if mx_records else None
    if gateway:
        # Only trust SPF if exactly one main provider is found in the
        # DIRECT SPF record (not resolved). Resolved SPF follows transitive
        # includes from third-party services (e.g., ekom21 → Microsoft)
        # which don't prove the municipality itself uses that provider.
        spf_blob = (spf_record or "").lower()
        spf_providers = set()
        for prov, keywords in PROVIDER_KEYWORDS.items():
            if any(k in spf_blob for k in keywords):
                spf_providers.add(prov)
        if len(spf_providers) == 1:
            spf_provider = next(iter(spf_providers))
            # SPF behind a gateway is only trusted if corroborated by
            # autodiscover or DKIM. SPF alone just means "authorized to send",
            # not "hosts the mailbox" — many German municipalities include
            # spf.protection.outlook.com for calendar sharing or hybrid use.
            ad_provider = classify_from_autodiscover(autodiscover)
            dkim_provider = classify_from_dkim(dkim)
            if ad_provider == spf_provider or dkim_provider == spf_provider:
                return spf_provider, (
                    f"MX is {gateway} gateway; SPF+{'DKIM' if dkim_provider == spf_provider else 'autodiscover'} confirm {spf_provider}"
                )
            if ad_provider:
                return ad_provider, (
                    f"MX is {gateway} gateway; autodiscover points to {ad_provider}"
                )
            if dkim_provider:
                return dkim_provider, (
                    f"MX is {gateway} gateway; DKIM signs via {dkim_provider}"
                )
            # SPF-only behind gateway — not definitive, fall through
        ad_provider = classify_from_autodiscover(autodiscover)
        if ad_provider:
            return ad_provider, (
                f"MX is {gateway} gateway; autodiscover points to {ad_provider}"
            )
        dkim_provider = classify_from_dkim(dkim)
        if dkim_provider:
            return dkim_provider, (
                f"MX is {gateway} gateway; DKIM signs via {dkim_provider}"
            )
        # TXT verification tokens as last resort for gateways
        txt_provider = classify_from_txt_verifications(txt_verifications)
        if txt_provider:
            return txt_provider, (
                f"MX is {gateway} gateway; TXT verification proves {txt_provider} tenant"
            )
        # MS365 tenant detection via getuserrealm.srf
        if tenant:
            return "microsoft", (
                f"MX is {gateway} gateway; MS365 tenant detected ({tenant})"
            )
        # Gateway relays to unknown backend
        return "independent", (f"MX is {gateway} gateway; backend provider unknown")

    # 4. MX exists but no direct provider match → check DKIM for hidden
    #    backend (self-hosted gateway pattern), then Local ISP, then independent
    #    Note: SPF is NOT used here — SPF only indicates send authorization,
    #    not where mailboxes are hosted. Many ISP-hosted municipalities have
    #    SPF includes for Outlook (shared calendars, etc.) without using it
    #    for mail hosting. DKIM CNAMEs are specific to the actual mail host.
    if mx_records:
        # Check if DKIM reveals a backend provider (self-hosted gateway)
        if not gateway:
            dkim_provider = classify_from_dkim(dkim)
            if dkim_provider:
                return dkim_provider, (
                    f"MX ({mx_display}) is local gateway; "
                    f"DKIM reveals {dkim_provider} backend"
                )

        # 4b. Italian-provider ASN override — when MX is on a known Italian
        # provider's AS but the hostname didn't match the keyword (custom
        # subdomains like mail.comune.foo.it on Aruba AS31034). Apply BEFORE
        # the generic local-isp classification so we get a specific label.
        if mx_asns:
            for asn in sorted(mx_asns):
                if asn in ITALIAN_PROVIDER_ASN_OVERRIDES:
                    provider = ITALIAN_PROVIDER_ASN_OVERRIDES[asn]
                    return provider, (
                        f"MX ({mx_display}) on AS{asn} ({LOCAL_ISP_ASNS.get(asn, '?')}) "
                        f"-> {provider} (ASN-based override)"
                    )

        is_local_isp = bool(mx_asns and mx_asns & LOCAL_ISP_ASNS.keys())

        if is_local_isp:
            asn_names = [
                LOCAL_ISP_ASNS[a] for a in sorted(mx_asns & LOCAL_ISP_ASNS.keys())
            ]
            return "local-isp", (
                f"MX ({mx_display}) hosted on Local ISP ({', '.join(asn_names)})"
            )

        return "independent", (f"MX ({mx_display}) is self-hosted")

    # 5. No MX → unknown
    return "unknown", "No MX records found"


def classify_from_mx(mx_records: list[str]) -> str | None:
    """Classify provider from MX records alone."""
    if not mx_records:
        return None
    blob = " ".join(mx_records).lower()
    for provider, keywords in PROVIDER_KEYWORDS.items():
        if any(k in blob for k in keywords):
            return provider
    return "independent"


def classify_from_spf(spf_record: str | None) -> str | None:
    """Classify provider from SPF record alone."""
    if not spf_record:
        return None
    blob = spf_record.lower()
    for provider, keywords in PROVIDER_KEYWORDS.items():
        if any(k in blob for k in keywords):
            return provider
    return None


def spf_mentions_providers(spf_record: str | None) -> set[str]:
    """Return set of providers mentioned in SPF (main + foreign senders)."""
    if not spf_record:
        return set()
    blob = spf_record.lower()
    found = set()
    for provider, keywords in PROVIDER_KEYWORDS.items():
        if any(k in blob for k in keywords):
            found.add(provider)
    for provider, keywords in FOREIGN_SENDER_KEYWORDS.items():
        if any(k in blob for k in keywords):
            found.add(provider)
    return found

from mail_sovereignty.constants import (
    MICROSOFT_KEYWORDS,
    GOOGLE_KEYWORDS,
    AWS_KEYWORDS,
    ZONE_KEYWORDS,
    TELIA_KEYWORDS,
    TET_KEYWORDS,
    PROVIDER_KEYWORDS,
    FOREIGN_SENDER_KEYWORDS,
    SKIP_DOMAINS,
    LOCAL_ISP_ASNS,
    GATEWAY_KEYWORDS,
    GATEWAY_CATEGORIES,
    GATEWAY_CATEGORY_SECURITY,
    GATEWAY_CATEGORY_VENDOR,
    _SECURITY_GATEWAYS,
    _VENDOR_RELAY_GATEWAYS,
)


def test_keyword_lists_non_empty():
    assert MICROSOFT_KEYWORDS
    assert GOOGLE_KEYWORDS
    assert AWS_KEYWORDS
    assert ZONE_KEYWORDS
    assert TELIA_KEYWORDS
    assert TET_KEYWORDS


def test_provider_keywords_has_all_providers():
    # Baltic-era providers (fork mxmap.ch) + Italian fork additions.
    # Se aggiungi un provider in PROVIDER_KEYWORDS, aggiornalo anche qui.
    assert set(PROVIDER_KEYWORDS.keys()) == {
        # Baltic-era
        "microsoft",
        "google",
        "aws",
        "zoho",
        "yandex",
        "zone",
        "telia",
        "tet",
        "elkdata",
        # Italian commercial providers
        "aruba",
        "register-it",
        "seeweb",
        "infocert",
        "namirial",
        # Italian public/regional/contractor
        "regional-public",
        "pa-contractor-private",
        # Italian commercial ISPs (AIIP)
        "local-isp",
        # European non-Italian providers (eu_non_it bucket, #21)
        "ovh",
        "hetzner",
        "ionos",
        "scaleway",
        "gandi",
        "infomaniak",
    }


def test_foreign_sender_keywords_non_empty():
    assert FOREIGN_SENDER_KEYWORDS
    assert "mailchimp" in FOREIGN_SENDER_KEYWORDS
    assert "sendgrid" in FOREIGN_SENDER_KEYWORDS
    assert "smtp2go" in FOREIGN_SENDER_KEYWORDS
    assert "nl2go" in FOREIGN_SENDER_KEYWORDS
    assert "hubspot" in FOREIGN_SENDER_KEYWORDS
    assert "knowbe4" in FOREIGN_SENDER_KEYWORDS
    assert "hornetsecurity" in FOREIGN_SENDER_KEYWORDS
    assert set(FOREIGN_SENDER_KEYWORDS.keys()).isdisjoint(set(PROVIDER_KEYWORDS.keys()))


def test_skip_domains_contains_expected():
    assert "example.com" in SKIP_DOMAINS
    assert "sentry.io" in SKIP_DOMAINS
    assert "schema.org" in SKIP_DOMAINS


def test_local_isp_asns_contains_key_providers():
    assert 3249 in LOCAL_ISP_ASNS  # Telia
    assert 5518 in LOCAL_ISP_ASNS  # TET
    assert 2586 in LOCAL_ISP_ASNS  # Elisa
    assert 13194 in LOCAL_ISP_ASNS  # Bite


def test_local_isp_asns_minimum_count():
    assert len(LOCAL_ISP_ASNS) >= 10


# ── Categorie gateway (mxmap.it#28) ─────────────────────────────────────────
# La Ricerca Ente distingue security gateway (antispam) da vendor/relay
# (fornitore informatico): ogni firma di GATEWAY_KEYWORDS deve avere una
# categoria ESPLICITA, scelta a mano quando la firma viene aggiunta.


def test_gateway_categories_cover_every_keyword():
    missing = set(GATEWAY_KEYWORDS) - set(GATEWAY_CATEGORIES)
    extra = set(GATEWAY_CATEGORIES) - set(GATEWAY_KEYWORDS)
    assert not missing, f"firme gateway senza categoria: {sorted(missing)}"
    assert not extra, f"categorie per firme inesistenti: {sorted(extra)}"


def test_gateway_categories_are_disjoint_and_valid():
    overlap = _SECURITY_GATEWAYS & _VENDOR_RELAY_GATEWAYS
    assert not overlap, f"firme in entrambe le categorie: {sorted(overlap)}"
    assert set(GATEWAY_CATEGORIES.values()) == {
        GATEWAY_CATEGORY_SECURITY,
        GATEWAY_CATEGORY_VENDOR,
    }


def test_gateway_categories_known_anchors():
    # ancore note: se qualcuno riclassifica per sbaglio, il test parla chiaro
    for sec in ("sophos", "libraesva", "proofpoint", "trendmicro", "mimecast"):
        assert GATEWAY_CATEGORIES[sec] == GATEWAY_CATEGORY_SECURITY, sec
    for ven in ("halley", "gecomail", "epublic", "host-it", "vianova"):
        assert GATEWAY_CATEGORIES[ven] == GATEWAY_CATEGORY_VENDOR, ven

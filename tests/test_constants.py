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

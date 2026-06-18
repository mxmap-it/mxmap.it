from mail_sovereignty.classify import (
    classify,
    classify_from_autodiscover,
    classify_from_mx,
    classify_from_smtp_banner,
    classify_from_spf,
    classify_from_txt_verifications,
    detect_gateway,
    spf_mentions_providers,
)


def provider(result):
    """Extract provider from classify() return tuple."""
    return result[0]


def reason(result):
    """Extract reason from classify() return tuple."""
    return result[1]


# ── classify() ──────────────────────────────────────────────────────


class TestClassify:
    def test_microsoft_mx(self):
        assert (
            provider(classify(["tallinn-ch.mail.protection.outlook.com"], ""))
            == "microsoft"
        )

    def test_google_mx(self):
        assert (
            provider(classify(["aspmx.l.google.com", "alt1.aspmx.l.google.com"], ""))
            == "google"
        )

    def test_zone_mx(self):
        assert provider(classify(["mxpool.zone.eu"], "")) == "zone"

    def test_zone_mx_zonemx(self):
        assert provider(classify(["zonemx.eu"], "")) == "zone"

    def test_telia_mx(self):
        assert provider(classify(["mail.telia.ee"], "")) == "telia"

    def test_tet_mx(self):
        assert provider(classify(["mail.tet.lv"], "")) == "tet"

    def test_aws_mx(self):
        assert provider(classify(["inbound-smtp.us-east-1.amazonaws.com"], "")) == "aws"

    def test_independent_mx(self):
        assert provider(classify(["mail.example.ee"], "")) == "independent"

    def test_no_mx_with_spf_stays_unknown(self):
        """SPF alone does not determine provider — MX is required."""
        assert (
            provider(classify([], "v=spf1 include:spf.protection.outlook.com -all"))
            == "unknown"
        )

    def test_no_mx_no_spf(self):
        assert provider(classify([], "")) == "unknown"

    def test_empty_string_mx_stays_unknown(self):
        # NULL MX (RFC 7505 ".") arriva come [''] (lista truthy): deve risultare
        # unknown, non "independent/self-hosted". mxmap.it#18.
        assert provider(classify([""], "")) == "unknown"
        assert provider(classify(["", "  "], "v=spf1 -all")) == "unknown"

    def test_independent_mx_with_microsoft_spf_stays_independent(self):
        """Self-hosted MX stays independent — SPF only means authorized sender."""
        result = classify(
            ["mail.tallinn.ee"],
            "v=spf1 include:spf.protection.outlook.com -all",
        )
        assert provider(result) == "independent"

    def test_independent_mx_without_provider_spf_stays_independent(self):
        """Self-hosted MX with no provider keywords in SPF → independent."""
        result = classify(
            ["mail.example.ee"],
            "v=spf1 ip4:1.2.3.4 -all",
        )
        assert provider(result) == "independent"

    def test_cname_detects_microsoft(self):
        result = classify(
            ["mail.example.ee"],
            "",
            mx_cnames={"mail.example.ee": "mail.protection.outlook.com"},
        )
        assert provider(result) == "microsoft"

    def test_cname_none_stays_independent(self):
        assert (
            provider(classify(["mail.example.ee"], "", mx_cnames=None)) == "independent"
        )

    def test_cname_empty_stays_independent(self):
        assert (
            provider(classify(["mail.example.ee"], "", mx_cnames={})) == "independent"
        )

    def test_direct_mx_takes_precedence_over_cname(self):
        result = classify(
            ["mail.protection.outlook.com"],
            "",
            mx_cnames={"mail.protection.outlook.com": "something.else.com"},
        )
        assert provider(result) == "microsoft"

    def test_local_isp_asn(self):
        result = classify(
            ["mail1.example.ee"],
            "",
            mx_asns={3249},
        )
        assert provider(result) == "local-isp"
        assert "Local ISP" in reason(result)

    def test_local_isp_does_not_override_hostname_match(self):
        result = classify(
            ["mail.protection.outlook.com"],
            "",
            mx_asns={3249},
        )
        assert provider(result) == "microsoft"

    def test_local_isp_does_not_override_cname_match(self):
        result = classify(
            ["mail.example.ee"],
            "",
            mx_cnames={"mail.example.ee": "mail.protection.outlook.com"},
            mx_asns={3249},
        )
        assert provider(result) == "microsoft"

    def test_local_isp_with_microsoft_spf_stays_local_isp(self):
        """Local ISP stays local-isp — SPF only means authorized sender."""
        result = classify(
            ["mail1.example.ee"],
            "v=spf1 include:spf.protection.outlook.com -all",
            mx_asns={3249},
        )
        assert provider(result) == "local-isp"

    def test_local_isp_with_autodiscover_stays_local_isp(self):
        """Local ISP stays local-isp even with autodiscover pointing elsewhere."""
        result = classify(
            ["mail1.example.ee"],
            "",
            mx_asns={3249},
            autodiscover={"autodiscover_cname": "autodiscover.outlook.com"},
        )
        assert provider(result) == "local-isp"

    def test_local_isp_without_spf_or_autodiscover_stays_local_isp(self):
        """Local ISP relay without any hyperscaler signals stays local-isp."""
        result = classify(
            ["mail1.example.ee"],
            "",
            mx_asns={3249},
            autodiscover=None,
        )
        assert provider(result) == "local-isp"

    def test_non_local_isp_asn_stays_independent(self):
        result = classify(
            ["mail.example.ee"],
            "",
            mx_asns={99999},
        )
        assert provider(result) == "independent"

    def test_empty_asns_stays_independent(self):
        result = classify(
            ["mail.example.ee"],
            "",
            mx_asns=set(),
        )
        assert provider(result) == "independent"

    # ── Gateway detection in classify() ──

    def test_seppmail_gateway_spf_plus_dkim_confirms_microsoft(self):
        result = classify(
            ["customer.seppmail.cloud"],
            "v=spf1 include:spf.protection.outlook.com -all",
            dkim={"selector1": "selector1-example._domainkey.tenant.onmicrosoft.com"},
        )
        assert provider(result) == "microsoft"

    def test_seppmail_gateway_spf_only_stays_independent(self):
        """SPF alone behind a gateway is not definitive."""
        result = classify(
            ["customer.seppmail.cloud"],
            "v=spf1 include:spf.protection.outlook.com -all",
        )
        assert provider(result) == "independent"

    def test_gateway_no_hyperscaler_spf_stays_independent(self):
        result = classify(
            ["filter.seppmail.cloud"],
            "v=spf1 ip4:1.2.3.4 -all",
        )
        assert provider(result) == "independent"

    def test_gateway_empty_spf_stays_independent(self):
        result = classify(
            ["filter.seppmail.cloud"],
            "",
        )
        assert provider(result) == "independent"

    def test_gateway_ignores_resolved_spf(self):
        # Resolved SPF can contain transitive includes from third-party
        # services (e.g., ekom21 → Microsoft) that don't prove the
        # municipality uses that provider. Only direct SPF is checked.
        result = classify(
            ["mx01.hornetsecurity.com"],
            "v=spf1 include:custom.ee -all",
            resolved_spf="v=spf1 include:custom.ee -all v=spf1 include:spf.protection.outlook.com -all",
        )
        assert provider(result) == "independent"

    def test_barracuda_gateway_spf_plus_autodiscover(self):
        result = classify(
            ["mail.barracudanetworks.com"],
            "v=spf1 include:spf.protection.outlook.com -all",
            autodiscover={"autodiscover_cname": "autodiscover.outlook.com"},
        )
        assert provider(result) == "microsoft"

    def test_trendmicro_gateway_with_aws_spf_plus_dkim(self):
        result = classify(
            ["filter.tmes.trendmicro.eu"],
            "v=spf1 include:amazonses.com -all",
            dkim={"selector1": "something.amazonses.com"},
        )
        assert provider(result) == "aws"

    def test_hornetsecurity_gateway_spf_plus_dkim(self):
        result = classify(
            ["mx01.hornetsecurity.com"],
            "v=spf1 include:spf.protection.outlook.com -all",
            dkim={"selector1": "selector1-x._domainkey.tenant.onmicrosoft.com"},
        )
        assert provider(result) == "microsoft"

    def test_proofpoint_gateway_spf_plus_dkim(self):
        result = classify(
            ["mx1.ppe-hosted.com"],
            "v=spf1 include:spf.protection.outlook.com -all",
            dkim={"selector1": "selector1-x._domainkey.tenant.onmicrosoft.com"},
        )
        assert provider(result) == "microsoft"

    def test_sophos_gateway_spf_plus_dkim(self):
        result = classify(
            ["mx.hydra.sophos.com"],
            "v=spf1 include:spf.protection.outlook.com -all",
            dkim={"selector1": "selector1-x._domainkey.tenant.onmicrosoft.com"},
        )
        assert provider(result) == "microsoft"

    def test_gateway_does_not_override_direct_mx_match(self):
        """If MX directly matches a provider, gateway check is skipped."""
        result = classify(
            ["mail.protection.outlook.com"],
            "v=spf1 include:_spf.google.com -all",
        )
        assert provider(result) == "microsoft"

    # ── Autodiscover in classify() ──

    def test_gateway_autodiscover_reveals_microsoft(self):
        result = classify(
            ["mx01.hornetsecurity.com"],
            "v=spf1 ip4:1.2.3.4 -all",
            autodiscover={"autodiscover_cname": "autodiscover.outlook.com"},
        )
        assert provider(result) == "microsoft"

    def test_gateway_autodiscover_reveals_google(self):
        result = classify(
            ["filter.seppmail.cloud"],
            "",
            autodiscover={"autodiscover_srv": "autodiscover.google.com"},
        )
        assert provider(result) == "google"

    def test_gateway_spf_uncorroborated_falls_to_autodiscover(self):
        """SPF says Google but autodiscover says Microsoft — autodiscover wins
        because SPF alone behind a gateway is not trusted."""
        result = classify(
            ["mx01.hornetsecurity.com"],
            "v=spf1 include:_spf.google.com -all",
            autodiscover={"autodiscover_cname": "autodiscover.outlook.com"},
        )
        assert provider(result) == "microsoft"

    def test_non_gateway_independent_ignores_autodiscover(self):
        """Non-gateway independent MX stays independent regardless of autodiscover."""
        result = classify(
            ["mail.example.ee"],
            "",
            autodiscover={"autodiscover_cname": "autodiscover.outlook.com"},
        )
        assert provider(result) == "independent"

    def test_non_gateway_independent_no_autodiscover_stays_independent(self):
        """Non-gateway independent MX without autodiscover stays independent."""
        result = classify(
            ["mail.example.ee"],
            "",
            autodiscover=None,
        )
        assert provider(result) == "independent"

    def test_gateway_empty_autodiscover_stays_independent(self):
        result = classify(
            ["filter.seppmail.cloud"],
            "",
            autodiscover={},
        )
        assert provider(result) == "independent"

    def test_gateway_autodiscover_none_stays_independent(self):
        result = classify(
            ["filter.seppmail.cloud"],
            "",
            autodiscover=None,
        )
        assert provider(result) == "independent"

    # ── No MX — SPF does not classify ──

    def test_no_mx_spf_resolved_stays_unknown(self):
        """No MX → unknown, even if resolved SPF has a provider."""
        result = classify(
            [],
            "v=spf1 include:custom.ee -all",
            resolved_spf="v=spf1 include:spf.protection.outlook.com -all",
        )
        assert provider(result) == "unknown"

    def test_no_mx_spf_google_stays_unknown(self):
        """No MX → unknown, even if raw SPF has Google."""
        result = classify(
            [],
            "v=spf1 include:_spf.google.com -all",
        )
        assert provider(result) == "unknown"

    def test_no_mx_no_spf_stays_unknown(self):
        """No MX, no meaningful SPF → unknown."""
        result = classify(
            [],
            "v=spf1 ip4:1.2.3.4 -all",
            resolved_spf=None,
        )
        assert provider(result) == "unknown"

    # ── Reason field ──

    def test_reason_included_in_result(self):
        _, r = classify(["mail.protection.outlook.com"], "")
        assert isinstance(r, str)
        assert len(r) > 0


# ── classify_from_autodiscover() ────────────────────────────────────


class TestClassifyFromAutodiscover:
    def test_none_returns_none(self):
        assert classify_from_autodiscover(None) is None

    def test_empty_dict_returns_none(self):
        assert classify_from_autodiscover({}) is None

    def test_microsoft_cname(self):
        assert (
            classify_from_autodiscover(
                {"autodiscover_cname": "autodiscover.outlook.com"}
            )
            == "microsoft"
        )

    def test_google_srv(self):
        assert (
            classify_from_autodiscover({"autodiscover_srv": "autodiscover.google.com"})
            == "google"
        )

    def test_unrecognized_returns_none(self):
        assert (
            classify_from_autodiscover(
                {"autodiscover_cname": "autodiscover.custom-host.ee"}
            )
            is None
        )


# ── detect_gateway() ────────────────────────────────────────────────


class TestDetectGateway:
    def test_seppmail(self):
        assert detect_gateway(["customer.seppmail.cloud"]) == "seppmail"

    def test_barracuda(self):
        assert detect_gateway(["mail.barracudanetworks.com"]) == "barracuda"

    def test_trendmicro(self):
        assert detect_gateway(["filter.tmes.trendmicro.eu"]) == "trendmicro"

    def test_hornetsecurity(self):
        assert detect_gateway(["mx01.hornetsecurity.com"]) == "hornetsecurity"

    def test_proofpoint(self):
        assert detect_gateway(["mx1.ppe-hosted.com"]) == "proofpoint"

    def test_sophos(self):
        assert detect_gateway(["mx.hydra.sophos.com"]) == "sophos"

    def test_no_gateway(self):
        assert detect_gateway(["mail.example.ee"]) is None

    def test_empty_list(self):
        assert detect_gateway([]) is None

    def test_case_insensitive(self):
        assert detect_gateway(["CUSTOMER.SEPPMAIL.CLOUD"]) == "seppmail"


# ── classify_from_mx() ──────────────────────────────────────────────


class TestClassifyFromMx:
    def test_empty_returns_none(self):
        assert classify_from_mx([]) is None

    def test_microsoft(self):
        assert classify_from_mx(["mail.protection.outlook.com"]) == "microsoft"

    def test_google(self):
        assert classify_from_mx(["aspmx.l.google.com"]) == "google"

    def test_unrecognized_returns_independent(self):
        assert classify_from_mx(["mail.custom.ee"]) == "independent"

    def test_case_insensitive(self):
        assert classify_from_mx(["MAIL.PROTECTION.OUTLOOK.COM"]) == "microsoft"


# ── classify_from_spf() ─────────────────────────────────────────────


class TestClassifyFromSpf:
    def test_empty_returns_none(self):
        assert classify_from_spf("") is None

    def test_none_returns_none(self):
        assert classify_from_spf(None) is None

    def test_microsoft(self):
        assert (
            classify_from_spf("v=spf1 include:spf.protection.outlook.com -all")
            == "microsoft"
        )

    def test_unrecognized_returns_none(self):
        assert classify_from_spf("v=spf1 include:custom.ee -all") is None


# ── spf_mentions_providers() ─────────────────────────────────────────


class TestSpfMentionsProviders:
    def test_empty_returns_empty(self):
        assert spf_mentions_providers("") == set()

    def test_single_provider(self):
        result = spf_mentions_providers(
            "v=spf1 include:spf.protection.outlook.com -all"
        )
        assert result == {"microsoft"}

    def test_multiple_providers(self):
        result = spf_mentions_providers(
            "v=spf1 include:spf.protection.outlook.com include:_spf.google.com -all"
        )
        assert result == {"microsoft", "google"}

    def test_detects_mailchimp(self):
        result = spf_mentions_providers(
            "v=spf1 include:servers.mcsv.net include:spf.mandrillapp.com -all"
        )
        assert "mailchimp" in result

    def test_detects_sendgrid(self):
        result = spf_mentions_providers("v=spf1 include:sendgrid.net -all")
        assert result == {"sendgrid"}

    def test_mixed_main_and_foreign(self):
        result = spf_mentions_providers(
            "v=spf1 include:spf.protection.outlook.com include:spf.mandrillapp.com -all"
        )
        assert result == {"microsoft", "mailchimp"}

    def test_detects_smtp2go(self):
        result = spf_mentions_providers("v=spf1 include:spf.smtp2go.com -all")
        assert "smtp2go" in result

    def test_detects_nl2go(self):
        result = spf_mentions_providers("v=spf1 include:spf.nl2go.com -all")
        assert "nl2go" in result

    def test_foreign_sender_not_in_classify(self):
        assert (
            provider(classify([], "v=spf1 include:spf.mandrillapp.com -all"))
            == "unknown"
        )

    def test_foreign_sender_not_in_classify_from_spf(self):
        assert classify_from_spf("v=spf1 include:spf.mandrillapp.com -all") is None


# ── classify_from_smtp_banner() ────────────────────────────────────


class TestClassifyFromSmtpBanner:
    def test_empty_returns_none(self):
        assert classify_from_smtp_banner("") is None

    def test_both_empty_returns_none(self):
        assert classify_from_smtp_banner("", "") is None

    def test_microsoft_banner(self):
        assert (
            classify_from_smtp_banner(
                "220 BL02EPF0001CA17.mail.protection.outlook.com "
                "Microsoft ESMTP MAIL Service ready"
            )
            == "microsoft"
        )

    def test_microsoft_outlook_com(self):
        assert (
            classify_from_smtp_banner("220 something.outlook.com ready") == "microsoft"
        )

    def test_google_banner(self):
        assert classify_from_smtp_banner("220 mx.google.com ESMTP ready") == "google"

    def test_google_esmtp_in_ehlo(self):
        assert (
            classify_from_smtp_banner("220 custom.example.ee", "250 Google ESMTP ready")
            == "google"
        )

    def test_zone_banner(self):
        assert classify_from_smtp_banner("220 mail.zone.eu ESMTP") == "zone"

    def test_telia_banner(self):
        assert classify_from_smtp_banner("220 mail.telia.ee ESMTP") == "telia"

    def test_aws_banner(self):
        assert (
            classify_from_smtp_banner("220 inbound-smtp.eu-west-1.amazonaws.com ESMTP")
            == "aws"
        )

    def test_postfix_returns_none(self):
        assert classify_from_smtp_banner("220 mail.example.ee ESMTP Postfix") is None

    def test_exim_returns_none(self):
        assert classify_from_smtp_banner("220 mail.example.ee ESMTP Exim 4.96") is None

    def test_case_insensitive(self):
        assert (
            classify_from_smtp_banner(
                "220 MAIL.PROTECTION.OUTLOOK.COM MICROSOFT ESMTP MAIL SERVICE"
            )
            == "microsoft"
        )


# ── classify_from_txt_verifications() ──────────────────────────────


class TestClassifyFromTxtVerifications:
    def test_none_returns_none(self):
        assert classify_from_txt_verifications(None) is None

    def test_empty_returns_none(self):
        assert classify_from_txt_verifications({}) is None

    def test_microsoft_token(self):
        assert (
            classify_from_txt_verifications({"microsoft": "ms77422356"}) == "microsoft"
        )

    def test_google_token(self):
        assert classify_from_txt_verifications({"google": "R9vBEx8..."}) == "google"

    def test_non_mail_provider_returns_none(self):
        """Tokens like apple, atlassian, facebook don't identify mail hosting."""
        assert classify_from_txt_verifications({"apple": "abc123"}) is None

    def test_microsoft_takes_precedence_over_google(self):
        """When both exist, microsoft wins (checked first)."""
        assert (
            classify_from_txt_verifications({"microsoft": "ms123", "google": "gv123"})
            == "microsoft"
        )


# ── TXT verification in classify() ────────────────────────────────


class TestClassifyTxtVerification:
    def test_gateway_txt_microsoft_when_dkim_absent(self):
        """Gateway with no DKIM/autodiscover but MS= token → microsoft."""
        result = classify(
            ["filter.seppmail.cloud"],
            "",
            txt_verifications={"microsoft": "ms77422356"},
        )
        assert provider(result) == "microsoft"
        assert "TXT verification" in reason(result)

    def test_gateway_txt_google_when_dkim_absent(self):
        """Gateway with google-site-verification → google."""
        result = classify(
            ["filter.seppmail.cloud"],
            "",
            txt_verifications={"google": "R9vBEx8abcdef"},
        )
        assert provider(result) == "google"

    def test_gateway_dkim_takes_precedence_over_txt(self):
        """DKIM is more reliable than TXT tokens — DKIM wins."""
        result = classify(
            ["filter.seppmail.cloud"],
            "",
            dkim={"selector1": "selector1-x._domainkey.tenant.onmicrosoft.com"},
            txt_verifications={"google": "gv123"},
        )
        assert provider(result) == "microsoft"
        assert "DKIM" in reason(result)

    def test_self_hosted_txt_stays_independent(self):
        """TXT verification alone does NOT classify self-hosted MX.
        google-site-verification just means domain was verified, not mail hosted."""
        result = classify(
            ["mail.example.ee"],
            "",
            txt_verifications={"microsoft": "ms12345"},
        )
        assert provider(result) == "independent"

    def test_self_hosted_dkim_still_works(self):
        """DKIM still works for self-hosted MX (only TXT was removed)."""
        result = classify(
            ["mail.example.ee"],
            "",
            dkim={"google": "google._domainkey.googlemail.com"},
        )
        assert provider(result) == "google"
        assert "DKIM" in reason(result)

    def test_direct_mx_not_overridden_by_txt(self):
        """Direct MX match takes precedence over TXT tokens."""
        result = classify(
            ["mail.protection.outlook.com"],
            "",
            txt_verifications={"google": "gv123"},
        )
        assert provider(result) == "microsoft"

    def test_local_provider_dkim_reveals_cloud_backend(self):
        """Local provider MX with DKIM revealing cloud backend → cloud wins."""
        result = classify(
            ["cmx.telia.ee"],
            "",
            dkim={"selector1": "selector1-torva-ee._domainkey.torvavv.onmicrosoft.com"},
        )
        assert provider(result) == "microsoft"
        assert "DKIM" in reason(result)
        assert "Telia" in reason(result)

    def test_local_provider_no_dkim_stays_local(self):
        """Local provider MX without DKIM stays as-is."""
        result = classify(
            ["cmx.telia.ee"],
            "",
        )
        assert provider(result) == "telia"

    def test_gateway_non_mail_txt_stays_independent(self):
        """Non-mail TXT tokens (apple, facebook) don't classify."""
        result = classify(
            ["filter.seppmail.cloud"],
            "",
            txt_verifications={"apple": "abc123", "facebook": "def456"},
        )
        assert provider(result) == "independent"


# ── mx.microsoft MX pattern ─────────────────────────────────────────


class TestMxMicrosoft:
    def test_mx_microsoft_detected(self):
        result = classify(["mx.microsoft"], "")
        assert provider(result) == "microsoft"

    def test_mx_microsoft_subdomain(self):
        result = classify(["something.mx.microsoft"], "")
        assert provider(result) == "microsoft"


# ── MS365 tenant detection in classify() ─────────────────────────────


class TestTenantDetection:
    def test_gateway_tenant_managed(self):
        """Gateway with no other backend signals but MS365 tenant → microsoft."""
        result = classify(
            ["filter.seppmail.cloud"],
            "",
            tenant="Managed",
        )
        assert provider(result) == "microsoft"
        assert "MS365 tenant" in reason(result)

    def test_gateway_tenant_federated(self):
        """Gateway with Federated tenant → microsoft."""
        result = classify(
            ["filter.seppmail.cloud"],
            "",
            tenant="Federated",
        )
        assert provider(result) == "microsoft"
        assert "MS365 tenant" in reason(result)

    def test_gateway_dkim_takes_precedence_over_tenant(self):
        """DKIM is more reliable than tenant check — DKIM wins."""
        result = classify(
            ["filter.seppmail.cloud"],
            "",
            dkim={"google": "google._domainkey.googlemail.com"},
            tenant="Managed",
        )
        assert provider(result) == "google"
        assert "DKIM" in reason(result)

    def test_self_hosted_tenant_stays_independent(self):
        """Tenant alone does NOT classify self-hosted MX (no gateway)."""
        result = classify(
            ["mail.example.ee"],
            "",
            tenant="Managed",
        )
        assert provider(result) == "independent"

    def test_no_tenant_gateway_stays_independent(self):
        """Gateway with no tenant and no backend signals → independent."""
        result = classify(
            ["filter.seppmail.cloud"],
            "",
            tenant=None,
        )
        assert provider(result) == "independent"

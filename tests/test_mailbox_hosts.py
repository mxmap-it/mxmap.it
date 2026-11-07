"""Test della logica mailbox-host (#31) — fixture calcolate a mano."""

from mail_sovereignty.mailbox_hosts import (
    candidate_hosts,
    classify_login_page,
    entity_verdict,
    farm_of,
    is_cloud_host,
    is_farm_host,
)


class TestClassifyLoginPage:
    def test_zimbra_title(self):
        assert classify_login_page("", "Zimbra Web Client Sign In") == "zimbra"

    def test_carbonio_title(self):
        assert (
            classify_login_page("<html>…</html>", "Carbonio Authentication")
            == "carbonio"
        )

    def test_zextras_login_path_in_body(self):
        body = '<a href="/zx/login/page/?customerDomain=comune.rivoli.to.it">'
        assert classify_login_page(body) == "zextras"

    def test_carbonio_as_chemical_element_is_not_a_match(self):
        """Negativo decisivo: "carbonio" in italiano è l'elemento chimico —
        una pagina comunale sull'impronta di carbonio NON è una farm."""
        body = "<h1>Impronta di carbonio del Comune</h1><p>emissioni CO2</p>"
        assert classify_login_page(body, "Ambiente e carbonio") is None

    def test_empty_is_none(self):
        assert classify_login_page("") is None


class TestHostHelpers:
    def test_farm_hosts(self):
        assert is_farm_host("mx.zimbraopen.it")
        assert is_farm_host("proxy.zimbraopen.it")
        assert is_farm_host("mx.carboniocloud.com")
        assert farm_of("mx.carboniocloud.com") == "carboniocloud.com"
        assert not is_farm_host("mail.comune.esempio.it")

    def test_cloud_hosts(self):
        assert is_cloud_host("autodiscover.outlook.com")
        assert is_cloud_host("tenant.onmicrosoft.com")
        assert not is_cloud_host("proxy.zimbraopen.it")


class TestCandidateHosts:
    def test_autodiscover_then_conventions_then_farm_mx(self):
        entry = {
            "domain": "comune.esempio.it",
            "mx": ["mx.zimbraopen.it"],
            "autodiscover": {"autodiscover_cname": "proxy.zimbraopen.it"},
        }
        hosts = candidate_hosts(entry)
        assert hosts[0] == "proxy.zimbraopen.it"
        assert "webmail.comune.esempio.it" in hosts
        assert "mx.zimbraopen.it" in hosts
        assert len(hosts) <= 6

    def test_cloud_and_invalid_excluded(self):
        entry = {
            "domain": "",
            "mx": [],
            "autodiscover": {
                "autodiscover_cname": "autodiscover.outlook.com",
                "autodiscover_srv": "ms37449889.msv1.invalid",
            },
        }
        assert candidate_hosts(entry) == []


class TestEntityVerdict:
    def test_confirmed_by_probe(self):
        entry = {
            "domain": "comune.esempio.it",
            "mx": ["mx.carboniocloud.com"],
            "autodiscover": None,
        }
        probed = {"webmail.comune.esempio.it": "carbonio"}
        verdict, ev = entity_verdict(entry, probed, set())
        assert verdict == "mailbox_host_confirmed"
        assert "carbonio" in ev

    def test_farm_autodiscover_without_http(self):
        entry = {
            "domain": "comune.esempio.it",
            "mx": ["mx.zimbraopen.it"],
            "autodiscover": {"autodiscover_srv": "proxy.zimbraopen.it"},
        }
        verdict, ev = entity_verdict(entry, {}, set())
        assert verdict == "farm_autodiscover"
        assert "proxy.zimbraopen.it" in ev

    def test_hybrid_cloud_not_touched(self):
        entry = {
            "domain": "cittametropolitana.pa.it",
            "mx": ["mx.zimbraopen.it"],
            "autodiscover": {"autodiscover_cname": "autodiscover.outlook.com"},
        }
        verdict, ev = entity_verdict(entry, {}, {"zimbraopen.it"})
        assert verdict == "hybrid_cloud"

    def test_hybrid_by_real_dkim_beats_farm_probe(self):
        """Pattern CM Palermo: DKIM Microsoft reale + autodiscover sulla farm
        → nel report è un ibrido (il classificatore lo tiene cloud), anche se
        il webmail farm risponde."""
        entry = {
            "domain": "cittametropolitana.pa.it",
            "mx": ["mx.zimbraopen.it"],
            "autodiscover": {"autodiscover_cname": "proxy.zimbraopen.it"},
            "dkim": {"selector1": "selector1-x._domainkey.t.onmicrosoft.com"},
        }
        probed = {"proxy.zimbraopen.it": "zimbra"}
        verdict, ev = entity_verdict(entry, probed, {"zimbraopen.it"})
        assert verdict == "hybrid_cloud"
        assert "DKIM" in ev

    def test_farm_mx_inherits_confirmation(self):
        entry = {"domain": "x.it", "mx": ["mx.zimbraopen.it"], "autodiscover": None}
        verdict, ev = entity_verdict(entry, {}, {"zimbraopen.it"})
        assert verdict == "farm_mx_confirmed"

    def test_unverified_when_nothing_known(self):
        entry = {"domain": "x.it", "mx": ["mail.x.it"], "autodiscover": None}
        assert entity_verdict(entry, {}, set())[0] == "unverified"

import asyncio
import json
from unittest.mock import AsyncMock, patch

from mail_sovereignty.postprocess import (
    MANUAL_OVERRIDES,
    build_urls,
    decrypt_typo3,
    extract_email_domains,
    process_unknown,
    run,
    scrape_email_domains,
)


# ── decrypt_typo3() ──────────────────────────────────────────────────


class TestDecryptTypo3:
    def test_known_encrypted(self):
        encrypted = "kygjrm8yYz,af"
        decrypted = decrypt_typo3(encrypted)
        assert decrypted == "mailto:a@b.ch"

    def test_empty_string(self):
        assert decrypt_typo3("") == ""

    def test_non_range_passthrough(self):
        assert decrypt_typo3(" ") == " "

    def test_custom_offset(self):
        result = decrypt_typo3("a", offset=1)
        assert result == "b"

    def test_wrap_around(self):
        result = decrypt_typo3("z", offset=2)
        assert result == "b"


# ── extract_email_domains() ──────────────────────────────────────────


class TestExtractEmailDomains:
    def test_plain_email(self):
        html = "Contact us at info@tallinn.ee for more info."
        assert "tallinn.ee" in extract_email_domains(html)

    def test_mailto_link(self):
        html = '<a href="mailto:contact@vald.ee">Email</a>'
        assert "vald.ee" in extract_email_domains(html)

    def test_typo3_obfuscated(self):
        html = """linkTo_UnCryptMailto('kygjrm8yYz,af')"""
        domains = extract_email_domains(html)
        assert "b.ch" in domains

    def test_skip_domains_filtered(self):
        html = "admin@example.com test@sentry.io"
        domains = extract_email_domains(html)
        assert "example.com" not in domains
        assert "sentry.io" not in domains

    def test_multiple_sources_combined(self):
        html = 'info@tallinn.ee <a href="mailto:admin@riga.lv">x</a>'
        domains = extract_email_domains(html)
        assert "tallinn.ee" in domains
        assert "riga.lv" in domains

    def test_no_emails(self):
        html = "<html><body>No contact here</body></html>"
        assert extract_email_domains(html) == set()


# ── build_urls() ─────────────────────────────────────────────────────


class TestBuildUrls:
    def test_bare_domain(self):
        urls = build_urls("tallinn.ee")
        assert "https://www.tallinn.ee/" in urls
        assert "https://tallinn.ee/" in urls
        assert any("/kontakt" in u for u in urls)

    def test_www_prefix(self):
        urls = build_urls("www.tallinn.ee")
        assert "https://www.tallinn.ee/" in urls
        assert "https://tallinn.ee/" in urls

    def test_https_prefix_stripped(self):
        urls = build_urls("https://tallinn.ee")
        assert "https://www.tallinn.ee/" in urls

    def test_includes_contact_paths(self):
        urls = build_urls("tallinn.ee")
        assert any("/contact" in u for u in urls)
        assert any("/kontakt" in u for u in urls)
        assert any("/kontaktid" in u for u in urls)


# ── MANUAL_OVERRIDES ─────────────────────────────────────────────────


class TestManualOverrides:
    def test_all_entries_have_required_keys(self):
        for bfs, entry in MANUAL_OVERRIDES.items():
            # Each override must have at least a domain or a provider
            assert "domain" in entry or "provider" in entry, (
                f"BFS {bfs} missing both 'domain' and 'provider'"
            )

    def test_valid_providers(self):
        valid = {
            "independent",
            "zone",
            "telia",
            "tet",
            "microsoft",
            "google",
            "aws",
            "local-isp",
            "merged",
        }
        for bfs, entry in MANUAL_OVERRIDES.items():
            if "provider" in entry:
                assert entry["provider"] in valid, (
                    f"BFS {bfs}: unexpected provider {entry['provider']}"
                )


# ── Async functions ──────────────────────────────────────────────────


class TestScrapeEmailDomains:
    async def test_empty_domain(self):
        result = await scrape_email_domains(None, "")
        assert result == set()

    async def test_with_emails_found(self):
        class FakeResponse:
            status_code = 200
            text = "Contact us at info@tallinn.ee"

        client = AsyncMock()
        client.get = AsyncMock(return_value=FakeResponse())

        result = await scrape_email_domains(client, "tallinn.ee")
        assert "tallinn.ee" in result


class TestProcessUnknown:
    async def test_no_domain_returns_unchanged(self):
        m = {"bfs": "LT-99", "name": "Test", "domain": "", "provider": "unknown"}
        sem = asyncio.Semaphore(10)
        client = AsyncMock()

        result = await process_unknown(client, sem, m)
        assert result["provider"] == "unknown"

    async def test_resolves_via_email_scraping(self):
        m = {
            "bfs": "EE-0001",
            "name": "Test",
            "domain": "test.ee",
            "provider": "unknown",
        }
        sem = asyncio.Semaphore(10)

        class FakeResponse:
            status_code = 200
            text = "Contact us at info@test.ee"

        client = AsyncMock()
        client.get = AsyncMock(return_value=FakeResponse())

        with (
            patch(
                "mail_sovereignty.postprocess.lookup_mx",
                new_callable=AsyncMock,
                return_value=["mail.test.ee"],
            ),
            patch(
                "mail_sovereignty.postprocess.lookup_txt",
                new_callable=AsyncMock,
                return_value=("", {}),
            ),
            patch(
                "mail_sovereignty.postprocess.lookup_autodiscover",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "mail_sovereignty.postprocess.resolve_mx_asns",
                new_callable=AsyncMock,
                return_value=set(),
            ),
        ):
            result = await process_unknown(client, sem, m)

        assert result["provider"] == "independent"

    async def test_no_email_domains_found(self):
        m = {
            "bfs": "EE-0001",
            "name": "Test",
            "domain": "test.ee",
            "provider": "unknown",
        }
        sem = asyncio.Semaphore(10)

        class FakeResponse:
            status_code = 200
            text = "<html>No emails here</html>"

        client = AsyncMock()
        client.get = AsyncMock(return_value=FakeResponse())

        result = await process_unknown(client, sem, m)
        assert result["provider"] == "unknown"


class TestScrapeEmailDomainsNoEmails:
    async def test_non_200_skipped(self):
        class FakeResponse:
            status_code = 404
            text = ""

        client = AsyncMock()
        client.get = AsyncMock(return_value=FakeResponse())

        result = await scrape_email_domains(client, "test.ee")
        assert result == set()

    async def test_exception_handled(self):
        client = AsyncMock()
        client.get = AsyncMock(side_effect=Exception("connection error"))

        result = await scrape_email_domains(client, "test.ee")
        assert result == set()


class TestDnsRetryStep:
    async def test_recovers_unknown_with_domain(self, tmp_path):
        data = {
            "generated": "2025-01-01",
            "total": 1,
            "counts": {"unknown": 1},
            "municipalities": {
                "EE-0001": {
                    "bfs": "EE-0001",
                    "name": "Testlinn",
                    "canton": "Harju maakond",
                    "domain": "testlinn.ee",
                    "mx": [],
                    "spf": "",
                    "provider": "unknown",
                },
            },
        }
        path = tmp_path / "data.json"
        path.write_text(json.dumps(data))

        with (
            patch(
                "mail_sovereignty.postprocess.lookup_mx",
                new_callable=AsyncMock,
                return_value=["testlinn-ee.mail.protection.outlook.com"],
            ),
            patch(
                "mail_sovereignty.postprocess.lookup_txt",
                new_callable=AsyncMock,
                return_value=("v=spf1 include:spf.protection.outlook.com -all", {}),
            ),
            patch(
                "mail_sovereignty.postprocess.lookup_autodiscover",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            await run(path)

        result = json.loads(path.read_text())
        assert result["municipalities"]["EE-0001"]["provider"] == "microsoft"

    async def test_skips_unknown_without_domain(self, tmp_path):
        data = {
            "generated": "2025-01-01",
            "total": 1,
            "counts": {"unknown": 1},
            "municipalities": {
                "LT-99": {
                    "bfs": "LT-99",
                    "name": "NoDomain",
                    "canton": "Test",
                    "domain": "",
                    "mx": [],
                    "spf": "",
                    "provider": "unknown",
                },
            },
        }
        path = tmp_path / "data.json"
        path.write_text(json.dumps(data))

        await run(path)

        result = json.loads(path.read_text())
        assert result["municipalities"]["LT-99"]["provider"] == "unknown"


class TestSmtpBannerStep:
    async def test_reclassifies_independent_via_smtp(self, tmp_path):
        data = {
            "generated": "2025-01-01",
            "total": 1,
            "counts": {"independent": 1},
            "municipalities": {
                "EE-0100": {
                    "bfs": "EE-0100",
                    "name": "SmtpTown",
                    "canton": "Test",
                    "domain": "smtptown.ee",
                    "mx": ["mail.smtptown.ee"],
                    "spf": "",
                    "provider": "independent",
                },
            },
        }
        path = tmp_path / "data.json"
        path.write_text(json.dumps(data))

        with patch(
            "mail_sovereignty.postprocess.fetch_smtp_banner",
            new_callable=AsyncMock,
            return_value={
                "banner": "220 mail.protection.outlook.com Microsoft ESMTP MAIL Service ready",
                "ehlo": "250 ready",
            },
        ):
            await run(path)

        result = json.loads(path.read_text())
        assert result["municipalities"]["EE-0100"]["provider"] == "microsoft"
        assert "smtp_banner" in result["municipalities"]["EE-0100"]

    async def test_leaves_independent_when_banner_is_postfix(self, tmp_path):
        data = {
            "generated": "2025-01-01",
            "total": 1,
            "counts": {"independent": 1},
            "municipalities": {
                "EE-0101": {
                    "bfs": "EE-0101",
                    "name": "PostfixTown",
                    "canton": "Test",
                    "domain": "postfixtown.ee",
                    "mx": ["mail.postfixtown.ee"],
                    "spf": "",
                    "provider": "independent",
                },
            },
        }
        path = tmp_path / "data.json"
        path.write_text(json.dumps(data))

        with patch(
            "mail_sovereignty.postprocess.fetch_smtp_banner",
            new_callable=AsyncMock,
            return_value={
                "banner": "220 mail.postfixtown.ee ESMTP Postfix",
                "ehlo": "250 mail.postfixtown.ee",
            },
        ):
            await run(path)

        result = json.loads(path.read_text())
        assert result["municipalities"]["EE-0101"]["provider"] == "independent"
        assert "smtp_banner" in result["municipalities"]["EE-0101"]

    async def test_skips_already_classified(self, tmp_path):
        data = {
            "generated": "2025-01-01",
            "total": 1,
            "counts": {"microsoft": 1},
            "municipalities": {
                "EE-0102": {
                    "bfs": "EE-0102",
                    "name": "AlreadyKnown",
                    "canton": "Test",
                    "domain": "known.ee",
                    "mx": ["mail.protection.outlook.com"],
                    "spf": "v=spf1 include:spf.protection.outlook.com -all",
                    "provider": "microsoft",
                },
            },
        }
        path = tmp_path / "data.json"
        path.write_text(json.dumps(data))

        with patch(
            "mail_sovereignty.postprocess.fetch_smtp_banner",
            new_callable=AsyncMock,
        ) as mock_fetch:
            await run(path)
            mock_fetch.assert_not_called()

    async def test_deduplicates_mx_hosts(self, tmp_path):
        data = {
            "generated": "2025-01-01",
            "total": 2,
            "counts": {"independent": 2},
            "municipalities": {
                "EE-2000": {
                    "bfs": "EE-2000",
                    "name": "Town1",
                    "canton": "Test",
                    "domain": "town1.ee",
                    "mx": ["shared-mx.example.ee"],
                    "spf": "",
                    "provider": "independent",
                },
                "EE-2001": {
                    "bfs": "EE-2001",
                    "name": "Town2",
                    "canton": "Test",
                    "domain": "town2.ee",
                    "mx": ["shared-mx.example.ee"],
                    "spf": "",
                    "provider": "independent",
                },
            },
        }
        path = tmp_path / "data.json"
        path.write_text(json.dumps(data))

        with patch(
            "mail_sovereignty.postprocess.fetch_smtp_banner",
            new_callable=AsyncMock,
            return_value={
                "banner": "220 mail.protection.outlook.com Microsoft ESMTP MAIL Service",
                "ehlo": "250 ready",
            },
        ) as mock_fetch:
            await run(path)
            # Should only be called once for the shared MX host
            assert mock_fetch.call_count == 1

        result = json.loads(path.read_text())
        assert result["municipalities"]["EE-2000"]["provider"] == "microsoft"
        assert result["municipalities"]["EE-2001"]["provider"] == "microsoft"

    async def test_empty_banner_no_change(self, tmp_path):
        data = {
            "generated": "2025-01-01",
            "total": 1,
            "counts": {"independent": 1},
            "municipalities": {
                "EE-3000": {
                    "bfs": "EE-3000",
                    "name": "NoConnect",
                    "canton": "Test",
                    "domain": "noconnect.ee",
                    "mx": ["mail.noconnect.ee"],
                    "spf": "",
                    "provider": "independent",
                },
            },
        }
        path = tmp_path / "data.json"
        path.write_text(json.dumps(data))

        with patch(
            "mail_sovereignty.postprocess.fetch_smtp_banner",
            new_callable=AsyncMock,
            return_value={"banner": "", "ehlo": ""},
        ):
            await run(path)

        result = json.loads(path.read_text())
        assert result["municipalities"]["EE-3000"]["provider"] == "independent"
        assert "smtp_banner" not in result["municipalities"]["EE-3000"]


class TestPostprocessRun:
    async def test_manual_overrides_empty(self, tmp_path):
        """MANUAL_OVERRIDES is empty — verify no overrides applied."""
        data = {
            "generated": "2025-01-01",
            "total": 1,
            "counts": {"unknown": 1},
            "municipalities": {
                "EE-0001": {
                    "bfs": "EE-0001",
                    "name": "Test",
                    "canton": "Harju maakond",
                    "domain": "",
                    "mx": [],
                    "spf": "",
                    "provider": "unknown",
                },
            },
        }
        path = tmp_path / "data.json"
        path.write_text(json.dumps(data))

        await run(path)

        result = json.loads(path.read_text())
        assert result["municipalities"]["EE-0001"]["provider"] == "unknown"

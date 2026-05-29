import json
from unittest.mock import AsyncMock, patch

from mail_sovereignty.cli import _parse_country_args
from mail_sovereignty.preprocess import (
    guess_domains,
    load_seed_data,
    run,
    scan_municipality,
    url_to_domain,
)


# ── url_to_domain() ─────────────────────────────────────────────────


class TestUrlToDomain:
    def test_full_url_with_path(self):
        assert url_to_domain("https://www.tallinn.ee/some/path") == "tallinn.ee"

    def test_no_scheme(self):
        assert url_to_domain("tallinn.ee") == "tallinn.ee"

    def test_strips_www(self):
        assert url_to_domain("https://www.example.ee") == "example.ee"

    def test_empty_string(self):
        assert url_to_domain("") is None

    def test_none(self):
        assert url_to_domain(None) is None

    def test_bare_domain(self):
        assert url_to_domain("example.lv") == "example.lv"

    def test_http_scheme(self):
        assert url_to_domain("http://example.lt/page") == "example.lt"


# ── guess_domains() ─────────────────────────────────────────────────


class TestGuessDomains:
    def test_simple_estonian(self):
        domains = guess_domains("Tallinn", "EE")
        assert "tallinn.ee" in domains

    def test_estonian_diacritics(self):
        domains = guess_domains("Jõhvi", "EE")
        assert "johvi.ee" in domains

    def test_latvian_diacritics(self):
        domains = guess_domains("Jēkabpils", "LV")
        assert "jekabpils.lv" in domains

    def test_lithuanian_diacritics(self):
        domains = guess_domains("Šiauliai", "LT")
        assert "siauliai.lt" in domains

    def test_parenthetical_stripped(self):
        domains = guess_domains("Rakvere (linn)", "EE")
        assert any("rakvere" in d for d in domains)

    def test_vald_suffix_removed(self):
        domains = guess_domains("Saue vald", "EE")
        assert "saue.ee" in domains

    def test_country_tld(self):
        domains = guess_domains("Vilnius", "LT")
        assert all(d.endswith(".lt") for d in domains)

    def test_no_country_generates_all_tlds(self):
        domains = guess_domains("Test")
        tlds = {d.split(".")[-1] for d in domains}
        assert "ee" in tlds and "de" in tlds and "dk" in tlds

    def test_norwegian_diacritics(self):
        domains = guess_domains("Trømsø", "NO")
        assert "tromso.no" in domains or "tromso.kommune.no" in domains

    def test_swedish_diacritics(self):
        domains = guess_domains("Malmö", "SE")
        assert "malmo.se" in domains

    def test_german_umlaut_expansion(self):
        domains = guess_domains("München", "DE")
        assert "muenchen.de" in domains

    def test_german_prefix_strip(self):
        domains = guess_domains("Landkreis Rostock", "DE")
        assert "rostock.de" in domains

    def test_danish_aa_convention(self):
        domains = guess_domains("Aabenraa", "DK")
        assert "aabenraa.dk" in domains

    def test_danish_aa_from_å(self):
        domains = guess_domains("Århus", "DK")
        assert "aarhus.dk" in domains

    def test_czech_diacritics(self):
        domains = guess_domains("Třebíč", "CZ")
        assert "trebic.cz" in domains

    def test_polish_diacritics(self):
        domains = guess_domains("Łódź", "PL")
        assert "lodz.pl" in domains or "lodz.gov.pl" in domains

    def test_polish_prefix_strip(self):
        domains = guess_domains("Powiat Krakowski", "PL")
        assert "krakowski.pl" in domains or "krakowski.gov.pl" in domains

    def test_irish_fada(self):
        domains = guess_domains("Dún Laoghaire–Rathdown County Council", "IE")
        assert any("dun-laoghaire" in d for d in domains)

    def test_irish_suffix_strip(self):
        domains = guess_domains("Kerry County Council", "IE")
        assert "kerry.ie" in domains

    def test_dutch_diacritics(self):
        domains = guess_domains("Súdwest-Fryslân", "NL")
        assert any(d.endswith(".nl") for d in domains)

    def test_dutch_gemeente_prefix_strip(self):
        domains = guess_domains("Gemeente Utrecht", "NL")
        assert "utrecht.nl" in domains

    def test_slovenian_diacritics(self):
        domains = guess_domains("Črnomelj", "SI")
        assert "crnomelj.si" in domains

    def test_slovak_diacritics(self):
        domains = guess_domains("Ľubovňa", "SK")
        assert "lubovna.sk" in domains

    def test_slovak_diacritics_rz(self):
        domains = guess_domains("Ružomberok", "SK")
        assert "ruzomberok.sk" in domains

    def test_uk_gov_uk_tld(self):
        domains = guess_domains("Cambridge", "GB")
        assert "cambridge.gov.uk" in domains

    def test_uk_prefix_strip(self):
        domains = guess_domains("City of Westminster", "GB")
        assert "westminster.gov.uk" in domains

    def test_croatian_diacritics(self):
        domains = guess_domains("Đakovo", "HR")
        assert "djakovo.hr" in domains

    def test_hungarian_diacritics(self):
        domains = guess_domains("Győr", "HU")
        assert "gyor.hu" in domains

    def test_romanian_diacritics(self):
        domains = guess_domains("Timișoara", "RO")
        assert "timisoara.ro" in domains

    def test_romanian_prefix_pattern(self):
        domains = guess_domains("Cluj", "RO")
        assert "primaria-cluj.ro" in domains

    def test_maltese_diacritics(self):
        domains = guess_domains("Ħamrun", "MT")
        assert any("hamrun" in d for d in domains)

    def test_greek_romanized(self):
        domains = guess_domains("Thessaloniki", "GR")
        assert "thessaloniki.gr" in domains

    def test_cypriot_tld(self):
        domains = guess_domains("Limassol", "CY")
        assert any(d.endswith(".org.cy") or d.endswith(".com.cy") for d in domains)


# ── load_seed_data() ─────────────────────────────────────────────────


class TestLoadSeedData:
    def test_loads_all_countries(self):
        data = load_seed_data()
        countries = {m.get("country") for m in data.values()}
        assert countries >= {
            "EE",
            "LV",
            "LT",
            "FI",
            "NO",
            "SE",
            "DE",
            "DK",
            "IE",
            "NL",
            "SK",
            "GB",
            "BG",
            "HR",
            "CY",
            "GR",
            "HU",
            "MT",
            "RO",
            "AL",
            "XK",
            "ME",
            "BA",
            "RS",
            "MK",
            "UA",
            "MD",
            "LI",
            "SM",
            "GE",
            "AM",
            "AZ",
            "BY",
            "TR",
            "AU",
            "NZ",
            "ID",
            "PG",
            "MY",
            "TH",
            "KH",
            "PH",
            "VN",
            "MM",
            "OM",
            "AE",
            "QA",
            "BH",
            "FJ",
            "WS",
            "VU",
            "TO",
            "NR",
            "PW",
            "JP",
            "TW",
            "KR",
            "KP",
            "CN",
            "MN",
            "IN",
            "BD",
            "PK",
            "LK",
            "NP",
            "LA",
            "BN",
            "TL",
            "KZ",
            "UZ",
            "KG",
            "RU",
            "SA",
            "IQ",
            "JO",
            "LB",
            "KW",
            "IR",
            "IL",
            "AR",
            "BO",
            "BR",
            "CL",
            "CO",
            "EC",
            "GY",
            "PE",
            "PY",
            "SR",
            "UY",
            "VE",
            "CA",
            "MX",
            "BZ",
            "GT",
            "HN",
            "SV",
            "NI",
            "CR",
            "PA",
            "DZ",
            "EG",
            "LY",
            "MA",
            "TN",
            "SD",
            "BJ",
            "BF",
            "CV",
            "CI",
            "GM",
            "GH",
            "GN",
            "GW",
            "LR",
            "ML",
            "MR",
            "NE",
            "NG",
            "SN",
            "SL",
            "TG",
            "CM",
            "CF",
            "TD",
            "CG",
            "CD",
            "GQ",
            "GA",
            "ST",
            "BI",
            "KM",
            "DJ",
            "ER",
            "ET",
            "KE",
            "MG",
            "MW",
            "MU",
            "MZ",
            "RW",
            "SC",
            "SO",
            "SS",
            "TZ",
            "UG",
            "AO",
            "BW",
            "SZ",
            "LS",
            "NA",
            "ZA",
            "ZM",
            "ZW",
            "CU",
            "HT",
            "DO",
            "JM",
            "TT",
            "BS",
            "BB",
            "AG",
            "DM",
            "GD",
            "KN",
            "LC",
            "VC",
            "AF",
            "SG",
            "YE",
            "SY",
            "PS",
            "TJ",
            "TM",
            "MV",
            "BT",
            "SB",
            "MH",
            "FM",
            "KI",
            "TV",
        }

    def test_minimum_count(self):
        data = load_seed_data()
        assert len(data) >= 150

    def test_required_fields(self):
        data = load_seed_data()
        for muni_id, m in data.items():
            assert "bfs" in m
            assert "name" in m
            assert "website" in m


# ── scan_municipality() ──────────────────────────────────────────────


class TestScanMunicipality:
    async def test_website_domain_mx_found(self):
        m = {
            "bfs": "EE-0784",
            "name": "Tallinn",
            "canton": "Harju maakond",
            "country": "EE",
            "website": "https://www.tallinn.ee",
        }
        sem = __import__("asyncio").Semaphore(10)

        with (
            patch(
                "mail_sovereignty.preprocess.lookup_mx",
                new_callable=AsyncMock,
                return_value=["tallinn-ee.mail.protection.outlook.com"],
            ),
            patch(
                "mail_sovereignty.preprocess.lookup_txt",
                new_callable=AsyncMock,
                return_value=("v=spf1 include:spf.protection.outlook.com -all", {}),
            ),
            patch(
                "mail_sovereignty.preprocess.resolve_spf_includes",
                new_callable=AsyncMock,
                return_value="v=spf1 include:spf.protection.outlook.com -all",
            ),
            patch(
                "mail_sovereignty.preprocess.lookup_autodiscover",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            result = await scan_municipality(m, sem)

        assert result["provider"] == "microsoft"
        assert result["domain"] == "tallinn.ee"

    async def test_no_mx_unknown(self):
        m = {
            "bfs": "LT-99",
            "name": "Zzz",
            "canton": "Test",
            "country": "LT",
            "website": "",
        }
        sem = __import__("asyncio").Semaphore(10)

        with (
            patch(
                "mail_sovereignty.preprocess.lookup_mx",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "mail_sovereignty.preprocess.lookup_txt",
                new_callable=AsyncMock,
                return_value=("", {}),
            ),
        ):
            result = await scan_municipality(m, sem)

        assert result["provider"] == "unknown"


# ── run() ────────────────────────────────────────────────────────────


class TestPreprocessRun:
    async def test_writes_output(self, tmp_path):
        with (
            patch(
                "mail_sovereignty.preprocess.load_seed_data",
                return_value={
                    "EE-0784": {
                        "bfs": "EE-0784",
                        "name": "Tallinn",
                        "canton": "Harju maakond",
                        "country": "EE",
                        "website": "tallinn.ee",
                    },
                },
            ),
            patch(
                "mail_sovereignty.preprocess.lookup_mx",
                new_callable=AsyncMock,
                return_value=["mx.tallinn.ee"],
            ),
            patch(
                "mail_sovereignty.preprocess.lookup_txt",
                new_callable=AsyncMock,
                return_value=("", {}),
            ),
            patch(
                "mail_sovereignty.preprocess.resolve_spf_includes",
                new_callable=AsyncMock,
                return_value="",
            ),
            patch(
                "mail_sovereignty.preprocess.lookup_autodiscover",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            output = tmp_path / "data.json"
            await run(output)

        assert output.exists()
        data = json.loads(output.read_text())
        assert data["total"] == 1
        assert "EE-0784" in data["municipalities"]


# ── _parse_country_args() ─────────────────────────────────────────


class TestParseCountryArgs:
    def test_empty_args(self):
        countries, state_filters = _parse_country_args([])
        assert countries is None
        assert state_filters == {}

    def test_simple_country(self):
        countries, state_filters = _parse_country_args(["IT"])
        assert countries == ["IT"]
        assert state_filters == {}

    def test_de_state_abbreviation(self):
        countries, state_filters = _parse_country_args(["DE:BY"])
        assert countries == ["DE"]
        assert state_filters == {"DE": ["09"]}

    def test_de_state_code(self):
        countries, state_filters = _parse_country_args(["DE:09"])
        assert countries == ["DE"]
        assert state_filters == {"DE": ["09"]}

    def test_de_multiple_states(self):
        countries, state_filters = _parse_country_args(["DE:BY,NW"])
        assert countries == ["DE"]
        assert "09" in state_filters["DE"]
        assert "05" in state_filters["DE"]

    def test_mixed_args(self):
        countries, state_filters = _parse_country_args(["DE:BY", "IT"])
        assert set(countries) == {"DE", "IT"}
        assert state_filters == {"DE": ["09"]}

    def test_case_insensitive(self):
        countries, state_filters = _parse_country_args(["de:by"])
        assert countries == ["DE"]
        assert state_filters == {"DE": ["09"]}


# ── State filter in run() ────────────────────────────────────────


class TestPreprocessStateFilter:
    async def test_state_filter_reduces_municipalities(self, tmp_path):
        seed_data = {
            "DE-09001": {
                "bfs": "DE-09001",
                "name": "München",
                "canton": "Bayern",
                "country": "DE",
                "website": "muenchen.de",
            },
            "DE-01001": {
                "bfs": "DE-01001",
                "name": "Flensburg",
                "canton": "Schleswig-Holstein",
                "country": "DE",
                "website": "flensburg.de",
            },
        }
        with (
            patch("mail_sovereignty.preprocess.load_seed_data", return_value=seed_data),
            patch(
                "mail_sovereignty.preprocess.lookup_mx",
                new_callable=AsyncMock,
                return_value=["mx.test.de"],
            ),
            patch(
                "mail_sovereignty.preprocess.lookup_txt",
                new_callable=AsyncMock,
                return_value=("", {}),
            ),
            patch(
                "mail_sovereignty.preprocess.resolve_spf_includes",
                new_callable=AsyncMock,
                return_value="",
            ),
            patch(
                "mail_sovereignty.preprocess.lookup_autodiscover",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            output = tmp_path / "data.json"
            await run(
                output,
                countries=["DE"],
                state_filters={"DE": ["09"]},
            )

        data = json.loads(output.read_text())
        # Only Bayern (09) should be scanned
        assert data["total"] == 1
        assert "DE-09001" in data["municipalities"]
        assert "DE-01001" not in data["municipalities"]

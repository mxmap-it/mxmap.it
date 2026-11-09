"""Test del modello di sovranità relativa — EU Security Map (mxmap.it#33).

Valori attesi calcolati a mano su una popolazione sintetica piccola.
"""

import pytest

from mail_sovereignty import eu_security as es


class TestProviderCountry:
    def test_known_providers_legal_seat(self):
        assert es.provider_country("microsoft", None) == "US"
        assert es.provider_country("ovh", None) == "FR"
        assert es.provider_country("hetzner", None) == "DE"
        assert es.provider_country("aruba", None) == "IT"

    def test_independent_uses_single_mx_country(self):
        assert es.provider_country("independent", ["DE"]) == "DE"
        assert es.provider_country("independent", ["de"]) == "DE"

    def test_independent_multi_country_is_unknown(self):
        assert es.provider_country("independent", ["DE", "US"]) is None

    def test_independent_no_country_is_unknown(self):
        assert es.provider_country("independent", []) is None
        assert es.provider_country("independent", None) is None

    def test_local_isp_uses_mx_country(self):
        assert es.provider_country("local-isp", ["PL"]) == "PL"
        assert es.bucket_for("PL", "local-isp", ["PL"]) == "national"

    def test_unknown_provider_not_in_table(self):
        assert es.provider_country("something-else", None) is None


class TestBucketFor:
    def test_national_when_provider_seat_matches_country(self):
        # Polizia tedesca su Hetzner (DE) → national
        assert es.bucket_for("DE", "hetzner", None) == "national"
        # Ente IT su Aruba → national
        assert es.bucket_for("IT", "aruba", None) == "national"

    def test_us_provider_is_us_everywhere(self):
        assert es.bucket_for("DE", "microsoft", None) == "us"
        assert es.bucket_for("FR", "google", None) == "us"
        assert es.bucket_for("IT", "aws", None) == "us"

    def test_european_provider_other_member_is_eu_other(self):
        # Ente tedesco su OVH (FR) → eu_other
        assert es.bucket_for("DE", "ovh", None) == "eu_other"
        # Ente francese su Hetzner (DE) → eu_other
        assert es.bucket_for("FR", "hetzner", None) == "eu_other"

    def test_non_european_foreign_is_other_foreign(self):
        # Ente tedesco su Zoho (IN) → other_foreign
        assert es.bucket_for("DE", "zoho", None) == "other_foreign"
        assert es.bucket_for("PL", "yandex", None) == "other_foreign"

    def test_independent_in_own_country_is_national(self):
        assert es.bucket_for("DE", "independent", ["DE"]) == "national"

    def test_independent_hosted_in_us_is_us(self):
        assert es.bucket_for("DE", "independent", ["US"]) == "us"

    def test_unknown_provider_is_unknown(self):
        assert es.bucket_for("DE", "unknown", None) == "unknown"

    def test_independent_unresolved_is_unknown(self):
        assert es.bucket_for("DE", "independent", None) == "unknown"

    def test_eu_institution_european_provider_is_national(self):
        # Istituzione UE su OVH (FR, UE) → national (sovranità europea)
        assert es.bucket_for("EU", "ovh", None) == "national"
        # su Infomaniak (CH, europeo non-UE) → national (europeo)
        assert es.bucket_for("EU", "infomaniak", None) == "national"

    def test_eu_institution_us_provider_is_us(self):
        assert es.bucket_for("EU", "microsoft", None) == "us"

    def test_eu_institution_foreign_is_other_foreign(self):
        assert es.bucket_for("EU", "zoho", None) == "other_foreign"


def _pop():
    """Popolazione sintetica a verdetto calcolato a mano.

    DE: 2 us (microsoft, google), 1 national (hetzner), 1 eu_other (ovh) → 4 class.
    FR: 1 us (microsoft), 1 national (ovh) → 2 classificati
    MC: 1 unknown → 0 classificati
    """
    raw = [
        {"id": "de-a", "country": "DE", "type": "police", "provider": "microsoft"},
        {"id": "de-b", "country": "DE", "type": "intelligence", "provider": "google"},
        {"id": "de-c", "country": "DE", "type": "cybersecurity", "provider": "hetzner"},
        {"id": "de-d", "country": "DE", "type": "defence_ministry", "provider": "ovh"},
        {"id": "fr-a", "country": "FR", "type": "police", "provider": "microsoft"},
        {"id": "fr-b", "country": "FR", "type": "intelligence", "provider": "ovh"},
        {"id": "mc-a", "country": "MC", "type": "police", "provider": "unknown"},
    ]
    return es.classify_entities(raw)


class TestComputeKpi:
    def test_overall_counts(self):
        kpi = es.compute_kpi(_pop(), min_classified=2)
        assert kpi["n_entities"] == 7
        assert kpi["n_countries"] == 3
        # us: de-a, de-b, fr-a = 3 ; national: de-c, fr-b = 2 ;
        # eu_other: de-d = 1 ; unknown: mc-a = 1
        assert kpi["overall"] == {
            "national": 2,
            "us": 3,
            "eu_other": 1,
            "other_foreign": 0,
            "unknown": 1,
        }

    def test_country_us_exposure(self):
        kpi = es.compute_kpi(_pop(), min_classified=2)
        by_cc = {c["country"]: c for c in kpi["countries"]}
        # DE: us 2 / classificati 4 = 50.0
        assert by_cc["DE"]["us_exposure_pct"] == 50.0
        assert by_cc["DE"]["national_pct"] == 25.0
        # FR: us 1 / classificati 2 = 50.0
        assert by_cc["FR"]["us_exposure_pct"] == 50.0
        # MC: 0 classificati → 0.0, non eleggibile
        assert by_cc["MC"]["us_exposure_pct"] == 0.0
        assert by_cc["MC"]["ranking_eligible"] is False
        assert by_cc["DE"]["ranking_eligible"] is True

    def test_ranking_sorted_desc(self):
        kpi = es.compute_kpi(_pop(), min_classified=2)
        elig = [c["us_exposure_pct"] for c in kpi["countries"] if c["ranking_eligible"]]
        assert elig == sorted(elig, reverse=True)

    def test_by_type_present(self):
        kpi = es.compute_kpi(_pop(), min_classified=2)
        assert kpi["by_type"]["police"]["us"] == 2  # de-a, fr-a


class TestAssertIntegrity:
    def test_passes_on_valid(self):
        pop = _pop()
        kpi = es.compute_kpi(pop, min_classified=2)
        es.assert_integrity(kpi, pop)  # non deve sollevare

    def test_fires_on_bucket_sum_mismatch(self):
        pop = _pop()
        kpi = es.compute_kpi(pop, min_classified=2)
        kpi["overall"]["us"] += 1  # corrompe
        with pytest.raises(AssertionError):
            es.assert_integrity(kpi, pop)

    def test_fires_on_bad_bucket(self):
        pop = _pop()
        kpi = es.compute_kpi(pop, min_classified=2)
        pop[0]["bucket"] = "nonsense"
        with pytest.raises(AssertionError):
            es.assert_integrity(kpi, pop)

    def test_fires_on_country_sum_mismatch(self):
        pop = _pop()
        kpi = es.compute_kpi(pop, min_classified=2)
        kpi["countries"][0]["n"] += 5
        with pytest.raises(AssertionError):
            es.assert_integrity(kpi, pop)

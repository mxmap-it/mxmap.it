"""Unit tests for the SEO page URL/slug logic (src/mail_sovereignty/pages.py)."""

from mail_sovereignty import pages as P


def test_slugify_accents_and_apostrophes():
    # Real entity name: caps + apostrophe-as-accent + spaces.
    assert (
        P.slugify("MINISTERO DELL'UNIVERSITA' E DELLA RICERCA")
        == "ministero-delluniversita-e-della-ricerca"
    )
    assert P.slugify("Città di Castello") == "citta-di-castello"
    assert P.slugify("Forlì-Cesena") == "forli-cesena"
    assert P.slugify("  A  B  ") == "a-b"
    assert P.slugify("") == ""


def test_slugify_maxlen():
    s = P.slugify("a" * 200, maxlen=20)
    assert len(s) <= 20 and not s.endswith("-")


def test_province_slug():
    assert P.province_slug("RM") == "rm"
    assert P.province_slug(" mi ") == "mi"
    assert P.province_slug(None) == "italia"
    assert P.province_slug("") == "italia"


def test_hub_paths():
    assert P.region_path("Lazio") == "/aree/lazio/"
    assert P.province_path("Lazio", "RM") == "/aree/lazio/rm/"
    assert P.comune_path("Lazio", "RM", "Roma") == "/aree/lazio/rm/roma/"
    # Bilingual / spaced regions fold cleanly.
    assert P.region_path("Valle d'Aosta") == "/aree/valle-daosta/"


def test_assign_entity_paths_singleton_is_clean():
    ents = [{"bfs": "IT-COM-AAA", "name": "Comune di Roma", "provincia": "RM"}]
    paths = P.assign_entity_paths(ents)
    assert paths == {"IT-COM-AAA": "/ente/rm/comune-di-roma/"}


def test_assign_entity_paths_collision_is_tokenized_and_stable():
    ents = [
        {
            "bfs": "IT-L33-ZZZ",
            "name": "Istituto Comprensivo Statale",
            "provincia": "MI",
        },
        {
            "bfs": "IT-L33-AAA",
            "name": "Istituto Comprensivo Statale",
            "provincia": "MI",
        },
    ]
    paths = P.assign_entity_paths(ents)
    # Both colliding members get a stable per-bfs token; neither keeps the clean slug.
    assert paths["IT-L33-ZZZ"] == "/ente/mi/istituto-comprensivo-statale-zzz/"
    assert paths["IT-L33-AAA"] == "/ente/mi/istituto-comprensivo-statale-aaa/"
    # Order-independent: reversing input yields identical mapping.
    assert P.assign_entity_paths(list(reversed(ents))) == paths


def test_assign_entity_paths_all_unique():
    ents = [
        {"bfs": f"IT-COM-{i:04d}", "name": f"Comune di Test {i}", "provincia": "TO"}
        for i in range(50)
    ] + [
        {"bfs": "IT-COM-DUP1", "name": "Comune Doppio", "provincia": "TO"},
        {"bfs": "IT-COM-DUP2", "name": "Comune Doppio", "provincia": "TO"},
        # Same name, different province → no collision, both clean.
        {"bfs": "IT-COM-NA01", "name": "Comune Doppio", "provincia": "NA"},
    ]
    paths = P.assign_entity_paths(ents)
    assert len(paths) == len(ents)
    assert len(set(paths.values())) == len(ents)  # no collisions
    assert paths["IT-COM-NA01"] == "/ente/na/comune-doppio/"  # clean in its province


def test_domain_alias_path():
    assert P.domain_alias_path("Comune.roma.it") == "/dominio/comune.roma.it/"
    assert P.domain_alias_path("") is None
    assert P.domain_alias_path("nodomain") is None  # no dot
    assert P.domain_alias_path("bad domain.it") is None  # space → rejected


def test_cluster_of():
    assert P.cluster_of("IT-COM-XYZ")[0] == "territorial"
    assert P.cluster_of("IT-L33-XYZ")[0] == "education"
    assert P.cluster_of("IT-C1-XYZ")[0] == "central"
    assert P.cluster_of("IT-ZZZ-XYZ") == ("altri", "Altri enti")
    assert P.category_path("education") == "/categoria/education/"


def test_sovereignty_colors_present():
    assert P.sov6_color("USA (CLOUD Act)") == "#D42E2E"
    assert P.sov6_color("Italia — Cloud sovrano") == "#009246"
    assert P.sov4_color("extra_eu") == "#D42E2E"
    assert P.sov4_color("eu_non_it") == "#1E5FB4"
    assert P.sov6_color("bucket-inesistente") == "#BFBFBF"  # safe fallback

"""Tests to detect regressions where countries lose map coloring.

These tests verify that TopoJSON files have valid feature IDs that
match data.json OSM relation IDs, ensuring polygons can be colored
on the map. A regression here means a country will appear gray.
"""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
TOPO_DIR = ROOT / "topo"
MANIFEST_PATH = TOPO_DIR / "manifest.json"
DATA_PATH = ROOT / "data.json"

# Countries that use the monolithic TopoJSON (split via split_topo.py)
MONOLITHIC_COUNTRIES = {"EE", "LV", "LT", "FI", "NO", "SE", "DE", "DK", "AD", "LU", "BE", "AT", "CZ", "GB"}

# Countries with standalone TopoJSON files
STANDALONE_COUNTRIES = {"IS", "ES", "FR", "PL", "PT", "NL", "IT", "IE", "SI", "BG", "SK", "HR", "CY", "GR", "HU", "MT", "RO", "AL", "XK", "ME", "BA", "RS", "MK", "UA", "MD", "LI", "SM", "GE", "AM", "AZ", "BY", "TR"}

# Countries that use name-based matching (OSM IDs differ between seed data and TopoJSON)
NAME_MATCHED_COUNTRIES = set()  # All countries now use ID matching

# Countries with incomplete topo coverage (boundary fetch got fewer features than seed data).
# These use a lower match threshold until their topo files are regenerated.
PARTIAL_TOPO_COUNTRIES = {
    "AM",  # 14 of 46 municipalities have boundaries
    "AZ",  # Only 1 feature fetched (Overpass returned incomplete data)
    "BA",  # Brčko District boundary missing
    "DE",  # ~425 Gemeinden missing (Overpass didn't return all admin_level=8)
    "GE",  # Gali, Ochamchire (occupied Abkhazia) boundaries missing
    "TR",  # Nevşehir Province boundary missing
    "UA",  # Topo has oblasts (admin_level=4), seed has raions (admin_level=6)
}

ALL_COUNTRIES = MONOLITHIC_COUNTRIES | STANDALONE_COUNTRIES

# Minimum expected features per country (catches collapsed/empty files)
MIN_FEATURES = {
    "EE": 70, "LV": 40, "LT": 55, "FI": 300, "NO": 350, "SE": 280,
    "DE": 395, "DK": 95, "AD": 7, "LU": 95, "BE": 560, "AT": 2070, "CZ": 75,
    "IS": 60, "ES": 50, "FR": 90, "PL": 370, "PT": 300, "NL": 330,
    "IT": 100, "IE": 25, "SI": 200, "BG": 25, "SK": 70, "GB": 280,
    "HR": 530, "CY": 15, "GR": 320, "HU": 170, "MT": 60, "RO": 40,
    "AL": 55, "XK": 30, "ME": 20, "BA": 100,
    "RS": 30, "MK": 70, "UA": 20, "MD": 30, "LI": 10, "SM": 8,
    "GE": 60, "AM": 10, "AZ": 1, "BY": 110, "TR": 75,
}


@pytest.fixture
def manifest():
    with open(MANIFEST_PATH) as f:
        return json.load(f)


@pytest.fixture
def data_json():
    if not DATA_PATH.exists():
        pytest.skip("data.json not found (run preprocess first)")
    with open(DATA_PATH) as f:
        return json.load(f)


def get_muni_filenames(manifest, cc):
    """Get municipality filename(s) from manifest, handling both string and object formats."""
    entry = manifest[cc]["files"]["municipality"]
    if isinstance(entry, str):
        return [entry]
    if isinstance(entry, dict):
        return list(entry.keys())
    return []


class TestManifestIntegrity:
    def test_all_countries_in_manifest(self, manifest):
        for cc in ALL_COUNTRIES:
            assert cc in manifest, f"{cc} missing from manifest.json"

    def test_manifest_files_exist(self, manifest):
        for cc, info in manifest.items():
            for level, entry in info["files"].items():
                if isinstance(entry, str):
                    path = TOPO_DIR / entry
                    assert path.exists(), f"{cc} {level}: {entry} not found"
                elif isinstance(entry, dict):
                    for filename in entry:
                        path = TOPO_DIR / filename
                        assert path.exists(), f"{cc} {level}: {filename} not found"

    def test_manifest_has_municipality_level(self, manifest):
        for cc in ALL_COUNTRIES:
            assert "municipality" in manifest[cc]["files"], (
                f"{cc} missing municipality level in manifest"
            )


def load_topo_geometries(manifest, cc):
    """Load all municipality geometries, handling multi-file manifest entries."""
    filenames = get_muni_filenames(manifest, cc)
    all_geoms = []
    for filename in filenames:
        path = TOPO_DIR / filename
        if not path.exists():
            continue
        with open(path) as f:
            topo = json.load(f)
        obj = list(topo["objects"].keys())[0]
        all_geoms.extend(topo["objects"][obj]["geometries"])
    return all_geoms


class TestTopoFeatureIds:
    """Verify that TopoJSON features have IDs matching data.json."""

    @pytest.mark.parametrize("cc", sorted(MONOLITHIC_COUNTRIES))
    def test_monolithic_country_has_feature_ids(self, cc, manifest):
        geoms = load_topo_geometries(manifest, cc)

        with_ids = sum(1 for g in geoms if g.get("id"))
        assert with_ids == len(geoms), (
            f"{cc}: {len(geoms) - with_ids} features missing IDs "
            f"(have {with_ids}/{len(geoms)})"
        )

    @pytest.mark.parametrize("cc", sorted(STANDALONE_COUNTRIES))
    def test_standalone_country_has_feature_ids(self, cc, manifest):
        if cc not in manifest:
            pytest.skip(f"{cc} not in manifest")
        geoms = load_topo_geometries(manifest, cc)

        with_ids = sum(1 for g in geoms if g.get("id"))
        # Allow up to 2% missing IDs (name-based fallback handles these)
        pct = with_ids / len(geoms) * 100 if geoms else 0
        assert pct >= 98, (
            f"{cc}: {len(geoms) - with_ids} features missing IDs "
            f"(have {with_ids}/{len(geoms)}, {pct:.0f}%)"
        )


class TestTopoFeatureCount:
    """Catch regressions where a country's TopoJSON collapses to too few features."""

    @pytest.mark.parametrize("cc", sorted(ALL_COUNTRIES))
    def test_minimum_feature_count(self, cc, manifest):
        if cc not in manifest:
            pytest.skip(f"{cc} not in manifest")
        geoms = load_topo_geometries(manifest, cc)
        n = len(geoms)
        expected = MIN_FEATURES.get(cc, 1)
        assert n >= expected, (
            f"{cc}: only {n} features (expected >= {expected}). "
            f"TopoJSON may have been corrupted."
        )


class TestTopoDataMatching:
    """Verify that data.json OSM IDs match TopoJSON feature IDs."""

    @pytest.mark.parametrize("cc", sorted(ALL_COUNTRIES))
    def test_data_matches_topo(self, cc, manifest, data_json):
        if cc not in manifest:
            pytest.skip(f"{cc} not in manifest")

        # Get data.json entries for this country
        entries = [
            m for m in data_json["municipalities"].values()
            if m.get("country") == cc and m.get("osm_relation_id")
        ]
        if not entries:
            pytest.skip(f"No {cc} entries in data.json")

        data_osm_ids = {
            f"relation/{m['osm_relation_id']}" for m in entries
        }

        # Get topo feature IDs (handles multi-file manifest)
        geoms = load_topo_geometries(manifest, cc)
        topo_ids = {g["id"] for g in geoms if g.get("id")}

        # Check overlap
        matched = data_osm_ids & topo_ids
        match_pct = len(matched) / len(data_osm_ids) * 100 if data_osm_ids else 0

        # Countries with name-based matching have different OSM IDs — skip ID check
        if cc in NAME_MATCHED_COUNTRIES:
            # Verify name-based matching works instead
            topo_names = {
                g.get("properties", {}).get("name", "").lower()
                for g in geoms if g.get("properties", {}).get("name")
            }
            data_names = {m["name"].lower() for m in entries}
            name_matched = data_names & topo_names
            assert len(name_matched) >= len(data_names) * 0.5, (
                f"{cc}: only {len(name_matched)}/{len(data_names)} names match topo features"
            )
            return

        # Countries with partial topo use a lower threshold
        if cc in PARTIAL_TOPO_COUNTRIES:
            # Just verify that whatever topo features exist have valid IDs
            assert len(topo_ids) >= MIN_FEATURES.get(cc, 1), (
                f"{cc}: topo has {len(topo_ids)} features "
                f"(expected >= {MIN_FEATURES.get(cc, 1)})"
            )
            return

        # At least 80% of data entries should match topo features
        assert match_pct >= 80, (
            f"{cc}: only {len(matched)}/{len(data_osm_ids)} data entries "
            f"({match_pct:.0f}%) match topo features. "
            f"Map polygons will appear gray."
        )


# Gap noti pre-esistenti (legacy coverage debt). Il test fallisce solo
# su gap NUOVI oltre questi — pattern "ratchet": il debito noto è
# congelato e visibile, le regressioni vengono bloccate.
#
# Per "chiudere" un gap: aggiungi/correggi il polygon nel topo, poi
# rimuovi il nome da qui. Se rimuovi un polygon esistente per errore,
# il test fallisce perché il nome non è (ancora) in allowlist.
#
# IT: 7 comuni piccoli senza polygon nel municipality topo (VdA/Friuli/
# Sardegna) — coverage da completare via fetch_it_boundaries.
# Altri: gap pre-esistenti del fork Baltic, non legati al progetto IT.
KNOWN_TOPO_GAPS = {
    "EE": {"Toila vald"},
    "ES": {"Altza", "Canillejas", "Formentera", "Los Molinos",
           "Melilla", "Oza-Cesuras", "Peña", "Valley of Aibar"},
    "GB": {"Antrim and Newtownabbey", "Ards and North Down",
           "Armagh City, Banbridge and Craigavon", "Belfast",
           "Causeway Coast and Glens", "City of Portsmouth",
           "City of Southampton", "Cumberland", "Derry City and Strabane",
           "Fermanagh and Omagh", "Isle of Man",
           "Lisburn and Castlereagh", "Mid Ulster",
           "Newry, Mourne and Down", "Reading"},
    "IT": {"Comune di Challand-Saint-Anselme", "Comune di Gressan",
           "Comune di Latisana", "Comune di Osini",
           "Comune di Remanzacco", "Comune di Santa Maria La Longa",
           "Comune di Villanovafranca"},
    "LV": {"Rīga"},
    "RS": {"Palilula City Municipality", "Trgovište Municipality",
           "Žagubica Municipality"},
}


class TestZeroGaps:
    """Ensure every data entry with an OSM ID has a matching TopoJSON polygon.

    This is the definitive test for map coverage — any entry failing this
    test will appear as a white gap on the map.
    """

    def test_no_gaps_across_all_countries(self, manifest, data_json):
        """Ogni entità a LIVELLO MUNICIPIO con OSM ID deve avere un polygon
        nel municipality topo. I gap noti pre-esistenti sono in
        KNOWN_TOPO_GAPS; il test fallisce solo su gap nuovi (regressioni).

        Scoping IT: il seed IT è multi-tier (REG/PRO/CMM/COM) in un solo
        file. Solo IT-COM-* (veri comuni) appartiene al municipality topo;
        IT-REG/PRO/CMM hanno i loro livelli region/district. Quindi per IT
        controlliamo solo IT-COM-*.
        """
        new_gaps = {}

        for cc in sorted(ALL_COUNTRIES):
            if cc not in manifest:
                continue
            if cc in PARTIAL_TOPO_COUNTRIES:
                continue

            entries = [
                m for m in data_json["municipalities"].values()
                if m.get("country") == cc and m.get("osm_relation_id")
            ]
            # IT: solo entità a livello municipio (IT-COM-*). REG/PRO/CMM
            # vivono nei topo region/district, non nel municipality.
            if cc == "IT":
                entries = [
                    m for m in entries
                    if (m.get("bfs") or m.get("id") or "").startswith("IT-COM-")
                ]
            if not entries:
                continue

            geoms = load_topo_geometries(manifest, cc)
            if not geoms:
                missing = [m["name"] for m in entries]
            else:
                topo_ids = {g["id"] for g in geoms if g.get("id")}
                missing = [
                    m["name"]
                    for m in entries
                    if f"relation/{m['osm_relation_id']}" not in topo_ids
                ]
            # Sottrai i gap noti pre-esistenti (allowlist).
            allowed = KNOWN_TOPO_GAPS.get(cc, set())
            unexpected = [name for name in missing if name not in allowed]
            if unexpected:
                new_gaps[cc] = unexpected

        if new_gaps:
            total = sum(len(v) for v in new_gaps.values())
            details = "; ".join(
                f"{cc}: {len(names)} ({', '.join(names[:3])}{'...' if len(names) > 3 else ''})"
                for cc, names in sorted(new_gaps.items())
            )
            pytest.fail(
                f"{total} NUOVE municipalities senza map polygon (oltre i gap "
                f"noti in KNOWN_TOPO_GAPS): {details}"
            )


class TestRegionFiles:
    """Verify region-level TopoJSON files exist and have features."""

    @pytest.mark.parametrize("cc", sorted(ALL_COUNTRIES))
    def test_region_file_has_features(self, cc, manifest):
        if cc not in manifest:
            pytest.skip(f"{cc} not in manifest")
        region_file = manifest[cc]["files"].get("region")
        if not region_file:
            pytest.skip(f"{cc} has no region level")
        if not isinstance(region_file, str):
            pytest.skip(f"{cc} region is multi-file")
        path = TOPO_DIR / region_file
        if not path.exists():
            pytest.skip(f"{region_file} not found")
        with open(path) as f:
            topo = json.load(f)
        obj = list(topo["objects"].keys())[0]
        n = len(topo["objects"][obj]["geometries"])
        # Countries with very few municipalities may have only 1 region
        min_regions = 1 if MIN_FEATURES.get(cc, 1) <= 1 else 2
        assert n >= min_regions, (
            f"{cc} region file has only {n} features (expected >= {min_regions})"
        )

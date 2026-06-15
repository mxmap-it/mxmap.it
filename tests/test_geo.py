"""Test del crosswalk geografico (src/mail_sovereignty/geo.py).

Verifica la tabella regioni, l'indice ISTAT (con alias dei codici storici) e la
risoluzione comune→regione, incluso il fallback onesto a 'Sconosciuta'.
"""

from mail_sovereignty.geo import (
    REGIONI,
    SCONOSCIUTA,
    build_istat_index,
    resolve_geo,
)

ISTAT = [
    {
        "codice_istat": "042002",
        "codici_storici": [],
        "denominazione_it": "Ancona",
        "codice_regione": "11",
        "sigla_auto": "AN",
    },
    {
        "codice_istat": "015146",
        "codici_storici": ["015146-old"],
        "denominazione_it": "Milano",
        "codice_regione": "03",
        "sigla_auto": "MI",
    },
]


def test_regioni_table():
    assert len(REGIONI) == 20
    assert REGIONI["01"] == ("Piemonte", "Nord")
    assert REGIONI["19"][0] == "Sicilia" and REGIONI["20"][0] == "Sardegna"
    assert {m for _, m in REGIONI.values()} == {"Nord", "Centro", "Sud", "Isole"}


def test_index_with_aliases():
    idx = build_istat_index(ISTAT)
    assert idx["042002"]["denominazione_it"] == "Ancona"
    assert idx["015146-old"]["denominazione_it"] == "Milano"  # alias storico


def test_resolve_known():
    idx = build_istat_index(ISTAT)
    g = resolve_geo("042002", idx)
    assert g["regione"] == "Marche" and g["macroarea"] == "Centro"
    assert g["provincia"] == "AN" and g["comune"] == "Ancona"
    assert g["codice_regione"] == "11"


def test_resolve_via_alias():
    idx = build_istat_index(ISTAT)
    assert resolve_geo("015146-old", idx)["regione"] == "Lombardia"


def test_resolve_sardegna_legacy():
    # i codici provincia legacy sardi (112-119) non sono nel crosswalk ma la
    # regione è certa: devono risolvere a Sardegna (asse "per aree" completo).
    idx = build_istat_index(ISTAT)  # nessun codice 11X nella fixture
    for code in ("118006", "112050", "119003"):
        g = resolve_geo(code, idx)
        assert g["regione"] == "Sardegna" and g["macroarea"] == "Isole"
        assert g["codice_regione"] == "20"
        assert g["comune"] is None  # comune non ricavabile dal codice rotto


def test_resolve_unknown_and_none():
    idx = build_istat_index(ISTAT)
    for code in ("999999", None, ""):
        g = resolve_geo(code, idx)
        assert g["regione"] == SCONOSCIUTA and g["macroarea"] == SCONOSCIUTA
        assert g["comune"] is None and g["codice_regione"] is None


def test_resolve_code_without_region_mapping():
    idx = build_istat_index([{"codice_istat": "x", "codice_regione": "99"}])
    g = resolve_geo("x", idx)
    assert g["regione"] == SCONOSCIUTA  # codice regione 99 non in tabella
    assert g["provincia"] is None

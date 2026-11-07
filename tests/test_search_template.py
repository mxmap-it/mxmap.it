"""Contratto della Ricerca Ente — vista Security Gateway + diagnostica (#28).

La pagina templates/it_search_template.html è statica e senza build step:
questi test fissano il contratto tra la pagina, il dataset pubblico
(dist/mxmap_it_dataset.json, campi uid/gateway_category/gateway_keyword) e
la sorgente diagnostica lazy (data-detail.json, keyed by uid). Se un refactor
rimuove un filtro, una colonna o il join diagnostico, qui diventa rosso.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TPL_PATH = ROOT / "templates" / "it_search_template.html"
DATASET_SCRIPT = ROOT / "scripts" / "build_public_dataset.py"


@pytest.fixture(scope="module")
def tpl() -> str:
    assert TPL_PATH.exists(), "template Ricerca Ente mancante"
    return TPL_PATH.read_text(encoding="utf-8")


def test_gateway_filter_present_with_all_modes(tpl: str) -> None:
    assert 'id="filter-gateway"' in tpl, "manca il select filtro gateway"
    for mode in ("__any__", "__security__", "__vendor__", "__none__"):
        assert f'value="{mode}"' in tpl, f"manca la modalità filtro {mode}"


def test_gateway_column_and_colspan_consistent(tpl: str) -> None:
    assert 'data-key="gateway"' in tpl, "manca la colonna Gateway nella thead"
    n_th = len(re.findall(r"<th\b", tpl))
    assert n_th == 11, f"attese 11 colonne, trovate {n_th}"
    # ogni riga di servizio (loading / vuoto / errore) deve coprire 11 colonne
    assert 'colspan="10"' not in tpl, "colspan non aggiornato alla nuova colonna"
    assert tpl.count('colspan="11"') >= 3, "righe di servizio senza colspan=11"


def test_filter_logic_uses_gateway_category(tpl: str) -> None:
    assert "gateway_category" in tpl
    assert "'security'" in tpl and "'vendor-relay'" in tpl


def test_diag_toggle_with_lazy_detail_join(tpl: str) -> None:
    assert 'id="diag-toggle"' in tpl, "manca il tick modalità diagnostica"
    assert "data-detail.json" in tpl, "manca la sorgente diagnostica lazy"
    assert "ensureDiagLoaded" in tpl, "manca il lazy-load della diagnostica"
    assert "diagPanelHTML" in tpl, "manca il pannello diagnostico per riga"
    # il join avviene per uid (chiave di data.json / data-detail.json)
    assert re.search(r"diagById\[r\.uid\]", tpl), "join diagnostica non per uid"


def test_diag_report_link_prefills_github_issue(tpl: str) -> None:
    assert "buildDiagReportURL" in tpl
    assert "issues/new" in tpl
    assert "Segnala anomalia" in tpl
    assert "[Segnalazione dato]" in tpl  # convenzione issue (cfr. #25)


def test_deeplink_gateway_and_diag(tpl: str) -> None:
    assert "URLSearchParams" in tpl
    assert "'gateway'" in tpl or '"gateway"' in tpl
    assert "'diag'" in tpl or '"diag"' in tpl
    assert "applyURLParams" in tpl and "updateURL" in tpl


def test_dataset_script_exposes_fields_the_page_consumes() -> None:
    src = DATASET_SCRIPT.read_text(encoding="utf-8")
    for field in ('"uid"', '"gateway_category"', '"gateway_keyword"'):
        assert field in src, f"build_public_dataset non espone {field}"
    assert "GATEWAY_CATEGORIES" in src, "categorie gateway non importate"

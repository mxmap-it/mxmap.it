"""Invarianti sui DATI COMMITTATI — tripwire anti-rigenerazione.

Incidente 2026-09: la cache di geocoding delle scuole non era mai stata
committata; ogni nightly rigenerava gli artefatti derivati con la lista punti
VUOTA e la vista Scuole è rimasta silenziosamente rotta per settimane (nessun
errore: solo dati che collassano a zero). Direttiva di progetto: "dobbiamo
essere resilienti rispetto a queste failure di rigenerazione" e "ciò che è
stato prodotto deve esistere nello storico git; se esisteva, si RIPRISTINA,
non si rigenera".

Questi test fissano dei PAVIMENTI sugli artefatti committati: un rebuild che
fa collassare un dataset prima popolato deve diventare ROSSO, mai passare
inosservato. Sono la seconda linea di difesa dopo le guardie anti-shrink
negli script (aggregate_istruzione_per_comune.py, geocode_istruzione.py),
che restano la prima: i push dei dati della nightly avvengono con
GITHUB_TOKEN e NON ri-triggherano la CI, quindi qui si intercettano
regressioni su push umani/PR e nei run manuali.

I pavimenti sono deliberatamente CONSERVATIVI (≈70-90% del valore atteso):
devono scattare sul collasso, non sul rumore fisiologico di IndicePA.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(rel: str) -> dict:
    p = ROOT / rel
    assert p.exists(), f"artefatto committato mancante: {rel}"
    return json.loads(p.read_text(encoding="utf-8"))


def test_geocode_cache_floor() -> None:
    """La cache di geocoding scuole (artefatto storico, ripristinato dal
    server 2026-09-29) non deve mai collassare sotto ~7000 punti."""
    d = _load("data/it_istruzione_points.json")
    pts = d.get("points", {})
    assert len(pts) >= 7000, f"cache geocoding collassata: {len(pts)} punti"


def test_istruzione_aggregate_points_floor() -> None:
    """L'aggregato per-comune deve portare i punti scuola (input della
    vista Scuole): lista vuota = incidente 2026-09 che si ripete."""
    d = _load("data/it_istruzione_by_comune.json")
    assert len(d.get("points", [])) >= 7000, (
        f"aggregato istruzione senza punti: {len(d.get('points', []))} — "
        "input di geocoding mancante al rebuild?"
    )
    assert len(d.get("by_osm", {})) >= 2000, "choropleth istruzione collassato"


def test_data_regions_istruzione_points_floor() -> None:
    """data-regions.json è ciò che la mappa scarica: i marker Scuole vivono
    qui. È l'artefatto che è rimasto vuoto per settimane."""
    d = _load("data-regions.json")
    pts = d.get("countries", {}).get("IT", {}).get("istruzione_points", [])
    assert len(pts) >= 7000, f"istruzione_points in data-regions: {len(pts)}"


def test_public_dataset_gateway_fields_and_floors() -> None:
    """Il dataset pubblico (consumato dalla Ricerca Ente, #28) deve esporre i
    campi gateway e restare popolato: al run 2026-11-07 gli enti dietro
    gateway erano 3.454 (973 security, 2.481 vendor/relay) — pavimenti ~70%.
    """
    d = _load("dist/mxmap_it_dataset.json")
    fields = d.get("_meta", {}).get("fields", [])
    for f in ("uid", "gateway", "gateway_category", "gateway_keyword"):
        assert f in fields, f"campo {f} assente dal dataset pubblico"
    rows = d.get("rows", [])
    assert len(rows) >= 20000, f"dataset pubblico collassato: {len(rows)} righe"
    with_gw = [r for r in rows if r.get("gateway")]
    assert len(with_gw) >= 2500, f"enti dietro gateway: {len(with_gw)}"
    cats = {r.get("gateway_category") for r in with_gw}
    assert cats <= {"security", "vendor-relay"}, f"categorie inattese: {cats}"
    n_sec = sum(1 for r in with_gw if r["gateway_category"] == "security")
    n_ven = sum(1 for r in with_gw if r["gateway_category"] == "vendor-relay")
    assert n_sec >= 600, f"security gateway collassati: {n_sec}"
    assert n_ven >= 1500, f"vendor/relay collassati: {n_ven}"


def test_data_detail_floor_for_diagnostics() -> None:
    """data-detail.json è la sorgente diagnostica lazy della Ricerca Ente
    (#28) oltre che dei popup mappa: deve coprire ~tutti gli enti."""
    d = _load("data-detail.json")
    assert len(d) >= 20000, f"data-detail collassato: {len(d)} enti"
    sample = next(iter(d.values()))
    assert "mx" in sample or "reason" in sample, "entry diagnostica senza campi"


def test_pa_centrale_table_floor_and_armed_forces() -> None:
    """La tabella PA Centrale deve restare popolata e contenere le Forze
    Armate (aggiunte manuali al seed, 2026-09: erano sparite perché il
    generatore non era in nightly e la tabella era stantia)."""
    d = _load("data/reports/it_pa_centrale_table.json")
    rows = d.get("rows", [])
    assert len(rows) >= 50, f"tabella PA Centrale collassata: {len(rows)} righe"
    ids = {r.get("id") for r in rows}
    for must in (
        "IT-C1-esercito",
        "IT-C1-marina_militare",
        "IT-C1-aeronautica_militare",
    ):
        assert must in ids, f"Forza Armata sparita dalla tabella PA Centrale: {must}"

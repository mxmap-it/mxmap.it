"""Regression invariants on data/municipalities_it.json.

These tests pin two structural properties of the IT seed produced by
scripts/fetch_indicepa.py and guarantee they never regress:

1. **No IT-COM-XXX id collisions.** Each IT-COM-XXX id corresponds to
   exactly one entity in the seed. The historical bug "UNCEM
   Delegazione Regionale del Lazio appears as Roma comune polygon"
   was a collision between IT-COM-058091 (Roma, the real comune) and
   IT-COM-058091 (UNCEM headquartered in Roma, mis-categorised L6 by
   IndicePA) — both sharing the same Codice_comune_ISTAT.

2. **All IT-COM-XXX entries are real Comuni.** Every entity with an
   IT-COM-XXX id must satisfy at least one of:
     - Denominazione_ente starts with "Comune" (case-insensitive)
     - codice_ipa is in the documented whitelist of ladin/bilingue
       comuni whose IndicePA name doesn't include the "Comune" prefix

If a new IndicePA entity violates these rules, this test fails and
forces a manual review (either add to the whitelist or fix the
categorisation in fetch_indicepa.py).
"""
import json
import re
from collections import Counter
from pathlib import Path

import pytest


SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "municipalities_it.json"

# Import the whitelist from the source of truth so the test stays in
# sync with the fetcher. We use importlib because scripts/ is not a
# package, but the constants are module-level.
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    "fetch_indicepa",
    str(Path(__file__).resolve().parent.parent / "scripts" / "fetch_indicepa.py"),
)
_fi = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_fi)
L6_NAME_EXCEPTIONS = _fi.L6_NAME_EXCEPTIONS

COMUNE_NAME_RE = re.compile(r"^\s*comune\b", re.IGNORECASE)
REGIONE_NAME_RE = re.compile(r"^\s*(regione\b|provincia\s+autonoma\b)", re.IGNORECASE)
PROVINCIA_NAME_RE = re.compile(
    r"^\s*(provincia\b|libero\s+consorzio\s+comunale\b)", re.IGNORECASE)
CMM_NAME_RE = re.compile(r"^\s*citt[aà]'?\s+metropolitana\b", re.IGNORECASE)


@pytest.fixture(scope="module")
def seed():
    if not SEED_PATH.exists():
        pytest.skip(f"{SEED_PATH} missing — run scripts/fetch_indicepa.py first")
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


def test_no_it_com_id_collisions(seed):
    """No two entries in the seed share the same IT-COM-XXX id."""
    it_com_ids = [e["id"] for e in seed if e.get("id", "").startswith("IT-COM-")]
    counts = Counter(it_com_ids)
    duplicates = {k: v for k, v in counts.items() if v > 1}
    assert not duplicates, (
        f"Found {len(duplicates)} duplicate IT-COM-XXX ids. Each id must be "
        f"unique because the frontend maps it to a single comune polygon. "
        f"Duplicates: {duplicates}"
    )


def test_all_it_com_entries_have_comune_name(seed):
    """Every IT-COM-XXX entry must be a real Comune (name starts with
    'Comune' or codice_ipa is in the documented whitelist)."""
    violations = []
    for e in seed:
        if not e.get("id", "").startswith("IT-COM-"):
            continue
        name = e.get("name", "") or ""
        codice_ipa = (e.get("ipa_codice_ipa") or "").strip().lower()
        if COMUNE_NAME_RE.match(name):
            continue
        if codice_ipa in L6_NAME_EXCEPTIONS:
            continue
        violations.append({
            "id": e["id"],
            "codice_ipa": codice_ipa,
            "name": name,
        })
    assert not violations, (
        f"{len(violations)} entries have IT-COM-XXX id but name does NOT "
        f"start with 'Comune' and codice_ipa is NOT in L6_NAME_EXCEPTIONS. "
        f"Either fix the IndicePA categorisation (they should be IT-CONS-*) "
        f"or add codice_ipa to L6_NAME_EXCEPTIONS in scripts/fetch_indicepa.py "
        f"with a justification.\nFirst 10 violations: {violations[:10]}"
    )


def test_all_it_reg_entries_have_regione_name(seed):
    """Ogni IT-REG-XXX deve avere nome che inizia con 'Regione' o 'Provincia
    Autonoma'. Le 30 anomalie L4 IndicePA (assemblee, consorzi, associazioni
    tematiche) finiscono correttamente come IT-CONS-*."""
    violations = [
        {"id": e["id"], "name": (e.get("name") or "")[:60]}
        for e in seed
        if e.get("id", "").startswith("IT-REG-")
        and not REGIONE_NAME_RE.match(e.get("name") or "")
    ]
    assert not violations, (
        f"{len(violations)} IT-REG-* entries non hanno nome 'Regione'. "
        f"First 5: {violations[:5]}"
    )


def test_all_it_pro_entries_have_provincia_name(seed):
    """Ogni IT-PRO-XXX deve avere nome 'Provincia' o 'Libero Consorzio'."""
    violations = [
        {"id": e["id"], "name": (e.get("name") or "")[:60]}
        for e in seed
        if e.get("id", "").startswith("IT-PRO-")
        and not PROVINCIA_NAME_RE.match(e.get("name") or "")
    ]
    assert not violations, (
        f"{len(violations)} IT-PRO-* non hanno nome 'Provincia'. "
        f"First 5: {violations[:5]}"
    )


def test_all_it_cmm_entries_have_cmm_name(seed):
    """Ogni IT-CMM-XXX deve avere nome 'Città Metropolitana'."""
    violations = [
        {"id": e["id"], "name": (e.get("name") or "")[:60]}
        for e in seed
        if e.get("id", "").startswith("IT-CMM-")
        and not CMM_NAME_RE.match(e.get("name") or "")
    ]
    assert not violations, (
        f"{len(violations)} IT-CMM-* non hanno nome 'Città Metropolitana'. "
        f"First 5: {violations[:5]}"
    )


def test_no_it_com_for_non_l6_categorie(seed):
    """No entry with non-L6 ipa_codice_categoria should have IT-COM-XXX id.
    The id namespace IT-COM-* is reserved for L6 Comuni."""
    violations = [
        {"id": e["id"], "categoria": e.get("ipa_codice_categoria"),
         "name": (e.get("name") or "")[:60]}
        for e in seed
        if e.get("id", "").startswith("IT-COM-")
        and (e.get("ipa_codice_categoria") or "").upper() != "L6"
    ]
    assert not violations, (
        f"{len(violations)} entries have IT-COM-XXX id but categoria != L6. "
        f"First 10: {violations[:10]}"
    )


# ============================================================================
# Cross-validation con ISTAT (fonte autoritativa dei comuni italiani)
# ============================================================================
ISTAT_PATH = Path(__file__).resolve().parent.parent / "data" / "istat_comuni.json"


@pytest.fixture(scope="module")
def istat_codes():
    """Set dei codici ISTAT validi (6 cifre alfanumeriche) caricati dal
    snapshot ISTAT in data/istat_comuni.json. Include sia i codici
    correnti sia i codici storici (110/107/103 province) perché
    IndicePA mappa ancora i comuni sardi sui codici 'vecchi' (111-118)
    invece dei nuovi post-riforma 2016. Skip se il file manca —
    indica all'utente come generarlo con scripts/fetch_istat_comuni.py."""
    if not ISTAT_PATH.exists():
        pytest.skip(
            f"{ISTAT_PATH} missing — run "
            f"`uv run python3 scripts/fetch_istat_comuni.py` to generate it."
        )
    payload = json.loads(ISTAT_PATH.read_text(encoding="utf-8"))
    codes = set()
    for c in payload["comuni"]:
        codes.add(c["codice_istat"])
        for storico in c.get("codici_storici") or []:
            codes.add(storico)
    return codes


@pytest.fixture(scope="module")
def istat_index():
    """Indice dei comuni ISTAT per codice → record completo (denominazione,
    codice catastale, regione, ecc.)."""
    if not ISTAT_PATH.exists():
        pytest.skip(f"{ISTAT_PATH} missing")
    payload = json.loads(ISTAT_PATH.read_text(encoding="utf-8"))
    return {c["codice_istat"]: c for c in payload["comuni"]}


def test_all_it_com_istat_codes_are_valid(seed, istat_codes):
    """Ogni IT-COM-XXX nel seed deve avere ipa_codice_comune_istat
    presente nella lista ufficiale ISTAT. Cattura comuni IndicePA con
    codice ISTAT obsoleto (es. comuni fusi non aggiornati upstream) o
    spurio."""
    violations = []
    for e in seed:
        if not e.get("id", "").startswith("IT-COM-"):
            continue
        istat = (e.get("ipa_codice_comune_istat") or "").strip()
        if istat not in istat_codes:
            violations.append({
                "id": e["id"],
                "istat": istat,
                "name": (e.get("name") or "")[:50],
                "ipa": e.get("ipa_codice_ipa"),
            })
    # Soglia: max 20 comuni con codice ISTAT non valido. Sopra questa soglia
    # il test fallisce e va investigato (probabile snapshot ISTAT obsoleto).
    assert len(violations) <= 20, (
        f"{len(violations)} IT-COM-* hanno codice ISTAT NON in elenco ISTAT "
        f"ufficiale. Probabili comuni fusi/aggiornamenti. Se il numero è "
        f"alto, rigenera lo snapshot con "
        f"`uv run python3 scripts/fetch_istat_comuni.py`.\n"
        f"First 10: {violations[:10]}"
    )


def test_seed_comuni_count_matches_istat(seed, istat_codes):
    """Il numero di IT-COM-* nel seed deve essere ±50 di quello ISTAT.
    Margine ampio per assorbire lag IndicePA su variazioni amministrative
    e i 2 comuni L6_NAME_EXCEPTIONS ladini."""
    seed_it_com = [e for e in seed if e.get("id", "").startswith("IT-COM-")]
    istat_count = len(istat_codes)
    seed_count = len(seed_it_com)
    diff = abs(seed_count - istat_count)
    assert diff <= 50, (
        f"Seed IT-COM-* count ({seed_count}) si discosta di {diff} da "
        f"ISTAT ({istat_count}). Soglia: 50. Possibile bug di filter o "
        f"snapshot ISTAT da rinfrescare."
    )


def test_no_orphan_it_com_istat_pairs(seed, istat_index):
    """Ogni IT-COM-XXX deve avere codice_istat che corrisponde all'id
    (cioè IT-COM-058091 deve avere ipa_codice_comune_istat=058091).
    Verifica che la mappatura id↔istat sia consistente."""
    violations = []
    for e in seed:
        eid = e.get("id", "")
        if not eid.startswith("IT-COM-"):
            continue
        id_istat = eid.split("-")[-1]  # IT-COM-058091 → "058091"
        field_istat = (e.get("ipa_codice_comune_istat") or "").strip()
        if id_istat != field_istat:
            violations.append({
                "id": eid,
                "ipa_codice_comune_istat_field": field_istat,
                "name": (e.get("name") or "")[:50],
            })
    assert not violations, (
        f"{len(violations)} entries hanno IT-COM-{{X}} ma "
        f"ipa_codice_comune_istat != X. First 5: {violations[:5]}"
    )

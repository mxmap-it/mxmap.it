"""Regression invariants on data/municipalities_it.json.

Documentazione completa: docs/SEED_VALIDATION.md

Questo file pinna 6 invarianti strutturali (I1-I6 in SEED_VALIDATION.md)
sul seed IT prodotto da scripts/fetch_indicepa.py, più meta-test sulla
whitelist L6_NAME_EXCEPTIONS e sullo schema del snapshot ISTAT.

I test si autoskippano in modo "graceful" quando le dipendenze esterne
mancano (data/municipalities_it.json, data/istat_comuni.json),
indicando all'utente il comando esatto per generarle.

Architettura difesa-in-profondita':
  1. fetch_indicepa.is_territorial() filtra i falsi territoriali a fetch-time
  2. Questi pytest catturano le anomalie residue post-fetch
  3. .github/workflows/nightly.yml esegue questi pytest prima del commit

Storia: il bug "UNCEM Delegazione Regionale del Lazio appare come
polygon di Roma" (commit c26a7358) ha rivelato 90 enti L6 mal-
categorizzati in IndicePA. Tutti correttamente riassegnati a IT-CONS-*
dal filtro positivo `^Comune\\b` aggiunto in quel commit.
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
def istat_payload():
    if not ISTAT_PATH.exists():
        pytest.skip(
            f"{ISTAT_PATH} missing — run "
            f"`uv run python3 scripts/fetch_istat_comuni.py` to generate it."
        )
    return json.loads(ISTAT_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def istat_codes_current(istat_payload):
    """Set dei codici ISTAT CORRENTI (solo edizione 2024+). Usato per
    verificare il count del seed (7896 comuni ufficiali)."""
    return {c["codice_istat"] for c in istat_payload["comuni"]}


@pytest.fixture(scope="module")
def istat_codes(istat_payload):
    """Set ESTESO di tutti i codici ISTAT mai validi (correnti + storici
    110/107/103 province). IndicePA mappa ancora i comuni sardi sui
    codici provincia pre-riforma 2016 (111-118). Usato per la
    cross-validation 'è un codice comune legittimo?'."""
    codes = set()
    for c in istat_payload["comuni"]:
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


@pytest.fixture(scope="module")
def istat_codici_catastali(istat_payload):
    """Set dei codici catastali ufficiali ISTAT (4 caratteri tipo 'A007',
    'H501'). Stabili nel tempo (un comune mantiene il codice catastale
    anche dopo fusioni provinciali), quindi più robusti del codice ISTAT
    numerico per validazione cross-source."""
    return {(c.get("codice_catastale") or "").upper()
            for c in istat_payload["comuni"] if c.get("codice_catastale")}


def test_all_it_com_cross_validate_against_istat(seed, istat_codes,
                                                   istat_codici_catastali):
    """Cross-validation OR su tre fonti ISTAT, per assorbire le
    inconsistenze IndicePA tipiche (codici legacy):

      1. ipa_codice_comune_istat in `istat_codes` (codici correnti +
         storici 110/107/103 province). Questo cattura ~99% dei comuni
         italiani inclusi quelli con codici Sardegna pre-2016.

      2. codice catastale estratto da ipa_codice_ipa nel pattern
         'c_<catastale>' presente in `istat_codici_catastali`.

    Il match riesce se ALMENO UNA delle due regole hit. Solo i comuni
    dove NESSUNA matcha sono violation reale (potenzialmente bug o
    snapshot ISTAT obsoleto).

    Le inconsistenze ISTAT vs IndicePA note:
      - Sardegna 2016: riforma province → IndicePA usa codici 11X,
        ISTAT pubblica 09X. Risolto da (1) con codici storici.
      - Fusioni comuni 2010+: IndicePA conserva codice catastale
        pre-fusione (Bellagio c_a744), ISTAT pubblica solo il nuovo
        (M335). Risolto da (1) (ISTAT numerico matcha sempre).
    """
    import re
    CATASTALE_RE = re.compile(r"^c_([a-z][a-z0-9]{3})$", re.IGNORECASE)
    n_match_istat = 0
    n_match_catastale = 0
    n_total = 0
    violations = []
    for e in seed:
        if not e.get("id", "").startswith("IT-COM-"):
            continue
        n_total += 1
        istat = (e.get("ipa_codice_comune_istat") or "").strip()
        ipa = (e.get("ipa_codice_ipa") or "").strip()
        m = CATASTALE_RE.match(ipa)
        catastale = m.group(1).upper() if m else None

        if istat in istat_codes:
            n_match_istat += 1
            continue
        if catastale and catastale in istat_codici_catastali:
            n_match_catastale += 1
            continue
        violations.append({
            "id": e["id"], "istat": istat, "ipa": ipa,
            "catastale": catastale, "name": (e.get("name") or "")[:50],
        })
    print(f"\n[info] ISTAT cross-validation: total={n_total} "
          f"match_istat={n_match_istat} match_catastale={n_match_catastale} "
          f"violations={len(violations)}")
    # Soglia: max 30 violazioni. Sotto questa soglia possiamo accettare
    # (snapshot ISTAT ±6 mesi vs IndicePA su variazioni amministrative).
    assert len(violations) <= 30, (
        f"{len(violations)} IT-COM-* non si cross-validano contro ISTAT "
        f"(né ipa_codice_comune_istat né codice catastale matchano). "
        f"Rigenera snapshot ISTAT o investiga upstream IndicePA.\n"
        f"First 10: {violations[:10]}"
    )


def test_seed_comuni_count_matches_istat(seed, istat_codes_current):
    """Il numero di IT-COM-* nel seed deve essere ±50 di quello ISTAT
    CORRENTE (7896 a gennaio 2024). Margine ampio per assorbire lag
    IndicePA su variazioni amministrative."""
    seed_it_com = [e for e in seed if e.get("id", "").startswith("IT-COM-")]
    istat_count = len(istat_codes_current)
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


# ============================================================================
# Meta-test sulla whitelist L6_NAME_EXCEPTIONS
# ============================================================================

def test_l6_exceptions_are_in_seed(seed):
    """Ogni codice_ipa in L6_NAME_EXCEPTIONS deve esistere nel seed.
    Se IndicePA un domani toglie il comune dal registro (es. dopo
    fusione), il commento della whitelist diventa stale e va aggiornato.
    """
    seed_ipa_codes = {(e.get("ipa_codice_ipa") or "").lower() for e in seed}
    stale = [exc for exc in L6_NAME_EXCEPTIONS
             if exc.lower() not in seed_ipa_codes]
    assert not stale, (
        f"L6_NAME_EXCEPTIONS contiene {len(stale)} codice_ipa NON presenti "
        f"nel seed corrente: {stale}. Probabilmente sono stati rimossi/fusi "
        f"da IndicePA. Aggiorna scripts/fetch_indicepa.py e questo test."
    )


def test_l6_exceptions_are_actually_l6_in_seed(seed):
    """Ogni eccezione L6_NAME_EXCEPTIONS deve avere ipa_codice_categoria=L6
    nel seed. Se IndicePA ricategorizza il comune (improbabile ma possibile),
    la whitelist potrebbe nascondere un bug futuro."""
    by_ipa = {(e.get("ipa_codice_ipa") or "").lower(): e for e in seed}
    violations = []
    for exc in L6_NAME_EXCEPTIONS:
        e = by_ipa.get(exc.lower())
        if e and (e.get("ipa_codice_categoria") or "").upper() != "L6":
            violations.append({
                "codice_ipa": exc,
                "categoria_attuale": e.get("ipa_codice_categoria"),
                "name": (e.get("name") or "")[:50],
            })
    assert not violations, (
        f"L6_NAME_EXCEPTIONS contiene {len(violations)} entries la cui "
        f"categoria IndicePA non è più L6: {violations}"
    )


def test_l6_exceptions_are_real_istat_comuni(seed, istat_codici_catastali):
    """Ogni L6_NAME_EXCEPTIONS deve essere un VERO comune ISTAT. Se la
    whitelist contiene un finto comune, è un bypass del filtro is_territorial
    e va rimosso."""
    import re
    CATASTALE_RE = re.compile(r"^c_([a-z][a-z0-9]{3})$", re.IGNORECASE)
    by_ipa = {(e.get("ipa_codice_ipa") or "").lower(): e for e in seed}
    violations = []
    for exc in L6_NAME_EXCEPTIONS:
        e = by_ipa.get(exc.lower())
        if not e:
            continue   # gestito da test_l6_exceptions_are_in_seed
        m = CATASTALE_RE.match(exc)
        if not m:
            violations.append({
                "codice_ipa": exc,
                "reason": "non in pattern c_<catastale>",
                "name": (e.get("name") or "")[:50],
            })
            continue
        catastale = m.group(1).upper()
        if catastale not in istat_codici_catastali:
            violations.append({
                "codice_ipa": exc,
                "catastale": catastale,
                "reason": "non in ISTAT catastali",
                "name": (e.get("name") or "")[:50],
            })
    assert not violations, (
        f"L6_NAME_EXCEPTIONS contiene {len(violations)} entries che NON "
        f"sono comuni ISTAT validi: {violations}. Rivedi la whitelist."
    )


# ============================================================================
# Meta-test sullo snapshot ISTAT
# ============================================================================

def test_istat_snapshot_well_formed(istat_payload):
    """Schema check sul snapshot ISTAT: assicura formato atteso, count
    ragionevole, no rows malformed."""
    assert "_meta" in istat_payload, "snapshot ISTAT senza _meta"
    assert "comuni" in istat_payload, "snapshot ISTAT senza array comuni"

    comuni = istat_payload["comuni"]
    assert 7800 <= len(comuni) <= 8000, (
        f"Conteggio comuni ISTAT inatteso: {len(comuni)}. Dovrebbe essere "
        f"tra 7800 (~ fusione max) e 8000 (~ split max). Verifica CSV."
    )

    # Schema: ogni comune ha i campi obbligatori
    required = ("codice_istat", "denominazione_it", "codice_catastale",
                "codice_regione", "codice_provincia")
    missing = []
    for i, c in enumerate(comuni):
        for f in required:
            if not c.get(f):
                missing.append((i, f, c.get("denominazione_it", "?")))
                break
    assert not missing, (
        f"{len(missing)} comuni ISTAT con campi mancanti. First 3: "
        f"{missing[:3]}"
    )

    # Codici ISTAT ben formati (6 cifre)
    bad_codes = [c["codice_istat"] for c in comuni
                 if not (len(c["codice_istat"]) == 6 and c["codice_istat"].isdigit())]
    assert not bad_codes, (
        f"{len(bad_codes)} codici ISTAT non sono 6-cifre: first 3 {bad_codes[:3]}"
    )

    # Codici catastali ben formati (4 char alfanum, primo è una lettera)
    bad_cat = [c["codice_catastale"] for c in comuni
               if not (len(c["codice_catastale"]) == 4
                       and c["codice_catastale"][0].isalpha())]
    assert len(bad_cat) <= 5, (   # ammettiamo qualche caso esotico
        f"{len(bad_cat)} codici catastali malformed: first 5 {bad_cat[:5]}"
    )


def test_istat_codes_no_duplicates(istat_payload):
    """Ogni codice ISTAT deve essere unico nel snapshot. Duplicati =
    bug nel parser o CSV ISTAT corrotto."""
    codes = [c["codice_istat"] for c in istat_payload["comuni"]]
    from collections import Counter as _C
    dups = {k: v for k, v in _C(codes).items() if v > 1}
    assert not dups, f"Duplicati nel snapshot ISTAT: {dups}"


def test_istat_catastali_no_duplicates(istat_payload):
    """Ogni codice catastale deve essere unico (1:1 con comune)."""
    cats = [c["codice_catastale"] for c in istat_payload["comuni"]
            if c.get("codice_catastale")]
    from collections import Counter as _C
    dups = {k: v for k, v in _C(cats).items() if v > 1}
    assert not dups, f"Duplicati codici catastali ISTAT: {dups}"


# ============================================================================
# Unit test sintetici di is_territorial() — copre i casi senza dipendere
# dal seed reale, utili per pinnare le regex senza dover regenerate il seed.
# ============================================================================

def test_is_territorial_l6_positive_cases():
    """is_territorial() deve accettare nomi standard 'Comune *'."""
    from importlib import util as _u
    _spec = _u.spec_from_file_location(
        "fetch_indicepa",
        str(Path(__file__).resolve().parent.parent / "scripts" / "fetch_indicepa.py"))
    _m = _u.module_from_spec(_spec)
    _spec.loader.exec_module(_m)
    is_terr = _m.is_territorial

    accepts = [
        ("Comune di Roma", "L6"),
        ("Comune di Bologna", "L6"),
        ("Comune Casciana Terme Lari", "L6"),    # fusione, manca "di"
        ("Comune Presicce - Acquarica", "L6"),    # fusione
        ("comune di milano", "L6"),               # lowercase
        ("COMUNE DI BARI", "L6"),                 # uppercase
    ]
    for name, cat in accepts:
        assert is_terr(name, cat), f"Doveva accettare: {name!r}"


def test_is_territorial_l6_negative_cases():
    """is_territorial() deve rifiutare i falsi 'comuni' IndicePA."""
    from importlib import util as _u
    _spec = _u.spec_from_file_location(
        "fetch_indicepa",
        str(Path(__file__).resolve().parent.parent / "scripts" / "fetch_indicepa.py"))
    _m = _u.module_from_spec(_spec)
    _spec.loader.exec_module(_m)
    is_terr = _m.is_territorial

    rejects = [
        ("UNCEM DELEGAZIONE REGIONALE DEL LAZIO", "L6"),
        ("ANCI Piemonte", "L6"),
        ("ANCI Veneto", "L6"),
        ("Patrimonio Mobilita Provincia di Rimini", "L6"),
        ("Acquedotto Consortile Biviere", "L6"),
        ("ATS Madonie Sud", "L6"),
        ("Federazione Regionale Agronomi Lombardia", "L6"),
        ("Consorzio Acquedotto Comuni Media Sabina", "L6"),
        # Caso edge: nome contiene "Comune" ma non all'inizio
        ("CONSORZIO RIUNITO STRADE VICINALI COMUNE ARCIDOSSO", "L6"),
    ]
    for name, cat in rejects:
        assert not is_terr(name, cat), (
            f"Doveva rifiutare: {name!r} (cat={cat})"
        )


def test_is_territorial_l6_exception_whitelist():
    """is_territorial() accetta i 2 comuni ladini via L6_NAME_EXCEPTIONS."""
    from importlib import util as _u
    _spec = _u.spec_from_file_location(
        "fetch_indicepa",
        str(Path(__file__).resolve().parent.parent / "scripts" / "fetch_indicepa.py"))
    _m = _u.module_from_spec(_spec)
    _spec.loader.exec_module(_m)

    assert _m.is_territorial(
        "San Giovanni di Fassa-Sen Jan", "L6", codice_ipa="c_m390")
    assert _m.is_territorial(
        "Montagna sulla strada del vino", "L6", codice_ipa="c_f392")
    # Stesso nome ma senza codice_ipa nella whitelist → rifiuto
    assert not _m.is_territorial(
        "San Giovanni di Fassa-Sen Jan", "L6", codice_ipa="not_in_whitelist")


def test_is_territorial_l4_l5_l45():
    """is_territorial() comportamento atteso per le altre categorie territoriali."""
    from importlib import util as _u
    _spec = _u.spec_from_file_location(
        "fetch_indicepa",
        str(Path(__file__).resolve().parent.parent / "scripts" / "fetch_indicepa.py"))
    _m = _u.module_from_spec(_spec)
    _spec.loader.exec_module(_m)
    is_terr = _m.is_territorial

    # L4 Regione
    assert is_terr("Regione Lazio", "L4")
    assert is_terr("Provincia Autonoma di Trento", "L4")
    assert not is_terr("Assemblea Regionale Siciliana", "L4")
    assert not is_terr("Associazione Nazionale degli Enti di Governo d'Ambito", "L4")

    # L5 Provincia
    assert is_terr("Provincia di Belluno", "L5")
    assert is_terr("Libero Consorzio Comunale di Agrigento", "L5")
    assert not is_terr("Unione Province D'Italia", "L5")
    assert not is_terr("Upi Veneto", "L5")

    # L45 Città Metropolitana
    assert is_terr("Città Metropolitana di Milano", "L45")
    assert is_terr("Citta Metropolitana di Roma", "L45")   # senza accento
    assert not is_terr("Patrimonio Mobilita Provincia di Rimini", "L45")

"""Pure URL/slug/display logic for the per-entity & geographic SEO pages (#15).

No I/O — fully unit-tested in ``tests/test_pages.py``. The page generator
(``scripts/build_entity_pages.py``) imports these helpers to assign **stable,
collision-free, SEO-friendly** URLs and to reuse the **canonical** sovereignty
model (``historicize.sovereignty_of`` / ``kpi.provider_to_sov4``) — never
re-deriving sovereignty here.

URL scheme (decisions of #15):
- entity : ``/ente/{provincia-sigla}/{nome-completo-ente-slug}/``  (full name)
- region : ``/aree/{regione}/``
- provincia: ``/aree/{regione}/{sigla}/``
- comune : ``/aree/{regione}/{sigla}/{comune}/``
- category: ``/categoria/{cluster-key}/``
- domain : ``/dominio/{dominio}/``  (lightweight alias → canonical to the entity)
"""

from __future__ import annotations

import re
import unicodedata

from mail_sovereignty import stats as _stats

# --- character folding: Italian accents + curly apostrophes ------------------
_TRANSLIT = str.maketrans(
    {
        "à": "a",
        "á": "a",
        "â": "a",
        "ä": "a",
        "ã": "a",
        "è": "e",
        "é": "e",
        "ê": "e",
        "ë": "e",
        "ì": "i",
        "í": "i",
        "î": "i",
        "ï": "i",
        "ò": "o",
        "ó": "o",
        "ô": "o",
        "ö": "o",
        "õ": "o",
        "ù": "u",
        "ú": "u",
        "û": "u",
        "ü": "u",
        "ç": "c",
        "ñ": "n",
        "’": "",
        "‘": "",
        "'": "",
        "`": "",
    }
)


def slugify(text: str, maxlen: int = 90) -> str:
    """Lowercase, accent-fold, drop apostrophes, hyphenate. ASCII-only output."""
    if not text:
        return ""
    t = text.strip().lower().translate(_TRANSLIT)
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    t = re.sub(r"-{2,}", "-", t)
    if len(t) > maxlen:
        t = t[:maxlen].rstrip("-")
    return t


def province_slug(sigla: str | None) -> str:
    """Province car-plate sigla → lowercase path token; '' → 'italia'."""
    s = (sigla or "").strip().lower()
    return s if s else "italia"


def region_slug(regione: str | None) -> str:
    return slugify(regione or "") or "italia"


def comune_slug(comune: str | None) -> str:
    return slugify(comune or "") or "na"


def _bfs_token(bfs: str) -> str:
    """Stable per-entity disambiguator: the unique trailing segment of the bfs."""
    seg = str(bfs).split("-")[-1]
    return slugify(seg) or "x"


def entity_name_slug(name: str | None) -> str:
    return slugify(name or "") or "ente"


def assign_entity_paths(entities: list[dict]) -> dict[str, str]:
    """Return ``{bfs: "/ente/{sigla}/{slug}/"}`` — deterministic, collision-free.

    Namespace = province sigla. A name unique within its province keeps the
    clean ``{slug}``; entities sharing ``(provincia, name-slug)`` are **all**
    suffixed with their stable bfs token, so each URL depends only on that
    entity's own (provincia, name, bfs) — independent of iteration order and
    stable across runs (a singleton only ever changes if a genuine namesake
    later appears in the same province; the generator logs the collision count).
    """
    groups: dict[tuple[str, str], list[dict]] = {}
    for e in entities:
        key = (province_slug(e.get("provincia")), entity_name_slug(e.get("name")))
        groups.setdefault(key, []).append(e)
    out: dict[str, str] = {}
    for (ps, ns), members in groups.items():
        if len(members) == 1:
            out[members[0]["bfs"]] = f"/ente/{ps}/{ns}/"
        else:
            for e in members:
                out[e["bfs"]] = f"/ente/{ps}/{ns}-{_bfs_token(e['bfs'])}/"
    return out


# --- geographic hub paths ----------------------------------------------------
def region_path(regione: str | None) -> str:
    return f"/aree/{region_slug(regione)}/"


def province_path(regione: str | None, sigla: str | None) -> str:
    return f"/aree/{region_slug(regione)}/{province_slug(sigla)}/"


def comune_path(regione: str | None, sigla: str | None, comune: str | None) -> str:
    return f"/aree/{region_slug(regione)}/{province_slug(sigla)}/{comune_slug(comune)}/"


def domain_alias_path(domain: str | None) -> str | None:
    """``/dominio/{dominio}/`` or None when there is no usable domain."""
    d = (domain or "").strip().lower()
    if not d or "." not in d:
        return None
    if not re.fullmatch(r"[a-z0-9.\-]+", d):
        return None
    return f"/dominio/{d}/"


# --- category (cluster) facets — reuse stats.CLUSTERS (single source) --------
# {bfs middle-code -> (cluster_key, cluster_label)}
_BFS_TO_CLUSTER: dict[str, tuple[str, str]] = {
    code: (key, label) for key, label, codes in _stats.CLUSTERS for code in codes
}
CLUSTER_LABELS: dict[str, str] = {key: label for key, label, _ in _stats.CLUSTERS}


def cluster_of(bfs: str) -> tuple[str, str]:
    """(cluster_key, label) for a bfs code; ('altri','Altri enti') if unmapped."""
    parts = str(bfs).split("-")
    code = parts[1] if len(parts) >= 2 else ""
    return _BFS_TO_CLUSTER.get(code, ("altri", "Altri enti"))


def category_path(cluster_key: str) -> str:
    return f"/categoria/{slugify(cluster_key) or 'altri'}/"


# --- canonical bucket colours (mirror scripts/build_frontend.py COLORS) -------
SOV6_COLORS: dict[str, str] = {
    "USA (CLOUD Act)": "#D42E2E",
    "Altri provider esteri": "#1E5FB4",
    "Italia — Cloud sovrano": "#009246",
    "Italia — Provider commerciali": "#2E7D32",
    "Italia — Infrastruttura autonoma": "#558B2F",
    "Sconosciuto": "#BFBFBF",
}
SOV4_COLORS: dict[str, str] = {
    "extra_eu": "#D42E2E",
    "eu_non_it": "#1E5FB4",
    "it": "#009246",
    "unknown": "#BFBFBF",
}


def sov6_color(bucket: str) -> str:
    return SOV6_COLORS.get(bucket, "#BFBFBF")


def sov4_color(sov4_key: str) -> str:
    return SOV4_COLORS.get(sov4_key, "#BFBFBF")

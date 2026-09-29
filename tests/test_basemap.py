"""Batteria funzionale RIGIDA del basemap della mappa (index.html).

Contesto (incidente 2026-09): CARTO ha messo a chiave/pagamento i basemap di
``basemaps.cartocdn.com`` che il fork originale usava keyless. I tile hanno
continuato a rispondere **HTTP 200** servendo però un segnaposto "API KEY
REQUIRED" — la mappa si è rotta in modo SILENZIOSO: nessun 4xx, nessun errore
in console, nessun check esistente in grado di accorgersene. Questa batteria
è il tripwire che mancava, su due livelli:

STRUTTURALI (offline, deterministici) — il config Leaflet dentro index.html
resta coerente: esattamente 2 layer basemap (base + labels), ordine degli
assi corretto per l'host usato (Esri = ``/tile/{z}/{y}/{x}``, slippy-map
classico = ``/{z}/{x}/{y}``), preconnect allineati agli host reali, niente
CARTO keyless (morto), attribuzione presente, estetica ``foreign-faded``.

FUNZIONALI (rete) — i tile VERI arrivano dal provider: HTTP 200 + Content-Type
immagine + dimensione minima su tile di TERRAFERMA (Roma, Milano — mai oceano,
che produce tile uniformi piccoli) + il check ANTI-SEGNAPOSTO decisivo: due
coordinate diverse devono restituire byte DIVERSI. Il watermark "API KEY
REQUIRED" è identico a ogni coordinata; due tile veri non lo sono mai. È
l'unico check capace di vedere questa classe di rottura dietro un 200.

Dove gira: in CI su ogni push/PR (job ``test``, pytest completo) e ogni notte
nel job dedicato ``basemap-battery`` di nightly.yml (drift lato provider →
rilevazione ≤24h con auto-issue, senza bloccare la pipeline dati).
"""

from __future__ import annotations

import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
UA = "mxmap.it-basemap-battery/1.0 (+https://mxmap.it)"

# Tile campione a z=6 sulla TERRAFERMA italiana, in ordine slippy-map (z, x, y):
# Roma e Milano. Land-only: le soglie di peso minimo non devono dare falsi
# positivi su tile uniformi di mare aperto.
SAMPLE_TILES = [(6, 34, 23), (6, 33, 22)]

# Un tile base di terraferma a z=6 pesa >5 KB; il segnaposto CARTO "API KEY
# REQUIRED" pesava 2049 byte fissi. I tile label sull'Italia portano toponimi
# ma possono essere sparsi → soglia più bassa.
MIN_BYTES_BASE = 3000
MIN_BYTES_LABELS = 800

TILELAYER_RE = re.compile(r"L\.tileLayer\(\s*'([^']+)'\s*,\s*\{(.*?)\}\s*\)", re.S)
PRECONNECT_RE = re.compile(r'<link rel="preconnect" href="https://([^"/]+)"')
LEAFLET_ASSET_RE = re.compile(r'https://unpkg\.com/[^"\']+\.(?:js|css)')


@pytest.fixture(scope="module")
def html() -> str:
    return INDEX.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def layers(html: str) -> list[tuple[str, str]]:
    """[(url_template, options_blob), …] dei L.tileLayer di index.html."""
    found = TILELAYER_RE.findall(html)
    assert found, "nessun L.tileLayer trovato in index.html: mappa senza basemap"
    return found


def _host(template: str) -> str:
    return urlsplit(template.replace("{s}", "a")).hostname or ""


def _tile_url(template: str, z: int, x: int, y: int) -> str:
    return (
        template.replace("{s}", "a")
        .replace("{r}", "")
        .replace("{z}", str(z))
        .replace("{x}", str(x))
        .replace("{y}", str(y))
    )


def _fetch(url: str, retries: int = 2) -> tuple[int, str, bytes]:
    """GET con retry/backoff sui soli errori transienti (rete, 5xx).

    Un 4xx viene restituito subito: è un esito da asserire, non da ritentare.
    """
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.status, r.headers.get("Content-Type", ""), r.read()
        except urllib.error.HTTPError as e:
            if e.code >= 500 and attempt < retries:
                last = e
                time.sleep(5 * (attempt + 1))
                continue
            return e.code, e.headers.get("Content-Type", ""), e.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            last = e
            if attempt < retries:
                time.sleep(5 * (attempt + 1))
    pytest.fail(f"irraggiungibile dopo {retries + 1} tentativi: {url} — {last!r}")


# ── STRUTTURALI (offline) ────────────────────────────────────────────────────


def test_exactly_two_basemap_layers(layers: list[tuple[str, str]]) -> None:
    """Contratto della mappa: layer base (con attribution) + layer label
    (pane dedicato 'toponimi', sopra i poligoni). Né più né meno."""
    assert len(layers) == 2, (
        f"attesi 2 L.tileLayer (base+labels), trovati {len(layers)}"
    )
    base_opts, label_opts = layers[0][1], layers[1][1]
    assert "attribution" in base_opts, (
        "layer base senza attribution (obbligo di licenza)"
    )
    assert "pane:" in label_opts.replace(" ", ""), (
        "layer toponimi senza pane dedicato: le etichette finirebbero sotto i poligoni"
    )
    assert "toponimi" in label_opts, (
        "layer toponimi non sul pane 'toponimi' (z 450: sopra poligoni, sotto marker)"
    )


def test_foreign_faded_aesthetic(html: str, layers: list[tuple[str, str]]) -> None:
    """Contratto estetico: il layer base porta className 'foreign-faded' (filtro
    CSS che desatura l'estero); il pane 'toponimi' ha la regola blend che fa
    emergere le etichette sopra i poligoni, con fallback nascosto (@supports)."""
    base_opts = layers[0][1]
    assert "foreign-faded" in base_opts, (
        f"className foreign-faded mancante sul layer base {layers[0][0]}"
    )
    assert ".leaflet-layer.foreign-faded" in html, (
        "manca il selettore CSS .leaflet-layer.foreign-faded: Leaflet mette la "
        "className sul CONTAINER del layer, non sui tile — senza questo "
        "selettore il filtro di desaturazione non si applica (bug storico del "
        "fork, invisibile coi tile CARTO/Esri già grigi)"
    )
    assert ".leaflet-toponimi-pane" in html, (
        "manca la regola CSS .leaflet-toponimi-pane (overlay toponimi)"
    )
    assert "mix-blend-mode: darken" in html, (
        "manca mix-blend-mode:darken sul pane toponimi: etichette invisibili "
        "o tile opachi sopra i poligoni"
    )
    assert "@supports (mix-blend-mode: darken)" in html, (
        "manca il guard @supports: senza blend il pane deve restare nascosto"
    )
    assert "createPane('toponimi')" in html, (
        "manca map.createPane('toponimi') in index.html"
    )


def _assert_axis_rule(template: str) -> None:
    """Regola ordine-assi per host. Un mismatch NON dà errori runtime (ogni
    coordinata è un tile valido altrove): la mappa mostra il posto sbagliato."""
    host = _host(template)
    for var in ("{z}", "{x}", "{y}"):
        assert var in template, f"variabile {var} assente nel template {template}"
    if host.endswith("arcgisonline.com"):
        assert "/tile/{z}/{y}/{x}" in template, (
            f"Esri usa l'ordine /tile/{{z}}/{{y}}/{{x}}, trovato: {template}"
        )
        assert "{s}" not in template and "{r}" not in template, (
            f"Esri non supporta subdomini {{s}} né retina {{r}}: {template}"
        )
    elif host.endswith("cartocdn.com") or host.endswith("openstreetmap.org"):
        assert "/{z}/{x}/{y}" in template, (
            f"{host} usa l'ordine slippy /{{z}}/{{x}}/{{y}}, trovato: {template}"
        )


def test_axis_order_matches_host(layers: list[tuple[str, str]]) -> None:
    """Codifichiamo la regola ordine-assi per ogni layer attivo."""
    for template, _ in layers:
        _assert_axis_rule(template)


def test_no_keyless_carto(layers: list[tuple[str, str]]) -> None:
    """basemaps.cartocdn.com senza ?key= è MORTO da 2026-09 (serve il
    segnaposto 'API KEY REQUIRED' con HTTP 200). Vietato reintrodurlo."""
    for template, _ in layers:
        if "cartocdn.com" in template:
            assert "key=" in template, (
                "CARTO keyless reintrodotto: dal 2026-09 serve solo watermark "
                f"'API KEY REQUIRED' (con HTTP 200!) — template: {template}"
            )


def test_preconnect_aligned_with_tile_hosts(
    html: str, layers: list[tuple[str, str]]
) -> None:
    """I preconnect nell'<head> devono coprire gli host dei tile (performance)
    e non puntare a CDN basemap che non usiamo più (igiene/privacy)."""
    preconnects = set(PRECONNECT_RE.findall(html))
    tile_hosts: set[str] = set()
    for template, opts in layers:
        if "{s}" in template:
            m = re.search(r"subdomains:\s*'([^']+)'", opts)
            for sub in m.group(1) if m else "a":
                tile_hosts.add(urlsplit(template.replace("{s}", sub)).hostname or "")
        else:
            tile_hosts.add(_host(template))
    for h in tile_hosts:
        assert h in preconnects, f"manca <link rel=preconnect> per l'host tile {h}"
    stale = {
        p
        for p in preconnects
        if ("cartocdn" in p or "arcgisonline" in p or "tile.openstreetmap" in p)
        and p not in tile_hosts
    }
    assert not stale, f"preconnect a CDN basemap non più usati: {sorted(stale)}"


# ── FUNZIONALI (rete) ────────────────────────────────────────────────────────


def _assert_real_tiles(template: str, min_bytes: int) -> None:
    payloads = []
    for z, x, y in SAMPLE_TILES:
        url = _tile_url(template, z, x, y)
        status, ctype, body = _fetch(url)
        assert status == 200, f"tile {url}: HTTP {status}"
        assert ctype.startswith("image/"), f"tile {url}: Content-Type '{ctype}'"
        assert len(body) >= min_bytes, (
            f"tile {url}: {len(body)} byte < soglia {min_bytes} — probabile "
            "segnaposto/errore mascherato da 200 (classe-incidente CARTO)"
        )
        payloads.append(body)
    assert payloads[0] != payloads[1], (
        f"ANTI-SEGNAPOSTO: {template} restituisce byte IDENTICI per Roma e "
        "Milano — è un watermark uguale ovunque (es. 'API KEY REQUIRED'), "
        "non un basemap vero"
    )


def test_base_tiles_are_real(layers: list[tuple[str, str]]) -> None:
    """Il layer base serve tile veri: 200 + image/* + peso minimo + tile
    diversi in posti diversi."""
    _assert_real_tiles(layers[0][0], MIN_BYTES_BASE)


def test_label_tiles_are_real(layers: list[tuple[str, str]]) -> None:
    """Idem per il layer dei toponimi (soglia più bassa: i label sono sparsi)."""
    _assert_real_tiles(layers[1][0], MIN_BYTES_LABELS)


def test_leaflet_cdn_assets_reachable(html: str) -> None:
    """Leaflet/markercluster/topojson da unpkg: ogni asset richiesto dalla
    pagina risponde 200 con un corpo non banale."""
    assets = sorted(set(LEAFLET_ASSET_RE.findall(html)))
    assert assets, "nessun asset unpkg trovato in index.html (regex rotta?)"
    for url in assets:
        status, _, body = _fetch(url)
        assert status == 200, f"asset {url}: HTTP {status}"
        # Soglia bassa di proposito: MarkerCluster.css pesa 872 byte legittimi.
        assert len(body) > 500, f"asset {url}: solo {len(body)} byte"


# ── RISERVA + FAILOVER (#26) ─────────────────────────────────────────────────

FALLBACK_RE = re.compile(r"const FALLBACK_(BASE|LABELS)\s*=\s*'([^']+)'")


@pytest.fixture(scope="module")
def fallbacks(html: str) -> dict[str, str]:
    """{'BASE': url, 'LABELS': url} della riserva keyless dichiarata nel
    failover runtime di index.html."""
    found = dict(FALLBACK_RE.findall(html))
    assert set(found) == {"BASE", "LABELS"}, (
        f"template di riserva FALLBACK_BASE/FALLBACK_LABELS non trovati: {found}"
    )
    return found


def test_fallback_templates_valid(fallbacks: dict[str, str]) -> None:
    """La riserva deve essere keyless, su host noto e con l'ordine assi giusto
    (il trabocchetto Esri: /tile/{z}/{y}/{x}, invertito rispetto a slippy)."""
    for name, template in fallbacks.items():
        assert "key=" not in template and "apikey" not in template.lower(), (
            f"la riserva {name} non deve richiedere chiavi: {template}"
        )
        _assert_axis_rule(template)


def test_fallback_tiles_are_real(fallbacks: dict[str, str]) -> None:
    """La riserva viene verificata OGNI GIORNO con gli stessi criteri del
    provider primario (200 + image/* + peso + anti-segnaposto): non deve
    scoprirsi morta il giorno in cui serve davvero."""
    _assert_real_tiles(fallbacks["BASE"], MIN_BYTES_BASE)
    _assert_real_tiles(fallbacks["LABELS"], MIN_BYTES_LABELS)


def test_failover_wiring_present(html: str) -> None:
    """Il meccanismo di failover deve restare cablato: contatore tileerror
    sul layer base, soglia, swap dei DUE layer, hook di test manuale."""
    for marker in (
        "on('tileerror'",
        "FAILOVER_THRESHOLD",
        "activateBasemapFailover",
        "removeLayer(osmBaseLayer)",
        "removeLayer(osmLabelLayer)",
        "window.__forceBasemapFailover",
    ):
        assert marker in html, f"failover basemap: manca '{marker}' in index.html"

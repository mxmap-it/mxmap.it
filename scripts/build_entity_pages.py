#!/usr/bin/env python3
"""Generate the per-entity + geographic + category SEO pages and sitemaps (#15).

For every Italian PA entity we emit a static, richly-linked, indexable page
(``/ente/{sigla}/{nome-ente}/``) carrying ALL its scan data — provider, MX/SPF/
DKIM evidence, sovereignty (6- and 4-bucket, reusing the canonical model),
reliability, history (when historicization is live) and the territorially-near
entities as a reputational nudge (#15). We also emit geographic hubs
(region/province/comune), category facets and lightweight domain aliases, plus
a **sitemap index** that feeds search engines the whole of Italy.

Every page carries a "Riporta un errore" link; for anomalous / low-confidence
entities it becomes an emphasised "Aiutaci a risolvere l'anomalia" CTA.

Pages are written under the repo root (``/ente``, ``/aree``, ``/dominio``,
``/categoria``) and are **git-ignored**: they ship only inside the Pages
artifact (deploy is decoupled from git — see CLAUDE.md). The generator is the
single sitemap authority (writes ``sitemap.xml`` index + children).

Run:  ``python3 scripts/build_entity_pages.py --country IT``
Smoke (fast subset):  ``--solo-regione Molise``  or  ``--limit 200``
"""

from __future__ import annotations

import argparse
import collections
import html
import json
import os
import sys
from pathlib import Path
from urllib.parse import quote

from mail_sovereignty import historicize as H
from mail_sovereignty import kpi as K
from mail_sovereignty import pages as P

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_sitemap  # noqa: E402  (sibling script: reuse core PAGES + _lastmod)

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://mxmap.it"
OG_IMAGE = f"{BASE}/brand/og-image.png"
GH_NEW = "https://github.com/mxmap-it/mxmap.it/issues/new"
TG_GROUP = "https://t.me/+Ot-M_g0dkh1kMGI0"
SOV4_LABELS = K.SOV4_LABELS
NEARBY_N = 8
LOWCONF = 0.60


def esc(x: object) -> str:
    return html.escape("" if x is None else str(x), quote=True)


# --------------------------------------------------------------------------- #
#  Data access helpers (reuse the canonical sovereignty model — never re-derive)
# --------------------------------------------------------------------------- #
def load_entities(country: str):
    data = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
    ents = data.get("municipalities") or data
    if isinstance(ents, dict):
        ents = list(ents.values())
    it = [e for e in ents if str(e.get("bfs", "")).startswith(f"{country}-")]
    try:
        detail = json.loads((ROOT / "data-detail.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        detail = {}
    return it, detail


def prov(e):
    return (e.get("provider") or "unknown") or "unknown"


def sov6(e):
    return H.sovereignty_of(prov(e))


def sov4(e):
    return K.provider_to_sov4(prov(e))


def provider_disp(e):
    p = prov(e)
    return H.PROVIDER_DISPLAY.get(p, "Sconosciuto" if p == "unknown" else p.title())


def has_mx(e):
    return any((h or "").strip() for h in (e.get("mx") or []))


def confidence(e):
    c = e.get("classification_confidence")
    return c if isinstance(c, (int, float)) else None


def is_anomaly(e):
    return prov(e) == "unknown" or not has_mx(e)


def is_lowconf(e):
    c = confidence(e)
    return c is not None and c < LOWCONF


def aggregate(entities):
    n = len(entities)
    by4 = collections.Counter(sov4(e) for e in entities)
    by6 = collections.Counter(sov6(e) for e in entities)
    classified = n - by4.get("unknown", 0)
    isd = (by4.get("it", 0) / classified * 100.0) if classified else 0.0
    return {"n": n, "by4": by4, "by6": by6, "classified": classified, "isd": isd}


# --------------------------------------------------------------------------- #
#  HTML building blocks
# --------------------------------------------------------------------------- #
def footer():
    return (
        '<footer class="site"><p>'
        '<a href="/">Mappa</a> · <a href="/statistiche.html">Statistiche</a> · '
        '<a href="/report.html">Report</a> · <a href="/methodology.html">Metodologia</a> · '
        '<a href="/aree/">Aree</a> · <a href="/categoria/">Categorie</a> · '
        '<a href="/anomalie.html">Anomalie</a></p>'
        '<p class="small muted">Dati CC BY-SA 4.0 · classificazione del provider email via '
        "analisi DNS (MX, SPF, CNAME, DKIM) · un progetto dell'Osservatorio Nazionale "
        "Sovranità Digitale. I dati possono contenere imprecisioni: usa il pulsante "
        "“Riporta un errore”.</p></footer>"
    )


def crumbs(items):
    parts = []
    for label, href in items:
        parts.append(
            f'<a href="{esc(href)}">{esc(label)}</a>'
            if href
            else f"<span>{esc(label)}</span>"
        )
    return '<nav class="crumbs">' + '<span class="sep">›</span>'.join(parts) + "</nav>"


def shell(
    *, title, description, canonical, body, keywords=None, jsonld=None, og_title=None
):
    kw = keywords or (
        "MxMap Italia, MXMap Italia, sovranità digitale, posta elettronica PA, "
        "provider email pubblica amministrazione, CLOUD Act, IndicePA, analisi DNS"
    )
    jl = ""
    if jsonld:
        jl = (
            '<script type="application/ld+json">'
            + json.dumps(jsonld, ensure_ascii=False)
            + "</script>"
        )
    return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="keywords" content="{esc(kw)}">
<meta name="robots" content="index, follow, max-image-preview:large">
<link rel="canonical" href="{esc(canonical)}">
<meta name="application-name" content="MxMap Italia">
<meta property="og:type" content="article">
<meta property="og:locale" content="it_IT">
<meta property="og:site_name" content="MxMap Italia">
<meta property="og:title" content="{esc(og_title or title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:image" content="{OG_IMAGE}">
<meta property="og:url" content="{esc(canonical)}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/svg+xml" href="/brand/favicon.svg">
<link rel="stylesheet" href="/assets/ente.css">
{jl}
</head>
<body>
<header class="site"><div class="wrap"><a href="/">MxMap <span style="font-weight:400">Italia</span></a><span class="tag">Sovranità digitale della PA</span></div></header>
<main class="wrap">
{body}
{footer()}
</main>
</body>
</html>
"""


def report_block(e, page_url, emphasised):
    name = e.get("name") or ""
    domain = e.get("domain") or "—"
    pdisp = provider_disp(e)
    reason = e.get("reason") or ""
    mx = ", ".join(h for h in (e.get("mx") or []) if h)
    spf = e.get("spf") or ""
    title = (
        "[Aiuto anomalia] " if emphasised else "[Segnalazione dato] "
    ) + f"{name} — {domain}"
    lines = [
        f"**Ente:** {name}",
        f"**Dominio:** {domain}",
        f"**Codice IPA / ID:** {e.get('bfs', '')}",
        f"**Provider classificato:** {pdisp}",
    ]
    if reason:
        lines.append(f"**Motivazione:** {reason}")
    if mx:
        lines.append(f"**MX:** {mx}")
    if spf:
        lines.append(f"**SPF:** {spf}")
    lines += [
        "",
        "**Cosa risulta sbagliato e qual è il dato corretto:**",
        "",
        "",
        f"— inviato da {page_url}",
    ]
    gh = f"{GH_NEW}?title={quote(title)}&body={quote(chr(10).join(lines))}&labels=segnalazione-dato"
    tgtext = f'Possibile errore su MxMap Italia — {name} ({domain}), classificato "{pdisp}". {page_url}'
    tg = f"https://t.me/share/url?url={quote(BASE)}&text={quote(tgtext)}"
    cls = "report card anom" if emphasised else "report card"
    head = "Aiutaci a risolvere l'anomalia" if emphasised else "Riporta un errore"
    if emphasised:
        intro = (
            "Per questo ente il dato è <strong>anomalo o a bassa affidabilità</strong> e "
            "potrebbe essere incompleto. Se conosci il provider o il dominio email corretto, "
            "aiutaci a sistemarlo: bastano 30 secondi e migliori l'osservatorio per tutti."
        )
    else:
        intro = "Hai notato un dato sbagliato? Segnalacelo — ogni correzione rende l'osservatorio più accurato."
    return (
        f'<section class="{cls}"><h2>⚠️ {esc(head)}</h2>'
        f'<p class="small">{intro}</p>'
        f'<div class="cta"><a class="btn" href="{esc(gh)}" target="_blank" rel="noopener">🐙 Apri un ticket GitHub</a>'
        f'<a class="btn tg" href="{esc(tg)}" target="_blank" rel="noopener">✈️ Segnala via Telegram</a></div></section>'
    )


def stacked_bar(by4):
    total = sum(by4.values()) or 1
    order = ["it", "eu_non_it", "extra_eu", "unknown"]
    seg = ""
    for k in order:
        v = by4.get(k, 0)
        if not v:
            continue
        pct = v / total * 100
        seg += f'<span style="width:{pct:.2f}%;background:{P.sov4_color(k)}" title="{esc(SOV4_LABELS.get(k, k))}: {v}"></span>'
    return f'<div class="bar">{seg}</div>'


def status_dot(e):
    return f'<span class="dot" style="background:{P.sov6_color(sov6(e))}"></span>'


# --------------------------------------------------------------------------- #
#  Entity page
# --------------------------------------------------------------------------- #
def entity_page(e, detail, path, nearby):
    name = e.get("name") or "Ente"
    domain = e.get("domain") or ""
    canonical = BASE + path
    b6 = sov6(e)
    b4 = sov4(e)
    pdisp = provider_disp(e)
    conf = confidence(e)
    anomaly, lowconf = is_anomaly(e), is_lowconf(e)
    emph = anomaly or lowconf
    regione, sigla, comune = e.get("regione"), e.get("provincia"), e.get("comune")

    title = f"{name} — Sovranità digitale della posta elettronica" + (
        f" ({domain})" if domain else ""
    )
    desc = (
        f"{name}: provider email {pdisp}, sovranità «{b6}»"
        + (f", dominio {domain}" if domain else "")
        + f". Affidabilità {int((conf or 0) * 100)}%. Classificazione via analisi DNS (MX, SPF, DKIM) — MxMap Italia."
    )

    # --- verdict ---
    verdict = (
        f'<section class="card"><h2>Verdetto di sovranità</h2><div class="verdict">'
        f'<span class="badge"><span class="dot" style="background:{P.sov6_color(b6)}"></span>{esc(b6)}</span>'
        f'<span class="pill" style="background:{P.sov4_color(b4)}">{esc(SOV4_LABELS.get(b4, b4))}</span></div>'
        f'<p class="sub" style="margin-top:10px">Provider email rilevato: <strong>{esc(pdisp)}</strong>'
        + (f" · dominio <code>{esc(domain)}</code>" if domain else "")
        + "</p></section>"
    )

    # --- evidence ---
    def row(k, v):
        return f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" if v else ""

    mx = ", ".join(h for h in (e.get("mx") or []) if h) or "—"
    countries = ", ".join(e.get("mx_countries") or []) or "—"
    asns = ", ".join(f"AS{a}" for a in (e.get("mx_asns") or [])) or "—"
    dkim = e.get("dkim")
    dkim_txt = (
        ", ".join(f"{k}→{v}" for k, v in dkim.items())
        if isinstance(dkim, dict) and dkim
        else "—"
    )
    ad = e.get("autodiscover")
    ad_txt = (
        ", ".join(f"{k}: {v}" for k, v in ad.items())
        if isinstance(ad, dict) and ad
        else "—"
    )
    evidence = (
        '<section class="card"><h2>Evidenze di rilevamento (DNS)</h2><table class="kv">'
        + row("Dominio (IndicePA)", domain or "—")
        + row("Record MX", mx)
        + row("Paese MX", countries)
        + row("ASN MX", asns)
        + row("SPF", e.get("spf") or "—")
        + row("DKIM", dkim_txt)
        + row("Autodiscover", ad_txt)
        + row(
            "Giurisdizione MX",
            {"foreign": "estera", "domestic": "italiana"}.get(
                e.get("mx_jurisdiction"), e.get("mx_jurisdiction")
            ),
        )
        + row("Scoperta dominio", e.get("mx_discovery_method"))
        + "</table></section>"
    )

    # --- reliability ---
    cpct = int((conf or 0) * 100)
    signals = ", ".join(e.get("classification_signals") or []) or "—"
    reli = (
        '<section class="card"><h2>Affidabilità del risultato</h2>'
        f'<p class="small">Confidenza della classificazione: <strong>{cpct}%</strong></p>'
        f'<div class="meter"><i style="width:{cpct}%"></i></div>'
        '<table class="kv" style="margin-top:10px">'
        + row("Regola", e.get("classification_rule"))
        + row("Segnali usati", signals)
        + row("Motivazione", e.get("reason"))
        + "</table>"
        + (
            '<p class="small muted" style="margin-top:8px">⚠️ Dato segnalato come <strong>anomalo</strong> '
            "(provider non determinato o MX assente): non è classificabile come sovrano né non-sovrano finché "
            "non viene corretto.</p>"
            if anomaly
            else ""
        )
        + "</section>"
    )

    # --- nearby (reputational nudge, #15) ---
    nb_html = ""
    if nearby:
        cards = "".join(
            f'<a class="nb" href="{esc(p)}">{status_dot(n)}<span class="nm">{esc(n.get("name"))}</span></a>'
            for n, p in nearby
        )
        agg = aggregate([n for n, _ in nearby] + [e])
        nb_html = (
            f'<section class="card"><h2>Come stanno gli enti vicini</h2>'
            f'<p class="small">Confronto con altri enti di <strong>{esc(comune or sigla)}</strong>. '
            f"Sovranità italiana dell'area (ISD): <strong>{agg['isd']:.0f}%</strong>.</p>"
            f'<div class="grid">{cards}</div></section>'
        )

    # --- history (gated until run #1) ---
    hist = (
        '<section class="card"><h2>Storico delle scansioni</h2>'
        '<p class="small muted">Prima scansione registrata. Lo storico per ente (variazioni di provider e '
        "sovranità nel tempo) si popolerà dai prossimi cicli di rilevamento.</p></section>"
    )

    report = report_block(e, canonical, emph)

    crumb = crumbs(
        [
            ("Italia", "/aree/"),
            (regione or "—", P.region_path(regione)),
            (sigla or "—", P.province_path(regione, sigla)),
            (comune or "—", P.comune_path(regione, sigla, comune)),
            (name, None),
        ]
    )
    body = (
        crumb
        + f"<h1>{esc(name)}</h1>"
        + '<p class="sub">Sovranità digitale della posta elettronica'
        + (f" · <code>{esc(domain)}</code>" if domain else "")
        + (f" · {esc(comune)} ({esc(sigla)}), {esc(regione)}" if comune else "")
        + "</p>"
        + (report if emph else verdict)
        + (verdict if emph else evidence)
        + (evidence if emph else reli)
        + (reli if emph else nb_html)
        + (nb_html if emph else hist)
        + (hist if emph else report)
    )

    jsonld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "GovernmentOrganization",
                "name": name,
                "url": f"http://{domain}" if domain else canonical,
                "identifier": e.get("bfs"),
                "address": {
                    "@type": "PostalAddress",
                    "addressLocality": comune,
                    "addressRegion": regione,
                    "addressCountry": "IT",
                },
                "additionalProperty": [
                    {
                        "@type": "PropertyValue",
                        "name": "Provider email",
                        "value": pdisp,
                    },
                    {"@type": "PropertyValue", "name": "Sovranità", "value": b6},
                    {
                        "@type": "PropertyValue",
                        "name": "Affidabilità",
                        "value": f"{cpct}%",
                    },
                ],
                "mainEntityOfPage": canonical,
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": i + 1,
                        "name": lbl,
                        "item": BASE + href,
                    }
                    for i, (lbl, href) in enumerate(
                        [
                            ("Italia", "/aree/"),
                            (regione or "—", P.region_path(regione)),
                            (sigla or "—", P.province_path(regione, sigla)),
                            (name, path),
                        ]
                    )
                ],
            },
        ],
    }
    return shell(
        title=title, description=desc, canonical=canonical, body=body, jsonld=jsonld
    )


# --------------------------------------------------------------------------- #
#  Hub + category + alias + index pages
# --------------------------------------------------------------------------- #
def kpi_exhibit(agg):
    rows = ""
    for k in ("it", "eu_non_it", "extra_eu", "unknown"):
        v = agg["by4"].get(k, 0)
        if not v:
            continue
        rows += (
            f'<tr><td><span class="dot" style="background:{P.sov4_color(k)}"></span> {esc(SOV4_LABELS.get(k, k))}</td>'
            f'<td class="num">{v}</td><td class="num">{v / agg["n"] * 100:.1f}%</td></tr>'
        )
    return (
        '<section class="card"><h2>Sovranità dell\'area</h2>'
        f'<p class="sub">Enti analizzati: <strong>{agg["n"]}</strong> · '
        f"Indice di Sovranità Digitale (ISD): <strong>{agg['isd']:.1f}%</strong> "
        '<span class="muted small">(quota italiana sui classificati)</span></p>'
        + stacked_bar(agg["by4"])
        + '<table class="league" style="margin-top:12px"><tr><th>Bucket</th><th class="num">Enti</th><th class="num">%</th></tr>'
        + rows
        + "</table></section>"
    )


def entity_list_card(title, entities, path_of, limit=400):
    items = sorted(entities, key=lambda e: (e.get("name") or "").lower())
    extra = ""
    if len(items) > limit:
        extra = f'<p class="small muted">…e altri {len(items) - limit} enti.</p>'
        items = items[:limit]
    rows = "".join(
        f'<a class="nb" href="{esc(path_of[e["bfs"]])}">{status_dot(e)}<span class="nm">{esc(e.get("name"))}</span></a>'
        for e in items
        if e["bfs"] in path_of
    )
    return f'<section class="card"><h2>{esc(title)}</h2><div class="grid">{rows}</div>{extra}</section>'


def league_card(title, rows):
    # rows: list of (label, href, agg)
    body = ""
    for label, href, agg in sorted(rows, key=lambda r: r[2]["isd"], reverse=True):
        body += (
            f'<tr><td><a href="{esc(href)}">{esc(label)}</a></td>'
            f'<td class="num">{agg["n"]}</td>'
            f'<td class="num">{agg["isd"]:.0f}%</td>'
            f"<td>{stacked_bar(agg['by4'])}</td></tr>"
        )
    return (
        f'<section class="card"><h2>{esc(title)}</h2>'
        '<table class="league"><tr><th>Area</th><th class="num">Enti</th>'
        '<th class="num">ISD</th><th>Composizione</th></tr>'
        + body
        + "</table></section>"
    )


def hub_page(
    *,
    title,
    h1,
    sub,
    canonical,
    crumb_items,
    agg,
    children_card="",
    entities_card="",
    desc=None,
):
    body = (
        crumbs(crumb_items)
        + f"<h1>{esc(h1)}</h1>"
        + f'<p class="sub">{esc(sub)}</p>'
        + kpi_exhibit(agg)
        + children_card
        + entities_card
    )
    return shell(
        title=title,
        description=desc or sub,
        canonical=canonical,
        body=body,
        keywords="MxMap Italia, sovranità digitale, PA, " + h1,
    )


def alias_page(domain, entity_path, entity_name):
    canonical = BASE + entity_path
    body = (
        f"<h1>{esc(domain)}</h1>"
        f'<p class="sub">Sovranità digitale della posta elettronica del dominio <code>{esc(domain)}</code>.</p>'
        f'<section class="card"><p>Scheda dell\'ente: <a href="{esc(entity_path)}"><strong>{esc(entity_name)}</strong></a>.</p>'
        f'<p class="small muted">Reindirizzamento in corso…</p></section>'
        f'<meta http-equiv="refresh" content="0; url={esc(entity_path)}">'
    )
    # canonical points at the entity page so search engines consolidate.
    return shell(
        title=f"{domain} — Sovranità digitale della posta ({entity_name})",
        description=f"Provider email e sovranità digitale del dominio {domain} ({entity_name}). MxMap Italia.",
        canonical=canonical,
        body=body,
        og_title=f"{domain} — MxMap Italia",
    )


# --------------------------------------------------------------------------- #
#  Sitemaps
# --------------------------------------------------------------------------- #
def _urlset(entries, lastmod):
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc, cf, pr in entries:
        out += [
            "  <url>",
            f"    <loc>{html.escape(loc)}</loc>",
            f"    <lastmod>{lastmod}</lastmod>",
            f"    <changefreq>{cf}</changefreq>",
            f"    <priority>{pr}</priority>",
            "  </url>",
        ]
    out.append("</urlset>")
    return "\n".join(out) + "\n"


def _sitemapindex(children, lastmod):
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for fn in children:
        out += [
            "  <sitemap>",
            f"    <loc>{BASE}/{fn}</loc>",
            f"    <lastmod>{lastmod}</lastmod>",
            "  </sitemap>",
        ]
    out.append("</sitemapindex>")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- #
#  Orchestration
# --------------------------------------------------------------------------- #
def write_page(out_dir: Path, path: str, htmlstr: str, written: set):
    fp = out_dir / path.strip("/") / "index.html"
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(htmlstr, encoding="utf-8")
    written.add(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--country", default="IT")
    ap.add_argument("--out-dir", default=str(ROOT))
    ap.add_argument(
        "--solo-regione", default=None, help="genera solo una regione (smoke)"
    )
    ap.add_argument(
        "--limit", type=int, default=None, help="limita il numero di enti (smoke)"
    )
    ap.add_argument("--no-domain-aliases", action="store_true")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    entities, detail = load_entities(args.country)
    if args.solo_regione:
        entities = [
            e
            for e in entities
            if (e.get("regione") or "").lower() == args.solo_regione.lower()
        ]
    if args.limit:
        entities = entities[: args.limit]
    if not entities:
        sys.exit(
            f"[build_entity_pages] nessun ente per i filtri dati (country={args.country})"
        )

    paths = P.assign_entity_paths(entities)

    # groupings
    g_region = collections.defaultdict(list)
    g_prov = collections.defaultdict(list)
    g_comune = collections.defaultdict(list)
    g_cluster = collections.defaultdict(list)
    g_domain = collections.defaultdict(list)
    for e in entities:
        g_region[e.get("regione")].append(e)
        g_prov[(e.get("regione"), e.get("provincia"))].append(e)
        g_comune[(e.get("regione"), e.get("provincia"), e.get("comune"))].append(e)
        g_cluster[P.cluster_of(e.get("bfs"))].append(e)
        if e.get("domain"):
            g_domain[e["domain"].strip().lower()].append(e)

    written: set[str] = set()
    lastmod = build_sitemap._lastmod()
    collisions = sum(1 for p in paths.values() if not p.rstrip("/").split("/")[-1])

    # --- entity pages ---
    for e in entities:
        same_comune = [
            x
            for x in g_comune[(e.get("regione"), e.get("provincia"), e.get("comune"))]
            if x["bfs"] != e["bfs"]
        ]
        pool = same_comune or [
            x
            for x in g_prov[(e.get("regione"), e.get("provincia"))]
            if x["bfs"] != e["bfs"]
        ]
        nearby = [
            (n, paths[n["bfs"]])
            for n in sorted(pool, key=lambda x: x.get("name") or "")[:NEARBY_N]
        ]
        write_page(
            out_dir,
            paths[e["bfs"]],
            entity_page(e, detail.get(e["bfs"], {}), paths[e["bfs"]], nearby),
            written,
        )

    # --- comune hubs ---
    for (reg, sig, com), ents in g_comune.items():
        agg = aggregate(ents)
        path = P.comune_path(reg, sig, com)
        write_page(
            out_dir,
            path,
            hub_page(
                title=f"{com} — Sovranità digitale della PA ({sig})",
                h1=f"PA di {com}",
                sub=f"Sovranità digitale della posta elettronica degli enti pubblici di {com} ({sig}), {reg}.",
                canonical=BASE + path,
                crumb_items=[
                    ("Italia", "/aree/"),
                    (reg, P.region_path(reg)),
                    (sig, P.province_path(reg, sig)),
                    (com, None),
                ],
                agg=agg,
                entities_card=entity_list_card(f"Enti a {com}", ents, paths),
            ),
            written,
        )

    # --- province hubs ---
    for (reg, sig), ents in g_prov.items():
        agg = aggregate(ents)
        path = P.province_path(reg, sig)
        comuni_rows = [
            (com or "—", P.comune_path(reg, sig, com), aggregate(cents))
            for (r2, s2, com), cents in g_comune.items()
            if r2 == reg and s2 == sig
        ]
        write_page(
            out_dir,
            path,
            hub_page(
                title=f"Provincia di {sig} — Sovranità digitale della PA",
                h1=f"Provincia di {sig}",
                sub=f"Sovranità digitale della posta elettronica della PA in provincia di {sig} ({reg}).",
                canonical=BASE + path,
                crumb_items=[
                    ("Italia", "/aree/"),
                    (reg, P.region_path(reg)),
                    (sig, None),
                ],
                agg=agg,
                children_card=league_card("Comuni della provincia", comuni_rows),
            ),
            written,
        )

    # --- region hubs ---
    for reg, ents in g_region.items():
        agg = aggregate(ents)
        path = P.region_path(reg)
        prov_rows = [
            (s2 or "—", P.province_path(reg, s2), aggregate(pents))
            for (r2, s2), pents in g_prov.items()
            if r2 == reg
        ]
        write_page(
            out_dir,
            path,
            hub_page(
                title=f"{reg} — Sovranità digitale della PA",
                h1=f"{reg}",
                sub=f"Sovranità digitale della posta elettronica della Pubblica Amministrazione in {reg}.",
                canonical=BASE + path,
                crumb_items=[("Italia", "/aree/"), (reg, None)],
                agg=agg,
                children_card=league_card("Province della regione", prov_rows),
            ),
            written,
        )

    # --- /aree/ index ---
    region_rows = [
        (reg or "—", P.region_path(reg), aggregate(ents))
        for reg, ents in g_region.items()
    ]
    write_page(
        out_dir,
        "/aree/",
        hub_page(
            title="Aree geografiche — Sovranità digitale della PA italiana | MxMap Italia",
            h1="Sovranità digitale per area",
            sub="Esplora la sovranità digitale della posta elettronica della PA italiana per regione, provincia e comune.",
            canonical=f"{BASE}/aree/",
            crumb_items=[("Italia", None)],
            agg=aggregate(entities),
            children_card=league_card("Regioni d'Italia", region_rows),
        ),
        written,
    )

    # --- category facets ---
    for (ckey, clabel), ents in g_cluster.items():
        agg = aggregate(ents)
        path = P.category_path(ckey)
        write_page(
            out_dir,
            path,
            hub_page(
                title=f"{clabel} — Sovranità digitale | MxMap Italia",
                h1=clabel,
                sub=f"Sovranità digitale della posta elettronica della categoria «{clabel}» nella PA italiana.",
                canonical=BASE + path,
                crumb_items=[("Categorie", "/categoria/"), (clabel, None)],
                agg=agg,
                entities_card=entity_list_card(f"Enti — {clabel}", ents, paths),
            ),
            written,
        )
    cat_rows = [
        (clabel, P.category_path(ckey), aggregate(ents))
        for (ckey, clabel), ents in g_cluster.items()
    ]
    write_page(
        out_dir,
        "/categoria/",
        hub_page(
            title="Categorie di enti — Sovranità digitale della PA | MxMap Italia",
            h1="Sovranità digitale per categoria",
            sub="La sovranità digitale della posta elettronica per tipologia di ente pubblico italiano.",
            canonical=f"{BASE}/categoria/",
            crumb_items=[("Categorie", None)],
            agg=aggregate(entities),
            children_card=league_card("Categorie", cat_rows),
        ),
        written,
    )

    # --- domain aliases (NOT in sitemap: canonical → entity page) ---
    alias_count = 0
    if not args.no_domain_aliases:
        for domain, ents in g_domain.items():
            ap_path = P.domain_alias_path(domain)
            if not ap_path:
                continue
            target = min(ents, key=lambda e: e["bfs"])  # deterministic
            write_page(
                out_dir,
                ap_path,
                alias_page(domain, paths[target["bfs"]], target.get("name") or domain),
                set(),
            )
            alias_count += 1

    # --- sitemaps (index + children) ---
    smdir = out_dir
    children = []
    # core (the 8 static pages)
    (smdir / "sitemap-core.xml").write_text(
        _urlset(
            [
                (BASE + p["loc"], p["changefreq"], p["priority"])
                for p in build_sitemap.PAGES
            ],
            lastmod,
        ),
        encoding="utf-8",
    )
    children.append("sitemap-core.xml")
    # aree + categorie
    aree = [
        (BASE + p, "weekly", "0.6") for p in sorted(written) if p.startswith("/aree/")
    ]
    cats = [
        (BASE + p, "weekly", "0.5")
        for p in sorted(written)
        if p.startswith("/categoria/")
    ]
    (smdir / "sitemap-aree.xml").write_text(_urlset(aree, lastmod), encoding="utf-8")
    (smdir / "sitemap-categorie.xml").write_text(
        _urlset(cats, lastmod), encoding="utf-8"
    )
    children += ["sitemap-aree.xml", "sitemap-categorie.xml"]
    # entities chunked by region
    ent_paths_by_region = collections.defaultdict(list)
    for e in entities:
        ent_paths_by_region[P.region_slug(e.get("regione"))].append(
            BASE + paths[e["bfs"]]
        )
    for rslug, locs in sorted(ent_paths_by_region.items()):
        fn = f"sitemap-enti-{rslug}.xml"
        (smdir / fn).write_text(
            _urlset([(u, "monthly", "0.7") for u in sorted(locs)], lastmod),
            encoding="utf-8",
        )
        children.append(fn)
    # index
    (smdir / "sitemap.xml").write_text(
        _sitemapindex(children, lastmod), encoding="utf-8"
    )

    # --- integrity ---
    n_entity_pages = sum(1 for p in written if p.startswith("/ente/"))
    assert n_entity_pages == len(entities), (
        f"entity pages {n_entity_pages} != entities {len(entities)}"
    )
    assert len(set(paths.values())) == len(paths), "duplicate entity URLs!"
    full_isd = aggregate(entities)["isd"]
    assert 0.0 <= full_isd <= 100.0, f"ISD out of range: {full_isd}"

    print(
        f"[build_entity_pages] enti={len(entities)} pagine_ente={n_entity_pages} "
        f"hub_aree={len(aree)} categorie={len(cats)} alias_dominio={alias_count} "
        f"sitemap_children={len(children)} ISD={full_isd:.1f}% collisioni_slug={collisions} lastmod={lastmod}"
    )


if __name__ == "__main__":
    main()

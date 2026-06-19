#!/usr/bin/env python3
"""Generate sitemap.xml for mxmap.it (maintained over time).

The sitemap is regenerated on every nightly run so that ``<lastmod>`` always
reflects the freshness of the published data. ``lastmod`` is taken from
``kpi.json``'s ``generated_at`` (the canonical run timestamp) so the value is
deterministic given a committed ``kpi.json`` — this keeps the CI smoke job from
producing spurious diffs. It falls back to today's date only if ``kpi.json`` is
missing or unparseable.

Run: ``python3 scripts/build_sitemap.py`` (from the repo root).

NOTE: in the pipeline the sitemap is now owned by ``build_entity_pages.py``,
which writes a **sitemap index** + per-section children and reuses ``PAGES`` /
``_lastmod`` from this module for the core child. This standalone script remains
as that importable library and as a dev convenience (flat sitemap of the core
pages); it is still import-checked by the ``smoke`` job in ``ci.yml``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
BASE_URL = "https://mxmap.it"

# Canonical public pages, in priority order. The homepage is published at the
# bare domain (matches the <link rel="canonical"> in index.html), not
# /index.html. ``loc`` is the path appended to BASE_URL ("" → the root).
PAGES: list[dict[str, object]] = [
    {"loc": "/", "priority": "1.0", "changefreq": "daily"},
    {"loc": "/statistiche.html", "priority": "0.9", "changefreq": "daily"},
    {"loc": "/report.html", "priority": "0.9", "changefreq": "weekly"},
    {"loc": "/anomalie.html", "priority": "0.7", "changefreq": "daily"},
    {
        "loc": "/templates/it_search_template.html",
        "priority": "0.7",
        "changefreq": "daily",
    },
    {
        "loc": "/templates/it_table_template.html",
        "priority": "0.6",
        "changefreq": "weekly",
    },
    {"loc": "/methodology.html", "priority": "0.6", "changefreq": "monthly"},
    {"loc": "/storia.html", "priority": "0.5", "changefreq": "weekly"},
]


def _lastmod() -> str:
    """Return the publication date (YYYY-MM-DD) from kpi.json, else today (UTC)."""
    kpi = ROOT / "kpi.json"
    try:
        generated_at = json.loads(kpi.read_text(encoding="utf-8"))["generated_at"]
        # Accept both "...Z" and offset-aware ISO timestamps.
        ts = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        return ts.date().isoformat()
    except (OSError, KeyError, ValueError, TypeError):
        return datetime.now(timezone.utc).date().isoformat()


def build_sitemap(lastmod: str | None = None) -> str:
    """Return the sitemap.xml document as a string."""
    lastmod = lastmod or _lastmod()
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for page in PAGES:
        loc = escape(f"{BASE_URL}{page['loc']}")
        lines += [
            "  <url>",
            f"    <loc>{loc}</loc>",
            f"    <lastmod>{lastmod}</lastmod>",
            f"    <changefreq>{page['changefreq']}</changefreq>",
            f"    <priority>{page['priority']}</priority>",
            "  </url>",
        ]
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def main() -> None:
    out = ROOT / "sitemap.xml"
    xml = build_sitemap()
    out.write_text(xml, encoding="utf-8")
    n = len(PAGES)
    print(
        f"[build_sitemap] wrote {out.relative_to(ROOT)} ({n} URLs, lastmod {_lastmod()})"
    )


if __name__ == "__main__":
    main()

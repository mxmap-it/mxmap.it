#!/usr/bin/env python3
"""Validate that the % labels on Region/Province polygons show the
Italian-sovereignty share (Cloud Italiano + Provider Italiano +
Infrastruttura autonoma) — NOT the dominant-provider share."""
import sys
import time
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8765/index.html"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1400, "height": 800})
        page = ctx.new_page()
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_function(
            "document.getElementById('map-loading') == null || "
            "document.getElementById('map-loading').style.display === 'none'",
            timeout=30000)

        # Test on Province view (where the user reported)
        page.click("button[data-level='district']")
        time.sleep(4)
        # Compute expected vs actual share for first 5 visible groups
        result = page.evaluate("""
          (() => {
            const ITALIAN = ['Cloud Italiano','Provider Italiano',
                             'Infrastruttura autonoma',
                             'Mail provinciale condivisa',
                             'Contractor PA privato'];
            var rows = [];
            window._map.eachLayer(function(layer) {
              if (typeof layer.eachLayer !== 'function') return;
              layer.eachLayer(function(sub) {
                if (rows.length >= 6) return;
                var g = sub.feature ? sub.feature._matchedGroup : null;
                if (!g || !g.providers) return;
                var total = 0, ital = 0;
                for (var p in g.providers) {
                  var v = g.providers[p] || 0;
                  total += v;
                  if (ITALIAN.indexOf(p) >= 0) ital += v;
                }
                rows.push({
                  name: g.name || 'unknown',
                  total: total,
                  italian_sum: ital,
                  italian_pct: total > 0 ? Math.round(ital/total*100) : 0,
                  dominant: g.dominant,
                  dominant_pct: total > 0 ? Math.round((g.providers[g.dominant]||0)/total*100) : 0,
                  providers: g.providers,
                });
              });
            });
            return rows;
          })()
        """)
        print("=== Province (district) groups — comparison ===")
        for r in result:
            print(f"  {r['name'][:30]:<30}  total={r['total']:>4}  "
                  f"italian_sum={r['italian_sum']:>4} ({r['italian_pct']}%)   "
                  f"dominant={r['dominant'][:18]:<18} ({r['dominant_pct']}%)")
        # Also extract the actual rendered label from a known point
        # via dominanceMarkers
        rendered = page.evaluate("""
          (() => {
            var n = 0, vals = [];
            // dominanceMarkers is module-scoped — find via map layers
            window._map.eachLayer(function(layer) {
              if (typeof layer.eachLayer !== 'function') return;
              layer.eachLayer(function(m) {
                if (m.options && m.options.icon && m.options.icon.options
                    && m.options.icon.options.className === 'dominance-label') {
                  n++;
                  var match = m.options.icon.options.html.match(/(\\d+)%/);
                  if (match) vals.push(parseInt(match[1], 10));
                }
              });
            });
            return { count: n, sample: vals.slice(0, 10) };
          })()
        """)
        print(f"\nRendered label count: {rendered['count']}")
        print(f"  sample %: {rendered['sample']}")
        page.screenshot(path="C:/temp/dom_label_test.png", full_page=False)
        browser.close()
        # Heuristic check: at least one province should have italian_pct
        # significantly different from dominant_pct. If they're always
        # equal, the change didn't take effect.
        diffs = [abs(r['italian_pct'] - r['dominant_pct']) for r in result if r['total'] > 0]
        ok = any(d > 5 for d in diffs)
        print(f"\n[{'OK' if ok else 'FAIL'}] italian_pct differs from dominant_pct: "
              f"max diff = {max(diffs) if diffs else 0}")
        return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())

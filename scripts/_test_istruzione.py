#!/usr/bin/env python3
"""Headless regression test for the Scuole/Istruzione level.

Validates 3 user-requested behaviours:
  A. School marker popup shows the SAME analytical detail used for
     comuni (MX records, SPF, DKIM, autodiscover, classification reason)
     not the 3-line slim summary.
  B. No cluster-aggregation numbers (5, 4, ...): plain layerGroup, no
     leaflet.markercluster.
  C. Comune polygons (choropleth) are NOT visible at istruzione level —
     map shows only base tile + markers."""
import sys
import time
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8765/index.html"
VIEWPORT = {"width": 1400, "height": 800}


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport=VIEWPORT)
        page = ctx.new_page()
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_function(
            "document.getElementById('map-loading') == null || "
            "document.getElementById('map-loading').style.display === 'none'",
            timeout=30000,
        )
        # Switch to Scuole
        page.click("button[data-level='istruzione']")
        # Give time for: loadSummaryData, marker build, polygon hide
        time.sleep(6)

        # B. Cluster-numbers absence: no .marker-cluster elements
        cluster_count = page.evaluate(
            "(() => document.querySelectorAll('.marker-cluster').length)()"
        )
        # C. Country polygon layers removed from map. Detect by walking
        #    map._layers and counting GeoJSON FeatureGroups that contain
        #    Polygon/MultiPolygon sub-layers (= the choropleth).
        polygons_on_map = page.evaluate("""
          (() => {
            var n = 0;
            window._map.eachLayer(function(layer) {
              if (typeof layer.eachLayer !== 'function') return;
              if (layer instanceof L.LayerGroup && !(layer instanceof L.GeoJSON)) {
                // skip pure layergroups (markers, dominance markers)
              }
              if (layer instanceof L.GeoJSON) {
                var hasPoly = false;
                layer.eachLayer(function(s) {
                  if (s.feature && s.feature.geometry &&
                      (s.feature.geometry.type === 'Polygon' ||
                       s.feature.geometry.type === 'MultiPolygon')) hasPoly = true;
                });
                if (hasPoly) n++;
              }
            });
            return n;
          })()
        """)
        # Markers visible — count CircleMarker layers
        marker_count = page.evaluate("""
          (() => {
            var n = 0;
            window._map.eachLayer(function(layer) {
              if (typeof layer.eachLayer !== 'function') return;
              layer.eachLayer(function(sub) {
                if (sub instanceof L.CircleMarker) n++;
              });
            });
            return n;
          })()
        """)

        print(f"=== B. cluster numbers ===")
        print(f"  .marker-cluster elements on map: {cluster_count}  "
              f"(want 0; if >0 means clusterGroup is still active)")

        print(f"=== C. polygon visibility ===")
        print(f"  countryLayers on map: {polygons_on_map}  (want 0 at istruzione)")

        print(f"=== Markers ===")
        print(f"  rendered: {marker_count}  (want ~8400)")

        # A. Open popup on a known school and check popup detail
        print(f"\n=== A. school popup detail ===")
        opened = page.evaluate("""
          (() => {
            var first = null;
            window._map.eachLayer(function(layer) {
              if (first) return;
              if (typeof layer.eachLayer !== 'function') return;
              layer.eachLayer(function(sub) {
                if (first) return;
                if (sub instanceof L.CircleMarker && sub._mxmapPoint) first = sub;
              });
            });
            if (!first) return 'no markers';
            window._map.setView(first.getLatLng(), 12);
            first.openPopup();
            return 'opened on ' + (first._mxmapPoint ? first._mxmapPoint.name : '?');
          })()
        """)
        print(f"  {opened}")
        time.sleep(2)

        popup_content = page.evaluate("""
          (() => {
            var el = document.querySelector('.leaflet-popup-content');
            return el ? el.innerHTML : '(no popup)';
          })()
        """)
        # Heuristic checks
        has_mx = 'POSTA IN ENTRATA' in popup_content or 'MX' in popup_content
        has_spf = 'MITTENTI AUTORIZZATI' in popup_content or 'SPF' in popup_content
        has_reason = 'reason' in popup_content.lower() or 'matches' in popup_content.lower() or 'MX record' in popup_content
        is_slim = ('Dettaglio non ancora caricato' in popup_content)

        print(f"  popup contains MX section:  {has_mx}")
        print(f"  popup contains SPF section: {has_spf}")
        print(f"  popup contains reason text: {has_reason}")
        print(f"  popup is the slim fallback: {is_slim}")
        print(f"  popup HTML length: {len(popup_content)} chars")

        page.screenshot(path="C:/temp/istruzione_test.png", full_page=False)
        print(f"\nScreenshot: C:/temp/istruzione_test.png")

        all_ok = (cluster_count == 0
                  and polygons_on_map == 0
                  and marker_count > 1000
                  and (has_mx or has_spf or has_reason)
                  and not is_slim)
        print(f"\n{'[OK]' if all_ok else '[FAIL]'} all assertions: {all_ok}")
        browser.close()
        return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())

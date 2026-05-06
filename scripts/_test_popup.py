#!/usr/bin/env python3
"""Headless browser regression test for the Province popup top-clip bug.

Loads the LOCAL index.html (served via http://127.0.0.1:8765/), waits for
the map to be ready, switches to Province view, clicks Venezia / Bolzano /
top-of-map provinces, and asserts the popup is fully visible (top edge
not clipped behind the brand bar)."""
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
        # Wait for the loading overlay to disappear and tiles to render
        page.wait_for_function("document.getElementById('map-loading') == null || "
                               "document.getElementById('map-loading').style.display === 'none'",
                               timeout=30000)
        # Switch to province view
        page.click("button[data-level='district']")
        time.sleep(2)  # let renderCountryLayer finish
        # Find a province polygon high on the map (Venezia / Lombardia / Bolzano)
        # We'll programmatically open the popup at the top region by clicking
        # on a known Lat/Lng using map.openPopup directly.
        page.evaluate("""
          // Find a north-Italy province polygon by recursing through map layers.
          var found = null;
          window._map.eachLayer(function(layer) {
            if (found) return;
            if (typeof layer.eachLayer !== 'function') return;
            layer.eachLayer(function(sub) {
              if (found) return;
              if (!sub.feature || !sub.feature.properties) return;
              var n = (sub.feature.properties.name || '').toLowerCase();
              if (n.includes('bolzano') || n.includes('südtirol') || n.includes('venezia')) {
                found = sub;
              }
            });
          });
          if (found) {
            found.openPopup();
            'opened popup on ' + (found.feature.properties.name || '?');
          } else {
            'NO match';
          }
        """)
        time.sleep(2)  # autoPan animation
        # Inspect popup position
        result = page.evaluate("""
          (() => {
            var p = document.querySelector('.leaflet-popup');
            var bb = document.querySelector('header.brand') ||
                     document.querySelector('#header') ||
                     document.querySelector('header');
            if (!p) return {error: 'no popup'};
            var pr = p.getBoundingClientRect();
            var br = bb ? bb.getBoundingClientRect() : null;
            var content = p.querySelector('.leaflet-popup-content');
            var cr = content ? content.getBoundingClientRect() : null;
            return {
              popup: { top: pr.top, bottom: pr.bottom, height: pr.height, left: pr.left, width: pr.width },
              brand: br ? { top: br.top, bottom: br.bottom, height: br.height } : null,
              content: cr ? { top: cr.top, bottom: cr.bottom, height: cr.height } : null,
              viewport: { width: window.innerWidth, height: window.innerHeight },
              scrollY: window.scrollY,
            };
          })()
        """)
        print("Popup test result:")
        for k, v in result.items():
            print(f"  {k}: {v}")
        # Assertion: popup top must be >= brand bar bottom (or >= 0 if no brand)
        ok = True
        if result.get("popup"):
            ptop = result["popup"]["top"]
            bbot = result["brand"]["bottom"] if result.get("brand") else 0
            if ptop < bbot:
                print(f"\n[BUG] popup top ({ptop:.0f}px) above brand bar bottom ({bbot:.0f}px) - clipped!")
                ok = False
            else:
                print(f"\n[OK] popup top {ptop:.0f}px >= brand bar {bbot:.0f}px (no clipping).")
        else:
            print("[ERROR] no popup found")
            ok = False
        page.screenshot(path="C:/temp/popup_test.png", full_page=False)
        print("Screenshot: C:/temp/popup_test.png")
        browser.close()
        return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())

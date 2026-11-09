"""EU Security Map (#33): immagine di anteprima social (Open Graph 1200x630).

Legge eu-security/kpi.json (già verificato da build_eu_security_page.py) e
disegna `eu-security/og.png` con cosa misuriamo + sintesi dei risultati.
Dipendenza opzionale: Pillow (`uv run --with pillow ...`); non è richiesta dal
resto della pipeline.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
KPI = ROOT / "eu-security" / "kpi.json"
OUT = ROOT / "eu-security" / "og.png"

W, H = 1200, 630
BG = (14, 20, 33)
FG = (236, 239, 244)
MUT = (148, 160, 178)
US = (251, 146, 60)
NAT = (74, 222, 128)
LINE = (40, 50, 68)

FONT_CANDIDATES = {
    "bold": [
        "C:/Windows/Fonts/segoeuib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    "regular": [
        "C:/Windows/Fonts/segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
}


def font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    for p in FONT_CANDIDATES[kind]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


def main() -> int:
    k = json.loads(KPI.read_text(encoding="utf-8"))
    n = k["n_entities"]
    unk = k["overall"]["unknown"]
    cls = n - unk
    us = k["overall"]["us"]
    nat = k["overall"]["national"]
    us_pct = round(100 * us / cls) if cls else 0
    nat_pct = round(100 * nat / cls) if cls else 0
    n_countries = len([c for c in k["countries"] if c["country"] != "EU"])
    top = [c for c in k["countries"] if c["ranking_eligible"]][:5]

    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    pad = 56

    d.text((pad, 44), "EU SECURITY MAIL MAP", font=font("bold", 22), fill=US)
    d.text(
        (pad, 78),
        "Where Europe's security bodies host their email",
        font=font("bold", 44),
        fill=FG,
    )
    d.text(
        (pad, 138),
        f"Police, intelligence, defence, border & cyber agencies — {n} bodies in "
        f"{n_countries} countries + EU",
        font=font("regular", 24),
        fill=MUT,
    )

    # Statistiche principali
    y = 200
    d.text((pad, y), f"{us_pct}%", font=font("bold", 96), fill=US)
    d.text((pad, y + 112), "on US providers", font=font("bold", 26), fill=FG)
    d.text((pad, y + 146), f"{us} bodies · US CLOUD Act", font=font("regular", 21), fill=MUT)
    x2 = pad + 330
    d.text((x2, y), f"{nat_pct}%", font=font("bold", 96), fill=NAT)
    d.text((x2, y + 112), "national jurisdiction", font=font("bold", 26), fill=FG)
    d.text((x2, y + 146), f"{nat} bodies", font=font("regular", 21), fill=MUT)

    # Sintesi per settore (quota USA sui classificati)
    fam_label = {
        "police": "Police",
        "defence": "Defence",
        "intelligence": "Intelligence",
        "border": "Border",
        "interior_justice": "Interior",
        "cyber": "Cyber",
        "civil_other": "Civil prot.",
    }
    d.text((pad, 404), "US share by sector", font=font("bold", 22), fill=FG)
    cw, ch, gap = 88, 74, 6
    for i, (fam, fk) in enumerate(k.get("by_family", {}).items()):
        c_cls = fk["n_entities"] - fk["overall"]["unknown"]
        pct = round(100 * fk["overall"]["us"] / c_cls) if c_cls else 0
        cx = pad + i * (cw + gap)
        d.rounded_rectangle((cx, 440, cx + cw, 440 + ch), radius=10, fill=LINE)
        f_p = font("bold", 28)
        t = f"{pct}%"
        d.text((cx + (cw - d.textlength(t, font=f_p)) / 2, 448), t, font=f_p, fill=US)
        f_l = font("regular", 15)
        lab = fam_label.get(fam, fam)
        d.text((cx + (cw - d.textlength(lab, font=f_l)) / 2, 488), lab, font=f_l, fill=MUT)

    # Classifica più esposti
    rx = 760
    d.line((rx - 30, 200, rx - 30, 520), fill=LINE, width=2)
    d.text((rx, 196), "Highest US exposure", font=font("bold", 24), fill=FG)
    bar_w = 260
    for i, c in enumerate(top):
        yy = 246 + i * 54
        name = c.get("name", c["country"])
        if len(name) > 16:
            name = name[:15] + "…"
        d.text((rx, yy), name, font=font("regular", 22), fill=FG)
        by = yy + 32
        d.rounded_rectangle((rx, by, rx + bar_w, by + 9), radius=4, fill=LINE)
        w = int(bar_w * c["us_exposure_pct"] / 100)
        if w > 0:
            d.rounded_rectangle((rx, by, rx + w, by + 9), radius=4, fill=US)
        d.text(
            (rx + bar_w + 14, yy + 14),
            f"{c['us_exposure_pct']:.0f}%",
            font=font("bold", 22),
            fill=US,
        )

    # Piè di pagina
    d.line((pad, 548, W - pad, 548), fill=LINE, width=2)
    d.text(
        (pad, 566),
        "Passive public-DNS measurement · weekly update · open data CC BY-SA",
        font=font("regular", 21),
        fill=MUT,
    )
    url = "mxmap.it/eu-security"
    f_url = font("bold", 26)
    tw = d.textlength(url, font=f_url)
    d.text((W - pad - tw, 562), url, font=f_url, fill=FG)

    im.save(OUT, optimize=True)
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

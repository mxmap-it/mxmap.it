"""Anteprima social della home di mxmap.it (Open Graph 1200x630), dai KPI live.

Legge kpi.json (verificato da build_kpi.py) e scrive `og-home.png` alla root:
cosa misuriamo + sintesi dei risultati. Dipendenza opzionale Pillow
(`uv run --with pillow ...`), fuori dal percorso critico della nightly.
Esclude PA Centrale dagli estremi per scelta editoriale (CLAUDE.md, SPOTLIGHT).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
KPI = ROOT / "kpi.json"
OUT = ROOT / "og-home.png"

W, H = 1200, 630
BG = (14, 20, 33)
FG = (236, 239, 244)
MUT = (148, 160, 178)
US = (251, 146, 60)
NAT = (74, 222, 128)
LINE = (40, 50, 68)
IT_G, IT_W, IT_R = (0, 140, 69), (230, 230, 230), (205, 33, 42)
SPOTLIGHT_EXCLUDE = {"PA Centrale"}
SHORT = {
    "Previdenza e Assistenza Sociale": "Previdenza",
    "Gestori di pubblici servizi": "Servizi pubblici",
    "Ordini professionali e Camere": "Ordini e Camere",
    "Consorzi e Unioni di enti locali": "Consorzi e Unioni",
    "Welfare e politiche sociali": "Welfare",
}

FONTS = {
    "bold": ["C:/Windows/Fonts/segoeuib.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "regular": ["C:/Windows/Fonts/segoeui.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
}


def font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    for p in FONTS[kind]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


def it_int(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def it_pct(x: float) -> str:
    return f"{round(x)}%"


def main() -> int:
    k = json.loads(KPI.read_text(encoding="utf-8"))
    n = k["totals"]["n_entities"]
    sov = k["sovereignty"]
    clusters = [
        c
        for c in k["by_cluster"]
        if c["cluster"] not in SPOTLIGHT_EXCLUDE and c["n_entities"] >= 100
    ]
    clusters.sort(key=lambda c: -c["usa_pct"])
    top = clusters[:5]

    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    pad = 56
    for i, col in enumerate((IT_G, IT_W, IT_R)):
        d.rectangle((pad + i * 34, 40, pad + i * 34 + 30, 46), fill=col)
    d.text((pad, 58), "OSSERVATORIO NAZIONALE SOVRANITÀ DIGITALE", font=font("bold", 22), fill=US)
    d.text((pad, 92), "Dove la PA italiana tiene la posta elettronica", font=font("bold", 42), fill=FG)
    d.text(
        (pad, 148),
        f"{it_int(n)} enti pubblici · provider reale da analisi DNS · aggiornamento quotidiano",
        font=font("regular", 23),
        fill=MUT,
    )

    y = 206
    d.text((pad, y), it_pct(sov["extra_eu"]["pct"]), font=font("bold", 96), fill=US)
    d.text((pad, y + 112), "su provider extra-UE", font=font("bold", 26), fill=FG)
    d.text(
        (pad, y + 146),
        f"{it_int(sov['extra_eu']['count'])} enti · CLOUD Act USA",
        font=font("regular", 21),
        fill=MUT,
    )
    x2 = pad + 330
    d.text((x2, y), it_pct(sov["it"]["pct"]), font=font("bold", 96), fill=NAT)
    d.text((x2, y + 112), "su provider italiani", font=font("bold", 26), fill=FG)
    d.text((x2, y + 146), f"{it_int(sov['it']['count'])} enti", font=font("regular", 21), fill=MUT)

    d.text(
        (pad, 420),
        f"Provider europei {str(sov['eu_non_it']['pct']).replace('.', ',')}% · "
        f"non determinabili {str(sov['unknown']['pct']).replace('.', ',')}%",
        font=font("regular", 21),
        fill=MUT,
    )
    d.text(
        (pad, 460),
        "Nuovo: la mappa della sicurezza europea",
        font=font("bold", 20),
        fill=FG,
    )
    d.text((pad, 488), "mxmap.it/eu-security", font=font("regular", 20), fill=US)

    rx = 760
    d.line((rx - 30, 206, rx - 30, 520), fill=LINE, width=2)
    d.text((rx, 202), "Quota su provider USA", font=font("bold", 24), fill=FG)
    bar_w = 260
    for i, c in enumerate(top):
        yy = 250 + i * 54
        name = SHORT.get(c["cluster"], c["cluster"])
        if len(name) > 24:
            name = name[:23] + "…"
        d.text((rx, yy), name, font=font("regular", 21), fill=FG)
        by = yy + 31
        d.rounded_rectangle((rx, by, rx + bar_w, by + 9), radius=4, fill=LINE)
        w = int(bar_w * c["usa_pct"] / 100)
        if w > 0:
            d.rounded_rectangle((rx, by, rx + w, by + 9), radius=4, fill=US)
        d.text((rx + bar_w + 14, yy + 13), it_pct(c["usa_pct"]), font=font("bold", 22), fill=US)

    d.line((pad, 548, W - pad, 548), fill=LINE, width=2)
    d.text(
        (pad, 566),
        "Misura passiva su DNS pubblico · dati aperti CC BY-SA 4.0",
        font=font("regular", 21),
        fill=MUT,
    )
    f_url = font("bold", 28)
    tw = d.textlength("mxmap.it", font=f_url)
    d.text((W - pad - tw, 560), "mxmap.it", font=f_url, fill=FG)

    im.save(OUT, optimize=True)
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

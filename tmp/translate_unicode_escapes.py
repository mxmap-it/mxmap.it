"""Apply Italian translations to literal backslash-escaped strings in index.html.

The JS source uses backslash escapes as TEXT (e.g. the 6 chars: backslash, u, 2, 5, b, e).
Use double-backslash in Python so we match the literal text.
"""
import pathlib
import sys
sys.stdout.reconfigure(encoding="utf-8")

p = pathlib.Path("index.html")
src = p.read_text(encoding="utf-8")

# Each pair: literal text in file (with double backslash) -> Italian replacement.
fixups = [
    ("'Loading municipality data\\u2026'", "'Caricamento dati comuni\\u2026'"),
    ("btn.textContent = 'Loading\\u2026';", "btn.textContent = 'Caricamento\\u2026';"),
    ("'About \\u25be' : 'About \\u25b4'", "'Informazioni \\u25be' : 'Informazioni \\u25b4'"),
    ("'Statistics \\u25be' : 'Statistics \\u25b4'", "'Statistiche \\u25be' : 'Statistiche \\u25b4'"),
    ("'Countries \\u25b4' : 'Countries \\u25be'", "'Paesi \\u25b4' : 'Paesi \\u25be'"),
    ("isMobile ? 'Legend \\u25B8' : ''", "isMobile ? 'Legenda \\u25B8' : ''"),
    ("collapsed ? 'Legend \\u25B8' : '\\u2715'", "collapsed ? 'Legenda \\u25B8' : '\\u2715'"),
    ("placeholder=\"Search\\u2026\"", "placeholder=\"Cerca\\u2026\""),
]

count = 0
missed = []
for old, new in fixups:
    if old in src:
        src = src.replace(old, new)
        count += 1
    else:
        missed.append(old)

p.write_text(src, encoding="utf-8")
print(f"Applied {count}/{len(fixups)} pairs")
for m in missed:
    print(f"MISSED: {m}")

"""Rename + merge provider categories per user request:
   - 'IT pubblico (sovrano)' -> 'Cloud Italiano'
   - merge Aruba/Register.it/Seeweb/InfoCert/Namirial/ISP italiano -> 'Provider Italiano'
   - 'Self-hosted' -> 'Infrastruttura autonoma'
"""
import pathlib
p = pathlib.Path("index.html")
s = p.read_text(encoding="utf-8")

# 1) providerDisplayMap
old_pdm = """const providerDisplayMap = {
  'microsoft': 'Microsoft 365', 'google': 'Google Workspace', 'aws': 'AWS',
  'telia': 'ISP locale', 'tet': 'ISP locale', 'zone': 'ISP locale', 'elkdata': 'ISP locale',
  'local-isp': 'ISP italiano', 'zoho': 'Zoho', 'yandex': 'Yandex', 'independent': 'Self-hosted',
  // Italian commercial providers (mxmap.it Phase 3)
  'aruba': 'Aruba', 'register-it': 'Register.it', 'seeweb': 'Seeweb',
  'infocert': 'InfoCert', 'namirial': 'Namirial',
  // Italian publicly-owned consortium / regional ICT (sovereign)
  'regional-public': 'IT pubblico (sovrano)',
  // Italian private PA contractor
  'pa-contractor-private': 'Contractor PA privato',
  // Provincial-shared (XX.it pattern, no hyperscaler backend identified)
  'provincial-shared': 'Mail provinciale condivisa',
  'unknown': 'Sconosciuto',
};"""
new_pdm = """const providerDisplayMap = {
  'microsoft': 'Microsoft 365', 'google': 'Google Workspace', 'aws': 'AWS',
  // Italian commercial providers — accorpati in un unico "Provider Italiano"
  'aruba':       'Provider Italiano',
  'register-it': 'Provider Italiano',
  'seeweb':      'Provider Italiano',
  'infocert':    'Provider Italiano',
  'namirial':    'Provider Italiano',
  'local-isp':   'Provider Italiano',
  'telia':       'Provider Italiano',
  'tet':         'Provider Italiano',
  'zone':        'Provider Italiano',
  'elkdata':     'Provider Italiano',
  // Italian publicly-owned consortium / regional ICT — sovereign cloud
  'regional-public':       'Cloud Italiano',
  // Italian private PA contractor (still tagged separately)
  'pa-contractor-private': 'Contractor PA privato',
  // Self-hosted (renamed)
  'independent': 'Infrastruttura autonoma',
  // Provincial-shared (XX.it pattern, no hyperscaler backend identified)
  'provincial-shared': 'Mail provinciale condivisa',
  // Foreign minor (not Italian)
  'zoho':   'Zoho',
  'yandex': 'Yandex',
  'unknown': 'Sconosciuto',
};"""
assert old_pdm in s, "providerDisplayMap block not found"
s = s.replace(old_pdm, new_pdm, 1)

# 2) COLORS
old_colors = """const COLORS = {
  // US hyperscalers (CLOUD Act) — red/orange for contrast vs Italian greens
  'Microsoft 365':              '#D42E2E',
  'Google Workspace':           '#FF6B6B',
  'AWS':                        '#FF8C42',
  // ITALIAN — green palette throughout. Sovereign/public is the bright
  // Italian-flag green (#009246); commercial Italian providers are medium
  // greens; self-hosted / consortium-shared / contractor are paler greens.
  'IT pubblico (sovrano)':      '#009246', // Italian flag green
  'Aruba':                      '#2E7D32',
  'Register.it':                '#388E3C',
  'Seeweb':                     '#43A047',
  'InfoCert':                   '#1B5E20',
  'Namirial':                   '#4CAF50',
  'ISP italiano':               '#66BB6A',
  'ISP locale':                 '#66BB6A',
  'Self-hosted':                '#558B2F',
  'Mail provinciale condivisa': '#7CB342',
  'Contractor PA privato':      '#AED581',
  // Non-Italian foreign senders (small share, kept distinct for honesty)
  'Zoho':                       '#7C3AED',
  'Yandex':                     '#FFCC00',
  // Backwards-compatible aliases (used by some upstream code paths)
  'Microsoft':                  '#D42E2E',
  'Google':                     '#FF6B6B',
  'Local Provider':             '#66BB6A',
  'Sconosciuto':                '#BFBFBF',
  'Unknown':                    '#BFBFBF',
};"""
new_colors = """const COLORS = {
  // USA hyperscalers (CLOUD Act) — rosso/arancione, contrasto vs verde italiano
  'Microsoft 365':              '#D42E2E',
  'Google Workspace':           '#FF6B6B',
  'AWS':                        '#FF8C42',
  // ITALIA — palette verde, gradata per grado di sovranità
  'Cloud Italiano':             '#009246', // verde bandiera — Lepida/ARIA/CSI/Insiel/Sogei...
  'Provider Italiano':          '#2E7D32', // Aruba/Register.it/Seeweb/InfoCert/Namirial/ISP
  'Infrastruttura autonoma':    '#558B2F', // ex-Self-hosted/independent
  'Mail provinciale condivisa': '#7CB342',
  'Contractor PA privato':      '#AED581',
  // Foreign minor senders
  'Zoho':                       '#7C3AED',
  'Yandex':                     '#FFCC00',
  // Backwards-compatible aliases (in case some old code references the original keys)
  'Microsoft':                  '#D42E2E',
  'Google':                     '#FF6B6B',
  'Local Provider':             '#2E7D32',
  'Self-hosted':                '#558B2F',
  'IT pubblico (sovrano)':      '#009246',
  'Aruba':                      '#2E7D32',
  'Register.it':                '#2E7D32',
  'Seeweb':                     '#2E7D32',
  'InfoCert':                   '#2E7D32',
  'Namirial':                   '#2E7D32',
  'ISP italiano':               '#2E7D32',
  'ISP locale':                 '#2E7D32',
  'Sconosciuto':                '#BFBFBF',
  'Unknown':                    '#BFBFBF',
};"""
assert old_colors in s, "COLORS block not found"
s = s.replace(old_colors, new_colors, 1)

# 3) TIERS
old_tiers = """const TIERS = {
  'USA (CLOUD Act)': ['Microsoft 365', 'Google Workspace', 'AWS'],
  'Sovrano (PA italiana pubblica)': ['IT pubblico (sovrano)'],
  'Italiano commerciale': ['Aruba', 'Register.it', 'Seeweb', 'InfoCert', 'Namirial', 'ISP italiano', 'ISP locale', 'Contractor PA privato', 'Zoho', 'Yandex'],
  'Self-hosted / condiviso': ['Self-hosted', 'Mail provinciale condivisa'],
  'Sconosciuto': ['Sconosciuto'],
};"""
new_tiers = """const TIERS = {
  'USA (CLOUD Act)': ['Microsoft 365', 'Google Workspace', 'AWS'],
  'Cloud Italiano (sovrano)': ['Cloud Italiano'],
  'Provider Italiano': ['Provider Italiano', 'Contractor PA privato'],
  'Infrastruttura autonoma': ['Infrastruttura autonoma', 'Mail provinciale condivisa'],
  'Altro': ['Zoho', 'Yandex', 'Sconosciuto'],
};"""
assert old_tiers in s, "TIERS block not found"
s = s.replace(old_tiers, new_tiers, 1)

# 4) Legend group HTML
old_legend = """        legendGroupHtml('USA (CLOUD Act)', ['Microsoft 365', 'Google Workspace', 'AWS'], counts) +
        legendGroupHtml('Italia', ['IT pubblico (sovrano)', 'Aruba', 'Register.it', 'Seeweb', 'InfoCert', 'Namirial', 'ISP italiano', 'Contractor PA privato', 'Self-hosted', 'Mail provinciale condivisa', 'Sconosciuto'], counts) +"""
new_legend = """        legendGroupHtml('USA (CLOUD Act)', ['Microsoft 365', 'Google Workspace', 'AWS'], counts) +
        legendGroupHtml('Italia — Cloud sovrano', ['Cloud Italiano'], counts) +
        legendGroupHtml('Italia — Provider commerciali', ['Provider Italiano', 'Contractor PA privato'], counts) +
        legendGroupHtml('Italia — Infrastruttura autonoma', ['Infrastruttura autonoma', 'Mail provinciale condivisa'], counts) +
        legendGroupHtml('Altro', ['Zoho', 'Yandex', 'Sconosciuto'], counts) +"""
assert old_legend in s, "legend block not found"
s = s.replace(old_legend, new_legend, 1)

# 5) DARK_TEXT
s = s.replace(
    "const DARK_TEXT = new Set(['Google Workspace', 'Google', 'AWS', 'Sconosciuto', 'Unknown', 'Yandex', 'Mail provinciale condivisa', 'Contractor PA privato', 'ISP italiano', 'ISP locale', 'Local Provider', 'Namirial']);",
    "const DARK_TEXT = new Set(['Google Workspace', 'Google', 'AWS', 'Sconosciuto', 'Unknown', 'Yandex', 'Mail provinciale condivisa', 'Contractor PA privato']);"
)

p.write_text(s, encoding="utf-8")
print("Renamed + merged categories applied.")

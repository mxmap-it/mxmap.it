"""EU Security Map (#33 F5): KPI + rendiconto inglese `eu-security/index.html`.

Legge data/eu_security/results.json, applica il modello di sovranità relativa
(mail_sovereignty.eu_security), verifica gli invarianti (assert_integrity) e
genera una pagina statica ricercabile con bandierine vendorizzate.
"""

from __future__ import annotations

import html
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from mail_sovereignty import eu_security as es

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "data" / "eu_security" / "results.json"
OUT = ROOT / "eu-security"

# Fuori dal ranking headline (misura l'Europa alleata/allineata).
ANNEX = {"RU", "BY"}

TYPE_LABEL = {
    "police": "Police",
    "gendarmerie": "Gendarmerie",
    "border_guard": "Border / coast guard",
    "intelligence": "Intelligence",
    "interior_ministry": "Interior ministry",
    "defence_ministry": "Defence ministry",
    "armed_forces": "Armed forces / general staff",
    "cybersecurity": "Cybersecurity",
    "other_natsec": "Other national security",
}
BUCKET_LABEL = {
    "national": "National",
    "us": "US provider (CLOUD Act)",
    "eu_other": "Other European",
    "other_foreign": "Other foreign",
    "unknown": "Unknown",
}
PROVIDER_LABEL = {
    "microsoft": "Microsoft 365",
    "google": "Google Workspace",
    "aws": "Amazon (AWS)",
    "independent": "Self-hosted",
    "local-isp": "National ISP",
    "unknown": "Not determinable",
}
METHOD_LABEL = {
    "contact_page": "Address published on the body's official contact page",
    "privacy_page": "Address published in the body's official privacy notice",
    "press_page": "Address published on the body's official press page",
    "other_official": "Address published on an official government page",
    "official_pdf": "Address found in an official document (PDF, notice, register)",
    "third_party": "Address reported by a reliable third-party source",
    "llm_consensus": "Inferred: at least two independent AI assistants (ChatGPT, Claude, DeepSeek, Qwen) "
    "agreed on this domain citing public sources; domain has live MX records",
    "assumed_from_website": "Inferred from the website domain — no published address found",
}
METHOD_SHORT = {
    "contact_page": "official site",
    "privacy_page": "official site",
    "press_page": "official site",
    "other_official": "official site",
    "official_pdf": "official document",
    "third_party": "third-party source",
    "llm_consensus": "AI cross-check",
    "assumed_from_website": "inferred from website",
}


def method_cell(r: dict) -> str:
    ev = r.get("domain_evidence") or {}
    kind = ev.get("kind") or "assumed_from_website"
    if kind not in METHOD_LABEL:
        kind = "third_party"
    title = METHOD_LABEL[kind]
    if ev.get("note"):
        title += f" — e.g. {ev['note']}"
    short = METHOD_SHORT[kind]
    cls = "m-inf" if kind in ("assumed_from_website", "llm_consensus") else "m-ok"
    url = ev.get("url") or ""
    label = f'<span class="{cls}" title="{html.escape(title)}">{short}</span>'
    if url and kind != "assumed_from_website":
        label = f'<a href="{html.escape(url)}" rel="noopener nofollow">{label}</a>'
    return label


GROUP_LABEL = {
    "eu27": "EU member state",
    "efta": "EFTA",
    "uk": "United Kingdom",
    "candidate": "Candidate / neighbour",
    "microstate": "Microstate",
    "eu_institutions": "EU institutions",
    "annex_non_aligned": "Annex",
}


def build() -> dict:
    raw = json.loads(RESULTS.read_text(encoding="utf-8"))
    rows = es.classify_entities(raw)
    kpi = es.compute_kpi(rows)
    es.assert_integrity(kpi, rows)
    for c in kpi["countries"]:
        if c["country"] in ANNEX or c["country"] == "EU":
            c["ranking_eligible"] = False
    meta = {}
    for r in rows:
        meta.setdefault(r["country"], (r["country_name_en"], r["group"]))
    for c in kpi["countries"]:
        c["name"], c["group"] = meta[c["country"]]
    kpi["generated_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"kpi": kpi, "rows": rows}


def flag(cc: str, cls: str = "flag") -> str:
    return f'<img class="{cls}" src="flags/{cc.lower()}.svg" alt="" loading="lazy">'


def page(data: dict) -> str:
    kpi, rows = data["kpi"], data["rows"]
    n = kpi["n_entities"]
    cls = n - kpi["overall"]["unknown"]
    us = kpi["overall"]["us"]
    nat = kpi["overall"]["national"]
    elig = [c for c in kpi["countries"] if c["ranking_eligible"]]
    worst = elig[:10]
    best = sorted(elig, key=lambda c: (-c["national_pct"], c["us_exposure_pct"]))[:10]

    def rank_rows(items, field, color):
        out = []
        for i, c in enumerate(items, 1):
            v = c[field]
            out.append(
                f'<li><span class="rk">{i}</span>{flag(c["country"])}'
                f'<a href="#c-{c["country"]}">{html.escape(c["name"])}</a>'
                f'<span class="bar"><i style="width:{v}%;background:var({color})"></i></span>'
                f'<b>{v:.0f}%</b><small>{c["classified"]} classified</small></li>'
            )
        return "\n".join(out)

    def type_table():
        out = []
        for t, b in kpi["by_type"].items():
            tot = sum(b.values())
            c = tot - b["unknown"]
            pct = round(100 * b["us"] / c) if c else 0
            out.append(
                f"<tr><td>{TYPE_LABEL.get(t, t)}</td><td>{tot}</td>"
                f'<td>{b["national"]}</td><td>{b["us"]}</td><td>{b["eu_other"]}</td>'
                f'<td>{b["unknown"]}</td><td><b>{pct}%</b></td></tr>'
            )
        return "\n".join(out)

    by_cc: dict[str, list] = {}
    for r in rows:
        by_cc.setdefault(r["country"], []).append(r)

    def country_sections(ccs):
        out = []
        for c in ccs:
            cc = c["country"]
            trs = []
            for r in sorted(by_cc[cc], key=lambda x: (x["type"], x["name_en"] or "")):
                prov = PROVIDER_LABEL.get(r["provider"], r["provider"])
                web = r.get("website") or ""
                hay = " ".join(
                    str(x)
                    for x in (
                        c["name"], cc, r["name_native"], r["name_en"], r["acronym"],
                        r["type"], prov, r["primary_domain"],
                    )
                    if x
                ).lower()
                trs.append(
                    f'<tr data-b="{r["bucket"]}" data-t="{r["type"]}" '
                    f'data-q="{html.escape(hay)}">'
                    f'<td><b>{html.escape(r["name_en"] or "")}</b>'
                    f'{" (" + html.escape(r["acronym"]) + ")" if r.get("acronym") else ""}'
                    f'<br><small>{html.escape(r["name_native"] or "")}</small></td>'
                    f'<td>{TYPE_LABEL.get(r["type"], r["type"])}</td>'
                    f'<td><a href="{html.escape(web)}" rel="noopener">{html.escape(web.split("//")[-1].rstrip("/"))}</a></td>'
                    f'<td><code>{html.escape(r["primary_domain"] or "—")}</code>'
                    f"<br><small>{method_cell(r)}</small></td>"
                    f"<td>{html.escape(prov)}</td>"
                    f'<td><span class="pill {r["bucket"]}">{BUCKET_LABEL[r["bucket"]]}</span></td></tr>'
                )
            stat = (
                f'US exposure <b>{c["us_exposure_pct"]:.0f}%</b> · national '
                f'<b>{c["national_pct"]:.0f}%</b> · {c["n"]} bodies'
            )
            out.append(
                f'<section class="country" id="c-{cc}"><h3>{flag(cc, "flag big")}'
                f'{html.escape(c["name"])} <small>{GROUP_LABEL.get(c["group"], "")}</small>'
                f'<span class="cstat">{stat}</span></h3>'
                f'<div class="tw"><table><thead><tr><th>Body</th><th>Type</th><th>Website</th>'
                f"<th>Mail domain · how established</th><th>Mail provider</th><th>Jurisdiction</th></tr></thead>"
                f'<tbody>{"".join(trs)}</tbody></table></div></section>'
            )
        return "\n".join(out)

    main_cc = sorted(
        [c for c in kpi["countries"] if c["country"] not in ANNEX and c["country"] != "EU"],
        key=lambda c: c["name"],
    )
    eu_cc = [c for c in kpi["countries"] if c["country"] == "EU"]
    annex_cc = [c for c in kpi["countries"] if c["country"] in ANNEX]
    type_opts = "".join(f'<option value="{k}">{v}</option>' for k, v in TYPE_LABEL.items())
    b_opts = "".join(f'<option value="{k}">{v}</option>' for k, v in BUCKET_LABEL.items())

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EU Security Mail Map</title>
<meta name="description" content="Where Europe's police, intelligence, interior, defence and cybersecurity bodies host their email — and how many depend on US providers subject to the CLOUD Act.">
<link rel="canonical" href="https://mxmap.it/eu-security/">
<style>
:root{{--bg:#fff;--fg:#1a1d21;--mut:#5d6670;--line:#e3e6ea;--card:#f6f7f9;--us:#c2410c;--nat:#15803d;--eu:#1d4ed8;--of:#7c3aed;--unk:#9aa3ad}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#111316;--fg:#e8eaed;--mut:#9aa3ad;--line:#2a2f35;--card:#191c20;--us:#fb923c;--nat:#4ade80;--eu:#60a5fa;--of:#c4b5fd;--unk:#6b7280}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}}
main{{max-width:1180px;margin:0 auto;padding:24px 16px 64px}}a{{color:var(--eu)}}
h1{{font-size:clamp(24px,4vw,36px);margin:.2em 0}}h2{{margin-top:2.2em;border-bottom:1px solid var(--line);padding-bottom:.3em}}
.lead{{color:var(--mut);max-width:780px}}.caveat{{background:var(--card);border-left:4px solid var(--eu);padding:12px 16px;margin:18px 0;max-width:900px;font-size:14px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:20px 0}}
.kpi{{background:var(--card);border-radius:10px;padding:14px}}.kpi b{{font-size:28px;display:block}}.kpi span{{color:var(--mut);font-size:13px}}
.flag{{width:22px;height:16px;border-radius:2px;vertical-align:-3px;margin-right:8px;box-shadow:0 0 0 1px var(--line)}}.flag.big{{width:30px;height:22px}}
.ranks{{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:24px}}
.ranks ol{{list-style:none;padding:0;margin:0}}.ranks li{{display:grid;grid-template-columns:22px 30px 1fr 110px 42px;align-items:center;gap:4px;padding:5px 0;border-bottom:1px solid var(--line)}}
.ranks li small{{grid-column:3/6;color:var(--mut);font-size:12px;margin-top:-4px}}.rk{{color:var(--mut)}}
.bar{{height:8px;background:var(--line);border-radius:4px;overflow:hidden}}.bar i{{display:block;height:100%}}
table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top}}th{{color:var(--mut);font-weight:600}}
.tw{{overflow-x:auto}}code{{font-size:13px}}.m-ok{{color:var(--nat)}}.m-inf{{color:var(--us)}}small{{color:var(--mut)}}
.pill{{display:inline-block;padding:1px 8px;border-radius:10px;font-size:12px;color:#fff;white-space:nowrap}}
.pill.us{{background:var(--us)}}.pill.national{{background:var(--nat)}}.pill.eu_other{{background:var(--eu)}}.pill.other_foreign{{background:var(--of)}}.pill.unknown{{background:var(--unk)}}
.filters{{position:sticky;top:0;background:var(--bg);padding:10px 0;display:flex;gap:8px;flex-wrap:wrap;z-index:2;border-bottom:1px solid var(--line)}}
.filters input,.filters select{{font:inherit;padding:7px 10px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--fg)}}.filters input{{flex:1;min-width:200px}}
.country h3{{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:28px 0 8px}}.cstat{{margin-left:auto;font-weight:400;font-size:14px;color:var(--mut)}}
footer{{margin-top:48px;color:var(--mut);font-size:13px}}
</style></head><body><main>
<p><a href="/">mxmap.it</a> · Osservatorio Nazionale Sovranità Digitale</p>
<h1>EU Security Mail Map</h1>
<p class="lead">Where Europe's police forces, intelligence services, interior and defence ministries,
cybersecurity agencies and EU security institutions host their <b>public email</b> — and how many depend on
US-based providers subject to the <b>US CLOUD Act</b>.</p>
<div class="caveat"><b>What this measures.</b> Only public DNS records (MX, SPF, DKIM) of each body's official
mail domain — the same passive lookup any mail server performs before delivering a message. Classified networks are
separate by design and are <b>not</b> measured here. Public mail still carries real institutional traffic
(international cooperation, citizen reports, procurement), and its metadata is itself sensitive: this map reads
jurisdictional exposure as a <b>resilience and policy</b> question, not as a judgement on any institution.</div>
<div class="kpis">
<div class="kpi"><b>{n}</b><span>security bodies in {kpi["n_countries"]} countries + EU</span></div>
<div class="kpi"><b style="color:var(--us)">{round(100 * us / cls) if cls else 0}%</b><span>of classified bodies use a US provider ({us})</span></div>
<div class="kpi"><b style="color:var(--nat)">{round(100 * nat / cls) if cls else 0}%</b><span>keep mail under national jurisdiction ({nat})</span></div>
<div class="kpi"><b>{kpi["overall"]["unknown"]}</b><span>not determinable from DNS</span></div>
</div>
<h2>Country ranking</h2>
<p class="lead">Share of each country's classified security bodies by mail jurisdiction. Countries with at least
{kpi["min_classified_for_ranking"]} classified bodies; Russia and Belarus are listed in the annex, outside the ranking.</p>
<div class="ranks"><div><h3>Highest US exposure</h3><ol>{rank_rows(worst, "us_exposure_pct", "--us")}</ol></div>
<div><h3>Best positioned (national jurisdiction)</h3><ol>{rank_rows(best, "national_pct", "--nat")}</ol></div></div>
<h2>By type of body</h2><div class="tw"><table><thead><tr><th>Type</th><th>Bodies</th><th>National</th><th>US</th><th>Other European</th><th>Unknown</th><th>US share of classified</th></tr></thead>
<tbody>{type_table()}</tbody></table></div>
<h2>Directory by country</h2>
<div class="filters"><input id="q" type="search" placeholder="Search body, country, acronym, provider, domain…" aria-label="Search">
<select id="ft" aria-label="Type"><option value="">All types</option>{type_opts}</select>
<select id="fb" aria-label="Jurisdiction"><option value="">All jurisdictions</option>{b_opts}</select></div>
{country_sections(eu_cc)}
{country_sections(main_cc)}
<h2>Annex — non-aligned states</h2>
{country_sections(annex_cc)}
<footer><p><b>Method.</b> Bodies and their mail domains were researched from official sources (contact, press and
privacy pages; evidence per domain in the open dataset). Each domain is classified by the mxmap engine
(<a href="/methodology.html">methodology</a>): provider from MX/CNAME, gateways looked through only with primary
signals. Jurisdiction is relative to the body's own country: <i>National</i> = provider seated in that country, or
self-hosted/ISP mail servers located there; <i>US provider</i> = Microsoft, Google, Amazon (CLOUD Act);
<i>Other European</i> = a provider seated in another European state. For EU institutions any European provider counts as national.
English names are official where published, otherwise faithful translations.</p>
<p><b>How each mail domain was established</b> (shown under every domain; hover for detail, click for the source):
<span class="m-ok">official site</span> = an address on that domain is published on the body's own contact, press or privacy page;
<span class="m-ok">official document</span> = an address appears in an official PDF, procurement notice or register;
<span class="m-ok">third-party source</span> = reported by a reliable external directory (e.g. FIRST, Trusted Introducer);
<span class="m-inf">AI cross-check</span> = no address found by us; at least two independent AI assistants (ChatGPT, Claude, DeepSeek, Qwen) agreed on the domain citing public sources, and the domain has live MX records;
<span class="m-inf">inferred from website</span> = no published address anywhere; the website domain is assumed (many intelligence services publish only web forms).
Inferred domains are lower-confidence and are flagged so readers can weigh them.</p>
<p>Data: <a href="kpi.json">kpi.json</a> · CC BY-SA 4.0 · generated {kpi["generated_at"]} · flags: flag-icons (MIT).</p></footer>
</main>
<script>
const q=document.getElementById('q'),ft=document.getElementById('ft'),fb=document.getElementById('fb');
function f(){{const s=q.value.trim().toLowerCase(),t=ft.value,b=fb.value;
document.querySelectorAll('.country').forEach(sec=>{{let any=0;sec.querySelectorAll('tbody tr').forEach(tr=>{{
const ok=(!s||tr.dataset.q.includes(s))&&(!t||tr.dataset.t===t)&&(!b||tr.dataset.b===b);tr.hidden=!ok;if(ok)any=1;}});sec.hidden=!any;}});}}
[q,ft,fb].forEach(e=>e.addEventListener('input',f));
</script></body></html>
"""


def main() -> int:
    data = build()
    OUT.mkdir(exist_ok=True)
    (OUT / "kpi.json").write_text(
        json.dumps(data["kpi"], ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (OUT / "index.html").write_text(page(data), encoding="utf-8")
    k = data["kpi"]
    print(f"{k['n_entities']} bodies, overall {k['overall']}")
    for c in [c for c in k["countries"] if c["ranking_eligible"]][:5]:
        print(f"  top US: {c['country']} {c['us_exposure_pct']}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())

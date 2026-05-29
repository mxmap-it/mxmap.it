import asyncio
import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from mail_sovereignty.classify import classify, detect_gateway
from mail_sovereignty.constants import CONCURRENCY, LOCAL_ISP_ASNS, PARTITIONED_COUNTRIES
from mail_sovereignty.dns import (
    lookup_autodiscover,
    lookup_dkim,
    lookup_mx,
    lookup_tenant,
    lookup_txt,
    resolve_mx_asns,
    resolve_mx_countries,
    resolve_mx_cnames,
    resolve_spf_includes,
)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

SEED_FILES = {
    "EE": "municipalities_ee.json",
    "LV": "municipalities_lv.json",
    "LT": "municipalities_lt.json",
    "FI": "municipalities_fi.json",
    "NO": "municipalities_no.json",
    "SE": "municipalities_se.json",
    "DE": "municipalities_de.json",
    "DK": "municipalities_dk.json",
    "AD": "municipalities_ad.json",
    "LU": "municipalities_lu.json",
    "BE": "municipalities_be.json",
    "AT": "municipalities_at.json",
    "CZ": "municipalities_cz.json",
    "IS": "municipalities_is.json",
    "ES": "municipalities_es.json",
    "FR": "municipalities_fr.json",
    "PL": "municipalities_pl.json",
    "PT": "municipalities_pt.json",
    "IT": "municipalities_it.json",
    "NL": "municipalities_nl.json",
    "IE": "municipalities_ie.json",
    "BG": "municipalities_bg.json",
    "SK": "municipalities_sk.json",
    "SI": "municipalities_si.json",
    "GB": "municipalities_gb.json",
    "HR": "municipalities_hr.json",
    "CY": "municipalities_cy.json",
    "GR": "municipalities_gr.json",
    "HU": "municipalities_hu.json",
    "MT": "municipalities_mt.json",
    "RO": "municipalities_ro.json",
    "AL": "municipalities_al.json",
    "XK": "municipalities_xk.json",
    "ME": "municipalities_me.json",
    "BA": "municipalities_ba.json",
    "RS": "municipalities_rs.json",
    "MK": "municipalities_mk.json",
    "UA": "municipalities_ua.json",
    "MD": "municipalities_md.json",
    "LI": "municipalities_li.json",
    "SM": "municipalities_sm.json",
    "GE": "municipalities_ge.json",
    "AM": "municipalities_am.json",
    "AZ": "municipalities_az.json",
    "BY": "municipalities_by.json",
    "TR": "municipalities_tr.json",
    "MC": "municipalities_mc.json",
    "GL": "municipalities_gl.json",
    # Oceania
    "AU": "municipalities_au.json",
    "NZ": "municipalities_nz.json",
    "FJ": "municipalities_fj.json",
    "WS": "municipalities_ws.json",
    "VU": "municipalities_vu.json",
    "TO": "municipalities_to.json",
    "NR": "municipalities_nr.json",
    "PW": "municipalities_pw.json",
    # Southeast Asia
    "ID": "municipalities_id.json",
    "PG": "municipalities_pg.json",
    "MY": "municipalities_my.json",
    "TH": "municipalities_th.json",
    "KH": "municipalities_kh.json",
    "PH": "municipalities_ph.json",
    "VN": "municipalities_vn.json",
    "MM": "municipalities_mm.json",
    # Remaining SE Asia
    "LA": "municipalities_la.json",
    "BN": "municipalities_bn.json",
    "TL": "municipalities_tl.json",
    # East Asia
    "JP": "municipalities_jp.json",
    "TW": "municipalities_tw.json",
    "KR": "municipalities_kr.json",
    "KP": "municipalities_kp.json",
    "CN": "municipalities_cn.json",
    "MN": "municipalities_mn.json",
    # South Asia
    "IN": "municipalities_in.json",
    "BD": "municipalities_bd.json",
    "PK": "municipalities_pk.json",
    "LK": "municipalities_lk.json",
    "NP": "municipalities_np.json",
    # Central Asia
    "KZ": "municipalities_kz.json",
    "UZ": "municipalities_uz.json",
    "KG": "municipalities_kg.json",
    "RU": "municipalities_ru.json",
    # Middle East
    "OM": "municipalities_om.json",
    "AE": "municipalities_ae.json",
    "QA": "municipalities_qa.json",
    "BH": "municipalities_bh.json",
    "SA": "municipalities_sa.json",
    "IQ": "municipalities_iq.json",
    "JO": "municipalities_jo.json",
    "LB": "municipalities_lb.json",
    "KW": "municipalities_kw.json",
    "IR": "municipalities_ir.json",
    "IL": "municipalities_il.json",
    # South America
    "AR": "municipalities_ar.json",
    "BO": "municipalities_bo.json",
    "BR": "municipalities_br.json",
    "CL": "municipalities_cl.json",
    "CO": "municipalities_co.json",
    "EC": "municipalities_ec.json",
    "GY": "municipalities_gy.json",
    "PE": "municipalities_pe.json",
    "PY": "municipalities_py.json",
    "SR": "municipalities_sr.json",
    "UY": "municipalities_uy.json",
    "VE": "municipalities_ve.json",
    # Canada + Mexico
    "CA": "municipalities_ca.json",
    "MX": "municipalities_mx.json",
    # Central America
    "BZ": "municipalities_bz.json",
    "GT": "municipalities_gt.json",
    "HN": "municipalities_hn.json",
    "SV": "municipalities_sv.json",
    "NI": "municipalities_ni.json",
    "CR": "municipalities_cr.json",
    "PA": "municipalities_pa.json",
    # Africa — North
    "DZ": "municipalities_dz.json",
    "EG": "municipalities_eg.json",
    "LY": "municipalities_ly.json",
    "MA": "municipalities_ma.json",
    "TN": "municipalities_tn.json",
    "SD": "municipalities_sd.json",
    # Africa — West
    "BJ": "municipalities_bj.json",
    "BF": "municipalities_bf.json",
    "CV": "municipalities_cv.json",
    "CI": "municipalities_ci.json",
    "GM": "municipalities_gm.json",
    "GH": "municipalities_gh.json",
    "GN": "municipalities_gn.json",
    "GW": "municipalities_gw.json",
    "LR": "municipalities_lr.json",
    "ML": "municipalities_ml.json",
    "MR": "municipalities_mr.json",
    "NE": "municipalities_ne.json",
    "NG": "municipalities_ng.json",
    "SN": "municipalities_sn.json",
    "SL": "municipalities_sl.json",
    "TG": "municipalities_tg.json",
    # Africa — Central
    "CM": "municipalities_cm.json",
    "CF": "municipalities_cf.json",
    "TD": "municipalities_td.json",
    "CG": "municipalities_cg.json",
    "CD": "municipalities_cd.json",
    "GQ": "municipalities_gq.json",
    "GA": "municipalities_ga.json",
    "ST": "municipalities_st.json",
    # Africa — East
    "BI": "municipalities_bi.json",
    "KM": "municipalities_km.json",
    "DJ": "municipalities_dj.json",
    "ER": "municipalities_er.json",
    "ET": "municipalities_et.json",
    "KE": "municipalities_ke.json",
    "MG": "municipalities_mg.json",
    "MW": "municipalities_mw.json",
    "MU": "municipalities_mu.json",
    "MZ": "municipalities_mz.json",
    "RW": "municipalities_rw.json",
    "SC": "municipalities_sc.json",
    "SO": "municipalities_so.json",
    "SS": "municipalities_ss.json",
    "TZ": "municipalities_tz.json",
    "UG": "municipalities_ug.json",
    # Africa — Southern
    "AO": "municipalities_ao.json",
    "BW": "municipalities_bw.json",
    "SZ": "municipalities_sz.json",
    "LS": "municipalities_ls.json",
    "NA": "municipalities_na.json",
    "ZA": "municipalities_za.json",
    "ZM": "municipalities_zm.json",
    "ZW": "municipalities_zw.json",
    # Caribbean
    "CU": "municipalities_cu.json",
    "HT": "municipalities_ht.json",
    "DO": "municipalities_do.json",
    "JM": "municipalities_jm.json",
    "TT": "municipalities_tt.json",
    "BS": "municipalities_bs.json",
    "BB": "municipalities_bb.json",
    "AG": "municipalities_ag.json",
    "DM": "municipalities_dm.json",
    "GD": "municipalities_gd.json",
    "KN": "municipalities_kn.json",
    "LC": "municipalities_lc.json",
    "VC": "municipalities_vc.json",
    # Asia (additional)
    "AF": "municipalities_af.json",
    "SG": "municipalities_sg.json",
    "YE": "municipalities_ye.json",
    "SY": "municipalities_sy.json",
    "PS": "municipalities_ps.json",
    "TJ": "municipalities_tj.json",
    "TM": "municipalities_tm.json",
    "MV": "municipalities_mv.json",
    "BT": "municipalities_bt.json",
    # Oceania (additional)
    "SB": "municipalities_sb.json",
    "MH": "municipalities_mh.json",
    "FM": "municipalities_fm.json",
    "KI": "municipalities_ki.json",
    "TV": "municipalities_tv.json",
}


def url_to_domain(url: str | None) -> str | None:
    """Extract the base domain from a URL."""
    if not url:
        return None
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = parsed.hostname or ""
    if host.startswith("www."):
        host = host[4:]
    return host if host else None


def guess_domains(name: str, country: str = "") -> list[str]:
    """Generate plausible domain guesses for a municipality."""
    raw = name.lower().strip()
    raw = re.sub(r"\s*\(.*?\)\s*", "", raw)

    # Remove common prefixes in municipality names
    for prefix in [
        "landkreis ",
        "kreis ",
        "stadt ",
        "sveitarfélagið ",
        "diputación de ",
        "diputación provincial de ",
        "diputación foral de ",
        "département de ",
        "conseil départemental de ",
        "conseil départemental du ",
        "conseil départemental des ",
        "powiat ",
        "município de ",
        "município do ",
        "município da ",
        "câmara municipal de ",
        "câmara municipal do ",
        "câmara municipal da ",
        "provincia di ",
        "provincia del ",
        "provincia della ",
        "città metropolitana di ",
        "gemeente ",  # Dutch
        "city of ",  # UK
        "royal borough of ",  # UK
        "borough of ",  # UK
        "london borough of ",  # UK
        "metropolitan borough of ",  # UK
        "općina ",  # Croatian: municipality
        "grad ",  # Croatian: city
        "δήμος ",  # Greek: municipality
        "dimos ",  # Greek: municipality (romanized)
        "municipality of ",  # Generic (GR/CY/MT)
        "județul ",  # Romanian: county
        "consiliul județean ",  # Romanian: county council
        "primăria ",  # Romanian: city hall
        "bashkia ",  # Albanian: municipality
        "komuna e ",  # Albanian/Kosovo: municipality
        "opština ",  # Serbian/Montenegrin: municipality
        "općina ",  # Bosnian: municipality (same as Croatian)
    ]:
        if raw.startswith(prefix):
            raw = raw[len(prefix) :]

    # Remove common suffixes in municipality names
    for suffix in [
        " vald",
        " linn",  # Estonian
        " novads",
        " pilsēta",
        " valstspilsēta",  # Latvian
        " rajono savivaldybė",
        " miesto savivaldybė",  # Lithuanian
        " savivaldybė",
        " kaupunki",
        " kunta",  # Finnish
        " kommune",  # Norwegian
        " kommun",  # Swedish
        " (kreisfreie stadt)",  # German
        " (statutarstadt)",
        " (marktgemeinde)",  # Austrian
        "bær",
        "hreppur",
        "sveit",
        "kaupstaður",  # Icelandic
        " county council",
        " city council",
        " city and county council",  # Irish
        " borough council",
        " district council",
        " council",  # UK
        " municipality",  # GR/CY/MT
        " district",  # HU
        " county",  # RO/HU
        " járás",  # Hungarian: district
        " megye",  # Hungarian: county
        " regional council",  # AU/NZ
        " shire council",
        " shire",  # AU
        " canton",
        " cantón",  # Ecuador
        " municipio",  # South America (ES)
        " município",  # Brazil (PT)
        " distrito",  # Peru
        " departamento",  # Argentina/Uruguay
        " provincia",  # Peru
        " comuna",  # Chile
        " partido",  # Argentina (Buenos Aires)
        " ressort",  # Suriname
    ]:
        if raw.endswith(suffix):
            raw = raw[: -len(suffix)]

    # Diacritics transliteration
    translits = [
        ("ä", "a"),
        ("ö", "o"),
        ("ü", "u"),
        ("õ", "o"),  # Estonian
        ("š", "s"),
        ("ž", "z"),
        ("č", "c"),
        ("ř", "r"),  # Shared
        ("ā", "a"),
        ("ē", "e"),
        ("ī", "i"),
        ("ū", "u"),  # Latvian
        ("ķ", "k"),
        ("ļ", "l"),
        ("ņ", "n"),
        ("ģ", "g"),
        ("ė", "e"),
        ("į", "i"),
        ("ų", "u"),
        ("ū", "u"),  # Lithuanian
        ("å", "a"),  # Finnish/Nordic
        ("ø", "o"),
        ("æ", "ae"),  # Norwegian/Danish
        ("í", "i"),
        ("ý", "y"),
        ("ď", "d"),
        ("ť", "t"),
        ("ň", "n"),  # Czech/Slovak
        ("ľ", "l"),
        ("ĺ", "l"),
        ("ŕ", "r"),  # Slovak
        ("þ", "th"),
        ("ð", "d"),  # Icelandic
        ("á", "a"),
        ("ú", "u"),
        ("é", "e"),
        ("ó", "o"),  # Icelandic accents
        ("ñ", "n"),  # Spanish
        ("ã", "a"),  # Portuguese
        ("ą", "a"),
        ("ć", "c"),
        ("ę", "e"),
        ("ł", "l"),
        ("ń", "n"),
        ("ś", "s"),
        ("ź", "z"),
        ("ż", "z"),  # Polish
        ("è", "e"),
        ("ê", "e"),
        ("ë", "e"),
        ("à", "a"),
        ("â", "a"),
        ("ô", "o"),
        ("û", "u"),
        ("ù", "u"),
        ("î", "i"),
        ("ï", "i"),
        ("ç", "c"),
        ("œ", "oe"),  # French
        ("ì", "i"),
        ("ò", "o"),  # Italian grave accents
        ("ъ", "a"),  # Bulgarian Cyrillic
        ("đ", "dj"),  # Croatian
        ("ő", "o"),
        ("ű", "u"),  # Hungarian double-acute
        ("ț", "t"),
        ("ș", "s"),
        ("ă", "a"),  # Romanian
        ("ħ", "h"),
        ("ġ", "g"),
        ("ċ", "c"),  # Maltese
    ]
    clean = raw
    for a, b in translits:
        clean = clean.replace(a, b)

    def slugify(s):
        s = re.sub(r"['\u2019`]", "", s)
        s = re.sub(r"[^a-z0-9]+", "-", s)
        return s.strip("-")

    slugs = {slugify(clean), slugify(raw)} - {""}

    # Danish convention: å→aa, ø→oe (e.g., Aabenraa, Aalborg)
    if country == "DK" or not country:
        danish_translits = [("å", "aa"), ("ø", "oe")]
        dk_clean = raw
        for a, b in danish_translits:
            dk_clean = dk_clean.replace(a, b)
        dk_slug = slugify(dk_clean)
        if dk_slug:
            slugs.add(dk_slug)

    # German umlaut expansion (ä→ae, ö→oe, ü→ue, ß→ss)
    if country == "DE" or not country:
        german_translits = [("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")]
        de_clean = raw
        for a, b in german_translits:
            de_clean = de_clean.replace(a, b)
        de_slug = slugify(de_clean)
        if de_slug:
            slugs.add(de_slug)

    # Determine TLDs based on country
    tld_map = {
        "EE": [".ee"],
        "LV": [".lv"],
        "LT": [".lt"],
        "FI": [".fi"],
        "NO": [".no", ".kommune.no"],
        "SE": [".se"],
        "DE": [".de"],
        "DK": [".dk"],
        "AD": [".ad"],
        "LU": [".lu"],
        "BE": [".be"],
        "AT": [".gv.at", ".at"],
        "CZ": [".cz"],
        "IS": [".is"],
        "ES": [".es", ".gob.es", ".cat", ".eus", ".gal"],
        "FR": [".fr", ".gouv.fr"],
        "PL": [".pl", ".gov.pl"],
        "PT": [".pt"],
        "IT": [".it", ".gov.it"],
        "NL": [".nl"],
        "IE": [".ie"],
        "BG": [".bg"],
        "SK": [".sk"],
        "SI": [".si"],
        "GB": [".gov.uk", ".uk"],
        "HR": [".hr"],
        "CY": [".org.cy", ".com.cy", ".cy"],
        "GR": [".gr", ".gov.gr"],
        "HU": [".hu"],
        "MT": [".gov.mt", ".org.mt", ".com.mt", ".mt"],
        "RO": [".ro"],
        "AL": [".al", ".gov.al"],
        "XK": [".rks-gov.net", ".com"],
        "ME": [".me"],
        "BA": [".ba", ".gov.ba"],
        "RS": [".rs", ".org.rs"],
        "MK": [".mk", ".gov.mk"],
        "UA": [".ua", ".gov.ua"],
        "MD": [".md"],
        "LI": [".li"],
        "SM": [".sm", ".org"],
        "GE": [".ge", ".gov.ge"],
        "AM": [".am"],
        "AZ": [".az", ".gov.az"],
        "BY": [".by", ".gov.by"],
        "TR": [".gov.tr", ".bel.tr", ".tr"],
        "MC": [".mc", ".gouv.mc"],
        "GL": [".gl"],
        # Oceania
        "AU": [".gov.au", ".com.au", ".au"],
        "NZ": [".govt.nz", ".co.nz", ".nz"],
        "FJ": [".gov.fj", ".fj"],
        "WS": [".gov.ws", ".ws"],
        "VU": [".gov.vu", ".vu"],
        "TO": [".gov.to", ".to"],
        "NR": [".gov.nr", ".nr"],
        "PW": [".gov.pw", ".pw"],
        # Southeast Asia
        "ID": [".go.id", ".id"],
        "PG": [".gov.pg", ".pg"],
        "MY": [".gov.my", ".com.my", ".my"],
        "TH": [".go.th", ".or.th", ".th"],
        "KH": [".gov.kh", ".kh"],
        "PH": [".gov.ph", ".ph"],
        "VN": [".gov.vn", ".vn"],
        "MM": [".gov.mm", ".mm"],
        # Remaining SE Asia
        "LA": [".gov.la", ".la"],
        "BN": [".gov.bn", ".bn"],
        "TL": [".gov.tl", ".tl"],
        # East Asia
        "JP": [".lg.jp", ".jp"],
        "TW": [".gov.tw", ".tw"],
        "KR": [".go.kr", ".or.kr", ".kr"],
        "KP": [".kp"],
        "CN": [".gov.cn", ".cn"],
        "MN": [".gov.mn", ".mn"],
        # South Asia
        "IN": [".gov.in", ".nic.in", ".in"],
        "BD": [".gov.bd", ".bd"],
        "PK": [".gov.pk", ".pk"],
        "LK": [".gov.lk", ".lk"],
        "NP": [".gov.np", ".np"],
        # Central Asia
        "KZ": [".gov.kz", ".kz"],
        "UZ": [".gov.uz", ".uz"],
        "KG": [".gov.kg", ".kg"],
        "RU": [".gov.ru", ".ru"],
        # Middle East
        "OM": [".gov.om", ".om"],
        "AE": [".gov.ae", ".ae"],
        "QA": [".gov.qa", ".qa"],
        "BH": [".gov.bh", ".bh"],
        "SA": [".gov.sa", ".sa"],
        "IQ": [".gov.iq", ".iq"],
        "JO": [".gov.jo", ".jo"],
        "LB": [".gov.lb", ".lb"],
        "KW": [".gov.kw", ".kw"],
        "IR": [".gov.ir", ".ir"],
        "IL": [".gov.il", ".muni.il", ".il"],
        # South America
        "AR": [".gob.ar", ".gov.ar", ".ar"],
        "BO": [".gob.bo", ".bo"],
        "BR": [".gov.br", ".com.br", ".br"],
        "CL": [".gob.cl", ".cl"],
        "CO": [".gov.co", ".co"],
        "EC": [".gob.ec", ".ec"],
        "GY": [".gov.gy", ".gy"],
        "PE": [".gob.pe", ".pe"],
        "PY": [".gov.py", ".py"],
        "SR": [".gov.sr", ".sr"],
        "UY": [".gub.uy", ".uy"],
        "VE": [".gob.ve", ".ve"],
        # Canada + Mexico
        "CA": [".ca", ".gc.ca"],
        "MX": [".gob.mx", ".mx"],
        # Central America
        "BZ": [".gov.bz", ".bz"],
        "GT": [".gob.gt", ".gt"],
        "HN": [".gob.hn", ".hn"],
        "SV": [".gob.sv", ".sv"],
        "NI": [".gob.ni", ".ni"],
        "CR": [".go.cr", ".cr"],
        "PA": [".gob.pa", ".pa"],
        # Africa — North
        "DZ": [".dz", ".gov.dz"],
        "EG": [".gov.eg", ".eg"],
        "LY": [".gov.ly", ".ly"],
        "MA": [".ma", ".gov.ma"],
        "TN": [".gov.tn", ".tn"],
        "SD": [".gov.sd", ".sd"],
        # Africa — West
        "BJ": [".bj", ".gouv.bj"],
        "BF": [".bf", ".gov.bf"],
        "CV": [".cv", ".gov.cv"],
        "CI": [".ci", ".gouv.ci"],
        "GM": [".gm", ".gov.gm"],
        "GH": [".gov.gh", ".gh"],
        "GN": [".gov.gn", ".gn"],
        "GW": [".gw", ".gov.gw"],
        "LR": [".gov.lr", ".lr"],
        "ML": [".ml", ".gouv.ml"],
        "MR": [".mr", ".gov.mr"],
        "NE": [".ne", ".gouv.ne"],
        "NG": [".gov.ng", ".ng"],
        "SN": [".sn", ".gouv.sn"],
        "SL": [".gov.sl", ".sl"],
        "TG": [".tg", ".gouv.tg"],
        # Africa — Central
        "CM": [".cm", ".gov.cm"],
        "CF": [".cf", ".gouv.cf"],
        "TD": [".td", ".gouv.td"],
        "CG": [".cg", ".gouv.cg"],
        "CD": [".cd", ".gouv.cd"],
        "GQ": [".gq", ".gov.gq"],
        "GA": [".ga", ".gouv.ga"],
        "ST": [".st", ".gov.st"],
        # Africa — East
        "BI": [".bi", ".gov.bi"],
        "KM": [".km", ".gov.km"],
        "DJ": [".dj", ".gouv.dj"],
        "ER": [".gov.er", ".er"],
        "ET": [".gov.et", ".et"],
        "KE": [".go.ke", ".ke"],
        "MG": [".mg", ".gov.mg"],
        "MW": [".gov.mw", ".mw"],
        "MU": [".gov.mu", ".mu"],
        "MZ": [".gov.mz", ".mz"],
        "RW": [".gov.rw", ".rw"],
        "SC": [".gov.sc", ".sc"],
        "SO": [".gov.so", ".so"],
        "SS": [".gov.ss", ".ss"],
        "TZ": [".go.tz", ".tz"],
        "UG": [".go.ug", ".ug"],
        # Africa — Southern
        "AO": [".gov.ao", ".ao"],
        "BW": [".gov.bw", ".bw"],
        "SZ": [".gov.sz", ".sz"],
        "LS": [".gov.ls", ".ls"],
        "NA": [".gov.na", ".na"],
        "ZA": [".gov.za", ".za"],
        "ZM": [".gov.zm", ".zm"],
        "ZW": [".gov.zw", ".zw"],
        # Caribbean
        "CU": [".cu", ".gob.cu"],
        "HT": [".ht", ".gouv.ht"],
        "DO": [".gob.do", ".do"],
        "JM": [".gov.jm", ".jm"],
        "TT": [".gov.tt", ".tt"],
        "BS": [".gov.bs", ".bs"],
        "BB": [".gov.bb", ".bb"],
        "AG": [".gov.ag", ".ag"],
        "DM": [".gov.dm", ".dm"],
        "GD": [".gov.gd", ".gd"],
        "KN": [".gov.kn", ".kn"],
        "LC": [".gov.lc", ".lc"],
        "VC": [".gov.vc", ".vc"],
        # Asia (additional)
        "AF": [".gov.af", ".af"],
        "SG": [".gov.sg", ".sg"],
        "YE": [".gov.ye", ".ye"],
        "SY": [".gov.sy", ".sy"],
        "PS": [".gov.ps", ".ps"],
        "TJ": [".gov.tj", ".tj"],
        "TM": [".gov.tm", ".tm"],
        "MV": [".gov.mv", ".mv"],
        "BT": [".gov.bt", ".bt"],
        # Oceania (additional)
        "SB": [".gov.sb", ".sb"],
        "MH": [".gov.mh", ".mh"],
        "FM": [".gov.fm", ".fm"],
        "KI": [".gov.ki", ".ki"],
        "TV": [".gov.tv", ".tv"],
    }
    tlds = tld_map.get(
        country, [".ee", ".lv", ".lt", ".fi", ".no", ".se", ".de", ".dk"]
    )

    candidates = set()
    for slug in slugs:
        for tld in tlds:
            candidates.add(f"{slug}{tld}")
        # Portuguese municipalities commonly use cm-name.pt
        if country == "PT" or not country:
            candidates.add(f"cm-{slug}.pt")
        # Romanian municipalities commonly use primaria-name.ro
        if country == "RO" or not country:
            candidates.add(f"primaria-{slug}.ro")
        # Croatian municipalities use opcina-name.hr or grad-name.hr
        if country == "HR" or not country:
            candidates.add(f"opcina-{slug}.hr")
            candidates.add(f"grad-{slug}.hr")
    return sorted(candidates)


def load_seed_data() -> dict[str, dict[str, str]]:
    """Load municipalities from curated seed JSON files."""
    print("Loading municipalities from seed data...")
    municipalities = {}

    for country_code, filename in SEED_FILES.items():
        path = DATA_DIR / filename
        if not path.exists():
            print(f"  WARNING: {path} not found, skipping {country_code}")
            continue
        with open(path, encoding="utf-8") as f:
            entries = json.load(f)

        for entry in entries:
            muni_id = entry["id"]
            muni = {
                "bfs": muni_id,  # reuse "bfs" field as generic municipality ID
                "name": entry["name"],
                "canton": entry.get("region", ""),  # reuse "canton" field for region
                "district": entry.get("district", ""),
                "country": entry.get("country", country_code),
                "website": entry.get("domain", ""),
                "osm_relation_id": entry.get("osm_relation_id"),
            }
            if entry.get("population"):
                muni["population"] = entry["population"]
            municipalities[muni_id] = muni
        print(f"  {country_code}: {len(entries)} municipalities")

    # Apply overrides
    overrides_path = DATA_DIR / "overrides.json"
    if overrides_path.exists():
        with open(overrides_path, encoding="utf-8") as f:
            overrides = json.load(f)
        for muni_id, override in overrides.items():
            if muni_id in municipalities:
                municipalities[muni_id].update(override)

    print(
        f"  Total: {len(municipalities)} municipalities, "
        f"{sum(1 for m in municipalities.values() if m['website'])} with domains"
    )
    return municipalities


async def scan_municipality(
    m: dict[str, str],
    semaphore: asyncio.Semaphore,
    dns_cache=None,
) -> dict[str, Any]:
    """Scan a single municipality for email provider info."""
    async with semaphore:
        domain = url_to_domain(m.get("website", ""))
        mx, spf = [], ""
        txt_verifications: dict[str, str] = {}

        # Check DNS cache first
        cached = dns_cache.get_domain(domain) if dns_cache and domain else None
        if cached:
            mx = cached.get("mx", [])
            spf = cached.get("spf", "")
            txt_verifications = cached.get("txt_verifications", {})
            if not mx:
                # Cache says no MX for this domain — still try guessing
                cached = None

        if not cached:
            if domain:
                mx = await lookup_mx(domain)
                if mx:
                    spf, txt_verifications = await lookup_txt(domain)

            if not mx:
                country = m.get("country", "")
                for guess in guess_domains(m["name"], country):
                    if guess == domain:
                        continue
                    # Check cache for guessed domain too
                    gcached = (
                        dns_cache.get_domain(guess) if dns_cache else None
                    )
                    if gcached and gcached.get("mx"):
                        mx = gcached["mx"]
                        spf = gcached.get("spf", "")
                        txt_verifications = gcached.get("txt_verifications", {})
                        domain = guess
                        cached = gcached
                        break
                    mx = await lookup_mx(guess)
                    if mx:
                        domain = guess
                        spf, txt_verifications = await lookup_txt(guess)
                        break

        tenant: str | None = None
        if cached and mx:
            # Use cached derived data
            spf_resolved = cached.get("spf_resolved", "")
            mx_cnames = cached.get("mx_cnames", {})
            mx_asns = set(cached.get("mx_asns", []))
            mx_countries = set(cached.get("mx_countries", []))
            autodiscover = cached.get("autodiscover", {})
            dkim = cached.get("dkim", {})
            txt_verifications = cached.get("txt_verifications", txt_verifications)
            tenant = cached.get("tenant")

            # Backfill txt_verifications if missing from old cache
            if not txt_verifications and domain:
                _, txt_verifications = await lookup_txt(domain)
                if txt_verifications:
                    cached["txt_verifications"] = txt_verifications

            # Backfill tenant if missing from old cache (only for gateway scenarios)
            if tenant is None and domain and mx and detect_gateway(mx):
                tenant = await lookup_tenant(domain)
                if tenant:
                    cached["tenant"] = tenant
        else:
            # Fresh DNS lookups
            spf_resolved = await resolve_spf_includes(spf) if spf else ""
            mx_cnames = await resolve_mx_cnames(mx) if mx else {}
            mx_asns = await resolve_mx_asns(mx) if mx else set()
            mx_countries = await resolve_mx_countries(mx) if mx else set()
            autodiscover = await lookup_autodiscover(domain) if domain else {}
            dkim = await lookup_dkim(domain) if domain else {}
            # Only lookup tenant for gateway scenarios (avoids HTTP call for ~80% of domains)
            tenant = await lookup_tenant(domain) if domain and mx and detect_gateway(mx) else None

            # Store in cache
            if dns_cache and domain:
                cache_data = {
                    "mx": mx, "spf": spf,
                    "spf_resolved": spf_resolved,
                    "mx_cnames": mx_cnames,
                    "mx_asns": sorted(mx_asns) if mx_asns else [],
                    "mx_countries": sorted(mx_countries) if mx_countries else [],
                    "autodiscover": autodiscover,
                    "dkim": dkim,
                    "txt_verifications": txt_verifications,
                }
                if tenant:
                    cache_data["tenant"] = tenant
                dns_cache.set_domain(domain, cache_data)
        provider, reason = classify(
            mx,
            spf,
            mx_cnames=mx_cnames,
            mx_asns=mx_asns or None,
            resolved_spf=spf_resolved or None,
            autodiscover=autodiscover or None,
            dkim=dkim or None,
            txt_verifications=txt_verifications or None,
            tenant=tenant,
        )
        gateway = detect_gateway(mx) if mx else None

        entry: dict[str, Any] = {
            "bfs": m["bfs"],
            "name": m["name"],
            "canton": m.get("canton", ""),
            "district": m.get("district", ""),
            "country": m.get("country", ""),
            "domain": domain or "",
            "mx": mx,
            "spf": spf,
            "provider": provider,
            "reason": reason,
        }
        if m.get("osm_relation_id"):
            entry["osm_relation_id"] = m["osm_relation_id"]
        if m.get("population"):
            entry["population"] = m["population"]
        if spf_resolved and spf_resolved != spf:
            entry["spf_resolved"] = spf_resolved
        if gateway:
            entry["gateway"] = gateway
        if mx_cnames:
            entry["mx_cnames"] = mx_cnames
        if mx_asns:
            entry["mx_asns"] = sorted(mx_asns)
            # Resolve ISP name for local-isp entries
            if provider == "local-isp":
                for asn in mx_asns:
                    if asn in LOCAL_ISP_ASNS:
                        entry["isp_name"] = LOCAL_ISP_ASNS[asn]
                        break
        # Named local providers also get isp_name for frontend grouping
        isp_display = {
            "zone": "Zone.eu",
            "telia": "Telia",
            "elkdata": "Elkdata",
            "tet": "TET",
        }
        if provider in isp_display:
            entry["isp_name"] = isp_display[provider]
        if mx_countries:
            entry["mx_countries"] = sorted(mx_countries)
        if autodiscover:
            entry["autodiscover"] = autodiscover
        if dkim:
            entry["dkim"] = dkim
        if txt_verifications:
            entry["txt_verifications"] = txt_verifications
        if tenant:
            entry["tenant"] = tenant

        # MX discovery provenance — see src/mail_sovereignty/mx_discovery.py.
        # Map the seed's domain_source (set by fetch_indicepa per ente) to
        # the canonical taxonomy tag. If MX wasn't found here, the entry
        # may be promoted later by recover/finalize/postprocess, which
        # will overwrite these two fields with their own method tag.
        seed_source = m.get("domain_source") or ""
        if mx:
            # Map fetch_indicepa.py seed.domain_source values to the canonical
            # mx_discovery_method taxonomy (see src/mail_sovereignty/mx_discovery.py).
            seed_to_method = {
                "sito_istituzionale":       "seed_primary_mx",
                "manual_override":          "manual_override",
                "manual_llm_enrichment":    "manual_llm_enrichment",
                "pec_enrichment":           "pec_only_enrichment",
                "email_non_pec_fallback":   "domain_fallback",
                "aoo_uo_email_fallback":    "aoo_uo_tier6",
                "name_guess":               "domain_guess",
            }
            method = seed_to_method.get(seed_source, "seed_primary_mx" if domain else "unknown")
            entry["mx_discovery_method"] = method
            entry["mx_discovery_evidence"] = domain
        else:
            entry["mx_discovery_method"] = "unknown"
        return entry


async def run(
    output_path: Path,
    countries: list[str] | None = None,
    state_filters: dict[str, list[str]] | None = None,
) -> None:
    state_filters = state_filters or {}
    all_municipalities = load_seed_data()

    # Filter by country if specified
    if countries:
        municipalities = {
            k: v
            for k, v in all_municipalities.items()
            if v.get("country", "") in countries
        }
        print(f"\nFiltering to countries: {', '.join(countries)}")
    else:
        municipalities = all_municipalities

    # Apply sub-country state filters
    if state_filters:
        filtered = {}
        for k, v in municipalities.items():
            cc = v.get("country", "")
            if cc in state_filters:
                extract = PARTITIONED_COUNTRIES.get(cc)
                if extract:
                    partition = extract(k)
                    if partition in state_filters[cc]:
                        filtered[k] = v
            else:
                filtered[k] = v
        from mail_sovereignty.constants import DE_STATE_CODES
        filter_labels = []
        for cc, codes in state_filters.items():
            abbrevs = [DE_STATE_CODES.get(c, c) for c in codes] if cc == "DE" else codes
            filter_labels.append(f"{cc}:{','.join(abbrevs)}")
        print(f"  State filter: {', '.join(filter_labels)} "
              f"({len(filtered)}/{len(municipalities)} municipalities)")
        municipalities = filtered

    total = len(municipalities)
    print(f"\nScanning {total} municipalities for MX/SPF records...")
    print("(This takes a few minutes with async lookups)\n")

    # Initialize per-country DNS caches (partitioned for large countries)
    from mail_sovereignty.dns_cache import DnsCache

    active_countries = countries or sorted(
        {m.get("country", "") for m in municipalities.values()}
    )
    caches: dict[str, DnsCache] = {}
    for cc in active_countries:
        if cc in PARTITIONED_COUNTRIES:
            # Create one cache per partition (state)
            extract = PARTITIONED_COUNTRIES[cc]
            partitions = sorted({
                extract(k) for k, v in municipalities.items()
                if v.get("country", "") == cc
            })
            for part in partitions:
                caches[f"{cc}:{part}"] = DnsCache(cc, partition=part)
        else:
            caches[cc] = DnsCache(cc)

    def get_cache(m):
        cc = m.get("country", "")
        if cc in PARTITIONED_COUNTRIES:
            extract = PARTITIONED_COUNTRIES[cc]
            partition = extract(m["bfs"])
            return caches.get(f"{cc}:{partition}")
        return caches.get(cc)

    semaphore = asyncio.Semaphore(CONCURRENCY)
    tasks = [
        scan_municipality(m, semaphore, dns_cache=get_cache(m))
        for m in municipalities.values()
    ]

    results = {}
    done = 0
    for coro in asyncio.as_completed(tasks):
        result = await coro
        results[result["bfs"]] = result
        done += 1
        if done % 50 == 0 or done == total:
            counts = {}
            for r in results.values():
                counts[r["provider"]] = counts.get(r["provider"], 0) + 1
            print(
                f"  [{done:4d}/{total}]  "
                f"MS={counts.get('microsoft', 0)}  "
                f"Google={counts.get('google', 0)}  "
                f"Zone={counts.get('zone', 0)}  "
                f"Telia={counts.get('telia', 0)}  "
                f"TET={counts.get('tet', 0)}  "
                f"AWS={counts.get('aws', 0)}  "
                f"ISP={counts.get('local-isp', 0)}  "
                f"Indep={counts.get('independent', 0)}  "
                f"?={counts.get('unknown', 0)}"
            )

    # Save DNS caches
    for cache in caches.values():
        cache.save()

    counts = {}
    for r in results.values():
        counts[r["provider"]] = counts.get(r["provider"], 0) + 1

    print(f"\n{'=' * 50}")
    print(f"RESULTS: {len(results)} municipalities scanned")
    print(f"  Microsoft/Azure        : {counts.get('microsoft', 0):>5}")
    print(f"  Google/GCP             : {counts.get('google', 0):>5}")
    print(f"  Zone.eu                : {counts.get('zone', 0):>5}")
    print(f"  Telia                  : {counts.get('telia', 0):>5}")
    print(f"  TET                    : {counts.get('tet', 0):>5}")
    print(f"  AWS                    : {counts.get('aws', 0):>5}")
    # Italian commercial providers (mxmap.it Phase 3)
    print(f"  Aruba                  : {counts.get('aruba', 0):>5}")
    print(f"  Register.it            : {counts.get('register-it', 0):>5}")
    print(f"  Seeweb                 : {counts.get('seeweb', 0):>5}")
    print(f"  InfoCert               : {counts.get('infocert', 0):>5}")
    print(f"  Namirial               : {counts.get('namirial', 0):>5}")
    print(f"  Italian Regional Public: {counts.get('regional-public', 0):>5}")
    print(f"  Italian PA Contractor  : {counts.get('pa-contractor-private', 0):>5}")
    print(f"  Local ISP              : {counts.get('local-isp', 0):>5}")
    print(f"  Independent            : {counts.get('independent', 0):>5}")
    print(f"  Unknown/No MX          : {counts.get('unknown', 0):>5}")
    print(f"{'=' * 50}")

    # Merge with existing data.json when filtering by country or state
    if countries and output_path.exists():
        with open(output_path, encoding="utf-8") as f:
            existing = json.load(f)
        existing_munis = existing.get("municipalities", {})

        if state_filters:
            # Sub-country merge: only replace entries matching filtered partitions
            def should_replace(k, v):
                cc = v.get("country", "")
                if cc not in state_filters:
                    return cc in countries  # full-country replacement
                extract = PARTITIONED_COUNTRIES.get(cc)
                if extract:
                    return extract(k) in state_filters[cc]
                return True

            merged = {
                k: v for k, v in existing_munis.items()
                if not should_replace(k, v)
            }
        else:
            # Remove old entries for the filtered countries, keep the rest
            merged = {
                k: v
                for k, v in existing_munis.items()
                if v.get("country", "") not in countries
            }
        merged.update(results)
        results = merged
        print(f"  Merged with existing data: {len(results)} total")

    sorted_counts = {}
    for r in results.values():
        p = r.get("provider", "unknown")
        sorted_counts[p] = sorted_counts.get(p, 0) + 1
    sorted_counts = dict(sorted(sorted_counts.items()))
    sorted_munis = dict(sorted(results.items()))

    output = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total": len(results),
        "counts": sorted_counts,
        "municipalities": sorted_munis,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=None, separators=(",", ":"))

    size_kb = len(json.dumps(output)) / 1024
    print(f"\nWritten {output_path} ({size_kb:.0f} KB)")

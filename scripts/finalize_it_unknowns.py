#!/usr/bin/env python3
"""Final pass for IT entries still classified as `unknown` after preprocess
+ recover_it_unknowns + reclassify_it_provincial.

Four strategies, applied in order per remaining unknown. The first to yield
a working domain (with MX) wins. The original `domain` field is preserved
(audit trail of the IndicePA value); `domain_used` records the recovery
domain that actually worked, and full mxmap classify() runs against it —
so the typo / migration / wrong-domain fix flows through the standard MX
pipeline rather than a hardcoded override.

  S1. ASMEL → ASMENET (override su conoscenza nota). I comuni ASMEL con sola PEC
      su asmepec.it usano la piattaforma ASMENET (asmenet.it → MX mail.asmenet.it,
      ICT consortile pubblico = regional-public): override esplicito, risolto via
      asmenet.it. RUPAR Piemonte (cert.ruparpiemonte.it) NON gode di questa
      certezza → senza MX ordinario resta `unknown` + anomalia `no_mx`. mxmap.it#18.

  S2. Wikidata P856 correction:
      Query Wikidata for the comune's official website by ISTAT 6-digit
      code. If it differs from IndicePA's domain AND has MX, use it.
      Catches typos (castefranco -> castelfranco, ww. -> www.) and
      defunct *.gov.it migrations to comune.{name}.{prov}.it.

  S3. Homepage scrape on the IndicePA primary domain:
      If the primary domain resolves, fetch https://{domain}/, extract
      emails, try each email's domain via MX. First with MX wins.

  S4. Search-engine + scrape fallback:
      If S1-S3 all fail, query DuckDuckGo for "comune di {name} sito
      ufficiale", fetch the top candidate URLs whose hostname looks
      like a comune site, scrape for emails, MX-test, classify.

Idempotent via the existing `domain_used` field. Re-runs skip already-
recovered entries.

Usage: uv run python3 scripts/finalize_it_unknowns.py
"""

from __future__ import annotations

import asyncio
import json
import re
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import httpx

from mail_sovereignty.classify import classify
from mail_sovereignty.constants import EMAIL_RE
from mail_sovereignty.scrape_validator import is_legit_email_domain
from mail_sovereignty.dns import (
    lookup_autodiscover,
    lookup_dkim,
    lookup_mx,
    lookup_spf,
    lookup_tenant,
    lookup_txt,
    resolve_mx_asns,
    resolve_mx_cnames,
    resolve_mx_countries,
    resolve_spf_includes,
)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

CKAN_BASE = "https://indicepa.gov.it/ipa-dati/api/3/action"
RESOURCE_ID = "d09adf99-dc10-4349-8c53-27b1e5aa97b6"

SPARQL_URL = "https://query.wikidata.org/sparql"

DDG_HTML_URL = "https://html.duckduckgo.com/html/"

USER_AGENT = "mxmap.it/0.2 (+https://github.com/mxmap-it/mxmap.it)"

CONCURRENCY_DNS = 10
CONCURRENCY_HTTP = 8

# Third-party email vendors to ignore when scraping comune homepages.
EMAIL_BLOCKLIST = frozenset(
    {
        "iubenda.com",
        "cookiebot.com",
        "cookieyes.com",
        "onetrust.com",
        "sentry.io",
        "google-analytics.com",
        "googletagmanager.com",
        "wpbeginner.com",
        "wordpress.com",
        "automattic.com",
        "example.com",
        "example.it",
        "test.it",
        "domain.com",
        "localhost",
        "yourcompany.com",
        "sitiwp.com",
        "designerthemes.com",
        "templatemonster.com",
        "elegantthemes.com",
        "linkedin.com",
        "facebook.com",
        "twitter.com",
        "instagram.com",
        "youtube.com",
        "tiktok.com",
    }
)

# When DDG returns multiple URLs, we discard hosts on these properties.
SEARCH_RESULT_HOST_BLOCKLIST = frozenset(
    {
        "wikipedia.org",
        "it.wikipedia.org",
        "en.wikipedia.org",
        "wikidata.org",
        "facebook.com",
        "instagram.com",
        "twitter.com",
        "youtube.com",
        "linkedin.com",
        "tripadvisor.it",
        "tripadvisor.com",
        "tuttitalia.it",
        "comuni-italiani.it",
        "italia.indettaglio.it",
        "italymap.com",
    }
)

# Italian regional/consortium PEC domains owned by comuni or sovereign
# regional ICT — when an entry has only PEC mail and one of these is the
# host, we classify the entry as `regional-public` with reason crediting
# the consortium. ANY pure-PEC entry on these domains qualifies.
PUBLIC_PEC_DOMAINS = {
    "cert.ruparpiemonte.it": "RUPAR Piemonte / CSI Piemonte (publicly-owned regional ICT)",
    "asmepec.it": "ASMEPEC (ASMEL — consortium owned by Italian comuni)",
}


def fetch_ipa_record(codice_ipa: str) -> dict | None:
    params = {
        "resource_id": RESOURCE_ID,
        "filters": json.dumps({"Codice_IPA": codice_ipa}),
        "limit": 1,
    }
    url = f"{CKAN_BASE}/datastore_search?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None
    records = data.get("result", {}).get("records", [])
    return records[0] if records else None


def detect_public_pec(raw: dict) -> tuple[str | None, str | None]:
    """If any Mail{n} is on a public PEC infrastructure domain, return
    (matched_domain, evidence_string). Otherwise (None, None)."""
    for n in range(1, 6):
        addr = (raw.get(f"Mail{n}") or "").strip().lower()
        if not addr or "@" not in addr:
            continue
        host = addr.rsplit("@", 1)[1].rstrip(".")
        for pec_domain, evidence in PUBLIC_PEC_DOMAINS.items():
            if host == pec_domain or host.endswith(f".{pec_domain}"):
                return pec_domain, evidence
    return None, None


def fetch_wikidata_websites(istat_codes: list[str]) -> dict[str, str]:
    """Batch-query Wikidata for ISTAT-keyed comune websites (P856).

    Returns {istat_code: hostname}. Comuni with no P856 are absent.
    """
    if not istat_codes:
        return {}
    values_block = " ".join(f'"{c}"' for c in istat_codes)
    query = f"""
SELECT ?istat ?website WHERE {{
  VALUES ?istat {{ {values_block} }}
  ?item wdt:P635 ?istat ;
        wdt:P17 wd:Q38 ;
        wdt:P856 ?website .
}}
"""
    url = f"{SPARQL_URL}?{urllib.parse.urlencode({'query': query, 'format': 'json'})}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"},
    )
    out: dict[str, str] = {}
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for r in data.get("results", {}).get("bindings", []):
            istat = r["istat"]["value"]
            website = r.get("website", {}).get("value", "")
            if not website:
                continue
            host = hostname_of(website)
            if host and istat not in out:
                out[istat] = host
    except Exception as e:
        print(f"  Wikidata batch query error: {e!r}")
    return out


def hostname_of(url: str) -> str:
    if not url:
        return ""
    try:
        h = urlparse(url if "://" in url else f"https://{url}").hostname or ""
    except Exception:
        return ""
    h = h.lower().rstrip(".")
    if h.startswith("www."):
        h = h[4:]
    return h


HOSTNAME_RE = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$"
)


def looks_like_valid_host(h: str) -> bool:
    return bool(h) and bool(HOSTNAME_RE.match(h))


async def classify_domain(domain: str) -> dict | None:
    """Run the full mxmap classification pipeline against `domain`."""
    mx_records = await lookup_mx(domain)
    if not mx_records:
        return None
    spf_task = asyncio.create_task(lookup_spf(domain))
    txt_task = asyncio.create_task(lookup_txt(domain))
    cname_task = asyncio.create_task(resolve_mx_cnames(mx_records))
    asn_task = asyncio.create_task(resolve_mx_asns(mx_records))
    country_task = asyncio.create_task(resolve_mx_countries(mx_records))
    autodiscover_task = asyncio.create_task(lookup_autodiscover(domain))
    dkim_task = asyncio.create_task(lookup_dkim(domain))
    tenant_task = asyncio.create_task(lookup_tenant(domain))

    spf_record = await spf_task
    _spf_raw, txt_verifications = await txt_task
    mx_cnames = await cname_task
    mx_asns = await asn_task
    mx_countries = await country_task
    autodiscover = await autodiscover_task
    dkim = await dkim_task
    tenant = await tenant_task
    resolved_spf = await resolve_spf_includes(spf_record) if spf_record else None

    provider, reason = classify(
        mx_records=mx_records,
        spf_record=spf_record,
        mx_cnames=mx_cnames,
        mx_asns=mx_asns,
        resolved_spf=resolved_spf,
        autodiscover=autodiscover,
        dkim=dkim,
        txt_verifications=txt_verifications,
        tenant=tenant,
    )
    return {
        "mx": mx_records,
        "spf": spf_record,
        "spf_resolved": resolved_spf,
        "provider": provider,
        "reason": reason,
        "mx_cnames": mx_cnames,
        "mx_asns": sorted(mx_asns) if isinstance(mx_asns, set) else list(mx_asns or []),
        "mx_countries": sorted(mx_countries)
        if isinstance(mx_countries, set)
        else list(mx_countries or []),
        "autodiscover": autodiscover,
        "dkim": dkim,
        "txt_verifications": txt_verifications,
        "tenant": tenant,
    }


async def fetch_homepage(
    client: httpx.AsyncClient, domain: str
) -> tuple[str | None, str]:
    """Try https://domain/, fall back to http://. Return (text, status)
    where status is 'ok' / 'dns_fail' / 'http_fail' / 'empty'."""
    for scheme in ("https", "http"):
        url = f"{scheme}://{domain}/"
        try:
            r = await client.get(url, follow_redirects=True, timeout=10.0)
        except httpx.ConnectError as e:
            msg = str(e).lower()
            if (
                "name" in msg
                or "resolve" in msg
                or "dns" in msg
                or "nodename" in msg
                or "getaddrinfo" in msg
            ):
                return None, "dns_fail"
            continue
        except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.RemoteProtocolError):
            continue
        except Exception:
            continue
        if r.status_code >= 400:
            continue
        if not r.text:
            return None, "empty"
        return r.text, "ok"
    return None, "http_fail"


def extract_emails(html: str, primary_domain: str) -> list[str]:
    """Pull email addresses from HTML, filter junk, prefer same-registrable
    domain as primary_domain."""
    primary_reg = ".".join((primary_domain or "").lower().split(".")[-2:])
    candidates = set(EMAIL_RE.findall(html or ""))
    same_dom: list[str] = []
    other: list[str] = []
    for raw in candidates:
        addr = raw.strip().lower()
        if "@" not in addr:
            continue
        host = addr.rsplit("@", 1)[1]
        host_reg = ".".join(host.split(".")[-2:])
        if host_reg in EMAIL_BLOCKLIST:
            continue
        if (
            host == primary_domain
            or host.endswith(f".{primary_domain}")
            or host_reg == primary_reg
        ):
            same_dom.append(addr)
        else:
            other.append(addr)
    return same_dom + other


def parse_ddg_html(html: str) -> list[str]:
    """Extract result hostnames from a DuckDuckGo HTML page."""
    if not html:
        return []
    # DDG wraps URLs as href="/l/?uddg=ENCODED&..." — extract the uddg=
    # parameter and decode, OR direct hrefs starting with http(s)://.
    urls: list[str] = []
    seen: set[str] = set()
    # Direct hrefs
    for m in re.finditer(r'href="(https?://[^"]+)"', html):
        url = m.group(1)
        if url in seen:
            continue
        seen.add(url)
        urls.append(url)
    # DDG redirect format
    for m in re.finditer(r'href="//duckduckgo\.com/l/\?uddg=([^&"]+)', html):
        try:
            url = urllib.parse.unquote(m.group(1))
        except Exception:
            continue
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


async def search_for_comune_website(
    client: httpx.AsyncClient,
    name: str,
    primary_domain: str,
) -> list[str]:
    """Query DuckDuckGo for "{name} sito ufficiale" and return candidate
    hostnames (filtered)."""
    query = f"{name} sito ufficiale"
    try:
        r = await client.post(
            DDG_HTML_URL, data={"q": query}, timeout=15.0, follow_redirects=True
        )
    except Exception as e:
        print(f"    DDG error for {name!r}: {e!r}")
        return []
    if r.status_code >= 400 or not r.text:
        return []
    urls = parse_ddg_html(r.text)
    primary_reg = ".".join((primary_domain or "").lower().split(".")[-2:])
    hosts: list[str] = []
    seen: set[str] = set()
    for url in urls[:30]:
        h = hostname_of(url)
        if not h or not looks_like_valid_host(h):
            continue
        if h in seen:
            continue
        h_reg = ".".join(h.split(".")[-2:])
        if h_reg in SEARCH_RESULT_HOST_BLOCKLIST or h in SEARCH_RESULT_HOST_BLOCKLIST:
            continue
        # Prefer hostnames containing "comune" OR matching the primary's
        # registrable suffix (e.g. *.<prov>.it for the comune's province).
        seen.add(h)
        hosts.append(h)

    # Re-rank: comune-named first, then same-registrable, then rest.
    def score(h: str) -> int:
        s = 0
        if "comune" in h or "municipio" in h or "citta" in h:
            s += 10
        h_reg = ".".join(h.split(".")[-2:])
        if h_reg == primary_reg:
            s += 5
        if h.endswith(".it"):
            s += 1
        return -s

    hosts.sort(key=score)
    return hosts[:6]


async def try_domain_for_classify(
    domain: str, dns_sem: asyncio.Semaphore
) -> dict | None:
    async with dns_sem:
        try:
            return await classify_domain(domain)
        except Exception:
            return None


async def try_scrape_for_email_mx(
    client: httpx.AsyncClient,
    target_host: str,
    primary_domain: str,
    http_sem: asyncio.Semaphore,
    dns_sem: asyncio.Semaphore,
) -> tuple[dict | None, str | None, str | None, list[str]]:
    """Fetch homepage of target_host; extract emails; MX-test each. Return
    (classification, email_used, host_used, tried_hosts)."""
    async with http_sem:
        text, status = await fetch_homepage(client, target_host)
    if not text:
        return None, None, None, []
    emails = extract_emails(text, primary_domain)
    if not emails:
        return None, None, None, []
    tried: list[str] = []
    rejected: list[tuple[str, str]] = []
    for addr in emails[:6]:
        host = addr.rsplit("@", 1)[1]
        tried.append(host)
        # Strict gate: only accept emails whose domain is provably tied
        # to the parent ente (primary_domain). Prevents the cross-tenant
        # bug where scraping comune A's homepage finds an email of
        # comune B in a footer/news/partner block.
        ok, reason = is_legit_email_domain(host, primary_domain)
        if not ok:
            rejected.append((host, reason))
            continue
        result = await try_domain_for_classify(host, dns_sem)
        if result:
            return result, addr, host, tried
    # Surface rejects in the tried list as audit so they show up in reports.
    if rejected:
        tried.extend([f"{h}!REJECT[{r}]" for h, r in rejected])
    return None, None, None, tried


async def finalize_one(
    key: str,
    entry: dict,
    seed_entry: dict,
    raw: dict | None,
    wd_corrections: dict[str, str],
    aoo_uo_ext: dict[str, list[str]],
    client: httpx.AsyncClient,
    dns_sem: asyncio.Semaphore,
    http_sem: asyncio.Semaphore,
) -> tuple[str, dict, str]:
    """Try the strategies in order; return (key, mutation_dict, status)."""
    primary = (entry.get("domain") or "").strip().lower()
    name = seed_entry.get("name") or entry.get("name") or ""
    istat = (seed_entry.get("ipa_codice_comune_istat") or "").zfill(6)
    codice_ipa = (seed_entry.get("ipa_codice_ipa") or "").strip().lower()

    # S0 — IndicePA AOO/UO non-PEC enrichment (Tier-6, is_legit-validated
    # at harvest time). Highest-confidence signal; no scraping involved.
    if codice_ipa and codice_ipa in aoo_uo_ext:
        for cand in aoo_uo_ext[codice_ipa]:
            if cand == primary:
                continue
            result = await try_domain_for_classify(cand, dns_sem)
            if result:
                mutation = {
                    "domain_used": cand,
                    "domain_correction_source": "indicepa_aoo_uo_tier6",
                    "mx_discovery_method": "aoo_uo_tier6",
                    "mx_discovery_evidence": cand,
                }
                mutation.update(result)
                return key, mutation, "aoo_uo_tier6"

    # S1 — ASMEL → ASMENET (override su conoscenza nota). I comuni ASMEL con SOLA
    # PEC su asmepec.it usano la piattaforma ASMENET per la posta ordinaria
    # (asmenet.it → MX mail.asmenet.it, ICT consortile pubblico = regional-public):
    # non è "nessun dato", sappiamo dov'è la posta → risolviamo via asmenet.it.
    # NB: RUPAR Piemonte (cert.ruparpiemonte.it) NON gode di questa certezza →
    # senza MX ordinario resta unknown + anomalia no_mx. mxmap.it#18.
    if raw:
        matched, _ = detect_public_pec(raw)
        if matched == "asmepec.it":
            result = await try_domain_for_classify("asmenet.it", dns_sem)
            if result:
                mutation = {
                    "domain_used": "asmenet.it",
                    "public_pec_match": matched,
                    "mx_discovery_method": "asmel_asmenet_override",
                    "mx_discovery_evidence": "asmenet.it",
                }
                mutation.update(result)
                mutation["reason"] = (
                    "ASMEL member (solo-PEC asmepec.it) → posta su ASMENET "
                    "(mail.asmenet.it)"
                )
                return key, mutation, "asmel_asmenet"

    # S2 — Wikidata P856 correction
    wd_host = wd_corrections.get(istat)
    if wd_host and wd_host != primary:
        result = await try_domain_for_classify(wd_host, dns_sem)
        if result:
            mutation = {
                "domain_used": wd_host,
                "domain_correction_source": "wikidata_p856",
                "mx_discovery_method": "wikidata_p856",
                "mx_discovery_evidence": wd_host,
            }
            mutation.update(result)
            return key, mutation, "wikidata"

    # S3 — Homepage scrape on primary domain
    if primary:
        result, addr, host, tried = await try_scrape_for_email_mx(
            client,
            primary,
            primary,
            http_sem,
            dns_sem,
        )
        if result:
            mutation = {
                "domain_used": host,
                "scraped_email": addr,
                "scrape_tried_hosts": tried,
                "domain_correction_source": "homepage_scrape_primary",
                "mx_discovery_method": "homepage_scrape",
                "mx_discovery_evidence": addr,
            }
            mutation.update(result)
            return key, mutation, "scrape_primary"

    # S4 — Search-engine fallback
    candidates = await search_for_comune_website(client, name, primary)
    if candidates:
        for cand in candidates:
            if cand == primary:
                continue
            result, addr, host, tried = await try_scrape_for_email_mx(
                client,
                cand,
                primary,
                http_sem,
                dns_sem,
            )
            if result:
                mutation = {
                    "domain_used": host,
                    "scraped_email": addr,
                    "scrape_tried_hosts": tried,
                    "search_engine_winner": cand,
                    "search_engine_candidates": candidates,
                    "domain_correction_source": "search_engine",
                    "mx_discovery_method": "search_engine_scrape",
                    "mx_discovery_evidence": addr,
                }
                mutation.update(result)
                return key, mutation, "search_engine"
        # S4 ran but found no working candidate
        return (
            key,
            {
                "reason": f"search engine returned {len(candidates)} candidates; none yielded MX",
                "search_engine_candidates": candidates,
            },
            "search_no_mx",
        )

    # All strategies failed
    return (
        key,
        {
            "reason": "all strategies exhausted (S0 AOO/UO Tier-6, S1 PEC, S2 Wikidata, S3 scrape primary, S4 search engine)"
        },
        "all_failed",
    )


def load_aoo_uo_extension() -> dict[str, list[str]]:
    """Load AOO/UO Tier-6 enrichment (codice_ipa_lower -> [non-PEC domains]).
    Each domain has been is_legit-validated at harvest time."""
    p = DATA / "indicepa_extended_emails.json"
    if not p.exists():
        print(
            f"  WARN: {p} missing — Tier-6 (S0) skipped. "
            f"Run scripts/enrich_from_aoo_uo.py first."
        )
        return {}
    d = json.loads(p.read_text(encoding="utf-8"))
    return {
        k.lower(): (v.get("non_pec_domains") or [])
        for k, v in d.get("by_ipa", {}).items()
        if v.get("non_pec_domains")
    }


async def main_async() -> int:
    seed = json.loads((DATA / "municipalities_it.json").read_text(encoding="utf-8"))
    seed_by_id = {e["id"]: e for e in seed}
    aoo_uo_ext = load_aoo_uo_extension()
    print(f"Loaded {len(aoo_uo_ext)} enti with Tier-6 AOO/UO domains")
    data_path = ROOT / "data.json"
    data = json.loads(data_path.read_text(encoding="utf-8"))
    muns = data["municipalities"]

    # Identify candidates
    candidates: list[tuple[str, dict, dict]] = []
    for key, entry in muns.items():
        if entry.get("country") != "IT":
            continue
        if entry.get("provider") != "unknown":
            continue
        if entry.get("domain_used"):
            continue
        eid = entry.get("id") or key
        seed_entry = seed_by_id.get(eid)
        if not seed_entry:
            continue
        candidates.append((key, entry, seed_entry))

    print(f"Found {len(candidates)} IT entries still unknown")
    if not candidates:
        return 0

    # Pre-fetch IndicePA records (for S1 PEC detection)
    print(f"Pre-fetching IndicePA records for {len(candidates)} candidates...")
    raw_by_key: dict[str, dict | None] = {}
    for k, e, s in candidates:
        codice_ipa = s.get("ipa_codice_ipa")
        raw_by_key[k] = fetch_ipa_record(codice_ipa) if codice_ipa else None
        time.sleep(0.05)

    # Pre-fetch Wikidata corrections (single batched SPARQL query)
    print("Batch-querying Wikidata P856 for all candidate ISTAT codes...")
    istat_codes = sorted(
        {
            (s.get("ipa_codice_comune_istat") or "").zfill(6)
            for _, _, s in candidates
            if s.get("ipa_codice_comune_istat")
        }
    )
    wd_corrections = fetch_wikidata_websites(istat_codes)
    print(f"  Wikidata returned {len(wd_corrections)} entries with P856")

    dns_sem = asyncio.Semaphore(CONCURRENCY_DNS)
    http_sem = asyncio.Semaphore(CONCURRENCY_HTTP)

    status_counter: Counter[str] = Counter()
    provider_counter: Counter[str] = Counter()

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        verify=False,  # PA sites occasionally have self-signed certs
        max_redirects=4,
    ) as client:
        tasks = [
            finalize_one(
                k,
                e,
                s,
                raw_by_key.get(k),
                wd_corrections,
                aoo_uo_ext,
                client,
                dns_sem,
                http_sem,
            )
            for k, e, s in candidates
        ]
        n_done = 0
        for coro in asyncio.as_completed(tasks):
            key, mutation, status = await coro
            n_done += 1
            status_counter[status] += 1
            entry = muns[key]
            for k, v in mutation.items():
                entry[k] = v
            if status in ("public_pec", "wikidata", "scrape_primary", "search_engine"):
                provider_counter[entry.get("provider", "?")] += 1
            if n_done % 5 == 0:
                print(f"  [{n_done}/{len(candidates)}] {dict(status_counter)}")

    counts: Counter[str] = Counter(v.get("provider", "unknown") for v in muns.values())
    data["counts"] = dict(counts)
    data_path.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )

    print()
    print("=== Status breakdown ===")
    for s, n in status_counter.most_common():
        print(f"  {s:<20} {n:>4}")
    print()
    print("=== New provider distribution among finalized ===")
    for p, n in provider_counter.most_common():
        print(f"  {p:<25} {n:>4}")
    print()
    print(f"Wrote {data_path}")
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())

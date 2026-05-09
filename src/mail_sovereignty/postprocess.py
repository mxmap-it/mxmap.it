import asyncio
import json
import ssl
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from mail_sovereignty.classify import (
    classify,
    classify_from_smtp_banner,
    detect_gateway,
)
from mail_sovereignty.constants import (
    CONCURRENCY_POSTPROCESS,
    CONCURRENCY_SMTP,
    EMAIL_RE,
    PROVIDER_KEYWORDS,
    SCRAPE_TIME_BUDGET,
    SKIP_DOMAINS,
    SUBPAGES,
    TYPO3_RE,
)
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
from mail_sovereignty.smtp import fetch_smtp_banner
from mail_sovereignty.scrape_validator import is_legit_email_domain


def decrypt_typo3(encoded: str, offset: int = 2) -> str:
    """Decrypt TYPO3 linkTo_UnCryptMailto Caesar cipher.

    TYPO3 encrypts mailto: links with a Caesar shift on three ASCII ranges:
      0x2B-0x3A (+,-./0123456789:)  -- covers . : and digits
      0x40-0x5A (@A-Z)             -- covers @ and uppercase
      0x61-0x7A (a-z)             -- covers lowercase
    Default encryption offset is -2, so decryption is +2 with wrap.
    """
    ranges = [(0x2B, 0x3A), (0x40, 0x5A), (0x61, 0x7A)]
    result = []
    for c in encoded:
        code = ord(c)
        decrypted = False
        for start, end in ranges:
            if start <= code <= end:
                n = code + offset
                if n > end:
                    n = start + (n - end - 1)
                result.append(chr(n))
                decrypted = True
                break
        if not decrypted:
            result.append(c)
    return "".join(result)


def extract_email_domains(html: str) -> set[str]:
    """Extract email domains from HTML, including TYPO3-obfuscated emails."""
    domains = set()

    for email in EMAIL_RE.findall(html):
        domain = email.split("@")[1].lower()
        if domain not in SKIP_DOMAINS:
            domains.add(domain)

    for email in __import__("re").findall(r'mailto:([^">\s?]+)', html):
        if "@" in email:
            domain = email.split("@")[1].lower()
            if domain not in SKIP_DOMAINS:
                domains.add(domain)

    for encoded in TYPO3_RE.findall(html):
        decoded = decrypt_typo3(encoded)
        decoded = decoded.replace("mailto:", "")
        if "@" in decoded:
            domain = decoded.split("@")[1].lower()
            if domain not in SKIP_DOMAINS:
                domains.add(domain)

    return domains


def build_urls(domain: str) -> list[str]:
    """Build candidate URLs to scrape, trying www. prefix first."""
    domain = domain.strip()
    if domain.startswith(("http://", "https://")):
        parsed = urlparse(domain)
        domain = parsed.hostname or domain
    if domain.startswith("www."):
        bare = domain[4:]
    else:
        bare = domain

    bases = [f"https://www.{bare}", f"https://{bare}"]
    urls = []
    for base in bases:
        urls.append(base + "/")
        for path in SUBPAGES:
            urls.append(base + path)
    return urls


async def scrape_email_domains(client: httpx.AsyncClient, domain: str) -> set[str]:
    """Scrape a municipality website for email domains."""
    if not domain:
        return set()

    all_domains = set()
    urls = build_urls(domain)

    for url in urls:
        try:
            r = await client.get(url, follow_redirects=True, timeout=15)
            if r.status_code != 200:
                continue
            domains = extract_email_domains(r.text)
            all_domains |= domains
            if all_domains:
                return all_domains
        except ssl.SSLCertVerificationError:
            # Retry without SSL verification for expired/invalid certs
            try:
                async with httpx.AsyncClient(verify=False) as insecure:
                    r = await insecure.get(url, follow_redirects=True, timeout=15)
                    if r.status_code == 200:
                        domains = extract_email_domains(r.text)
                        all_domains |= domains
                        if all_domains:
                            return all_domains
            except Exception:
                continue
        except Exception:
            continue

    return all_domains


async def process_unknown(
    client: httpx.AsyncClient, semaphore: asyncio.Semaphore, m: dict[str, Any]
) -> dict[str, Any]:
    """Try to resolve an unknown municipality by scraping its website."""
    async with semaphore:
        bfs = m["bfs"]
        name = m["name"]
        domain = m.get("domain", "")

        if not domain:
            print(f"  SKIP     {bfs:>5} {name:<30} (no domain)")
            return m

        try:
            email_domains = await asyncio.wait_for(
                scrape_email_domains(client, domain), timeout=30
            )
        except asyncio.TimeoutError:
            print(
                f"  TIMEOUT  {bfs:>5} {name:<30} (scraping timed out)"
            )
            return m

        ente_domain = m.get("domain", "")
        codice_ipa = m.get("ipa_codice_ipa") or m.get("codice_ipa")
        rejected_audit: list[dict[str, str]] = []
        for email_domain in sorted(email_domains):
            ok, reason_legit = is_legit_email_domain(
                email_domain, ente_domain, codice_ipa=codice_ipa
            )
            if not ok:
                rejected_audit.append(
                    {"dom": email_domain, "reason": reason_legit}
                )
                continue
            mx = await lookup_mx(email_domain)
            if mx:
                spf, txt_verifications = await lookup_txt(email_domain)
                spf_resolved = await resolve_spf_includes(spf) if spf else ""
                mx_cnames = await resolve_mx_cnames(mx)
                mx_asns = await resolve_mx_asns(mx)
                mx_countries = await resolve_mx_countries(mx)
                autodiscover = await lookup_autodiscover(email_domain)
                dkim = await lookup_dkim(email_domain)
                tenant = await lookup_tenant(email_domain)
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
                gateway = detect_gateway(mx)
                print(
                    f"  RESOLVED {bfs:>5} {name:<30} "
                    f"email_domain={email_domain} -> {provider}"
                )
                m["mx"] = mx
                m["spf"] = spf
                m["provider"] = provider
                m["reason"] = reason
                m["domain"] = email_domain
                if spf_resolved and spf_resolved != spf:
                    m["spf_resolved"] = spf_resolved
                if gateway:
                    m["gateway"] = gateway
                if mx_cnames:
                    m["mx_cnames"] = mx_cnames
                if mx_asns:
                    m["mx_asns"] = sorted(mx_asns)
                if mx_countries:
                    m["mx_countries"] = sorted(mx_countries)
                if autodiscover:
                    m["autodiscover"] = autodiscover
                if dkim:
                    m["dkim"] = dkim
                if txt_verifications:
                    m["txt_verifications"] = txt_verifications
                if tenant:
                    m["tenant"] = tenant
                return m

        if rejected_audit:
            m["scrape_rejected_domains"] = rejected_audit[:10]
            print(
                f"  UNKNOWN  {bfs:>5} {name:<30} "
                f"(scraped {len(email_domains)} email domains, "
                f"all rejected by is_legit gate: "
                f"{[r['dom'] for r in rejected_audit][:5]})"
            )
        else:
            print(
                f"  UNKNOWN  {bfs:>5} {name:<30} "
                f"(scraped email domains: {email_domains or 'none'})"
            )
        return m


MANUAL_OVERRIDES = {
    # Domains that differ from the guessed pattern
    "EE-0528": {
        "domain": "nvv.ee",  # noo.ee is Noo Lihatoostus (meat factory)
    },
    "EE-0589": {
        "domain": "peipsivald.ee",  # peipsi.ee is a tourism NGO
    },
    "EE-0638": {
        "domain": "pparnumaa.ee",
    },
    "LT-33": {
        "domain": "panrs.lt",
    },
    "LV-0112": {
        "domain": "dkn.lv",
    },
    # Outokumpu: outokumpu.fi is the mining company, not the city
    "FI-309": {
        "domain": "outokummunkaupunki.fi",
    },
    # Nokia: nokia.fi is the phone company, not the city
    "FI-536": {
        "domain": "nokiankaupunki.fi",
    },
    # Närpiö: domain is narpes.fi (Swedish name), not narpio.fi
    "FI-545": {
        "domain": "narpes.fi",
    },
    # Koski Tl: official domain is koski.fi (not koski-tl.fi)
    "FI-284": {
        "domain": "koski.fi",
    },
    # Salzlandkreis: salzlandkreis.de has no MX, email is on kreis-slk.de
    "DE-15089": {
        "domain": "kreis-slk.de",
    },
    # Rhein-Pfalz-Kreis: rhein-pfalz-kreis.de has no MX, email on rheinpfalzkreis.de
    "DE-07338": {
        "domain": "rheinpfalzkreis.de",
    },
    # Pölla: poella.gv.at has no MX, email is on poella.at
    "AT-32520": {
        "domain": "poella.at",
    },
    # Rainbach im Mühlkreis: website is rainbach.at, email on gemeinde-rainbach.at
    "AT-40615": {
        "domain": "gemeinde-rainbach.at",
    },
    # Austrian Tirol municipalities: email on name.gv.at, not name.tirol.gv.at
    "AT-62279": {"domain": "waldbach-moenichwald.gv.at"},
    "AT-70201": {"domain": "arzl-pitztal.gv.at"},
    "AT-70207": {"domain": "karroesten.gv.at"},
    "AT-70208": {"domain": "laengenfeld.gv.at"},
    "AT-70210": {"domain": "mils-imst.gv.at"},
    "AT-70217": {"domain": "st-leonhard-pitztal.gv.at"},
    "AT-70220": {"domain": "soelden.gv.at"},
    "AT-70312": {"domain": "goetzens.gv.at"},
    "AT-70313": {"domain": "gries-brenner.gv.at"},
    "AT-70314": {"domain": "gries-sellrain.gv.at"},
    "AT-70334": {"domain": "neustift-stubaital.gv.at"},
    "AT-70335": {"domain": "oberhofen-inntal.gv.at"},
    "AT-70336": {"domain": "obernberg-brenner.gv.at"},
    "AT-70344": {"domain": "reith-seefeld.at"},
    "AT-70347": {"domain": "st-sigmund.gv.at"},
    "AT-70350": {"domain": "schoenberg.gv.at"},
    "AT-70355": {"domain": "steinach.gv.at"},
    "AT-70401": {"domain": "aurach-kitzbuehel.gv.at"},
    "AT-70402": {"domain": "brixen-thale.gv.at"},
    "AT-70404": {"domain": "going.gv.at"},
    "AT-70406": {"domain": "hopfgarten-brixental.gv.at"},
    "AT-70409": {"domain": "kirchberg-tirol.gv.at"},
    "AT-70410": {"domain": "kirchdorf-tirol.gv.at"},
    "AT-70415": {"domain": "st-jakob-haus.gv.at"},
    "AT-70417": {"domain": "st-ulrich-pillersee.gv.at"},
    "AT-70505": {"domain": "breitenbach-inn.gv.at"},
    "AT-70522": {"domain": "reithimalpbachtal.at"},
    "AT-70530": {"domain": "wildschoenau.gv.at"},
    "AT-70604": {"domain": "fliess.gv.at"},
    "AT-70616": {"domain": "pettneu.gv.at"},
    "AT-70620": {"domain": "ried-oberinntal.gv.at"},
    "AT-70622": {"domain": "schoenwies.gv.at"},
    "AT-70626": {"domain": "stanz-landeck.gv.at"},
    "AT-70629": {"domain": "toesens.gv.at"},
    "AT-70717": {"domain": "matrei-osttirol.gv.at"},
    "AT-70813": {"domain": "haeselgehr.gv.at"},
    "AT-70824": {"domain": "nesselwaengle.gv.at"},
    "AT-70836": {"domain": "weissenbach-lech.gv.at"},
    "AT-70837": {"domain": "zoeblen.gv.at"},
    "AT-70902": {"domain": "aschau-zillertal.gv.at"},
    "AT-70907": {"domain": "eben-achensee.gv.at"},
    "AT-70910": {"domain": "fuegenberg.gv.at"},
    "AT-70922": {"domain": "ramsau-zillertal.gv.at"},
    "AT-70923": {"domain": "ried-zillertal.gv.at"},
    "AT-70929": {"domain": "steinberg-rofan.gv.at"},
    "AT-70930": {"domain": "strass-zillertal.gv.at"},
    "AT-70941": {"domain": "gemeinde-zellberg.at"},
}


async def run(data_path: Path) -> None:
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    muni = data["municipalities"]

    # Step 1: Apply manual overrides
    print("Applying manual overrides...")
    dns_relookup = []  # (bfs, domain) pairs needing MX/SPF re-lookup
    for bfs, override in MANUAL_OVERRIDES.items():
        if bfs not in muni and "name" in override:
            muni[bfs] = {
                "bfs": bfs,
                "name": override["name"],
                "canton": override.get("canton", ""),
                "domain": "",
                "mx": [],
                "spf": "",
                "provider": "unknown",
            }
            print(f"  {bfs:>5} {override['name']:<30} (added missing municipality)")
        if bfs not in muni:
            continue
        if bfs in muni:
            if "domain" in override:
                muni[bfs]["domain"] = override["domain"]
            if "provider" in override:
                muni[bfs]["provider"] = override["provider"]
            if "gateway" in override:
                muni[bfs]["gateway"] = override["gateway"]
            if "mx" in override:
                muni[bfs]["mx"] = override["mx"]
            if "spf" in override:
                muni[bfs]["spf"] = override["spf"]
            if override.get("provider") == "merged":
                muni[bfs]["mx"] = []
                muni[bfs]["spf"] = ""
            # Domain-only override: need to re-lookup MX/SPF from DNS
            if (
                "domain" in override
                and override["domain"]
                and "mx" not in override
                and "provider" not in override
            ):
                dns_relookup.append((bfs, override["domain"]))
            else:
                print(
                    f"  {bfs:>5} {muni[bfs]['name']:<30} -> {override.get('provider', '?')}"
                )

    if dns_relookup:

        async def _relookup(bfs, domain):
            mx = await lookup_mx(domain)
            spf, txt_verifications = await lookup_txt(domain)
            spf_resolved = await resolve_spf_includes(spf) if spf else ""
            mx_cnames = await resolve_mx_cnames(mx) if mx else {}
            mx_asns = await resolve_mx_asns(mx) if mx else set()
            mx_countries = await resolve_mx_countries(mx) if mx else set()
            autodiscover = await lookup_autodiscover(domain)
            dkim = await lookup_dkim(domain)
            tenant = await lookup_tenant(domain)
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
            return (
                bfs,
                mx,
                spf,
                spf_resolved,
                mx_cnames,
                mx_asns,
                mx_countries,
                provider,
                reason,
                gateway,
                autodiscover,
                dkim,
                txt_verifications,
                tenant,
            )

        results = await asyncio.gather(*[_relookup(b, d) for b, d in dns_relookup])
        for (
            bfs,
            mx,
            spf,
            spf_resolved,
            mx_cnames,
            mx_asns,
            mx_countries,
            provider,
            reason,
            gateway,
            autodiscover,
            dkim,
            txt_verifications,
            tenant,
        ) in results:
            muni[bfs]["mx"] = mx
            muni[bfs]["spf"] = spf
            muni[bfs]["provider"] = provider
            muni[bfs]["reason"] = reason
            if spf_resolved and spf_resolved != spf:
                muni[bfs]["spf_resolved"] = spf_resolved
            if gateway:
                muni[bfs]["gateway"] = gateway
            if mx_cnames:
                muni[bfs]["mx_cnames"] = mx_cnames
            if mx_asns:
                muni[bfs]["mx_asns"] = sorted(mx_asns)
            if mx_countries:
                muni[bfs]["mx_countries"] = sorted(mx_countries)
            if autodiscover:
                muni[bfs]["autodiscover"] = autodiscover
            if dkim:
                muni[bfs]["dkim"] = dkim
            if txt_verifications:
                muni[bfs]["txt_verifications"] = txt_verifications
            if tenant:
                muni[bfs]["tenant"] = tenant
            print(f"  {bfs:>5} {muni[bfs]['name']:<30} -> {provider} (DNS re-lookup)")

    # Step 2: Retry DNS for unknowns that have a domain (concurrent)
    dns_retry_candidates = [
        m for m in muni.values() if m["provider"] == "unknown" and m.get("domain")
    ]
    if dns_retry_candidates:
        print(f"\nRetrying DNS for {len(dns_retry_candidates)} unknown domains...")
        dns_retry_sem = asyncio.Semaphore(20)

        async def _dns_retry(m):
            async with dns_retry_sem:
                domain = m["domain"]
                mx = await lookup_mx(domain)
                if not mx:
                    return
                spf, txt_verifications = await lookup_txt(domain)
                spf_resolved = await resolve_spf_includes(spf) if spf else ""
                mx_cnames = await resolve_mx_cnames(mx)
                mx_asns = await resolve_mx_asns(mx)
                mx_countries = await resolve_mx_countries(mx)
                autodiscover = await lookup_autodiscover(domain)
                dkim = await lookup_dkim(domain)
                tenant = await lookup_tenant(domain)
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
                gateway = detect_gateway(mx)
                m["mx"] = mx
                m["spf"] = spf
                m["provider"] = provider
                m["reason"] = reason
                if spf_resolved and spf_resolved != spf:
                    m["spf_resolved"] = spf_resolved
                if gateway:
                    m["gateway"] = gateway
                if mx_cnames:
                    m["mx_cnames"] = mx_cnames
                if mx_asns:
                    m["mx_asns"] = sorted(mx_asns)
                if mx_countries:
                    m["mx_countries"] = sorted(mx_countries)
                if autodiscover:
                    m["autodiscover"] = autodiscover
                if dkim:
                    m["dkim"] = dkim
                if txt_verifications:
                    m["txt_verifications"] = txt_verifications
                if tenant:
                    m["tenant"] = tenant
                print(f"  RECOVERED {m['bfs']:>5} {m['name']:<30} -> {provider}")

        await asyncio.gather(*[_dns_retry(m) for m in dns_retry_candidates])

    # Step 2.5: SMTP banner check for independent/unknown with MX records
    smtp_candidates = [
        m
        for m in muni.values()
        if m["provider"] in ("independent", "unknown") and m.get("mx")
    ]
    if smtp_candidates:
        # Deduplicate: map each unique MX host -> list of BFS numbers
        mx_host_to_bfs: dict[str, list[str]] = {}
        for m in smtp_candidates:
            primary_mx = m["mx"][0]
            mx_host_to_bfs.setdefault(primary_mx, []).append(m["bfs"])

        print(
            f"\nSMTP banner check: {len(smtp_candidates)} entries, "
            f"{len(mx_host_to_bfs)} unique MX hosts..."
        )
        smtp_semaphore = asyncio.Semaphore(CONCURRENCY_SMTP)

        async def _fetch_banner(mx_host: str) -> tuple[str, dict[str, str]]:
            async with smtp_semaphore:
                res = await fetch_smtp_banner(mx_host)
                return mx_host, res

        banner_results = await asyncio.gather(
            *[_fetch_banner(host) for host in mx_host_to_bfs]
        )

        smtp_reclassified = 0
        for mx_host, result in banner_results:
            banner = result.get("banner", "")
            ehlo = result.get("ehlo", "")
            if not banner:
                continue
            provider = classify_from_smtp_banner(banner, ehlo)
            # Check if the banner hostname itself belongs to a cloud
            # provider (e.g. "220 xxx.mail.protection.outlook.com ...").
            # If so, the municipality truly uses that provider's cloud
            # even though the MX hostname looked self-hosted.
            banner_host_is_cloud = provider and any(
                kw in banner.lower().split()[1]
                for kw in PROVIDER_KEYWORDS.get(provider, [])
                if "." in kw  # only domain-like keywords
            ) if len(banner.split()) > 1 else False
            for bfs in mx_host_to_bfs[mx_host]:
                muni[bfs]["smtp_banner"] = banner
                if provider and muni[bfs]["provider"] in ("independent", "unknown"):
                    old = muni[bfs]["provider"]
                    if old == "independent" and not banner_host_is_cloud:
                        # Self-hosted server running commercial software
                        # (e.g. on-premise Exchange).  Keep as
                        # "independent" but record the software so the
                        # frontend can show it.
                        muni[bfs]["smtp_software"] = provider
                        print(
                            f"  SMTP     {bfs:>5} {muni[bfs]['name']:<30} "
                            f"independent (runs {provider}) ({mx_host})"
                        )
                    else:
                        muni[bfs]["provider"] = provider
                        smtp_reclassified += 1
                        print(
                            f"  SMTP     {bfs:>5} {muni[bfs]['name']:<30} "
                            f"{old} -> {provider} ({mx_host})"
                        )

        print(f"  SMTP reclassified: {smtp_reclassified}")

    # Step 3: Scrape remaining unknowns (with time budget)
    unknowns = [m for m in muni.values() if m["provider"] == "unknown"]
    print(f"\n{len(unknowns)} unknown municipalities to investigate\n")

    if unknowns:
        import time

        scrape_budget = SCRAPE_TIME_BUDGET
        scrape_start = time.monotonic()
        budget_exhausted = False
        semaphore = asyncio.Semaphore(CONCURRENCY_POSTPROCESS)

        async def process_with_budget(
            client: httpx.AsyncClient, m: dict[str, Any]
        ) -> dict[str, Any]:
            nonlocal budget_exhausted
            if budget_exhausted:
                return m
            elapsed = time.monotonic() - scrape_start
            if elapsed >= scrape_budget:
                budget_exhausted = True
                print(
                    f"\n  Time budget exhausted ({scrape_budget}s) — "
                    f"skipping remaining unknowns"
                )
                return m
            return await process_unknown(client, semaphore, m)

        async with httpx.AsyncClient(
            headers={
                "User-Agent": "mxmap.ee/1.0 (https://github.com/livenson/mxmap)"
            },
            follow_redirects=True,
        ) as client:
            tasks = [process_with_budget(client, m) for m in unknowns]
            results = await asyncio.gather(*tasks)

        resolved = 0
        for m in results:
            muni[m["bfs"]] = m
            if m["provider"] != "unknown":
                resolved += 1
        elapsed = int(time.monotonic() - scrape_start)
        print(f"\nResolved {resolved}/{len(unknowns)} via scraping ({elapsed}s)")

    # Recompute counts
    counts = {}
    for m in muni.values():
        counts[m["provider"]] = counts.get(m["provider"], 0) + 1
    data["counts"] = dict(sorted(counts.items()))
    data["total"] = len(muni)
    data["municipalities"] = dict(sorted(muni.items()))

    remaining = counts.get("unknown", 0)
    print(f"\nFinal counts: {json.dumps(counts)}")

    if remaining > 0:
        print(f"\nStill unknown ({remaining}, for manual review):")
        for m in sorted(muni.values(), key=lambda x: x["bfs"]):
            if m["provider"] == "unknown":
                print(
                    f"  {m['bfs']:>5}  {m['name']:<30} {m['canton']:<20} domain={m['domain']}"
                )

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, separators=(",", ":"))

    print(f"\nUpdated {data_path}")

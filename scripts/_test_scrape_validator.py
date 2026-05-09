#!/usr/bin/env python3
"""Unit tests for scrape_validator.is_legit_email_domain.

Cases derived from the scraped_mx_bug audit + design discussion."""
import sys
from pathlib import Path
sys.path.insert(0, str((Path(__file__).resolve().parent.parent / "src").as_posix()))
from mail_sovereignty.scrape_validator import is_legit_email_domain, meaningful_labels


CASES = [
    # (scraped, ente, expected_legit, label_for_test)

    # === ACCEPT cases ===
    ("interno.it",                   "interno.gov.it",            True,
     "gov.it -> .it migration"),
    ("comune.padova.it",             "comune.padova.it",          True,
     "exact match"),
    ("mail.comune.padova.it",        "comune.padova.it",          True,
     "subdomain prefix"),
    ("comune.roccagorga.lt.it",      "roccagorga.lt.it",          True,
     "comune. prefix vs bare"),
    ("lepida.it",                    "comune.bolognola.mc.it",    True,
     "PA-shared platform Lepida"),
    ("ariaspa.it",                   "comune.milano.it",          True,
     "PA-shared platform ARIA"),
    ("ruparpiemonte.it",             "comune.albianodivrea.to.it", True,
     "PA-shared platform RUPAR Piemonte"),
    ("schule.suedtirol.it",          "spcgg",                     True,
     "PA-shared schule South Tyrol"),
    ("regione.emilia-romagna.it",    "comune.bologna.it",         True,
     "PA-shared regione ER"),

    # === REJECT cases (the actual bug pattern) ===
    ("comune.roma.it",               "interno.gov.it",            False,
     "BUG: cross-tenant Roma -> Min Interno"),
    ("comune.roma.it",               "peritiagrari.it",           False,
     "BUG: Roma -> Periti Agrari"),
    ("comune.catanzaro.it",          "peritiagraricatanzaro.it",  False,
     "BUG: Catanzaro -> Periti Agrari Catanzaro (different ente)"),
    ("istruzione.it",                "comune.padova.it",          False,
     "BUG: MIUR tenant -> random comune"),
    ("comune.napoli.it",             "comune.padova.it",          False,
     "BUG: Napoli tenant -> Padova"),
    ("legalmail.it",                 "comune.foo.it",             False,
     "PEC provider always rejected"),
    ("pec.it",                       "comune.foo.it",             False,
     "PEC provider always rejected"),
    ("aruba.it",                     "comune.foo.it",             False,
     "Aruba (= Aruba PEC) rejected as PEC"),
    ("postecert.it",                 "comune.foo.it",             False,
     "Posta Certificata rejected"),
    ("gmail.com",                    "comune.foo.it",             False,
     "Generic gmail rejected"),

    # === Edge cases ===
    ("comune.padova.it",             "comune.roma.it",            False,
     "two different comuni — 'comune' is noise prefix, no shared identity"),
    ("provincia.lecce.it",           "comune.lecce.it",           True,
     "same city -> 'lecce' shared label"),
    ("aslroma1.it",                  "asl-roma1.it",              False,
     "hyphenation typo — limit acknowledged, manual override needed"),
]


def main():
    fails = 0
    print(f"=== {len(CASES)} test cases ===\n")
    for scraped, ente, expected, desc in CASES:
        got, reason = is_legit_email_domain(scraped, ente)
        status = "OK  " if got == expected else "FAIL"
        if got != expected:
            fails += 1
        print(f"  {status}  {scraped:<30} vs {ente:<30}  exp={expected!s:<5}  got={got!s:<5}  reason={reason}")
        if got != expected:
            print(f"        ({desc})")
            sl, el = meaningful_labels(scraped), meaningful_labels(ente)
            print(f"        scraped_labels={sl}  ente_labels={el}")
    print()
    print(f"=== Summary: {len(CASES)-fails}/{len(CASES)} passed ===")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

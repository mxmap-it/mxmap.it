"""EU Security Map (#33/#34): fonde le risposte di più LLM sui domini email.

Input: data/eu_security/llm/{model}.txt nel formato compatto
  "id dominio CODICE;id dominio CODICE;..."  (CODICE: S=visto su sito ufficiale,
  D=documento ufficiale, T=fonte terza, P=dedotto dal ministero, W=dal sito).

Regola (multi-LLM, owner): un dominio è accettato solo se **almeno due modelli
indipendenti concordano citando una fonte (S/D/T)** E il dominio ha record MX attivi. In tal caso il file
di ricerca del paese riceve un'evidenza `kind=llm_consensus` che documenta chi
ha concordato e su quale base dichiarata — mostrata in pagina come metodo di
inferenza. Mai sovrascrivere un'evidenza da sito/documento ufficiale.
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path

from mail_sovereignty.dns import lookup_mx

ROOT = Path(__file__).resolve().parent.parent
LLM_DIR = ROOT / "data" / "eu_security" / "llm"
RESEARCH = ROOT / "data" / "eu_security" / "research"
CODE = {
    "S": "seen on official site",
    "D": "seen in official document",
    "T": "seen in third-party source",
    "P": "inferred from parent ministry",
    "W": "inferred from website",
}
MODEL_NAME = {"chatgpt": "ChatGPT", "qwen": "Qwen", "deepseek": "DeepSeek", "claude": "Claude"}
EVIDENCE_CODES = {"S", "D", "T"}
STRONG_KINDS = {"contact_page", "privacy_page", "press_page", "other_official", "official_pdf"}


def load_answers() -> dict[str, dict[str, tuple[str, str]]]:
    """{id: {model: (domain, code)}}"""
    out: dict[str, dict[str, tuple[str, str]]] = defaultdict(dict)
    for f in sorted(LLM_DIR.glob("*.txt")):
        model = f.stem
        for item in f.read_text(encoding="utf-8").replace("\n", ";").split(";"):
            parts = item.strip().split()
            if len(parts) != 3:
                continue
            eid, dom, code = parts
            dom = dom.lower().strip(".")
            if dom == "unknown" or "." not in dom:
                continue
            # solo voti con fonte dichiarata: "dedotto dal sito/ministero" ripete
            # l'indizio che abbiamo fornito noi e non è evidenza indipendente
            if code not in EVIDENCE_CODES:
                continue
            out[eid][model] = (dom, code)
    return out


async def has_mx(domains: set[str]) -> dict[str, bool]:
    res = await asyncio.gather(*(lookup_mx(d) for d in domains))
    return {d: bool(r) for d, r in zip(domains, res, strict=True)}


def main() -> int:
    answers = load_answers()
    consensus: dict[str, tuple[str, list[str]]] = {}
    for eid, by_model in answers.items():
        votes: dict[str, list[str]] = defaultdict(list)
        for model, (dom, code) in by_model.items():
            votes[dom].append(f"{MODEL_NAME.get(model, model)}: {CODE.get(code, code)}")
        best = max(votes.items(), key=lambda kv: len(kv[1]))
        if len(best[1]) >= 2:
            consensus[eid] = best
    mx = asyncio.run(has_mx({d for d, _ in consensus.values()}))

    applied, rejected_mx, kept_official = [], [], []
    for f in sorted(RESEARCH.glob("*.json")):  # LLM pass solo su wave 1
        doc = json.loads(f.read_text(encoding="utf-8"))
        changed = False
        for e in doc["entities"]:
            if e["id"] not in consensus:
                continue
            dom, who = consensus[e["id"]]
            if not mx.get(dom):
                rejected_mx.append(f"{e['id']} {dom}")
                continue
            evs = e.setdefault("evidence", [])
            if any(
                ev.get("domain") == dom and ev.get("kind") in STRONG_KINDS for ev in evs
            ):
                kept_official.append(e["id"])
                continue
            evs[:] = [ev for ev in evs if ev.get("domain") != dom]
            evs.insert(
                0,
                {
                    "domain": dom,
                    "url": "",
                    "kind": "llm_consensus",
                    "note": "; ".join(who),
                },
            )
            doms = [d for d in e.get("mail_domains") or [] if d != dom]
            e["mail_domains"] = [dom, *doms]
            if e.get("confidence") == "low":
                e["confidence"] = "medium"
            changed = True
            applied.append(f"{e['id']} -> {dom} ({'; '.join(who)})")
        if changed:
            f.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"consensus candidates: {len(consensus)}")
    print(f"applied: {len(applied)}")
    for a in applied:
        print("  +", a)
    print(f"rejected (no MX): {rejected_mx}")
    print(f"already backed by official evidence: {len(kept_official)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

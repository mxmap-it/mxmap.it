import asyncio
import sys
from pathlib import Path


def _parse_country_args(
    args: list[str],
) -> tuple[list[str] | None, dict[str, list[str]]]:
    """Parse country arguments, supporting CC:STATE syntax for sub-country filtering.

    Examples:
        ["DE:BY"]       → countries=["DE"], state_filters={"DE": ["09"]}
        ["DE:09"]       → countries=["DE"], state_filters={"DE": ["09"]}
        ["DE:BY,NW"]    → countries=["DE"], state_filters={"DE": ["09", "05"]}
        ["DE:BY", "IT"] → countries=["DE", "IT"], state_filters={"DE": ["09"]}
        []              → countries=None, state_filters={}
    """
    from mail_sovereignty.constants import DE_STATES

    if not args:
        return None, {}

    countries = []
    state_filters: dict[str, list[str]] = {}

    for arg in args:
        arg = arg.upper()
        if ":" in arg:
            cc, state_part = arg.split(":", 1)
            countries.append(cc)
            codes = []
            for s in state_part.split(","):
                s = s.strip()
                if not s:
                    continue
                # Accept both abbreviation (BY) and code (09)
                if cc == "DE" and s in DE_STATES:
                    codes.append(DE_STATES[s])
                else:
                    codes.append(s)
            if codes:
                state_filters[cc] = codes
        else:
            countries.append(arg)

    return countries, state_filters


def preprocess() -> None:
    from mail_sovereignty.preprocess import run

    # Optional country filter: `uv run preprocess IT IE NL` or `uv run preprocess DE:BY`
    countries, state_filters = _parse_country_args(sys.argv[1:])
    asyncio.run(
        run(Path("data.json"), countries=countries, state_filters=state_filters)
    )


def postprocess() -> None:
    from mail_sovereignty.postprocess import run

    asyncio.run(run(Path("data.json")))


def validate() -> None:
    from mail_sovereignty.validate import run

    run(Path("data.json"), Path("."), quality_gate=True)

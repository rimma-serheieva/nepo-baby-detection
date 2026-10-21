"""
classify.py — runs the tier cascade for one actor and merges the results.

Order matches the production design: Tier 1 (Wikipedia) is checked
first because it's the most reliably sourced; Tier 2 (Wikidata) only
runs when Tier 1 is inconclusive, not to double-check a "Yes" — a
confirmed result from either trusted tier is final, never re-litigated
by a lower-priority source.

Optional tiers (LLM, TMDb bio) are pluggable, loaded only if their
module is present and a key is configured — see tiers/llm.py and
tiers/tmdb.py. This demo runs fully on Tiers 1+2 alone, which the real
production benchmark found already catch the large majority of
confirmable cases.
"""
import os

from tiers import wikidata, wikipedia

FINAL_STATUSES = {"Yes", "Not a nepo baby"}   # these never get overridden by a later tier


def classify(actor_name, birth_year=""):
    """-> dict with status, evidence, and which tier(s) actually ran."""
    tiers_run = []

    status, evidence = wikipedia.check(actor_name)
    tiers_run.append("wikipedia")
    if status in FINAL_STATUSES:
        return {"actor": actor_name, "status": status, "evidence": evidence,
                "tiers_run": tiers_run}

    status, evidence = wikidata.check(actor_name, birth_year)
    tiers_run.append("wikidata")
    if status in FINAL_STATUSES:
        return {"actor": actor_name, "status": status, "evidence": evidence,
                "tiers_run": tiers_run}

    # optional tiers — only attempted if configured; neither is required
    # for the demo to run or for its measured result to be real
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            from tiers import llm
            status, evidence = llm.check(actor_name)
            tiers_run.append("llm")
            if status in FINAL_STATUSES:
                return {"actor": actor_name, "status": status, "evidence": evidence,
                        "tiers_run": tiers_run}
        except ImportError:
            pass

    if os.environ.get("TMDB_API_KEY"):
        try:
            from tiers import tmdb
            status, evidence = tmdb.check(actor_name)
            tiers_run.append("tmdb")
            if status in FINAL_STATUSES:
                return {"actor": actor_name, "status": status, "evidence": evidence,
                        "tiers_run": tiers_run}
        except ImportError:
            pass

    return {"actor": actor_name, "status": "Unknown",
            "evidence": {"reason": "no tier could confirm or rule it out"},
            "tiers_run": tiers_run}

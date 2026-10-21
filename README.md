# Nepo Baby Detection

Given an actor's name, confirm whether they have a parent in the
entertainment industry — a multi-tier classification cascade over
public sources, built so that a "Yes" is never a guess.

## The real project this generalizes

This is an independent rebuild of the methodology behind research I
built that replaced roughly two months of manual work, covering 44,980
actors across 25 years of box-office films (2000–2024). It fed a report
published on Giggster's own site and picked up by outlets including
**The Economist** and **Esquire**:

- Report: https://giggster.com/guide/reports/nepo-babies-in-hollywood-films-2000-2025
- Covered by The Economist: https://www.economist.com/culture/2026/09/08/how-much-does-nepotism-really-matter-in-hollywood
- Covered by Esquire (Italy): https://www.esquire.com/it/cultura/film/a73615691/quanto-nepotismo-hollywood/

**Real production benchmark** (from the project's own architecture doc,
measured against a manual research team's 143 independently-confirmed
nepo babies):

| Metric | Result |
|---|---|
| Hard recall (pipeline said "Yes") | 88/143 = **61.5%** |
| Soft recall ("Yes" or "To check") | 117/143 = **81.8%** |
| False negatives (a confirmed nepo marked "Not a nepo baby") | **0** |

This repo is a from-scratch rebuild of that cascade design, on a
different (smaller, demo-scale) sample, with its own measurement below
— not an export of the production code or its full dataset.

## The cascade

```
actor name
    │
    ▼
Tier 1 — Wikipedia infobox        "Parents" field is community-sourced
    │ inconclusive?                and citation-backed -> trusted outright
    ▼
Tier 2 — Wikidata                 looked up by NAME + BIRTH YEAR, never
    │ inconclusive?                name alone (see "a real bug" below)
    ▼
Tier 3 — LLM (optional, your own key)      }  pluggable fallbacks — this
Tier 4 — TMDb actor bio (optional, your own key)  }  demo runs on 1+2 alone
    │
    ▼
Yes / Not a nepo baby / Unknown
```

**The design principle that matters most**: a parent is identified by
checking *their own* page for an entertainment occupation — never by
searching for the parent's name and assuming a match. Searching by name
alone is exactly the kind of collision that cost a *different* project
in this portfolio real false positives; this pipeline never does that
search at all.

**"Not a nepo baby" and "Yes" are both FINAL.** A confirmed result from
a trusted tier is never re-litigated by a lower-priority one — see
`tests/test_classify.py` for the regression tests on this specifically.

## Results — a real benchmark, including two bugs it caught

18 public figures, deliberately including both classes — confirming
only positives can't test the "zero false positives" requirement that
actually matters:

| | |
|---|---|
| Recall on 10 confirmed positives | **9/10 (90%)** |
| False positives on 8 confirmed negatives | **0/8** |
| Unknown (neither free tier could confirm or rule out) | 6/18 |

### Two real bugs this benchmark found

1. **A Wikidata label bug.** Kate Hudson's mother came back as the
   literal string `"Q188459"` instead of "Goldie Hawn" — `wikibase:label`
   occasionally fails to bind inside a query with multiple `OPTIONAL`
   clauses. Fixed by reading the entity's own `enwiki` sitelink directly
   whenever a "label" looks like a bare QID (see `tiers/wikidata.py`).
   This is the same failure mode documented in an earlier project this
   year (`Dynasties of Hollywood`), where it was first discovered and
   fixed.
2. **A worse bug: a failed fetch read as a confident negative.** During
   the very first benchmark run, Angelina Jolie came back "Not a nepo
   baby" — wrong, since Jon Voight is about as undisputed a case as
   exists. The real cause: rate-limited, back-to-back lookups made one
   parent-page fetch silently fail, and the code fell through to "no
   parent found" instead of flagging that the check was never actually
   completed. Fixed to distinguish "checked and found nothing" from "the
   check itself failed" — the second case now reports `Inconclusive`,
   never a confident wrong answer. A re-run with proper pacing between
   requests then correctly returned `Unknown` for the one case still
   genuinely short on data.

## Architecture

```
tiers/
├── wikipedia.py    infobox parsing + parent's-own-page verification
└── wikidata.py     birth-year-disambiguated lookup + label repair
classify.py          the tier cascade + merge logic
benchmark.py         the 18-case real-network benchmark above
tests/
└── test_classify.py   6 tests on the merge logic, mocked tiers, no network
```

## Running it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m unittest tests.test_classify -v      # 6 tests, no network needed
python benchmark.py                             # the real 18-case result above
```

Optional: add `ANTHROPIC_API_KEY` and/or `TMDB_API_KEY` to `.env` to
enable Tiers 3–4 for the harder, less-documented cases this demo's
`Unknown` bucket represents.

## Honest limitations

- Demo-scale: 18 cases, not 44,980. The real recall number above is
  this repo's own, measured fresh — not borrowed from production.
- Tiers 3–4 are implemented as pluggable adapters but untested in this
  repo (no key configured) — same honest-no-key-path pattern as the
  sibling `contact-enrichment-workflows` repo.
- Wikipedia/Wikidata rate-limit sustained lookups, same as other
  projects in this portfolio; `benchmark.py` paces requests accordingly.

---
Independent re-implementation, built on public data as a portfolio
piece. Not affiliated with, and contains no code or data from, any employer.

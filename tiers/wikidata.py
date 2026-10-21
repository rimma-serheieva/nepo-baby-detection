"""
tiers/wikidata.py — Tier 2: structured data, run only when Tier 1 can't
confirm anything.

Looks the actor up by NAME + BIRTH YEAR, not name alone — the single most
important line in this file. "John Smith" without a birth year could
resolve to any of a dozen Wikidata entities; a confirmed birth year
collapses that to (almost always) exactly one.

Parent relationships: P22 (father), P25 (mother). Occupation: P106,
checked against a curated list of entertainment-industry Wikidata QIDs
rather than a string match on an English label, since Wikidata's own
labels for an occupation are multilingual and a string match would miss
every non-English one.
"""
import requests

UA = "nepo-baby-detection-portfolio-project/1.0 (educational; github.com/rimma-serheieva)"
SPARQL = "https://query.wikidata.org/sparql"

# A curated set of entertainment-industry occupation QIDs. Not
# exhaustive — the real production system used 40+; this is the core
# set for a portfolio-scale demo.
ENTERTAINMENT_OCCUPATIONS = {
    "Q33999": "actor", "Q10800557": "film actor", "Q2526255": "film director",
    "Q3282637": "film producer", "Q639669": "musician", "Q177220": "singer",
    "Q28389": "screenwriter", "Q36834": "composer", "Q245068": "comedian",
    "Q10798782": "television actor", "Q2259451": "stunt performer",
}
ENTERTAINMENT_QIDS = set(ENTERTAINMENT_OCCUPATIONS)


def sparql_query(query, tries=2):
    for _ in range(tries):
        try:
            r = requests.get(SPARQL, params={"query": query, "format": "json"},
                             headers={"User-Agent": UA}, timeout=30)
            if r.status_code == 200:
                return r.json()["results"]["bindings"]
        except (requests.RequestException, KeyError):
            pass
    return []


def find_person(name, birth_year=""):
    """-> qid or None. Birth year is matched if given; without one, this
    only accepts a result when the name search returns exactly one
    plausible match — ambiguous names with no year are left Inconclusive
    rather than guessed at."""
    year_filter = ""
    if birth_year:
        year_filter = ('?item wdt:P569 ?dob . FILTER(YEAR(?dob) = %s)' % int(birth_year))
    q = """
    SELECT ?item WHERE {
      ?item rdfs:label "%s"@en .
      ?item wdt:P31 wd:Q5 .
      %s
    } LIMIT 5
    """ % (name.replace('"', ''), year_filter)
    rows = sparql_query(q)
    qids = [r["item"]["value"].rsplit("/", 1)[-1] for r in rows]
    if not qids:
        return None
    if birth_year or len(qids) == 1:
        return qids[0]
    return None   # ambiguous with no disambiguator — don't guess


def get_parents_and_occupations(qid):
    q = """
    SELECT ?parent ?parentLabel ?occ WHERE {
      wd:%s wdt:P22|wdt:P25 ?parent .
      OPTIONAL { ?parent wdt:P106 ?occ }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
    }
    """ % qid
    return sparql_query(q)


def is_entertainment(qid):
    return qid in ENTERTAINMENT_QIDS


def repair_label(qid):
    """The wikibase:label SERVICE occasionally fails to bind an English
    label inside a query with multiple OPTIONAL clauses — it then
    silently returns the QID itself as the "label" (no xml:lang on the
    literal), which is how Goldie Hawn came back as the string
    "Q188459" during testing. The fix: read the entity's own enwiki
    sitelink title directly — a separate, simpler API call that doesn't
    share whatever caused the SPARQL label service to miss it."""
    try:
        r = requests.get("https://www.wikidata.org/w/api.php",
                         params={"action": "wbgetentities", "ids": qid,
                                "props": "sitelinks", "sitefilter": "enwiki",
                                "format": "json"},
                         headers={"User-Agent": UA}, timeout=15)
        title = r.json()["entities"][qid]["sitelinks"].get("enwiki", {}).get("title")
        return title or qid
    except Exception:
        return qid


def looks_like_a_bare_qid(label, qid):
    return label == qid or not label


def check(actor_name, birth_year=""):
    """-> (status, evidence). Same status vocabulary as tiers/wikipedia.py."""
    qid = find_person(actor_name, birth_year)
    if not qid:
        return "Inconclusive", {"reason": "could not disambiguate on Wikidata"
                                + ("" if birth_year else " (no birth year given)")}

    rows = get_parents_and_occupations(qid)
    if not rows:
        return "Inconclusive", {"reason": "no parent recorded on Wikidata", "qid": qid}

    by_parent = {}
    for r in rows:
        pqid = r["parent"]["value"].rsplit("/", 1)[-1]
        label = r.get("parentLabel", {}).get("value", pqid)
        if pqid not in by_parent:
            if looks_like_a_bare_qid(label, pqid):
                label = repair_label(pqid)
            by_parent[pqid] = {"name": label, "occupations": []}
        if "occ" in r:
            by_parent[pqid]["occupations"].append(r["occ"]["value"].rsplit("/", 1)[-1])

    for pqid, info in by_parent.items():
        if any(is_entertainment(o) for o in info["occupations"]):
            matched = next(o for o in info["occupations"] if is_entertainment(o))
            return "Yes", {"parent": info["name"],
                          "parent_occupation": ENTERTAINMENT_OCCUPATIONS.get(matched, matched),
                          "source": "wikidata", "qid": qid}

    return "Not a nepo baby", {"parents_checked": [i["name"] for i in by_parent.values()],
                               "qid": qid}

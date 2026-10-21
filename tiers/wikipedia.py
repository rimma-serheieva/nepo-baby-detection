"""
tiers/wikipedia.py — Tier 1: the most trusted source, so it's checked
first.

A Wikipedia infobox "Parents" field is community-sourced and citation-
backed, which is why a hit here is trusted outright rather than treated
as a candidate to verify. The actual check is two hops: find the
subject's listed parent, then check THAT PARENT'S OWN page for an
entertainment occupation — never inferring it from the child's page
alone, since a child's page describing a parent as "a businessman" would
otherwise be silently missed, and one describing them vaguely wouldn't
be wrongly credited either.
"""
import re
import urllib.parse

import requests
from bs4 import BeautifulSoup

UA = "nepo-baby-detection-portfolio-project/1.0 (educational; github.com/rimma-serheieva)"
WIKI_API = "https://en.wikipedia.org/w/api.php"

ENTERTAINMENT_KEYWORDS = (
    "actor", "actress", "director", "producer", "musician", "singer",
    "screenwriter", "writer", "filmmaker", "composer", "comedian",
    "entertainer", "film", "television", "music", "record producer",
    "talk show host", "dancer", "choreographer",
)


def _api_get(params, tries=2):
    params = dict(params, format="json")
    for _ in range(tries):
        try:
            r = requests.get(WIKI_API, params=params, headers={"User-Agent": UA}, timeout=15)
            if r.status_code == 200:
                return r.json()
        except requests.RequestException:
            pass
    return {}


def fetch_page_html(title):
    data = _api_get({"action": "parse", "page": title, "prop": "text", "redirects": 1})
    try:
        return data["parse"]["text"]["*"]
    except (KeyError, TypeError):
        return None


def extract_infobox_field(html, field_names):
    """Find a labelled row in the first infobox table and return its
    (text, [links]) — links matter because a parent's name is usually a
    Wikipedia link straight to THEIR page, which is the whole point."""
    soup = BeautifulSoup(html, "html.parser")
    infobox = soup.find("table", class_=re.compile(r"infobox"))
    if not infobox:
        return "", []
    for row in infobox.find_all("tr"):
        header = row.find("th")
        if not header:
            continue
        label = header.get_text(strip=True).lower()
        if any(f in label for f in field_names):
            cell = row.find("td")
            if not cell:
                continue
            text = cell.get_text(", ", strip=True)
            links = [a.get_text(strip=True) for a in cell.find_all("a")
                    if a.get_text(strip=True)]
            return text, links
    return "", []


def is_entertainment_occupation(text):
    low = text.lower()
    return any(k in low for k in ENTERTAINMENT_KEYWORDS)


def check(actor_name):
    """-> (status, evidence_dict). status in:
       "Yes", "Not a nepo baby", "Inconclusive" (Tier 1 can't confirm —
       NOT the same as a final "Unknown", which only applies once every
       tier has been tried)."""
    html = fetch_page_html(actor_name)
    if not html:
        return "Inconclusive", {"reason": "no Wikipedia page found"}

    parent_text, parent_links = extract_infobox_field(html, ("parent",))
    if not parent_text:
        return "Inconclusive", {"reason": "no Parents field in infobox"}

    parent_names = parent_links or [p.strip() for p in re.split(r",|;", parent_text) if p.strip()]
    all_fetches_succeeded = True
    for parent in parent_names[:3]:
        parent_html = fetch_page_html(parent)
        if not parent_html:
            # A failed fetch is MISSING DATA, not evidence this parent
            # isn't in entertainment. Treating it as a clean negative
            # here is exactly how a confident "Not a nepo baby" turned
            # out to be wrong during testing — the parent page fetch had
            # silently failed (rate-limited by back-to-back lookups),
            # and the bug fell through to a negative instead of flagging
            # that the check was never actually completed.
            all_fetches_succeeded = False
            continue
        occ_text, _ = extract_infobox_field(parent_html, ("occupation", "profession"))
        if occ_text and is_entertainment_occupation(occ_text):
            return "Yes", {"parent": parent, "parent_occupation": occ_text,
                          "source": "wikipedia_infobox"}
        # a parent's own LEAD PARAGRAPH often states the occupation even
        # without a clean infobox field (fewer actors have one filled in
        # than you'd expect) — checked as a second chance before giving up
        soup = BeautifulSoup(parent_html, "html.parser")
        lead = soup.find("p")
        if lead and is_entertainment_occupation(lead.get_text()):
            return "Yes", {"parent": parent, "source": "wikipedia_lead_paragraph"}

    if not all_fetches_succeeded:
        return "Inconclusive", {"parents_checked": parent_names,
                                "reason": "one or more parent pages could not be fetched"}
    return "Not a nepo baby", {"parents_checked": parent_names,
                               "reason": "no parent found with an entertainment occupation"}

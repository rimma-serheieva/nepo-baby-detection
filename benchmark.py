"""
benchmark.py — measure the pipeline against a small, hand-curated ground
truth, the same way the production system was measured against its
manual team's 143 confirmed cases.

Every entry below is a widely-documented public fact (a parent's own
Wikipedia page states their occupation) — nothing here is a guess or an
inference, which is the same standard the real benchmark held itself to.

    python3 benchmark.py
"""
import sys

import time

from classify import classify

# name, birth_year, ground_truth ("Yes" or "Not a nepo baby")
# Both classes are included on purpose — the production doc's hard
# requirement was ZERO FALSE POSITIVES, which only "Not a nepo baby"
# ground truth can actually test.
BENCHMARK = [
    ("Jamie Lee Curtis", "1958", "Yes"),      # parents: Tony Curtis, Janet Leigh
    ("Kate Hudson", "1979", "Yes"),           # parent: Goldie Hawn
    ("Zoë Kravitz", "1988", "Yes"),           # parent: Lenny Kravitz
    ("Dakota Johnson", "1989", "Yes"),        # parents: Melanie Griffith, Don Johnson
    ("Angelina Jolie", "1975", "Yes"),        # parent: Jon Voight
    ("Gwyneth Paltrow", "1972", "Yes"),       # parents: Bruce Paltrow, Blythe Danner
    ("Liza Minnelli", "1946", "Yes"),         # parent: Judy Garland
    ("Maya Hawke", "1998", "Yes"),            # parents: Uma Thurman, Ethan Hawke
    ("Lily-Rose Depp", "1999", "Yes"),        # parent: Johnny Depp
    ("Jaden Smith", "1998", "Yes"),           # parent: Will Smith

    ("Jennifer Lawrence", "1990", "Not a nepo baby"),
    ("Charlize Theron", "1975", "Not a nepo baby"),
    ("Meryl Streep", "1949", "Not a nepo baby"),
    ("Natalie Portman", "1981", "Not a nepo baby"),
    ("Reese Witherspoon", "1976", "Not a nepo baby"),
    ("Jessica Chastain", "1977", "Not a nepo baby"),
    ("Emma Stone", "1988", "Not a nepo baby"),
    ("Viola Davis", "1965", "Not a nepo baby"),
]


def run():
    results = []
    for name, year, truth in BENCHMARK:
        r = classify(name, year)
        results.append((name, truth, r["status"], r["tiers_run"], r["evidence"]))
        print("  %-20s truth=%-16s got=%-16s tiers=%s"
              % (name, truth, r["status"], "+".join(r["tiers_run"])))
        time.sleep(1.0)      # pace requests — Wikipedia rate-limits rapid lookups

    n = len(results)
    correct_yes = sum(1 for _, t, g, _, _ in results if t == "Yes" and g == "Yes")
    total_yes = sum(1 for _, t, _, _, _ in results if t == "Yes")
    false_positives = sum(1 for _, t, g, _, _ in results if t == "Not a nepo baby" and g == "Yes")
    total_negative = sum(1 for _, t, _, _, _ in results if t == "Not a nepo baby")
    unknowns = sum(1 for _, _, g, _, _ in results if g == "Unknown")

    print("\n--- %d-case benchmark ---" % n)
    print("  recall on confirmed positives : %d/%d (%.0f%%)"
          % (correct_yes, total_yes, 100 * correct_yes / total_yes))
    print("  FALSE POSITIVES (negative case wrongly called Yes): %d/%d"
          % (false_positives, total_negative))
    print("  Unknown (neither tier could confirm or rule out)  : %d/%d" % (unknowns, n))
    return results


if __name__ == "__main__":
    run()

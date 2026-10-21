"""
Unit tests for the merge logic in classify.py — tiers are mocked so
these run deterministically with no live network call. The tier
MODULES (wikipedia.py, wikidata.py) are tested separately, against real
public figures, in benchmark.py — that one needs the network on purpose.
"""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))

import classify


class TestTierOrdering(unittest.TestCase):
    def test_a_confirmed_yes_from_tier1_skips_tier2_entirely(self):
        """Tier 1 is the most trusted source — a confirmed result from
        it must not be second-guessed by a lower-priority tier."""
        with patch("tiers.wikipedia.check", return_value=("Yes", {"parent": "X"})), \
             patch("tiers.wikidata.check") as mock_wd:
            result = classify.classify("Test Actor")
            mock_wd.assert_not_called()
            self.assertEqual(result["status"], "Yes")
            self.assertEqual(result["tiers_run"], ["wikipedia"])

    def test_a_confirmed_negative_from_tier1_also_skips_tier2(self):
        """"Not a nepo baby" is as final as "Yes" — Tier 1 ruling someone
        out is not revisited just because Tier 2 is available."""
        with patch("tiers.wikipedia.check", return_value=("Not a nepo baby", {})), \
             patch("tiers.wikidata.check") as mock_wd:
            result = classify.classify("Test Actor")
            mock_wd.assert_not_called()
            self.assertEqual(result["status"], "Not a nepo baby")

    def test_inconclusive_tier1_falls_through_to_tier2(self):
        with patch("tiers.wikipedia.check", return_value=("Inconclusive", {})), \
             patch("tiers.wikidata.check", return_value=("Yes", {"parent": "X"})):
            result = classify.classify("Test Actor")
            self.assertEqual(result["status"], "Yes")
            self.assertEqual(result["tiers_run"], ["wikipedia", "wikidata"])

    def test_both_tiers_inconclusive_with_no_optional_keys_gives_honest_unknown(self):
        """No ANTHROPIC_API_KEY or TMDB_API_KEY configured in this test's
        environment -> the optional tiers must not even be attempted,
        and the result must be "Unknown", never a guess."""
        with patch("tiers.wikipedia.check", return_value=("Inconclusive", {})), \
             patch("tiers.wikidata.check", return_value=("Inconclusive", {})), \
             patch.dict(os.environ, {}, clear=True):
            result = classify.classify("Test Actor")
            self.assertEqual(result["status"], "Unknown")
            self.assertEqual(result["tiers_run"], ["wikipedia", "wikidata"])


class TestWikidataLabelRepair(unittest.TestCase):
    def test_detects_a_bare_qid_masquerading_as_a_label(self):
        from tiers.wikidata import looks_like_a_bare_qid
        self.assertTrue(looks_like_a_bare_qid("Q188459", "Q188459"))
        self.assertTrue(looks_like_a_bare_qid("", "Q188459"))

    def test_a_real_label_is_not_flagged(self):
        from tiers.wikidata import looks_like_a_bare_qid
        self.assertFalse(looks_like_a_bare_qid("Goldie Hawn", "Q188459"))


if __name__ == "__main__":
    unittest.main()

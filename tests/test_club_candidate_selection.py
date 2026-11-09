import unittest
from app.services.club_candidate_selection import select_candidate


class CandidateSelectionTests(unittest.TestCase):
    def setUp(self):
        self.a = {"clubhead_candidate": [100, 100]}
        self.b = {"clubhead_candidate": [160, 160]}

    def test_requires_reference(self):
        self.assertEqual(select_candidate([self.a], [10, 10])["status"],
                         "needs_verified_reference")

    def test_unique_match_is_still_unverified(self):
        result = select_candidate([self.a, self.b], [10, 10], [102, 101])
        self.assertEqual(result["status"], "candidate_matches_reference")
        self.assertFalse(result["verified"])

    def test_ambiguity_abstains(self):
        result = select_candidate(
            [self.a, {"clubhead_candidate": [104, 103]}], [10, 10], [102, 101])
        self.assertEqual(result["status"], "ambiguous_candidates")

    def test_wrong_head_abstains(self):
        self.assertEqual(select_candidate([self.a], [10, 10], [200, 200])["status"],
                         "no_matching_candidate")

    def test_invalid_reference(self):
        with self.assertRaises(ValueError):
            select_candidate([self.a], [10, 10], [10, 10])

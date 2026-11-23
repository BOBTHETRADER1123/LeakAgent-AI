import unittest
from detection import analyze_rows

class DetectionTests(unittest.TestCase):
    def row(self, cycle, down):
        return {"branch_id":"A", "cycle_id":cycle, "q_up_l_s":12.5, "q_down_l_s":down,
                "pipe_storage_change_l_s":0, "branch_tap_l_s":0,
                "meter_up_sigma_l_s":0.3, "meter_down_sigma_l_s":0.3,
                "full_pipe_flag":"true", "stable_window_verified":"true"}

    def test_repeated_large_imbalance_flags_branch(self):
        result = analyze_rows([self.row("1",10.2), self.row("2",10.1)])
        self.assertEqual(result["overall_status"], "POSSIBLE LEAK SIGNAL FOUND")
        self.assertIn("POSSIBLE LEAK", result["branches"][0]["status"])

    def test_small_imbalance_does_not_flag(self):
        result = analyze_rows([self.row("1",12.4), self.row("2",12.3)])
        self.assertEqual(result["overall_status"], "NO QUALIFYING LEAK SIGNAL FOUND")

    def test_unverified_window_is_ineligible(self):
        row = self.row("1",10.0)
        row["stable_window_verified"] = "false"
        result = analyze_rows([row])
        self.assertEqual(result["eligible_rows"], 0)

if __name__ == '__main__':
    unittest.main()

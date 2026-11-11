import unittest

from oci_compute_idle_recommender.idle import analyze_fleet


def series(cpu, net, days=10):
    return [{"date": f"2026-11-{d+1:02d}", "cpu_pct": cpu, "net_mbps": net} for d in range(days)]


def inst(name, cpu, net, ocpus=2, days=10, state="RUNNING", tags=None):
    return {"name": name, "ocpus": ocpus, "lifecycle_state": state,
            "metrics": series(cpu, net, days), "tags": tags or {}}


def ids(findings):
    return {f.rule_id for f in findings}


class TestIdle(unittest.TestCase):
    def test_idle001_clear_stop_candidate(self):
        findings = analyze_fleet({"instances": [inst("box", 1.0, 0.1, ocpus=4)]})
        idle001 = [f for f in findings if f.rule_id == "IDLE001"]
        self.assertEqual(len(idle001), 1)
        self.assertEqual(idle001[0].severity, "HIGH")
        self.assertIn("$73.00", idle001[0].message)  # 4 * 0.025 * 730

    def test_idle001_not_for_busy_instance(self):
        self.assertNotIn("IDLE001", ids(analyze_fleet({"instances": [inst("box", 40.0, 5.0)]})))

    def test_idle001_requires_low_network_too(self):
        self.assertNotIn("IDLE001", ids(analyze_fleet({"instances": [inst("box", 1.0, 5.0)]})))

    def test_idle002_downsize_band(self):
        findings = analyze_fleet({"instances": [inst("box", 12.0, 2.0, ocpus=8)]})
        idle002 = [f for f in findings if f.rule_id == "IDLE002"]
        self.assertEqual(len(idle002), 1)
        self.assertIn("8 -> 4", idle002[0].message)

    def test_idle002_suggests_at_least_one_ocpu(self):
        findings = analyze_fleet({"instances": [inst("box", 12.0, 2.0, ocpus=1)]})
        self.assertIn("1 -> 1", [f for f in findings if f.rule_id == "IDLE002"][0].message)

    def test_idle003_insufficient_data(self):
        findings = analyze_fleet({"instances": [inst("box", 1.0, 0.1, days=3)]})
        self.assertIn("IDLE003", ids(findings))
        self.assertNotIn("IDLE001", ids(findings))

    def test_idle004_missing_schedule_tag_only_on_stop_candidate(self):
        findings = analyze_fleet({"instances": [inst("box", 1.0, 0.1)]})
        self.assertIn("IDLE004", ids(findings))
        findings = analyze_fleet({"instances": [inst("box", 1.0, 0.1, tags={"schedule": "nightly"})]})
        self.assertNotIn("IDLE004", ids(findings))

    def test_stopped_instance_skipped(self):
        self.assertEqual(analyze_fleet({"instances": [inst("box", 1.0, 0.1, state="STOPPED")]}), [])

    def test_findings_sorted_high_first(self):
        findings = analyze_fleet({"instances": [
            inst("short", 1.0, 0.1, days=2), inst("idle", 1.0, 0.1)]})
        self.assertEqual(findings[0].severity, "HIGH")
        self.assertEqual(findings[-1].severity, "LOW")

    def test_missing_instances_list_rejected(self):
        with self.assertRaises(ValueError):
            analyze_fleet({"items": []})

    def test_instance_missing_name_rejected(self):
        with self.assertRaises(ValueError):
            analyze_fleet({"instances": [{"ocpus": 1, "metrics": []}]})


if __name__ == "__main__":
    unittest.main()

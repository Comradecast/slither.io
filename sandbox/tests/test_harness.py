import json
import tempfile
import unittest
from pathlib import Path

from sandbox.tools.validate_scenarios import ScenarioRunner, build_scenarios, run_all_scenarios


EXPECTED_SCENARIOS = [
    "large_snake_near_enemy_body",
    "large_snake_near_boundary_wall_facing",
    "large_snake_near_boundary_escape_heading",
    "enemy_head_intercept_crossing",
    "enemy_head_projection_non_crossing",
    "food_near_threat",
    "safe_food_path",
    "loot_cluster_safe_preferred",
    "loot_cluster_unsafe_rejected",
    "normal_food_without_cluster",
    "boost_safe_clear_path",
    "boost_blocked_near_boundary",
    "boost_blocked_enemy_intercept",
    "boost_blocked_sharp_turn",
    "telemetry_projected_collision_001",
    "telemetry_enemy_intercept_001",
]


def test_harness_writes_jsonl_report(tmp_path):
    results = run_all_scenarios(reports_dir=tmp_path)
    report_path = tmp_path / "harness_results.jsonl"

    assert [result["scenario"] for result in results] == EXPECTED_SCENARIOS
    assert report_path.exists()

    lines = report_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(EXPECTED_SCENARIOS)

    for line, scenario_name in zip(lines, EXPECTED_SCENARIOS):
        data = json.loads(line)
        assert data["scenario"] == scenario_name
        assert "perception" in data
        assert "strategy" in data
        assert "steering" in data
        assert "gate" in data
        assert "controller" in data
        assert data["passed"] is True
        assert "selected_heading" in data
        assert "boost" in data
        assert "requested_boost" in data
        assert "final_boost" in data
        assert "boost_allowed" in data
        assert "boost_reason" in data
        assert "was_overridden" in data
        assert "reason" in data
        assert "collision_risk" in data
        assert "enemy_head_intercept_risk" in data
        assert "boundary_forward_distance" in data
        assert "enemy_head_intercept_time" in data
        assert "enemy_head_intercept_distance" in data
        assert "my_radius" in data
        assert "my_mass" in data
        assert "loot_cluster_score" in data
        assert "loot_cluster_total_value" in data
        assert "loot_cluster_pellet_count" in data
        assert "loot_cluster_target_x" in data
        assert "loot_cluster_target_y" in data


def test_runner_can_append_without_resetting_report(tmp_path):
    runner = ScenarioRunner(reports_dir=tmp_path)
    scenario = next(iter(build_scenarios()))
    runner.run_scenario(scenario)

    appending_runner = ScenarioRunner(reports_dir=tmp_path, reset_report=False)
    appending_runner.run_scenario(scenario)

    lines = (tmp_path / "harness_results.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2


class TestHarnessUnittestDiscovery(unittest.TestCase):
    def test_harness_writes_jsonl_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            results = run_all_scenarios(reports_dir=report_dir)
            report_path = report_dir / "harness_results.jsonl"

            self.assertEqual([result["scenario"] for result in results], EXPECTED_SCENARIOS)
            self.assertTrue(all(result["passed"] for result in results))
            self.assertTrue(report_path.exists())
            self.assertEqual(
                len(report_path.read_text(encoding="utf-8").splitlines()),
                len(EXPECTED_SCENARIOS),
            )

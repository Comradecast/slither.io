import json
from pathlib import Path

from sandbox.tools.validate_scenarios import (
    PROMOTED_TELEMETRY_SCENARIOS_PATH,
    ScenarioRunner,
    build_promoted_telemetry_scenarios,
)


REQUIRED_FIELDS = {
    "name",
    "source_line",
    "candidate_type",
    "my_mass",
    "my_radius",
    "my_position",
    "my_heading",
    "requested_heading",
    "expected_override",
    "expected_gate_reason",
    "notes",
    "my_snake",
    "snakes",
    "foods",
}


def _fixture_records():
    path = Path(PROMOTED_TELEMETRY_SCENARIOS_PATH)
    return json.loads(path.read_text(encoding="utf-8"))


def test_promoted_fixture_file_exists():
    assert Path(PROMOTED_TELEMETRY_SCENARIOS_PATH).exists()


def test_promoted_records_have_required_fields():
    records = _fixture_records()

    assert records
    for record in records:
        assert REQUIRED_FIELDS.issubset(record)


def test_promoted_scenario_names_are_unique():
    records = _fixture_records()
    names = [record["name"] for record in records]

    assert len(names) == len(set(names))


def test_promoted_scenarios_load_deterministically():
    first = list(build_promoted_telemetry_scenarios())
    second = list(build_promoted_telemetry_scenarios())

    assert [scenario.name for scenario in first] == [
        "telemetry_projected_collision_001",
        "telemetry_enemy_intercept_001",
    ]
    assert [scenario.name for scenario in first] == [scenario.name for scenario in second]


def test_promoted_scenarios_run_through_strategy_and_safety_gate(tmp_path):
    runner = ScenarioRunner(reports_dir=tmp_path)
    results = [
        runner.run_scenario(scenario)
        for scenario in build_promoted_telemetry_scenarios()
    ]

    assert [result["scenario"] for result in results] == [
        "telemetry_projected_collision_001",
        "telemetry_enemy_intercept_001",
    ]
    assert all(result["passed"] is True for result in results)
    assert results[0]["was_overridden"] is True
    assert results[0]["reason"] == "projected_collision"
    assert results[0]["collision_risk"] > 0.5
    assert results[1]["was_overridden"] is True
    assert results[1]["reason"] == "enemy_head_intercept"
    assert results[1]["enemy_head_intercept_risk"] > 1.5


def test_missing_promoted_fixture_returns_no_scenarios(tmp_path):
    missing_fixture = tmp_path / "missing.json"

    assert list(build_promoted_telemetry_scenarios(missing_fixture)) == []

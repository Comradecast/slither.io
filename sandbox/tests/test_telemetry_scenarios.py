import json
import math

from sandbox.config import Config
from sandbox.tools.extract_telemetry_scenarios import (
    REQUIRED_FIELDS,
    candidate_from_row,
    extract_candidates,
)


def _row(my_snake, snakes=None, foods=None, action=None):
    return {
        "timestamp": 123.0,
        "raw_data": {
            "my_snake": my_snake,
            "snakes": snakes or [],
            "foods": foods or [],
        },
        "action": action or {"target_angle": 0.0, "boost": False},
    }


def test_missing_file_exits_cleanly(tmp_path):
    missing = tmp_path / "missing.jsonl"
    output = tmp_path / "out.jsonl"

    stats = extract_candidates(input_path=missing, output_path=output)

    assert stats.scanned == 0
    assert stats.written == 0
    assert "not found" in stats.message
    assert not output.exists()


def test_malformed_line_is_skipped_and_counted(tmp_path):
    source = tmp_path / "telemetry.jsonl"
    output = tmp_path / "out.jsonl"
    valid = _row(
        {"id": 1, "x": 0, "y": 0, "angle": 0.0, "mass": 10},
        foods=[{"x": 20, "y": 0, "value": 1.0}],
    )
    source.write_text("{bad json\n" + json.dumps(valid) + "\n", encoding="utf-8")

    stats = extract_candidates(input_path=source, output_path=output, scan_limit=10, stride=1)

    assert stats.malformed == 1
    assert stats.written == 1


def test_candidate_extraction_detects_enemy_intercept_style_record():
    row = _row(
        {"id": 1, "x": 0, "y": 0, "angle": 0.0, "mass": 10},
        snakes=[
            {
                "id": 2,
                "x": 75,
                "y": 80,
                "angle": -math.pi / 2,
                "wang": -math.pi / 2,
                "mass": 100,
                "trail": [],
            }
        ],
        action={"target_angle": 0.0, "boost": False},
    )

    candidate = candidate_from_row(row, 7)

    assert candidate["candidate_type"] == "enemy_intercept"
    assert candidate["gate_reason"] == "enemy_head_intercept"
    assert candidate["enemy_head_intercept_risk"] > 1.5
    assert candidate["usable_for_harness"] is True


def test_candidate_extraction_detects_boundary_style_record():
    row = _row(
        {
            "id": 1,
            "x": Config.WORLD_RADIUS - 60,
            "y": 0,
            "angle": 0.0,
            "mass": 5000,
        },
        action={"target_angle": 0.0, "boost": True},
    )

    candidate = candidate_from_row(row, 8)

    assert candidate["candidate_type"] == "boundary_risk"
    assert candidate["gate_reason"] == "boundary_too_close"
    assert candidate["was_overridden"] is True
    assert candidate["usable_for_harness"] is True


def test_incomplete_records_are_not_usable_for_harness():
    candidate = candidate_from_row({"raw_data": {}, "action": {}}, 9)

    assert candidate["candidate_type"] == "unknown_insufficient_data"
    assert candidate["usable_for_harness"] is False
    assert "raw_data.my_snake" in candidate["missing_fields"]
    assert "action.target_angle" in candidate["missing_fields"]


def test_output_records_include_required_top_level_fields(tmp_path):
    source = tmp_path / "telemetry.jsonl"
    output = tmp_path / "out.jsonl"
    row = _row(
        {"id": 1, "x": Config.WORLD_RADIUS - 60, "y": 0, "angle": 0.0, "mass": 5000},
        action={"target_angle": 0.0, "boost": False},
    )
    source.write_text(json.dumps(row) + "\n", encoding="utf-8")

    stats = extract_candidates(input_path=source, output_path=output, scan_limit=10)
    record = json.loads(output.read_text(encoding="utf-8").splitlines()[0])

    assert stats.written == 1
    for field_name in REQUIRED_FIELDS:
        assert field_name in record

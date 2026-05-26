import json

from sandbox.tools.controlled_live_baseline import (
    recommended_next_focus,
    run_controlled_baseline,
    safe_label,
)
from sandbox.tools.live_evaluation_runner import analyze_live_telemetry


def _row(
    snake_id=1,
    timestamp=1.0,
    mass=10.0,
    x=1000.0,
    y=1000.0,
    action_angle=0.0,
    snakes=None,
):
    return {
        "timestamp": timestamp,
        "raw_data": {
            "my_snake": {
                "id": snake_id,
                "x": x,
                "y": y,
                "angle": 0.0,
                "wang": 0.0,
                "mass": mass,
                "trail": [{"x": x - 20.0, "y": y}],
            },
            "snakes": snakes or [],
            "foods": [],
            "map_radius": 3000.0,
        },
        "action": {"target_angle": action_angle, "boost": False},
    }


def _write_jsonl(path, rows):
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_safe_label_is_deterministic_and_path_safe():
    assert safe_label(" v0.24 sample ") == "v0.24_sample"
    assert safe_label("../../escape") == "escape"
    assert safe_label("!!!") == "live_baseline"


def test_missing_input_is_handled_cleanly(tmp_path):
    aggregate = run_controlled_baseline(
        inputs=[tmp_path / "missing.jsonl"],
        label="missing",
        output_dir=tmp_path / "reports",
    )

    run = aggregate["runs"][0]
    assert run["total_frames"] == 0
    assert run["session_count"] == 0
    assert run["recommended_next_focus"] == "continue controlled live comparison"


def test_one_fixture_run_writes_summary_and_aggregate(tmp_path):
    source = tmp_path / "telemetry.jsonl"
    output_dir = tmp_path / "reports"
    _write_jsonl(source, [_row(timestamp=1.0, mass=10.0), _row(timestamp=2.0, mass=15.0)])

    aggregate = run_controlled_baseline(
        inputs=[source],
        label="fixture",
        output_dir=output_dir,
    )

    assert aggregate["run_count"] == 1
    assert (output_dir / "fixture_summary.json").exists()
    assert (output_dir / "fixture_frames.jsonl").exists()
    assert (output_dir / "aggregate_summary.json").exists()
    assert aggregate["runs"][0]["peak_mass"] == 15.0


def test_aggregate_summary_is_deterministic(tmp_path):
    source = tmp_path / "telemetry.jsonl"
    output_dir = tmp_path / "reports"
    _write_jsonl(source, [_row(timestamp=1.0, mass=10.0), _row(timestamp=2.0, mass=20.0)])

    first = run_controlled_baseline(inputs=[source], label="det", output_dir=output_dir)
    second = run_controlled_baseline(inputs=[source], label="det", output_dir=output_dir)

    assert first == second


def test_baseline_comparison_propagates_through(tmp_path):
    source = tmp_path / "telemetry.jsonl"
    baseline = tmp_path / "baseline.json"
    _write_jsonl(source, [_row(timestamp=1.0, mass=10.0), _row(timestamp=2.0, mass=25.0)])
    baseline.write_text(json.dumps({
        "explicit_death_count": 0,
        "inferred_session_end_count": 0,
        "mass": {"peak_mass": 15.0},
        "override_count": 0,
        "override_rate": 0.0,
        "total_frames": 1,
    }), encoding="utf-8")

    aggregate = run_controlled_baseline(
        inputs=[source],
        label="compare",
        output_dir=tmp_path / "reports",
        baseline=baseline,
    )

    assert aggregate["runs"][0]["comparison"]["total_frames_delta"] == 1
    assert aggregate["runs"][0]["comparison"]["peak_mass_delta"] == 10.0


def test_recommended_next_focus_is_stable_for_known_patterns(tmp_path):
    source = tmp_path / "telemetry.jsonl"
    enemy = {
        "id": 2,
        "x": 1050.0,
        "y": 1000.0,
        "angle": 0.0,
        "wang": 0.0,
        "mass": 100.0,
        "trail": [{"x": 1050.0, "y": 1000.0}],
    }
    _write_jsonl(source, [
        _row(timestamp=1.0, snakes=[enemy]),
        _row(timestamp=2.0, snakes=[enemy]),
    ])
    summary = analyze_live_telemetry(
        input_path=source,
        output_path=tmp_path / "summary.json",
        frames_output_path=None,
    )

    assert recommended_next_focus(summary) == "perception/threat corridor tuning"


def test_generated_output_stays_under_requested_output_directory(tmp_path):
    source = tmp_path / "telemetry.jsonl"
    output_dir = tmp_path / "reports"
    _write_jsonl(source, [_row(timestamp=1.0)])

    aggregate = run_controlled_baseline(
        inputs=[source],
        label="../escape",
        output_dir=output_dir,
    )

    run = aggregate["runs"][0]
    assert run["summary_path"].startswith(str(output_dir))
    assert run["frames_path"].startswith(str(output_dir))
    assert (output_dir / "escape_summary.json").exists()

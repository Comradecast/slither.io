import json

from sandbox.tools.live_evaluation_runner import analyze_live_telemetry


def _row(
    snake_id=1,
    timestamp=1.0,
    mass=10.0,
    x=1000.0,
    y=1000.0,
    angle=0.0,
    action_angle=0.0,
    action_boost=False,
    snakes=None,
    foods=None,
    alive=True,
):
    return {
        "timestamp": timestamp,
        "raw_data": {
            "my_snake": {
                "id": snake_id,
                "x": x,
                "y": y,
                "angle": angle,
                "wang": angle,
                "mass": mass,
                "alive": alive,
                "trail": [{"x": x - 20.0, "y": y}],
            },
            "snakes": snakes or [],
            "foods": foods or [],
            "map_radius": 3000.0,
        },
        "action": {
            "target_angle": action_angle,
            "boost": action_boost,
        },
    }


def _write_jsonl(path, rows):
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) if isinstance(row, dict) else row for row in rows) + "\n",
        encoding="utf-8",
    )


def test_live_evaluation_handles_missing_file(tmp_path):
    summary = analyze_live_telemetry(
        input_path=tmp_path / "missing.jsonl",
        output_path=tmp_path / "summary.json",
        frames_output_path=None,
    )

    assert summary.total_frames == 0
    assert summary.session_count == 0
    assert "not found" in summary.stats.message


def test_live_evaluation_summarizes_mass_and_survival_metrics(tmp_path):
    source = tmp_path / "telemetry.jsonl"
    output = tmp_path / "summary.json"
    _write_jsonl(source, [
        _row(timestamp=1.0, mass=10.0),
        _row(timestamp=2.0, mass=15.0),
        _row(timestamp=3.0, mass=12.0),
    ])

    summary = analyze_live_telemetry(
        input_path=source,
        output_path=output,
        frames_output_path=tmp_path / "frames.jsonl",
    )

    assert summary.total_frames == 3
    assert summary.session_count == 1
    assert summary.survived_session_count == 1
    assert summary.mass["start_mass"] == 10.0
    assert summary.mass["final_mass"] == 12.0
    assert summary.mass["peak_mass"] == 15.0
    assert output.exists()


def test_live_evaluation_splits_sessions_by_snake_id_and_timestamp_gap(tmp_path):
    source = tmp_path / "telemetry.jsonl"
    _write_jsonl(source, [
        _row(snake_id=1, timestamp=1.0),
        _row(snake_id=1, timestamp=20.0),
        _row(snake_id=2, timestamp=21.0),
    ])

    summary = analyze_live_telemetry(
        input_path=source,
        output_path=tmp_path / "summary.json",
        frames_output_path=None,
        session_gap_seconds=5.0,
    )

    assert summary.session_count == 3
    assert summary.inferred_session_end_count == 2
    assert [session.inferred_end_reason for session in summary.sessions] == [
        "timestamp_gap",
        "snake_id_changed",
        "eof",
    ]


def test_live_evaluation_counts_malformed_and_skipped_rows(tmp_path):
    source = tmp_path / "telemetry.jsonl"
    _write_jsonl(source, [
        "{not json",
        {"timestamp": 1.0, "raw_data": {}, "action": {}},
        _row(timestamp=2.0),
    ])

    summary = analyze_live_telemetry(
        input_path=source,
        output_path=tmp_path / "summary.json",
        frames_output_path=None,
    )

    assert summary.stats.malformed == 1
    assert summary.stats.skipped == 1
    assert summary.total_frames == 1


def test_live_evaluation_counts_safety_override_reasons(tmp_path):
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
        _row(timestamp=1.0, snakes=[enemy], action_angle=0.0),
    ])

    summary = analyze_live_telemetry(
        input_path=source,
        output_path=tmp_path / "summary.json",
        frames_output_path=tmp_path / "frames.jsonl",
    )

    assert summary.override_count >= 1
    assert summary.aggregate_gate_reasons["projected_collision"] >= 1
    frame = json.loads((tmp_path / "frames.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert frame["was_overridden"] is True
    assert frame["gate_reason"] == "projected_collision"


def test_live_evaluation_baseline_comparison_is_deterministic(tmp_path):
    source = tmp_path / "telemetry.jsonl"
    current = tmp_path / "current.json"
    baseline = tmp_path / "baseline.json"
    _write_jsonl(source, [_row(timestamp=1.0, mass=10.0), _row(timestamp=2.0, mass=20.0)])
    baseline.write_text(json.dumps({
        "explicit_death_count": 0,
        "inferred_session_end_count": 0,
        "mass": {"peak_mass": 15.0},
        "override_count": 0,
        "override_rate": 0.0,
        "total_frames": 1,
    }), encoding="utf-8")

    summary = analyze_live_telemetry(
        input_path=source,
        output_path=current,
        frames_output_path=None,
        baseline_path=baseline,
    )

    assert summary.comparison["baseline"] == str(baseline)
    assert summary.comparison["total_frames_delta"] == 1
    assert summary.comparison["peak_mass_delta"] == 5.0


def test_live_evaluation_malformed_baseline_does_not_fail(tmp_path):
    source = tmp_path / "telemetry.jsonl"
    baseline = tmp_path / "baseline.json"
    _write_jsonl(source, [_row(timestamp=1.0, mass=10.0)])
    baseline.write_text("{not json", encoding="utf-8")

    summary = analyze_live_telemetry(
        input_path=source,
        output_path=tmp_path / "summary.json",
        frames_output_path=None,
        baseline_path=baseline,
    )

    assert summary.comparison == {
        "baseline": str(baseline),
        "error": "baseline_unreadable",
    }


def test_live_evaluation_invalid_baseline_values_do_not_fail(tmp_path):
    source = tmp_path / "telemetry.jsonl"
    baseline = tmp_path / "baseline.json"
    _write_jsonl(source, [_row(timestamp=1.0, mass=10.0)])
    baseline.write_text(json.dumps({
        "mass": {"peak_mass": "bad"},
        "override_count": "abc",
    }), encoding="utf-8")

    summary = analyze_live_telemetry(
        input_path=source,
        output_path=tmp_path / "summary.json",
        frames_output_path=None,
        baseline_path=baseline,
    )

    assert summary.comparison == {
        "baseline": str(baseline),
        "error": "baseline_invalid_values",
    }


def test_live_evaluation_invalid_baseline_mass_shape_does_not_fail(tmp_path):
    source = tmp_path / "telemetry.jsonl"
    baseline = tmp_path / "baseline.json"
    _write_jsonl(source, [_row(timestamp=1.0, mass=10.0)])
    baseline.write_text(json.dumps({"mass": "not-a-dict"}), encoding="utf-8")

    summary = analyze_live_telemetry(
        input_path=source,
        output_path=tmp_path / "summary.json",
        frames_output_path=None,
        baseline_path=baseline,
    )

    assert summary.comparison == {
        "baseline": str(baseline),
        "error": "baseline_invalid_shape",
    }

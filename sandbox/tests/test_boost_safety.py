import json
import math

import pytest

from sandbox.bot.perception import Perception
from sandbox.bot.safety_gate import SafetyGate, is_boost_safe
from sandbox.bot.strategy import Strategy
from sandbox.config import Config
from sandbox.snake import Snake
from sandbox.tools.validate_scenarios import ScenarioRunner, build_scenarios


def _state(my_snake, snakes=None, vision_radius=Config.AI_VISION_RADIUS):
    return Perception(vision_radius=vision_radius).build(
        my_snake,
        snakes if snakes is not None else [my_snake],
        [],
    )


def _eval_heading(state, requested_angle):
    min_turn_radius = state.my_radius * 2.0 + (state.my_mass / 100.0)
    result = Strategy()._evaluate_heading(
        requested_angle,
        math.cos(requested_angle),
        math.sin(requested_angle),
        state,
        min_turn_radius,
    )
    return result, min_turn_radius


def test_safe_clear_path_preserves_requested_boost():
    snake = Snake(1, 0, 0, 0)
    snake.mass = 100
    snake.recompute_segments()
    state = _state(snake)

    safe_angle, safe_boost, overridden, reason = SafetyGate().filter_action(
        state,
        0.0,
        True,
    )

    assert safe_angle == pytest.approx(0.0)
    assert safe_boost is True
    assert overridden is False
    assert reason == "none"


def test_safety_gate_override_disables_boost():
    snake = Snake(1, Config.WORLD_RADIUS - 60, 0, 0)
    snake.mass = 5000
    snake.recompute_segments()
    state = _state(snake, vision_radius=100)

    _, safe_boost, overridden, reason = SafetyGate().filter_action(state, 0.0, True)

    assert safe_boost is False
    assert overridden is True
    assert reason == "boundary_too_close"


def test_boost_disabled_near_boundary_without_heading_override():
    snake = Snake(1, Config.WORLD_RADIUS - 100, 0, 0)
    snake.mass = 5000
    snake.recompute_segments()
    state = _state(snake, vision_radius=100)

    safe_angle, safe_boost, overridden, reason = SafetyGate().filter_action(
        state,
        0.0,
        True,
    )

    assert safe_angle == pytest.approx(0.0)
    assert safe_boost is False
    assert overridden is False
    assert reason == "boost_boundary_too_close"


def test_boost_disabled_for_projected_enemy_intercept():
    snake = Snake(1, 0, 0, 0)
    snake.angle = math.pi / 2
    snake.mass = 100
    enemy = Snake(2, 75, 80, -math.pi / 2)
    enemy.speed = Config.BASE_SPEED
    enemy.segments = []
    state = _state(snake, [snake, enemy], vision_radius=200)

    _, safe_boost, overridden, reason = SafetyGate().filter_action(state, 0.0, True)

    assert safe_boost is False
    assert overridden is True
    assert reason == "enemy_head_intercept"


def test_boost_disabled_for_sharp_turn():
    snake = Snake(1, 0, 0, 0)
    snake.mass = 100
    snake.recompute_segments()
    state = _state(snake)

    safe_angle, safe_boost, overridden, reason = SafetyGate().filter_action(
        state,
        math.pi / 2,
        True,
    )

    assert safe_angle == pytest.approx(math.pi / 2)
    assert safe_boost is False
    assert overridden is False
    assert reason == "boost_turn_too_sharp"


def test_boost_safety_result_is_deterministic():
    snake = Snake(1, 0, 0, 0)
    snake.mass = 100
    snake.recompute_segments()
    state = _state(snake)
    eval_result, min_turn_radius = _eval_heading(state, math.pi / 2)

    first = is_boost_safe(state, math.pi / 2, eval_result, min_turn_radius)
    second = is_boost_safe(state, math.pi / 2, eval_result, min_turn_radius)

    assert first == second
    assert first.allowed is False
    assert first.reason == "boost_turn_too_sharp"


def test_harness_records_include_boost_fields(tmp_path):
    scenario = next(
        scenario
        for scenario in build_scenarios()
        if scenario.name == "boost_safe_clear_path"
    )
    result = ScenarioRunner(reports_dir=tmp_path).run_scenario(scenario)
    report_line = (tmp_path / "harness_results.jsonl").read_text(encoding="utf-8")
    report_record = json.loads(report_line)

    for record in (result, report_record):
        assert record["requested_boost"] is True
        assert record["final_boost"] is True
        assert record["boost_allowed"] is True
        assert record["boost_reason"] == "none"
        assert record["gate"]["requested_boost"] is True
        assert record["gate"]["final_boost"] is True
        assert record["gate"]["boost_allowed"] is True
        assert record["gate"]["boost_reason"] == "none"


def test_promoted_telemetry_scenarios_still_pass(tmp_path):
    runner = ScenarioRunner(reports_dir=tmp_path)
    promoted = [
        scenario
        for scenario in build_scenarios()
        if scenario.name.startswith("telemetry_")
    ]

    assert promoted
    assert all(runner.run_scenario(scenario)["passed"] for scenario in promoted)

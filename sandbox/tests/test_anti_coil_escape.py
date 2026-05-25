import math

import pytest

from sandbox.bot.perception import Perception
from sandbox.bot.safety_gate import SafetyGate
from sandbox.bot.strategy import Strategy, StrategyMode
from sandbox.config import Config
from sandbox.snake import Snake
from sandbox.tools.validate_scenarios import build_scenarios
from sandbox.vector import Vector2


def _state(my_snake, enemies=None, vision_radius=400):
    snakes = [my_snake, *(enemies or [])]
    return Perception(vision_radius=vision_radius).build(my_snake, snakes, [])


def _surrounding_enemy(enemy_id=2):
    enemy = Snake(enemy_id, -90, 0, 0)
    enemy.segments = [
        Vector2(-90, 0),
        Vector2(-90, 55),
        Vector2(-55, 90),
        Vector2(0, 90),
        Vector2(55, 90),
        Vector2(-90, -55),
        Vector2(-55, -90),
        Vector2(0, -90),
        Vector2(55, -90),
    ]
    return enemy


def test_compression_detector_is_deterministic():
    snake = Snake(1, 0, 0, 0)
    state = _state(snake, [_surrounding_enemy()])

    first = Strategy.analyze_compression(state)
    second = Strategy.analyze_compression(state)

    assert first == second
    assert first.active is True


def test_sector_count_increases_when_threats_surround_bot():
    snake = Snake(1, 0, 0, 0)
    narrow_enemy = Snake(2, 60, 0, 0)
    narrow_enemy.segments = [Vector2(60, 0), Vector2(75, 12)]
    surrounded = Strategy.analyze_compression(_state(snake, [_surrounding_enemy()]))
    narrow = Strategy.analyze_compression(_state(snake, [narrow_enemy]))

    assert surrounded.sector_count > narrow.sector_count
    assert surrounded.nearby_threat_count > narrow.nearby_threat_count


def test_open_space_case_does_not_trigger_false_positive():
    snake = Snake(1, 0, 0, 0)
    enemy = Snake(2, 60, 0, 0)
    enemy.segments = [Vector2(60, 0), Vector2(75, 12)]
    state = _state(snake, [enemy])

    analysis = Strategy.analyze_compression(state)
    result = Strategy().decide(state)

    assert analysis.active is False
    assert result.anti_coil_escape_active is False
    assert result.mode == StrategyMode.AVOID_THREAT
    assert result.defensive_reason == "Forward danger"


def test_escape_heading_points_toward_clear_gap():
    snake = Snake(1, 0, 0, 0)
    state = _state(snake, [_surrounding_enemy()])
    strategy = Strategy()

    plan = strategy.select_anti_coil_escape(state)
    result = strategy.decide(state)

    assert plan is not None
    assert plan.heading == pytest.approx(0.0)
    assert result.anti_coil_escape_active is True
    assert result.best_escape_heading == pytest.approx(0.0)
    assert result.target_pos.x > 0
    assert result.target_pos.y == pytest.approx(0.0)


def test_unsafe_projected_gap_is_rejected():
    snake = Snake(1, 0, 0, 0)
    closing_head = Snake(3, 75, 80, -math.pi / 2)
    closing_head.speed = Config.BASE_SPEED
    closing_head.segments = []
    state = _state(snake, [_surrounding_enemy(), closing_head])

    plan = Strategy().select_anti_coil_escape(state)

    assert plan is not None
    assert plan.heading != pytest.approx(0.0)
    assert plan.eval_result.enemy_head_intercept_risk == 0.0


def test_boundary_facing_escape_is_rejected():
    snake = Snake(1, Config.WORLD_RADIUS - 20, 0, 0)
    enemy = Snake(2, snake.pos.x - 90, 0, 0)
    enemy.segments = [
        Vector2(snake.pos.x - 90, 0),
        Vector2(snake.pos.x - 90, 55),
        Vector2(snake.pos.x - 55, 90),
        Vector2(snake.pos.x, 90),
        Vector2(snake.pos.x - 90, -55),
        Vector2(snake.pos.x - 55, -90),
        Vector2(snake.pos.x, -90),
    ]
    state = _state(snake, [enemy])

    plan = Strategy().select_anti_coil_escape(state)

    assert plan is not None
    assert plan.heading != pytest.approx(0.0)
    assert plan.eval_result.open_space_score >= 0.15


def test_boost_remains_controlled_by_existing_safety_policy():
    snake = Snake(1, 0, 0, 0)
    snake.mass = 100
    snake.recompute_segments()
    state = _state(snake, [_surrounding_enemy()])
    result = Strategy().decide(state)

    safe_angle, safe_boost, overridden, reason = SafetyGate().filter_action(
        state,
        result.best_escape_heading,
        True,
    )

    assert safe_angle == pytest.approx(result.best_escape_heading)
    assert overridden is False
    assert reason in {"none", "boost_mass_reserve", "boost_turn_too_sharp"}
    assert isinstance(safe_boost, bool)


def test_harness_includes_anti_coil_scenarios_and_existing_regressions():
    names = [scenario.name for scenario in build_scenarios()]

    assert "anti_coil_escape_open_gap" in names
    assert "anti_coil_escape_rejects_closing_gap" in names
    assert "anti_coil_no_false_positive_open_space" in names
    assert "guarded_cluster_center_safe" in names
    assert "telemetry_projected_collision_001" in names

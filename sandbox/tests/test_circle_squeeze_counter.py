import math

import pytest

from sandbox.bot.perception import Perception
from sandbox.bot.strategy import Strategy, StrategyMode
from sandbox.config import Config
from sandbox.food import FoodItem
from sandbox.snake import Snake
from sandbox.tools.validate_scenarios import build_scenarios
from sandbox.vector import Vector2


def _ring_segments(radius=90.0, omitted_angles=(-45, -22.5, 0, 22.5, 45)):
    omitted = {round(angle % 360, 4) for angle in omitted_angles}
    segments = []
    for index in range(16):
        angle_deg = index * 22.5
        if round(angle_deg % 360, 4) in omitted:
            continue
        angle = math.radians(angle_deg)
        segments.append(Vector2(math.cos(angle) * radius, math.sin(angle) * radius))
    return segments


def _state(my_snake, enemies=None, foods=None, vision_radius=500):
    return Perception(vision_radius=vision_radius).build(
        my_snake,
        [my_snake, *(enemies or [])],
        foods or [],
    )


def _circle_enemy(enemy_id=2, segments=None):
    enemy = Snake(enemy_id, -90, 0, 0)
    enemy.segments = segments or _ring_segments()
    return enemy


def test_loop_gap_detector_is_deterministic():
    snake = Snake(1, 0, 0, 0)
    state = _state(snake, [_circle_enemy()])

    first = Strategy.analyze_circle_squeeze(state)
    second = Strategy.analyze_circle_squeeze(state)

    assert first == second
    assert first.active is True


def test_sector_occupancy_and_largest_gap_are_computed():
    snake = Snake(1, 0, 0, 0)
    state = _state(snake, [_circle_enemy()])

    analysis = Strategy.analyze_circle_squeeze(state)

    assert analysis.sector_count >= Strategy.CIRCLE_SQUEEZE_MIN_SECTORS
    assert analysis.largest_gap == pytest.approx(math.radians(112.5))
    assert abs(math.degrees(analysis.largest_gap_center)) < 20.0


def test_mostly_closed_ring_activates_circle_squeeze_counter():
    snake = Snake(1, 0, 0, 0)
    state = _state(snake, [_circle_enemy()])

    result = Strategy().decide(state)

    assert result.mode == StrategyMode.AVOID_THREAT
    assert result.circle_squeeze_counter_active is True
    assert result.defensive_reason == "Circle squeeze counter"


def test_open_arc_does_not_activate_false_positive():
    snake = Snake(1, 0, 0, 0)
    arc_enemy = _circle_enemy(
        segments=[
            Vector2(math.cos(math.radians(angle)) * 95, math.sin(math.radians(angle)) * 95)
            for angle in (0, 22.5, 45, 67.5, 90)
        ],
    )
    state = _state(snake, [arc_enemy])

    analysis = Strategy.analyze_circle_squeeze(state)
    result = Strategy().decide(state)

    assert analysis.active is False
    assert result.circle_squeeze_counter_active is False
    assert result.defensive_reason == "Forward danger"


def test_selected_escape_heading_points_through_largest_safe_gap():
    snake = Snake(1, 0, 0, 0)
    state = _state(snake, [_circle_enemy()])
    strategy = Strategy()

    plan = strategy.select_circle_squeeze_escape(state)
    result = strategy.decide(state)

    assert plan is not None
    assert abs(math.degrees(plan.heading)) < 20.0
    assert result.circle_squeeze_escape_heading == pytest.approx(plan.heading)
    assert result.target_pos.x > 0


def test_projected_closing_gap_is_rejected():
    snake = Snake(1, 0, 0, 0)
    closing_head = Snake(3, 75, 80, -math.pi / 2)
    closing_head.speed = Config.BASE_SPEED
    closing_head.segments = []
    lower_closing_head = Snake(4, 75, -80, math.pi / 2)
    lower_closing_head.speed = Config.BASE_SPEED
    lower_closing_head.segments = []
    state = _state(snake, [_circle_enemy(), closing_head, lower_closing_head])

    plan = Strategy().select_circle_squeeze_escape(state)

    assert plan is not None
    assert abs(math.degrees(plan.heading)) > 20.0
    assert plan.eval_result.enemy_head_intercept_risk == 0.0


def test_boundary_facing_gap_is_rejected_by_boundary_priority():
    snake = Snake(1, Config.WORLD_RADIUS - 50, 0, 0)
    enemy = _circle_enemy(
        segments=[
            Vector2(
                snake.pos.x + math.cos(math.radians(angle)) * 90,
                math.sin(math.radians(angle)) * 90,
            )
            for angle in (67.5, 135, 157.5, 180, 202.5, 225, 247.5, 270, 292.5)
        ],
    )
    state = _state(snake, [enemy])

    result = Strategy().decide(state)

    assert result.mode == StrategyMode.AVOID_BOUNDARY
    assert result.circle_squeeze_counter_active is False
    assert result.defensive_reason == "Boundary proximity"


def test_circle_squeeze_counter_blocks_food_and_partial_guard_priority():
    snake = Snake(1, 0, 0, 0)
    pressure = Snake(3, 185, 95, 0)
    pressure.segments = []
    foods = [
        FoodItem(170, -15, 6.0),
        FoodItem(190, 0, 5.5),
        FoodItem(178, 20, 5.0),
    ]
    state = _state(snake, [_circle_enemy(), pressure], foods)

    result = Strategy().decide(state)

    assert result.circle_squeeze_counter_active is True
    assert result.partial_guard_active is False
    assert result.loot_cluster_target_kind is None
    assert result.defensive_reason == "Circle squeeze counter"


def test_harness_includes_circle_squeeze_counter_scenarios():
    names = [scenario.name for scenario in build_scenarios()]

    assert "circle_squeeze_counter_open_gap" in names
    assert "circle_squeeze_counter_closing_gap" in names
    assert "circle_squeeze_counter_no_false_positive_arc" in names
    assert "circle_squeeze_counter_prioritizes_boundary_safety" in names

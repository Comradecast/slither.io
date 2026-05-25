import math

import pytest

from sandbox.bot.perception import Perception
from sandbox.bot.safety_gate import SafetyGate
from sandbox.bot.strategy import Strategy, StrategyMode
from sandbox.config import Config
from sandbox.food import FoodItem
from sandbox.snake import Snake
from sandbox.tools.validate_scenarios import build_scenarios
from sandbox.vector import Vector2


def _cluster_food():
    return [
        FoodItem(170, -15, 6.0),
        FoodItem(190, 0, 5.5),
        FoodItem(178, 20, 5.0),
        FoodItem(45, 0, 2.0),
    ]


def _state(snake, foods=None, enemies=None, vision_radius=500):
    return Perception(vision_radius=vision_radius).build(
        snake,
        [snake, *(enemies or [])],
        foods or [],
    )


def _pressure_enemy(x=185, y=95, snake_id=2):
    enemy = Snake(snake_id, x, y, 0)
    enemy.segments = []
    return enemy


def _surrounding_enemy(enemy_id=9):
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


def test_partial_guard_activation_requires_enemy_pressure():
    snake = Snake(1, 0, 0, 0)
    strategy = Strategy()
    pressure_state = _state(snake, _cluster_food(), [_pressure_enemy()])
    quiet_state = _state(snake, _cluster_food(), [])

    assert strategy.select_partial_guard(pressure_state) is not None
    assert strategy.select_partial_guard(quiet_state) is None


def test_partial_guard_does_not_activate_with_no_enemy_near_cluster():
    snake = Snake(1, 0, 0, 0)
    far_enemy = _pressure_enemy(520, 320)
    state = _state(snake, _cluster_food(), [far_enemy])

    result = Strategy().decide(state)

    assert result.mode == StrategyMode.SEEK_FOOD
    assert result.partial_guard_active is False
    assert result.loot_cluster_target_kind == "center"


def test_selected_guard_offset_is_deterministic():
    snake = Snake(1, 0, 0, 0)
    state = _state(snake, _cluster_food(), [_pressure_enemy()])
    strategy = Strategy()

    first = strategy.select_partial_guard(state)
    second = strategy.select_partial_guard(state)

    assert first is not None
    assert second is not None
    assert first.side == second.side == "left"
    assert first.target.x == pytest.approx(second.target.x)
    assert first.target.y == pytest.approx(second.target.y)


def test_unsafe_preferred_guard_offset_is_rejected_for_safe_alternate():
    snake = Snake(1, 0, 0, 0)
    closing_head = Snake(3, 120, 130, -math.pi / 2)
    closing_head.speed = Config.BASE_SPEED
    closing_head.segments = []
    state = _state(snake, _cluster_food(), [_pressure_enemy(), closing_head])

    plan = Strategy().select_partial_guard(state)

    assert plan is not None
    assert plan.side == "right"
    assert plan.eval_result.enemy_head_intercept_risk == 0.0
    assert plan.eval_result.collision_risk == 0.0


def test_anti_coil_priority_blocks_partial_guard():
    snake = Snake(1, 0, 0, 0)
    state = _state(
        snake,
        _cluster_food(),
        [_surrounding_enemy(), _pressure_enemy(185, 95, 3)],
    )

    result = Strategy().decide(state)

    assert result.mode == StrategyMode.AVOID_THREAT
    assert result.anti_coil_escape_active is True
    assert result.partial_guard_active is False
    assert result.defensive_reason == "Anti-coil escape"


def test_selected_guard_heading_passes_safety_evaluation():
    snake = Snake(1, 0, 0, 0)
    state = _state(snake, _cluster_food(), [_pressure_enemy()])
    strategy = Strategy()
    plan = strategy.select_partial_guard(state)

    assert plan is not None
    assert strategy._is_safe_target_heading(plan.target, state) is True


def test_boost_remains_controlled_by_existing_boost_policy():
    snake = Snake(1, 0, 0, 0)
    snake.mass = 100
    snake.recompute_segments()
    state = _state(snake, _cluster_food(), [_pressure_enemy()])
    result = Strategy().decide(state)
    heading = math.atan2(
        result.target_pos.y - state.my_head.y,
        result.target_pos.x - state.my_head.x,
    )

    _, safe_boost, overridden, reason = SafetyGate().filter_action(state, heading, True)

    assert overridden is False
    assert reason in {"none", "boost_turn_too_sharp"}
    assert isinstance(safe_boost, bool)


def test_harness_includes_partial_guard_scenarios():
    names = [scenario.name for scenario in build_scenarios()]

    assert "partial_guard_safe_offset" in names
    assert "partial_guard_rejects_unsafe_offset" in names
    assert "partial_guard_not_when_no_enemy_pressure" in names
    assert "partial_guard_not_during_anti_coil_escape" in names

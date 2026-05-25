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


def _state(snake, foods, snakes=None, vision_radius=400):
    return Perception(vision_radius=vision_radius).build(
        snake,
        snakes if snakes is not None else [snake],
        foods,
    )


def _assert_target_is_safe(strategy, state, target):
    assert strategy._is_safe_target_heading(target, state) is True


def test_approach_candidate_generation_is_deterministic():
    snake = Snake(1, 0, 0, 0)
    foods = [
        FoodItem(150, 50, 6.0),
        FoodItem(170, 0, 5.5),
        FoodItem(190, -20, 5.0),
    ]
    state = _state(snake, foods)
    cluster = Strategy.detect_loot_clusters(state.visible_food)[0]
    strategy = Strategy()

    first = strategy.loot_cluster_approach_candidates(cluster, state)
    second = strategy.loot_cluster_approach_candidates(cluster, state)

    assert [(c.target_kind, c.target.x, c.target.y) for c in first] == [
        (c.target_kind, c.target.x, c.target.y) for c in second
    ]
    assert first[0].target_kind == "center"


def test_center_approach_is_selected_when_safe():
    snake = Snake(1, 0, 0, 0)
    foods = [
        FoodItem(170, 40, 6.0),
        FoodItem(190, 55, 5.5),
        FoodItem(185, 72, 5.0),
        FoodItem(45, 0, 2.0),
    ]
    state = _state(snake, foods)

    result = Strategy().decide(state)

    assert result.mode == StrategyMode.SEEK_FOOD
    assert result.loot_cluster_target_kind == "center"
    assert result.target_pos.x == pytest.approx(result.loot_cluster_target.x)
    assert result.target_pos.y == pytest.approx(result.loot_cluster_target.y)


def test_edge_approach_is_selected_when_center_is_unsafe():
    snake = Snake(1, 0, 0, 0)
    enemy = Snake(2, 75, 80, -math.pi / 2)
    enemy.speed = Config.BASE_SPEED
    enemy.segments = []
    foods = [
        FoodItem(150, 50, 6.0),
        FoodItem(170, 0, 5.5),
        FoodItem(190, -20, 5.0),
        FoodItem(45, 0, 2.0),
    ]
    state = _state(snake, foods, [snake, enemy])
    strategy = Strategy()
    cluster = Strategy.detect_loot_clusters(state.visible_food)[0]

    assert strategy._is_safe_target_heading(cluster.center, state) is False

    result = strategy.decide(state)

    assert result.mode == StrategyMode.SEEK_FOOD
    assert result.loot_cluster_target_kind == "pellet"
    assert result.target_pos.y > 0
    _assert_target_is_safe(strategy, state, result.target_pos)


def test_unsafe_cluster_does_not_override_defensive_threat_avoidance():
    snake = Snake(1, 0, 0, 0)
    enemy = Snake(2, 100, 0, 0)
    enemy.segments = [Vector2(100, 0)]
    foods = [
        FoodItem(150, -8, 7.0),
        FoodItem(166, 6, 6.0),
        FoodItem(178, -4, 5.0),
        FoodItem(40, 80, 2.0),
    ]
    state = _state(snake, foods, [snake, enemy])

    result = Strategy().decide(state)

    assert result.mode == StrategyMode.AVOID_THREAT
    assert result.loot_cluster_target_kind is None
    assert result.target_pos.x == 100
    assert result.target_pos.y == 0


def test_selected_guarded_target_passes_heading_safety_checks():
    snake = Snake(1, 0, 0, 0)
    foods = [
        FoodItem(170, 40, 6.0),
        FoodItem(190, 55, 5.5),
        FoodItem(185, 72, 5.0),
        FoodItem(45, 0, 2.0),
    ]
    state = _state(snake, foods)
    strategy = Strategy()

    result = strategy.decide(state)

    _assert_target_is_safe(strategy, state, result.target_pos)


def test_boost_remains_controlled_by_existing_safety_gate():
    snake = Snake(1, 0, 0, 0)
    snake.mass = 100
    snake.recompute_segments()
    foods = [
        FoodItem(170, 40, 6.0),
        FoodItem(190, 55, 5.5),
        FoodItem(185, 72, 5.0),
    ]
    state = _state(snake, foods)
    result = Strategy().decide(state)
    heading = math.atan2(
        result.target_pos.y - state.my_head.y,
        result.target_pos.x - state.my_head.x,
    )

    _, safe_boost, overridden, reason = SafetyGate().filter_action(state, heading, True)

    assert overridden is False
    assert reason in {"none", "boost_turn_too_sharp"}
    assert isinstance(safe_boost, bool)


def test_harness_includes_guarded_collection_scenarios():
    names = [scenario.name for scenario in build_scenarios()]

    assert "guarded_cluster_center_safe" in names
    assert "guarded_cluster_edge_entry_preferred" in names
    assert "guarded_cluster_threat_blocks_collection" in names

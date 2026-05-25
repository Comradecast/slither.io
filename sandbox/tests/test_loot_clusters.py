import pytest

from sandbox.bot.perception import Perception
from sandbox.bot.strategy import Strategy, StrategyMode
from sandbox.food import FoodItem
from sandbox.snake import Snake
from sandbox.tools.validate_scenarios import ScenarioRunner, build_scenarios
from sandbox.vector import Vector2


def _state(snake, foods, snakes=None, vision_radius=400):
    return Perception(vision_radius=vision_radius).build(
        snake,
        snakes if snakes is not None else [snake],
        foods,
    )


def test_cluster_detection_groups_nearby_high_value_pellets():
    snake = Snake(1, 0, 0, 0)
    foods = [
        FoodItem(100, 0, 6.0),
        FoodItem(120, 10, 5.0),
        FoodItem(90, -12, 5.0),
        FoodItem(260, 0, 2.0),
    ]
    state = _state(snake, foods)

    clusters = Strategy.detect_loot_clusters(state.visible_food)

    assert len(clusters) == 1
    assert clusters[0].pellet_count == 3
    assert clusters[0].total_value == pytest.approx(16.0)
    assert clusters[0].high_value_pellet_count == 3


def test_cluster_weighted_center_is_deterministic():
    snake = Snake(1, 0, 0, 0)
    foods = [
        FoodItem(100, 0, 5.0),
        FoodItem(130, 0, 10.0),
        FoodItem(100, 30, 5.0),
    ]
    state = _state(snake, foods)

    first = Strategy.detect_loot_clusters(state.visible_food)[0]
    second = Strategy.detect_loot_clusters(list(reversed(state.visible_food)))[0]

    assert first.center.x == pytest.approx(115.0)
    assert first.center.y == pytest.approx(7.5)
    assert second.center.x == pytest.approx(first.center.x)
    assert second.center.y == pytest.approx(first.center.y)


def test_safe_high_value_cluster_beats_isolated_low_value_food():
    snake = Snake(1, 0, 0, 0)
    foods = [
        FoodItem(180, 48, 6.0),
        FoodItem(196, 54, 5.5),
        FoodItem(188, 70, 5.0),
        FoodItem(45, 0, 2.0),
    ]
    state = _state(snake, foods)

    result = Strategy().decide(state)

    assert result.mode == StrategyMode.SEEK_FOOD
    assert result.loot_cluster_pellet_count == 3
    assert result.loot_cluster_total_value == pytest.approx(16.5)
    assert result.target_pos.x == pytest.approx(result.loot_cluster_target.x)
    assert result.target_pos.y == pytest.approx(result.loot_cluster_target.y)


def test_unsafe_cluster_near_threat_is_not_selected():
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
    assert result.loot_cluster_score is None
    assert result.target_pos.x == 100
    assert result.target_pos.y == 0


def test_no_cluster_preserves_existing_food_selection():
    snake = Snake(1, 0, 0, 0)
    foods = [
        FoodItem(30, 0, 2.0),
        FoodItem(80, 30, 1.0),
        FoodItem(140, -40, 1.0),
    ]
    state = _state(snake, foods)

    result = Strategy().decide(state)

    assert result.mode == StrategyMode.SEEK_FOOD
    assert result.target_pos.x == 30
    assert result.target_pos.y == 0
    assert result.loot_cluster_score is None


def test_harness_includes_loot_cluster_scenarios():
    names = [scenario.name for scenario in build_scenarios()]

    assert "loot_cluster_safe_preferred" in names
    assert "loot_cluster_unsafe_rejected" in names
    assert "normal_food_without_cluster" in names


def test_harness_reports_include_loot_cluster_fields(tmp_path):
    scenario = next(
        scenario
        for scenario in build_scenarios()
        if scenario.name == "loot_cluster_safe_preferred"
    )

    result = ScenarioRunner(reports_dir=tmp_path).run_scenario(scenario)

    assert result["passed"] is True
    assert result["loot_cluster_score"] is not None
    assert result["loot_cluster_total_value"] == pytest.approx(16.5)
    assert result["loot_cluster_pellet_count"] == 3
    assert result["loot_cluster_target_x"] == pytest.approx(result["strategy"]["target_x"])
    assert result["loot_cluster_target_y"] == pytest.approx(result["strategy"]["target_y"])

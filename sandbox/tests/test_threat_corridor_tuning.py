import math

import pytest

from sandbox.bot.perception import PerceivedSnake, PerceivedThreat, Perception
from sandbox.bot.safety_gate import SafetyGate
from sandbox.bot.strategy import Strategy, StrategyMode
from sandbox.config import Config
from sandbox.food import FoodItem
from sandbox.snake import Snake
from sandbox.tools.validate_scenarios import run_all_scenarios
from sandbox.vector import Vector2


def _state(my_snake=None, threats=None, enemies=None, foods=None):
    snake = my_snake or Snake(1, 0, 0, 0)
    state = Perception(vision_radius=600).build(snake, [snake], foods or [])
    state.visible_threats = threats or []
    state.visible_snakes = enemies or []
    state.highest_threat = max(state.visible_threats, key=lambda threat: threat.score) if threats else None
    state.nearest_threat = min(state.visible_threats, key=lambda threat: threat.distance) if threats else None
    return state


def _threat(x, y, *, radius=10.0, velocity=None, persistent_frames=1):
    distance = math.hypot(x, y)
    angle_diff = math.atan2(y, x)
    in_forward_cone = abs(angle_diff) < Perception.FORWARD_CONE_ANGLE
    return PerceivedThreat(
        pos=Vector2(x, y),
        source_id=2,
        distance=distance,
        score=600 - distance,
        angle_diff=angle_diff,
        in_forward_cone=in_forward_cone,
        radius=radius,
        velocity=velocity,
        persistent_frames=persistent_frames,
    )


def test_direct_forward_body_collision_remains_unsafe():
    state = _state(threats=[_threat(70, 0, persistent_frames=3)])

    result = Strategy()._evaluate_heading(0.0, 1.0, 0.0, state, 10.0)

    assert result.collision_risk == 1.0
    assert result.collision_lateral_offset == pytest.approx(0.0)
    assert result.threat_confidence is not None


def test_lateral_body_threat_outside_core_corridor_is_soft_pressure():
    my = Snake(1, 0, 0, 0)
    my.mass = 100
    state = _state(my_snake=my, threats=[_threat(120, 13, radius=10.0)])

    result = Strategy()._evaluate_heading(0.0, 1.0, 0.0, state, 10.0)
    safe_angle, safe_boost, overridden, reason = SafetyGate().filter_action(state, 0.0, False)

    assert 0.0 < result.collision_risk <= Strategy.THREAT_CORRIDOR_SOFT_RISK
    assert result.collision_lateral_offset == pytest.approx(13.0)
    assert overridden is False
    assert safe_boost is False
    assert safe_angle == pytest.approx(0.0)
    assert reason == "none"


def test_dense_lateral_threat_field_remains_hard_projected_collision():
    my = Snake(1, 0, 0, 0)
    my.mass = 100
    threats = [
        _threat(120 + index * 0.1, 13, radius=10.0)
        for index in range(Strategy.DENSE_THREAT_FIELD_COUNT)
    ]
    state = _state(my_snake=my, threats=threats)

    result = Strategy()._evaluate_heading(0.0, 1.0, 0.0, state, 10.0)
    safe_angle, safe_boost, overridden, reason = SafetyGate().filter_action(state, 0.0, False)

    assert result.collision_risk == 1.0
    assert overridden is True
    assert safe_boost is False
    assert reason == "projected_collision"


def test_receding_threat_has_lower_confidence_than_closing_threat():
    receding = _state(
        threats=[_threat(120, 13, radius=10.0, velocity=Vector2(5, 0), persistent_frames=3)]
    )
    closing = _state(
        threats=[_threat(120, 13, radius=10.0, velocity=Vector2(-5, 0), persistent_frames=3)]
    )

    receding_result = Strategy()._evaluate_heading(0.0, 1.0, 0.0, receding, 10.0)
    closing_result = Strategy()._evaluate_heading(0.0, 1.0, 0.0, closing, 10.0)

    assert receding_result.threat_receding is True
    assert closing_result.threat_receding is False
    assert receding_result.threat_confidence < closing_result.threat_confidence


def test_distant_lateral_non_closing_threat_does_not_dominate_food_route():
    food = FoodItem(80, 0, 4.0)
    state = _state(
        threats=[_threat(260, 90, radius=10.0, velocity=Vector2(2, 0))],
        foods=[food],
    )

    result = Strategy().decide(state)

    assert result.mode == StrategyMode.SEEK_FOOD
    assert result.target_pos.x == pytest.approx(80.0)
    assert result.target_pos.y == pytest.approx(0.0)


def test_seek_food_is_blocked_under_heavy_threat_pressure():
    food = FoodItem(80, 0, 4.0)
    threats = [
        _threat(260 + index * 0.1, 500, radius=10.0, velocity=Vector2(2, 0))
        for index in range(Strategy.DENSE_THREAT_FIELD_COUNT)
    ]
    state = _state(threats=threats, foods=[food])

    result = Strategy().decide(state)

    assert result.mode == StrategyMode.AVOID_THREAT
    assert result.defensive_reason == "Nearby body segment"
    assert result.target_pos is not None


def test_circle_squeeze_with_high_closing_count_stays_defensive():
    angles = (67.5, 90, 112.5, 135, 157.5, 180, 202.5, 225, 247.5, 270, 292.5)
    threats = [
        _threat(
            math.cos(math.radians(angle)) * 90,
            math.sin(math.radians(angle)) * 90,
            radius=10.0,
            velocity=Vector2(-math.cos(math.radians(angle)), -math.sin(math.radians(angle))),
            persistent_frames=3,
        )
        for angle in angles
    ]
    state = _state(threats=threats, foods=[FoodItem(80, 0, 4.0)])
    state.closing_threat_count = Strategy.DENSE_CLOSING_THREAT_COUNT

    result = Strategy().decide(state)

    assert result.mode == StrategyMode.AVOID_THREAT
    assert result.circle_squeeze_counter_active is True
    assert result.loot_cluster_target_kind is None


def test_true_projected_collision_still_triggers_safety_gate_override():
    state = _state(threats=[_threat(60, 0, radius=12.0, persistent_frames=3)])

    safe_angle, safe_boost, overridden, reason = SafetyGate().filter_action(state, 0.0, True)

    assert overridden is True
    assert reason == "projected_collision"
    assert safe_boost is False
    assert abs(safe_angle) > 0.1


def test_true_enemy_head_intercept_still_triggers():
    enemy = PerceivedSnake(
        id=2,
        head=Vector2(75, 80),
        mass=100,
        distance=110,
        radius=Config.get_radius(100),
        speed=Config.BASE_SPEED,
        heading=-math.pi / 2,
    )
    state = _state(enemies=[enemy])

    result = Strategy()._evaluate_heading(0.0, 1.0, 0.0, state, 10.0)
    safe_angle, safe_boost, overridden, reason = SafetyGate().filter_action(state, 0.0, True)

    assert result.enemy_head_intercept_risk == 2.0
    assert result.enemy_intercept_heading_delta_deg is not None
    assert overridden is True
    assert reason == "enemy_head_intercept"
    assert safe_boost is False


def test_existing_harness_scenarios_still_pass(tmp_path):
    results = run_all_scenarios(reports_dir=tmp_path)

    assert all(result["passed"] for result in results)

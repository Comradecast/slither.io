import math
import pytest
from sandbox.vector import Vector2
from sandbox.snake import Snake
from sandbox.food import FoodItem
from sandbox.config import Config
from sandbox.bot.perception import Perception, PerceivedThreat, PerceivedSnake
from sandbox.bot.strategy import Strategy, StrategyMode
from sandbox.bot.steering import Steering
from sandbox.bot.controller import BotController
from sandbox.bot.safety_gate import SafetyGate

def test_perception_includes_snake_state():
    s = Snake(1, 100, 200, 1.5)
    p = Perception()
    state = p.build(s, [s], [])
    assert state.my_id == 1
    assert state.my_head.x == 100
    assert state.my_head.y == 200
    assert state.my_angle == 1.5

def test_perception_lists_visible_food():
    s = Snake(1, 0, 0, 0)
    s.speed = 5.0
    f1 = FoodItem(10, 0, 1.0) # Visible
    f2 = FoodItem(Config.AI_VISION_RADIUS + 100, 0, 1.0) # Outside vision
    
    p = Perception(vision_radius=Config.AI_VISION_RADIUS)
    state = p.build(s, [s], [f1, f2])
    
    assert len(state.visible_food) == 1
    assert state.visible_food[0].pos.x == 10

def test_perception_detects_enemy_threats_not_own_body():
    my_snake = Snake(1, 0, 0, 0)
    my_snake.segments = [Vector2(0, 0), Vector2(-10, 0), Vector2(-20, 0)]
    
    enemy_snake = Snake(2, 50, 0, 0)
    enemy_snake.segments = [Vector2(50, 0), Vector2(60, 0)]
    
    p = Perception(vision_radius=100)
    state = p.build(my_snake, [my_snake, enemy_snake], [])
    
    assert state.active_threat_count == 2
    assert state.nearest_threat is not None
    assert state.nearest_threat.source_id == 2
    assert state.nearest_threat.distance == 50

def test_perception_forward_threats_score_higher():
    # My snake faces right (0 radians)
    my_snake = Snake(1, 0, 0, 0)
    
    # Threat 1 is directly in front, distance 50
    enemy1 = Snake(2, 50, 0, 0)
    enemy1.segments = [Vector2(50, 0)]
    
    # Threat 2 is directly behind, distance 50
    enemy2 = Snake(3, -50, 0, 0)
    enemy2.segments = [Vector2(-50, 0)]
    
    p = Perception(vision_radius=100)
    state = p.build(my_snake, [my_snake, enemy1, enemy2], [])
    
    assert state.active_threat_count == 2
    assert state.highest_threat.pos.x == 50
    assert state.highest_threat.in_forward_cone == True

def test_perception_closer_threats_score_higher():
    my_snake = Snake(1, 0, 0, 0)
    
    # Both in front, different distances
    enemy1 = Snake(2, 50, 0, 0)
    enemy1.segments = [Vector2(50, 0)]
    enemy2 = Snake(3, 80, 0, 0)
    enemy2.segments = [Vector2(80, 0)]
    
    p = Perception(vision_radius=100)
    state = p.build(my_snake, [my_snake, enemy1, enemy2], [])
    
    assert state.highest_threat.pos.x == 50 # 50 is closer than 80

def test_strategy_boundary_avoidance_priority():
    # Near edge, but also near an enemy
    s = Snake(1, Config.WORLD_RADIUS - 10, 0, 0)
    enemy = Snake(2, Config.WORLD_RADIUS - 20, 0, 0)
    
    p = Perception(vision_radius=100)
    state = p.build(s, [s, enemy], [])
    
    strat = Strategy()
    result = strat.decide(state)
    
    # Boundary avoidance must take priority over threat avoidance
    assert result.mode == StrategyMode.AVOID_BOUNDARY
    assert result.defensive_reason == "Boundary proximity"


def test_boundary_distance_from_center_is_world_radius_in_any_heading():
    head = Vector2(0, 0)

    assert Strategy.boundary_distance_along_heading(head, 0.0) == pytest.approx(Config.WORLD_RADIUS)
    assert Strategy.boundary_distance_along_heading(head, math.pi / 2) == pytest.approx(Config.WORLD_RADIUS)
    assert Strategy.boundary_distance_along_heading(head, math.radians(217)) == pytest.approx(Config.WORLD_RADIUS)


def test_boundary_distance_near_east_boundary_heading_east_is_short():
    head = Vector2(Config.WORLD_RADIUS - 60, 0)

    distance = Strategy.boundary_distance_along_heading(head, 0.0)

    assert distance == pytest.approx(60.0)


def test_boundary_distance_near_east_boundary_heading_west_is_long():
    head = Vector2(Config.WORLD_RADIUS - 60, 0)

    distance = Strategy.boundary_distance_along_heading(head, math.pi)

    assert distance == pytest.approx((Config.WORLD_RADIUS * 2.0) - 60.0)


def test_enemy_projection_helper_returns_expected_future_point_heading_east():
    projected = Strategy.project_enemy_positions(
        Vector2(10, 20),
        speed=100.0,
        heading=0.0,
        sample_times=(0.5,),
    )

    sample_time, point = projected[0]

    assert sample_time == pytest.approx(0.5)
    assert point.x == pytest.approx(60.0)
    assert point.y == pytest.approx(20.0)


def test_enemy_projection_helper_returns_expected_future_point_heading_north():
    projected = Strategy.project_enemy_positions(
        Vector2(10, 20),
        speed=100.0,
        heading=math.pi / 2,
        sample_times=(0.5,),
    )

    sample_time, point = projected[0]

    assert sample_time == pytest.approx(0.5)
    assert point.x == pytest.approx(10.0)
    assert point.y == pytest.approx(70.0)


def test_safety_gate_overrides_wall_facing_boundary_heading():
    s = Snake(1, Config.WORLD_RADIUS - 60, 0, 0)
    s.mass = 5000
    s.recompute_segments()
    state = Perception(vision_radius=100).build(s, [s], [])

    safe_angle, safe_boost, overridden, reason = SafetyGate().filter_action(state, 0.0, True)

    assert overridden is True
    assert reason == "boundary_too_close"
    assert safe_boost is False
    assert safe_angle == pytest.approx(math.pi)


def test_safety_gate_allows_escape_boundary_heading():
    s = Snake(1, Config.WORLD_RADIUS - 60, 0, math.pi)
    s.mass = 5000
    s.recompute_segments()
    state = Perception(vision_radius=100).build(s, [s], [])

    safe_angle, safe_boost, overridden, reason = SafetyGate().filter_action(state, math.pi, True)

    assert overridden is False
    assert reason == "none"
    assert safe_boost is True
    assert safe_angle == pytest.approx(math.pi)


def test_strategy_detects_projected_crossing_risk():
    s = Snake(1, 0, 0, 0)
    s.speed = Config.BASE_SPEED
    state = Perception(vision_radius=200).build(s, [s], [])
    state.visible_snakes = [
        PerceivedSnake(
            id=2,
            head=Vector2(75, 80),
            mass=100,
            distance=110,
            radius=Config.get_radius(100),
            speed=Config.BASE_SPEED,
            heading=-math.pi / 2,
        )
    ]

    res = Strategy()._evaluate_heading(0.0, 1.0, 0.0, state, 10.0)

    assert res.enemy_head_intercept_risk == 2.0
    assert res.enemy_head_intercept_time == pytest.approx(0.5)
    assert res.enemy_head_intercept_distance == pytest.approx(75.0)


def test_strategy_does_not_flag_non_crossing_projected_enemy():
    s = Snake(1, 0, 0, 0)
    s.speed = Config.BASE_SPEED
    state = Perception(vision_radius=200).build(s, [s], [])
    state.visible_snakes = [
        PerceivedSnake(
            id=2,
            head=Vector2(75, 80),
            mass=100,
            distance=110,
            radius=Config.get_radius(100),
            speed=Config.BASE_SPEED,
            heading=math.pi / 2,
        )
    ]

    res = Strategy()._evaluate_heading(0.0, 1.0, 0.0, state, 10.0)

    assert res.enemy_head_intercept_risk == 0.0
    assert res.enemy_head_intercept_time is None


def test_safety_gate_overrides_projected_intercept():
    s = Snake(1, 0, 0, 0)
    s.speed = Config.BASE_SPEED
    enemy = Snake(2, 75, 80, -math.pi / 2)
    enemy.speed = Config.BASE_SPEED
    enemy.segments = []
    state = Perception(vision_radius=200).build(s, [s, enemy], [])

    safe_angle, safe_boost, overridden, reason = SafetyGate().filter_action(state, 0.0, True)

    assert overridden is True
    assert reason == "enemy_head_intercept"
    assert safe_boost is False


def test_safety_gate_allows_non_crossing_safe_heading():
    s = Snake(1, 0, 0, 0)
    s.speed = Config.BASE_SPEED
    s.mass = 100
    s.recompute_segments()
    enemy = Snake(2, 75, 80, math.pi / 2)
    enemy.speed = Config.BASE_SPEED
    enemy.segments = []
    state = Perception(vision_radius=200).build(s, [s, enemy], [])

    safe_angle, safe_boost, overridden, reason = SafetyGate().filter_action(state, 0.0, True)

    assert overridden is False
    assert reason == "none"
    assert safe_boost is True
    assert safe_angle == pytest.approx(0.0)

def test_strategy_threat_avoidance():
    # Safe from boundary, but near enemy
    s = Snake(1, 0, 0, 0)
    s.speed = 5.0
    enemy = Snake(2, 50, 0, 0)
    enemy.segments = [Vector2(50, 0)]
    
    p = Perception(vision_radius=100)
    state = p.build(s, [s, enemy], [])
    
    strat = Strategy()
    result = strat.decide(state)
    assert result.mode == StrategyMode.AVOID_THREAT
    assert result.target_pos.x == 50
    assert result.defensive_reason == "Forward danger"

def test_strategy_food_seeking_when_safe():
    s = Snake(1, 0, 0, 0)
    s.speed = 5.0
    f1 = FoodItem(10, 0, 1.0)
    p = Perception(vision_radius=100)
    state = p.build(s, [s], [f1])
    
    strat = Strategy()
    result = strat.decide(state)
    assert result.mode == StrategyMode.SEEK_FOOD

def test_strategy_prefers_higher_value_nearby_food():
    s = Snake(1, 0, 0, 0)
    s.speed = 5.0
    low_value = FoodItem(10, 0, 1.0)
    high_value = FoodItem(30, 0, 4.0)
    p = Perception(vision_radius=100)
    state = p.build(s, [s], [low_value, high_value])

    result = Strategy().decide(state)

    assert result.mode == StrategyMode.SEEK_FOOD
    assert result.target_pos.x == 30

def test_strategy_distant_high_value_does_not_always_win():
    s = Snake(1, 0, 0, 0)
    s.speed = 5.0
    close_reasonable = FoodItem(30, 0, 2.0)
    distant_high_value = FoodItem(500, 0, 5.0)
    p = Perception(vision_radius=600)
    state = p.build(s, [s], [close_reasonable, distant_high_value])

    result = Strategy().decide(state)

    assert result.mode == StrategyMode.SEEK_FOOD
    assert result.target_pos.x == 30

def test_strategy_prefers_front_food_over_similar_behind_food():
    s = Snake(1, 0, 0, 0)
    s.speed = 5.0
    front_food = FoodItem(40, 0, 2.0)
    behind_food = FoodItem(-40, 0, 2.0)
    p = Perception(vision_radius=100)
    state = p.build(s, [s], [behind_food, front_food])

    result = Strategy().decide(state)

    assert result.mode == StrategyMode.SEEK_FOOD
    assert result.target_pos.x == 40

def test_strategy_penalizes_food_near_known_threat():
    s = Snake(1, 0, 0, 0)
    s.speed = 5.0
    risky_high_value = FoodItem(45, 0, 5.0)
    safe_food = FoodItem(40, 80, 2.0)
    p = Perception(vision_radius=100)
    state = p.build(s, [s], [risky_high_value, safe_food])
    state.visible_threats = [
        PerceivedThreat(
            pos=Vector2(40, 0),
            source_id=2,
            distance=40,
            score=0,
            angle_diff=0,
            in_forward_cone=True,
            radius=6.0,
        )
    ]

    result = Strategy().decide(state)

    assert result.mode == StrategyMode.SEEK_FOOD
    assert result.target_pos.x == 40
    assert result.target_pos.y == 80

def test_steering_valid_heading_seek():
    s = Snake(1, 100, 100, 0)
    f = FoodItem(200, 100, 1.0)
    p = Perception(vision_radius=500)
    state = p.build(s, [s], [f])
    
    strat = Strategy()
    strat_result = strat.decide(state)
    
    steer = Steering()
    steer_result = steer.compute(strat_result, state)
    
    assert steer_result.heading == 0.0 # From (100,100) to (200,100) is 0 radians
    assert isinstance(steer_result.heading, float)

def test_steering_valid_heading_avoid_threat():
    s = Snake(1, 100, 100, 0)
    enemy = Snake(2, 200, 100, 0) # Enemy is directly to the right (0 radians)
    enemy.segments = [Vector2(200, 100)]
    
    p = Perception(vision_radius=500)
    state = p.build(s, [s, enemy], [])
    
    strat = Strategy()
    strat_result = strat.decide(state)
    assert strat_result.mode == StrategyMode.AVOID_THREAT
    
    steer = Steering()
    steer_result = steer.compute(strat_result, state)
    
    # We want to steer perpendicular to the enemy, so we should head left/right
    # In this case angle_diff is 0, so it steers left (my_angle - pi/2 = -pi/2)
    assert steer_result.heading == pytest.approx(-math.pi / 2)

def test_controller_returns_action_no_boost():
    s = Snake(1, 0, 0, 0)
    s.speed = 5.0
    f = FoodItem(100, 0, 1.0)
    
    controller = BotController(s)
    action = controller.update([s], [f])
    
    assert hasattr(action, 'target_angle')
    assert hasattr(action, 'boost')
    assert not action.boost # 7. Controller does not boost by default


def test_strategy_evaluate_heading_uses_projected_enemy_snake():
    s = Snake(1, 0, 0, 0)
    s.speed = Config.BASE_SPEED
    p = Perception(vision_radius=200)
    state = p.build(s, [s], [])
    state.visible_snakes = [
        PerceivedSnake(
            id=2,
            head=Vector2(75, 80),
            mass=100,
            distance=110,
            radius=10.0,
            speed=Config.BASE_SPEED,
            heading=math.pi / 2,
        )
    ]
    
    strat = Strategy()
    res = strat._evaluate_heading(0.0, 1.0, 0.0, state, 10.0)
    assert res.enemy_head_intercept_risk == 0.0
    
    state.visible_snakes[0].heading = -math.pi / 2
    res = strat._evaluate_heading(0.0, 1.0, 0.0, state, 10.0)
    assert res.enemy_head_intercept_risk == 2.0


def test_strategy_evaluate_heading_uses_dynamic_enemy_radius():
    s = Snake(1, 0, 0, 0)
    s.speed = Config.BASE_SPEED
    p = Perception(vision_radius=200)
    state = p.build(s, [s], [])
    
    state.visible_snakes = [
        PerceivedSnake(
            id=2,
            head=Vector2(75, 30),
            mass=100,
            distance=82,
            radius=1.0,
            speed=Config.BASE_SPEED,
            heading=-math.pi / 2,
        )
    ]
    
    strat = Strategy()
    res_safe = strat._evaluate_heading(0.0, 1.0, 0.0, state, 10.0)
    assert res_safe.enemy_head_intercept_risk == 0.0
    
    state.visible_snakes[0].radius = 40.0
    
    res_danger = strat._evaluate_heading(0.0, 1.0, 0.0, state, 10.0)
    assert res_danger.enemy_head_intercept_risk == 2.0


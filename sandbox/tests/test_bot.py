import math
from sandbox.vector import Vector2
from sandbox.snake import Snake
from sandbox.food import FoodItem
from sandbox.config import Config
from sandbox.bot.perception import Perception
from sandbox.bot.strategy import Strategy, StrategyMode
from sandbox.bot.steering import Steering
from sandbox.bot.controller import BotController

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
    f1 = FoodItem(10, 0, 1.0) # Visible
    f2 = FoodItem(Config.AI_VISION_RADIUS + 100, 0, 1.0) # Outside vision
    
    p = Perception(vision_radius=Config.AI_VISION_RADIUS)
    state = p.build(s, [s], [f1, f2])
    
    assert len(state.visible_food) == 1
    assert state.visible_food[0].pos.x == 10

def test_strategy_boundary_avoidance():
    s = Snake(1, Config.WORLD_RADIUS - 100, 0, 0) # Near edge
    p = Perception()
    state = p.build(s, [s], [])
    
    strat = Strategy()
    result = strat.decide(state)
    assert result.mode == StrategyMode.AVOID_BOUNDARY

def test_strategy_food_seeking():
    s = Snake(1, 0, 0, 0) # Safe at center
    f1 = FoodItem(10, 0, 1.0)
    p = Perception()
    state = p.build(s, [s], [f1])
    
    strat = Strategy()
    result = strat.decide(state)
    assert result.mode == StrategyMode.SEEK_FOOD

def test_steering_valid_heading():
    s = Snake(1, 100, 100, 0)
    f = FoodItem(200, 100, 1.0)
    p = Perception()
    state = p.build(s, [s], [f])
    
    strat = Strategy()
    strat_result = strat.decide(state)
    
    steer = Steering()
    steer_result = steer.compute(strat_result, state)
    
    assert steer_result.heading == 0.0 # From (100,100) to (200,100) is 0 radians
    assert isinstance(steer_result.heading, float)

def test_controller_returns_action_no_boost():
    s = Snake(1, 0, 0, 0)
    f = FoodItem(100, 0, 1.0)
    
    controller = BotController(s)
    action = controller.update([s], [f])
    
    assert hasattr(action, 'target_angle')
    assert hasattr(action, 'boost')
    assert not action.boost # 7. Controller does not boost by default

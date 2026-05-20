import math
from sandbox.snake import Snake
from sandbox.config import Config

def test_snake_movement():
    s = Snake(0, 0, 0, 0.0) # pointing right
    s.update(1.0) # move 1 sec
    assert s.x > 0
    assert len(s.trail) > 1

def test_snake_turn():
    s = Snake(0, 0, 0, 0.0)
    s.target_angle = math.pi / 2
    s.update(1.0)
    assert s.angle > 0

def test_snake_boost_mass_cost():
    s = Snake(0, 0, 0, 0.0)
    s.mass = 20.0
    start_mass = s.mass
    s.boosting = True
    s.update(1.0)
    assert s.mass < start_mass

def test_snake_boost_blocked_below_min():
    s = Snake(0, 0, 0, 0.0)
    s.mass = Config.BOOST_MIN_MASS - 1
    s.boosting = True
    s.update(1.0)
    assert not s.boosting

from sandbox.collision import CollisionDetector
from sandbox.snake import Snake
from sandbox.config import Config

def test_boundary_death():
    s = Snake(0, Config.WORLD_RADIUS + 100, 0)
    dead = CollisionDetector.check_all([s])
    assert s in dead

def test_head_to_body_collision():
    s1 = Snake(1, 0, 0)
    s2 = Snake(2, 0, 0)
    s2.segments = [s1.pos.copy()] # s2 has a segment exactly at s1's head
    # Add dummy segments to avoid the "skip first 3" rule
    s2.segments = [(1000,1000), (1000,1000), (1000,1000), s1.pos.copy()]
    
    dead = CollisionDetector.check_all([s1, s2])
    assert s1 in dead
    assert s2 not in dead # s2's head isn't hitting anything

def test_self_collision_immunity():
    s1 = Snake(1, 0, 0)
    s1.segments = [(1000,1000), (1000,1000), (1000,1000), s1.pos.copy()]
    dead = CollisionDetector.check_all([s1])
    assert s1 not in dead

from __future__ import annotations
import math
from collections import deque
from sandbox.config import Config
from sandbox.vector import Vector2

class Snake:
    def __init__(self, snake_id: int, x: float, y: float, angle: float = 0.0):
        self.id = snake_id
        self.pos = Vector2(x, y)
        self.angle = angle
        self.target_angle = angle
        self.mass = Config.INITIAL_MASS
        self.alive = True
        self.boosting = False
        
        # Trail history (stores Vector2)
        self.trail: deque[Vector2] = deque()
        self.segments: list[Vector2] = []
        
        # Initialize trail
        self.segment_count = Config.INITIAL_SEGMENTS
        for i in range(self.segment_count * int(Config.SEGMENT_SPACING) + 50):
            self.trail.appendleft(Vector2(x - math.cos(angle) * i, y - math.sin(angle) * i))
            
        self.speed = Config.BASE_SPEED
        self.turn_rate = Config.BASE_TURN_RATE
        self.radius = Config.get_radius(self.mass)
        
        self.recompute_segments()

    @property
    def x(self) -> float:
        return self.pos.x
        
    @property
    def y(self) -> float:
        return self.pos.y

    def die(self):
        self.alive = False
        self.boosting = False

    def update(self, dt: float):
        if not self.alive:
            return

        # Handle boost
        if self.boosting and self.mass > Config.BOOST_MIN_MASS:
            self.mass -= Config.BOOST_MASS_COST * dt
            current_speed = Config.BASE_SPEED * Config.BOOST_SPEED_MULTIPLIER
            if self.mass <= Config.BOOST_MIN_MASS:
                self.boosting = False
        else:
            self.boosting = False
            current_speed = Config.BASE_SPEED

        # Update angle towards target_angle
        diff = self.target_angle - self.angle
        # Normalize diff to [-pi, pi]
        while diff > math.pi: diff -= 2 * math.pi
        while diff < -math.pi: diff += 2 * math.pi
        
        max_turn = self.turn_rate * dt
        self.angle += max(-max_turn, min(max_turn, diff))

        # Advance head
        self.pos.x += math.cos(self.angle) * current_speed * dt
        self.pos.y += math.sin(self.angle) * current_speed * dt
        self.trail.appendleft(self.pos.copy())

        self.recompute_segments()

    def recompute_segments(self):
        target_segments = Config.INITIAL_SEGMENTS + int((self.mass - Config.INITIAL_MASS) / Config.MASS_PER_SEGMENT)
        self.segment_count = max(Config.INITIAL_SEGMENTS, target_segments)
        self.radius = Config.get_radius(self.mass)

        self.segments = []
        trail_len = len(self.trail)
        for i in range(self.segment_count):
            trail_index = int(i * Config.SEGMENT_SPACING)
            if trail_index < trail_len:
                self.segments.append(self.trail[trail_index])
            else:
                self.segments.append(self.trail[-1] if self.trail else self.pos.copy())

        # Trim trail
        max_trail = int(self.segment_count * Config.SEGMENT_SPACING) + 50
        while len(self.trail) > max_trail:
            self.trail.pop()

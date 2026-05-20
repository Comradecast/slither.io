from __future__ import annotations
from dataclasses import dataclass, field
from sandbox.vector import Vector2
from sandbox.config import Config

@dataclass
class PerceivedFood:
    pos: Vector2
    value: float
    distance: float

@dataclass
class PerceivedSnake:
    id: int
    head: Vector2
    mass: float
    distance: float

@dataclass
class PerceptionState:
    """The bot's perception of the world."""
    my_id: int
    my_head: Vector2
    my_angle: float
    my_mass: float
    my_speed: float
    boundary_distance: float
    visible_food: list[PerceivedFood] = field(default_factory=list)
    visible_snakes: list[PerceivedSnake] = field(default_factory=list)


class Perception:
    """Builds a PerceptionState from raw game state."""
    
    def __init__(self, vision_radius: float = Config.AI_VISION_RADIUS):
        self.vision_radius = vision_radius

    def build(self, my_snake, snakes: list, food_items: list) -> PerceptionState:
        # Distance to boundary from head
        dist_to_center = my_snake.pos.length()
        boundary_distance = Config.WORLD_RADIUS - dist_to_center

        visible_food = []
        for f in food_items:
            dist = my_snake.pos.distance_to(f.pos)
            if dist <= self.vision_radius:
                visible_food.append(PerceivedFood(f.pos.copy(), f.value, dist))
                
        # Sort food by distance
        visible_food.sort(key=lambda x: x.distance)

        visible_snakes = []
        for s in snakes:
            if s.id == my_snake.id or not s.alive:
                continue
            dist = my_snake.pos.distance_to(s.pos)
            if dist <= self.vision_radius:
                visible_snakes.append(PerceivedSnake(s.id, s.pos.copy(), s.mass, dist))

        return PerceptionState(
            my_id=my_snake.id,
            my_head=my_snake.pos.copy(),
            my_angle=my_snake.angle,
            my_mass=my_snake.mass,
            my_speed=my_snake.speed,
            boundary_distance=boundary_distance,
            visible_food=visible_food,
            visible_snakes=visible_snakes
        )

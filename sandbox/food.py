from __future__ import annotations
import random
import math
from sandbox.config import Config
from sandbox.vector import Vector2

class FoodItem:
    def __init__(self, x: float, y: float, value: float):
        self.pos = Vector2(x, y)
        self.value = value
        self.radius = Config.NATURAL_FOOD_RADIUS

    @property
    def x(self) -> float:
        return self.pos.x

    @property
    def y(self) -> float:
        return self.pos.y


class FoodManager:
    def __init__(self):
        self.items: list[FoodItem] = []

    def spawn_food(self, dt: float):
        """Spawn natural food to maintain target count."""
        deficit = Config.NATURAL_FOOD_COUNT - len(self.items)
        to_spawn = min(deficit, int(Config.NATURAL_FOOD_SPAWN_RATE * dt) + 1)
        
        for _ in range(max(0, to_spawn)):
            angle = random.random() * math.pi * 2
            r = math.sqrt(random.random()) * (Config.WORLD_RADIUS * 0.95)
            x = math.cos(angle) * r
            y = math.sin(angle) * r
            value = random.uniform(Config.NATURAL_FOOD_MIN_VALUE, Config.NATURAL_FOOD_MAX_VALUE)
            self.items.append(FoodItem(x, y, value))

    def try_eat(self, snake) -> float:
        """Check if snake head can eat any food. Returns mass gained."""
        mass_gained = 0.0
        collection_radius = snake.radius + Config.FOOD_COLLECTION_MARGIN
        
        eaten = []
        for food in self.items:
            if snake.pos.distance_to(food.pos) < collection_radius:
                mass_gained += food.value
                eaten.append(food)
                
        for food in eaten:
            self.items.remove(food)
            
        return mass_gained

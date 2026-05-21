from __future__ import annotations
from dataclasses import dataclass
from sandbox.config import Config
from sandbox.food import FoodItem
from sandbox.vector import Vector2
from sandbox.world import World


SCENARIO_NAMES = (
    "baseline_farming",
    "boundary_pressure",
    "nearby_threat",
    "mixed_food_and_threat",
)


@dataclass
class Scenario:
    name: str
    world: World
    bot_id: int


def create_scenario(name: str) -> Scenario:
    if name == "baseline_farming":
        return _baseline_farming()
    if name == "boundary_pressure":
        return _boundary_pressure()
    if name == "nearby_threat":
        return _nearby_threat()
    if name == "mixed_food_and_threat":
        return _mixed_food_and_threat()
    raise ValueError(f"Unknown scenario: {name}")


def _spawn_bot(world: World, x: float, y: float, angle: float = 0.0):
    bot = world.spawn_snake(1, x, y, is_bot=True, track_metrics=True)
    bot.angle = angle
    bot.target_angle = angle
    return bot


def _baseline_farming() -> Scenario:
    world = World()
    bot = _spawn_bot(world, 0.0, 0.0)
    _add_food_line(world)
    return Scenario("baseline_farming", world, bot.id)


def _boundary_pressure() -> Scenario:
    world = World()
    bot = _spawn_bot(world, Config.WORLD_RADIUS - 45.0, 0.0, 0.0)
    _add_food_line(world, start_x=Config.WORLD_RADIUS - 180.0, count=6, step=-30.0)
    return Scenario("boundary_pressure", world, bot.id)


def _nearby_threat() -> Scenario:
    world = World()
    bot = _spawn_bot(world, 0.0, 0.0)
    enemy = world.spawn_snake(2, 250.0, 0.0)
    enemy.segments = [
        Vector2(65.0, 0.0),
        Vector2(75.0, 0.0),
        Vector2(85.0, 0.0),
        Vector2(110.0, 0.0),
    ]
    _add_food_line(world, start_x=120.0, count=6)
    return Scenario("nearby_threat", world, bot.id)


def _mixed_food_and_threat() -> Scenario:
    world = World()
    bot = _spawn_bot(world, 0.0, 0.0)
    enemy = world.spawn_snake(2, 250.0, 0.0)
    enemy.segments = [
        Vector2(55.0, 0.0),
        Vector2(65.0, 0.0),
        Vector2(75.0, 0.0),
        Vector2(100.0, 0.0),
    ]
    world.food_manager.items.append(FoodItem(60.0, 0.0, 5.0))
    world.food_manager.items.append(FoodItem(40.0, 90.0, 3.0))
    world.food_manager.items.append(FoodItem(90.0, 90.0, 2.0))
    return Scenario("mixed_food_and_threat", world, bot.id)


def _add_food_line(world: World, start_x: float = 80.0, count: int = 12, step: float = 35.0):
    for index in range(count):
        x = start_x + index * step
        value = Config.NATURAL_FOOD_MIN_VALUE + (index % 4)
        world.food_manager.items.append(FoodItem(x, 0.0, value))

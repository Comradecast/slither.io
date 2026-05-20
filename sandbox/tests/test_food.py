import math

from sandbox.food import FoodManager, FoodItem
from sandbox.config import Config
from sandbox.snake import Snake

def test_food_spawn():
    fm = FoodManager()
    fm.spawn_food(1.0)
    assert len(fm.items) > 0

def test_food_collection():
    fm = FoodManager()
    fm.items.append(FoodItem(0, 0, 5.0))
    s = Snake(0, 0, 0) # head at (0,0)
    mass_gained = fm.try_eat(s)
    assert mass_gained == 5.0
    assert len(fm.items) == 0

def test_food_collection_inside_margin():
    fm = FoodManager()
    s = Snake(0, 0, 0) # head at (0,0)
    pickup_distance = s.radius + Config.FOOD_COLLECTION_MARGIN - 0.1
    fm.items.append(FoodItem(pickup_distance, 0, 5.0))

    mass_gained = fm.try_eat(s)

    assert mass_gained == 5.0
    assert len(fm.items) == 0

def test_food_collection_outside_margin():
    fm = FoodManager()
    s = Snake(0, 0, 0) # head at (0,0)
    pickup_distance = s.radius + Config.FOOD_COLLECTION_MARGIN + 0.1
    fm.items.append(FoodItem(pickup_distance, 0, 5.0))

    mass_gained = fm.try_eat(s)

    assert mass_gained == 0.0
    assert len(fm.items) == 1

def test_food_vacuum_moves_food_inside_radius_closer():
    fm = FoodManager()
    s = Snake(0, 0, 0) # head at (0,0)
    food = FoodItem(Config.FOOD_VACUUM_RADIUS - 1.0, 0, 5.0)
    fm.items.append(food)
    initial_distance = s.pos.distance_to(food.pos)

    fm.apply_vacuum(s, 0.1)

    assert s.pos.distance_to(food.pos) < initial_distance

def test_food_vacuum_does_not_move_food_outside_radius():
    fm = FoodManager()
    s = Snake(0, 0, 0) # head at (0,0)
    food = FoodItem(Config.FOOD_VACUUM_RADIUS + 1.0, 0, 5.0)
    fm.items.append(food)
    initial_x = food.x
    initial_y = food.y

    fm.apply_vacuum(s, 0.1)

    assert food.x == initial_x
    assert food.y == initial_y

def test_food_vacuum_does_not_move_food_behind_snake():
    fm = FoodManager()
    s = Snake(0, 0, 0) # facing +x
    food = FoodItem(-20.0, 0, 5.0)
    fm.items.append(food)
    initial_x = food.x
    initial_y = food.y

    fm.apply_vacuum(s, 0.1)

    assert food.x == initial_x
    assert food.y == initial_y

def test_food_vacuum_does_not_move_food_outside_cone():
    fm = FoodManager()
    s = Snake(0, 0, 0) # facing +x
    distance = Config.FOOD_VACUUM_RADIUS * 0.5
    angle = (Config.FOOD_VACUUM_CONE_ANGLE / 2.0) + 0.1
    food = FoodItem(math.cos(angle) * distance, math.sin(angle) * distance, 5.0)
    fm.items.append(food)
    initial_x = food.x
    initial_y = food.y

    fm.apply_vacuum(s, 0.1)

    assert food.x == initial_x
    assert food.y == initial_y

def test_food_vacuum_cone_edge_is_deterministic():
    fm = FoodManager()
    s = Snake(0, 0, 0) # facing +x
    distance = Config.FOOD_VACUUM_RADIUS * 0.5
    edge_angle = Config.FOOD_VACUUM_CONE_ANGLE / 2.0
    food = FoodItem(math.cos(edge_angle) * distance, math.sin(edge_angle) * distance, 5.0)
    fm.items.append(food)
    initial_distance = s.pos.distance_to(food.pos)

    fm.apply_vacuum(s, 0.1)

    assert s.pos.distance_to(food.pos) < initial_distance

def test_food_vacuum_pulls_close_food_farther_than_edge_food():
    fm = FoodManager()
    s = Snake(0, 0, 0) # facing +x
    close_food = FoodItem(Config.FOOD_VACUUM_RADIUS * 0.25, 0, 5.0)
    far_food = FoodItem(Config.FOOD_VACUUM_RADIUS * 0.9, 0, 5.0)
    fm.items.extend([close_food, far_food])
    close_initial_distance = s.pos.distance_to(close_food.pos)
    far_initial_distance = s.pos.distance_to(far_food.pos)

    fm.apply_vacuum(s, 0.1)

    close_move = close_initial_distance - s.pos.distance_to(close_food.pos)
    far_move = far_initial_distance - s.pos.distance_to(far_food.pos)
    assert close_move > far_move

def test_food_collects_after_vacuum_enters_pickup_range():
    fm = FoodManager()
    s = Snake(0, 0, 0) # head at (0,0)
    collection_radius = s.radius + Config.FOOD_COLLECTION_MARGIN
    food = FoodItem(collection_radius + 1.0, 0, 5.0)
    fm.items.append(food)

    fm.apply_vacuum(s, 0.1)
    mass_gained = fm.try_eat(s)

    assert mass_gained == 5.0
    assert len(fm.items) == 0

def test_food_vacuum_does_not_overshoot_snake_head():
    fm = FoodManager()
    s = Snake(0, 0, 0) # head at (0,0)
    food = FoodItem(5.0, 0, 5.0)
    fm.items.append(food)

    fm.apply_vacuum(s, 1.0)

    assert food.x == 0.0
    assert food.y == 0.0

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

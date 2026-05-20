from __future__ import annotations
from sandbox.snake import Snake
from sandbox.food import FoodManager
from sandbox.collision import CollisionDetector
from sandbox.bot.controller import BotController

class World:
    def __init__(self):
        self.snakes: list[Snake] = []
        self.food_manager = FoodManager()
        self.bot_controllers: dict[int, BotController] = {}
        self.tick = 0
        self.elapsed = 0.0

    def spawn_snake(self, snake_id: int, x: float, y: float, is_bot: bool = False) -> Snake:
        snake = Snake(snake_id, x, y)
        self.snakes.append(snake)
        if is_bot:
            self.bot_controllers[snake.id] = BotController(snake)
        return snake

    def update(self, dt: float):
        # 0. Bot controllers
        for bot_id, controller in self.bot_controllers.items():
            controller.update(self.snakes, self.food_manager.items)
            
        # 1. Update snakes
        for snake in self.snakes:
            snake.update(dt)

        # 2. Collision detection
        dead_snakes = CollisionDetector.check_all(self.snakes)
        for dead_snake in dead_snakes:
            dead_snake.die()

        # 3. Food collection
        for snake in self.snakes:
            if snake.alive:
                mass_gained = self.food_manager.try_eat(snake)
                snake.mass += mass_gained

        # 4. Food spawning
        self.food_manager.spawn_food(dt)

        self.tick += 1
        self.elapsed += dt

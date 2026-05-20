from __future__ import annotations
from sandbox.snake import Snake
from sandbox.food import FoodManager
from sandbox.collision import CollisionDetector
from sandbox.bot.controller import BotController
from sandbox.logging_.game_logger import GameLogger
from sandbox.logging_.metrics import MetricsTracker

class World:
    def __init__(self, logger: GameLogger | None = None):
        self.snakes: list[Snake] = []
        self.food_manager = FoodManager()
        self.bot_controllers: dict[int, BotController] = {}
        self.metrics_trackers: dict[int, MetricsTracker] = {}
        self.logger = logger
        self.tick = 0
        self.elapsed = 0.0

    def spawn_snake(self, snake_id: int, x: float, y: float, is_bot: bool = False, track_metrics: bool = False) -> Snake:
        snake = Snake(snake_id, x, y)
        self.snakes.append(snake)
        
        metrics = MetricsTracker() if track_metrics else None
        if metrics:
            self.metrics_trackers[snake.id] = metrics
            
        if is_bot:
            self.bot_controllers[snake.id] = BotController(snake, logger=self.logger, metrics=metrics)
            
        return snake

    def update(self, dt: float):
        # 0. Bot controllers
        for bot_id, controller in self.bot_controllers.items():
            controller.update(self.snakes, self.food_manager.items, self.tick)
            
        # 1. Update snakes and metrics
        for snake in self.snakes:
            snake.update(dt)
            metrics = self.metrics_trackers.get(snake.id)
            if metrics and snake.alive:
                metrics.record_tick()
                metrics.record_mass(snake.mass)
                metrics.record_boost(snake.boosting)

        # 2. Collision detection
        dead_snakes = CollisionDetector.check_all(self.snakes)
        for dead_snake in dead_snakes:
            dead_snake.die()
            metrics = self.metrics_trackers.get(dead_snake.id)
            if metrics:
                metrics.record_death("collision or boundary")

        # 3. Food collection
        for snake in self.snakes:
            if snake.alive:
                self.food_manager.apply_vacuum(snake, dt)
                mass_gained = self.food_manager.try_eat(snake)
                if mass_gained > 0:
                    snake.mass += mass_gained
                    metrics = self.metrics_trackers.get(snake.id)
                    if metrics:
                        # Assuming 1 pellet eaten per frame for simplicity of tracking count in this basic version,
                        # or we can just count the exact number of items if try_eat returned items instead of mass.
                        # For now, if mass_gained > 0, we'll increment food eaten by 1.
                        metrics.record_food_eaten()

        # 4. Food spawning
        self.food_manager.spawn_food(dt)

        self.tick += 1
        self.elapsed += dt

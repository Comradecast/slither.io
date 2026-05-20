from __future__ import annotations
from dataclasses import dataclass
from sandbox.bot.perception import Perception
from sandbox.bot.strategy import Strategy
from sandbox.bot.steering import Steering
from sandbox.logging_.game_logger import GameLogger
from sandbox.logging_.metrics import MetricsTracker

@dataclass
class BotAction:
    target_angle: float
    boost: bool

class BotController:
    """Orchestrates the bot's decision pipeline."""
    
    def __init__(self, snake, logger: GameLogger | None = None, metrics: MetricsTracker | None = None):
        self.snake = snake
        self.logger = logger
        self.metrics = metrics
        self.perception = Perception()
        self.strategy = Strategy()
        self.steering = Steering()

    def update(self, snakes: list, food_items: list, tick: int = 0) -> BotAction:
        if not self.snake.alive:
            return BotAction(target_angle=self.snake.angle, boost=False)
            
        # 1. Perceive world
        perception_state = self.perception.build(self.snake, snakes, food_items)
        
        # 2. Select strategy
        strategy_result = self.strategy.decide(perception_state)
        
        # 3. Compute steering
        steering_result = self.steering.compute(strategy_result, perception_state)
        
        # 4. Action (no boosting in Phase 3 default)
        action = BotAction(target_angle=steering_result.heading, boost=False)
        
        # Log decision
        if self.logger:
            nearest_food_dist = perception_state.visible_food[0].distance if perception_state.visible_food else None
            self.logger.log_decision(
                tick=tick,
                snake_id=self.snake.id,
                pos_x=self.snake.pos.x,
                pos_y=self.snake.pos.y,
                mass=self.snake.mass,
                heading=self.snake.angle,
                strategy_mode=strategy_result.mode.value,
                target_pos_x=strategy_result.target_pos.x if strategy_result.target_pos else None,
                target_pos_y=strategy_result.target_pos.y if strategy_result.target_pos else None,
                steering_heading=steering_result.heading,
                boost=action.boost,
                nearest_food_distance=nearest_food_dist,
                boundary_distance=perception_state.boundary_distance
            )
            
        if self.metrics:
            self.metrics.record_decision()
        
        # Apply to snake
        self.snake.target_angle = action.target_angle
        self.snake.boosting = action.boost
        
        return action

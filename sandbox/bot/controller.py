from __future__ import annotations
from dataclasses import dataclass
from sandbox.bot.perception import Perception
from sandbox.bot.strategy import Strategy
from sandbox.bot.steering import Steering

@dataclass
class BotAction:
    target_angle: float
    boost: bool

class BotController:
    """Orchestrates the bot's decision pipeline."""
    
    def __init__(self, snake):
        self.snake = snake
        self.perception = Perception()
        self.strategy = Strategy()
        self.steering = Steering()

    def update(self, snakes: list, food_items: list) -> BotAction:
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
        
        # Apply to snake
        self.snake.target_angle = action.target_angle
        self.snake.boosting = action.boost
        
        return action

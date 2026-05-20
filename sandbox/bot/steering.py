from __future__ import annotations
from dataclasses import dataclass
import math
from sandbox.bot.perception import PerceptionState
from sandbox.bot.strategy import StrategyResult, StrategyMode

@dataclass
class SteeringResult:
    heading: float

class Steering:
    """Translates strategy into a heading angle."""

    def compute(self, strategy_res: StrategyResult, perception: PerceptionState) -> SteeringResult:
        if strategy_res.mode == StrategyMode.AVOID_BOUNDARY and strategy_res.target_pos:
            # Steer towards center
            dx = strategy_res.target_pos.x - perception.my_head.x
            dy = strategy_res.target_pos.y - perception.my_head.y
            return SteeringResult(heading=math.atan2(dy, dx))
            
        elif strategy_res.mode == StrategyMode.SEEK_FOOD and strategy_res.target_pos:
            # Steer towards food
            dx = strategy_res.target_pos.x - perception.my_head.x
            dy = strategy_res.target_pos.y - perception.my_head.y
            return SteeringResult(heading=math.atan2(dy, dx))
            
        else: # WANDER or fallback
            # Just keep current heading for Phase 3 simple wander
            return SteeringResult(heading=perception.my_angle)

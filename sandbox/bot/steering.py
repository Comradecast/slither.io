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
            
        elif strategy_res.mode == StrategyMode.AVOID_THREAT and strategy_res.target_pos:
            # Smooth defensive steering (steer perpendicular to the threat rather than 180 hard turn)
            angle_to_threat = math.atan2(strategy_res.target_pos.y - perception.my_head.y, 
                                         strategy_res.target_pos.x - perception.my_head.x)
            angle_diff = (angle_to_threat - perception.my_angle)
            angle_diff = (angle_diff + math.pi) % (2 * math.pi) - math.pi
            
            # If threat is on the right, steer left (-pi/2)
            # If threat is on the left, steer right (+pi/2)
            if angle_diff >= 0:
                target_heading = perception.my_angle - math.pi/2
            else:
                target_heading = perception.my_angle + math.pi/2
                
            return SteeringResult(heading=target_heading)
            
        elif strategy_res.mode == StrategyMode.SEEK_FOOD and strategy_res.target_pos:
            # Steer towards food
            dx = strategy_res.target_pos.x - perception.my_head.x
            dy = strategy_res.target_pos.y - perception.my_head.y
            return SteeringResult(heading=math.atan2(dy, dx))
            
        else: # WANDER or fallback
            # Just keep current heading for Phase 3 simple wander
            return SteeringResult(heading=perception.my_angle)

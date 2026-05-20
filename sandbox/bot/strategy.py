from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from sandbox.bot.perception import PerceptionState
from sandbox.vector import Vector2

class StrategyMode(Enum):
    AVOID_BOUNDARY = "AVOID_BOUNDARY"
    SEEK_FOOD = "SEEK_FOOD"
    WANDER = "WANDER"

@dataclass
class StrategyResult:
    mode: StrategyMode
    target_pos: Vector2 | None = None
    
class Strategy:
    """High-level decision making."""
    
    BOUNDARY_DANGER_THRESHOLD = 300.0

    def decide(self, perception: PerceptionState) -> StrategyResult:
        # 1. Boundary avoidance takes highest priority
        if perception.boundary_distance < self.BOUNDARY_DANGER_THRESHOLD:
            # Target the center of the map
            return StrategyResult(mode=StrategyMode.AVOID_BOUNDARY, target_pos=Vector2(0, 0))
            
        # 2. Seek nearest food
        if perception.visible_food:
            nearest_food = perception.visible_food[0]
            return StrategyResult(mode=StrategyMode.SEEK_FOOD, target_pos=nearest_food.pos)
            
        # 3. Wander fallback
        return StrategyResult(mode=StrategyMode.WANDER, target_pos=None)

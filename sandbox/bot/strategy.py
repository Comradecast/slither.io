from __future__ import annotations
from enum import Enum
from dataclasses import dataclass
from sandbox.vector import Vector2
from sandbox.bot.perception import PerceptionState
from sandbox.config import Config

class StrategyMode(Enum):
    WANDER = "wander"
    SEEK_FOOD = "seek_food"
    AVOID_BOUNDARY = "avoid_boundary"
    AVOID_THREAT = "avoid_threat"

@dataclass
class StrategyResult:
    mode: StrategyMode
    target_pos: Vector2 | None = None

class Strategy:
    """Decides the high-level goal based on perception."""
    
    def decide(self, perception: PerceptionState) -> StrategyResult:
        # 1. Boundary avoidance is highest priority
        if perception.boundary_distance < Config.BASE_RADIUS * 10:
            return StrategyResult(mode=StrategyMode.AVOID_BOUNDARY, target_pos=Vector2(0, 0))
            
        # 2. Threat avoidance
        if perception.nearest_threat is not None:
            # target_pos is the threat we want to avoid
            return StrategyResult(mode=StrategyMode.AVOID_THREAT, target_pos=perception.nearest_threat.pos)
            
        # 3. Seek food if safe
        if perception.visible_food:
            nearest_food = perception.visible_food[0]
            return StrategyResult(mode=StrategyMode.SEEK_FOOD, target_pos=nearest_food.pos)
            
        # 4. Default: wander
        return StrategyResult(mode=StrategyMode.WANDER, target_pos=None)

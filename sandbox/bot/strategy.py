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
    defensive_reason: str | None = None
    food_score: float | None = None

class Strategy:
    """Decides the high-level goal based on perception."""

    FOOD_VALUE_WEIGHT = 100.0
    FOOD_DISTANCE_PENALTY = 1.0
    FOOD_FRONT_BONUS = 25.0
    FOOD_BEHIND_PENALTY = 75.0
    FOOD_THREAT_RADIUS = Config.BASE_RADIUS * 12.0
    FOOD_THREAT_PENALTY = 250.0
    FOOD_BLOCKED_BY_THREAT_PENALTY = 200.0
    
    def decide(self, perception: PerceptionState) -> StrategyResult:
        # 1. Boundary avoidance is highest priority
        if perception.boundary_distance < Config.BASE_RADIUS * 10:
            return StrategyResult(mode=StrategyMode.AVOID_BOUNDARY, target_pos=Vector2(0, 0), defensive_reason="Boundary proximity")
            
        # 2. Threat avoidance (using highest scored threat)
        if perception.highest_threat is not None:
            # target_pos is the threat we want to avoid
            reason = "Forward danger" if perception.highest_threat.in_forward_cone else "Nearby body segment"
            return StrategyResult(mode=StrategyMode.AVOID_THREAT, target_pos=perception.highest_threat.pos, defensive_reason=reason)
            
        # 3. Seek food if safe
        if perception.visible_food:
            best_food = max(perception.visible_food, key=lambda food: self.score_food(food, perception))
            return StrategyResult(
                mode=StrategyMode.SEEK_FOOD,
                target_pos=best_food.pos,
                food_score=self.score_food(best_food, perception),
            )
            
        # 4. Default: wander
        return StrategyResult(mode=StrategyMode.WANDER, target_pos=None)

    def score_food(self, food, perception: PerceptionState) -> float:
        score = (food.value * self.FOOD_VALUE_WEIGHT) - (food.distance * self.FOOD_DISTANCE_PENALTY)
        score += self.FOOD_FRONT_BONUS if food.in_front else -self.FOOD_BEHIND_PENALTY

        for threat in perception.visible_threats:
            if food.pos.distance_to(threat.pos) <= self.FOOD_THREAT_RADIUS:
                score -= self.FOOD_THREAT_PENALTY
            if (
                food.in_front
                and threat.in_forward_cone
                and threat.distance < food.distance
                and abs(threat.angle_diff - food.angle_diff) < 0.35
            ):
                score -= self.FOOD_BLOCKED_BY_THREAT_PENALTY

        return score

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass
from sandbox.vector import Vector2
from sandbox.bot.perception import PerceptionState
from sandbox.config import Config
import math

@dataclass
class EvalResult:
    collision_risk: float = 0.0
    open_space_score: float = 1.0
    enemy_head_intercept_risk: float = 0.0

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
    FOOD_THREAT_PENALTY = 250.0
    FOOD_BLOCKED_BY_THREAT_PENALTY = 200.0
    
    def __init__(self, profile="default"):
        self.profile = profile

    def _evaluate_heading(self, requested_angle: float, ray_dx: float, ray_dy: float, perception: PerceptionState, min_turn_radius: float) -> EvalResult:
        res = EvalResult()
        
        max_dist = max(perception.my_radius * 10, min_turn_radius * 2.0)
        
        # 1. Check body threats
        for threat in perception.visible_threats:
            tx = threat.pos.x - perception.my_head.x
            ty = threat.pos.y - perception.my_head.y
            
            t = tx * ray_dx + ty * ray_dy
            if 0 < t < max_dist:
                perp_dist = abs(-tx * ray_dy + ty * ray_dx)
                
                # Requirement: Ensure collision envelopes use perception.my_radius + threat.radius
                envelope = perception.my_radius + threat.radius
                
                if perp_dist < envelope:
                    res.collision_risk = 1.0
                    
        # 2. Check enemy head intercepts
        for enemy in perception.visible_snakes:
            ex = enemy.head.x - perception.my_head.x
            ey = enemy.head.y - perception.my_head.y
            
            t = ex * ray_dx + ey * ray_dy
            if 0 < t < max_dist:
                perp_dist = abs(-ex * ray_dy + ey * ray_dx)
                
                # Requirement: Ensure collision envelopes use perception.my_radius + enemy.radius
                envelope = perception.my_radius + enemy.radius
                
                if perp_dist < envelope:
                    # Requirement: Replace enemy_time = speed-magnitude logic with distance-to-intersection / enemy.speed
                    intersection_x = perception.my_head.x + ray_dx * t
                    intersection_y = perception.my_head.y + ray_dy * t
                    
                    enemy_dist_to_intersection = math.hypot(
                        intersection_x - enemy.head.x,
                        intersection_y - enemy.head.y,
                    )
                    
                    enemy_speed = getattr(enemy, "speed", Config.BASE_SPEED)
                    enemy_time = enemy_dist_to_intersection / max(1.0, enemy_speed)
                    my_time = t / max(1.0, perception.my_speed)
                    
                    if abs(my_time - enemy_time) < 0.5 or my_time > enemy_time:
                        res.enemy_head_intercept_risk = 2.0
        
        # 3. Check boundaries
        # Requirement: If a heading does not provide enough open distance for the bot to turn safely, mark it risky
        if perception.boundary_distance < min_turn_radius:
            res.open_space_score = 0.1
            
        return res

    def decide(self, perception: PerceptionState) -> StrategyResult:
        # 1. Boundary avoidance is highest priority
        if perception.boundary_distance < perception.my_radius * 10:
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
        
        dynamic_food_threat_radius = perception.my_radius * 12.0

        for threat in perception.visible_threats:
            if food.pos.distance_to(threat.pos) <= dynamic_food_threat_radius:
                score -= self.FOOD_THREAT_PENALTY
            if (
                food.in_front
                and threat.in_forward_cone
                and threat.distance < food.distance
                and abs(threat.angle_diff - food.angle_diff) < 0.35
            ):
                score -= self.FOOD_BLOCKED_BY_THREAT_PENALTY

        return score

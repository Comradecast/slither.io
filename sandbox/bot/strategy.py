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
    boundary_forward_distance: float | None = None
    enemy_head_intercept_time: float | None = None
    enemy_head_intercept_distance: float | None = None

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
    ENEMY_PROJECTION_SAMPLE_TIMES = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0)
    
    def __init__(self, profile="default"):
        self.profile = profile

    @staticmethod
    def boundary_distance_along_heading(head: Vector2, heading: float) -> float:
        """Return forward distance from head to the circular world boundary."""
        ray_dx = math.cos(heading)
        ray_dy = math.sin(heading)
        return Strategy.boundary_distance_along_ray(head, ray_dx, ray_dy)

    @staticmethod
    def boundary_distance_along_ray(head: Vector2, ray_dx: float, ray_dy: float) -> float:
        ray_length = math.hypot(ray_dx, ray_dy)
        if ray_length <= 0.0:
            return 0.0

        unit_dx = ray_dx / ray_length
        unit_dy = ray_dy / ray_length
        projection = head.x * unit_dx + head.y * unit_dy
        distance_from_center_sq = head.x * head.x + head.y * head.y
        radius_sq = Config.WORLD_RADIUS * Config.WORLD_RADIUS
        discriminant = projection * projection + radius_sq - distance_from_center_sq
        if discriminant <= 0.0:
            return 0.0

        return max(0.0, -projection + math.sqrt(discriminant))

    @staticmethod
    def project_enemy_positions(
        enemy_head: Vector2,
        speed: float,
        heading: float,
        sample_times: tuple[float, ...] | None = None,
        wanted_heading: float | None = None,
    ) -> list[tuple[float, Vector2]]:
        projected_heading = heading if wanted_heading is None else wanted_heading
        sample_times = sample_times or Strategy.ENEMY_PROJECTION_SAMPLE_TIMES
        return [
            (
                sample_time,
                Vector2(
                    enemy_head.x + math.cos(projected_heading) * speed * sample_time,
                    enemy_head.y + math.sin(projected_heading) * speed * sample_time,
                ),
            )
            for sample_time in sample_times
        ]

    def _evaluate_heading(self, requested_angle: float, ray_dx: float, ray_dy: float, perception: PerceptionState, min_turn_radius: float) -> EvalResult:
        res = EvalResult()
        
        max_projection_distance = perception.my_speed * max(self.ENEMY_PROJECTION_SAMPLE_TIMES)
        max_dist = max(perception.my_radius * 10, min_turn_radius * 2.0, max_projection_distance)
        
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
                    
        # 2. Check projected enemy head intercepts
        for enemy in perception.visible_snakes:
            envelope = perception.my_radius + enemy.radius
            enemy_speed = getattr(enemy, "speed", Config.BASE_SPEED)
            enemy_heading = getattr(enemy, "heading", 0.0)
            enemy_wanted_heading = getattr(enemy, "wanted_heading", None)
            projected_positions = self.project_enemy_positions(
                enemy.head,
                enemy_speed,
                enemy_heading,
                wanted_heading=enemy_wanted_heading,
            )

            for enemy_time, projected_head in projected_positions:
                ex = projected_head.x - perception.my_head.x
                ey = projected_head.y - perception.my_head.y
                t = ex * ray_dx + ey * ray_dy
                if 0 < t < max_dist:
                    perp_dist = abs(-ex * ray_dy + ey * ray_dx)
                    my_time = t / max(1.0, perception.my_speed)

                    if perp_dist < envelope and abs(my_time - enemy_time) < 0.5:
                        res.enemy_head_intercept_risk = 2.0
                        res.enemy_head_intercept_time = enemy_time
                        res.enemy_head_intercept_distance = t
                        break

            if res.enemy_head_intercept_risk > 1.5:
                break
        
        # 3. Check heading-aware boundary space
        boundary_forward_distance = self.boundary_distance_along_ray(
            perception.my_head,
            ray_dx,
            ray_dy,
        )
        res.boundary_forward_distance = boundary_forward_distance
        if boundary_forward_distance < min_turn_radius:
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

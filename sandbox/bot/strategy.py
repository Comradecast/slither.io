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


@dataclass
class LootCluster:
    foods: list
    total_value: float
    pellet_count: int
    center: Vector2
    nearest_distance: float
    average_distance: float
    high_value_pellet_count: int
    score: float


@dataclass
class LootApproach:
    cluster: LootCluster
    target: Vector2
    target_kind: str
    score: float

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
    loot_cluster_score: float | None = None
    loot_cluster_total_value: float | None = None
    loot_cluster_pellet_count: int | None = None
    loot_cluster_target: Vector2 | None = None
    loot_cluster_target_kind: str | None = None
    loot_cluster_approach: Vector2 | None = None

class Strategy:
    """Decides the high-level goal based on perception."""

    FOOD_VALUE_WEIGHT = 100.0
    FOOD_DISTANCE_PENALTY = 1.0
    FOOD_FRONT_BONUS = 25.0
    FOOD_BEHIND_PENALTY = 75.0
    FOOD_THREAT_PENALTY = 250.0
    FOOD_BLOCKED_BY_THREAT_PENALTY = 200.0
    ENEMY_PROJECTION_SAMPLE_TIMES = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0)
    LOOT_CLUSTER_DISTANCE = 60.0
    LOOT_CLUSTER_TOTAL_VALUE_THRESHOLD = 15.0
    LOOT_CLUSTER_HIGH_VALUE_THRESHOLD = 5.0
    LOOT_CLUSTER_HIGH_VALUE_COUNT_THRESHOLD = 3
    LOOT_CLUSTER_MIN_PELLETS = 3
    LOOT_CLUSTER_COUNT_BONUS = 20.0
    LOOT_CLUSTER_NEAREST_DISTANCE_PENALTY = 0.75
    LOOT_CLUSTER_AVERAGE_DISTANCE_PENALTY = 0.25
    LOOT_CLUSTER_CENTER_APPROACH_BONUS = 1000.0
    LOOT_CLUSTER_HIGH_VALUE_APPROACH_BONUS = 25.0
    
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

    @classmethod
    def detect_loot_clusters(cls, visible_food: list) -> list[LootCluster]:
        ordered_food = sorted(
            visible_food,
            key=lambda food: (food.pos.x, food.pos.y, food.value, food.distance),
        )
        visited: set[int] = set()
        clusters: list[LootCluster] = []

        for start_index, _ in enumerate(ordered_food):
            if start_index in visited:
                continue

            group_indexes = []
            pending = [start_index]
            visited.add(start_index)
            while pending:
                current_index = pending.pop()
                current_food = ordered_food[current_index]
                group_indexes.append(current_index)

                for candidate_index, candidate_food in enumerate(ordered_food):
                    if candidate_index in visited:
                        continue
                    if (
                        current_food.pos.distance_to(candidate_food.pos)
                        <= cls.LOOT_CLUSTER_DISTANCE
                    ):
                        visited.add(candidate_index)
                        pending.append(candidate_index)

            foods = [ordered_food[index] for index in group_indexes]
            if not cls._is_high_value_cluster(foods):
                continue

            clusters.append(cls._build_loot_cluster(foods))

        clusters.sort(
            key=lambda cluster: (
                -cluster.score,
                cluster.nearest_distance,
                cluster.center.x,
                cluster.center.y,
            )
        )
        return clusters

    @classmethod
    def _is_high_value_cluster(cls, foods: list) -> bool:
        if len(foods) < cls.LOOT_CLUSTER_MIN_PELLETS:
            return False

        total_value = sum(food.value for food in foods)
        high_value_count = sum(
            1
            for food in foods
            if food.value >= cls.LOOT_CLUSTER_HIGH_VALUE_THRESHOLD
        )
        return (
            total_value >= cls.LOOT_CLUSTER_TOTAL_VALUE_THRESHOLD
            or high_value_count >= cls.LOOT_CLUSTER_HIGH_VALUE_COUNT_THRESHOLD
        )

    @classmethod
    def _build_loot_cluster(cls, foods: list) -> LootCluster:
        total_value = sum(food.value for food in foods)
        weighted_x = sum(food.pos.x * food.value for food in foods) / total_value
        weighted_y = sum(food.pos.y * food.value for food in foods) / total_value
        nearest_distance = min(food.distance for food in foods)
        average_distance = sum(food.distance for food in foods) / len(foods)
        high_value_count = sum(
            1
            for food in foods
            if food.value >= cls.LOOT_CLUSTER_HIGH_VALUE_THRESHOLD
        )
        score = (
            total_value * cls.FOOD_VALUE_WEIGHT
            + len(foods) * cls.LOOT_CLUSTER_COUNT_BONUS
            - nearest_distance * cls.LOOT_CLUSTER_NEAREST_DISTANCE_PENALTY
            - average_distance * cls.LOOT_CLUSTER_AVERAGE_DISTANCE_PENALTY
        )
        return LootCluster(
            foods=foods,
            total_value=total_value,
            pellet_count=len(foods),
            center=Vector2(weighted_x, weighted_y),
            nearest_distance=nearest_distance,
            average_distance=average_distance,
            high_value_pellet_count=high_value_count,
            score=score,
        )

    def _evaluate_target_heading(self, target_pos: Vector2, perception: PerceptionState) -> EvalResult | None:
        dx = target_pos.x - perception.my_head.x
        dy = target_pos.y - perception.my_head.y
        distance = math.hypot(dx, dy)
        if distance <= 0.0:
            return None

        requested_angle = math.atan2(dy, dx)
        min_turn_radius = perception.my_radius * 2.0 + (perception.my_mass / 100.0)
        return self._evaluate_heading(
            requested_angle,
            dx / distance,
            dy / distance,
            perception,
            min_turn_radius,
        )

    def _is_safe_target_heading(self, target_pos: Vector2, perception: PerceptionState) -> bool:
        eval_result = self._evaluate_target_heading(target_pos, perception)
        if eval_result is None:
            return False
        return (
            eval_result.collision_risk <= 0.5
            and eval_result.open_space_score >= 0.15
            and eval_result.enemy_head_intercept_risk <= 1.5
        )

    def loot_cluster_approach_candidates(
        self,
        cluster: LootCluster,
        perception: PerceptionState,
    ) -> list[LootApproach]:
        candidates = [
            LootApproach(
                cluster=cluster,
                target=cluster.center,
                target_kind="center",
                score=cluster.score + self.LOOT_CLUSTER_CENTER_APPROACH_BONUS,
            )
        ]

        ordered_foods = sorted(
            cluster.foods,
            key=lambda food: (
                food.distance,
                -food.value,
                food.pos.x,
                food.pos.y,
            ),
        )
        for food in ordered_foods:
            high_value_bonus = (
                self.LOOT_CLUSTER_HIGH_VALUE_APPROACH_BONUS
                if food.value >= self.LOOT_CLUSTER_HIGH_VALUE_THRESHOLD
                else 0.0
            )
            candidates.append(LootApproach(
                cluster=cluster,
                target=food.pos,
                target_kind="pellet",
                score=(
                    cluster.score
                    + food.value * self.FOOD_VALUE_WEIGHT
                    + high_value_bonus
                    - food.distance * self.FOOD_DISTANCE_PENALTY
                ),
            ))

        return sorted(
            candidates,
            key=lambda candidate: (
                -candidate.score,
                0 if candidate.target_kind == "center" else 1,
                candidate.target.x,
                candidate.target.y,
            ),
        )

    def _best_safe_loot_approach(self, perception: PerceptionState) -> LootApproach | None:
        for cluster in self.detect_loot_clusters(perception.visible_food):
            for candidate in self.loot_cluster_approach_candidates(cluster, perception):
                if self._is_safe_target_heading(candidate.target, perception):
                    return candidate
        return None

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
            best_food_score = self.score_food(best_food, perception)
            best_approach = self._best_safe_loot_approach(perception)
            if best_approach is not None and best_approach.cluster.score > best_food_score:
                return StrategyResult(
                    mode=StrategyMode.SEEK_FOOD,
                    target_pos=best_approach.target,
                    food_score=best_food_score,
                    loot_cluster_score=best_approach.cluster.score,
                    loot_cluster_total_value=best_approach.cluster.total_value,
                    loot_cluster_pellet_count=best_approach.cluster.pellet_count,
                    loot_cluster_target=best_approach.cluster.center,
                    loot_cluster_target_kind=best_approach.target_kind,
                    loot_cluster_approach=best_approach.target,
                )
            return StrategyResult(
                mode=StrategyMode.SEEK_FOOD,
                target_pos=best_food.pos,
                food_score=best_food_score,
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

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
    collision_threat_distance: float | None = None
    collision_threat_angle_deg: float | None = None
    collision_corridor_density: int = 0
    collision_forward_cone: bool = False
    collision_lateral_offset: float | None = None
    threat_receding: bool | None = None
    threat_persistent_frames: int | None = None
    threat_confidence: float | None = None
    enemy_intercept_heading_delta_deg: float | None = None


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


@dataclass(frozen=True)
class CompressionAnalysis:
    risk: float
    sector_count: int
    nearby_threat_count: int
    active: bool


@dataclass(frozen=True)
class CircleSqueezeAnalysis:
    active: bool
    sector_count: int
    nearby_threat_count: int
    largest_gap: float
    largest_gap_center: float
    closure_risk: float
    reason: str | None = None


@dataclass(frozen=True)
class EscapePlan:
    heading: float
    target: Vector2
    open_space_score: float
    corridor_density: int
    eval_result: EvalResult


@dataclass(frozen=True)
class PartialGuardPlan:
    cluster: LootCluster
    target: Vector2
    side: str
    reason: str
    score: float
    eval_result: EvalResult

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
    compression_risk: float | None = None
    enclosure_sector_count: int | None = None
    best_escape_heading: float | None = None
    escape_open_space_score: float | None = None
    anti_coil_escape_active: bool = False
    partial_guard_active: bool = False
    partial_guard_target: Vector2 | None = None
    partial_guard_side: str | None = None
    partial_guard_reason: str | None = None
    partial_guard_score: float | None = None
    circle_squeeze_counter_active: bool = False
    circle_squeeze_sector_count: int | None = None
    circle_squeeze_largest_gap_deg: float | None = None
    circle_squeeze_escape_heading: float | None = None
    circle_squeeze_escape_gap_center_deg: float | None = None
    circle_squeeze_closure_risk: float | None = None
    circle_squeeze_reason: str | None = None
    persistent_threat_count: int | None = None
    reacquired_threat_count: int | None = None
    recent_missing_threat_count: int | None = None
    closing_threat_count: int | None = None

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
    ANTI_COIL_DETECTION_RADIUS = 180.0
    ANTI_COIL_SECTOR_COUNT = 8
    ANTI_COIL_MIN_THREATS = 5
    ANTI_COIL_MIN_SECTORS = 4
    ANTI_COIL_ESCAPE_DISTANCE = 180.0
    ANTI_COIL_CORRIDOR_DISTANCE = 220.0
    ANTI_COIL_CORRIDOR_HALF_ANGLE = math.pi / 6
    ANTI_COIL_HEADING_SAMPLES = tuple(index * math.pi / 4 for index in range(8))
    ANTI_COIL_DENSITY_PENALTY = 150.0
    ANTI_COIL_BOUNDARY_DISTANCE_WEIGHT = 0.05
    PARTIAL_GUARD_PRESSURE_RADIUS = 260.0
    PARTIAL_GUARD_LANE_WIDTH = 120.0
    PARTIAL_GUARD_OFFSET_DISTANCE = 70.0
    PARTIAL_GUARD_PROTECTIVE_BONUS = 450.0
    PARTIAL_GUARD_DIRECT_APPROACH_MARGIN = 75.0
    PARTIAL_GUARD_DISTANCE_PENALTY = 0.5
    CIRCLE_SQUEEZE_DETECTION_RADIUS = 190.0
    CIRCLE_SQUEEZE_SECTOR_COUNT = 16
    CIRCLE_SQUEEZE_MIN_THREATS = 8
    CIRCLE_SQUEEZE_MIN_SECTORS = 9
    CIRCLE_SQUEEZE_MAX_LARGEST_GAP = math.radians(135.0)
    CIRCLE_SQUEEZE_ESCAPE_DISTANCE = 210.0
    CIRCLE_SQUEEZE_GAP_CENTER_BONUS = 350.0
    CIRCLE_SQUEEZE_BOUNDARY_DISTANCE_WEIGHT = 0.06
    CIRCLE_SQUEEZE_DENSITY_PENALTY = 175.0
    THREAT_MEMORY_CLOSING_DENSITY_PENALTY = 120.0
    THREAT_CORRIDOR_HARD_CENTER_RATIO = 0.55
    THREAT_CORRIDOR_CLOSE_DISTANCE_FACTOR = 1.25
    THREAT_CORRIDOR_SOFT_RISK = 0.4
    THREAT_CORRIDOR_PERSISTENCE_FRAMES = 2
    THREAT_CORRIDOR_DENSITY_DISTANCE = 220.0
    THREAT_CORRIDOR_DENSITY_HALF_ANGLE = math.pi / 8
    THREAT_INTERCEPT_HARD_TIME_DELTA = 0.35
    THREAT_INTERCEPT_SOFT_TIME_DELTA = 0.5
    THREAT_INTERCEPT_COMMIT_HEADING_DELTA = math.radians(120.0)
    IMMEDIATE_FORWARD_THREAT_DISTANCE = 180.0
    IMMEDIATE_LATERAL_THREAT_DISTANCE = 80.0
    DENSE_THREAT_FIELD_COUNT = 96
    DENSE_CLOSING_THREAT_COUNT = 24
    DENSE_CORRIDOR_THREAT_COUNT = 4
    
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

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        return (angle + math.pi) % (2 * math.pi) - math.pi

    @classmethod
    def analyze_compression(cls, perception: PerceptionState) -> CompressionAnalysis:
        nearby_threats = [
            threat
            for threat in perception.visible_threats
            if threat.distance <= cls.ANTI_COIL_DETECTION_RADIUS
        ]
        sectors: set[int] = set()
        sector_width = (2 * math.pi) / cls.ANTI_COIL_SECTOR_COUNT
        for threat in nearby_threats:
            angle = math.atan2(
                threat.pos.y - perception.my_head.y,
                threat.pos.x - perception.my_head.x,
            )
            normalized_angle = angle % (2 * math.pi)
            sectors.add(int(normalized_angle / sector_width))

        nearby_count = len(nearby_threats)
        sector_count = len(sectors)
        threat_ratio = nearby_count / cls.ANTI_COIL_MIN_THREATS
        sector_ratio = sector_count / cls.ANTI_COIL_MIN_SECTORS
        risk = min(threat_ratio, sector_ratio)
        active = (
            nearby_count >= cls.ANTI_COIL_MIN_THREATS
            and sector_count >= cls.ANTI_COIL_MIN_SECTORS
        )
        return CompressionAnalysis(
            risk=risk,
            sector_count=sector_count,
            nearby_threat_count=nearby_count,
            active=active,
        )

    @classmethod
    def analyze_circle_squeeze(cls, perception: PerceptionState) -> CircleSqueezeAnalysis:
        nearby_threats = [
            threat
            for threat in perception.visible_threats
            if threat.distance <= cls.CIRCLE_SQUEEZE_DETECTION_RADIUS
        ]
        sector_width = (2 * math.pi) / cls.CIRCLE_SQUEEZE_SECTOR_COUNT
        occupied: set[int] = set()
        for threat in nearby_threats:
            angle = math.atan2(
                threat.pos.y - perception.my_head.y,
                threat.pos.x - perception.my_head.x,
            ) % (2 * math.pi)
            occupied.add(int(angle / sector_width))

        largest_gap_sectors, gap_start = cls._largest_empty_sector_run(occupied)
        largest_gap = largest_gap_sectors * sector_width
        gap_center = (
            gap_start + (largest_gap_sectors / 2.0)
        ) * sector_width
        gap_center = cls._normalize_angle(gap_center)
        sector_count = len(occupied)
        nearby_count = len(nearby_threats)
        sector_ratio = sector_count / cls.CIRCLE_SQUEEZE_MIN_SECTORS
        threat_ratio = nearby_count / cls.CIRCLE_SQUEEZE_MIN_THREATS
        gap_ratio = (
            cls.CIRCLE_SQUEEZE_MAX_LARGEST_GAP / max(largest_gap, sector_width)
        )
        closure_risk = min(sector_ratio, threat_ratio, gap_ratio)
        active = (
            nearby_count >= cls.CIRCLE_SQUEEZE_MIN_THREATS
            and sector_count >= cls.CIRCLE_SQUEEZE_MIN_SECTORS
            and largest_gap <= cls.CIRCLE_SQUEEZE_MAX_LARGEST_GAP
        )
        return CircleSqueezeAnalysis(
            active=active,
            sector_count=sector_count,
            nearby_threat_count=nearby_count,
            largest_gap=largest_gap,
            largest_gap_center=gap_center,
            closure_risk=closure_risk,
            reason="closing_loop_gap_detected" if active else None,
        )

    @classmethod
    def _largest_empty_sector_run(cls, occupied: set[int]) -> tuple[int, int]:
        total = cls.CIRCLE_SQUEEZE_SECTOR_COUNT
        if not occupied:
            return total, 0
        if len(occupied) == total:
            return 0, 0

        empty = [index not in occupied for index in range(total)]
        best_length = 0
        best_start = 0
        current_length = 0
        current_start = 0
        for offset in range(total * 2):
            index = offset % total
            if empty[index]:
                if current_length == 0:
                    current_start = offset
                current_length += 1
                if current_length > best_length:
                    best_length = min(current_length, total)
                    best_start = current_start % total
            else:
                current_length = 0
            if current_length >= total:
                break
        return best_length, best_start

    @classmethod
    def _heading_corridor_density(
        cls,
        heading: float,
        perception: PerceptionState,
    ) -> int:
        density = 0
        for threat in perception.visible_threats:
            if threat.distance > cls.ANTI_COIL_CORRIDOR_DISTANCE:
                continue
            angle_to_threat = math.atan2(
                threat.pos.y - perception.my_head.y,
                threat.pos.x - perception.my_head.x,
            )
            if abs(cls._normalize_angle(angle_to_threat - heading)) <= cls.ANTI_COIL_CORRIDOR_HALF_ANGLE:
                density += 1
        return density

    @classmethod
    def _heading_closing_threat_density(
        cls,
        heading: float,
        perception: PerceptionState,
    ) -> int:
        density = 0
        for threat in perception.visible_threats:
            if threat.velocity is None or threat.distance > cls.ANTI_COIL_CORRIDOR_DISTANCE:
                continue
            to_head_x = perception.my_head.x - threat.pos.x
            to_head_y = perception.my_head.y - threat.pos.y
            if threat.velocity.x * to_head_x + threat.velocity.y * to_head_y <= 0.0:
                continue
            angle_to_threat = math.atan2(
                threat.pos.y - perception.my_head.y,
                threat.pos.x - perception.my_head.x,
            )
            if abs(cls._normalize_angle(angle_to_threat - heading)) <= cls.ANTI_COIL_CORRIDOR_HALF_ANGLE:
                density += 1
        return density

    @classmethod
    def _threat_receding_from_head(
        cls,
        threat,
        perception: PerceptionState,
    ) -> bool | None:
        if threat.velocity is None:
            return None
        from_head_x = threat.pos.x - perception.my_head.x
        from_head_y = threat.pos.y - perception.my_head.y
        return threat.velocity.x * from_head_x + threat.velocity.y * from_head_y > 0.0

    @classmethod
    def _threat_corridor_density_for_heading(
        cls,
        heading: float,
        perception: PerceptionState,
    ) -> int:
        density = 0
        for threat in perception.visible_threats:
            if threat.distance > cls.THREAT_CORRIDOR_DENSITY_DISTANCE:
                continue
            angle_to_threat = math.atan2(
                threat.pos.y - perception.my_head.y,
                threat.pos.x - perception.my_head.x,
            )
            if abs(cls._normalize_angle(angle_to_threat - heading)) <= cls.THREAT_CORRIDOR_DENSITY_HALF_ANGLE:
                density += 1
        return density

    @classmethod
    def _threat_confidence(
        cls,
        center_ratio: float,
        threat,
        receding: bool | None,
    ) -> float:
        persistence = min(
            1.0,
            threat.persistent_frames / cls.THREAT_CORRIDOR_PERSISTENCE_FRAMES,
        )
        movement = 0.6 if receding is True else 1.0
        return max(0.0, min(1.0, center_ratio * persistence * movement))

    @classmethod
    def _requires_immediate_threat_avoidance(
        cls,
        perception: PerceptionState,
    ) -> bool:
        threat = perception.highest_threat
        if threat is None:
            return False
        if cls._has_heavy_threat_pressure(perception):
            return True
        if threat.in_forward_cone and threat.distance <= cls.IMMEDIATE_FORWARD_THREAT_DISTANCE:
            return True
        return threat.distance <= cls.IMMEDIATE_LATERAL_THREAT_DISTANCE

    @classmethod
    def _has_heavy_threat_pressure(cls, perception: PerceptionState) -> bool:
        return (
            len(perception.visible_threats) >= cls.DENSE_THREAT_FIELD_COUNT
            or perception.closing_threat_count >= cls.DENSE_CLOSING_THREAT_COUNT
        )

    def select_anti_coil_escape(
        self,
        perception: PerceptionState,
        analysis: CompressionAnalysis | None = None,
    ) -> EscapePlan | None:
        analysis = analysis or self.analyze_compression(perception)
        if not analysis.active:
            return None

        min_turn_radius = perception.my_radius * 2.0 + (perception.my_mass / 100.0)
        plans: list[tuple[float, float, float, EscapePlan]] = []
        for heading in self.ANTI_COIL_HEADING_SAMPLES:
            ray_dx = math.cos(heading)
            ray_dy = math.sin(heading)
            eval_result = self._evaluate_heading(
                heading,
                ray_dx,
                ray_dy,
                perception,
                min_turn_radius,
            )
            if (
                eval_result.collision_risk > 0.5
                or eval_result.open_space_score < 0.15
                or eval_result.enemy_head_intercept_risk > 1.5
            ):
                continue

            density = self._heading_corridor_density(heading, perception)
            open_space_score = eval_result.open_space_score / (1 + density)
            boundary_distance = eval_result.boundary_forward_distance or 0.0
            score = (
                open_space_score * 1000.0
                + min(boundary_distance, self.ANTI_COIL_CORRIDOR_DISTANCE)
                * self.ANTI_COIL_BOUNDARY_DISTANCE_WEIGHT
                - density * self.ANTI_COIL_DENSITY_PENALTY
            )
            target = Vector2(
                perception.my_head.x + ray_dx * self.ANTI_COIL_ESCAPE_DISTANCE,
                perception.my_head.y + ray_dy * self.ANTI_COIL_ESCAPE_DISTANCE,
            )
            plans.append((
                -score,
                abs(self._normalize_angle(heading - perception.my_angle)),
                heading,
                EscapePlan(
                    heading=heading,
                    target=target,
                    open_space_score=open_space_score,
                    corridor_density=density,
                    eval_result=eval_result,
                ),
            ))

        if not plans:
            return None

        plans.sort(key=lambda item: (item[0], item[1], item[2]))
        return plans[0][3]

    def select_circle_squeeze_escape(
        self,
        perception: PerceptionState,
        analysis: CircleSqueezeAnalysis | None = None,
    ) -> EscapePlan | None:
        analysis = analysis or self.analyze_circle_squeeze(perception)
        if not analysis.active:
            return None

        sector_width = (2 * math.pi) / self.CIRCLE_SQUEEZE_SECTOR_COUNT
        candidate_headings = [
            analysis.largest_gap_center,
            analysis.largest_gap_center - sector_width,
            analysis.largest_gap_center + sector_width,
            analysis.largest_gap_center - sector_width * 2,
            analysis.largest_gap_center + sector_width * 2,
            *self.ANTI_COIL_HEADING_SAMPLES,
        ]
        unique_headings = sorted({
            round(self._normalize_angle(heading), 10)
            for heading in candidate_headings
        })

        min_turn_radius = perception.my_radius * 2.0 + (perception.my_mass / 100.0)
        plans: list[tuple[float, float, float, EscapePlan]] = []
        for heading in unique_headings:
            ray_dx = math.cos(heading)
            ray_dy = math.sin(heading)
            eval_result = self._evaluate_heading(
                heading,
                ray_dx,
                ray_dy,
                perception,
                min_turn_radius,
            )
            if (
                eval_result.collision_risk > 0.5
                or eval_result.open_space_score < 0.15
                or eval_result.enemy_head_intercept_risk > 1.5
            ):
                continue

            density = self._heading_corridor_density(heading, perception)
            closing_density = self._heading_closing_threat_density(heading, perception)
            gap_delta = abs(self._normalize_angle(heading - analysis.largest_gap_center))
            boundary_distance = eval_result.boundary_forward_distance or 0.0
            open_space_score = eval_result.open_space_score / (1 + density)
            score = (
                open_space_score * 1000.0
                + max(0.0, math.pi - gap_delta) * self.CIRCLE_SQUEEZE_GAP_CENTER_BONUS
                + min(boundary_distance, self.ANTI_COIL_CORRIDOR_DISTANCE)
                * self.CIRCLE_SQUEEZE_BOUNDARY_DISTANCE_WEIGHT
                - density * self.CIRCLE_SQUEEZE_DENSITY_PENALTY
                - closing_density * self.THREAT_MEMORY_CLOSING_DENSITY_PENALTY
            )
            target = Vector2(
                perception.my_head.x + ray_dx * self.CIRCLE_SQUEEZE_ESCAPE_DISTANCE,
                perception.my_head.y + ray_dy * self.CIRCLE_SQUEEZE_ESCAPE_DISTANCE,
            )
            plans.append((
                -score,
                gap_delta,
                abs(self._normalize_angle(heading - perception.my_angle)),
                EscapePlan(
                    heading=heading,
                    target=target,
                    open_space_score=open_space_score,
                    corridor_density=density,
                    eval_result=eval_result,
                ),
            ))

        if not plans:
            return None

        plans.sort(key=lambda item: (item[0], item[1], item[2], item[3].heading))
        return plans[0][3]

    @classmethod
    def _enemy_pressures_cluster_or_lane(
        cls,
        cluster: LootCluster,
        perception: PerceptionState,
    ) -> list:
        pressures = []
        cluster_dx = cluster.center.x - perception.my_head.x
        cluster_dy = cluster.center.y - perception.my_head.y
        cluster_distance = math.hypot(cluster_dx, cluster_dy)
        if cluster_distance <= 0.0:
            return pressures

        unit_x = cluster_dx / cluster_distance
        unit_y = cluster_dy / cluster_distance
        for enemy in perception.visible_snakes:
            enemy_to_cluster = enemy.head.distance_to(cluster.center)
            ex = enemy.head.x - perception.my_head.x
            ey = enemy.head.y - perception.my_head.y
            along_lane = ex * unit_x + ey * unit_y
            lane_perp_distance = abs(-ex * unit_y + ey * unit_x)
            near_lane = (
                0.0 <= along_lane <= cluster_distance + cls.PARTIAL_GUARD_PRESSURE_RADIUS
                and lane_perp_distance <= cls.PARTIAL_GUARD_LANE_WIDTH
            )
            if enemy_to_cluster <= cls.PARTIAL_GUARD_PRESSURE_RADIUS or near_lane:
                pressures.append(enemy)

        pressures.sort(key=lambda enemy: (enemy.head.distance_to(cluster.center), enemy.id))
        return pressures

    @classmethod
    def _preferred_guard_side(
        cls,
        cluster: LootCluster,
        perception: PerceptionState,
        pressures: list,
    ) -> str:
        cluster_dx = cluster.center.x - perception.my_head.x
        cluster_dy = cluster.center.y - perception.my_head.y
        side_score = 0.0
        for enemy in pressures:
            ex = enemy.head.x - perception.my_head.x
            ey = enemy.head.y - perception.my_head.y
            cross = cluster_dx * ey - cluster_dy * ex
            weight = 1.0 / max(1.0, enemy.head.distance_to(cluster.center))
            side_score += cross * weight
        return "left" if side_score >= 0.0 else "right"

    def select_partial_guard(
        self,
        perception: PerceptionState,
        best_approach: LootApproach | None = None,
    ) -> PartialGuardPlan | None:
        clusters = self.detect_loot_clusters(perception.visible_food)
        if not clusters:
            return None

        plans: list[tuple[float, str, PartialGuardPlan]] = []
        for cluster in clusters:
            safe_approaches = [
                candidate
                for candidate in self.loot_cluster_approach_candidates(cluster, perception)
                if self._is_safe_target_heading(candidate.target, perception)
            ]
            if not safe_approaches:
                continue

            direct_approach = (
                best_approach
                if best_approach is not None and best_approach.cluster is cluster
                else safe_approaches[0]
            )
            if direct_approach.target_kind != "center":
                continue
            pressures = self._enemy_pressures_cluster_or_lane(cluster, perception)
            if not pressures:
                continue

            dx = direct_approach.target.x - perception.my_head.x
            dy = direct_approach.target.y - perception.my_head.y
            distance = math.hypot(dx, dy)
            if distance <= 0.0:
                continue

            unit_x = dx / distance
            unit_y = dy / distance
            preferred_side = self._preferred_guard_side(cluster, perception, pressures)
            ordered_sides = (
                [preferred_side, "right" if preferred_side == "left" else "left"]
            )

            for side in ordered_sides:
                side_sign = 1.0 if side == "left" else -1.0
                guard_target = Vector2(
                    direct_approach.target.x - unit_y * self.PARTIAL_GUARD_OFFSET_DISTANCE * side_sign,
                    direct_approach.target.y + unit_x * self.PARTIAL_GUARD_OFFSET_DISTANCE * side_sign,
                )
                eval_result = self._evaluate_target_heading(guard_target, perception)
                if eval_result is None:
                    continue
                if (
                    eval_result.collision_risk > 0.5
                    or eval_result.open_space_score < 0.15
                    or eval_result.enemy_head_intercept_risk > 1.5
                    or eval_result.enemy_head_intercept_time is not None
                ):
                    continue

                target_distance = perception.my_head.distance_to(guard_target)
                protective_bonus = (
                    self.PARTIAL_GUARD_PROTECTIVE_BONUS
                    if side == preferred_side
                    else self.PARTIAL_GUARD_PROTECTIVE_BONUS * 0.5
                )
                score = (
                    direct_approach.score
                    + protective_bonus
                    - target_distance * self.PARTIAL_GUARD_DISTANCE_PENALTY
                )
                if score < direct_approach.score + self.PARTIAL_GUARD_DIRECT_APPROACH_MARGIN:
                    continue

                plans.append((
                    -score,
                    side,
                    PartialGuardPlan(
                        cluster=cluster,
                        target=guard_target,
                        side=side,
                        reason="enemy_pressure_on_loot_lane",
                        score=score,
                        eval_result=eval_result,
                    ),
                ))

        if not plans:
            return None

        plans.sort(key=lambda item: (item[0], item[1], item[2].target.x, item[2].target.y))
        return plans[0][2]

    @staticmethod
    def _threat_memory_fields(perception: PerceptionState) -> dict:
        return {
            "persistent_threat_count": perception.persistent_threat_count,
            "reacquired_threat_count": perception.reacquired_threat_count,
            "recent_missing_threat_count": perception.recent_missing_threat_count,
            "closing_threat_count": perception.closing_threat_count,
        }

    def _evaluate_heading(self, requested_angle: float, ray_dx: float, ray_dy: float, perception: PerceptionState, min_turn_radius: float) -> EvalResult:
        res = EvalResult()
        
        max_projection_distance = perception.my_speed * max(self.ENEMY_PROJECTION_SAMPLE_TIMES)
        max_dist = max(perception.my_radius * 10, min_turn_radius * 2.0, max_projection_distance)
        res.collision_corridor_density = self._threat_corridor_density_for_heading(
            requested_angle,
            perception,
        )
        heavy_threat_pressure = self._has_heavy_threat_pressure(perception)
        
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
                    center_ratio = 1.0 - (perp_dist / max(1.0, envelope))
                    receding = self._threat_receding_from_head(threat, perception)
                    confidence = self._threat_confidence(center_ratio, threat, receding)
                    close_hit = t <= min_turn_radius * self.THREAT_CORRIDOR_CLOSE_DISTANCE_FACTOR
                    center_hit = center_ratio >= self.THREAT_CORRIDOR_HARD_CENTER_RATIO
                    persistent_or_closing = (
                        threat.persistent_frames >= self.THREAT_CORRIDOR_PERSISTENCE_FRAMES
                        or receding is False
                    )
                    dense_corridor = (
                        heavy_threat_pressure
                        or res.collision_corridor_density >= self.DENSE_CORRIDOR_THREAT_COUNT
                    )
                    hard_collision = (
                        close_hit
                        or center_hit
                        or dense_corridor
                        or (
                            persistent_or_closing
                            and confidence >= self.THREAT_CORRIDOR_HARD_CENTER_RATIO
                        )
                    )
                    risk = 1.0 if hard_collision else self.THREAT_CORRIDOR_SOFT_RISK
                    if risk > res.collision_risk:
                        res.collision_risk = risk
                        res.collision_threat_distance = t
                        res.collision_threat_angle_deg = math.degrees(
                            self._normalize_angle(math.atan2(ty, tx) - requested_angle)
                        )
                        res.collision_lateral_offset = perp_dist
                        res.collision_forward_cone = abs(
                            self._normalize_angle(math.atan2(ty, tx) - perception.my_angle)
                        ) <= self.THREAT_CORRIDOR_DENSITY_HALF_ANGLE
                        res.threat_receding = receding
                        res.threat_persistent_frames = threat.persistent_frames
                        res.threat_confidence = confidence
                    
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
                    time_delta = abs(my_time - enemy_time)

                    if perp_dist < envelope and time_delta < self.THREAT_INTERCEPT_SOFT_TIME_DELTA:
                        heading_to_crossing = math.atan2(
                            perception.my_head.y - projected_head.y,
                            perception.my_head.x - projected_head.x,
                        )
                        heading_delta = abs(
                            self._normalize_angle(heading_to_crossing - enemy_heading)
                        )
                        committed_to_lane = (
                            heading_delta <= self.THREAT_INTERCEPT_COMMIT_HEADING_DELTA
                        )
                        hard_intercept = committed_to_lane and (
                            time_delta <= self.THREAT_INTERCEPT_HARD_TIME_DELTA
                            or heading_delta <= math.radians(60.0)
                        )
                        risk = 2.0 if hard_intercept else 0.0
                        if (
                            risk <= res.enemy_head_intercept_risk
                            and res.enemy_head_intercept_distance is not None
                        ):
                            continue
                        res.enemy_head_intercept_risk = risk
                        res.enemy_head_intercept_time = enemy_time
                        res.enemy_head_intercept_distance = t
                        res.enemy_intercept_heading_delta_deg = math.degrees(heading_delta)
                        if hard_intercept:
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
        memory_fields = self._threat_memory_fields(perception)

        # 1. Boundary avoidance is highest priority
        if perception.boundary_distance < perception.my_radius * 10:
            return StrategyResult(
                mode=StrategyMode.AVOID_BOUNDARY,
                target_pos=Vector2(0, 0),
                defensive_reason="Boundary proximity",
                **memory_fields,
            )

        # 2. Circle-squeeze counter: classify tight loops before the generic anti-coil escape.
        circle_squeeze = self.analyze_circle_squeeze(perception)
        circle_escape = self.select_circle_squeeze_escape(perception, circle_squeeze)
        if circle_escape is not None:
            return StrategyResult(
                mode=StrategyMode.AVOID_THREAT,
                target_pos=circle_escape.target,
                defensive_reason="Circle squeeze counter",
                circle_squeeze_counter_active=True,
                circle_squeeze_sector_count=circle_squeeze.sector_count,
                circle_squeeze_largest_gap_deg=math.degrees(circle_squeeze.largest_gap),
                circle_squeeze_escape_heading=circle_escape.heading,
                circle_squeeze_escape_gap_center_deg=math.degrees(circle_squeeze.largest_gap_center),
                circle_squeeze_closure_risk=circle_squeeze.closure_risk,
                circle_squeeze_reason=circle_squeeze.reason,
                anti_coil_escape_active=True,
                compression_risk=circle_squeeze.closure_risk,
                enclosure_sector_count=circle_squeeze.sector_count,
                best_escape_heading=circle_escape.heading,
                escape_open_space_score=circle_escape.open_space_score,
                **memory_fields,
            )

        # 3. Anti-coil escape: choose a safe gap before compression becomes a closed cage.
        compression = self.analyze_compression(perception)
        escape_plan = self.select_anti_coil_escape(perception, compression)
        if escape_plan is not None:
            return StrategyResult(
                mode=StrategyMode.AVOID_THREAT,
                target_pos=escape_plan.target,
                defensive_reason="Anti-coil escape",
                compression_risk=compression.risk,
                enclosure_sector_count=compression.sector_count,
                best_escape_heading=escape_plan.heading,
                escape_open_space_score=escape_plan.open_space_score,
                anti_coil_escape_active=True,
                **memory_fields,
            )

        # 4. Threat avoidance (using highest scored threat)
        if self._requires_immediate_threat_avoidance(perception):
            # target_pos is the threat we want to avoid
            reason = "Forward danger" if perception.highest_threat.in_forward_cone else "Nearby body segment"
            return StrategyResult(
                mode=StrategyMode.AVOID_THREAT,
                target_pos=perception.highest_threat.pos,
                defensive_reason=reason,
                compression_risk=compression.risk,
                enclosure_sector_count=compression.sector_count,
                **memory_fields,
            )

        # 5. Seek food if safe
        if perception.visible_food:
            best_food = max(perception.visible_food, key=lambda food: self.score_food(food, perception))
            best_food_score = self.score_food(best_food, perception)
            best_approach = self._best_safe_loot_approach(perception)
            partial_guard = self.select_partial_guard(perception, best_approach)
            if partial_guard is not None:
                return StrategyResult(
                    mode=StrategyMode.SEEK_FOOD,
                    target_pos=partial_guard.target,
                    food_score=best_food_score,
                    loot_cluster_score=partial_guard.cluster.score,
                    loot_cluster_total_value=partial_guard.cluster.total_value,
                    loot_cluster_pellet_count=partial_guard.cluster.pellet_count,
                    loot_cluster_target=partial_guard.cluster.center,
                    loot_cluster_target_kind="partial_guard",
                    loot_cluster_approach=partial_guard.target,
                    partial_guard_active=True,
                    partial_guard_target=partial_guard.target,
                    partial_guard_side=partial_guard.side,
                    partial_guard_reason=partial_guard.reason,
                    partial_guard_score=partial_guard.score,
                    **memory_fields,
                )
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
                    **memory_fields,
                )
            return StrategyResult(
                mode=StrategyMode.SEEK_FOOD,
                target_pos=best_food.pos,
                food_score=best_food_score,
                **memory_fields,
            )
            
        # 6. Default: wander
        return StrategyResult(mode=StrategyMode.WANDER, target_pos=None, **memory_fields)

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

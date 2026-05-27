import math
from dataclasses import dataclass

from sandbox.bot.perception import PerceptionState
from sandbox.bot.steering import Steering
from sandbox.bot.strategy import Strategy
from sandbox.config import Config


@dataclass(frozen=True)
class BoostSafetyResult:
    allowed: bool
    reason: str = "none"


@dataclass(frozen=True)
class TacticalPathResult:
    safe: bool
    min_clearance: float
    collision_count: int
    closing_count: int
    boundary_forward_distance: float


def _normalize_angle(angle: float) -> float:
    return (angle + math.pi) % (2 * math.pi) - math.pi


def is_boost_safe(
    perception_state: PerceptionState,
    requested_angle: float,
    eval_result,
    min_turn_radius: float,
    max_turn_delta: float = math.pi / 3,
) -> BoostSafetyResult:
    boosted_turn_safety_distance = min_turn_radius * Config.BOOST_SPEED_MULTIPLIER
    turn_delta = abs(_normalize_angle(requested_angle - perception_state.my_angle))

    if eval_result.collision_risk > 0.5:
        return BoostSafetyResult(False, "boost_collision_risk")
    if eval_result.enemy_head_intercept_risk > 1.5:
        return BoostSafetyResult(False, "boost_enemy_intercept_risk")
    if (
        eval_result.boundary_forward_distance is not None
        and eval_result.boundary_forward_distance < boosted_turn_safety_distance
    ):
        return BoostSafetyResult(False, "boost_boundary_too_close")
    if turn_delta > max_turn_delta:
        return BoostSafetyResult(False, "boost_turn_too_sharp")
    if perception_state.my_mass <= Config.BOOST_MIN_MASS + Config.BOOST_MASS_COST:
        return BoostSafetyResult(False, "boost_mass_reserve")

    return BoostSafetyResult(True, "none")


class SafetyGate:
    HEADING_SAMPLES = tuple(index * math.pi / 32 for index in range(64))
    LOOKAHEAD_STEPS = 18
    LOOKAHEAD_DT = 1.0 / 20.0
    LOOKAHEAD_COLLISION_MARGIN = 2.0
    LOOKAHEAD_BOUNDARY_MARGIN = 24.0
    LOOKAHEAD_TURN_MASS_FACTOR = 1800.0
    LOOKAHEAD_THREAT_DISTANCE = 320.0
    LOOKAHEAD_MAX_THREATS = 80

    def __init__(self):
        self.strategy = Strategy("safety_first")
        self.steering = Steering()
        self._last_override_heading: float | None = None

    @classmethod
    def _max_turn_per_step(cls, perception_state: PerceptionState) -> float:
        mass_factor = 1.0 + max(0.0, perception_state.my_mass - Config.INITIAL_MASS) / cls.LOOKAHEAD_TURN_MASS_FACTOR
        return Config.BASE_TURN_RATE * cls.LOOKAHEAD_DT / mass_factor

    def _project_tactical_path(
        self,
        perception_state: PerceptionState,
        requested_angle: float,
        boosted: bool,
    ) -> TacticalPathResult:
        x = perception_state.my_head.x
        y = perception_state.my_head.y
        heading = perception_state.my_angle
        speed = max(1.0, perception_state.my_speed)
        if boosted:
            speed *= Config.BOOST_SPEED_MULTIPLIER

        max_turn = self._max_turn_per_step(perception_state)
        min_clearance = float("inf")
        collision_count = 0
        closing_count = 0
        min_boundary = self.strategy.boundary_distance_along_heading(
            perception_state.my_head,
            heading,
        )
        nearby_threats = [
            threat
            for threat in perception_state.visible_threats
            if threat.distance <= self.LOOKAHEAD_THREAT_DISTANCE
        ]
        nearby_threats.sort(key=lambda threat: threat.distance)
        nearby_threats = nearby_threats[: self.LOOKAHEAD_MAX_THREATS]

        for step in range(1, self.LOOKAHEAD_STEPS + 1):
            turn_delta = _normalize_angle(requested_angle - heading)
            heading += max(-max_turn, min(max_turn, turn_delta))
            x += math.cos(heading) * speed * self.LOOKAHEAD_DT
            y += math.sin(heading) * speed * self.LOOKAHEAD_DT

            boundary_space = Config.WORLD_RADIUS - math.hypot(x, y)
            min_boundary = min(min_boundary, boundary_space)
            if boundary_space < perception_state.my_radius + self.LOOKAHEAD_BOUNDARY_MARGIN:
                collision_count += 1

            for threat in nearby_threats:
                tx = threat.pos.x
                ty = threat.pos.y
                if threat.velocity is not None:
                    elapsed = step * self.LOOKAHEAD_DT
                    tx += threat.velocity.x * elapsed
                    ty += threat.velocity.y * elapsed
                clearance = math.hypot(tx - x, ty - y) - (
                    perception_state.my_radius
                    + threat.radius
                    + self.LOOKAHEAD_COLLISION_MARGIN
                )
                min_clearance = min(min_clearance, clearance)
                if clearance < -perception_state.my_radius:
                    collision_count += 1
                    if threat.velocity is not None:
                        to_head_x = x - tx
                        to_head_y = y - ty
                        if threat.velocity.x * to_head_x + threat.velocity.y * to_head_y > 0.0:
                            closing_count += 1

            for enemy in perception_state.visible_snakes:
                enemy_speed = max(1.0, getattr(enemy, "speed", Config.BASE_SPEED))
                enemy_heading = enemy.wanted_heading if enemy.wanted_heading is not None else enemy.heading
                if enemy.velocity is not None:
                    elapsed = step * self.LOOKAHEAD_DT
                    ex = enemy.head.x + enemy.velocity.x * elapsed
                    ey = enemy.head.y + enemy.velocity.y * elapsed
                else:
                    elapsed = step * self.LOOKAHEAD_DT
                    ex = enemy.head.x + math.cos(enemy_heading) * enemy_speed * elapsed
                    ey = enemy.head.y + math.sin(enemy_heading) * enemy_speed * elapsed
                clearance = math.hypot(ex - x, ey - y) - (
                    perception_state.my_radius
                    + enemy.radius
                    + self.LOOKAHEAD_COLLISION_MARGIN
                )
                min_clearance = min(min_clearance, clearance)
                if clearance < -perception_state.my_radius:
                    collision_count += 2
                    closing_count += 1

        if min_clearance == float("inf"):
            min_clearance = Config.AI_VISION_RADIUS

        return TacticalPathResult(
            safe=collision_count == 0,
            min_clearance=min_clearance,
            collision_count=collision_count,
            closing_count=closing_count,
            boundary_forward_distance=min_boundary,
        )

    def _select_safe_heading(self, perception_state: PerceptionState, min_turn_radius: float) -> float:
        plans: list[tuple[float, float, float]] = []
        center_heading = math.atan2(-perception_state.my_head.y, -perception_state.my_head.x)
        for heading in self.HEADING_SAMPLES:
            ray_dx = math.cos(heading)
            ray_dy = math.sin(heading)
            eval_result = self.strategy._evaluate_heading(
                heading,
                ray_dx,
                ray_dy,
                perception_state,
                min_turn_radius,
            )
            path_result = self._project_tactical_path(
                perception_state,
                heading,
                boosted=False,
            )
            density = self.strategy._heading_corridor_density(heading, perception_state)
            closing_density = self.strategy._heading_closing_threat_density(heading, perception_state)
            receding_density = self.strategy._heading_receding_threat_density(heading, perception_state)
            flow_density = max(0, density - receding_density)
            turn_delta = abs(_normalize_angle(heading - perception_state.my_angle))
            continuity_bonus = 0.0
            if self._last_override_heading is not None:
                continuity_bonus = max(
                    0.0,
                    math.pi - abs(_normalize_angle(heading - self._last_override_heading)),
                ) * 180.0
            score = (
                eval_result.open_space_score * 1000.0
                + min(eval_result.boundary_forward_distance or 0.0, 300.0) * 0.1
                + max(0.0, math.pi - abs(_normalize_angle(heading - center_heading))) * 120.0
                + continuity_bonus
                + max(-60.0, min(path_result.min_clearance, 120.0)) * 8.0
                + receding_density * 120.0
                - flow_density * 95.0
                - closing_density * 240.0
                - path_result.collision_count * 2200.0
                - path_result.closing_count * 800.0
                - turn_delta * 120.0
            )
            if eval_result.collision_risk > 0.5:
                score -= 10000.0
            if eval_result.enemy_head_intercept_risk > 1.5:
                score -= 9000.0
            if eval_result.open_space_score < 0.15:
                score -= 5000.0
            plans.append((-score, turn_delta, heading))

        plans.sort()
        if plans:
            return plans[0][2]

        strategy_result = self.strategy.decide(perception_state)
        steering_result = self.steering.compute(strategy_result, perception_state)
        return steering_result.heading

    def filter_action(
        self,
        perception_state: PerceptionState,
        requested_angle: float,
        requested_boost: bool,
        boost_max_turn_delta: float = math.pi / 3,
    ) -> tuple[float, bool, bool, str]:
        ray_dx = math.cos(requested_angle)
        ray_dy = math.sin(requested_angle)
        min_turn_radius = perception_state.my_radius * 2.0 + (perception_state.my_mass / 100.0)

        eval_result = self.strategy._evaluate_heading(
            requested_angle,
            ray_dx,
            ray_dy,
            perception_state,
            min_turn_radius,
        )
        path_result = self._project_tactical_path(
            perception_state,
            requested_angle,
            boosted=False,
        )

        is_unsafe = False
        reason = ""
        if eval_result.collision_risk > 0.5:
            is_unsafe = True
            reason = "projected_collision"
        elif eval_result.open_space_score < 0.15:
            is_unsafe = True
            reason = "boundary_too_close"
        elif eval_result.enemy_head_intercept_risk > 1.5:
            is_unsafe = True
            reason = "enemy_head_intercept"
        elif not path_result.safe:
            is_unsafe = True
            reason = "tactical_lookahead_collision"

        if is_unsafe:
            if reason == "boundary_too_close":
                safe_heading = math.atan2(
                    -perception_state.my_head.y,
                    -perception_state.my_head.x,
                )
                self._last_override_heading = safe_heading
                return safe_heading, False, True, reason
            safe_heading = self._select_safe_heading(perception_state, min_turn_radius)
            self._last_override_heading = safe_heading
            return safe_heading, False, True, reason

        if requested_boost:
            boost_safety = is_boost_safe(
                perception_state,
                requested_angle,
                eval_result,
                min_turn_radius,
                boost_max_turn_delta,
            )
            if not boost_safety.allowed:
                return requested_angle, False, False, boost_safety.reason
            boosted_path_result = self._project_tactical_path(
                perception_state,
                requested_angle,
                boosted=True,
            )
            if not boosted_path_result.safe:
                return requested_angle, False, False, "boost_tactical_lookahead_collision"

        self._last_override_heading = None
        return requested_angle, requested_boost, False, "none"

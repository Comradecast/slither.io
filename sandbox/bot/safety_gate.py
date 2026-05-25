import math
from dataclasses import dataclass
from sandbox.config import Config
from sandbox.bot.strategy import Strategy
from sandbox.bot.steering import Steering
from sandbox.bot.perception import PerceptionState


@dataclass(frozen=True)
class BoostSafetyResult:
    allowed: bool
    reason: str = "none"


def _normalize_angle(angle: float) -> float:
    return (angle + math.pi) % (2 * math.pi) - math.pi


def is_boost_safe(
    perception_state: PerceptionState,
    requested_angle: float,
    eval_result,
    min_turn_radius: float,
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
    if turn_delta > math.pi / 3:
        return BoostSafetyResult(False, "boost_turn_too_sharp")
    if perception_state.my_mass <= Config.BOOST_MIN_MASS + Config.BOOST_MASS_COST:
        return BoostSafetyResult(False, "boost_mass_reserve")

    return BoostSafetyResult(True, "none")


class SafetyGate:
    def __init__(self):
        # We use the safety_first profile for the override logic
        self.strategy = Strategy("safety_first")
        self.steering = Steering()
        
    def filter_action(self, perception_state: PerceptionState, requested_angle: float, requested_boost: bool) -> tuple[float, bool, bool, str]:
        """
        Evaluates the requested angle. If it leads to imminent death (collision, boundary, intercept),
        overrides it with a safe heading from the Strategy planner.
        Returns: safe_angle, safe_boost, was_overridden, reason
        """
        ray_dx = math.cos(requested_angle)
        ray_dy = math.sin(requested_angle)
        
        min_turn_radius = perception_state.my_radius * 2.0 + (perception_state.my_mass / 100.0)
        
        eval_result = self.strategy._evaluate_heading(requested_angle, ray_dx, ray_dy, perception_state, min_turn_radius)
        
        is_unsafe = False
        reason = ""
        
        # 1. Projected Collision with snake body or boundary
        if eval_result.collision_risk > 0.5:
            is_unsafe = True
            reason = "projected_collision"
            
        # 2. Boundary / Open space too small
        elif eval_result.open_space_score < 0.15:
            is_unsafe = True
            reason = "boundary_too_close"
            
        # 3. Enemy head intercept risk
        elif eval_result.enemy_head_intercept_risk > 1.5:
            is_unsafe = True
            reason = "enemy_head_intercept"
            
        if is_unsafe:
            # Get safe heading
            strategy_result = self.strategy.decide(perception_state)
            steering_result = self.steering.compute(strategy_result, perception_state)
            # Disable boost to prioritize turning tight
            return steering_result.heading, False, True, reason

        if requested_boost:
            boost_safety = is_boost_safe(
                perception_state,
                requested_angle,
                eval_result,
                min_turn_radius,
            )
            if not boost_safety.allowed:
                return requested_angle, False, False, boost_safety.reason

        return requested_angle, requested_boost, False, "none"

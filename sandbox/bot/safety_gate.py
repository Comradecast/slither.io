import math
from sandbox.config import Config
from sandbox.bot.strategy import Strategy
from sandbox.bot.perception import PerceptionState

class SafetyGate:
    def __init__(self):
        # We use the safety_first profile for the override logic
        self.strategy = Strategy("safety_first")
        
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
            # Disable boost to prioritize turning tight
            return strategy_result.selected_heading, False, True, reason
            
        return requested_angle, requested_boost, False, "none"

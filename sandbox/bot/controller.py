from __future__ import annotations

from dataclasses import dataclass

from sandbox.bot.perception import Perception
from sandbox.bot.safety_gate import SafetyGate
from sandbox.bot.steering import Steering
from sandbox.bot.strategy import Strategy
from sandbox.logging_.game_logger import GameLogger
from sandbox.logging_.metrics import MetricsTracker


@dataclass
class BotAction:
    target_angle: float
    boost: bool


class BotController:
    """Orchestrates the bot's decision pipeline."""

    def __init__(self, snake, logger: GameLogger | None = None, metrics: MetricsTracker | None = None):
        self.snake = snake
        self.logger = logger
        self.metrics = metrics
        self.perception = Perception()
        self.strategy = Strategy()
        self.steering = Steering()
        self.safety_gate = SafetyGate()
        self.last_decision: dict | None = None

    def update(self, snakes: list, food_items: list, tick: int = 0) -> BotAction:
        if not self.snake.alive:
            return BotAction(target_angle=self.snake.angle, boost=False)

        perception_state = self.perception.build(self.snake, snakes, food_items)
        strategy_result = self.strategy.decide(perception_state)
        steering_result = self.steering.compute(strategy_result, perception_state)

        # v0.26 keeps live boost behavior disabled while SafetyGate becomes final authority.
        requested_boost = False
        safe_heading, safe_boost, gate_overridden, gate_reason = self.safety_gate.filter_action(
            perception_state,
            steering_result.heading,
            requested_boost,
        )
        action = BotAction(target_angle=safe_heading, boost=safe_boost)
        self.last_decision = {
            "strategy_mode": strategy_result.mode.value,
            "defensive_reason": strategy_result.defensive_reason,
            "target_position": {
                "x": strategy_result.target_pos.x,
                "y": strategy_result.target_pos.y,
            } if strategy_result.target_pos else None,
            "requested_heading": steering_result.heading,
            "final_heading": action.target_angle,
            "requested_boost": requested_boost,
            "final_boost": action.boost,
            "safety_gate_overridden": gate_overridden,
            "safety_gate_reason": gate_reason,
            "active_threat_count": perception_state.active_threat_count,
            "visible_food_count": len(perception_state.visible_food),
            "visible_snake_count": len(perception_state.visible_snakes),
            "closing_threat_count": perception_state.closing_threat_count,
            "persistent_threat_count": perception_state.persistent_threat_count,
            "recent_missing_threat_count": perception_state.recent_missing_threat_count,
            "reacquired_threat_count": perception_state.reacquired_threat_count,
        }

        if self.logger:
            nearest_food_dist = perception_state.visible_food[0].distance if perception_state.visible_food else None

            t_dist = None
            t_score = None
            t_pos_x = None
            t_pos_y = None
            if perception_state.nearest_threat:
                t_dist = perception_state.nearest_threat.distance
                t_score = perception_state.nearest_threat.score
                t_pos_x = perception_state.nearest_threat.pos.x
                t_pos_y = perception_state.nearest_threat.pos.y

            h_score = None
            h_dist = None
            h_angle = None
            h_cone = None
            if perception_state.highest_threat:
                h_score = perception_state.highest_threat.score
                h_dist = perception_state.highest_threat.distance
                h_angle = perception_state.highest_threat.angle_diff
                h_cone = perception_state.highest_threat.in_forward_cone

            self.logger.log_decision(
                tick=tick,
                snake_id=self.snake.id,
                pos_x=self.snake.pos.x,
                pos_y=self.snake.pos.y,
                mass=self.snake.mass,
                heading=self.snake.angle,
                strategy_mode=strategy_result.mode.value,
                target_pos_x=strategy_result.target_pos.x if strategy_result.target_pos else None,
                target_pos_y=strategy_result.target_pos.y if strategy_result.target_pos else None,
                steering_heading=steering_result.heading,
                final_heading=action.target_angle,
                boost=action.boost,
                safety_gate_overridden=gate_overridden,
                safety_gate_reason=gate_reason,
                nearest_food_distance=nearest_food_dist,
                boundary_distance=perception_state.boundary_distance,
                nearest_threat_distance=t_dist,
                nearest_threat_score=t_score,
                nearest_threat_position_x=t_pos_x,
                nearest_threat_position_y=t_pos_y,
                highest_threat_score=h_score,
                highest_threat_distance=h_dist,
                highest_threat_angle=h_angle,
                highest_threat_in_forward_cone=h_cone,
                defensive_reason=strategy_result.defensive_reason,
                active_threat_count=perception_state.active_threat_count,
            )

        if self.metrics:
            self.metrics.record_decision()

        self.snake.target_angle = action.target_angle
        self.snake.boosting = action.boost
        return action

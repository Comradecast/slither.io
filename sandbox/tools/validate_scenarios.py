from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from sandbox.bot.controller import BotController
from sandbox.bot.perception import Perception
from sandbox.bot.safety_gate import SafetyGate
from sandbox.bot.steering import Steering
from sandbox.bot.strategy import Strategy
from sandbox.config import Config
from sandbox.food import FoodItem
from sandbox.snake import Snake
from sandbox.vector import Vector2


DEFAULT_REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"
DEFAULT_REPORT_NAME = "harness_results.jsonl"


@dataclass
class ScenarioCase:
    name: str
    my_snake: Snake
    snakes: list[Snake]
    foods: list[FoodItem]
    expected_mode: str | None = None
    expected_gate_reason: str | None = None
    expected_gate_reasons: set[str] | None = None
    expected_override: bool | None = None
    requested_heading: float | None = None
    requested_boost: bool = False
    validator: Callable[[dict], bool] | None = None


class ScenarioRunner:
    def __init__(
        self,
        reports_dir: str | Path | None = None,
        report_name: str = DEFAULT_REPORT_NAME,
        reset_report: bool = True,
    ):
        self.reports_dir = Path(reports_dir) if reports_dir is not None else DEFAULT_REPORTS_DIR
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.report_file = self.reports_dir / report_name
        if reset_report and self.report_file.exists():
            self.report_file.unlink()

    def run_scenario(
        self,
        scenario: ScenarioCase,
    ) -> dict:
        name = scenario.name
        my_snake = scenario.my_snake
        snakes = scenario.snakes
        foods = scenario.foods

        perception = Perception(vision_radius=Config.AI_VISION_RADIUS)
        state = perception.build(my_snake, snakes, foods)

        strategy = Strategy()
        strategy_result = strategy.decide(state)

        steering = Steering()
        steering_result = steering.compute(strategy_result, state)
        requested_heading = (
            scenario.requested_heading
            if scenario.requested_heading is not None
            else steering_result.heading
        )

        min_turn_radius = state.my_radius * 2.0 + (state.my_mass / 100.0)
        eval_result = strategy._evaluate_heading(
            requested_heading,
            math.cos(requested_heading),
            math.sin(requested_heading),
            state,
            min_turn_radius,
        )

        gate = SafetyGate()
        safe_angle, safe_boost, overridden, reason = gate.filter_action(
            state,
            requested_heading,
            scenario.requested_boost,
        )

        controller = BotController(my_snake)
        controller_action = controller.update(snakes, foods)

        result = {
            "scenario": name,
            "perception": {
                "my_radius": state.my_radius,
                "visible_snakes": len(state.visible_snakes),
                "visible_threats": len(state.visible_threats),
                "visible_food": len(state.visible_food),
                "boundary_distance": state.boundary_distance,
            },
            "strategy": {
                "mode": strategy_result.mode.value,
                "target_x": strategy_result.target_pos.x if strategy_result.target_pos else None,
                "target_y": strategy_result.target_pos.y if strategy_result.target_pos else None,
                "defensive_reason": strategy_result.defensive_reason,
                "food_score": strategy_result.food_score,
            },
            "steering": {
                "strategy_heading_deg": math.degrees(steering_result.heading),
                "requested_angle_deg": math.degrees(requested_heading),
            },
            "gate": {
                "overridden": overridden,
                "reason": reason,
                "final_angle_deg": math.degrees(safe_angle),
                "final_boost": safe_boost,
            },
            "controller": {
                "action_target_angle_deg": math.degrees(controller_action.target_angle),
                "action_boost": controller_action.boost,
            },
        }
        result.update({
            "selected_heading": safe_angle,
            "selected_heading_deg": math.degrees(safe_angle),
            "boost": safe_boost,
            "was_overridden": overridden,
            "reason": reason,
            "collision_risk": eval_result.collision_risk,
            "enemy_head_intercept_risk": eval_result.enemy_head_intercept_risk,
            "boundary_forward_distance": eval_result.boundary_forward_distance,
            "my_radius": state.my_radius,
            "my_mass": state.my_mass,
        })

        passed = True
        if scenario.expected_mode is not None:
            passed = passed and strategy_result.mode.value == scenario.expected_mode
        if scenario.expected_gate_reason is not None:
            passed = passed and reason == scenario.expected_gate_reason
        if scenario.expected_gate_reasons is not None:
            passed = passed and reason in scenario.expected_gate_reasons
        if scenario.expected_override is not None:
            passed = passed and overridden == scenario.expected_override
        if scenario.validator is not None:
            passed = passed and scenario.validator(result)
        result["passed"] = passed

        with self.report_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result, sort_keys=True) + "\n")

        return result


def _large_snake(snake_id: int, x: float, y: float, angle: float) -> Snake:
    snake = Snake(snake_id, x, y, angle)
    snake.mass = 5000
    snake.recompute_segments()
    return snake


def build_scenarios() -> Iterable[ScenarioCase]:
    my_large = _large_snake(1, 0, 0, 0)
    enemy_wall = Snake(2, 50, 0, 0)
    enemy_wall.mass = 100
    enemy_wall.recompute_segments()
    enemy_wall.segments = [Vector2(50, 0), Vector2(50, 20), Vector2(50, -20)]
    yield ScenarioCase(
        name="large_snake_near_enemy_body",
        my_snake=my_large,
        snakes=[my_large, enemy_wall],
        foods=[],
        expected_mode="avoid_threat",
        expected_gate_reason="projected_collision",
        expected_override=True,
        requested_heading=0.0,
        validator=lambda result: result["collision_risk"] > 0.5,
    )

    boundary_snake = _large_snake(1, Config.WORLD_RADIUS - 60, 0, 0)
    yield ScenarioCase(
        name="large_snake_near_boundary_wall_facing",
        my_snake=boundary_snake,
        snakes=[boundary_snake],
        foods=[],
        expected_mode="avoid_boundary",
        expected_gate_reason="boundary_too_close",
        expected_override=True,
        requested_heading=0.0,
        validator=lambda result: (
            result["boundary_forward_distance"]
            < result["my_radius"] * 2.0 + (result["my_mass"] / 100.0)
        ),
    )

    escape_boundary_snake = _large_snake(1, Config.WORLD_RADIUS - 60, 0, math.pi)
    yield ScenarioCase(
        name="large_snake_near_boundary_escape_heading",
        my_snake=escape_boundary_snake,
        snakes=[escape_boundary_snake],
        foods=[],
        expected_mode="avoid_boundary",
        expected_gate_reason="none",
        expected_override=False,
        requested_heading=math.pi,
        validator=lambda result: (
            result["boundary_forward_distance"]
            > result["my_radius"] * 2.0 + (result["my_mass"] / 100.0)
        ),
    )

    intercept_snake = Snake(1, 0, 0, 0)
    intercept_snake.angle = math.pi / 2
    intercept_enemy = Snake(2, 40, 12, math.radians(-90))
    intercept_enemy.speed = Config.BASE_SPEED
    intercept_enemy.segments = []
    yield ScenarioCase(
        name="enemy_head_intercept_crossing",
        my_snake=intercept_snake,
        snakes=[intercept_snake, intercept_enemy],
        foods=[],
        expected_gate_reason="enemy_head_intercept",
        expected_override=True,
        requested_heading=0.0,
        validator=lambda result: (
            result["enemy_head_intercept_risk"] > 1.5
            and abs(result["selected_heading"]) > 0.1
        ),
    )

    risky_food_snake = Snake(1, 0, 0, 0)
    risky_food = FoodItem(50, 0, 10.0)
    nearby_enemy = Snake(2, 50, 10, 0)
    nearby_enemy.segments = [Vector2(50, 10)]
    yield ScenarioCase(
        name="food_near_threat",
        my_snake=risky_food_snake,
        snakes=[risky_food_snake, nearby_enemy],
        foods=[risky_food],
        expected_mode="avoid_threat",
        expected_gate_reason="none",
        expected_override=False,
    )

    food_snake = Snake(1, 0, 0, 0)
    foods = [FoodItem(100, 0, 10.0), FoodItem(50, 20, 5.0)]
    yield ScenarioCase(
        name="safe_food_path",
        my_snake=food_snake,
        snakes=[food_snake],
        foods=foods,
        expected_mode="seek_food",
        expected_gate_reason="none",
        expected_override=False,
    )


def run_all_scenarios(
    reports_dir: str | Path | None = None,
    report_name: str = DEFAULT_REPORT_NAME,
) -> list[dict]:
    runner = ScenarioRunner(reports_dir=reports_dir, report_name=report_name)
    return [
        runner.run_scenario(scenario)
        for scenario in build_scenarios()
    ]


if __name__ == "__main__":
    results = run_all_scenarios()
    for result in results:
        print(json.dumps(result, sort_keys=True))
    if not all(result["passed"] for result in results):
        sys.exit(1)

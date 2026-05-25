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
PROMOTED_TELEMETRY_SCENARIOS_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "promoted_telemetry_scenarios.json"
)


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
    expected_final_boost: bool | None = None
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
                "loot_cluster_score": strategy_result.loot_cluster_score,
                "loot_cluster_total_value": strategy_result.loot_cluster_total_value,
                "loot_cluster_pellet_count": strategy_result.loot_cluster_pellet_count,
                "loot_cluster_target_x": (
                    strategy_result.loot_cluster_target.x
                    if strategy_result.loot_cluster_target
                    else None
                ),
                "loot_cluster_target_y": (
                    strategy_result.loot_cluster_target.y
                    if strategy_result.loot_cluster_target
                    else None
                ),
                "loot_cluster_target_kind": strategy_result.loot_cluster_target_kind,
                "loot_cluster_approach_x": (
                    strategy_result.loot_cluster_approach.x
                    if strategy_result.loot_cluster_approach
                    else None
                ),
                "loot_cluster_approach_y": (
                    strategy_result.loot_cluster_approach.y
                    if strategy_result.loot_cluster_approach
                    else None
                ),
                "compression_risk": strategy_result.compression_risk,
                "enclosure_sector_count": strategy_result.enclosure_sector_count,
                "best_escape_heading": strategy_result.best_escape_heading,
                "escape_open_space_score": strategy_result.escape_open_space_score,
                "anti_coil_escape_active": strategy_result.anti_coil_escape_active,
                "partial_guard_active": strategy_result.partial_guard_active,
                "partial_guard_target_x": (
                    strategy_result.partial_guard_target.x
                    if strategy_result.partial_guard_target
                    else None
                ),
                "partial_guard_target_y": (
                    strategy_result.partial_guard_target.y
                    if strategy_result.partial_guard_target
                    else None
                ),
                "partial_guard_side": strategy_result.partial_guard_side,
                "partial_guard_reason": strategy_result.partial_guard_reason,
                "partial_guard_score": strategy_result.partial_guard_score,
                "circle_squeeze_counter_active": strategy_result.circle_squeeze_counter_active,
                "circle_squeeze_sector_count": strategy_result.circle_squeeze_sector_count,
                "circle_squeeze_largest_gap_deg": strategy_result.circle_squeeze_largest_gap_deg,
                "circle_squeeze_escape_heading": strategy_result.circle_squeeze_escape_heading,
                "circle_squeeze_escape_gap_center_deg": (
                    strategy_result.circle_squeeze_escape_gap_center_deg
                ),
                "circle_squeeze_closure_risk": strategy_result.circle_squeeze_closure_risk,
                "circle_squeeze_reason": strategy_result.circle_squeeze_reason,
                "persistent_threat_count": strategy_result.persistent_threat_count,
                "reacquired_threat_count": strategy_result.reacquired_threat_count,
                "recent_missing_threat_count": strategy_result.recent_missing_threat_count,
                "closing_threat_count": strategy_result.closing_threat_count,
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
                "requested_boost": scenario.requested_boost,
                "boost_allowed": safe_boost if scenario.requested_boost else False,
                "boost_reason": reason if scenario.requested_boost and not safe_boost else "none",
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
            "requested_boost": scenario.requested_boost,
            "final_boost": safe_boost,
            "boost_allowed": safe_boost if scenario.requested_boost else False,
            "boost_reason": reason if scenario.requested_boost and not safe_boost else "none",
            "was_overridden": overridden,
            "reason": reason,
            "collision_risk": eval_result.collision_risk,
            "enemy_head_intercept_risk": eval_result.enemy_head_intercept_risk,
            "boundary_forward_distance": eval_result.boundary_forward_distance,
            "enemy_head_intercept_time": eval_result.enemy_head_intercept_time,
            "enemy_head_intercept_distance": eval_result.enemy_head_intercept_distance,
            "my_radius": state.my_radius,
            "my_mass": state.my_mass,
            "loot_cluster_score": strategy_result.loot_cluster_score,
            "loot_cluster_total_value": strategy_result.loot_cluster_total_value,
            "loot_cluster_pellet_count": strategy_result.loot_cluster_pellet_count,
            "loot_cluster_target_x": (
                strategy_result.loot_cluster_target.x
                if strategy_result.loot_cluster_target
                else None
            ),
            "loot_cluster_target_y": (
                strategy_result.loot_cluster_target.y
                if strategy_result.loot_cluster_target
                else None
            ),
            "loot_cluster_target_kind": strategy_result.loot_cluster_target_kind,
            "loot_cluster_approach_x": (
                strategy_result.loot_cluster_approach.x
                if strategy_result.loot_cluster_approach
                else None
            ),
            "loot_cluster_approach_y": (
                strategy_result.loot_cluster_approach.y
                if strategy_result.loot_cluster_approach
                else None
            ),
            "compression_risk": strategy_result.compression_risk,
            "enclosure_sector_count": strategy_result.enclosure_sector_count,
            "best_escape_heading": strategy_result.best_escape_heading,
            "escape_open_space_score": strategy_result.escape_open_space_score,
            "anti_coil_escape_active": strategy_result.anti_coil_escape_active,
            "partial_guard_active": strategy_result.partial_guard_active,
            "partial_guard_target_x": (
                strategy_result.partial_guard_target.x
                if strategy_result.partial_guard_target
                else None
            ),
            "partial_guard_target_y": (
                strategy_result.partial_guard_target.y
                if strategy_result.partial_guard_target
                else None
            ),
            "partial_guard_side": strategy_result.partial_guard_side,
            "partial_guard_reason": strategy_result.partial_guard_reason,
            "partial_guard_score": strategy_result.partial_guard_score,
            "circle_squeeze_counter_active": strategy_result.circle_squeeze_counter_active,
            "circle_squeeze_sector_count": strategy_result.circle_squeeze_sector_count,
            "circle_squeeze_largest_gap_deg": strategy_result.circle_squeeze_largest_gap_deg,
            "circle_squeeze_escape_heading": strategy_result.circle_squeeze_escape_heading,
            "circle_squeeze_escape_gap_center_deg": (
                strategy_result.circle_squeeze_escape_gap_center_deg
            ),
            "circle_squeeze_closure_risk": strategy_result.circle_squeeze_closure_risk,
            "circle_squeeze_reason": strategy_result.circle_squeeze_reason,
            "persistent_threat_count": strategy_result.persistent_threat_count,
            "reacquired_threat_count": strategy_result.reacquired_threat_count,
            "recent_missing_threat_count": strategy_result.recent_missing_threat_count,
            "closing_threat_count": strategy_result.closing_threat_count,
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
        if scenario.expected_final_boost is not None:
            passed = passed and safe_boost == scenario.expected_final_boost
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


def _snake_from_fixture(data: dict) -> Snake:
    position = data["position"]
    snake = Snake(data["id"], position["x"], position["y"], data["heading"])
    snake.target_angle = data.get("wanted_heading", data["heading"])
    snake.mass = data["mass"]
    snake.recompute_segments()
    if "segments" in data:
        snake.segments = [
            Vector2(segment["x"], segment["y"])
            for segment in data["segments"]
        ]
    return snake


def _food_from_fixture(data: dict) -> FoodItem:
    position = data["position"]
    return FoodItem(position["x"], position["y"], data["value"])


def _telemetry_validator(candidate_type: str) -> Callable[[dict], bool]:
    if candidate_type == "projected_collision":
        return lambda result: result["collision_risk"] > 0.5
    if candidate_type == "enemy_intercept":
        return lambda result: result["enemy_head_intercept_risk"] > 1.5
    return lambda result: result["was_overridden"] is False


def build_promoted_telemetry_scenarios(
    fixture_path: str | Path = PROMOTED_TELEMETRY_SCENARIOS_PATH,
) -> Iterable[ScenarioCase]:
    path = Path(fixture_path)
    if not path.exists():
        return []

    records = json.loads(path.read_text(encoding="utf-8"))
    scenarios = []
    for record in records:
        my_snake = _snake_from_fixture(record["my_snake"])
        enemies = [
            _snake_from_fixture(enemy)
            for enemy in record.get("snakes", [])
        ]
        foods = [
            _food_from_fixture(food)
            for food in record.get("foods", [])
        ]
        scenarios.append(ScenarioCase(
            name=record["name"],
            my_snake=my_snake,
            snakes=[my_snake, *enemies],
            foods=foods,
            expected_gate_reason=record["expected_gate_reason"],
            expected_override=record["expected_override"],
            requested_heading=record["requested_heading"],
            validator=_telemetry_validator(record["candidate_type"]),
        ))
    return scenarios


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
    intercept_enemy = Snake(2, 75, 80, math.radians(-90))
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
            and result["enemy_head_intercept_time"] is not None
            and abs(result["selected_heading"]) > 0.1
        ),
    )

    non_crossing_snake = Snake(1, 0, 0, 0)
    non_crossing_enemy = Snake(2, 75, 80, math.radians(90))
    non_crossing_enemy.speed = Config.BASE_SPEED
    non_crossing_enemy.segments = []
    yield ScenarioCase(
        name="enemy_head_projection_non_crossing",
        my_snake=non_crossing_snake,
        snakes=[non_crossing_snake, non_crossing_enemy],
        foods=[],
        expected_gate_reason="none",
        expected_override=False,
        requested_heading=0.0,
        validator=lambda result: result["enemy_head_intercept_risk"] == 0.0,
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

    cluster_snake = Snake(1, 0, 0, 0)
    cluster_food = [
        FoodItem(180, 48, 6.0),
        FoodItem(196, 54, 5.5),
        FoodItem(188, 70, 5.0),
        FoodItem(45, 0, 2.0),
    ]
    yield ScenarioCase(
        name="loot_cluster_safe_preferred",
        my_snake=cluster_snake,
        snakes=[cluster_snake],
        foods=cluster_food,
        expected_mode="seek_food",
        expected_gate_reason="none",
        expected_override=False,
        validator=lambda result: (
            result["loot_cluster_pellet_count"] == 3
            and result["loot_cluster_total_value"] > 15.0
            and result["strategy"]["target_x"] > 180.0
            and result["strategy"]["target_y"] > 45.0
        ),
    )

    guarded_center_snake = Snake(1, 0, 0, 0)
    guarded_center_food = [
        FoodItem(170, 40, 6.0),
        FoodItem(190, 55, 5.5),
        FoodItem(185, 72, 5.0),
        FoodItem(45, 0, 2.0),
    ]
    yield ScenarioCase(
        name="guarded_cluster_center_safe",
        my_snake=guarded_center_snake,
        snakes=[guarded_center_snake],
        foods=guarded_center_food,
        expected_mode="seek_food",
        expected_gate_reason="none",
        expected_override=False,
        validator=lambda result: (
            result["loot_cluster_target_kind"] == "center"
            and result["loot_cluster_approach_x"] == result["loot_cluster_target_x"]
            and result["loot_cluster_approach_y"] == result["loot_cluster_target_y"]
        ),
    )

    guarded_edge_snake = Snake(1, 0, 0, 0)
    guarded_edge_food = [
        FoodItem(150, 50, 6.0),
        FoodItem(170, 0, 5.5),
        FoodItem(190, -20, 5.0),
        FoodItem(45, 0, 2.0),
    ]
    guarded_edge_enemy = Snake(2, 75, 80, math.radians(-90))
    guarded_edge_enemy.speed = Config.BASE_SPEED
    guarded_edge_enemy.segments = []
    yield ScenarioCase(
        name="guarded_cluster_edge_entry_preferred",
        my_snake=guarded_edge_snake,
        snakes=[guarded_edge_snake, guarded_edge_enemy],
        foods=guarded_edge_food,
        expected_mode="seek_food",
        expected_gate_reason="none",
        expected_override=False,
        validator=lambda result: (
            result["loot_cluster_target_kind"] == "pellet"
            and result["loot_cluster_approach_y"] > 0
            and result["enemy_head_intercept_risk"] == 0.0
        ),
    )

    guarded_blocked_snake = Snake(1, 0, 0, 0)
    guarded_blocked_food = [
        FoodItem(150, -8, 7.0),
        FoodItem(166, 6, 6.0),
        FoodItem(178, -4, 5.0),
        FoodItem(40, 80, 2.0),
    ]
    guarded_blocking_enemy = Snake(2, 100, 0, 0)
    guarded_blocking_enemy.segments = [Vector2(100, 0)]
    yield ScenarioCase(
        name="guarded_cluster_threat_blocks_collection",
        my_snake=guarded_blocked_snake,
        snakes=[guarded_blocked_snake, guarded_blocking_enemy],
        foods=guarded_blocked_food,
        expected_mode="avoid_threat",
        expected_gate_reason="none",
        expected_override=False,
        expected_final_boost=False,
        validator=lambda result: (
            result["loot_cluster_target_kind"] is None
            and result["boost"] is False
        ),
    )

    unsafe_cluster_snake = Snake(1, 0, 0, 0)
    unsafe_cluster_food = [
        FoodItem(150, -8, 7.0),
        FoodItem(166, 6, 6.0),
        FoodItem(178, -4, 5.0),
        FoodItem(40, 80, 2.0),
    ]
    unsafe_cluster_enemy = Snake(2, 100, 0, 0)
    unsafe_cluster_enemy.segments = [Vector2(100, 0)]
    yield ScenarioCase(
        name="loot_cluster_unsafe_rejected",
        my_snake=unsafe_cluster_snake,
        snakes=[unsafe_cluster_snake, unsafe_cluster_enemy],
        foods=unsafe_cluster_food,
        expected_mode="avoid_threat",
        expected_gate_reason="none",
        expected_override=False,
        validator=lambda result: (
            result["strategy"]["target_x"] == 100
            and result["loot_cluster_score"] is None
        ),
    )

    normal_food_snake = Snake(1, 0, 0, 0)
    normal_food = [
        FoodItem(30, 0, 2.0),
        FoodItem(80, 30, 1.0),
        FoodItem(140, -40, 1.0),
    ]
    yield ScenarioCase(
        name="normal_food_without_cluster",
        my_snake=normal_food_snake,
        snakes=[normal_food_snake],
        foods=normal_food,
        expected_mode="seek_food",
        expected_gate_reason="none",
        expected_override=False,
        validator=lambda result: (
            result["strategy"]["target_x"] == 30
            and result["strategy"]["target_y"] == 0
            and result["loot_cluster_score"] is None
        ),
    )

    boost_safe_snake = Snake(1, 0, 0, 0)
    boost_safe_snake.mass = 100
    boost_safe_snake.recompute_segments()
    yield ScenarioCase(
        name="boost_safe_clear_path",
        my_snake=boost_safe_snake,
        snakes=[boost_safe_snake],
        foods=[],
        expected_gate_reason="none",
        expected_override=False,
        requested_heading=0.0,
        requested_boost=True,
        expected_final_boost=True,
        validator=lambda result: (
            result["boost_allowed"] is True
            and result["boost_reason"] == "none"
        ),
    )

    boost_boundary_snake = _large_snake(1, Config.WORLD_RADIUS - 100, 0, 0)
    yield ScenarioCase(
        name="boost_blocked_near_boundary",
        my_snake=boost_boundary_snake,
        snakes=[boost_boundary_snake],
        foods=[],
        expected_mode="avoid_boundary",
        expected_gate_reason="boost_boundary_too_close",
        expected_override=False,
        requested_heading=0.0,
        requested_boost=True,
        expected_final_boost=False,
        validator=lambda result: (
            result["boundary_forward_distance"]
            > result["my_radius"] * 2.0 + (result["my_mass"] / 100.0)
            and result["boost_reason"] == "boost_boundary_too_close"
        ),
    )

    boost_intercept_snake = Snake(1, 0, 0, 0)
    boost_intercept_snake.angle = math.pi / 2
    boost_intercept_snake.mass = 100
    boost_intercept_enemy = Snake(2, 75, 80, math.radians(-90))
    boost_intercept_enemy.speed = Config.BASE_SPEED
    boost_intercept_enemy.segments = []
    yield ScenarioCase(
        name="boost_blocked_enemy_intercept",
        my_snake=boost_intercept_snake,
        snakes=[boost_intercept_snake, boost_intercept_enemy],
        foods=[],
        expected_gate_reason="enemy_head_intercept",
        expected_override=True,
        requested_heading=0.0,
        requested_boost=True,
        expected_final_boost=False,
        validator=lambda result: (
            result["enemy_head_intercept_risk"] > 1.5
            and result["boost_reason"] == "enemy_head_intercept"
        ),
    )

    boost_turn_snake = Snake(1, 0, 0, 0)
    boost_turn_snake.mass = 100
    boost_turn_snake.recompute_segments()
    yield ScenarioCase(
        name="boost_blocked_sharp_turn",
        my_snake=boost_turn_snake,
        snakes=[boost_turn_snake],
        foods=[],
        expected_gate_reason="boost_turn_too_sharp",
        expected_override=False,
        requested_heading=math.pi / 2,
        requested_boost=True,
        expected_final_boost=False,
        validator=lambda result: (
            result["boost_reason"] == "boost_turn_too_sharp"
            and result["collision_risk"] == 0.0
            and result["enemy_head_intercept_risk"] == 0.0
        ),
    )

    anti_coil_snake = Snake(1, 0, 0, 0)
    anti_coil_enemy = Snake(2, -90, 0, 0)
    anti_coil_enemy.segments = [
        Vector2(-90, 0),
        Vector2(-90, 55),
        Vector2(-55, 90),
        Vector2(0, 90),
        Vector2(55, 90),
        Vector2(-90, -55),
        Vector2(-55, -90),
        Vector2(0, -90),
        Vector2(55, -90),
    ]
    yield ScenarioCase(
        name="anti_coil_escape_open_gap",
        my_snake=anti_coil_snake,
        snakes=[anti_coil_snake, anti_coil_enemy],
        foods=[],
        expected_mode="avoid_threat",
        expected_gate_reason="none",
        expected_override=False,
        validator=lambda result: (
            result["anti_coil_escape_active"] is True
            and result["best_escape_heading"] == 0.0
            and result["strategy"]["defensive_reason"] in {
                "Anti-coil escape",
                "Circle squeeze counter",
            }
            and abs(result["selected_heading_deg"]) < 1.0
        ),
    )

    closing_gap_snake = Snake(1, 0, 0, 0)
    closing_gap_enemy = Snake(2, -90, 0, 0)
    closing_gap_enemy.segments = [
        Vector2(-90, 0),
        Vector2(-90, 55),
        Vector2(-55, 90),
        Vector2(0, 90),
        Vector2(55, 90),
        Vector2(-90, -55),
        Vector2(-55, -90),
        Vector2(0, -90),
    ]
    closing_gap_head = Snake(3, 75, 80, math.radians(-90))
    closing_gap_head.speed = Config.BASE_SPEED
    closing_gap_head.segments = []
    yield ScenarioCase(
        name="anti_coil_escape_rejects_closing_gap",
        my_snake=closing_gap_snake,
        snakes=[closing_gap_snake, closing_gap_enemy, closing_gap_head],
        foods=[],
        expected_mode="avoid_threat",
        expected_gate_reason="none",
        expected_override=False,
        validator=lambda result: (
            result["anti_coil_escape_active"] is True
            and result["best_escape_heading"] != 0.0
            and result["enemy_head_intercept_risk"] == 0.0
            and result["strategy"]["defensive_reason"] == "Anti-coil escape"
        ),
    )

    open_space_snake = Snake(1, 0, 0, 0)
    open_space_enemy = Snake(2, 60, 0, 0)
    open_space_enemy.segments = [
        Vector2(60, 0),
        Vector2(75, 12),
    ]
    yield ScenarioCase(
        name="anti_coil_no_false_positive_open_space",
        my_snake=open_space_snake,
        snakes=[open_space_snake, open_space_enemy],
        foods=[],
        expected_mode="avoid_threat",
        expected_gate_reason="none",
        expected_override=False,
        validator=lambda result: (
            result["anti_coil_escape_active"] is False
            and result["enclosure_sector_count"] < Strategy.ANTI_COIL_MIN_SECTORS
            and result["strategy"]["defensive_reason"] == "Forward danger"
        ),
    )

    circle_snake = Snake(1, 0, 0, 0)
    circle_enemy = Snake(2, -90, 0, 0)
    circle_enemy.segments = [
        Vector2(
            math.cos(math.radians(angle)) * 90,
            math.sin(math.radians(angle)) * 90,
        )
        for angle in (67.5, 90, 112.5, 135, 157.5, 180, 202.5, 225, 247.5, 270, 292.5)
    ]
    yield ScenarioCase(
        name="circle_squeeze_counter_open_gap",
        my_snake=circle_snake,
        snakes=[circle_snake, circle_enemy],
        foods=[],
        expected_mode="avoid_threat",
        expected_gate_reason="none",
        expected_override=False,
        validator=lambda result: (
            result["circle_squeeze_counter_active"] is True
            and result["circle_squeeze_sector_count"] >= Strategy.CIRCLE_SQUEEZE_MIN_SECTORS
            and abs(result["selected_heading_deg"]) < 35.0
            and result["strategy"]["defensive_reason"] == "Circle squeeze counter"
        ),
    )

    closing_circle_snake = Snake(1, 0, 0, 0)
    closing_circle_enemy = Snake(2, -90, 0, 0)
    closing_circle_enemy.segments = [
        Vector2(
            math.cos(math.radians(angle)) * 90,
            math.sin(math.radians(angle)) * 90,
        )
        for angle in (67.5, 90, 112.5, 135, 157.5, 180, 202.5, 225, 247.5, 270, 292.5)
    ]
    closing_circle_head = Snake(3, 75, 80, math.radians(-90))
    closing_circle_head.speed = Config.BASE_SPEED
    closing_circle_head.segments = []
    lower_closing_circle_head = Snake(4, 75, -80, math.radians(90))
    lower_closing_circle_head.speed = Config.BASE_SPEED
    lower_closing_circle_head.segments = []
    yield ScenarioCase(
        name="circle_squeeze_counter_closing_gap",
        my_snake=closing_circle_snake,
        snakes=[
            closing_circle_snake,
            closing_circle_enemy,
            closing_circle_head,
            lower_closing_circle_head,
        ],
        foods=[],
        expected_mode="avoid_threat",
        expected_gate_reason="none",
        expected_override=False,
        validator=lambda result: (
            result["circle_squeeze_counter_active"] is True
            and abs(result["selected_heading_deg"]) > 20.0
            and result["enemy_head_intercept_risk"] == 0.0
            and result["strategy"]["defensive_reason"] == "Circle squeeze counter"
        ),
    )

    open_arc_snake = Snake(1, 0, 0, 0)
    open_arc_enemy = Snake(2, 70, 0, 0)
    open_arc_enemy.segments = [
        Vector2(
            math.cos(math.radians(angle)) * 95,
            math.sin(math.radians(angle)) * 95,
        )
        for angle in (0, 22.5, 45, 67.5, 90)
    ]
    yield ScenarioCase(
        name="circle_squeeze_counter_no_false_positive_arc",
        my_snake=open_arc_snake,
        snakes=[open_arc_snake, open_arc_enemy],
        foods=[],
        expected_mode="avoid_threat",
        expected_gate_reason="none",
        expected_override=False,
        validator=lambda result: (
            result["circle_squeeze_counter_active"] is False
            and result["circle_squeeze_sector_count"] is None
            and result["strategy"]["defensive_reason"] == "Forward danger"
        ),
    )

    boundary_circle_snake = Snake(1, Config.WORLD_RADIUS - 50, 0, 0)
    boundary_circle_enemy = Snake(2, boundary_circle_snake.pos.x - 90, 0, 0)
    boundary_circle_enemy.segments = [
        Vector2(
            boundary_circle_snake.pos.x + math.cos(math.radians(angle)) * 90,
            math.sin(math.radians(angle)) * 90,
        )
        for angle in (67.5, 135, 157.5, 180, 202.5, 225, 247.5, 270, 292.5)
    ]
    yield ScenarioCase(
        name="circle_squeeze_counter_prioritizes_boundary_safety",
        my_snake=boundary_circle_snake,
        snakes=[boundary_circle_snake, boundary_circle_enemy],
        foods=[],
        expected_mode="avoid_boundary",
        expected_gate_reason="none",
        expected_override=False,
        requested_heading=math.pi / 2,
        validator=lambda result: (
            result["circle_squeeze_counter_active"] is False
            and result["selected_heading_deg"] == 90.0
        ),
    )

    partial_guard_snake = Snake(1, 0, 0, 0)
    partial_guard_food = [
        FoodItem(170, -15, 6.0),
        FoodItem(190, 0, 5.5),
        FoodItem(178, 20, 5.0),
        FoodItem(45, 0, 2.0),
    ]
    partial_guard_enemy = Snake(2, 185, 95, 0)
    partial_guard_enemy.segments = []
    yield ScenarioCase(
        name="partial_guard_safe_offset",
        my_snake=partial_guard_snake,
        snakes=[partial_guard_snake, partial_guard_enemy],
        foods=partial_guard_food,
        expected_mode="seek_food",
        expected_gate_reason="none",
        expected_override=False,
        expected_final_boost=False,
        validator=lambda result: (
            result["partial_guard_active"] is True
            and result["partial_guard_side"] == "left"
            and result["loot_cluster_target_kind"] == "partial_guard"
            and result["strategy"]["target_y"] > result["loot_cluster_target_y"]
        ),
    )

    unsafe_guard_snake = Snake(1, 0, 0, 0)
    unsafe_guard_food = [
        FoodItem(170, -15, 6.0),
        FoodItem(190, 0, 5.5),
        FoodItem(178, 20, 5.0),
        FoodItem(45, 0, 2.0),
    ]
    unsafe_guard_enemy = Snake(2, 185, 95, 0)
    unsafe_guard_enemy.segments = []
    unsafe_guard_closer = Snake(3, 120, 130, math.radians(-90))
    unsafe_guard_closer.speed = Config.BASE_SPEED
    unsafe_guard_closer.segments = []
    yield ScenarioCase(
        name="partial_guard_rejects_unsafe_offset",
        my_snake=unsafe_guard_snake,
        snakes=[unsafe_guard_snake, unsafe_guard_enemy, unsafe_guard_closer],
        foods=unsafe_guard_food,
        expected_mode="seek_food",
        expected_gate_reason="none",
        expected_override=False,
        expected_final_boost=False,
        validator=lambda result: (
            result["partial_guard_active"] is True
            and result["partial_guard_side"] == "right"
            and result["enemy_head_intercept_risk"] == 0.0
        ),
    )

    no_pressure_snake = Snake(1, 0, 0, 0)
    no_pressure_food = [
        FoodItem(170, -15, 6.0),
        FoodItem(190, 0, 5.5),
        FoodItem(178, 20, 5.0),
        FoodItem(45, 0, 2.0),
    ]
    yield ScenarioCase(
        name="partial_guard_not_when_no_enemy_pressure",
        my_snake=no_pressure_snake,
        snakes=[no_pressure_snake],
        foods=no_pressure_food,
        expected_mode="seek_food",
        expected_gate_reason="none",
        expected_override=False,
        validator=lambda result: (
            result["partial_guard_active"] is False
            and result["loot_cluster_target_kind"] == "center"
        ),
    )

    anti_coil_guard_snake = Snake(1, 0, 0, 0)
    anti_coil_guard_enemy = Snake(2, -90, 0, 0)
    anti_coil_guard_enemy.segments = [
        Vector2(-90, 0),
        Vector2(-90, 55),
        Vector2(-55, 90),
        Vector2(0, 90),
        Vector2(55, 90),
        Vector2(-90, -55),
        Vector2(-55, -90),
        Vector2(0, -90),
        Vector2(55, -90),
    ]
    anti_coil_guard_food = [
        FoodItem(170, -15, 6.0),
        FoodItem(190, 0, 5.5),
        FoodItem(178, 20, 5.0),
    ]
    anti_coil_guard_pressure = Snake(3, 185, 95, 0)
    anti_coil_guard_pressure.segments = []
    yield ScenarioCase(
        name="partial_guard_not_during_anti_coil_escape",
        my_snake=anti_coil_guard_snake,
        snakes=[anti_coil_guard_snake, anti_coil_guard_enemy, anti_coil_guard_pressure],
        foods=anti_coil_guard_food,
        expected_mode="avoid_threat",
        expected_gate_reason="none",
        expected_override=False,
        validator=lambda result: (
            result["anti_coil_escape_active"] is True
            and result["partial_guard_active"] is False
            and result["strategy"]["defensive_reason"] in {
                "Anti-coil escape",
                "Circle squeeze counter",
            }
        ),
    )

    for scenario in build_promoted_telemetry_scenarios():
        yield scenario


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

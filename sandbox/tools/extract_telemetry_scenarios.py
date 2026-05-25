from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from sandbox.bot.perception import Perception
from sandbox.bot.safety_gate import SafetyGate
from sandbox.bot.strategy import Strategy
from sandbox.config import Config
from sandbox.food import FoodItem
from sandbox.snake import Snake
from sandbox.vector import Vector2


DEFAULT_INPUT = Path("live_telemetry.jsonl")
DEFAULT_OUTPUT = Path("reports/telemetry_scenario_candidates.jsonl")
REQUIRED_FIELDS = (
    "source_line",
    "candidate_type",
    "reason",
    "timestamp_or_tick",
    "my_mass",
    "my_radius",
    "my_position",
    "my_heading",
    "requested_heading",
    "selected_heading",
    "boost",
    "was_overridden",
    "gate_reason",
    "collision_risk",
    "enemy_head_intercept_risk",
    "boundary_forward_distance",
    "raw_shape_keys",
    "usable_for_harness",
    "missing_fields",
)


@dataclass
class ExtractionStats:
    scanned: int = 0
    malformed: int = 0
    skipped: int = 0
    written: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    usable_for_harness: int = 0
    message: str | None = None


def empty_candidate(source_line: int, reason: str) -> dict:
    return {
        "source_line": source_line,
        "candidate_type": "unknown_insufficient_data",
        "reason": reason,
        "timestamp_or_tick": None,
        "my_mass": None,
        "my_radius": None,
        "my_position": None,
        "my_heading": None,
        "requested_heading": None,
        "selected_heading": None,
        "boost": None,
        "was_overridden": None,
        "gate_reason": None,
        "collision_risk": None,
        "enemy_head_intercept_risk": None,
        "boundary_forward_distance": None,
        "raw_shape_keys": [],
        "usable_for_harness": False,
        "missing_fields": [],
    }


def validate_required_fields(candidate: dict) -> None:
    for field_name in REQUIRED_FIELDS:
        candidate.setdefault(field_name, None)


def _map_radius(raw_data: dict) -> float | None:
    value = raw_data.get("map_radius")
    if isinstance(value, (int, float)) and value > 0:
        return float(value)
    return None


def _normalize_point(raw_point: dict, raw_data: dict) -> dict:
    map_radius = _map_radius(raw_data)
    if map_radius is None:
        return {"x": float(raw_point["x"]), "y": float(raw_point["y"])}
    scale = Config.WORLD_RADIUS / map_radius
    return {
        "x": (float(raw_point["x"]) - map_radius) * scale,
        "y": (float(raw_point["y"]) - map_radius) * scale,
    }


def _snake_from_raw(raw_snake: dict, raw_data: dict, max_segments: int) -> Snake:
    point = _normalize_point(raw_snake, raw_data)
    angle = float(raw_snake.get("angle", 0.0))
    snake = Snake(int(raw_snake.get("id", 0)), point["x"], point["y"], angle)
    snake.target_angle = float(raw_snake.get("wang", angle))
    snake.mass = float(raw_snake.get("mass", Config.INITIAL_MASS))
    snake.recompute_segments()
    trail = raw_snake.get("trail", [])
    if isinstance(trail, list) and trail:
        snake.segments = [
            Vector2(**_normalize_point(segment, raw_data))
            for segment in trail[:max_segments]
            if isinstance(segment, dict) and "x" in segment and "y" in segment
        ]
    return snake


def _food_from_raw(raw_food: dict, raw_data: dict) -> FoodItem:
    point = _normalize_point(raw_food, raw_data)
    return FoodItem(point["x"], point["y"], float(raw_food.get("value", Config.NATURAL_FOOD_MIN_VALUE)))


def _missing_fields(row: dict) -> list[str]:
    missing = []
    raw_data = row.get("raw_data")
    action = row.get("action")
    if not isinstance(raw_data, dict):
        return ["raw_data"]
    raw_my_snake = raw_data.get("my_snake")
    if not isinstance(raw_my_snake, dict):
        missing.append("raw_data.my_snake")
    else:
        for key in ("x", "y", "angle", "mass"):
            if key not in raw_my_snake:
                missing.append(f"raw_data.my_snake.{key}")
    if not isinstance(action, dict):
        missing.append("action")
    elif "target_angle" not in action:
        missing.append("action.target_angle")
    if "snakes" not in raw_data:
        missing.append("raw_data.snakes")
    if "foods" not in raw_data:
        missing.append("raw_data.foods")
    return missing


def _evaluate_row(
    row: dict,
    max_snakes: int,
    max_food: int,
    max_segments_per_snake: int,
) -> dict:
    raw_data = row["raw_data"]
    action = row["action"]
    my_snake = _snake_from_raw(raw_data["my_snake"], raw_data, max_segments_per_snake)
    enemies = [
        _snake_from_raw(raw_snake, raw_data, max_segments_per_snake)
        for raw_snake in raw_data.get("snakes", [])[:max_snakes]
        if isinstance(raw_snake, dict) and "x" in raw_snake and "y" in raw_snake
    ]
    foods = [
        _food_from_raw(raw_food, raw_data)
        for raw_food in raw_data.get("foods", [])[:max_food]
        if isinstance(raw_food, dict) and "x" in raw_food and "y" in raw_food
    ]
    snakes = [my_snake, *enemies]
    requested_heading = float(action["target_angle"])
    requested_boost = bool(action.get("boost", False))

    perception = Perception(vision_radius=Config.AI_VISION_RADIUS)
    state = perception.build(my_snake, snakes, foods)
    min_turn_radius = state.my_radius * 2.0 + (state.my_mass / 100.0)
    eval_result = Strategy()._evaluate_heading(
        requested_heading,
        math.cos(requested_heading),
        math.sin(requested_heading),
        state,
        min_turn_radius,
    )
    selected_heading, selected_boost, was_overridden, gate_reason = SafetyGate().filter_action(
        state,
        requested_heading,
        requested_boost,
    )

    return {
        "my_snake": my_snake,
        "state": state,
        "requested_heading": requested_heading,
        "selected_heading": selected_heading,
        "boost": selected_boost,
        "was_overridden": was_overridden,
        "gate_reason": gate_reason,
        "collision_risk": eval_result.collision_risk,
        "enemy_head_intercept_risk": eval_result.enemy_head_intercept_risk,
        "boundary_forward_distance": eval_result.boundary_forward_distance,
        "visible_snakes": len(state.visible_snakes),
        "visible_threats": len(state.visible_threats),
        "visible_food": len(state.visible_food),
    }


def classify_candidate(evaluation: dict) -> tuple[str, str]:
    if evaluation["was_overridden"] and evaluation["gate_reason"] == "boundary_too_close":
        return "boundary_risk", "SafetyGate overrode a boundary-facing or low-open-space heading."
    if evaluation["was_overridden"] and evaluation["gate_reason"] == "projected_collision":
        return "projected_collision", "SafetyGate overrode a projected collision heading."
    if evaluation["was_overridden"] and evaluation["gate_reason"] == "enemy_head_intercept":
        return "enemy_intercept", "SafetyGate overrode a projected enemy intercept heading."
    if evaluation["collision_risk"] > 0.5:
        return "high_collision_risk", "Heading evaluation reported high collision risk."
    if evaluation["enemy_head_intercept_risk"] > 1.5:
        return "enemy_intercept", "Heading evaluation reported projected enemy intercept risk."
    if evaluation["boundary_forward_distance"] is not None and evaluation["boundary_forward_distance"] < Config.AI_VISION_RADIUS:
        return "boundary_risk", "Heading has limited forward distance to the world boundary."
    if evaluation["boost"] is False and evaluation["was_overridden"]:
        return "boost_while_unsafe", "Unsafe request had boost disabled by SafetyGate."
    if evaluation["state"].my_mass >= 1000:
        return "large_snake_survival", "Telemetry frame contains a large controlled snake."
    return "unknown_insufficient_data", "Frame parsed but did not match a stronger candidate category."


def candidate_from_row(
    row: dict,
    source_line: int,
    max_snakes: int = 5,
    max_food: int = 25,
    max_segments_per_snake: int = 80,
) -> dict:
    candidate = empty_candidate(source_line, "Telemetry row did not contain enough shape data.")
    raw_data = row.get("raw_data") if isinstance(row.get("raw_data"), dict) else {}
    candidate["timestamp_or_tick"] = row.get("timestamp")
    candidate["raw_shape_keys"] = sorted(raw_data.keys())
    candidate["missing_fields"] = _missing_fields(row)

    if candidate["missing_fields"]:
        validate_required_fields(candidate)
        return candidate

    try:
        evaluation = _evaluate_row(row, max_snakes, max_food, max_segments_per_snake)
    except (TypeError, ValueError, KeyError) as exc:
        candidate["reason"] = f"Telemetry row could not be evaluated: {type(exc).__name__}."
        candidate["missing_fields"] = candidate["missing_fields"] or ["evaluation"]
        validate_required_fields(candidate)
        return candidate

    my_snake = evaluation["my_snake"]
    candidate_type, reason = classify_candidate(evaluation)
    candidate.update({
        "candidate_type": candidate_type,
        "reason": reason,
        "my_mass": my_snake.mass,
        "my_radius": Config.get_radius(my_snake.mass),
        "my_position": {"x": my_snake.pos.x, "y": my_snake.pos.y},
        "my_heading": my_snake.angle,
        "requested_heading": evaluation["requested_heading"],
        "selected_heading": evaluation["selected_heading"],
        "boost": evaluation["boost"],
        "was_overridden": evaluation["was_overridden"],
        "gate_reason": evaluation["gate_reason"],
        "collision_risk": evaluation["collision_risk"],
        "enemy_head_intercept_risk": evaluation["enemy_head_intercept_risk"],
        "boundary_forward_distance": evaluation["boundary_forward_distance"],
        "usable_for_harness": candidate_type != "unknown_insufficient_data",
        "missing_fields": [],
    })
    validate_required_fields(candidate)
    return candidate


def iter_jsonl_candidates(
    input_path: Path,
    scan_limit: int,
    stride: int,
    max_snakes: int,
    max_food: int,
    max_segments_per_snake: int,
    include_unknown: bool,
    stats: ExtractionStats,
) -> Iterable[dict]:
    with input_path.open("r", encoding="utf-8") as handle:
        for source_line, line in enumerate(handle, start=1):
            if scan_limit and stats.scanned >= scan_limit:
                break
            stats.scanned += 1
            if (source_line - 1) % max(1, stride) != 0:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                stats.malformed += 1
                continue
            candidate = candidate_from_row(
                row,
                source_line,
                max_snakes=max_snakes,
                max_food=max_food,
                max_segments_per_snake=max_segments_per_snake,
            )
            if candidate["candidate_type"] == "unknown_insufficient_data" and not include_unknown:
                stats.skipped += 1
                continue
            yield candidate


def extract_candidates(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
    max_candidates: int = 20,
    scan_limit: int = 2000,
    stride: int = 10,
    max_snakes: int = 5,
    max_food: int = 25,
    max_segments_per_snake: int = 80,
    include_unknown: bool = True,
) -> ExtractionStats:
    stats = ExtractionStats()
    if not input_path.exists():
        stats.message = f"Telemetry input not found: {input_path}"
        return stats

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output:
        for candidate in iter_jsonl_candidates(
            input_path,
            scan_limit,
            stride,
            max_snakes,
            max_food,
            max_segments_per_snake,
            include_unknown,
            stats,
        ):
            output.write(json.dumps(candidate, sort_keys=True) + "\n")
            stats.written += 1
            stats.by_type[candidate["candidate_type"]] = stats.by_type.get(candidate["candidate_type"], 0) + 1
            if candidate["usable_for_harness"]:
                stats.usable_for_harness += 1
            if stats.written >= max_candidates:
                break
    stats.message = f"Wrote {stats.written} candidate records to {output_path}"
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract review-only deterministic scenario candidates from telemetry."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-candidates", type=int, default=20)
    parser.add_argument("--scan-limit", type=int, default=2000)
    parser.add_argument("--stride", type=int, default=10)
    parser.add_argument("--max-snakes", type=int, default=5)
    parser.add_argument("--max-food", type=int, default=25)
    parser.add_argument("--max-segments-per-snake", type=int, default=80)
    parser.add_argument("--exclude-unknown", action="store_true")
    args = parser.parse_args()

    stats = extract_candidates(
        input_path=args.input,
        output_path=args.output,
        max_candidates=args.max_candidates,
        scan_limit=args.scan_limit,
        stride=args.stride,
        max_snakes=args.max_snakes,
        max_food=args.max_food,
        max_segments_per_snake=args.max_segments_per_snake,
        include_unknown=not args.exclude_unknown,
    )
    print(json.dumps({
        "by_type": stats.by_type,
        "input": str(args.input),
        "malformed": stats.malformed,
        "message": stats.message,
        "output": str(args.output),
        "scanned": stats.scanned,
        "skipped": stats.skipped,
        "usable_for_harness": stats.usable_for_harness,
        "written": stats.written,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

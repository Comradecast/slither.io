from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from sandbox.bot.perception import Perception
from sandbox.bot.safety_gate import SafetyGate
from sandbox.bot.steering import Steering
from sandbox.bot.strategy import Strategy
from sandbox.config import Config
from sandbox.tools.extract_telemetry_scenarios import _food_from_raw, _snake_from_raw


DEFAULT_INPUT = Path("live_telemetry.jsonl")
DEFAULT_OUTPUT = Path("reports/live_evaluation_summary.json")
DEFAULT_FRAMES_OUTPUT = Path("reports/live_evaluation_frames.jsonl")


@dataclass
class LiveEvaluationStats:
    scanned: int = 0
    malformed: int = 0
    skipped: int = 0
    evaluated_frames: int = 0
    explicit_deaths: int = 0
    inferred_session_ends: int = 0
    message: str | None = None


@dataclass
class LiveSessionSummary:
    session_index: int
    snake_id: int
    start_line: int
    end_line: int
    frame_count: int
    start_timestamp: float | None
    end_timestamp: float | None
    duration_seconds: float | None
    start_mass: float
    final_mass: float
    peak_mass: float
    min_mass: float
    mass_delta: float
    override_count: int = 0
    boost_requested_count: int = 0
    boost_allowed_count: int = 0
    explicit_death_count: int = 0
    inferred_end_reason: str = "eof"
    gate_reasons: dict[str, int] = field(default_factory=dict)
    strategy_modes: dict[str, int] = field(default_factory=dict)
    max_persistent_threat_count: int = 0
    max_reacquired_threat_count: int = 0
    max_recent_missing_threat_count: int = 0
    max_closing_threat_count: int = 0


@dataclass
class LiveEvaluationSummary:
    input: str
    output: str
    frames_output: str | None
    max_frames: int
    stride: int
    session_gap_seconds: float
    stats: LiveEvaluationStats
    session_count: int
    total_duration_seconds: float
    total_frames: int
    survived_session_count: int
    explicit_death_count: int
    inferred_session_end_count: int
    override_count: int
    override_rate: float
    boost_requested_count: int
    boost_allowed_count: int
    boost_allowed_rate: float
    aggregate_gate_reasons: dict[str, int]
    aggregate_strategy_modes: dict[str, int]
    mass: dict[str, float | None]
    sessions: list[LiveSessionSummary]
    comparison: dict | None = None


class _SessionAccumulator:
    def __init__(self, session_index: int, snake_id: int, source_line: int, timestamp: float | None, mass: float):
        self.session_index = session_index
        self.snake_id = snake_id
        self.start_line = source_line
        self.end_line = source_line
        self.frame_count = 0
        self.start_timestamp = timestamp
        self.end_timestamp = timestamp
        self.start_mass = mass
        self.final_mass = mass
        self.peak_mass = mass
        self.min_mass = mass
        self.override_count = 0
        self.boost_requested_count = 0
        self.boost_allowed_count = 0
        self.explicit_death_count = 0
        self.gate_reasons: dict[str, int] = {}
        self.strategy_modes: dict[str, int] = {}
        self.max_persistent_threat_count = 0
        self.max_reacquired_threat_count = 0
        self.max_recent_missing_threat_count = 0
        self.max_closing_threat_count = 0
        self.perception = Perception(vision_radius=Config.AI_VISION_RADIUS)

    def add_frame(self, frame: dict) -> None:
        self.end_line = frame["source_line"]
        self.frame_count += 1
        self.end_timestamp = frame["timestamp"]
        mass = frame["my_mass"]
        self.final_mass = mass
        self.peak_mass = max(self.peak_mass, mass)
        self.min_mass = min(self.min_mass, mass)
        if frame["was_overridden"]:
            self.override_count += 1
        if frame["requested_boost"]:
            self.boost_requested_count += 1
        if frame["final_boost"]:
            self.boost_allowed_count += 1
        if frame["explicit_death"]:
            self.explicit_death_count += 1
        self.gate_reasons[frame["gate_reason"]] = self.gate_reasons.get(frame["gate_reason"], 0) + 1
        self.strategy_modes[frame["strategy_mode"]] = self.strategy_modes.get(frame["strategy_mode"], 0) + 1
        self.max_persistent_threat_count = max(
            self.max_persistent_threat_count,
            frame["persistent_threat_count"],
        )
        self.max_reacquired_threat_count = max(
            self.max_reacquired_threat_count,
            frame["reacquired_threat_count"],
        )
        self.max_recent_missing_threat_count = max(
            self.max_recent_missing_threat_count,
            frame["recent_missing_threat_count"],
        )
        self.max_closing_threat_count = max(
            self.max_closing_threat_count,
            frame["closing_threat_count"],
        )

    def summary(self, inferred_end_reason: str) -> LiveSessionSummary:
        duration = None
        if self.start_timestamp is not None and self.end_timestamp is not None:
            duration = max(0.0, self.end_timestamp - self.start_timestamp)
        return LiveSessionSummary(
            session_index=self.session_index,
            snake_id=self.snake_id,
            start_line=self.start_line,
            end_line=self.end_line,
            frame_count=self.frame_count,
            start_timestamp=self.start_timestamp,
            end_timestamp=self.end_timestamp,
            duration_seconds=duration,
            start_mass=self.start_mass,
            final_mass=self.final_mass,
            peak_mass=self.peak_mass,
            min_mass=self.min_mass,
            mass_delta=self.final_mass - self.start_mass,
            override_count=self.override_count,
            boost_requested_count=self.boost_requested_count,
            boost_allowed_count=self.boost_allowed_count,
            explicit_death_count=self.explicit_death_count,
            inferred_end_reason=inferred_end_reason,
            gate_reasons=dict(sorted(self.gate_reasons.items())),
            strategy_modes=dict(sorted(self.strategy_modes.items())),
            max_persistent_threat_count=self.max_persistent_threat_count,
            max_reacquired_threat_count=self.max_reacquired_threat_count,
            max_recent_missing_threat_count=self.max_recent_missing_threat_count,
            max_closing_threat_count=self.max_closing_threat_count,
        )


def _timestamp(row: dict) -> float | None:
    value = row.get("timestamp", row.get("tick"))
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _explicit_death(row: dict) -> bool:
    if row.get("event") in {"death", "dead"}:
        return True
    raw_data = row.get("raw_data")
    if not isinstance(raw_data, dict):
        return False
    my_snake = raw_data.get("my_snake")
    if not isinstance(my_snake, dict):
        return False
    return my_snake.get("alive") is False or my_snake.get("dead") is True


def _gate_reason_counts(sessions: Iterable[LiveSessionSummary]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for session in sessions:
        for reason, count in session.gate_reasons.items():
            counts[reason] = counts.get(reason, 0) + count
    return dict(sorted(counts.items()))


def _strategy_mode_counts(sessions: Iterable[LiveSessionSummary]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for session in sessions:
        for mode, count in session.strategy_modes.items():
            counts[mode] = counts.get(mode, 0) + count
    return dict(sorted(counts.items()))


def _parse_row(line: str) -> dict | None:
    row = json.loads(line)
    if not isinstance(row, dict):
        return None
    raw_data = row.get("raw_data")
    if not isinstance(raw_data, dict):
        return None
    my_snake = raw_data.get("my_snake")
    if not isinstance(my_snake, dict):
        return None
    if not all(key in my_snake for key in ("id", "x", "y", "angle", "mass")):
        return None
    return row


def _evaluate_frame(
    row: dict,
    source_line: int,
    perception: Perception,
    max_snakes: int,
    max_food: int,
    max_segments_per_snake: int,
) -> dict:
    raw_data = row["raw_data"]
    raw_my_snake = raw_data["my_snake"]
    my_snake = _snake_from_raw(raw_my_snake, raw_data, max_segments_per_snake)
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
    state = perception.build(my_snake, [my_snake, *enemies], foods)
    strategy_result = Strategy().decide(state)
    steering_result = Steering().compute(strategy_result, state)
    requested_boost = bool(row.get("action", {}).get("boost", False))
    action = row.get("action") if isinstance(row.get("action"), dict) else {}
    observed_heading = action.get("target_angle")
    requested_heading = (
        float(observed_heading)
        if isinstance(observed_heading, (int, float))
        else steering_result.heading
    )
    safe_angle, safe_boost, overridden, reason = SafetyGate().filter_action(
        state,
        requested_heading,
        requested_boost,
    )
    heading_delta = None
    if isinstance(observed_heading, (int, float)):
        heading_delta = abs(_normalize_angle(float(observed_heading) - safe_angle))

    return {
        "source_line": source_line,
        "timestamp": _timestamp(row),
        "snake_id": int(raw_my_snake["id"]),
        "my_mass": my_snake.mass,
        "strategy_mode": strategy_result.mode.value,
        "strategy_defensive_reason": strategy_result.defensive_reason,
        "strategy_heading": steering_result.heading,
        "requested_heading": requested_heading,
        "final_heading": safe_angle,
        "observed_action_heading": observed_heading if isinstance(observed_heading, (int, float)) else None,
        "observed_action_heading_delta": heading_delta,
        "requested_boost": requested_boost,
        "final_boost": safe_boost,
        "was_overridden": overridden,
        "gate_reason": reason,
        "explicit_death": _explicit_death(row),
        "visible_snakes": len(state.visible_snakes),
        "visible_threats": len(state.visible_threats),
        "visible_food": len(state.visible_food),
        "persistent_threat_count": state.persistent_threat_count,
        "reacquired_threat_count": state.reacquired_threat_count,
        "recent_missing_threat_count": state.recent_missing_threat_count,
        "closing_threat_count": state.closing_threat_count,
    }


def _normalize_angle(angle: float) -> float:
    return (angle + math.pi) % (2 * math.pi) - math.pi


def _comparison(current: LiveEvaluationSummary, baseline_path: Path | None) -> dict | None:
    if baseline_path is None or not baseline_path.exists():
        return None
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "baseline": str(baseline_path),
            "error": "baseline_unreadable",
        }
    if not isinstance(baseline, dict):
        return {
            "baseline": str(baseline_path),
            "error": "baseline_invalid_shape",
        }
    mass = baseline.get("mass") or {}
    if not isinstance(mass, dict):
        return {
            "baseline": str(baseline_path),
            "error": "baseline_invalid_shape",
        }
    try:
        return {
            "baseline": str(baseline_path),
            "override_count_delta": current.override_count - int(baseline.get("override_count", 0)),
            "override_rate_delta": current.override_rate - float(baseline.get("override_rate", 0.0)),
            "total_frames_delta": current.total_frames - int(baseline.get("total_frames", 0)),
            "explicit_death_count_delta": (
                current.explicit_death_count
                - int(baseline.get("explicit_death_count", 0))
            ),
            "inferred_session_end_count_delta": (
                current.inferred_session_end_count
                - int(baseline.get("inferred_session_end_count", 0))
            ),
            "peak_mass_delta": (
                (current.mass.get("peak_mass") or 0.0)
                - float(mass.get("peak_mass") or 0.0)
            ),
        }
    except (TypeError, ValueError):
        return {
            "baseline": str(baseline_path),
            "error": "baseline_invalid_values",
        }


def analyze_live_telemetry(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
    frames_output_path: Path | None = DEFAULT_FRAMES_OUTPUT,
    max_frames: int = 2000,
    stride: int = 1,
    session_gap_seconds: float = 12.0,
    max_snakes: int = 8,
    max_food: int = 80,
    max_segments_per_snake: int = 120,
    baseline_path: Path | None = None,
) -> LiveEvaluationSummary:
    stats = LiveEvaluationStats()
    sessions: list[LiveSessionSummary] = []
    current: _SessionAccumulator | None = None
    frame_handle = None

    if not input_path.exists():
        stats.message = f"Telemetry input not found: {input_path}"
        return LiveEvaluationSummary(
            input=str(input_path),
            output=str(output_path),
            frames_output=str(frames_output_path) if frames_output_path else None,
            max_frames=max_frames,
            stride=stride,
            session_gap_seconds=session_gap_seconds,
            stats=stats,
            session_count=0,
            total_duration_seconds=0.0,
            total_frames=0,
            survived_session_count=0,
            explicit_death_count=0,
            inferred_session_end_count=0,
            override_count=0,
            override_rate=0.0,
            boost_requested_count=0,
            boost_allowed_count=0,
            boost_allowed_rate=0.0,
            aggregate_gate_reasons={},
            aggregate_strategy_modes={},
            mass={"start_mass": None, "final_mass": None, "peak_mass": None, "min_mass": None, "mass_delta": None},
            sessions=[],
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if frames_output_path is not None:
        frames_output_path.parent.mkdir(parents=True, exist_ok=True)
        frame_handle = frames_output_path.open("w", encoding="utf-8")

    try:
        with input_path.open("r", encoding="utf-8") as handle:
            for source_line, line in enumerate(handle, start=1):
                if max_frames and stats.evaluated_frames >= max_frames:
                    break
                stats.scanned += 1
                if (source_line - 1) % max(1, stride) != 0:
                    continue
                try:
                    row = _parse_row(line)
                except json.JSONDecodeError:
                    stats.malformed += 1
                    continue
                if row is None:
                    stats.skipped += 1
                    continue

                raw_my_snake = row["raw_data"]["my_snake"]
                snake_id = int(raw_my_snake["id"])
                timestamp = _timestamp(row)
                new_session_reason = None
                if current is not None and snake_id != current.snake_id:
                    new_session_reason = "snake_id_changed"
                elif (
                    current is not None
                    and timestamp is not None
                    and current.end_timestamp is not None
                    and timestamp - current.end_timestamp > session_gap_seconds
                ):
                    new_session_reason = "timestamp_gap"

                if current is None or new_session_reason is not None:
                    if current is not None:
                        sessions.append(current.summary(new_session_reason or "new_session"))
                        stats.inferred_session_ends += 1
                    current = _SessionAccumulator(
                        len(sessions) + 1,
                        snake_id,
                        source_line,
                        timestamp,
                        float(raw_my_snake["mass"]),
                    )

                frame = _evaluate_frame(
                    row,
                    source_line,
                    current.perception,
                    max_snakes=max_snakes,
                    max_food=max_food,
                    max_segments_per_snake=max_segments_per_snake,
                )
                current.add_frame(frame)
                stats.evaluated_frames += 1
                if frame["explicit_death"]:
                    stats.explicit_deaths += 1
                if frame_handle is not None:
                    frame_handle.write(json.dumps(frame, sort_keys=True) + "\n")
    finally:
        if frame_handle is not None:
            frame_handle.close()

    if current is not None:
        sessions.append(current.summary("eof"))

    total_frames = sum(session.frame_count for session in sessions)
    total_duration = sum(session.duration_seconds or 0.0 for session in sessions)
    override_count = sum(session.override_count for session in sessions)
    boost_requested_count = sum(session.boost_requested_count for session in sessions)
    boost_allowed_count = sum(session.boost_allowed_count for session in sessions)
    explicit_death_count = sum(session.explicit_death_count for session in sessions)
    survived_session_count = sum(1 for session in sessions if session.explicit_death_count == 0)
    start_mass = sessions[0].start_mass if sessions else None
    final_mass = sessions[-1].final_mass if sessions else None
    peak_mass = max((session.peak_mass for session in sessions), default=None)
    min_mass = min((session.min_mass for session in sessions), default=None)

    summary = LiveEvaluationSummary(
        input=str(input_path),
        output=str(output_path),
        frames_output=str(frames_output_path) if frames_output_path else None,
        max_frames=max_frames,
        stride=stride,
        session_gap_seconds=session_gap_seconds,
        stats=stats,
        session_count=len(sessions),
        total_duration_seconds=total_duration,
        total_frames=total_frames,
        survived_session_count=survived_session_count,
        explicit_death_count=explicit_death_count,
        inferred_session_end_count=stats.inferred_session_ends,
        override_count=override_count,
        override_rate=override_count / total_frames if total_frames else 0.0,
        boost_requested_count=boost_requested_count,
        boost_allowed_count=boost_allowed_count,
        boost_allowed_rate=boost_allowed_count / boost_requested_count if boost_requested_count else 0.0,
        aggregate_gate_reasons=_gate_reason_counts(sessions),
        aggregate_strategy_modes=_strategy_mode_counts(sessions),
        mass={
            "start_mass": start_mass,
            "final_mass": final_mass,
            "peak_mass": peak_mass,
            "min_mass": min_mass,
            "mass_delta": final_mass - start_mass if final_mass is not None and start_mass is not None else None,
        },
        sessions=sessions,
    )
    summary.comparison = _comparison(summary, baseline_path)
    stats.message = f"Wrote live evaluation summary to {output_path}"
    output_path.write_text(json.dumps(asdict(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize controlled live bot telemetry runs.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--frames-output", type=Path, default=DEFAULT_FRAMES_OUTPUT)
    parser.add_argument("--no-frames-output", action="store_true")
    parser.add_argument("--max-frames", type=int, default=2000)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--session-gap-seconds", type=float, default=12.0)
    parser.add_argument("--max-snakes", type=int, default=8)
    parser.add_argument("--max-food", type=int, default=80)
    parser.add_argument("--max-segments-per-snake", type=int, default=120)
    parser.add_argument("--baseline", type=Path, default=None)
    args = parser.parse_args()

    summary = analyze_live_telemetry(
        input_path=args.input,
        output_path=args.output,
        frames_output_path=None if args.no_frames_output else args.frames_output,
        max_frames=args.max_frames,
        stride=args.stride,
        session_gap_seconds=args.session_gap_seconds,
        max_snakes=args.max_snakes,
        max_food=args.max_food,
        max_segments_per_snake=args.max_segments_per_snake,
        baseline_path=args.baseline,
    )
    print(json.dumps({
        "explicit_death_count": summary.explicit_death_count,
        "inferred_session_end_count": summary.inferred_session_end_count,
        "input": summary.input,
        "message": summary.stats.message,
        "override_count": summary.override_count,
        "override_rate": summary.override_rate,
        "output": summary.output,
        "session_count": summary.session_count,
        "total_frames": summary.total_frames,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

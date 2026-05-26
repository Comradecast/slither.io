from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from sandbox.tools.live_evaluation_runner import LiveEvaluationSummary, analyze_live_telemetry


DEFAULT_OUTPUT_DIR = Path("reports/live_baselines")


def safe_label(label: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", label.strip())
    cleaned = cleaned.strip("._")
    return cleaned or "live_baseline"


def _inside_directory(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
        return True
    except ValueError:
        return False


def _top_counts(counts: dict[str, int], limit: int = 3) -> list[dict]:
    return [
        {"name": name, "count": count}
        for name, count in sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0]),
        )[:limit]
    ]


def recommended_next_focus(summary: LiveEvaluationSummary) -> str:
    if summary.inferred_session_end_count >= max(1, summary.session_count):
        return "live capture/session tracking quality"

    gate_reasons = summary.aggregate_gate_reasons
    total_frames = max(1, summary.total_frames)
    boundary_rate = gate_reasons.get("boundary_too_close", 0) / total_frames
    collision_rate = gate_reasons.get("projected_collision", 0) / total_frames
    intercept_rate = gate_reasons.get("enemy_head_intercept", 0) / total_frames

    if boundary_rate >= 0.15:
        return "boundary/escape tuning"
    if collision_rate >= 0.20:
        return "perception/threat corridor tuning"
    if intercept_rate >= 0.15:
        return "enemy projection tuning"
    if summary.override_rate >= 0.50:
        return "safety over-triggering or route quality"

    mass_delta = summary.mass.get("mass_delta")
    if (
        isinstance(mass_delta, (int, float))
        and mass_delta <= 0
        and summary.explicit_death_count == 0
    ):
        return "food/loot routing"

    return "continue controlled live comparison"


def aggregate_record(label: str, summary: LiveEvaluationSummary) -> dict:
    return {
        "label": label,
        "input": summary.input,
        "total_frames": summary.total_frames,
        "session_count": summary.session_count,
        "explicit_death_count": summary.explicit_death_count,
        "inferred_session_end_count": summary.inferred_session_end_count,
        "override_rate": summary.override_rate,
        "boost_allowed_rate": summary.boost_allowed_rate,
        "peak_mass": summary.mass.get("peak_mass"),
        "final_mass": summary.mass.get("final_mass"),
        "mass_delta": summary.mass.get("mass_delta"),
        "top_gate_reasons": _top_counts(summary.aggregate_gate_reasons),
        "top_strategy_modes": _top_counts(summary.aggregate_strategy_modes),
        "recommended_next_focus": recommended_next_focus(summary),
        "summary_path": summary.output,
        "frames_path": summary.frames_output,
        "comparison": summary.comparison,
    }


def run_controlled_baseline(
    inputs: list[Path],
    label: str,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    max_frames: int = 2000,
    stride: int = 1,
    session_gap_seconds: float = 12.0,
    max_snakes: int = 8,
    max_food: int = 80,
    max_segments_per_snake: int = 120,
    baseline: Path | None = None,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = []

    for index, input_path in enumerate(inputs, start=1):
        run_label = safe_label(label if len(inputs) == 1 else f"{label}_{index}")
        summary_path = output_dir / f"{run_label}_summary.json"
        frames_path = output_dir / f"{run_label}_frames.jsonl"
        if not _inside_directory(summary_path, output_dir) or not _inside_directory(frames_path, output_dir):
            raise ValueError("generated output path escaped output directory")

        summary = analyze_live_telemetry(
            input_path=input_path,
            output_path=summary_path,
            frames_output_path=frames_path,
            max_frames=max_frames,
            stride=stride,
            session_gap_seconds=session_gap_seconds,
            max_snakes=max_snakes,
            max_food=max_food,
            max_segments_per_snake=max_segments_per_snake,
            baseline_path=baseline,
        )
        records.append(aggregate_record(run_label, summary))

    aggregate = {
        "label": safe_label(label),
        "run_count": len(records),
        "output_dir": str(output_dir),
        "runs": records,
        "recommended_next_focus": _aggregate_focus(records),
    }
    aggregate_path = output_dir / "aggregate_summary.json"
    if not _inside_directory(aggregate_path, output_dir):
        raise ValueError("aggregate output path escaped output directory")
    aggregate_path.write_text(json.dumps(aggregate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return aggregate


def _aggregate_focus(records: list[dict]) -> str:
    if not records:
        return "no telemetry inputs evaluated"
    focus_counts: dict[str, int] = {}
    for record in records:
        focus = record["recommended_next_focus"]
        focus_counts[focus] = focus_counts.get(focus, 0) + 1
    return sorted(focus_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run controlled live baseline summaries.")
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-frames", type=int, default=2000)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--session-gap-seconds", type=float, default=12.0)
    parser.add_argument("--max-snakes", type=int, default=8)
    parser.add_argument("--max-food", type=int, default=80)
    parser.add_argument("--max-segments-per-snake", type=int, default=120)
    parser.add_argument("--baseline", type=Path, default=None)
    args = parser.parse_args()

    aggregate = run_controlled_baseline(
        inputs=args.input,
        label=args.label,
        output_dir=args.output_dir,
        max_frames=args.max_frames,
        stride=args.stride,
        session_gap_seconds=args.session_gap_seconds,
        max_snakes=args.max_snakes,
        max_food=args.max_food,
        max_segments_per_snake=args.max_segments_per_snake,
        baseline=args.baseline,
    )
    print(json.dumps({
        "label": aggregate["label"],
        "output_dir": aggregate["output_dir"],
        "recommended_next_focus": aggregate["recommended_next_focus"],
        "run_count": aggregate["run_count"],
        "runs": [
            {
                "label": run["label"],
                "session_count": run["session_count"],
                "total_frames": run["total_frames"],
                "override_rate": run["override_rate"],
                "recommended_next_focus": run["recommended_next_focus"],
            }
            for run in aggregate["runs"]
        ],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations
import argparse
import random
from dataclasses import asdict, dataclass
from sandbox.config import Config
from sandbox.scenarios import SCENARIO_NAMES, create_scenario


@dataclass
class EvaluationSummary:
    scenario_name: str
    seed: int | None
    ticks_requested: int
    ticks_elapsed: int
    final_mass: float
    peak_mass: float
    food_eaten_count: int
    survival_status: str
    death_reason: str | None
    decision_count: int


@dataclass
class BenchmarkSummary:
    scenarios: list[EvaluationSummary]
    total_scenarios: int
    survived_count: int


def run_evaluation(
    ticks: int = 300,
    seed: int | None = None,
    scenario: str = "baseline_farming",
) -> EvaluationSummary:
    """Run a deterministic headless bot simulation and return summary metrics."""
    if ticks < 0:
        raise ValueError("ticks must be non-negative")

    random_state = random.getstate()
    if seed is not None:
            random.seed(seed)

    try:
        scenario_state = create_scenario(scenario)
        world = scenario_state.world
        bot = next(s for s in world.snakes if s.id == scenario_state.bot_id)

        for _ in range(ticks):
            if not bot.alive:
                break
            world.update(Config.DT)

        tracker = world.metrics_trackers[bot.id]
        tracker.record_mass(bot.mass)
        metrics = tracker.metrics

        return EvaluationSummary(
            scenario_name=scenario_state.name,
            seed=seed,
            ticks_requested=ticks,
            ticks_elapsed=metrics.ticks_elapsed,
            final_mass=metrics.final_mass,
            peak_mass=metrics.peak_mass,
            food_eaten_count=metrics.food_eaten_count,
            survival_status=metrics.survival_status,
            death_reason=metrics.death_reason,
            decision_count=metrics.decision_count,
        )
    finally:
        random.setstate(random_state)


def run_benchmark(ticks: int = 300, seed: int | None = None) -> BenchmarkSummary:
    summaries = [
        run_evaluation(ticks=ticks, seed=seed, scenario=scenario_name)
        for scenario_name in SCENARIO_NAMES
    ]
    return BenchmarkSummary(
        scenarios=summaries,
        total_scenarios=len(summaries),
        survived_count=sum(1 for summary in summaries if summary.survival_status == "alive"),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a headless local bot evaluation.")
    parser.add_argument("--ticks", type=int, default=300)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--scenario", choices=SCENARIO_NAMES, default="baseline_farming")
    parser.add_argument("--all-scenarios", action="store_true")
    args = parser.parse_args()

    if args.all_scenarios:
        print(asdict(run_benchmark(ticks=args.ticks, seed=args.seed)))
    else:
        print(asdict(run_evaluation(ticks=args.ticks, seed=args.seed, scenario=args.scenario)))


if __name__ == "__main__":
    main()

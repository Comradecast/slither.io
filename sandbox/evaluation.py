from __future__ import annotations
import argparse
import random
from dataclasses import asdict, dataclass
from sandbox.config import Config
from sandbox.food import FoodItem
from sandbox.world import World


@dataclass
class EvaluationSummary:
    ticks_elapsed: int
    final_mass: float
    peak_mass: float
    food_eaten_count: int
    survival_status: str
    death_reason: str | None
    decision_count: int


def run_evaluation(ticks: int = 300, seed: int | None = None) -> EvaluationSummary:
    """Run a deterministic headless bot simulation and return summary metrics."""
    if ticks < 0:
        raise ValueError("ticks must be non-negative")

    random_state = random.getstate()
    if seed is not None:
        random.seed(seed)

    try:
        world = World()
        bot = world.spawn_snake(1, 0, 0, is_bot=True, track_metrics=True)
        _seed_food(world)

        for _ in range(ticks):
            if not bot.alive:
                break
            world.update(Config.DT)

        tracker = world.metrics_trackers[bot.id]
        tracker.record_mass(bot.mass)
        metrics = tracker.metrics

        return EvaluationSummary(
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


def _seed_food(world: World):
    """Place deterministic starter food, then let normal spawning maintain density."""
    for index in range(12):
        x = 80.0 + index * 35.0
        value = Config.NATURAL_FOOD_MIN_VALUE + (index % 4)
        world.food_manager.items.append(FoodItem(x, 0.0, value))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a headless local bot evaluation.")
    parser.add_argument("--ticks", type=int, default=300)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    print(asdict(run_evaluation(ticks=args.ticks, seed=args.seed)))


if __name__ == "__main__":
    main()

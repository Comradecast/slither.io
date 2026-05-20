from dataclasses import dataclass

@dataclass
class SessionMetrics:
    ticks_elapsed: int = 0
    survival_status: str = "alive"  # "alive" or "dead"
    final_mass: float = 0.0
    peak_mass: float = 0.0
    food_eaten_count: int = 0
    deaths: int = 0
    death_reason: str | None = None
    boost_usage_count: int = 0
    boost_ticks: int = 0
    decision_count: int = 0

class MetricsTracker:
    def __init__(self):
        self.metrics = SessionMetrics()
        self._was_boosting = False

    def record_tick(self):
        self.metrics.ticks_elapsed += 1

    def record_decision(self):
        self.metrics.decision_count += 1

    def record_food_eaten(self):
        self.metrics.food_eaten_count += 1

    def record_mass(self, mass: float):
        self.metrics.final_mass = mass
        if mass > self.metrics.peak_mass:
            self.metrics.peak_mass = mass

    def record_death(self, reason: str):
        self.metrics.survival_status = "dead"
        self.metrics.deaths += 1
        self.metrics.death_reason = reason

    def record_boost(self, boosting: bool):
        if boosting:
            self.metrics.boost_ticks += 1
            if not self._was_boosting:
                self.metrics.boost_usage_count += 1
        self._was_boosting = boosting

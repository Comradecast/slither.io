from sandbox.logging_.metrics import MetricsTracker
from sandbox.world import World

def test_metrics_initializes_zero():
    tracker = MetricsTracker()
    assert tracker.metrics.ticks_elapsed == 0
    assert tracker.metrics.survival_status == "alive"
    assert tracker.metrics.food_eaten_count == 0
    assert tracker.metrics.deaths == 0

def test_metrics_records_food_collection():
    tracker = MetricsTracker()
    tracker.record_food_eaten()
    tracker.record_food_eaten()
    assert tracker.metrics.food_eaten_count == 2

def test_metrics_records_peak_mass():
    tracker = MetricsTracker()
    tracker.record_mass(10.0)
    tracker.record_mass(20.0)
    tracker.record_mass(15.0)
    assert tracker.metrics.final_mass == 15.0
    assert tracker.metrics.peak_mass == 20.0

def test_metrics_records_death_reason():
    tracker = MetricsTracker()
    tracker.record_death("collision")
    assert tracker.metrics.survival_status == "dead"
    assert tracker.metrics.deaths == 1
    assert tracker.metrics.death_reason == "collision"

def test_metrics_records_decision_count():
    tracker = MetricsTracker()
    tracker.record_decision()
    tracker.record_decision()
    assert tracker.metrics.decision_count == 2

def test_world_integration_records_metrics():
    world = World()
    snake = world.spawn_snake(1, 0, 0, is_bot=True, track_metrics=True)
    
    # Run a few ticks
    world.update(0.016)
    world.update(0.016)
    
    metrics = world.metrics_trackers[snake.id].metrics
    assert metrics.ticks_elapsed == 2
    assert metrics.decision_count == 2
    assert metrics.final_mass == 10.0 # Initial mass

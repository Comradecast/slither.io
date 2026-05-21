import builtins
from dataclasses import asdict
from sandbox.evaluation import BenchmarkSummary, EvaluationSummary, run_benchmark, run_evaluation
from sandbox.scenarios import SCENARIO_NAMES


def test_evaluation_runner_runs_without_pygame(monkeypatch):
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "pygame":
            raise AssertionError("evaluation runner should not import pygame")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    summary = run_evaluation(ticks=1, seed=1)

    assert isinstance(summary, EvaluationSummary)


def test_evaluation_runner_returns_summary_object():
    summary = run_evaluation(ticks=1, seed=1)

    assert isinstance(summary, EvaluationSummary)
    assert isinstance(asdict(summary), dict)


def test_evaluation_runner_records_ticks_elapsed():
    summary = run_evaluation(ticks=5, seed=1)

    assert summary.scenario_name == "baseline_farming"
    assert summary.seed == 1
    assert summary.ticks_requested == 5
    assert summary.ticks_elapsed == 5
    assert summary.decision_count == 5


def test_evaluation_runner_records_mass_metrics():
    summary = run_evaluation(ticks=5, seed=1)

    assert summary.final_mass >= 10.0
    assert summary.peak_mass >= summary.final_mass


def test_evaluation_runner_records_food_eaten_count():
    summary = run_evaluation(ticks=60, seed=1)

    assert summary.food_eaten_count > 0


def test_evaluation_runner_is_deterministic_with_seed():
    first = run_evaluation(ticks=30, seed=7)
    second = run_evaluation(ticks=30, seed=7)

    assert first == second


def test_single_scenario_evaluation_returns_expected_summary_fields():
    summary = run_evaluation(ticks=5, seed=1, scenario="boundary_pressure")
    summary_dict = asdict(summary)

    assert summary_dict["scenario_name"] == "boundary_pressure"
    assert summary_dict["seed"] == 1
    assert summary_dict["ticks_requested"] == 5
    assert "final_mass" in summary_dict
    assert "peak_mass" in summary_dict
    assert "food_eaten_count" in summary_dict
    assert "survival_status" in summary_dict
    assert "death_reason" in summary_dict
    assert "decision_count" in summary_dict


def test_all_scenarios_benchmark_returns_one_summary_per_scenario():
    benchmark = run_benchmark(ticks=5, seed=1)

    assert isinstance(benchmark, BenchmarkSummary)
    assert benchmark.total_scenarios == len(SCENARIO_NAMES)
    assert len(benchmark.scenarios) == len(SCENARIO_NAMES)
    assert {summary.scenario_name for summary in benchmark.scenarios} == set(SCENARIO_NAMES)


def test_benchmark_runner_is_deterministic_with_seed():
    first = run_benchmark(ticks=10, seed=7)
    second = run_benchmark(ticks=10, seed=7)

    assert first == second


def test_threat_scenarios_do_not_immediately_collide():
    nearby = run_evaluation(ticks=5, seed=1, scenario="nearby_threat")
    mixed = run_evaluation(ticks=5, seed=1, scenario="mixed_food_and_threat")

    assert nearby.survival_status == "alive"
    assert mixed.survival_status == "alive"

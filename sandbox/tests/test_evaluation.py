import builtins
from dataclasses import asdict
from sandbox.evaluation import EvaluationSummary, run_evaluation


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

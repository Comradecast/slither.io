# Telemetry Scenario Candidates

## Purpose
`sandbox/tools/extract_telemetry_scenarios.py` reads local `live_telemetry.jsonl` samples and emits deterministic candidate moments for future validation-harness scenarios.

This is an inventory and triage step. The output is not imported into the live bot and is not automatically promoted into tracked tests.

## Why Telemetry Is Not Live Control
The current bot is being rebuilt around deterministic survival primitives. Telemetry may reveal useful boundary, collision, or enemy-intercept situations, but replay data is noisy and may not match the local sandbox exactly. Using it directly for steering would bypass the Strategy and SafetyGate review process.

The extractor only evaluates a telemetry frame with the current deterministic perception and safety checks, then records a review summary.

## Candidate Categories
- `boundary_risk`: requested heading has low forward distance to the circular boundary or is overridden for boundary safety.
- `projected_collision`: SafetyGate classifies the requested heading as a projected body collision.
- `enemy_intercept`: Strategy/SafetyGate reports projected enemy head intercept risk.
- `high_collision_risk`: heading evaluation reports collision risk even if a higher-priority category did not claim it.
- `boost_while_unsafe`: an unsafe request had boost disabled by SafetyGate.
- `large_snake_survival`: the frame contains a large controlled snake and may be useful for size-aware survival review.
- `unknown_insufficient_data`: the record is malformed, incomplete, or does not yet map cleanly to a harness candidate.

## Output Location
Generated candidates are written to:

```text
reports/telemetry_scenario_candidates.jsonl
```

`reports/` is gitignored. Generated candidate JSONL should remain untracked unless explicitly reviewed and approved.

Each JSONL record includes source line, candidate type, reason, mass/radius/position, requested and selected headings, SafetyGate result, risk scores, raw shape keys, missing fields, and whether the record appears usable for a future deterministic harness scenario.

## Limitations
- The live telemetry coordinate system is normalized into the local sandbox coordinate system using `map_radius` when present.
- Candidate records are summaries, not executable `ScenarioCase` objects.
- Only a bounded number of snakes, food items, and body trail points are inspected for review output.
- A `usable_for_harness=true` candidate still needs human review before becoming a tracked scenario.
- The extractor does not load RL models, train models, or consult prior ML artifacts.

## Promoted Candidates
Two candidates were promoted into tracked fixtures at `sandbox/fixtures/promoted_telemetry_scenarios.json`.

### `telemetry_projected_collision_001`
- Source line: `31`
- Candidate type: `projected_collision`
- Expected gate behavior: override with `projected_collision`
- Why selected: The requested heading intersects a normalized enemy body segment, giving a compact regression case for body collision gating.
- Limitations: The fixture keeps only the controlled snake and the single enemy segment needed to reproduce the collision risk; it does not preserve the full telemetry frame.

### `telemetry_enemy_intercept_001`
- Source line: `111`
- Candidate type: `enemy_intercept`
- Expected gate behavior: override with `enemy_head_intercept`
- Why selected: The requested heading is unsafe because a projected enemy head crosses the path, giving a compact regression case for heading-aware enemy projection.
- Limitations: The fixture keeps only the enemy head that reproduces the intercept; unrelated snakes, food, and telemetry trails are omitted.

### Reviewed But Not Promoted
- Source line `1`: usable `projected_collision`, but it also reported enemy intercept risk. It was skipped in favor of line `31`, which isolates projected body collision more cleanly.
- Source line `121`: usable `projected_collision`, but redundant with line `31`.
- Source line `171`: usable `enemy_intercept`, but redundant with line `111`.

## Next Milestone Recommendation
`v0.16.0-expand-telemetry-regression-set`: review additional generated candidates only after the first promoted fixtures stay stable in the harness.

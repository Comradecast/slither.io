# Controlled Live Evaluation Baseline

## Purpose
This protocol creates repeatable live evidence for the current deterministic bot stack. It is not a behavior-tuning step by itself.

Reports are evidence, not proof of live strength. Live Slither.io sessions vary by server, spawn, nearby players, latency, browser state, and capture quality, so compare runs only when the capture settings are documented.

## Protocol
1. Start from a fresh browser and game state when possible.
2. Start the local bridge and confirm the extension is connected.
3. Use the same bot tag, browser, extension build, and capture settings for the whole set.
4. Capture 3 to 5 sessions with a fixed time or frame window.
5. Do not tune behavior during the capture set.
6. Keep `live_telemetry.jsonl` local and untracked.
7. Generate ignored summaries under `reports/live_baselines/`.
8. Review the aggregate metrics before choosing a behavior milestone.

## Commands
Single telemetry file:

```powershell
python -m sandbox.tools.controlled_live_baseline `
  --input live_telemetry.jsonl `
  --label v0.24_local `
  --max-frames 2000 `
  --stride 1
```

Comparison against an earlier summary:

```powershell
python -m sandbox.tools.controlled_live_baseline `
  --input live_telemetry.jsonl `
  --label v0.24_local `
  --max-frames 2000 `
  --stride 1 `
  --baseline reports/live_baselines/v0.23_sample_summary.json
```

Generated files:

```text
reports/live_baselines/<label>_summary.json
reports/live_baselines/<label>_frames.jsonl
reports/live_baselines/aggregate_summary.json
```

These paths are ignored by `.gitignore` through `reports/`.

## Metrics
The aggregate report includes:

- total frames
- session count
- explicit deaths
- inferred session ends
- override rate
- boost allowed rate
- peak, final, and delta mass
- top SafetyGate reasons
- top Strategy modes
- conservative recommended next focus

## Recommended Focus Rules
The helper recommends a next focus from metrics only:

- many inferred session ends: live capture/session tracking quality
- high boundary overrides: boundary/escape tuning
- high projected collisions: perception/threat corridor tuning
- high enemy intercepts: enemy projection tuning
- high overall override rate: safety over-triggering or route quality
- low mass delta with few deaths: food/loot routing

The recommendation is a triage hint. It does not automatically patch behavior.

## Guardrails
Do not compare runs with different capture settings unless that difference is documented in the report notes. Do not commit `live_telemetry.jsonl` or generated reports. Do not change Controller, Strategy, SafetyGate, Steering, or Perception during the capture set.

Behavior changes should come after reviewing the report and promoting representative failures into deterministic tests or harness scenarios.

## Limitations
The current telemetry may not include explicit death reasons. When no explicit marker is present, the tools report id changes or timestamp gaps as inferred session ends rather than confirmed deaths.

# Live Evaluation Runner V2

## Purpose
`sandbox/tools/live_evaluation_runner.py` summarizes controlled live bot sessions captured in `live_telemetry.jsonl`. It is an evaluation tool for comparing the current behavior stack against prior summaries, not a live-control path.

## Scope
The runner is read-only with respect to telemetry input. It does not connect to the browser, drive the snake, train a model, load RL artifacts, or change Controller, Strategy, Steering, Perception, or SafetyGate behavior.

Generated outputs are written under `reports/`:

- `reports/live_evaluation_summary.json`
- `reports/live_evaluation_frames.jsonl`

These files are ignored and should not be committed unless explicitly reviewed and approved.

## Metrics
The summary includes:

- session count
- evaluated frame count
- duration by timestamp
- start, final, peak, minimum, and delta mass
- explicit death count when telemetry provides a death/dead marker
- inferred session ends from controlled snake id changes or timestamp gaps
- SafetyGate override count and rate
- SafetyGate reason counts
- boost requested and allowed counts
- Strategy mode counts
- threat-memory maxima from v0.22 fields

## Session Boundaries
A new session starts when:

- the controlled snake id changes
- the timestamp gap exceeds the configured threshold

If telemetry does not include an explicit death marker, the runner reports these as inferred session ends rather than confirmed deaths.

## Comparison
The runner can compare a current summary with an older summary:

```powershell
python -m sandbox.tools.live_evaluation_runner `
  --input live_telemetry.jsonl `
  --output reports/live_evaluation_summary_v022.json `
  --baseline reports/live_evaluation_summary_previous.json
```

The comparison reports deltas for frame count, override count/rate, explicit deaths, inferred session ends, and peak mass.

## Limitations
The telemetry currently observed does not consistently include explicit death reason data. Survival and death analysis is therefore split into explicit death markers and inferred session stops.

The runner re-evaluates each captured frame through the current deterministic stack. It can show how v0.22 classifies captured live situations, but it is not a perfect replay of the original browser timing or server state.

## Next Step
Use a small number of controlled live sessions with consistent start/stop rules, then compare summaries between tagged versions. If a regression appears, promote representative frames into deterministic harness scenarios instead of tuning directly from raw telemetry.

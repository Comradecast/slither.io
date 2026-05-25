# Circle Squeeze Counter

## Purpose
Circle squeeze counter is a defensive refinement of anti-coil escape. It detects when enemy body geometry is forming a mostly closed loop around the bot and chooses a safe exit heading before the opening closes.

## Difference From Anti-Coil Escape
Anti-coil escape reacts to general compression: many nearby body threats across multiple sectors. Circle squeeze counter is narrower. It looks for a tighter loop shape, measures the largest remaining angular gap, and tries to exit through the best safe gap while the gap still exists.

## Not Offensive Circle Squeeze
This behavior does not circle, trap, pinch, bait, orbit, or squeeze enemies. It does not place our body to seal an opponent. It only tries to leave an active or forming enclosure.

## Detection Rules
Strategy divides the area around the snake head into deterministic angular sectors. A circle-squeeze risk can activate only when:

- enough enemy body threats are within the local detection radius
- enough angular sectors are occupied
- the largest empty angular gap is below the configured threshold

The analysis exposes additive metadata:

- `circle_squeeze_counter_active`
- `circle_squeeze_sector_count`
- `circle_squeeze_largest_gap_deg`
- `circle_squeeze_escape_heading`
- `circle_squeeze_escape_gap_center_deg`
- `circle_squeeze_closure_risk`
- `circle_squeeze_reason`

## Escape Heading Selection
When a squeeze is active, Strategy samples deterministic candidate headings:

- the center of the largest remaining gap
- neighboring headings around that gap
- the existing anti-coil escape sample headings

Each candidate is evaluated with the existing heading evaluator. Candidates are rejected when they have projected body collision, projected enemy head intercept, or inadequate heading-aware boundary space. Remaining headings are ranked by safety, closeness to the gap center, open-space score, boundary-forward distance, corridor density, and stable tie-breakers.

## Safety Checks Used
The counter uses the same defensive substrate as the rest of the bot:

- dynamic collision envelopes
- heading-aware boundary distance
- deterministic enemy head projection
- SafetyGate override behavior
- boost safety veto policy

Boost is not requested offensively. If boost is requested elsewhere, SafetyGate remains responsible for allowing or vetoing it.

## Limitations
The detector is local and memoryless. It uses currently visible body segments and enemy heads only. It does not infer hidden body arcs, long-term opponent intent, or future wall-off plans. Boundary avoidance remains higher priority, so a gap facing the wall is rejected by the existing defensive stack.

## Future Path
Offensive coiling, full circle control, or stronger counter-coiling should remain separate milestones. They should build on this escape layer without replacing SafetyGate or deterministic safety evaluation.

# Anti-Coil Escape Behavior

## Purpose
Anti-coil escape is a defensive behavior for leaving a closing enemy-body cage before it becomes fully closed. It detects compression around the bot and chooses a safe escape heading through the clearest available gap.

## Non-Goals
This milestone does not add offensive coiling, circle squeeze, loot guarding, perimeter orbiting, pinching, feints, or RL/ML control. The bot does not try to trap an opponent or defend territory. It only exits dangerous compression.

## Compression Scoring
Strategy inspects visible enemy body threats around the snake head. Threats within the anti-coil detection radius are assigned to deterministic angular sectors. Compression becomes active only when both conditions are met:

- enough nearby enemy body threats are visible
- enough angular sectors around the bot contain threats

The resulting metadata is additive:

- `compression_risk`
- `enclosure_sector_count`
- `anti_coil_escape_active`

## Escape Heading Selection
When compression is active, Strategy evaluates a fixed set of escape headings. Each heading is checked by the existing heading evaluator, so candidates with projected body collision, enemy head intercept, or insufficient heading-aware boundary distance are rejected.

Remaining headings are ranked by:

- higher open-space score
- lower body-threat corridor density
- adequate forward boundary distance
- deterministic tie-breakers

The selected heading is exposed as `best_escape_heading` and points at an escape target. Steering follows that escape target directly only for the `Anti-coil escape` defensive reason.

## Safety Checks Used
Anti-coil escape uses the existing deterministic safety substrate:

- dynamic collision envelopes
- heading-aware boundary distance
- projected enemy head intercepts
- SafetyGate override behavior
- boost safety veto policy

Boost is not requested offensively by this behavior. If boost is requested by a caller, SafetyGate still decides whether it is safe.

## Limitations
The detector is local and memoryless. It uses currently visible enemy body geometry and does not infer hidden body segments, future opponent strategy, or ownership of nearby food. It may conservatively leave a promising food path when compression geometry appears dangerous.

## Future Path
Future milestones can add stronger circle-squeeze counterplay or offensive coiling, but those should remain separate from this escape layer and continue to respect SafetyGate and boost safety vetoes.

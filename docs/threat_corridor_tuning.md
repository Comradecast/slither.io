# Threat Corridor Tuning

## Purpose
Live evaluation after `v0.24.0` showed the bot could survive and grow, but it spent nearly every frame in `avoid_threat`. The dominant gate reason was `projected_collision`, followed by `enemy_head_intercept`.

This milestone reduces false-positive corridor pressure while preserving hard safety for direct body collisions, boundary compression, and true head intercepts.

## Live Evidence
- Run 002: 2,807 frames, mass 30 to 345, override rate 0.7104.
- Run 003: 10,320 frames, mass 30 to 1260, override rate 0.816.
- Run 003 strategy mode was `avoid_threat` for all frames.
- Run 003 gate reasons were dominated by `projected_collision`.

## Tuning Rules
Projected body collision remains hard unsafe when the threat is close, centered in the travel corridor, persistent, or closing.

Projected body pressure is softened only when the threat is a grazing lateral overlap, distant enough to maneuver around, sparse, non-persistent, and not known to be closing. Soft pressure is diagnostic and ranking information; it does not force a SafetyGate override by itself.

Dense visible threat fields, high closing-threat counts, and dense per-heading corridors stay hard conservative. This correction was added after fresh live validation showed that the first tuning pass over-relaxed during a closing circle-squeeze sequence.

Enemy head intercept remains hard unsafe when the projected crossing is inside the dynamic envelope, timing overlap is tight, and the enemy heading is committed toward the lane. Looser timing or uncommitted headings are recorded as lower-severity pressure.

Ordinary visible threats no longer force `avoid_threat` unless they are forward and close, lateral and very close, or part of a dense/heavy pressure field. Circle-squeeze, anti-coil, boundary, and hard gate behavior remain higher priority. Food seeking is blocked while heavy threat pressure is active.

## Diagnostics
Harness reports now include additive fields for:

- `collision_threat_distance`
- `collision_threat_angle_deg`
- `collision_corridor_density`
- `collision_forward_cone`
- `collision_lateral_offset`
- `threat_receding`
- `threat_persistent_frames`
- `threat_confidence`
- `enemy_intercept_heading_delta_deg`

## Safety Invariants
- Direct forward body collision still triggers `projected_collision`.
- True projected enemy head intercept still triggers `enemy_head_intercept`.
- Dense closing-threat and circle-squeeze contexts remain defensive.
- Boundary distance checks are unchanged.
- Boost safety policy is unchanged.
- Circle-squeeze and anti-coil escape priority is unchanged.

## Limitations
This is conservative corridor tuning, not tactical behavior. It does not add attacks, trapping, coiling, or boost offense. Live evaluation is still required after this change to verify that `avoid_threat` and override rates drop without increasing deaths.

## Next Evaluation Plan
Run the same controlled live baseline workflow with fresh telemetry and compare:

- override rate
- projected collision count
- enemy intercept count
- strategy mode distribution
- mass delta
- explicit deaths and inferred session ends

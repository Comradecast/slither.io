# Partial Guarding Behavior

## Purpose
Partial guarding adds a limited defensive body-wall placement around high-value loot. When enemy pressure appears near a selected loot cluster or its approach lane, the bot can choose a safe one-step offset heading that places its body between the enemy and the collection path.

## Not Full Guarding
This is not orbiting, perimeter control, coiling, circle squeeze, pinching, baiting, or territorial play. The bot does not loop around loot, trap enemies, or defend a zone over time. It only selects a temporary wall-like heading when the existing safety system says that heading is safe.

## Activation Criteria
Partial guarding can activate only when:

- a deterministic high-value loot cluster is visible
- at least one enemy head is near the cluster or its approach lane
- anti-coil escape is inactive
- boundary and immediate threat avoidance have not already taken priority
- a safe guard offset exists
- the guard offset scores better than direct collection by the configured margin

Enemy body threats that require immediate avoidance still win before partial guarding is considered.

## Candidate Heading Rules
Strategy starts from the existing guarded food collection approach. It then evaluates two offset targets:

- left of the collection approach line
- right of the collection approach line

The preferred side is the side where enemy pressure appears relative to the approach line. If that side is unsafe, the opposite side can be selected as a safe fallback.

## Safety Checks
Each offset target is evaluated with the existing heading evaluator. A candidate is rejected when it has:

- projected body collision risk
- projected enemy head intercept risk
- inadequate heading-aware boundary distance

SafetyGate still controls final heading overrides and boost vetoes. Partial guarding does not request boost for offense.

## Limitations
The behavior is one-step and memoryless. It uses visible food and visible enemy geometry only. It does not reserve loot, orbit around clusters, predict long-term enemy intent, or maintain a perimeter.

## Future Path
Full guarding, perimeter control, circle counterplay, or offensive coiling should remain separate future milestones. Those tactics should build on this safety-gated offset layer rather than replacing it.

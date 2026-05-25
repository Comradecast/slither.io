# Loot Cluster Targeting

## Purpose
Loot cluster targeting lets the bot prefer rich groups of visible food pellets when the approach heading is already safe. This is target selection only: the bot aims at a cluster center, then the existing steering and SafetyGate layers continue to control the final action.

## Loot Cluster Definition
A loot cluster is a deterministic grouping of visible food pellets. The strategy groups pellets whose positions are within a fixed distance threshold, then computes:

- total value
- pellet count
- value-weighted center
- nearest pellet distance
- average pellet distance
- high-value pellet count

A group is considered a high-value cluster when it has at least three pellets and either its total value meets the configured cluster value threshold or it contains enough high-value pellets.

## Scoring Inputs
Cluster score uses total food value, pellet count, nearest distance, and average distance. The score is compared with the best individual food score. A cluster can replace the individual food target only when its score is higher and at least one approach point remains safe.

## Safety Checks
Before selecting a cluster, Strategy evaluates candidate approach headings with the existing deterministic heading evaluator. The center is preferred when safe; otherwise safe pellet entry points can be used for collection. A candidate is rejected when that heading has:

- projected body collision risk
- projected enemy head intercept risk
- insufficient heading-aware boundary distance

This does not bypass SafetyGate. SafetyGate still gets the final opportunity to override unsafe requested headings and veto unsafe boost.

## Deliberately Not Included
This milestone does not add coiling, circle squeeze, perimeter orbiting, loot guarding, head-in-sand behavior, pinch behavior, zig-zag/feint behavior, offensive boost, or RL/ML control.

## Future Path
Later milestones can build guarded or partially guarded loot behavior on top of these cluster signals. Those tactics should remain separate from this target-selection layer and continue to accept SafetyGate heading and boost vetoes.

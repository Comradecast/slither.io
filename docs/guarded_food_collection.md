# Guarded Food Collection

## Purpose
Guarded food collection improves how the bot approaches a selected high-value loot cluster. It chooses a safe collection point inside the cluster rather than blindly driving through the center.

## Not Territory Control
This is not loot guarding, perimeter control, orbiting, coiling, or fencing. The bot does not circle the cluster, defend it from opponents, or try to control space around it. It only chooses a safe target point to collect food.

## Approach-Point Rules
For each selected loot cluster, Strategy builds deterministic approach candidates:

- cluster center
- visible pellets in the cluster, sorted by distance, value, and position

The center receives a fixed approach bonus so it remains preferred when it is safe. If the center heading is unsafe, pellet candidates can be selected as edge or near-side entry points.

## Safety Checks
Every approach candidate is evaluated with the existing heading evaluator before selection. A candidate is rejected when it has:

- projected body collision risk
- projected enemy head intercept risk
- insufficient heading-aware boundary distance

Defensive priority still runs before food logic. If boundary or threat avoidance should trigger, guarded collection does not override it. SafetyGate still controls final heading overrides and boost vetoes.

## Limitations
The approach selector uses visible food only and does not predict future pellet ownership or opponent intent beyond the existing enemy path prediction. It does not remember clusters over time and does not reserve or defend food.

## Future Path
Partial guarding or perimeter behavior should be separate future milestones. Those tactics should build on this collection layer while preserving SafetyGate and boost safety vetoes.

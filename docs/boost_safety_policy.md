# Boost Safety Policy

## Purpose
Boost safety is a deterministic veto layer. It answers whether a requested boost can remain enabled for the already requested heading. It does not decide when to seek food, attack, chase, coil, guard loot, or use any learned policy.

## Inputs
- Current perceived snake state: head position, heading, mass, radius, and speed.
- Strategy heading evaluation: projected collision risk, enemy head intercept risk, and heading-aware boundary distance.
- Existing SafetyGate override result for the requested heading.
- Static configuration values for boost speed and minimum boost mass.

## Block Reasons
- `projected_collision`: the heading itself is unsafe and SafetyGate overrides it.
- `boundary_too_close`: the heading itself is too close to the world boundary and SafetyGate overrides it.
- `enemy_head_intercept`: the heading itself is unsafe because projected enemy movement intercepts it.
- `boost_collision_risk`: boost is blocked because collision risk is present.
- `boost_enemy_intercept_risk`: boost is blocked because projected enemy intercept risk is present.
- `boost_boundary_too_close`: boost is blocked because the requested heading has enough room to steer normally, but not enough forward boundary distance for boosted movement.
- `boost_turn_too_sharp`: boost is blocked because the requested heading requires a large turn from the current heading.
- `boost_mass_reserve`: boost is blocked because mass is too close to the configured boost reserve.
- `none`: boost is allowed or was not requested.

## Relationship To SafetyGate
SafetyGate keeps its public contract:

```text
safe_angle, safe_boost, was_overridden, reason
```

Unsafe headings are handled first. If the heading is overridden, boost is always forced off and the existing unsafe-heading reason is preserved. If the heading is not overridden, a requested boost is checked by the boost safety policy. A boost-only veto keeps the requested heading, returns `was_overridden=false`, forces boost off, and returns a boost-specific reason.

## Limitations
The policy is deliberately conservative and hand-tuned. It does not learn from telemetry, does not inspect RL artifacts, and does not decide that boost should be used for offense or food collection. It only disables boost when existing deterministic risk signals say boosted movement would reduce survival margin.

## Future Offensive Tactics
Future offensive milestones may decide when boost is useful, but they should treat this policy as a safety gate. Any new tactic should request boost separately and still accept a boost veto from SafetyGate.

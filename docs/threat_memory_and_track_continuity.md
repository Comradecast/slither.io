# Threat Memory and Track Continuity

## Purpose
Threat memory adds short-term continuity for visible enemy heads and body threats. It lets the bot distinguish one-frame sightings from persistent threats, notice body segments moving toward the head, and recognize recently missing or reacquired body segments.

## Scope
This is deterministic safety context only. It does not add ML, offensive coiling, trapping, orbiting, feints, or attack behavior.

## Tracked Data
Perception keeps short-lived in-memory tracks for:

- visible enemy heads by snake id
- visible enemy body threats by snake id and segment index

Each visible track can expose:

- velocity from the previous observed position
- persistent frame count
- missing frame count
- reacquired flag when a previously missing track reappears

Recently missing body threats are kept for a small fixed number of frames and then discarded.

## Strategy Use
Strategy receives additive memory summary fields:

- `persistent_threat_count`
- `reacquired_threat_count`
- `recent_missing_threat_count`
- `closing_threat_count`

Circle-squeeze escape ranking uses closing-threat density as a conservative penalty when a candidate heading points into a lane where remembered threat motion is closing toward the bot. The candidate still must pass the existing heading evaluator and SafetyGate.

## Limitations
The memory is local to a `Perception` instance. The live controller reuses one perception object, so continuity exists across live frames. One-shot harness scenarios create fresh perception objects, so continuity is tested with focused fixture tests instead of synthetic single-frame scenarios.

Memory is short-term and geometric only. It does not infer hidden bodies, enemy intent, or learned behavior.

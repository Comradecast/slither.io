# Phase 6.1: Sandbox Fidelity Review

Based on a review of the sandbox code, constants, and observed game loop execution, here is a breakdown of how the local sandbox feels compared to typical Slither-like gameplay expectations.

## Findings

### Movement Feel
* **Observed Issue:** The snake moves linearly and turns instantly up to `BASE_TURN_RATE`. The turning mechanic is crisp but lacks the slight physics-based "skid" or momentum smoothing seen in real browser clones.
* **Why it matters:** Movement might feel slightly robotic compared to real gameplay.
* **Classification:** `visual-only`
* **Suggested Future Phase:** Polishing / Visuals Phase
* **Blocks Phase 7?** No

### Turning Radius
* **Observed Issue:** Turn rate is fixed and scales strictly with agility/mass. When the snake is very long, it still turns tightly enough, but the visual spacing of segments can make sharp turns look disjointed if `SEGMENT_SPACING` isn't perfectly tuned against the frame rate.
* **Why it matters:** In tight coiling maneuvers, visual overlap might confuse players or bots.
* **Classification:** `visual-only`
* **Suggested Future Phase:** Polishing Phase
* **Blocks Phase 7?** No

### Body Spacing / Trail Behavior
* **Observed Issue:** Segments are sampled strictly by history index (`trail`). If the frame rate drops or fluctuates, spacing between segments might jitter slightly. Interpolated rendering isn't fully implemented for ultra-smooth body flow.
* **Why it matters:** If the segment hitboxes jitter, collision detection might become non-deterministic or unfair.
* **Classification:** `training-quality`
* **Suggested Future Phase:** Physics & Collision Tuning Phase
* **Blocks Phase 7?** No

### Boost Speed/Cost Feel
* **Observed Issue:** Boosting simply doubles speed and drains mass continuously. When mass reaches the minimum threshold, it abruptly stops boosting.
* **Why it matters:** The current implementation is functionally correct but lacks visual flair (e.g. glowing head, particle spray) and the gradual speed drop-off present in some clones.
* **Classification:** `visual-only`
* **Suggested Future Phase:** Visual Polish
* **Blocks Phase 7?** No

### Food Spawn/Collection Feel
* **Observed Issue:** Food collection uses a simple radius check. There's no "vacuum" effect pulling nearby food into the snake's mouth, which means the snake must run perfectly over the food center.
* **Why it matters:** This makes farming pellets harder and slower for bots and human players alike, shifting the balance away from casual farming.
* **Classification:** `behavior-critical`
* **Suggested Future Phase:** Food Mechanics / Vacuum Phase
* **Blocks Phase 7?** No (but highly recommended soon)

### Collision Feel
* **Observed Issue:** Collisions are point-circle vs point-circle distance checks. Head-to-head collisions currently result in both snakes dying or an arbitrary winner based on update order if both hit simultaneously.
* **Why it matters:** Head-to-head resolution in Slither usually favors the snake that is "inside" the other's turn or uses a precise angle check. Current logic is too random.
* **Classification:** `behavior-critical`
* **Suggested Future Phase:** Collision Physics Polish
* **Blocks Phase 7?** No

### Boundary Behavior
* **Observed Issue:** Hitting the boundary results in instant death. The boundary is a hard line. Real games usually have a red "danger zone" and then a kill wall.
* **Why it matters:** Bots can easily get trapped if their turn radius is larger than their distance to the wall.
* **Classification:** `defer/ignore`
* **Suggested Future Phase:** N/A (current logic is sufficient for a pure sandbox)
* **Blocks Phase 7?** No

### Camera/Visual Readability
* **Observed Issue:** The camera tracks the head strictly 1:1. The camera doesn't zoom out as the snake gets larger.
* **Why it matters:** A massive snake will quickly fill the entire screen, severely limiting player vision and bot proxy-vision (if tied to screen size, though currently bot vision is radius-based).
* **Classification:** `training-quality`
* **Suggested Future Phase:** Camera / Viewport Scaling
* **Blocks Phase 7?** No

### Bot Defensive Behavior
* **Observed Issue:** The bot now smoothly avoids threats with perpendicular steering, but it has no memory or trajectory prediction. If an enemy is coiling, the bot might just steer directly into a wall or another body segment because it only evaluates the single `highest_threat` at a time.
* **Why it matters:** The bot will still get easily trapped by human players or more advanced bots.
* **Classification:** `training-quality`
* **Suggested Future Phase:** Advanced Strategy / Prediction Phase
* **Blocks Phase 7?** No

## Recommendation
**Proceed to Phase 7.** 
The sandbox is highly functional and deterministic, which is ideal for offline testing. The fidelity gaps (like food vacuuming, camera scaling, and head-to-head collision ties) are known but do not block the addition of further modular features. We can address `behavior-critical` items in dedicated mini-phases later.

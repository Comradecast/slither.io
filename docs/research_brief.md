# Slither.io Bot Project — Phase 1 Research Brief

> **Author**: Antigravity (Phase 1 Research)
> **Audience**: ChatGPT (Architecture Design), Jules (Implementation Reference)
> **Date**: 2026-05-20
> **Purpose**: Provide enough detail about Slither.io's mechanics, existing work, and AI approaches for ChatGPT to design the bot architecture and local sandbox specification.

---

## Table of Contents

1. [Game Mechanics Reference](#1-game-mechanics-reference)
2. [Open-Source Landscape](#2-open-source-landscape)
3. [Existing Bot & AI Approaches](#3-existing-bot--ai-approaches)
4. [Recommended Local Sandbox Architecture](#4-recommended-local-sandbox-architecture)
5. [Key Design Decisions for ChatGPT](#5-key-design-decisions-for-chatgpt)

---

## 1. Game Mechanics Reference

### 1.1 Movement

| Property | Detail |
|----------|--------|
| **Steering model** | Snake head continuously rotates toward mouse/touch position |
| **Always moving** | Snake cannot stop or reverse; always in forward motion |
| **Turn rate** | Dynamic — smaller snakes turn sharply, larger snakes turn wide |
| **Body following** | Trail-following algorithm: head records positions into a history buffer; each body segment is placed at fixed intervals along the trail. No physics simulation. |

**Key formulas (from reverse-engineered source):**

```
// Snake thickness (scale), capped at 6
sc = Math.min(6, 1 + (sct - 2) / 106)     // sct = segment count

// Angular speed factor — small snakes are agile, large snakes are sluggish
scang = 0.13 + 0.87 * Math.pow((7 - sc) / 6, 2)

// Base angular speed: 0.033 radians/frame (server-configurable)

// Base movement speed
ssp = nsp1 + nsp2 * sc    // nsp1=4.25, nsp2=0.5
fsp = ssp + 0.1            // final speed per frame
```

**Implication for bot**: Turn rate is the snake's most important constraint. A bot must plan maneuvers within its current turn radius — sharp cuts are only possible when small.

---

### 1.2 Food & Pellets

| Type | Mass Value | Behavior |
|------|-----------|----------|
| **Natural pellets** | 1–4 (can grow to ~20 if uneaten) | Static, random spawn across map, denser near center |
| **Evasive orbs** | 50–100 | Actively flee from nearby snakes (requires boost to catch) |
| **Boost trail pellets** | ~1.2–1.4 each | Static once dropped; left behind by boosting snakes |
| **Death remains** | Proportional to dead snake's mass | Static clusters; bright, large, highest value |

**Spawning behavior:**
- Natural pellets spawn randomly at a constant rate
- Food density is significantly higher near the map center
- ~6 pellets/second shed while boosting
- Dying at the boundary drops NO food (mass removed from game)

**Implication for bot**: Death remains are the highest-value food source. A bot should prioritize collecting them. Evasive orbs require boost (mass investment) — only worthwhile when large.

---

### 1.3 Growth

- Starting mass/score: **10**
- Eating adds mass directly to score (1:1)
- Score-to-segments is **non-linear** — more mass needed per additional segment as you grow
- Snake thickness increases: `sc = Math.min(6, 1 + (sct - 2) / 106)` — caps at scale 6
- Visual size caps at ~40,000–50,000 mass (score can keep climbing)
- **No passive score decay** (unlike Agar.io)

**Implication for bot**: Growth has diminishing returns on agility. The bot needs a strategy for optimal size — big enough to be threatening, small enough to maneuver.

---

### 1.4 Boost / Sprint

| Property | Value |
|----------|-------|
| **Activation** | Mouse click, spacebar, or up-arrow (hold) |
| **Speed multiplier** | ~2× normal speed |
| **Mass cost** | ~15 mass/second |
| **Pellet drop rate** | ~6 pellets/second (each ~1.2–1.4 mass) |
| **Minimum mass** | Cannot boost below ~10–11 mass |
| **Cooldown** | None — instant on/off |

**Mass tax**: You lose more mass than what's recoverable from your trail pellets (some mass is destroyed). Boosting is a net-negative resource trade used for tactical advantage.

**Implication for bot**: Boost is the primary tactical tool. A bot needs clear criteria for when boosting is worth the mass cost (escaping danger, securing a kill, grabbing death remains).

---

### 1.5 Collision Rules

| Scenario | Result |
|----------|--------|
| **Head → other snake's body** | You die |
| **Head → own body** | Nothing (pass through freely) |
| **Head → head** | Both may die (depends on server tick timing) |
| **Head → map boundary** | Instant death, no food dropped |

- Collision uses **circle-based** distance checks
- Hitbox radius scales with snake thickness (`sc`)
- Self-collision immunity enables the coiling/encirclement strategy

**Implication for bot**: The bot's #1 priority is never letting its head touch another snake's body. Threat detection and evasion must be the highest-priority behavior.

---

### 1.6 Map / Arena

| Property | Value |
|----------|-------|
| **Shape** | Circular disc |
| **Radius** | ~21,600 game units (live servers), 16,384 default |
| **Coordinate system** | X/Y centered at origin (0, 0) |
| **Boundary** | Instant-death wall, no wrapping |
| **Spatial partitioning** | Sectors of ~300–480 units; client processes ~144 sectors along each edge |
| **Camera zoom** | Zooms out as snake grows |

**Implication for bot**: Boundary awareness is critical. The bot should maintain a safety margin from the edge and never chase food or enemies toward the boundary.

---

### 1.7 Scoring & Economy

- **Leaderboard**: Top 10 by score (displayed as "length")
- **Score = accumulated mass**, starting at 10
- **Kill reward**: No explicit bonus — reward is the victim's dropped pellets
- **Death drops**: ~40% of dead snake's mass becomes food; ~60% is destroyed (mass sink)
- **No passive decay**, no time bonuses

**Implication for bot**: Kills are high-risk, high-reward. The bot should pursue kills only when it has a clear tactical advantage (size, positioning).

---

### 1.8 Common Player Strategies

| Strategy | Description | When Used |
|----------|-------------|-----------|
| **Coiling** | Circle a smaller snake, tighten loop until it crashes | Large vs small |
| **Cutting off** | Boost ahead and turn to block path | Mid-size, near food clusters |
| **Trailing/vulturing** | Follow large snakes, eat their death drops | Any size, low risk |
| **Baiting** | Appear vulnerable near food to lure crashes | Advanced, any size |
| **Center camping** | Stay near center for food density + kill opportunities | Mid-large |
| **Edge trapping** | Push opponents toward boundary | Any size |

---

## 2. Open-Source Landscape

### 2.1 Reference Clone Projects

| Project | Language | Key Value |
|---------|----------|-----------|
| **[knagaitsev/slither.io-clone](https://github.com/knagaitsev/slither.io-clone)** | JS / Phaser | Best client-side mechanics reference (~263 stars) |
| **[iiegor/slither](https://github.com/iiegor/slither)** | Node.js | Server architecture understanding |
| **[ClitherProject/Slither.io-Protocol](https://github.com/ClitherProject/Slither.io-Protocol)** | Documentation | Definitive protocol reverse-engineering reference |
| **[moddio/moddio2](https://github.com/moddio/moddio2)** | JS / HTML5 | Full multiplayer engine with built-in A* AI |
| **[simondiep/node-multiplayer-snake](https://github.com/simondiep/node-multiplayer-snake)** | Node.js / Socket.io | Feature-rich snake implementation |

### 2.2 Implementation Patterns Across Clones

**Movement**: Vector-based (not grid-based). `direction = normalize(mousePos - headPos) × speed`. Body is a list of position samples from head's trail.

**Collision**: Circle-based distance checks per segment. Optimized with squared distances to avoid `sqrt`. **Spatial hashing preferred over quadtrees** for uniformly-sized, frequently-moving objects.

**Architecture**: Server-authoritative model. Client sends heading angle + boost toggle → server processes physics/collision → client renders.

### 2.3 Useful Libraries

- **[RBush](https://github.com/mourner/rbush)**: R-tree spatial index (JS)
- **[d3-quadtree](https://github.com/d3/d3-quadtree)**: Quadtree (JS)
- **[Colyseus](https://colyseus.io/)**: Multiplayer game server framework (Node.js)

---

## 3. Existing Bot & AI Approaches

### 3.1 Existing Bot Projects

| Project | Approach | Language | Key Insight |
|---------|----------|----------|-------------|
| **[JuiHsiu/Slither-DRL](https://github.com/JuiHsiu/Slither-DRL)** | Deep RL (DQN, PG, A2C) | Python | Most comprehensive RL implementation; Dueling DQN + PER |
| **[elliott-wen/slitherbot](https://github.com/elliott-wen/slitherbot)** | Neural Network | JS/Tampermonkey | Hooks game internals, NN for decisions |
| **[nkalupahana/slither.io-bot](https://github.com/nkalupahana/slither.io-bot)** | Heuristic | JS/Tampermonkey | Simple avoidance-focused; "anti-social" strategy |
| **[BabakAkbari/Slither.io-AI](https://github.com/BabakAkbari/Slither.io-AI)** | OpenAI Gym Env | Python | Gym-compatible RL environment |
| **[zachabarnes/slither-rl-agent](https://github.com/zachabarnes/slither-rl-agent)** | Deep RL | Python | "RattLe" DRL agent |

### 3.2 Stanford Research (CS229)

**"Learning to play SLITHER.IO with deep reinforcement learning"** — Joan Creus-Costa & Zhanpei Fang:
- Deep Q-Learning with human demonstrations + reward shaping
- Input: Raw pixels → cropped, downsized, grayscale
- Environment: OpenAI Universe (VNC-based virtual desktop)
- **Result**: Significantly better than random but below skilled human
- **Key finding**: Pure RL on raw pixels is very hard for Slither.io due to real-time multiplayer non-determinism and VNC latency. Structured game state + heuristics may be more practical than end-to-end learning.

### 3.3 AI Approach Comparison

#### Heuristic Bots (Rule-Based)
- **Pros**: Fast, predictable, interpretable, no training needed
- **Cons**: Rigid, can't adapt to novel situations
- **How**: Hand-coded rules (seek food, flee threats, avoid walls) with weighted priorities
- **Common patterns**: Zone-based enemy classification (close <300, mid 300-700, far >700), sector-based food density scanning

#### Reinforcement Learning Bots
- **Pros**: Can discover non-obvious strategies, adaptable
- **Cons**: Requires massive training time, hard to tune reward shaping, fragile
- **Approaches tried**: DQN, Dueling DQN, Policy Gradient, Actor-Critic, A2C
- **Reality check**: Stanford paper found RL still underperforms good heuristics for this game

#### Hybrid (Recommended for This Project)
- **High-level decisions**: Behavior Tree or Utility AI (strategic layer)
- **Low-level movement**: Steering behaviors (tactical layer)
- Interpretable, debuggable, iteratively improvable
- Can later add ML components to specific decision points

---

### 3.4 Path Planning & Steering Behaviors

#### Grid-Based (Not Applicable)
Hamiltonian cycles, A* on grids — these are for classic grid-based Snake. Slither.io uses continuous movement, so these don't directly apply.

#### Steering Behaviors (Craig Reynolds) — The Right Tool

Core principle: **Steering Force = Desired Velocity − Current Velocity**

| Behavior | Description | Use in Bot |
|----------|-------------|------------|
| **Seek** | Steer toward target at max speed | Move toward food |
| **Flee** | Steer away from threat | Evade enemies |
| **Arrive** | Slow down when approaching target | Precise food collection |
| **Wander** | Random exploration circle projected ahead | Default when no targets |
| **Obstacle Avoidance** | Only triggers when obstacle is in direct path | Avoid snake bodies |
| **Pursuit** | Predict target's future position and intercept | Chase smaller snakes |
| **Evade** | Predict threat's future position and flee | Escape larger snakes |

**Key insight**: These behaviors are **combinable** — weight and sum forces from multiple behaviors to produce smooth, natural movement:

```
finalSteering = 0.5 * seek(nearestFood)
              + 0.8 * flee(nearestThreat)      // higher weight = higher priority
              + 0.3 * avoidWall(boundary)
              + 0.1 * wander()
```

### 3.5 Decision-Making Frameworks

| Framework | Best For | Scalability | Debuggability |
|-----------|----------|-------------|---------------|
| **Finite State Machine** | Simple bots (3-5 states) | Poor | Good |
| **Behavior Trees** | Hierarchical priorities | Good | Good |
| **Utility AI** | Dynamic action scoring | Excellent | Moderate |
| **Potential Fields** | Smooth reactive navigation | Good | Good |
| **Hybrid BT + Steering** | Overall best for this project | Excellent | Excellent |

### 3.6 Recommended Bot Architecture (for ChatGPT to refine)

```
┌─────────────────────────────────────────────────┐
│                 PERCEPTION LAYER                │
│  Read game state → build world model            │
│  • My snake: position, size, heading, speed     │
│  • Food: positions, values, types               │
│  • Enemies: positions, sizes, headings, speeds  │
│  • Map: boundary distance, safe zones           │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│            STRATEGIC LAYER (Behavior Tree)       │
│  HIGH-LEVEL: What should I be doing?            │
│  ├─ SURVIVE (highest priority)                  │
│  │   ├─ Boundary too close? → flee inward       │
│  │   ├─ Collision imminent? → emergency evade   │
│  │   └─ Being encircled? → escape boost         │
│  ├─ ATTACK (if advantaged)                      │
│  │   ├─ Smaller snake nearby? → pursue          │
│  │   └─ Cut-off opportunity? → execute          │
│  └─ FEED (default)                              │
│      ├─ Death remains nearby? → collect          │
│      ├─ Dense food cluster? → navigate to       │
│      └─ Wander toward center                    │
└─────────────────────┬───────────────────────────┘
                      │ target + mode
┌─────────────────────▼───────────────────────────┐
│           TACTICAL LAYER (Steering Behaviors)    │
│  LOW-LEVEL: How do I execute the strategy?      │
│  • Seek/Arrive toward target                    │
│  • Flee from threats                            │
│  • Obstacle avoidance (snake bodies)            │
│  • Wander for exploration                       │
│  • Weighted combination → final heading angle   │
└─────────────────────┬───────────────────────────┘
                      │ heading + boost
┌─────────────────────▼───────────────────────────┐
│              ACTUATOR LAYER                      │
│  Apply heading angle + boost toggle to snake     │
└─────────────────────────────────────────────────┘
```

---

## 4. Recommended Local Sandbox Architecture

### 4.1 Platform Decision

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Python / Pygame** | Fast iteration, easy data logging, ML ecosystem | Separate from any future browser deployment | ✅ Best for bot development |
| **Browser / HTML5 Canvas** | Matches real Slither.io platform | Harder to integrate ML tools, slower iteration | ⚠️ Good for final deployment |
| **Python + Browser viz** | Best of both: Python sim + browser dashboard | More complex setup | 🔮 Future enhancement |

**Recommendation**: Start with **Python / Pygame** for the sandbox. It gives us:
- Direct access to game state (no DOM parsing)
- Easy logging/metrics with standard Python tools
- Seamless integration with numpy/scipy for AI math
- Path to ML/RL experimentation if desired later
- Fast iteration cycle

### 4.2 Sandbox Requirements

The local sandbox must faithfully model these mechanics:

| Mechanic | Priority | Fidelity Needed |
|----------|----------|-----------------|
| Continuous snake movement | P0 | High — must match real steering/speed model |
| Turn rate scaling with size | P0 | High — use the real formulas |
| Food spawning (natural + death) | P0 | Medium — simplified types okay |
| Growth (eating → longer) | P0 | Medium — linear approximation okay initially |
| Boost (speed up, lose mass, drop food) | P0 | High — core strategic mechanic |
| Head-to-body collision | P0 | High — the core death mechanic |
| Circular map boundary (instant death) | P0 | High — simple to implement |
| Self-collision immunity | P0 | High — enables coiling strategy |
| AI opponent snakes | P0 | Medium — start with simple heuristic bots |
| Evasive food orbs | P2 | Low — nice-to-have |
| Size-based thickness scaling | P1 | Medium — affects hitboxes |
| Camera zoom scaling | P2 | Low — visual only |

### 4.3 Proposed Module Structure

```
slither.io/
├── docs/
│   └── research_brief.md          ← This document
├── sandbox/
│   ├── main.py                    # Entry point, game loop
│   ├── config.py                  # All tunable constants (from real game formulas)
│   ├── world.py                   # Game world: manages entities, spatial grid, boundaries
│   ├── snake.py                   # Snake entity: movement, growth, boost, death
│   ├── food.py                    # Food entity: spawning, types, collection
│   ├── collision.py               # Spatial hash grid + collision detection
│   ├── renderer.py                # Pygame rendering (visual representation)
│   ├── input_handler.py           # Player input (mouse/keyboard)
│   ├── bot/
│   │   ├── perception.py          # World model builder (what does the bot see?)
│   │   ├── strategy.py            # High-level behavior tree / utility AI
│   │   ├── steering.py            # Low-level steering behaviors
│   │   └── bot_controller.py      # Ties perception → strategy → steering → action
│   ├── logging/
│   │   ├── game_logger.py         # Decision logging, score tracking, event recording
│   │   └── metrics.py             # Survival time, score/time, kill efficiency, etc.
│   └── tests/
│       ├── test_snake.py
│       ├── test_collision.py
│       └── test_steering.py
├── .gitignore
└── README.md
```

### 4.4 Logging & Evaluation (Critical for Bot Development)

The sandbox must produce structured logs for bot evaluation:

```
Bot Decision Log (per frame / per decision):
- timestamp
- bot_state: {position, heading, speed, mass, boosting}
- perceived_threats: [{enemy_id, distance, heading, mass}]
- perceived_food: [{position, value, distance}]
- active_strategy: "FEED" | "EVADE" | "ATTACK" | "SURVIVE"
- steering_weights: {seek: 0.5, flee: 0.8, avoid: 0.3, wander: 0.1}
- final_heading: angle
- boost_decision: true/false
- boost_reason: "escaping threat" | null

Session Metrics:
- survival_time
- final_score
- peak_score
- food_eaten_count
- kills
- deaths_by: "collision" | "boundary" | "encircled"
- boost_mass_spent
- boost_mass_efficiency (mass gained from kills vs mass spent boosting)
```

---

## 5. Key Design Decisions for ChatGPT

These are the open questions and design decisions that ChatGPT should address in the architecture phase:

### 5.1 Bot Brain Architecture
- **Behavior Tree vs Utility AI vs Hybrid** for the strategic layer?
- How many behavior states/priorities?
- Should strategies be pluggable/swappable for A/B testing?

### 5.2 Perception Model
- **How far should the bot "see"?** In the real game, vision is limited to the camera viewport. Should we simulate this limitation or give the bot full world knowledge?
- **What data structure represents the bot's world model?** Flat lists? Spatial buckets? Polar coordinates relative to the bot?

### 5.3 Threat Assessment
- How to score threat level of nearby enemies? (size ratio × distance × heading alignment?)
- What's the threshold for switching from FEED to EVADE?
- How to detect encirclement?

### 5.4 Boost Decision Framework
- Under what conditions should the bot boost?
- How to calculate ROI of boosting (mass cost vs expected gain)?
- Minimum mass threshold before allowing boost?

### 5.5 Evaluation Criteria
- What metrics define a "good" bot? (survival time? score? score/time ratio? kill count?)
- How to compare two bot strategies? (tournament? average over N runs?)
- Should we track per-strategy performance separately?

### 5.6 Sandbox Fidelity
- Use the exact real-game formulas from Section 1, or simplified approximations?
- How many AI opponents in the sandbox? (real game has hundreds, but we need reasonable perf)
- Fixed or randomized food spawn patterns?

### 5.7 Future Considerations (not for Phase 2, but worth thinking about)
- How would this bot architecture translate to the real game later?
- Should the perception layer be abstracted enough to swap between sandbox state and real-game state?
- Dashboard/visualizer for watching bot decisions in real-time?

---

## Appendix: Server Constants Reference

| Constant | Description | Default Value |
|----------|-------------|---------------|
| `gameRadius` | Arena radius | 16,384 (live: ~21,600) |
| `mscps` | Max segments | Server-configured |
| `sector_size` | Spatial cell size | ~300–480 |
| `spangdv` | Angular speed divisor | 4.8 |
| `nsp1` | Base speed constant 1 | 4.25 |
| `nsp2` | Base speed constant 2 | 0.5 |
| `nsp3` | Boost speed constant | 12 |
| `mamu` | Base angular speed (rad/frame) | 0.033 |

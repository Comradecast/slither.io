# Slither Sandbox

A local, deterministic Python/Pygame sandbox for developing AI bots that play a game similar to Slither.io. 
This project models the core gameplay shape (movement, growth, boosting, spatial collision, food) but is completely decoupled from live game internals. It operates strictly locally with no multiplayer or network dependencies.

## Structure

*   `sandbox/` - The core application package.
    *   `config.py` - Tunable gameplay constants.
    *   `world.py`, `snake.py`, `food.py`, `collision.py` - Core entity definitions and game loop mechanics.
    *   `renderer.py`, `main.py` - Pygame integration and rendering.
    *   `bot/` - Architecture for pluggable bot AI (Perception, Strategy, Steering).
    *   `logging_/` - Event and metrics logging infrastructure.
    *   `tests/` - Pytest coverage for core mechanics.

## Installation

```bash
pip install -r requirements.txt
```

## Running the Sandbox

```bash
python -m sandbox.main
```
*Note: Phase 3 implements the foundational Bot Controller pipeline. The dummy AI spawned in `main.py` is now driven by this pipeline (avoiding boundaries and seeking food).*

## Running Tests

```bash
pytest sandbox/tests/ -v
```

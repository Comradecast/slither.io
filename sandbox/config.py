"""All tunable sandbox constants.

Values are approximate, inspired by Slither-like game mechanics observed in
public references, open-source clones, and community analysis. They are NOT
coupled to any live game's internals.
"""


class Config:
    """Central configuration for the Slither sandbox."""

    # ── World ────────────────────────────────────────────────────────────
    WORLD_RADIUS: float = 3000.0          # Circular arena radius (game units)
    TICK_RATE: int = 60                    # Logic ticks per second
    DT: float = 1.0 / TICK_RATE           # Fixed delta time per tick (seconds)

    # ── Snake: Movement ──────────────────────────────────────────────────
    BASE_SPEED: float = 150.0             # Units/sec at scale=1
    SPEED_SCALE_FACTOR: float = 10.0      # Extra speed per unit of scale
    BOOST_SPEED_MULTIPLIER: float = 2.0   # Speed multiplied by this when boosting
    BASE_TURN_RATE: float = 4.0           # Radians/sec at scale=1
    MAX_SCALE: float = 6.0                # Thickness cap

    # ── Snake: Body ──────────────────────────────────────────────────────
    SEGMENT_SPACING: float = 8.0          # Distance between segments along trail
    INITIAL_MASS: float = 10.0            # Starting mass / score
    INITIAL_SEGMENTS: int = 10            # Starting body segment count
    MASS_PER_SEGMENT: float = 5.0         # Mass needed per additional segment
    SCALE_FORMULA_DIVISOR: float = 100.0  # sc = min(MAX_SCALE, 1 + (segs-2)/this)
    BASE_RADIUS: float = 6.0             # Head collision radius at scale=1
    RADIUS_SCALE_FACTOR: float = 2.0     # Additional radius per unit of scale

    # ── Snake: Boost ─────────────────────────────────────────────────────
    BOOST_MASS_COST: float = 15.0         # Mass lost per second while boosting
    BOOST_PELLET_RATE: float = 6.0        # Boost-trail pellets dropped per second
    BOOST_PELLET_VALUE: float = 1.2       # Mass value of each boost-trail pellet
    BOOST_MIN_MASS: float = 12.0          # Cannot boost below this mass

    # ── Food ─────────────────────────────────────────────────────────────
    NATURAL_FOOD_COUNT: int = 500         # Target natural food count on the map
    NATURAL_FOOD_SPAWN_RATE: float = 10.0 # New natural pellets per second
    NATURAL_FOOD_MIN_VALUE: float = 1.0
    NATURAL_FOOD_MAX_VALUE: float = 4.0
    NATURAL_FOOD_RADIUS: float = 4.0
    DEATH_DROP_FRACTION: float = 0.4      # Fraction of dead snake's mass → food
    DEATH_DROP_PELLET_VALUE: float = 5.0  # Approx value per death-drop pellet
    DEATH_DROP_RADIUS: float = 8.0
    FOOD_COLLECTION_MARGIN: float = 5.0   # Extra radius for food pickup

    # ── AI Opponents ─────────────────────────────────────────────────────
    AI_COUNT: int = 15                    # Number of AI opponent snakes
    AI_RESPAWN_DELAY: float = 3.0         # Seconds before dead AI respawns
    AI_VISION_RADIUS: float = 400.0       # How far AI opponent can "see"

    # ── Collision ────────────────────────────────────────────────────────
    GRID_CELL_SIZE: int = 200             # Spatial hash cell size (game units)

    # ── Rendering ────────────────────────────────────────────────────────
    SCREEN_WIDTH: int = 1280
    SCREEN_HEIGHT: int = 720
    FPS_CAP: int = 60
    CAMERA_LERP_SPEED: float = 5.0       # Camera follow smoothing factor
    CAMERA_ZOOM_BASE: float = 1.0        # Zoom at scale=1
    CAMERA_ZOOM_MIN: float = 0.35        # Minimum zoom (zoomed out, large snake)
    CAMERA_ZOOM_SHRINK_RATE: float = 0.015  # Zoom reduction per unit of scale
    BACKGROUND_COLOR: tuple = (10, 10, 26)
    GRID_LINE_COLOR: tuple = (30, 30, 50)
    GRID_LINE_SPACING: int = 60
    BOUNDARY_COLOR: tuple = (255, 68, 68)
    BOUNDARY_WIDTH: int = 3
    MINIMAP_RADIUS: int = 70
    MINIMAP_MARGIN: int = 15
    LEADERBOARD_COUNT: int = 10          # Top N shown on leaderboard
    SHOW_DEBUG_INFO: bool = False        # Show FPS, entity counts, etc.

    # ── Snake Color Palettes ─────────────────────────────────────────────
    SNAKE_PALETTES: list = [
        ((255, 107, 107), (255, 142, 142)),   # Red
        ((78, 205, 196),  (110, 231, 222)),   # Teal
        ((69, 183, 209),  (107, 197, 217)),   # Blue
        ((150, 230, 161), (184, 240, 191)),   # Green
        ((221, 160, 221), (232, 184, 232)),   # Plum
        ((247, 220, 111), (249, 232, 140)),   # Yellow
        ((231, 76, 60),   (255, 107, 107)),   # Crimson
        ((52, 152, 219),  (93, 173, 226)),    # Ocean
        ((230, 126, 34),  (240, 160, 75)),    # Orange
        ((155, 89, 182),  (176, 124, 198)),   # Purple
        ((26, 188, 156),  (72, 209, 165)),    # Emerald
        ((255, 105, 180), (255, 141, 199)),   # Pink
    ]

    FOOD_COLORS: list = [
        (255, 107, 107), (78, 205, 196), (69, 183, 209), (150, 230, 161),
        (221, 160, 221), (247, 220, 111), (231, 76, 60),  (255, 105, 180),
        (52, 152, 219),  (230, 126, 34),  (155, 89, 182), (26, 188, 156),
    ]

    # ── Bot Names (for AI opponents) ────────────────────────────────────
    BOT_NAMES: list = [
        "Slyther", "Cobra", "Viper", "Anaconda", "Mamba",
        "Python", "Rattler", "Sidewinder", "Copperhead", "Basilisk",
        "Noodle", "Wiggler", "Slippy", "Snakey", "Hisser",
        "xX_Snek_Xx", "ProGamer99", "NomNom", "BigBoi", "TinySnake",
        "Destroyer", "Hunter", "Ghost", "Shadow", "Phantom",
        "Lightning", "Thunder", "Storm", "Blaze", "Frost",
        "Captain", "Major", "General", "Admiral", "Commander",
        "Cookie", "Donut", "Cupcake", "Muffin", "Waffles",
        "Pixel", "Glitch", "Matrix", "Binary", "Vector",
    ]

    # ── Logging ──────────────────────────────────────────────────────────
    LOG_DECISIONS: bool = True            # Log bot decisions every frame
    LOG_EVENTS: bool = True               # Log game events (deaths, kills, eats)
    LOG_INTERVAL_FRAMES: int = 1          # Log every N frames (1 = every frame)
    LOG_DIR: str = "logs/"

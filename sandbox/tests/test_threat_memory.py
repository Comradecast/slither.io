from sandbox.bot.perception import Perception
from sandbox.bot.strategy import Strategy
from sandbox.snake import Snake
from sandbox.vector import Vector2


def _state(perception, snake, enemy):
    return perception.build(snake, [snake, enemy], [])


def test_threat_memory_tracks_persistent_movement_and_closing_count():
    perception = Perception(vision_radius=400)
    snake = Snake(1, 0, 0, 0)
    enemy = Snake(2, 120, 0, 0)
    enemy.segments = [Vector2(100, 0)]

    first = _state(perception, snake, enemy)
    enemy.segments = [Vector2(90, 0)]
    second = _state(perception, snake, enemy)

    assert first.visible_threats[0].persistent_frames == 1
    assert first.visible_threats[0].velocity is None
    assert second.visible_threats[0].persistent_frames == 2
    assert second.visible_threats[0].velocity.x == -10
    assert second.visible_threats[0].velocity.y == 0
    assert second.persistent_threat_count == 1
    assert second.closing_threat_count == 1


def test_threat_memory_keeps_recently_missing_tracks_temporarily():
    perception = Perception(vision_radius=400)
    snake = Snake(1, 0, 0, 0)
    enemy = Snake(2, 120, 0, 0)
    enemy.segments = [Vector2(100, 0)]
    _state(perception, snake, enemy)

    enemy.segments = []
    missing = _state(perception, snake, enemy)

    assert missing.visible_threats == []
    assert missing.recent_missing_threat_count == 1
    assert missing.recent_missing_threats[0].source_id == 2
    assert missing.recent_missing_threats[0].segment_index == 0
    assert missing.recent_missing_threats[0].missing_frames == 1


def test_threat_memory_reacquires_disappearing_body_segment():
    perception = Perception(vision_radius=400)
    snake = Snake(1, 0, 0, 0)
    enemy = Snake(2, 120, 0, 0)
    enemy.segments = [Vector2(100, 0)]
    _state(perception, snake, enemy)

    enemy.segments = []
    _state(perception, snake, enemy)
    enemy.segments = [Vector2(85, 0)]
    reacquired = _state(perception, snake, enemy)

    threat = reacquired.visible_threats[0]
    assert threat.reacquired is True
    assert threat.missing_frames == 0
    assert threat.persistent_frames == 2
    assert reacquired.reacquired_threat_count == 1


def test_threat_memory_expires_missing_tracks_after_ttl():
    perception = Perception(vision_radius=400)
    snake = Snake(1, 0, 0, 0)
    enemy = Snake(2, 120, 0, 0)
    enemy.segments = [Vector2(100, 0)]
    _state(perception, snake, enemy)

    enemy.segments = []
    state = None
    for _ in range(Perception.TRACK_MEMORY_TTL_FRAMES + 1):
        state = _state(perception, snake, enemy)

    assert state is not None
    assert state.recent_missing_threat_count == 0


def test_strategy_can_use_closing_threat_memory_for_heading_density():
    perception = Perception(vision_radius=400)
    snake = Snake(1, 0, 0, 0)
    enemy = Snake(2, 120, 0, 0)
    enemy.segments = [Vector2(100, 0)]
    _state(perception, snake, enemy)

    enemy.segments = [Vector2(90, 0)]
    state = _state(perception, snake, enemy)

    assert Strategy._heading_closing_threat_density(0.0, state) == 1
    assert Strategy._heading_closing_threat_density(3.141592653589793, state) == 0

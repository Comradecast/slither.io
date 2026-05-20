from sandbox.world import World

def test_world_spawn_snake():
    w = World()
    s = w.spawn_snake(1, 0, 0)
    assert len(w.snakes) == 1
    assert s.id == 1

def test_world_update():
    w = World()
    w.spawn_snake(1, 0, 0)
    w.update(1.0)
    assert w.elapsed == 1.0
    assert w.tick == 1
    assert w.snakes[0].x > 0

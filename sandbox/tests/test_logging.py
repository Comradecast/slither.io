import os
import json
import tempfile
from sandbox.logging_.game_logger import GameLogger
from sandbox.world import World

def test_logger_writes_one_record():
    with tempfile.TemporaryDirectory() as temp_dir:
        log_path = os.path.join(temp_dir, "decisions.jsonl")
        logger = GameLogger(log_path)
        
        logger.log_decision(
            tick=1, snake_id=42, pos_x=10.0, pos_y=20.0, mass=15.0,
            heading=3.14, strategy_mode="SEEK_FOOD", target_pos_x=100.0,
            target_pos_y=200.0, steering_heading=1.57, boost=False,
            nearest_food_distance=90.0, boundary_distance=2800.0
        )
        
        assert os.path.exists(log_path)
        with open(log_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 1
            record = json.loads(lines[0])
            assert record["tick"] == 1
            assert record["snake_id"] == 42
            assert record["strategy_mode"] == "SEEK_FOOD"
            assert record["position"]["x"] == 10.0

def test_logger_appends_multiple_records():
    with tempfile.TemporaryDirectory() as temp_dir:
        log_path = os.path.join(temp_dir, "decisions.jsonl")
        logger = GameLogger(log_path)
        
        for i in range(3):
            logger.log_decision(
                tick=i, snake_id=42, pos_x=0.0, pos_y=0.0, mass=10.0,
                heading=0.0, strategy_mode="WANDER", target_pos_x=None,
                target_pos_y=None, steering_heading=0.0, boost=False,
                nearest_food_distance=None, boundary_distance=3000.0
            )
            
        with open(log_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 3
            assert json.loads(lines[0])["tick"] == 0
            assert json.loads(lines[2])["tick"] == 2

def test_world_integration_emits_record():
    with tempfile.TemporaryDirectory() as temp_dir:
        log_path = os.path.join(temp_dir, "decisions.jsonl")
        logger = GameLogger(log_path)
        
        world = World(logger=logger)
        # Spawn an AI snake
        world.spawn_snake(1, 0, 0, is_bot=True)
        
        # Run one tick
        world.update(0.016)
        
        assert os.path.exists(log_path)
        with open(log_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 1
            record = json.loads(lines[0])
            assert record["snake_id"] == 1
            assert "strategy_mode" in record

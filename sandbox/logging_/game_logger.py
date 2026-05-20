import json
import os
from datetime import datetime

class GameLogger:
    """Logs bot decisions to a JSONL file."""
    
    def __init__(self, output_path: str | None = None):
        self.output_path = output_path
        if self.output_path:
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
            # Create or truncate the file
            with open(self.output_path, 'w') as f:
                pass

    def log_decision(self, tick: int, snake_id: int, pos_x: float, pos_y: float, mass: float,
                     heading: float, strategy_mode: str, target_pos_x: float | None,
                     target_pos_y: float | None, steering_heading: float, boost: bool,
                     nearest_food_distance: float | None, boundary_distance: float,
                     nearest_threat_distance: float | None = None,
                     nearest_threat_score: float | None = None,
                     nearest_threat_position_x: float | None = None,
                     nearest_threat_position_y: float | None = None,
                     active_threat_count: int = 0):
        """Write a single decision record."""
        if not self.output_path:
            return

        record = {
            "tick": tick,
            "snake_id": snake_id,
            "position": {"x": round(pos_x, 2), "y": round(pos_y, 2)},
            "mass": round(mass, 2),
            "heading": round(heading, 4),
            "strategy_mode": strategy_mode,
            "target_position": {"x": round(target_pos_x, 2), "y": round(target_pos_y, 2)} if target_pos_x is not None and target_pos_y is not None else None,
            "steering_heading": round(steering_heading, 4),
            "boost": boost,
            "nearest_food_distance": round(nearest_food_distance, 2) if nearest_food_distance is not None else None,
            "boundary_distance": round(boundary_distance, 2),
            "nearest_threat_distance": round(nearest_threat_distance, 2) if nearest_threat_distance is not None else None,
            "nearest_threat_score": round(nearest_threat_score, 2) if nearest_threat_score is not None else None,
            "nearest_threat_position": {"x": round(nearest_threat_position_x, 2), "y": round(nearest_threat_position_y, 2)} if nearest_threat_position_x is not None and nearest_threat_position_y is not None else None,
            "active_threat_count": active_threat_count
        }

        with open(self.output_path, 'a') as f:
            f.write(json.dumps(record) + '\n')

from __future__ import annotations
from sandbox.config import Config

class CollisionDetector:
    @staticmethod
    def check_all(snakes: list) -> list:
        """Checks collisions. Returns a list of dead snakes."""
        deaths = []

        for snake in snakes:
            if not snake.alive:
                continue

            # 1. Boundary check
            if snake.pos.length() + snake.radius > Config.WORLD_RADIUS:
                deaths.append(snake)
                continue

            # 2. Head-to-body
            # For this simple scaffold, we just check distance between head and all segments of other snakes.
            # No spatial hash yet, keep it O(N^2) but small N for the scaffold.
            collided = False
            for other_snake in snakes:
                if other_snake.id == snake.id or not other_snake.alive:
                    continue
                
                # Check head against other snake segments (skip first few segments near their head to avoid head-to-head edge cases in simple check)
                for i, segment in enumerate(other_snake.segments):
                    if i < 3: 
                        continue
                        
                    collision_dist = snake.radius + other_snake.radius
                    if snake.pos.distance_to(segment) < collision_dist:
                        deaths.append(snake)
                        collided = True
                        break
                
                if collided:
                    break

        return deaths

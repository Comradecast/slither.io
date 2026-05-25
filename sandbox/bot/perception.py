from __future__ import annotations
import math
from dataclasses import dataclass, field
from sandbox.vector import Vector2
from sandbox.config import Config

@dataclass
class PerceivedFood:
    pos: Vector2
    value: float
    distance: float
    angle_diff: float
    in_front: bool

@dataclass
class PerceivedSnake:
    id: int
    head: Vector2
    mass: float
    distance: float
    radius: float
    speed: float = Config.BASE_SPEED
    heading: float = 0.0
    wanted_heading: float | None = None

@dataclass
class PerceivedThreat:
    pos: Vector2
    source_id: int
    distance: float
    score: float
    angle_diff: float
    in_forward_cone: bool
    radius: float
    segment_index: int | None = None

@dataclass
class PerceptionState:
    """The bot's perception of the world."""
    my_id: int
    my_head: Vector2
    my_angle: float
    my_mass: float
    my_speed: float
    my_radius: float
    boundary_distance: float
    visible_food: list[PerceivedFood] = field(default_factory=list)
    visible_snakes: list[PerceivedSnake] = field(default_factory=list)
    nearest_threat: PerceivedThreat | None = None
    highest_threat: PerceivedThreat | None = None
    visible_threats: list[PerceivedThreat] = field(default_factory=list)
    active_threat_count: int = 0


class Perception:
    """Builds a PerceptionState from raw game state."""
    
    FORWARD_CONE_ANGLE = math.pi / 3  # 60 degrees left or right
    
    def __init__(self, vision_radius: float = Config.AI_VISION_RADIUS):
        self.vision_radius = vision_radius

    def build(self, my_snake, snakes: list, food_items: list) -> PerceptionState:
        # Distance to boundary from head
        dist_to_center = my_snake.pos.length()
        boundary_distance = Config.WORLD_RADIUS - dist_to_center

        visible_food = []
        for f in food_items:
            dist = my_snake.pos.distance_to(f.pos)
            if dist <= self.vision_radius:
                angle_to_food = math.atan2(f.pos.y - my_snake.pos.y, f.pos.x - my_snake.pos.x)
                angle_diff = self._normalize_angle(angle_to_food - my_snake.angle)
                visible_food.append(PerceivedFood(
                    pos=f.pos.copy(),
                    value=f.value,
                    distance=dist,
                    angle_diff=angle_diff,
                    in_front=abs(angle_diff) <= math.pi / 2,
                ))
                
        # Sort food by distance
        visible_food.sort(key=lambda x: x.distance)

        visible_snakes = []
        threats = []
        
        for s in snakes:
            if s.id == my_snake.id or not s.alive:
                continue
                
            dist_to_head = my_snake.pos.distance_to(s.pos)
            if dist_to_head <= self.vision_radius:
                visible_snakes.append(PerceivedSnake(
                    id=s.id, 
                    head=s.pos.copy(), 
                    mass=s.mass, 
                    distance=dist_to_head, 
                    radius=Config.get_radius(s.mass),
                    speed=s.speed,
                    heading=getattr(s, "angle", 0.0),
                    wanted_heading=getattr(s, "target_angle", getattr(s, "wang", None)),
                ))
                
            # Treat enemy segments as threats
            for i, segment in enumerate(s.segments):
                dist = my_snake.pos.distance_to(segment)
                if dist <= self.vision_radius:
                    # Calculate angle
                    angle_to_threat = math.atan2(segment.y - my_snake.pos.y, segment.x - my_snake.pos.x)
                    angle_diff = self._normalize_angle(angle_to_threat - my_snake.angle)
                    
                    in_forward_cone = abs(angle_diff) < self.FORWARD_CONE_ANGLE
                    
                    # Simple score: closer = higher score. Max base score is vision_radius
                    base_score = self.vision_radius - dist
                    
                    # Threats in front score higher (2x multiplier)
                    score = base_score * 2.0 if in_forward_cone else base_score
                    
                    threats.append(PerceivedThreat(
                        pos=segment.copy(),
                        source_id=s.id,
                        distance=dist,
                        score=score,
                        angle_diff=angle_diff,
                        in_forward_cone=in_forward_cone,
                        radius=Config.get_radius(s.mass),
                        segment_index=i
                    ))
                    
        # Sort threats by score descending (highest score first)
        threats.sort(key=lambda x: x.score, reverse=True)
        
        highest_threat = threats[0] if threats else None
        
        # Sort by distance for nearest_threat
        threats_by_dist = sorted(threats, key=lambda x: x.distance)
        nearest_threat = threats_by_dist[0] if threats_by_dist else None

        return PerceptionState(
            my_id=my_snake.id,
            my_head=my_snake.pos.copy(),
            my_angle=my_snake.angle,
            my_mass=my_snake.mass,
            my_speed=my_snake.speed,
            my_radius=Config.get_radius(my_snake.mass),
            boundary_distance=boundary_distance,
            visible_food=visible_food,
            visible_snakes=visible_snakes,
            nearest_threat=nearest_threat,
            highest_threat=highest_threat,
            visible_threats=threats,
            active_threat_count=len(threats)
        )

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        return (angle + math.pi) % (2 * math.pi) - math.pi

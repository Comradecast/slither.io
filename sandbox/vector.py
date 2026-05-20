from __future__ import annotations
import math

class Vector2:
    __slots__ = ('x', 'y')

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def __add__(self, other: Vector2) -> Vector2:
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vector2) -> Vector2:
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vector2:
        return Vector2(self.x * scalar, self.y * scalar)

    def distance_to(self, other: Vector2) -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def distance_squared_to(self, other: Vector2) -> float:
        return (self.x - other.x)**2 + (self.y - other.y)**2

    def length(self) -> float:
        return math.hypot(self.x, self.y)

    def normalized(self) -> Vector2:
        l = self.length()
        if l == 0:
            return Vector2(0, 0)
        return Vector2(self.x / l, self.y / l)

    def copy(self) -> Vector2:
        return Vector2(self.x, self.y)

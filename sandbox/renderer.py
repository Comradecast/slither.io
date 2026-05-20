import pygame
from sandbox.config import Config
from sandbox.world import World

class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font = pygame.font.SysFont('Arial', 14)
        self.camera_x = 0
        self.camera_y = 0

    def draw(self, world: World, player_snake):
        self.screen.fill(Config.BACKGROUND_COLOR)

        if player_snake and player_snake.alive:
            self.camera_x = player_snake.x
            self.camera_y = player_snake.y

        cx = Config.SCREEN_WIDTH // 2
        cy = Config.SCREEN_HEIGHT // 2

        # Draw boundary
        pygame.draw.circle(
            self.screen, Config.BOUNDARY_COLOR,
            (int(-self.camera_x + cx), int(-self.camera_y + cy)),
            Config.WORLD_RADIUS, Config.BOUNDARY_WIDTH
        )

        # Draw food
        for food in world.food_manager.items:
            fx = int(food.x - self.camera_x + cx)
            fy = int(food.y - self.camera_y + cy)
            pygame.draw.circle(self.screen, (150, 230, 161), (fx, fy), int(food.radius))

        # Draw snakes
        for snake in world.snakes:
            if not snake.alive:
                continue
                
            color = (255, 107, 107) if snake == player_snake else (78, 205, 196)
            
            # Draw body
            for segment in reversed(snake.segments):
                sx = int(segment.x - self.camera_x + cx)
                sy = int(segment.y - self.camera_y + cy)
                pygame.draw.circle(self.screen, color, (sx, sy), int(snake.radius))

            # Draw head slightly darker
            hx = int(snake.x - self.camera_x + cx)
            hy = int(snake.y - self.camera_y + cy)
            pygame.draw.circle(self.screen, (200, 50, 50) if snake == player_snake else (50, 150, 150), (hx, hy), int(snake.radius) + 1)

        if player_snake:
            hud_text = f"Mass: {int(player_snake.mass)} | Alive: {player_snake.alive}"
            text_surface = self.font.render(hud_text, True, (255, 255, 255))
            self.screen.blit(text_surface, (10, 10))

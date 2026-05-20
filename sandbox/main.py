import pygame
import sys
import math
from sandbox.config import Config
from sandbox.world import World
from sandbox.renderer import Renderer

def main():
    pygame.init()
    screen = pygame.display.set_mode((Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT))
    pygame.display.set_caption("Slither Sandbox")
    clock = pygame.time.Clock()

    world = World()
    renderer = Renderer(screen)

    # Spawn player
    player = world.spawn_snake(0, 0, 0)
    
    # Spawn dummy AI
    world.spawn_snake(1, 200, 200, is_bot=True)

    running = True
    while running:
        dt = clock.tick(Config.TICK_RATE) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        if player.alive:
            # Handle input
            mouse_x, mouse_y = pygame.mouse.get_pos()
            cx = Config.SCREEN_WIDTH // 2
            cy = Config.SCREEN_HEIGHT // 2
            
            player.target_angle = math.atan2(mouse_y - cy, mouse_x - cx)
            
            keys = pygame.key.get_pressed()
            buttons = pygame.mouse.get_pressed()
            player.boosting = keys[pygame.K_SPACE] or buttons[2]

        world.update(dt)
        renderer.draw(world, player)
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()

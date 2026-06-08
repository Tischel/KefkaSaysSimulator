import sys
import ctypes
import pygame
from constants import WINDOW_WIDTH, WINDOW_HEIGHT, FPS, BACKGROUND_COLOR
from game import Game
from hud import Legend


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Kefka Says Simulator")
    ctypes.windll.user32.ShowWindow(pygame.display.get_wm_info()['window'], 3)
    clock = pygame.time.Clock()
    game = Game()
    legend = Legend()

    while True:
        dt = clock.tick(FPS) / 1000.0
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()
        keys = pygame.key.get_pressed()

        sw, sh = screen.get_size()
        arena_offset = ((sw - WINDOW_WIDTH) // 2, (sh - WINDOW_HEIGHT) // 2)

        game.update(dt, keys, events, arena_offset)
        game.render(screen, arena_offset)
        legend.render(screen)
        pygame.display.flip()


if __name__ == "__main__":
    main()

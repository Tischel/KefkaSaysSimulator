import sys
import ctypes
import pygame
from constants import WINDOW_WIDTH, WINDOW_HEIGHT, FPS, BACKGROUND_COLOR
from game import Game
from hud import Legend, FpsCounter
from role_select import RoleSelectScreen


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Kefka Says Simulator")
    hwnd = pygame.display.get_wm_info()['window']
    ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0001 | 0x0004)  # move to primary monitor origin, keep size/z-order
    ctypes.windll.user32.ShowWindow(hwnd, 3)
    clock = pygame.time.Clock()

    role_select = RoleSelectScreen()
    selected_role = None
    while selected_role is None:
        dt = clock.tick(FPS) / 1000.0
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()
        sw, sh = screen.get_size()
        arena_offset = ((sw - WINDOW_WIDTH) // 2, (sh - WINDOW_HEIGHT) // 2)
        selected_role = role_select.update(events, arena_offset)
        role_select.render(screen, arena_offset)
        pygame.display.flip()

    start_time = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
    game = Game(selected_role, start_time=start_time)
    legend = Legend()
    fps_counter = FpsCounter()

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
        fps_counter.render(screen, clock.get_fps())
        pygame.display.flip()


if __name__ == "__main__":
    main()

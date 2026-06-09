import os
import pygame
from constants import BACKGROUND_COLOR, ARENA_CENTER
from _paths import ASSETS as _ASSETS


class Arena:
    def __init__(self):
        self._layers = [
            pygame.image.load(os.path.join(_ASSETS, 'arena.png')).convert_alpha(),
            pygame.image.load(os.path.join(_ASSETS, 'markers.png')).convert_alpha(),
            pygame.image.load(os.path.join(_ASSETS, 'hitbox.png')).convert_alpha(),
        ]

    def render(self, surface, offset=(0, 0)):
        surface.fill(BACKGROUND_COLOR)
        cx = ARENA_CENTER[0] + offset[0]
        cy = ARENA_CENTER[1] + offset[1]
        for img in self._layers:
            surface.blit(img, img.get_rect(center=(cx, cy)))

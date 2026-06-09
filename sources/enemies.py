import os
import pygame
from constants import ARENA_CENTER, ARENA_RADIUS

_ASSETS = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets'))


class Enemies:
    def __init__(self):
        chaos_img = pygame.image.load(os.path.join(_ASSETS, 'chaos.png')).convert_alpha()
        neo_img = pygame.image.load(os.path.join(_ASSETS, 'neo_exdeath.png')).convert_alpha()

        self._chaos = (chaos_img, chaos_img.get_rect(
            right=ARENA_CENTER[0] - ARENA_RADIUS,
            centery=ARENA_CENTER[1],
        ))
        self._neo = (neo_img, neo_img.get_rect(
            bottom=ARENA_CENTER[1] - ARENA_RADIUS,
            centerx=ARENA_CENTER[0],
        ))

    @property
    def chaos_center(self):
        return self._chaos[1].center

    @property
    def neo_center(self):
        return self._neo[1].center

    def render(self, surface, offset=(0, 0)):
        ox, oy = offset
        for img, rect in (self._chaos, self._neo):
            surface.blit(img, rect.move(ox, oy))

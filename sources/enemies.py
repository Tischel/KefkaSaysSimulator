import math
import os
import pygame
from constants import ARENA_CENTER, ARENA_RADIUS
from _paths import ASSETS as _ASSETS

_DIAG = ARENA_RADIUS * math.cos(math.radians(45))


class Enemies:
    def __init__(self):
        self._chaos_img = pygame.image.load(os.path.join(_ASSETS, 'chaos.png')).convert_alpha()
        self._neo_img   = pygame.image.load(os.path.join(_ASSETS, 'neo_exdeath.png')).convert_alpha()

        cx, cy = ARENA_CENTER
        # Chaos: NW, bottom-right corner at the NW edge of the arena circle
        self._chaos_rect = self._chaos_img.get_rect(
            bottomright=(cx - _DIAG, cy - _DIAG),
        )
        # Neo: NE starting position, bottom-left corner at the NE edge
        self._neo_ne_rect = self._neo_img.get_rect(
            bottomleft=(cx + _DIAG, cy - _DIAG),
        )
        # Neo: north position (after 3rd Grand Cross)
        self._neo_north_rect = self._neo_img.get_rect(
            bottom=cy - ARENA_RADIUS,
            centerx=cx,
        )
        self._neo_rect = self._neo_ne_rect

        self._chaos_visible = True
        self._neo_visible = True

    @property
    def chaos_rect(self):
        return self._chaos_rect

    @property
    def chaos_center(self):
        return self._chaos_rect.center

    @property
    def neo_rect(self):
        return self._neo_rect

    @property
    def neo_center(self):
        return self._neo_rect.center

    def hide_chaos(self):
        self._chaos_visible = False

    def hide_neo(self):
        self._neo_visible = False

    def teleport_neo_north(self):
        self._neo_rect = self._neo_north_rect

    def reset(self):
        self._chaos_visible = True
        self._neo_visible = True
        self._neo_rect = self._neo_ne_rect

    def render(self, surface, offset=(0, 0)):
        ox, oy = offset
        for img, rect, visible in (
            (self._chaos_img, self._chaos_rect, self._chaos_visible),
            (self._neo_img,   self._neo_rect,   self._neo_visible),
        ):
            if visible:
                surface.blit(img, rect.move(ox, oy))

import math
import os
import random
import pygame
from constants import ARENA_CENTER, PLAYER_SPEED

_ASSETS = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets'))

CIRCLE_ORDER = ['T1', 'R2', 'H2', 'M2', 'T2', 'M1', 'H1', 'R1']
_CIRCLE_RADIUS = 150
_JITTER = 40  # max random offset in pixels


def circle_positions():
    n = len(CIRCLE_ORDER)
    result = {}
    for i, role in enumerate(CIRCLE_ORDER):
        angle = -math.pi / 2 + i * (2 * math.pi / n)
        x = ARENA_CENTER[0] + _CIRCLE_RADIUS * math.cos(angle)
        y = ARENA_CENTER[1] + _CIRCLE_RADIUS * math.sin(angle)
        result[role] = pygame.Vector2(x, y)
    return result


class Bot:
    def __init__(self, role, start_pos):
        self._icon = pygame.image.load(os.path.join(_ASSETS, f'{role}.png')).convert_alpha()
        self._start_pos = pygame.Vector2(start_pos)
        self.position = pygame.Vector2(start_pos)
        self._destination = None
        self._moving = False

    def set_destination(self, base_dest):
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(0, _JITTER)
        self._destination = pygame.Vector2(
            base_dest[0] + math.cos(angle) * dist,
            base_dest[1] + math.sin(angle) * dist,
        )
        self._moving = False

    def reset(self):
        self.position = pygame.Vector2(self._start_pos)
        self._destination = None
        self._moving = False

    def update(self, dt, state_timer):
        if self._destination is None:
            return
        to_dest = self._destination - self.position
        dist = to_dest.length()
        if dist < 0.5:
            self.position = pygame.Vector2(self._destination)
            return
        travel_time = dist / PLAYER_SPEED
        if state_timer <= travel_time * 1.1:
            self._moving = True
        if self._moving:
            step = PLAYER_SPEED * dt
            if step >= dist:
                self.position = pygame.Vector2(self._destination)
            else:
                self.position += to_dest.normalize() * step

    def render(self, surface, offset=(0, 0)):
        sx = int(self.position.x) + offset[0]
        sy = int(self.position.y) + offset[1]
        surface.blit(self._icon, self._icon.get_rect(center=(sx, sy)))

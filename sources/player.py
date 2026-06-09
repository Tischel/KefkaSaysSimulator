import os
import pygame
from constants import ARENA_CENTER, ARENA_RADIUS, PLAYER_SPEED

_ASSETS = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets'))


class Player:
    def __init__(self, role='T1', start_pos=None):
        self.role = role
        self._icon = pygame.image.load(os.path.join(_ASSETS, f'{role}.png')).convert_alpha()
        self.position = pygame.Vector2(start_pos if start_pos is not None else ARENA_CENTER)
        self.debuffs = []

    def update(self, dt, keys):
        dx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
        velocity = pygame.Vector2(dx, dy)
        if velocity.length_squared() > 0:
            velocity.normalize_ip()
        self.position += velocity * PLAYER_SPEED * dt

        center = pygame.Vector2(ARENA_CENTER)
        offset = self.position - center
        if offset.length() > ARENA_RADIUS:
            self.position = center + offset.normalize() * ARENA_RADIUS

    def render(self, surface, offset=(0, 0)):
        screen_x = int(self.position.x) + offset[0]
        screen_y = int(self.position.y) + offset[1]
        surface.blit(self._icon, self._icon.get_rect(center=(screen_x, screen_y)))

    def update_debuffs(self, dt):
        for d in self.debuffs:
            d.update(dt)
        self.debuffs = sorted(
            [d for d in self.debuffs if not d.is_expired],
            key=lambda d: d.sort_order,
        )

    def get_center(self):
        return (self.position.x, self.position.y)

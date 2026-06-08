import math
import os
import random
import pygame
from constants import (
    ARENA_CENTER,
    LIGHTNING_COLOR, LIGHTNING_TELEGRAPH_COLOR, LIGHTNING_RECT_W, LIGHTNING_RECT_H,
    LIGHTNING_RING_OFFSET, LIGHTNING_RING_COLOR,
    ICE_COLOR, ICE_TELEGRAPH_COLOR, ICE_RECT_SIZE,
    ICE_RING_OFFSET, ICE_RING_COLOR,
    TELEGRAPH_RING_W, TELEGRAPH_RING_H, TELEGRAPH_RING_LINE_W, ORB_REVOLUTION_TIME,
    TELEGRAPH_BORDER_COLOR, TELEGRAPH_BORDER_WIDTH,
)

_ASSETS = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets'))
_orb_real = None
_orb_fake = None


def _get_orbs():
    global _orb_real, _orb_fake
    if _orb_real is None:
        _orb_real = pygame.image.load(os.path.join(_ASSETS, 'orb_real.png')).convert_alpha()
        _orb_fake = pygame.image.load(os.path.join(_ASSETS, 'orb_fake.png')).convert_alpha()
    return _orb_real, _orb_fake


def _draw_ring(surface, center, angle, color, offset, fake=False):
    ox, oy = offset
    sx = center[0] + ox
    sy = center[1] + oy
    a = TELEGRAPH_RING_W // 2
    b = TELEGRAPH_RING_H // 2
    ring_rect = pygame.Rect(sx - a, sy - b, TELEGRAPH_RING_W, TELEGRAPH_RING_H)
    pygame.draw.ellipse(surface, color, ring_rect, TELEGRAPH_RING_LINE_W)
    orb_real, orb_fake = _get_orbs()
    orb_img = orb_fake if fake else orb_real
    for i in range(2):
        theta = angle + i * math.pi
        px = int(sx + a * math.cos(theta))
        py = int(sy + b * math.sin(theta))
        surface.blit(orb_img, orb_img.get_rect(center=(px, py)))


class LightningAttack:
    def __init__(self):
        self.angle = random.choice([45, -45])
        a = math.radians(self.angle)
        perp = pygame.Vector2(math.cos(a), -math.sin(a))
        origin = pygame.Vector2(ARENA_CENTER)
        all_offsets = [[-294, 98], [-98, 294]]
        idx = random.randint(0, 1)
        self.centers = [origin + perp * o for o in all_offsets[idx]]
        self._inverted_centers = [origin + perp * o for o in all_offsets[1 - idx]]
        self._ring_center = (ARENA_CENTER[0] + LIGHTNING_RING_OFFSET[0],
                             ARENA_CENTER[1] + LIGHTNING_RING_OFFSET[1])
        self._ring_color = LIGHTNING_RING_COLOR
        self._ring_angle = 0.0
        self.is_fake = random.choice([True, False])

    def update(self, dt):
        self._ring_angle += (2 * math.pi / ORB_REVOLUTION_TIME) * dt

    def render(self, surface, telegraphing, alpha, offset=(0, 0)):
        color = LIGHTNING_TELEGRAPH_COLOR if telegraphing else LIGHTNING_COLOR
        ox, oy = offset
        centers = self.centers if (telegraphing or not self.is_fake) else self._inverted_centers
        for c in centers:
            surf = pygame.Surface((LIGHTNING_RECT_W, LIGHTNING_RECT_H), pygame.SRCALPHA)
            surf.fill((*color, alpha))
            if telegraphing:
                pygame.draw.rect(surf, (*TELEGRAPH_BORDER_COLOR, alpha), surf.get_rect(), TELEGRAPH_BORDER_WIDTH)
            rotated = pygame.transform.rotate(surf, self.angle)
            surface.blit(rotated, rotated.get_rect(center=(int(c.x) + ox, int(c.y) + oy)))

    def render_ring(self, surface, offset=(0, 0)):
        _draw_ring(surface, self._ring_center, self._ring_angle, self._ring_color, offset, self.is_fake)

    def is_hit(self, point):
        a = math.radians(self.angle)
        cos_a, sin_a = math.cos(a), math.sin(a)
        half_w, half_h = LIGHTNING_RECT_W / 2, LIGHTNING_RECT_H / 2
        centers = self._inverted_centers if self.is_fake else self.centers
        for c in centers:
            dx, dy = point[0] - c.x, point[1] - c.y
            local_x = cos_a * dx - sin_a * dy
            local_y = sin_a * dx + cos_a * dy
            if abs(local_x) <= half_w and abs(local_y) <= half_h:
                return True
        return False


class IceAttack:
    def __init__(self):
        cx, cy = ARENA_CENTER
        s = ICE_RECT_SIZE
        quads = {
            'NW': pygame.Rect(cx - s, cy - s, s, s),
            'NE': pygame.Rect(cx,     cy - s, s, s),
            'SW': pygame.Rect(cx - s, cy,     s, s),
            'SE': pygame.Rect(cx,     cy,     s, s),
        }
        pairs = [('NW', 'SE'), ('NE', 'SW')]
        idx = random.randint(0, 1)
        a, b = pairs[idx]
        inv_a, inv_b = pairs[1 - idx]
        self.rects = [quads[a], quads[b]]
        self._inverted_rects = [quads[inv_a], quads[inv_b]]
        self._ring_center = (ARENA_CENTER[0] + ICE_RING_OFFSET[0],
                             ARENA_CENTER[1] + ICE_RING_OFFSET[1])
        self._ring_color = ICE_RING_COLOR
        self._ring_angle = 0.0
        self.is_fake = random.choice([True, False])

    def update(self, dt):
        self._ring_angle += (2 * math.pi / ORB_REVOLUTION_TIME) * dt

    def render(self, surface, telegraphing, alpha, offset=(0, 0)):
        color = ICE_TELEGRAPH_COLOR if telegraphing else ICE_COLOR
        s = ICE_RECT_SIZE
        ox, oy = offset
        rects = self.rects if (telegraphing or not self.is_fake) else self._inverted_rects
        for rect in rects:
            surf = pygame.Surface((s, s), pygame.SRCALPHA)
            surf.fill((*color, alpha))
            if telegraphing:
                pygame.draw.rect(surf, (*TELEGRAPH_BORDER_COLOR, alpha), surf.get_rect(), TELEGRAPH_BORDER_WIDTH)
            surface.blit(surf, (rect.x + ox, rect.y + oy))

    def render_ring(self, surface, offset=(0, 0)):
        _draw_ring(surface, self._ring_center, self._ring_angle, self._ring_color, offset, self.is_fake)

    def is_hit(self, point):
        rects = self._inverted_rects if self.is_fake else self.rects
        return any(r.collidepoint(point) for r in rects)

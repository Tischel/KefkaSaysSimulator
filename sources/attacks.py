import math
import random
import pygame
from constants import (
    ARENA_CENTER,
    LIGHTNING_COLOR, LIGHTNING_TELEGRAPH_COLOR, LIGHTNING_RECT_W, LIGHTNING_RECT_H,
    ICE_COLOR, ICE_TELEGRAPH_COLOR, ICE_RECT_SIZE,
)


class LightningAttack:
    def __init__(self):
        self.angle = random.choice([45, -45])
        a = math.radians(self.angle)
        # Short axis of the rotated rect (perpendicular to the stripe direction)
        perp = pygame.Vector2(math.cos(a), -math.sin(a))
        origin = pygame.Vector2(ARENA_CENTER)
        offsets = random.choice([[-294, 98], [-98, 294]])
        self.centers = [origin + perp * o for o in offsets]

    def render(self, surface, telegraphing, alpha, offset=(0, 0)):
        color = LIGHTNING_TELEGRAPH_COLOR if telegraphing else LIGHTNING_COLOR
        ox, oy = offset
        for c in self.centers:
            surf = pygame.Surface((LIGHTNING_RECT_W, LIGHTNING_RECT_H), pygame.SRCALPHA)
            surf.fill((*color, alpha))
            rotated = pygame.transform.rotate(surf, self.angle)
            surface.blit(rotated, rotated.get_rect(center=(int(c.x) + ox, int(c.y) + oy)))

    def is_hit(self, point):
        a = math.radians(self.angle)
        cos_a, sin_a = math.cos(a), math.sin(a)
        half_w, half_h = LIGHTNING_RECT_W / 2, LIGHTNING_RECT_H / 2
        for c in self.centers:
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
        a, b = random.choice([('NW', 'SE'), ('NE', 'SW')])
        self.rects = [quads[a], quads[b]]

    def render(self, surface, telegraphing, alpha, offset=(0, 0)):
        color = ICE_TELEGRAPH_COLOR if telegraphing else ICE_COLOR
        s = ICE_RECT_SIZE
        ox, oy = offset
        for rect in self.rects:
            surf = pygame.Surface((s, s), pygame.SRCALPHA)
            surf.fill((*color, alpha))
            surface.blit(surf, (rect.x + ox, rect.y + oy))

    def is_hit(self, point):
        return any(r.collidepoint(point) for r in self.rects)

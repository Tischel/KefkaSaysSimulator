import math
import os
import random
import pygame
from constants import (
    ARENA_CENTER, ARENA_RADIUS,
    LIGHTNING_COLOR, LIGHTNING_TELEGRAPH_COLOR, LIGHTNING_RECT_W, LIGHTNING_RECT_H,
    LIGHTNING_RING_OFFSET, LIGHTNING_RING_COLOR,
    ICE_COLOR, ICE_TELEGRAPH_COLOR, ICE_RECT_SIZE,
    ICE_RING_OFFSET, ICE_RING_COLOR,
    TELEGRAPH_RING_W, TELEGRAPH_RING_H, TELEGRAPH_RING_LINE_W, ORB_REVOLUTION_TIME,
    TELEGRAPH_BORDER_COLOR, TELEGRAPH_BORDER_WIDTH,
    WHITE_ANTILIGHT_COLOR, BLACK_ANTILIGHT_COLOR, ANTILIGHT_H, ANTILIGHT_TELEGRAPH_SIZE,
    ANTILIGHT_TELEGRAPH_GAP,
    ENTROPY_COLOR, ENTROPY_TELEGRAPH_COLOR, ENTROPY_RADIUS,
    DYNAMIC_FLUID_COLOR, DYNAMIC_FLUID_TELEGRAPH_COLOR, DYNAMIC_FLUID_RADIUS,
)
from debuff import Debuff

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


def compute_safe_centroid(lightning, ice):
    """Return the centroid of the safe intersection region closest to the arena center."""
    cx, cy = ARENA_CENTER
    s = ICE_RECT_SIZE
    quadrants = [
        pygame.Rect(cx - s, cy - s, s, s),  # NW
        pygame.Rect(cx,     cy - s, s, s),  # NE
        pygame.Rect(cx - s, cy,     s, s),  # SW
        pygame.Rect(cx,     cy,     s, s),  # SE
    ]
    n = 15
    candidates = []
    for quad in quadrants:
        sx_step = quad.width / n
        sy_step = quad.height / n
        sum_x = sum_y = count = 0
        for i in range(n):
            for j in range(n):
                x = quad.x + (i + 0.5) * sx_step
                y = quad.y + (j + 0.5) * sy_step
                if not lightning.is_hit((x, y)) and not ice.is_hit((x, y)):
                    sum_x += x
                    sum_y += y
                    count += 1
        if count > 0:
            candidates.append((sum_x / count, sum_y / count))
    if not candidates:
        return ARENA_CENTER
    return min(candidates, key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2)


class LightningAttack:
    def __init__(self):
        self.angle = random.choice([45, -45])
        a = math.radians(self.angle)
        perp = pygame.Vector2(math.cos(a), -math.sin(a))
        origin = pygame.Vector2(ARENA_CENTER)
        all_offsets = [[-294, 98], [-98, 294]]
        idx = random.randint(0, 1)
        self._idx = idx
        self.centers = [origin + perp * o for o in all_offsets[idx]]
        self._inverted_centers = [origin + perp * o for o in all_offsets[1 - idx]]
        self._ring_center = (ARENA_CENTER[0] + LIGHTNING_RING_OFFSET[0],
                             ARENA_CENTER[1] + LIGHTNING_RING_OFFSET[1])
        self._ring_color = LIGHTNING_RING_COLOR
        self._ring_angle = 0.0
        self.is_fake = random.choice([True, False])

    @property
    def effective_pair_idx(self):
        return self._idx if not self.is_fake else 1 - self._idx

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
        self._idx = idx
        a, b = pairs[idx]
        inv_a, inv_b = pairs[1 - idx]
        self.rects = [quads[a], quads[b]]
        self._inverted_rects = [quads[inv_a], quads[inv_b]]
        self._ring_center = (ARENA_CENTER[0] + ICE_RING_OFFSET[0],
                             ARENA_CENTER[1] + ICE_RING_OFFSET[1])
        self._ring_color = ICE_RING_COLOR
        self._ring_angle = 0.0
        self.is_fake = random.choice([True, False])

    @property
    def effective_pair_idx(self):
        return self._idx if not self.is_fake else 1 - self._idx

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


class RingOnlyAttack:
    def __init__(self, ring_offset, ring_color, is_fake=False):
        self._ring_center = (ARENA_CENTER[0] + ring_offset[0],
                             ARENA_CENTER[1] + ring_offset[1])
        self._ring_color = ring_color
        self._ring_angle = 0.0
        self.is_fake = is_fake

    def update(self, dt):
        self._ring_angle += (2 * math.pi / ORB_REVOLUTION_TIME) * dt

    def render(self, surface, telegraphing, alpha, offset=(0, 0)):
        pass

    def render_ring(self, surface, offset=(0, 0)):
        _draw_ring(surface, self._ring_center, self._ring_angle, self._ring_color, offset, self.is_fake)

    def is_hit(self, point):
        return False


class AntilightAttack:
    def __init__(self, wound_type, side, neo_rect, is_fake=False):
        # wound_type: 'white' or 'black'
        # side: 'west' or 'east' — where the telegraph appears and where it hits when real
        self.wound_type = wound_type
        self.side = side
        self.is_fake = is_fake
        self._neo_rect = neo_rect
        icon = 'white_wound_5541.png' if wound_type == 'white' else 'black_wound_5542.png'
        img = pygame.image.load(os.path.join(_ASSETS, icon)).convert_alpha()
        self._telegraph_img = pygame.transform.smoothscale(img, ANTILIGHT_TELEGRAPH_SIZE)
        self._color = WHITE_ANTILIGHT_COLOR if wound_type == 'white' else BLACK_ANTILIGHT_COLOR

    def _hit_side(self):
        if self.is_fake:
            return 'east' if self.side == 'west' else 'west'
        return self.side

    def update(self, dt):
        pass

    def render(self, surface, telegraphing, alpha, offset=(0, 0)):
        if telegraphing:
            return  # telegraph is the image drawn unmasked via render_ring
        ox, oy = offset
        hit_side = self._hit_side()
        x = (ARENA_CENTER[0] - ARENA_RADIUS + ox) if hit_side == 'west' else (ARENA_CENTER[0] + ox)
        y = ARENA_CENTER[1] - ANTILIGHT_H // 2 + oy
        surf = pygame.Surface((ARENA_RADIUS, ANTILIGHT_H), pygame.SRCALPHA)
        surf.fill((*self._color, alpha))
        surface.blit(surf, (x, y))

    def render_ring(self, surface, offset=(0, 0)):
        ox, oy = offset
        neo = self._neo_rect.move(ox, oy)
        iw, ih = ANTILIGHT_TELEGRAPH_SIZE
        img_x = (neo.left - iw - ANTILIGHT_TELEGRAPH_GAP) if self.side == 'west' else (neo.right + ANTILIGHT_TELEGRAPH_GAP)
        img_y = neo.centery - ih // 2
        surface.blit(self._telegraph_img, (img_x, img_y))

    def is_hit(self, point):
        return point[0] < ARENA_CENTER[0] if self._hit_side() == 'west' else point[0] >= ARENA_CENTER[0]

    def apply_hit_effect(self, members):
        swap_from = 'black_wound' if self.wound_type == 'white' else 'white_wound'
        swap_to   = 'white_wound' if self.wound_type == 'white' else 'black_wound'
        for member in members.values():
            if not self.is_hit((member.position.x, member.position.y)):
                continue
            if any(d.debuff_type == swap_from for d in member.debuffs):
                member.debuffs = [d for d in member.debuffs if d.debuff_type != swap_from]
                member.debuffs.append(Debuff(swap_to, None))
                member.debuffs.sort(key=lambda d: d.sort_order)


class EntropyAttack:
    def __init__(self, center, is_fake=False):
        self.center = pygame.Vector2(center)
        self.is_fake = is_fake

    def update(self, dt):
        pass

    def render(self, surface, telegraphing, alpha, offset=(0, 0)):
        color = ENTROPY_TELEGRAPH_COLOR if telegraphing else ENTROPY_COLOR
        ox, oy = offset
        cx = int(self.center.x) + ox
        cy = int(self.center.y) + oy
        if self.is_fake:
            surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            surf.fill((*color, alpha))
            pygame.draw.circle(surf, (0, 0, 0, 0), (cx, cy), ENTROPY_RADIUS)
            surface.blit(surf, (0, 0))
        else:
            pygame.draw.circle(surface, (*color, alpha), (cx, cy), ENTROPY_RADIUS)

    def render_ring(self, surface, offset=(0, 0)):
        pass

    def is_hit(self, point):
        dist = (pygame.Vector2(point) - self.center).length()
        return dist > ENTROPY_RADIUS if self.is_fake else dist <= ENTROPY_RADIUS


class DynamicFluidAttack:
    def __init__(self, center, is_fake=False):
        self.center = pygame.Vector2(center)
        self.is_fake = is_fake

    def update(self, dt):
        pass

    def render(self, surface, telegraphing, alpha, offset=(0, 0)):
        color = DYNAMIC_FLUID_TELEGRAPH_COLOR if telegraphing else DYNAMIC_FLUID_COLOR
        ox, oy = offset
        cx = int(self.center.x) + ox
        cy = int(self.center.y) + oy
        if not self.is_fake:  # real = inverted: safe inside, fill outside
            surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            surf.fill((*color, alpha))
            pygame.draw.circle(surf, (0, 0, 0, 0), (cx, cy), DYNAMIC_FLUID_RADIUS)
            surface.blit(surf, (0, 0))
        else:  # fake = filled circle: danger inside
            pygame.draw.circle(surface, (*color, alpha), (cx, cy), DYNAMIC_FLUID_RADIUS)

    def render_ring(self, surface, offset=(0, 0)):
        pass

    def is_hit(self, point):
        dist = (pygame.Vector2(point) - self.center).length()
        return dist > DYNAMIC_FLUID_RADIUS if not self.is_fake else dist <= DYNAMIC_FLUID_RADIUS

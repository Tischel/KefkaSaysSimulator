"""Visualize the 8 attack combinations at actual game scale. Arrow keys to cycle."""
import sys
import math
import ctypes
import pygame

pygame.init()

# --- Game constants (match constants.py) ---
ARENA_CENTER = (400, 400)
ARENA_RADIUS = 392
WINDOW_SIZE  = 800
ICE_S        = 420
L_W          = 196
L_H          = 820
BG_COLOR     = (58, 103, 164)

ALL_OFFSETS = [[-294, 98], [-98, 294]]
ICE_PAIRS   = [('NW', 'SE'), ('NE', 'SW')]

COMBOS = [
    (45,  0, 0), (45,  0, 1),
    (45,  1, 0), (45,  1, 1),
    (-45, 0, 0), (-45, 0, 1),
    (-45, 1, 0), (-45, 1, 1),
]

COMBO_LABELS = [
    "+45°  pair A  |  Ice NW+SE",
    "+45°  pair A  |  Ice NE+SW",
    "+45°  pair B  |  Ice NW+SE",
    "+45°  pair B  |  Ice NE+SW",
    "-45°  pair A  |  Ice NW+SE",
    "-45°  pair A  |  Ice NE+SW",
    "-45°  pair B  |  Ice NW+SE",
    "-45°  pair B  |  Ice NE+SW",
]

# --- Window ---
screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE), pygame.RESIZABLE)
pygame.display.set_caption("Attack Combinations Visualizer")
hwnd = pygame.display.get_wm_info()['window']
ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0001 | 0x0004)
ctypes.windll.user32.ShowWindow(hwnd, 3)

clock = pygame.time.Clock()
font_s = pygame.font.SysFont("arial", 13)
font_m = pygame.font.SysFont("arial", 16)
font_l = pygame.font.SysFont("arial", 22, bold=True)

# --- Circle mask (game space, 800x800) ---
_mask = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
_mask.fill((0, 0, 0, 0))
pygame.draw.circle(_mask, (255, 255, 255, 255), ARENA_CENTER, ARENA_RADIUS)
ARENA_MASK = _mask


def _ice_rects(i_idx):
    cx, cy = ARENA_CENTER
    rects = []
    for q in ICE_PAIRS[i_idx]:
        if q == 'NW': rects.append(pygame.Rect(cx - ICE_S, cy - ICE_S, ICE_S, ICE_S))
        if q == 'NE': rects.append(pygame.Rect(cx,         cy - ICE_S, ICE_S, ICE_S))
        if q == 'SW': rects.append(pygame.Rect(cx - ICE_S, cy,         ICE_S, ICE_S))
        if q == 'SE': rects.append(pygame.Rect(cx,         cy,         ICE_S, ICE_S))
    return rects


def _build_combo_surf(angle_deg, l_idx, i_idx):
    """Pre-render one combination to an 800x800 SRCALPHA surface."""
    surf = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)

    # Grey arena base
    pygame.draw.circle(surf, (55, 55, 55, 255), ARENA_CENTER, ARENA_RADIUS)

    # Green safe-zone tint
    safe = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
    pygame.draw.circle(safe, (60, 190, 80, 70), ARENA_CENTER, ARENA_RADIUS)
    surf.blit(safe, (0, 0))

    # Ice hit rects (blue)
    ice_s = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
    for rect in _ice_rects(i_idx):
        pygame.draw.rect(ice_s, (80, 140, 220, 150), rect)
    surf.blit(ice_s, (0, 0))

    # Lightning hit stripes (purple)
    a = math.radians(angle_deg)
    perp = (math.cos(a), -math.sin(a))
    l_s = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
    for off in ALL_OFFSETS[l_idx]:
        cx2 = ARENA_CENTER[0] + perp[0] * off
        cy2 = ARENA_CENTER[1] + perp[1] * off
        stripe = pygame.Surface((L_W, L_H), pygame.SRCALPHA)
        stripe.fill((160, 60, 220, 150))
        rot = pygame.transform.rotate(stripe, angle_deg)
        l_s.blit(rot, rot.get_rect(center=(int(cx2), int(cy2))))
    surf.blit(l_s, (0, 0))

    # Clip to circle
    surf.blit(ARENA_MASK, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return surf


# Pre-render all 8 combinations once
COMBO_SURFS = [_build_combo_surf(*c) for c in COMBOS]

current = 0

while True:
    clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()
            if event.key in (pygame.K_RIGHT, pygame.K_DOWN):
                current = (current + 1) % len(COMBOS)
            if event.key in (pygame.K_LEFT, pygame.K_UP):
                current = (current - 1) % len(COMBOS)

    sw, sh = screen.get_size()
    arena_offset = ((sw - WINDOW_SIZE) // 2, (sh - WINDOW_SIZE) // 2)
    ox, oy = arena_offset
    screen_cx = ARENA_CENTER[0] + ox
    screen_cy = ARENA_CENTER[1] + oy

    # Background
    screen.fill(BG_COLOR)

    # Combo surface
    screen.blit(COMBO_SURFS[current], arena_offset)

    # Crosshair
    pygame.draw.line(screen, (100, 100, 100),
                     (screen_cx, screen_cy - ARENA_RADIUS),
                     (screen_cx, screen_cy + ARENA_RADIUS), 1)
    pygame.draw.line(screen, (100, 100, 100),
                     (screen_cx - ARENA_RADIUS, screen_cy),
                     (screen_cx + ARENA_RADIUS, screen_cy), 1)

    # Arena border
    pygame.draw.circle(screen, (200, 200, 200), (screen_cx, screen_cy), ARENA_RADIUS, 1)

    # Compass
    for lbl, pos in [
        ("N", (screen_cx - 5,              screen_cy - ARENA_RADIUS - 18)),
        ("S", (screen_cx - 4,              screen_cy + ARENA_RADIUS + 4)),
        ("W", (screen_cx - ARENA_RADIUS - 18, screen_cy - 7)),
        ("E", (screen_cx + ARENA_RADIUS + 4,  screen_cy - 7)),
    ]:
        screen.blit(font_s.render(lbl, True, (160, 160, 160)), pos)

    # --- HUD ---
    # Combo number + label
    num_txt = font_l.render(f"#{current + 1} / 8", True, (255, 220, 60))
    screen.blit(num_txt, (ox + 10, oy + 10))
    lbl_txt = font_m.render(COMBO_LABELS[current], True, (220, 220, 220))
    screen.blit(lbl_txt, (ox + 10, oy + 40))

    # Legend
    legend_lines = [
        ("Green = safe from both",     (80,  210, 100)),
        ("Blue  = Ice hit zone",        (100, 160, 240)),
        ("Purple= Lightning hit zone",  (180, 100, 240)),
    ]
    ly = oy + WINDOW_SIZE - 20 - len(legend_lines) * 18
    for text, color in legend_lines:
        screen.blit(font_s.render(text, True, color), (ox + 10, ly))
        ly += 18

    # Nav hint
    nav = font_s.render("← → to cycle combinations", True, (160, 160, 160))
    screen.blit(nav, nav.get_rect(right=ox + WINDOW_SIZE - 10, bottom=oy + WINDOW_SIZE - 10))

    # Mouse coordinates relative to arena center
    mx, my = pygame.mouse.get_pos()
    dx = mx - screen_cx
    dy = my - screen_cy
    coord_txt = font_m.render(f"X: {dx:+d}   Y: {dy:+d}", True, (255, 255, 255))
    screen.blit(coord_txt, coord_txt.get_rect(
        right=ox + WINDOW_SIZE - 10, top=oy + 10
    ))

    pygame.display.flip()

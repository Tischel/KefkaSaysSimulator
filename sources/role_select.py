import os
import pygame
from constants import (
    BACKGROUND_COLOR, ARENA_CENTER,
    FONT_NAME, FONT_SIZE_LARGE, FONT_SIZE_NORMAL, FONT_SIZE_SMALL,
)

_ASSETS = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets'))

_ROLES = [
    ('T1', 'Tank 1'),   ('T2', 'Tank 2'),
    ('H1', 'Healer 1'), ('H2', 'Healer 2'),
    ('M1', 'Melee 1'),  ('M2', 'Melee 2'),
    ('R1', 'Ranged 1'), ('R2', 'Ranged 2'),
]

_ICON_SIZE   = 72
_CELL_W      = 110
_CELL_H      = 118
_COLS        = 4
_GAP         = 14


def _make_font(name, size):
    font = pygame.font.SysFont(name, size)
    return font if font is not None else pygame.font.Font(None, size)


class RoleSelectScreen:
    def __init__(self):
        self._icons = {
            role: pygame.transform.smoothscale(
                pygame.image.load(os.path.join(_ASSETS, f'{role}.png')).convert_alpha(),
                (_ICON_SIZE, _ICON_SIZE),
            )
            for role, _ in _ROLES
        }
        self._font_title = _make_font(FONT_NAME, FONT_SIZE_LARGE)
        self._font_label = _make_font(FONT_NAME, FONT_SIZE_SMALL)
        self._hovered = None

    def _cell_rects(self, arena_offset):
        cx = ARENA_CENTER[0] + arena_offset[0]
        cy = ARENA_CENTER[1] + arena_offset[1]
        rows = len(_ROLES) // _COLS
        grid_w = _COLS * _CELL_W + (_COLS - 1) * _GAP
        grid_h = rows * _CELL_H + (rows - 1) * _GAP
        x0 = cx - grid_w // 2
        y0 = cy - grid_h // 2 + 30
        rects = []
        for i, (role, label) in enumerate(_ROLES):
            col = i % _COLS
            row = i // _COLS
            x = x0 + col * (_CELL_W + _GAP)
            y = y0 + row * (_CELL_H + _GAP)
            rects.append((role, label, pygame.Rect(x, y, _CELL_W, _CELL_H)))
        return rects

    def update(self, events, arena_offset=(0, 0)):
        cells = self._cell_rects(arena_offset)
        mouse_pos = pygame.mouse.get_pos()
        self._hovered = None
        for role, _, rect in cells:
            if rect.collidepoint(mouse_pos):
                self._hovered = role
                break
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for role, _, rect in cells:
                    if rect.collidepoint(event.pos):
                        return role
        return None

    def render(self, surface, arena_offset=(0, 0)):
        surface.fill(BACKGROUND_COLOR)

        cells = self._cell_rects(arena_offset)
        cx = ARENA_CENTER[0] + arena_offset[0]

        title = self._font_title.render("Select Your Role", True, (255, 255, 255))
        title_y = cells[0][2].top - title.get_height() - 20
        surface.blit(title, title.get_rect(centerx=cx, top=title_y))

        for role, label, rect in cells:
            hovered = role == self._hovered
            bg = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            bg.fill((80, 80, 80, 200) if hovered else (30, 30, 30, 180))
            surface.blit(bg, rect.topleft)
            if hovered:
                pygame.draw.rect(surface, (255, 255, 0), rect, 2)

            icon = self._icons[role]
            surface.blit(icon, icon.get_rect(centerx=rect.centerx, top=rect.top + 10))

            lbl = self._font_label.render(label, True, (255, 255, 255))
            surface.blit(lbl, lbl.get_rect(centerx=rect.centerx, bottom=rect.bottom - 8))

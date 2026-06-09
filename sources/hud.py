import os
import pygame
from constants import (
    ARENA_CENTER,
    ENEMY_LIST_WIDTH, ENEMY_LIST_HEIGHT, ENEMY_LIST_ROW_H,
    PARTY_LIST_WIDTH, PARTY_LIST_ROW_H, PARTY_LIST_ORDER, ROLE_NAMES,
    CAST_BAR_COLOR, CAST_BAR_BG_COLOR,
    FONT_NAME, FONT_SIZE_NORMAL, FONT_SIZE_SMALL,
)
from debuff import ICON_W, ICON_H

_ASSETS = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets'))


def _make_font(name, size):
    font = pygame.font.SysFont(name, size)
    return font if font is not None else pygame.font.Font(None, size)


def _make_bg(w, h, locked):
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 128) if locked else (0, 0, 0, 255))
    return surf


class EnemyList:
    def __init__(self):
        x = ARENA_CENTER[0] + 400
        y = ARENA_CENTER[1] - ENEMY_LIST_HEIGHT // 2
        self.rect = pygame.Rect(x, y, ENEMY_LIST_WIDTH, ENEMY_LIST_HEIGHT)
        self._is_dragging = False
        self._drag_offset = (0, 0)
        self._font = _make_font(FONT_NAME, FONT_SIZE_NORMAL)
        self._font_small = _make_font(FONT_NAME, FONT_SIZE_SMALL)
        self._bg_locked = _make_bg(ENEMY_LIST_WIDTH, ENEMY_LIST_HEIGHT, locked=True)
        self._bg_unlocked = _make_bg(ENEMY_LIST_WIDTH, ENEMY_LIST_HEIGHT, locked=False)

    def update(self, events, locked, arena_offset=(0, 0)):
        if locked:
            self._is_dragging = False
            return
        ox, oy = arena_offset
        screen_rect = self.rect.move(ox, oy)
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if screen_rect.collidepoint(event.pos):
                    self._is_dragging = True
                    self._drag_offset = (event.pos[0] - screen_rect.x, event.pos[1] - screen_rect.y)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._is_dragging = False
            elif event.type == pygame.MOUSEMOTION and self._is_dragging:
                self.rect.x = event.pos[0] - self._drag_offset[0] - ox
                self.rect.y = event.pos[1] - self._drag_offset[1] - oy

    def render(self, surface, active_casts, locked, arena_offset=(0, 0)):
        # active_casts: dict of {enemy_name: {'name': cast_name, 'progress': 0.0-1.0}}
        ox, oy = arena_offset
        screen_rect = self.rect.move(ox, oy)
        surface.blit(self._bg_locked if locked else self._bg_unlocked, screen_rect.topleft)

        pad = 8
        bar_h = 10
        bar_w = 140  # fixed cast bar width, right-aligned
        bar_section_x = screen_rect.right - pad - bar_w
        label_h = self._font_small.get_height()
        cast_content_h = label_h + 2 + bar_h
        cast_top_pad = (ENEMY_LIST_ROW_H - cast_content_h) // 2
        name_x = screen_rect.x + pad

        for i, enemy_name in enumerate(('Kefka', 'Neo Exdeath', 'Chaos')):
            row_y = screen_rect.y + pad + i * ENEMY_LIST_ROW_H
            cast = active_casts.get(enemy_name)
            name_surf = self._font.render(enemy_name, True, (255, 255, 255))
            name_y = row_y + (ENEMY_LIST_ROW_H - name_surf.get_height()) // 2
            surface.blit(name_surf, (name_x, name_y))
            if cast:
                label_surf = self._font_small.render(cast['name'], True, (255, 255, 255))
                label_y = row_y + cast_top_pad
                bar_y = label_y + label_h + 2
                surface.blit(label_surf, (bar_section_x, label_y))
                pygame.draw.rect(surface, CAST_BAR_BG_COLOR,
                                 (bar_section_x, bar_y, bar_w, bar_h))
                pygame.draw.rect(surface, CAST_BAR_COLOR,
                                 (bar_section_x, bar_y, int(bar_w * cast['progress']), bar_h))


class FpsCounter:
    def __init__(self):
        self._font = _make_font(FONT_NAME, FONT_SIZE_SMALL)

    def render(self, surface, fps):
        text = self._font.render(f"{fps:.0f} FPS", True, (255, 255, 255))
        surface.blit(text, text.get_rect(topright=(surface.get_width() - 10, 10)))


class Legend:
    _LINES = ["(ESC) Quit", "(R) Restart", "(U) Unlock/Lock HUD"]

    def __init__(self):
        self._font = _make_font(FONT_NAME, FONT_SIZE_SMALL)

    def render(self, surface):
        x, y = 10, 10
        for line in self._LINES:
            text = self._font.render(line, True, (255, 255, 255))
            surface.blit(text, (x, y))
            y += text.get_height() + 2


class PartyList:
    _ROLE_ICON_SIZE = 20
    _PAD = 6
    _ICON_GAP = 4
    _NAME_W = 62           # fixed width reserved for the name column
    _NAME_DEBUFF_GAP = 14  # margin between name column and first debuff
    _DEBUFF_GAP = 2        # gap between debuff icons
    _PLAYER_ROW_COLOR = (255, 255, 255, 30)

    def __init__(self, roles, player_role):
        self._roles = roles
        self._player_role = player_role
        self._role_icons = {}
        for role in roles:
            img = pygame.image.load(os.path.join(_ASSETS, f'{role}.png')).convert_alpha()
            self._role_icons[role] = pygame.transform.smoothscale(img, (self._ROLE_ICON_SIZE, self._ROLE_ICON_SIZE))
        h = len(roles) * PARTY_LIST_ROW_H + 2 * self._PAD
        x = -PARTY_LIST_WIDTH - 310
        y = ARENA_CENTER[1] - h // 2
        self.rect = pygame.Rect(x, y, PARTY_LIST_WIDTH, h)
        self._is_dragging = False
        self._drag_offset = (0, 0)
        self._font = _make_font(FONT_NAME, FONT_SIZE_SMALL)
        self._dur_font = _make_font(FONT_NAME, FONT_SIZE_SMALL - 2)
        self._bg_locked = _make_bg(PARTY_LIST_WIDTH, h, locked=True)
        self._bg_unlocked = _make_bg(PARTY_LIST_WIDTH, h, locked=False)
        self._highlight = pygame.Surface((PARTY_LIST_WIDTH, PARTY_LIST_ROW_H), pygame.SRCALPHA)
        self._highlight.fill(self._PLAYER_ROW_COLOR)

    def update(self, events, locked, arena_offset=(0, 0)):
        if locked:
            self._is_dragging = False
            return
        ox, oy = arena_offset
        screen_rect = self.rect.move(ox, oy)
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if screen_rect.collidepoint(event.pos):
                    self._is_dragging = True
                    self._drag_offset = (event.pos[0] - screen_rect.x, event.pos[1] - screen_rect.y)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._is_dragging = False
            elif event.type == pygame.MOUSEMOTION and self._is_dragging:
                self.rect.x = event.pos[0] - self._drag_offset[0] - ox
                self.rect.y = event.pos[1] - self._drag_offset[1] - oy

    def render(self, surface, locked, members, arena_offset=(0, 0)):
        # members: dict of {role: player_or_bot}
        ox, oy = arena_offset
        screen_rect = self.rect.move(ox, oy)
        surface.blit(self._bg_locked if locked else self._bg_unlocked, screen_rect.topleft)

        debuff_top_pad = (PARTY_LIST_ROW_H - ICON_H - self._dur_font.get_height() - 2) // 2

        for i, role in enumerate(self._roles):
            row_y = screen_rect.y + self._PAD + i * PARTY_LIST_ROW_H
            if role == self._player_role:
                surface.blit(self._highlight, (screen_rect.x, row_y))

            # Role icon (vertically centered)
            icon = self._role_icons[role]
            icon_y = row_y + (PARTY_LIST_ROW_H - self._ROLE_ICON_SIZE) // 2
            surface.blit(icon, (screen_rect.x + self._PAD, icon_y))

            # Role name (vertically centered)
            text = self._font.render(ROLE_NAMES.get(role, role), True, (255, 255, 255))
            text_y = row_y + (PARTY_LIST_ROW_H - text.get_height()) // 2
            name_x = screen_rect.x + self._PAD + self._ROLE_ICON_SIZE + self._ICON_GAP
            surface.blit(text, (name_x, text_y))

            # Debuffs
            member = members.get(role)
            if member is None:
                continue
            debuff_x = name_x + self._NAME_W + self._NAME_DEBUFF_GAP
            for debuff in sorted(member.debuffs, key=lambda d: d.sort_order):
                icon_surf = debuff.load_icon()
                dy = row_y + debuff_top_pad
                surface.blit(icon_surf, (debuff_x, dy))
                dur_text = debuff.duration_text
                if dur_text:
                    dur_surf = self._dur_font.render(dur_text, True, (255, 255, 255))
                    dur_x = debuff_x + (ICON_W - dur_surf.get_width()) // 2
                    surface.blit(dur_surf, (dur_x, dy + ICON_H + 2))
                debuff_x += ICON_W + self._DEBUFF_GAP

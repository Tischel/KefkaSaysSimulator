import pygame
from constants import (
    ARENA_CENTER,
    ENEMY_LIST_WIDTH, ENEMY_LIST_HEIGHT,
    CAST_DURATION, CAST_BAR_COLOR, CAST_BAR_BG_COLOR,
    FONT_NAME, FONT_SIZE_NORMAL, FONT_SIZE_SMALL,
)


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

    def render(self, surface, is_casting, cast_timer, locked, arena_offset=(0, 0)):
        ox, oy = arena_offset
        screen_rect = self.rect.move(ox, oy)
        surface.blit(self._bg_locked if locked else self._bg_unlocked, screen_rect.topleft)

        pad = 8
        x = screen_rect.x + pad
        y = screen_rect.y + pad

        name = self._font.render("Kefka", True, (255, 255, 255))

        if is_casting:
            attack_label = self._font_small.render("Mystery Magic", True, (255, 255, 255))
            bar_h = 10
            bar_area_h = attack_label.get_height() + 2 + bar_h
            name_y = y + max(0, (bar_area_h - name.get_height()) // 2)
            surface.blit(name, (x, name_y))

            bar_x = x + name.get_width() + 8
            bar_w = screen_rect.right - pad - bar_x
            surface.blit(attack_label, (bar_x, y))
            bar_y = y + attack_label.get_height() + 2
            progress = max(0.0, (CAST_DURATION - cast_timer) / CAST_DURATION)
            pygame.draw.rect(surface, CAST_BAR_BG_COLOR, (bar_x, bar_y, bar_w, bar_h))
            pygame.draw.rect(surface, CAST_BAR_COLOR, (bar_x, bar_y, int(bar_w * progress), bar_h))
        else:
            surface.blit(name, (x, y))


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

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


class Timer:
    _W = 100
    _H = 28

    def __init__(self, enemy_list):
        x = enemy_list.rect.centerx - self._W // 2
        y = enemy_list.rect.top - self._H - 4
        self.rect = pygame.Rect(x, y, self._W, self._H)
        self._elapsed = 0.0
        self._font = _make_font(FONT_NAME, FONT_SIZE_SMALL + 4)
        self._bg = _make_bg(self._W, self._H, locked=True)

    def reset(self):
        self._elapsed = 0.0

    def update(self, dt, paused=False):
        if not paused:
            self._elapsed += dt

    def render(self, surface, arena_offset=(0, 0)):
        ox, oy = arena_offset
        screen_rect = self.rect.move(ox, oy)
        surface.blit(self._bg, screen_rect.topleft)
        total_secs = int(self._elapsed)
        text = f"{total_secs // 60}:{total_secs % 60:02d}"
        text_surf = self._font.render(text, True, (255, 255, 255))
        surface.blit(text_surf, text_surf.get_rect(center=screen_rect.center))


class FpsCounter:
    def __init__(self):
        self._font = _make_font(FONT_NAME, FONT_SIZE_SMALL)

    def render(self, surface, fps):
        text = self._font.render(f"{fps:.0f} FPS", True, (255, 255, 255))
        surface.blit(text, text.get_rect(topright=(surface.get_width() - 10, 10)))


class Legend:
    _LINES = ["(ESC) Quit", "(R) Restart", "(U) Unlock/Lock HUD", "(T) Toggle fake debuffs help"]

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
    _TOOLTIP_W = 200
    _TOOLTIP_PAD = 6
    _TOOLTIP_OFFSET = (12, 12)

    def __init__(self, roles, player_role, chaos_left):
        self._roles = roles
        self._player_role = player_role
        self._role_icons = {}
        for role in roles:
            img = pygame.image.load(os.path.join(_ASSETS, f'{role}.png')).convert_alpha()
            self._role_icons[role] = pygame.transform.smoothscale(img, (self._ROLE_ICON_SIZE, self._ROLE_ICON_SIZE))
        h = len(roles) * PARTY_LIST_ROW_H + 2 * self._PAD
        x = chaos_left - 8 - PARTY_LIST_WIDTH
        y = ARENA_CENTER[1] - h // 2
        self.rect = pygame.Rect(x, y, PARTY_LIST_WIDTH, h)
        self._is_dragging = False
        self._drag_offset = (0, 0)
        self._font = _make_font(FONT_NAME, FONT_SIZE_SMALL)
        self._dur_font = _make_font(FONT_NAME, FONT_SIZE_SMALL - 2)
        self._tooltip_font = _make_font(FONT_NAME, FONT_SIZE_SMALL + 2)
        self._tooltip_desc_font = _make_font(FONT_NAME, FONT_SIZE_SMALL)
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

    def render(self, surface, locked, members, arena_offset=(0, 0), debug_mode=False):
        # members: dict of {role: player_or_bot}
        ox, oy = arena_offset
        screen_rect = self.rect.move(ox, oy)
        surface.blit(self._bg_locked if locked else self._bg_unlocked, screen_rect.topleft)

        debuff_top_pad = (PARTY_LIST_ROW_H - ICON_H - self._dur_font.get_height() - 2) // 2
        mouse_pos = pygame.mouse.get_pos()
        hovered_debuff = None

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
                    dur_color = (255, 60, 60) if (debug_mode and debuff.is_fake) else (255, 255, 255)
                    dur_surf = self._dur_font.render(dur_text, True, dur_color)
                    dur_x = debuff_x + (ICON_W - dur_surf.get_width()) // 2
                    surface.blit(dur_surf, (dur_x, dy + ICON_H + 2))
                if pygame.Rect(debuff_x, dy, ICON_W, ICON_H).collidepoint(mouse_pos):
                    hovered_debuff = debuff
                debuff_x += ICON_W + self._DEBUFF_GAP

        if hovered_debuff:
            self._draw_tooltip(surface, hovered_debuff, mouse_pos)

    @staticmethod
    def _wrap_text(font, text, max_width):
        words = text.split(' ')
        lines = []
        current = []
        for word in words:
            test = ' '.join(current + [word])
            if font.size(test)[0] <= max_width:
                current.append(word)
            else:
                if current:
                    lines.append(' '.join(current))
                current = [word]
        if current:
            lines.append(' '.join(current))
        return lines

    def _draw_tooltip(self, surface, debuff, cursor_pos):
        PAD = self._TOOLTIP_PAD
        W = self._TOOLTIP_W
        desc_lines = self._wrap_text(self._tooltip_desc_font, debuff.description, W - 2 * PAD)
        name_h = self._tooltip_font.get_height()
        line_h = self._tooltip_desc_font.get_height() + 1
        h = PAD + name_h + 4 + len(desc_lines) * line_h + PAD
        x = cursor_pos[0] + self._TOOLTIP_OFFSET[0]
        y = cursor_pos[1] + self._TOOLTIP_OFFSET[1]
        sw, sh = surface.get_size()
        if x + W > sw:
            x = cursor_pos[0] - W - 4
        if y + h > sh:
            y = cursor_pos[1] - h - 4
        bg = pygame.Surface((W, h), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 210))
        surface.blit(bg, (x, y))
        cy = y + PAD
        surface.blit(self._tooltip_font.render(debuff.name, True, (255, 255, 255)), (x + PAD, cy))
        cy += name_h + 4
        for line in desc_lines:
            surface.blit(self._tooltip_desc_font.render(line, True, (200, 200, 200)), (x + PAD, cy))
            cy += line_h


_MACRO_BUTTONS = [
    ('button_ice.png',       'Ice: REAL'),
    ('button_fake.png',      'Ice: FAKE'),
    ('button_thunder.png',   'Thunder: REAL'),
    ('button_fake.png',      'Thunder: FAKE'),
    ('button_fire.png',      'Fire: TWISTER'),
    ('button_fake.png',      'Fire: DONUT'),
    ('button_water.png',     'Water: DONUT'),
    ('button_fake.png',      'Water: TWISTER'),
    ('button_gaze.png',      'Gaze: REAL'),
    ('button_fake.png',      'Gaze: FAKE'),
    ('button_stillness.png', 'STILLNESS'),
    ('button_fake.png',      'MOTION'),
    ('button_spread.png',    'SPREAD'),
    ('button_stack.png',     'STACK'),
]


class MacroOutput:
    _W = 200
    _H = 350
    _PAD = 6
    _LINE_GAP = 2
    _CLEAR_BTN_W = 50
    _CLEAR_BTN_H = 22

    def __init__(self, enemy_list):
        x = enemy_list.rect.x
        y = enemy_list.rect.bottom + 8
        self.rect = pygame.Rect(x, y, self._W, self._H)
        self._lines = []
        self._scroll_offset = 0
        self._font = _make_font(FONT_NAME, FONT_SIZE_NORMAL)
        self._line_h = self._font.get_height() + self._LINE_GAP
        self._bg_locked = _make_bg(self._W, self._H, locked=True)
        self._bg_unlocked = _make_bg(self._W, self._H, locked=False)
        self._is_dragging = False
        self._drag_offset = (0, 0)

    def add_line(self, text):
        self._lines.append(text)
        self._scroll_offset = self._max_scroll()

    def clear(self):
        self._lines.clear()
        self._scroll_offset = 0

    def _text_h(self):
        return self._H - 2 * self._PAD - self._CLEAR_BTN_H - 4

    def _max_scroll(self):
        return max(0, len(self._lines) * self._line_h - self._text_h())

    def update(self, events, locked, arena_offset=(0, 0)):
        ox, oy = arena_offset
        screen_rect = self.rect.move(ox, oy)
        clear_rect = pygame.Rect(
            screen_rect.right - self._PAD - self._CLEAR_BTN_W,
            screen_rect.bottom - self._PAD - self._CLEAR_BTN_H,
            self._CLEAR_BTN_W, self._CLEAR_BTN_H,
        )
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if clear_rect.collidepoint(event.pos):
                    self._lines.clear()
                    self._scroll_offset = 0
                elif screen_rect.collidepoint(event.pos) and not locked:
                    self._is_dragging = True
                    self._drag_offset = (event.pos[0] - screen_rect.x,
                                         event.pos[1] - screen_rect.y)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._is_dragging = False
            elif event.type == pygame.MOUSEMOTION and self._is_dragging:
                self.rect.x = event.pos[0] - self._drag_offset[0] - ox
                self.rect.y = event.pos[1] - self._drag_offset[1] - oy
            elif event.type == pygame.MOUSEWHEEL:
                if screen_rect.collidepoint(pygame.mouse.get_pos()):
                    self._scroll_offset = max(0, min(
                        self._max_scroll(),
                        self._scroll_offset - event.y * self._line_h,
                    ))

    def render(self, surface, locked, arena_offset=(0, 0)):
        ox, oy = arena_offset
        screen_rect = self.rect.move(ox, oy)
        surface.blit(self._bg_locked if locked else self._bg_unlocked, screen_rect.topleft)

        text_area = pygame.Rect(
            screen_rect.x + self._PAD,
            screen_rect.y + self._PAD,
            self._W - 2 * self._PAD,
            self._text_h(),
        )
        old_clip = surface.get_clip()
        surface.set_clip(text_area)
        for i, line in enumerate(self._lines):
            y = text_area.y + i * self._line_h - self._scroll_offset
            if y + self._line_h <= text_area.y:
                continue
            if y >= text_area.bottom:
                break
            surface.blit(self._font.render(line, True, (255, 255, 255)), (text_area.x, y))
        surface.set_clip(old_clip)

        clear_rect = pygame.Rect(
            screen_rect.right - self._PAD - self._CLEAR_BTN_W,
            screen_rect.bottom - self._PAD - self._CLEAR_BTN_H,
            self._CLEAR_BTN_W, self._CLEAR_BTN_H,
        )
        pygame.draw.rect(surface, (60, 60, 60), clear_rect)
        pygame.draw.rect(surface, (150, 150, 150), clear_rect, 1)
        clear_label = self._font.render('Clear', True, (255, 255, 255))
        surface.blit(clear_label, clear_label.get_rect(center=clear_rect.center))


class MacroButtons:
    _BTN_SIZE = 38
    _BTN_MARGIN = 4
    _PAD = 4
    _COLS = 2
    _ROWS = 7

    def __init__(self, macro_output):
        self._macro_output = macro_output
        w = 2 * self._PAD + self._COLS * self._BTN_SIZE + (self._COLS - 1) * self._BTN_MARGIN
        h = 2 * self._PAD + self._ROWS * self._BTN_SIZE + (self._ROWS - 1) * self._BTN_MARGIN
        self.rect = pygame.Rect(macro_output.rect.right + 8, macro_output.rect.y, w, h)
        self._is_dragging = False
        self._drag_offset = (0, 0)
        self._bg_locked = _make_bg(w, h, locked=True)
        self._bg_unlocked = _make_bg(w, h, locked=False)
        self._buttons = []
        for i, (fname, output) in enumerate(_MACRO_BUTTONS):
            col = i % self._COLS
            row = i // self._COLS
            bx = self._PAD + col * (self._BTN_SIZE + self._BTN_MARGIN)
            by = self._PAD + row * (self._BTN_SIZE + self._BTN_MARGIN)
            img = pygame.image.load(os.path.join(_ASSETS, fname)).convert_alpha()
            img = pygame.transform.smoothscale(img, (self._BTN_SIZE, self._BTN_SIZE))
            self._buttons.append((img, pygame.Rect(bx, by, self._BTN_SIZE, self._BTN_SIZE), output))

    def update(self, events, locked, arena_offset=(0, 0)):
        ox, oy = arena_offset
        screen_rect = self.rect.move(ox, oy)
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked_btn = False
                for _, local_rect, output in self._buttons:
                    if local_rect.move(screen_rect.x, screen_rect.y).collidepoint(event.pos):
                        self._macro_output.add_line(output)
                        clicked_btn = True
                        break
                if not clicked_btn and not locked and screen_rect.collidepoint(event.pos):
                    self._is_dragging = True
                    self._drag_offset = (event.pos[0] - screen_rect.x,
                                         event.pos[1] - screen_rect.y)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._is_dragging = False
            elif event.type == pygame.MOUSEMOTION and self._is_dragging:
                self.rect.x = event.pos[0] - self._drag_offset[0] - ox
                self.rect.y = event.pos[1] - self._drag_offset[1] - oy

    def render(self, surface, locked, arena_offset=(0, 0)):
        ox, oy = arena_offset
        screen_rect = self.rect.move(ox, oy)
        surface.blit(self._bg_locked if locked else self._bg_unlocked, screen_rect.topleft)
        for img, local_rect, _ in self._buttons:
            surface.blit(img, local_rect.move(screen_rect.x, screen_rect.y).topleft)

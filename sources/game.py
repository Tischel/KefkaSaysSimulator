import pygame
from enum import Enum
from constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    INITIAL_WAIT, CAST_DURATION, ATTACK_DURATION, COOLDOWN_DURATION,
    ATTACK_ALPHA_START, TELEGRAPH_ALPHA,
    FONT_NAME, FONT_SIZE_LARGE, FONT_SIZE_NORMAL,
)
from arena import Arena
from player import Player
from attacks import LightningAttack, IceAttack
from hud import EnemyList, _make_font


class GameState(Enum):
    WAITING = 0
    CASTING = 1
    RESOLVING = 2
    COOLDOWN = 3
    GAME_OVER = 4


class Game:
    def __init__(self):
        self.arena = Arena()
        self.player = Player()
        self.enemy_list = EnemyList()
        self.attacks = []
        self.state = GameState.WAITING
        self.state_timer = INITIAL_WAIT
        self.player_was_hit = False
        self.hud_locked = True
        self._font_large = _make_font(FONT_NAME, FONT_SIZE_LARGE)
        self._font_normal = _make_font(FONT_NAME, FONT_SIZE_NORMAL)
        self._overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 153))

    def _generate_attacks(self):
        self.attacks = [LightningAttack(), IceAttack()]

    def _check_hits(self):
        point = self.player.get_center()
        for attack in self.attacks:
            if attack.is_hit(point):
                self.player_was_hit = True
                return

    def _attack_alpha(self):
        t = max(0.0, self.state_timer) / ATTACK_DURATION
        return int(ATTACK_ALPHA_START * t)

    def _reset(self):
        self.player = Player()
        self.attacks = []
        self.player_was_hit = False
        self.state = GameState.WAITING
        self.state_timer = INITIAL_WAIT

    def update(self, dt, keys, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self._reset()
                    return
                if event.key == pygame.K_u:
                    self.hud_locked = not self.hud_locked

        self.enemy_list.update(events, self.hud_locked)

        if self.state == GameState.WAITING:
            self.state_timer -= dt
            self.player.update(dt, keys)
            if self.state_timer <= 0:
                self._generate_attacks()
                self.state = GameState.CASTING
                self.state_timer = CAST_DURATION

        elif self.state == GameState.CASTING:
            self.state_timer -= dt
            self.player.update(dt, keys)
            if self.state_timer <= 0:
                self._check_hits()
                if self.player_was_hit:
                    self.attacks = []
                    self.state = GameState.GAME_OVER
                else:
                    self.state = GameState.RESOLVING
                    self.state_timer = ATTACK_DURATION

        elif self.state == GameState.RESOLVING:
            self.state_timer -= dt
            self.player.update(dt, keys)
            if self.state_timer <= 0:
                self.attacks = []
                self.state = GameState.COOLDOWN
                self.state_timer = COOLDOWN_DURATION

        elif self.state == GameState.COOLDOWN:
            self.state_timer -= dt
            self.player.update(dt, keys)
            if self.state_timer <= 0:
                self._generate_attacks()
                self.state = GameState.CASTING
                self.state_timer = CAST_DURATION

    def render(self, surface, arena_offset=(0, 0)):
        self.arena.render(surface, arena_offset)

        for attack in self.attacks:
            if self.state == GameState.CASTING:
                attack.render(surface, telegraphing=True, alpha=TELEGRAPH_ALPHA, offset=arena_offset)
            elif self.state == GameState.RESOLVING:
                attack.render(surface, telegraphing=False, alpha=self._attack_alpha(), offset=arena_offset)

        self.player.render(surface, arena_offset)

        is_casting = self.state == GameState.CASTING
        self.enemy_list.render(surface, is_casting, self.state_timer, self.hud_locked)

        if self.state == GameState.GAME_OVER:
            self._render_game_over(surface, arena_offset)

    def _render_game_over(self, surface, arena_offset=(0, 0)):
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 153))
        surface.blit(overlay, (0, 0))
        cx = arena_offset[0] + WINDOW_WIDTH // 2
        cy = arena_offset[1] + WINDOW_HEIGHT // 2
        go_text = self._font_large.render("GAME OVER", True, (255, 255, 255))
        restart_text = self._font_normal.render("Press R to restart", True, (255, 255, 255))
        surface.blit(go_text, go_text.get_rect(center=(cx, cy - 30)))
        surface.blit(restart_text, restart_text.get_rect(center=(cx, cy + 30)))

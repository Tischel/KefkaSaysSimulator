import random
import pygame
from enum import Enum
from constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    ARENA_CENTER, ARENA_RADIUS,
    INITIAL_WAIT, CAST_DURATION, ATTACK_DURATION, COOLDOWN_DURATION,
    ATTACK_ALPHA_START, TELEGRAPH_ALPHA,
    FONT_NAME, FONT_SIZE_LARGE, FONT_SIZE_NORMAL,
    SAFE_SPOTS,
)
from arena import Arena
from player import Player
from attacks import LightningAttack, IceAttack
from bot import Bot, circle_positions, CIRCLE_ORDER
from hud import EnemyList, _make_font


class GameState(Enum):
    WAITING = 0
    CASTING = 1
    RESOLVING = 2
    COOLDOWN = 3
    GAME_OVER = 4


class Game:
    def __init__(self, role='T1'):
        self._role = role
        self.arena = Arena()
        positions = circle_positions()
        self._player_start = positions[role]
        self.player = Player(role, self._player_start)
        self.bots = [Bot(r, positions[r]) for r in CIRCLE_ORDER if r != role]
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
        self._attack_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        self._attack_mask = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        self._attack_mask.fill((0, 0, 0, 0))
        pygame.draw.circle(self._attack_mask, (255, 255, 255, 255), ARENA_CENTER, ARENA_RADIUS)

    def _generate_attacks(self):
        lightning = LightningAttack()
        ice = IceAttack()
        self.attacks = [lightning, ice]
        key = (lightning.angle, lightning.effective_pair_idx, ice.effective_pair_idx)
        spot = SAFE_SPOTS[key]
        for bot in self.bots:
            s = random.choice(spot) if isinstance(spot, list) else spot
            base_dest = (ARENA_CENTER[0] + s[0], ARENA_CENTER[1] + s[1])
            bot.set_destination(base_dest)

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
        self.player = Player(self._role, self._player_start)
        for bot in self.bots:
            bot.reset()
        self.attacks = []
        self.player_was_hit = False
        self.state = GameState.WAITING
        self.state_timer = INITIAL_WAIT

    def update(self, dt, keys, events, arena_offset=(0, 0)):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self._reset()
                    return
                if event.key == pygame.K_u:
                    self.hud_locked = not self.hud_locked

        self.enemy_list.update(events, self.hud_locked, arena_offset)

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
            for attack in self.attacks:
                attack.update(dt)
            for bot in self.bots:
                bot.update(dt, self.state_timer)
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

        if self.attacks:
            self._attack_surf.fill((0, 0, 0, 0))
            for attack in self.attacks:
                if self.state == GameState.CASTING:
                    attack.render(self._attack_surf, telegraphing=True, alpha=TELEGRAPH_ALPHA, offset=(0, 0))
                elif self.state == GameState.RESOLVING:
                    attack.render(self._attack_surf, telegraphing=False, alpha=self._attack_alpha(), offset=(0, 0))
            if self.state == GameState.CASTING:
                for attack in self.attacks:
                    attack.render_ring(self._attack_surf, (0, 0))
            self._attack_surf.blit(self._attack_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(self._attack_surf, arena_offset)

        for bot in self.bots:
            bot.render(surface, arena_offset)
        self.player.render(surface, arena_offset)

        is_casting = self.state == GameState.CASTING
        self.enemy_list.render(surface, is_casting, self.state_timer, self.hud_locked, arena_offset)

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

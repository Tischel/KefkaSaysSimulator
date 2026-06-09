import random
import pygame
from enum import Enum
from constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    ARENA_CENTER, ARENA_RADIUS,
    ATTACK_DURATION, ATTACK_ALPHA_START, TELEGRAPH_ALPHA,
    FONT_NAME, FONT_SIZE_LARGE, FONT_SIZE_NORMAL,
    SAFE_SPOTS, PARTY_LIST_ORDER, SUPPORTS, DPS, TIMELINE,
    ICE_RING_COLOR,
)
from arena import Arena
from player import Player
from attacks import LightningAttack, IceAttack, RingOnlyAttack
from bot import Bot, circle_positions, CIRCLE_ORDER
from debuff import Debuff
from enemies import Enemies
from hud import EnemyList, PartyList, _make_font


class GameState(Enum):
    RUNNING = 0
    GAME_OVER = 1


class _ActiveCast:
    def __init__(self, cast_name, duration):
        self.cast_name = cast_name
        self.duration = duration
        self.elapsed = 0.0

    def update(self, dt):
        self.elapsed = min(self.elapsed + dt, self.duration)

    @property
    def progress(self):
        return self.elapsed / self.duration if self.duration > 0 else 1.0

    @property
    def is_done(self):
        return self.elapsed >= self.duration


class _AttackWrapper:
    def __init__(self, attack, trigger_time):
        self.attack = attack
        self.trigger_time = trigger_time
        self.hit_elapsed = 0.0
        self.triggered = False

    def update(self, dt, elapsed):
        self.attack.update(dt)
        if self.triggered:
            self.hit_elapsed += dt

    @property
    def is_done(self):
        return self.triggered and self.hit_elapsed >= ATTACK_DURATION


def _attack_alpha(hit_elapsed):
    t = max(0.0, (ATTACK_DURATION - hit_elapsed)) / ATTACK_DURATION
    return int(ATTACK_ALPHA_START * t)


class Game:
    def __init__(self, role='T1'):
        self._role = role
        self.arena = Arena()
        positions = circle_positions()
        self._player_start = positions[role]
        self.player = Player(role, self._player_start)
        self.bots = [Bot(r, positions[r]) for r in CIRCLE_ORDER if r != role]
        self._members = {role: self.player}
        for bot in self.bots:
            self._members[bot.role] = bot
        self.enemies = Enemies()
        self.enemy_list = EnemyList()
        self.party_list = PartyList(PARTY_LIST_ORDER, role)
        self.state = GameState.RUNNING
        self.player_was_hit = False
        self._font_large = _make_font(FONT_NAME, FONT_SIZE_LARGE)
        self._font_normal = _make_font(FONT_NAME, FONT_SIZE_NORMAL)
        self._attack_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        self._attack_mask = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        self._attack_mask.fill((0, 0, 0, 0))
        pygame.draw.circle(self._attack_mask, (255, 255, 255, 255), ARENA_CENTER, ARENA_RADIUS)
        self.hud_locked = True
        self._elapsed = 0.0
        self._timeline_idx = 0
        self._active_casts = {}   # caster_name → _ActiveCast
        self._attack_wrappers = []
        self._pending_actions = []  # (trigger_time, action_type, is_fake)

    # ------------------------------------------------------------------
    # Timeline
    # ------------------------------------------------------------------

    def _process_timeline(self):
        while self._timeline_idx < len(TIMELINE):
            t, caster, cast_name, duration, action = TIMELINE[self._timeline_idx]
            if self._elapsed < t:
                break
            self._timeline_idx += 1
            self._active_casts[caster] = _ActiveCast(cast_name, duration)
            if action == 'mystery_magic':
                lightning = LightningAttack()
                ice = IceAttack()
                key = (lightning.angle, lightning.effective_pair_idx, ice.effective_pair_idx)
                spot = SAFE_SPOTS[key]
                for bot in self.bots:
                    s = random.choice(spot) if isinstance(spot, list) else spot
                    base_dest = (ARENA_CENTER[0] + s[0], ARENA_CENTER[1] + s[1])
                    bot.set_destination(base_dest)
                trigger = t + duration
                self._attack_wrappers.append(_AttackWrapper(lightning, trigger))
                self._attack_wrappers.append(_AttackWrapper(ice, trigger))
            elif action in ('neo_debuffs_1', 'neo_debuffs_2', 'neo_debuffs_3'):
                is_fake = random.choice([True, False])
                self._pending_actions.append((t + duration, action, is_fake))
                nx, ny = self.enemies.neo_center
                neo_offset = (nx - ARENA_CENTER[0], ny - ARENA_CENTER[1])
                ring = RingOnlyAttack(neo_offset, ICE_RING_COLOR)
                self._attack_wrappers.append(_AttackWrapper(ring, t + duration))
            elif action in ('chaos_tsunami', 'chaos_entropy'):
                is_fake = random.choice([True, False])
                self._pending_actions.append((t + duration, action, is_fake))
                cx, cy = self.enemies.chaos_center
                chaos_offset = (cx - ARENA_CENTER[0], cy - ARENA_CENTER[1])
                ring = RingOnlyAttack(chaos_offset, ICE_RING_COLOR)
                self._attack_wrappers.append(_AttackWrapper(ring, t + duration))

    def _fire_pending_actions(self):
        remaining = []
        for (trigger_time, action, is_fake) in self._pending_actions:
            if self._elapsed >= trigger_time:
                self._apply_action(action, is_fake)
            else:
                remaining.append((trigger_time, action, is_fake))
        self._pending_actions = remaining

    def _apply_action(self, action, is_fake):
        supports = SUPPORTS[:]
        dps = DPS[:]

        if action == 'neo_debuffs_1':
            random.shuffle(supports)
            random.shuffle(dps)
            # FL, CW, CS+AB51, AB76 — one of each per group
            self._add(supports[0], Debuff('forked_lightning',  51.0, is_fake))
            self._add(supports[1], Debuff('compressed_water',  51.0, is_fake))
            self._add(supports[2], Debuff('cursed_shriek',     60.0, is_fake))
            self._add(supports[2], Debuff('acceleration_bomb', 51.0, is_fake))
            self._add(supports[3], Debuff('acceleration_bomb', 76.0, is_fake))
            self._add(dps[0], Debuff('forked_lightning',  51.0, is_fake))
            self._add(dps[1], Debuff('compressed_water',  51.0, is_fake))
            self._add(dps[2], Debuff('cursed_shriek',     60.0, is_fake))
            self._add(dps[2], Debuff('acceleration_bomb', 51.0, is_fake))
            self._add(dps[3], Debuff('acceleration_bomb', 76.0, is_fake))

        elif action == 'neo_debuffs_2':
            fl_cw = [r for r in supports if self._has(r, 'forked_lightning') or self._has(r, 'compressed_water')]
            ab_s  = [r for r in supports if self._has(r, 'acceleration_bomb')]
            fl_cw_d = [r for r in dps if self._has(r, 'forked_lightning') or self._has(r, 'compressed_water')]
            ab_d  = [r for r in dps if self._has(r, 'acceleration_bomb')]
            random.shuffle(fl_cw); random.shuffle(ab_s)
            random.shuffle(fl_cw_d); random.shuffle(ab_d)
            # fl_cw supports get AB
            self._add(fl_cw[0], Debuff('acceleration_bomb', 36.0, is_fake))
            self._add(fl_cw[1], Debuff('cursed_shriek',     69.0, is_fake))
            self._add(fl_cw[1], Debuff('acceleration_bomb', 61.0, is_fake))
            # ab supports get FL or CW
            self._add(ab_s[0], Debuff('forked_lightning',  61.0, is_fake))
            self._add(ab_s[1], Debuff('compressed_water',  61.0, is_fake))
            # same for DPS
            self._add(fl_cw_d[0], Debuff('acceleration_bomb', 36.0, is_fake))
            self._add(fl_cw_d[1], Debuff('cursed_shriek',     69.0, is_fake))
            self._add(fl_cw_d[1], Debuff('acceleration_bomb', 61.0, is_fake))
            self._add(ab_d[0], Debuff('forked_lightning',  61.0, is_fake))
            self._add(ab_d[1], Debuff('compressed_water',  61.0, is_fake))

        elif action == 'neo_debuffs_3':
            random.shuffle(supports); random.shuffle(dps)
            bd_roles = supports[:2] + dps[:2]
            af_roles = supports[2:] + dps[2:]
            for r in bd_roles:
                self._add(r, Debuff('beyond_death', 15.0, is_fake))
            for r in af_roles:
                self._add(r, Debuff('allagan_field', 15.0, is_fake))
            all_roles = supports + dps
            for r in all_roles:
                wound = 'white_wound' if random.random() < 0.5 else 'black_wound'
                self._add(r, Debuff(wound, None, is_fake))

        elif action == 'chaos_tsunami':
            for r in (supports + dps):
                self._add(r, Debuff('dynamic_fluid', 84.0, is_fake))

        elif action == 'chaos_entropy':
            for r in (supports + dps):
                self._add(r, Debuff('entropy', 45.0, is_fake))

    def _add(self, role, debuff):
        member = self._members.get(role)
        if member:
            member.debuffs.append(debuff)
            member.debuffs.sort(key=lambda d: d.sort_order)

    def _has(self, role, debuff_type):
        member = self._members.get(role)
        return member is not None and any(d.debuff_type == debuff_type for d in member.debuffs)

    # ------------------------------------------------------------------
    # Update / Render
    # ------------------------------------------------------------------

    def _reset(self):
        self.player = Player(self._role, self._player_start)
        self._members[self._role] = self.player
        for bot in self.bots:
            bot.reset()
        self.state = GameState.RUNNING
        self.player_was_hit = False
        self._elapsed = 0.0
        self._timeline_idx = 0
        self._active_casts = {}
        self._attack_wrappers = []
        self._pending_actions = []

    def update(self, dt, keys, events, arena_offset=(0, 0)):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self._reset()
                    return
                if event.key == pygame.K_u:
                    self.hud_locked = not self.hud_locked

        self.enemy_list.update(events, self.hud_locked, arena_offset)
        self.party_list.update(events, self.hud_locked, arena_offset)

        if self.state == GameState.GAME_OVER:
            return

        self._elapsed += dt
        self._process_timeline()
        self._fire_pending_actions()

        # Update active casts; remove completed ones
        for caster, cast in list(self._active_casts.items()):
            cast.update(dt)
            if cast.is_done:
                del self._active_casts[caster]

        # Update attack wrappers; trigger at hit time
        for w in self._attack_wrappers:
            w.update(dt, self._elapsed)
            if not w.triggered and self._elapsed >= w.trigger_time:
                w.triggered = True
                if w.attack.is_hit(self.player.get_center()):
                    self.player_was_hit = True
                    self.state = GameState.GAME_OVER
        self._attack_wrappers = [w for w in self._attack_wrappers if not w.is_done]

        # Move players
        self.player.update(dt, keys)
        kefka_cast = self._active_casts.get('Kefka')
        kefka_remaining = (kefka_cast.duration - kefka_cast.elapsed) if kefka_cast else 0.0
        for bot in self.bots:
            bot.update(dt, kefka_remaining)

        # Tick debuffs
        self.player.update_debuffs(dt)
        for bot in self.bots:
            bot.update_debuffs(dt)

    def _build_active_casts_hud(self):
        result = {}
        for caster, cast in self._active_casts.items():
            result[caster] = {'name': cast.cast_name, 'progress': cast.progress}
        return result

    def render(self, surface, arena_offset=(0, 0)):
        self.arena.render(surface, arena_offset)

        if self._attack_wrappers:
            self._attack_surf.fill((0, 0, 0, 0))
            for w in self._attack_wrappers:
                if not w.triggered:
                    w.attack.render(self._attack_surf, telegraphing=True,
                                    alpha=TELEGRAPH_ALPHA, offset=(0, 0))
                else:
                    w.attack.render(self._attack_surf, telegraphing=False,
                                    alpha=_attack_alpha(w.hit_elapsed), offset=(0, 0))
            self._attack_surf.blit(self._attack_mask, (0, 0),
                                   special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(self._attack_surf, arena_offset)

        self.enemies.render(surface, arena_offset)

        if self._attack_wrappers:
            for w in self._attack_wrappers:
                if not w.triggered:
                    w.attack.render_ring(surface, arena_offset)

        for bot in self.bots:
            bot.render(surface, arena_offset)
        self.player.render(surface, arena_offset)

        self.enemy_list.render(surface, self._build_active_casts_hud(),
                               self.hud_locked, arena_offset)
        self.party_list.render(surface, self.hud_locked, self._members, arena_offset)

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

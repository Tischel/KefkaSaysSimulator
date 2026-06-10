import math
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
    BOT_SUPPORTS_SPREAD, BOT_DPS_SPREAD, BOT_SUPPORTS_STACK, BOT_DPS_STACK,
    BOT_WATER_FIRE_BAIT,
    BOT_SUPPORT_GAZE_REAL, BOT_DPS_GAZE_REAL, BOT_SUPPORT_GAZE_FAKE, BOT_DPS_GAZE_FAKE,
    BOT_PARTY_GAZE_REAL, BOT_TANK_GAZE_FAKE, BOT_PARTY_GAZE_FAKE,
    TT_GAZE_SPOTS,
)
from arena import Arena
from player import Player
from attacks import LightningAttack, IceAttack, RingOnlyAttack, AntilightAttack, EntropyAttack, DynamicFluidAttack
from bot import Bot, circle_positions, CIRCLE_ORDER
from debuff import Debuff
from enemies import Enemies
from hud import EnemyList, PartyList, MacroOutput, MacroButtons, Timer, _make_font


class GameState(Enum):
    RUNNING = 0
    GAME_OVER = 1
    VICTORY = 2


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
    def __init__(self, attack, trigger_time, shape_start_time=None, skip_hit_check=False):
        self.attack = attack
        self.trigger_time = trigger_time
        self.shape_start_time = shape_start_time  # shapes hidden until this elapsed time
        self.skip_hit_check = skip_hit_check
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
    def __init__(self, role='T1', start_time=0.0):
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
        self.party_list = PartyList(PARTY_LIST_ORDER, role, self.enemies.chaos_rect.left)
        self.macro_output = MacroOutput(self.enemy_list)
        self.macro_buttons = MacroButtons(self.macro_output)
        self.timer = Timer(self.enemy_list)
        self.state = GameState.RUNNING
        self.player_was_hit = False
        self._font_large = _make_font(FONT_NAME, FONT_SIZE_LARGE)
        self._font_normal = _make_font(FONT_NAME, FONT_SIZE_NORMAL)
        self._attack_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        self._attack_mask = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        self._attack_mask.fill((0, 0, 0, 0))
        pygame.draw.circle(self._attack_mask, (255, 255, 255, 255), ARENA_CENTER, ARENA_RADIUS)
        self.hud_locked = True
        self._show_fake_help = False
        self._start_time = start_time
        self._elapsed = start_time
        self._timeline_idx = 0
        self._active_casts = {}   # caster_name → _ActiveCast
        self._attack_wrappers = []
        self._pending_actions = []  # (trigger_time, action_type, is_fake)
        self._chaos_queue = None
        self._chaos_cast_count = 0
        self._add_correction = 0.0
        self._player_allagan_original_wound = None
        self._player_beyond_death_original_wound = None
        self._thrumming_thunder_attack = None
        self._blizzard_attack = None
        self._mana_release_lightning = None
        self._mana_release_ice = None
        self._mana_release_safe_spot = None
        self._debuffs_1_fl_roles = set()
        self._debuffs_1_cw_roles = set()
        self._debuffs_1_cs_roles = set()
        self._debuffs_2_fl_roles = set()
        self._debuffs_2_cw_roles = set()
        self._debuffs_2_cs_roles = set()
        self._dynamic_fluid_is_fake = None
        self._loss_reason = ""
        self._fov_timer = 0.0
        self._fov_facing = pygame.Vector2(0, -1)
        self._fl_cw_hit_circles = []
        self._ab_window_active = False
        self._ab_window_end = 0.0
        self._ab_is_fake = False
        self._ab_violated = False
        self._ab_stationary_dur = 0.0
        self._entropy_is_fake = None

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
                if action == 'neo_debuffs_2':
                    # 6s before 2nd FL/CW expires; 5s before 2nd CS expires
                    self._pending_actions.append((t + duration + 55.0, 'fl_cw_2_move', None))
                    self._pending_actions.append((t + duration + 64.0, 'cs_2_gaze',    None))
                nx, ny = self.enemies.neo_center
                neo_offset = (nx - ARENA_CENTER[0], ny - ARENA_CENTER[1])
                ring = RingOnlyAttack(neo_offset, ICE_RING_COLOR, is_fake)
                self._attack_wrappers.append(_AttackWrapper(ring, t + duration))
            elif action in ('chaos_tsunami', 'chaos_entropy'):
                if self._chaos_queue is None:
                    self._chaos_queue = ['chaos_tsunami', 'chaos_entropy']
                    random.shuffle(self._chaos_queue)
                actual_action = self._chaos_queue.pop(0)
                actual_cast_name = 'Tsunami' if actual_action == 'chaos_tsunami' else 'Inferno'
                self._active_casts[caster] = _ActiveCast(actual_cast_name, duration)
                is_first_cast = len(self._chaos_queue) == 1
                if actual_action == 'chaos_tsunami':
                    debuff_dur = 84.0 if is_first_cast else 69.0
                else:
                    debuff_dur = 60.0 if is_first_cast else 45.0
                bait_offset = debuff_dur - 5.0
                is_fake = random.choice([True, False])
                self._pending_actions.append((t + duration, actual_action, is_fake))
                if actual_action == 'chaos_entropy':
                    self._pending_actions.append((t + duration + bait_offset, 'entropy_bait', None))
                elif actual_action == 'chaos_tsunami':
                    self._pending_actions.append((t + duration + bait_offset, 'df_bait', None))
                cx, cy = self.enemies.chaos_center
                chaos_offset = (cx - ARENA_CENTER[0], cy - ARENA_CENTER[1])
                ring = RingOnlyAttack(chaos_offset, ICE_RING_COLOR, is_fake)
                self._attack_wrappers.append(_AttackWrapper(ring, t + duration))
            elif action == 'flood_of_naught':
                is_fake = random.choice([True, False])
                self._pending_actions.append((t + duration, action, is_fake))
                nx, ny = self.enemies.neo_center
                neo_offset = (nx - ARENA_CENTER[0], ny - ARENA_CENTER[1])
                ring = RingOnlyAttack(neo_offset, ICE_RING_COLOR, is_fake)
                self._attack_wrappers.append(_AttackWrapper(ring, t + duration))
                neo_rect = self.enemies.neo_rect
                sides = ['west', 'east']
                random.shuffle(sides)
                white_atk = AntilightAttack('white', sides[0], neo_rect, is_fake)
                black_atk = AntilightAttack('black', sides[1], neo_rect, is_fake)
                self._attack_wrappers.append(_AttackWrapper(white_atk, t + duration))
                self._attack_wrappers.append(_AttackWrapper(black_atk, t + duration))
                white_side = white_atk._hit_side()
                black_side = black_atk._hit_side()
                for bot in self.bots:
                    has_allagan = any(d.debuff_type == 'allagan_field' for d in bot.debuffs)
                    has_white_w = any(d.debuff_type == 'white_wound'   for d in bot.debuffs)
                    if has_allagan:
                        target_side = black_side if has_white_w else white_side
                    else:  # beyond_death
                        target_side = white_side if has_white_w else black_side
                    dx = -50 if target_side == 'west' else 50
                    bot.set_destination((ARENA_CENTER[0] + dx, ARENA_CENTER[1]),
                                        time_to_hit=duration)
            elif action == 'thrumming_thunder':
                lightning = LightningAttack()
                self._thrumming_thunder_attack = lightning
                self._attack_wrappers.append(_AttackWrapper(lightning, t + duration))
                self._pending_actions.append((t, 'tt_gaze', None))
            elif action == 'blizzard_blowout':
                ice = IceAttack()
                self._blizzard_attack = ice
                # no lightning present — pick any lightning combo to look up an ice-safe spot
                key = (random.choice([45, -45]), random.randint(0, 1), ice.effective_pair_idx)
                spot = SAFE_SPOTS[key]
                fl_cw_2_roles = self._debuffs_2_fl_roles | self._debuffs_2_cw_roles
                fl_cw_2_resolving = any(
                    any(d.debuff_type in ('forked_lightning', 'compressed_water')
                        for d in self._members[r].debuffs)
                    for r in fl_cw_2_roles if r in self._members
                )
                if not fl_cw_2_resolving:
                    for bot in self.bots:
                        s = random.choice(spot) if isinstance(spot, list) else spot
                        bot.set_destination((ARENA_CENTER[0] + s[0], ARENA_CENTER[1] + s[1]))
                self._attack_wrappers.append(_AttackWrapper(ice, t + duration))
            elif action == 'mana_release':
                shape_start = t + duration          # cast end: shapes appear
                trigger = t + duration + 5.0        # 5s later: hit
                lightning = LightningAttack()
                ice = IceAttack()
                self._mana_release_lightning = lightning
                self._mana_release_ice = ice
                # bots use the XNOR-adjusted effective pairs to find the correct safe spot
                if self._thrumming_thunder_attack and self._blizzard_attack:
                    final_l_fake = lightning.is_fake != self._thrumming_thunder_attack.is_fake
                    final_l_pair = lightning._idx if not final_l_fake else 1 - lightning._idx
                    final_i_fake = ice.is_fake != self._blizzard_attack.is_fake
                    final_i_pair = ice._idx if not final_i_fake else 1 - ice._idx
                    key = (lightning.angle, final_l_pair, final_i_pair)
                    self._mana_release_safe_spot = SAFE_SPOTS[key]
                    # schedule bot movement 3s before hit so DF mechanics don't overwrite it
                    self._pending_actions.append((trigger - 3.0, 'mana_release_bots', None))
                self._attack_wrappers.append(_AttackWrapper(
                    lightning, trigger, shape_start_time=shape_start, skip_hit_check=True))
                self._attack_wrappers.append(_AttackWrapper(
                    ice, trigger, shape_start_time=shape_start, skip_hit_check=True))
                self._pending_actions.append((trigger, 'mana_release_hit', None))

    def _fire_pending_actions(self):
        remaining = []
        for (trigger_time, action, is_fake) in self._pending_actions:
            if self._elapsed >= trigger_time:
                skip_hit = trigger_time <= self._start_time
                self._add_correction = max(0.0, self._start_time - trigger_time) if skip_hit else 0.0
                self._apply_action(action, is_fake, skip_hit=skip_hit)
            else:
                remaining.append((trigger_time, action, is_fake))
        self._pending_actions = remaining
        self._add_correction = 0.0

    def _apply_action(self, action, is_fake, skip_hit=False):
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
            self._debuffs_1_fl_roles = {supports[0], dps[0]}
            self._debuffs_1_cw_roles = {supports[1], dps[1]}
            self._debuffs_1_cs_roles = {supports[2], dps[2]}

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
            self._debuffs_2_fl_roles = {ab_s[0], ab_d[0]}
            self._debuffs_2_cw_roles = {ab_s[1], ab_d[1]}
            self._debuffs_2_cs_roles = {fl_cw[1], fl_cw_d[1]}

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
            player = self._members.get(self._role)
            if player:
                if any(d.debuff_type == 'allagan_field' for d in player.debuffs):
                    self._player_allagan_original_wound = next(
                        (d.debuff_type for d in player.debuffs if 'wound' in d.debuff_type), None)
                elif any(d.debuff_type == 'beyond_death' for d in player.debuffs):
                    self._player_beyond_death_original_wound = next(
                        (d.debuff_type for d in player.debuffs if 'wound' in d.debuff_type), None)
            self.enemies.teleport_neo_north()

        elif action == 'chaos_tsunami':
            debuff_dur = 84.0 if self._chaos_cast_count == 0 else 69.0
            self._chaos_cast_count += 1
            self._dynamic_fluid_is_fake = is_fake
            for r in (supports + dps):
                self._add(r, Debuff('dynamic_fluid', debuff_dur, is_fake))
            if self._chaos_cast_count == 2:
                self.enemies.hide_chaos()

        elif action == 'chaos_entropy':
            debuff_dur = 60.0 if self._chaos_cast_count == 0 else 45.0
            self._chaos_cast_count += 1
            self._entropy_is_fake = is_fake
            for r in (supports + dps):
                self._add(r, Debuff('entropy', debuff_dur, is_fake))
            if self._chaos_cast_count == 2:
                self.enemies.hide_chaos()

        elif action == 'flood_of_naught':
            self.enemies.hide_neo()
            time_ref = 0.0
            for bot in self.bots:
                if bot.role in self._debuffs_1_fl_roles or bot.role in self._debuffs_1_cw_roles:
                    d = next((d for d in bot.debuffs
                              if d.debuff_type in ('forked_lightning', 'compressed_water')), None)
                    if d:
                        time_ref = d.remaining
                        break
            for bot in self.bots:
                is_support = bot.role in SUPPORTS
                if bot.role in self._debuffs_1_fl_roles:
                    d = next((d for d in bot.debuffs if d.debuff_type == 'forked_lightning'), None)
                    if d:
                        spread = not d.is_fake
                        offset = (BOT_SUPPORTS_SPREAD if is_support else BOT_DPS_SPREAD) if spread \
                            else (BOT_SUPPORTS_STACK if is_support else BOT_DPS_STACK)
                        bot.set_destination(
                            (ARENA_CENTER[0] + offset[0], ARENA_CENTER[1] + offset[1]),
                            time_to_hit=d.remaining,
                        )
                        continue
                if bot.role in self._debuffs_1_cw_roles:
                    d = next((d for d in bot.debuffs if d.debuff_type == 'compressed_water'), None)
                    if d:
                        spread = d.is_fake
                        offset = (BOT_SUPPORTS_SPREAD if is_support else BOT_DPS_SPREAD) if spread \
                            else (BOT_SUPPORTS_STACK if is_support else BOT_DPS_STACK)
                        bot.set_destination(
                            (ARENA_CENTER[0] + offset[0], ARENA_CENTER[1] + offset[1]),
                            time_to_hit=d.remaining,
                        )
                        continue
                offset = BOT_SUPPORTS_STACK if is_support else BOT_DPS_STACK
                bot.set_destination(
                    (ARENA_CENTER[0] + offset[0], ARENA_CENTER[1] + offset[1]),
                    time_to_hit=time_ref,
                )

        elif action == 'tt_gaze':
            if not self._thrumming_thunder_attack or not self._debuffs_1_cs_roles:
                return
            cs_remaining = 0.0
            shriek_is_fake = None
            for r in self._debuffs_1_cs_roles:
                member = self._members.get(r)
                if member:
                    d = next((d for d in member.debuffs if d.debuff_type == 'cursed_shriek'), None)
                    if d:
                        cs_remaining = d.remaining
                        shriek_is_fake = d.is_fake
                        break
            if shriek_is_fake is None:
                return
            lt = self._thrumming_thunder_attack
            spots = TT_GAZE_SPOTS.get((lt.angle, lt.effective_pair_idx, shriek_is_fake))
            if spots is None:
                return
            support_cs = next((r for r in self._debuffs_1_cs_roles if r in SUPPORTS), None)
            dps_cs     = next((r for r in self._debuffs_1_cs_roles if r in DPS),      None)
            for bot in self.bots:
                if bot.role == support_cs:
                    dest = spots['support_shriek']
                elif bot.role == dps_cs:
                    dest = spots['dps_shriek']
                elif bot.role in ('T1', 'T2'):
                    dest = spots['tank']
                else:
                    dest = spots['party']
                bot.set_destination(
                    (ARENA_CENTER[0] + dest[0], ARENA_CENTER[1] + dest[1]),
                    time_to_hit=max(0.0, cs_remaining - 3.0),
                    force_move=True,
                )

        elif action == 'entropy_bait':
            for bot in self.bots:
                d = next((x for x in bot.debuffs if x.debuff_type == 'entropy'), None)
                if d and d.remaining is not None and d.remaining > 0:
                    bot.set_destination(
                        (ARENA_CENTER[0] + BOT_WATER_FIRE_BAIT[0], ARENA_CENTER[1] + BOT_WATER_FIRE_BAIT[1]),
                        time_to_hit=d.remaining,
                        force_move=True,
                    )

        elif action == 'df_bait':
            for bot in self.bots:
                d = next((x for x in bot.debuffs if x.debuff_type == 'dynamic_fluid'), None)
                if d and d.remaining is not None and d.remaining > 0:
                    bot.set_destination(
                        (ARENA_CENTER[0] + BOT_WATER_FIRE_BAIT[0], ARENA_CENTER[1] + BOT_WATER_FIRE_BAIT[1]),
                        time_to_hit=d.remaining,
                        force_move=True,
                    )

        elif action == 'fl_cw_2_move':
            time_ref = 0.0
            for bot in self.bots:
                if bot.role in self._debuffs_2_fl_roles or bot.role in self._debuffs_2_cw_roles:
                    d = next((x for x in bot.debuffs
                              if x.debuff_type in ('forked_lightning', 'compressed_water')), None)
                    if d:
                        time_ref = d.remaining
                        break
            for bot in self.bots:
                is_support = bot.role in SUPPORTS
                if bot.role in self._debuffs_2_fl_roles:
                    d = next((x for x in bot.debuffs if x.debuff_type == 'forked_lightning'), None)
                    if d:
                        spread = not d.is_fake
                        offset = (BOT_SUPPORTS_SPREAD if is_support else BOT_DPS_SPREAD) if spread \
                            else (BOT_SUPPORTS_STACK if is_support else BOT_DPS_STACK)
                        bot.set_destination(
                            (ARENA_CENTER[0] + offset[0], ARENA_CENTER[1] + offset[1]),
                            time_to_hit=d.remaining, force_move=True,
                        )
                        continue
                if bot.role in self._debuffs_2_cw_roles:
                    d = next((x for x in bot.debuffs if x.debuff_type == 'compressed_water'), None)
                    if d:
                        spread = d.is_fake
                        offset = (BOT_SUPPORTS_SPREAD if is_support else BOT_DPS_SPREAD) if spread \
                            else (BOT_SUPPORTS_STACK if is_support else BOT_DPS_STACK)
                        bot.set_destination(
                            (ARENA_CENTER[0] + offset[0], ARENA_CENTER[1] + offset[1]),
                            time_to_hit=d.remaining, force_move=True,
                        )
                        continue
                offset = BOT_SUPPORTS_STACK if is_support else BOT_DPS_STACK
                bot.set_destination(
                    (ARENA_CENTER[0] + offset[0], ARENA_CENTER[1] + offset[1]),
                    time_to_hit=time_ref, force_move=True,
                )

        elif action == 'cs_2_gaze':
            if not self._debuffs_2_cs_roles:
                return
            cs_is_fake = None
            cs_remaining = 0.0
            for r in self._debuffs_2_cs_roles:
                member = self._members.get(r)
                if member:
                    d = next((x for x in member.debuffs if x.debuff_type == 'cursed_shriek'), None)
                    if d:
                        cs_is_fake = d.is_fake
                        cs_remaining = d.remaining
                        break
            if cs_is_fake is None:
                return
            support_cs = next((r for r in self._debuffs_2_cs_roles if r in SUPPORTS), None)
            dps_cs     = next((r for r in self._debuffs_2_cs_roles if r in DPS),      None)
            for bot in self.bots:
                if bot.role == support_cs:
                    dest = BOT_SUPPORT_GAZE_REAL if not cs_is_fake else BOT_SUPPORT_GAZE_FAKE
                elif bot.role == dps_cs:
                    dest = BOT_DPS_GAZE_REAL if not cs_is_fake else BOT_DPS_GAZE_FAKE
                elif bot.role in ('T1', 'T2'):
                    dest = BOT_PARTY_GAZE_REAL if not cs_is_fake else BOT_TANK_GAZE_FAKE
                else:
                    dest = BOT_PARTY_GAZE_REAL if not cs_is_fake else BOT_PARTY_GAZE_FAKE
                bot.set_destination(
                    (ARENA_CENTER[0] + dest[0], ARENA_CENTER[1] + dest[1]),
                    time_to_hit=max(0.0, cs_remaining - 3.0),
                    force_move=True,
                )

        elif action == 'mana_release_bots':
            if self._mana_release_safe_spot is not None:
                spot = self._mana_release_safe_spot
                for bot in self.bots:
                    s = random.choice(spot) if isinstance(spot, list) else spot
                    bot.set_destination(
                        (ARENA_CENTER[0] + s[0], ARENA_CENTER[1] + s[1]),
                        time_to_hit=3.0, force_move=True,
                    )

        elif action == 'mana_release_hit':
            if self._mana_release_lightning and self._thrumming_thunder_attack:
                final_fake = self._mana_release_lightning.is_fake != self._thrumming_thunder_attack.is_fake
                self._mana_release_lightning.is_fake = final_fake
                if not skip_hit and self._mana_release_lightning.is_hit(self.player.get_center()):
                    self.player_was_hit = True
                    self._loss_reason = "You were hit by Mana Release (Lightning)."
                    self.state = GameState.GAME_OVER
            if not self.player_was_hit and self._mana_release_ice and self._blizzard_attack:
                final_fake = self._mana_release_ice.is_fake != self._blizzard_attack.is_fake
                self._mana_release_ice.is_fake = final_fake
                if not skip_hit and self._mana_release_ice.is_hit(self.player.get_center()):
                    self.player_was_hit = True
                    self._loss_reason = "You were hit by Mana Release (Ice)."
                    self.state = GameState.GAME_OVER

    def _add(self, role, debuff):
        member = self._members.get(role)
        if member:
            if debuff.remaining is not None:
                debuff.remaining = max(0.0, debuff.remaining - self._add_correction)
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
        self._start_time = 0.0
        self._elapsed = 0.0
        self._timeline_idx = 0
        self._active_casts = {}
        self._attack_wrappers = []
        self._pending_actions = []
        self._chaos_queue = None
        self._chaos_cast_count = 0
        self._player_allagan_original_wound = None
        self._player_beyond_death_original_wound = None
        self._thrumming_thunder_attack = None
        self._blizzard_attack = None
        self._mana_release_lightning = None
        self._mana_release_ice = None
        self._mana_release_safe_spot = None
        self._debuffs_1_fl_roles = set()
        self._debuffs_1_cw_roles = set()
        self._debuffs_1_cs_roles = set()
        self._debuffs_2_fl_roles = set()
        self._debuffs_2_cw_roles = set()
        self._debuffs_2_cs_roles = set()
        self._dynamic_fluid_is_fake = None
        self._loss_reason = ""
        self._fov_timer = 0.0
        self._fov_facing = pygame.Vector2(0, -1)
        self._fl_cw_hit_circles = []
        self._ab_window_active = False
        self._ab_window_end = 0.0
        self._ab_is_fake = False
        self._ab_violated = False
        self._ab_stationary_dur = 0.0
        self._entropy_is_fake = None
        self.enemies.reset()
        self.macro_output.clear()
        self.timer.reset()

    def update(self, dt, keys, events, arena_offset=(0, 0)):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self._reset()
                    return
                if event.key == pygame.K_u:
                    self.hud_locked = not self.hud_locked
                if event.key == pygame.K_t:
                    self._show_fake_help = not self._show_fake_help

        self.enemy_list.update(events, self.hud_locked, arena_offset)
        self.party_list.update(events, self.hud_locked, arena_offset)
        self.macro_output.update(events, self.hud_locked, arena_offset)
        self.macro_buttons.update(events, self.hud_locked, arena_offset)
        self.timer.update(dt, paused=(self.state in (GameState.GAME_OVER, GameState.VICTORY)))
        if self._fov_timer > 0:
            self._fov_timer = max(0.0, self._fov_timer - dt)
        self._fl_cw_hit_circles = [c for c in self._fl_cw_hit_circles if c[3] > 0]
        for c in self._fl_cw_hit_circles:
            c[3] = max(0.0, c[3] - dt)

        if self.state in (GameState.GAME_OVER, GameState.VICTORY):
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
                if hasattr(w.attack, 'apply_hit_effect'):
                    w.attack.apply_hit_effect(self._members)
                elif (not w.skip_hit_check
                      and w.trigger_time > self._start_time
                      and w.attack.is_hit(self.player.get_center())):
                    self.player_was_hit = True
                    if isinstance(w.attack, LightningAttack):
                        self._loss_reason = "You were hit by Lightning."
                    elif isinstance(w.attack, IceAttack):
                        self._loss_reason = "You were hit by Ice."
                    elif isinstance(w.attack, EntropyAttack):
                        if w.attack.is_fake:
                            self._loss_reason = "Fake Entropy: you were outside the safe zone."
                        else:
                            self._loss_reason = "Entropy: you were in the danger zone."
                    elif isinstance(w.attack, DynamicFluidAttack):
                        if w.attack.is_fake:
                            self._loss_reason = "Fake Dynamic Fluid: you were in the danger zone."
                        else:
                            self._loss_reason = "Dynamic Fluid: you were outside the safe zone."
                    else:
                        self._loss_reason = "You were hit by an attack."
                    self.state = GameState.GAME_OVER
        self._attack_wrappers = [w for w in self._attack_wrappers if not w.is_done]

        # Move players
        self.player.update(dt, keys)
        kefka_cast = self._active_casts.get('Kefka')
        kefka_remaining = (kefka_cast.duration - kefka_cast.elapsed) if kefka_cast else 0.0
        for bot in self.bots:
            bot.update(dt, kefka_remaining)

        # Tick debuffs; check Allagan Field / Beyond Death expiry for the player
        _af = next((d for d in self.player.debuffs if d.debuff_type == 'allagan_field'), None)
        had_allagan = (self._player_allagan_original_wound is not None
                       and _af is not None and _af.remaining is not None and _af.remaining > 0)
        _bd = next((d for d in self.player.debuffs if d.debuff_type == 'beyond_death'), None)
        had_beyond = (self._player_beyond_death_original_wound is not None
                      and _bd is not None and _bd.remaining is not None and _bd.remaining > 0)
        fl_cw_pre = {}
        for r in (self._debuffs_1_fl_roles | self._debuffs_1_cw_roles
                  | self._debuffs_2_fl_roles | self._debuffs_2_cw_roles):
            member = self._members.get(r)
            if member:
                d = next((x for x in member.debuffs
                          if x.debuff_type in ('forked_lightning', 'compressed_water')), None)
                if d and d.remaining is not None and d.remaining > 0:
                    fl_cw_pre[r] = (member, d)
        entropy_pre = {}
        for r, member in self._members.items():
            d = next((x for x in member.debuffs if x.debuff_type == 'entropy'), None)
            if d and d.remaining is not None and d.remaining > 0:
                entropy_pre[r] = pygame.Vector2(member.position)
        cs_pre = {}
        cs_is_fake = None
        cs_had_positive_remaining = False
        for r in self._debuffs_1_cs_roles:
            member = self._members.get(r)
            if member:
                d = next((x for x in member.debuffs if x.debuff_type == 'cursed_shriek'), None)
                cs_pre[r] = d is not None
                if d:
                    cs_is_fake = d.is_fake
                    if d.remaining is not None and d.remaining > 0:
                        cs_had_positive_remaining = True
            else:
                cs_pre[r] = False

        cs_pre_2 = {}
        cs_is_fake_2 = None
        cs_had_positive_remaining_2 = False
        for r in self._debuffs_2_cs_roles:
            member = self._members.get(r)
            if member:
                d = next((x for x in member.debuffs if x.debuff_type == 'cursed_shriek'), None)
                cs_pre_2[r] = d is not None
                if d:
                    cs_is_fake_2 = d.is_fake
                    if d.remaining is not None and d.remaining > 0:
                        cs_had_positive_remaining_2 = True
            else:
                cs_pre_2[r] = False
        df_pre = {}
        for r, member in self._members.items():
            d = next((x for x in member.debuffs if x.debuff_type == 'dynamic_fluid'), None)
            if d and d.remaining is not None and d.remaining > 0:
                df_pre[r] = pygame.Vector2(member.position)

        # AB window activation + per-frame violation tracking (read remaining before tick)
        player_ab = next((d for d in self.player.debuffs if d.debuff_type == 'acceleration_bomb'), None)
        if not self._ab_window_active and player_ab and player_ab.remaining is not None and 0 < player_ab.remaining <= 0.5:
            self._ab_window_active = True
            self._ab_window_end = self._elapsed + player_ab.remaining + 0.5
            self._ab_is_fake = player_ab.is_fake
            self._ab_violated = False
            self._ab_stationary_dur = 0.0
        if self._ab_window_active:
            if not self._ab_is_fake and self.player._is_moving:
                self._ab_violated = True
            elif self._ab_is_fake and not self.player._is_moving:
                self._ab_stationary_dur += dt
                if self._ab_stationary_dur >= 0.2:
                    self._ab_violated = True
            else:
                self._ab_stationary_dur = 0.0

        self.player.update_debuffs(dt)
        allagan_expired = had_allagan and not any(d.debuff_type == 'allagan_field' for d in self.player.debuffs)
        beyond_expired = had_beyond and not any(d.debuff_type == 'beyond_death' for d in self.player.debuffs)
        if allagan_expired:
            current_wound = next(
                (d.debuff_type for d in self.player.debuffs if 'wound' in d.debuff_type), None)
            if current_wound == self._player_allagan_original_wound:
                self.player_was_hit = True
                self._loss_reason = "You had Allagan Field and didn't swap your Wound debuff"
                self.state = GameState.GAME_OVER
        if beyond_expired and not self.player_was_hit:
            current_wound = next(
                (d.debuff_type for d in self.player.debuffs if 'wound' in d.debuff_type), None)
            if current_wound != self._player_beyond_death_original_wound:
                self.player_was_hit = True
                self._loss_reason = "You had Beyond Death and swapped your Wound debuff."
                self.state = GameState.GAME_OVER
        if allagan_expired or beyond_expired:
            self.player.debuffs = [d for d in self.player.debuffs if 'wound' not in d.debuff_type]
        for bot in self.bots:
            had_af_or_bd = any(d.debuff_type in ('allagan_field', 'beyond_death') for d in bot.debuffs)
            bot.update_debuffs(dt)
            if had_af_or_bd and not any(d.debuff_type in ('allagan_field', 'beyond_death') for d in bot.debuffs):
                bot.debuffs = [d for d in bot.debuffs if 'wound' not in d.debuff_type]

        # CS gaze check (skip if debuffs expired immediately due to start_time skip)
        if cs_is_fake is not None and cs_had_positive_remaining and any(
                cs_pre.get(r) and not any(x.debuff_type == 'cursed_shriek'
                for x in (self._members[r].debuffs if r in self._members else []))
                for r in self._debuffs_1_cs_roles):
            self._fov_timer = 2.0
            self._fov_facing = pygame.Vector2(self.player._facing)
            others = [self._members[r] for r in self._debuffs_1_cs_roles
                      if r in self._members and self._members[r] is not self.player]
            if others and not self.player_was_hit:
                in_cone = [self._in_fov(m.position, self.player.position, self._fov_facing) for m in others]
                if cs_is_fake and not all(in_cone):
                    self.player_was_hit = True
                    self._loss_reason = "Fake Cursed Shriek: not all Shriek players were in your field of view."
                    self.state = GameState.GAME_OVER
                elif not cs_is_fake and any(in_cone):
                    self.player_was_hit = True
                    self._loss_reason = "Cursed Shriek: a Shriek player was inside your field of view."
                    self.state = GameState.GAME_OVER

        # FL / CW expiry check
        fl_cw_expired = {r: (member, d) for r, (member, d) in fl_cw_pre.items()
                         if not any(x.debuff_type in ('forked_lightning', 'compressed_water')
                                    for x in member.debuffs)}
        if fl_cw_expired:
            all_positions = [m.position for m in self._members.values()]
            circles = []
            for r, (member, d) in fl_cw_expired.items():
                is_spread = (d.debuff_type == 'forked_lightning' and not d.is_fake) or \
                            (d.debuff_type == 'compressed_water' and d.is_fake)
                radius = 150 if is_spread else 100
                color  = (0x8e, 0x00, 0xff) if is_spread else (0x00, 0x84, 0xff)
                self._fl_cw_hit_circles.append([pygame.Vector2(member.position), radius, color, ATTACK_DURATION])
                circles.append((member.position, radius, is_spread))
            if not self.player_was_hit:
                for center, radius, is_spread in circles:
                    count = sum(1 for pos in all_positions
                                if (pygame.Vector2(pos) - pygame.Vector2(center)).length() <= radius)
                    expected = 1 if is_spread else 3
                    if count != expected:
                        self.player_was_hit = True
                        kind = "Spread" if is_spread else "Stack"
                        self._loss_reason = f"{kind}: {count} player{'s' if count != 1 else ''} hit instead of {expected}."
                        self.state = GameState.GAME_OVER
                        break

        # CS2 gaze check
        if cs_is_fake_2 is not None and cs_had_positive_remaining_2 and any(
                cs_pre_2.get(r) and not any(x.debuff_type == 'cursed_shriek'
                for x in (self._members[r].debuffs if r in self._members else []))
                for r in self._debuffs_2_cs_roles):
            self._fov_timer = 2.0
            self._fov_facing = pygame.Vector2(self.player._facing)
            others = [self._members[r] for r in self._debuffs_2_cs_roles
                      if r in self._members and self._members[r] is not self.player]
            if others and not self.player_was_hit:
                in_cone = [self._in_fov(m.position, self.player.position, self._fov_facing) for m in others]
                if cs_is_fake_2 and not all(in_cone):
                    self.player_was_hit = True
                    self._loss_reason = "Fake Cursed Shriek: not all Shriek players were in your field of view."
                    self.state = GameState.GAME_OVER
                elif not cs_is_fake_2 and any(in_cone):
                    self.player_was_hit = True
                    self._loss_reason = "Cursed Shriek: a Shriek player was inside your field of view."
                    self.state = GameState.GAME_OVER

        # Entropy expiry check
        if entropy_pre and self._entropy_is_fake is not None:
            for r, pos_at_expiry in entropy_pre.items():
                member = self._members[r]
                if not any(d.debuff_type == 'entropy' for d in member.debuffs):
                    entropy_atk = EntropyAttack(pos_at_expiry, self._entropy_is_fake)
                    self._attack_wrappers.append(_AttackWrapper(entropy_atk, self._elapsed + 2.0))
                    if member is not self.player and not self._entropy_is_fake:
                        direction = member._start_pos - pygame.Vector2(ARENA_CENTER)
                        extended = pygame.Vector2(ARENA_CENTER) + direction.normalize() * (direction.length() + 100)
                        member.set_destination(extended, force_move=True)

        # Dynamic Fluid expiry check
        if df_pre and self._dynamic_fluid_is_fake is not None:
            for r, pos_at_expiry in df_pre.items():
                member = self._members[r]
                if not any(d.debuff_type == 'dynamic_fluid' for d in member.debuffs):
                    df_atk = DynamicFluidAttack(pos_at_expiry, self._dynamic_fluid_is_fake)
                    self._attack_wrappers.append(_AttackWrapper(df_atk, self._elapsed + 2.0))
                    if member is not self.player and self._dynamic_fluid_is_fake:
                        direction = member._start_pos - pygame.Vector2(ARENA_CENTER)
                        extended = pygame.Vector2(ARENA_CENTER) + direction.normalize() * (direction.length() + 100)
                        member.set_destination(extended, force_move=True)

        # AB window end evaluation
        if self._ab_window_active and self._elapsed >= self._ab_window_end:
            self._ab_window_active = False
            if self._ab_violated and not self.player_was_hit:
                self.player_was_hit = True
                if self._ab_is_fake:
                    self._loss_reason = "Fake Acceleration Bomb: you stopped moving."
                else:
                    self._loss_reason = "Acceleration Bomb: you moved."
                self.state = GameState.GAME_OVER

        # Victory: timeline exhausted, no pending actions or unresolved attacks remain
        if (not self.player_was_hit
                and self._timeline_idx >= len(TIMELINE)
                and not self._pending_actions
                and not self._attack_wrappers):
            self.state = GameState.VICTORY

    def _build_active_casts_hud(self):
        result = {}
        for caster, cast in self._active_casts.items():
            result[caster] = {'name': cast.cast_name, 'progress': cast.progress}
        return result

    def render(self, surface, arena_offset=(0, 0)):
        self.arena.render(surface, arena_offset)

        if self._attack_wrappers or self._fl_cw_hit_circles:
            self._attack_surf.fill((0, 0, 0, 0))
            for w in self._attack_wrappers:
                if not w.triggered:
                    if w.shape_start_time is None or self._elapsed >= w.shape_start_time:
                        w.attack.render(self._attack_surf, telegraphing=True,
                                        alpha=TELEGRAPH_ALPHA, offset=(0, 0))
                else:
                    w.attack.render(self._attack_surf, telegraphing=False,
                                    alpha=_attack_alpha(w.hit_elapsed), offset=(0, 0))
            for center, radius, color, timer in self._fl_cw_hit_circles:
                alpha = int(ATTACK_ALPHA_START * (timer / ATTACK_DURATION))
                pygame.draw.circle(self._attack_surf, (*color, alpha),
                                   (int(center.x), int(center.y)), radius)
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
        self._render_fov(surface, arena_offset)

        self.enemy_list.render(surface, self._build_active_casts_hud(),
                               self.hud_locked, arena_offset)
        self.party_list.render(surface, self.hud_locked, self._members, arena_offset,
                               debug_mode=self._show_fake_help)
        self.macro_output.render(surface, self.hud_locked, arena_offset)
        self.macro_buttons.render(surface, self.hud_locked, arena_offset)
        self.timer.render(surface, arena_offset)

        if self.state == GameState.GAME_OVER:
            self._render_game_over(surface, arena_offset)
        elif self.state == GameState.VICTORY:
            self._render_victory(surface, arena_offset)

    def _in_fov(self, target_pos, origin_pos, facing):
        v = pygame.Vector2(target_pos) - pygame.Vector2(origin_pos)
        if v.length() > 800:
            return False
        if v.length() < 0.001:
            return True
        return v.normalize().dot(facing) >= math.cos(math.pi / 4)

    def _render_fov(self, surface, arena_offset=(0, 0)):
        if self._fov_timer <= 0:
            return
        alpha = int(191 * (self._fov_timer / 2.0))
        if alpha <= 0:
            return
        ox, oy = arena_offset
        tip = (self.player.position.x + ox, self.player.position.y + oy)
        left_dir  = pygame.Vector2(self._fov_facing).rotate(-45)
        right_dir = pygame.Vector2(self._fov_facing).rotate(45)
        p2 = (tip[0] + left_dir.x  * 800, tip[1] + left_dir.y  * 800)
        p3 = (tip[0] + right_dir.x * 800, tip[1] + right_dir.y * 800)
        surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(surf, (255, 255, 255, alpha), [tip, p2, p3])
        surface.blit(surf, (0, 0))

    def _render_game_over(self, surface, arena_offset=(0, 0)):
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 153))
        surface.blit(overlay, (0, 0))
        cx = arena_offset[0] + WINDOW_WIDTH // 2
        cy = arena_offset[1] + WINDOW_HEIGHT // 2
        go_text = self._font_large.render("GAME OVER", True, (255, 255, 255))
        surface.blit(go_text, go_text.get_rect(center=(cx, cy - 50)))
        if self._loss_reason:
            reason_text = self._font_normal.render(self._loss_reason, True, (255, 180, 180))
            surface.blit(reason_text, reason_text.get_rect(center=(cx, cy)))
        restart_text = self._font_normal.render("Press R to restart", True, (255, 255, 255))
        surface.blit(restart_text, restart_text.get_rect(center=(cx, cy + 40)))

    def _render_victory(self, surface, arena_offset=(0, 0)):
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 153))
        surface.blit(overlay, (0, 0))
        cx = arena_offset[0] + WINDOW_WIDTH // 2
        cy = arena_offset[1] + WINDOW_HEIGHT // 2
        win_text = self._font_large.render("CLEAR!", True, (255, 223, 0))
        surface.blit(win_text, win_text.get_rect(center=(cx, cy - 50)))
        sub_text = self._font_normal.render("Phase 4 complete. Well done!", True, (200, 255, 200))
        surface.blit(sub_text, sub_text.get_rect(center=(cx, cy)))
        restart_text = self._font_normal.render("Press R to restart", True, (255, 255, 255))
        surface.blit(restart_text, restart_text.get_rect(center=(cx, cy + 40)))

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 800
FPS = 144

ARENA_DIAMETER = 784
ARENA_RADIUS = 392
ARENA_CENTER = (400, 400)

BACKGROUND_COLOR = (58, 103, 164)

LIGHTNING_COLOR = (126, 62, 255)
LIGHTNING_TELEGRAPH_COLOR = (255, 0, 255)
ICE_COLOR = (111, 150, 215)
ICE_TELEGRAPH_COLOR = (255, 0, 255)

LIGHTNING_RECT_W = 196
LIGHTNING_RECT_H = 820
ICE_RECT_SIZE = 420

TELEGRAPH_ALPHA = 128
TELEGRAPH_BORDER_COLOR = (255, 255, 0)
TELEGRAPH_BORDER_WIDTH = 4
TELEGRAPH_RING_W = 200
TELEGRAPH_RING_H = 50
TELEGRAPH_RING_LINE_W = 4
ORB_REVOLUTION_TIME = 2.0

LIGHTNING_RING_OFFSET = (0, -80)
LIGHTNING_RING_COLOR = (224, 185, 255)

ICE_RING_OFFSET = (0, -20)
ICE_RING_COLOR = (185, 211, 255)

WHITE_ANTILIGHT_COLOR = (107, 57, 189)
BLACK_ANTILIGHT_COLOR = (2, 38, 255)
ANTILIGHT_H = 798
ANTILIGHT_TELEGRAPH_SIZE = (48, 64)
ANTILIGHT_TELEGRAPH_GAP  = 24

ATTACK_ALPHA_START = 191
TELEGRAPH_DURATION = 5.0
ATTACK_DURATION = 2.0
INITIAL_WAIT = 5.0
CAST_DURATION = 5.0
COOLDOWN_DURATION = 4.0

PLAYER_SPEED = 196

ENEMY_LIST_WIDTH = 300
ENEMY_LIST_ROW_H = 46
ENEMY_LIST_HEIGHT = 3 * 46 + 16  # 3 rows + top/bottom padding

PARTY_LIST_WIDTH = 290
PARTY_LIST_ROW_H = 52
PARTY_LIST_ORDER = ['T1', 'T2', 'H1', 'H2', 'M1', 'M2', 'R1', 'R2']

SUPPORTS = ['T1', 'T2', 'H1', 'H2']
DPS = ['M1', 'M2', 'R1', 'R2']

# (start_time_secs, caster, display_name, cast_duration_secs, action_type)
TIMELINE = [
    ( 0.000, 'Kefka',       'Kefka Says',    5.0, None),
    ( 9.588, 'Kefka',       'Mystery Magic',  5.0, 'mystery_magic'),
    ( 9.989, 'Neo Exdeath', 'Grand Cross',    9.0, 'neo_debuffs_1'),
    (15.079, 'Chaos',       'Tsunami',        9.0, 'chaos_tsunami'),
    (24.518, 'Kefka',       'Mystery Magic',  5.0, 'mystery_magic'),
    (24.920, 'Neo Exdeath', 'Grand Cross',    9.0, 'neo_debuffs_2'),
    (30.012, 'Chaos',       'Inferno',        9.0, 'chaos_entropy'),
    (39.655, 'Kefka',       'Mystery Magic',    5.0, 'mystery_magic'),
    (39.877, 'Neo Exdeath', 'Grand Cross',      9.0, 'neo_debuffs_3'),
    (56.023, 'Neo Exdeath', 'Flood of Naught',       5.0, 'flood_of_naught'),
    (66.768, 'Kefka',       'Mana Charge',           3.0, None),
    (73.013, 'Kefka',       'Thrumming Thunder III', 5.0, 'thrumming_thunder'),
    (83.148, 'Kefka',       'Ultima Upsurge',        5.0, None),
    (90.994, 'Kefka',       'Blizzard III Blowout',  5.0, 'blizzard_blowout'),
   (102.172, 'Kefka',       'Mana Release',          5.0, 'mana_release'),
   (121.948, 'Kefka',       'Ultima Upsurge',        5.0, None),
]
ROLE_NAMES = {
    'T1': 'Tank 1',
    'T2': 'Tank 2',
    'H1': 'Healer 1',
    'H2': 'Healer 2',
    'M1': 'Melee 1',
    'M2': 'Melee 2',
    'R1': 'Ranged 1',
    'R2': 'Ranged 2',
}

CAST_BAR_COLOR = (255, 255, 255)
CAST_BAR_BG_COLOR = (51, 51, 51)

FONT_NAME = "arial"
FONT_SIZE_LARGE = 48
FONT_SIZE_NORMAL = 20
FONT_SIZE_SMALL = 14

# Safe spot destinations for each of the 8 attack combinations.
# Key: (lightning_angle, lightning_pair_idx, ice_pair_idx)
#   lightning_angle:    45 or -45 degrees
#   lightning_pair_idx: 0 = stripes at offsets [-294, 98] are dangerous
#                       1 = stripes at offsets [-98, 294] are dangerous
#   ice_pair_idx:       0 = NW+SE quadrants are dangerous
#                       1 = NE+SW quadrants are dangerous
# Value: (x, y) in game-space coordinates (arena center = 400, 400)
BOT_SUPPORTS_SPREAD = (-200, 0)
BOT_DPS_SPREAD      = (200, 0)
BOT_SUPPORTS_STACK  = (0, -150)
BOT_DPS_STACK       = (0, 150)

# Key: (tt_angle, tt_effective_pair_idx, shriek_is_fake)
# Value: dict with positions for each group that must satisfy both TT safety and gaze
#   support_shriek: Support bot with Cursed Shriek
#   dps_shriek:     DPS bot with Cursed Shriek
#   tank:           non-Shriek Tank bots
#   party:          non-Shriek non-Tank bots
TT_GAZE_SPOTS = {
    ( 45, 0, False): {'support_shriek': (-40, 100), 'dps_shriek': (40, 100), 'tank': (-100, 40), 'party': (-100, -40)},
    ( 45, 0, True):  {'support_shriek': (-100, -40), 'dps_shriek': (40, 100), 'tank': (180, -180), 'party': (0, 200)},
    ( 45, 1, False): {'support_shriek': (-180, 180), 'dps_shriek': (100, 40), 'tank': (0, -80), 'party': (0, -80)},
    ( 45, 1, True):  {'support_shriek': (-40, -100), 'dps_shriek': (100, 40), 'tank': (0, -200), 'party': (0, -200)},
    (-45, 0, False): {'support_shriek': (-100, 40), 'dps_shriek': (180, 180), 'tank': (0, -80), 'party': (0, -80)},
    (-45, 0, True):  {'support_shriek': (-100, 40), 'dps_shriek': (40, -100), 'tank': (0, -200), 'party': (0, -200)},
    (-45, 1, False): {'support_shriek': (-40, 100), 'dps_shriek': (40, 100), 'tank': (100, -40), 'party': (100, -40)},
    (-45, 1, True):  {'support_shriek': (-40, 100), 'dps_shriek': (100, -40), 'tank': (0, 200), 'party': (0, 200)},
}

SAFE_SPOTS = {
    ( 45, 0, 0): (-80, 80),  # +45° pair A | Ice NW+SE
    ( 45, 0, 1): [(40, 100), (-100, -40)],  # +45° pair A | Ice NE+SW
    ( 45, 1, 0): (80, -80),  # +45° pair B | Ice NW+SE
    ( 45, 1, 1): [(100, 40), (-40, -100)],  # +45° pair B | Ice NE+SW
    (-45, 0, 0): [(40, -100), (-100, 40)],  # -45° pair A | Ice NW+SE
    (-45, 0, 1): (-80, -80),  # -45° pair A | Ice NE+SW
    (-45, 1, 0): [(100, -40), (-40, 100)],  # -45° pair B | Ice NW+SE
    (-45, 1, 1): (80, 80),  # -45° pair B | Ice NE+SW
}

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
ATTACK_ALPHA_START = 191
TELEGRAPH_DURATION = 5.0
ATTACK_DURATION = 2.0
INITIAL_WAIT = 5.0
CAST_DURATION = 5.0
COOLDOWN_DURATION = 4.0

PLAYER_SPEED = 196

ENEMY_LIST_WIDTH = 200
ENEMY_LIST_HEIGHT = 110

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

import math
import os
import pygame

_ASSETS = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets'))
_icon_cache = {}

ICON_W = 24
ICON_H = 32

DEBUFF_DEFS = {
    'white_wound':       {'name': 'White Wound',       'icon': 'white_wound_5541.png',      'sort_order': 0},
    'black_wound':       {'name': 'Black Wound',       'icon': 'black_wound_5542.png',      'sort_order': 0},
    'beyond_death':      {'name': 'Beyond Death',      'icon': 'beyond_deatrh_566.png',     'sort_order': 1},
    'allagan_field':     {'name': 'Allagan Field',     'icon': 'allagan_field_454.png',     'sort_order': 1},
    'cursed_shriek':     {'name': 'Cursed Shriek',     'icon': 'cursed_shriek_5543.png',    'sort_order': 2},
    'forked_lightning':  {'name': 'Forked Lightning',  'icon': 'forked_lightning_5544.png', 'sort_order': 3},
    'compressed_water':  {'name': 'Compressed Water',  'icon': 'compressed_water_5545.png', 'sort_order': 3},
    'acceleration_bomb': {'name': 'Acceleration Bomb', 'icon': 'acceleration_bomb_5546.png', 'sort_order': 4},
    'dynamic_fluid':     {'name': 'Dynamic Fluid',     'icon': 'dynamic_fluid_5548.png',    'sort_order': 5},
    'entropy':           {'name': 'Entropy',           'icon': 'entropy_5547.png',          'sort_order': 6},
}


def _load_icon(filename):
    if filename not in _icon_cache:
        path = os.path.join(_ASSETS, filename)
        img = pygame.image.load(path).convert_alpha()
        _icon_cache[filename] = pygame.transform.smoothscale(img, (ICON_W, ICON_H))
    return _icon_cache[filename]


class Debuff:
    def __init__(self, debuff_type, duration, is_fake=False):
        defn = DEBUFF_DEFS[debuff_type]
        self.debuff_type = debuff_type
        self.name = defn['name']
        self.sort_order = defn['sort_order']
        self.duration = duration   # float seconds, or None for permanent
        self.remaining = duration
        self.is_fake = is_fake

    def load_icon(self):
        return _load_icon(DEBUFF_DEFS[self.debuff_type]['icon'])

    def update(self, dt):
        if self.remaining is not None:
            self.remaining -= dt

    @property
    def is_expired(self):
        return self.remaining is not None and self.remaining <= 0

    @property
    def duration_text(self):
        if self.remaining is None:
            return ''
        return str(int(math.ceil(max(0.0, self.remaining))))

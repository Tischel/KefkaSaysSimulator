import os
import sys

if getattr(sys, 'frozen', False):
    _ROOT = sys._MEIPASS
else:
    _ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

ASSETS = os.path.join(_ROOT, 'assets')

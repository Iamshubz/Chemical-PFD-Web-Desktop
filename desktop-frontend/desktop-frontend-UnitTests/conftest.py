import os
import sys


UNIT_TESTS_DIR = os.path.dirname(__file__)
DESKTOP_FRONTEND_DIR = os.path.abspath(os.path.join(UNIT_TESTS_DIR, ".."))

if DESKTOP_FRONTEND_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_FRONTEND_DIR)

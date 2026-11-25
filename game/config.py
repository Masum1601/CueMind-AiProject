"""Shared constants for CueMind: table geometry, physics, rules and look.

All table coordinates are in "table units". The playing field (the cloth inside
the cushions) runs from (0, 0) to (FIELD_W, FIELD_H); y grows downwards.
"""
import os
import math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
IMAGES = os.path.join(ASSETS, "images")

# ---------------------------------------------------------------- table
FIELD_W = 1000.0
FIELD_H = 500.0
BALL_R = 11.5

CORNER_POCKET = 26.0      # capture radius of a corner pocket
SIDE_POCKET = 23.0        # capture radius of a side pocket
CORNER_MOUTH = 34.0       # cushions stop this far from each corner
SIDE_MOUTH = 26.0         # half width of the side pocket opening

POCKETS = [  # (x, y, capture radius) - TL, TM, TR, BL, BM, BR
    (-9.0, -9.0, CORNER_POCKET),
    (FIELD_W / 2, -15.0, SIDE_POCKET),
    (FIELD_W + 9.0, -9.0, CORNER_POCKET),
    (-9.0, FIELD_H + 9.0, CORNER_POCKET),
    (FIELD_W / 2, FIELD_H + 15.0, SIDE_POCKET),
    (FIELD_W + 9.0, FIELD_H + 9.0, CORNER_POCKET),
]
POCKET_NAMES = ["top-left", "top side", "top-right", "bottom-left", "bottom side", "bottom-right"]
SIDE_POCKETS = (1, 4)

HEAD_SPOT = (FIELD_W * 0.25, FIELD_H / 2)   # cue ball for the break
FOOT_SPOT = (FIELD_W * 0.72, FIELD_H / 2)   # apex of the rack

# ---------------------------------------------------------------- physics
DT = 1.0 / 240.0          # fixed step: the screen and the AI share it exactly
FRICTION_A = 120.0        # constant rolling deceleration (units/s^2)
FRICTION_K = 0.55         # speed-proportional drag (1/s)
BALL_E = 0.95             # ball-ball restitution
CUSHION_E = 0.78          # cushion restitution (normal part)
CUSHION_T = 0.97          # cushion keeps this much of the sliding part
STOP_SPEED = 4.0
MAX_SPEED = 1900.0
MAX_SIM_TIME = 16.0
POCKET_MIN_SPEED = 55.0   # an object ball should still roll this fast at the pocket

# execution noise for every AI (fair: both sides get the same)
NOISE_ANGLE_DEG = 0.30
NOISE_SPEED = 0.025

# ---------------------------------------------------------------- rules
MATCH_CLOCK = 60.0
POINTS_BALL = 1
POINTS_EIGHT = 3
FOUL_POINTS = 1
FOUL_SECONDS = 5.0

# ---------------------------------------------------------------- look
SCREEN_W, SCREEN_H = 1600, 900
FPS = 60
RAIL = 58                  # rail thickness on screen
TABLE_X = 64 + RAIL        # screen x of field origin
TABLE_Y = 196 + RAIL       # screen y of field origin

BG = (8, 12, 24)
INK = (234, 242, 250)
MUTED = (150, 172, 196)
CYAN = (34, 211, 238)
AMBER = (245, 165, 36)
RED = (244, 84, 84)
GREEN = (74, 222, 128)
PANEL = (16, 25, 46)
PANEL_EDGE = (38, 56, 86)

BALL_COLORS = {
    0: (246, 244, 236),
    1: (247, 196, 30), 2: (30, 82, 200), 3: (214, 40, 40), 4: (110, 46, 170),
    5: (244, 120, 26), 6: (22, 140, 72), 7: (130, 32, 38), 8: (22, 22, 26),
    9: (247, 196, 30), 10: (30, 82, 200), 11: (214, 40, 40), 12: (110, 46, 170),
    13: (244, 120, 26), 14: (22, 140, 72), 15: (130, 32, 38),
}


def ball_points(n):
    return POINTS_EIGHT if n == 8 else POINTS_BALL


def deg(a):
    return a * 180.0 / math.pi

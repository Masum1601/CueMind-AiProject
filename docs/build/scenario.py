"""Draw the traced scenario with the game's own renderer: top shots A-D and the A* order."""
import json
import math
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
GAME = r"F:\E\Downloads\Need2livewebsite\cuemind"
MEDIA = os.path.join(GAME, "docs", "media")
sys.path.insert(0, GAME)

import numpy as np  # noqa: E402
import pygame  # noqa: E402

pygame.init()
screen = pygame.display.set_mode((1600, 900))
from game import config as C  # noqa: E402
from game.render import assets as A  # noqa: E402
from game.render.tablegfx import TableArt, to_screen  # noqa: E402
from game.render.balls import BallSprites  # noqa: E402

T = json.load(open(os.path.join(MEDIA, "trace.json")))
data = np.load(os.path.join(MEDIA, "scenario_pos.npy"))
pos, alive = data[:, :2], data[:, 2] > 0.5
art = TableArt()
art.draw(screen, None)
bs = BallSprites(C.BALL_R)
rng = np.random.default_rng(4)
over = pygame.Surface((1600, 900), pygame.SRCALPHA)
cue = to_screen(*pos[0])
cols = [C.CYAN, C.AMBER, (120, 220, 140), (200, 160, 255)]
for k, r in enumerate(T["heuristic"][:4]):
    g = to_screen(*r["ghost"])
    b = to_screen(*pos[r["ball"]])
    pk = [i for i, n in enumerate(C.POCKET_NAMES) if n == r["pocket"]][0]
    p = to_screen(C.POCKETS[pk][0], C.POCKETS[pk][1])
    c = cols[k]
    pygame.draw.line(over, (*c, 200), cue, g, 3 if k == 0 else 2)
    pygame.draw.circle(over, (*c, 230), (int(g[0]), int(g[1])), int(C.BALL_R), 2)
    pygame.draw.line(over, (*c, 140), b, p, 2)
screen.blit(over, (0, 0))
for n in range(16):
    if not alive[n]:
        continue
    bs.reset(n, rng)
    x, y = to_screen(*pos[n])
    s = bs.sprite(n)
    screen.blit(bs.shadow, (x - bs.shadow.get_width() / 2 + 5, y - bs.shadow.get_height() / 2 + 7))
    screen.blit(s, (x - s.get_width() / 2, y - s.get_height() / 2))
for k, r in enumerate(T["heuristic"][:4]):
    b = to_screen(*pos[r["ball"]])
    pk = [i for i, n in enumerate(C.POCKET_NAMES) if n == r["pocket"]][0]
    p = to_screen(C.POCKETS[pk][0], C.POCKETS[pk][1])
    mx, my = b[0] + (p[0] - b[0]) * 0.55, b[1] + (p[1] - b[1]) * 0.55
    pygame.draw.circle(screen, cols[k], (int(mx), int(my)), 13)
    A.text(screen, "ABCD"[k], "bold", 15, (10, 14, 24), (mx, my), "center")
for k, (b, pk) in enumerate(T["astar"]["plan"]):
    x, y = to_screen(*pos[b])
    pygame.draw.circle(screen, (250, 250, 250), (int(x - 15), int(y + 15)), 10)
    A.text(screen, str(k + 1), "bold", 13, (10, 14, 24), (x - 15, y + 15), "center")
cx, cy = cue
A.text(screen, "cue ball", "semibold", 15, C.INK, (cx + 4, cy - 20), "midbottom")
crop = screen.subsurface(pygame.Rect(C.TABLE_X - 70, C.TABLE_Y - 70, int(C.FIELD_W) + 140, int(C.FIELD_H) + 140))
pygame.image.save(crop, os.path.join(MEDIA, "scenario.png"))
print("saved scenario")

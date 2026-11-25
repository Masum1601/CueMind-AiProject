"""Extra stills: pause, ball-in-hand, benchmark (from real CSV results), badge clean-up, benchmark chart."""
import csv
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
GAME = r"F:\E\Downloads\Need2livewebsite\cuemind"
MEDIA = os.path.join(GAME, "docs", "media")
sys.path.insert(0, GAME)

import pygame  # noqa: E402
from game.app import App  # noqa: E402
from game import config as C  # noqa: E402

app = App(headless=True)
app.loading()
mouse = [800, 450]
app.mouse = lambda: tuple(mouse)
scr = app.screen

# clean bottom-right corner (video speed badges) using the plain background
clean = app.art.composite(None)
for f in os.listdir(MEDIA):
    if f[:2].isdigit() and f.endswith(".png"):
        p = os.path.join(MEDIA, f)
        im = pygame.image.load(p)
        if im.get_size() == (1600, 900):
            im.blit(clean, (1440, 826), pygame.Rect(1440, 826, 160, 74))
            pygame.image.save(im, p)

from game.scenes.setup import SetupScene  # noqa: E402
from game.scenes.match import MatchScene  # noqa: E402
from game.scenes.benchmark import BenchmarkScene  # noqa: E402


def frames(s, n):
    for _ in range(n):
        s.update(1 / 60)
        s.draw(scr)


# ball in hand (human)
hs = MatchScene(app, SetupScene(app, human=True).players(), 1, True, 0, 5)
frames(hs, 170)
m = hs.match
m.is_break = False
m.table.alive[0] = False
m.ball_in_hand = True
hs.set_phase("place_human")
mouse[:] = [C.TABLE_X + 300, C.TABLE_Y + 300]
frames(hs, 20)
pygame.image.save(scr, os.path.join(MEDIA, "12_ball_in_hand.png"))

# pause menu
ps = MatchScene(app, SetupScene(app, human=False).players(), 1, True, 0, 3)
frames(ps, 200)
ps.paused = True
frames(ps, 2)
pygame.image.save(scr, os.path.join(MEDIA, "14_pause.png"))
ps._shutdown()

# benchmark screen filled with the real 20-match Minimax vs MCTS results
rows = list(csv.DictReader(open(os.path.join(MEDIA, "bench_minimax_mcts.csv"))))
b = BenchmarkScene(app)
b.n.index = 1
b.total = len(rows)
for r in rows:
    w = 0 if r["winner"] == "Minimax" else (1 if r["winner"] == "MCTS" else -1)
    b.results.append({"game": int(r["game"]), "a": "Minimax", "b": "MCTS", "score_a": int(r["score_a"]),
                      "score_b": int(r["score_b"]), "winner": r["winner"], "fouls_a": int(r["fouls_a"]),
                      "fouls_b": int(r["fouls_b"]), "balls_a": int(r["balls_a"]), "balls_b": int(r["balls_b"]),
                      "think_a": 0.6, "think_b": 0.6, "sims_a": 0, "sims_b": 0, "w": w, "secs": 13.0})
frames(b, 3)
pygame.image.save(scr, os.path.join(MEDIA, "13_benchmark.png"))
print("stills done")

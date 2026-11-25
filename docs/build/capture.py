"""Render screenshots and gameplay videos straight from the game (headless)."""
import math
import os
import sys
import time

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
GAME = r"F:\E\Downloads\Need2livewebsite\cuemind"
MEDIA = os.path.join(GAME, "docs", "media")
os.makedirs(MEDIA, exist_ok=True)
sys.path.insert(0, GAME)

import numpy as np  # noqa: E402
import pygame  # noqa: E402
import imageio.v2 as imageio  # noqa: E402

from game.app import App  # noqa: E402
from game import config as C  # noqa: E402
from game.render import assets as A  # noqa: E402

which = sys.argv[1] if len(sys.argv) > 1 else "all"
app = App(headless=True)
app.loading()
mouse = [800, 450]
app.mouse = lambda: tuple(mouse)
scr = app.screen


def shot(name):
    pygame.image.save(scr, os.path.join(MEDIA, name + ".png"))


class Video:
    def __init__(self, name, every=1, badge=None):
        self.w = imageio.get_writer(os.path.join(MEDIA, name + ".mp4"), fps=30, codec="libx264",
                                    quality=8, pixelformat="yuv420p", macro_block_size=8)
        self.every = every
        self.k = 0
        self.badge = badge

    def add(self):
        self.k += 1
        if self.k % self.every:
            return
        if self.badge:
            r = pygame.Rect(C.SCREEN_W - 124, C.SCREEN_H - 50, 96, 34)
            A.panel(scr, r, fill=(8, 12, 24), edge=C.AMBER, radius=17, alpha=230, width=2)
            A.text(scr, self.badge, "bold", 18, C.AMBER, r.center, "center")
        frame = pygame.surfarray.array3d(scr).transpose(1, 0, 2)
        small = pygame.transform.smoothscale(scr, (1280, 720))
        self.w.append_data(pygame.surfarray.array3d(small).transpose(1, 0, 2))

    def close(self):
        self.w.close()


def step(scene, dt=1 / 60):
    if app.next_scene is not None:
        app.scene = app.next_scene
        app.next_scene = None
        app.fade_dir = 0
    s = app.scene if app.scene is not None else scene
    s.update(dt)
    s.draw(scr)
    return s


from game.scenes.menu import MenuScene  # noqa: E402
from game.scenes.setup import SetupScene  # noqa: E402
from game.scenes.match import MatchScene  # noqa: E402
from game.scenes.howto import HowToScene  # noqa: E402
from game.scenes.benchmark import BenchmarkScene  # noqa: E402
from game.scenes.results import ResultsScene  # noqa: E402
from game import shots as S  # noqa: E402

# ------------------------------------------------------------------ UI tour + stills
if which in ("all", "tour"):
    v = Video("ui_tour", every=2)
    app.scene = MenuScene(app)
    for i in range(150):
        mouse[:] = [300, 470 if i < 60 else 556]
        step(app.scene); v.add()
    shot("01_menu")
    app.scene = SetupScene(app, human=False)
    for i in range(110):
        mouse[:] = [800, 845]
        step(app.scene); v.add()
    shot("02_setup_ai")
    app.scene = SetupScene(app, human=True)
    for i in range(60):
        step(app.scene); v.add()
    shot("03_setup_human")
    app.scene = HowToScene(app)
    for i in range(90):
        step(app.scene); v.add()
    shot("04_howto")
    v.close()

# ------------------------------------------------------------------ AI vs AI match
if which in ("all", "match"):
    v = Video("ai_vs_ai_4x", every=8, badge="4x speed")
    players = SetupScene(app, human=False).players()
    ms = MatchScene(app, players, speed=1, vision=True, breaker=0, seed=11)
    app.scene = ms
    got = set()
    t0 = time.time()
    while time.time() - t0 < 900:
        s = step(ms)
        v.add()
        if s is not ms:
            break
        ph = ms.phase
        if ph == "intro" and ms.phase_t > 1.9 and "intro" not in got:
            shot("05_intro"); got.add("intro")
        if not ms.match.is_break:
            if ph == "think" and ms.phase_t > 0.9 and "think" not in got:
                shot("06_think"); got.add("think")
            if ph == "think" and ms.phase_t > 0.9 and "think2" not in got and len(ms.match.history) > 6:
                shot("06b_think_late"); got.add("think2")
            if ph == "pull" and "aim" not in got:
                shot("07_ai_aim"); got.add("aim")
            if ph == "roll" and ms.phase_t > 0.3 and "roll" not in got:
                shot("08_roll"); got.add("roll")
            if ph == "result" and ms.toast and ms.phase_t > 0.2 and "pot" not in got and \
                    ms.match.history and ms.match.history[-1].potted:
                shot("09_pot"); got.add("pot")
        if ph == "roll" and ms.match.is_break and ms.phase_t > 0.25 and "break" not in got:
            shot("05b_break"); got.add("break")
    # results screen
    for i in range(150):
        s = step(app.scene); v.add()
    shot("10_results")
    v.close()
    m = ms.match
    print("match", m.scores, [round(c, 1) for c in m.clocks], "shots", len(m.history))

# ------------------------------------------------------------------ Human vs AI
if which in ("all", "human"):
    v = Video("human_vs_ai_2x", every=4, badge="2x speed")
    players = SetupScene(app, human=True).players()
    hs = MatchScene(app, players, speed=1, vision=True, breaker=0, seed=5)
    app.scene = hs
    human_shots = 0
    t0 = time.time()
    plan = None
    while time.time() - t0 < 600 and human_shots < 4:
        s = step(hs); v.add()
        if s is not hs:
            break
        if hs.phase == "place_human":
            spot = S.bfs_place(hs.table, S.ideal_spots(hs.table, 1)[0])
            tx, ty = C.TABLE_X + spot[0], C.TABLE_Y + spot[1]
            for i in range(40):           # glide the cue ball into place
                k = (i + 1) / 40
                mouse[:] = [int(mouse[0] + (tx - mouse[0]) * k), int(mouse[1] + (ty - mouse[1]) * k)]
                step(hs); v.add()
            if "place" not in getattr(hs, "_shots", set()):
                shot("12_ball_in_hand")
            hs.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(tx, ty)))
            continue
        if hs.phase == "human" and hs.phase_t > 0.2:
            t = hs.table
            if hs.match.is_break:
                ang, power = 0.0, 1.0
                ang = math.atan2(t.pos[1, 1] - t.pos[0, 1], t.pos[1, 0] - t.pos[0, 0])
            else:
                cands = [c for c in S.direct_shots(t)]
                cands.sort(key=lambda c: -c.value)
                c = cands[0] if cands else S.safety_shots(t)[0]
                ang = c.angle
                power = min(1.0, (c.speed * 1.12 / C.MAX_SPEED) ** (1 / 1.35))
            cx, cy = C.TABLE_X + t.pos[0, 0], C.TABLE_Y + t.pos[0, 1]
            a0 = hs.cue_angle
            for i in range(45):            # sweep the aim onto the target
                k = A.ease_in_out((i + 1) / 45)
                a = a0 + ((ang - a0 + math.pi) % (2 * math.pi) - math.pi) * k
                mouse[:] = [int(cx + math.cos(a) * 260), int(cy + math.sin(a) * 260)]
                step(hs); v.add()
            hs.cue_angle = ang
            hs.key_aim = True
            if human_shots == 1:
                shot("11_human_aim")
            hs.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=tuple(mouse)))
            start = tuple(mouse)
            for i in range(40):            # pull back for power
                d = power * 240 * (i + 1) / 40
                mouse[:] = [int(start[0] - math.cos(ang) * d), int(start[1] - math.sin(ang) * d)]
                step(hs); v.add()
            if human_shots == 1:
                shot("11b_human_power")
            hs.handle(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=tuple(mouse)))
            hs.key_aim = False
            human_shots += 1
    for i in range(300):
        s = step(app.scene); v.add()
        if hs.phase == "human":
            break
    v.close()
    print("human demo", hs.match.scores)

# ------------------------------------------------------------------ benchmark + pause stills
if which in ("all", "bench"):
    b = BenchmarkScene(app)
    b.bud.index = 0
    b.n.index = 0
    b.start()
    t0 = time.time()
    while b.running and time.time() - t0 < 600:
        time.sleep(0.5)
    app.scene = b
    for i in range(5):
        step(b)
    shot("13_benchmark")
    print("bench", [(r["score_a"], r["score_b"]) for r in b.results])
    players = SetupScene(app, human=False).players()
    ps = MatchScene(app, players, 1, True, 0, 3)
    app.scene = ps
    for i in range(200):
        step(ps)
    ps.paused = True
    step(ps)
    shot("14_pause")
print("done")

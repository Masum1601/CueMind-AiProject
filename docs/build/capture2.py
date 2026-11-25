"""Real-time (60 fps) footage with a phase log, for cutting short looping clips."""
import json
import math
import os
import sys
import time

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
GAME = r"F:\E\Downloads\Need2livewebsite\cuemind"
RAW = os.path.join(GAME, "docs", "media", "raw")
os.makedirs(RAW, exist_ok=True)
sys.path.insert(0, GAME)

import pygame  # noqa: E402
import imageio.v2 as imageio  # noqa: E402
from game.app import App  # noqa: E402
from game import config as C  # noqa: E402
from game.render import assets as A  # noqa: E402
from game import shots as S  # noqa: E402

which = sys.argv[1]
app = App(headless=True)
app.loading()
mouse = [800, 450]
app.mouse = lambda: tuple(mouse)
scr = app.screen
from game.scenes.setup import SetupScene  # noqa: E402
from game.scenes.match import MatchScene  # noqa: E402

w = imageio.get_writer(os.path.join(RAW, which + ".mp4"), fps=60, codec="libx264", quality=9,
                       pixelformat="yuv420p", macro_block_size=8)
log = []
frame = [0]


def rec(scene):
    scene.update(1 / 60)
    scene.draw(scr)
    small = pygame.transform.smoothscale(scr, (1920, 1080))
    w.append_data(pygame.surfarray.array3d(small).transpose(1, 0, 2))
    frame[0] += 1


if which == "ai":
    ms = MatchScene(app, SetupScene(app, human=False).players(), 1, True, 0, 11)
    last = None
    while frame[0] < 60 * 75:
        rec(ms)
        if ms.phase != last:
            log.append((round(frame[0] / 60, 2), ms.phase, len(ms.match.history)))
            last = ms.phase
        if ms.phase == "over":
            break
else:
    hs = MatchScene(app, SetupScene(app, human=True).players(), 1, True, 0, 5)
    shots_done = 0
    last = None
    while frame[0] < 60 * 60 and shots_done < 3:
        rec(hs)
        if hs.phase != last:
            log.append((round(frame[0] / 60, 2), hs.phase, len(hs.match.history)))
            last = hs.phase
        if hs.phase == "human" and hs.phase_t > 0.3:
            t = hs.table
            if hs.match.is_break:
                ang = math.atan2(t.pos[1, 1] - t.pos[0, 1], t.pos[1, 0] - t.pos[0, 0]); power = 1.0
            else:
                c = sorted(S.direct_shots(t), key=lambda c: -c.value)
                c = c[0] if c else S.safety_shots(t)[0]
                ang, power = c.angle, min(1.0, (c.speed * 1.12 / C.MAX_SPEED) ** (1 / 1.35))
            cx, cy = C.TABLE_X + t.pos[0, 0], C.TABLE_Y + t.pos[0, 1]
            a0 = hs.cue_angle
            log.append((round(frame[0] / 60, 2), "human_aim_start", shots_done))
            for i in range(70):
                k = A.ease_in_out((i + 1) / 70)
                a = a0 + ((ang - a0 + math.pi) % (2 * math.pi) - math.pi) * k
                mouse[:] = [int(cx + math.cos(a) * 260), int(cy + math.sin(a) * 260)]
                rec(hs)
            hs.cue_angle = ang
            hs.key_aim = True
            hs.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=tuple(mouse)))
            start = tuple(mouse)
            for i in range(50):
                d = power * 240 * (i + 1) / 50
                mouse[:] = [int(start[0] - math.cos(ang) * d), int(start[1] - math.sin(ang) * d)]
                rec(hs)
            hs.handle(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=tuple(mouse)))
            hs.key_aim = False
            shots_done += 1
w.close()
json.dump(log, open(os.path.join(RAW, which + "_log.json"), "w"))
print(which, "frames", frame[0], "events", len(log))

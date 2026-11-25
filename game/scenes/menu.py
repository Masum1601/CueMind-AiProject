"""Main menu: slow cinematic background, a live-rendered 3D 8-ball and the mode buttons."""
import math
import random

import numpy as np
import pygame

from .. import config as C
from ..render import assets as A
from ..render.balls import BallSprites, _rot
from ..render.ui import Button


class MenuScene:
    def __init__(self, app):
        self.app = app
        self.t = 0.0
        self.bg = A.image("hero.jpg", (int(C.SCREEN_W * 1.08), int(C.SCREEN_H * 1.08)))
        shade = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
        for x in range(C.SCREEN_W):
            a = int(235 * max(0.0, 1 - x / (C.SCREEN_W * 0.78)) ** 1.1)
            pygame.draw.line(shade, (6, 10, 20, a), (x, 0), (x, C.SCREEN_H))
        self.shade = shade.convert_alpha()
        self.ball = BallSprites(92, ss=1)
        self.M = _rot((0.3, 1.0, 0.2), 0.6) @ np.eye(3)
        self.ball_glow = A.radial_glow(190, C.CYAN, 2.2, 90)
        self.motes = [[random.uniform(0, C.SCREEN_W), random.uniform(0, C.SCREEN_H), random.uniform(6, 22),
                       random.uniform(1.5, 3.5), random.choice((C.CYAN, C.AMBER))] for _ in range(46)]
        x, w = 120, 470
        y0 = 430
        self.buttons = [
            Button((x, y0, w, 74), "AI vs AI", "Watch Minimax and MCTS duel", C.CYAN, self.ai_vs_ai, big=True),
            Button((x, y0 + 88, w, 74), "Human vs AI", "Take on Greedy, Minimax or MCTS", C.AMBER, self.human_vs_ai, big=True),
            Button((x, y0 + 176, w, 60), "Benchmark", "Run 10-100 silent matches", C.GREEN, self.benchmark),
            Button((x, y0 + 248, 228, 54), "How to play", accent=C.MUTED, on_click=self.howto),
            Button((x + 242, y0 + 248, 228, 54), "Quit", accent=C.RED, on_click=self.app.quit),
        ]
        app.sounds.music(True)

    def ai_vs_ai(self):
        from .setup import SetupScene
        self.app.switch(SetupScene(self.app, human=False))

    def human_vs_ai(self):
        from .setup import SetupScene
        self.app.switch(SetupScene(self.app, human=True))

    def benchmark(self):
        from .benchmark import BenchmarkScene
        self.app.switch(BenchmarkScene(self.app))

    def howto(self):
        from .howto import HowToScene
        self.app.switch(HowToScene(self.app))

    def handle(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for b in self.buttons:
                if b.click(e.pos, self.app.sounds):
                    return

    def update(self, dt):
        self.t += dt
        mouse = self.app.mouse()
        for b in self.buttons:
            b.update(dt, mouse, self.app.sounds)
        self.M = _rot((0.25, 1.0, 0.35), dt * 0.55) @ self.M
        self.ball.orient[8] = self.M
        self.ball.cache.pop(8, None)
        for m in self.motes:
            m[1] -= m[2] * dt
            m[0] += math.sin(self.t * 0.4 + m[3]) * 6 * dt
            if m[1] < -10:
                m[1] = C.SCREEN_H + 10
                m[0] = random.uniform(0, C.SCREEN_W)

    def draw(self, screen):
        if self.bg:
            ox = (self.bg.get_width() - C.SCREEN_W) * (0.5 + 0.5 * math.sin(self.t * 0.07))
            oy = (self.bg.get_height() - C.SCREEN_H) * (0.5 + 0.5 * math.cos(self.t * 0.05))
            screen.blit(self.bg, (-ox, -oy))
        else:
            screen.fill(C.BG)
        screen.blit(self.shade, (0, 0))
        for x, y, sp, ph, col in self.motes:
            g = self.app.fx_glow(col, int(ph * 2))
            screen.blit(g, (x, y), special_flags=pygame.BLEND_ADD)
        # live 3D 8-ball
        bx, by = 200, 196
        screen.blit(self.ball_glow, (bx - 190, by - 190), special_flags=pygame.BLEND_ADD)
        s = self.ball.sprite(8)
        screen.blit(s, s.get_rect(center=(bx, by)))
        A.text(screen, "CueMind", "display", 128, C.INK, (320, 120), "topleft", glow=C.CYAN, glow_strength=0.9)
        A.text(screen, "60-SECOND RACK ATTACK DUEL", "semibold", 26, C.AMBER, (328, 262), "topleft")
        A.text(screen, "Two AI players, one table: Minimax vs Monte Carlo Tree Search", "body", 20, C.MUTED,
               (328, 302), "topleft")
        for b in self.buttons:
            b.draw(screen)
        A.text(screen, "Azmaeen Nur Sajin · 2207113     Masumur Rahman Fokrul · 2207114", "semibold", 16, C.INK,
               (120, 838), "topleft")
        A.text(screen, "CSE 3210 Artificial Intelligence Lab · Department of CSE · KUET", "body", 15, C.MUTED,
               (120, 862), "topleft")
        x = A.keycap(screen, "F11", "fullscreen", (C.SCREEN_W - 250, 868)) + 18
        A.keycap(screen, "M", "mute", (x, 868))

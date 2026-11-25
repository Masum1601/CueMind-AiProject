"""End of match: winner, scores and how each AI played."""
import math
import random

import pygame

from .. import config as C
from ..render import assets as A
from ..render.ui import Button
from .match import avatar_surface

COLORS = (C.CYAN, C.AMBER)


class ResultsScene:
    def __init__(self, app, match, players, totals, opts):
        self.app = app
        self.m = match
        self.players = players
        self.totals = totals
        self.opts = opts
        self.t = 0.0
        self.bg = A.image("closing.jpg", (C.SCREEN_W, C.SCREEN_H))
        self.dim = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
        self.dim.fill((6, 10, 20, 150))
        self.w = match.winner()
        self.avatars = [avatar_surface(p["avatar"], COLORS[i], 150) for i, p in enumerate(players)]
        col = COLORS[self.w] if self.w >= 0 else C.INK
        self.confetti = [[random.uniform(0, C.SCREEN_W), random.uniform(-C.SCREEN_H, 0), random.uniform(60, 180),
                          random.uniform(-40, 40), random.choice((col, C.INK, C.AMBER))] for _ in range(140)]
        self.buttons = [Button((560, 790, 230, 64), "Rematch", accent=C.GREEN, on_click=self.rematch, big=True),
                        Button((810, 790, 230, 64), "Main menu", accent=C.MUTED, on_click=self.menu, big=True)]

    def rematch(self):
        from .match import MatchScene
        sp, vis, br = self.opts
        self.app.switch(MatchScene(self.app, self.players, sp, vis, 1 - br))

    def menu(self):
        from .menu import MenuScene
        self.app.switch(MenuScene(self.app))

    def handle(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for b in self.buttons:
                if b.click(e.pos, self.app.sounds):
                    return
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_RETURN):
            self.menu()

    def update(self, dt):
        self.t += dt
        for b in self.buttons:
            b.update(dt, self.app.mouse(), self.app.sounds)
        for c in self.confetti:
            c[1] += c[2] * dt
            c[0] += c[3] * dt + math.sin(self.t * 2 + c[2]) * 0.4
            if c[1] > C.SCREEN_H + 10:
                c[1] = random.uniform(-200, -10)

    def draw(self, screen):
        if self.bg:
            screen.blit(self.bg, (0, 0))
        screen.blit(self.dim, (0, 0))
        for x, y, sp, dx, col in self.confetti:
            pygame.draw.rect(screen, col, (x, y, 6, 10), border_radius=2)
        m = self.m
        if self.w >= 0:
            col = COLORS[self.w]
            A.text(screen, f"{m.names[self.w].upper()} WINS", "display", 76, col, (C.SCREEN_W / 2, 70), "midtop",
                   glow=col, glow_strength=1.0)
        else:
            A.text(screen, "DRAW", "display", 76, C.INK, (C.SCREEN_W / 2, 70), "midtop", glow=C.CYAN)
        A.text(screen, "Rack Attack Duel · final result", "body", 20, C.MUTED, (C.SCREEN_W / 2, 170), "midtop")
        for p, cx in ((0, 470), (1, 1130)):
            col = COLORS[p]
            rect = pygame.Rect(cx - 280, 230, 560, 520)
            A.panel(screen, rect, fill=(10, 18, 34), edge=col if p == self.w else C.PANEL_EDGE, radius=22,
                    alpha=230, width=2)
            screen.blit(self.avatars[p], self.avatars[p].get_rect(center=(cx, 320)))
            pygame.draw.circle(screen, col, (cx, 320), 78, 3)
            A.text(screen, m.names[p], "bold", 30, C.INK, (cx, 410), "midtop")
            A.text(screen, self.players[p].get("sub", ""), "body", 15, C.MUTED, (cx, 448), "midtop")
            A.text(screen, str(m.scores[p]), "display", 90, col, (cx, 470), "midtop", glow=col)
            tot = self.totals[p]
            dec = max(tot["decisions"], 1)
            rows = [("Balls potted", m.balls_potted[p]), ("Fouls", m.fouls[p]),
                    ("Shots", m.shots_taken[p]), ("Clock left", f"{m.clocks[p]:.1f} s"),
                    ("Avg think", f"{tot['think'] / dec:.2f} s" if tot["decisions"] else "-"),
                    ("Simulations", tot["sims"] if tot["decisions"] else "-")]
            y = 582
            for i, (k, v) in enumerate(rows):
                x = rect.x + 40 + (i % 2) * 260
                yy = y + (i // 2) * 52
                A.text(screen, k, "body", 15, C.MUTED, (x, yy))
                A.text(screen, str(v), "bold", 22, C.INK, (x, yy + 18))
        for b in self.buttons:
            b.draw(screen)

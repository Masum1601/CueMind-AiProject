"""Pick the players and options before a match."""
import random

import pygame

from .. import config as C
from ..render import assets as A
from ..render.ui import Button, Picker
from .match import avatar_surface

AI_INFO = {
    "Minimax": ("minimax", "Minimax + alpha-beta + IDDFS"),
    "MCTS": ("mcts", "Monte Carlo Tree Search (UCB1)"),
    "Greedy": ("greedy", "Greedy best-first"),
}
LEVELS = {"Easy": "Greedy", "Medium": "Minimax", "Hard": "MCTS"}


class SetupScene:
    def __init__(self, app, human=False):
        self.app = app
        self.human = human
        self.t = 0.0
        self.bg = A.image("duel.jpg", (C.SCREEN_W, C.SCREEN_H))
        self.dim = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
        self.dim.fill((6, 10, 20, 170))
        names = list(AI_INFO)
        if human:
            self.left = None
            self.right = Picker((1000, 600, 420, 76), "Difficulty", list(LEVELS), 1, C.AMBER)
        else:
            self.left = Picker((180, 600, 420, 76), "Player 1 (cyan)", names, 0, C.CYAN)
            self.right = Picker((1000, 600, 420, 76), "Player 2 (amber)", names, 1, C.AMBER)
        self.speed = Picker((440, 720, 230, 70), "Ball speed", ["1x", "2x", "4x"], 0, C.MUTED)
        self.vision = Picker((685, 720, 230, 70), "AI vision lines", ["On", "Off"], 0, C.MUTED)
        self.breaker = Picker((930, 720, 230, 70), "Who breaks", ["Player 1", "Player 2", "Random"], 0, C.MUTED)
        self.start = Button((620, 812, 360, 66), "Start match", accent=C.GREEN, on_click=self.go, big=True)
        self.back = Button((40, 30, 170, 52), "Back", accent=C.MUTED, on_click=self.go_back)
        self.widgets = [w for w in (self.left, self.right, self.speed, self.vision, self.breaker) if w]
        self._av = {}

    def av(self, kind, col):
        k = (kind, col)
        if k not in self._av:
            self._av[k] = avatar_surface(kind, col, 220)
        return self._av[k]

    def players(self):
        if self.human:
            ai = LEVELS[self.right.value]
            kind, sub = AI_INFO[ai]
            return [{"kind": "human", "agent": None, "name": "You", "avatar": "human", "sub": "Human player"},
                    {"kind": "ai", "agent": ai, "name": ai, "avatar": kind, "sub": sub}]
        out = []
        for pk in (self.left, self.right):
            kind, sub = AI_INFO[pk.value]
            out.append({"kind": "ai", "agent": pk.value, "name": pk.value, "avatar": kind, "sub": sub})
        if out[0]["name"] == out[1]["name"]:
            out[0]["name"] += " A"
            out[1]["name"] += " B"
        return out

    def go(self):
        from .match import MatchScene
        b = {"Player 1": 0, "Player 2": 1}.get(self.breaker.value, random.randint(0, 1))
        sp = int(self.speed.value[0])
        self.app.switch(MatchScene(self.app, self.players(), sp, self.vision.value == "On", b))

    def go_back(self):
        from .menu import MenuScene
        self.app.switch(MenuScene(self.app))

    def handle(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for w in self.widgets + [self.start, self.back]:
                if w.click(e.pos, self.app.sounds):
                    return
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_RETURN:
                self.go()
            elif e.key == pygame.K_ESCAPE:
                self.go_back()

    def update(self, dt):
        self.t += dt
        mouse = self.app.mouse()
        for w in self.widgets + [self.start, self.back]:
            w.update(dt, mouse, self.app.sounds)

    def draw(self, screen):
        if self.bg:
            screen.blit(self.bg, (0, 0))
        screen.blit(self.dim, (0, 0))
        title = "Human vs AI" if self.human else "AI vs AI"
        A.text(screen, title, "display", 64, C.INK, (C.SCREEN_W / 2, 70), "midtop", glow=C.CYAN, glow_strength=0.7)
        A.text(screen, "Choose the players", "body", 22, C.MUTED, (C.SCREEN_W / 2, 150), "midtop")
        pl = self.players()
        for i, (p, cx) in enumerate(zip(pl, (390, 1210))):
            col = (C.CYAN, C.AMBER)[i]
            g = self.app.fx_glow(col, 150)
            screen.blit(g, (cx - 150, 380 - 150), special_flags=pygame.BLEND_ADD)
            img = self.av(p["avatar"], col)
            screen.blit(img, img.get_rect(center=(cx, 380)))
            pygame.draw.circle(screen, col, (cx, 380), 112, 3)
            A.text(screen, p["name"], "bold", 34, C.INK, (cx, 506), "midtop")
            A.text(screen, p["sub"], "body", 18, C.MUTED, (cx, 548), "midtop")
        A.text(screen, "VS", "display", 72, C.INK, (C.SCREEN_W / 2, 380), "center", glow=C.AMBER)
        if self.human:
            A.text(screen, "You play with the mouse", "body", 18, C.MUTED, (390, 640), "center")
        for w in self.widgets:
            w.draw(screen)
        self.start.draw(screen)
        self.back.draw(screen)

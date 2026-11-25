"""Rules, controls and the algorithms at a glance."""
import pygame

from .. import config as C
from ..render import assets as A
from ..render.ui import Button

CARDS = [
    ("Rules", C.CYAN, [
        "Both players share one table.",
        "Each has a 60 s clock; it runs only",
        "while that player thinks and aims.",
        "Any ball = 1 point, the 8-ball = 3.",
        "Foul (scratch or no contact):",
        "-1 point, -5 s, rival gets ball-in-hand.",
        "Pot a ball and you shoot again.",
        "Ends when the table is clear or",
        "both clocks reach zero.",
    ]),
    ("Controls", C.AMBER, [
        "Mouse: aim the cue.",
        "Hold left button, drag away: power.",
        "Release: shoot.  Right click: cancel.",
        "Arrows: fine aim (Shift = faster).",
        "Up/Down: power, Space: shoot.",
        "V: AI vision lines on/off.",
        "F: ball speed 1x / 2x / 4x.",
        "P or Esc: pause.  M: mute.",
        "F11: fullscreen.",
    ]),
    ("Algorithms", C.GREEN, [
        "Minimax + alpha-beta: AI player 1.",
        "MCTS (UCB1): AI player 2.",
        "A*: cheapest order to clear balls.",
        "Greedy best-first: the Easy AI.",
        "BFS: ball-in-hand placement.",
        "DFS / DLS: bank shots (2 cushions).",
        "IDDFS: kick shots and time control.",
        "Bidirectional: combination shots.",
        "Ghost ball: aiming every pot.",
    ]),
]


class HowToScene:
    def __init__(self, app):
        self.app = app
        self.bg = A.image("aim.jpg", (C.SCREEN_W, C.SCREEN_H))
        self.dim = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
        self.dim.fill((6, 10, 20, 205))
        self.back = Button((40, 30, 170, 52), "Back", accent=C.MUTED, on_click=self.go_back)

    def go_back(self):
        from .menu import MenuScene
        self.app.switch(MenuScene(self.app))

    def handle(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.back.click(e.pos, self.app.sounds)
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_RETURN):
            self.go_back()

    def update(self, dt):
        self.back.update(dt, self.app.mouse(), self.app.sounds)

    def draw(self, screen):
        if self.bg:
            screen.blit(self.bg, (0, 0))
        screen.blit(self.dim, (0, 0))
        A.text(screen, "How to play", "display", 60, C.INK, (C.SCREEN_W / 2, 60), "midtop", glow=C.CYAN, glow_strength=0.6)
        for i, (title, col, lines) in enumerate(CARDS):
            x = 90 + i * 480
            A.panel(screen, (x, 190, 450, 560), fill=(10, 18, 34), edge=col, radius=20, alpha=235, width=2)
            A.text(screen, title, "bold", 32, col, (x + 32, 216))
            y = 280
            for ln in lines:
                A.text(screen, ln, "body", 19, C.INK, (x + 32, y))
                y += 48
        self.back.draw(screen)

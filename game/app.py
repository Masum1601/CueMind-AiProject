"""The application shell: window, loading screen, scene switching with fades."""
import math
import os
import sys
import threading

import numpy as np
import pygame

from . import config as C
from .render import assets as A


def warmup_all():
    """Compile every numba kernel once (cached on disk afterwards)."""
    from . import physics, shots
    from .render.balls import BallSprites
    physics.warmup()
    t = physics.rack(np.random.default_rng(0))
    t.strike(0.0, 1500.0)
    t.run_to_rest()
    shots.direct_shots(t)
    shots.combo_shots(t)
    shots.bank_shots(t)
    bs = BallSprites(C.BALL_R)
    bs.orient[3] = np.eye(3)
    bs.sprite(3)
    bs.orient[11] = np.eye(3)
    bs.sprite(11)


class App:
    def __init__(self, headless=False):
        sys.setswitchinterval(0.002)     # keep the screen smooth while the AI thinks in its thread
        pygame.init()
        flags = 0 if headless else (pygame.SCALED | pygame.RESIZABLE)
        try:
            self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H), flags, vsync=1)
        except Exception:
            self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H), flags)
        pygame.display.set_caption("CueMind - 60-Second Rack Attack Duel")
        self.clock = pygame.time.Clock()
        self.running = True
        self.scene = None
        self.next_scene = None
        self.fade = 0.0
        self.fade_dir = 0
        self._glows = {}
        from .render.sound import Sounds
        self.sounds = Sounds()
        self.art = None

    def fx_glow(self, color, r):
        k = (color, r)
        if k not in self._glows:
            self._glows[k] = A.radial_glow(max(2, r), color, 2.2, 160)
        return self._glows[k]

    def mouse(self):
        return pygame.mouse.get_pos()

    def quit(self):
        self.running = False

    def switch(self, scene):
        self.next_scene = scene
        self.fade_dir = 1

    # ------------------------------------------------------------ loading
    def loading(self):
        done = {"ok": False, "err": None}

        def work():
            try:
                warmup_all()
            except Exception as e:  # keep going with whatever compiled
                done["err"] = e
            done["ok"] = True

        th = threading.Thread(target=work, daemon=True)
        th.start()
        bg = A.image("hero.jpg", (C.SCREEN_W, C.SCREEN_H))
        dim = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
        dim.fill((4, 8, 16, 215))
        t = 0.0
        while not done["ok"] and self.running:
            dt = self.clock.tick(30) / 1000.0
            t += dt
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
            if bg:
                self.screen.blit(bg, (0, 0))
            self.screen.blit(dim, (0, 0))
            A.text(self.screen, "CueMind", "display", 96, C.INK, (C.SCREEN_W / 2, 330), "center", glow=C.CYAN)
            A.text(self.screen, "Warming up the physics engine and AI", "body", 22, C.MUTED,
                   (C.SCREEN_W / 2, 420), "center")
            A.text(self.screen, "(the first launch compiles everything once, then it starts instantly)", "body", 16,
                   C.MUTED, (C.SCREEN_W / 2, 452), "center")
            for k in range(8):
                a = t * 3 + k * math.pi / 4
                x = C.SCREEN_W / 2 + math.cos(a) * 34
                y = 540 + math.sin(a) * 34
                pygame.draw.circle(self.screen, A.mix(C.CYAN, C.AMBER, k / 7), (int(x), int(y)), 4 + k % 3)
            pygame.display.flip()
        th.join(timeout=0.1)
        from .render.tablegfx import TableArt
        from .render.balls import BallSprites, _rot
        try:
            icon = BallSprites(15)
            icon.orient[8] = _rot((0.0, 1.0, 0.0), -1.2) @ np.eye(3)
            pygame.display.set_icon(icon.sprite(8))
        except Exception:
            pass
        self.art = TableArt()

    # ------------------------------------------------------------ loop
    def run(self):
        self.loading()
        from .scenes.menu import MenuScene
        self.scene = MenuScene(self)
        while self.running:
            dt = min(self.clock.tick(C.FPS) / 1000.0, 1 / 20)
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
                elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                elif e.type == pygame.KEYDOWN and e.key == pygame.K_m:
                    self.sounds.enabled = not self.sounds.enabled
                    self.sounds.music(self.sounds.enabled)
                elif self.fade_dir == 0:
                    self.scene.handle(e)
            self.step(dt)
            pygame.display.flip()
        pygame.quit()

    def step(self, dt):
        if self.fade_dir == 1:
            self.fade = min(1.0, self.fade + dt * 4)
            if self.fade >= 1.0 and self.next_scene is not None:
                self.scene = self.next_scene
                self.next_scene = None
                self.fade_dir = -1
        elif self.fade_dir == -1:
            self.fade = max(0.0, self.fade - dt * 4)
            if self.fade <= 0:
                self.fade_dir = 0
        self.scene.update(dt)
        self.scene.draw(self.screen)
        if self.fade > 0:
            s = pygame.Surface((C.SCREEN_W, C.SCREEN_H))
            s.fill((2, 4, 10))
            s.set_alpha(int(255 * self.fade))
            self.screen.blit(s, (0, 0))

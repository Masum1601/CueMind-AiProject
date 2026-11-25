"""Particles, shockwaves, floating text, pocket drops, ball trails and screen shake."""
import math
import random
from collections import deque

import pygame

from .. import config as C
from . import assets as A


class Effects:
    def __init__(self):
        self.particles = []
        self.rings = []
        self.texts = []
        self.drops = []
        self.trails = {}
        self.shake = 0.0
        self._glows = {}

    def glow(self, color, r):
        key = (color, r)
        if key not in self._glows:
            self._glows[key] = A.radial_glow(r, color, power=2.0)
        return self._glows[key]

    # ------------------------------------------------------------ spawners
    def sparks(self, x, y, color, n=10, speed=160.0, life=0.45):
        for _ in range(n):
            a = random.uniform(0, 2 * math.pi)
            s = random.uniform(0.3, 1.0) * speed
            self.particles.append([x, y, math.cos(a) * s, math.sin(a) * s, life, life, color, random.choice((3, 4, 5))])

    def ring(self, x, y, color, r0=6, r1=46, life=0.35, width=3):
        self.rings.append([x, y, r0, r1, life, life, color, width])

    def float_text(self, x, y, s, color, size=34, life=1.2):
        self.texts.append([x, y, s, color, size, life, life])

    def drop(self, sprite, x, y, px, py):
        self.drops.append([sprite, x, y, px, py, 0.0])

    def add_shake(self, amount):
        self.shake = min(14.0, self.shake + amount)

    def trail(self, n, x, y, speed):
        q = self.trails.setdefault(n, deque(maxlen=10))
        if speed > 520:
            q.append((x, y, speed))
        elif q:
            q.popleft()

    # ------------------------------------------------------------ update + draw
    def update(self, dt):
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[2] *= 0.90
            p[3] *= 0.90
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]
        for r in self.rings:
            r[4] -= dt
        self.rings = [r for r in self.rings if r[4] > 0]
        for t in self.texts:
            t[1] -= 38 * dt
            t[5] -= dt
        self.texts = [t for t in self.texts if t[5] > 0]
        for d in self.drops:
            d[5] += dt / 0.32
        self.drops = [d for d in self.drops if d[5] < 1.0]
        self.shake *= 0.86 if self.shake > 0.2 else 0.0

    def offset(self):
        if self.shake <= 0.2:
            return (0, 0)
        return (random.uniform(-1, 1) * self.shake, random.uniform(-1, 1) * self.shake)

    def draw_under(self, screen):
        for n, q in self.trails.items():
            if len(q) < 2:
                continue
            pts = list(q)
            for i in range(1, len(pts)):
                a = i / len(pts)
                col = (int(120 * a), int(200 * a), int(230 * a))
                pygame.draw.line(screen, col, pts[i - 1][:2], pts[i][:2], max(1, int(6 * a)))
        for d in self.drops:
            spr, x, y, px, py, t = d
            k = A.ease_in_out(t)
            cx, cy = A.lerp(x, px, k), A.lerp(y, py, k)
            sc = 1.0 - 0.55 * k
            img = pygame.transform.smoothscale(spr, (max(2, int(spr.get_width() * sc)), max(2, int(spr.get_height() * sc))))
            img.set_alpha(int(255 * (1 - k * 0.85)))
            screen.blit(img, img.get_rect(center=(cx, cy)))

    def draw_over(self, screen):
        for p in self.particles:
            a = p[4] / p[5]
            g = self.glow(p[6], p[7] * 2)
            g2 = g.copy()
            g2.set_alpha(int(255 * a))
            screen.blit(g2, (p[0] - p[7] * 2, p[1] - p[7] * 2), special_flags=pygame.BLEND_ADD)
        for r in self.rings:
            x, y, r0, r1, life, mx, col, w = r
            t = 1 - life / mx
            rad = A.lerp(r0, r1, A.ease_out(t))
            s = pygame.Surface((int(rad * 2 + 8), int(rad * 2 + 8)), pygame.SRCALPHA)
            pygame.draw.circle(s, (*col, int(220 * (1 - t))), (s.get_width() // 2, s.get_height() // 2), int(rad), w)
            screen.blit(s, (x - s.get_width() / 2, y - s.get_height() / 2))
        for t in self.texts:
            x, y, s, col, size, life, mx = t
            k = 1 - life / mx
            pop = 1.0 + 0.35 * max(0.0, 1 - k * 6)
            alpha = int(255 * min(1.0, life / mx * 2.2))
            A.text(screen, s, "black", int(size * pop), col, (x, y), "center", glow=col, alpha=alpha)

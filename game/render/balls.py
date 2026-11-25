"""Real-time 3D balls.

Every ball is drawn per pixel as a lit sphere: for each pixel we know the
sphere's surface normal, rotate it into the ball's own frame (so numbers and
stripes roll with the ball), look up the colour (base, stripe band, number
disc, digit) and shade it with diffuse light, a sharp specular highlight and a
soft cool reflection. Drawn 3x larger and smoothed down for clean edges.

Rolling: a ball moving by d rotates by |d| / r around the axis (dy, -dx, 0)
(x right, y down, z into the screen), so the top of the ball moves forwards.
"""
import math

import numpy as np
import pygame

from .. import config as C
from ..physics import njit
from . import assets as A

SS = 3  # supersampling
COS_DISC = math.cos(0.43)
SIN_DISC = math.sin(0.43)


@njit(cache=True)
def _shade(n, diffuse, spec, rim, M, base, stripe, number, glyph, out):
    G = glyph.shape[0]
    for k in range(n.shape[1]):
        n0 = n[0, k]
        n1 = n[1, k]
        n2 = n[2, k]
        qx = M[0, 0] * n0 + M[1, 0] * n1 + M[2, 0] * n2
        qy = M[0, 1] * n0 + M[1, 1] * n1 + M[2, 1] * n2
        qz = M[0, 2] * n0 + M[1, 2] * n1 + M[2, 2] * n2
        r = base[0]
        g = base[1]
        b = base[2]
        if stripe and abs(qz) > 0.50:
            r, g, b = 0.96, 0.95, 0.91
        if number > 0:
            for sgn in (1.0, -1.0):
                if qx * sgn > COS_DISC:
                    r, g, b = 0.96, 0.95, 0.91
                    u = -sgn * qy / SIN_DISC
                    v = qz / SIN_DISC
                    gx = int((u * 0.95 + 1.0) * 0.5 * (G - 1))
                    gy = int((v * 0.95 + 1.0) * 0.5 * (G - 1))
                    if 0 <= gx < G and 0 <= gy < G:
                        ink = glyph[gx, gy]
                        r = r * (1 - ink) + 0.06 * ink
                        g = g * (1 - ink) + 0.06 * ink
                        b = b * (1 - ink) + 0.08 * ink
        d = diffuse[k]
        s = spec[k]
        e = rim[k] * 0.20
        rr = r * d + s + 0.55 * e
        gg = g * d + s + 0.75 * e
        bb = b * d + s + 0.95 * e
        out[k, 0] = min(255.0, max(0.0, rr * 255.0))
        out[k, 1] = min(255.0, max(0.0, gg * 255.0))
        out[k, 2] = min(255.0, max(0.0, bb * 255.0))


def _rot(axis, angle):
    x, y, z = axis
    c, s = math.cos(angle), math.sin(angle)
    t = 1 - c
    return np.array([[t * x * x + c, t * x * y - s * z, t * x * z + s * y],
                     [t * x * y + s * z, t * y * y + c, t * y * z - s * x],
                     [t * x * z - s * y, t * y * z + s * x, t * z * z + c]])


class BallSprites:
    def __init__(self, radius_px, ss=None):
        self.r = radius_px
        self.D = int(math.ceil(radius_px * 2)) + 2
        ss = SS if ss is None else ss
        self.S = self.D * ss
        c = (self.S - 1) / 2.0
        rr = radius_px * ss
        y, x = np.mgrid[0:self.S, 0:self.S].astype(np.float64)
        px = (x - c) / rr
        py = (y - c) / rr
        d2 = px * px + py * py
        inside = d2 <= 1.0
        self.mask = inside
        pz = -np.sqrt(np.clip(1 - d2, 0, 1))          # facing the viewer
        self.n = np.stack([px[inside], py[inside], pz[inside]], axis=0)   # 3 x P
        L = np.array([-0.48, -0.58, -0.66])
        L /= np.linalg.norm(L)
        V = np.array([0.0, 0.0, -1.0])
        Hh = (L + V) / np.linalg.norm(L + V)
        nl = np.clip(L @ self.n, 0, 1)
        nh = np.clip(Hh @ self.n, 0, 1)
        self.diffuse = 0.30 + 0.78 * nl
        self.spec = 1.05 * nh ** 70 + 0.18 * nh ** 8
        rim = np.clip(1.0 + self.n[2], 0, 1)               # 0 facing us, 1 at the edge
        self.rim = rim ** 2.2
        # soft anti-aliased alpha edge
        edge = np.clip((1.0 - np.sqrt(d2)) * rr / 1.2, 0, 1)
        self.alpha = (edge * 255).astype(np.uint8)
        self._out = np.zeros((self.n.shape[1], 3))
        self.glyphs = {}
        self.orient = {}
        self.cache = {}
        self.shadow = self._shadow()

    def _glyph(self, n):
        if n in self.glyphs:
            return self.glyphs[n]
        G = 96
        surf = pygame.Surface((G, G))
        surf.fill((0, 0, 0))
        f = A.font("black", 58 if n < 10 else 48)
        img = f.render(str(n), True, (255, 255, 255))
        surf.blit(img, img.get_rect(center=(G // 2, G // 2 + 2)))
        arr = np.ascontiguousarray(pygame.surfarray.array3d(surf)[:, :, 0].astype(np.float64) / 255.0)   # [x, y]
        self.glyphs[n] = arr
        return arr

    def _shadow(self):
        d = int(self.r * 3.4)
        s = pygame.Surface((d, d), pygame.SRCALPHA)
        y, x = np.mgrid[0:d, 0:d].astype(np.float32)
        rr = np.sqrt(((x - d / 2) / (d / 2)) ** 2 + ((y - d / 2) / (d / 2 * 0.82)) ** 2)
        a = np.clip(1 - rr, 0, 1) ** 1.6 * 150
        al = pygame.surfarray.pixels_alpha(s)
        al[:] = a.T.astype(np.uint8)
        del al
        return s

    def reset(self, n, rng):
        q, _ = np.linalg.qr(rng.normal(size=(3, 3)))
        self.orient[n] = q
        self.cache.pop(n, None)

    def roll(self, n, dx, dy):
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            return
        axis = (dy / dist, -dx / dist, 0.0)
        self.orient[n] = _rot(axis, dist / C.BALL_R) @ self.orient[n]
        self.cache.pop(n, None)

    def sprite(self, n):
        if n in self.cache:
            return self.cache[n]
        M = self.orient.get(n)
        if M is None:
            M = np.eye(3)
            self.orient[n] = M
        base = np.array(C.BALL_COLORS[n], dtype=np.float64) / 255.0
        glyph = self._glyph(n) if n > 0 else self._glyph(1)
        out = self._out
        _shade(self.n, self.diffuse, self.spec, self.rim, M, base, 9 <= n <= 15, n, glyph, out)
        img = np.zeros((self.S, self.S, 3), dtype=np.uint8)
        img[self.mask] = out.astype(np.uint8)
        surf = pygame.Surface((self.S, self.S), pygame.SRCALPHA)
        pygame.surfarray.pixels3d(surf)[:] = img.transpose(1, 0, 2)
        al = pygame.surfarray.pixels_alpha(surf)
        a = np.zeros((self.S, self.S), dtype=np.uint8)
        a[self.mask] = self.alpha[self.mask]
        al[:] = a.T
        del al
        out = pygame.transform.smoothscale(surf, (self.D, self.D))
        self.cache[n] = out
        return out

    def big(self, n, size, M=None):
        """A large one-off render (menu logo ball)."""
        bs = BallSprites(size / 2)
        bs.orient[n] = M if M is not None else self.orient.get(n, np.eye(3))
        return bs.sprite(n)

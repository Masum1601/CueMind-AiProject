"""The table, painted procedurally: walnut rails, woven cloth, cushions, chrome pockets, LED glow."""
import math

import numpy as np
import pygame

from .. import config as C
from ..physics import SEGMENTS
from . import assets as A

TX, TY = C.TABLE_X, C.TABLE_Y
RAIL = C.RAIL
CUSH = 15          # visible cushion width


def to_screen(x, y):
    return (TX + x, TY + y)


def _noise(w, h, scale, rng, octaves=4):
    """Smooth value noise in [0, 1], shape (w, h)."""
    out = np.zeros((w, h), dtype=np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        gw = max(2, int(w / scale * (2 ** o)) + 2)
        gh = max(2, int(h / scale * (2 ** o)) + 2)
        grid = (rng.random((gw, gh)) * 255).astype(np.uint8)
        s = pygame.surfarray.make_surface(np.stack([grid] * 3, axis=-1))
        s = pygame.transform.smoothscale(s, (w, h))
        out += pygame.surfarray.array3d(s)[:, :, 0].astype(np.float32) / 255.0 * amp
        total += amp
        amp *= 0.5
    return out / total


def _aniso(w, h, sx, sy, rng):
    gw, gh = max(2, int(w / sx) + 2), max(2, int(h / sy) + 2)
    grid = (rng.random((gw, gh)) * 255).astype(np.uint8)
    s = pygame.surfarray.make_surface(np.stack([grid] * 3, axis=-1))
    s = pygame.transform.smoothscale(s, (w, h))
    return pygame.surfarray.array3d(s)[:, :, 0].astype(np.float32) / 255.0


def wood_surface(w, h, rng):
    """Walnut with long grain running along x."""
    warp = _aniso(w, h, 260, 40, rng)
    streak = _aniso(w, h, 120, 1.6, rng)
    pores = _aniso(w, h, 9, 1.2, rng)
    y = np.arange(h, dtype=np.float32)[None, :]
    grain = np.sin(y * 0.30 + warp * 9.0) * 0.5 + 0.5
    t = np.clip(0.18 + 0.36 * grain ** 1.6 + 0.42 * streak - 0.12 * pores, 0, 1)[:, :, None]
    dark = np.array([30, 15, 9], dtype=np.float32)
    light = np.array([104, 58, 30], dtype=np.float32)
    rgb = dark * (1 - t) + light * t
    return pygame.surfarray.make_surface(rgb.clip(0, 255).astype(np.uint8))


def felt_surface(w, h, rng):
    fine = _noise(w, h, 2.2, rng, 2)
    mott = _noise(w, h, 140, rng, 3)
    base = np.array([16, 94, 116], dtype=np.float32)
    x = (np.arange(w, dtype=np.float32)[:, None] - w / 2) / (w / 2)
    y = (np.arange(h, dtype=np.float32)[None, :] - h / 2) / (h / 2)
    light = 1.10 - 0.28 * np.clip(x * x * 0.55 + y * y * 0.9, 0, 1.6)
    # ambient occlusion next to the cushions
    ex = np.minimum(np.arange(w)[:, None], w - 1 - np.arange(w)[:, None]).astype(np.float32)
    ey = np.minimum(np.arange(h)[None, :], h - 1 - np.arange(h)[None, :]).astype(np.float32)
    edge = np.minimum(ex, ey)
    ao = 1.0 - 0.32 * np.exp(-edge / 10.0)
    f = (light * ao)[:, :, None]
    rgb = base * f + (fine[:, :, None] - 0.5) * 16 + (mott[:, :, None] - 0.5) * 8
    return pygame.surfarray.make_surface(rgb.clip(0, 255).astype(np.uint8))


class TableArt:
    def __init__(self, seed=7):
        rng = np.random.default_rng(seed)
        self.background = self._background()
        self.table = self._table(rng)
        self.glow = {0: self._glow(C.CYAN), 1: self._glow(C.AMBER)}

    # ------------------------------------------------------------ background
    def _background(self):
        W, H = C.SCREEN_W, C.SCREEN_H
        bg = pygame.Surface((W, H))
        img = A.image("hero.jpg", (W, H))
        if img:
            img = A.blur(img, 14)
            bg.blit(img, (0, 0))
            dim = pygame.Surface((W, H))
            dim.fill((6, 9, 18))
            dim.set_alpha(205)
            bg.blit(dim, (0, 0))
        else:
            bg.blit(A.vgradient((W, H), (10, 16, 32), (4, 6, 12)), (0, 0))
        for cx, cy, col in ((0, 120, C.CYAN), (W, 760, C.AMBER)):
            g = A.radial_glow(520, col, power=2.6, alpha=40)
            bg.blit(g, (cx - 520, cy - 520), special_flags=pygame.BLEND_ADD)
        vig = pygame.Surface((W, H), pygame.SRCALPHA)
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((x - W / 2) / (W * 0.62)) ** 2 + ((y - H / 2) / (H * 0.62)) ** 2)
        a = np.clip((r - 0.6) * 1.4, 0, 1) * 200
        pygame.surfarray.pixels_alpha(vig)[:] = a.T.astype(np.uint8)
        bg.blit(vig, (0, 0))
        return bg

    def _glow(self, color):
        pad = 70
        ow, oh = int(C.FIELD_W + 2 * RAIL), int(C.FIELD_H + 2 * RAIL)
        s = pygame.Surface((ow + pad * 2, oh + pad * 2), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color, 255), (pad - 6, pad - 6, ow + 12, oh + 12), width=10, border_radius=40)
        s = A.blur(s, 10)
        s2 = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        s2.blit(s, (0, 0))
        s2.blit(s, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        return s2

    # ------------------------------------------------------------ table
    def _table(self, rng):
        W, H = int(C.FIELD_W), int(C.FIELD_H)
        ow, oh = W + 2 * RAIL, H + 2 * RAIL
        pad = 30
        surf = pygame.Surface((ow + pad * 2, oh + pad * 2), pygame.SRCALPHA)
        ox, oy = pad, pad                      # outer table corner inside surf
        fx, fy = ox + RAIL, oy + RAIL          # field corner inside surf

        # drop shadow under the whole table
        sh = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(sh, (0, 0, 0, 200), (ox + 6, oy + 14, ow, oh), border_radius=34)
        surf.blit(A.blur(sh, 9), (0, 0))

        # walnut frame: grain runs along each rail
        wood = wood_surface(ow, oh, rng)
        side = pygame.transform.rotate(wood_surface(oh, RAIL + 2, rng), 90)
        wood.blit(side, (0, RAIL), (0, RAIL, RAIL + 2, oh - 2 * RAIL))
        wood.blit(pygame.transform.flip(side, True, False), (ow - RAIL - 2, RAIL), (0, RAIL, RAIL + 2, oh - 2 * RAIL))
        frame = pygame.Surface((ow, oh), pygame.SRCALPHA)
        pygame.draw.rect(frame, (255, 255, 255, 255), (0, 0, ow, oh), border_radius=30)
        wood_a = wood.convert_alpha()
        wood_a.blit(frame, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        # varnish: light from the top, darker towards the bottom
        shade = A.vgradient((ow, oh), (60, 46, 36), (0, 0, 0))
        shade.set_alpha(90)
        wood_a.blit(shade, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        surf.blit(wood_a, (ox, oy))
        # bevel lines
        pygame.draw.rect(surf, (150, 102, 66), (ox, oy, ow, oh), width=2, border_radius=30)
        pygame.draw.rect(surf, (20, 10, 6), (ox + 10, oy + 10, ow - 20, oh - 20), width=2, border_radius=22)
        pygame.draw.rect(surf, (120, 80, 50), (ox + 12, oy + 12, ow - 24, oh - 24), width=1, border_radius=20)

        # cloth
        felt = felt_surface(W + 2 * CUSH, H + 2 * CUSH, rng)
        surf.blit(felt, (fx - CUSH, fy - CUSH))

        # cushions: a darker band with a bright nose line, cut at the pockets
        cush_col = (11, 70, 88)
        nose_col = (60, 160, 180)
        cm, sm = C.CORNER_MOUTH, C.SIDE_MOUTH
        runs = [
            ((cm, 0), (W / 2 - sm, 0), (0, -1)), ((W / 2 + sm, 0), (W - cm, 0), (0, -1)),
            ((cm, H), (W / 2 - sm, H), (0, 1)), ((W / 2 + sm, H), (W - cm, H), (0, 1)),
            ((0, cm), (0, H - cm), (-1, 0)), ((W, cm), (W, H - cm), (1, 0)),
        ]
        for (x1, y1), (x2, y2), (nx, ny) in runs:
            k = CUSH + 2
            if ny:
                poly = [(x1, y1), (x2, y2), (x2 + 7, y2 + ny * k), (x1 - 7, y1 + ny * k)]
            else:
                poly = [(x1, y1), (x2, y2), (x2 + nx * k, y2 + 7), (x1 + nx * k, y1 - 7)]
            pts = [(fx + px, fy + py) for px, py in poly]
            pygame.draw.polygon(surf, cush_col, pts)
            pygame.draw.line(surf, nose_col, (fx + x1, fy + y1), (fx + x2, fy + y2), 2)
            # cushion top highlight
            a2 = (fx + x1 + nx * (k - 3), fy + y1 + ny * (k - 3))
            b2 = (fx + x2 + nx * (k - 3), fy + y2 + ny * (k - 3))
            pygame.draw.line(surf, (30, 110, 128), a2, b2, 1)

        # pockets: chrome caps on the rail and a deep hole
        for (px, py, pr), name in zip(C.POCKETS, C.POCKET_NAMES):
            cx, cy = fx + px, fy + py
            corner = pr == C.CORNER_POCKET
            cap = 44 if corner else 38
            chrome = pygame.Surface((cap * 2, cap * 2), pygame.SRCALPHA)
            for r in range(cap, 0, -1):
                t = r / cap
                c = A.mix((230, 232, 240), (70, 74, 86), t ** 0.6)
                pygame.draw.circle(chrome, (*c, 255), (cap, cap), r)
            surf.blit(chrome, (cx - cap, cy - cap))
            hole_r = int(pr + 5)
            hole = pygame.Surface((hole_r * 2 + 8, hole_r * 2 + 8), pygame.SRCALPHA)
            for r in range(hole_r + 4, 0, -1):
                t = r / (hole_r + 4)
                c = A.mix((0, 0, 0), (34, 30, 28), t ** 3)
                pygame.draw.circle(hole, (*c, 255), (hole_r + 4, hole_r + 4), r)
            surf.blit(hole, (cx - hole_r - 4, cy - hole_r - 4))

        # jaws drawn over the cloth so the pocket mouths read clearly
        for x1, y1, x2, y2 in SEGMENTS[6:]:
            pygame.draw.line(surf, cush_col, (fx + x1, fy + y1), (fx + x2, fy + y2), 8)
            pygame.draw.line(surf, (34, 112, 130), (fx + x1, fy + y1), (fx + x2, fy + y2), 1)

        # a soft gloss streak along the top rail (overhead light)
        gloss = pygame.Surface((ow, RAIL), pygame.SRCALPHA)
        for i in range(RAIL // 2):
            a = int(40 * (1 - i / (RAIL / 2)) ** 2)
            pygame.draw.line(gloss, (255, 236, 210, a), (40, 8 + i), (ow - 40, 8 + i))
        surf.blit(gloss, (ox, oy))

        # diamond sights (mother of pearl)
        def diamond(cx, cy):
            pts = [(cx, cy - 5), (cx + 4, cy), (cx, cy + 5), (cx - 4, cy)]
            pygame.draw.polygon(surf, (236, 232, 220), pts)
            pygame.draw.polygon(surf, (150, 140, 120), pts, 1)
        for k in (1, 2, 3, 5, 6, 7):
            x = fx + W * k / 8
            diamond(x, oy + RAIL / 2 - 4)
            diamond(x, oy + oh - RAIL / 2 + 4)
        for k in (1, 2, 3):
            y = fy + H * k / 4
            diamond(ox + RAIL / 2 - 4, y)
            diamond(ox + ow - RAIL / 2 + 4, y)

        # head string and spots
        hx = fx + C.HEAD_SPOT[0]
        for yy in range(int(fy + 6), int(fy + H - 6), 10):
            pygame.draw.line(surf, (40, 130, 150), (hx, yy), (hx, yy + 4), 1)
        for sx, sy in (C.HEAD_SPOT, C.FOOT_SPOT):
            pygame.draw.circle(surf, (70, 160, 178), (int(fx + sx), int(fy + sy)), 2)

        # brand plate on the rail
        plate = pygame.Rect(0, 0, 128, 20)
        plate.center = (ox + ow * 0.375, oy + oh - RAIL / 2 + 3)
        pygame.draw.rect(surf, (24, 14, 9), plate, border_radius=5)
        pygame.draw.rect(surf, (176, 140, 90), plate, width=1, border_radius=5)
        A.text(surf, "CUEMIND", "display", 14, (226, 192, 130), plate.center, "center")
        self.offset = (TX - RAIL - pad, TY - RAIL - pad)
        return surf

    def composite(self, turn_glow):
        """Background + LED glow + table baked into one opaque surface (fast to blit)."""
        if not hasattr(self, "_comp"):
            self._comp = {}
        if turn_glow not in self._comp:
            s = self.background.copy()
            if turn_glow is not None:
                s.blit(self.glow[turn_glow], (TX - RAIL - 70, TY - RAIL - 70))
            s.blit(self.table, self.offset)
            self._comp[turn_glow] = s.convert()
        return self._comp[turn_glow]

    def draw(self, screen, turn_glow=None, t=0.0):
        screen.blit(self.composite(turn_glow), (0, 0))

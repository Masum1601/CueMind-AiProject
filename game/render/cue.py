"""A turned cue stick: maple shaft, ivory ferrule, ebony forearm with accent inlays, wrap and butt."""
import math

import numpy as np
import pygame

from . import assets as A

LENGTH = 540
SCALE = 2


def _segments(accent):
    # (length in px from the tip, colour, kind)
    return [
        (4, (70, 120, 180), "tip"),
        (12, (238, 232, 214), "ferrule"),
        (300, (226, 196, 146), "shaft"),
        (6, (205, 210, 220), "metal"),
        (4, accent, "accent"),
        (124, (28, 20, 16), "forearm"),
        (4, accent, "accent"),
        (54, (34, 34, 40), "wrap"),
        (4, (205, 210, 220), "metal"),
        (24, (24, 16, 12), "butt"),
        (4, (16, 16, 18), "bumper"),
    ]


def build(accent):
    L = LENGTH * SCALE
    T = 16 * SCALE
    img = np.zeros((L, T, 4), dtype=np.float32)
    cy = (T - 1) / 2
    segs = _segments(accent)
    total = sum(s[0] for s in segs)
    col_at = np.zeros((L, 3), dtype=np.float32)
    kind_at = [""] * L
    pos = 0
    for length, col, kind in segs:
        n = int(length / total * L)
        col_at[L - pos - n:L - pos] = col
        for x in range(L - pos - n, L - pos):
            kind_at[x] = kind
        pos += n
    col_at[: L - pos] = segs[-1][1]
    x = np.arange(L, dtype=np.float32)
    half = (3.2 + (6.6 - 3.2) * (1 - x / L)) * SCALE          # thin at the tip (right)
    ys = np.arange(T, dtype=np.float32)
    rel = (ys[None, :] - cy) / half[:, None]
    inside = np.abs(rel) <= 1.0
    body = np.sqrt(np.clip(1 - rel ** 2, 0, 1))
    shade = 0.42 + 0.62 * body - 0.18 * rel
    spec = np.exp(-((rel + 0.45) / 0.16) ** 2) * 0.55
    rgb = col_at[:, None, :] * shade[:, :, None] + spec[:, :, None] * 255
    # forearm inlay points and wrap texture
    for i in range(L):
        k = kind_at[i]
        if k == "forearm":
            local = (i - kind_at.index("forearm")) / max(1, kind_at.count("forearm"))
            tip = abs(((local * 4) % 1.0) - 0.5) * 2         # 4 sharp points
            m = np.abs(rel[i]) < (1 - tip) * 0.55
            rgb[i, m] = np.array(accent, dtype=np.float32) * 0.9 * shade[i, m, None] + spec[i, m, None] * 255
        elif k == "wrap" and (i // 3) % 2 == 0:
            rgb[i] *= 0.78
    a = np.clip((1 - np.abs(rel)) * half[:, None] / 1.2, 0, 1) * inside
    img[:, :, :3] = np.clip(rgb, 0, 255)
    img[:, :, 3] = a * 255
    surf = pygame.Surface((L, T), pygame.SRCALPHA)
    pygame.surfarray.pixels3d(surf)[:] = img[:, :, :3].astype(np.uint8)
    pygame.surfarray.pixels_alpha(surf)[:] = img[:, :, 3].astype(np.uint8)
    surf = pygame.transform.smoothscale(surf, (LENGTH, 16))
    shadow = pygame.Surface((LENGTH + 40, 56), pygame.SRCALPHA)
    pygame.draw.line(shadow, (0, 0, 0, 120), (20, 28), (LENGTH + 20, 28), 9)
    shadow = A.blur(shadow, 4)
    return surf, shadow


class Cue:
    def __init__(self, accent):
        self.surf, self.shadow = build(accent)

    def draw(self, screen, tip, angle, alpha=255):
        """tip = screen point the tip sits at; the cue extends away from the aim direction."""
        deg = -math.degrees(angle)
        dx, dy = math.cos(angle), math.sin(angle)
        cx = tip[0] - dx * LENGTH / 2
        cy = tip[1] - dy * LENGTH / 2
        sh = pygame.transform.rotate(self.shadow, deg)
        sh.set_alpha(int(alpha * 0.8))
        screen.blit(sh, sh.get_rect(center=(cx + 10, cy + 16)))
        img = pygame.transform.rotozoom(self.surf, deg, 1.0)
        if alpha < 255:
            img.set_alpha(alpha)
        screen.blit(img, img.get_rect(center=(cx, cy)))

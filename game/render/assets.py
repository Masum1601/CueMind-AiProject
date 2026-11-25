"""Fonts, images and small drawing helpers (glow text, gradients, blur, rounded panels)."""
import os
import math

import numpy as np
import pygame

from .. import config as C

FONT_DIR = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
_FONT_FILES = {
    "display": ["bahnschrift.ttf"],
    "bold": ["segoeuib.ttf", "seguisb.ttf"],
    "semibold": ["seguisb.ttf", "segoeuib.ttf"],
    "black": ["seguibl.ttf", "segoeuib.ttf"],
    "body": ["segoeui.ttf"],
}
_font_cache = {}
_img_cache = {}


def font(kind, size):
    key = (kind, size)
    if key in _font_cache:
        return _font_cache[key]
    f = None
    for name in _FONT_FILES.get(kind, []):
        path = os.path.join(FONT_DIR, name)
        if os.path.exists(path):
            try:
                f = pygame.font.Font(path, size)
                break
            except Exception:
                pass
    if f is None:
        f = pygame.font.SysFont("segoe ui,arial", size, bold=kind in ("bold", "black"))
    _font_cache[key] = f
    return f


def image(name, size=None, alpha=False):
    key = (name, size)
    if key in _img_cache:
        return _img_cache[key]
    path = os.path.join(C.IMAGES, name)
    if not os.path.exists(path):
        return None
    surf = pygame.image.load(path)
    surf = surf.convert_alpha() if alpha else surf.convert()
    if size:
        surf = cover(surf, size)
    _img_cache[key] = surf
    return surf


def cover(surf, size):
    """Scale and centre-crop to fill size, like CSS object-fit: cover."""
    w, h = surf.get_size()
    s = max(size[0] / w, size[1] / h)
    scaled = pygame.transform.smoothscale(surf, (max(1, int(w * s + 0.5)), max(1, int(h * s + 0.5))))
    x = (scaled.get_width() - size[0]) // 2
    y = (scaled.get_height() - size[1]) // 2
    return scaled.subsurface((x, y, size[0], size[1])).copy()


def blur(surf, amount=8):
    w, h = surf.get_size()
    small = pygame.transform.smoothscale(surf, (max(1, w // amount), max(1, h // amount)))
    return pygame.transform.smoothscale(small, (w, h))


_text_cache = {}


def _render_text(s, kind, size, color, glow, alpha):
    key = (s, kind, size, color, glow, alpha)
    hit = _text_cache.get(key)
    if hit is not None:
        return hit
    if len(_text_cache) > 1500:
        _text_cache.clear()
    f = font(kind, size)
    img = f.render(s, True, color)
    if alpha < 255:
        img.set_alpha(alpha)
    gs = None
    if glow is not None:
        g = f.render(s, True, glow)
        pad = size
        gs = pygame.Surface((g.get_width() + pad * 2, g.get_height() + pad * 2), pygame.SRCALPHA)
        gs.blit(g, (pad, pad))
        gs = blur(gs.premul_alpha(), max(2, size // 5))
        k = int(alpha * 0.8)
        gs.fill((k, k, k, 255), special_flags=pygame.BLEND_RGBA_MULT)
    _text_cache[key] = (img, gs)
    return img, gs


def text(surface, s, kind, size, color, pos, anchor="topleft", glow=None, glow_strength=1.0, alpha=255):
    alpha = 255 if alpha >= 250 else max(0, (int(alpha) // 16) * 16)
    if glow is not None and size > 30:
        size = int(round(size / 4.0) * 4)        # animated sizes share cached glows
    img, gs = _render_text(s, kind, size, tuple(color), tuple(glow) if glow is not None else None, alpha)
    rect = img.get_rect(**{anchor: pos})
    if gs is not None:
        pad = size
        for _ in range(2 if glow_strength > 1.2 else 1):
            surface.blit(gs, (rect.x - pad, rect.y - pad), special_flags=pygame.BLEND_ADD)
    surface.blit(img, rect)
    return rect


def vgradient(size, top, bottom):
    w, h = size
    arr = np.zeros((w, h, 3), dtype=np.float32)
    t = np.linspace(0, 1, h)[None, :, None]
    arr[:] = np.array(top)[None, None, :] * (1 - t) + np.array(bottom)[None, None, :] * t
    return pygame.surfarray.make_surface(arr.clip(0, 255).astype(np.uint8))


def radial_glow(radius, color, power=2.0, alpha=255):
    """A soft round glow sprite (premultiplied for additive blending)."""
    d = radius * 2
    y, x = np.mgrid[0:d, 0:d].astype(np.float32)
    r = np.sqrt((x - radius + 0.5) ** 2 + (y - radius + 0.5) ** 2) / radius
    a = np.clip(1 - r, 0, 1) ** power * (alpha / 255.0)
    surf = pygame.Surface((d, d), pygame.SRCALPHA)
    rgb = pygame.surfarray.pixels3d(surf)
    for k in range(3):
        rgb[:, :, k] = (a.T * color[k]).astype(np.uint8)
    del rgb
    al = pygame.surfarray.pixels_alpha(surf)
    al[:] = (a.T * 255).astype(np.uint8)
    del al
    return surf


_panel_cache = {}


def panel(surface, rect, fill=C.PANEL, edge=C.PANEL_EDGE, radius=16, alpha=230, accent=None, width=1):
    r = pygame.Rect(rect)
    key = (r.size, tuple(fill), tuple(edge) if edge else None, radius, alpha, accent, width)
    s = _panel_cache.get(key)
    if s is None:
        if len(_panel_cache) > 400:
            _panel_cache.clear()
        s = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (*fill, alpha), s.get_rect(), border_radius=radius)
        if edge:
            pygame.draw.rect(s, (*edge, 255), s.get_rect(), width=width, border_radius=radius)
        if accent:
            pygame.draw.rect(s, (*accent, 255), s.get_rect(), width=2, border_radius=radius)
        _panel_cache[key] = s
    surface.blit(s, r)


_glow_rect_cache = {}


def glow_rect(surface, rect, color, strength=1.0, radius=20, spread=30):
    """A soft coloured halo around a rectangle (cached, alpha-modulated)."""
    r = pygame.Rect(rect)
    key = (r.size, tuple(color), radius, spread)
    levels = _glow_rect_cache.get(key)
    if levels is None:
        g = pygame.Surface((r.w + spread * 2, r.h + spread * 2), pygame.SRCALPHA)
        pygame.draw.rect(g, (*color, 110), (spread, spread, r.w, r.h), border_radius=radius)
        g = blur(g.premul_alpha(), 10)
        base = pygame.Surface(g.get_size())
        base.fill((0, 0, 0))
        base.blit(g, (0, 0), special_flags=pygame.BLEND_ADD)      # opaque, black = no light
        levels = []
        for i in range(1, 13):
            k = int(255 * i / 12)
            s = base.copy()
            s.fill((k, k, k), special_flags=pygame.BLEND_MULT)
            levels.append(s.convert())
        _glow_rect_cache[key] = levels
    i = int(max(0.0, min(1.0, strength)) * 12 + 0.5)
    if i > 0:
        surface.blit(levels[i - 1], (r.x - spread, r.y - spread), special_flags=pygame.BLEND_ADD)


def keycap(surface, key, label, pos, color=C.MUTED):
    """A small 3D key chip followed by its label; returns the right edge x."""
    x, y = pos
    kw = max(26, font("bold", 13).size(key)[0] + 16)
    r = pygame.Rect(int(x), int(y) - 12, kw, 24)
    panel(surface, r.move(0, 2), fill=(6, 10, 20), edge=None, radius=6, alpha=255)
    panel(surface, r, fill=(26, 38, 64), edge=(72, 96, 136), radius=6, alpha=255)
    pygame.draw.line(surface, (104, 132, 176), (r.x + 5, r.y + 2), (r.right - 6, r.y + 2))
    text(surface, key, "bold", 13, C.INK, r.center, "center")
    rr = text(surface, label, "body", 14, color, (r.right + 8, y), "midleft")
    return rr.right


def circle_crop(surf, d):
    img = pygame.transform.smoothscale(surf, (d, d)).convert_alpha()
    mask = pygame.Surface((d, d), pygame.SRCALPHA)
    pygame.draw.circle(mask, (255, 255, 255, 255), (d // 2, d // 2), d // 2)
    img.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return img


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    t = max(0.0, min(1.0, t))
    return 3 * t * t - 2 * t * t * t


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def arc(surface, color, center, radius, frac, width=6, start=-math.pi / 2):
    """A smooth arc (clock ring) drawn as short line pieces."""
    if frac <= 0:
        return
    n = max(8, int(90 * frac))
    pts = [(center[0] + math.cos(start + 2 * math.pi * frac * i / n) * radius,
            center[1] + math.sin(start + 2 * math.pi * frac * i / n) * radius) for i in range(n + 1)]
    pygame.draw.lines(surface, color, False, pts, width)
    for p in (pts[0], pts[-1]):
        pygame.draw.circle(surface, color, (int(p[0]), int(p[1])), width // 2)

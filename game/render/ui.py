"""Buttons and option pickers with hover animation and glow."""
import pygame

from .. import config as C
from . import assets as A


class Button:
    def __init__(self, rect, label, sub="", accent=C.CYAN, on_click=None, big=False):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.sub = sub
        self.accent = accent
        self.on_click = on_click
        self.big = big
        self.hover = 0.0
        self.was_hover = False
        self.enabled = True

    def update(self, dt, mouse, sounds=None):
        inside = self.enabled and self.rect.collidepoint(mouse)
        if inside and not self.was_hover and sounds:
            sounds.play("hover")
        self.was_hover = inside
        target = 1.0 if inside else 0.0
        self.hover += (target - self.hover) * min(1.0, dt * 12)

    def click(self, pos, sounds=None):
        if self.enabled and self.rect.collidepoint(pos):
            if sounds:
                sounds.play("click")
            if self.on_click:
                self.on_click()
            return True
        return False

    def draw(self, screen):
        h = self.hover
        r = self.rect.inflate(int(10 * h), int(4 * h))
        if h > 0.02:
            A.glow_rect(screen, self.rect, self.accent, h * 0.8, 18)
        fill = A.mix((14, 22, 40), (24, 38, 66), h)
        A.panel(screen, r, fill=fill, edge=A.mix(C.PANEL_EDGE, self.accent, h), radius=16, alpha=235, width=2)
        bar = pygame.Rect(r.x, r.y + 12, 5, r.h - 24)
        pygame.draw.rect(screen, self.accent, bar, border_radius=3)
        col = C.INK if self.enabled else C.MUTED
        if self.sub:
            A.text(screen, self.label, "bold", 30 if self.big else 24, col, (r.x + 30, r.centery - 2), "bottomleft")
            A.text(screen, self.sub, "body", 17, C.MUTED, (r.x + 30, r.centery + 2), "topleft")
        else:
            A.text(screen, self.label, "bold", 26 if self.big else 22, col, (r.x + 30, r.centery), "midleft")
        A.text(screen, "›", "bold", 34, A.mix(C.MUTED, self.accent, h), (r.right - 24 + 4 * h, r.centery - 2), "center")


class Picker:
    """A labelled value you cycle through with clicks or the arrows."""

    def __init__(self, rect, title, options, index=0, accent=C.CYAN, on_change=None):
        self.rect = pygame.Rect(rect)
        self.title = title
        self.options = options
        self.index = index
        self.accent = accent
        self.on_change = on_change
        self.hover = 0.0

    @property
    def value(self):
        return self.options[self.index]

    def update(self, dt, mouse, sounds=None):
        target = 1.0 if self.rect.collidepoint(mouse) else 0.0
        self.hover += (target - self.hover) * min(1.0, dt * 12)

    def click(self, pos, sounds=None):
        if not self.rect.collidepoint(pos):
            return False
        step = -1 if pos[0] < self.rect.x + 56 else 1
        self.index = (self.index + step) % len(self.options)
        if sounds:
            sounds.play("click")
        if self.on_change:
            self.on_change(self.value)
        return True

    def draw(self, screen):
        r = self.rect
        A.panel(screen, r, fill=A.mix((14, 22, 40), (22, 34, 60), self.hover),
                edge=A.mix(C.PANEL_EDGE, self.accent, self.hover), radius=14, alpha=230, width=2)
        A.text(screen, self.title.upper(), "semibold", 14, C.MUTED, (r.centerx, r.y + 10), "midtop")
        A.text(screen, str(self.value), "bold", 24, C.INK, (r.centerx, r.bottom - 14), "midbottom")
        A.text(screen, "‹", "bold", 32, self.accent, (r.x + 24, r.centery + 2), "center")
        A.text(screen, "›", "bold", 32, self.accent, (r.right - 24, r.centery + 2), "center")

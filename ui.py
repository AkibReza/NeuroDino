"""
ui.py
=====
Small reusable Pygame widgets and drawing helpers. Kept deliberately minimal so
the rest of the UI code reads clearly. The built-in default font is used
(pygame.font.Font(None, size)) so the app never depends on system fonts being
installed.
"""
from __future__ import annotations

import pygame

import config

_FONT_CACHE: dict[int, pygame.font.Font] = {}


def get_font(size: int) -> pygame.font.Font:
    if size not in _FONT_CACHE:
        _FONT_CACHE[size] = pygame.font.Font(None, size)
    return _FONT_CACHE[size]


def draw_text(surface, text, x, y, size=18, color=config.COL_TEXT,
              center=False, right=False) -> pygame.Rect:
    font = get_font(size)
    img = font.render(str(text), True, color)
    rect = img.get_rect()
    if center:
        rect.center = (x, y)
    elif right:
        rect.topright = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(img, rect)
    return rect


def shade(color, factor: float):
    """Lighten (factor>1) or darken (factor<1) an RGB colour, clamped 0-255."""
    return tuple(max(0, min(255, int(c * factor))) for c in color)


def dino_color(slot: int) -> tuple[int, int, int]:
    """A distinct fixed colour for each of the 10 dinosaurs in a lane."""
    return config.DINO_COLORS[slot % len(config.DINO_COLORS)]


def lane_dino_color(lane: int, slot: int):
    """A distinct tint within a lane's colour family (fallback for backwards compatibility)."""
    return dino_color(slot)


class Button:
    def __init__(self, label, x, y, w, h, callback, size=18,
                 toggle=False, group=None):
        self.label = label
        self.rect = pygame.Rect(x, y, w, h)
        self.callback = callback
        self.size = size
        self.hover = False
        self.active = False        # for toggle / selected state
        self.enabled = True
        self.toggle = toggle
        self.group = group         # buttons sharing a group act like radio set

    def handle_event(self, event) -> bool:
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.callback:
                    self.callback()
                return True
        return False

    def draw(self, surface):
        if not self.enabled:
            bg = config.COL_PANEL
            fg = config.COL_TEXT_DIM
        elif self.active:
            bg = config.COL_ACCENT
            fg = (20, 22, 28)
        elif self.hover:
            bg = config.COL_PANEL_LIGHT
            fg = config.COL_TEXT
        else:
            bg = config.COL_PANEL_LIGHT
            fg = config.COL_TEXT
        pygame.draw.rect(surface, bg, self.rect, border_radius=6)
        if not self.active:
            pygame.draw.rect(surface, config.COL_GRID, self.rect, width=1,
                             border_radius=6)
        draw_text(surface, self.label, self.rect.centerx, self.rect.centery,
                  size=self.size, color=fg, center=True)


def progress_bar(surface, x, y, w, h, frac, color=config.COL_ACCENT,
                 bg=config.COL_PANEL_LIGHT):
    frac = max(0.0, min(1.0, frac))
    pygame.draw.rect(surface, bg, (x, y, w, h), border_radius=4)
    if frac > 0:
        pygame.draw.rect(surface, color, (x, y, int(w * frac), h),
                         border_radius=4)

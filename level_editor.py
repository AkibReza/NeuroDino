"""
level_editor.py
===============
An in-app editor for the cactus layout. Physics/terrain/gravity/speed are *not*
editable here (explicitly out of scope) — only obstacle placement.

Controls (also drawn on screen):
    Left click            place a cactus at the cursor (or pick up one to drag)
    Left drag             move the picked-up cactus
    Right click on cactus delete it
    [  /  ]               decrease / increase the height used for new cacti
    A / D  or  arrows     scroll the level left / right
    S                     save to the active level file
    L                     reload from the active level file
    Esc                   leave the editor (back to menu)
"""
from __future__ import annotations

import pygame

import config
import ui
from level import Level


class LevelEditor:
    def __init__(self, level: Level, save_path: str):
        self.level = level
        self.save_path = save_path
        self.scroll = 0.0
        self.place_height = 45
        self.dragging = None        # obstacle currently being dragged
        self.ground_y = config.WINDOW_HEIGHT - 140
        self.message = ""
        self.message_timer = 0

    # ------------------------------------------------------------- helpers
    def _screen_to_world(self, mx: float) -> float:
        return self.scroll + (mx - config.DINO_SCREEN_X)

    def _world_to_screen(self, wx: float) -> float:
        return config.DINO_SCREEN_X + (wx - self.scroll)

    def _obstacle_at(self, mx, my):
        for ob in self.level.obstacles:
            sx = self._world_to_screen(ob.x)
            rect = pygame.Rect(int(sx), int(self.ground_y - ob.height),
                               ob.width, ob.height)
            if rect.collidepoint(mx, my):
                return ob
        return None

    def _flash(self, text):
        self.message = text
        self.message_timer = 120

    # -------------------------------------------------------------- events
    def handle_event(self, event) -> str | None:
        """Returns 'exit' when the user wants to leave the editor."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "exit"
            elif event.key in (pygame.K_a, pygame.K_LEFT):
                self.scroll = max(0, self.scroll - 120)
            elif event.key in (pygame.K_d, pygame.K_RIGHT):
                self.scroll = min(self.level.width, self.scroll + 120)
            elif event.key == pygame.K_LEFTBRACKET:
                self.place_height = max(config.MIN_CACTUS_HEIGHT,
                                        self.place_height - 5)
            elif event.key == pygame.K_RIGHTBRACKET:
                self.place_height = min(int(config.MAX_CACTUS_HEIGHT),
                                        self.place_height + 5)
            elif event.key == pygame.K_s:
                self.level.save(self.save_path)
                self._flash(f"Saved -> {self.save_path}")
            elif event.key == pygame.K_l:
                try:
                    self.level = Level.load(self.save_path)
                    self._flash("Reloaded level from disk")
                except Exception as exc:  # noqa: BLE001
                    self._flash(f"Load failed: {exc}")

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            if mx > config.GAME_AREA_WIDTH:
                return None  # ignore clicks in the sidebar
            if event.button == 1:           # left: pick up or place
                hit = self._obstacle_at(mx, my)
                if hit is not None:
                    self.dragging = hit
                else:
                    wx = max(0.0, min(self.level.width, self._screen_to_world(mx)))
                    self.level.add_obstacle(wx, self.place_height)
                    self._flash("Cactus placed")
            elif event.button == 3:         # right: delete
                hit = self._obstacle_at(mx, my)
                if hit is not None:
                    self.level.remove_obstacle(hit)
                    self._flash("Cactus deleted")
            elif event.button == 4:         # wheel up -> scroll right
                self.scroll = min(self.level.width, self.scroll + 80)
            elif event.button == 5:         # wheel down -> scroll left
                self.scroll = max(0, self.scroll - 80)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging is not None:
                self.dragging = None
                self.level.resort()

        elif event.type == pygame.MOUSEMOTION and self.dragging is not None:
            mx, _ = event.pos
            self.dragging.x = max(0.0, min(self.level.width,
                                           self._screen_to_world(mx)))
        return None

    def update(self):
        if self.message_timer > 0:
            self.message_timer -= 1

    # ---------------------------------------------------------------- draw
    def draw(self, surface):
        s = surface
        pygame.draw.rect(s, config.COL_BG,
                         (0, 0, config.GAME_AREA_WIDTH, config.WINDOW_HEIGHT))
        pygame.draw.line(s, config.COL_GROUND, (0, self.ground_y),
                         (config.GAME_AREA_WIDTH, self.ground_y), 3)

        # obstacles
        for ob in self.level.obstacles:
            sx = self._world_to_screen(ob.x)
            if sx + ob.width < 0 or sx > config.GAME_AREA_WIDTH:
                continue
            col = config.COL_CHAMPION if ob is self.dragging else config.COL_CACTUS
            pygame.draw.rect(s, col, (int(sx), int(self.ground_y - ob.height),
                                      ob.width, ob.height))
            pygame.draw.rect(s, config.COL_CACTUS_DARK,
                             (int(sx), int(self.ground_y - ob.height),
                              ob.width, ob.height), 1)
            ui.draw_text(s, f"{int(ob.x)}", int(sx), int(self.ground_y + 6),
                         size=12, color=config.COL_TEXT_DIM)

        # ghost preview of the next placement at the cursor
        mx, my = pygame.mouse.get_pos()
        if mx <= config.GAME_AREA_WIDTH and self.dragging is None:
            ghost = pygame.Surface((config.DEFAULT_CACTUS_WIDTH, self.place_height),
                                   pygame.SRCALPHA)
            ghost.fill((90, 170, 90, 110))
            s.blit(ghost, (int(mx), int(self.ground_y - self.place_height)))

        # title + ruler
        ui.draw_text(s, "LEVEL EDITOR", 16, 12, size=26, color=config.COL_ACCENT)
        ui.draw_text(s, f"scroll x={int(self.scroll)}  |  "
                        f"obstacles={len(self.level.obstacles)}  |  "
                        f"new height={self.place_height}",
                     16, 44, size=16, color=config.COL_TEXT_DIM)
        # level progress ruler
        frac = self.scroll / max(1, self.level.width)
        ui.progress_bar(s, 16, 70, config.GAME_AREA_WIDTH - 32, 8, frac)

        if self.message_timer > 0:
            ui.draw_text(s, self.message, config.GAME_AREA_WIDTH // 2,
                         self.ground_y + 40, size=20, color=config.COL_ACCENT,
                         center=True)

    def draw_help(self, surface, x, y):
        lines = [
            "EDITOR CONTROLS",
            "L-click: place / drag cactus",
            "R-click: delete cactus",
            "[ / ] : new cactus height",
            "A / D or arrows: scroll",
            "mouse wheel: scroll",
            "S: save level   L: reload",
            "Esc: back to menu",
        ]
        ui.draw_text(surface, lines[0], x, y, size=18, color=config.COL_ACCENT)
        y += 28
        for ln in lines[1:]:
            ui.draw_text(surface, ln, x, y, size=15, color=config.COL_TEXT_DIM)
            y += 22

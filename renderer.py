"""
renderer.py
===========
All world/HUD drawing. The renderer is stateless with respect to the
simulation: it is handed the current simulation/level/stats each frame and
draws them. Interactive buttons live in main.py; the renderer draws the
non-interactive parts (game world, leaderboard text, replay overlay, history
list).
"""
from __future__ import annotations

import random
import pygame

import config
import ui


def draw_gradient_rect(surface, color1, color2, rect):
    """Draws a vertical gradient from color1 to color2 in rect."""
    grad_surf = pygame.Surface((1, 2))
    grad_surf.set_at((0, 0), color1)
    grad_surf.set_at((0, 1), color2)
    scaled_surf = pygame.transform.smoothscale(grad_surf, (rect.width, rect.height))
    surface.blit(scaled_surf, rect.topleft)


class Renderer:
    def __init__(self, surface):
        self.surface = surface
        self.particles = []  # Running particle system for visual juice

    # ------------------------------------------------------------------ world
    def _lane_ground_y(self, lane: int) -> int:
        """Screen y of the ground line for a given lane (dinos rest here)."""
        top = config.LANE_AREA_TOP + lane * config.LANE_HEIGHT
        return top + config.LANE_HEIGHT - 12  # a little padding below the line

    def draw_world(self, sim, level):
        s = self.surface
        # Game area background
        pygame.draw.rect(s, config.COL_BG,
                         (0, config.LANE_AREA_TOP, config.GAME_AREA_WIDTH,
                          config.LANE_AREA_HEIGHT))

        spacing = config.DINO_SPACING
        max_spacing = (config.DINOS_PER_LANE - 1) * spacing

        # Clean/update particles list
        self.particles = [p for p in self.particles if p["alpha"] > 0]

        for lane in range(config.NUM_LANES):
            top = config.LANE_AREA_TOP + lane * config.LANE_HEIGHT
            ground_y = self._lane_ground_y(lane)
            
            # Draw premium vertical gradient for the lane background
            draw_gradient_rect(s, (32, 34, 44), (20, 22, 28), 
                               pygame.Rect(0, top, config.GAME_AREA_WIDTH, config.LANE_HEIGHT))

            # Lane separator grid line
            pygame.draw.line(s, config.COL_GRID, (0, top),
                             (config.GAME_AREA_WIDTH, top), 1)

            # Glowing neon ground line (thick dark neon line + thin bright core)
            pygame.draw.line(s, (48, 52, 68), (0, ground_y),
                             (config.GAME_AREA_WIDTH, ground_y), 3)
            pygame.draw.line(s, config.COL_GROUND, (0, ground_y),
                             (config.GAME_AREA_WIDTH, ground_y), 1)

            # Lane label
            ui.draw_text(s, f"L{lane+1}", 10, top + 3, size=14,
                         color=config.COL_TEXT_DIM)

            # Set clipping boundary for the lane so jumping dinos never enter other lanes
            s.set_clip(pygame.Rect(0, top + 1, config.GAME_AREA_WIDTH, config.LANE_HEIGHT - 1))

            # Draw lane-specific particles
            for p in self.particles:
                if p["lane"] != lane:
                    continue
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                p["alpha"] -= 6
                if p["alpha"] > 0:
                    s_part = pygame.Surface((p["size"] * 2, p["size"] * 2), pygame.SRCALPHA)
                    pygame.draw.circle(s_part, (*p["color"], p["alpha"]), (p["size"], p["size"]), p["size"])
                    s.blit(s_part, (int(p["x"] - p["size"]), int(p["y"] - p["size"])))

            # Obstacles (identical layout drawn in every lane, offset to line up with spacing)
            for ob in level.obstacles:
                screen_x = config.DINO_SCREEN_X + max_spacing + (ob.x - sim.world_x)
                if screen_x + ob.width < 0 or screen_x > config.GAME_AREA_WIDTH:
                    continue
                h = min(ob.height, config.LANE_HEIGHT - 16)
                # Neon cactus with green gradient and a bright border
                draw_gradient_rect(s, (6, 214, 160), (4, 120, 90),
                                   pygame.Rect(int(screen_x), int(ground_y - h), ob.width, int(h)))
                pygame.draw.rect(s, (15, 255, 190),
                                 (int(screen_x), int(ground_y - h),
                                  ob.width, int(h)), 1)

            # Dinos belonging to this lane
            for d in sim.dinos:
                if d.lane != lane:
                    continue
                self._draw_dino(d, ground_y, sim.world_x)

            s.set_clip(None)

    def _draw_dino(self, d, ground_y, sim_world_x):
        s = self.surface
        spacing = config.DINO_SPACING
        max_spacing = (config.DINOS_PER_LANE - 1) * spacing
        x = config.DINO_SCREEN_X + max_spacing + (d.world_x - sim_world_x)

        w, h = 14, config.DINO_HEIGHT - 8
        if x + w < 0 or x > config.GAME_AREA_WIDTH:
            return

        jump_px = d.y * 0.45
        y = ground_y - config.DINO_HEIGHT - jump_px
        if d.alive:
            color = ui.dino_color(d.slot)
        elif d.solved:
            color = config.COL_CHAMPION
        else:
            color = config.COL_DEAD

        # Spawn dust particles if running
        if d.alive and d.on_ground and random.random() < 0.35:
            py = ground_y - 4
            self.particles.append({
                "lane": d.lane,
                "x": x + w / 2,
                "y": py,
                "vx": random.uniform(-1.5, -0.5),
                "vy": random.uniform(-0.5, 0.2),
                "alpha": 180,
                "size": random.randint(2, 3),
                "color": color
            })

        # Body
        pygame.draw.rect(s, color, (int(x), int(y), w, h), border_radius=3)
        # Tiny head
        pygame.draw.rect(s, color, (int(x + w - 4), int(y - 6), 8, 8),
                         border_radius=2)
        # Glowing eye if alive
        if d.alive:
            pygame.draw.rect(s, (255, 255, 255), (int(x + w), int(y - 4), 2, 2))
            ui.draw_text(s, d.id, int(x + w + 3), int(y - 2), size=12,
                         color=config.COL_TEXT_DIM)

    # ---------------------------------------------------------------- top bar
    def draw_top_bar(self, generation, sim_stats, level, speed_label,
                     headless, state_label):
        s = self.surface
        pygame.draw.rect(s, config.COL_PANEL,
                         (0, 0, config.GAME_AREA_WIDTH, config.TOP_BAR_HEIGHT))
        ui.draw_text(s, f"Gen {generation}", 12, 11, size=22,
                     color=config.COL_ACCENT)
        ui.draw_text(s, f"Alive {sim_stats['alive']}/{config.POPULATION_SIZE}",
                     130, 13, size=18)
        ui.draw_text(s, f"Frame {sim_stats['frame']}", 290, 13, size=18,
                     color=config.COL_TEXT_DIM)
        mode = "HEADLESS" if headless else "RENDER"
        ui.draw_text(s, f"{speed_label}  {mode}", 420, 13, size=18,
                     color=config.COL_TEXT_DIM)
        ui.draw_text(s, state_label, 600, 13, size=18, color=config.COL_TEXT_DIM)
        # level progress bar
        frac = min(1.0, sim_stats["world_x"] / level.width)
        ui.progress_bar(s, 760, 14, config.GAME_AREA_WIDTH - 780, 12, frac)

    # -------------------------------------------------------------- sidebar
    def draw_sidebar_panel(self):
        s = self.surface
        x = config.GAME_AREA_WIDTH
        pygame.draw.rect(s, config.COL_PANEL,
                         (x, 0, config.SIDEBAR_WIDTH, config.WINDOW_HEIGHT))
        pygame.draw.line(s, config.COL_GRID, (x, 0), (x, config.WINDOW_HEIGHT), 1)

    def draw_leaderboard(self, sim, stats, generation, best_ever, y0):
        """Draw the live leaderboard. Returns the y after the last line."""
        s = self.surface
        x = config.GAME_AREA_WIDTH + 18
        ui.draw_text(s, "LEADERBOARD", x, y0, size=20, color=config.COL_ACCENT)
        y = y0 + 30
        ui.draw_text(s, f"Best fitness:  {stats['best_fitness']:.0f}", x, y, size=17)
        y += 22
        ui.draw_text(s, f"Avg fitness:   {stats['avg_fitness']:.0f}", x, y, size=17)
        y += 22
        ui.draw_text(s, f"Solved:        {stats['solved_count']}", x, y, size=17)
        y += 28

        champ = stats["champion"]
        if champ is not None:
            ui.draw_text(s, f"Champion: #{champ.id}  (Lane {champ.lane+1})",
                         x, y, size=17, color=config.COL_CHAMPION)
        y += 26
        if best_ever is not None:
            ui.draw_text(s,
                         f"Best ever: gen {best_ever.generation}  "
                         f"#{best_ever.champion_id}  {best_ever.best_fitness:.0f}",
                         x, y, size=15, color=config.COL_TEXT_DIM)
        y += 30

        ui.draw_text(s, "TOP 10 DINOS", x, y, size=17, color=config.COL_ACCENT)
        y += 24
        top10 = sorted(sim.dinos, key=lambda d: d.fitness, reverse=True)[:10]
        for i, d in enumerate(top10, 1):
            tag = ui.dino_color(d.slot)
            pygame.draw.rect(s, tag, (x, y + 2, 10, 10), border_radius=2)
            ui.draw_text(s, f"{i:>2}. #{d.id:<3} L{d.lane+1:<2}  {d.fitness:>7.0f}",
                         x + 16, y, size=15,
                         color=config.COL_TEXT if d.alive else config.COL_TEXT_DIM)
            y += 19
        return y + 6

    # --------------------------------------------------------- champion replay
    def draw_replay(self, dino, level, sim, nn_inputs, nn_output, generation_label):
        """Full-area single-dino replay with a live neural-network overlay."""
        s = self.surface
        pygame.draw.rect(s, config.COL_BG,
                         (0, config.LANE_AREA_TOP, config.GAME_AREA_WIDTH,
                          config.LANE_AREA_HEIGHT))
        ground_y = config.WINDOW_HEIGHT - 120
        pygame.draw.line(s, config.COL_GROUND, (0, ground_y),
                         (config.GAME_AREA_WIDTH, ground_y), 3)

        # obstacles, scaled up (replay uses full obstacle heights)
        for ob in level.obstacles:
            screen_x = config.DINO_SCREEN_X + (ob.x - sim.world_x)
            if screen_x + ob.width < 0 or screen_x > config.GAME_AREA_WIDTH:
                continue
            pygame.draw.rect(s, config.COL_CACTUS,
                             (int(screen_x), int(ground_y - ob.height),
                              ob.width + 6, int(ob.height)))
            pygame.draw.rect(s, config.COL_CACTUS_DARK,
                             (int(screen_x), int(ground_y - ob.height),
                              ob.width + 6, int(ob.height)), 2)

        # the champion dino (bigger)
        x = config.DINO_SCREEN_X
        jump_px = dino.y
        dw, dh = 30, 48
        y = ground_y - dh - jump_px
        color = config.COL_CHAMPION if dino.alive else config.COL_DEAD
        pygame.draw.rect(s, color, (int(x), int(y), dw, dh), border_radius=4)
        pygame.draw.rect(s, color, (int(x + dw - 8), int(y - 12), 16, 16),
                         border_radius=3)

        # progress + label
        frac = min(1.0, sim.world_x / level.width)
        ui.progress_bar(s, 20, config.LANE_AREA_TOP + 16,
                        config.GAME_AREA_WIDTH - 40, 14, frac)
        ui.draw_text(s, generation_label, 20, config.LANE_AREA_TOP + 38,
                     size=20, color=config.COL_CHAMPION)
        if dino.solved:
            ui.draw_text(s, "LEVEL SOLVED!", config.GAME_AREA_WIDTH // 2,
                         config.LANE_AREA_TOP + 80, size=40,
                         color=config.COL_ACCENT, center=True)
        elif not dino.alive:
            ui.draw_text(s, "CRASHED", config.GAME_AREA_WIDTH // 2,
                         config.LANE_AREA_TOP + 80, size=40,
                         color=config.COL_DEAD, center=True)

        self._draw_nn_overlay(nn_inputs, nn_output, dino)

    def _draw_nn_overlay(self, inputs, output, dino):
        """Live neural-network input/output overlay for champion replay."""
        s = self.surface
        ox, oy = 24, config.LANE_AREA_TOP + 130
        w, h = 300, 230
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((20, 22, 28, 220))
        s.blit(panel, (ox, oy))
        pygame.draw.rect(s, config.COL_GRID, (ox, oy, w, h), 1, border_radius=6)

        ui.draw_text(s, "NEURAL NETWORK (live)", ox + 12, oy + 10, size=18,
                     color=config.COL_ACCENT)
        labels = ["dist to cactus", "cactus height", "game speed", "dino height"]
        y = oy + 40
        for lab, val in zip(labels, inputs):
            ui.draw_text(s, lab, ox + 12, y, size=15, color=config.COL_TEXT_DIM)
            ui.progress_bar(s, ox + 150, y + 1, 100, 12, val)
            ui.draw_text(s, f"{val:.2f}", ox + 258, y, size=14)
            y += 26
        y += 6
        pygame.draw.line(s, config.COL_GRID, (ox + 12, y), (ox + w - 12, y), 1)
        y += 10
        decision = "JUMP" if output > config.JUMP_THRESHOLD else "RUN"
        dcol = config.COL_ACCENT if output > config.JUMP_THRESHOLD else config.COL_TEXT_DIM
        ui.draw_text(s, "output", ox + 12, y, size=15, color=config.COL_TEXT_DIM)
        ui.progress_bar(s, ox + 150, y + 1, 100, 12, output,
                        color=dcol)
        ui.draw_text(s, f"{output:.2f}", ox + 258, y, size=14)
        y += 26
        ui.draw_text(s, f"decision: {decision}", ox + 12, y, size=18, color=dcol)

    # -------------------------------------------------------------- history
    def draw_history_list(self, history, scroll, selected_gen, x0, y0, w, h):
        """Scrollable list of all saved generations."""
        s = self.surface
        ui.draw_text(s, "GENERATION HISTORY", x0, y0, size=20,
                     color=config.COL_ACCENT)
        ui.draw_text(s, "(click a row to replay its champion)", x0, y0 + 24,
                     size=13, color=config.COL_TEXT_DIM)
        list_top = y0 + 46
        row_h = 26
        clip = pygame.Rect(x0, list_top, w, h - 46)
        s.set_clip(clip)
        snaps = history.snapshots
        rects = []
        for i, snap in enumerate(snaps):
            ry = list_top + i * row_h - scroll
            if ry + row_h < list_top or ry > list_top + (h - 46):
                rects.append(None)
                continue
            rect = pygame.Rect(x0, ry, w, row_h - 3)
            sel = (snap.generation == selected_gen)
            bg = config.COL_ACCENT if sel else config.COL_PANEL_LIGHT
            fg = (20, 22, 28) if sel else config.COL_TEXT
            pygame.draw.rect(s, bg, rect, border_radius=4)
            ui.draw_text(s, f"Gen {snap.generation:<3}  best {snap.best_fitness:>7.0f}"
                            f"  avg {snap.avg_fitness:>6.0f}  solved {snap.solved_count}",
                         x0 + 8, ry + 5, size=14, color=fg)
            rects.append(rect)
        s.set_clip(None)
        return rects, row_h, list_top

"""
main.py
=======
NeuroDino entry point. Wires together the simulation, genetic algorithm,
renderer, level editor, snapshots and logging behind a small state machine and
a sidebar of controls.

Run:  python main.py

States:
    TRAINING  - evolving generations (running or paused)
    REPLAY    - champion replay of the best-ever dinosaur
    HISTORY   - scrollable list of every saved generation
    EDITOR    - level editor

Speed:
    1x runs rendered frame-by-frame. 2x / 5x / 10x (and the "Headless" toggle)
    run each generation headlessly then display the final state, exactly as the
    spec requires, so Pygame rendering never bottlenecks high multipliers.
"""
from __future__ import annotations

import sys
import time

import pygame

import config
import ui
from renderer import Renderer
from level import ensure_default_level, Level
from genetic_algorithm import GeneticAlgorithm
from simulation import Simulation
from snapshots import GenerationHistory, GenerationSnapshot
from logger import PerformanceLogger
from level_editor import LevelEditor
from neural_network import NeuralNetwork
from dino import Dino

# How long (render frames) the final state of a headless generation is shown.
SHOW_RESULT_FRAMES = 22

TRAINING, REPLAY, HISTORY, EDITOR = "TRAINING", "REPLAY", "HISTORY", "EDITOR"


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("NeuroDino - Neuroevolution Dinosaur")
        w, h = config.WINDOW_WIDTH, config.WINDOW_HEIGHT
        self.screen = pygame.display.set_mode((w, h), pygame.DOUBLEBUF | pygame.HWSURFACE)
        config.init_layout(w, h)
        self.clock = pygame.time.Clock()
        self.renderer = Renderer(self.screen)

        # Domain objects
        self.level = ensure_default_level()
        self.ga = GeneticAlgorithm(seed=None)
        self.history = GenerationHistory.load()
        self.logger = PerformanceLogger()

        # Training state
        self.dinos = self.ga.initial_population()
        self.generation = 1
        self.sim = Simulation(self.dinos, self.level)
        self.running = False           # is training actively advancing?
        self.dwell = 0                 # frames left to display a headless result
        self.t_start = time.time()
        self.speed_multiplier = 1
        self.render_every_frame = True
        self.auto_start_gen = True
        self.paused_for_gen_completion = False

        # Other modes
        self.mode = TRAINING
        self.replay_sim = None
        self.replay_dino = None
        self.replay_label = ""
        self.history_scroll = 0
        self.selected_gen = None
        self.editor = None
        self.history_rects = []
        self.history_row_h = 26
        self.history_list_top = 0
        self.toast = ""
        self.toast_timer = 0

        self._build_buttons()

    # ------------------------------------------------------------ toast
    def _flash(self, text):
        self.toast = text
        self.toast_timer = 150

    # ------------------------------------------------------ button wiring
    def _build_buttons(self):
        x = config.GAME_AREA_WIDTH + 16
        w = config.SIDEBAR_WIDTH - 32
        self.buttons = []
        self.speed_buttons = []

        # Primary controls (two columns)
        bw = (w - 8) // 2
        y = 78
        self.btn_start = ui.Button("Start", x, y, bw, 30, self._start)
        self.btn_pause = ui.Button("Pause", x + bw + 8, y, bw, 30, self._toggle_pause)
        y += 36
        self.btn_reset = ui.Button("Reset", x, y, bw, 30, self._reset)
        self.btn_replay = ui.Button("Replay Champ", x + bw + 8, y, bw, 30,
                                    self._start_replay_best)
        y += 36
        self.btn_history = ui.Button("Prev Gens", x, y, bw, 30, self._enter_history)
        self.btn_editor = ui.Button("Level Editor", x + bw + 8, y, bw, 30,
                                    self._enter_editor)
        y += 36
        self.btn_graphs = ui.Button("Save Graphs", x, y, bw, 30, self._generate_graphs)
        self.btn_render = ui.Button("Render: ON", x + bw + 8, y, bw, 30,
                                    self._toggle_render)
        y += 36
        self.btn_autostart = ui.Button("Auto Start: ON", x, y, w, 30, self._toggle_autostart)
        self.buttons += [self.btn_start, self.btn_pause, self.btn_reset,
                         self.btn_replay, self.btn_history, self.btn_editor,
                         self.btn_graphs, self.btn_render, self.btn_autostart]

        # Speed row
        y += 40
        self.speed_row_y = y
        sw = (w - 3 * 6) // 4
        for i, mult in enumerate(config.SPEED_MULTIPLIERS):
            bx = x + i * (sw + 6)
            b = ui.Button(f"{mult}x", bx, y, sw, 28,
                          lambda m=mult: self._set_speed(m), size=16)
            b.active = (mult == self.speed_multiplier)
            self.speed_buttons.append(b)
        self.buttons += self.speed_buttons

        # A "back to training" button reused by history/editor views.
        self.btn_back = ui.Button("Back to Training", x, config.WINDOW_HEIGHT - 44,
                                  w, 32, self._back_to_training)

    def _refresh_button_states(self):
        self.btn_start.enabled = (self.mode == TRAINING and not self.running)
        self.btn_pause.label = "Pause" if self.running else "Resume"
        self.btn_pause.enabled = (self.mode == TRAINING)
        self.btn_render.label = f"Render: {'ON' if self.render_every_frame else 'OFF'}"
        self.btn_autostart.label = f"Auto Start: {'ON' if self.auto_start_gen else 'OFF'}"
        for b, mult in zip(self.speed_buttons, config.SPEED_MULTIPLIERS):
            b.active = (mult == self.speed_multiplier)

    # ----------------------------------------------------- control actions
    def _is_headless(self) -> bool:
        return (self.speed_multiplier >= config.HEADLESS_THRESHOLD
                or not self.render_every_frame)

    def _start(self):
        if self.mode == TRAINING:
            self.running = True

    def _toggle_pause(self):
        if self.mode == TRAINING:
            self.running = not self.running

    def _reset(self):
        self.dinos = self.ga.initial_population()
        self.generation = 1
        self.sim = Simulation(self.dinos, self.level)
        self.running = False
        self.dwell = 0
        self.history = GenerationHistory()
        self.logger = PerformanceLogger()
        self.t_start = time.time()
        self.mode = TRAINING
        self.paused_for_gen_completion = False
        self._flash("Training reset")

    def _set_speed(self, mult):
        self.speed_multiplier = mult

    def _toggle_render(self):
        self.render_every_frame = not self.render_every_frame

    def _toggle_autostart(self):
        self.auto_start_gen = not self.auto_start_gen
        self._flash(f"Auto Start Gen: {'ON' if self.auto_start_gen else 'OFF'}")

    def _back_to_training(self):
        self.mode = TRAINING

    # ------------------------------------------------------- training loop
    def _complete_generation(self):
        self.sim.finalize_fitness()
        stats = self.sim.stats()
        champ = stats["champion"]
        elapsed = time.time() - self.t_start
        snap = GenerationSnapshot(
            generation=self.generation,
            best_fitness=stats["best_fitness"],
            avg_fitness=stats["avg_fitness"],
            champion_id=champ.id,
            champion_lane=champ.lane,
            champion_genome=champ.brain.to_list(),
            alive_count=stats["alive"],
            solved_count=stats["solved_count"],
            time_elapsed=elapsed,
        )
        self.history.add(snap)
        self.history.save()
        self.logger.log(self.generation, stats["best_fitness"],
                        stats["avg_fitness"], champ.id, stats["alive"],
                        stats["solved_count"], elapsed)

        # Breed next generation
        self.dinos = self.ga.evolve(self.sim.dinos)
        self.generation += 1
        self.sim = Simulation(self.dinos, self.level)
        self.dwell = 0

    def _result_dwell(self) -> int:
        """Frames to display a finished generation. Higher speed multipliers
        linger less, so 10x visibly flies while 2x is more watchable."""
        return max(2, SHOW_RESULT_FRAMES // max(1, self.speed_multiplier))

    def _update_training(self):
        if not self.running:
            return
        if self.sim.finished:
            self.sim.finalize_fitness()
            if self.dwell > 0:
                self.dwell -= 1
                return
            
            if not self.auto_start_gen and not self.paused_for_gen_completion:
                self.running = False
                self.paused_for_gen_completion = True
                self._flash(f"Gen {self.generation} complete. Press Resume to advance.")
                return

            self.paused_for_gen_completion = False
            self._complete_generation()
            return

        if self._is_headless():
            self.sim.run_headless()
            self.sim.finalize_fitness()
            self.dwell = self._result_dwell()
        else:
            # 1x rendered: advance a single simulation frame per render frame
            self.sim.step()
            self.sim.finalize_fitness()
            if self.sim.finished:
                self.dwell = self._result_dwell()

    # ------------------------------------------------------------- replay
    def _start_replay_from_genome(self, genome, label):
        brain = NeuralNetwork.from_list(genome)
        d = Dino(dino_id=1, brain=brain)
        d.lane = 0
        self.replay_dino = d
        self.replay_sim = Simulation([d], self.level)
        self.replay_label = label
        self.mode = REPLAY
        self.running = False

    def _start_replay_best(self):
        be = self.history.best_ever
        if be is None:
            self._flash("No champion yet - run some generations first")
            return
        self._start_replay_from_genome(
            be.champion_genome,
            f"Champion replay - gen {be.generation}, #{be.champion_id} "
            f"(fitness {be.best_fitness:.0f})")

    def _update_replay(self):
        if self.replay_sim is None or self.replay_sim.finished:
            return
        self.replay_sim.step()

    # ------------------------------------------------------------ history
    def _enter_history(self):
        self.mode = HISTORY
        self.running = False
        self.history_scroll = 0
        self.selected_gen = (self.history.latest.generation
                             if self.history.latest else None)

    # ------------------------------------------------------------- editor
    def _enter_editor(self):
        self.mode = EDITOR
        self.running = False
        self.editor = LevelEditor(Level.load(config.DEFAULT_LEVEL_PATH)
                                  if config.DEFAULT_LEVEL_PATH else self.level,
                                  config.DEFAULT_LEVEL_PATH)

    def _exit_editor(self):
        # Adopt the (possibly edited) level for future training.
        self.level = self.editor.level
        self.mode = TRAINING
        self._flash("Level updated. Reset training to use it on gen 1.")

    # ------------------------------------------------------------- graphs
    def _generate_graphs(self):
        paths = self.logger.generate_graphs()
        if paths:
            self._flash(f"Saved {len(paths)} graphs to output/")
        else:
            self._flash("No data yet - run a generation first")

    # -------------------------------------------------------------- events
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()

            if self.mode == EDITOR:
                result = self.editor.handle_event(event)
                if result == "exit":
                    self._exit_editor()
                continue

            # global buttons
            for b in self.buttons:
                b.handle_event(event)
            if self.mode in (HISTORY, REPLAY):
                self.btn_back.handle_event(event)

            if self.mode == HISTORY:
                self._handle_history_event(event)

            if event.type == pygame.KEYDOWN:
                self._handle_hotkey(event)

    def _handle_hotkey(self, event):
        if event.key == pygame.K_SPACE and self.mode == TRAINING:
            self._toggle_pause() if self.running or self.history.latest else self._start()
        elif event.key == pygame.K_r:
            self._start_replay_best()
        elif event.key == pygame.K_e and self.mode != EDITOR:
            self._enter_editor()
        elif event.key == pygame.K_h:
            self._enter_history()
        elif event.key == pygame.K_g:
            self._generate_graphs()
        elif event.key == pygame.K_ESCAPE:
            if self.mode in (REPLAY, HISTORY):
                self.mode = TRAINING
            elif self.mode == TRAINING:
                self._quit()
        elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
            idx = event.key - pygame.K_1
            if idx < len(config.SPEED_MULTIPLIERS):
                self._set_speed(config.SPEED_MULTIPLIERS[idx])

    def _handle_history_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:
                self.history_scroll = max(0, self.history_scroll - 40)
            elif event.button == 5:
                max_scroll = max(0, len(self.history) * self.history_row_h - 400)
                self.history_scroll = min(max_scroll, self.history_scroll + 40)
            elif event.button == 1:
                for snap, rect in zip(self.history.snapshots, self.history_rects):
                    if rect and rect.collidepoint(event.pos):
                        self.selected_gen = snap.generation
                        # clicking a row replays that generation's champion
                        self._start_replay_from_genome(
                            snap.champion_genome,
                            f"Replay - gen {snap.generation}, #{snap.champion_id} "
                            f"(fitness {snap.best_fitness:.0f})")
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                max_scroll = max(0, len(self.history) * self.history_row_h - 400)
                self.history_scroll = min(max_scroll, self.history_scroll + self.history_row_h)
            elif event.key == pygame.K_UP:
                self.history_scroll = max(0, self.history_scroll - self.history_row_h)

    # -------------------------------------------------------------- update
    def update(self):
        if self.toast_timer > 0:
            self.toast_timer -= 1
        if self.mode == TRAINING:
            # At high multipliers we run several headless generations per frame
            # would be overkill; one full generation per frame already advances
            # extremely fast. We instead run 1 generation per frame in headless
            # and rely on the multiplier only to pick headless vs rendered. To
            # honour the multiplier as a throughput hint we step it that many
            # times when rendered.
            if self._is_headless():
                self._update_training()
            else:
                for _ in range(self.speed_multiplier):
                    self._update_training()
        elif self.mode == REPLAY:
            steps = self.speed_multiplier if self.speed_multiplier > 1 else 1
            for _ in range(steps):
                self._update_replay()
        elif self.mode == EDITOR:
            self.editor.update()

    # ---------------------------------------------------------------- draw
    def draw(self):
        self.screen.fill(config.COL_BG)
        if self.mode == EDITOR:
            self.editor.draw(self.screen)
            self.renderer.draw_sidebar_panel()
            self.editor.draw_help(self.screen, config.GAME_AREA_WIDTH + 18, 80)
            ui.draw_text(self.screen, "Press Esc to return", config.GAME_AREA_WIDTH + 18,
                         config.WINDOW_HEIGHT - 70, size=15, color=config.COL_TEXT_DIM)
        elif self.mode == REPLAY:
            self._draw_replay()
        elif self.mode == HISTORY:
            self._draw_history()
        else:
            self._draw_training()

        self._draw_toast()
        pygame.display.flip()

    def _draw_training(self):
        self.sim.finalize_fitness()
        stats = self.sim.stats()
        speed_label = f"{self.speed_multiplier}x"
        state = "RUNNING" if self.running else ("PAUSED" if self.history.latest
                                                or self.sim.frame else "READY")
        self.renderer.draw_world(self.sim, self.level)
        self.renderer.draw_top_bar(self.generation, stats, self.level,
                                   speed_label, self._is_headless(), state)
        self.renderer.draw_sidebar_panel()
        self._draw_controls()
        self.renderer.draw_leaderboard(self.sim, stats, self.generation,
                                       self.history.best_ever, y0=self.speed_row_y + 50)

    def _draw_replay(self):
        d = self.replay_dino
        self.renderer.draw_replay(d, self.level, self.replay_sim,
                                  d.last_inputs, d.last_output, self.replay_label)
        self.renderer.draw_sidebar_panel()
        self._draw_controls()
        x = config.GAME_AREA_WIDTH + 18
        ui.draw_text(self.screen, "CHAMPION REPLAY", x, self.speed_row_y + 50,
                     size=20, color=config.COL_CHAMPION)
        y = self.speed_row_y + 84
        ui.draw_text(self.screen, f"distance: {self.replay_sim.world_x:.0f}"
                     f" / {self.level.width}", x, y, size=16); y += 24
        ui.draw_text(self.screen, f"cleared: {d.obstacles_cleared}", x, y, size=16)
        y += 24
        status = "SOLVED" if d.solved else ("alive" if d.alive else "crashed")
        ui.draw_text(self.screen, f"status: {status}", x, y, size=16)
        self.btn_back.draw(self.screen)

    def _draw_history(self):
        self.renderer.draw_world(self.sim, self.level)  # dim backdrop
        overlay = pygame.Surface((config.GAME_AREA_WIDTH, config.WINDOW_HEIGHT),
                                 pygame.SRCALPHA)
        overlay.fill((18, 19, 24, 220))
        self.screen.blit(overlay, (0, 0))
        self.history_rects, self.history_row_h, self.history_list_top = \
            self.renderer.draw_history_list(
                self.history, self.history_scroll, self.selected_gen,
                x0=30, y0=30, w=config.GAME_AREA_WIDTH - 60,
                h=config.WINDOW_HEIGHT - 60)
        self.renderer.draw_sidebar_panel()
        self._draw_controls()
        x = config.GAME_AREA_WIDTH + 18
        ui.draw_text(self.screen, f"{len(self.history)} generations saved",
                     x, self.speed_row_y + 50, size=17, color=config.COL_TEXT_DIM)
        self.btn_back.draw(self.screen)

    def _draw_controls(self):
        self._refresh_button_states()
        x = config.GAME_AREA_WIDTH + 16
        ui.draw_text(self.screen, "NeuroDino", x, 14, size=28,
                     color=config.COL_ACCENT)
        ui.draw_text(self.screen, "neuroevolution dinosaur", x, 44, size=14,
                     color=config.COL_TEXT_DIM)
        for b in self.buttons:
            b.draw(self.screen)
        ui.draw_text(self.screen, "Speed (2x+ = headless):", x, self.speed_row_y - 18,
                     size=14, color=config.COL_TEXT_DIM)

    def _draw_toast(self):
        if self.toast_timer > 0:
            ui.draw_text(self.screen, self.toast, config.GAME_AREA_WIDTH // 2,
                         config.WINDOW_HEIGHT - 24, size=18,
                         color=config.COL_ACCENT, center=True)

    # ---------------------------------------------------------------- loop
    def _quit(self):
        try:
            self.history.save()
        except Exception:  # noqa: BLE001
            pass
        pygame.quit()
        sys.exit(0)

    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(config.FPS)


def main():
    App().run()


if __name__ == "__main__":
    main()

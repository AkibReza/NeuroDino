"""
simulation.py
=============
Runs a single generation of dinosaurs over a level.

Two modes:
  * step()          -> advances exactly one frame (used by the renderer at 1x).
  * run_headless()  -> runs the whole generation in a tight loop with no
                       rendering (used for 2x/5x/10x speeds and fast-forward).

Both share the same per-frame logic in `_advance_frame`, so behaviour is
identical regardless of how the generation is driven.
"""
from __future__ import annotations

import config


class Simulation:
    def __init__(self, dinos, level):
        self.dinos = dinos
        self.level = level
        self.world_x = 0.0
        self.speed = config.BASE_SPEED
        self.frame = 0
        self.alive_count = len(dinos)
        self.finished = False
        for d in self.dinos:
            d.reset()

    # -- per-frame core -----------------------------------------------------
    def _advance_frame(self) -> None:
        # Scroll the world camera/simulation distance.
        self.speed = config.speed_at(self.world_x)
        self.world_x += self.speed

        alive = 0
        for d in self.dinos:
            if not d.alive:
                continue

            # Spacing start distance
            start_dist = d.slot * config.DINO_SPACING
            if self.world_x < start_dist:
                # Not started yet
                d.world_x = 0.0
                alive += 1
                continue

            # Active!
            d.world_x = self.world_x - start_dist
            d.speed = config.speed_at(d.world_x)

            # 1. sense -> decide -> act
            inputs = d.sense(d.world_x, d.speed, self.level)
            output = d.brain.forward(inputs)
            d.last_output = output
            if output > config.JUMP_THRESHOLD:
                d.jump()
            d.update_physics()

            # 2. resolve outcome
            if d.world_x >= self.level.width:
                d.alive = False
                d.solved = True
                d.distance = self.level.width
                d.world_x = self.level.width
            elif d.collides_with_current(d.world_x, self.level):
                d.alive = False
                d.distance = d.world_x
                d.world_x = d.distance
            else:
                d.distance = d.world_x
                alive += 1

        self.alive_count = alive
        self.frame += 1

        if self.alive_count == 0 or self.frame >= config.MAX_FRAMES_PER_GENERATION:
            self.finished = True

    # -- drivers ------------------------------------------------------------
    def step(self) -> bool:
        """Advance one frame. Returns True if the generation is now finished."""
        if not self.finished:
            self._advance_frame()
        return self.finished

    def step_n(self, n: int) -> bool:
        """Advance up to n frames (used for 2x/5x render-lite). Returns finished."""
        for _ in range(n):
            if self.finished:
                break
            self._advance_frame()
        return self.finished

    def run_headless(self) -> None:
        """Run the entire generation with no rendering."""
        while not self.finished:
            self._advance_frame()

    # -- stats --------------------------------------------------------------
    def finalize_fitness(self) -> None:
        for d in self.dinos:
            d.compute_fitness()

    def stats(self) -> dict:
        fits = [d.fitness for d in self.dinos]
        best = max(fits) if fits else 0.0
        avg = sum(fits) / len(fits) if fits else 0.0
        champion = max(self.dinos, key=lambda d: d.fitness) if self.dinos else None
        return {
            "alive": self.alive_count,
            "best_fitness": best,
            "avg_fitness": avg,
            "champion": champion,
            "world_x": self.world_x,
            "speed": self.speed,
            "frame": self.frame,
            "solved_count": sum(1 for d in self.dinos if d.solved),
        }

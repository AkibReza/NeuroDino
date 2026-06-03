"""
logger.py
=========
Two responsibilities:
  1. Append one row per generation to a CSV training log.
  2. Generate the three matplotlib graphs on demand (or at end of training):
        - Best fitness vs generation
        - Average fitness vs generation
        - Alive count per generation

matplotlib uses the non-interactive 'Agg' backend so this works headlessly and
never tries to pop a window (the figures are saved to PNG instead).
"""
from __future__ import annotations

import csv
import os

import matplotlib
matplotlib.use("Agg")  # must precede pyplot import; safe for headless use
import matplotlib.pyplot as plt  # noqa: E402

import config


CSV_HEADER = ["generation", "best_fitness", "avg_fitness", "champion_id",
              "alive_count", "solved_count", "time_elapsed"]


class PerformanceLogger:
    def __init__(self, csv_path: str = config.CSV_LOG_PATH):
        self.csv_path = csv_path
        self.rows: list[dict] = []
        self._init_csv()

    def _init_csv(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.csv_path)), exist_ok=True)
        with open(self.csv_path, "w", newline="", encoding="utf-8") as fh:
            csv.DictWriter(fh, fieldnames=CSV_HEADER).writeheader()

    def log(self, generation: int, best_fitness: float, avg_fitness: float,
            champion_id: int, alive_count: int, solved_count: int,
            time_elapsed: float) -> None:
        row = {
            "generation": generation,
            "best_fitness": round(best_fitness, 3),
            "avg_fitness": round(avg_fitness, 3),
            "champion_id": champion_id,
            "alive_count": alive_count,
            "solved_count": solved_count,
            "time_elapsed": round(time_elapsed, 3),
        }
        self.rows.append(row)
        with open(self.csv_path, "a", newline="", encoding="utf-8") as fh:
            csv.DictWriter(fh, fieldnames=CSV_HEADER).writerow(row)

    # -- graphs -------------------------------------------------------------
    def generate_graphs(self, out_dir: str = config.OUTPUT_DIR) -> list[str]:
        """Render the three required graphs. Returns the list of file paths.
        Returns an empty list (without crashing) if there is no data yet."""
        if not self.rows:
            return []
        os.makedirs(out_dir, exist_ok=True)
        gens = [r["generation"] for r in self.rows]
        best = [r["best_fitness"] for r in self.rows]
        avg = [r["avg_fitness"] for r in self.rows]
        alive = [r["alive_count"] for r in self.rows]

        paths = []

        def _plot(x, y, title, ylabel, fname, color):
            fig, ax = plt.subplots(figsize=(8, 4.5))
            ax.plot(x, y, marker="o", markersize=3, color=color, linewidth=1.6)
            ax.set_title(title)
            ax.set_xlabel("Generation")
            ax.set_ylabel(ylabel)
            ax.grid(True, alpha=0.3)
            fig.tight_layout()
            p = os.path.join(out_dir, fname)
            fig.savefig(p, dpi=110)
            plt.close(fig)
            paths.append(p)

        _plot(gens, best, "Best Fitness vs Generation", "Best Fitness",
              "graph_best_fitness.png", "#2e8b57")
        _plot(gens, avg, "Average Fitness vs Generation", "Average Fitness",
              "graph_avg_fitness.png", "#1f6fb2")
        _plot(gens, alive, "Alive Count per Generation", "Alive at End",
              "graph_alive_count.png", "#b2521f")
        return paths

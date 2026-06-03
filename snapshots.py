"""
snapshots.py
============
Stores a snapshot of every generation so the viewer can scroll through all of
them and so champion replay can reconstruct any champion's brain.

Per the modified spec a snapshot is saved *every* generation (not at fixed
milestones). Each snapshot records:
    generation number, best fitness, avg fitness, champion NN weights,
    champion id (and lane, alive count, solved count for convenience).

The whole history is persisted as one JSON file so it survives a restart.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict

import config


@dataclass
class GenerationSnapshot:
    generation: int
    best_fitness: float
    avg_fitness: float
    champion_id: int
    champion_lane: int
    champion_genome: list = field(default_factory=list)
    alive_count: int = 0
    solved_count: int = 0
    time_elapsed: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "GenerationSnapshot":
        return cls(**d)


class GenerationHistory:
    def __init__(self):
        self.snapshots: list[GenerationSnapshot] = []
        # The single best snapshot ever seen (drives champion replay).
        self.best_ever: GenerationSnapshot | None = None

    def __len__(self) -> int:
        return len(self.snapshots)

    def add(self, snap: GenerationSnapshot) -> None:
        self.snapshots.append(snap)
        if self.best_ever is None or snap.best_fitness > self.best_ever.best_fitness:
            self.best_ever = snap

    def get(self, generation: int) -> GenerationSnapshot | None:
        for s in self.snapshots:
            if s.generation == generation:
                return s
        return None

    @property
    def latest(self) -> GenerationSnapshot | None:
        return self.snapshots[-1] if self.snapshots else None

    # -- persistence --------------------------------------------------------
    def save(self, path: str = config.SNAPSHOT_PATH) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        data = {
            "snapshots": [s.to_dict() for s in self.snapshots],
            "best_ever_generation": self.best_ever.generation if self.best_ever else None,
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)

    @classmethod
    def load(cls, path: str = config.SNAPSHOT_PATH) -> "GenerationHistory":
        hist = cls()
        if not os.path.exists(path):
            return hist
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        for sd in data.get("snapshots", []):
            hist.add(GenerationSnapshot.from_dict(sd))
        return hist

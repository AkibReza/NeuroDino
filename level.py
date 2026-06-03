"""
level.py
========
A Level is an ordered list of cactus obstacles plus the level width. Levels are
deterministic: the same level file produces the same obstacle layout for every
generation, which is essential for fair fitness comparison across generations.

JSON schema (levels/*.json):
    {
        "width": 10000,
        "obstacles": [
            {"x": 600, "width": 24, "height": 45},
            ...
        ]
    }
"""
from __future__ import annotations

import json
import os
import random

import config


class Obstacle:
    __slots__ = ("x", "width", "height")

    def __init__(self, x: float, width: int, height: int):
        self.x = float(x)
        self.width = int(width)
        self.height = int(height)

    @property
    def right(self) -> float:
        return self.x + self.width

    def to_dict(self) -> dict:
        return {"x": self.x, "width": self.width, "height": self.height}

    @classmethod
    def from_dict(cls, d: dict) -> "Obstacle":
        return cls(d["x"], d.get("width", config.DEFAULT_CACTUS_WIDTH), d["height"])

    def __repr__(self) -> str:
        return f"Obstacle(x={self.x:.0f}, w={self.width}, h={self.height})"


class Level:
    def __init__(self, width: int = config.LEVEL_WIDTH,
                 obstacles: list[Obstacle] | None = None):
        self.width = int(width)
        # Always keep obstacles sorted by x so "next cactus" lookups are simple.
        self.obstacles = sorted(obstacles or [], key=lambda o: o.x)

    # -- mutation helpers (used by the level editor) ------------------------
    def add_obstacle(self, x: float, height: int,
                     width: int = config.DEFAULT_CACTUS_WIDTH) -> Obstacle:
        ob = Obstacle(x, width, height)
        self.obstacles.append(ob)
        self.obstacles.sort(key=lambda o: o.x)
        return ob

    def remove_obstacle(self, ob: Obstacle) -> None:
        if ob in self.obstacles:
            self.obstacles.remove(ob)

    def resort(self) -> None:
        self.obstacles.sort(key=lambda o: o.x)

    # -- persistence --------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "width": self.width,
            "obstacles": [o.to_dict() for o in self.obstacles],
        }

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)

    @classmethod
    def load(cls, path: str) -> "Level":
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        obstacles = [Obstacle.from_dict(o) for o in data.get("obstacles", [])]
        return cls(width=data.get("width", config.LEVEL_WIDTH), obstacles=obstacles)

    # -- generation ---------------------------------------------------------
    @classmethod
    def generate_default(cls, seed: int = 42) -> "Level":
        """A hand-tuned-ish deterministic level: gradually tighter spacing and
        taller cacti so the difficulty increases as game speed ramps up."""
        rng = random.Random(seed)
        obstacles: list[Obstacle] = []
        x = 700.0  # first obstacle has breathing room
        while x < config.LEVEL_WIDTH - 300:
            progress = x / config.LEVEL_WIDTH
            # Spacing shrinks from ~520px down to ~300px across the level.
            gap = rng.uniform(520, 600) - progress * 240
            gap = max(280.0, gap)
            height = int(rng.uniform(
                config.MIN_CACTUS_HEIGHT,
                config.MIN_CACTUS_HEIGHT + (config.MAX_CACTUS_HEIGHT - config.MIN_CACTUS_HEIGHT) * (0.5 + 0.5 * progress),
            ))
            width = rng.choice([config.DEFAULT_CACTUS_WIDTH,
                                config.DEFAULT_CACTUS_WIDTH,
                                config.DEFAULT_CACTUS_WIDTH + 16])  # occasional wide cactus
            obstacles.append(Obstacle(x, width, height))
            x += gap
        return cls(width=config.LEVEL_WIDTH, obstacles=obstacles)


def ensure_default_level() -> Level:
    """Load the default level from disk, creating it first if missing."""
    if os.path.exists(config.DEFAULT_LEVEL_PATH):
        return Level.load(config.DEFAULT_LEVEL_PATH)
    level = Level.generate_default()
    level.save(config.DEFAULT_LEVEL_PATH)
    return level

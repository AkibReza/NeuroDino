"""
dino.py
=======
A single dinosaur agent. Holds physics state, its neural-network brain, and the
bookkeeping needed for fitness. All dinos in a generation share one global
scroll position (`world_x`), so the only thing that distinguishes them is *when*
they jump. Collisions are still resolved per-dinosaur.
"""
from __future__ import annotations

import config
from neural_network import NeuralNetwork


class Dino:
    def __init__(self, dino_id: int, brain: NeuralNetwork):
        self.id = dino_id                       # 1..POPULATION_SIZE
        self.lane = (dino_id - 1) // config.DINOS_PER_LANE  # 0..NUM_LANES-1
        self.slot = (dino_id - 1) % config.DINOS_PER_LANE   # 0..9 within lane
        self.brain = brain
        self.reset()

    def reset(self) -> None:
        self.world_x = 0.0
        # y is measured from the ground line. 0 == on the ground, positive == up.
        self.y = 0.0
        self.vy = 0.0
        self.on_ground = True
        self.alive = True
        self.solved = False                     # reached the level endpoint
        self.distance = 0.0                     # world_x reached when it stopped
        self.obstacles_cleared = 0
        self.fitness = 0.0
        self._next_idx = 0                      # index of next un-passed obstacle
        self.last_inputs = [0.0, 0.0, 0.0, 0.0]  # for the replay NN overlay
        self.last_output = 0.0

    # -- sensing ------------------------------------------------------------
    def sense(self, world_x: float, speed: float, level) -> list[float]:
        """Build the 4-element normalised input vector for the network."""
        obstacles = level.obstacles
        # Advance the "next obstacle" pointer past any fully-cleared cacti.
        while (self._next_idx < len(obstacles)
               and obstacles[self._next_idx].right < world_x):
            self._next_idx += 1
            self.obstacles_cleared += 1

        if self._next_idx < len(obstacles):
            nxt = obstacles[self._next_idx]
            dist = max(0.0, nxt.x - world_x)
            dist_norm = min(1.0, dist / config.SENSOR_RANGE)
            height_norm = nxt.height / config.MAX_CACTUS_HEIGHT
        else:
            # No more obstacles ahead: report "far away, no height".
            dist_norm = 1.0
            height_norm = 0.0

        speed_norm = ((speed - config.BASE_SPEED)
                      / max(1e-6, (config.MAX_SPEED - config.BASE_SPEED)))
        y_norm = min(1.0, self.y / config.MAX_JUMP_HEIGHT)
        self.last_inputs = [dist_norm, height_norm, speed_norm, y_norm]
        return self.last_inputs

    # -- physics ------------------------------------------------------------
    def jump(self) -> None:
        if self.on_ground:
            self.vy = -config.JUMP_VELOCITY  # stored as upward-positive velocity
            self.on_ground = False

    def update_physics(self) -> None:
        if not self.on_ground:
            self.y += self.vy
            self.vy -= config.GRAVITY
            if self.y <= 0.0:
                self.y = 0.0
                self.vy = 0.0
                self.on_ground = True

    # -- collision ----------------------------------------------------------
    def collides_with_current(self, world_x: float, level) -> bool:
        """Check overlap against the obstacle(s) near the dino's fixed x.

        Screen-space rectangles: the dino occupies a fixed horizontal band; an
        obstacle's horizontal position relative to the dino is (obstacle.x -
        world_x). They overlap horizontally when that offset is within the
        dino's footprint. Vertically, the dino clears the cactus if the bottom
        of the dino is above the top of the cactus.
        """
        dino_left = 0.0                     # dino spans [0, DINO_WIDTH] relative
        dino_right = config.DINO_WIDTH
        dino_bottom = self.y                # height above ground of dino's feet
        for ob in level.obstacles:
            rel = ob.x - world_x            # obstacle left edge relative to dino
            if rel > dino_right:
                break                       # obstacles are sorted; rest are ahead
            if rel + ob.width < dino_left:
                continue                    # already passed
            # Horizontal overlap confirmed; check vertical clearance.
            if dino_bottom < ob.height:
                return True
        return False

    # -- fitness ------------------------------------------------------------
    def compute_fitness(self) -> float:
        """Non-negative fitness per the modified spec:
            distance * 1.0 + obstacles_cleared * 200
        """
        self.fitness = self.distance * 1.0 + self.obstacles_cleared * 200.0
        return self.fitness

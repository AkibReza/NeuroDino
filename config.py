"""
config.py
=========
Central configuration for NeuroDino. Every tunable constant lives here so the
rest of the codebase never hard-codes magic numbers. Importing this module is
cheap and side-effect free.
"""

# ---------------------------------------------------------------------------
# Population / Genetic Algorithm
# ---------------------------------------------------------------------------
POPULATION_SIZE = 100          # total number of dinosaurs per generation
NUM_LANES = 10                 # visual lanes
DINOS_PER_LANE = POPULATION_SIZE // NUM_LANES  # 10

ELITE_COUNT = 6                # top performers copied unchanged into next gen
TOURNAMENT_SIZE = 5            # contestants per tournament selection round
MUTATION_RATE = 0.15           # probability a given weight is perturbed
MUTATION_SCALE = 0.5           # std-dev of the Gaussian perturbation
CROSSOVER_RATE = 0.75          # probability two parents are crossed (else clone)
WEIGHT_INIT_SCALE = 1.0        # std-dev for initial random weights

# ---------------------------------------------------------------------------
# Neural Network architecture (per the spec)
# ---------------------------------------------------------------------------
NN_INPUT_SIZE = 4              # [dist_to_cactus, cactus_height, speed, dino_y]
NN_HIDDEN_SIZE = 8             # ReLU
NN_OUTPUT_SIZE = 1             # sigmoid -> jump if > 0.5
JUMP_THRESHOLD = 0.5

# ---------------------------------------------------------------------------
# Level geometry
# ---------------------------------------------------------------------------
LEVEL_WIDTH = 10000            # pixels; reaching this == solved
SENSOR_RANGE = 600.0           # px over which "distance to next cactus" normalises
MAX_CACTUS_HEIGHT = 70.0       # px; used to normalise cactus height input
MIN_CACTUS_HEIGHT = 30
DEFAULT_CACTUS_WIDTH = 24

# ---------------------------------------------------------------------------
# Physics (fixed for every generation; not editable in the level editor)
# ---------------------------------------------------------------------------
GRAVITY = 0.9                  # px / frame^2
JUMP_VELOCITY = -16.0          # px / frame (negative = upward)
MAX_JUMP_HEIGHT = 130.0        # px; used to normalise dino vertical position
DINO_WIDTH = 34
DINO_HEIGHT = 38

# Game speed ramps up across the level so the "speed" NN input is meaningful.
BASE_SPEED = 6.0               # px / frame at level start
MAX_SPEED = 13.0               # px / frame at level end
SPEED_RAMP_DISTANCE = LEVEL_WIDTH  # distance over which speed ramps base->max

# A generation that never resolves is force-stopped after this many frames.
MAX_FRAMES_PER_GENERATION = 6000

# ---------------------------------------------------------------------------
# Rendering / window layout
# ---------------------------------------------------------------------------
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 820
SIDEBAR_WIDTH = 360            # right-hand leaderboard / controls panel
GAME_AREA_WIDTH = WINDOW_WIDTH - SIDEBAR_WIDTH
TOP_BAR_HEIGHT = 40            # thin status strip above the lanes

LANE_AREA_TOP = TOP_BAR_HEIGHT
LANE_AREA_HEIGHT = WINDOW_HEIGHT - TOP_BAR_HEIGHT
LANE_HEIGHT = LANE_AREA_HEIGHT // NUM_LANES
DINO_SCREEN_X = 70             # fixed horizontal screen position of every dino

def init_layout(w, h):
    global WINDOW_WIDTH, WINDOW_HEIGHT, GAME_AREA_WIDTH, LANE_AREA_HEIGHT, LANE_HEIGHT
    WINDOW_WIDTH = w
    WINDOW_HEIGHT = h
    GAME_AREA_WIDTH = WINDOW_WIDTH - SIDEBAR_WIDTH
    LANE_AREA_HEIGHT = WINDOW_HEIGHT - TOP_BAR_HEIGHT
    LANE_HEIGHT = LANE_AREA_HEIGHT // NUM_LANES

FPS = 60                       # render frame-rate cap (1x speed)

# Speed multipliers. Anything above 1 runs headless (per the spec) so Pygame
# rendering never becomes the bottleneck.
SPEED_MULTIPLIERS = [1, 2, 5, 10]
HEADLESS_THRESHOLD = 2         # multipliers >= this run headless

# ---------------------------------------------------------------------------
# Colours (R, G, B)
# ---------------------------------------------------------------------------
COL_BG = (24, 26, 33)
COL_PANEL = (32, 35, 44)
COL_PANEL_LIGHT = (44, 48, 60)
COL_TEXT = (228, 231, 240)
COL_TEXT_DIM = (150, 156, 170)
COL_ACCENT = (94, 200, 160)
COL_GROUND = (70, 74, 86)
COL_CACTUS = (90, 170, 90)
COL_CACTUS_DARK = (60, 120, 60)
COL_GRID = (40, 43, 52)
COL_CHAMPION = (255, 215, 0)
COL_DEAD = (70, 72, 80)

# Dinosaur spacing and 10 fixed slot colors
DINO_SPACING = 80
DINO_COLORS = [
    (239, 71, 111),   # 0: Coral Red
    (247, 140, 107),  # 1: Soft Orange
    (255, 209, 102),  # 2: Sunny Yellow
    (6, 214, 160),    # 3: Mint Green
    (17, 138, 178),   # 4: Ocean Blue
    (131, 56, 236),   # 5: Royal Purple
    (255, 0, 110),    # 6: Hot Pink
    (58, 125, 68),    # 7: Forest Green
    (74, 78, 105),    # 8: Slate Gray
    (201, 24, 74),    # 9: Crimson Red
]

LANE_COLORS = DINO_COLORS  # For backwards compatibility if referenced elsewhere


# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEVELS_DIR = os.path.join(BASE_DIR, "levels")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
DEFAULT_LEVEL_PATH = os.path.join(LEVELS_DIR, "default_level.json")
SNAPSHOT_PATH = os.path.join(OUTPUT_DIR, "generation_history.json")
CSV_LOG_PATH = os.path.join(OUTPUT_DIR, "training_log.csv")

os.makedirs(LEVELS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def speed_at(distance: float) -> float:
    """Game speed (px/frame) as a function of distance travelled into the level."""
    t = min(1.0, max(0.0, distance / SPEED_RAMP_DISTANCE))
    return BASE_SPEED + (MAX_SPEED - BASE_SPEED) * t

# NeuroDino — Neuroevolution Chrome-Dinosaur

A standalone Python application where a population of **100 AI-controlled
dinosaurs** learns to clear a fixed Chrome-Dinosaur-style level through
**neuroevolution** — a genetic algorithm that breeds small neural networks
across generations using selection, crossover, and mutation.

The level never changes between generations, so any improvement you see is the
population genuinely *learning* the obstacle course, not getting lucky.

---

## Quick start

From inside the project directory:

```bash
pip install pygame numpy matplotlib      # pandas is optional
python main.py
```

Then click **Start** (or press `Space`) and watch the dinos learn.

> Run `python main.py` from **inside** the `neurodino/` folder so the relative
> `levels/` and `output/` paths resolve correctly.

### Dependencies

| Package      | Required | Used for                                |
|--------------|----------|-----------------------------------------|
| `pygame`     | yes      | window, rendering, input                |
| `numpy`      | yes      | neural-network math, genome operations  |
| `matplotlib` | yes      | training graphs (Agg backend, no GUI)   |
| `pandas`     | optional | nicer CSV handling if present           |

Python 3.10+ recommended (developed/tested on 3.12).

---

## What you're looking at

The window is split into a **game area** (left) and a **control sidebar** (right).

- **10 lanes**, 10 dinos each = 100 dinos, all running the same level in sync.
- Lanes are **visual only** — every dino faces the exact same obstacles at the
  same scroll position. Collisions are computed **per-dino**, so within a lane
  some dinos clear a cactus while others crash into it.
- Each lane has its own **color family** (Lane 1 reds, Lane 2 blues, …) and each
  dino carries a unique ID label.
- The sidebar shows a **live leaderboard**: current generation, alive count,
  best/avg fitness, the top 10 dinos (ID + lane), and the current champion.

When a generation ends (all 100 dinos have either crashed or reached the
10,000 px finish line), fitness is scored, the next generation is bred, and the
run restarts on the same level.

---

## Controls

### Sidebar buttons
**Start · Pause/Resume · Reset · Replay Champion · Previous Generations ·
Level Editor · Save Graphs**, plus speed buttons **1x / 2x / 5x / 10x** and a
**Render every frame** toggle.

### Keyboard

| Key       | Action                                              |
|-----------|-----------------------------------------------------|
| `Space`   | Start / Pause / Resume training                     |
| `R`       | Reset (back to generation 1, empty history)         |
| `E`       | Open the Level Editor                               |
| `H`       | Open the Generation History viewer                  |
| `G`       | Save the three training graphs to `output/`         |
| `1`–`4`   | Set speed to 1x / 2x / 5x / 10x                     |
| `Esc`     | Back to training (from any sub-mode)                |
| `↑` / `↓` | Scroll the history list (in History view)           |

### Speed & headless mode
- **1x** renders every frame so you can watch the action.
- **2x / 5x / 10x** automatically run **headless** — physics and neural-network
  evaluation run with no per-frame drawing, then the final state of the
  generation is shown. This stops Pygame's rendering from bottlenecking high
  speed multipliers. Higher multipliers linger less on the result screen.
- The **Render every frame** toggle lets you force rendering on, or keep things
  headless even at 1x.

---

## Champion replay

Replays the **best dino ever seen** alone on the full level (no other lanes).
A live overlay shows the network's four inputs (distance to next cactus, its
height, current game speed, the dino's vertical position), the raw sigmoid
output, and the resulting **RUN / JUMP** decision each frame. The replay is
deterministic — it reproduces the champion's original run exactly.

---

## Generation history

A snapshot is saved **every generation**, not just at milestones. The history
viewer lists all available generations in a scrollable panel showing generation
number and best/avg fitness; clicking a row replays that generation's champion.
Each snapshot stores the generation number, best fitness, average fitness, the
champion's network weights, and the champion's ID.

---

## Level editor

Press `E` to design your own course:

| Input              | Action                              |
|--------------------|-------------------------------------|
| Left click         | place a cactus (or pick one to drag)|
| Left drag          | move the picked-up cactus           |
| Right click        | delete the cactus under the cursor  |
| `[` / `]`          | decrease / increase cactus height   |
| `A`/`←`, `D`/`→`   | scroll the level preview            |
| `S`                | save level to JSON                  |
| `L`                | reload level from JSON              |
| `Esc`              | back to training                    |

Terrain, gravity, physics, and game speed are intentionally **not** editable —
only obstacle layout. Levels are stored as JSON in `levels/`.

---

## The neural network

Each dino is driven by a tiny feed-forward network:

```
Input (4)            Hidden (8, ReLU)        Output (1, sigmoid)
─────────            ────────────────        ───────────────────
distance to cactus
cactus height    →   8 neurons          →    jump if output > 0.5
game speed                                    else keep running
dino vertical pos
```

All inputs are normalized to 0–1. The network's weights and biases are flattened
into a single **49-value genome** that the genetic algorithm operates on.

### Fitness

```
fitness = distance_traveled * 1.0  +  obstacles_cleared * 200
```

Fitness is **always non-negative** — there is no crash penalty, because dying
early already means less distance and fewer obstacles cleared. (Negative scores
break tournament/rank selection in early generations, so they're avoided.)

### How a new generation is bred

1. **Elitism** — the top performers carry over unchanged.
2. **Selection** — tournament selection picks fit parents.
3. **Crossover** — uniform crossover mixes two parent genomes.
4. **Mutation** — Gaussian noise nudges weights to explore new behavior.

Default tuning (in `config.py`): population 100, elites 6, tournament size 5,
crossover rate 0.75, mutation rate 0.15, mutation scale 0.5. Edit `config.py` to
experiment.

---

## Outputs

Written to the `output/` folder:

- `training_log.csv` — per-generation log: generation, best fitness, avg
  fitness, champion ID, elapsed time.
- `generation_history.json` — every generation's snapshot (used by the history
  viewer and champion replay).
- `graph_best_fitness.png` — best fitness vs generation.
- `graph_avg_fitness.png` — average fitness vs generation.
- `graph_alive_count.png` — dinos still alive vs generation.

Graphs are generated on demand (**Save Graphs** / `G`) and use matplotlib's
headless Agg backend, so they never require a display.

---

## Project structure

| File                  | Responsibility                                            |
|-----------------------|-----------------------------------------------------------|
| `main.py`             | app entry point; state machine + main loop + controls     |
| `config.py`           | all tunable constants and file paths                      |
| `neural_network.py`   | 4-8-1 network, genome encode/decode, forward pass         |
| `dino.py`             | a single dino: sensing, physics, collisions, fitness      |
| `simulation.py`       | runs one generation (stepped or headless)                 |
| `genetic_algorithm.py`| selection, crossover, mutation, next-gen breeding         |
| `level.py`            | obstacle + level model; JSON load/save; default level     |
| `snapshots.py`        | per-generation snapshot storage + JSON persistence        |
| `logger.py`           | CSV logging + matplotlib graph generation                 |
| `renderer.py`         | draws world, sidebar, leaderboard, replay, history        |
| `level_editor.py`     | interactive cactus placement / editing                    |
| `ui.py`               | fonts, buttons, text and shared UI helpers                |

A `default_level.json` (22 obstacles of increasing difficulty over 10,000 px)
ships in `levels/` so the app runs immediately.

---

## How it's wired together

`main.py` runs a state machine with four modes — **training**, **champion
replay**, **history**, and **editor** — and a 60 FPS loop. During training it
drives `Simulation`, which steps every live `Dino` (each dino senses the level,
runs its `NeuralNetwork`, and updates physics). When the generation ends,
`PerformanceLogger` records a CSV row, `GenerationHistory` stores a snapshot, and
`GeneticAlgorithm` breeds the next population. `Renderer` handles all drawing;
in headless mode it's skipped until the generation finishes.

Enjoy watching them learn.

"""
neural_network.py
=================
A tiny, dependency-light feed-forward network used as each dinosaur's "brain".

Architecture (fixed by the spec):
    4 inputs -> 8 hidden (ReLU) -> 1 output (sigmoid)

The network is fully described by a flat "genome" vector, which is what the
genetic algorithm operates on. The split between weights/biases is handled here
so the GA can stay blissfully ignorant of the network shape.
"""
from __future__ import annotations

import numpy as np

import config


def _sigmoid(x: np.ndarray) -> np.ndarray:
    # Clip to avoid overflow warnings on extreme pre-activations.
    return 1.0 / (1.0 + np.exp(-np.clip(x, -60.0, 60.0)))


def _relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(0.0, x)


class NeuralNetwork:
    """Feed-forward NN with weights stored as NumPy arrays.

    Layout of the genome (flattened, in this order):
        W1: (input, hidden)
        b1: (hidden,)
        W2: (hidden, output)
        b2: (output,)
    """

    INPUT = config.NN_INPUT_SIZE
    HIDDEN = config.NN_HIDDEN_SIZE
    OUTPUT = config.NN_OUTPUT_SIZE

    # Number of scalar parameters in the genome.
    GENOME_SIZE = (
        INPUT * HIDDEN + HIDDEN + HIDDEN * OUTPUT + OUTPUT
    )

    def __init__(self, genome: np.ndarray | None = None,
                 rng: np.random.Generator | None = None):
        self.rng = rng if rng is not None else np.random.default_rng()
        if genome is None:
            genome = self.rng.normal(
                0.0, config.WEIGHT_INIT_SCALE, size=self.GENOME_SIZE
            )
        self.set_genome(np.asarray(genome, dtype=np.float64))

    # -- genome <-> weights -------------------------------------------------
    def set_genome(self, genome: np.ndarray) -> None:
        if genome.shape[0] != self.GENOME_SIZE:
            raise ValueError(
                f"genome has {genome.shape[0]} params, expected {self.GENOME_SIZE}"
            )
        self.genome = genome.astype(np.float64)
        i = 0
        n = self.INPUT * self.HIDDEN
        self.W1 = self.genome[i:i + n].reshape(self.INPUT, self.HIDDEN); i += n
        n = self.HIDDEN
        self.b1 = self.genome[i:i + n]; i += n
        n = self.HIDDEN * self.OUTPUT
        self.W2 = self.genome[i:i + n].reshape(self.HIDDEN, self.OUTPUT); i += n
        n = self.OUTPUT
        self.b2 = self.genome[i:i + n]; i += n

    def get_genome(self) -> np.ndarray:
        return self.genome.copy()

    # -- inference ----------------------------------------------------------
    def forward(self, inputs) -> float:
        """Run a single forward pass. `inputs` is a length-4 sequence.

        Returns the raw sigmoid output in [0, 1].
        """
        x = np.asarray(inputs, dtype=np.float64).reshape(1, self.INPUT)
        h = _relu(x @ self.W1 + self.b1)
        out = _sigmoid(h @ self.W2 + self.b2)
        return float(out[0, 0])

    def should_jump(self, inputs) -> bool:
        return self.forward(inputs) > config.JUMP_THRESHOLD

    # -- utility ------------------------------------------------------------
    def clone(self) -> "NeuralNetwork":
        return NeuralNetwork(self.get_genome(), rng=self.rng)

    def to_list(self) -> list:
        """JSON-serialisable representation of the genome."""
        return self.genome.tolist()

    @classmethod
    def from_list(cls, data: list,
                  rng: np.random.Generator | None = None) -> "NeuralNetwork":
        return cls(np.asarray(data, dtype=np.float64), rng=rng)

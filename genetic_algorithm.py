"""
genetic_algorithm.py
====================
Breeds the next generation of dinosaur brains from the current one.

Pipeline per generation:
  1. Fitness already computed by the simulation.
  2. Elitism: copy the top ELITE_COUNT genomes unchanged.
  3. Fill the rest of the population by:
       parent_a, parent_b <- tournament selection
       child <- crossover(parent_a, parent_b)   (with prob CROSSOVER_RATE)
       child <- mutate(child)

Fitness is non-negative (enforced upstream in dino.compute_fitness), so
tournament selection is stable from generation 1.
"""
from __future__ import annotations

import numpy as np

import config
from dino import Dino
from neural_network import NeuralNetwork


class GeneticAlgorithm:
    def __init__(self, seed: int | None = None):
        self.rng = np.random.default_rng(seed)

    # -- population bootstrap ----------------------------------------------
    def initial_population(self) -> list[Dino]:
        dinos = []
        for i in range(config.POPULATION_SIZE):
            brain = NeuralNetwork(rng=self.rng)
            dinos.append(Dino(dino_id=i + 1, brain=brain))
        return dinos

    # -- operators ----------------------------------------------------------
    def _tournament(self, dinos: list[Dino]) -> Dino:
        contenders = self.rng.choice(
            len(dinos), size=min(config.TOURNAMENT_SIZE, len(dinos)),
            replace=False,
        )
        best = max((dinos[i] for i in contenders), key=lambda d: d.fitness)
        return best

    def _crossover(self, g1: np.ndarray, g2: np.ndarray) -> np.ndarray:
        """Uniform crossover: each weight comes from one parent at random."""
        if self.rng.random() > config.CROSSOVER_RATE:
            return g1.copy()
        mask = self.rng.random(g1.shape[0]) < 0.5
        child = np.where(mask, g1, g2)
        return child

    def _mutate(self, genome: np.ndarray) -> np.ndarray:
        mask = self.rng.random(genome.shape[0]) < config.MUTATION_RATE
        noise = self.rng.normal(0.0, config.MUTATION_SCALE, size=genome.shape[0])
        genome = genome + mask * noise
        return genome

    # -- breeding -----------------------------------------------------------
    def evolve(self, dinos: list[Dino]) -> list[Dino]:
        """Return a fresh list of Dinos for the next generation."""
        ranked = sorted(dinos, key=lambda d: d.fitness, reverse=True)

        next_genomes: list[np.ndarray] = []

        # Elitism: carry the best genomes through unchanged.
        for elite in ranked[:config.ELITE_COUNT]:
            next_genomes.append(elite.brain.get_genome())

        # Fill the remainder via selection + crossover + mutation.
        while len(next_genomes) < config.POPULATION_SIZE:
            pa = self._tournament(dinos)
            pb = self._tournament(dinos)
            child = self._crossover(pa.brain.get_genome(), pb.brain.get_genome())
            child = self._mutate(child)
            next_genomes.append(child)

        new_dinos = []
        for i, genome in enumerate(next_genomes[:config.POPULATION_SIZE]):
            brain = NeuralNetwork(genome=genome, rng=self.rng)
            new_dinos.append(Dino(dino_id=i + 1, brain=brain))
        return new_dinos

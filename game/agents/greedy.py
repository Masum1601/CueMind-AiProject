"""Greedy best-first agent (the Easy AI).

It scores every direct pot with the heuristic h = chance x points, tests the
top few once in the physics engine, and plays the one that scores most right
now. It never thinks about the next shot or the opponent.
"""
import numpy as np

from ..physics import simulate_shot
from .. import config as C
from .common import Decision, Clock, candidates, place_best


class GreedyAgent:
    name = "Greedy"
    algo = "Greedy best-first"

    def __init__(self, seed=None):
        self.rng = np.random.default_rng(seed)

    def place(self, match, stats=None):
        return place_best(match.snapshot(), stats)

    def choose(self, match, budget=0.5, progress=None):
        clock = Clock(budget)
        state = match.snapshot()
        shots = candidates(state, wide=False, rng=self.rng)[:8]
        ranked = []
        sims = 0
        for s in shots:
            after, potted, first = simulate_shot(state.table, s.angle, s.speed)
            sims += 1
            foul = after.pocket_of[0] >= 0 or first < 0
            pts = sum(C.ball_points(b) for b in potted if b > 0) - (C.FOUL_POINTS if foul else 0)
            s.score = pts + 0.3 * s.est
            ranked.append((s, s.score, None))
            if clock.left() < 0:
                break
        ranked.sort(key=lambda r: -r[1])
        best = ranked[0][0] if ranked else shots[0]
        return Decision(best, {"algorithm": self.algo, "candidates": len(shots), "sims": sims,
                               "time": budget - clock.left()}, ranked[:6], [])

"""Minimax agent: alpha-beta search with chance nodes, deepened iteratively.

MAX  = my shot, MIN = the opponent's shot. If a player pots a ball they shoot
again, so two MAX levels can follow each other: the tree follows the real turn.

Shots can miss, so a shot is a CHANCE node: we play it a few times with random
execution error and average the results. Alpha-beta pruning still works across
chance nodes when values are bounded (Ballard's Star1): after k of n samples we
know the best and worst the average can still become, and stop early when that
range is already outside (alpha, beta).

Iterative deepening (IDDFS): search 1 shot deep, then 2, then 3, until the time
budget runs out, and keep the best shot of the deepest finished search.
"""
import math

import numpy as np

from .common import (Decision, Clock, TimeUp, VMIN, VMAX, candidates, dedupe, evaluate,
                     play, place_best, apply_plan_bonus)
from ..planner import plan_runout


class MinimaxAgent:
    name = "Minimax"
    algo = "Minimax + alpha-beta + IDDFS"

    def __init__(self, seed=None, root_width=10, inner_width=5, samples_root=3, samples_inner=2, max_depth=4):
        self.rng = np.random.default_rng(seed)
        self.root_width = root_width
        self.inner_width = inner_width
        self.samples_root = samples_root
        self.samples_inner = samples_inner
        self.max_depth = max_depth

    def place(self, match, stats=None):
        return place_best(match.snapshot(), stats)

    # ------------------------------------------------------------ search
    def choose(self, match, budget=2.0, progress=None):
        clock = Clock(budget)
        root = match.snapshot()
        self.me = root.turn
        self.stats = {"algorithm": self.algo, "nodes": 0, "sims": 0, "pruned": 0, "depth": 0}
        plan, _ = plan_runout(root.table, stats=self.stats) if not root.is_break else ([], 0)
        shots = dedupe(apply_plan_bonus(candidates(root, wide=True, stats=self.stats, rng=self.rng), plan),
                       self.root_width)
        self.stats["candidates"] = len(shots)
        if root.is_break:
            return Decision(shots[0], self.stats, [(s, 0.0, None) for s in shots], plan)
        best, scores = shots[0], {}
        for depth in range(1, self.max_depth + 1):
            try:
                alpha = -math.inf
                cur = {}
                for s in shots:
                    v = self._chance(root, s, depth, alpha, math.inf, self.samples_root, clock)
                    cur[s.key()] = v
                    if v > alpha:
                        alpha, best_now = v, s
                best, scores = best_now, cur
                self.stats["depth"] = depth
                shots.sort(key=lambda s: -cur.get(s.key(), -99))     # best first: more pruning next time
                if progress:
                    p = dict(self.stats)
                    p["top"] = [(s, cur.get(s.key(), 0.0), None) for s in shots[:5]]
                    progress(p)
            except TimeUp:
                break
        if not scores:          # not even depth 1 finished: trust the heuristic
            scores = {s.key(): s.value for s in shots}
        ranked = sorted(((s, scores.get(s.key(), -99), None) for s in shots), key=lambda r: -r[1])
        self.stats["time"] = budget - clock.left()
        self.stats["value"] = round(scores.get(best.key(), 0.0), 2)
        return Decision(best, self.stats, ranked[:6], plan)

    def _chance(self, state, shot, depth, alpha, beta, n, clock):
        total = 0.0
        for k in range(n):
            clock.check()
            child = play(state, shot.angle, shot.speed, self.rng, self.stats)
            self.stats["nodes"] += 1
            rest = n - k - 1
            lo = (n * alpha - total - rest * VMAX) if alpha > -math.inf else -math.inf
            hi = (n * beta - total - rest * VMIN) if beta < math.inf else math.inf
            v = self._value(child, depth - 1, max(lo, VMIN - 1), min(hi, VMAX + 1), clock)
            total += v
            if alpha > -math.inf and (total + rest * VMAX) / n <= alpha:
                self.stats["pruned"] += rest
                return (total + rest * VMAX) / n
            if beta < math.inf and (total + rest * VMIN) / n >= beta:
                self.stats["pruned"] += rest
                return (total + rest * VMIN) / n
        return total / n

    def _value(self, state, depth, alpha, beta, clock):
        if depth == 0 or state.over:
            return evaluate(state, self.me)
        shots = dedupe(candidates(state, wide=False), self.inner_width)
        if state.turn == self.me:                       # MAX
            v = -math.inf
            for s in shots:
                v = max(v, self._chance(state, s, depth, alpha, beta, self.samples_inner, clock))
                alpha = max(alpha, v)
                if alpha >= beta:
                    self.stats["pruned"] += 1
                    break
            return v
        v = math.inf                                    # MIN
        for s in shots:
            v = min(v, self._chance(state, s, depth, alpha, beta, self.samples_inner, clock))
            beta = min(beta, v)
            if beta <= alpha:
                self.stats["pruned"] += 1
                break
        return v

"""Monte Carlo Tree Search agent (UCB1).

Each iteration:
  1. Selection      walk down the tree, always taking the child with the best UCB1
  2. Expansion      add one untried shot as a new child
  3. Simulation     play the shots on that path with random execution error, then
                    a quick greedy play-out, and score the end position
  4. Backpropagation add the result (0..1) to every node on the path

    UCB1(child) = W/N + C * sqrt(ln N_parent / N)

The tree is "open loop": shots are re-simulated with fresh noise every time,
so a node stores how good a choice is on average, not one fixed outcome.
Below the root, a move means "the k-th best shot in the position you reach".
When time is up we play the root shot with the most visits.
"""
import math

import numpy as np

from .common import (Decision, Clock, TimeUp, candidates, dedupe, evaluate, play,
                     place_best, apply_plan_bonus)
from ..planner import plan_runout


class Node:
    __slots__ = ("parent", "action", "children", "N", "W", "mover", "order")

    def __init__(self, parent, action, mover):
        self.parent = parent
        self.action = action
        self.children = {}
        self.N = 0
        self.W = 0.0
        self.mover = mover          # who played the move that leads here
        self.order = 0


class MCTSAgent:
    name = "MCTS"
    algo = "Monte Carlo Tree Search (UCB1)"

    def __init__(self, seed=None, c=1.4, root_width=14, inner_width=4, max_tree_depth=3, rollout=1):
        self.rng = np.random.default_rng(seed)
        self.c = c
        self.root_width = root_width
        self.inner_width = inner_width
        self.max_tree_depth = max_tree_depth
        self.rollout = rollout

    def place(self, match, stats=None):
        return place_best(match.snapshot(), stats)

    def _allowed(self, node):
        # progressive widening: more children may be opened as a node gets visited
        return int(math.ceil(1.5 * math.sqrt(node.N + 1)))

    def choose(self, match, budget=2.0, progress=None):
        clock = Clock(budget)
        root_state = match.snapshot()
        me = root_state.turn
        stats = {"algorithm": self.algo, "iterations": 0, "sims": 0, "depth": 0}
        plan, _ = plan_runout(root_state.table, stats=stats) if not root_state.is_break else ([], 0)
        shots = dedupe(apply_plan_bonus(candidates(root_state, wide=True, stats=stats, rng=self.rng), plan),
                       self.root_width)
        stats["candidates"] = len(shots)
        if root_state.is_break:
            return Decision(shots[0], stats, [(s, 0.0, None) for s in shots], plan)
        root = Node(None, None, 1 - me)
        try:
            while True:
                clock.check()
                self._iterate(root, root_state, shots, me, stats, clock)
                stats["iterations"] += 1
                if progress and stats["iterations"] % 10 == 0:
                    progress(self._summary(root, shots, stats))
        except TimeUp:
            pass
        if not root.children:
            return Decision(shots[0], stats, [(s, s.value, 0) for s in shots], plan)
        best_a = max(root.children, key=lambda a: root.children[a].N)
        ranked = sorted(((shots[a], ch.W / max(ch.N, 1), ch.N) for a, ch in root.children.items()),
                        key=lambda r: -r[2])
        stats["time"] = budget - clock.left()
        stats["value"] = round(root.children[best_a].W / max(root.children[best_a].N, 1), 3)
        return Decision(shots[best_a], stats, ranked[:6], plan)

    def _summary(self, root, shots, stats):
        s = dict(stats)
        s["top"] = sorted(((shots[a], ch.W / max(ch.N, 1), ch.N) for a, ch in root.children.items()),
                          key=lambda r: -r[2])[:5]
        return s

    def _shot_for(self, node, state, action, root_shots):
        if node.parent is None:
            return root_shots[action]
        opts = dedupe(candidates(state, wide=False), self.inner_width)
        return opts[min(action, len(opts) - 1)]

    def _iterate(self, root, root_state, root_shots, me, stats, clock):
        node, state, path, depth = root, root_state, [root], 0
        # 1-2. selection and expansion
        while not state.over and depth < self.max_tree_depth:
            n_actions = len(root_shots) if node.parent is None else self.inner_width
            untried = [a for a in range(min(n_actions, self._allowed(node))) if a not in node.children]
            mover = state.turn
            if untried:
                a = untried[0]
                shot = self._shot_for(node, state, a, root_shots)
                child = Node(node, a, mover)
                node.children[a] = child
                state = play(state, shot.angle, shot.speed, self.rng, stats)
                node = child
                path.append(node)
                depth += 1
                break
            logn = math.log(node.N + 1)
            a, node_next = max(node.children.items(),
                               key=lambda kv: kv[1].W / kv[1].N + self.c * math.sqrt(logn / kv[1].N))
            shot = self._shot_for(node, state, a, root_shots)
            state = play(state, shot.angle, shot.speed, self.rng, stats)
            node = node_next
            path.append(node)
            depth += 1
        stats["depth"] = max(stats["depth"], depth)
        # 3. simulation: a short greedy play-out
        for _ in range(self.rollout):
            if state.over:
                break
            clock.check()
            s = candidates(state, wide=False)[0]
            state = play(state, s.angle, s.speed, self.rng, stats)
        r = 1.0 / (1.0 + math.exp(-evaluate(state, me) / 2.0))
        # 4. backpropagation
        for n in path:
            n.N += 1
            n.W += r if n.mover == me else 1.0 - r

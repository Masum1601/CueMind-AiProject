"""Tools every agent shares: noisy execution, playing a shot on a copy, scoring a state."""
import math
import time
from dataclasses import dataclass, field

import numpy as np

from .. import config as C
from .. import shots as S
from ..physics import simulate_shot
from ..planner import plan_runout

VMIN, VMAX = -20.0, 20.0


class TimeUp(Exception):
    pass


@dataclass
class Decision:
    shot: object
    stats: dict = field(default_factory=dict)
    ranked: list = field(default_factory=list)    # [(shot, score, visits_or_None)]
    plan: list = field(default_factory=list)      # A* order [(ball, pocket)]


def noisy(angle, speed, rng):
    a = angle + rng.normal(0.0, math.radians(C.NOISE_ANGLE_DEG))
    v = speed * (1.0 + rng.normal(0.0, C.NOISE_SPEED))
    return a, min(max(v, 20.0), C.MAX_SPEED)


def play(state, angle, speed, rng=None, counter=None):
    """Return the match state after this shot (on copies; the real game is untouched)."""
    if rng is not None:
        angle, speed = noisy(angle, speed, rng)
    after, _, _ = simulate_shot(state.table, angle, speed)
    nxt = state.snapshot()
    nxt.apply_result(after)
    if nxt.ball_in_hand and not nxt.over:
        place_best(nxt)
    if counter is not None:
        counter["sims"] = counter.get("sims", 0) + 1
    return nxt


def pot_quality(table):
    """How good the best simple pot is for whoever shoots next (expected points)."""
    best = 0.0
    if not table.alive[0]:
        return 0.0
    cue = (table.pos[0, 0], table.pos[0, 1])
    for b in range(1, 16):
        if not table.alive[b]:
            continue
        bx, by = table.pos[b]
        for p in range(6):
            tx, ty = S.pocket_aim(p)
            (gx, gy), (ux, uy), d2 = S.ghost_for(bx, by, tx, ty)
            if not S.in_field(gx, gy, 1.0):
                continue
            dx, dy = gx - cue[0], gy - cue[1]
            d1 = math.hypot(dx, dy)
            if d1 < 1:
                continue
            cut = math.acos(max(-1.0, min(1.0, (dx * ux + dy * uy) / d1)))
            if cut > math.radians(80) or (p in C.SIDE_POCKETS and abs(uy) < 0.5):
                continue
            v = S.pot_chance(d1, d2, cut, p, uy) * C.ball_points(b)
            if v <= best:
                continue
            if S.seg_clear(cue, (gx, gy), table, ignore=(0, b)) and S.seg_clear((bx, by), (tx, ty), table, ignore=(0, b)):
                best = v
    return best


def evaluate(state, me):
    """Score a state from `me`'s point of view (bounded to [VMIN, VMAX])."""
    opp = 1 - me
    diff = state.scores[me] - state.scores[opp]
    if state.over:
        w = 0 if diff == 0 else (1 if diff > 0 else -1)
        return max(VMIN, min(VMAX, diff + 4.0 * w))
    q = pot_quality(state.table) if state.table.alive[0] else 0.8
    if state.ball_in_hand:
        q = max(q, 0.85)
    turn_term = 0.9 * q if state.turn == me else -0.9 * q
    time_term = 0.025 * (state.clocks[me] - state.clocks[opp])
    return max(VMIN, min(VMAX, diff + turn_term + time_term))


def place_best(state, stats=None):
    """Ball in hand: BFS from each ideal spot to the nearest legal one, keep the best."""
    best, best_q = None, -1.0
    for spot in S.ideal_spots(state.table, 4):
        pos = S.bfs_place(state.table, spot, stats=stats)
        state.table.pos[0] = pos
        state.table.alive[0] = True
        q = pot_quality(state.table)
        if q > best_q:
            best, best_q = pos, q
    state.place_cue(*best)
    return best


def heuristic_order(shots):
    return sorted(shots, key=lambda s: -(s.value + (0.02 if s.kind == "direct" else 0.0) - (0.05 if s.kind == "safety" else 0.0)))


def candidates(state, wide=True, stats=None, rng=None):
    """Candidate shots for the player to move, best heuristic first."""
    t = state.table
    if state.is_break:
        return S.break_shots(t, rng or np.random.default_rng())
    if wide:
        shots = S.all_candidates(t, with_banks=True, with_combos=True, stats=stats)
    else:
        shots = S.direct_shots(t)
        if not shots:
            shots = S.safety_shots(t) or S.kick_shots(t)[0]
    if not shots:
        ang = math.atan2(C.FIELD_H / 2 - t.pos[0, 1], C.FIELD_W / 2 - t.pos[0, 0])
        shots = [S.Shot("safety", ang, 600.0, label="desperation")]
    if stats is not None:
        kinds = {}
        for s in shots:
            kinds[s.kind] = kinds.get(s.kind, 0) + 1
        stats["kinds"] = kinds
    return heuristic_order(shots)


def apply_plan_bonus(shots, plan):
    """A*'s first planned pot gets tried first: good position play."""
    if not plan:
        return shots
    b, p = plan[0]
    for s in shots:
        if s.kind == "direct" and s.ball == b and s.pocket == p:
            s.value += 0.25
    return heuristic_order(shots)


def dedupe(shots, limit):
    seen, out = set(), []
    for s in shots:
        k = (s.kind, s.ball, s.pocket, round(s.speed / 120))
        if k in seen:
            continue
        seen.add(k)
        out.append(s)
        if len(out) >= limit:
            break
    return out


class Clock:
    def __init__(self, budget):
        self.t0 = time.perf_counter()
        self.deadline = self.t0 + budget

    def left(self):
        return self.deadline - time.perf_counter()

    def check(self):
        if time.perf_counter() > self.deadline:
            raise TimeUp()

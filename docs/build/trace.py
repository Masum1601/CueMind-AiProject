"""Trace one fixed scenario through every algorithm and save the numbers as JSON + a table image."""
import heapq
import itertools
import json
import math
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
GAME = r"F:\E\Downloads\Need2livewebsite\cuemind"
MEDIA = os.path.join(GAME, "docs", "media")
os.makedirs(MEDIA, exist_ok=True)
sys.path.insert(0, GAME)

import numpy as np  # noqa: E402

from game import config as C  # noqa: E402
from game import shots as S  # noqa: E402
from game import planner as P  # noqa: E402
from game.physics import simulate_shot  # noqa: E402
from game.rules import Match  # noqa: E402
from game.agents.common import (candidates, dedupe, evaluate, play, apply_plan_bonus,  # noqa: E402
                                pot_quality, VMIN, VMAX)
from game.agents.mcts import MCTSAgent, Node  # noqa: E402
from game.agents.common import Clock  # noqa: E402

OUT = {}

# ------------------------------------------------------------------ scenario
m = Match.new(("Minimax", "MCTS"), breaker=0, seed=11)
t = m.table
apex = math.atan2(t.pos[1, 1] - t.pos[0, 1], t.pos[1, 0] - t.pos[0, 0])
after, _, _ = simulate_shot(t, apex + math.radians(0.25), 1820.0)
m.apply_result(after)
m.turn = 0                       # Minimax to move in this scenario
m.ball_in_hand = False
m.is_break = False
if not m.table.alive[0]:
    m.place_cue(*C.HEAD_SPOT)
state = m.snapshot()
tab = state.table
OUT["scenario"] = {
    "balls": {int(b): [round(float(tab.pos[b, 0]), 1), round(float(tab.pos[b, 1]), 1)]
              for b in range(16) if tab.alive[b]},
    "scores": list(state.scores), "clocks": list(state.clocks), "turn": state.turn,
    "potted_on_break": [b for b in range(1, 16) if not tab.alive[b]],
}
np.save(os.path.join(MEDIA, "scenario_pos.npy"), np.c_[tab.pos, tab.alive])

# ------------------------------------------------------------------ candidate shots + heuristic
stats = {}
allc = candidates(state, wide=True, stats=stats)
OUT["kinds"] = stats.get("kinds", {})
rows = []
seen = set()
cue = (tab.pos[0, 0], tab.pos[0, 1])
SIG = math.radians(C.NOISE_ANGLE_DEG)
for s in S.direct_shots(tab):
    if (s.ball, s.pocket) in seen:
        continue
    seen.add((s.ball, s.pocket))
    bx, by = tab.pos[s.ball]
    tx, ty = S.pocket_aim(s.pocket)
    (gx, gy), (ux, uy), d2 = S.ghost_for(bx, by, tx, ty)
    d1 = math.hypot(gx - cue[0], gy - cue[1])
    d2e = max(d2 - C.POCKETS[s.pocket][2] * 0.6, 1.0)
    cut = math.radians(s.cut)
    w = C.POCKETS[s.pocket][2] * 0.62 * (max(abs(uy), 0.15) if s.pocket in C.SIDE_POCKETS else 1)
    alpha = math.atan2(w, d2e)
    sigma = d1 * SIG / (2 * C.BALL_R * max(math.cos(cut), 0.08))
    rows.append({"ball": s.ball, "pocket": C.POCKET_NAMES[s.pocket], "d1": round(d1, 1), "d2": round(d2e, 1),
                 "cut": round(s.cut, 1), "alpha_deg": round(math.degrees(alpha), 2),
                 "sigma_deg": round(math.degrees(sigma), 3), "p": round(s.est, 3),
                 "points": C.ball_points(s.ball), "value": round(s.value, 3), "speed": round(s.speed),
                 "ghost": [round(gx, 1), round(gy, 1)]})
rows.sort(key=lambda r: -r["value"])
OUT["heuristic"] = rows[:8]

# ------------------------------------------------------------------ A* with a log
def astar_trace(table, max_balls=5, max_exp=2500):
    balls = [b for b in range(1, 16) if table.alive[b]]
    cue0 = (float(table.pos[0, 0]), float(table.pos[0, 1]))
    balls.sort(key=lambda b: math.dist(cue0, table.pos[b]))
    target = frozenset(balls[:max_balls])
    cnt = itertools.count()
    fr = [(len(target) * P.TIME_COST, next(cnt), 0.0, (cue0, target), [])]
    best_g, log, exp = {}, [], 0
    while fr and exp < max_exp:
        f, _, g, (c, rem), path = heapq.heappop(fr)
        if not rem:
            return path, g, log, exp, sorted(target)
        key = (round(c[0] / 6), round(c[1] / 6), rem)
        if best_g.get(key, 1e9) <= g:
            continue
        best_g[key] = g
        exp += 1
        kids = list(P._moves(table, c, rem))
        if len(log) < 12:
            log.append({"step": exp, "path": [f"{b}->{C.POCKET_NAMES[p]}" for b, p in path],
                        "g": round(g, 3), "h": round(len(rem) * P.TIME_COST, 3), "f": round(f, 3),
                        "children": len(kids)})
        for b, p, ghost, cost in kids:
            nrem = rem - {b}
            ng = g + cost
            heapq.heappush(fr, (ng + len(nrem) * P.TIME_COST, next(cnt), ng, (ghost, nrem), path + [(b, p)]))
    return [], 0, log, exp, sorted(target)


plan, cost, alog, aexp, atarget = astar_trace(tab)
OUT["astar"] = {"plan": [[b, C.POCKET_NAMES[p]] for b, p in plan], "cost": round(cost, 3), "expansions": aexp,
                "targets": atarget, "log": alog, "time_cost": P.TIME_COST}

# ------------------------------------------------------------------ Minimax with a full tree log
rng = np.random.default_rng(7)
ROOT_W, INNER_W, SR, SI = 4, 3, 2, 1
me = state.turn
nodes = []


def add(parent, kind, label, **kw):
    nodes.append({"id": len(nodes), "parent": parent, "kind": kind, "label": label, **kw})
    return len(nodes) - 1


counter = {"sims": 0, "pruned": 0}


def chance(st, shot, depth, alpha, beta, n, parent):
    cid = add(parent, "CHANCE", shot.label, alpha=alpha, beta=beta)
    total = 0.0
    for k in range(n):
        child = play(st, shot.angle, shot.speed, rng, counter)
        rest = n - k - 1
        lo = (n * alpha - total - rest * VMAX) if alpha > -math.inf else -math.inf
        hi = (n * beta - total - rest * VMIN) if beta < math.inf else math.inf
        out = "pot " + ",".join(map(str, [b for b in range(1, 16) if st.table.alive[b] and not child.table.alive[b]])) \
            if any(st.table.alive[b] and not child.table.alive[b] for b in range(1, 16)) else "no pot"
        sid = add(cid, "SAMPLE", f"sample {k + 1}: {out}", score=[child.scores[0], child.scores[1]],
                  turn=child.turn)
        v = value(child, depth - 1, max(lo, VMIN - 1), min(hi, VMAX + 1), sid)
        nodes[sid]["value"] = round(v, 3)
        total += v
        if alpha > -math.inf and (total + rest * VMAX) / n <= alpha:
            counter["pruned"] += rest
            nodes[cid]["value"] = round((total + rest * VMAX) / n, 3)
            nodes[cid]["cut"] = f"Star1 cut: {rest} sample(s) skipped"
            return nodes[cid]["value"]
    nodes[cid]["value"] = round(total / n, 3)
    return total / n


def value(st, depth, alpha, beta, parent):
    if depth == 0 or st.over:
        v = evaluate(st, me)
        add(parent, "LEAF", "eval", value=round(v, 3), q=round(pot_quality(st.table), 3))
        return v
    shots = dedupe(candidates(st, wide=False), INNER_W)
    maxi = st.turn == me
    nid = add(parent, "MAX" if maxi else "MIN", "MAX (Minimax)" if maxi else "MIN (opponent)")
    v = -math.inf if maxi else math.inf
    for i, s in enumerate(shots):
        cv = chance(st, s, depth, alpha, beta, SI, nid)
        if maxi:
            v = max(v, cv)
            alpha = max(alpha, v)
        else:
            v = min(v, cv)
            beta = min(beta, v)
        if alpha >= beta:
            counter["pruned"] += len(shots) - i - 1
            nodes[nid]["cut"] = f"alpha-beta cut: {len(shots) - i - 1} shot(s) skipped"
            break
    nodes[nid]["value"] = round(v, 3)
    return v


root_shots = dedupe(candidates(state, wide=True, rng=rng), ROOT_W)
iddfs = []
for depth in (1, 2):
    nodes.clear()
    counter.update(sims=0, pruned=0)
    rid = add(None, "ROOT", "Minimax to move (MAX)")
    alpha, best = -math.inf, None
    vals = []
    for s in root_shots:
        v = chance(state, s, depth, alpha, math.inf, SR, rid)
        vals.append((s.label, round(v, 3)))
        if v > alpha:
            alpha, best = v, s
    nodes[rid]["value"] = round(alpha, 3)
    iddfs.append({"depth": depth, "values": vals, "best": best.label, "sims": counter["sims"],
                  "pruned": counter["pruned"], "nodes": len(nodes)})
    root_shots.sort(key=lambda s: -dict(vals)[s.label])
OUT["minimax"] = {"iddfs": iddfs, "tree": list(nodes), "settings": {"root_width": ROOT_W, "inner_width": INNER_W,
                                                                     "samples_root": SR, "samples_inner": SI}}

# ------------------------------------------------------------------ MCTS with an iteration log
ag = MCTSAgent(seed=3)
mstate = state.snapshot()
mshots = dedupe(apply_plan_bonus(candidates(mstate, wide=True, rng=ag.rng), plan), 8)
root = Node(None, None, 1 - me)
st = {"iterations": 0, "sims": 0, "depth": 0}
clock = Clock(1e9)
it_log = []
ITER = 160
hist = []
for i in range(ITER):
    before = {a: (ch.N, ch.W) for a, ch in root.children.items()}
    ag._iterate(root, mstate, mshots, me, st, clock)
    chosen = None
    for a, ch in root.children.items():
        if before.get(a, (0, 0))[0] != ch.N:
            chosen = a
            r = ch.W - before.get(a, (0, 0))[1]
    if i < 12:
        it_log.append({"iter": i + 1, "root_action": mshots[chosen].label, "reward": round(r, 3),
                       "N": root.children[chosen].N, "Q": round(root.children[chosen].W / root.children[chosen].N, 3)})
    hist.append([root.children[a].N if a in root.children else 0 for a in range(len(mshots))])
lnN = math.log(root.N)
children = []
for a, ch in sorted(root.children.items(), key=lambda kv: -kv[1].N):
    q = ch.W / ch.N
    explore = ag.c * math.sqrt(lnN / ch.N)
    grand = sorted(((b, g.N, round(g.W / g.N, 3)) for b, g in ch.children.items()), key=lambda r: -r[1])[:3]
    children.append({"action": mshots[a].label, "N": ch.N, "W": round(ch.W, 2), "Q": round(q, 3),
                     "explore": round(explore, 3), "ucb1": round(q + explore, 3), "grand": grand})
OUT["mcts"] = {"iterations": ITER, "root_N": root.N, "C": ag.c, "children": children, "log": it_log,
               "history": hist, "labels": [s.label for s in mshots], "sims": st["sims"], "depth": st["depth"]}

with open(os.path.join(MEDIA, "trace.json"), "w") as f:
    json.dump(OUT, f, indent=1, default=float)
print("kinds", OUT["kinds"])
print("top heuristic", [(r["ball"], r["pocket"], r["p"], r["value"]) for r in rows[:4]])
print("A*", OUT["astar"]["plan"], OUT["astar"]["cost"], "exp", aexp)
print("minimax", iddfs)
print("mcts", [(c["action"], c["N"], c["Q"], c["ucb1"]) for c in children])

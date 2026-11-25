"""A* run-out planner.

Question: in which order should I pot the balls so the whole run is easiest?

State   = (where the cue ball is, which balls are still on the table)
Action  = pot ball b into pocket p from here
Cost    = -log(chance the pot works) + TIME_COST     (difficulty + clock time)
Next    = the cue ball is assumed to stop near the ghost spot (a "stun" shot)
h(n)    = remaining balls x TIME_COST

Every pot costs at least TIME_COST, so h never overestimates: it is admissible
and A* returns the cheapest order it can find. To stay fast we plan only the
next few balls and cap the number of expansions.
"""
import heapq
import itertools
import math

from . import config as C
from .shots import ghost_for, pocket_aim, pot_chance, seg_clear, in_field

TIME_COST = 0.15


class _View:
    """A light table view where planned balls are already gone."""

    def __init__(self, table, gone):
        self.pos = table.pos
        self.alive = table.alive.copy()
        for b in gone:
            self.alive[b] = False


def _moves(table, cue, remaining):
    view = _View(table, [b for b in range(1, 16) if table.alive[b] and b not in remaining])
    view.pos = table.pos.copy()
    view.pos[0] = cue
    for b in remaining:
        bx, by = table.pos[b]
        for p in range(6):
            tx, ty = pocket_aim(p)
            (gx, gy), (ux, uy), d2 = ghost_for(bx, by, tx, ty)
            if not in_field(gx, gy, 1.0):
                continue
            dx, dy = gx - cue[0], gy - cue[1]
            d1 = math.hypot(dx, dy)
            if d1 < 1:
                continue
            cosc = (dx * ux + dy * uy) / d1
            cut = math.acos(max(-1.0, min(1.0, cosc)))
            if cut > math.radians(78) or (p in C.SIDE_POCKETS and abs(uy) < 0.5):
                continue
            if not seg_clear(cue, (gx, gy), view, ignore=(0, b)):
                continue
            if not seg_clear((bx, by), (tx, ty), view, ignore=(0, b)):
                continue
            pr = pot_chance(d1, d2, cut, p, uy)
            if pr < 0.05:
                continue
            yield b, p, (gx, gy), -math.log(pr) + TIME_COST


def plan_runout(table, max_balls=5, max_expansions=2500, stats=None):
    """Returns ([(ball, pocket), ...], total cost) for the next few pots."""
    balls = [b for b in range(1, 16) if table.alive[b]]
    if not balls or not table.alive[0]:
        return [], 0.0
    cue0 = (float(table.pos[0, 0]), float(table.pos[0, 1]))
    # plan for the balls nearest the cue ball when the table is crowded
    balls.sort(key=lambda b: math.dist(cue0, table.pos[b]))
    target = frozenset(balls[:max_balls])
    counter = itertools.count()
    start = (cue0, target)
    frontier = [(len(target) * TIME_COST, next(counter), 0.0, start, [])]
    best_g = {}
    expansions = 0
    best_partial = ([], 0.0, -1)
    while frontier and expansions < max_expansions:
        f, _, g, (cue, rem), path = heapq.heappop(frontier)
        if not rem:
            if stats is not None:
                stats["astar_expansions"] = expansions
            return path, g
        key = (round(cue[0] / 6), round(cue[1] / 6), rem)
        if best_g.get(key, 1e9) <= g:
            continue
        best_g[key] = g
        expansions += 1
        if len(path) > best_partial[2] or (len(path) == best_partial[2] and g < best_partial[1]):
            best_partial = (path, g, len(path))
        for b, p, ghost, cost in _moves(table, cue, rem):
            nrem = rem - {b}
            ng = g + cost
            h = len(nrem) * TIME_COST
            heapq.heappush(frontier, (ng + h, next(counter), ng, (ghost, nrem), path + [(b, p)]))
    if stats is not None:
        stats["astar_expansions"] = expansions
    return best_partial[0], best_partial[1]

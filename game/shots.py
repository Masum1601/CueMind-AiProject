"""Finding candidate shots.

Pool shots are continuous (any angle, any power), so before any search we turn
the table into a short list of sensible shots:

* direct pots     - ghost-ball aiming at every (ball, pocket) pair
* bank shots      - the object ball bounces off cushions first (DLS, mirror method)
* kick shots      - the cue ball bounces off cushions to reach a ball when every
                    direct line is blocked (IDDFS: 0, then 1, then 2 cushions)
* combinations    - cue -> ball A -> ball B -> pocket (bidirectional search)
* safeties        - soft, legal contact when nothing pots
* ball-in-hand    - where to put the cue ball after a foul (BFS on a grid)
"""
import math
from dataclasses import dataclass, field

import numpy as np

from . import config as C
from .physics import njit, speed_needed

R = C.BALL_R
W, H = C.FIELD_W, C.FIELD_H
SIGMA_ANGLE = math.radians(C.NOISE_ANGLE_DEG)


@dataclass
class Shot:
    kind: str                 # direct, bank, combo, kick, safety, break
    angle: float
    speed: float
    ball: int = -1            # ball we try to pot (or hit)
    pocket: int = -1
    est: float = 0.0          # estimated chance the pot works (0..1)
    value: float = 0.0        # expected points from the pot alone
    cut: float = 0.0          # cut angle in degrees
    path: list = field(default_factory=list)   # points for drawing
    label: str = ""
    score: float = 0.0        # filled in by agents
    extra: dict = field(default_factory=dict)

    def key(self):
        return (self.kind, self.ball, self.pocket, round(self.angle, 4), round(self.speed))


# --------------------------------------------------------------- geometry kernels

@njit(cache=True)
def _seg_clear(ax, ay, bx, by, pos, alive, ign1, ign2, clr):
    """True when no ball (except ign1/ign2) sits within clr of segment A-B."""
    ex = bx - ax
    ey = by - ay
    L2 = ex * ex + ey * ey
    if L2 < 1e-9:
        return True
    for k in range(pos.shape[0]):
        if not alive[k] or k == ign1 or k == ign2:
            continue
        t = ((pos[k, 0] - ax) * ex + (pos[k, 1] - ay) * ey) / L2
        if t < 0.0:
            t = 0.0
        elif t > 1.0:
            t = 1.0
        dx = pos[k, 0] - (ax + ex * t)
        dy = pos[k, 1] - (ay + ey * t)
        if dx * dx + dy * dy < clr * clr:
            return False
    return True


def seg_clear(a, b, table, ignore=(), clr=2 * R - 0.6):
    i1 = ignore[0] if len(ignore) > 0 else -1
    i2 = ignore[1] if len(ignore) > 1 else -1
    return _seg_clear(a[0], a[1], b[0], b[1], table.pos, table.alive, i1, i2, clr)


def pocket_aim(p):
    x, y, _ = C.POCKETS[p]
    return (x, y)


def in_field(x, y, m=0.0):
    return R - m <= x <= W - R + m and R - m <= y <= H - R + m


def _unit(dx, dy):
    d = math.hypot(dx, dy)
    return (dx / d, dy / d, d) if d > 1e-9 else (0.0, 0.0, 0.0)


def pot_chance(d1, d2, cut_rad, pocket, approach=None):
    """Chance a pot works, from geometry and the shared execution noise.

    An aiming error of dθ moves the contact point sideways by d1·dθ, which turns
    the object ball by about d1·dθ / (2r·cos cut). The pot works while that turn
    stays inside the pocket's angular window atan(w / d2).
    """
    cosc = max(math.cos(cut_rad), 0.08)
    w = C.POCKETS[pocket][2] * 0.62
    if pocket in C.SIDE_POCKETS and approach is not None:
        w *= max(abs(approach), 0.15)       # side pockets shrink when hit at an angle
    alpha = math.atan2(w, max(d2, 1.0))
    sigma = max(d1, 1.0) * SIGMA_ANGLE / (2 * R * cosc) + 1e-6
    p = math.erf(alpha / (sigma * math.sqrt(2)))
    p *= 1.0 - 0.25 * (cut_rad / math.radians(85)) ** 4     # thin cuts are touchy
    return max(0.0, min(0.995, p))


def ghost_for(bx, by, tx, ty):
    """Ghost ball: where the cue ball must be to send (bx, by) towards (tx, ty).

        Ghost = B - 2r * (T - B) / |T - B|
    """
    ux, uy, d = _unit(tx - bx, ty - by)
    return (bx - 2 * R * ux, by - 2 * R * uy), (ux, uy), d


def _speeds_for_pot(d1, d2, cut, extra_loss=1.0):
    v_obj = speed_needed(max(d2, 1.0), C.POCKET_MIN_SPEED + 45.0) * extra_loss
    transfer = max(math.cos(cut), 0.12) * 0.5 * (1 + C.BALL_E)
    v_contact = v_obj / transfer
    return speed_needed(max(d1, 1.0), v_contact)


# --------------------------------------------------------------- direct pots

def direct_shots(table, cue_pos=None, balls=None, max_cut=80.0):
    cue = cue_pos if cue_pos is not None else (table.pos[0, 0], table.pos[0, 1])
    out = []
    balls = balls if balls is not None else [b for b in range(1, 16) if table.alive[b]]
    for b in balls:
        bx, by = table.pos[b]
        for p in range(6):
            tx, ty = pocket_aim(p)
            (gx, gy), (ux, uy), d2 = ghost_for(bx, by, tx, ty)
            if not in_field(gx, gy, 1.0):
                continue
            wx, wy, d1 = _unit(gx - cue[0], gy - cue[1])
            if d1 < 1e-6:
                continue
            cosc = wx * ux + wy * uy
            cut = math.acos(max(-1.0, min(1.0, cosc)))
            if math.degrees(cut) > max_cut:
                continue
            if p in C.SIDE_POCKETS and abs(uy) < 0.5:
                continue        # too flat for a side pocket: the jaws would reject it
            if not seg_clear(cue, (gx, gy), table, ignore=(0, b)):
                continue
            if not seg_clear((bx, by), (tx, ty), table, ignore=(0, b)):
                continue
            d2e = max(d2 - C.POCKETS[p][2] * 0.6, 1.0)
            v0 = _speeds_for_pot(d1, d2e, cut)
            if v0 > C.MAX_SPEED:
                continue
            est = pot_chance(d1, d2e, cut, p, uy)
            ang = math.atan2(wy, wx)
            for f, word in ((1.0, "soft"), (1.3, "medium"), (1.75, "firm")):
                v = v0 * f
                if v > C.MAX_SPEED:
                    break
                out.append(Shot("direct", ang, v, b, p, est, est * C.ball_points(b),
                                math.degrees(cut), [cue, (gx, gy), (bx, by), (tx, ty)],
                                f"{b} into {C.POCKET_NAMES[p]}, {word}"))
    return out


# --------------------------------------------------------------- cushions (mirror method)

CUSHIONS = [("top", R), ("bottom", H - R), ("left", R), ("right", W - R)]


def _reflect(pt, c):
    """Mirror a point through cushion c, scaled for the cushion's energy loss."""
    name, v = CUSHIONS[c]
    e = C.CUSHION_E
    if name in ("top", "bottom"):
        return (pt[0], v - (pt[1] - v) / e)
    return (v - (pt[0] - v) / e, pt[1])


def _hit_line(a, b, c):
    """Where the segment a->b crosses cushion line c (None if it does not)."""
    name, v = CUSHIONS[c]
    if name in ("top", "bottom"):
        if abs(b[1] - a[1]) < 1e-9:
            return None
        t = (v - a[1]) / (b[1] - a[1])
        x = a[0] + (b[0] - a[0]) * t
        ok = 0 < t < 1 and C.CORNER_MOUTH + 4 < x < W - C.CORNER_MOUTH - 4 and abs(x - W / 2) > C.SIDE_MOUTH + 6
        return (x, v) if ok else None
    if abs(b[0] - a[0]) < 1e-9:
        return None
    t = (v - a[0]) / (b[0] - a[0])
    y = a[1] + (b[1] - a[1]) * t
    ok = 0 < t < 1 and C.CORNER_MOUTH + 4 < y < H - C.CORNER_MOUTH - 4
    return (v, y) if ok else None


def _unfold(start, target, seq):
    """Turn a cushion sequence into the real path start -> c1 -> ... -> target."""
    images = [target]
    for c in reversed(seq):
        images.append(_reflect(images[-1], c))
    images.reverse()            # images[0] is target mirrored through every cushion
    pts = [start]
    cur = start
    for k, c in enumerate(seq):
        aim = images[k]
        hit = _hit_line(cur, aim, c)
        if hit is None:
            return None
        pts.append(hit)
        cur = hit
    pts.append(target)
    return pts


def cushion_paths(start, target, table, ignore, depth, clr=2 * R - 0.6, stats=None):
    """Depth-limited DFS over cushion sequences of exactly `depth` bounces."""
    found = []

    def dfs(seq):
        if stats is not None:
            stats["nodes"] = stats.get("nodes", 0) + 1
        if len(seq) == depth:
            pts = _unfold(start, target, seq)
            if pts is None:
                return
            for a, b in zip(pts, pts[1:]):
                if not seg_clear(a, b, table, ignore=ignore, clr=clr):
                    return
            found.append((list(seq), pts))
            return
        for c in range(4):
            if seq and seq[-1] == c:
                continue
            seq.append(c)
            dfs(seq)
            seq.pop()

    dfs([])
    return found


def bank_shots(table, depth_limit=2):
    """Object-ball banks: ball -> cushion(s) -> pocket, using depth-limited search."""
    cue = (table.pos[0, 0], table.pos[0, 1])
    out = []
    for b in range(1, 16):
        if not table.alive[b]:
            continue
        B = (table.pos[b, 0], table.pos[b, 1])
        for p in range(6):
            T = pocket_aim(p)
            for depth in range(1, depth_limit + 1):
                for seq, pts in cushion_paths(B, T, table, (0, b), depth):
                    first = pts[1]
                    (gx, gy), (ux, uy), _ = ghost_for(B[0], B[1], first[0], first[1])
                    if not in_field(gx, gy, 1.0):
                        continue
                    wx, wy, d1 = _unit(gx - cue[0], gy - cue[1])
                    cut = math.acos(max(-1.0, min(1.0, wx * ux + wy * uy)))
                    if math.degrees(cut) > 60 or not seg_clear(cue, (gx, gy), table, ignore=(0, b)):
                        continue
                    d2 = sum(math.dist(a, c) for a, c in zip(pts, pts[1:]))
                    v0 = _speeds_for_pot(d1, d2, cut, extra_loss=(1 / C.CUSHION_E) ** (0.6 * depth))
                    if v0 > C.MAX_SPEED:
                        continue
                    est = pot_chance(d1 + d2 * 0.6, d2, cut, p) * (0.55 ** depth)
                    out.append(Shot("bank", math.atan2(wy, wx), v0 * 1.15, b, p, est,
                                    est * C.ball_points(b), math.degrees(cut), [cue, (gx, gy)] + pts[1:],
                                    f"{b} bank x{depth} into {C.POCKET_NAMES[p]}"))
    return out


def kick_shots(table, max_depth=3, stats=None):
    """Cue-ball kicks with IDDFS: try 0 cushions, then 1, 2, 3; stop at the first depth that works."""
    cue = (table.pos[0, 0], table.pos[0, 1])
    for depth in range(0, max_depth + 1):
        out = []
        for b in range(1, 16):
            if not table.alive[b]:
                continue
            B = (table.pos[b, 0], table.pos[b, 1])
            if depth == 0:
                if seg_clear(cue, B, table, ignore=(0, b), clr=2 * R - 0.6):
                    out.append((b, [cue, B]))
                continue
            for seq, pts in cushion_paths(cue, B, table, (0, b), depth, stats=stats):
                out.append((b, pts))
        if out:
            shots = []
            for b, pts in out:
                L = sum(math.dist(a, c) for a, c in zip(pts, pts[1:]))
                ang = math.atan2(pts[1][1] - cue[1], pts[1][0] - cue[0])
                v = min(speed_needed(L, 260.0) * (1 / C.CUSHION_E) ** (0.5 * depth), C.MAX_SPEED)
                shots.append(Shot("kick" if depth else "safety", ang, v, b, -1, 0.0, 0.0, 0.0,
                                  pts, f"kick x{depth} onto {b}" if depth else f"safe touch on {b}",
                                  extra={"depth": depth}))
            return shots, depth
    return [], -1


# --------------------------------------------------------------- combinations (bidirectional)

def combo_shots(table, stats=None):
    """Bidirectional search for cue -> A -> B -> pocket.

    Forward frontier:  balls the cue ball can reach in a straight line.
    Backward frontier: for each pocket, balls B that can drop (clear line), then
                       the ghost spot behind B that another ball must reach.
    Where a forward ball A can reach a backward ghost spot, the two searches meet.
    """
    cue = (table.pos[0, 0], table.pos[0, 1])
    alive = [b for b in range(1, 16) if table.alive[b]]
    forward = [a for a in alive if seg_clear(cue, tuple(table.pos[a]), table, ignore=(0, a))]
    backward = []
    for b in alive:
        B = tuple(table.pos[b])
        for p in range(6):
            T = pocket_aim(p)
            if p in C.SIDE_POCKETS and abs(_unit(T[0] - B[0], T[1] - B[1])[1]) < 0.55:
                continue
            if seg_clear(B, T, table, ignore=(0, b)):
                g, _, d2 = ghost_for(B[0], B[1], T[0], T[1])
                if in_field(g[0], g[1], 1.0):
                    backward.append((b, p, g, d2))
    if stats is not None:
        stats["forward"] = len(forward)
        stats["backward"] = len(backward)
    out = []
    for a in forward:
        A = tuple(table.pos[a])
        for b, p, gB, d2 in backward:
            if b == a:
                continue
            (gx, gy), (ux, uy), d_ab = ghost_for(A[0], A[1], gB[0], gB[1])
            if d_ab > 420 or not in_field(gx, gy, 1.0):
                continue
            if not seg_clear(A, gB, table, ignore=(0, a)):
                continue
            if not seg_clear(cue, (gx, gy), table, ignore=(0, a)):
                continue
            wx, wy, d1 = _unit(gx - cue[0], gy - cue[1])
            cut1 = math.acos(max(-1.0, min(1.0, wx * ux + wy * uy)))
            bux, buy, _ = _unit(pocket_aim(p)[0] - table.pos[b, 0], pocket_aim(p)[1] - table.pos[b, 1])
            cut2 = math.acos(max(-1.0, min(1.0, ux * bux + uy * buy)))
            if math.degrees(cut1) > 45 or math.degrees(cut2) > 40:
                continue
            v_b = speed_needed(d2, C.POCKET_MIN_SPEED + 45)
            v_a = speed_needed(d_ab, v_b / (math.cos(cut2) * 0.5 * (1 + C.BALL_E)))
            v0 = speed_needed(d1, v_a / (math.cos(cut1) * 0.5 * (1 + C.BALL_E)))
            if v0 > C.MAX_SPEED:
                continue
            est = pot_chance(d1 + d_ab, d2, cut1, p) * pot_chance(d_ab, d2, cut2, p) * 0.8
            out.append(Shot("combo", math.atan2(wy, wx), v0 * 1.1, b, p, est, est * C.ball_points(b),
                            math.degrees(cut1), [cue, (gx, gy), A, gB, tuple(table.pos[b]), pocket_aim(p)],
                            f"combo {a}->{b} into {C.POCKET_NAMES[p]}", extra={"via": a}))
    return out


# --------------------------------------------------------------- safeties and the break

def safety_shots(table):
    cue = (table.pos[0, 0], table.pos[0, 1])
    out = []
    for b in range(1, 16):
        if not table.alive[b]:
            continue
        B = tuple(table.pos[b])
        if not seg_clear(cue, B, table, ignore=(0, b)):
            continue
        ang = math.atan2(B[1] - cue[1], B[0] - cue[0])
        d = math.dist(cue, B)
        for v_end in (180.0, 330.0):
            v = min(speed_needed(d, v_end), C.MAX_SPEED)
            out.append(Shot("safety", ang, v, b, -1, 0.0, 0.0, 0.0, [cue, B], f"safety on {b}"))
    return out


def break_shots(table, rng):
    cue = (table.pos[0, 0], table.pos[0, 1])
    apex = tuple(table.pos[1])
    base = math.atan2(apex[1] - cue[1], apex[0] - cue[0])
    out = []
    for k in range(5):
        off = math.radians(rng.uniform(-0.6, 0.6))
        out.append(Shot("break", base + off, C.MAX_SPEED * rng.uniform(0.93, 1.0), 1, -1, 0, 0, 0,
                        [cue, apex], "break"))
    return out


def all_candidates(table, with_banks=True, with_combos=True, stats=None):
    shots = direct_shots(table)
    if with_combos:
        shots += combo_shots(table, stats)
    if with_banks:
        shots += bank_shots(table)
    shots += safety_shots(table)
    if not any(s.kind != "safety" for s in shots):
        kicks, depth = kick_shots(table, stats=stats)
        if stats is not None:
            stats["kick_depth"] = depth
        shots += kicks
    return shots


# --------------------------------------------------------------- ball in hand (BFS)

def legal_cue_spot(table, x, y):
    if not in_field(x, y, -1.0):
        return False
    for k in range(1, 16):
        if table.alive[k] and (table.pos[k, 0] - x) ** 2 + (table.pos[k, 1] - y) ** 2 < (2 * R + 1.5) ** 2:
            return False
    for px, py, pr in C.POCKETS:
        if (px - x) ** 2 + (py - y) ** 2 < (pr + R + 14) ** 2:
            return False
    return True


def bfs_place(table, ideal, step=8.0, max_nodes=6000, stats=None):
    """Breadth-first search outwards from the ideal spot to the nearest legal one."""
    from collections import deque
    gx0, gy0 = int(round(ideal[0] / step)), int(round(ideal[1] / step))
    seen = {(gx0, gy0)}
    q = deque([(gx0, gy0)])
    n = 0
    while q and n < max_nodes:
        gx, gy = q.popleft()
        n += 1
        x, y = gx * step, gy * step
        if legal_cue_spot(table, x, y):
            if stats is not None:
                stats["bfs_nodes"] = n
            return (x, y)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            nb = (gx + dx, gy + dy)
            if nb not in seen and -2 <= nb[0] <= W / step + 2 and -2 <= nb[1] <= H / step + 2:
                seen.add(nb)
                q.append(nb)
    if stats is not None:
        stats["bfs_nodes"] = n
    return C.HEAD_SPOT


def ideal_spots(table, count=4):
    """Straight-in spots behind the easiest pots, used as BFS starting points."""
    spots = []
    for b in range(1, 16):
        if not table.alive[b]:
            continue
        bx, by = table.pos[b]
        for p in range(6):
            tx, ty = pocket_aim(p)
            (gx, gy), (ux, uy), d2 = ghost_for(bx, by, tx, ty)
            if p in C.SIDE_POCKETS and abs(uy) < 0.55:
                continue
            if not seg_clear((bx, by), (tx, ty), table, ignore=(0, b)):
                continue
            back = 70.0
            spot = (gx - ux * back, gy - uy * back)
            spots.append((pot_chance(back, d2, 0.0, p, uy) * C.ball_points(b), spot))
    spots.sort(key=lambda s: -s[0])
    return [s for _, s in spots[:count]] or [C.HEAD_SPOT]

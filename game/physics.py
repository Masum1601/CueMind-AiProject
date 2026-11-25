"""The physics engine.

One fixed-step engine serves two jobs: it moves the balls on screen, and it lets
the AI play shots "in its head". Because both use the same step (config.DT),
a shot the AI simulates behaves exactly like the shot on screen (apart from the
random execution noise every player gets).

Each step:
  1. move every ball (x += v * dt) and slow it down (friction),
  2. resolve ball-ball hits (equal masses: swap speed along the line of centres),
  3. bounce balls off cushion segments and pocket jaws,
  4. capture balls that reach a pocket.
The core loops are compiled with numba when it is available.
"""
import math
import numpy as np

from . import config as C

try:
    from numba import njit
    HAVE_NUMBA = True
except Exception:  # pragma: no cover - plain Python fallback
    HAVE_NUMBA = False

    def njit(*args, **kwargs):
        if args and callable(args[0]):
            return args[0]
        return lambda f: f

N_BALLS = 16
MAX_EVENTS = 256
EV_BALL, EV_CUSHION, EV_POCKET = 1, 2, 3


def build_segments():
    """Cushion and jaw segments as an (n, 4) array of x1, y1, x2, y2."""
    W, H, cm, sm = C.FIELD_W, C.FIELD_H, C.CORNER_MOUTH, C.SIDE_MOUTH
    s = []
    # rails
    s += [(cm, 0, W / 2 - sm, 0), (W / 2 + sm, 0, W - cm, 0)]
    s += [(cm, H, W / 2 - sm, H), (W / 2 + sm, H, W - cm, H)]
    s += [(0, cm, 0, H - cm), (W, cm, W, H - cm)]
    # corner jaws (angled into the pocket)
    j = 18.0
    s += [(cm, 0, cm - j, -20), (0, cm, -20, cm - j)]
    s += [(W - cm, 0, W - cm + j, -20), (W, cm, W + 20, cm - j)]
    s += [(cm, H, cm - j, H + 20), (0, H - cm, -20, H - cm + j)]
    s += [(W - cm, H, W - cm + j, H + 20), (W, H - cm, W + 20, H - cm + j)]
    # side jaws
    s += [(W / 2 - sm, 0, W / 2 - sm + 4, -22), (W / 2 + sm, 0, W / 2 + sm - 4, -22)]
    s += [(W / 2 - sm, H, W / 2 - sm + 4, H + 22), (W / 2 + sm, H, W / 2 + sm - 4, H + 22)]
    return np.array(s, dtype=np.float64)


SEGMENTS = build_segments()
POCKET_ARR = np.array(C.POCKETS, dtype=np.float64)


@njit(cache=True, nogil=True)
def _step(pos, vel, alive, pocket_of, first_hit, segs, pockets, dt,
          ev, nev, record, R, fa, fk, be, ce, ct, stop):
    n = pos.shape[0]
    moving = False
    # 1. move + friction
    for i in range(n):
        if not alive[i]:
            continue
        vx = vel[i, 0]
        vy = vel[i, 1]
        sp = math.sqrt(vx * vx + vy * vy)
        if sp <= 0.0:
            continue
        pos[i, 0] += vx * dt
        pos[i, 1] += vy * dt
        nsp = sp - (fa + fk * sp) * dt
        if nsp < stop:
            vel[i, 0] = 0.0
            vel[i, 1] = 0.0
        else:
            f = nsp / sp
            vel[i, 0] = vx * f
            vel[i, 1] = vy * f
            moving = True
    # 2. ball-ball, with back-up to the exact moment of contact
    R2 = 2.0 * R
    for i in range(n):
        if not alive[i]:
            continue
        for j in range(i + 1, n):
            if not alive[j]:
                continue
            dx = pos[j, 0] - pos[i, 0]
            dy = pos[j, 1] - pos[i, 1]
            d2 = dx * dx + dy * dy
            if d2 >= R2 * R2 or d2 < 1e-12:
                continue
            dvx = vel[j, 0] - vel[i, 0]
            dvy = vel[j, 1] - vel[i, 1]
            approach = -(dx * dvx + dy * dvy)
            if approach <= 0.0:
                # touching but separating: just push apart
                d = math.sqrt(d2)
                o = 0.5 * (R2 - d)
                pos[i, 0] -= dx / d * o
                pos[i, 1] -= dy / d * o
                pos[j, 0] += dx / d * o
                pos[j, 1] += dy / d * o
                continue
            a = dvx * dvx + dvy * dvy
            tau = 0.0
            if a > 1e-9:
                b = dx * dvx + dy * dvy
                c = d2 - R2 * R2
                disc = b * b - a * c
                if disc < 0.0:
                    disc = 0.0
                tau = (b + math.sqrt(disc)) / a
                if tau > dt:
                    tau = dt
                if tau < 0.0:
                    tau = 0.0
            # back up to contact
            pos[i, 0] -= vel[i, 0] * tau
            pos[i, 1] -= vel[i, 1] * tau
            pos[j, 0] -= vel[j, 0] * tau
            pos[j, 1] -= vel[j, 1] * tau
            dx = pos[j, 0] - pos[i, 0]
            dy = pos[j, 1] - pos[i, 1]
            d = math.sqrt(dx * dx + dy * dy)
            if d < 1e-9:
                d = 1e-9
            nx = dx / d
            ny = dy / d
            rel = (vel[i, 0] - vel[j, 0]) * nx + (vel[i, 1] - vel[j, 1]) * ny
            if rel > 0.0:
                imp = 0.5 * (1.0 + be) * rel
                vel[i, 0] -= imp * nx
                vel[i, 1] -= imp * ny
                vel[j, 0] += imp * nx
                vel[j, 1] += imp * ny
                if first_hit[0] == -1:
                    if i == 0:
                        first_hit[0] = j
                    elif j == 0:
                        first_hit[0] = i
                if record and nev[0] < ev.shape[0]:
                    k = nev[0]
                    ev[k, 0] = 1.0
                    ev[k, 1] = i
                    ev[k, 2] = j
                    ev[k, 3] = rel
                    ev[k, 4] = pos[i, 0] + nx * R
                    ev[k, 5] = pos[i, 1] + ny * R
                    nev[0] = k + 1
            # move forward again with the new velocities
            pos[i, 0] += vel[i, 0] * tau
            pos[i, 1] += vel[i, 1] * tau
            pos[j, 0] += vel[j, 0] * tau
            pos[j, 1] += vel[j, 1] * tau
            dx = pos[j, 0] - pos[i, 0]
            dy = pos[j, 1] - pos[i, 1]
            d = math.sqrt(dx * dx + dy * dy)
            if d < R2 and d > 1e-9:
                o = 0.5 * (R2 - d)
                pos[i, 0] -= dx / d * o
                pos[i, 1] -= dy / d * o
                pos[j, 0] += dx / d * o
                pos[j, 1] += dy / d * o
            moving = True
    # 3. cushions and jaws
    for i in range(n):
        if not alive[i]:
            continue
        for s in range(segs.shape[0]):
            x1 = segs[s, 0]
            y1 = segs[s, 1]
            x2 = segs[s, 2]
            y2 = segs[s, 3]
            ex = x2 - x1
            ey = y2 - y1
            L2 = ex * ex + ey * ey
            t = ((pos[i, 0] - x1) * ex + (pos[i, 1] - y1) * ey) / L2
            if t < 0.0:
                t = 0.0
            elif t > 1.0:
                t = 1.0
            qx = x1 + ex * t
            qy = y1 + ey * t
            dx = pos[i, 0] - qx
            dy = pos[i, 1] - qy
            d2 = dx * dx + dy * dy
            if d2 >= R * R or d2 < 1e-12:
                continue
            d = math.sqrt(d2)
            nx = dx / d
            ny = dy / d
            vn = vel[i, 0] * nx + vel[i, 1] * ny
            if vn < 0.0:
                tx = vel[i, 0] - vn * nx
                ty = vel[i, 1] - vn * ny
                vel[i, 0] = tx * ct - vn * ce * nx
                vel[i, 1] = ty * ct - vn * ce * ny
                if record and nev[0] < ev.shape[0]:
                    k = nev[0]
                    ev[k, 0] = 2.0
                    ev[k, 1] = i
                    ev[k, 2] = s
                    ev[k, 3] = -vn
                    ev[k, 4] = qx
                    ev[k, 5] = qy
                    nev[0] = k + 1
            pos[i, 0] = qx + nx * R
            pos[i, 1] = qy + ny * R
    # 4. pockets
    for i in range(n):
        if not alive[i]:
            continue
        for p in range(pockets.shape[0]):
            dx = pos[i, 0] - pockets[p, 0]
            dy = pos[i, 1] - pockets[p, 1]
            if dx * dx + dy * dy < pockets[p, 2] * pockets[p, 2]:
                alive[i] = False
                pocket_of[i] = p
                if record and nev[0] < ev.shape[0]:
                    k = nev[0]
                    ev[k, 0] = 3.0
                    ev[k, 1] = i
                    ev[k, 2] = p
                    ev[k, 3] = math.sqrt(vel[i, 0] ** 2 + vel[i, 1] ** 2)
                    ev[k, 4] = pos[i, 0]
                    ev[k, 5] = pos[i, 1]
                    nev[0] = k + 1
                vel[i, 0] = 0.0
                vel[i, 1] = 0.0
                break
        # safety net: a ball that escapes the table drops into the nearest pocket
        if alive[i] and (pos[i, 0] < -40.0 or pos[i, 0] > 1040.0 or pos[i, 1] < -40.0 or pos[i, 1] > 540.0):
            best = 0
            bd = 1e18
            for p in range(pockets.shape[0]):
                dx = pos[i, 0] - pockets[p, 0]
                dy = pos[i, 1] - pockets[p, 1]
                if dx * dx + dy * dy < bd:
                    bd = dx * dx + dy * dy
                    best = p
            alive[i] = False
            pocket_of[i] = best
            vel[i, 0] = 0.0
            vel[i, 1] = 0.0
    return moving


@njit(cache=True, nogil=True)
def _advance(pos, vel, alive, pocket_of, first_hit, segs, pockets, dt, nsteps,
             ev, nev, record, R, fa, fk, be, ce, ct, stop):
    moving = False
    for _ in range(nsteps):
        moving = _step(pos, vel, alive, pocket_of, first_hit, segs, pockets, dt,
                       ev, nev, record, R, fa, fk, be, ce, ct, stop)
        if not moving:
            break
    return moving


@njit(cache=True, nogil=True)
def _simulate(pos, vel, alive, pocket_of, first_hit, segs, pockets, dt, max_steps,
              R, fa, fk, be, ce, ct, stop):
    ev = np.zeros((1, 6))
    nev = np.zeros(1, dtype=np.int64)
    steps = 0
    while steps < max_steps:
        moving = _step(pos, vel, alive, pocket_of, first_hit, segs, pockets, dt,
                       ev, nev, False, R, fa, fk, be, ce, ct, stop)
        steps += 1
        if not moving:
            break
    return steps


# ------------------------------------------------------------------ Python API

class Table:
    """Live ball state. Index 0 is the cue ball, 1..15 the object balls."""

    def __init__(self):
        self.pos = np.zeros((N_BALLS, 2))
        self.vel = np.zeros((N_BALLS, 2))
        self.alive = np.zeros(N_BALLS, dtype=np.bool_)
        self.reset_shot_info()

    def reset_shot_info(self):
        self.pocket_of = np.full(N_BALLS, -1, dtype=np.int64)
        self.first_hit = np.full(1, -1, dtype=np.int64)
        self.ev = np.zeros((MAX_EVENTS, 6))
        self.nev = np.zeros(1, dtype=np.int64)

    def copy(self):
        t = Table.__new__(Table)
        t.pos = self.pos.copy()
        t.vel = self.vel.copy()
        t.alive = self.alive.copy()
        t.reset_shot_info()
        return t

    def moving(self):
        return bool(np.any(np.abs(self.vel[self.alive]) > 0))

    def strike(self, angle, speed):
        self.reset_shot_info()
        self.vel[0, 0] = math.cos(angle) * speed
        self.vel[0, 1] = math.sin(angle) * speed

    def advance(self, nsteps):
        """Run nsteps fixed steps, recording events for sound and effects."""
        self.nev[0] = 0
        return _advance(self.pos, self.vel, self.alive, self.pocket_of, self.first_hit,
                        SEGMENTS, POCKET_ARR, C.DT, nsteps, self.ev, self.nev, True,
                        C.BALL_R, C.FRICTION_A, C.FRICTION_K, C.BALL_E, C.CUSHION_E,
                        C.CUSHION_T, C.STOP_SPEED)

    def events(self):
        return self.ev[: self.nev[0]]

    def run_to_rest(self):
        steps = _simulate(self.pos, self.vel, self.alive, self.pocket_of, self.first_hit,
                          SEGMENTS, POCKET_ARR, C.DT, int(C.MAX_SIM_TIME / C.DT),
                          C.BALL_R, C.FRICTION_A, C.FRICTION_K, C.BALL_E, C.CUSHION_E,
                          C.CUSHION_T, C.STOP_SPEED)
        self.vel[:] = 0.0
        return steps

    def potted(self):
        return [i for i in range(N_BALLS) if self.pocket_of[i] >= 0]


def simulate_shot(table, angle, speed):
    """Play a shot on a copy of the table and return (copy, potted list, first hit)."""
    t = table.copy()
    t.strike(angle, speed)
    t.run_to_rest()
    return t, t.potted(), int(t.first_hit[0])


def rack(rng=None):
    """A fresh rack: 15 balls in a triangle, the 8 in the middle, cue on the head spot."""
    rng = rng or np.random.default_rng()
    t = Table()
    t.alive[:] = True
    t.pos[0] = C.HEAD_SPOT
    order = [1, 9, 2, 10, 8, 3, 11, 4, 12, 5, 13, 6, 14, 7, 15]
    rest = [b for b in order if b not in (1, 8)]
    rng.shuffle(rest)
    rows = [[1], [rest[0], rest[1]], [rest[2], 8, rest[3]], rest[4:8], rest[8:13]]
    gap = 2 * C.BALL_R + 0.15
    dxr = gap * math.sqrt(3) / 2
    for r, row in enumerate(rows):
        for k, b in enumerate(row):
            x = C.FOOT_SPOT[0] + r * dxr
            y = C.FOOT_SPOT[1] + (k - (len(row) - 1) / 2) * gap
            t.pos[b] = (x + rng.uniform(-0.05, 0.05), y + rng.uniform(-0.05, 0.05))
    return t


def stopping_distance(v0):
    a, k = C.FRICTION_A, C.FRICTION_K
    return v0 / k - a / (k * k) * math.log(1 + k * v0 / a)


def distance_between_speeds(v0, v1):
    """How far a ball rolls while slowing from v0 to v1."""
    a, k = C.FRICTION_A, C.FRICTION_K
    return (v0 - v1) / k - a / (k * k) * math.log((a + k * v0) / (a + k * v1))


def speed_needed(d, v_end):
    """Start speed so the ball still has v_end after rolling d units (bisection)."""
    lo, hi = v_end, C.MAX_SPEED * 1.6
    if distance_between_speeds(hi, v_end) < d:
        return hi
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if distance_between_speeds(mid, v_end) < d:
            lo = mid
        else:
            hi = mid
    return hi


def warmup():
    """Compile the numba kernels once (cached on disk after the first run)."""
    t = rack(np.random.default_rng(0))
    t.strike(0.0, 1500.0)
    t.run_to_rest()
    t2 = rack(np.random.default_rng(0))
    t2.strike(0.0, 1500.0)
    t2.advance(4)

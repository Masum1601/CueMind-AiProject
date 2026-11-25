"""Run AI vs AI matches without graphics (benchmark mode and tests).

Thinking time is charged to each player's clock exactly as in the real game.
"""
import time

from . import config as C
from .agents import make
from .rules import Match
from .physics import simulate_shot


def think_budget(clock_left, fixed=None):
    if fixed is not None:
        return min(fixed, max(clock_left, 0.05))
    return max(0.25, min(2.5, clock_left * 0.14))


def play_match(name_a, name_b, seed=0, budget=None, breaker=0, verbose=False, on_shot=None):
    agents = [make(name_a, seed=seed * 2 + 1), make(name_b, seed=seed * 2 + 2)]
    m = Match.new((name_a, name_b), breaker=breaker, seed=seed)
    guard = 0
    while not m.over and guard < 400:
        guard += 1
        p = m.turn
        ag = agents[p]
        t0 = time.perf_counter()
        if m.ball_in_hand:
            x, y = ag.place(m)
            m.place_cue(x, y)
        bud = think_budget(m.clocks[p] - (time.perf_counter() - t0), budget)
        d = ag.choose(m, bud)
        spent = time.perf_counter() - t0
        if m.tick(spent):
            continue
        after, _, _ = simulate_shot(m.table, *_noise(d.shot, ag))
        rep = m.apply_result(after)
        if on_shot:
            on_shot(m, d, rep, spent)
        if verbose:
            print(f"{m.names[p]:8s} {d.shot.label:32s} {rep.text():28s} "
                  f"score {m.scores[0]}-{m.scores[1]} clock {m.clocks[0]:.1f}/{m.clocks[1]:.1f} "
                  f"think {spent:.2f}s {_brief(d.stats)}")
    return m


def _noise(shot, agent):
    from .agents.common import noisy
    return noisy(shot.angle, shot.speed, agent.rng)


def _brief(st):
    keys = ("depth", "sims", "pruned", "iterations")
    return " ".join(f"{k}={st[k]}" for k in keys if k in st)

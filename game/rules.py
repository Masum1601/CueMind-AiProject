"""Rack Attack Duel rules.

* Both players share one table; each has a 60 s clock that runs only while
  that player thinks and aims (it is paused while balls roll).
* Any object ball is worth 1 point, the 8-ball 3 points.
* Foul = the cue ball is pocketed (scratch) or the cue ball hits nothing.
  A foul costs 1 point and 5 seconds, and the opponent gets ball-in-hand.
* Pot a ball without a foul and you shoot again; otherwise the turn passes.
* The match ends when the table is clear or both clocks reach zero.
"""
from dataclasses import dataclass, field

import numpy as np

from . import config as C
from .physics import rack


@dataclass
class ShotReport:
    player: int
    potted: list
    scratch: bool
    no_contact: bool
    points: int
    foul: bool
    keeps_turn: bool
    first_hit: int

    def text(self):
        if self.foul:
            why = "Scratch" if self.scratch else "No contact"
            return f"{why}! -{C.FOUL_POINTS} pt, -{int(C.FOUL_SECONDS)} s"
        if self.potted:
            return f"+{self.points}"
        return "Miss"


@dataclass
class Match:
    names: tuple = ("Player 1", "Player 2")
    table: object = None
    scores: list = field(default_factory=lambda: [0, 0])
    clocks: list = field(default_factory=lambda: [C.MATCH_CLOCK, C.MATCH_CLOCK])
    turn: int = 0
    ball_in_hand: bool = False
    is_break: bool = True
    over: bool = False
    shots_taken: list = field(default_factory=lambda: [0, 0])
    balls_potted: list = field(default_factory=lambda: [0, 0])
    fouls: list = field(default_factory=lambda: [0, 0])
    think_time: list = field(default_factory=lambda: [0.0, 0.0])
    history: list = field(default_factory=list)

    @classmethod
    def new(cls, names, breaker=0, seed=None):
        m = cls(names=tuple(names))
        m.table = rack(np.random.default_rng(seed))
        m.turn = breaker
        return m

    # --------------------------------------------------------- clocks
    def tick(self, dt):
        """Spend clock time for the player to move. Returns True if it ran out."""
        if self.over:
            return False
        self.clocks[self.turn] = max(0.0, self.clocks[self.turn] - dt)
        self.think_time[self.turn] += dt
        if self.clocks[self.turn] <= 0.0:
            self._pass_turn()
            return True
        return False

    def _pass_turn(self):
        other = 1 - self.turn
        if self.clocks[other] > 0.0:
            self.turn = other
        if self.clocks[0] <= 0.0 and self.clocks[1] <= 0.0:
            self.over = True

    def balls_left(self):
        return int(self.table.alive[1:].sum())

    # --------------------------------------------------------- shots
    def apply_result(self, table_after):
        """Score a finished shot; table_after holds pocket_of / first_hit."""
        p = self.turn
        potted = [b for b in range(1, 16) if table_after.pocket_of[b] >= 0]
        scratch = table_after.pocket_of[0] >= 0
        first = int(table_after.first_hit[0])
        no_contact = first < 0
        foul = scratch or no_contact
        points = sum(C.ball_points(b) for b in potted)
        if foul:
            points -= C.FOUL_POINTS
            self.clocks[p] = max(0.0, self.clocks[p] - C.FOUL_SECONDS)
            self.fouls[p] += 1
        self.scores[p] += points
        self.balls_potted[p] += len(potted)
        self.shots_taken[p] += 1
        self.is_break = False
        keeps = bool(potted) and not foul and self.clocks[p] > 0.0
        rep = ShotReport(p, potted, scratch, no_contact, points, foul, keeps, first)
        self.history.append(rep)
        self.table = table_after
        self.table.vel[:] = 0.0
        if scratch:
            self.table.alive[0] = False
        self.ball_in_hand = foul
        if self.balls_left() == 0:
            self.over = True
            return rep
        if not keeps:
            other = 1 - p
            if self.clocks[other] > 0.0:
                self.turn = other
            elif self.clocks[p] <= 0.0:
                self.over = True
        if self.clocks[0] <= 0.0 and self.clocks[1] <= 0.0:
            self.over = True
        return rep

    def place_cue(self, x, y):
        self.table.pos[0] = (x, y)
        self.table.vel[0] = (0.0, 0.0)
        self.table.alive[0] = True
        self.table.pocket_of[0] = -1
        self.ball_in_hand = False

    def winner(self):
        if self.scores[0] != self.scores[1]:
            return 0 if self.scores[0] > self.scores[1] else 1
        if abs(self.clocks[0] - self.clocks[1]) > 0.05:
            return 0 if self.clocks[0] > self.clocks[1] else 1
        return -1

    def snapshot(self):
        """A cheap copy for the AI to search from."""
        m = Match(self.names)
        m.table = self.table.copy()
        m.scores = list(self.scores)
        m.clocks = list(self.clocks)
        m.turn = self.turn
        m.ball_in_hand = self.ball_in_hand
        m.is_break = self.is_break
        m.over = self.over
        return m

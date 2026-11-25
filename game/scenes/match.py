"""The match scene: AI vs AI or Human vs AI, with animation, sound and the AI Vision panel."""
import math
import random
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pygame

from .. import config as C
from ..rules import Match
from ..agents import make
from ..agents.common import noisy
from ..shots import legal_cue_spot
from ..planner import plan_runout
from ..headless import think_budget
from ..render import assets as A
from ..render.balls import BallSprites
from ..render.tablegfx import to_screen, TX, TY
from ..render.cue import Cue
from ..render.effects import Effects
from ..render.ui import Button

COLORS = (C.CYAN, C.AMBER)
R = C.BALL_R
PANEL_RECT = pygame.Rect(1206, 196, 370, 616)
OV_RECT = pygame.Rect(30, 176, 1170, 660)       # the part of the screen the aim/vision overlay can touch


def avatar_surface(kind, accent, d):
    img = None
    if kind == "minimax":
        img = A.image("avatar_minimax.jpg")
    elif kind == "mcts":
        img = A.image("avatar_mcts.jpg")
    elif kind == "greedy":
        base = A.image("avatar_minimax.jpg")
        if base:
            img = base.copy()
            tint = pygame.Surface(img.get_size())
            tint.fill((60, 230, 140))
            img.blit(tint, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    if img is not None:
        return A.circle_crop(img, d)
    s = pygame.Surface((d, d), pygame.SRCALPHA)
    for r in range(d // 2, 0, -1):
        c = A.mix((10, 16, 30), tuple(int(v * 0.55) for v in accent), (1 - r / (d / 2)) ** 1.5)
        pygame.draw.circle(s, (*c, 255), (d // 2, d // 2), r)
    pygame.draw.circle(s, (*accent, 255), (d // 2, int(d * 0.40)), int(d * 0.16))
    pygame.draw.ellipse(s, (*accent, 255), (int(d * 0.24), int(d * 0.60), int(d * 0.52), int(d * 0.42)))
    mask = pygame.Surface((d, d), pygame.SRCALPHA)
    pygame.draw.circle(mask, (255, 255, 255, 255), (d // 2, d // 2), d // 2)
    s.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return s


def lerp_angle(a, b, t):
    d = (b - a + math.pi) % (2 * math.pi) - math.pi
    return a + d * t


def aim_preview(table, angle):
    """Where a shot along `angle` first hits: ghost ball, object path and cue deflection."""
    cx, cy = table.pos[0]
    dx, dy = math.cos(angle), math.sin(angle)
    best_t, best_b = 1e9, -1
    for b in range(1, 16):
        if not table.alive[b]:
            continue
        bx, by = table.pos[b]
        t = (bx - cx) * dx + (by - cy) * dy
        if t <= 0:
            continue
        perp2 = (bx - cx) ** 2 + (by - cy) ** 2 - t * t
        if perp2 < (2 * R) ** 2:
            th = t - math.sqrt(4 * R * R - perp2)
            if th < best_t:
                best_t, best_b = th, b
    # first cushion along the ray
    tc = 1e9
    for lim, axis in ((R, 0), (C.FIELD_W - R, 0), (R, 1), (C.FIELD_H - R, 1)):
        comp = dx if axis == 0 else dy
        base = cx if axis == 0 else cy
        if abs(comp) > 1e-9:
            t = (lim - base) / comp
            if t > 1e-6:
                tc = min(tc, t)
    out = {"start": (cx, cy)}
    if best_b >= 0 and best_t < tc:
        gx, gy = cx + dx * best_t, cy + dy * best_t
        bx, by = table.pos[best_b]
        nx, ny = bx - gx, by - gy
        nl = math.hypot(nx, ny) or 1
        nx, ny = nx / nl, ny / nl
        dot = dx * nx + dy * ny
        tx, ty = dx - dot * nx, dy - dot * ny
        tl = math.hypot(tx, ty)
        out.update(ghost=(gx, gy), ball=best_b, obj=(nx, ny), cue_after=(tx / tl, ty / tl) if tl > 0.05 else None,
                   cut=math.degrees(math.acos(max(-1, min(1, dot)))))
    else:
        out.update(end=(cx + dx * min(tc, 1400), cy + dy * min(tc, 1400)))
    return out


class MatchScene:
    def __init__(self, app, players, speed=1, vision=True, breaker=0, seed=None):
        self.app = app
        self.players = players
        self.speed = speed
        self.vision = vision
        self.breaker = breaker
        self.seed = seed
        self.match = Match.new([p["name"] for p in players], breaker=breaker, seed=seed)
        self.agents = [make(p["agent"], seed=(seed or random.randint(0, 99999)) + i) if p["kind"] == "ai" else None
                       for i, p in enumerate(players)]
        self.sprites = BallSprites(R)
        rng = np.random.default_rng(seed)
        for n in range(16):
            self.sprites.reset(n, rng)
        self.mini = BallSprites(8.5)
        face = np.array([[0.0, 1.0, 0.0], [0.0, 0.0, -1.0], [-1.0, 0.0, 0.0]])   # number disc towards the viewer
        for n in range(16):
            self.mini.orient[n] = face
        self.fx = Effects()
        self.cues = [Cue(COLORS[0]), Cue(COLORS[1])]
        self.avatars = [avatar_surface(p["avatar"], COLORS[i], 104) for i, p in enumerate(players)]
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.future = None
        self.progress = {}
        self.decision = None
        self.plan = []
        self.cue_angle = 0.0
        self.aim_from = self.aim_to = 0.0
        self.pull = 0.0
        self.pull_target = 0.0
        self.cue_alpha = 255
        self.phase = "intro"
        self.phase_t = 0.0
        self.t = 0.0
        self.acc = 0.0
        self.toast = None
        self.banner = None
        self.log = []
        self.totals = [{"sims": 0, "decisions": 0, "think": 0.0, "best_depth": 0, "iterations": 0} for _ in range(2)]
        self.paused = False
        self.dragging = False
        self.drag_start = (0, 0)
        self.power = 0.0
        self.key_aim = False
        self.last_tick_sec = [99, 99]
        self.overlay = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
        self.pause_buttons = [
            Button((650, 400, 300, 64), "Resume", accent=C.CYAN, on_click=self._resume),
            Button((650, 480, 300, 64), "Restart", accent=C.AMBER, on_click=self._restart),
            Button((650, 560, 300, 64), "Main menu", accent=C.MUTED, on_click=self._to_menu),
        ]
        self.cue_angle = math.atan2(C.FOOT_SPOT[1] - C.HEAD_SPOT[1], C.FOOT_SPOT[0] - C.HEAD_SPOT[0])
        app.sounds.music(True)

    # ------------------------------------------------------------ helpers
    @property
    def table(self):
        return self.match.table

    def is_ai(self, p):
        return self.players[p]["kind"] == "ai"

    def set_phase(self, p):
        self.phase = p
        self.phase_t = 0.0

    def _resume(self):
        self.paused = False

    def _restart(self):
        self._shutdown()
        self.app.switch(MatchScene(self.app, self.players, self.speed, self.vision, self.breaker, None))

    def _to_menu(self):
        self._shutdown()
        from .menu import MenuScene
        self.app.switch(MenuScene(self.app))

    def _shutdown(self):
        self.pool.shutdown(wait=False, cancel_futures=True)

    def say(self, text, color, size=40, life=1.4):
        self.toast = [text, color, size, life, life]
        tw, th = A.font("black", size).size(text)
        pill = pygame.Surface((tw + 72, th + 26), pygame.SRCALPHA)
        rr = pill.get_rect()
        pygame.draw.rect(pill, (6, 10, 20, 210), rr, border_radius=rr.h // 2)
        pygame.draw.rect(pill, (*color, 255), rr, width=2, border_radius=rr.h // 2)
        self.toast_pill = pill

    def _on_progress(self, stats):
        self.progress = stats

    # ------------------------------------------------------------ turn flow
    def begin_turn(self):
        m = self.match
        if m.over:
            self.set_phase("over")
            self.app.sounds.play("win")
            return
        p = m.turn
        if m.clocks[p] <= 0.05:
            m.clocks[p] = 0.0
            m._pass_turn()
            if m.turn == p or m.over:
                m.over = True
                self.set_phase("over")
                self.app.sounds.play("win")
                return
            self.say(f"{m.names[p]}: time up!", C.RED, 40, 1.2)
            p = m.turn
        self.decision = None
        self.progress = {}
        self.plan = []
        if self.log and self.log[-1][0] != p:
            who = "Your turn" if m.names[p] == "You" else f"{m.names[p]}'s turn"
            self.banner = [who, COLORS[p], 1.1]
        if m.ball_in_hand or not self.table.alive[0]:
            if self.is_ai(p):
                x, y = self.agents[p].place(m)
                m.place_cue(x, y)
                self.sprites.cache.pop(0, None)
                sx, sy = to_screen(x, y)
                self.fx.ring(sx, sy, COLORS[p], 8, 40, 0.5)
                self.say("Ball in hand", COLORS[p], 30, 1.0)
            else:
                self.set_phase("place_human")
                return
        if self.is_ai(p):
            budget = think_budget(m.clocks[p])
            budget = max(0.15, min(budget, m.clocks[p] - 0.2))
            if not m.is_break:
                self.plan, _ = plan_runout(self.table)
            self.think_budget = budget
            self.future = self.pool.submit(self.agents[p].choose, m, budget, self._on_progress)
            self.set_phase("think")
        else:
            self.power = 0.0
            self.dragging = False
            self.set_phase("human")

    def do_strike(self):
        m = self.match
        p = m.turn
        if self.is_ai(p):
            shot = self.decision.shot
            a, v = noisy(shot.angle, shot.speed, self.agents[p].rng)
        else:
            a, v = self.cue_angle, max(40.0, self.power ** 1.35 * C.MAX_SPEED)
        self.table.strike(a, v)
        self.app.sounds.play("strike", 0.4 + 0.6 * v / C.MAX_SPEED)
        if m.is_break:
            self.fx.add_shake(9)
        self.shot_player = p
        self.acc = 0.0
        self.cue_alpha = 255
        self.set_phase("roll")

    def resolve(self):
        m = self.match
        rep = m.apply_result(self.table)
        p = rep.player
        self.fx.trails.clear()
        if rep.foul:
            self.app.sounds.play("foul")
            self.say(rep.text(), C.RED, 40, 1.6)
        elif rep.potted:
            self.app.sounds.play("score", 0.8)
            n = len(rep.potted)
            if n >= 2:
                word = {2: "DOUBLE!", 3: "TRIPLE!"}.get(n, f"x{n} MULTI!")
                self.say(word, C.AMBER, 60, 1.6)
            else:
                self.say(f"+{rep.points}" + ("  8-BALL!" if 8 in rep.potted else ""), COLORS[p], 44, 1.1)
        else:
            self.say("Miss", C.MUTED, 32, 0.9)
        label = self.decision.shot.label if (self.decision and self.is_ai(p)) else "your shot"
        self.log.append((p, label, rep.text(), rep.foul, bool(rep.potted)))
        self.log = self.log[-6:]
        self.set_phase("result")

    # ------------------------------------------------------------ update
    def update(self, dt):
        if self.paused:
            mouse = self.app.mouse()
            for b in self.pause_buttons:
                b.update(dt, mouse, self.app.sounds)
            return
        self.t += dt
        self.phase_t += dt
        self.fx.update(dt)
        if self.toast:
            self.toast[3] -= dt
            if self.toast[3] <= 0:
                self.toast = None
        if self.banner:
            self.banner[2] -= dt
            if self.banner[2] <= 0:
                self.banner = None
        m = self.match
        p = m.turn
        ph = self.phase
        if ph == "intro":
            k = int(self.phase_t / 0.6)
            if 1 <= k <= 3 and getattr(self, "_intro_k", 0) != k:
                self._intro_k = k
                self.app.sounds.play("tick", 1.0)
            if self.phase_t > 2.6:
                self.begin_turn()
        elif ph == "think":
            m.clocks[p] = max(0.02, m.clocks[p] - dt)
            m.think_time[p] += dt
            self._clock_ticks(p)
            self.cue_angle += math.sin(self.t * 1.7) * 0.0009
            if self.future is not None and self.future.done():
                d = self.future.result()
                if m.clocks[p] <= 0.03:          # thought past the end of the clock: the shot is lost
                    m.clocks[p] = 0.0
                    self.begin_turn()
                    return
                self.decision = d
                tot = self.totals[p]
                tot["sims"] += d.stats.get("sims", 0)
                tot["decisions"] += 1
                tot["think"] += d.stats.get("time", 0.0)
                tot["best_depth"] = max(tot["best_depth"], d.stats.get("depth", 0))
                tot["iterations"] += d.stats.get("iterations", 0)
                if d.plan:
                    self.plan = d.plan
                self.aim_from = self.cue_angle
                self.aim_to = d.shot.angle
                self.pull_target = 16 + 100 * (d.shot.speed / C.MAX_SPEED)
                self.set_phase("aim")
        elif ph in ("human", "place_human"):
            if m.tick(dt):
                self.say("Time up!", C.RED, 44, 1.2)
                self.begin_turn()
                return
            self._clock_ticks(p)
            if ph == "human" and not self.dragging and not self.key_aim:
                mx, my = self.app.mouse()
                cx, cy = to_screen(*self.table.pos[0])
                if (mx - cx) ** 2 + (my - cy) ** 2 > 16:
                    self.cue_angle = math.atan2(my - cy, mx - cx)
            if ph == "human" and self.dragging:
                mx, my = self.app.mouse()
                d = math.hypot(mx - self.drag_start[0], my - self.drag_start[1])
                self.power = max(0.0, min(1.0, d / 240.0))
                self.pull = 8 + 110 * self.power
            keys = pygame.key.get_pressed()
            rot = (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * (0.6 if keys[pygame.K_LSHIFT] else 0.12)
            if rot and ph == "human":
                self.key_aim = True
                self.cue_angle += math.radians(rot) * dt * 60
        elif ph == "aim":
            k = A.ease_in_out(self.phase_t / 0.6)
            self.cue_angle = lerp_angle(self.aim_from, self.aim_to, k)
            if self.phase_t >= 0.6:
                self.set_phase("pull")
        elif ph == "pull":
            self.pull = A.ease_out(self.phase_t / 0.38) * self.pull_target
            if self.phase_t >= 0.5:
                self.set_phase("stroke")
        elif ph == "stroke":
            self.pull = self.pull_target * max(0.0, 1 - self.phase_t / 0.06)
            if self.phase_t >= 0.06:
                self.pull = 0.0
                self.do_strike()
        elif ph == "roll":
            self._roll(dt)
        elif ph == "result":
            if self.phase_t > 0.85:
                if m.over:
                    self.set_phase("over")
                    self.app.sounds.play("win")
                else:
                    self.begin_turn()
        elif ph == "over":
            if self.phase_t > 2.4:
                self._shutdown()
                from .results import ResultsScene
                self.app.switch(ResultsScene(self.app, self.match, self.players, self.totals,
                                             (self.speed, self.vision, self.breaker)))

    def _clock_ticks(self, p):
        s = int(self.match.clocks[p])
        if s < 10 and s != self.last_tick_sec[p]:
            self.last_tick_sec[p] = s
            self.app.sounds.play("tick", 0.8)

    def _roll(self, dt):
        t = self.table
        self.acc += dt * self.speed
        steps = int(self.acc / C.DT)
        self.acc -= steps * C.DT
        steps = min(steps, 32)
        self.cue_alpha = max(0, self.cue_alpha - int(dt * 900))
        if steps <= 0:
            return
        before = t.pos.copy()
        alive_before = t.alive.copy()
        moving = t.advance(steps)
        sounds = self.app.sounds
        n_clacks = 0
        for ev in t.events():
            kind = int(ev[0])
            sx, sy = to_screen(ev[4], ev[5])
            if kind == 1:
                if n_clacks < 5:
                    sounds.play("clacks", min(1.0, ev[3] / 900.0))
                    n_clacks += 1
                if ev[3] > 650:
                    self.fx.sparks(sx, sy, (210, 240, 255), 6, 120, 0.3)
                if ev[3] > 1100:
                    self.fx.ring(sx, sy, (200, 235, 255), 4, 26, 0.22, 2)
            elif kind == 2:
                if ev[3] > 70:
                    sounds.play("thud", min(1.0, ev[3] / 1100.0) * 0.8)
            elif kind == 3:
                ball, pk = int(ev[1]), int(ev[2])
                px, py = to_screen(C.POCKETS[pk][0], C.POCKETS[pk][1])
                col = COLORS[self.shot_player] if ball != 0 else C.RED
                sounds.play("pocket", 0.9)
                self.fx.ring(px, py, col, 10, 58, 0.5, 4)
                self.fx.sparks(px, py, col, 16, 200, 0.55)
                if ball != 0:
                    self.fx.float_text(px, py - 30 if py > TY + 100 else py + 40,
                                       f"+{C.ball_points(ball)}", col, 34 if ball != 8 else 46)
        for n in range(16):
            if alive_before[n] and not t.alive[n]:
                pk = t.pocket_of[n]
                px, py = to_screen(C.POCKETS[pk][0], C.POCKETS[pk][1])
                bx, by = to_screen(*before[n])
                self.fx.drop(self.sprites.sprite(n), bx, by, px, py)
            elif t.alive[n]:
                dx, dy = t.pos[n, 0] - before[n, 0], t.pos[n, 1] - before[n, 1]
                if dx or dy:
                    self.sprites.roll(n, dx, dy)
                    sp = math.hypot(t.vel[n, 0], t.vel[n, 1])
                    self.fx.trail(n, *to_screen(*t.pos[n]), sp)
        if not moving or self.phase_t > 20:
            t.vel[:] = 0.0
            self.resolve()

    # ------------------------------------------------------------ input
    def handle(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE or e.key == pygame.K_p:
                self.paused = not self.paused
                return
            if e.key == pygame.K_v:
                self.vision = not self.vision
            if e.key == pygame.K_f:
                self.speed = {1: 2, 2: 4, 4: 1}[self.speed]
                self.say(f"Speed {self.speed}x", C.INK, 30, 0.8)
        if self.paused:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for b in self.pause_buttons:
                    if b.click(e.pos, self.app.sounds):
                        break
            return
        if self.phase == "place_human":
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                x, y = e.pos[0] - TX, e.pos[1] - TY
                if legal_cue_spot(self.table, x, y):
                    self.match.place_cue(x, y)
                    self.sprites.cache.pop(0, None)
                    self.fx.ring(e.pos[0], e.pos[1], COLORS[self.match.turn], 8, 36, 0.4)
                    self.app.sounds.play("click")
                    self.power = 0.0
                    self.set_phase("human")
            return
        if self.phase != "human":
            return
        if e.type == pygame.MOUSEMOTION and not self.dragging:
            self.key_aim = False
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.dragging = True
            self.drag_start = e.pos
            self.power = 0.0
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 3:
            self.dragging = False
            self.power = 0.0
            self.pull = 0.0
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1 and self.dragging:
            self.dragging = False
            if self.power > 0.03:
                self.pull_target = self.pull
                self.set_phase("stroke")
            else:
                self.pull = 0.0
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE and not self.dragging:
            if self.power < 0.03:
                self.power = 0.5
            self.pull_target = 8 + 110 * self.power
            self.set_phase("stroke")
        elif e.type == pygame.KEYDOWN and e.key in (pygame.K_UP, pygame.K_DOWN):
            self.power = max(0.0, min(1.0, self.power + (0.05 if e.key == pygame.K_UP else -0.05)))
            self.pull = 8 + 110 * self.power

    # ------------------------------------------------------------ drawing
    def draw(self, screen):
        m = self.match
        ox, oy = self.fx.offset()
        self.app.art.draw(screen, m.turn if self.phase not in ("intro", "over") else None, self.t)
        if self.vision and self.phase in ("think", "aim", "pull", "stroke") and self.is_ai(m.turn):
            self.overlay.fill((0, 0, 0, 0), OV_RECT)
            self._draw_vision(self.overlay)
            screen.blit(self.overlay, OV_RECT.topleft, OV_RECT)
        self.fx.draw_under(screen)
        self._draw_balls(screen, ox, oy)
        self._draw_aim(screen)
        self._draw_cue(screen)
        self.fx.draw_over(screen)
        self._draw_hud(screen)
        self._draw_panel(screen)
        self._draw_bottom(screen)
        self._draw_messages(screen)
        if self.phase == "intro":
            self._draw_intro(screen)
        if self.paused:
            self._draw_pause(screen)

    def _draw_balls(self, screen, ox, oy):
        t = self.table
        sh = self.sprites.shadow
        for n in range(16):
            if not t.alive[n]:
                continue
            x, y = to_screen(*t.pos[n])
            screen.blit(sh, (x - sh.get_width() / 2 + 5 + ox, y - sh.get_height() / 2 + 7 + oy))
        for n in range(16):
            if not t.alive[n]:
                continue
            x, y = to_screen(*t.pos[n])
            s = self.sprites.sprite(n)
            screen.blit(s, (x - s.get_width() / 2 + ox, y - s.get_height() / 2 + oy))
        if self.phase == "place_human":
            mx, my = self.app.mouse()
            ok = legal_cue_spot(t, mx - TX, my - TY)
            s = self.sprites.sprite(0).copy()
            s.set_alpha(170)
            screen.blit(s, s.get_rect(center=(mx, my)))
            pygame.draw.circle(screen, C.GREEN if ok else C.RED, (mx, my), int(R + 6), 2)

    def _cue_tip(self):
        cx, cy = to_screen(*self.table.pos[0])
        d = R + 5 + self.pull
        return (cx - math.cos(self.cue_angle) * d, cy - math.sin(self.cue_angle) * d)

    def _draw_cue(self, screen):
        if not self.table.alive[0] or self.phase in ("intro", "place_human", "over", "result"):
            return
        alpha = 255
        if self.phase == "roll":
            alpha = self.cue_alpha
            if alpha <= 0:
                return
        self.cues[self.match.turn if self.phase != "roll" else self.shot_player].draw(
            screen, self._cue_tip(), self.cue_angle, alpha)

    def _dash(self, surf, a, b, color, alpha=200, width=2, dash=9, gap=7):
        ax, ay = a
        bx, by = b
        L = math.hypot(bx - ax, by - ay)
        if L < 1:
            return
        ux, uy = (bx - ax) / L, (by - ay) / L
        s = 0.0
        while s < L:
            e = min(L, s + dash)
            pygame.draw.line(surf, (*color, alpha), (ax + ux * s, ay + uy * s), (ax + ux * e, ay + uy * e), width)
            s = e + gap

    def _draw_aim(self, screen):
        ph = self.phase
        if not self.table.alive[0]:
            return
        human = ph == "human"
        ai_aim = ph in ("aim", "pull", "stroke") and self.decision is not None
        if not (human or ai_aim):
            return
        p = self.match.turn
        col = COLORS[p]
        ov = self.overlay
        ov.fill((0, 0, 0, 0), OV_RECT)
        prev = aim_preview(self.table, self.cue_angle)
        sx, sy = to_screen(*prev["start"])
        if "ghost" in prev:
            gx, gy = to_screen(*prev["ghost"])
            pygame.draw.line(ov, (140, 225, 255, 45), (sx, sy), (gx, gy), 8)
            self._dash(ov, (sx, sy), (gx, gy), (235, 245, 255), 210, 2)
            pygame.draw.circle(ov, (235, 245, 255, 45), (int(gx), int(gy)), int(R))
            pygame.draw.circle(ov, (235, 245, 255, 200), (int(gx), int(gy)), int(R), 2)
            bx, by = to_screen(*self.table.pos[prev["ball"]])
            ox, oy = prev["obj"]
            pygame.draw.line(ov, (*col, 70), (bx, by), (bx + ox * 150, by + oy * 150), 10)
            pygame.draw.line(ov, (*col, 230), (bx, by), (bx + ox * 150, by + oy * 150), 3)
            if prev["cue_after"] is not None:
                tx, ty = prev["cue_after"]
                self._dash(ov, (gx, gy), (gx + tx * 80, gy + ty * 80), (235, 245, 255), 120, 2, 5, 6)
            if human:
                A.text(ov, f"cut {prev['cut']:.0f}°", "semibold", 16, (235, 245, 255),
                       (gx + 16, gy - 26), "topleft")
        else:
            ex, ey = to_screen(*prev["end"])
            self._dash(ov, (sx, sy), (ex, ey), (235, 245, 255), 160, 2)
        screen.blit(ov, OV_RECT.topleft, OV_RECT)
        if ai_aim:
            lab = self.decision.shot.label
            A.text(screen, lab.upper(), "bold", 18, col, (TX + C.FIELD_W / 2, TY + 18), "midtop", glow=col)

    def _draw_vision(self, ov):
        if not self.vision or self.phase not in ("think", "aim", "pull", "stroke"):
            return
        p = self.match.turn
        if not self.is_ai(p):
            return
        col = COLORS[p]
        top = self.progress.get("top") or (self.decision.ranked if self.decision else [])
        for i, item in enumerate(top[:5]):
            shot = item[0]
            if not shot.path:
                continue
            pts = [to_screen(*q) for q in shot.path]
            a = 150 if i == 0 else 70
            w = 3 if i == 0 else 1
            pygame.draw.lines(ov, (*col, a), False, pts, w)
            if len(pts) > 1:
                pygame.draw.circle(ov, (*col, a), (int(pts[1][0]), int(pts[1][1])), int(R), 1)
        for k, (b, pk) in enumerate(self.plan[:5]):
            if not self.table.alive[b]:
                continue
            x, y = to_screen(*self.table.pos[b])
            pygame.draw.circle(ov, (*C.AMBER, 235), (int(x + 13), int(y - 13)), 9)
            A.text(ov, str(k + 1), "bold", 13, (20, 14, 6), (x + 13, y - 13), "center")

    # ------------------------------------------------------------ HUD
    def _draw_hud(self, screen):
        m = self.match
        for p in (0, 1):
            self._player_card(screen, p)
        cx = C.SCREEN_W / 2
        A.text(screen, "RACK ATTACK", "display", 30, C.INK, (cx, 28), "midtop", glow=C.CYAN, glow_strength=0.6)
        A.text(screen, f"60-SECOND DUEL  ·  {m.balls_left()} BALLS LEFT", "semibold", 13, C.AMBER, (cx, 68), "midtop")
        # rack tracker: every object ball, an empty socket once it is potted
        x0 = cx - 7 * 21
        for i, b in enumerate(range(1, 16)):
            x, y = int(x0 + i * 21), 106
            if m.table.alive[b]:
                s = self.mini.sprite(b)
                screen.blit(s, s.get_rect(center=(x, y)))
                if b == 8:
                    pygame.draw.circle(screen, C.AMBER, (x, y), 12, 1)
            else:
                pygame.draw.circle(screen, (16, 24, 42), (x, y), 9)
                pygame.draw.circle(screen, (44, 60, 92), (x, y), 9, 1)
        # clock tug bar: each side shrinks towards the centre as its clock runs down
        w, y = 300, 136
        pygame.draw.rect(screen, (20, 30, 52), (cx - w / 2, y, w, 10), border_radius=5)
        f0 = max(0.0, m.clocks[0] / C.MATCH_CLOCK)
        f1 = max(0.0, m.clocks[1] / C.MATCH_CLOCK)
        if f0 > 0:
            pygame.draw.rect(screen, C.CYAN, (cx - w / 2 * f0, y, w / 2 * f0, 10),
                             border_top_left_radius=5, border_bottom_left_radius=5)
        if f1 > 0:
            pygame.draw.rect(screen, C.AMBER, (cx, y, w / 2 * f1, 10),
                             border_top_right_radius=5, border_bottom_right_radius=5)
        pygame.draw.line(screen, C.INK, (cx, y - 3), (cx, y + 12), 2)
        A.text(screen, "TIME", "semibold", 11, C.MUTED, (cx, y + 16), "midtop")

    def _player_card(self, screen, p):
        m = self.match
        col = COLORS[p]
        active = (m.turn == p) and self.phase not in ("intro", "over")
        rect = pygame.Rect(64, 22, 520, 150) if p == 0 else pygame.Rect(1016, 22, 520, 150)
        if active:
            pulse = 0.55 + 0.45 * math.sin(self.t * 3)
            A.glow_rect(screen, rect, col, pulse)
        A.panel(screen, rect, fill=(12, 20, 38), edge=col if active else C.PANEL_EDGE, radius=20, alpha=235, width=2)
        av_c = (rect.x + 80, rect.centery) if p == 0 else (rect.right - 80, rect.centery)
        frac = m.clocks[p] / C.MATCH_CLOCK
        low = m.clocks[p] < 10
        ring_col = C.RED if low else col
        pygame.draw.circle(screen, (30, 44, 70), av_c, 62, 6)
        A.arc(screen, ring_col, av_c, 62, frac, 6)
        screen.blit(self.avatars[p], self.avatars[p].get_rect(center=av_c))
        name_x = rect.x + 160 if p == 0 else rect.right - 160
        anchor = "topleft" if p == 0 else "topright"
        pl = self.players[p]
        A.text(screen, pl["name"], "bold", 28, C.INK, (name_x, rect.y + 18), anchor)
        sub = pl.get("sub", "")
        A.text(screen, sub, "body", 15, C.MUTED, (name_x, rect.y + 54), anchor)
        clock_txt = f"{m.clocks[p]:4.1f}s"
        cc = C.RED if low else C.INK
        if low and active:
            cc = A.mix(C.RED, (255, 255, 255), 0.5 + 0.5 * math.sin(self.t * 10))
        A.text(screen, clock_txt, "display", 26, cc, (name_x, rect.y + 80), anchor)
        status = ""
        if active:
            status = {"think": "THINKING", "aim": "AIMING", "pull": "AIMING", "stroke": "SHOOT",
                      "roll": "", "human": "YOUR SHOT", "place_human": "BALL IN HAND"}.get(self.phase, "")
        if status:
            dots = "." * (1 + int(self.t * 3) % 3) if self.phase == "think" else ""
            pw = A.font("semibold", 13).size(status + "...")[0] + 22
            px = name_x + 118 if p == 0 else name_x - 118 - pw
            pill = pygame.Rect(px, rect.y + 86, pw, 24)
            A.panel(screen, pill, fill=(10, 18, 34), edge=col, radius=12, alpha=255, width=1)
            A.text(screen, status + dots, "semibold", 13, col, (pill.x + 11, pill.centery), "midleft")
        score_x = rect.right - 34 if p == 0 else rect.x + 34
        A.text(screen, str(m.scores[p]), "display", 72, col, (score_x, rect.centery - 6),
               "midright" if p == 0 else "midleft", glow=col, glow_strength=0.8)
        # potted balls tray
        potted = [b for rep in m.history if rep.player == p for b in rep.potted]
        bx = name_x
        for i, b in enumerate(potted[:12]):
            s = self.mini.sprite(b)
            x = bx + i * 19 if p == 0 else bx - i * 19
            screen.blit(s, s.get_rect(center=(x + (8 if p == 0 else -8), rect.bottom - 18)))

    def _draw_panel(self, screen):
        r = PANEL_RECT
        A.panel(screen, r, fill=(10, 17, 33), edge=C.PANEL_EDGE, radius=18, alpha=225)
        m = self.match
        # after a shot the turn may already have passed: keep showing whoever just played
        p = self.shot_player if self.phase == "result" and hasattr(self, "shot_player") else m.turn
        col = COLORS[p]
        x0, y = r.x + 22, r.y + 20
        A.text(screen, "AI VISION", "display", 22, C.INK, (x0, y), glow=C.CYAN, glow_strength=0.4)
        A.text(screen, "lines " + ("on" if self.vision else "off"), "body", 13, C.MUTED, (r.right - 22, y + 6), "topright")
        pygame.draw.line(screen, C.PANEL_EDGE, (x0, y + 34), (r.right - 22, y + 34), 1)
        pygame.draw.line(screen, col, (x0, y + 34), (x0 + 64, y + 34), 3)
        y += 46
        if not self.is_ai(p):
            self._panel_human(screen, x0, y, col)
            return
        pl = self.players[p]
        pygame.draw.circle(screen, col, (x0 + 7, y + 11), 6)
        A.text(screen, pl["name"], "bold", 20, C.INK, (x0 + 22, y), "topleft")
        if self.phase == "think":
            pygame.draw.circle(screen, (30, 44, 70), (r.right - 34, y + 11), 9, 3)
            A.arc(screen, col, (r.right - 34, y + 11), 9, 0.3, 3, start=self.t * 7)
        y += 26
        algo = (self.decision.stats if self.decision else self.progress).get("algorithm", pl.get("sub", ""))
        A.text(screen, algo, "body", 14, C.MUTED, (x0, y))
        y += 30
        st = self.decision.stats if self.decision else self.progress
        if self.phase == "think":
            el = self.phase_t
            frac = min(1.0, el / max(self.think_budget, 0.01))
            pygame.draw.rect(screen, (28, 40, 64), (x0, y, r.w - 44, 6), border_radius=3)
            pygame.draw.rect(screen, col, (x0, y, int((r.w - 44) * frac), 6), border_radius=3)
            y += 14
        tiles = self._tiles(st, pl["agent"])
        tw = (r.w - 44 - 12) // 2
        for i, (lab, val) in enumerate(tiles):
            tx = x0 + (i % 2) * (tw + 12)
            ty = y + (i // 2) * 70
            A.panel(screen, (tx, ty, tw, 60), fill=(16, 26, 48), edge=C.PANEL_EDGE, radius=10, alpha=240)
            A.text(screen, str(val), "display", 24, C.INK, (tx + 14, ty + 6))
            A.text(screen, lab, "body", 13, C.MUTED, (tx + 14, ty + 38))
        y += 2 * 70 + 6
        A.text(screen, "TOP SHOTS", "semibold", 13, C.MUTED, (x0, y))
        y += 22
        top = st.get("top") or (self.decision.ranked if self.decision else [])
        maxv = max([abs(t[1]) for t in top[:5]] + [1e-6]) if top else 1
        maxn = max([t[2] or 0 for t in top[:5]] + [1]) if top else 1
        for i, item in enumerate(top[:5]):
            shot, val, visits = item
            w = r.w - 44
            frac = (visits / maxn) if visits else (max(0.0, val) / maxv if maxv else 0)
            pygame.draw.rect(screen, (22, 34, 58), (x0, y, w, 30), border_radius=8)
            pygame.draw.rect(screen, A.mix((22, 34, 58), col, 0.55 if i == 0 else 0.3),
                             (x0, y, max(8, int(w * frac)), 30), border_radius=8)
            lab = shot.label[:26]
            A.text(screen, lab, "semibold", 14, C.INK, (x0 + 10, y + 15), "midleft")
            v = f"{visits} visits" if visits else f"{val:+.2f}"
            A.text(screen, v, "body", 13, C.INK, (x0 + w - 10, y + 15), "midright")
            y += 36
        y = max(y, r.y + 470)
        if self.plan:
            A.text(screen, "A* RUN-OUT PLAN", "semibold", 13, C.MUTED, (x0, y))
            y += 22
            for k, (b, pk) in enumerate(self.plan[:6]):
                s = self.mini.sprite(b)
                screen.blit(s, (x0 + k * 52, y))
                if k < len(self.plan[:6]) - 1:
                    A.text(screen, "›", "bold", 20, C.AMBER, (x0 + k * 52 + 30, y + 8), "center")
            y += 34
        kinds = st.get("kinds") or {}
        if kinds:
            line = "  ".join(f"{k} {v}" for k, v in sorted(kinds.items()))
            A.text(screen, "shots found: " + line, "body", 12, C.MUTED, (x0, r.bottom - 28))

    def _tiles(self, st, agent):
        if agent == "MCTS":
            sims = st.get("sims", 0)
            tm = max(st.get("time", self.phase_t if self.phase == "think" else 0.0), 0.01)
            return [("iterations", st.get("iterations", 0)), ("simulations", sims),
                    ("tree depth", st.get("depth", 0)), ("sims / sec", int(sims / tm) if sims else 0)]
        if agent == "Minimax":
            return [("IDDFS depth", st.get("depth", 0)), ("simulations", st.get("sims", 0)),
                    ("pruned (α-β)", st.get("pruned", 0)), ("nodes", st.get("nodes", 0))]
        return [("candidates", st.get("candidates", 0)), ("simulations", st.get("sims", 0)),
                ("look-ahead", "none"), ("policy", "greedy")]

    def _panel_human(self, screen, x0, y, col):
        A.text(screen, "YOUR SHOT", "bold", 22, col, (x0, y))
        y += 40
        lines = [
            "Move the mouse to aim.",
            "Hold the left button and drag",
            "away to set power, release to shoot.",
            "Right click cancels the stroke.",
            "Arrow keys: fine aim (Shift = fast).",
            "Up/Down: power, Space: shoot.",
            "",
            "Ball in hand: click to place",
            "the cue ball (green = legal).",
            "",
            "Your clock runs while you aim!",
        ]
        for ln in lines:
            A.text(screen, ln, "body", 16, C.INK if ln.startswith("Your") else C.MUTED, (x0, y))
            y += 26
        self._draw_log(screen, x0, PANEL_RECT.bottom - 150)

    def _draw_log(self, screen, x0, y):
        A.text(screen, "LAST SHOTS", "semibold", 13, C.MUTED, (x0, y))
        y += 22
        for p, label, res, foul, potted in self.log[-4:][::-1]:
            pygame.draw.circle(screen, COLORS[p], (x0 + 5, y + 9), 5)
            colr = C.RED if foul else (C.GREEN if potted else C.MUTED)
            A.text(screen, res, "semibold", 14, colr, (x0 + 18, y), "topleft")
            y += 24

    def _draw_bottom(self, screen):
        y = 848
        x = 64
        for key, lab in (("V", "AI vision " + ("on" if self.vision else "off")), ("F", f"speed {self.speed}x"),
                         ("P", "pause"), ("Esc", "menu")):
            x = A.keycap(screen, key, lab, (x, y)) + 20
        if self.phase in ("human", "stroke") and not self.is_ai(self.match.turn):
            x, w = 620, 420
            A.text(screen, "POWER", "semibold", 14, C.MUTED, (x - 12, y), "midright")
            pygame.draw.rect(screen, (24, 36, 60), (x, y - 9, w, 18), border_radius=9)
            fw = int(w * self.power)
            if fw > 0:
                c = A.mix(C.CYAN, C.AMBER, self.power)
                c = A.mix(c, C.RED, max(0.0, self.power - 0.8) * 5)
                pygame.draw.rect(screen, c, (x, y - 9, fw, 18), border_radius=9)
        # shot log for AI turns
        if self.is_ai(self.match.turn) or self.phase == "intro":
            x = 700
            for p, label, res, foul, potted in self.log[-3:][::-1]:
                colr = C.RED if foul else (C.GREEN if potted else C.MUTED)
                pygame.draw.circle(screen, COLORS[p], (x, y), 5)
                t = f"{label[:22]}  {res}"
                rr = A.text(screen, t, "body", 14, colr, (x + 12, y), "midleft")
                x = rr.right + 28
                if x > 1150:
                    break

    def _draw_messages(self, screen):
        if self.toast:
            txt, col, size, life, mx = self.toast
            k = 1 - life / mx
            pop = 1.0 + 0.15 * max(0.0, 1 - k * 5)
            alpha = int(255 * min(1.0, life / mx * 2.5))
            centre = (TX + C.FIELD_W / 2, TY + C.FIELD_H / 2 - 40)
            pill = self.toast_pill
            pill.set_alpha(alpha)
            screen.blit(pill, pill.get_rect(center=centre))
            A.text(screen, txt, "black", int(size * pop), col, centre, "center", glow=col, alpha=alpha)
        if self.banner:
            txt, col, life = self.banner
            k = 1 - life / 1.1
            x = TX + C.FIELD_W / 2 + (1 - A.ease_out(min(1, k * 4))) * 400
            alpha = int(255 * min(1.0, life * 3))
            band = pygame.Surface((C.FIELD_W, 70), pygame.SRCALPHA)
            band.fill((8, 12, 24, int(alpha * 0.6)))
            screen.blit(band, (TX, TY + C.FIELD_H / 2 + 30))
            A.text(screen, txt.upper(), "display", 34, col, (x, TY + C.FIELD_H / 2 + 65), "center", glow=col, alpha=alpha)

    def _draw_intro(self, screen):
        k = self.phase_t
        if not hasattr(self, "_scrim"):
            self._scrim = pygame.Surface((C.SCREEN_W, C.SCREEN_H))
            self._scrim.fill((4, 8, 16))
        self._scrim.set_alpha(int(200 * max(0.0, 1 - max(0.0, k - 2.2) * 2.5)))
        screen.blit(self._scrim, (0, 0))
        cy = C.SCREEN_H / 2 - 60
        A.text(screen, "RACK ATTACK DUEL", "display", 64, C.INK, (C.SCREEN_W / 2, cy - 70), "center",
               glow=C.CYAN, glow_strength=0.8)
        n0, n1 = self.players[0]["name"].upper(), self.players[1]["name"].upper()
        A.text(screen, n0, "display", 40, C.CYAN, (C.SCREEN_W / 2 - 60, cy + 10), "midright", glow=C.CYAN)
        A.text(screen, "VS", "black", 28, C.MUTED, (C.SCREEN_W / 2, cy + 10), "center")
        A.text(screen, n1, "display", 40, C.AMBER, (C.SCREEN_W / 2 + 60, cy + 10), "midleft", glow=C.AMBER)
        step = int(k / 0.6)
        word = {0: "", 1: "3", 2: "2", 3: "1"}.get(step, "BREAK!")
        if word:
            frac = (k % 0.6) / 0.6
            size = int(110 * (1.25 - 0.25 * A.ease_out(frac)))
            A.text(screen, word, "display", size, C.AMBER, (C.SCREEN_W / 2, cy + 130), "center",
                   glow=C.AMBER, alpha=int(255 * (1 - frac * 0.6)))
        A.text(screen, "60 s each  ·  1 pt per ball  ·  8-ball = 3  ·  foul = −1 pt, −5 s",
               "semibold", 18, C.MUTED, (C.SCREEN_W / 2, cy + 230), "center")

    def _draw_pause(self, screen):
        if not hasattr(self, "_pause_dim"):
            self._pause_dim = pygame.Surface((C.SCREEN_W, C.SCREEN_H))
            self._pause_dim.fill((4, 8, 16))
            self._pause_dim.set_alpha(190)
        screen.blit(self._pause_dim, (0, 0))
        A.text(screen, "PAUSED", "display", 64, C.INK, (C.SCREEN_W / 2, 300), "center", glow=C.CYAN)
        for b in self.pause_buttons:
            b.draw(screen)

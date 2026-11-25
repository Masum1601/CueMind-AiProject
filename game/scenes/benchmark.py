"""Benchmark: many silent AI vs AI matches, with live results and a CSV export."""
import csv
import os
import threading
import time

import pygame

from .. import config as C
from ..headless import play_match
from ..render import assets as A
from ..render.ui import Button, Picker


class BenchmarkScene:
    def __init__(self, app):
        self.app = app
        self.bg = A.image("tree.jpg", (C.SCREEN_W, C.SCREEN_H))
        self.dim = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
        self.dim.fill((6, 10, 20, 200))
        self.a = Picker((140, 220, 300, 76), "Player A (cyan)", ["Minimax", "MCTS", "Greedy"], 0, C.CYAN)
        self.b = Picker((460, 220, 300, 76), "Player B (amber)", ["Minimax", "MCTS", "Greedy"], 1, C.AMBER)
        self.n = Picker((780, 220, 220, 76), "Matches", ["10", "20", "50", "100"], 0, C.MUTED)
        self.bud = Picker((1020, 220, 240, 76), "Think time / shot", ["0.3 s", "0.6 s", "1.0 s", "clock"], 1, C.MUTED)
        self.run_btn = Button((1280, 220, 200, 76), "Run", accent=C.GREEN, on_click=self.start, big=True)
        self.back = Button((40, 30, 170, 52), "Back", accent=C.MUTED, on_click=self.go_back)
        self.save_btn = Button((1280, 760, 200, 60), "Save CSV", accent=C.CYAN, on_click=self.save)
        self.widgets = [self.a, self.b, self.n, self.bud]
        self.running = False
        self.stop = False
        self.results = []
        self.total = 0
        self.saved = ""
        self.lock = threading.Lock()

    def start(self):
        if self.running:
            self.stop = True
            return
        self.results = []
        self.saved = ""
        self.total = int(self.n.value)
        self.stop = False
        self.running = True
        names = (self.a.value, self.b.value)
        bud = None if self.bud.value == "clock" else float(self.bud.value.split()[0])
        threading.Thread(target=self._worker, args=(names, bud), daemon=True).start()

    def _worker(self, names, bud):
        for g in range(self.total):
            if self.stop:
                break
            totals = [{"sims": 0, "think": 0.0, "n": 0}, {"sims": 0, "think": 0.0, "n": 0}]

            def on_shot(m, d, rep, spent):
                t = totals[rep.player]
                t["sims"] += d.stats.get("sims", 0)
                t["think"] += spent
                t["n"] += 1

            t0 = time.perf_counter()
            m = play_match(names[0], names[1], seed=1000 + g, budget=bud, breaker=g % 2, on_shot=on_shot)
            row = {"game": g + 1, "a": names[0], "b": names[1], "score_a": m.scores[0], "score_b": m.scores[1],
                   "winner": {0: names[0], 1: names[1]}.get(m.winner(), "draw"), "fouls_a": m.fouls[0],
                   "fouls_b": m.fouls[1], "balls_a": m.balls_potted[0], "balls_b": m.balls_potted[1],
                   "think_a": totals[0]["think"] / max(totals[0]["n"], 1),
                   "think_b": totals[1]["think"] / max(totals[1]["n"], 1),
                   "sims_a": totals[0]["sims"], "sims_b": totals[1]["sims"],
                   "w": m.winner(), "secs": time.perf_counter() - t0}
            with self.lock:
                self.results.append(row)
        self.running = False

    def save(self):
        if not self.results:
            return
        path = os.path.join(C.ROOT, "benchmark_results.csv")
        keys = [k for k in self.results[0] if k != "w"]
        with open(path, "w", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            wr.writeheader()
            wr.writerows(self.results)
        self.saved = path

    def go_back(self):
        self.stop = True
        from .menu import MenuScene
        self.app.switch(MenuScene(self.app))

    def handle(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for w in ([] if self.running else self.widgets) + [self.run_btn, self.back, self.save_btn]:
                if w.click(e.pos, self.app.sounds):
                    return
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.go_back()

    def update(self, dt):
        mouse = self.app.mouse()
        for w in self.widgets + [self.run_btn, self.back, self.save_btn]:
            w.update(dt, mouse, self.app.sounds)
        self.run_btn.label = "Stop" if self.running else "Run"

    def _summary(self):
        with self.lock:
            rows = list(self.results)
        n = len(rows)
        s = {"n": n, "wa": sum(r["w"] == 0 for r in rows), "wb": sum(r["w"] == 1 for r in rows),
             "d": sum(r["w"] == -1 for r in rows)}
        for side in ("a", "b"):
            s["score_" + side] = sum(r["score_" + side] for r in rows) / max(n, 1)
            s["fouls_" + side] = sum(r["fouls_" + side] for r in rows) / max(n, 1)
            s["balls_" + side] = sum(r["balls_" + side] for r in rows) / max(n, 1)
            s["think_" + side] = sum(r["think_" + side] for r in rows) / max(n, 1)
            s["sims_" + side] = sum(r["sims_" + side] for r in rows) / max(n, 1)
        return s, rows

    def draw(self, screen):
        if self.bg:
            screen.blit(self.bg, (0, 0))
        screen.blit(self.dim, (0, 0))
        A.text(screen, "Benchmark", "display", 60, C.INK, (C.SCREEN_W / 2, 50), "midtop", glow=C.GREEN, glow_strength=0.6)
        A.text(screen, "Silent AI vs AI matches · same physics, same noise, thinking time charged to the clock",
               "body", 19, C.MUTED, (C.SCREEN_W / 2, 130), "midtop")
        for w in self.widgets:
            w.draw(screen)
        self.run_btn.draw(screen)
        self.back.draw(screen)
        s, rows = self._summary()
        # progress
        x, y, w = 140, 330, 1340
        pygame.draw.rect(screen, (24, 36, 60), (x, y, w, 14), border_radius=7)
        if self.total:
            pygame.draw.rect(screen, C.GREEN, (x, y, int(w * s["n"] / self.total), 14), border_radius=7)
        status = f"{s['n']} / {self.total or int(self.n.value)} matches" + ("  · running…" if self.running else "")
        A.text(screen, status, "semibold", 16, C.MUTED, (x, y + 24))
        # summary cards
        names = (self.a.value, self.b.value) if not rows else (rows[0]["a"], rows[0]["b"])
        for i, (side, col) in enumerate((("a", C.CYAN), ("b", C.AMBER))):
            cx = 140 + i * 680
            A.panel(screen, (cx, 390, 660, 250), fill=(10, 18, 34), edge=col, radius=18, alpha=230, width=2)
            wins = s["wa"] if side == "a" else s["wb"]
            A.text(screen, names[i], "bold", 30, C.INK, (cx + 30, 410))
            pct = 100 * wins / max(s["n"], 1)
            A.text(screen, f"{wins} wins", "display", 56, col, (cx + 30, 452), glow=col)
            A.text(screen, f"{pct:.0f}% win rate", "semibold", 18, C.MUTED, (cx + 30, 520))
            stats = [("avg score", f"{s['score_' + side]:.1f}"), ("balls / match", f"{s['balls_' + side]:.1f}"),
                     ("fouls / match", f"{s['fouls_' + side]:.2f}"), ("avg think", f"{s['think_' + side]:.2f} s"),
                     ("sims / match", f"{s['sims_' + side]:.0f}")]
            for k, (lab, val) in enumerate(stats):
                xx = cx + 340 + (k % 2) * 160
                yy = 420 + (k // 2) * 66
                A.text(screen, lab, "body", 14, C.MUTED, (xx, yy))
                A.text(screen, val, "bold", 24, C.INK, (xx, yy + 18))
        # win bar
        if s["n"]:
            x, y, w = 140, 666, 1340
            wa = w * s["wa"] / s["n"]
            wd = w * s["d"] / s["n"]
            pygame.draw.rect(screen, C.CYAN, (x, y, wa, 26), border_radius=6)
            pygame.draw.rect(screen, C.MUTED, (x + wa, y, wd, 26))
            pygame.draw.rect(screen, C.AMBER, (x + wa + wd, y, w - wa - wd, 26), border_radius=6)
            A.text(screen, f"draws {s['d']}", "body", 14, C.MUTED, (x + w / 2, y + 36), "midtop")
        # last games
        y = 730
        for r in rows[-4:][::-1]:
            col = C.CYAN if r["w"] == 0 else (C.AMBER if r["w"] == 1 else C.MUTED)
            A.text(screen, f"#{r['game']:>3}  {r['score_a']:>2} - {r['score_b']:<2}  winner: {r['winner']}  "
                           f"({r['secs']:.1f} s)", "body", 16, col, (140, y))
            y += 24
        self.save_btn.draw(screen)
        if self.saved:
            A.text(screen, "Saved " + os.path.basename(self.saved), "body", 14, C.GREEN, (1380, 830), "midtop")

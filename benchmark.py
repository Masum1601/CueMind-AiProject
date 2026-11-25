"""Command-line benchmark: many silent AI vs AI matches.

    python benchmark.py --a Minimax --b MCTS --games 100 --budget 0.6

--budget is the thinking time per shot in seconds (omit it to use the real
clock rule: up to 14% of the time left, between 0.25 s and 2.5 s).
Results go to benchmark_results.csv.
"""
import argparse
import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game import physics  # noqa: E402
from game.headless import play_match  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default="Minimax", choices=["Minimax", "MCTS", "Greedy"])
    ap.add_argument("--b", default="MCTS", choices=["Minimax", "MCTS", "Greedy"])
    ap.add_argument("--games", type=int, default=20)
    ap.add_argument("--budget", type=float, default=None)
    ap.add_argument("--out", default="benchmark_results.csv")
    args = ap.parse_args()

    physics.warmup()
    rows, wins = [], [0, 0, 0]
    t0 = time.time()
    for g in range(args.games):
        m = play_match(args.a, args.b, seed=1000 + g, budget=args.budget, breaker=g % 2)
        w = m.winner()
        wins[w if w >= 0 else 2] += 1
        rows.append({"game": g + 1, "score_a": m.scores[0], "score_b": m.scores[1],
                     "winner": {0: args.a, 1: args.b}.get(w, "draw"),
                     "fouls_a": m.fouls[0], "fouls_b": m.fouls[1],
                     "balls_a": m.balls_potted[0], "balls_b": m.balls_potted[1],
                     "clock_left_a": round(m.clocks[0], 2), "clock_left_b": round(m.clocks[1], 2)})
        print(f"game {g + 1:3d}: {m.scores[0]:2d}-{m.scores[1]:<2d}  {rows[-1]['winner']:8s}  "
              f"[{args.a} {wins[0]} | {args.b} {wins[1]} | draws {wins[2]}]")
    with open(args.out, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    n = max(len(rows), 1)
    print(f"\n{args.a}: {wins[0]} wins ({100 * wins[0] / n:.0f}%)   {args.b}: {wins[1]} wins ({100 * wins[1] / n:.0f}%)"
          f"   draws: {wins[2]}   ({time.time() - t0:.0f} s)  -> {args.out}")


if __name__ == "__main__":
    main()

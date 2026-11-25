# CueMind: 60-Second Rack Attack Duel

An 8-ball pool game where two AI players, **Minimax** and **Monte Carlo Tree Search**,
compete on one table. You can also play against them yourself.

CSE 3210 Artificial Intelligence Lab, Department of CSE, KUET
Azmaeen Nur Sajin (2207113) · Masumur Rahman Fokrul (2207114)

## Run it

```bash
pip install -r requirements.txt
python main.py
```

The first launch compiles the physics and AI kernels with numba (about 1–2 minutes,
one time only). After that the game starts in a few seconds.

Benchmark from the command line (no window):

```bash
python benchmark.py --a Minimax --b MCTS --games 100 --budget 0.6
```

## Rules (Rack Attack)

| Rule | Detail |
|---|---|
| Table | Both players share one table |
| Clock | 60 s each, runs only while that player thinks and aims |
| Points | Any ball 1, the 8-ball 3 |
| Foul | Scratch (cue ball pocketed) or no contact: −1 point, −5 s, rival gets ball-in-hand |
| Turn | Pot a ball without a foul and you shoot again |
| End | Table clear, or both clocks at zero. Higher score wins (tie: more clock left) |

## Controls

| Key / mouse | Action |
|---|---|
| Mouse | Aim |
| Hold left button + drag away | Set power, release to shoot |
| Right click | Cancel the stroke |
| Arrow keys | Fine aim (Shift = faster) |
| Up / Down, Space | Power, shoot |
| Click (ball in hand) | Place the cue ball (green ring = legal) |
| V | AI vision lines on/off |
| F | Ball speed 1x / 2x / 4x |
| P or Esc | Pause |
| M | Mute |
| F11 | Fullscreen |

## Where each algorithm is used

| Algorithm | File | Job in the game |
|---|---|---|
| Minimax + alpha-beta | `game/agents/minimax.py` | AI player: plans its shot and the rival's best reply. Shots are chance nodes (averaged over random execution error) with Star1 alpha-beta pruning |
| IDDFS | `minimax.py`, `shots.py` | Minimax deepens 1, 2, 3… shots until its time budget ends; kick shots try 0, 1, 2, 3 cushions |
| MCTS (UCB1) | `game/agents/mcts.py` | AI player: selection, expansion, simulation, backpropagation; plays the most-visited shot |
| A* | `game/planner.py` | Cheapest order to pot the next balls (cost = −log chance + time, admissible h = balls × time) |
| Greedy best-first | `game/agents/greedy.py` | The Easy AI, and shot ordering for the searches |
| BFS | `game/shots.py` (`bfs_place`) | Ball-in-hand: nearest legal spot from the ideal one |
| DFS / Depth-limited search | `game/shots.py` (`cushion_paths`) | Bank shots, depth = number of cushions (limit 2), mirror method |
| Bidirectional search | `game/shots.py` (`combo_shots`) | Combination shots: forward from the cue ball, backward from the pocket |
| Ghost ball | `game/shots.py` (`ghost_for`) | Aim point: Ghost = B − 2r·(P − B)/\|P − B\| |

## Code map

```
main.py              start the game
benchmark.py         silent AI vs AI matches -> CSV
game/config.py       table size, physics constants, rules, colours
game/physics.py      fixed-step engine (numba): friction, ball/cushion collisions, pockets
game/shots.py        candidate shots: direct, bank, kick, combo, safety, ball-in-hand
game/planner.py      A* run-out planner
game/rules.py        Rack Attack scoring, fouls, clocks, turns
game/agents/         Greedy, Minimax, MCTS and shared helpers
game/headless.py     matches without graphics
game/render/         3D ball shader, table art, cue, effects, sound, UI widgets
game/scenes/         menu, setup, match, results, benchmark, how-to
assets/images/       AI-generated art (Gemini) for menus and avatars
```

## Graphics notes

* Balls are drawn per pixel as lit spheres every frame they move: diffuse light, a
  sharp specular highlight and a cool rim reflection. The numbers and stripes rotate
  with the true rolling motion.
* Wood, cloth, cushions, chrome pockets and the cue are painted procedurally at start-up.
* All sounds are synthesized with numpy (no audio files).
* Menu, setup, results and benchmark backgrounds and the robot avatars are Gemini images.

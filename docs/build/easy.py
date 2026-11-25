import re
s = open("report.html", encoding="utf8").read()
# ---- plain styling
s = s.replace("--ink:#152033;", "--ink:#111111;").replace("--muted:#5B6B82;", "--muted:#555555;").replace("--line:#D5DDE8;", "--line:#CCCCCC;").replace("--tint:#F3F6FA;", "--tint:#F6F6F6;")
s = s.replace("h2 .n { color: var(--cyan); margin-right: 8px; }", "h2 .n { margin-right: 8px; }")
s = s.replace("h3 { font-size: 12pt; margin: 14px 0 5px; color: #0B5E73; }", "h3 { font-size: 12pt; margin: 14px 0 5px; color: #111111; }")
s = s.replace("th { background: #E7EEF6; color: #0B3F52;", "th { background: #EEEEEE; color: #111111;")
s = s.replace("color: #22D3EE; font-weight: 600; }", "color: #DDDDDD; font-weight: 600; }")
s = s.replace("font-size: 17pt; color: #F5A524;", "font-size: 17pt; color: #EEEEEE;")
s = s.replace("color: #0B5E73; font-size: 10pt; }", "color: #111111; font-size: 10pt; }")
s = s.replace(".flow .hot { border-color: var(--amber); }", ".flow .hot { border-color: #888888; }")
s = s.replace('font-family: "Bahnschrift", "Segoe UI", sans-serif; font-weight: 600;', 'font-family: "Segoe UI", Arial, sans-serif; font-weight: 700;')
s = s.replace("font-family: Bahnschrift, sans-serif; font-weight: 600; color: #111111", "font-family: \"Segoe UI\", Arial, sans-serif; font-weight: 700; color: #111111")
s = s.replace("pre { font-family: Consolas, \"Courier New\", monospace; font-size: 7.9pt;", "pre { font-family: Consolas, \"Courier New\", monospace; font-size: 8.6pt;")

CODES = [
# 1 physics
'''# one tiny time step (dt = 1/240 second)
for ball in moving_balls:
    ball.position = ball.position + ball.speed * dt      # move a little
    ball.speed = ball.speed * 0.995                     # friction slows it down

for a, b in pairs_of_balls:
    if distance(a, b) < 2 * radius:                     # two balls touch
        swap_speed_along_line(a, b)                     # equal balls trade speed

for ball in balls:
    if ball touches a cushion:   bounce it back (keeps 78% of its speed)
    if ball is near a pocket:    ball.potted = True''',
# 2 minimax
'''def minimax(state, depth, my_turn, alpha, beta):
    if depth == 0 or game_over(state):
        return evaluate(state)                  # score of this table

    if my_turn:                                 # MAX: I want the highest value
        best = -infinity
        for shot in good_shots(state):
            value = average_of_2_tries(state, shot, depth)   # shots can miss
            best = max(best, value)
            alpha = max(alpha, best)
            if alpha >= beta:
                break                           # alpha-beta: skip the rest
        return best
    else:                                       # MIN: opponent wants the lowest
        best = +infinity
        for shot in good_shots(state):
            value = average_of_2_tries(state, shot, depth)
            best = min(best, value)
            beta = min(beta, best)
            if alpha >= beta:
                break
        return best

# iterative deepening: try depth 1, then 2, then 3 ... until time is up
for depth in [1, 2, 3, 4]:
    if time_is_up(): break
    best_shot = the shot with the best minimax value at this depth''',
# 3 mcts
'''for i in range(many_times):                         # until the time is up
    node = root
    # 1. Selection: go down the tree using UCB1
    while node is fully expanded:
        node = child with the highest  Q + C * sqrt(ln(N_parent) / N)
    # 2. Expansion: add one new shot we have not tried
    node = node.add_new_child()
    # 3. Simulation: play the shot (with a little random error) and one more quick shot
    reward = play_out_and_score(node)            # number between 0 and 1
    # 4. Backpropagation: tell every node on the path how it went
    while node is not None:
        node.N = node.N + 1
        node.W = node.W + reward
        node = node.parent

best_shot = root child with the most visits''',
# 4 A*
'''open_list = [ (f=0, cue_position, balls_left, plan=[]) ]
while open_list:
    node = take the node with the smallest f      # f = g + h
    if no balls left in node:
        return node.plan                          # cheapest order found
    for ball in node.balls_left:
        cost = -log(pot_chance(ball)) + 0.15      # hard shot = high cost
        g = node.g + cost                         # cost so far
        h = (number of balls left - 1) * 0.15     # guess of cost still to pay
        add (g + h, new cue position, balls_left - ball, plan + [ball]) to open_list''',
# 5 greedy
'''best_score = -1
for shot in direct_pots:
    score = pot_chance(shot) * points(shot)     # h = p x points
    if score > best_score:
        best_score = score
        best_shot = shot
play(best_shot)                                 # no thinking about the future''',
# 6 BFS
'''queue = [ideal_spot]
visited = {ideal_spot}
while queue:
    spot = queue.pop(0)                         # first in, first out
    if spot is inside the table and touches no ball:
        return spot                             # nearest free spot
    for next_spot in the 8 neighbours of spot:
        if next_spot not in visited:
            visited.add(next_spot)
            queue.append(next_spot)''',
# 7 DLS
'''def find_bank(path_of_cushions, limit):
    if len(path_of_cushions) == limit:
        if the ball can travel this cushion path into the pocket:
            save this bank shot
        return
    for cushion in ["top", "bottom", "left", "right"]:
        find_bank(path_of_cushions + [cushion], limit)      # go one level deeper

find_bank([], limit=1)       # banks off 1 cushion
find_bank([], limit=2)       # banks off 2 cushions''',
# 8 IDDFS
'''for limit in [0, 1, 2, 3]:              # 0 cushions = straight line
    shots = find_kick(cue_ball, limit)  # depth-limited search (as above)
    if shots:
        return shots                    # stop at the fewest cushions''',
# 9 bidirectional
'''# search 1 (forward): balls the cue ball can hit directly
forward = [ball for ball in balls if line_is_clear(cue_ball, ball)]

# search 2 (backward): balls that can drop into a pocket
backward = [ball for ball in balls if line_is_clear(ball, pocket)]

# where the two searches meet = a combination shot
for A in forward:
    for B in backward:
        if A != B and line_is_clear(A, B):
            save combo shot: cue ball -> A -> B -> pocket''',
]
pres = list(re.finditer(r"<pre>.*?</pre>", s, flags=re.S))
assert len(pres) == 9, len(pres)
for m, code in reversed(list(zip(pres, CODES))):
    esc = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = s[:m.start()] + "<pre>" + esc + "</pre>" + s[m.end():]
open("report.html", "w", encoding="utf8").write(s)
print("ok")

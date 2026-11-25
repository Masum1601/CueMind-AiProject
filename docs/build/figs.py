"""Analysis figures (light = report, dark = slides) from trace.json."""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

MEDIA = r"F:\E\Downloads\Need2livewebsite\cuemind\docs\media"
T = json.load(open(os.path.join(MEDIA, "trace.json")))

THEMES = {
    "light": dict(bg="#FFFFFF", ink="#152033", muted="#5B6B82", line="#B8C4D6", box="#F3F6FA",
                  cyan="#0E8FAD", amber="#C77700", red="#C2410C", green="#15803D"),
    "dark": dict(bg="#070B16", ink="#EAF2FA", muted="#94A9C2", line="#3A4E70", box="#0E1628",
                 cyan="#22D3EE", amber="#F5A524", red="#F87171", green="#4ADE80"),
}
plt.rcParams["font.family"] = "Segoe UI"


def short(label):
    return (label.replace("into ", "→ ").replace("bottom", "btm").replace(", soft", " · soft")
            .replace(", medium", " · med").replace(", firm", " · firm"))


def box(ax, x, y, w, h, text, th, edge, fill=None, bold=False, size=9.5, tc=None):
    p = FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                       linewidth=1.6, edgecolor=edge, facecolor=fill or th["box"])
    ax.add_patch(p)
    ax.text(x, y, text, ha="center", va="center", fontsize=size, color=tc or th["ink"],
            fontweight="bold" if bold else "normal", linespacing=1.25)


def edge(ax, a, b, th, color=None, dashed=False):
    ax.plot([a[0], b[0]], [a[1], b[1]], color=color or th["line"], lw=1.4, ls="--" if dashed else "-", zorder=0)


def save(fig, name, th):
    fig.savefig(os.path.join(MEDIA, name), dpi=220, facecolor=th["bg"], bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


# ---------------------------------------------------------------- Minimax overview (IDDFS)
def minimax_overview(mode):
    th = THEMES[mode]
    d1 = dict(T["minimax"]["iddfs"][0]["values"])
    d2 = dict(T["minimax"]["iddfs"][1]["values"])
    best2 = T["minimax"]["iddfs"][1]["best"]
    best1 = T["minimax"]["iddfs"][0]["best"]
    labels = list(d1.keys())
    fig, ax = plt.subplots(figsize=(11, 4.4))
    fig.patch.set_facecolor(th["bg"]); ax.set_facecolor(th["bg"]); ax.axis("off")
    root = (5.5, 3.6)
    box(ax, *root, 3.2, 0.7, "ROOT · MAX\nMinimax to move", th, th["cyan"], bold=True)
    xs = [1.4, 4.1, 6.9, 9.6]
    for x, lab in zip(xs, labels):
        win = lab == best2
        edge(ax, (root[0], root[1] - 0.35), (x, 2.05), th, th["cyan"] if win else None)
        box(ax, x, 1.7, 2.5, 0.7, "CHANCE\n" + short(lab), th, th["cyan"] if win else th["line"], bold=win, size=9)
        c1 = th["amber"] if lab == best1 else th["muted"]
        c2 = th["cyan"] if win else th["muted"]
        ax.text(x, 0.95, f"depth 1:  {d1[lab]:+.2f}", ha="center", fontsize=10, color=c1,
                fontweight="bold" if lab == best1 else "normal")
        ax.text(x, 0.6, f"depth 2:  {d2[lab]:+.2f}", ha="center", fontsize=10, color=c2,
                fontweight="bold" if win else "normal")
    ax.text(5.5, 0.05, "Iterative deepening: depth 1 prefers the soft pot (amber); the deeper search sees the next "
                       "position and switches to medium power (cyan).", ha="center", fontsize=9.5, color=th["muted"])
    ax.set_xlim(0, 11); ax.set_ylim(-0.2, 4.1)
    save(fig, f"fig_minimax_overview_{mode}.png", th)


# ---------------------------------------------------------------- Minimax expanded best branch
def minimax_branch(mode):
    th = THEMES[mode]
    tree = T["minimax"]["tree"]
    kids = {}
    for n in tree:
        kids.setdefault(n["parent"], []).append(n)
    best = T["minimax"]["iddfs"][1]["best"]
    root = [n for n in tree if n["kind"] == "ROOT"][0]
    ch = [n for n in kids[root["id"]] if n["label"] == best][0]
    fig, ax = plt.subplots(figsize=(12, 6.2))
    fig.patch.set_facecolor(th["bg"]); ax.set_facecolor(th["bg"]); ax.axis("off")
    top = (6, 5.4)
    box(ax, *top, 3.6, 0.75, f"CHANCE · {short(best)}\naverage = {ch['value']:+.2f}", th, th["cyan"], bold=True)
    samples = kids.get(ch["id"], [])
    sx = [3.0, 9.0] if len(samples) == 2 else [6.0]
    for s, x in zip(samples, sx):
        edge(ax, (top[0], top[1] - 0.38), (x, 4.33), th)
        box(ax, x, 4.0, 3.2, 0.65, f"{s['label']}\nscore {s['score'][0]}–{s['score'][1]} · value {s['value']:+.2f}",
            th, th["line"], size=9)
        nxt = kids.get(s["id"], [])
        if not nxt:
            continue
        node = nxt[0]
        if node["kind"] == "LEAF":
            box(ax, x, 2.7, 2.2, 0.6, f"leaf eval {node['value']:+.2f}", th, th["line"], size=9)
            edge(ax, (x, 3.67), (x, 3.0), th)
            continue
        col = th["cyan"] if node["kind"] == "MAX" else th["amber"]
        edge(ax, (x, 3.67), (x, 3.05), th)
        cut = node.get("cut")
        box(ax, x, 2.7, 2.8, 0.7, f"{node['label']}\nvalue {node.get('value', 0):+.2f}", th, col, bold=True, size=9)
        reps = kids.get(node["id"], [])
        n = len(reps)
        for k, r in enumerate(reps):
            rx = x + (k - (n - 1) / 2) * 1.95
            edge(ax, (x, 2.35), (rx, 1.62), th)
            leaf = kids.get(kids.get(r["id"], [{}])[0].get("id"), [{}]) if kids.get(r["id"]) else [{}]
            lv = leaf[0].get("value") if leaf and leaf[0] else None
            txt = short(r["label"]) + f"\n{r.get('value', 0):+.2f}"
            box(ax, rx, 1.3, 1.85, 0.62, txt, th, th["line"], size=8.2)
        if cut:
            ax.text(x, 0.62, "✂ " + cut, ha="center", fontsize=9, color=th["red"], fontweight="bold")
    ax.text(6, 0.05, "Each shot is played twice with random cue error (chance node). After a pot the same player "
                     "moves again (MAX); after a miss the opponent moves (MIN).", ha="center", fontsize=9.3,
            color=th["muted"])
    ax.set_xlim(0, 12); ax.set_ylim(-0.2, 5.9)
    save(fig, f"fig_minimax_branch_{mode}.png", th)


# ---------------------------------------------------------------- MCTS tree
def mcts_tree(mode):
    th = THEMES[mode]
    M = T["mcts"]
    ch = M["children"]
    fig, ax = plt.subplots(figsize=(12, 5.2))
    fig.patch.set_facecolor(th["bg"]); ax.set_facecolor(th["bg"]); ax.axis("off")
    root = (6, 4.5)
    box(ax, *root, 3.4, 0.7, f"ROOT · {M['root_N']} visits\nC = {M['C']}", th, th["amber"], bold=True)
    n = len(ch)
    for k, c in enumerate(ch):
        x = 0.75 + k * (10.5 / (n - 1))
        best = k == 0
        edge(ax, (root[0], root[1] - 0.35), (x, 3.12), th, th["amber"] if best else None)
        txt = f"{short(c['action'])}\nN={c['N']}  Q={c['Q']:.2f}\nUCB1={c['ucb1']:.2f}"
        box(ax, x, 2.7, 1.42, 0.86, txt, th, th["amber"] if best else th["line"], bold=best, size=7.6)
    g = ch[0]["grand"]
    for j, (a, N, Q) in enumerate(g):
        gx = 0.75 + (j - 0.0) * 1.5
        edge(ax, (0.75, 2.27), (gx + 0.2, 1.42), th, dashed=True)
        box(ax, gx + 0.2, 1.1, 1.35, 0.6, f"reply rank {a + 1}\nN={N}  Q={Q:.2f}", th, th["line"], size=7.8)
    ax.text(6.8, 1.1, "Q = W / N  (average reward, 0–1)\nUCB1 = Q + C·√(ln N_parent / N)\n"
                      "Play the child with the most visits.", fontsize=10, color=th["ink"], va="center")
    ax.text(6, 0.2, f"{M['iterations']} iterations · {M['sims']} physics simulations · tree depth {M['depth']}",
            ha="center", fontsize=9.5, color=th["muted"])
    ax.set_xlim(0, 12); ax.set_ylim(0, 5.0)
    save(fig, f"fig_mcts_tree_{mode}.png", th)


def mcts_visits(mode):
    th = THEMES[mode]
    M = T["mcts"]
    H = M["history"]
    fig, ax = plt.subplots(figsize=(8.5, 4))
    fig.patch.set_facecolor(th["bg"]); ax.set_facecolor(th["bg"])
    order = sorted(range(len(M["labels"])), key=lambda a: -H[-1][a])
    cols = [th["amber"], th["cyan"], th["green"], th["muted"]]
    for i, a in enumerate(order[:4]):
        ax.plot(range(1, len(H) + 1), [h[a] for h in H], lw=2.4 if i == 0 else 1.6,
                color=cols[i], label=short(M["labels"][a]))
    for a in order[4:]:
        ax.plot(range(1, len(H) + 1), [h[a] for h in H], lw=1, color=th["line"])
    ax.set_xlabel("iteration", color=th["muted"]); ax.set_ylabel("visits N", color=th["muted"])
    for s in ax.spines.values():
        s.set_color(th["line"])
    ax.tick_params(colors=th["muted"])
    ax.grid(color=th["line"], alpha=0.35, lw=0.6)
    lg = ax.legend(frameon=False, fontsize=9)
    for t in lg.get_texts():
        t.set_color(th["ink"])
    save(fig, f"fig_mcts_visits_{mode}.png", th)


def heuristic(mode):
    th = THEMES[mode]
    rows = T["heuristic"][:8][::-1]
    fig, ax = plt.subplots(figsize=(8.5, 4))
    fig.patch.set_facecolor(th["bg"]); ax.set_facecolor(th["bg"])
    labs = [f"{r['ball']} → {r['pocket']}  (cut {r['cut']:.0f}°)" for r in rows]
    vals = [r["value"] for r in rows]
    cols = [th["cyan"] if r is rows[-1] else th["line"] for r in rows]
    ax.barh(labs, vals, color=cols, height=0.62)
    for i, r in enumerate(rows):
        ax.text(r["value"] + 0.015, i, f"p={r['p']:.2f}", va="center", fontsize=9, color=th["ink"])
    ax.set_xlim(0, max(vals) * 1.25)
    ax.set_xlabel("h = pot chance × points", color=th["muted"])
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(th["line"])
    ax.tick_params(colors=th["ink"], labelsize=9)
    save(fig, f"fig_heuristic_{mode}.png", th)


for mode in THEMES:
    minimax_overview(mode)
    minimax_branch(mode)
    mcts_tree(mode)
    mcts_visits(mode)
    heuristic(mode)
print("figures done")

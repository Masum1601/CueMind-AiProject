// CueMind presentation v2: cinematic, video-led, minimal boxes
const pptxgen = require("pptxgenjs");
const fs = require("fs");

const M = "F:/E/Downloads/Need2livewebsite/cuemind/docs/media/";
const V = M + "clips/";
const OUT = "F:/E/Downloads/Need2livewebsite/cuemind/docs/CueMind_Presentation_v2.pptx";
const T = JSON.parse(fs.readFileSync(M + "trace.json", "utf8").replace(/-?Infinity/g, "null"));

const BG = "070B16", INK = "F1F5F9", MUTED = "8C9DB5", DIM = "56677F", LINE = "1E2A40";
const CYAN = "22D3EE", AMBER = "F5A524", GREEN = "4ADE80", RED = "FB7185";
const HEAD = "Bahnschrift SemiBold", LABEL = "Bahnschrift", BODY = "Segoe UI";
const W = 13.333, H = 7.5;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "Azmaeen Nur Sajin, Masumur Rahman Fokrul";
pres.title = "CueMind: 60-Second Rack Attack Duel";
pres.theme = { headFontFace: HEAD, bodyFontFace: BODY };
pres.defineSlideMaster({
  title: "CONTENT", background: { color: BG },
  slideNumber: { x: 12.45, y: 6.95, w: 0.4, h: 0.3, fontFace: LABEL, fontSize: 10, color: DIM, align: "right" },
});
pres.defineSlideMaster({ title: "BLEED", background: { color: BG } });

let sec = "";
function slide(master, section) {
  if (section !== sec) { pres.addSection({ title: section }); sec = section; }
  return pres.addSlide({ masterName: master, sectionTitle: sec });
}
const tb = (o) => Object.assign({ margin: 0, isTextBox: true, valign: "top" }, o);
function label(s, text, x = 0.7, y = 0.55, color = CYAN) {
  s.addText(text.toUpperCase(), tb({ x, y, w: 8, h: 0.3, fontFace: LABEL, fontSize: 11, color, charSpacing: 4 }));
}
function heading(s, text, x = 0.7, y = 0.9, w = 11.9, size = 34) {
  s.addText(text, tb({ x, y, w, h: 0.9, fontFace: HEAD, fontSize: size, color: INK }));
}
function body(s, text, x, y, w, h, size = 15, color = MUTED, extra = {}) {
  s.addText(text, tb(Object.assign({ x, y, w, h, fontFace: BODY, fontSize: size, color, lineSpacingMultiple: 1.15 }, extra)));
}
function poster(file) { return "image/jpeg;base64," + fs.readFileSync(file.replace(".mp4", "_poster.jpg")).toString("base64"); }
function vid(s, file, x, y, w, h) { s.addMedia({ type: "video", path: file, x, y, w, h, cover: poster(file) }); }
function pic(s, file, x, y, w, h) { s.addImage({ path: file, x, y, w, h }); }
function stat(s, big, small, x, y, color, w = 2.7) {
  s.addText(big, tb({ x, y, w, h: 0.85, fontFace: HEAD, fontSize: 44, color }));
  body(s, small, x, y + 0.85, w, 0.8, 13, MUTED);
}
function rows(items, color = INK) { // [{t, c}]
  return items.map((it, i) => ({ text: it.t, options: Object.assign({ breakLine: i < items.length - 1, color: it.c || color }, it.o || {}) }));
}
function table(s, head, data, x, y, w, colW, accent = CYAN, size = 12) {
  const r = [head.map(t => ({ text: t, options: { bold: true, color: accent, fontFace: LABEL, fontSize: size - 1, border: [{ type: "none" }, { type: "none" }, { pt: 1, color: "33445E" }, { type: "none" }] } }))];
  data.forEach(row => r.push(row.map((t, j) => ({ text: String(t), options: { color: j === 0 ? INK : "C9D4E3", border: [{ type: "none" }, { type: "none" }, { pt: 0.5, color: LINE }, { type: "none" }] } }))));
  s.addTable(r, { x, y, w, colW, fontFace: BODY, fontSize: size, rowH: 0.4, margin: [0.03, 0.08, 0.03, 0.08] });
}

// 1 ─ Title: full-bleed gameplay loop
{
  const s = slide("BLEED", "Introduction");
  vid(s, V + "c_title.mp4", 0, 0, W, H);
  pic(s, M + "ov_left.png", 0, 0, W, H);
  label(s, "CSE 3210 · Artificial Intelligence Lab · KUET", 0.85, 1.55);
  s.addText("CueMind", tb({ x: 0.8, y: 2.05, w: 7, h: 1.4, fontFace: HEAD, fontSize: 80, color: INK }));
  s.addText("60-Second Rack Attack Duel", tb({ x: 0.85, y: 3.45, w: 7, h: 0.6, fontFace: LABEL, fontSize: 26, color: AMBER }));
  body(s, "Minimax and Monte Carlo Tree Search play pool against each other on one shared table.", 0.85, 4.15, 5.6, 0.9, 16, "B8C5D6");
  s.addText(rows([{ t: "Azmaeen Nur Sajin  ·  2207113" }, { t: "Masumur Rahman Fokrul  ·  2207114" }]),
    tb({ x: 0.85, y: 5.85, w: 6, h: 0.8, fontFace: BODY, fontSize: 14, color: INK, paraSpaceAfter: 3 }));
  s.addNotes("Introduce the team. The background is live footage from the game.");
}

// 2 ─ Overview: full-bleed AI vs AI loop
{
  const s = slide("BLEED", "Introduction");
  vid(s, V + "c_overview.mp4", 0, 0, W, H);
  pic(s, M + "ov_left.png", 0, 0, W, H);
  label(s, "01  The game", 0.8, 0.8);
  heading(s, "Two AIs share one table and one minute each", 0.8, 1.15, 5.6, 34);
  const pts = [["AI vs AI", "Minimax (cyan) and MCTS (amber) alternate shots; every shot changes the rival's table.", CYAN],
    ["Human vs AI", "Play Greedy, Minimax or MCTS with mouse aiming and drag-to-power.", AMBER],
    ["AI Vision", "Watch each AI search live: candidate shots, depth, visits and its A* plan.", GREEN]];
  pts.forEach(([h, t, c], i) => {
    s.addText(h, tb({ x: 0.85, y: 3.05 + i * 1.15, w: 5, h: 0.4, fontFace: HEAD, fontSize: 18, color: c }));
    body(s, t, 0.85, 3.45 + i * 1.15, 4.9, 0.7, 13, "B8C5D6");
  });
}

// 3 ─ Rules
{
  const s = slide("CONTENT", "Game");
  label(s, "02  Rules");
  heading(s, "Rack Attack: points against the clock");
  stat(s, "60 s", "Each player's clock. It runs only while that player thinks and aims.", 0.7, 2.2, CYAN);
  stat(s, "1 · 3", "Points for any ball · for the 8-ball. Pot one and shoot again.", 3.6, 2.2, AMBER);
  stat(s, "−1 · −5 s", "Foul (scratch or no contact). Rival gets ball-in-hand.", 0.7, 4.3, RED);
  stat(s, "0 : 00", "Match ends when the table is clear or both clocks run out.", 3.6, 4.3, GREEN);
  vid(s, V + "c_pot.mp4", 6.75, 1.95, 5.9, 3.32);
  body(s, "Because the table is shared, each pot also sets up (or spoils) the opponent's next shot.", 6.75, 5.45, 5.9, 0.8, 13);
}

// 4 ─ Physics: slow-motion break, full bleed
{
  const s = slide("BLEED", "Game");
  vid(s, V + "c_break_slow.mp4", 0, 0, W, H);
  pic(s, M + "ov_left.png", 0, 0, W, H);
  label(s, "03  Physics · 0.5x slow motion", 0.8, 0.8);
  heading(s, "One engine moves the balls and powers the AI", 0.8, 1.15, 5.4, 32);
  const f = [["240", "physics steps per second, fixed"], ["3 ms", "to simulate a full shot (numba)"], ["e = 0.95", "ball collisions swap speed along the impact line"], ["σ = 0.3°", "random cue error for every AI shot"]];
  f.forEach(([b, t], i) => {
    s.addText(b, tb({ x: 0.85, y: 3.0 + i * 0.92, w: 1.9, h: 0.5, fontFace: HEAD, fontSize: 24, color: i % 2 ? AMBER : CYAN }));
    body(s, t, 2.85, 3.1 + i * 0.92, 3.2, 0.6, 13, "C2CEDD");
  });
  s.addNotes("The AI simulates shots with the same engine the screen uses, so its predictions match what happens, apart from the random cue error.");
}

// 5 ─ Aiming: human clip + formulas
{
  const s = slide("CONTENT", "Game");
  label(s, "04  Aiming and heuristic");
  heading(s, "Ghost ball aiming and pot chance");
  vid(s, V + "c_human_aim.mp4", 0.7, 1.95, 7.2, 4.05);
  s.addText("Ghost = B − 2r·(P − B)/|P − B|", tb({ x: 8.3, y: 2.0, w: 4.4, h: 0.5, fontFace: "Cambria Math", fontSize: 19, color: AMBER }));
  body(s, "Aim the cue ball at the point behind target B so B leaves along the line to pocket P.", 8.3, 2.55, 4.4, 0.8, 13);
  s.addText("h = p × points", tb({ x: 8.3, y: 3.55, w: 4.4, h: 0.5, fontFace: "Cambria Math", fontSize: 19, color: CYAN }));
  body(s, "σ = d₁·σθ / (2r·cos cut)\nα = atan(w / d₂)\np = erf(α / σ√2) · (1 − ¼(cut/85°)⁴)", 8.3, 4.1, 4.4, 1.3, 13, "C2CEDD");
  body(s, "The chance a pot survives the same cue error the AIs play with.", 8.3, 5.45, 4.4, 0.6, 12);
}

// 6 ─ Architecture: framed AI-thinking footage + five stages
{
  const s = slide("CONTENT", "Algorithms");
  label(s, "05  How a turn works");
  heading(s, "One turn, five stages", 0.7, 0.9, 6.5, 34);
  vid(s, V + "c_think.mp4", 6.0, 0.55, 6.65, 3.74);
  body(s, "Live: MCTS thinks (clock ring draining, AI Vision counting), aims, and plays.", 6.0, 4.4, 6.65, 0.4, 11, DIM);
  body(s, "The agent runs in a background thread on a copy of the table. Its clock drains in real time; the budget is 14% of the time left (0.25–2.5 s).", 0.7, 2.0, 4.9, 1.6, 14);
  const st = [["Physics", "numba engine, 240 Hz"], ["Shot finder", "pots, banks, kicks, combos"], ["Agent", "Greedy · Minimax · MCTS"], ["Rules", "points, fouls, clocks"], ["Renderer", "3D balls, AI Vision"]];
  st.forEach(([h, t], i) => {
    const x = 0.7 + i * 2.42;
    s.addShape(pres.shapes.LINE, { x, y: 5.05, w: 2.2, h: 0, line: { color: i === 2 ? AMBER : "2B3B57", width: 2 } });
    s.addText(String(i + 1).padStart(2, "0"), tb({ x, y: 5.2, w: 1, h: 0.45, fontFace: HEAD, fontSize: 22, color: i === 2 ? AMBER : CYAN }));
    s.addText(h, tb({ x, y: 5.7, w: 2.3, h: 0.4, fontFace: HEAD, fontSize: 17, color: INK }));
    body(s, t, x, 6.1, 2.2, 0.6, 12);
  });
}

// 7 ─ Algorithm map (typographic)
{
  const s = slide("CONTENT", "Algorithms");
  label(s, "06  Algorithms");
  heading(s, "Every lab algorithm has a job in the game");
  const A = [["Minimax + α-β", "AI player 1 · plans its shot and the rival's best reply", CYAN], ["MCTS · UCB1", "AI player 2 · learns from simulated play-outs", AMBER],
    ["A*", "Cheapest order to pot the next balls", INK], ["Greedy best-first", "Easy AI · orders shots for pruning", INK],
    ["BFS", "Ball-in-hand: nearest legal spot", INK], ["DFS / DLS", "Bank shots, one level per cushion", INK],
    ["IDDFS", "Kick shots and Minimax time control", INK], ["Bidirectional", "Combinations: from cue and from pocket", INK]];
  A.forEach(([h, t, c], i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.7 + col * 6.15, y = 2.05 + row * 1.15;
    s.addShape(pres.shapes.LINE, { x, y: y - 0.12, w: 5.75, h: 0, line: { color: LINE, width: 1 } });
    s.addText(h, tb({ x, y, w: 2.6, h: 0.45, fontFace: HEAD, fontSize: 19, color: c === INK ? INK : c }));
    body(s, t, x + 2.65, y + 0.05, 3.1, 0.8, 13);
  });
}

// 8-10 ─ Full gameplay videos
function fullVideo(title, lab, file, note, secName) {
  const s = slide("CONTENT", secName);
  label(s, lab);
  heading(s, title, 0.7, 0.9, 11.9, 30);
  vid(s, file, 2.4, 1.7, 8.53, 4.8);
  body(s, note, 2.4, 6.65, 8.53, 0.5, 12, MUTED, { align: "center" });
}
fullVideo("Full AI vs AI match", "07  Gameplay · 4x speed", M + "ai_vs_ai_4x_fs.mp4", "MCTS 11 – Minimax 6. Watch the candidate lines, the A* badges and the draining clock rings.", "Gameplay");
fullVideo("Human vs AI", "08  Gameplay · 2x speed", M + "human_vs_ai_2x_fs.mp4", "Mouse aims, drag back sets power; the ghost ball and cut angle guide the shot. Minimax replies.", "Gameplay");
{
  const s = slide("CONTENT", "Gameplay");
  label(s, "09  Interface");
  heading(s, "Menus, modes and benchmark", 0.7, 0.9, 11.9, 30);
  vid(s, M + "ui_tour_fs.mp4", 0.7, 1.85, 7.4, 4.16);
  pic(s, M + "13_benchmark.png", 8.4, 1.85, 4.23, 2.38);
  pic(s, M + "12_ball_in_hand.png", 8.4, 4.4, 2.05, 1.153);
  pic(s, M + "10_results.png", 10.58, 4.4, 2.05, 1.153);
  body(s, "Benchmark runs silent matches and saves a CSV · ball-in-hand shows a legal (green) ring · results list balls, fouls and think time.", 0.7, 6.25, 11.9, 0.6, 12);
}

// 11 ─ Scenario
{
  const s = slide("CONTENT", "Decision analysis");
  label(s, "10  Decision analysis · scenario");
  heading(s, "One position, traced through every algorithm");
  pic(s, M + "scenario.png", 0.7, 1.95, 7.6, 4.27);
  const k = T.kinds;
  stat(s, String(k.direct), "direct pots (ghost ball)", 8.75, 1.95, CYAN, 1.9);
  stat(s, String(k.bank), "bank shots (DLS)", 10.75, 1.95, AMBER, 1.9);
  stat(s, String(k.combo), "combination (bidirectional)", 8.75, 3.7, GREEN, 1.9);
  stat(s, String(k.safety), "safeties", 10.75, 3.7, INK, 1.9);
  body(s, "Minimax to move, 15 balls left. A–D: the four best pots by heuristic. White numbers: the A* order.", 8.75, 5.45, 3.9, 0.9, 12);
}

// 12 ─ Heuristic
{
  const s = slide("CONTENT", "Decision analysis");
  label(s, "11  Step 1 · heuristic");
  heading(s, "Scoring each pot: h = p × points");
  table(s, ["", "Ball → pocket", "d₁", "d₂", "cut", "σ", "α", "p"], T.heuristic.slice(0, 4).map((r, i) =>
    ["ABCD"[i], `${r.ball} → ${r.pocket}`, r.d1.toFixed(1), r.d2.toFixed(1), r.cut.toFixed(1) + "°", r.sigma_deg.toFixed(2) + "°", r.alpha_deg.toFixed(2) + "°", r.p.toFixed(3)]),
    0.7, 2.0, 7.4, [0.4, 2.0, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8]);
  s.addText("Shot A, step by step", tb({ x: 0.7, y: 4.35, w: 7, h: 0.4, fontFace: HEAD, fontSize: 18, color: AMBER }));
  body(s, "σ = 50.5 × 0.30° / (2 × 11.5 × cos 33.9°) = 0.79°\nα = atan(w / 145.6) = 4.91°\np = erf(4.91 / (0.79·√2)) × 0.994 = 0.994  →  h = 0.994", 0.7, 4.85, 7.4, 1.4, 14, "C9D4E3");
  pic(s, M + "fig_heuristic_dark.png", 8.45, 2.0, 4.2, 1.98);
  body(s, "Greedy plays shot A right here. A short cue-to-ghost distance keeps the error σ small, so the nearby ball 2 ranks first.", 8.45, 4.35, 4.2, 1.5, 13);
}

// 13 ─ A*
{
  const s = slide("CONTENT", "Decision analysis");
  label(s, "12  Step 2 · A*");
  heading(s, "A* plans the cheapest run-out order");
  T.astar.plan.forEach(([b, p], i) => {
    const x = 0.7 + i * 2.45;
    s.addText(String(b), tb({ x, y: 1.95, w: 0.9, h: 0.75, fontFace: HEAD, fontSize: 40, color: i === 0 ? CYAN : INK }));
    body(s, `${i + 1}${["st", "nd", "rd", "th", "th"][i]} · ${p}`, x, 2.75, 2.2, 0.4, 12);
  });
  table(s, ["Step", "Path so far", "g", "h", "f = g + h"], T.astar.log.slice(0, 6).map(r =>
    [r.step, r.path.length ? r.path.join(", ").replace(/->/g, " → ") : "start", r.g.toFixed(3), r.h.toFixed(2), r.f.toFixed(3)]),
    0.7, 3.5, 7.9, [0.6, 4.3, 1.0, 0.8, 1.2]);
  body(s, `Cost of a pot = −ln p + ${T.astar.time_cost}\nh = balls left × ${T.astar.time_cost}\n\nEvery pot costs at least the time term, so h never overestimates: admissible.\n\nTotal ${T.astar.cost} after ${T.astar.expansions} expansions.`, 9.0, 3.5, 3.7, 3.0, 14, "C9D4E3");
}

// 14 ─ Minimax IDDFS
{
  const s = slide("CONTENT", "Decision analysis");
  label(s, "13  Step 3 · Minimax");
  heading(s, "Deeper search changes Minimax's mind");
  pic(s, M + "fig_minimax_overview_dark.png", 0.7, 1.95, 8.0, 3.2);
  const d = T.minimax.iddfs;
  stat(s, "+1.63", `Depth 1 · best: soft power\n${d[0].sims} simulations`, 9.2, 1.95, AMBER, 3.4);
  stat(s, "+2.79", `Depth 2 · best: medium power\n${d[1].sims} simulations · ${d[1].pruned} pruned`, 9.2, 3.75, CYAN, 3.4);
  body(s, "Each root shot is a chance node played twice with random cue error. Leaf value = score lead + 0.9 × next pot chance + 0.025 × clock lead. At depth 2 Minimax sees that medium power leaves ball 15 pottable, so it switches.", 0.7, 5.45, 11.9, 1.2, 13);
}

// 15 ─ Minimax branch
{
  const s = slide("CONTENT", "Decision analysis");
  label(s, "14  Step 3 · inside the tree");
  heading(s, "The winning branch and an alpha-beta cut");
  pic(s, M + "fig_minimax_branch_dark.png", 0.7, 1.9, 7.9, 4.09);
  s.addText("Alpha-beta cut", tb({ x: 9.0, y: 1.95, w: 3.7, h: 0.4, fontFace: HEAD, fontSize: 18, color: RED }));
  body(s, "Searching '9 → bottom-right' after α = 2.79 was known: the shot missed, the opponent moved (MIN), and its first reply already fell below α. The other 2 replies were skipped.", 9.0, 2.45, 3.7, 2.2, 13, "C9D4E3");
  s.addText("Star1 for chance nodes", tb({ x: 9.0, y: 4.65, w: 3.7, h: 0.4, fontFace: HEAD, fontSize: 18, color: CYAN }));
  body(s, "Stop sampling when (sum + remaining · Vmax) / n ≤ α.", 9.0, 5.1, 3.7, 0.9, 13, "C9D4E3");
}

// 16 ─ MCTS tree
{
  const s = slide("CONTENT", "Decision analysis");
  label(s, "15  Step 4 · MCTS", 0.7, 0.55, AMBER);
  heading(s, "MCTS grows its tree with UCB1");
  pic(s, M + "fig_mcts_tree_dark.png", 0.7, 1.9, 8.3, 3.92);
  const c = T.mcts.children[0];
  s.addText("UCB1 = Q + C·√(ln N / n)", tb({ x: 9.35, y: 1.95, w: 3.4, h: 0.45, fontFace: "Cambria Math", fontSize: 17, color: AMBER }));
  body(s, `Best child: ${c.action}\nQ = ${c.W} / ${c.N} = ${c.Q}\n1.4·√(ln ${T.mcts.root_N} / ${c.N}) = ${c.explore}\nUCB1 = ${c.ucb1}\n\nAll children finish near 1.30: exploration and exploitation in balance.`, 9.35, 2.55, 3.4, 3.3, 13, "C9D4E3");
  body(s, "Selection → Expansion → Simulation (noisy shot + greedy play-out) → Backpropagation of a 0–1 reward. The most-visited shot is played.", 0.7, 6.05, 11.9, 0.7, 13);
}

// 17 ─ MCTS visits
{
  const s = slide("CONTENT", "Decision analysis");
  label(s, "16  Step 4 · iterations", 0.7, 0.55, AMBER);
  heading(s, "Visits flow to the shots that win play-outs");
  pic(s, M + "fig_mcts_visits_dark.png", 0.7, 1.9, 6.8, 3.2);
  table(s, ["#", "Root shot selected", "Reward", "N", "Q"], T.mcts.log.slice(0, 8).map(r => [r.iter, r.root_action, r.reward.toFixed(3), r.N, r.Q.toFixed(3)]),
    7.85, 1.9, 4.8, [0.4, 2.55, 0.75, 0.4, 0.7], AMBER, 11);
  body(s, `${T.mcts.iterations} iterations · ${T.mcts.sims} physics simulations · tree depth ${T.mcts.depth}. Early iterations open new shots in heuristic order; UCB1 then returns to the shots whose play-outs score best.`, 0.7, 5.45, 6.8, 1.2, 13);
}

// 18 ─ Comparison
{
  const s = slide("CONTENT", "Decision analysis");
  label(s, "17  Comparison");
  heading(s, "Same position, three decisions");
  const C3 = [["Greedy", "soft", "Highest one-shot chance (0.994). No look-ahead.", GREEN],
    ["Minimax", "medium", "Depth 2 sees the follow-up pot on ball 15: 2.79 beats 1.53.", CYAN],
    ["MCTS", "soft", "23 of 160 visits, Q = 0.65 from noisy play-outs.", AMBER]];
  C3.forEach(([h, p, t, c], i) => {
    const x = 0.7 + i * 4.1;
    s.addText(h, tb({ x, y: 2.1, w: 3.7, h: 0.5, fontFace: HEAD, fontSize: 22, color: c }));
    s.addText([{ text: "2 → bottom side, ", options: { color: INK } }, { text: p, options: { color: c } }], tb({ x, y: 2.7, w: 3.8, h: 0.5, fontFace: HEAD, fontSize: 20 }));
    body(s, t, x, 3.35, 3.6, 1.2, 14);
  });
  s.addShape(pres.shapes.LINE, { x: 0.7, y: 4.75, w: 11.9, h: 0, line: { color: LINE, width: 1 } });
  body(s, "All three pot ball 2 into the bottom side pocket: the heuristic is sound. They differ on power: only Minimax's exhaustive depth-2 search plans where the cue ball stops for the next shot.", 0.7, 5.0, 11.9, 1.2, 16, "C9D4E3");
}

// 19 ─ Benchmark
{
  const s = slide("CONTENT", "Results");
  label(s, "18  Results");
  heading(s, "40 silent matches, 0.6 s per shot");
  pic(s, M + "fig_benchmark_dark.png", 0.7, 1.95, 7.4, 3.13);
  stat(s, "11 – 9", "MCTS vs Minimax · 20 matches", 8.6, 1.95, AMBER, 4);
  stat(s, "9 – 1", "Minimax vs Greedy · 10 matches", 8.6, 3.55, CYAN, 4);
  stat(s, "7 – 3", "MCTS vs Greedy · 10 matches", 8.6, 5.15, AMBER, 4);
  body(s, "Both search agents beat the greedy baseline. MCTS edges Minimax (avg score 9.2 vs 7.6); fouls stay at or below 0.2 per match for every agent.", 0.7, 5.4, 7.4, 1.2, 13);
}

// 20 ─ Closing: full-bleed loop
{
  const s = slide("BLEED", "Results");
  vid(s, V + "c_end.mp4", 0, 0, W, H);
  pic(s, M + "ov_dim.png", 0, 0, W, H);
  s.addText("Thank you", tb({ x: 0.8, y: 2.3, w: 11.7, h: 1.3, fontFace: HEAD, fontSize: 66, color: INK, align: "center" }));
  s.addText("Questions and live demo", tb({ x: 0.8, y: 3.6, w: 11.7, h: 0.6, fontFace: LABEL, fontSize: 24, color: AMBER, align: "center" }));
  body(s, "Azmaeen Nur Sajin · 2207113     Masumur Rahman Fokrul · 2207114     CSE, KUET", 0.8, 6.3, 11.7, 0.4, 13, "B8C5D6", { align: "center" });
}

pres.writeFile({ fileName: OUT }).then(f => console.log("wrote", f));

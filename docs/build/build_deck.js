// CueMind presentation (20 slides, dark theme, embedded gameplay videos)
const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

const M = "F:/E/Downloads/Need2livewebsite/cuemind/docs/media/";
const ART = "F:/E/Downloads/Need2livewebsite/cuemind/assets/images/";
const OUT = "F:/E/Downloads/Need2livewebsite/cuemind/docs/CueMind_Presentation.pptx";
const T = JSON.parse(fs.readFileSync(M + "trace.json", "utf8").replace(/-?Infinity/g, "null"));

const BG = "0A1020", PANEL = "111B33", EDGE = "2A3B5C", INK = "EAF2FA", MUTED = "9AB0C8";
const CYAN = "22D3EE", AMBER = "F5A524", GREEN = "4ADE80", RED = "F87171";
const HEAD = "Bahnschrift", BODY = "Segoe UI";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.author = "Azmaeen Nur Sajin, Masumur Rahman Fokrul";
pres.title = "CueMind: 60-Second Rack Attack Duel";
pres.theme = { headFontFace: HEAD, bodyFontFace: BODY };

pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: BG },
  objects: [
    { text: { text: "CueMind · CSE 3210 AI Lab · KUET", options: { x: 0.6, y: 7.02, w: 6, h: 0.3, fontFace: BODY, fontSize: 10, color: "5F7593" } } },
  ],
  slideNumber: { x: 12.3, y: 7.0, w: 0.5, h: 0.3, fontFace: BODY, fontSize: 10, color: "5F7593", align: "right" },
});
pres.defineSlideMaster({ title: "FULL", background: { color: BG } });

const W = 13.333;
let sectionTitle = "";
function add(master, section) {
  if (section && section !== sectionTitle) { pres.addSection({ title: section }); sectionTitle = section; }
  return pres.addSlide({ masterName: master, sectionTitle: sectionTitle });
}
function title(s, text, kicker) {
  if (kicker) s.addText(kicker.toUpperCase(), { x: 0.6, y: 0.38, w: 10, h: 0.3, fontFace: BODY, fontSize: 12, bold: true, color: CYAN, charSpacing: 3, margin: 0, isTextBox: true });
  s.addText(text, { x: 0.6, y: 0.68, w: 12.1, h: 0.75, fontFace: HEAD, fontSize: 32, color: INK, margin: 0, isTextBox: true });
}
function card(s, x, y, w, h, fill = PANEL, line = EDGE) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { color: line, width: 1 }, rectRadius: 0.12 });
}
function img(s, file, x, y, w, h, frame = true) {
  if (frame) s.addShape(pres.shapes.RECTANGLE, { x: x - 0.03, y: y - 0.03, w: w + 0.06, h: h + 0.06, fill: { color: EDGE }, line: { color: EDGE, width: 0.5 } });
  s.addImage({ path: file, x, y, w, h });
}
function bullets(s, items, x, y, w, h, size = 15, color = INK) {
  s.addText(items.map((t, i) => ({ text: t, options: { bullet: { indent: 16 }, breakLine: i < items.length - 1, paraSpaceAfter: 7 } })),
    { x, y, w, h, fontFace: BODY, fontSize: size, color, valign: "top", margin: 0, isTextBox: true });
}
function para(s, text, x, y, w, h, size = 14, color = MUTED, opts = {}) {
  s.addText(text, { x, y, w, h, fontFace: BODY, fontSize: size, color, valign: "top", margin: 0, isTextBox: true, ...opts });
}
function video(s, file, poster, x, y, w, h) {
  s.addShape(pres.shapes.RECTANGLE, { x: x - 0.04, y: y - 0.04, w: w + 0.08, h: h + 0.08, fill: { color: EDGE }, line: { color: EDGE, width: 0.5 } });
  const cover = "image/jpeg;base64," + fs.readFileSync(poster).toString("base64");
  s.addMedia({ type: "video", path: file, x, y, w, h, cover });
}

// 1 ─ Title
{
  const s = add("FULL", "Introduction");
  s.addImage({ path: M + "gem_cover.jpg", x: 0, y: 0, w: W, h: 7.5 });
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 7.6, h: 7.5, fill: { color: BG, transparency: 25 }, line: { color: BG, transparency: 100 } });
  s.addText("CSE 3210 · ARTIFICIAL INTELLIGENCE LAB", { x: 0.7, y: 0.8, w: 7, h: 0.35, fontFace: BODY, fontSize: 13, bold: true, color: CYAN, charSpacing: 4, margin: 0, isTextBox: true });
  s.addText("CueMind", { x: 0.7, y: 1.6, w: 7, h: 1.3, fontFace: HEAD, fontSize: 72, bold: true, color: INK, margin: 0, isTextBox: true });
  s.addText("60-Second Rack Attack Duel", { x: 0.7, y: 2.9, w: 7, h: 0.6, fontFace: HEAD, fontSize: 28, color: AMBER, margin: 0, isTextBox: true });
  s.addText("Two AI players on one pool table: Minimax vs Monte Carlo Tree Search", { x: 0.7, y: 3.55, w: 6.4, h: 0.8, fontFace: BODY, fontSize: 16, color: MUTED, margin: 0, isTextBox: true });
  s.addText([
    { text: "Azmaeen Nur Sajin", options: { bold: true, color: INK } }, { text: "   Roll 2207113", options: { color: MUTED, breakLine: true } },
    { text: "Masumur Rahman Fokrul", options: { bold: true, color: INK } }, { text: "   Roll 2207114", options: { color: MUTED, breakLine: true } },
    { text: "Department of CSE, KUET", options: { color: MUTED } },
  ], { x: 0.7, y: 5.2, w: 6.5, h: 1.3, fontFace: BODY, fontSize: 15, margin: 0, isTextBox: true, paraSpaceAfter: 4 });
  s.addNotes("Introduce the team and the project: an 8-ball pool variant where two AI agents, Minimax and MCTS, compete on one shared table.");
}

// 2 ─ Overview
{
  const s = add("CONTENT", "Introduction");
  title(s, "Two AIs, one table, one minute each", "Game overview");
  img(s, M + "06b_think_late.png", 0.6, 1.7, 7.6, 4.275);
  para(s, "Minimax is thinking: its candidate shots are drawn on the table, its clock ring is draining, and the AI Vision panel lists depth, simulations and the best shots.", 0.6, 6.15, 7.6, 0.7, 12);
  const items = [
    ["AI vs AI duel", "Minimax (cyan) and MCTS (amber) take turns on a shared table, so every shot changes the rival's position."],
    ["Human vs AI", "Play against Greedy (Easy), Minimax (Medium) or MCTS (Hard) with mouse aiming and drag-to-power."],
    ["AI Vision", "A live panel shows each AI's search: simulations, depth, pruning, visits and its A* run-out plan."],
  ];
  items.forEach(([h, t], i) => {
    const y = 1.7 + i * 1.47;
    card(s, 8.55, y, 4.2, 1.3);
    s.addText(h, { x: 8.8, y: y + 0.15, w: 3.8, h: 0.35, fontFace: HEAD, fontSize: 17, color: i === 1 ? AMBER : CYAN, margin: 0, isTextBox: true });
    para(s, t, 8.8, y + 0.52, 3.8, 0.75, 12, MUTED);
  });
  s.addNotes("The match screen: player cards with clock rings, the rack tracker and time bar at the top, the table, and the AI Vision panel on the right.");
}

// 3 ─ Rules
{
  const s = add("CONTENT", "Game");
  title(s, "Rack Attack rules", "Rules");
  const stats = [["60 s", "Own clock", "Runs only while that player thinks and aims", CYAN], ["1 / 3", "Points", "Any ball 1 point, the 8-ball 3 points", AMBER],
    ["−1, −5 s", "Foul", "Scratch or no contact; rival gets ball-in-hand", RED], ["Again", "Pot = shoot again", "Miss or foul passes the turn", GREEN]];
  stats.forEach(([big, h, t, c], i) => {
    const x = 0.6 + i * 3.1;
    card(s, x, 1.75, 2.85, 2.35);
    s.addText(big, { x: x + 0.25, y: 1.95, w: 2.4, h: 0.75, fontFace: HEAD, fontSize: 36, bold: true, color: c, margin: 0, isTextBox: true });
    s.addText(h, { x: x + 0.25, y: 2.75, w: 2.4, h: 0.4, fontFace: HEAD, fontSize: 16, color: INK, margin: 0, isTextBox: true });
    para(s, t, x + 0.25, 3.18, 2.4, 0.8, 12);
  });
  img(s, M + "05b_break.png", 0.6, 4.45, 4.0, 2.25);
  img(s, M + "09_pot.png", 4.85, 4.45, 4.0, 2.25);
  para(s, "The match ends when the table is clear or both clocks reach zero. The higher score wins; a tie goes to the player with more clock left.",
    9.15, 4.5, 3.6, 2.2, 14, INK);
  s.addNotes("Why Rack Attack: thinking costs clock time, which makes the time budget of each algorithm part of the game.");
}

// 4 ─ Physics
{
  const s = add("CONTENT", "Game");
  title(s, "One physics engine for the screen and the AI", "Mechanics");
  bullets(s, [
    "Fixed time step dt = 1/240 s, compiled with numba (about 3 ms per full shot)",
    "Friction: speed drops by (120 + 0.55·v)·dt each step",
    "Ball–ball: equal masses swap velocity along the line of centres (e = 0.95), backed up to the exact contact time",
    "Cushions and pocket jaws are line segments; the normal speed is reflected and keeps 78%",
    "A ball inside a pocket's capture radius is potted",
    "AI shots get random error: σ = 0.30° in angle, 2.5% in power",
  ], 0.6, 1.75, 6.2, 4.8, 15);
  img(s, M + "08_roll.png", 7.1, 1.75, 5.65, 3.18);
  card(s, 7.1, 5.2, 5.65, 1.45);
  para(s, "Because the AI simulates with the same engine the screen uses, a shot the AI predicts is the shot that happens, apart from the execution noise.", 7.35, 5.35, 5.2, 1.2, 13, INK);
  s.addNotes("The same deterministic engine drives rendering and the AI's mental simulations.");
}

// 5 ─ Ghost ball + heuristic
{
  const s = add("CONTENT", "Game");
  title(s, "Aiming: ghost ball and pot chance", "Mechanics");
  card(s, 0.6, 1.75, 6.0, 1.25);
  s.addText("Ghost = B − 2r · (P − B) / |P − B|", { x: 0.85, y: 1.95, w: 5.6, h: 0.45, fontFace: "Cambria Math", fontSize: 20, color: AMBER, margin: 0, isTextBox: true });
  para(s, "Aim the cue ball at the ghost point behind the target B so the target leaves along the line to pocket P.", 0.85, 2.42, 5.6, 0.55, 12);
  card(s, 0.6, 3.2, 6.0, 2.05);
  s.addText("h = p × points", { x: 0.85, y: 3.35, w: 5.6, h: 0.4, fontFace: "Cambria Math", fontSize: 20, color: CYAN, margin: 0, isTextBox: true });
  para(s, "σ = d₁·σθ / (2r·cos cut)     α = atan(w / d₂)\np = erf(α / (σ√2)) · (1 − ¼·(cut/85°)⁴)\nd₁ = cue to ghost, d₂ = ball to pocket, w = usable pocket half-width", 0.85, 3.85, 5.6, 1.3, 12, INK);
  para(s, "Each pot gets 3 power levels (soft, medium, firm). Banks, kicks, combinations and safeties are added by the searches on slide 7.", 0.6, 5.5, 6.0, 1.0, 13);
  img(s, M + "11b_human_power.png", 7.0, 1.75, 5.75, 3.23);
  para(s, "Human view: dashed line to the ghost ball, object-ball path, cut angle and power bar.", 7.0, 5.15, 5.75, 0.6, 12);
  s.addNotes("The heuristic is the probability the pot works under the same execution noise the AIs use.");
}

// 6 ─ Architecture
{
  const s = add("CONTENT", "Algorithms");
  title(s, "How a turn flows through the system", "Architecture");
  const steps = [["Physics", "numba engine, 240 Hz"], ["Shot finder", "direct, bank, kick, combo, safety"], ["Agent", "Greedy · Minimax · MCTS"], ["Rules", "points, fouls, clocks"], ["Renderer", "3D balls, AI Vision, sound"]];
  steps.forEach(([h, t], i) => {
    const x = 0.6 + i * 2.5;
    card(s, x, 2.0, 2.2, 1.6, PANEL, i === 2 ? AMBER : EDGE);
    s.addText(String(i + 1).padStart(2, "0"), { x: x + 0.2, y: 2.12, w: 1, h: 0.35, fontFace: HEAD, fontSize: 14, color: i === 2 ? AMBER : CYAN, margin: 0, isTextBox: true });
    s.addText(h, { x: x + 0.2, y: 2.5, w: 1.9, h: 0.4, fontFace: HEAD, fontSize: 18, color: INK, margin: 0, isTextBox: true });
    para(s, t, x + 0.2, 2.95, 1.85, 0.6, 11);
    if (i < 4) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + 2.23, y: 2.65, w: 0.24, h: 0.3, fill: { color: "3A4E70" }, line: { color: "3A4E70" } });
  });
  card(s, 0.6, 4.1, 12.15, 1.95);
  bullets(s, [
    "The agent runs in a background thread; its clock drains in real time while it thinks.",
    "Thinking budget per shot: 14% of the time left (0.25 s to 2.5 s), so the AIs speed up when time is short.",
    "After the shot, the rules module scores it and decides the next turn; the match ends when the table is clear or both clocks reach zero.",
  ], 0.9, 4.35, 11.6, 2.2, 15);
  s.addNotes("Agents never touch the live table: they search on copies (snapshots).");
}

// 7 ─ Algorithm map
{
  const s = add("CONTENT", "Algorithms");
  title(s, "Every lab algorithm has a job in the game", "Algorithms");
  const A = [
    ["Minimax + α-β", "AI player 1: plans its shot and the rival's best reply", CYAN],
    ["MCTS · UCB1", "AI player 2: plays out simulated games", AMBER],
    ["A*", "Cheapest order to pot the next balls", INK],
    ["Greedy best-first", "Easy AI and shot ordering for pruning", INK],
    ["BFS", "Ball-in-hand: nearest legal spot on a grid", INK],
    ["DFS / DLS", "Bank shots: one level per cushion, limit 2", INK],
    ["IDDFS", "Kick shots (0→3 cushions) and Minimax time control", INK],
    ["Bidirectional", "Combinations: forward from cue, backward from pocket", INK],
  ];
  A.forEach(([h, t, c], i) => {
    const x = 0.6 + (i % 4) * 3.1, y = 1.75 + Math.floor(i / 4) * 2.45;
    card(s, x, y, 2.85, 2.2, PANEL, c === INK ? EDGE : c);
    s.addText(h, { x: x + 0.22, y: y + 0.25, w: 2.45, h: 0.5, fontFace: HEAD, fontSize: 18, color: c === INK ? CYAN : c, margin: 0, isTextBox: true });
    para(s, t, x + 0.22, y + 0.85, 2.45, 1.2, 13, INK);
  });
  s.addNotes("Minimax and MCTS are the two competing players; the other searches find and rank the shots they consider.");
}

// 8-10 ─ Videos
{
  const s = add("CONTENT", "Gameplay");
  title(s, "Full AI vs AI match at 4x speed", "Gameplay video");
  video(s, M + "ai_vs_ai_4x.mp4", M + "ai_vs_ai_4x_poster.jpg", 0.6, 1.65, 8.9, 5.006);
  card(s, 9.8, 1.65, 2.95, 5.0);
  s.addText("What to watch", { x: 10.0, y: 1.85, w: 2.6, h: 0.4, fontFace: HEAD, fontSize: 17, color: CYAN, margin: 0, isTextBox: true });
  bullets(s, ["The break and the 3-2-1 intro", "Faint lines: shots the AI is weighing", "Numbered badges: A* plan", "Clock rings drain while thinking", "Score pop-ups and rack tracker"], 10.0, 2.4, 2.6, 4.0, 12);
  s.addNotes("This match ended MCTS 11 – Minimax 6. Click the video to play.");
}
{
  const s = add("CONTENT", "Gameplay");
  title(s, "Human vs AI at 2x speed", "Gameplay video");
  video(s, M + "human_vs_ai_2x.mp4", M + "human_vs_ai_2x_poster.jpg", 0.6, 1.65, 8.9, 5.006);
  card(s, 9.8, 1.65, 2.95, 5.0);
  s.addText("Controls shown", { x: 10.0, y: 1.85, w: 2.6, h: 0.4, fontFace: HEAD, fontSize: 17, color: AMBER, margin: 0, isTextBox: true });
  bullets(s, ["Mouse aims the cue", "Drag back to set power", "Ghost ball and cut angle guide", "Your clock runs while you aim", "Then the AI replies"], 10.0, 2.4, 2.6, 4.0, 12);
  s.addNotes("The human plays against Minimax (Medium difficulty).");
}
{
  const s = add("CONTENT", "Gameplay");
  title(s, "Menus, modes and benchmark", "Gameplay video");
  video(s, M + "ui_tour.mp4", M + "ui_tour_poster.jpg", 0.6, 1.65, 6.4, 3.6);
  img(s, M + "13_benchmark.png", 7.3, 1.65, 5.45, 3.066);
  img(s, M + "12_ball_in_hand.png", 0.6, 5.45, 2.6, 1.4625);
  img(s, M + "10_results.png", 3.4, 5.45, 2.6, 1.4625);
  para(s, "Benchmark mode runs silent matches and saves a CSV. Ball-in-hand shows a green (legal) or red ring. The results screen lists balls, fouls, think time and simulations.", 7.3, 4.95, 5.45, 1.8, 13, INK);
  s.addNotes("Tour: main menu, player setup, how-to-play screen; plus benchmark, ball-in-hand and results.");
}

// 11 ─ Scenario
{
  const s = add("CONTENT", "Decision analysis");
  title(s, "The traced scenario: right after the break", "Decision analysis");
  img(s, M + "scenario.png", 0.6, 1.7, 7.9, 4.43);
  const k = T.kinds;
  card(s, 8.85, 1.7, 3.9, 2.4);
  s.addText("Shot finder output", { x: 9.1, y: 1.85, w: 3.5, h: 0.4, fontFace: HEAD, fontSize: 17, color: CYAN, margin: 0, isTextBox: true });
  s.addText([
    { text: `${k.direct} direct pots`, options: { breakLine: true } }, { text: `${k.bank} bank shots (DLS)`, options: { breakLine: true } },
    { text: `${k.combo} combination (bidirectional)`, options: { breakLine: true } }, { text: `${k.safety} safeties` },
  ], { x: 9.1, y: 2.35, w: 3.5, h: 1.6, fontFace: BODY, fontSize: 14, color: INK, margin: 0, isTextBox: true, paraSpaceAfter: 4 });
  card(s, 8.85, 4.3, 3.9, 1.83);
  para(s, "Minimax is to move with 15 balls on the table. Letters A–D mark the four best pots by heuristic; white numbers mark the A* run-out order.", 9.1, 4.45, 3.5, 1.6, 12, INK);
  s.addNotes("Same position is fed to the heuristic, A*, Minimax and MCTS so their decisions can be compared step by step.");
}

// 12 ─ Heuristic table
{
  const s = add("CONTENT", "Decision analysis");
  title(s, "Step 1: heuristic score of each pot", "Decision analysis");
  const hdr = ["Shot", "Ball → pocket", "d₁", "d₂", "cut", "σ", "α", "p", "h"];
  const rows = [hdr.map(t => ({ text: t, options: { bold: true, color: CYAN, fill: { color: "16233F" } } }))];
  T.heuristic.slice(0, 4).forEach((r, i) => rows.push([
    "ABCD"[i], `${r.ball} → ${r.pocket}`, r.d1.toFixed(1), r.d2.toFixed(1), r.cut.toFixed(1) + "°", r.sigma_deg.toFixed(2) + "°",
    r.alpha_deg.toFixed(2) + "°", r.p.toFixed(3), r.value.toFixed(3)].map(t => ({ text: t, options: { color: INK, fill: { color: PANEL } } }))));
  s.addTable(rows, { x: 0.6, y: 1.75, w: 7.5, colW: [0.6, 1.8, 0.7, 0.7, 0.7, 0.75, 0.75, 0.75, 0.75], fontFace: BODY, fontSize: 12, border: { type: "solid", pt: 0.5, color: EDGE }, rowH: 0.42 });
  card(s, 0.6, 4.15, 7.5, 2.5);
  s.addText("Worked example, shot A", { x: 0.85, y: 4.3, w: 7, h: 0.4, fontFace: HEAD, fontSize: 17, color: AMBER, margin: 0, isTextBox: true });
  para(s, "σ = 50.5 × 0.30° / (2 × 11.5 × cos 33.9°) = 0.79°\nα = atan(w / 145.6) = 4.91°\np = erf(4.91 / (0.79 × √2)) × (1 − ¼(33.9/85)⁴) = 0.994\nh = 0.994 × 1 point = 0.994", 0.85, 4.8, 7.0, 1.8, 13, INK);
  img(s, M + "fig_heuristic_dark.png", 8.35, 1.75, 4.4, 2.07, false);
  card(s, 8.35, 4.15, 4.4, 2.5);
  para(s, "Greedy stops here and plays shot A. A short cue-to-ghost distance d₁ keeps σ small, so the nearby ball 2 scores highest.\n\nMinimax and MCTS use the same score to order shots and as their play-out policy.", 8.6, 4.35, 3.95, 2.2, 13, INK);
  s.addNotes("This is exactly what the Greedy agent does; Minimax and MCTS use this score to order shots and as a play-out policy.");
}

// 13 ─ A*
{
  const s = add("CONTENT", "Decision analysis");
  title(s, "Step 2: A* plans the run-out order", "Decision analysis");
  const plan = T.astar.plan;
  plan.forEach(([b, p], i) => {
    const x = 0.6 + i * 2.48;
    card(s, x, 1.75, 2.25, 1.1, PANEL, i === 0 ? CYAN : EDGE);
    s.addText(`${i + 1}. ball ${b}`, { x: x + 0.2, y: 1.85, w: 1.9, h: 0.4, fontFace: HEAD, fontSize: 17, color: i === 0 ? CYAN : INK, margin: 0, isTextBox: true });
    para(s, `→ ${p}`, x + 0.2, 2.3, 1.95, 0.45, 12);
  });
  const hdr = ["Step", "Path so far", "g", "h", "f = g + h", "Children"];
  const rows = [hdr.map(t => ({ text: t, options: { bold: true, color: CYAN, fill: { color: "16233F" } } }))];
  T.astar.log.slice(0, 6).forEach(r => rows.push([String(r.step), r.path.length ? r.path.join(", ") : "start", r.g.toFixed(3), r.h.toFixed(2), r.f.toFixed(3), String(r.children)]
    .map(t => ({ text: t, options: { color: INK, fill: { color: PANEL } } }))));
  s.addTable(rows, { x: 0.6, y: 3.15, w: 7.9, colW: [0.6, 3.3, 0.9, 0.8, 1.2, 1.1], fontFace: BODY, fontSize: 12, border: { type: "solid", pt: 0.5, color: EDGE }, rowH: 0.4 });
  card(s, 8.8, 3.15, 3.95, 2.85);
  para(s, `Cost of a pot = −ln p + ${T.astar.time_cost} (time).\nh = balls left × ${T.astar.time_cost}: every pot costs at least the time term, so h never overestimates (admissible).\n\nTotal plan cost ${T.astar.cost} after ${T.astar.expansions} expansions.`, 9.05, 3.35, 3.5, 3.2, 13, INK);
  s.addNotes("A*'s first planned pot gets a bonus in the move ordering of Minimax and MCTS.");
}

// 14 ─ Minimax IDDFS
{
  const s = add("CONTENT", "Decision analysis");
  title(s, "Step 3: Minimax with iterative deepening", "Decision analysis");
  img(s, M + "fig_minimax_overview_dark.png", 0.6, 1.65, 8.2, 3.28, false);
  const d = T.minimax.iddfs;
  card(s, 9.1, 1.65, 3.65, 4.95);
  s.addText("Iteration results", { x: 9.35, y: 1.8, w: 3.2, h: 0.4, fontFace: HEAD, fontSize: 17, color: CYAN, margin: 0, isTextBox: true });
  para(s, `Depth 1: best = ${d[0].best}\n${d[0].sims} simulations, ${d[0].nodes} nodes\n\nDepth 2: best = ${d[1].best}\n${d[1].sims} simulations, ${d[1].nodes} nodes, ${d[1].pruned} branches pruned`, 9.35, 2.3, 3.2, 4.2, 13, INK);
  bullets(s, ["Root = MAX node; each shot is a CHANCE node played 2 times with random error",
    "Leaf value = score lead + 0.9 × best pot chance for whoever moves next + 0.025 × clock lead",
    "Deeper search sees the follow-up position, so medium power wins"], 0.6, 5.15, 8.2, 1.6, 13);
  s.addNotes("IDDFS lets Minimax always have an answer: if time runs out during depth 3, it plays the depth-2 choice.");
}

// 15 ─ Minimax branch + alpha-beta
{
  const s = add("CONTENT", "Decision analysis");
  title(s, "Inside the winning branch and an alpha-beta cut", "Decision analysis");
  img(s, M + "fig_minimax_branch_dark.png", 0.6, 1.6, 8.0, 4.14, false);
  card(s, 8.9, 1.6, 3.85, 5.05);
  s.addText("Pruning in this trace", { x: 9.15, y: 1.75, w: 3.4, h: 0.4, fontFace: HEAD, fontSize: 17, color: RED, margin: 0, isTextBox: true });
  para(s, "Under '9 → bottom-right, soft' the shot missed, so the opponent (MIN) moved. Its first reply already scored below α = 2.79 (Minimax's best so far), so the remaining 2 replies were skipped: the branch could never beat the current best.\n\nStar1 rule for chance nodes: after k of n samples, if (sum + remaining × Vmax) / n ≤ α, stop sampling.", 9.15, 2.25, 3.4, 4.3, 12, INK);
  para(s, "After both samples potted ball 2, Minimax shoots again (MAX). The best follow-up (15 → top-right) scores up to +2.90.", 0.6, 5.95, 8.0, 0.8, 13);
  s.addNotes("Alpha-beta never changes the result, only skips work that cannot matter.");
}

// 16 ─ MCTS tree
{
  const s = add("CONTENT", "Decision analysis");
  title(s, "Step 4: MCTS builds its tree with UCB1", "Decision analysis");
  img(s, M + "fig_mcts_tree_dark.png", 0.6, 1.6, 8.3, 3.92, false);
  const c = T.mcts.children[0];
  card(s, 9.2, 1.6, 3.55, 5.05);
  s.addText("UCB1 worked example", { x: 9.45, y: 1.75, w: 3.1, h: 0.4, fontFace: HEAD, fontSize: 17, color: AMBER, margin: 0, isTextBox: true });
  para(s, `Child: ${c.action}\nN = ${c.N}, W = ${c.W}\nQ = W/N = ${c.Q}\nC·√(ln ${T.mcts.root_N} / ${c.N}) = ${c.explore}\nUCB1 = ${c.Q} + ${c.explore} = ${c.ucb1}\n\nAll children end near 1.30: UCB1 keeps exploration and exploitation in balance.`, 9.45, 2.25, 3.1, 4.3, 12, INK);
  bullets(s, ["Selection by UCB1 → Expansion of one untried shot → Simulation with noise and a greedy play-out → Backpropagation of the 0–1 reward",
    "Below the root a move means 'the k-th best shot in the position you reach' (open-loop tree)"], 0.6, 5.7, 8.3, 1.2, 12);
  s.addNotes("After 160 iterations the most-visited root shot is played.");
}

// 17 ─ MCTS iterations
{
  const s = add("CONTENT", "Decision analysis");
  title(s, "How visits grow iteration by iteration", "Decision analysis");
  img(s, M + "fig_mcts_visits_dark.png", 0.6, 1.65, 7.0, 3.3, false);
  const hdr = ["Iter", "Root shot selected", "Reward", "N", "Q"];
  const rows = [hdr.map(t => ({ text: t, options: { bold: true, color: AMBER, fill: { color: "16233F" } } }))];
  T.mcts.log.slice(0, 8).forEach(r => rows.push([String(r.iter), r.root_action, r.reward.toFixed(3), String(r.N), r.Q.toFixed(3)]
    .map(t => ({ text: t, options: { color: INK, fill: { color: PANEL } } }))));
  s.addTable(rows, { x: 7.85, y: 1.65, w: 4.9, colW: [0.5, 2.4, 0.75, 0.5, 0.75], fontFace: BODY, fontSize: 11, border: { type: "solid", pt: 0.5, color: EDGE }, rowH: 0.36 });
  bullets(s, ["Iterations 1–3 try each new shot once (expansion order follows the heuristic)",
    "Iteration 4 returns to '2 soft' after its UCB1 stays the highest",
    `${T.mcts.iterations} iterations used ${T.mcts.sims} physics simulations, tree depth ${T.mcts.depth}`], 0.6, 5.2, 7.0, 1.6, 13);
  s.addNotes("Visits concentrate on the shots whose play-outs win most often.");
}

// 18 ─ Comparison
{
  const s = add("CONTENT", "Decision analysis");
  title(s, "Same position, three decisions", "Decision analysis");
  const cols = [["Greedy", "2 → bottom side, soft", "Highest one-shot chance (0.994). No look-ahead.", GREEN],
    ["Minimax", "2 → bottom side, medium", "Depth 2 sees the follow-up 15 → top-right; value 2.79 beats 1.53 for soft.", CYAN],
    ["MCTS", "2 → bottom side, soft", "23 of 160 visits; Q = 0.65 from noisy play-outs.", AMBER]];
  cols.forEach(([h, pick, why, c], i) => {
    const x = 0.6 + i * 4.1;
    card(s, x, 1.8, 3.85, 2.7, PANEL, c);
    s.addText(h, { x: x + 0.25, y: 2.0, w: 3.4, h: 0.5, fontFace: HEAD, fontSize: 22, color: c, margin: 0, isTextBox: true });
    s.addText(pick, { x: x + 0.25, y: 2.6, w: 3.4, h: 0.5, fontFace: BODY, fontSize: 16, bold: true, color: INK, margin: 0, isTextBox: true });
    para(s, why, x + 0.25, 3.2, 3.4, 1.8, 13);
  });
  card(s, 0.6, 4.85, 12.15, 1.2);
  para(s, "All three pot ball 2 into the bottom side pocket. They differ on power: Minimax looks one shot further and chooses medium power to land the cue ball for the next pot.", 0.85, 5.0, 11.7, 1.0, 14, INK);
  s.addNotes("Agreement on the ball shows the heuristic is sound; disagreement on power shows the value of look-ahead.");
}

// 19 ─ Benchmark
{
  const s = add("CONTENT", "Results");
  title(s, "Benchmark: 40 silent matches", "Results");
  img(s, M + "fig_benchmark_dark.png", 0.6, 1.7, 7.6, 3.22, false);
  const st = [["MCTS 11 – 9", "vs Minimax, 20 matches", AMBER], ["Minimax 9 – 1", "vs Greedy, 10 matches", CYAN], ["MCTS 7 – 3", "vs Greedy, 10 matches", AMBER]];
  st.forEach(([big, t, c], i) => {
    const y = 1.7 + i * 1.12;
    card(s, 8.55, y, 4.2, 0.98);
    s.addText(big, { x: 8.8, y: y + 0.1, w: 3.8, h: 0.45, fontFace: HEAD, fontSize: 22, color: c, margin: 0, isTextBox: true });
    para(s, t, 8.8, y + 0.56, 3.8, 0.35, 12);
  });
  bullets(s, ["0.6 s thinking per shot for every agent; same physics and same noise",
    "Both search agents clearly beat the greedy baseline",
    "MCTS edges Minimax (avg score 9.2 vs 7.6) with very few fouls on either side (≤ 0.2 per match)"], 0.6, 5.15, 12.1, 1.6, 14);
  s.addNotes("Results from benchmark.py; CSV files are in docs/media.");
}

// 20 ─ Conclusion
{
  const s = add("FULL", "Results");
  s.addImage({ path: M + "gem_glow.jpg", x: 0, y: 0, w: W, h: 7.5 });
  s.addText("Thank you", { x: 0.8, y: 1.6, w: 11.7, h: 1.2, fontFace: HEAD, fontSize: 60, bold: true, color: INK, align: "center", margin: 0, isTextBox: true });
  s.addText("Questions and live demo", { x: 0.8, y: 2.85, w: 11.7, h: 0.6, fontFace: HEAD, fontSize: 26, color: AMBER, align: "center", margin: 0, isTextBox: true });
  s.addText("A complete pool game where eight search algorithms work together: Minimax and MCTS decide, A*, Greedy, BFS, DLS, IDDFS and bidirectional search find and rank the shots.",
    { x: 2.2, y: 4.0, w: 8.9, h: 1.0, fontFace: BODY, fontSize: 16, color: INK, align: "center", margin: 0, isTextBox: true });
  s.addText("Azmaeen Nur Sajin · 2207113     Masumur Rahman Fokrul · 2207114     CSE, KUET", { x: 0.8, y: 6.2, w: 11.7, h: 0.4, fontFace: BODY, fontSize: 13, color: MUTED, align: "center", margin: 0, isTextBox: true });
}

pres.writeFile({ fileName: OUT }).then(f => console.log("wrote", f));

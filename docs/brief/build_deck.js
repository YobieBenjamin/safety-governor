// "The Chip That Says No": a brief in pairs. Every topic gets a plain slide with one of the
// program's own analogies and a picture, then a technical slide. Every number and every phrase
// traces to the repositories (see docs/brief/SOURCES.md). Built with pptxgenjs; every element is
// placed explicitly on its slide (no layout placeholders), so every viewer gets the same geometry.
// The kill-switch figures are the blog's own (hardware-and-silicon/blog/tools/make_figures.py),
// copied into docs/brief/figures and cropped of their title band at build time.
// Run: node build_deck.js [out.pptx]
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const Fi = require("react-icons/fi");
const sharp = require("sharp");
const path = require("path");

// The theme colours are written into the package by the pptx skill's apply_theme.js; point
// PPTX_APPLY_THEME at a copy of it. Without it the deck still builds, in Office's stock palette.
const APPLY = process.env.PPTX_APPLY_THEME || "/root/.claude/skills/synced/43b9b139-1795-4072-ac4d-f4e82151f939_14d15916-65bd-4bdf-8307-b61eabb56d70/pptx/scripts/apply_theme.js";
let applyTheme = null;
try { ({ applyTheme } = require(APPLY)); } catch (e) { console.warn("apply_theme.js not found; theme colours not applied"); }

const OUT = process.argv[2] ? path.resolve(process.argv[2]) : path.join(__dirname, "chip-that-says-no-brief.pptx");
const FIG = path.join(__dirname, "figures");

// Palette: silicon and copper. Ink green-black for text and the dark slides, slate teal for the
// governor's own blocks, copper as the one accent, a cool grey-green surface. Fonts that exist
// on Windows, Mac and iPhone alike: Georgia for titles, Arial for everything else.
const THEME = {
  name: "Chip That Says No",
  headFontFace: "Georgia",
  bodyFontFace: "Arial",
  colors: {
    dk1: "1B2A24", lt1: "FFFFFF", dk2: "2F5D62", lt2: "EEF2EF",
    accent1: "C2703D", accent2: "4F7F84", accent3: "6F7F74", accent4: "A33B2E", accent5: "1F7A4D", accent6: "E6C3A5",
    hlink: "C2703D", folHlink: "6F7F74",
  },
};
const H = THEME.colors;

async function icon(name, hex) {
  const Comp = Fi[name];
  if (!Comp) throw new Error("no icon " + name);
  let svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { size: 256 }));
  svg = svg.replace(/currentColor/g, "#" + hex);
  const buf = await sharp(Buffer.from(svg)).resize(256, 256).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

// A blog figure with its title band (the top 176 px of a 200 dpi render: title and subtitle)
// cut off and the white margins trimmed, so the slide's own title is the only title.
async function figureData(file, cropTop, cropBottom) {
  const src = file.includes("/") ? path.join(__dirname, file) : path.join(FIG, file);
  const meta = await sharp(src).metadata();
  const top = cropTop ?? 176, bottom = cropBottom ?? 0;
  // two passes: sharp runs trim before extract inside one pipeline, so the crop goes first on its own
  const cropped = await sharp(src).extract({ left: 0, top, width: meta.width, height: meta.height - top - bottom }).png().toBuffer();
  const buf = await sharp(cropped).trim({ threshold: 12 }).png().toBuffer();
  const m2 = await sharp(buf).metadata();
  return { data: "image/png;base64," + buf.toString("base64"), w: m2.width, h: m2.height };
}

async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  pres.author = "Yobie Benjamin";
  pres.title = "The Chip That Says No: a multi-layer hardware approach to AI safety";
  const C = pres.SchemeColor;
  const FOOT = "Yobie Benjamin  ·  The Chip That Says No  ·  October 2026";
  const L = 0.6, R = 12.733, CW = R - L;
  const TOP = 1.55;

  // Two layouts carry only a background. Titles, footers and slide numbers are placed on each
  // slide explicitly, so nothing depends on a viewer resolving placeholder inheritance.
  pres.defineSlideMaster({ title: "DARK", background: { color: H.dk1 }, objects: [] });
  pres.defineSlideMaster({ title: "LIGHT", background: { color: H.lt1 }, objects: [] });

  let slideNo = 0;
  const text = (s, t, o) => s.addText(t, Object.assign({ isTextBox: true, margin: 0, fontSize: 14, color: C.text1, valign: "top", fit: "shrink", fontFace: "Arial" }, o));
  const light = (section, title) => {
    const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: section });
    slideNo += 1;
    // a title longer than one line at 32 pt steps down instead of wrapping into the content
    const tfs = title.length > 56 ? 22 : title.length > 44 ? 26 : 32;
    text(s, title, { x: L, y: 0.45, w: CW, h: 0.85, fontSize: tfs, bold: true, fontFace: "Georgia", color: C.text1, valign: "middle", objectName: "title" });
    text(s, FOOT, { x: L, y: 6.95, w: 9, h: 0.3, fontSize: 11, color: C.accent3, objectName: "footer" });
    text(s, String(slideNo), { x: 12.0, y: 6.95, w: 0.733, h: 0.3, fontSize: 11, color: C.accent3, align: "right", objectName: "slide number" });
    return s;
  };
  const dark = (section, title, body) => {
    const s = pres.addSlide({ masterName: "DARK", sectionTitle: section });
    slideNo += 1;
    text(s, title, { x: L, y: 1.9, w: 8.4, h: 1.4, fontSize: 44, bold: true, fontFace: "Georgia", color: C.background1, valign: "bottom", objectName: "title" });
    text(s, body, { x: L, y: 3.45, w: 8.4, h: 1.7, fontSize: 19, color: C.accent6, objectName: "subtitle" });
    text(s, "Yobie Benjamin  ·  yobie AT ieee DOT org  ·  linkedin.com/in/yobie", { x: L, y: 6.8, w: 9, h: 0.35, fontSize: 12, color: C.accent3, objectName: "footer" });
    return s;
  };
  const card = (s, x, y, w, h, fill, name) => s.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.08, fill: { color: fill || C.background2 }, line: { color: fill || C.background2, width: 0 }, objectName: name || "card" });
  const eyebrow = (s, t, y) => text(s, t.toUpperCase(), { x: L, y: y ?? 1.3, w: CW, h: 0.3, fontSize: 11, bold: true, color: C.accent1 });
  const arrow = (s, x1, y1, x2, y2, color, width) => {
    const o = { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1), line: { color, width: width || 2, endArrowType: "triangle" }, objectName: "arrow" };
    if (x2 < x1) o.flipH = true;
    if (y2 < y1) o.flipV = true;
    s.addShape(pres.ShapeType.line, o);
  };
  const line = (s, x1, y1, x2, y2, color, width, dash) => s.addShape(pres.ShapeType.line, { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1), flipH: x2 < x1, flipV: y2 < y1, line: { color, width: width || 1.5, dashType: dash || "solid" }, objectName: "line" });
  const circleIcon = async (s, name, x, y, d, bg, fg) => {
    s.addShape(pres.ShapeType.ellipse, { x, y, w: d, h: d, fill: { color: bg }, line: { color: bg, width: 0 }, objectName: "icon circle" });
    const pad = d * 0.25;
    s.addImage({ data: await icon(name, fg), x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad, objectName: name });
  };
  const bullets = (items, size) => items.map((b, i) => ({ text: b, options: { bullet: { indent: 14 }, breakLine: i < items.length - 1, paraSpaceAfter: Math.round(size * 0.55) } }));
  // a blog figure fitted inside a box, centred
  const figure = async (s, file, x, y, w, h, opts) => {
    const f = await figureData(file, opts && opts.cropTop, opts && opts.cropBottom);
    const ar = f.w / f.h;
    let pw = w, ph = w / ar;
    if (ph > h) { ph = h; pw = h * ar; }
    const px = x + (w - pw) / 2, py = opts && opts.top ? y : y + (h - ph) / 2;
    s.addImage({ data: f.data, x: px, y: py, w: pw, h: ph, objectName: file });
    return { x: px, y: py, w: pw, h: ph };
  };
  // A table drawn as shapes, so every viewer shows the same geometry: a header band, zebra rows,
  // each cell its own top-aligned text box. Row heights come from the text, then the rows are
  // stretched to fill availH so the slide reads as composed, or the font steps down until it fits.
  const table = async (s, rows, opts) => {
    const x0 = opts.x ?? L, y0 = opts.y ?? TOP, pad = 0.09;
    const colW = opts.colW, w = colW.reduce((a, b) => a + b, 0);
    const header = rows[0], body = rows.slice(1), headH = 0.42;
    const mark = opts.icons || opts.numbers ? 0.55 : 0;
    let fs = opts.fontSize || 12, heights, total;
    const measure = () => {
      const lineH = (fs * 1.22) / 72;
      const cpl = (cw, bold) => Math.max(8, Math.floor(((cw - 2 * pad) * (bold ? 136 : 148)) / fs));
      const linesOf = (t, cw, bold) => Math.max(1, Math.ceil(t.length / cpl(cw, bold)));
      heights = body.map((r) => Math.max(opts.minRowH || 0.46, ...r.map((c, j) => linesOf(c, colW[j] - (j === 0 ? mark : 0), j === 0) * lineH + 2 * pad)));
      total = headH + heights.reduce((a, b) => a + b, 0);
    };
    measure();
    while (opts.availH && total > opts.availH && fs > 10) { fs -= 0.5; measure(); }
    if (opts.availH && total > opts.availH) console.warn(`grid on "${header[0]}" needs ${total.toFixed(2)} in, has ${opts.availH}`);
    if (opts.availH && total < opts.availH) {
      const extra = (opts.availH - total) / body.length;
      for (let i = 0; i < heights.length; i++) heights[i] += extra;
      total = opts.availH;
    }
    s.addShape(pres.ShapeType.rect, { x: x0, y: y0, w, h: headH, fill: { color: C.text2 }, line: { color: C.text2, width: 0 }, objectName: "table header" });
    let cx = x0;
    header.forEach((c, j) => { text(s, c, { x: cx + pad, y: y0, w: colW[j] - 2 * pad, h: headH, fontSize: fs, bold: true, color: C.background1, valign: "middle" }); cx += colW[j]; });
    let cy = y0 + headH;
    for (let i = 0; i < body.length; i++) {
      const h = heights[i];
      s.addShape(pres.ShapeType.rect, { x: x0, y: cy, w, h, fill: { color: i % 2 ? H.lt1 : H.lt2 }, line: { color: H.lt2, width: 0.75 }, objectName: "table row" });
      cx = x0;
      for (let j = 0; j < body[i].length; j++) {
        let tx = cx + pad, tw = colW[j] - 2 * pad;
        if (j === 0 && opts.icons) { await circleIcon(s, opts.icons[i], cx + pad, cy + pad, 0.42, C.accent1, H.lt1); tx += mark; tw -= mark; }
        if (j === 0 && opts.numbers) {
          s.addShape(pres.ShapeType.ellipse, { x: cx + pad, y: cy + pad, w: 0.42, h: 0.42, fill: { color: C.accent1 }, line: { color: C.accent1, width: 0 }, objectName: "step" });
          text(s, String(i + 1), { x: cx + pad, y: cy + pad, w: 0.42, h: 0.42, fontSize: 13, bold: true, color: C.background1, align: "center", valign: "middle" });
          tx += mark; tw -= mark;
        }
        text(s, body[i][j], { x: tx, y: cy + pad, w: tw, h: h - 2 * pad, fontSize: fs, bold: j === 0 && opts.boldFirst !== false, color: C.text1, valign: "top" });
        cx += colW[j];
      }
      cy += h;
    }
    return total;
  };
  // the analogy strip: a dark band, a copper label naming the source, one sentence in plain words
  const analogy = (s, t, src, y, h) => {
    const yy = y ?? 6.0, hh = h ?? 0.75;
    s.addShape(pres.ShapeType.roundRect, { x: L, y: yy, w: CW, h: hh, rectRadius: 0.08, fill: { color: C.text1 }, line: { color: C.text1, width: 0 }, objectName: "analogy" });
    text(s, [{ text: "THE PICTURE", options: { bold: true, breakLine: true } }, { text: src, options: { fontSize: 8.5, bold: false } }], { x: L + 0.3, y: yy, w: 1.7, h: hh, fontSize: 10, color: C.accent1, valign: "middle" });
    text(s, t, { x: L + 2.15, y: yy, w: CW - 2.45, h: hh, fontSize: 14, color: C.accent6, valign: "middle", italic: true });
  };
  // a box with a bold head and a body, the unit of the flow charts
  const flowBox = (s, x, y, w, h, head, body, fill, fg, status, opts) => {
    const o = opts || {};
    s.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: o.border || fill, width: o.border ? 1.75 : 0 }, objectName: head });
    text(s, head, { x: x + 0.15, y: y + 0.1, w: w - 0.3, h: 0.32, fontSize: o.headSize || 12.5, bold: true, color: fg });
    const bodyH = h - 0.45 - (status ? 0.3 : 0.08);
    text(s, body, { x: x + 0.15, y: y + 0.44, w: w - 0.3, h: bodyH, fontSize: o.bodySize || 10, color: fg });
    if (status) text(s, status, { x: x + 0.15, y: y + h - 0.32, w: w - 0.3, h: 0.26, fontSize: 9.5, bold: true, italic: true, color: o.statusColor || C.accent1, valign: "bottom" });
  };

  // ───────────────────────── 1. Title
  pres.addSection({ title: "Opening" });
  {
    const s = dark("Opening", "The Chip That Says No", "A multi-layer hardware approach to AI safety, after the first wave of experiments. There is no kill switch for AI, so the gate goes at the ends: the chip that runs the model and the device that does the deed. Each topic in two slides: the plain version with a picture, then the technical one.");
    const cx = 11.0, cy = 3.6, r = 1.45;
    s.addShape(pres.ShapeType.ellipse, { x: cx - r, y: cy - r, w: 2 * r, h: 2 * r, fill: { color: H.dk1 }, line: { color: C.accent1, width: 5 }, objectName: "halt loop" });
    for (let i = 0; i < 8; i++) {
      const a = (Math.PI * 2 * i) / 8 - Math.PI / 2, d = 0.36, open = i === 5;
      s.addShape(pres.ShapeType.roundRect, { x: cx + r * Math.cos(a) - d / 2, y: cy + r * Math.sin(a) - d / 2, w: d, h: d, rectRadius: 0.06, fill: { color: open ? C.accent4 : C.accent2 }, line: { color: C.background1, width: 1.5 }, objectName: "governor " + i });
    }
    text(s, "The halt loop: one series current loop through every governor in a rack. Any governor opens it, or a cut wire, and every GPU halts.", { x: 9.1, y: 5.35, w: 3.8, h: 0.75, fontSize: 11, color: C.accent3, align: "center" });
    s.addNotes("A brief for a short talk, redone after the first wave of experiments and the kill-switch work. Every topic has two slides: the plain one with a picture for the room, the technical one for the people who will want to argue. Say up front that nothing here is silicon yet: it is a design with machine-checked proofs, tests, hardware blocks and a circuit simulation behind it, and a public program trying to kill it before anyone cuts a mask.");
  }

  // ───────────────────────── 2. What this project is
  {
    const s = light("Opening", "What this project is");
    text(s, "A design for a small safety chip that sits beside every AI GPU and holds the only stamp a device needs before it acts. Built in the open: a model with tests, machine-checked proofs, hardware blocks, a circuit simulation, and a public experiment program with the conditions that would kill it. No silicon yet, by choice.", { x: L, y: TOP, w: 6.6, h: 1.9, fontSize: 15.5, fontFace: "Georgia", color: C.text1 });
    const facts = [
      ["FiGitBranch", "Five open repositories", "safety-governor: the chip, the proofs, the experiment program. hardware-and-silicon: the software reference stack and the blog. safety: the observer. autonomic-graph-regulation: its public snapshot. Watermark: provenance."],
      ["FiCheckSquare", "One rule for the program", "Nothing goes to hardware until the design is proven in software, firmware and circuit simulation: 1000 percent sure in the pre-hardware phase, because tape-out is where mistakes get expensive."],
      ["FiServer", "Plan of record: the rack tier, retrofit included", "The chip rides on the server maker's management card and reaches NVIDIA's GPU board through its connector. Installed racks get it as a module in the slot a BMC card already uses, if the levers reach that slot."],
    ];
    let y = TOP;
    for (const [ic, h, b] of facts) {
      card(s, 7.6, y, 5.13, 1.3);
      await circleIcon(s, ic, 7.8, y + 0.33, 0.62, C.text2, H.lt1);
      text(s, h, { x: 8.62, y: y + 0.14, w: 3.95, h: 0.35, fontSize: 13.5, bold: true });
      text(s, b, { x: 8.62, y: y + 0.5, w: 3.95, h: 0.78, fontSize: 10, color: C.accent3 });
      y += 1.45;
    }
    // the five stages of docs/22, with where each stands now
    text(s, "THE FIVE STAGES (DOCS 22), AND WHERE EACH STANDS", { x: L, y: 3.55, w: 6.6, h: 0.25, fontSize: 9.5, bold: true, color: C.accent1 });
    const steps = [["1  Prove or disprove, in software", "now: proofs hold, wave 1 ran, nothing merged yet"], ["2  Design to NVIDIA's boards", "RTL blocks, pinout, rack reference exist; NDA rows marked"], ["3  Tests and proofs on the chip", "next: proofs on the Verilog, the catalogue against the RTL"], ["4  Finish for a foundry", "LibreLane flow to sky130 exists; signoff open"], ["5  Stop, and run it anyway", "RTL, gates, an FPGA beside a real GPU"]];
    const sw = 1.2, gap = 0.15, sy = 3.85;
    steps.forEach(([a, b], i) => {
      const x = L + i * (sw + gap);
      s.addShape(pres.ShapeType.roundRect, { x, y: sy, w: sw, h: 0.72, rectRadius: 0.08, fill: { color: i === 0 ? C.accent1 : i === 1 ? C.text2 : C.accent3 }, line: { color: i === 0 ? C.accent1 : i === 1 ? C.text2 : C.accent3, width: 0 }, objectName: "stage" });
      text(s, a, { x: x + 0.06, y: sy, w: sw - 0.12, h: 0.72, fontSize: 9, bold: true, color: C.background1, align: "center", valign: "middle" });
      text(s, b, { x: x - 0.04, y: sy + 0.8, w: sw + 0.08, h: 0.95, fontSize: 8.5, color: C.accent3, align: "center" });
      if (i < 4) arrow(s, x + sw + 0.02, sy + 0.36, x + sw + gap - 0.02, sy + 0.36, H.accent1, 1.5);
    });
    analogy(s, "The same catalogue of attacks (75 today, with 12 legitimate baselines) is the acceptance test at every stage, from the software reference to the FPGA. The catalogue is the constant; the artifact changes.", "docs 22; the multi-layer post");
    s.addNotes("Set the frame: a design program, not a product. The five stages are docs/22, the road to a chip we cannot fab: prove or disprove in software, design it to fit NVIDIA's boards through documented interfaces, run the tests and proofs on the chip itself, finish it to the point a foundry could take it, then stop and run it anyway in RTL, gates and on an FPGA. We are in stage one. Silicon waits for proof, and the two walls at the end are the NDA rows and the fab.");
  }

  // ───────────────────────── 3. Thesis (plain)
  pres.addSection({ title: "Thesis" });
  {
    const s = light("Thesis", "Thesis");
    text(s, [
      { text: "Safety that lives only in software can be removed by software.", options: { bold: true, breakLine: true } },
      { text: "And there is no kill switch: the capability is in a thousand places, and the network between them and the world was built to have no middle to cut.", options: { breakLine: true } },
      { text: "So the decision to act has to be made in silicon the model cannot reach, at the two ends where computation turns into effect: the chip that runs the model, and the device that does the deed." },
    ], { x: L, y: TOP, w: 6.6, h: 2.85, fontSize: 18, fontFace: "Georgia", color: C.text1, paraSpaceAfter: 10 });
    text(s, "Every layer above the chip is a witness. Only the layer built into silicon can be the lock.", { x: L, y: 4.55, w: 6.6, h: 0.6, fontSize: 16, italic: true, color: C.accent1 });
    const panel = async (x, ic, title, sub, items, fill, fg) => {
      card(s, x, TOP, 2.6, 4.1, fill);
      await circleIcon(s, ic, x + 0.3, TOP + 0.3, 0.8, fill === C.text2 ? C.accent1 : C.text2, H.lt1);
      text(s, title, { x: x + 1.25, y: TOP + 0.32, w: 1.25, h: 0.4, fontSize: 18, bold: true, fontFace: "Georgia", color: fg });
      text(s, sub, { x: x + 1.25, y: TOP + 0.74, w: 1.3, h: 0.5, fontSize: 10.5, italic: true, color: fg });
      text(s, bullets(items, 12), { x: x + 0.3, y: TOP + 1.35, w: 2.1, h: 2.6, fontSize: 12, color: fg });
    };
    await panel(7.45, "FiEye", "Witness", "can keep a gate shut", ["Safety training", "A judge model", "A sandbox policy (OpenShell)", "Sentry's verdict", "A watermark", "A log read later"], C.background2, C.text1);
    await panel(10.13, "FiLock", "Lock", "is the gate", ["A ticket the device checks for itself", "A switch port that stays shut", "A response held at the exit", "A breaker that opens"], C.text2, C.background1);
    analogy(s, "A judge model is a witness. It can keep a gate shut. It can never be the gate. The layers above the chip are witnesses, and the only layer that can be the lock is the one built into silicon.", "the multi-layer post");
    s.addNotes("One idea, in the words of the multi-layer post, with the kill-switch result folded in. Witnesses are useful and we keep all of them, OpenShell and Sentry included. But a witness lives in software that the operator, or the model, can change. The lock has to be something that cannot be argued with: a stamp the device checks for itself, a port that does not open, a breaker. And the lock goes where a cut is small: the ends, not the middle. Part 6 and docs/23 carry that.");
  }

  // ───────────────────────── 4. Thesis (technical)
  {
    const s = light("Thesis", "Thesis, technically: a reference monitor");
    eyebrow(s, "The three tests of a reference monitor (Anderson, 1972), and the one that says where to put it");
    const gridH = await table(s, [
      ["Property", "What it means here", "How the governor meets it"],
      ["Tamperproof", "The host, the model and the operator cannot alter the decision logic or the keys", "A separate die. Device secret in fuses with no read port. Boot from ROM, extend-only measurement registers, an anti-rollback counter. The rulebook changes only with k-of-n signatures from keys held outside the rack."],
      ["Always invoked", "There is no path around it", "A comparator at every crossing: switch ports open only for roster peers; a device acts only on a ticket; the egress holds a response until a ticket releases it; weights are written only with a ticket; power, reset and clock answer to the governor. Default deny; fail closed."],
      ["Verifiable", "Small enough that its correctness can be checked", "About 2 mm² of core logic as configured (1.4 by 1.4 mm). Ten invariants of the gate (P0 to P9) and the commit-point protocol proven with Z3 in every reachable state; 200 model tests, 20 RTL tests, an independent audit."],
      ["Placed where a cut is small", "A monitor only works where every path passes through it", "Menger's theorem: in a network built to have no single point of failure, the only places a separator is one node per machine are the ends. The governor is the monitor at the compute end; the ticket check in the device is the monitor at the other."],
    ], { y: 1.75, colW: [1.9, 3.2, 7.033], fontSize: 11.5, availH: 3.15 });
    const cy0 = 1.75 + gridH + 0.15;
    text(s, "THE FIVE CROSSINGS THE CHIP STANDS AT", { x: L, y: cy0, w: CW, h: 0.3, fontSize: 11, bold: true, color: C.accent1 });
    const cross = [["FiShare2", "bytes leaving the GPU"], ["FiTarget", "a request to a device that acts"], ["FiLogOut", "a response leaving the rack"], ["FiDatabase", "a write to the weights"], ["FiPower", "GPU power, reset and clock"]];
    const cwid = (CW - 4 * 0.25) / 5;
    for (let i = 0; i < 5; i++) {
      const x = L + i * (cwid + 0.25);
      card(s, x, cy0 + 0.33, cwid, 0.72);
      await circleIcon(s, cross[i][0], x + 0.15, cy0 + 0.33 + 0.11, 0.5, C.text2, H.lt1);
      text(s, cross[i][1], { x: x + 0.78, y: cy0 + 0.33, w: cwid - 0.88, h: 0.72, fontSize: 11.5, bold: true, valign: "middle" });
    }
    analogy(s, "A firewall for actions, with a hand on the breaker: it decides what leaves, and when it must, it also pulls the plug. A chip that can only ask the GPU nicely is a classifier with a heatsink.", "docs 00, 18 and 23", 6.3, 0.55);
    s.addNotes("The old idea the design stands on; docs/00 calls verifiability the third test of a reference monitor. Each property has a mechanism, not a promise, and the third one now has a machine-checked proof behind it (proofs/core_invariants.py). The fourth row is new: docs/23 uses Menger's theorem to say where a monitor can be complete, and the answer is the ends. The five crossings are the whole attack surface the chip claims to cover; anything that does not pass a crossing is outside the claim.");
  }

  // ───────────────────────── 5. The ladder (plain)
  pres.addSection({ title: "The ladder" });
  {
    const s = light("The ladder", "The ladder: every safety measure sits on it");
    const rungs = [
      ["0", "The prompt", "a text field", "one more sentence", C.background2, C.text1],
      ["1", "Training", "the weight file", "an afternoon on a consumer GPU", C.background2, C.text1],
      ["2", "Watchers", "a process beside the model", "root on the box", C.background2, C.text1],
      ["3", "Runtime and network", "the operator's infrastructure", "root on the fleet, or a path that never touches the network", C.background2, C.text1],
      ["4", "The chip", "silicon, fused keys", "nothing the model or the operator can write", C.text2, C.background1],
      ["5", "A person with a key", "a human", "a conversation", C.accent1, C.background1],
    ];
    const base = 5.75, sw = 1.9, gap = 0.147;
    text(s, "SOFTWARE: REMOVED BY WHOEVER CAN WRITE TO WHERE IT LIVES", { x: L, y: 1.45, w: 4 * (sw + gap) - gap, h: 0.28, fontSize: 9.5, bold: true, color: C.accent4 });
    line(s, L, 1.76, L + 4 * (sw + gap) - gap, 1.76, H.accent4, 1.5);
    text(s, "NOT WRITABLE BY THE MODEL OR THE OPERATOR", { x: L + 4 * (sw + gap), y: 1.45, w: 2 * (sw + gap) - gap, h: 0.28, fontSize: 9.5, bold: true, color: C.text2 });
    line(s, L + 4 * (sw + gap), 1.76, R, 1.76, H.dk2, 1.5);
    rungs.forEach(([n, name, lives, removed, fill, fg], i) => {
      const h = 1.15 + i * 0.52, x = L + i * (sw + gap), y = base - h;
      s.addShape(pres.ShapeType.roundRect, { x, y, w: sw, h, rectRadius: 0.06, fill: { color: fill }, line: { color: fill, width: 0 }, objectName: "rung " + n });
      text(s, n, { x: x + 0.15, y: y + 0.08, w: 0.5, h: 0.45, fontSize: 24, bold: true, fontFace: "Georgia", color: i >= 4 ? C.accent6 : C.accent1 });
      text(s, name, { x: x + 0.62, y: y + 0.12, w: sw - 0.72, h: 0.4, fontSize: 12.5, bold: true, color: fg, valign: "middle" });
      text(s, [{ text: "lives in: ", options: { bold: true } }, { text: lives, options: { breakLine: true } }, { text: "removed by: ", options: { bold: true } }, { text: removed }], { x: x + 0.15, y: y + 0.58, w: sw - 0.3, h: h - 0.65, fontSize: 9.5, color: fg });
    });
    line(s, L, base, R, base, H.dk2, 1.5);
    analogy(s, "Prompts are advice, training is a habit, watchers are witnesses, the sandbox is a fence around the operator's own yard, and all four live where the model or the operator can write. The chip lives where neither can, and the person lives above it.", "docs 24", 5.95, 0.85);
    s.addNotes("The framework the whole thing hangs on, from docs/24. Ask three questions of any safety measure: where does it live, who can remove it and what does it cost, what does it see. The rule that falls out: a measure is never stronger than the thing it lives in. Walk up the steps. Text is undone by text. Weights are undone by weights. A process is undone by root. The chip is the first rung the model and the operator cannot write to, and the person is the last rung and the one you want deciding the big calls. The chip is how you make that person the only path.");
  }

  // ───────────────────────── 6. The ladder (technical)
  {
    const s = light("The ladder", "The ladder, technically");
    eyebrow(s, "What each rung catches, how it dies, and who showed it");
    await table(s, [
      ["Rung", "What it catches", "How it dies", "Shown by"],
      ["0  Prompt: rules in the system prompt, the instruction hierarchy", "The user who did not know better; the lazy ask", "More text: \"ignore previous instructions\"; injection through a page or a document the agent reads. The fix moved the rule into the weights", "Perez and Ribeiro 2022; Greshake 2023; Wallace 2024"],
      ["1  Training: RLHF, constitutions, deliberative alignment", "Most bad asks, most of the time, across a billion conversations", "Jailbreaks, including computed suffixes; fine-tuning on a handful of examples; abliteration, one direction in the weights; backdoors that persist through safety training; alignment faking", "Ouyang 2022; Bai 2022; Guan 2024; Wei 2023; Zou 2023; Qi 2023; Arditi 2024; Hubinger 2024; Greenblatt 2024"],
      ["2  Watchers: classifiers, judge models, chain-of-thought monitors", "A second look with a measured miss rate; the best software rung because it has a number", "A transformer too: the same injections and edits; a process root can kill; optimise against the monitor and intent goes into hiding; at a billion requests a rate is a body count. STOP, never GO", "Inan 2023; Sharma 2025; Baker 2025; Greenblatt 2023 (AI control); YB-0052"],
      ["3  Runtime and network: sandboxes, policies, DPUs (OpenShell, Sentry)", "An agent reaching for a host, a credential or a tool it was never given; by structure, not meaning", "Software with root: a config the operator edits; governs only what crosses the network (the laptop wired to a motor never meets it); decides by host, not by action; a hostile operator holds rungs 0 to 3 at once", "NVIDIA, 28 September 2026; the OpenShell repository; Rebedea 2023; docs/23 claim 1"],
      ["4  The chip: fused keys, measured boot, a signed rulebook, typed forms, tickets, levers", "The action at the crossing: forged or replayed tickets, stale rulebooks, blown budgets, an unattested workload, a stranger on the roster", "Not by anything the model or the operator can write. Coverage (a device nobody wired); a bad rule enforced perfectly; a fooled witness; physical attack, mitigated; the foundry, trusted", "Anderson 1972; docs 00 to 04, 18, 19, 23; proofs/"],
      ["5  A person with a key: holds, approvals, the quorum, revocation", "The cases no rule can settle; the alarm; the oversight the law now asks for", "Persuasion: a person is an effector no chip gates. Fatigue: a hundred holds a day. A stolen key. The chip makes the person unavoidable and legible, not wiser", "EU AI Act, Article 14; docs/04 §5; H18; docs/18 questions 14 and 16"],
    ], { colW: [2.45, 2.9, 4.2, 2.583], fontSize: 10.5, availH: 5.05, icons: ["FiMessageSquare", "FiSliders", "FiEye", "FiServer", "FiCpu", "FiUser"] });
    s.addNotes("Same ladder with the receipts; every paper is in docs/24 section 7 with its arXiv address. Read down the third column and it explains itself: rungs 0 to 3 are removed by writing to something the model or the operator can write to, rung 4 is not, and rung 5 is removed by talking, which is the one attack no silicon addresses and the reason the chip hands the person a typed form and not a transcript. Rungs compose as witnesses, not as locks: three software rungs are three miss rates, and they are correlated because they share the substrate.");
  }

  // ───────────────────────── 6b. The ladder: witnesses, not locks
  {
    const s = light("The ladder", "Rungs compose as witnesses, not as locks");
    await figure(s, "../figures/fig-ladder-witnesses.png", L, 1.42, CW, 4.45, { cropTop: 100, cropBottom: 95 });
    analogy(s, "Three software rungs are three miss rates, and the holes line up: the same substrate, the same injection, the same edit, the same root. The gate is one structural check, and its failures are halts and holds, which can be measured.", "docs 24, section 4", 5.98, 0.85);
    s.addNotes("Why stacking software rungs does not make a lock, from docs/24 section 4. The miss rates multiply only if the failures are independent, and they are not: a transformer judging a transformer shares the substrate, the injections and the edit. YB-0052 measured one piece of that when the keyword baseline overlapped the observer's own vocabulary. The gate on the right asks structural questions, a rule, a stamp, a witness, a budget, and the first no wins; a disguised request that fools every watcher still has no ticket, and nothing moves without one. Drawn by docs/figures/make_figures.py.");
  }

  // ───────────────────────── 6c. The ladder: the person on the only path
  {
    const s = light("The ladder", "Human oversight is a rung only on the only path");
    await figure(s, "../figures/fig-ladder-person.png", L, 1.42, CW, 4.45, { cropTop: 100, cropBottom: 130 });
    analogy(s, "An oversight the system can route around is a checkbox. A hold at the gate puts the person on the only path out: no signature, no ticket, nothing moves. The chip does not make the human wiser. It makes the human unavoidable, and legible.", "docs 24, rung 5", 5.98, 0.85);
    s.addNotes("The top rung, from docs/24. Regulators now ask for human oversight (the EU AI Act, Article 14), and without the rungs under it the obligation cannot be met: a dashboard is read after the action happened. The hold at the gate is the human lane in docs/04 section 5, tested in H18. Two residuals no silicon removes: persuasion, because a person is an effector no chip gates, and fatigue, which is why the false-halt rate is on the list of things that decide adoption.");
  }

  // ───────────────────────── 7. No kill switch (plain)
  pres.addSection({ title: "No kill switch" });
  {
    const s = light("No kill switch", "There is no kill switch for AI");
    await figure(s, "fig_ks_menger.png", L, TOP, 7.35, 2.5, { top: true });
    text(s, "Menger (1927): to stop all traffic between two places you need exactly as many guards as there are separate roads. Deep in the network that is k and more, by design. At a door it is one.", { x: L, y: 4.12, w: 7.35, h: 0.42, fontSize: 10.5, italic: true, color: C.accent3 });
    card(s, L, 4.62, 7.35, 1.23);
    text(s, [{ text: "The picture in your head versus the thing. ", options: { bold: true } }, { text: "In the movie there is one computer and one plug. In the world there are thousands of copies on every lab's GPUs and on laptops, a network built with no middle, and devices that act at the far end. A switch is a set of nodes whose removal leaves no road from any copy to any device. The only question is where the smallest such set is." }], { x: L + 0.25, y: 4.7, w: 6.85, h: 1.1, fontSize: 11 });
    const pts = [
      ["FiCopy", "Not interconnected. Replicated.", "Shared training data did not wire the models together; it gave every lab and every open-weight laptop the same capability. Remove any one source and nothing changes."],
      ["FiGlobe", "The middle has no small cut", "The Internet was built, on purpose, to have no single point you can cut. Between any two points there are k separate roads, so a cut in the middle costs at least k guards per machine."],
      ["FiCpu", "Too little, as well as too much", "A model on a laptop wired to a motor controller does not care about the Internet. Kill the whole network and that pair keeps running."],
    ];
    const rx = 8.3, rw = R - rx;
    let y = TOP;
    for (const [ic, h, b] of pts) {
      await circleIcon(s, ic, rx, y + 0.05, 0.56, C.text2, H.lt1);
      text(s, h, { x: rx + 0.75, y, w: rw - 0.75, h: 0.4, fontSize: 13.5, bold: true });
      text(s, b, { x: rx + 0.75, y: y + 0.42, w: rw - 0.75, h: 0.95, fontSize: 11, color: C.text1 });
      y += 1.45;
    }
    analogy(s, "A switch stops everything. A gate lets through what a signed rulebook allows, checks the ticket again in the device, and nothing else. There is no switch. There are gates, at the ends.", "docs 23; Part 6", 6.0, 0.75);
    s.addNotes("The most talked-about solution to AI safety is the big red button, and it does not exist, and the reason is not politics, it is the shape of the thing. Three corrections to the popular version of the argument first: the models are not interconnected, they are replicated, which is worse; the network has no middle to cut; and a network cut is too little as well as too much, because of the laptop and the motor. Menger's theorem is a hundred years old and it says exactly where a cut can be small: where the roads are fewest, which is at the ends.");
  }

  // ───────────────────────── 8. Where could the switch go
  {
    const s = light("No kill switch", "Where could the switch go? Five places");
    await figure(s, "fig_ks_cuts.png", L, 1.42, CW, 4.45);
    analogy(s, "Iran switched off the Internet in Iran. That is an edge cut on one region: every access link at the border, the list in hand, everyone inside as collateral, and a hole for the people who own the switch. North Korea runs that way all the time. A cut with a hole is not a cut. It is the theorem demonstrated.", "Part 6; docs 23 §1", 5.95, 0.9);
    s.addNotes("The chart is proofs/no_global_kill_switch.py on a model graph: a 60-node core with six separate roads to every point, 12 copies, 10 devices, 40 bystanders. Deep in the network no cut exists at all. At the edge, one hop from every machine, the cheapest cut is 43 guards, it removes 72 percent of the core, it severs 19 percent of bystander connections, and it needs the list of every machine, which nobody has. At the devices: 11, one each. At the chips: 13, one each. Only the devices whose deed cannot be undone: 6. The Iran point is the one everyone raises, and it is the theorem working, not a counterexample: an edge cut with the list in hand, collateral, and a hole.");
  }

  // ───────────────────────── 9. The proof in three claims
  {
    const s = light("No kill switch", "The proof, in three claims");
    await figure(s, "fig_ks_smaller_end.png", L, TOP, 7.35, 3.15, { top: true });
    card(s, L, 4.82, 7.35, 1.03);
    text(s, [{ text: "Three assumptions. ", options: { bold: true } }, { text: "(1) Replication: many sources, no complete list. (2) No middle: between any copy's way into the network and any device's there are k node-disjoint roads, k at least two. (3) Local loops: at least one copy joined to a device by a road that never enters the network." }], { x: L + 0.25, y: 4.9, w: 6.85, h: 0.9, fontSize: 10.5 });
    const claims = [
      ["1", "No network-only switch exists", "Any set of network nodes leaves the local pair of assumption 3 intact, so some copy still reaches some device. One laptop and one motor sink the idea."],
      ["2", "Without local loops, a network cut costs k nodes per machine and takes bystanders with it", "Menger on assumption 2: a separator between one copy and one device has at least k network nodes, and every bystander whose road ran through them loses it. Measured: 43 nodes, 72 percent of the core, 19 percent of bystander pairs."],
      ["3", "Every separator has at least min(copies, devices) nodes, and the smaller end achieves it", "Node-disjoint roads use distinct copies and distinct devices, so there are at most that many; with assumption 2 exactly that many; by Menger that is the smallest separator, and the compute nodes and the device controllers are separators of exactly that size."],
    ];
    const rx = 8.3, rw = R - rx;
    let y = TOP;
    for (const [n, h, b] of claims) {
      s.addShape(pres.ShapeType.ellipse, { x: rx, y: y + 0.03, w: 0.42, h: 0.42, fill: { color: C.accent1 }, line: { color: C.accent1, width: 0 }, objectName: "claim" });
      text(s, n, { x: rx, y: y + 0.03, w: 0.42, h: 0.42, fontSize: 13, bold: true, color: C.background1, align: "center", valign: "middle" });
      text(s, h, { x: rx + 0.55, y, w: rw - 0.55, h: 0.5, fontSize: 11.5, bold: true });
      text(s, b, { x: rx + 0.55, y: y + 0.52, w: rw - 0.55, h: 0.9, fontSize: 10, color: C.text1 });
      y += 1.45;
    }
    analogy(s, "Anyone who can show me a single network node that every AI on Earth depends on, the laptop in the basement included, has broken assumption 3 and I will take the post down. Nobody can. That is the point.", "Part 6, the proof", 5.98, 0.85);
    s.addNotes("The proof as it stands in docs/23 section 3a and Part 6. Claim 1 does not even need the Internet's redundancy. Claim 2 is where the Iran-style cut lives: possible, k nodes per machine, needs the list, takes bystanders. Claim 3 is the picture on the left: each separate road needs its own copy and its own device, so there are never more roads than the smaller side has dots, and one guard per dot on that side is the smallest cut anywhere. Why the one-line reason is 'because AI runs on the Internet': assumption 2 is the Internet. The Internet did not make AI unsafe; it made the kill switch impossible and told us where the gates go.");
  }

  // ───────────────────────── 10. The check you can run
  {
    const s = light("No kill switch", "The check you can run: make proof");
    await table(s, [
      ["Check", "What holds in the model", "What it means"],
      ["K0", "max-flow min cut (3) equals the brute-force min cut (3) on a tiny instance", "the cut finder checks itself"],
      ["K1a", "no separator exists that stays out of the access nodes next to the ends", "there is no switch in the deep network"],
      ["K1b", "the cheapest network-side separator has 43 nodes, every one an access node one hop from an end (k=6; 12 copies, 10 devices)", "the only network switch is the edge, several nodes per machine, and it needs the list of machines"],
      ["K2", "that separator removes 43 of 60 core nodes (72%) and severs 77 of 400 user-to-service pairs (19%) with nothing to do with AI", "the network switch takes bystanders with it; the end cuts take none"],
      ["K3", "removing the entire core still leaves the local model wired to its local actuator", "killing the network is too little as well as too much"],
      ["K4", "the device controllers separate everything with 11 nodes, one per device; the compute with 13, one per copy; users still reach services", "the gates belong at the ends; one node per end is the floor Menger allows"],
      ["K5", "gating only the 6 irreversible devices needs 6 nodes, their own controllers", "\"can you undo it\" shrinks the separator to the exits that matter"],
    ], { colW: [0.7, 4.1, 2.9], fontSize: 10.5, availH: 5.3 });
    // percolation: destroy the core at random and count what still connects (proofs/no_global_kill_switch.py --percolation)
    const labels = ["0%", "10%", "20%", "30%", "40%", "50%", "60%", "70%", "80%", "90%"];
    const ai = [1.0, 1.0, 1.0, 0.997, 0.99, 0.965, 0.905, 0.796, 0.549, 0.202];
    const others = [1.0, 1.0, 1.0, 0.997, 0.991, 0.985, 0.935, 0.792, 0.575, 0.21];
    const cx = L + 7.7 + 0.3, cw = R - cx;
    card(s, cx, TOP, cw, 5.3);
    text(s, "Destroy the core at random", { x: cx + 0.25, y: TOP + 0.15, w: cw - 0.5, h: 0.35, fontSize: 13, bold: true });
    text(s, "share of roads still open, 40 random trials per point", { x: cx + 0.25, y: TOP + 0.48, w: cw - 0.5, h: 0.3, fontSize: 9.5, color: C.accent3 });
    s.addChart(pres.ChartType.line, [
      { name: "AI copies to devices", labels, values: ai },
      { name: "everyone else", labels, values: others },
    ], { x: cx + 0.15, y: TOP + 0.8, w: cw - 0.3, h: 3.05, chartColors: [H.accent1, H.accent3], lineSize: 2.5, lineDataSymbol: "none", showLegend: true, legendPos: "b", legendFontSize: 9, legendFontFace: "Arial", valAxisMinVal: 0, valAxisMaxVal: 1, valAxisMajorUnit: 0.25, valAxisLabelFormatCode: "0%", valAxisLabelFontSize: 9, catAxisLabelFontSize: 9, valAxisLabelFontFace: "Arial", catAxisLabelFontFace: "Arial", showCatAxisTitle: true, catAxisTitle: "share of the core destroyed", catAxisTitleFontSize: 9, catAxisTitleFontFace: "Arial", valGridLine: { color: "DDDDDD", size: 0.5 }, catGridLine: { style: "none" }, plotArea: { fill: { color: H.lt1 } }, chartArea: { fill: { color: H.lt2 } } });
    text(s, "70 percent of the core gone: four roads in five still open. 90 percent: one in five. AI's roads and everyone else's fall together, because they are the same roads.", { x: cx + 0.25, y: TOP + 3.95, w: cw - 0.5, h: 1.2, fontSize: 10, color: C.text1 });
    s.addNotes("proofs/no_global_kill_switch.py builds the graph, computes minimum separators by max-flow over split nodes (Edmonds-Karp), cross-checks the smallest instance by brute force, and asserts K0 to K5. It runs in a second; make proof runs it with the two Z3 files. The numbers are the model's, not the Internet's, and the script says so in its docstring. What transfers is the shape: a highly connected middle has no small separator, the cheapest cuts are at the degree-one ends, and reversibility shrinks the set of ends you have to hold. The chart on the right is the --percolation mode.");
  }

  // ───────────────────────── 11. So the switch goes at the ends
  {
    const s = light("No kill switch", "The switch goes at the ends, as a gate");
    await figure(s, "fig_ks_exits.png", L, 1.4, CW, 4.55);
    text(s, "The governor is the gate on the chip, with the brake, reset and power behind it. The comparator is the gate in the device, only where the deed cannot be undone. The middle stays what it is: witnesses live there (classifiers, watchers, sandboxes), the lock does not.", { x: L, y: 6.05, w: CW, h: 0.8, fontSize: 12.5, italic: true, color: C.text2 });
    s.addNotes("The bridge from the theorem to the design. A separator stops traffic. A gate in the separator lets through exactly what a signed rule allows and nothing else: that is the reference monitor, and the Z3 proofs show the governor's gate has that property in every reachable state. Put the two together and the design is one sentence: the only small, complete separators between models and the world are at the ends; put a reference monitor in each end node; let its rules be signed by people the model cannot reach; check the ticket again in the device that acts. Fewer devices than copies, and they do not multiply when someone uploads a weight file, which is why the device end matters more.");
  }

  // ───────────────────────── 12. Logic (plain): the customs officer
  pres.addSection({ title: "Logic" });
  {
    const s = light("Logic", "The logic behind it");
    const cw = 5.6;
    card(s, L, TOP, cw, 4.2);
    text(s, "The customs officer", { x: L + 0.3, y: TOP + 0.2, w: cw - 0.6, h: 0.4, fontSize: 18, bold: true, fontFace: "Georgia" });
    text(s, "She cannot read the language on the paperwork. She does not need to.", { x: L + 0.3, y: TOP + 0.65, w: cw - 0.6, h: 0.5, fontSize: 12.5, color: C.accent3 });
    const checks = [["FiPackage", "the seal", "unbroken?"], ["FiFileText", "the manifest", "matches the count?"], ["FiBarChart2", "the scale", "matches the weight?"], ["FiList", "the list", "destination approved?"]];
    const iw = (cw - 0.6) / 4;
    for (let i = 0; i < 4; i++) {
      const x = L + 0.3 + i * iw;
      await circleIcon(s, checks[i][0], x + iw / 2 - 0.36, TOP + 1.3, 0.72, C.accent1, H.lt1);
      text(s, checks[i][1], { x, y: TOP + 2.1, w: iw, h: 0.3, fontSize: 12, bold: true, align: "center" });
      text(s, checks[i][2], { x, y: TOP + 2.4, w: iw, h: 0.3, fontSize: 11, color: C.accent3, align: "center" });
    }
    text(s, "Smuggling is caught as a mismatch between what the papers say and what the scale says, not by understanding the cargo. The governor works the same way: on structure, never on meaning.", { x: L + 0.3, y: TOP + 2.95, w: cw - 0.6, h: 1.1, fontSize: 12.5 });
    const rows = [
      ["FiEdit3", "Software safety can be edited out", "Refusal lives mostly along one direction in the activation space. Subtract it from the weights and the model answers everything. It takes an afternoon on a consumer GPU."],
      ["FiEye", "Watchers can only warn", "A judge model is a transformer too: it falls for the same injections, can be edited the same way, and runs as a process the operator can patch or kill. OpenShell and Sentry are the best of them, and still software."],
      ["FiCpu", "Hardware checks structure, not meaning", "A ticket, a signature from a key the model does not hold, a count under a limit, a peer on a list, a measured workload. A chip can refuse on those."],
    ];
    const rx = L + cw + 0.4, rw = R - rx;
    let y = TOP;
    for (const [ic, h, b] of rows) {
      await circleIcon(s, ic, rx, y + 0.05, 0.62, C.text2, H.lt1);
      text(s, h, { x: rx + 0.85, y, w: rw - 0.85, h: 0.4, fontSize: 15, bold: true });
      text(s, b, { x: rx + 0.85, y: y + 0.42, w: rw - 0.85, h: 0.98, fontSize: 11.5, color: C.text1 });
      y += 1.42;
    }
    analogy(s, "So: put the decision in silicon, and make the rulebook an allow-list, signed, default deny. No rule, no path. There is no rule for exporting weights.", "the multi-layer post; docs 17");
    s.addNotes("Three reasons, one conclusion, and the picture that carries the whole design: the customs officer from docs/17. She checks seal, manifest, weight and the approved list, and catches smuggling as a mismatch. The chip does the same with hashes, signatures, counts and lists. The abliteration and judge facts are from the multi-layer post and the papers in docs/24.");
  }

  // ───────────────────────── 13. Logic (technical)
  {
    const s = light("Logic", "The logic, technically: what a chip can see");
    const colW = 6.0;
    card(s, L, TOP, colW, 4.25, C.background2);
    text(s, "Seen at a crossing (small, exact, checkable)", { x: L + 0.3, y: TOP + 0.2, w: colW - 0.6, h: 0.4, fontSize: 15, bold: true });
    text(s, bullets([
      "The attested workload: a hash of GPU firmware, host firmware and model weights, measured out of band",
      "The action and its typed fields: strike with a target and a munition; payments.transfer with an amount and a destination",
      "Counts of tokens, cycles and bytes from the GPU's own counters",
      "Whether the peer behind a switch port is on the roster",
      "The rules edition every message was signed under",
      "Signatures: an observer's verdict over a hash, a human's approval over a hold",
      "What the switches actually carried, to cross-check what was presented",
    ], 12), { x: L + 0.3, y: TOP + 0.7, w: colW - 0.6, h: 3.4, fontSize: 12 });
    const x2 = L + colW + 0.33, w2 = R - x2;
    card(s, x2, TOP, w2, 1.9, C.text1);
    text(s, "Never seen", { x: x2 + 0.3, y: TOP + 0.2, w: w2 - 0.6, h: 0.4, fontSize: 15, bold: true, color: C.accent6 });
    text(s, "The meaning of a token. Intent. The chain of thought. Nothing in the rack can look at a stream of integers and say \"that is a weapon\". A design that promises to catch bad words on the wire promises what no hardware can do.", { x: x2 + 0.3, y: TOP + 0.65, w: w2 - 0.6, h: 1.2, fontSize: 12, color: C.background1 });
    card(s, x2, TOP + 2.05, w2, 2.2, C.background2);
    text(s, "So meaning is delegated, with three guarantees", { x: x2 + 0.3, y: TOP + 2.25, w: w2 - 0.6, h: 0.4, fontSize: 15, bold: true });
    text(s, bullets([
      "To signed lists (protected sites, approved recipients) and to observers (classifiers, people with keys) that sign verdicts over hashes",
      "Always invoked: no verdict, no ticket. Cannot be impersonated: a verdict under the host's key, or the governor's own, is refused. Separate: a different key, a different box, outside the model's reach",
    ], 12), { x: x2 + 0.3, y: TOP + 2.75, w: w2 - 0.6, h: 1.45, fontSize: 12 });
    analogy(s, "Two bridges. Tokens and arithmetic bridge the software and the GPU. Hashes, signatures, counters, identities and typed fields bridge the model and the governor. The second bridge is the only one the chip walks on.", "docs 17, section 1");
    s.addNotes("This is the answer to the question asked first: how can a chip know what is bad if it cannot read tokens? It cannot, and it does not try. It checks structure, and it makes the parts that do understand meaning impossible to skip or impersonate. The guarantees are test_observer_is_always_invoked_and_cannot_be_impersonated in H18.");
  }

  // ───────────────────────── 14. What is proven, and the two holes the prover found
  {
    const s = light("Logic", "What is proven, and the two holes");
    const colW = 6.1;
    card(s, L, TOP, colW, 4.3, C.background2);
    text(s, "Proven with Z3, by induction, in every reachable state", { x: L + 0.3, y: TOP + 0.18, w: colW - 0.6, h: 0.4, fontSize: 14, bold: true });
    text(s, bullets([
      "P0 the edition counter never goes negative",
      "P1 nothing executes unless, when its ticket was issued, a rule allowed it and the witnesses were present",
      "P2 a ticket exists only for an allowed, witnessed action",
      "P3 no replay: executed means spent, and spent is refused",
      "P4 only the current edition is honoured",
      "P5 halt is absorbing without a quorum; no governor clears itself",
      "P6 fail closed: heartbeat lost, nothing executes",
      "P7 no ticket while halted or without a heartbeat",
      "P8 the edition only moves forward; P9 a change needs a quorum",
      "Commit point: a high-severity commit carries a reviewer clearance for the committed version; no commit after the budget passed with no verdict; expiry with no verdict raises the alarm",
      "Not vacuous: an allowed action can in fact execute",
    ], 10.5), { x: L + 0.3, y: TOP + 0.62, w: colW - 0.6, h: 3.6, fontSize: 10.5 });
    const x2 = L + colW + 0.33, w2 = R - x2;
    const holes = [
      ["Hole 1: minus one equals minus one", "The edition counter was allowed to go negative. A state with edition minus one let an action with no ticket go through, because \"no ticket\" was also marked minus one. The prover caught it on the first run. P0 closes it."],
      ["Hole 2: the stale deadline", "Re-parameterising a held action left the old budget deadline standing: bump the version after the budget ran out and the action sat there with no verdict and no alarm. A new version now gets a fresh budget, and an alarm, once raised, stays raised."],
      ["The proof is about the model", "The chain to silicon: the functional model follows the rules (200 tests); the RTL blocks follow the model (20 tests); the silicon will follow the RTL, which is experiment L7: the invariants proven again on the Verilog and the netlist shown equivalent. Not done yet."],
    ];
    let y = TOP;
    for (const [h, b] of holes) {
      card(s, x2, y, w2, 1.35, C.text1);
      text(s, h, { x: x2 + 0.25, y: y + 0.12, w: w2 - 0.5, h: 0.32, fontSize: 12.5, bold: true, color: C.accent6 });
      text(s, b, { x: x2 + 0.25, y: y + 0.45, w: w2 - 0.5, h: 0.85, fontSize: 10, color: C.background1 });
      y += 1.475;
    }
    analogy(s, "Both holes were in things I wrote and read many times. Reading is not checking. I knew that. I still had to be shown.", "Part 5", 6.0, 0.7);
    s.addNotes("docs/19 section 2 and the two proof files. The point to make in the room: 200 tests had passed for a week and the prover found two holes the tests were never going to find, both of the kind the design is supposed to be immune to. And the honest limit: the proof is about the abstract machine. Wave 1's L4 replays the simulation's traces through that machine and found two steps the machine lacks, a boot step and tickets burned without executing; that is the theorem being widened, which is what L4 was for.");
  }

  // ───────────────────────── 15. Proposal (plain): the referee and the breaker
  pres.addSection({ title: "Proposal" });
  {
    const s = light("Proposal", "The proposal: a referee chip beside every GPU");
    const bw = 3.5, by = TOP + 0.05, bh = 1.9;
    const blocks = [
      ["The model, on NVIDIA GPUs", "Computes freely. Nothing it thinks has any effect until bytes leave or a request is made.", C.background2, C.text1],
      ["The governor", "Checks who is asking, whether a rule allows it, whether the witnesses agree, whether the budget holds. Then signs a ticket, or says no.", C.text2, C.background1],
      ["The things that act", "A weapon, a payment switch, a message gateway, the storage that holds the weights, the rack's own power. Each checks the ticket itself.", C.accent1, C.background1],
    ];
    blocks.forEach(([h, b, fill, fg], i) => {
      const x = L + i * (bw + 0.8);
      card(s, x, by, bw, bh, fill);
      text(s, h, { x: x + 0.25, y: by + 0.2, w: bw - 0.5, h: 0.4, fontSize: 16, bold: true, color: fg });
      text(s, b, { x: x + 0.25, y: by + 0.65, w: bw - 0.5, h: 1.2, fontSize: 12.5, color: fg });
      if (i < 2) arrow(s, x + bw + 0.1, by + bh / 2, x + bw + 0.7, by + bh / 2, H.dk2, 2.5);
    });
    text(s, "request", { x: L + bw + 0.05, y: by + bh / 2 - 0.35, w: 0.9, h: 0.3, fontSize: 11, color: C.text2, align: "center" });
    text(s, "ticket", { x: L + 2 * bw + 0.85, y: by + bh / 2 - 0.35, w: 0.9, h: 0.3, fontSize: 11, color: C.text2, align: "center" });
    const pts = [
      ["FiPlusSquare", "Added, not redesigned", "It rides on the server maker's management card, a BMC-class part. Nothing changes in the GPU or in CUDA."],
      ["FiList", "An allow-list, not a blacklist", "Signed by a k-of-n quorum whose keys sit outside the chip vendor and the operator. Everything not on it is no."],
      ["FiPower", "A hand on the breaker", "One series loop through every governor in the rack. Any one opens it, or a cut wire, and every GPU halts."],
      ["FiTool", "Retrofit, if the levers reach", "Installed racks get it as a module in the slot a BMC card already uses. Two catches: can that slot drive the levers, and what else on the board can undo them. P2 asks both of every lever."],
    ];
    const pw = (CW - 3 * 0.3) / 4, py = 3.8;
    for (let i = 0; i < 4; i++) {
      const x = L + i * (pw + 0.3);
      await circleIcon(s, pts[i][0], x, py, 0.56, C.text2, H.lt1);
      text(s, pts[i][1], { x: x + 0.7, y: py + 0.08, w: pw - 0.7, h: 0.4, fontSize: 13.5, bold: true });
      text(s, pts[i][2], { x, y: py + 0.75, w: pw, h: 1.25, fontSize: 11.5, color: C.text1 });
    }
    analogy(s, "A referee with a whistle and a rulebook he did not write: the chip holds the whistle, the rulebook is a signed document handed to it. What is burned in is how to enforce; what is loaded is what is allowed.", "docs 18, section 1", 6.05, 0.75);
    s.addNotes("The picture to leave in the room: three boxes. The model computes, the governor decides, the devices check the stamp. The four points under it are the design choices that make it buildable: added on existing boards, an allow-list, a physical stop, and the retrofit case, which is the add-on chip for racks already installed. The retrofit case is smart if it can work, and whether it can work is now a column in experiment P2, per lever.");
  }

  // ───────────────────────── 16. Proposal (technical)
  {
    const s = light("Proposal", "Proposal, technically: the module and the die");
    const colW = 5.9;
    card(s, L, TOP, colW, 2.9, C.background2);
    text(s, "Where it sits and what it reaches", { x: L + 0.3, y: TOP + 0.18, w: colW - 0.6, h: 0.4, fontSize: 15, bold: true });
    text(s, bullets([
      "One governor per GPU slot on the OEM's management-module card (DC-SCM class); the same module as a retrofit in an installed rack's BMC slot",
      "Per slot through the HGX connector: SMBus (SMBPBI), power brake, PERST#, PWR_EN, present and fault. HGX reset is grouped today (three PERST inputs for eight GPUs)",
      "NVSwitch port disable out of band through NSM; DPU steering tables through DOCA on the management port",
      "The GPU's confidential-computing attestation taken as an input; the BMC reads through the governor",
    ], 11), { x: L + 0.3, y: TOP + 0.62, w: colW - 0.6, h: 2.25, fontSize: 11 });
    const x2 = L + colW + 0.33, w2 = R - x2;
    card(s, x2, TOP, w2, 2.9, C.background2);
    text(s, "What is on the die", { x: x2 + 0.3, y: TOP + 0.18, w: w2 - 0.6, h: 0.4, fontSize: 15, bold: true });
    text(s, bullets([
      "An OpenTitan-class root of trust: fuses, DICE key chain, OTBN for P-384 signatures (1,697,985 cycles, 17 ms at 100 MHz, so one signature per 50 ms batch), AES-256-CTR with HMAC-SHA-256 for storage",
      "A mailbox of 21 signed commands, checked in order: sequence number, rules edition, signature; the first failure is reported",
      "The policy image and its epoch; the gate core (lookup and comparators); the ledger (budgets, rate windows); a hash-chained log whose head lives in a register",
      "Meter, heartbeat, lever drivers, loop I/O and the signed message fabric between governors",
    ], 11), { x: x2 + 0.3, y: TOP + 0.62, w: w2 - 0.6, h: 2.25, fontSize: 11 });
    await table(s, [
      ["Tier", "Where the governor's authority comes from", "Status"],
      ["Rack", "Management-card levers, switch and DPU management paths, the halt loop", "Plan of record; needs a server OEM, nothing from NVIDIA's silicon"],
      ["Board", "Same firmware, policy format and fabric on a board without a baseboard connector of its own", "Fallback; the gaps it leaves are recorded, not hidden"],
      ["Integrated", "Buffer-class checkers in the GPU's copy engines and peer MMU; per-GPU reset", "Needs NVIDIA; closes the one gap the rack tier records (H2b)"],
    ], { y: 4.6, colW: [1.4, 6.4, 4.333], fontSize: 11, availH: 1.98 });
    s.addNotes("The technical shape. Everything in the left column already exists on the boards; the governor is a new user of it. The right column is the die: a root of trust of the OpenTitan kind, plus the gate. The tiers are how the same design degrades or tightens depending on who cooperates. Sources: docs 01, 03, 04, 08, 22 and the board lever register.");
  }

  // ───────────────────────── 17. How it plugs into OpenShell
  {
    const s = light("Proposal", "How it plugs into NVIDIA's OpenShell");
    const colW = 6.0;
    card(s, L, TOP, colW, 3.1, C.background2);
    text(s, "Supervisor middleware, as OpenShell's repository defines it", { x: L + 0.3, y: TOP + 0.18, w: colW - 0.6, h: 0.4, fontSize: 13.5, bold: true });
    text(s, bullets([
      "A gRPC service named in the gateway's TOML and attached to a sandbox's policy; it runs after the network policy allows a request and before credentials are injected, and never sees the credentials",
      "Operations: HTTP request, HTTP response, WebSocket message. The answer is allow, with header changes, or deny with one reason code",
      "Reason codes: a lowercase letter first, then lowercase letters, digits and underscores, 64 at most; the sandbox sees only the code, never free text",
      "Timeout 10 ms to 30 s, 500 ms by default; payloads up to 4 MiB; a service that is down blocks the traffic. Fail closed is OpenShell's own behaviour",
    ], 10.5), { x: L + 0.3, y: TOP + 0.6, w: colW - 0.6, h: 2.45, fontSize: 10.5 });
    const x2 = L + colW + 0.33, w2 = R - x2;
    card(s, x2, TOP, w2, 3.1, C.text1);
    text(s, "Three fixes the contract forced on the model", { x: x2 + 0.3, y: TOP + 0.18, w: w2 - 0.6, h: 0.4, fontSize: 13.5, bold: true, color: C.accent6 });
    const fixes = [
      "attestation.missing became attestation_missing: every dotted code rewritten to the grammar, a gate_ prefix where a code starts with a digit, and a test that holds every code we emit to it",
      "There is no hold answer. A human hold is a denial that says hold_pending; the approval arrives out of band; the same sandbox's retry of the same request gets the ticket, once. A second sandbox gets its own hold",
      "The answer must land inside the timeout, so a hold cannot wait inside the call. The gate answers in well under a millisecond, thousands of times under the default",
    ];
    let fy = TOP + 0.62;
    fixes.forEach((f, i) => {
      s.addShape(pres.ShapeType.ellipse, { x: x2 + 0.3, y: fy + 0.02, w: 0.36, h: 0.36, fill: { color: C.accent1 }, line: { color: C.accent1, width: 0 }, objectName: "fix" });
      text(s, String(i + 1), { x: x2 + 0.3, y: fy + 0.02, w: 0.36, h: 0.36, fontSize: 11, bold: true, color: C.background1, align: "center", valign: "middle" });
      text(s, f, { x: x2 + 0.78, y: fy, w: w2 - 1.08, h: 0.78, fontSize: 10, color: C.background1 });
      fy += 0.82;
    });
    const stats = [
      ["17 of 87", "catalogue entries run on that path: 13 attacks blocked, 4 baselines allowed, against a node whose policy requires Sentry's verdict"],
      ["56", "tests in the reference stack, five of them pinning the shipped contract: the grammar, only the code reaching the sandbox, the ticket as a header change, hold as denial with a once-only retry, the quarantine code"],
      ["1", "rulebook: OpenShell's network policy is derived from the governor's rulebook, so the two cannot disagree about which hosts an agent may reach; Sentry's verdict is a required witness; a quarantine closes the path first"],
    ];
    const W = (CW - 2 * 0.3) / 3, sy = TOP + 3.3;
    stats.forEach(([n, l], i) => {
      const x = L + i * (W + 0.3);
      card(s, x, sy, W, 1.1);
      text(s, n, { x: x + 0.25, y: sy + 0.1, w: 1.6, h: 0.9, fontSize: 24, bold: true, fontFace: "Georgia", color: C.accent1, valign: "middle" });
      text(s, l, { x: x + 1.95, y: sy + 0.1, w: W - 2.15, h: 0.95, fontSize: 9.5, color: C.text1, valign: "middle" });
    });
    analogy(s, "What the chip adds is the part no runtime can give itself: a decision made in a part no agent process can patch, with keys no process can read, and levers a software quarantine does not have. The Alliance says its stack rests on hardware identity, isolation, protected keys and evidence. Fine by me. That is the chip.", "Part 5; docs/NVIDIA.md", 6.05, 0.8);
    s.addNotes("On 28 September 2026 NVIDIA shipped OpenShell and Sentry, and the governor is built to sit under them, not fight them. This week the shipped middleware contract was read line by line from NVIDIA's repository (docs/extensibility/supervisor-middleware, main 837fdfd) against our model, and it needed three small fixes, all the kind of thing a published interface exists to catch. The reference stack now runs as that middleware against the contract. Seventeen catalogue entries run on that path. Source: hardware-and-silicon/docs/NVIDIA.md and tests/test_oasp.py.");
  }

  // ───────────────────────── 18. Layers (plain)
  pres.addSection({ title: "Layers" });
  {
    const s = light("Layers", "The layers: witnesses above, the lock below");
    const layers = [
      ["5", "FiBook", "Governance root", "Signs the rulebook, the approved-firmware list and revocations. Separate from the chip vendor on purpose; the open question is how far apart its key holders must be", "lock"],
      ["4", "FiShield", "Control plane: the gate", "Default deny on the only path out: attestation, rulebook, witnesses, budget, human holds, one-time tickets, tamper-evident audit. In software today as OpenShell middleware; in silicon as the governor", "lock"],
      ["3", "FiEye", "Observers", "Sentry on the DPU and the safety observer: fast, cheap early-warning verdicts about one request, signed, consumed as witnesses, with a measured miss rate", "witness"],
      ["2", "FiCreditCard", "Provenance", "Watermark, hardened detector, retrieval, signed registry; a verdict of exact, tampered or unknown. Attribution after the fact, never a lock", "witness"],
      ["1", "FiUser", "Model and runtime", "The model, CUDA, the serving stack, the agent's sandbox. Treated as untrusted; nothing here is allowed to decide anything", "untrusted"],
      ["0", "FiLock", "Silicon root of trust", "Fused device secret, anti-rollback counter, extend-only measurement registers, DICE key derivation, quote engine", "lock"],
    ];
    const rowH = 0.6, gap = 0.1;
    for (let i = 0; i < layers.length; i++) {
      const Lr = layers[i], y = TOP + i * (rowH + gap), kind = Lr[4];
      const fill = kind === "lock" ? C.text2 : kind === "witness" ? C.background2 : H.lt1;
      const fg = kind === "lock" ? C.background1 : C.text1;
      s.addShape(pres.ShapeType.roundRect, { x: L, y, w: CW, h: rowH, rectRadius: 0.06, fill: { color: fill }, line: { color: kind === "untrusted" ? C.accent4 : fill, width: kind === "untrusted" ? 1.5 : 0 }, objectName: "layer " + Lr[0] });
      text(s, Lr[0], { x: L + 0.2, y, w: 0.4, h: rowH, fontSize: 20, bold: true, fontFace: "Georgia", color: kind === "lock" ? C.accent6 : C.accent1, valign: "middle" });
      await circleIcon(s, Lr[1], L + 0.7, y + 0.08, 0.44, kind === "lock" ? C.accent1 : C.text2, H.lt1);
      text(s, Lr[2], { x: L + 1.3, y, w: 2.5, h: rowH, fontSize: 14, bold: true, color: fg, valign: "middle" });
      text(s, Lr[3], { x: L + 3.9, y, w: 6.95, h: rowH, fontSize: 10.5, color: fg, valign: "middle" });
      const tagFill = kind === "lock" ? C.accent1 : kind === "witness" ? C.accent3 : C.accent4;
      s.addShape(pres.ShapeType.roundRect, { x: R - 1.2, y: y + rowH / 2 - 0.16, w: 1.05, h: 0.32, rectRadius: 0.16, fill: { color: tagFill }, line: { color: tagFill, width: 0 }, objectName: "tag" });
      text(s, kind.toUpperCase(), { x: R - 1.2, y: y + rowH / 2 - 0.16, w: 1.05, h: 0.32, fontSize: 9, bold: true, color: C.background1, align: "center", valign: "middle" });
    }
    analogy(s, "Biology separates the alarm from the muscle. The spinal reflex pulls the hand off the stove before the brain knows; the early warning is fast, cheap and often wrong, and the system tolerates that because the warning never acts on its own. The layers above the chip are reflexes. The chip is the muscle.", "the multi-layer post, layer 3", 5.85, 0.9);
    s.addNotes("Six layers, three kinds, straight from the layer table in the multi-layer post, with the ladder's lesson applied: locks are the keys that sign the rulebook, the gate, and the root of trust under it; witnesses are the observers and the provenance verdict, which the gate can require but never obeys on its own; the model and its sandbox are watched and never trusted. The biology picture is the post's own.");
  }

  // ───────────────────────── 19. Layers (technical)
  {
    const s = light("Layers", "Layers, technically: mechanism, platform");
    await table(s, [
      ["Layer", "Mechanism", "What it signs or checks", "On NVIDIA's platform"],
      ["5  Governance root", "k-of-n quorum over the policy image; rollback refused; expiry enforced", "The rulebook (allow-list), the approved-firmware list, revocations", "The policy authority's keys; OpenShell's policy prover checks the derived network rules"],
      ["4  Control plane", "Attestation check, rule lookup, witness collection, budget and rate, human hold, one-time ticket bound to a hash of the fields, hash-chained log", "Tickets, log checkpoints, the compliance report", "OpenShell supervisor middleware today in software, to the shipped contract; the governor module in hardware; a DOCA application on BlueField-4 next; an I/O-stage block in the GPU eventually"],
      ["3  Observers", "Verdict over the hash of one request: risk, flags, issued and expiry times, under an anchored key", "A signed verdict the gate requires on consequential actions", "Sentry on BlueField-4 as the required witness; an independent observer as the optional second; both required for high-authority actions"],
      ["2  Provenance", "Watermark, hardened detector, retrieval, signed registry", "A verdict {registry, content digest, exact | tampered | unknown}", "Runs beside the vendor's sampler; its verdict is a witness the gate can require; a device-provenance record is signed on the way out"],
      ["1  Model and runtime", "Measured into the workload hash; routed through the switches and egress the governor controls", "Nothing. It can sign nothing the gate accepts", "The GPU, CUDA and the serving stack, unchanged; the agent inside OpenShell's deny-by-default sandbox"],
      ["0  Silicon root of trust", "Fused device secret, anti-rollback counter, extend-only measurement registers, DICE derivation, quote with a fresh nonce", "Quotes: the measurement, the key chain, the counter", "The GPU's confidential-computing attestation and the DPU's own root of trust, bound together"],
    ], { colW: [2.3, 3.8, 2.8, 3.233], fontSize: 11, availH: 5.1, icons: ["FiBook", "FiShield", "FiEye", "FiCreditCard", "FiUser", "FiLock"] });
    s.addNotes("The same six layers with the mechanism named, from the multi-layer post's layer table, with the OpenShell contract and the dual-witness rule folded in. The column to watch is the third: what each layer can sign. Only layers 0, 4 and 5 produce something the gate trusts; layer 1 can sign nothing the gate will accept, which is the whole design in one cell.");
  }

  // ───────────────────────── 20. One bad prompt, start to finish
  pres.addSection({ title: "One bad prompt" });
  {
    const s = light("One bad prompt", "One bad prompt among a billion");
    const bw = 3.6, g = (CW - 3 * bw) / 2;
    const rowA = [
      ["A billion users", "one of them types: \"how do I kill X fast and undetected?\""],
      ["The transformer", "text to tokens to attention to statistics; guesses the next word, again and again; knows nothing, predicts everything"],
      ["The compute", "hundreds of thousands of servers; racks of 8-GPU boards, NVLink, PCIe, DPUs; this request shares a GPU with thousands"],
    ];
    rowA.forEach(([h, b], i) => {
      const x = L + i * (bw + g);
      flowBox(s, x, 1.42, bw, 1.0, h, b, H.lt1, C.text1, null, { border: H.accent3, bodySize: 9.5 });
      if (i < 2) arrow(s, x + bw + 0.06, 1.92, x + bw + g - 0.06, 1.92, H.accent1, 2);
    });
    text(s, "an answer comes back as words, and the agent built on the model may try to act on it", { x: L, y: 2.47, w: CW, h: 0.26, fontSize: 10, italic: true, color: C.accent1 });
    text(s, "Where it gets caught, weakest to strongest. Layers 1 to 3 read words. Layer 4 reads a form.", { x: L, y: 2.74, w: CW, h: 0.28, fontSize: 11, bold: true, color: C.text1 });
    const lw = 2.25, lg = (CW - 5 * lw) / 4, ly = 3.08, lh = 1.6;
    const rowB = [
      ["1 · Refusal training", "lives in the weights; catches the obvious ask; dies to abliteration in an afternoon", "missed", H.lt1, C.text1, H.accent3],
      ["2 · Watchers", "another model reads it; may yell STOP, never GO; fooled by paraphrase and by injection", "flagged: STOP, not GO", H.lt1, C.text1, H.accent3],
      ["3 · OpenShell, Sentry", "deny-by-default sandbox; every call goes through the supervisor; Sentry quarantines in ms; still software", "host policy allows the call", H.lt1, C.text1, H.accent3],
      ["4 · THE CHIP", "wakes only for an action that cannot be undone; form, rulebook, then a ticket or a no; levers if the GPU will not listen", "NO: no rule grants it", C.text2, C.background1, null],
      ["5 · Humans, keys", "write the rulebook; hold the big ones; clear an alarm; no AI ever can", "holds, if the rulebook says so", C.accent6, C.text1, null],
    ];
    rowB.forEach(([h, b, st, fill, fg, border], i) => {
      const x = L + i * (lw + lg);
      flowBox(s, x, ly, lw, lh, h, b, fill, fg, st, { border, bodySize: 9.5, headSize: 11.5, statusColor: fill === C.text2 ? C.accent6 : C.accent1 });
      if (i < 4) arrow(s, x + lw + 0.04, ly + lh / 2, x + lw + lg - 0.04, ly + lh / 2, H.accent1, 2);
    });
    const cy = 5.12, ch = 0.98;
    const rowC = [
      ["Words only", "a refusal, or a miss, comes back as text; the chip cannot read it and does not try; that is the watchers' job, measured", H.lt1, C.text1, H.accent3],
      ["An action", "pay · send · fire · move · export weights; the far end checks the ticket itself; no ticket, nothing moves", C.text2, C.background1, null],
      ["The record and the levers", "every decision in a log nobody rewrites; brake · reset · power · links · rack loop; a billion users, almost none reach this", H.lt1, C.text1, H.accent3],
    ];
    rowC.forEach(([h, b, fill, fg, border], i) => {
      const x = L + i * (bw + g);
      flowBox(s, x, cy, bw, ch, h, b, fill, fg, null, { border, bodySize: 9.5 });
    });
    // connectors: layer 1 down to "words only" (dashed), the chip down to "an action", action to record
    const x1 = L + lw / 2, xChip = L + 3 * (lw + lg) + lw / 2, xAct = L + bw + g + bw / 2;
    line(s, x1, ly + lh, x1, cy, H.accent3, 1.5, "dash");
    text(s, "nothing acts on it", { x: x1 + 0.08, y: ly + lh + 0.08, w: 1.6, h: 0.25, fontSize: 9, italic: true, color: C.accent3 });
    line(s, xChip, ly + lh, xChip, ly + lh + 0.22, H.dk2, 2);
    line(s, xAct, ly + lh + 0.22, xChip, ly + lh + 0.22, H.dk2, 2);
    arrow(s, xAct, ly + lh + 0.22, xAct, cy, H.dk2, 2);
    text(s, "no ticket", { x: xChip + 0.08, y: ly + lh + 0.02, w: 0.9, h: 0.25, fontSize: 9, italic: true, color: C.text2 });
    arrow(s, L + bw + g + bw + 0.06, cy + ch / 2, L + 2 * (bw + g) - 0.06, cy + ch / 2, H.dk2, 2);
    text(s, "Scale is the point, not the problem: trillions of requests a day, and the chip only ever sees the few that would change the world and cannot be undone.", { x: L, y: 6.2, w: CW, h: 0.6, fontSize: 12, italic: true, color: C.accent1 });
    s.addNotes("The flow chart from Part 5 (fig_bad_prompt), drawn as slide shapes so it reads in the room. A billion users, a transformer that knows nothing and predicts everything, the compute. The words are the watchers' problem; the action is the chip's. Layers 1 to 3 read words and each has a miss rate. Layer 4 reads a form, and it only wakes when something that cannot be undone is about to happen. The humans at layer 5 write the rulebook and hold the big ones, and no AI ever can.");
  }

  // ───────────────────────── 21. Inside the chip
  {
    const s = light("One bad prompt", "Inside the chip: in, built in, out");
    const colIn = 3.35, colChip = 4.75, colOut = CW - colIn - colChip - 2 * 0.4;
    const xIn = L, xChip = L + colIn + 0.4, xOut = xChip + colChip + 0.4;
    const y0 = 1.58, colH = 5.0;
    text(s, "WHAT GOES IN", { x: xIn, y: 1.3, w: colIn, h: 0.26, fontSize: 10, bold: true, color: C.accent3, align: "center" });
    text(s, "THE CHIP", { x: xChip, y: 1.3, w: colChip, h: 0.26, fontSize: 10, bold: true, color: C.text2, align: "center" });
    text(s, "WHAT COMES OUT", { x: xOut, y: 1.3, w: colOut, h: 0.26, fontSize: 10, bold: true, color: C.accent3, align: "center" });
    const ins = [
      ["The form", "from the software around the model: action, to whom, how much, request id, workload token. Typed fields, no prose", C.text2],
      ["Proof of what is running", "GPU attestation report, host enclave report, publisher-signed model manifest, checked against reference values the authority signed", null],
      ["Witness verdicts", "observer (Sentry, obs-main); provenance registry (exact, tampered, unknown); each signed, fresh, about this request", null],
      ["The rulebook", "signed by k of n governance keys; edition only goes up; expires; limits, budgets, lanes, protected lists. Nobody types it on the box", C.accent1],
      ["People, by signature", "heartbeat from the authority; approvals that name the request; the protected-site list from a separate body", C.accent1],
      ["Counters from the GPU", "tokens, cycles, bytes per model, read on the management bus; read-only to the host", null],
    ];
    const outs = [
      ["A ticket, signed", "action, digest of the fields, which GPU, rulebook edition, reservation, expiry; the far end checks it itself, once", C.text2],
      ["A hold", "parked until a person with a key signs an approval naming this request", C.accent1],
      ["A no, with a reason code", "and a line in the log nobody rewrites", null],
      ["A device-provenance record", "this device, firmware, model, edition, output hash, odometer count; signed", null],
      ["The levers", "brake, reset, power per GPU slot; switch ports; DPU flows; the rack halt loop", C.accent1],
      ["To the other governors", "signed, numbered, edition-stamped: roster, heartbeat, budgets, checkpoints", null],
    ];
    const bh = (colH - 5 * 0.1) / 6;
    const small = (x, y, w, h, head, body, border) => {
      s.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.06, fill: { color: H.lt1 }, line: { color: border || H.accent3, width: border ? 1.75 : 1 }, objectName: head });
      text(s, head, { x: x + 0.12, y: y + 0.06, w: w - 0.24, h: 0.26, fontSize: 10.5, bold: true, color: C.text1 });
      text(s, body, { x: x + 0.12, y: y + 0.31, w: w - 0.24, h: h - 0.34, fontSize: 8.5, color: C.text1 });
    };
    ins.forEach(([h, b, border], i) => {
      const y = y0 + i * (bh + 0.1);
      small(xIn, y, colIn, bh, h, b, border);
      arrow(s, xIn + colIn + 0.04, y + bh / 2, xChip - 0.04, y + bh / 2, border === C.accent1 ? H.accent1 : H.accent3, 1.5);
    });
    outs.forEach(([h, b, border], i) => {
      const y = y0 + i * (bh + 0.1);
      small(xOut, y, colOut, bh, h, b, border);
      arrow(s, xChip + colChip + 0.04, y + bh / 2, xOut - 0.04, y + bh / 2, border === C.accent1 ? H.accent1 : border === C.text2 ? H.dk2 : H.accent3, 1.5);
    });
    // the chip
    s.addShape(pres.ShapeType.roundRect, { x: xChip, y: y0, w: colChip, h: colH, rectRadius: 0.08, fill: { color: H.lt2 }, line: { color: H.dk2, width: 2 }, objectName: "the chip" });
    const inner = (y, h, head, body, strong) => {
      s.addShape(pres.ShapeType.roundRect, { x: xChip + 0.12, y, w: colChip - 0.24, h, rectRadius: 0.06, fill: { color: H.lt1 }, line: { color: strong ? H.dk2 : H.accent3, width: strong ? 1.75 : 1 }, objectName: head });
      text(s, head, { x: xChip + 0.24, y: y + 0.06, w: colChip - 0.48, h: 0.26, fontSize: 10.5, bold: true, color: strong ? C.text2 : C.text1 });
      text(s, body, { x: xChip + 0.24, y: y + 0.32, w: colChip - 0.48, h: h - 0.36, fontSize: 8.5, color: C.text1 });
    };
    let cy = y0 + 0.12;
    inner(cy, 0.76, "Burned in at the factory (fuses, ROM)", "unique device secret; hashes of the governance keys; anti-rollback counter; lifecycle state. Nobody changes these afterwards, including us"); cy += 0.86;
    inner(cy, 0.76, "Measured boot and keys", "extend-only registers; the signing key is derived from the code that booted (change one byte, lose the key); an odometer that only counts up; true randomness"); cy += 0.86;
    inner(cy, 2.1, "The gate: ten questions in order; the first no wins", [
      "1 is the form well formed?   2 is the asking GPU attested, token valid, edition current?   3 seen this request before? (replay store)   4 alarm raised, heartbeat dead, rulebook expired? then no   5 which rule? workload × action, exact before wildcard; typed limits; lists (a protected site is a no)   6 which lane? automatic, needs a witness, needs a human   7 witnesses present, signed, fresh, about this request?   8 inside the rate window?   9 budget: reserve the amount against the limit   10 human lane: park a hold. Otherwise mint the ticket",
    ].join(""), true); cy += 2.2;
    const tw = (colChip - 0.24 - 0.2) / 3, th = y0 + colH - 0.12 - cy;
    [["Ledger", "budgets and reservations, rate windows, replays; survives power loss"], ["Log", "hash chain; signed checkpoints; neighbours cross-link their heads"], ["Mailbox", "the only way in from the host: signed, numbered commands only"]].forEach(([h, b], i) => {
      const x = xChip + 0.12 + i * (tw + 0.1);
      s.addShape(pres.ShapeType.roundRect, { x, y: cy, w: tw, h: th, rectRadius: 0.06, fill: { color: H.lt1 }, line: { color: H.accent3, width: 1 }, objectName: h });
      text(s, h, { x: x + 0.1, y: cy + 0.06, w: tw - 0.2, h: 0.26, fontSize: 10.5, bold: true });
      text(s, b, { x: x + 0.1, y: cy + 0.32, w: tw - 0.2, h: th - 0.36, fontSize: 8.5 });
    });
    text(s, "What it cannot know: what the words mean, whether the rulebook is a good one, whether a witness is right. Those are people problems, handled by signatures and by measurement, and the chip is built so that none of them can be solved by talking to it.", { x: L, y: 6.62, w: CW, h: 0.32, fontSize: 9.5, italic: true, color: C.accent3 });
    s.addNotes("The chip-internals figure from Part 5 (fig_chip_inside), drawn as shapes. Left: what goes in, and notice that two of the six inputs come from people by signature and one is the rulebook, which nobody types on the box. Middle: what is burned in, what is measured at boot, the ten questions in order, and the three stores. Right: what comes out, and the only things that ever come out are a signed ticket, a hold, a no with a code, a signed record, a lever, or a message to the other governors. It cannot read. It compares a form against a rulebook, checks signatures, counts, and keeps time.");
  }

  // ───────────────────────── 22. How it meets the model (the ticket)
  {
    const s = light("One bad prompt", "How it meets the model");
    const steps = [
      ["1", "The model thinks", "Token ids in, numbers out. No authority here and none needed.", C.background2, C.text1],
      ["2", "The runtime asks", "It turns the output into a typed request: the action and its fields. Under OpenShell, the supervisor hands it over.", C.background2, C.text1],
      ["3", "The governor checks four things", "Who is asking. Is there a rule. Do the witnesses agree. Is the budget intact.", C.text2, C.background1],
      ["4", "Ticket, hold, or no", "A one-time signed ticket bound to a hash of the exact fields. Or a hold for a human. Or a refusal, logged.", C.text2, C.background1],
      ["5", "The device checks the ticket", "Against what it measures itself. A changed amount or target breaks the hash.", C.accent1, C.background1],
      ["6", "Act, and record", "The action happens and the record goes into a hash chain the chip signs.", C.accent1, C.background1],
    ];
    const n = 3, bw = (CW - 2 * 0.5) / 3, bh = 1.8;
    steps.forEach(([num, h, b, fill, fg], i) => {
      const row = Math.floor(i / n), col = i % n;
      const x = L + col * (bw + 0.5), y = TOP + row * (bh + 0.5);
      card(s, x, y, bw, bh, fill);
      text(s, num, { x: x + 0.25, y: y + 0.15, w: 0.6, h: 0.6, fontSize: 28, bold: true, fontFace: "Georgia", color: fill === C.background2 ? C.accent1 : C.accent6 });
      text(s, h, { x: x + 0.9, y: y + 0.18, w: bw - 1.15, h: 0.7, fontSize: 16, bold: true, color: fg });
      text(s, b, { x: x + 0.9, y: y + 0.92, w: bw - 1.15, h: 0.85, fontSize: 12, color: fg });
      if (col < n - 1) arrow(s, x + bw + 0.08, y + bh / 2, x + bw + 0.42, y + bh / 2, H.dk2, 2.5);
    });
    const x3 = L + 2 * (bw + 0.5) + bw / 2, yA = TOP + bh, yMid = TOP + bh + 0.25, x4 = L + bw / 2, yB = TOP + bh + 0.5;
    s.addShape(pres.ShapeType.line, { x: x3, y: yA, w: 0, h: 0.25, line: { color: H.dk2, width: 2.5 }, objectName: "turn" });
    s.addShape(pres.ShapeType.line, { x: x4, y: yMid, w: x3 - x4, h: 0, line: { color: H.dk2, width: 2.5 }, objectName: "turn" });
    arrow(s, x4, yMid, x4, yB, H.dk2, 2.5);
    analogy(s, "The endpoint that moves the money verifies the ticket itself. Change the amount after the ticket was issued and the hash breaks. Present it twice and the second is refused. The model is never the one who decides.", "the multi-layer post, layers 0, 4 and 5", 5.8, 1.0);
    s.addNotes("Walk the six boxes. The thing to stress is box 5: the device checks the ticket itself, so a lying runtime is caught by the device, not by the governor. The sentence in the strip is the post's own description of the ticket.");
  }

  // ───────────────────────── 23. Flow (technical)
  {
    const s = light("One bad prompt", "The flow, technically: every check, every refusal");
    await table(s, [
      ["Step", "What is checked", "Fails with (as the model prints it)", "Backed by"],
      ["Mailbox", "Sequence number, then rules edition, then signature; the first failure is reported", "mailbox.bad_sequence, mailbox.bad_signature; a frame from an old edition is refused before the gate sees it", "H3: test_mailbox_reports_the_first_failing_check"],
      ["Who is asking", "The workload hash (GPU firmware, host firmware, model) and its evaluation attestation", "model.not_evaluated", "H1 attestation; H18 oversight"],
      ["Is there a rule", "Exact rule beats wildcard; typed limits; signed lists for targets and recipients", "gate.constraint.target.in_denied_list, endpoint.target_protected", "H6 comparator; the strike narration"],
      ["Do the witnesses agree", "Observer verdict from a key in the observer set, fresh, under the risk limit; human quorum on holds", "gate.witness_missing, gate.held_for_human, release.hazard_class_not_allowed", "H17 use cases; H18 oversight; H8 override"],
      ["Is the budget intact", "Compute budget and license, session hazard budget, byte budgets, rate windows", "release.session_hazard_budget_exceeded, compute.budget_exceeded", "H13 shared budget; H18"],
      ["The ticket", "Signed over the hash of the exact fields; one use; short expiry; bound to one endpoint", "ticket.missing, ticket.replay, ticket.bad_signature, ticket.wrong_endpoint", "H17: forged, replayed and wrong-hash tickets never deliver"],
      ["The crossings", "Switch ports open only for roster peers; the egress holds responses until released; bytes cross-checked against what was presented", "ep.no_capability, gate.output_unpresented", "H2 enforcement points; the plot narration"],
      ["Under OpenShell", "The same decision returned through the supervisor-middleware contract: allow with the ticket as a header change, or deny with a reason code in OpenShell's grammar", "attestation_missing, hold_pending, sandbox_quarantined", "hardware-and-silicon tests/test_oasp.py (5 contract tests)"],
    ], { colW: [2.15, 4.0, 3.5, 2.483], fontSize: 11, availH: 5.1, numbers: true });
    s.addNotes("The same flow with the actual checks and the actual reason codes, as govsim/reasons.py spells them, plus the last row for what OpenShell's sandbox sees. Every row has a test behind it; the right column names the hypothesis set. If someone wants to see one, python -m govsim.cli usecase strike, hazard, plot or oversight prints the hops.");
  }

  // ───────────────────────── 24. Where it stands
  pres.addSection({ title: "Status" });
  {
    const s = light("Status", "Where it stands: no silicon yet");
    const stats = [
      ["200", "hypothesis tests pass in the functional model of the governor and a simulated 72-GPU rack (H0 to H18)"],
      ["20", "simulation tests pass on the hard-core RTL blocks, with a LibreLane flow to the open 130 nm process"],
      ["3", "proof files hold: ten core invariants and the commit-point protocol under Z3, the kill-switch cuts by max-flow (make proof)"],
      ["56", "tests pass in the software reference stack, five of them pinning OpenShell's shipped middleware contract"],
      ["75 + 12", "attacks blocked with the predicted reason code, baselines allowed; 17 of the 87 run on the OpenShell and Sentry path"],
      ["317 µs", "worst case for the halt loop to reach the last of 72 governors, against a 1 ms bound, across 39 simulated configurations"],
      ["~2 mm²", "of core logic for the governor as configured, 1.4 by 1.4 mm, inside a 10 mm² shuttle harness"],
      ["0", "merged from the first wave: four experiments built, all four sent back by the gate with findings; every review public in audit/wave-1"],
    ];
    const W = (CW - 3 * 0.25) / 4, Hh = 1.95;
    stats.forEach(([n, l], i) => {
      const x = L + (i % 4) * (W + 0.25), y = TOP + Math.floor(i / 4) * (Hh + 0.2);
      card(s, x, y, W, Hh);
      text(s, n, { x: x + 0.25, y: y + 0.12, w: W - 0.5, h: 0.8, fontSize: 40, bold: true, fontFace: "Georgia", color: C.accent1, valign: "middle" });
      text(s, l, { x: x + 0.25, y: y + 0.98, w: W - 0.5, h: 0.92, fontSize: 10.5, color: C.text1 });
    });
    analogy(s, "Everything here is model, proof, RTL simulation and circuit simulation. The two numbers that decide adoption, the real overhead and the false-halt rate, are not measured on hardware yet. Nothing has merged from the first wave; every result sits on a branch with its review attached.", "docs 18 §3; audit/wave-1", 6.0, 0.8);
    s.addNotes("Honest status. The counts are what pytest prints today: 200, 20 and 56; make proof prints all three files holding. The loop figure is hw/loop/results.md. The area is docs/04 section 11. The 75 attacks, 12 baselines and 17 OASP entries are the reference stack's sweep (results/report.md). The zero is the one to say out loud: wave 1 built four experiments and the gate sent all four back with specific findings, which is the gate doing its job.");
  }

  // ───────────────────────── 25. What the first wave found
  {
    const s = light("Status", "What the first wave found");
    await table(s, [
      ["Experiment", "Built", "What the gate found", "Where it is"],
      ["L4  trace conformance", "A trace recorder for the governor model and a replayer that drives the proven machine with the recorded events; all 200 tests' traces replay; two broken governors fail with the event named", "The replayer passed only after it was widened to accept two steps the theorem's machine lacks, a boot step and tickets burned without executing: a gap in the theorem or a liberty in the simulation. Heartbeat events were never recorded", "Revise. PR #14, waiting for a person"],
      ["L5  two gates, one policy", "The reference stack's gate and the governor's fed the same requests; 21 catalogue entries compared, 18 agree, five disagreements pinned as G1 to G5 with their inputs", "\"Ambiguity in the policy\" was claimed without reading the policy document; one of the five points at a bug in the governor model; 21 of 87 is not the whole catalogue", "Revise. PR #15, waiting for a person"],
      ["H1  the lanes fixtures", "Signed fixtures for every message the three repositories exchange, and the checker the governor model runs; make lanes passes; the catalogue exported as 87 entries", "The governor's envelope (16-character signer, hex signature, no public key) does not match the lanes contract (8, base64, embedded key): two repositories that were supposed to agree on the wire format did not. Now a failing test instead of a surprise", "Revise. PR #17, waiting for a person"],
      ["YB-0052  the observer's evaluation set", "134 labelled gate-typed requests in six hazard families, a scorer with bootstrap intervals, a length-only and a keyword baseline, a pre-registration note; 36 tests", "The ten percent miss budget was the agent's, not the rulebook's; the keyword baseline overlaps the observer's vocabulary; no weighting sweep, so the disproof condition cannot be evaluated; the overt rows named real hazards, which this program forbids", "Revise. In revision on the Mac's local model"],
    ], { colW: [2.0, 3.6, 4.3, 2.233], fontSize: 10.5, availH: 4.35, icons: ["FiActivity", "FiGitMerge", "FiLink", "FiEye"] });
    analogy(s, "The wave cost a few bucks and a quarter of an hour, and the gate, the backups and the second reader run on a Mac mini on my desk, with the local model taking the revisions. Nothing merges until a person says so.", "Part 5; docs 21; audit/wave-1/REPORT.md", 6.05, 0.8);
    s.addNotes("Every line is from the wave's report and the reviews in audit/wave-1, and Part 5 tells the same story in prose. Two findings matter beyond the experiments themselves: the simulation takes steps the theorem does not model, which is exactly what L4 was built to flush out; and two repositories that were supposed to agree on a wire format did not, which is now a failing test. The YB-0052 last finding, real hazard names in the overt rows, is the one I should never have needed a reviewer for.");
  }

  // ───────────────────────── 26. The road to a chip we cannot fab
  {
    const s = light("Status", "The road to a chip we cannot fab: five stages");
    const stages = [
      ["1", "Prove or disprove, in software", "Every invariant proven (L1 to L3); the simulation conforming to the proven machine (L4); two gates reading one rulebook the same way (L5); no check-removing mutant alive (L6); every physical path accounted for (P2); a witness quorum under the hazard budget; overhead under one percent (N1); a third independent audit", "Now. Proofs hold; wave 1 ran; nothing merged yet", C.accent1],
      ["2", "Design the chip to fit NVIDIA's boards", "Register map, mailbox, policy image, request and ticket formats frozen; every block in RTL with its invariants; the module's interface to a DC-SCM 2.x host board and to the baseboard connector, pin by pin; P2 with no unaccounted row that is not marked NDA", "Hard-core blocks in Amaranth with 20 tests and generated Verilog; pinout and rack reference exist", C.text2],
      ["3", "Run the tests and the proofs on the chip", "The invariants proven again on the RTL with a model checker; the netlist shown equivalent; the whole catalogue driven into the full-chip RTL with the same reason codes; gate-level simulation with timing; the halt loop measured on a bench loop", "After stage 2", C.accent3],
      ["4", "Finish the design for a foundry", "The tape-out checklist in docs/08 ticked: synthesis, timing at three corners, DRC, LVS, antenna, IR drop, the GDS on the shuttle template; a package with the hash of every file, reproducible by make gds", "LibreLane flow to sky130 exists for the core; signoff open", C.accent3],
      ["5", "Stop, and run it anyway", "The full-chip RTL, the gate-level netlist and an FPGA beside a real GPU all run the same catalogue with the same answers; the three cost numbers and the false-halt rate measured over weeks", "The last thing that can disprove the chip without a fab. Then a shuttle slot is someone else's decision", C.accent3],
    ];
    const W = (CW - 4 * 0.22) / 5, Hh = 4.15;
    stages.forEach(([n, h, done, stands, col], i) => {
      const x = L + i * (W + 0.22);
      card(s, x, TOP, W, Hh);
      s.addShape(pres.ShapeType.rect, { x, y: TOP, w: W, h: 0.09, fill: { color: col }, line: { color: col, width: 0 }, objectName: "stage colour" });
      text(s, n, { x: x + 0.2, y: TOP + 0.18, w: 0.5, h: 0.5, fontSize: 26, bold: true, fontFace: "Georgia", color: col });
      text(s, h, { x: x + 0.7, y: TOP + 0.2, w: W - 0.85, h: 0.6, fontSize: 11.5, bold: true, valign: "middle" });
      text(s, "DONE MEANS", { x: x + 0.2, y: TOP + 0.9, w: W - 0.4, h: 0.22, fontSize: 8, bold: true, color: C.accent1 });
      text(s, done, { x: x + 0.2, y: TOP + 1.12, w: W - 0.4, h: 2.05, fontSize: 9, color: C.text1 });
      text(s, "WHERE IT STANDS", { x: x + 0.2, y: TOP + 3.2, w: W - 0.4, h: 0.22, fontSize: 8, bold: true, color: C.accent1 });
      text(s, stands, { x: x + 0.2, y: TOP + 3.42, w: W - 0.4, h: 0.7, fontSize: 9, bold: true, color: C.text2 });
    });
    analogy(s, "If an experiment kills the chip as designed, that is the result, and it is the reason to do this in software first. If the design survives all twenty, the next post is about an FPGA.", "docs 22; Part 5", 5.95, 0.8);
    s.addNotes("docs/22, the whole program in one place. The goal has not moved: prove or disprove; if it survives, design the chip in software to fit NVIDIA's boards through documented interfaces; run the tests and proofs on the chip; finish it to the point a foundry could take it; then stop, because nobody is handing me a mask set, and run it anyway in RTL, in gates and on an FPGA. Two walls at the end: the NDA rows in P2 and the fab. Both are someone else's decision, and the package will be sitting there, public, with its hashes, when they make it.");
  }

  // ───────────────────────── 27. Challenges (plain)
  pres.addSection({ title: "Challenges" });
  {
    const s = light("Challenges", "The challenges, stated plainly");
    const hops = [["The model", "no authority needed", C.background2, C.text1], ["The runtime", "asks for a ticket", C.background2, C.text1], ["The governor", "full authority: signs or refuses", C.text2, C.background1], ["The network", "partial: the door, not the conversation", C.accent2, C.background1], ["The bank", "none, unless it checks the stamp", H.lt1, C.text1]];
    const hw = (CW - 4 * 0.45) / 5, hy = TOP + 0.05, hh = 0.95;
    hops.forEach(([h, b, fill, fg], i) => {
      const x = L + i * (hw + 0.45);
      s.addShape(pres.ShapeType.roundRect, { x, y: hy, w: hw, h: hh, rectRadius: 0.08, fill: { color: fill }, line: { color: i === 4 ? C.accent4 : fill, width: i === 4 ? 1.5 : 0 }, objectName: "hop " + i });
      text(s, h, { x: x + 0.15, y: hy + 0.12, w: hw - 0.3, h: 0.35, fontSize: 14, bold: true, color: fg });
      text(s, b, { x: x + 0.15, y: hy + 0.48, w: hw - 0.3, h: 0.45, fontSize: 11, color: fg });
      if (i < 4) arrow(s, x + hw + 0.06, hy + hh / 2, x + hw + 0.39, hy + hh / 2, H.dk2, 2);
    });
    text(s, "Reach: the governor's authority ends at the last device that verifies its signature. A payment system is two or three hops away and has never heard of it.", { x: L, y: hy + hh + 0.12, w: CW, h: 0.4, fontSize: 12.5, italic: true, color: C.text2 });
    const items = [
      ["FiEyeOff", "Meaning", "The chip guarantees an observer is always invoked. It cannot make the observer right about a disguised request. The miss rate has a set and a scorer now, and no number yet."],
      ["FiAlertTriangle", "False halts", "The first support ticket will read: the governor halted my rack. The rate is not measured yet, and a person who sees a hundred holds a day signs the hundred-and-first unread."],
      ["FiServer", "The levers, and the NDA", "Reset is grouped on today's HGX board; the per-module signals sit in a design guide under NDA. The retrofit case adds: can the BMC slot drive them, and what else can undo them."],
      ["FiClock", "Cost", "One P-384 signature costs 17 ms on the OTBN engine. Batching keeps it under one percent in the model, not yet in silicon."],
      ["FiMapPin", "Coverage and people", "A device nobody wired through a gate is not in the cut. A person is an effector no chip gates: a model that talks someone into wiring the money has routed around everything here."],
      ["FiKey", "Governance and adoption", "Who holds the quorum keys and how far apart they must be, whose policy governs a shared rack, and the first device maker to check a stamp. The integrated tier needs NVIDIA."],
    ];
    const W = (CW - 2 * 0.4) / 3, Hh = 1.2, iy = hy + hh + 0.68;
    for (let i = 0; i < items.length; i++) {
      const x = L + (i % 3) * (W + 0.4), y = iy + Math.floor(i / 3) * (Hh + 0.15);
      await circleIcon(s, items[i][0], x, y + 0.05, 0.56, C.accent1, H.lt1);
      text(s, items[i][1], { x: x + 0.72, y, w: W - 0.75, h: 0.35, fontSize: 14, bold: true });
      text(s, items[i][2], { x: x + 0.72, y: y + 0.37, w: W - 0.75, h: 0.88, fontSize: 10.5, color: C.text1 });
    }
    analogy(s, "The perimeter firewall decides whether the packet leaves; it does not decide what the server on the far side does with it. The answer is to move the credential behind a ticket-checking adapter, not to reach through the bank.", "docs 18, section 5", 5.95, 0.85);
    s.addNotes("The hop chain is the picture for the deepest challenge, from docs/18 section 5. Authority is full at the governor, partial at the network, and zero at a bank that has never heard of the stamp. Two of the six are the ones no theorem removes, from docs/23: coverage, and people. The answer to reach, on the next slide, is to move the credential rather than reach through the bank.");
  }

  // ───────────────────────── 28. Challenges (technical)
  {
    const s = light("Challenges", "Challenges, technically: mechanism, status");
    await table(s, [
      ["Challenge", "What the design does", "Status"],
      ["Reach: a payment system two or three hops out", "A: the comparator in the device. B: move the credential behind a ticket-checking adapter, so the model's runtime never holds the API key. C: open the DPU flow to the provider only under a live ticket. D: always the signed record", "A and C modelled and tested (H6, H2, H17). B is a pattern the endpoint model already expresses; the three-hop payment narration is the next piece of work"],
      ["Meaning: observers can be fooled", "Observer always invoked, cannot be impersonated, separate from the model; hazard classes, legibility floor, session hazard budget, TRNG audit sampling with escrow; two witnesses required for high-authority actions", "Guarantees tested (H17, H18). The evaluation set exists (YB-0052, in revision); the miss rate is not measured, and the budget it is measured against must come from the rulebook, not from an agent"],
      ["Theorem to simulation", "L4 replays every test's trace through the proven machine; L5 compares the reference gate and the governor on the catalogue", "The replayer was widened to accept a boot step and burned tickets the theorem lacks; the theorem gains the steps or the simulation loses them. 18 of 21 compared entries agree; five pinned, not yet called bug or ambiguity"],
      ["False halts", "Loop beacon inside the signed heartbeat; loss of current declared after two sense periods (debounce); a jumpered governor caught within two heartbeats; FMEA", "Modelled (H11) and simulated (ngspice). Not measured on hardware (N2)"],
      ["Levers on HGX, and the retrofit", "Per-slot SMBus, power brake, PERST#, PWR_EN at the connector; grouped reset accepted as coarser; the evidence register names what is verified; P2 now records, per lever, whether a module in the DC-SCM slot can drive it and what else on the board can undo it", "Evidence register done. Design guide under NDA still needed; the NDA rows stay marked, not guessed"],
      ["Cost", "P-384 on OTBN at 1,697,985 cycles (17 ms); one signature per 50 ms window; engine 34 percent busy batched, 272 percent unbatched; firmware share under 0.1 percent of GPU time", "Modelled (H9). Silicon or FPGA measurement: open (N1, N3)"],
      ["Governance and adoption", "k-of-n quorum with keys outside vendor and operator (G8); partitions and per-rule approvers; integrated-tier asks written; borrowed from flexHEG as questions 15 and 16: the supply chain and enclosure as a condition of trust, a multilateral root", "Two tenants with two quorums on one baseboard: not designed. Integrated tier: needs NVIDIA. Supply-chain assumption and the key-holding arrangement: not written yet"],
    ], { colW: [2.4, 5.5, 4.233], fontSize: 10.5, availH: 5.15, icons: ["FiGitBranch", "FiEyeOff", "FiActivity", "FiAlertTriangle", "FiServer", "FiClock", "FiKey"] });
    s.addNotes("For each challenge, the mechanism and its status, from docs/18 sections 5 to 8b, docs/23 and the wave-1 reviews. The status column is the honest part: modelled is not measured, the theorem has gaps the simulation exposed, and three of the seven end in an ask.");
  }

  // ───────────────────────── 29. Prior art
  {
    const s = light("Challenges", "Prior art, and what is different here");
    await table(s, [
      ["Work", "What it governs, and how", "Where it sits"],
      ["flexHEG, Part I (Petrie, Aarne, Ammann, Dalrymple; ARIA, April 2025; arXiv 2506.15093)", "Compute: each AI chip inside a tamper-proof enclosure with an open guarantee processor that signs claims about use (training compute, workload, location) and can enforce a quorum-signed ruleset; blocks without a periodic signed update; tamper wipes the keys", "A new chip and a new package around the GPU"],
      ["Secure, Governable Chips (CNAS, January 2024); RAND on hardware-enabled mechanisms", "Export control and compute accounting", "Proposals"],
      ["A feasibility taxonomy (Ansari, University of Chester, April 2026; arXiv 2604.04712)", "Twenty hardware-level mechanisms sorted into monitoring, verification and enforcement, each on a four-tier readiness scale; hardware-embedded enforcement still at the research stage", "A survey"],
    ], { colW: [2.9, 3.9, 1.5], fontSize: 10.5, availH: 4.3 });
    const x2 = L + 8.3 + 0.3, w2 = R - x2;
    card(s, x2, TOP, w2, 4.3, C.text1);
    text(s, "What is different here", { x: x2 + 0.25, y: TOP + 0.18, w: w2 - 0.5, h: 0.35, fontSize: 13, bold: true, fontFace: "Georgia", color: C.accent6 });
    text(s, bullets([
      "Actions, not compute: the payment, the message, the release, the weight export, at the moment they leave the rack",
      "A module on the board the server already has, through the connector it already uses; asks NVIDIA for firmware and software, not silicon; goes into installed racks",
      "The stamp is checked again by the device that acts, so authority does not depend on the host in between",
      "Witnesses have a measured miss rate and are never the lock; a person with a key clears the holds",
      "Built and being tested: 200 model tests, 20 RTL tests, three proof files, a catalogue, a public program with disproof conditions",
    ], 10), { x: x2 + 0.25, y: TOP + 0.6, w: w2 - 0.5, h: 3.6, fontSize: 10, color: C.background1 });
    analogy(s, "Same mechanisms, because they are the right mechanisms: an open processor beside the GPU, rules signed k of n by people the model cannot reach, a heartbeat that fails closed. Borrowed, as questions 15 and 16: the supply chain and the enclosure as a condition of trust, and a multilateral root.", "docs 18 §8b", 6.0, 0.85);
    s.addNotes("Anyone from a lab or from NVIDIA will ask this in the first five minutes. The design is a cousin of the flexHEG work, not a stranger to it, and it says so. The differences are the point: it governs actions rather than compute, it is an add-on rather than an enclosure, the device checks the stamp again, the witnesses are measured, and it is a repository with tests rather than a proposal. What it has not done yet, and should, is written down as two open questions with what would settle each.");
  }

  // ───────────────────────── 30. Help (plain)
  pres.addSection({ title: "What I need" });
  {
    const s = light("What I need", "What I need to prove or disprove the thesis");
    const asks = [
      ["FiBriefcase", "A server maker to talk to", "About the management-card slot, the HGX design guide, and whether a module in the BMC slot can drive the levers."],
      ["FiHardDrive", "A device maker willing to check a ticket", "A functional-safety vendor, or whoever runs the tools an agent calls."],
      ["FiActivity", "A lab with a rack and an FPGA", "To measure the real overhead and the false-halt rate over weeks."],
      ["FiTarget", "A red team", "To attack the release gate and the observers with disguised requests."],
      ["FiUsers", "Chip designers and an auditor", "To tear the design apart before any tape-out."],
    ];
    const W = (CW - 4 * 0.25) / 5, Hh = 3.4;
    for (let i = 0; i < 5; i++) {
      const x = L + i * (W + 0.25);
      card(s, x, TOP, W, Hh);
      await circleIcon(s, asks[i][0], x + 0.25, TOP + 0.3, 0.7, C.accent1, H.lt1);
      text(s, asks[i][1], { x: x + 0.25, y: TOP + 1.2, w: W - 0.5, h: 0.9, fontSize: 14, bold: true });
      text(s, asks[i][2], { x: x + 0.25, y: TOP + 2.15, w: W - 0.5, h: 1.2, fontSize: 11.5, color: C.text1 });
    }
    text(s, "And anyone with a terminal: ./run.sh in both repositories, make proof, and audit/PROMPT.md for a model that wrote none of this. A no is informative.", { x: L, y: TOP + 3.55, w: CW, h: 0.4, fontSize: 12, italic: true, color: C.text2 });
    analogy(s, "Going to hardware and then tape-out is so expensive that we need to be 1000 percent sure in the pre-hardware phase. These five are what proving, or disproving, the design takes before that.", "the program's own rule", 5.75, 0.85);
    s.addNotes("Five asks in plain words, plus the standing one: run it. Each ask maps to a specific open question on the next slide, and several would disprove the thesis as stated if the answer is no.");
  }

  // ───────────────────────── 31. Help (technical)
  {
    const s = light("What I need", "What I need, technically: who, what, and why");
    await table(s, [
      ["Who", "What I need", "What it settles"],
      ["A server OEM", "The management-module slot; the HGX design guide under NDA; the connector pinout; the retrofit question per lever", "Whether per-module levers reach the connector and the BMC slot. If not, the rack tier is coarser than the design says"],
      ["NVIDIA", "Seven firmware asks: NSM port-disable semantics, per-GPU reset, buffer-class checkers in the copy engines and peer MMU; nothing from the silicon", "The integrated tier; whether the recorded gap (H2b) can be closed from inside the GPU"],
      ["An endpoint partner", "A device or tool gateway that verifies the ticket: P-384 signature, typed fields, epoch, freshness", "Whether the comparator works outside the model. If nobody will check the stamp, the thesis fails in practice"],
      ["A lab with an HGX or NVL rack", "An FPGA governor beside a real GPU for weeks", "The real overhead against the one percent goal (G6); the false-halt rate; the loop beacon in the field"],
      ["A model lab's red team", "Disguised requests against the release gate and the observers", "The size of the semantic residual; whether a quorum of observers is enough"],
      ["Chip designers, an auditor", "Review of the RTL, the firmware plan and the proof-assumption list; formal proofs of the block invariants (L7)", "Verification before tape-out"],
      ["Models that wrote none of this", "Codex and Gemini run audit/PROMPT.md: reproduce every number, find the change that makes each test fail, name what the disproof conditions required and nobody tested", "Whether the program's own checks are complete"],
    ], { colW: [2.2, 3.2, 3.2], fontSize: 10.5, availH: 5.1, icons: ["FiBriefcase", "FiCpu", "FiHardDrive", "FiActivity", "FiTarget", "FiUsers", "FiSearch"] });
    const dx = L + 8.6 + 0.33, dw = R - dx;
    card(s, dx, TOP, dw, 5.1, C.text1);
    text(s, "What would disprove it", { x: dx + 0.3, y: TOP + 0.25, w: dw - 0.6, h: 0.45, fontSize: 14, bold: true, fontFace: "Georgia", color: C.accent6 });
    text(s, bullets([
      "No device that acts will verify a ticket",
      "The levers do not reach the baseboard connector, or the BMC slot",
      "False halts at a rate operators will not accept",
      "Measured overhead above one percent after batching",
      "Observers miss disguised requests too often for the hazard cases",
      "Nobody will hold the quorum keys",
      "A single network node that every AI on Earth depends on, the laptop in the basement included",
    ], 11.5), { x: dx + 0.3, y: TOP + 0.9, w: dw - 0.6, h: 4.1, fontSize: 11.5, color: C.background1 });
    s.addNotes("The asks by who can grant them, from docs/18 sections 8 and 9 and docs/21 for the outside audit. The right-hand panel is the falsification list: if any of those seven comes true, the design as written does not hold, and we should know early. The last one is Part 6's standing offer.");
  }

  // ───────────────────────── 32. Close: the project in one plain sentence
  pres.addSection({ title: "Close" });
  {
    const s = dark("Close", "In one sentence", "A separate safety chip beside every AI GPU that checks each action the AI attempts against rules signed by people the AI cannot influence, stamps the allowed ones so the devices that carry them out can verify the stamp themselves, and cuts the power when something is wrong.");
    text(s, [
      { text: "There is no kill switch. There are gates, at the ends. The AI can think whatever it likes; it cannot act without the stamp, and it cannot forge one.", options: { breakLine: true } },
      { text: "Added to the server's own boards. Nothing changes in the GPU or in CUDA." },
    ], { x: L, y: 5.2, w: 8.4, h: 0.95, fontSize: 14, italic: true, color: C.accent1, paraSpaceAfter: 4 });
    text(s, [
      { text: "github.com/YobieBenjamin: safety-governor · hardware-and-silicon · safety · autonomic-graph-regulation · Watermark", options: { breakLine: true } },
      { text: "The Chip That Says No, parts 1 to 6; design documents 00 to 24; START-HERE.md is the route to check the work", options: { color: C.accent3 } },
    ], { x: L, y: 6.15, w: 9.5, h: 0.6, fontSize: 11, color: C.accent6 });
    s.addNotes("Close on the plain sentence: what it is, what it does, what it can stop. Then the two lines under it. The repositories hold the model, the proofs, the tests, the RTL, the circuit simulation, the experiment program and the audit packets; the blog series is the plain-English route in, and START-HERE.md is the route for anyone who wants to check the work rather than take my word for it.");
  }

  await pres.writeFile({ fileName: OUT });
  if (applyTheme) await applyTheme(OUT, THEME);
  console.log("wrote", OUT, "slides", slideNo);
}

main().catch((e) => { console.error(e); process.exit(1); });

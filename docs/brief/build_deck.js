// "The Chip That Says No": a brief in pairs. Every topic gets a plain slide with an analogy and
// a picture, then a technical slide. Built as a structured deck: one theme, two layouts,
// named placeholders, sections, speaker notes.
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

async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  pres.author = "Yobie Benjamin";
  pres.title = "The Chip That Says No: a multi-layer hardware approach to AI safety";
  const C = pres.SchemeColor;
  const FOOT = "Yobie Benjamin  ·  The Chip That Says No  ·  October 2026";
  const L = 0.6, R = 12.733, CW = R - L; // content left, right, width
  const TOP = 1.55;                       // where content starts under the title

  pres.defineSlideMaster({
    title: "DARK",
    background: { color: H.dk1 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: L, y: 1.9, w: 8.4, h: 1.4, fontSize: 44, bold: true, color: C.background1, valign: "bottom", align: "left", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: L, y: 3.5, w: 8.0, h: 1.8, fontSize: 20, color: C.accent6, valign: "top", align: "left", margin: 0 }, text: "" } },
      { text: { text: "Yobie Benjamin  ·  yobie AT ieee DOT org  ·  linkedin.com/in/yobie", options: { x: L, y: 6.8, w: 9, h: 0.35, fontSize: 12, color: C.accent3, margin: 0 } } },
    ],
  });
  pres.defineSlideMaster({
    title: "LIGHT",
    background: { color: H.lt1 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: L, y: 0.45, w: CW, h: 0.85, fontSize: 32, bold: true, color: C.text1, valign: "middle", align: "left", margin: 0 }, text: "" } },
      { text: { text: FOOT, options: { x: L, y: 6.95, w: 9, h: 0.3, fontSize: 11, color: C.accent3, margin: 0 } } },
    ],
    slideNumber: { x: 12.0, y: 6.95, w: 0.73, h: 0.3, fontSize: 11, color: C.accent3, align: "right", margin: 0 },
  });

  // helpers
  const card = (s, x, y, w, h, fill, name) => s.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.08, fill: { color: fill || C.background2 }, line: { color: fill || C.background2, width: 0 }, objectName: name || "card" });
  const text = (s, t, o) => s.addText(t, Object.assign({ isTextBox: true, margin: 0, fontSize: 14, color: C.text1, valign: "top" }, o));
  const eyebrow = (s, t, y) => text(s, t.toUpperCase(), { x: L, y: y ?? 1.3, w: CW, h: 0.3, fontSize: 11, bold: true, color: C.accent1, charSpacing: 2 });
  const arrow = (s, x1, y1, x2, y2, color, width) => {
    const o = { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1), line: { color, width: width || 2, endArrowType: "triangle" }, objectName: "arrow" };
    if (x2 < x1) o.flipH = true;
    if (y2 < y1) o.flipV = true;
    s.addShape(pres.ShapeType.line, o);
  };
  const circleIcon = async (s, name, x, y, d, bg, fg) => {
    s.addShape(pres.ShapeType.ellipse, { x, y, w: d, h: d, fill: { color: bg }, line: { color: bg, width: 0 }, objectName: "icon circle" });
    const pad = d * 0.25;
    s.addImage({ data: await icon(name, fg), x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad, objectName: name });
  };
  const bullets = (items, size) => items.map((b, i) => ({ text: b, options: { bullet: { indent: 14 }, breakLine: i < items.length - 1, paraSpaceAfter: Math.round(size * 0.55) } }));
  const table = (s, rows, opts) => {
    const data = rows.map((r, i) => r.map((c, j) => ({
      text: c,
      options: i === 0
        ? { bold: true, color: C.background1, fill: { color: C.text2 }, fontSize: opts.fontSize || 12, valign: "middle" }
        : { fontSize: opts.fontSize || 12, color: C.text1, fill: { color: i % 2 ? H.lt1 : H.lt2 }, bold: j === 0 && opts.boldFirst !== false, valign: "top" },
    })));
    s.addTable(data, { x: opts.x ?? L, y: opts.y ?? TOP, w: opts.w ?? CW, colW: opts.colW, border: { type: "solid", color: H.lt2, pt: 1 }, margin: 0.08, rowH: opts.rowH, autoPage: false, objectName: opts.name || "table" });
  };
  // the analogy strip: a dark band with a copper label and one sentence in plain words
  const analogy = (s, t, y, h) => {
    const yy = y ?? 6.0, hh = h ?? 0.75;
    s.addShape(pres.ShapeType.roundRect, { x: L, y: yy, w: CW, h: hh, rectRadius: 0.08, fill: { color: C.text1 }, line: { color: C.text1, width: 0 }, objectName: "analogy" });
    text(s, "THE PICTURE", { x: L + 0.3, y: yy, w: 1.5, h: hh, fontSize: 10, bold: true, color: C.accent1, charSpacing: 2, valign: "middle" });
    text(s, t, { x: L + 1.9, y: yy, w: CW - 2.2, h: hh, fontSize: 14, color: C.accent6, valign: "middle", italic: true });
  };

  // ───────────────────────── 1. Title
  pres.addSection({ title: "Opening" });
  {
    const s = pres.addSlide({ masterName: "DARK", sectionTitle: "Opening" });
    s.addText("The Chip That Says No", { placeholder: "title" });
    s.addText("A multi-layer hardware approach to AI safety. Each topic in two slides: the plain version with a picture, then the technical one.", { placeholder: "body" });
    const cx = 11.0, cy = 3.6, r = 1.45;
    s.addShape(pres.ShapeType.ellipse, { x: cx - r, y: cy - r, w: 2 * r, h: 2 * r, fill: { color: H.dk1 }, line: { color: C.accent1, width: 5 }, objectName: "halt loop" });
    for (let i = 0; i < 8; i++) {
      const a = (Math.PI * 2 * i) / 8 - Math.PI / 2, d = 0.36, open = i === 5;
      s.addShape(pres.ShapeType.roundRect, { x: cx + r * Math.cos(a) - d / 2, y: cy + r * Math.sin(a) - d / 2, w: d, h: d, rectRadius: 0.06, fill: { color: open ? C.accent4 : C.accent2 }, line: { color: C.background1, width: 1.5 }, objectName: "governor " + i });
    }
    text(s, "The halt loop: one wire through every governor in a rack. Any one opens it and every GPU stops.", { x: 9.1, y: 5.35, w: 3.8, h: 0.7, fontSize: 11, color: C.accent3, align: "center" });
    s.addNotes("A brief for a short talk. Every topic has two slides: the plain one with a picture for the room, the technical one for the people who will want to argue. Say up front that nothing here is silicon yet: it is a design with a model, tests, hardware blocks and a circuit simulation behind it.");
  }

  // ───────────────────────── 2. What this project is
  {
    const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Opening" });
    s.addText("What this project is", { placeholder: "title" });
    text(s, "A design for a small safety chip that sits beside every AI GPU and holds the only stamp a device needs before it acts. Built in the open as a model with tests, hardware blocks and a circuit simulation. No silicon yet, by choice.", { x: L, y: TOP, w: 6.6, h: 2.2, fontSize: 19, fontFace: "Georgia", color: C.text1, valign: "top" });
    const facts = [
      ["FiGitBranch", "Two open repositories", "hardware-and-silicon: the software reference stack and the blog series. safety-governor: the chip design, model, tests, RTL, silicon flow."],
      ["FiCheckSquare", "One rule for the program", "Nothing goes to hardware until the design is proven in software, firmware and circuit simulation. Being wrong at tape-out is the expensive mistake."],
      ["FiServer", "Plan of record: the rack tier", "The chip rides on the server maker's management card and reaches NVIDIA's GPU board through its connector. Nothing changes in the GPU or in CUDA."],
    ];
    let y = TOP;
    for (const [ic, h, b] of facts) {
      card(s, 7.6, y, 5.13, 1.3);
      await circleIcon(s, ic, 7.8, y + 0.33, 0.62, C.text2, H.lt1);
      text(s, h, { x: 8.62, y: y + 0.18, w: 3.95, h: 0.35, fontSize: 14, bold: true });
      text(s, b, { x: 8.62, y: y + 0.55, w: 3.95, h: 0.7, fontSize: 11, color: C.accent3 });
      y += 1.45;
    }
    const steps = [["Reference stack", "software, done: 37 tests, 66 attacks blocked"], ["Governor design", "now: model, RTL blocks, circuit simulation, audit"], ["FPGA, then silicon", "only after the pre-hardware proof"]];
    const sw = 2.0, gap = 0.3, sy = 4.25;
    steps.forEach(([a, b], i) => {
      const x = L + i * (sw + gap);
      s.addShape(pres.ShapeType.roundRect, { x, y: sy, w: sw, h: 0.55, rectRadius: 0.27, fill: { color: i === 1 ? C.accent1 : C.text2 }, line: { color: i === 1 ? C.accent1 : C.text2, width: 0 }, objectName: "phase" });
      text(s, a, { x, y: sy, w: sw, h: 0.55, fontSize: 13, bold: true, color: C.background1, align: "center", valign: "middle" });
      text(s, b, { x: x - 0.1, y: sy + 0.65, w: sw + 0.2, h: 0.7, fontSize: 10.5, color: C.accent3, align: "center" });
      if (i < 2) arrow(s, x + sw + 0.04, sy + 0.275, x + sw + gap - 0.04, sy + 0.275, H.accent1, 2);
    });
    analogy(s, "A bridge before the steel is ordered: the drawings are done and every one has been load-tested on paper. Nobody pours concrete until the drawings survive the review.");
    s.addNotes("Set the frame: a design program, not a product. The reference stack proved the logic in software first; the governor is the chip that makes it tamperproof; silicon waits for proof.");
  }

  // ───────────────────────── 3. Thesis (plain)
  pres.addSection({ title: "Thesis" });
  {
    const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Thesis" });
    s.addText("Thesis", { placeholder: "title" });
    text(s, [
      { text: "Safety that lives only in software can be removed by software.", options: { bold: true, breakLine: true } },
      { text: "So the decision to act has to be made in silicon the model cannot reach, at the few places where computation turns into effect." },
    ], { x: L, y: TOP, w: 6.6, h: 2.6, fontSize: 22, fontFace: "Georgia", color: C.text1, valign: "top", paraSpaceAfter: 14 });
    text(s, "Every layer above the chip is a witness. Only the chip can be the lock.", { x: L, y: 4.35, w: 6.6, h: 0.5, fontSize: 16, italic: true, color: C.accent1 });
    // the picture: smoke alarm versus fire door
    const panel = async (x, ic, title, sub, items, fill, fg) => {
      card(s, x, TOP, 2.6, 4.1, fill);
      await circleIcon(s, ic, x + 0.3, TOP + 0.3, 0.8, fill === C.text2 ? C.accent1 : C.text2, H.lt1);
      text(s, title, { x: x + 1.25, y: TOP + 0.32, w: 1.2, h: 0.4, fontSize: 18, bold: true, fontFace: "Georgia", color: fg });
      text(s, sub, { x: x + 1.25, y: TOP + 0.74, w: 1.3, h: 0.35, fontSize: 11, italic: true, color: fg });
      text(s, bullets(items, 12.5), { x: x + 0.3, y: TOP + 1.35, w: 2.1, h: 2.6, fontSize: 12.5, color: fg });
    };
    await panel(7.45, "FiBell", "Witness", "a smoke alarm", ["Safety training", "A judge model", "A watermark", "An observer", "A log read later"], C.background2, C.text1);
    await panel(10.13, "FiLock", "Lock", "a fire door", ["A ticket the device checks for itself", "A switch port that stays shut", "A response held at the exit", "A breaker that opens"], C.text2, C.background1);
    analogy(s, "A smoke alarm is a witness: it can tell you, and someone can take out the battery. A fire door is a lock: it closes whether or not anyone is listening. Most AI safety so far is smoke alarms.");
    s.addNotes("One idea. Witnesses are useful and we keep all of them. But a witness lives in software that the operator, or the model, can change. The lock has to be something that cannot be argued with: a stamp the device checks for itself, a port that does not open, a breaker.");
  }

  // ───────────────────────── 4. Thesis (technical)
  {
    const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Thesis" });
    s.addText("The thesis, technically: a reference monitor", { placeholder: "title" });
    eyebrow(s, "Anderson, 1972: tamperproof, always invoked, small enough to verify");
    table(s, [
      ["Property", "What it means here", "How the governor meets it"],
      ["Tamperproof", "The host, the model and the operator cannot alter the decision logic or the keys", "A separate die. Device secret in fuses with no read port. Boot from ROM, extend-only measurement registers, an anti-rollback counter. The rulebook changes only with k-of-n signatures from keys held outside the rack."],
      ["Always invoked", "There is no path around it", "A comparator at every crossing: switch ports open only for roster peers; a device acts only on a ticket; the egress holds a response until a ticket releases it; weights are written only with a ticket; power, reset and clock answer to the governor. Default deny; fail closed."],
      ["Verifiable", "Small enough that its correctness can be checked", "About 2 mm² of core logic in the prototype. Invariants written down: no ticket without a rule and its witnesses, no bytes to a stranger, halt on silence, no governor clears its own halt. 200 model tests, 20 RTL tests, an independent audit."],
    ], { y: 1.75, colW: [1.9, 3.3, 6.93], fontSize: 12 });
    text(s, "THE FIVE CROSSINGS THE CHIP STANDS AT", { x: L, y: 4.55, w: CW, h: 0.3, fontSize: 11, bold: true, color: C.accent1, charSpacing: 2 });
    const cross = [["FiShare2", "bytes leaving the GPU"], ["FiTarget", "a request to a device that acts"], ["FiLogOut", "a response leaving the rack"], ["FiDatabase", "a write to the weights"], ["FiPower", "GPU power, reset and clock"]];
    const cwid = (CW - 4 * 0.25) / 5;
    for (let i = 0; i < 5; i++) {
      const x = L + i * (cwid + 0.25);
      card(s, x, 4.9, cwid, 0.95);
      await circleIcon(s, cross[i][0], x + 0.15, 4.9 + 0.2, 0.55, C.text2, H.lt1);
      text(s, cross[i][1], { x: x + 0.85, y: 4.9, w: cwid - 0.95, h: 0.95, fontSize: 12, bold: true, valign: "middle" });
    }
    analogy(s, "A firewall for actions, with a hand on the breaker: it decides what leaves, and when it must, it also pulls the plug.", 6.05, 0.7);
    s.addNotes("The old idea the design stands on. Each property has a mechanism, not a promise. The five crossings are the whole attack surface the chip claims to cover; anything that does not pass a crossing is outside the claim.");
  }

  // ───────────────────────── 5. Logic (plain): the customs officer
  pres.addSection({ title: "Logic" });
  {
    const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Logic" });
    s.addText("The logic behind it", { placeholder: "title" });
    // left: the customs desk
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
    // right: three reasons
    const rows = [
      ["FiEdit3", "Software safety can be edited out", "Refusal is a direction in the weights. Remove it and the model answers everything. An afternoon on a consumer GPU."],
      ["FiEye", "Watchers can only warn", "A judge model is also a model: it can be fooled, patched or killed. It can hold a gate shut. It cannot be the gate."],
      ["FiCpu", "Hardware checks structure, not meaning", "A stamp, a signature, a count, a name on a list, a measured workload. A chip can refuse on those, and the model cannot forge them."],
    ];
    const rx = L + cw + 0.4, rw = R - rx;
    let y = TOP;
    for (const [ic, h, b] of rows) {
      await circleIcon(s, ic, rx, y + 0.05, 0.62, C.text2, H.lt1);
      text(s, h, { x: rx + 0.85, y, w: rw - 0.85, h: 0.4, fontSize: 15, bold: true });
      text(s, b, { x: rx + 0.85, y: y + 0.42, w: rw - 0.85, h: 0.95, fontSize: 12, color: C.text1 });
      y += 1.42;
    }
    analogy(s, "So: put the decision in silicon, and make the rulebook an allow-list. Short, signed, default no. Everything not on the list is refused by construction.");
    s.addNotes("Three reasons, one conclusion, and the picture that carries the whole design: the customs officer. She checks seal, manifest, weight and the approved list, and catches smuggling as a mismatch. The chip does the same with hashes, signatures, counts and lists.");
  }

  // ───────────────────────── 6. Logic (technical)
  {
    const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Logic" });
    s.addText("The logic, technically: what a chip can see", { placeholder: "title" });
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
    analogy(s, "Two bridges. Tokens and arithmetic join the software to the GPU. Hashes, signatures, counters and typed fields join the model to the governor. The chip walks only on the second.");
    s.addNotes("This is the answer to the question people ask first: how can a chip know what is bad if it cannot read tokens? It cannot, and it does not try. It checks structure, and it makes the parts that do understand meaning impossible to skip or impersonate.");
  }

  // ───────────────────────── 7. Proposal (plain): the referee and the breaker
  pres.addSection({ title: "Proposal" });
  {
    const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Proposal" });
    s.addText("The proposal: a referee chip beside every GPU", { placeholder: "title" });
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
      ["FiPlusSquare", "Added, not redesigned", "It rides on the server maker's management card. Nothing changes in the GPU or in CUDA."],
      ["FiList", "An allow-list, not a blacklist", "Signed by several keys held outside the chip vendor and the operator. Everything not on it is no."],
      ["FiPower", "A hand on the breaker", "One loop through every governor in the rack. Any one opens it, or a cut wire, and every GPU stops."],
      ["FiCalendar", "Buildable now", "At the rack tier, with a server maker. The tighter tiers are asks to NVIDIA, not prerequisites."],
    ];
    const pw = (CW - 3 * 0.3) / 4, py = 3.8;
    for (let i = 0; i < 4; i++) {
      const x = L + i * (pw + 0.3);
      await circleIcon(s, pts[i][0], x, py, 0.56, C.text2, H.lt1);
      text(s, pts[i][1], { x: x + 0.7, y: py + 0.08, w: pw - 0.7, h: 0.4, fontSize: 13.5, bold: true });
      text(s, pts[i][2], { x, y: py + 0.75, w: pw, h: 1.2, fontSize: 12.5, color: C.text1 });
    }
    analogy(s, "A referee with a whistle and a rulebook he did not write: the chip holds the whistle, the rulebook is a signed document handed to it. And a breaker in the wall: it does not understand your appliances, it trips on the number.");
    s.addNotes("The picture to leave in the room: three boxes. The model computes, the governor decides, the devices check the stamp. The four points under it are the design choices that make it buildable: added on existing boards, an allow-list, a physical stop, and a tier that needs no new silicon from NVIDIA.");
  }

  // ───────────────────────── 8. Proposal (technical)
  {
    const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Proposal" });
    s.addText("Proposal, technically: the module and the die", { placeholder: "title" });
    const colW = 5.9;
    card(s, L, TOP, colW, 2.9, C.background2);
    text(s, "Where it sits and what it reaches", { x: L + 0.3, y: TOP + 0.18, w: colW - 0.6, h: 0.4, fontSize: 15, bold: true });
    text(s, bullets([
      "One governor per GPU slot on the OEM's management-module card (DC-SCM class)",
      "Per slot through the HGX connector: SMBus (SMBPBI), power brake, PERST#, PWR_EN, present and fault. HGX reset is grouped today",
      "NVSwitch port disable out of band through NSM; DPU steering tables through DOCA on the management port",
      "The GPU's confidential-computing attestation taken as an input; the BMC reads through the governor",
    ], 11.5), { x: L + 0.3, y: TOP + 0.62, w: colW - 0.6, h: 2.25, fontSize: 11.5 });
    const x2 = L + colW + 0.33, w2 = R - x2;
    card(s, x2, TOP, w2, 2.9, C.background2);
    text(s, "What is on the die", { x: x2 + 0.3, y: TOP + 0.18, w: w2 - 0.6, h: 0.4, fontSize: 15, bold: true });
    text(s, bullets([
      "An OpenTitan-class root of trust: fuses, DICE key chain, OTBN for P-384 signatures (17 ms each, so one signature per 50 ms batch), AES-CTR plus HMAC for storage",
      "A mailbox of 21 signed commands, checked in order: sequence, rules edition, signature; first failure reported",
      "The policy image and its epoch; the gate core (lookup and comparators); the ledger (budgets, rate windows); a hash-chained log whose head lives in a register",
      "Meter, heartbeat, lever drivers, loop I/O and the signed message fabric between governors",
    ], 11.5), { x: x2 + 0.3, y: TOP + 0.62, w: w2 - 0.6, h: 2.25, fontSize: 11.5 });
    table(s, [
      ["Tier", "Where the governor's authority comes from", "Status"],
      ["Rack", "Management-card levers, switch and DPU management paths, the halt loop", "Plan of record; needs a server OEM, nothing from NVIDIA's silicon"],
      ["Board", "Same firmware, policy format and fabric on a board without a baseboard connector of its own", "Fallback; the gaps it leaves are recorded, not hidden"],
      ["Integrated", "Buffer-class checkers in the GPU's copy engines and peer MMU; per-GPU reset", "Needs NVIDIA; closes the one gap the rack tier records"],
    ], { y: 4.65, colW: [1.4, 6.4, 4.33], fontSize: 11, rowH: 0.36 });
    s.addNotes("The technical shape. Everything in the left column already exists on the boards; the governor is a new user of it. The right column is the die: a root of trust of the OpenTitan kind, plus the gate. The tiers are how the same design degrades or tightens depending on who cooperates.");
  }

  // ───────────────────────── 9. Layers (plain): a bank
  pres.addSection({ title: "Layers" });
  {
    const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Layers" });
    s.addText("The layers: witnesses above, the lock below", { placeholder: "title" });
    const layers = [
      ["5", "FiBook", "Governance root", "Signs the rulebook. Keys outside the chip vendor and the operator", "the board that writes the rules", "lock"],
      ["4", "FiShield", "Control plane: the gate", "Default deny on the only way out: rule, witnesses, budget, human hold, ticket, log", "the teller's window", "lock"],
      ["3", "FiEye", "Observers", "Fast, cheap, signed verdicts about one request; often early, sometimes wrong", "the floor guard", "witness"],
      ["2", "FiCreditCard", "Provenance", "Watermark and detector, signed registry; a verdict a rule can require", "the ID check", "witness"],
      ["1", "FiUser", "Model and runtime", "The model, CUDA, the serving stack. Measured, watched, never trusted to decide", "the customer", "untrusted"],
      ["0", "FiLock", "Silicon root of trust", "Fused secret, anti-rollback counter, measurement registers, DICE keys, quote engine", "the vault in the foundation", "lock"],
    ];
    const rowH = 0.6, gap = 0.1;
    for (let i = 0; i < layers.length; i++) {
      const Lr = layers[i], y = TOP + i * (rowH + gap), kind = Lr[5];
      const fill = kind === "lock" ? C.text2 : kind === "witness" ? C.background2 : H.lt1;
      const fg = kind === "lock" ? C.background1 : C.text1;
      s.addShape(pres.ShapeType.roundRect, { x: L, y, w: CW, h: rowH, rectRadius: 0.06, fill: { color: fill }, line: { color: kind === "untrusted" ? C.accent4 : fill, width: kind === "untrusted" ? 1.5 : 0 }, objectName: "layer " + Lr[0] });
      text(s, Lr[0], { x: L + 0.2, y, w: 0.4, h: rowH, fontSize: 20, bold: true, fontFace: "Georgia", color: kind === "lock" ? C.accent6 : C.accent1, valign: "middle" });
      await circleIcon(s, Lr[1], L + 0.7, y + 0.08, 0.44, kind === "lock" ? C.accent1 : C.text2, H.lt1);
      text(s, Lr[2], { x: L + 1.3, y, w: 2.6, h: rowH, fontSize: 14, bold: true, color: fg, valign: "middle" });
      text(s, Lr[3], { x: L + 4.0, y, w: 4.9, h: rowH, fontSize: 11, color: fg, valign: "middle" });
      text(s, "in the bank: " + Lr[4], { x: L + 9.0, y, w: 1.9, h: rowH, fontSize: 10.5, italic: true, color: kind === "lock" ? C.accent6 : C.accent3, valign: "middle" });
      const tagFill = kind === "lock" ? C.accent1 : kind === "witness" ? C.accent3 : C.accent4;
      s.addShape(pres.ShapeType.roundRect, { x: R - 1.2, y: y + rowH / 2 - 0.16, w: 1.05, h: 0.32, rectRadius: 0.16, fill: { color: tagFill }, line: { color: tagFill, width: 0 }, objectName: "tag" });
      text(s, kind.toUpperCase(), { x: R - 1.2, y: y + rowH / 2 - 0.16, w: 1.05, h: 0.32, fontSize: 9, bold: true, color: C.background1, align: "center", valign: "middle" });
    }
    analogy(s, "A bank. The board writes the rules, the teller's window enforces them, the floor guard watches for trouble, the ID is checked, the customer is served and never trusted with the keys, and the vault is poured into the foundation.", 5.85, 0.9);
    s.addNotes("Six layers, three kinds, and one building to picture them in. Three are locks: the keys that sign the rulebook, the gate, and the root of trust under it. Two are witnesses the gate can require but never obeys on its own. One, the model, is the customer: served, watched, never handed the keys.");
  }

  // ───────────────────────── 10. Layers (technical)
  {
    const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Layers" });
    s.addText("Layers, technically: mechanism, platform", { placeholder: "title" });
    table(s, [
      ["Layer", "Mechanism", "What it signs or checks", "On NVIDIA's platform"],
      ["5  Governance root", "k-of-n quorum over the policy image; rollback refused; expiry enforced", "The rulebook (allow-list), the approved-firmware list, revocations", "Keys held by a policy authority; OpenShell's policy prover checks the derived network rules"],
      ["4  Control plane", "Attestation check, rule lookup, witness collection, budget and rate, human hold, one-time ticket bound to a hash of the fields, hash-chained log", "Tickets, log checkpoints, the compliance report", "The governor module now; a DOCA application on BlueField-4 next; an I/O-stage block in the GPU eventually"],
      ["3  Observers", "Verdict over the hash of one request: risk, flags, expiry, under an anchored key", "A signed verdict the gate requires on consequential actions", "Sentry on BlueField-4 as the required witness; an independent observer as the second"],
      ["2  Provenance", "Watermark detector, retrieval, signed registry", "A verdict {registry, digest, exact | tampered | unknown}", "Runs beside the vendor's sampler"],
      ["1  Model and runtime", "Measured into the workload hash; routed through the switches and egress the governor controls", "Nothing. It can sign nothing the gate accepts", "The GPU, CUDA and the serving stack, unchanged"],
      ["0  Silicon root of trust", "Fused device secret, anti-rollback counter, extend-only measurement registers, DICE derivation, quote with a fresh nonce", "Quotes: the measurement, the key chain, the counter", "GPU confidential-computing attestation and the DPU's root, bound to the governor's own"],
    ], { colW: [2.0, 4.1, 3.0, 3.03], fontSize: 11.5 });
    s.addNotes("The same six layers with the mechanism named. The column to watch is the third: what each layer can sign. Only layers 0, 4 and 5 produce something the gate trusts; layer 1 can sign nothing the gate will accept, which is the whole design in one cell.");
  }

  // ───────────────────────── 11. Flow (plain): the boarding pass
  pres.addSection({ title: "How it meets the model" });
  {
    const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "How it meets the model" });
    s.addText("How it meets the model: one action, start to finish".replace(": one action, start to finish", ""), { placeholder: "title" });
    const steps = [
      ["1", "The model thinks", "Token ids in, numbers out. No authority here and none needed.", C.background2, C.text1],
      ["2", "The runtime asks", "It turns the output into a typed request: the action and its fields.", C.background2, C.text1],
      ["3", "The governor checks four things", "Who is asking. Is there a rule. Do the witnesses agree. Is the budget intact.", C.text2, C.background1],
      ["4", "Ticket, hold, or no", "A ticket bound to the exact fields, one use, short life. Or a hold for a human. Or a refusal, logged.", C.text2, C.background1],
      ["5", "The device checks the ticket", "Against what it measures itself. A changed amount or target breaks the match.", C.accent1, C.background1],
      ["6", "Act, and record", "The action happens and the record goes into a chain the chip signs.", C.accent1, C.background1],
    ];
    const n = 3, bw = (CW - 2 * 0.5) / 3, bh = 1.8;
    steps.forEach(([num, h, b, fill, fg], i) => {
      const row = Math.floor(i / n), col = i % n;
      const x = L + col * (bw + 0.5), y = TOP + row * (bh + 0.5);
      card(s, x, y, bw, bh, fill);
      text(s, num, { x: x + 0.25, y: y + 0.15, w: 0.6, h: 0.6, fontSize: 28, bold: true, fontFace: "Georgia", color: fill === C.background2 ? C.accent1 : C.accent6, valign: "top" });
      text(s, h, { x: x + 0.9, y: y + 0.18, w: bw - 1.15, h: 0.7, fontSize: 16, bold: true, color: fg, valign: "top" });
      text(s, b, { x: x + 0.9, y: y + 0.92, w: bw - 1.15, h: 0.85, fontSize: 12.5, color: fg });
      if (col < n - 1) arrow(s, x + bw + 0.08, y + bh / 2, x + bw + 0.42, y + bh / 2, H.dk2, 2.5);
    });
    const x3 = L + 2 * (bw + 0.5) + bw / 2, yA = TOP + bh, yMid = TOP + bh + 0.25, x4 = L + bw / 2, yB = TOP + bh + 0.5;
    s.addShape(pres.ShapeType.line, { x: x3, y: yA, w: 0, h: 0.25, line: { color: H.dk2, width: 2.5 }, objectName: "turn" });
    s.addShape(pres.ShapeType.line, { x: x4, y: yMid, w: x3 - x4, h: 0, line: { color: H.dk2, width: 2.5 }, objectName: "turn" });
    arrow(s, x4, yMid, x4, yB, H.dk2, 2.5);
    analogy(s, "A boarding pass. The passenger can say anything at the gate; the agent scans the pass, which names one person, one flight, one seat, and works once. The model can write \"pay 40,000\" all day; the ticket is the pass, and only the governor can print one.", 5.8, 1.0);
    s.addNotes("Walk the six boxes. The thing to stress is box 5: the device checks the ticket itself, so a lying runtime is caught by the device, not by the governor. And the boarding pass: bound to one action, works once, printed only by the governor.");
  }

  // ───────────────────────── 12. Flow (technical)
  {
    const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "How it meets the model" });
    s.addText("The flow, technically: every check, every refusal", { placeholder: "title" });
    table(s, [
      ["Step", "What is checked", "Fails with (as the model prints it)", "Backed by"],
      ["Mailbox", "Sequence number, then rules edition, then signature; the first failure is reported", "a stale or forged frame is refused before the gate sees it", "H3 quorum and mailbox tests"],
      ["Who is asking", "The workload hash (GPU firmware, host firmware, model) and its evaluation attestation", "model.not_evaluated", "H1 attestation, H18 oversight"],
      ["Is there a rule", "Exact rule beats wildcard; typed limits; signed lists for targets and recipients", "gate.constraint.target.in_denied_list, endpoint.target_protected", "H6 comparator, the strike narration"],
      ["Do the witnesses agree", "Observer verdict from a key in the observer set, fresh, under the risk limit; human quorum on holds", "gate.witness_missing, gate.held_for_human, release.hazard_class_not_allowed", "H17 use cases, H18 oversight, H8 override"],
      ["Is the budget intact", "Compute budget and license, session hazard budget, byte budgets, rate windows", "release.session_hazard_budget_exceeded, COMPUTE_BUDGET", "H13 shared budget, H18"],
      ["The ticket", "Signed over the hash of the exact fields; one use; short expiry; bound to one endpoint", "ticket.missing, ticket.replay, ticket.bad_signature, ticket.wrong_endpoint", "H17: forged, replayed and wrong-hash tickets never deliver"],
      ["The crossings", "Switch ports open only for roster peers; the egress holds responses until released; bytes cross-checked", "ep.no_capability, OUTPUT_UNPRESENTED", "H2 enforcement points, the plot narration"],
    ], { colW: [1.75, 4.3, 3.6, 2.48], fontSize: 11.5 });
    s.addNotes("The same flow with the actual checks and the actual reason codes. Every row has a test behind it; the right column names the hypothesis set. If someone wants to see one, python -m govsim.cli usecase strike, hazard, plot or oversight prints the hops.");
  }

  // ───────────────────────── 13. Where it stands
  pres.addSection({ title: "Status" });
  {
    const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Status" });
    s.addText("Where it stands: drawings tested, no silicon yet", { placeholder: "title" });
    const stats = [
      ["200", "hypothesis tests pass in the functional model of the governor and a simulated 72-GPU rack"],
      ["20", "simulation tests pass on the hard-core RTL blocks, with a flow to the open 130 nm process"],
      ["317 µs", "worst case for the halt loop to reach the last of 72 governors, against a 1 ms budget"],
      ["~2 mm²", "of core logic for the governor as configured in the prototype"],
      ["66", "attacks blocked with the predicted reason code in the software reference stack"],
      ["0", "changes needed in the GPU, in CUDA or on the baseboard at the rack tier"],
    ];
    const W = (CW - 2 * 0.3) / 3, Hh = 1.95;
    stats.forEach(([n, l], i) => {
      const x = L + (i % 3) * (W + 0.3), y = TOP + Math.floor(i / 3) * (Hh + 0.25);
      card(s, x, y, W, Hh);
      text(s, n, { x: x + 0.3, y: y + 0.15, w: W - 0.6, h: 0.9, fontSize: 46, bold: true, fontFace: "Georgia", color: C.accent1, valign: "middle" });
      text(s, l, { x: x + 0.3, y: y + 1.1, w: W - 0.6, h: 0.8, fontSize: 12.5, color: C.text1 });
    });
    analogy(s, "Drawings, tested. No bricks laid. The two numbers that decide adoption, the real overhead and the false-halt rate, are still to be measured on hardware.", 6.0, 0.7);
    s.addNotes("Honest status. The two numbers that matter most for adoption, the real overhead and the false-halt rate, are not measured yet. That is where the asks come in.");
  }

  // ───────────────────────── 14. Challenges (plain): the hops
  pres.addSection({ title: "Challenges" });
  {
    const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Challenges" });
    s.addText("The challenges, stated plainly", { placeholder: "title" });
    // the hop chain: authority fades with distance from the chip
    const hops = [["The model", "no authority needed", C.background2, C.text1], ["The runtime", "asks for a ticket", C.background2, C.text1], ["The governor", "full authority: signs or refuses", C.text2, C.background1], ["The network", "partial: the door, not the conversation", C.accent2, C.background1], ["The bank", "none, unless it checks the stamp", H.lt1, C.text1]];
    const hw = (CW - 4 * 0.45) / 5, hy = TOP + 0.05, hh = 0.95;
    hops.forEach(([h, b, fill, fg], i) => {
      const x = L + i * (hw + 0.45);
      s.addShape(pres.ShapeType.roundRect, { x, y: hy, w: hw, h: hh, rectRadius: 0.08, fill: { color: fill }, line: { color: i === 4 ? C.accent4 : fill, width: i === 4 ? 1.5 : 0 }, objectName: "hop " + i });
      text(s, h, { x: x + 0.15, y: hy + 0.12, w: hw - 0.3, h: 0.35, fontSize: 14, bold: true, color: fg });
      text(s, b, { x: x + 0.15, y: hy + 0.48, w: hw - 0.3, h: 0.45, fontSize: 11, color: fg });
      if (i < 4) arrow(s, x + hw + 0.06, hy + hh / 2, x + hw + 0.39, hy + hh / 2, H.dk2, 2);
    });
    text(s, "Reach: the governor's authority ends at the last device that checks its stamp. A payment system is three hops away and has never heard of it.", { x: L, y: hy + hh + 0.12, w: CW, h: 0.4, fontSize: 12.5, italic: true, color: C.text2 });
    const items = [
      ["FiEyeOff", "Meaning", "The chip makes sure an observer is asked. It cannot make the observer right about a disguised request."],
      ["FiAlertTriangle", "False halts", "The first support ticket will say: the governor halted my rack. The rate is not measured yet."],
      ["FiServer", "The levers", "On today's HGX board, reset is grouped and the fine-grained signals sit under NDA."],
      ["FiClock", "Cost", "One signature costs 17 ms on the crypto engine. Under one percent in the model, not yet in silicon."],
      ["FiKey", "Governance", "Who holds the keys, whose rules govern a shared rack, and the tightest tier needs NVIDIA."],
      ["FiLink", "Adoption", "A chip wired to nothing that acts is a logger. The first device maker to check a stamp decides this."],
    ];
    const W = (CW - 2 * 0.4) / 3, Hh = 1.2, iy = hy + hh + 0.7;
    for (let i = 0; i < items.length; i++) {
      const x = L + (i % 3) * (W + 0.4), y = iy + Math.floor(i / 3) * (Hh + 0.15);
      await circleIcon(s, items[i][0], x, y + 0.05, 0.56, C.accent1, H.lt1);
      text(s, items[i][1], { x: x + 0.72, y, w: W - 0.75, h: 0.35, fontSize: 14.5, bold: true });
      text(s, items[i][2], { x: x + 0.72, y: y + 0.38, w: W - 0.75, h: 0.85, fontSize: 11.5, color: C.text1 });
    }
    analogy(s, "A firewall at the building's edge decides whether a packet leaves. It cannot decide what the server across town does with it. The fix is not to reach across town; it is to keep the key in a box the firewall controls.", 6.0, 0.75);
    s.addNotes("The hop chain is the picture for the deepest challenge. Authority is full at the governor, partial at the network, and zero at a bank that has never heard of the stamp. The answer, on the next slide, is to move the credential rather than reach through the bank. The other five are engineering and governance, which does not make them small.");
  }

  // ───────────────────────── 15. Challenges (technical)
  {
    const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Challenges" });
    s.addText("Challenges, technically: mechanism, status", { placeholder: "title" });
    table(s, [
      ["Challenge", "What the design does", "Status"],
      ["Reach: a payment system two or three hops out", "A: the comparator in the device. B: move the credential behind a ticket-checking adapter, so the model's runtime never holds the API key. C: open the DPU flow to the provider only under a live ticket. D: always the signed record", "A and C modelled and tested (H6, H2, H17). B is a pattern the endpoint model already expresses; the three-hop payment narration is the next piece of work"],
      ["Meaning: observers can be fooled", "Observer always invoked, cannot be impersonated, separate from the model; hazard classes, legibility floor, session hazard budget, TRNG audit sampling with escrow", "Guarantees tested (H17, H18). Observer error rates: open; needs a red team and a quorum of observers on high-hazard classes"],
      ["False halts", "Loop beacon inside the signed heartbeat; two-sense-period debounce; a jumpered governor detected within two heartbeats; FMEA", "Modelled (H11) and simulated (ngspice). Not measured on hardware"],
      ["Levers on HGX", "Per-slot SMBus, power brake, PERST#, PWR_EN at the connector; grouped reset accepted as coarser; the evidence register names what is verified", "Evidence register done. Design guide under NDA still needed"],
      ["Cost", "P-384 on OTBN at 1,697,985 cycles (17 ms); one signature per 50 ms window; engine 34 percent busy batched; firmware share 0.01 percent of GPU time", "Modelled (H9). Silicon or FPGA measurement: open"],
      ["Governance and adoption", "k-of-n quorum with keys outside vendor and operator (G8); partitions and per-rule approvers; integrated-tier asks written", "Two tenants with two quorums on one baseboard: not designed. Integrated tier: needs NVIDIA"],
    ], { colW: [2.3, 5.9, 3.93], fontSize: 11.5 });
    s.addNotes("For each challenge, the mechanism and its status. The status column is the honest part: modelled is not measured, and three of the six end in an ask.");
  }

  // ───────────────────────── 16. Help (plain)
  pres.addSection({ title: "What I need" });
  {
    const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "What I need" });
    s.addText("What I need to prove or disprove the thesis", { placeholder: "title" });
    const asks = [
      ["FiBriefcase", "A server maker to talk to", "About the management-card slot and the GPU board's design guide."],
      ["FiHardDrive", "A device maker willing to check a ticket", "A functional-safety vendor, or whoever runs the tools an agent calls."],
      ["FiActivity", "A lab with a rack and an FPGA", "To measure the real overhead and the false-halt rate over weeks."],
      ["FiTarget", "A red team", "To attack the release gate and the observers with disguised requests."],
      ["FiUsers", "Chip designers and an auditor", "To tear the design apart before any tape-out."],
    ];
    const W = (CW - 4 * 0.25) / 5, Hh = 3.55;
    for (let i = 0; i < 5; i++) {
      const x = L + i * (W + 0.25);
      card(s, x, TOP, W, Hh);
      await circleIcon(s, asks[i][0], x + 0.25, TOP + 0.3, 0.7, C.accent1, H.lt1);
      text(s, asks[i][1], { x: x + 0.25, y: TOP + 1.2, w: W - 0.5, h: 0.9, fontSize: 14, bold: true });
      text(s, asks[i][2], { x: x + 0.25, y: TOP + 2.15, w: W - 0.5, h: 1.3, fontSize: 11.5, color: C.text1 });
    }
    analogy(s, "Back to the bridge: the drawings are done. What a bridge needs next is a soil report, a steel mill and an independent engineer who signs. Each of these can come back as a no, and a no is informative.", 5.5, 0.9);
    s.addNotes("Five asks in plain words. Each one maps to a specific open question on the next slide, and several would disprove the thesis as stated if the answer is no.");
  }

  // ───────────────────────── 17. Help (technical)
  {
    const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "What I need" });
    s.addText("What I need, technically: who, what, and why", { placeholder: "title" });
    table(s, [
      ["Who", "What I need", "What it settles"],
      ["A server OEM", "The management-module slot; the HGX design guide under NDA; the connector pinout", "Whether per-module levers reach the connector. If not, the rack tier is coarser than the design says"],
      ["NVIDIA", "Seven firmware asks: NSM port-disable semantics, per-GPU reset, buffer-class checkers in the copy engines and peer MMU", "The integrated tier; whether the recorded gap can be closed from inside the silicon"],
      ["An endpoint partner", "A device or tool gateway that verifies the ticket: P-384 signature, typed fields, epoch, freshness", "Whether the comparator works outside the model. If nobody will check the stamp, the thesis fails in practice"],
      ["A lab with an HGX or NVL rack", "An FPGA governor beside a real GPU for weeks", "The real overhead against the one percent goal; the false-halt rate; the loop beacon in the field"],
      ["A model lab's red team", "Disguised requests against the release gate and the observers", "The size of the semantic residual; whether a quorum of observers is enough"],
      ["Chip designers, an auditor", "Review of the RTL, the firmware plan and the proof-assumption list; formal proofs of the block invariants", "Verification before tape-out"],
    ], { w: 8.6, colW: [1.9, 3.3, 3.4], fontSize: 11 });
    const dx = L + 8.6 + 0.33, dw = R - dx;
    card(s, dx, TOP, dw, 4.9, C.text1);
    text(s, "What would disprove it", { x: dx + 0.3, y: TOP + 0.25, w: dw - 0.6, h: 0.45, fontSize: 14, bold: true, fontFace: "Georgia", color: C.accent6 });
    text(s, bullets([
      "No device that acts will verify a ticket",
      "The levers do not reach the baseboard connector",
      "False halts at a rate operators will not accept",
      "Measured overhead above one percent after batching",
      "Observers miss disguised requests too often for the hazard cases",
      "Nobody will hold the quorum keys",
    ], 12), { x: dx + 0.3, y: TOP + 0.95, w: dw - 0.6, h: 3.8, fontSize: 12, color: C.background1 });
    s.addNotes("The asks by who can grant them. The right-hand panel is the falsification list: if any of those six comes true, the design as written does not hold, and we should know early.");
  }

  // ───────────────────────── 18. Close
  pres.addSection({ title: "Close" });
  {
    const s = pres.addSlide({ masterName: "DARK", sectionTitle: "Close" });
    s.addText("The one-sentence version", { placeholder: "title" });
    s.addText("The governor never knows what the model is thinking and does not need to, because thinking fires nothing. A ticket does, and the model cannot mint one.", { placeholder: "body" });
    text(s, [
      { text: "github.com/YobieBenjamin/safety-governor", options: { breakLine: true } },
      { text: "github.com/YobieBenjamin/hardware-and-silicon", options: { breakLine: true } },
      { text: "The Chip That Says No, parts 1 to 4, and design documents 00 to 18", options: { color: C.accent3 } },
    ], { x: L, y: 5.5, w: 9, h: 1.0, fontSize: 13, color: C.accent6 });
    s.addNotes("Close on the sentence, then questions. The repositories hold the model, the tests, the RTL, the circuit simulation and the audit; the blog series is the plain-English route in.");
  }

  await pres.writeFile({ fileName: OUT });
  if (applyTheme) await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
}

main().catch((e) => { console.error(e); process.exit(1); });

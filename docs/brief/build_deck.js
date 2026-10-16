// Builds "The Chip That Says No" brief: a short structured deck (theme, layouts, placeholders, sections).
// Run: node build_deck.js  -> chip-that-says-no-brief.pptx
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

// Palette: silicon and copper. Ink green-black for text and dark slides, slate teal for the
// governor's own blocks, copper for the single accent (the current loop, the stamp), a cool
// grey-green surface, refusal red and pass green only where state is shown.
const THEME = {
  name: "Chip That Says No",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1B2A24", lt1: "FFFFFF", dk2: "2F5D62", lt2: "EEF2EF",
    accent1: "C2703D", accent2: "4F7F84", accent3: "7D8C81", accent4: "A33B2E", accent5: "1F7A4D", accent6: "E6C3A5",
    hlink: "C2703D", folHlink: "7D8C81",
  },
};
const H = THEME.colors; // hex, for the few options that take hex only

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
  pres.layout = "LAYOUT_16x9"; // 10 x 5.625 in
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  pres.author = "Yobie Benjamin";
  pres.title = "The Chip That Says No: a multi-layer hardware approach to AI safety";
  const C = pres.SchemeColor;
  const FOOT = "Yobie Benjamin  ·  The Chip That Says No  ·  October 2026";

  pres.defineSlideMaster({
    title: "DARK",
    background: { color: H.dk1 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 1.35, w: 6.2, h: 1.2, fontSize: 40, bold: true, color: C.background1, valign: "bottom", align: "left", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: 0.6, y: 2.7, w: 6.2, h: 1.4, fontSize: 18, color: C.accent6, valign: "top", align: "left", margin: 0 }, text: "" } },
      { text: { text: "Yobie Benjamin  ·  yobie AT ieee DOT org  ·  linkedin.com/in/yobie", options: { x: 0.6, y: 5.05, w: 8.8, h: 0.3, fontSize: 10, color: C.accent3, margin: 0 } } },
    ],
  });
  pres.defineSlideMaster({
    title: "LIGHT",
    background: { color: H.lt1 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.32, w: 9.0, h: 0.7, fontSize: 28, bold: true, color: C.text1, valign: "middle", align: "left", margin: 0 }, text: "" } },
      { text: { text: FOOT, options: { x: 0.5, y: 5.22, w: 7.5, h: 0.28, fontSize: 10, color: C.accent3, margin: 0 } } },
    ],
    slideNumber: { x: 9.0, y: 5.22, w: 0.5, h: 0.28, fontSize: 10, color: C.accent3, align: "right", margin: 0 },
  });

  // helpers
  const card = (s, x, y, w, h, opts = {}) => s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.06, fill: { color: opts.fill || C.background2 }, line: { color: opts.line || C.background2, width: opts.lineW || 0.75 },
    objectName: opts.name || "card",
  });
  const text = (s, t, o) => s.addText(t, Object.assign({ isTextBox: true, margin: 0, fontSize: 14, color: C.text1, valign: "top" }, o));
  const arrow = (s, x1, y1, x2, y2, color, width = 1.5, head = true) => {
    const o = { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1), line: { color, width }, objectName: "connector" };
    if (head) o.line.endArrowType = "triangle";
    if (x2 < x1) o.flipH = true;
    if (y2 < y1) o.flipV = true;
    s.addShape(pres.ShapeType.line, o);
  };
  const circleIcon = async (s, name, x, y, d, bg, fg) => {
    s.addShape(pres.ShapeType.ellipse, { x, y, w: d, h: d, fill: { color: bg }, line: { color: bg, width: 0 }, objectName: "icon circle" });
    const pad = d * 0.24;
    s.addImage({ data: await icon(name, fg), x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad, objectName: name });
  };

  // ───────────────────────── 1. Title
  pres.addSection({ title: "Opening" });
  {
    const s = pres.addSlide({ masterName: "DARK", sectionTitle: "Opening" });
    s.addText("The Chip That Says No", { placeholder: "title" });
    s.addText("A multi-layer hardware approach to AI safety. The thesis, the logic behind it, the proposal, the layers, how it meets the model, the challenges, and the help I need to prove or disprove it.", { placeholder: "body" });
    // the halt loop as the motif: a copper ring of governors, one of them open
    const cx = 8.35, cy = 2.3, r = 1.05;
    s.addShape(pres.ShapeType.ellipse, { x: cx - r, y: cy - r, w: 2 * r, h: 2 * r, fill: { color: H.dk1 }, line: { color: C.accent1, width: 4 }, objectName: "halt loop" });
    for (let i = 0; i < 8; i++) {
      const a = (Math.PI * 2 * i) / 8 - Math.PI / 2;
      const d = 0.26;
      const open = i === 5;
      s.addShape(pres.ShapeType.roundRect, { x: cx + r * Math.cos(a) - d / 2, y: cy + r * Math.sin(a) - d / 2, w: d, h: d, rectRadius: 0.04, fill: { color: open ? C.accent4 : C.accent2 }, line: { color: C.background1, width: 1 }, objectName: "governor " + i });
    }
    text(s, "one series loop through every governor in a rack: any one opens it, every GPU stops", { x: 6.9, y: 3.55, w: 2.9, h: 0.6, fontSize: 10, color: C.accent3, align: "center" });
    s.addNotes("Brief for a short talk. The chip is a referee beside the GPU: it issues the stamp a device needs before it acts, and it has a hand on the breaker. Everything claimed here runs as a model with tests, not yet as silicon.");
  }

  // ───────────────────────── 2. Thesis
  pres.addSection({ title: "Thesis and logic" });
  {
    const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Thesis and logic" });
    s.addText("Thesis", { placeholder: "title" });
    text(s, [
      { text: "Safety that lives only in software can be removed by software. ", options: { bold: true } },
      { text: "The decision to act must be made in silicon the model cannot reach, at the few places where computation turns into effect." },
    ], { x: 0.5, y: 1.3, w: 5.2, h: 2.4, fontSize: 22, fontFace: "Cambria", color: C.text1, valign: "top", paraSpaceAfter: 6 });
    text(s, "Not a filter on words. A referee on actions, with a hand on the breaker.", { x: 0.5, y: 3.9, w: 5.2, h: 0.8, fontSize: 14, italic: true, color: C.accent1 });
    const rows = [
      ["FiEye", "Every layer above the chip is a witness", "Safety training, judges, watermarks and observers can raise an alarm. They live in software the operator can change."],
      ["FiLock", "Only the silicon layer can be the lock", "Keys with no read port, logic no update can patch, a comparator on the wire, fail-closed by physics, a log head in a register."],
      ["FiLogOut", "The lock sits at the crossings", "Bytes leaving the GPU, a request to a device that acts, a response leaving the rack, a write to the weights, GPU power and reset."],
    ];
    let y = 1.25;
    for (const [ic, h, b] of rows) {
      card(s, 6.0, y, 3.5, 1.2);
      await circleIcon(s, ic, 6.15, y + 0.2, 0.5, C.text2, H.lt1);
      text(s, h, { x: 6.8, y: y + 0.1, w: 2.6, h: 0.45, fontSize: 12, bold: true, valign: "top" });
      text(s, b, { x: 6.8, y: y + 0.56, w: 2.6, h: 0.6, fontSize: 10, color: C.accent3 });
      y += 1.32;
    }
    s.addNotes("The thesis in one breath. Witness versus lock is the whole argument: anything above the chip can warn, only the chip can refuse in a way that cannot be patched away.");
  }

  // ───────────────────────── 3. Logic
  {
    const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Thesis and logic" });
    s.addText("The logic behind it", { placeholder: "title" });
    const cards = [
      ["FiEdit3", "Weights are editable", "Refusal lives mostly along one direction in a transformer's activation space. Subtract it and the model answers everything; it takes an afternoon on a consumer GPU. Anything inside a weight file is at the mercy of whoever holds the file."],
      ["FiUsers", "A judge is a transformer too", "A second model that watches the first falls for the same injections, can be edited the same way, and runs as a process the operator can patch or kill. It can keep a gate shut. It can never be the gate."],
      ["FiCpu", "Chips cannot read meaning; they can check structure", "A chip sees a ticket, a signature from a key the model does not hold, a count under a limit, a peer on a list, a measured workload. Meaning becomes structure exactly at the crossings, and the chip stands at all of them."],
      ["FiShield", "The shape is known: the reference monitor", "Written down in 1972: every protected access passes through it, it cannot be tampered with, it is small enough to verify. Firewalls, kernels and HSMs are reference monitors. This one is for actions, and it can also cut the power."],
    ];
    const W = 4.4, Hh = 1.82, X0 = 0.5, Y0 = 1.25, G = 0.2;
    for (let i = 0; i < 4; i++) {
      const x = X0 + (i % 2) * (W + G), y = Y0 + Math.floor(i / 2) * (Hh + G);
      card(s, x, y, W, Hh);
      await circleIcon(s, cards[i][0], x + 0.18, y + 0.2, 0.52, C.accent1, H.lt1);
      text(s, cards[i][1], { x: x + 0.85, y: y + 0.2, w: W - 1.0, h: 0.5, fontSize: 13, bold: true });
      text(s, cards[i][2], { x: x + 0.18, y: y + 0.78, w: W - 0.36, h: Hh - 0.9, fontSize: 10.5, color: C.text1 });
    }
    s.addNotes("Why not stop at software. Three facts and one old idea. The abliteration point and the judge point are from the multi-layer post; the structure point is the center of the governor design.");
  }

  // ───────────────────────── 4. Proposal
  pres.addSection({ title: "Proposal" });
  {
    const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Proposal" });
    s.addText("The proposal: a governor beside every GPU", { placeholder: "title" });
    const bullets = [
      "A small separate die (about 2 mm² of core logic in the prototype) on the OEM's management-module card. It reaches NVIDIA's HGX baseboard through the baseboard's own connector.",
      "Nothing changes in the GPU or in CUDA. It governs through interfaces that already ship: BMC power, reset and clock levers, SMBPBI device disable, NSM switch-port disable, DOCA flow rules on the DPU, and the GPU's own attestation as an input.",
      "What it enforces is burned in: keys, fail-closed state machine, invariants no firmware update can remove. What is allowed is loaded: an allow-list signed by a quorum whose keys sit outside the chip vendor and the operator. Default deny.",
      "One series current loop through every governor in the rack. Any governor opens it, or a cut wire, and every GPU halts; a halt survives a power cycle and no governor can clear its own.",
      "Three tiers: rack (buildable now with an OEM), board-only fallback, integrated (checkers in the copy engines, which needs NVIDIA). Same firmware, policy format and fabric on all three.",
    ];
    text(s, bullets.map((b, i) => ({ text: b, options: { bullet: { indent: 12 }, breakLine: i < bullets.length - 1, paraSpaceAfter: 5 } })), { x: 0.5, y: 1.2, w: 4.75, h: 3.9, fontSize: 10.5, color: C.text1, valign: "top" });
    // simplified rack drawing, right side
    const X = 5.55, Y = 1.15, W = 3.95;
    text(s, "one compute tray", { x: X, y: Y, w: W, h: 0.25, fontSize: 10, color: C.accent3, align: "right" });
    card(s, X, Y + 0.28, W, 0.9, { fill: C.background2 });
    text(s, "system board", { x: X + 0.1, y: Y + 0.31, w: 2, h: 0.22, fontSize: 9, color: C.accent3 });
    const boards = ["CPU", "PCIe switch", "DPU / NIC", "BMC"];
    boards.forEach((b, i) => {
      s.addShape(pres.ShapeType.roundRect, { x: X + 0.12 + i * 0.95, y: Y + 0.55, w: 0.85, h: 0.5, rectRadius: 0.05, fill: { color: H.lt1 }, line: { color: C.accent6, width: 1 }, objectName: b });
      text(s, b, { x: X + 0.12 + i * 0.95, y: Y + 0.55, w: 0.85, h: 0.5, fontSize: 9, align: "center", valign: "middle" });
    });
    // governor module
    s.addShape(pres.ShapeType.roundRect, { x: X, y: Y + 1.3, w: W, h: 0.6, rectRadius: 0.05, fill: { color: C.text2 }, line: { color: C.text2, width: 0 }, objectName: "governor module" });
    text(s, [{ text: "SAFETY GOVERNOR MODULE", options: { bold: true, breakLine: true } }, { text: "one governor per GPU slot · mailbox, gate, ledger, log, meter, levers, loop, fabric", options: { fontSize: 8.5 } }], { x: X + 0.12, y: Y + 1.3, w: W - 0.24, h: 0.6, fontSize: 10, color: C.background1, valign: "middle" });
    for (let i = 0; i < 3; i++) arrow(s, X + 0.55 + i * 0.95, Y + 1.05, X + 0.55 + i * 0.95, Y + 1.3, H.dk2, 1, true);
    text(s, "mailbox · mgmt port · OOB port", { x: X + 2.95, y: Y + 1.06, w: 1.0, h: 0.22, fontSize: 7, color: C.text2, align: "right" });
    // baseboard
    card(s, X, Y + 2.15, W, 1.32, { fill: C.background2 });
    text(s, "GPU baseboard (NVIDIA's, reached through its connector)", { x: X + 0.1, y: Y + 2.18, w: W - 0.2, h: 0.22, fontSize: 9, color: C.accent3 });
    for (let i = 0; i < 8; i++) {
      s.addShape(pres.ShapeType.roundRect, { x: X + 0.12 + i * 0.47, y: Y + 2.43, w: 0.4, h: 0.4, rectRadius: 0.04, fill: { color: H.lt1 }, line: { color: C.accent6, width: 1 }, objectName: "GPU" + i });
      text(s, "GPU" + i, { x: X + 0.12 + i * 0.47, y: Y + 2.43, w: 0.4, h: 0.4, fontSize: 7, align: "center", valign: "middle" });
      arrow(s, X + 0.32 + i * 0.47, Y + 1.9, X + 0.32 + i * 0.47, Y + 2.43, H.dk2, 0.75, false);
    }
    s.addShape(pres.ShapeType.roundRect, { x: X + 0.6, y: Y + 2.95, w: W - 1.2, h: 0.42, rectRadius: 0.04, fill: { color: H.lt1 }, line: { color: C.accent6, width: 1 }, objectName: "NVSwitch" });
    text(s, "NVSwitch × N + management controller · port disable out of band", { x: X + 0.6, y: Y + 2.95, w: W - 1.2, h: 0.42, fontSize: 8, align: "center", valign: "middle" });
    text(s, "per slot: SMBus · power brake · PERST# · PWR_EN · present/fault", { x: X + 0.1, y: Y + 1.92, w: W - 0.2, h: 0.22, fontSize: 7.5, color: C.text2 });
    // loop line
    s.addShape(pres.ShapeType.line, { x: X, y: Y + 3.62, w: W, h: 0, line: { color: C.accent1, width: 2.5 }, objectName: "halt loop" });
    text(s, "halt loop and signed message fabric to the next tray", { x: X, y: Y + 3.66, w: W, h: 0.22, fontSize: 8, color: C.accent1, align: "right" });
    s.addNotes("The plan of record is the rack tier: the governor on the OEM's management-module card, reaching the HGX baseboard through its connector. Anything soldered onto the baseboard is an ask to NVIDIA. The allow-list is what makes it a referee rather than a censor: everything not on the list is refused by construction.");
  }

  // ───────────────────────── 5. Layers
  pres.addSection({ title: "Layers" });
  {
    const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Layers" });
    s.addText("The layers: witnesses above, the lock below", { placeholder: "title" });
    const layers = [
      ["5", "Governance root", "Signs the rulebook, the approved-firmware list and revocations. Keys outside the chip vendor and the operator, on purpose.", "lock", "the policy authority's keys; a k-of-n quorum"],
      ["4", "Control plane (the governor's gate)", "Default deny on the only path out: attestation check, rulebook, witnesses, budget, human holds, one-time tickets, tamper-evident log.", "lock", "the governor module today; a DOCA block on the DPU; an I/O block in the GPU eventually"],
      ["3", "Observers", "Fast, cheap, signed verdicts about one request, like a reflex: often early, sometimes wrong, never acting alone.", "witness", "NVIDIA Sentry on BlueField-4 as one witness; an independent observer as another"],
      ["2", "Provenance", "Watermark, hardened detector, retrieval and a signed registry; emits a signed verdict a rule can require.", "witness", "runs beside the vendor's sampler"],
      ["1", "Model and runtime", "The model, CUDA, the serving stack. Measured, watched, never trusted to decide anything.", "untrusted", "NVIDIA, unchanged"],
      ["0", "Silicon root of trust", "Fused device secret, anti-rollback counter, extend-only measurement registers, DICE key derivation, quote engine.", "lock", "the GPU's confidential-computing attestation and the DPU's root, bound to the governor's own"],
    ];
    const X0 = 0.5, Y0 = 1.2, rowH = 0.6, gap = 0.07;
    layers.forEach((L, i) => {
      const y = Y0 + i * (rowH + gap);
      const kind = L[3];
      const fill = kind === "lock" ? C.text2 : kind === "witness" ? C.background2 : H.lt1;
      const fg = kind === "lock" ? C.background1 : C.text1;
      s.addShape(pres.ShapeType.roundRect, { x: X0, y, w: 9.0, h: rowH, rectRadius: 0.05, fill: { color: fill }, line: { color: kind === "untrusted" ? C.accent4 : fill, width: kind === "untrusted" ? 1 : 0 }, objectName: "layer " + L[0] });
      text(s, L[0], { x: X0 + 0.15, y, w: 0.4, h: rowH, fontSize: 20, bold: true, fontFace: "Cambria", color: kind === "lock" ? C.accent6 : C.accent1, valign: "middle" });
      text(s, L[1], { x: X0 + 0.6, y, w: 1.75, h: rowH, fontSize: 11, bold: true, color: fg, valign: "middle" });
      text(s, L[2], { x: X0 + 2.4, y, w: 3.9, h: rowH, fontSize: 9, color: fg, valign: "middle" });
      // tag
      const tagFill = kind === "lock" ? C.accent1 : kind === "witness" ? C.accent3 : C.accent4;
      s.addShape(pres.ShapeType.roundRect, { x: X0 + 6.42, y: y + rowH / 2 - 0.13, w: 0.78, h: 0.26, rectRadius: 0.13, fill: { color: tagFill }, line: { color: tagFill, width: 0 }, objectName: "tag" });
      text(s, kind.toUpperCase(), { x: X0 + 6.42, y: y + rowH / 2 - 0.13, w: 0.78, h: 0.26, fontSize: 7.5, bold: true, color: C.background1, align: "center", valign: "middle" });
      text(s, L[4], { x: X0 + 7.3, y, w: 1.65, h: rowH, fontSize: 8, color: kind === "lock" ? C.accent6 : C.accent3, valign: "middle" });
    });
    text(s, "On NVIDIA's platform", { x: X0 + 7.3, y: Y0 - 0.22, w: 1.65, h: 0.2, fontSize: 8, color: C.accent3 });
    s.addNotes("Six layers, three kinds. The lock layers are 0, 4 and 5: the root of trust, the gate, and the keys that sign the rulebook. Layers 2 and 3 are witnesses: a rule can require their signature, they never open the gate. Layer 1 is the model: measured and watched, never trusted.");
  }

  // ───────────────────────── 6. Flow chart
  pres.addSection({ title: "How it meets the model" });
  {
    const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "How it meets the model" });
    s.addText("How it meets the model: one action, start to finish", { placeholder: "title" });
    const LX = 0.5, LW = 1.3, CX = LX + LW + 0.12, CW = 9.5 - CX; // lane label column, content column
    const lanes = [
      { y: 1.18, h: 0.82, label: "1  Model and runtime", sub: "untrusted; decides nothing" },
      { y: 2.22, h: 1.02, label: "2  Governor", sub: "silicon the model cannot reach" },
      { y: 3.46, h: 0.82, label: "3  Devices that act", sub: "endpoints hold the governors' keys" },
    ];
    for (const L of lanes) {
      s.addShape(pres.ShapeType.rect, { x: LX, y: L.y, w: 9.0, h: L.h, fill: { color: C.background2 }, line: { color: C.background2, width: 0 }, objectName: "lane" });
      text(s, [{ text: L.label, options: { bold: true, breakLine: true } }, { text: L.sub, options: { fontSize: 8, color: C.accent3 } }], { x: LX + 0.08, y: L.y, w: LW - 0.1, h: L.h, fontSize: 9.5, valign: "middle" });
    }
    const box = (x, y, w, h, t, kind) => {
      const fill = kind === "decide" ? H.lt1 : kind === "act" ? C.accent1 : C.text2;
      const fg = kind === "decide" ? C.text1 : C.background1;
      s.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.05, fill: { color: fill }, line: { color: kind === "decide" ? C.accent1 : fill, width: kind === "decide" ? 1.25 : 0 }, objectName: "step" });
      text(s, t, { x: x + 0.05, y, w: w - 0.1, h, fontSize: 8.5, color: fg, align: "center", valign: "middle" });
    };
    // lane 1
    const l1 = lanes[0]; const by1 = l1.y + 0.12, bh1 = l1.h - 0.24;
    box(CX, by1, 2.1, bh1, "Model computes: token ids in, numbers out. No authority here and none needed; thinking fires nothing.", "step");
    arrow(s, CX + 2.1, by1 + bh1 / 2, CX + 2.4, by1 + bh1 / 2, H.dk2);
    box(CX + 2.4, by1, 2.1, bh1, "Agent runtime forms a typed request: action and fields, e.g. payments.transfer, amount, destination, session", "step");
    text(s, "In parallel, in hardware: switch ports pass bytes only between roster peers; the egress holds every response until a ticket releases it; the halt loop stops the rack on any alarm.", { x: CX + 4.75, y: by1, w: CW - 4.75, h: bh1, fontSize: 8, color: C.text2, valign: "middle", italic: true });
    // lane 2: six steps
    const l2 = lanes[1]; const by2 = l2.y + 0.12, bh2 = l2.h - 0.24;
    const steps = [
      ["Mailbox: sequence, rules edition and signature in order; first failure reported", "decide"],
      ["Workload measured and attested: hash of GPU firmware, host firmware and model", "decide"],
      ["Rule for this workload and action in the signed allow-list? No rule, no path", "decide"],
      ["Witnesses fresh and signed: observer verdict, provenance, human hold if the rule says", "decide"],
      ["Budget and rate: compute, session hazard, bytes, per-action window", "decide"],
      ["Ticket signed: bound to a hash of the exact fields, one use, short expiry", "step"],
    ];
    const n = steps.length, g2 = 0.14, w2 = (CW - (n - 1) * g2) / n;
    steps.forEach(([t, k], i) => {
      const x = CX + i * (w2 + g2);
      box(x, by2, w2, bh2, t, k);
      if (i < n - 1) arrow(s, x + w2, by2 + bh2 / 2, x + w2 + g2, by2 + bh2 / 2, H.dk2, 1.25);
    });
    // REQUEST elbow: lane1 runtime bottom -> lane2 mailbox top
    const rx = CX + 2.4 + 1.05, mid1 = l1.y + l1.h + 0.11, tx = CX + w2 / 2;
    arrow(s, rx, by1 + bh1, rx, mid1, H.dk2, 1.25, false);
    arrow(s, rx, mid1, tx, mid1, H.dk2, 1.25, false);
    arrow(s, tx, mid1, tx, by2, H.dk2, 1.25, true);
    text(s, "REQUEST", { x: tx + 0.08, y: mid1 - 0.2, w: 1, h: 0.2, fontSize: 7.5, bold: true, color: C.text2 });
    // lane 3
    const l3 = lanes[2]; const by3 = l3.y + 0.12, bh3 = l3.h - 0.24;
    const w3 = (CW - 2 * 0.3) / 3;
    box(CX, by3, w3, bh3, "Endpoint comparator: the ticket must match what the device itself measures (target, amount, hash); a lying broker is caught here", "decide");
    arrow(s, CX + w3, by3 + bh3 / 2, CX + w3 + 0.3, by3 + bh3 / 2, H.dk2);
    box(CX + w3 + 0.3, by3, w3, bh3, "The action happens: the weapon fires, the money moves, the response leaves the rack, the weights are written", "act");
    arrow(s, CX + 2 * w3 + 0.3, by3 + bh3 / 2, CX + 2 * w3 + 0.6, by3 + bh3 / 2, H.dk2);
    box(CX + 2 * w3 + 0.6, by3, w3, bh3, "Recorded in the hash chain; the log head lives in a register the chip owns; checkpoints signed from inside the die", "step");
    // TICKET elbow: lane2 last box bottom -> lane3 first box top
    const tkx = CX + (n - 1) * (w2 + g2) + w2 / 2, mid2 = l2.y + l2.h + 0.11, cx3 = CX + w3 / 2;
    arrow(s, tkx, by2 + bh2, tkx, mid2, H.dk2, 1.25, false);
    arrow(s, tkx, mid2, cx3, mid2, H.dk2, 1.25, false);
    arrow(s, cx3, mid2, cx3, by3, H.dk2, 1.25, true);
    text(s, "TICKET", { x: cx3 + 0.08, y: mid2 - 0.2, w: 1, h: 0.2, fontSize: 7.5, bold: true, color: C.text2 });
    // refusal bar
    const ry = 4.42;
    s.addShape(pres.ShapeType.roundRect, { x: LX, y: ry, w: 9.0, h: 0.62, rectRadius: 0.05, fill: { color: H.lt1 }, line: { color: C.accent4, width: 1.25 }, objectName: "refusal" });
    text(s, [
      { text: "Any check that fails stops here: refused or held, with a reason code, appended to the log.  ", options: { bold: true, color: C.accent4 } },
      { text: "ticket.missing · gate.witness_missing · gate.held_for_human · ep.no_capability · release.hazard_class_not_allowed · model.not_evaluated · ticket.replay", options: { color: C.text1 } },
    ], { x: LX + 0.15, y: ry, w: 8.7, h: 0.62, fontSize: 8.5, valign: "middle" });
    s.addNotes("Read it as three lanes. The model lane has no authority. The governor lane asks four questions, failing closed: who is asking (measurement), is there a rule, are the witnesses present and fresh, is the budget intact. Then it signs a ticket bound to the exact fields. The device lane checks the ticket itself, so a broker that lies about the amount or the target is caught at the device. Everything is logged, including every refusal. The reason codes are the ones the model prints.");
  }

  // ───────────────────────── 7. Where it stands
  pres.addSection({ title: "Evidence" });
  {
    const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Evidence" });
    s.addText("Where it stands today: a model and a circuit, not yet a chip", { placeholder: "title" });
    const stats = [
      ["200", "hypothesis tests, H0 to H18, pass in the functional model of the governor and a simulated 72-GPU rack"],
      ["20", "simulation tests on the hard-core RTL blocks (Amaranth), with a LibreLane flow to sky130"],
      ["317 µs", "worst case for the halt loop to reach the last of 72 governors, against a 1 ms budget, in ngspice across 39 configurations including cut wires"],
      ["~2 mm²", "governor core as configured on the open 130 nm process; the whole module fits the OEM's management-card slot"],
      ["66", "attacks blocked with the predicted reason code in the reference stack, with all 10 legitimate baselines passing"],
      ["0", "changes to the GPU, to CUDA, or to the baseboard at the rack tier; every ask to NVIDIA is firmware or board work that tightens the design"],
    ];
    const W = 2.9, Hh = 1.75, X0 = 0.5, Y0 = 1.25, G = 0.15;
    stats.forEach(([n, l], i) => {
      const x = X0 + (i % 3) * (W + G), y = Y0 + Math.floor(i / 3) * (Hh + G);
      card(s, x, y, W, Hh);
      text(s, n, { x: x + 0.2, y: y + 0.12, w: W - 0.4, h: 0.75, fontSize: 40, bold: true, fontFace: "Cambria", color: C.accent1, valign: "middle" });
      text(s, l, { x: x + 0.2, y: y + 0.9, w: W - 0.4, h: Hh - 1.0, fontSize: 9.5, color: C.text1 });
    });
    s.addNotes("Honest status. Everything here is model, RTL simulation and circuit simulation. The two numbers that matter most for adoption, the real overhead and the false-halt rate, are not measured yet; that is on the next slide and the one after.");
  }

  // ───────────────────────── 8. Challenges
  pres.addSection({ title: "Challenges and asks" });
  {
    const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Challenges and asks" });
    s.addText("The challenges, stated plainly", { placeholder: "title" });
    const items = [
      ["FiGitBranch", "Reach ends at the last device that checks the stamp", "A payment system is two or three hops away and has never heard of the governor. The answer is to move the credential behind a ticket-checking adapter, not to reach through the bank."],
      ["FiEyeOff", "Meaning is delegated, and observers can be fooled", "The chip guarantees an observer is always invoked, cannot be impersonated and is separate. It cannot make the observer right about a disguised request."],
      ["FiAlertTriangle", "False halts", "The first support ticket will read: the governor halted my rack. The beacon, the debounce and the FMEA exist for this; none is measured on real hardware."],
      ["FiServer", "The levers on HGX", "Reset is grouped on the baseboard today; per-module levers and the design guide sit under NDA. Coarser is still safe, but it is coarser."],
      ["FiClock", "Cost", "One P-384 signature costs 17 ms on the OpenTitan engine. Batching keeps the whole-deployment overhead under one percent in the model; nobody has measured it in silicon."],
      ["FiKey", "Governance and adoption", "Who holds the quorum keys, whose policy governs a shared rack, and the integrated tier needs NVIDIA. A chip wired to nothing that acts is a logger."],
    ];
    const W = 2.9, Hh = 1.75, X0 = 0.5, Y0 = 1.25, G = 0.15;
    for (let i = 0; i < items.length; i++) {
      const x = X0 + (i % 3) * (W + G), y = Y0 + Math.floor(i / 3) * (Hh + G);
      card(s, x, y, W, Hh);
      await circleIcon(s, items[i][0], x + 0.15, y + 0.15, 0.46, C.accent1, H.lt1);
      text(s, items[i][1], { x: x + 0.72, y: y + 0.12, w: W - 0.85, h: 0.55, fontSize: 11, bold: true, valign: "middle" });
      text(s, items[i][2], { x: x + 0.15, y: y + 0.78, w: W - 0.3, h: Hh - 0.88, fontSize: 9.5, color: C.text1 });
    }
    s.addNotes("Six challenges, and none of them is a secret. The first two are the deep ones: the governor's authority is exactly as wide as the devices that verify its signature, and meaning still has to come from somewhere outside the chip.");
  }

  // ───────────────────────── 9. Help needed
  {
    const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Challenges and asks" });
    s.addText("What I need to prove or disprove the thesis", { placeholder: "title" });
    const rows = [
      ["Who", "What I need", "What it settles"],
      ["A server OEM", "A conversation about the management-module slot, and the HGX design guide under NDA", "Whether the per-module levers reach the connector. If they do not, the rack tier is coarser than the design says"],
      ["NVIDIA", "Seven firmware asks: NSM port-disable semantics, per-GPU reset, buffer-class checkers in the copy engines", "The integrated tier; whether the design's gaps can be closed from inside the silicon"],
      ["An endpoint partner", "A functional-safety vendor or a tool-gateway operator willing to check a ticket in a device", "Whether the comparator works outside the model. If nobody will check the stamp, the thesis fails in practice"],
      ["Chip designers and an auditor", "Independent review of the RTL, the firmware plan and the proof-assumption list", "Verification before any tape-out; the 1000 percent bar in the pre-hardware phase"],
      ["A lab with an HGX or NVL rack", "An FPGA beside a real GPU for weeks", "The real overhead against the one percent goal, and the false-halt rate"],
      ["A model lab's red team", "Attacks on the release gate and the observers with disguised requests", "The size of the semantic residual; whether a quorum of observers is enough"],
      ["A regulator or insurer", "A trial of the compliance wedge: what ran, under which rules, was it stoppable, signed by an independent key", "Whether the independent signer is worth paying for"],
    ];
    const tableRows = rows.map((r, i) => r.map((c, j) => ({
      text: c,
      options: i === 0
        ? { bold: true, color: C.background1, fill: { color: C.text2 }, fontSize: 10, valign: "middle" }
        : { fontSize: 9, color: C.text1, fill: { color: i % 2 ? H.lt1 : H.lt2 }, bold: j === 0, valign: "middle" },
    })));
    s.addTable(tableRows, { x: 0.5, y: 1.15, w: 6.3, colW: [1.35, 2.45, 2.5], border: { type: "solid", color: H.lt2, pt: 0.75 }, margin: 0.05, rowH: 0.42, autoPage: false, objectName: "asks" });
    // disproof callout
    s.addShape(pres.ShapeType.roundRect, { x: 7.05, y: 1.15, w: 2.45, h: 3.9, rectRadius: 0.06, fill: { color: C.text1 }, line: { color: C.text1, width: 0 }, objectName: "disproof" });
    text(s, "What would disprove it", { x: 7.25, y: 1.3, w: 2.1, h: 0.35, fontSize: 13, bold: true, fontFace: "Cambria", color: C.accent6 });
    const dis = [
      "No device that acts will verify a ticket",
      "The levers do not reach the baseboard connector",
      "False halts happen at a rate operators will not accept",
      "Measured overhead stays above one percent after batching",
      "Observers miss disguised requests too often for the hazard cases",
      "The quorum cannot be staffed: nobody will hold the keys",
    ];
    text(s, dis.map((d, i) => ({ text: d, options: { bullet: { indent: 10 }, breakLine: i < dis.length - 1, paraSpaceAfter: 5 } })), { x: 7.25, y: 1.75, w: 2.1, h: 3.2, fontSize: 9.5, color: C.background1, valign: "top" });
    s.addNotes("The asks, by who can grant them, and what each one settles. The right column is written so that a no is informative: several of these would disprove the thesis as stated, and that is the point of asking.");
  }

  // ───────────────────────── 10. Close
  pres.addSection({ title: "Close" });
  {
    const s = pres.addSlide({ masterName: "DARK", sectionTitle: "Close" });
    s.addText("The one-sentence version", { placeholder: "title" });
    s.addText("The governor never knows what the model is thinking and does not need to, because thinking fires nothing. A ticket does, and the model cannot mint one.", { placeholder: "body" });
    text(s, [
      { text: "github.com/YobieBenjamin/safety-governor", options: { breakLine: true } },
      { text: "github.com/YobieBenjamin/hardware-and-silicon", options: { breakLine: true } },
      { text: "The Chip That Says No, parts 1 to 4, and the design documents 00 to 18", options: { color: C.accent3 } },
    ], { x: 0.6, y: 4.15, w: 8.8, h: 0.8, fontSize: 11, color: C.accent6 });
    s.addNotes("Close on the sentence, then take questions. The repositories hold the model, the tests, the RTL, the circuit simulation and the audit; the blog series is the plain-English route in.");
  }

  await pres.writeFile({ fileName: OUT });
  if (applyTheme) await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
}

main().catch((e) => { console.error(e); process.exit(1); });

#!/usr/bin/env python3
"""Render the design figures in docs/ as PNGs.

Usage: python3 docs/figures/make_figures.py [outdir]      (default: this directory)

Every figure is drawn from the same facts the text states (docs/01, 02, 03, 04), so a change
to the design is a change here too. Needs matplotlib only.
"""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)

INK = "#2C2C2A"
QUIET = "#5F5E5A"
EDGE = "#8A8A82"
RULE = "#D3D1C7"
BLUE = "#185FA5"        # the governor and what it owns
BLUE_FILL = "#E6F1FB"
CORAL = "#D85A30"       # NVIDIA parts, unchanged
CORAL_FILL = "#FAECE7"
GREEN = "#2E7D4F"       # fail-safe wires
GREEN_FILL = "#E8F3EC"
GRAY_FILL = "#F6F5F0"
AMBER = "#B7791F"
AMBER_FILL = "#FBF3E0"

plt.rcParams["font.family"] = "DejaVu Sans"


def new_fig(w, h):
    fig = plt.figure(figsize=(w, h), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, title, lines=(), kind="plain", title_size=9.5, line_size=7.6, pad=0.12, align="left"):
    fill, edge, lw = {"plain": (GRAY_FILL, EDGE, 0.9), "gov": (BLUE_FILL, BLUE, 1.4), "nv": (CORAL_FILL, CORAL, 1.2),
                      "safe": (GREEN_FILL, GREEN, 1.2), "warn": (AMBER_FILL, AMBER, 1.2), "white": ("white", EDGE, 0.9)}[kind]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fill, ec=edge, lw=lw))
    tx = x + pad if align == "left" else x + w / 2
    ha = "left" if align == "left" else "center"
    ty = y + h - pad - 0.02
    ax.text(tx, ty, title, ha=ha, va="top", fontsize=title_size, color=INK, fontweight="bold")
    for i, line in enumerate(lines):
        ax.text(tx, ty - 0.21 - 0.17 * i, line, ha=ha, va="top", fontsize=line_size, color=QUIET)


def arrow(ax, x0, y0, x1, y1, color=INK, lw=1.0, style="-|>", ls="-", text=None, tsize=7.2, toff=(0, 0.06)):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle=style, mutation_scale=9, color=color, lw=lw, ls=ls,
                                 shrinkA=1, shrinkB=1))
    if text:
        ax.text((x0 + x1) / 2 + toff[0], (y0 + y1) / 2 + toff[1], text, ha="center", va="bottom", fontsize=tsize, color=color)


def label(ax, x, y, text, size=7.4, color=QUIET, ha="left", weight="normal"):
    ax.text(x, y, text, ha=ha, va="center", fontsize=size, color=color, fontweight=weight)


def save(fig, name):
    path = os.path.join(OUT, name)
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    print("wrote", path)


# ---------------------------------------------------------------------------------------------
# 1. The rack: where the governor module sits and what it is wired to
# ---------------------------------------------------------------------------------------------
def fig_rack():
    fig, ax = new_fig(10.4, 7.2)
    ax.text(0.3, 6.95, "Where the governor goes: added through the rack's own boards. Nothing in the GPU or CUDA changes.",
            fontsize=10.5, color=INK, fontweight="bold", va="center")
    # compute tray outline
    ax.add_patch(FancyBboxPatch((0.3, 1.45), 9.8, 5.2, boxstyle="round,pad=0.02,rounding_size=0.1", fc="white", ec=EDGE, lw=1.0, ls="--"))
    label(ax, 0.45, 6.48, "compute tray (one of many in the rack)", size=8, color=QUIET)
    # legend, top right inside the tray margin
    box(ax, 7.5, 6.38, 0.28, 0.18, "", kind="nv")
    label(ax, 7.83, 6.47, "NVIDIA, unchanged", size=6.8)
    box(ax, 9.05, 6.38, 0.28, 0.18, "", kind="gov")
    label(ax, 9.38, 6.47, "governor", size=6.8)
    # system board
    ax.add_patch(FancyBboxPatch((0.5, 3.9), 9.4, 2.4, boxstyle="round,pad=0.02,rounding_size=0.08", fc=GRAY_FILL, ec=EDGE, lw=0.9))
    label(ax, 0.65, 6.12, "system board (motherboard)", size=8.4, color=INK, weight="bold")
    box(ax, 0.7, 4.9, 1.5, 0.95, "CPU", ["TEE / enclave", "driver, broker"], kind="nv", align="center")
    box(ax, 2.5, 4.9, 1.7, 0.95, "PCIe switch", ["port enable, ACS", "DPC, hot-plug"], kind="nv", align="center")
    box(ax, 4.5, 4.9, 1.6, 0.95, "DPU / NIC", ["RDMA, storage", "filter tables"], kind="nv", align="center")
    box(ax, 6.4, 4.9, 1.4, 0.95, "BMC", ["platform mgmt", "(reads via gov.)"], kind="plain", align="center")
    arrow(ax, 2.2, 5.37, 2.5, 5.37, style="<|-|>", color=QUIET)
    arrow(ax, 4.2, 5.37, 4.5, 5.37, style="<|-|>", color=QUIET)
    arrow(ax, 5.3, 5.85, 5.3, 6.08, color=QUIET, style="-|>")
    label(ax, 5.4, 5.99, "network, storage", size=6.6, color=QUIET)
    # governor module
    box(ax, 0.7, 4.0, 7.1, 0.75, "SAFETY GOVERNOR module  (the OEM's management-module slot, DC-SCM-class; soldering on the baseboard is an ask to NVIDIA)",
        ["one governor instance per GPU slot · fuses, root, verifier, policy + epoch, gate core, ledger, log, meter, heartbeat, levers, loop, fabric"],
        kind="gov", title_size=8.6, line_size=7.2)
    arrow(ax, 3.35, 4.9, 3.35, 4.75, color=BLUE, style="-|>", lw=1.3)
    label(ax, 3.45, 4.82, "mgmt port: only writer", size=6.6, color=BLUE)
    arrow(ax, 5.3, 4.9, 5.3, 4.75, color=BLUE, style="-|>", lw=1.3)
    label(ax, 5.4, 4.82, "OOB port: signed table cmds", size=6.6, color=BLUE)
    arrow(ax, 1.45, 4.9, 1.45, 4.75, color=QUIET, style="-|>", lw=1.0)
    label(ax, 1.55, 4.82, "mailbox (PCIe / SMBus)", size=6.6, color=QUIET)
    # rack supervisor
    box(ax, 8.2, 4.0, 1.5, 1.85, "Rack supervisor", ["heartbeat entry point", "(the authority is a key", "held outside the rack)", "loop current source", "fabric ring head"], kind="plain", align="center", title_size=8.4, line_size=6.6)
    # baseboard (narrower, so the loop and fabric drops have a free strip on the right)
    ax.add_patch(FancyBboxPatch((0.5, 1.6), 7.3, 2.0, boxstyle="round,pad=0.02,rounding_size=0.08", fc=GRAY_FILL, ec=EDGE, lw=0.9))
    label(ax, 0.65, 3.42, "GPU baseboard, NVIDIA's (HGX: 8 slots · NVL72 compute tray: 4 slots); reached through its connector", size=8.0, color=INK, weight="bold")
    for i in range(8):
        x = 0.65 + i * 0.86
        box(ax, x, 2.5, 0.72, 0.75, f"GPU{i}", ["SXM"], kind="nv", align="center", title_size=7.6, line_size=6.4)
        ax.plot([x + 0.36, x + 0.36], [2.5, 2.3], color=CORAL, lw=1.4)
    ax.plot([1.01, 7.03], [2.3, 2.3], color=CORAL, lw=2.2)
    box(ax, 2.6, 1.68, 2.9, 0.55, "NVSwitch × N + HMC", ["NVLink ports · partitions (Fabric Manager) · SMBPBI OOB monitor"], kind="nv", align="center", title_size=7.6, line_size=6.3)
    ax.plot([4.05, 4.05], [2.3, 2.23], color=CORAL, lw=1.4)
    label(ax, 7.1, 2.3, "NVLink", size=6.6, color=CORAL)
    # per-slot wires from governor
    for i in range(8):
        x = 0.65 + i * 0.86 + 0.36
        ax.plot([x, x], [3.25, 4.0], color=BLUE, lw=1.1)
    ax.text(0.75, 3.78, "per slot: SMBus (SMBPBI) · power brake · PERST# · PWR_EN · present / fault", fontsize=6.8, color=BLUE, va="center",
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none"))
    ax.plot([7.62, 7.62], [4.0, 1.95], color=BLUE, lw=1.3)
    arrow(ax, 7.62, 1.95, 5.5, 1.95, color=BLUE, lw=1.3, style="-|>")
    ax.text(7.66, 3.0, "switch\nmgmt\nbus", fontsize=6.4, color=BLUE, va="center", ha="left")
    # loop and fabric
    ax.plot([0.3, 10.1], [1.2, 1.2], color=GREEN, lw=2.4)
    ax.plot([0.3, 10.1], [0.78, 0.78], color=BLUE, lw=1.6, ls=(0, (4, 2)))
    ax.plot([0.3, 10.1], [0.65, 0.65], color=BLUE, lw=1.6, ls=(0, (4, 2)))
    label(ax, 0.35, 1.02, "HALT LOOP: one series current loop through every governor in the rack. Any governor opens it, or a cut wire, and every GPU halts.", size=7.2, color=GREEN)
    label(ax, 0.35, 0.44, "MESSAGE FABRIC: dual ring, signed and sequenced messages (roster, epoch, heartbeat, budgets, log checkpoints). Not on the tenants' network.", size=7.2, color=BLUE)
    ax.plot([7.9, 7.9], [4.0, 1.2], color=GREEN, lw=1.6)
    ax.plot([8.05, 8.05], [4.0, 0.78], color=BLUE, lw=1.2, ls=(0, (4, 2)))
    ax.plot([8.95, 8.95], [4.0, 1.2], color=GREEN, lw=1.6)
    ax.plot([9.1, 9.1], [4.0, 0.78], color=BLUE, lw=1.2, ls=(0, (4, 2)))
    ax.text(9.95, 1.2, "next tray ›", fontsize=7, color=GREEN, va="center", ha="right", bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none"))
    ax.text(9.95, 0.715, "next tray ›", fontsize=7, color=BLUE, va="center", ha="right", bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none"))
    save(fig, "fig-rack.png")


# ---------------------------------------------------------------------------------------------
# 2. The governor die: blocks and who can write what
# ---------------------------------------------------------------------------------------------
def fig_die():
    fig, ax = new_fig(10.4, 7.6)
    ax.text(0.3, 7.35, "The governor die: one chip, five regions, and only one way in from the host (the mailbox).",
            fontsize=10.5, color=INK, fontweight="bold", va="center")
    ax.add_patch(FancyBboxPatch((0.3, 0.9), 9.8, 6.2, boxstyle="round,pad=0.02,rounding_size=0.1", fc="white", ec=BLUE, lw=1.6))
    label(ax, 0.45, 6.95, "governor die (sky130 prototype: ~2 mm² core in a ~10 mm² harness, QFN-64 · product: < 4 mm² at 22 nm, BGA-169)", size=8, color=BLUE)
    # region 1: root of trust
    ax.add_patch(FancyBboxPatch((0.5, 4.5), 3.0, 2.3, boxstyle="round,pad=0.02,rounding_size=0.08", fc=GRAY_FILL, ec=EDGE, lw=0.8))
    label(ax, 0.62, 6.62, "ROOT OF TRUST (OpenTitan-class)", size=7.8, color=INK, weight="bold")
    box(ax, 0.6, 5.55, 1.35, 0.9, "Fuses (OTP)", ["UDS · anti-rollback", "lifecycle · key hashes"], kind="gov", title_size=7.8, line_size=6.4)
    box(ax, 2.05, 5.55, 1.35, 0.9, "Silicon root", ["ROM · MEAS0/1", "DICE keys · TRNG"], kind="gov", title_size=7.8, line_size=6.4)
    box(ax, 0.6, 4.6, 2.8, 0.85, "Crypto engines (integrated IP)", ["SHA-256/384 · HMAC · AES-CTR · TRNG", "ECDSA P-256 / P-384 on an OTBN-class coprocessor (17 ms)"], kind="plain", title_size=7.8, line_size=6.4)
    # region 2: policy and gate
    ax.add_patch(FancyBboxPatch((3.7, 4.5), 3.2, 2.3, boxstyle="round,pad=0.02,rounding_size=0.08", fc=GRAY_FILL, ec=EDGE, lw=0.8))
    label(ax, 3.82, 6.62, "RULES AND PERMISSIONS", size=7.8, color=INK, weight="bold")
    box(ax, 3.8, 5.55, 1.45, 0.9, "Policy store", ["signed image, k-of-n", "EPOCH reg: no host write"], kind="gov", title_size=7.8, line_size=6.4)
    box(ax, 5.35, 5.55, 1.45, 0.9, "Gate core", ["workload × action", "→ rule, lane, budget"], kind="gov", title_size=7.8, line_size=6.4)
    box(ax, 3.8, 4.6, 1.45, 0.85, "Ledger", ["budgets · reservations", "rate windows · replay"], kind="gov", title_size=7.8, line_size=6.4)
    box(ax, 5.35, 4.6, 1.45, 0.85, "Ticket store", ["used-ticket set", "(endpoint role)"], kind="gov", title_size=7.8, line_size=6.4)
    # region 3: provenance
    ax.add_patch(FancyBboxPatch((7.1, 4.5), 2.8, 2.3, boxstyle="round,pad=0.02,rounding_size=0.08", fc=GRAY_FILL, ec=EDGE, lw=0.8))
    label(ax, 7.22, 6.62, "RECORD", size=7.8, color=INK, weight="bold")
    box(ax, 7.2, 5.55, 1.25, 0.9, "Hash + sign", ["provenance records", "Merkle batches"], kind="gov", title_size=7.8, line_size=6.4)
    box(ax, 8.55, 5.55, 1.25, 0.9, "Meter", ["tokens · cycles", "bytes per model"], kind="gov", title_size=7.8, line_size=6.4)
    box(ax, 7.2, 4.6, 2.6, 0.85, "Log engine", ["hash chain in the governor's own NVM", "signed Merkle checkpoints · neighbor heads"], kind="gov", title_size=7.8, line_size=6.4)
    # region 4: stopping
    ax.add_patch(FancyBboxPatch((0.5, 2.3), 9.4, 2.0, boxstyle="round,pad=0.02,rounding_size=0.08", fc=GREEN_FILL, ec=GREEN, lw=0.9))
    label(ax, 0.62, 4.12, "STOPPING (hard logic, no firmware in the path)", size=7.8, color=GREEN, weight="bold")
    box(ax, 0.6, 2.45, 1.7, 1.45, "Heartbeat", ["countdown from last", "valid authority token", "expiry → safe mode"], kind="safe", title_size=7.8, line_size=6.4)
    box(ax, 2.4, 2.45, 2.2, 1.45, "Safe-mode sequencer", ["RUN → THROTTLE → HALT → SAFE", "levers: brake · PERST# · PWR_EN", "rung and cause survive power loss"], kind="safe", title_size=7.8, line_size=6.4)
    box(ax, 4.7, 2.45, 1.9, 1.45, "Halt loop I/O", ["series switch, fail-open", "current sense, 100 µs", "open → HALT, everyone"], kind="safe", title_size=7.8, line_size=6.4)
    box(ax, 6.7, 2.45, 1.5, 1.45, "Alarms", ["sticky, monotone", "set by anyone", "clear path only"], kind="safe", title_size=7.8, line_size=6.4)
    box(ax, 8.3, 2.45, 1.5, 1.45, "Lifecycle", ["test → production", "→ decommissioned", "debug fused off"], kind="safe", title_size=7.8, line_size=6.4)
    # region 5: interfaces and control
    box(ax, 0.6, 1.05, 2.1, 1.05, "Mailbox", ["the ONLY host input", "signed, sequenced, epoch-checked", "no writable registers but the doorbell"], kind="warn", title_size=7.8, line_size=6.2)
    box(ax, 2.8, 1.05, 2.0, 1.05, "Fabric ports × 2", ["dual ring, SGMII-class", "signed messages", "governor-to-governor only"], kind="gov", title_size=7.8, line_size=6.2)
    box(ax, 4.9, 1.05, 2.2, 1.05, "Switch management", ["capability tables: which port is", "open to whom, until when", "PCIe switch / DPU / NVSwitch buses"], kind="gov", title_size=7.8, line_size=6.2)
    box(ax, 7.2, 1.05, 1.3, 1.05, "Lever ch. × 8", ["per GPU slot", "SMBus + 3 pins", "+ present/fault"], kind="gov", title_size=7.8, line_size=6.2)
    box(ax, 8.6, 1.05, 1.25, 1.05, "Control CPU", ["Ibex-class", "firmware < 10k", "lines, no DMA"], kind="plain", title_size=7.8, line_size=6.2)
    label(ax, 0.45, 0.55, "Memory: ROM 64 KB · OTP 8 Kbit · SRAM 512 KB · authenticated NVM 16 MB (policy ≤ 1 MB, log, ledger, used tickets).  "
                         "Every register the host can see is read-only; the doorbell is the one exception.", size=7.2)
    save(fig, "fig-die.png")


# ---------------------------------------------------------------------------------------------
# 3. Safe-mode state machine
# ---------------------------------------------------------------------------------------------
def fig_safe_mode():
    fig, ax = new_fig(10.4, 5.0)
    ax.text(0.3, 4.75, "Safe mode: the rungs go one way. Nobody climbs back up alone.", fontsize=10.5, color=INK, fontweight="bold", va="center")
    W = 1.3
    states = [("HALTED_INITIAL", 0.4, "boot state:", "levers asserted,", "ports closed", "plain"),
              ("RUN", 2.35, "heartbeat live,", "loop closed, epoch", "current, no tamper", "safe"),
              ("THROTTLE", 4.3, "ports closed,", "power brake on;", "reversible", "warn"),
              ("HALT", 6.25, "PERST# asserted;", "the job is lost,", "the GPU is intact", "warn"),
              ("SAFE", 8.2, "PWR_EN low;", "slot power cut;", "the floor", "nv")]
    for name, x, a, b, c, kind in states:
        box(ax, x, 2.3, W, 1.35, name, [a, b, c], kind=kind, align="center", title_size=7.6 if len(name) > 8 else 8.6, line_size=6.3)
    label(ax, 0.4, 0.14, "The rung and its cause are written to the chip's own memory: a power cycle brings the governor back on the same rung, with its loop switch open.", size=6.4)
    ym = 2.97
    arrow(ax, 0.4 + W, ym, 2.35, ym, color=GREEN, lw=1.4)
    ax.text(2.025, ym + 0.12, "heartbeat\n+ loop current", ha="center", va="bottom", fontsize=5.8, color=GREEN)
    arrow(ax, 2.35 + W, ym, 4.3, ym, color=AMBER, lw=1.4)
    ax.text(3.975, ym + 0.12, "local\ncause", ha="center", va="bottom", fontsize=5.8, color=AMBER)
    arrow(ax, 4.3 + W, ym, 6.25, ym, color=AMBER, lw=1.4)
    ax.text(5.925, ym + 0.12, "T_throttle\n30 s", ha="center", va="bottom", fontsize=5.8, color=AMBER)
    arrow(ax, 6.25 + W, ym, 8.2, ym, color=CORAL, lw=1.4)
    ax.text(7.875, ym + 0.12, "T_halt\n300 s", ha="center", va="bottom", fontsize=5.8, color=CORAL)
    # causes
    box(ax, 2.5, 0.35, 3.6, 1.45, "Local causes → THROTTLE first", ["heartbeat expired (5 s)", "epoch stale (missed a rack-wide policy change)", "output budget exceeded", "policy may start any cause on a higher rung"], kind="warn", title_size=8, line_size=6.6)
    box(ax, 6.4, 0.35, 3.6, 1.45, "Loop-opening causes → HALT, whole rack (tamper → SAFE)", ["loop open or broken (any governor, any cut)", "tamper detected: straight to SAFE, keys zeroized", "signed HALT from the policy authority", "the governor's own loop switch opens"], kind="nv", title_size=7.6, line_size=6.6)
    arrow(ax, 4.3, 1.8, 4.95, 2.3, color=AMBER, lw=1.2)
    arrow(ax, 7.6, 1.8, 6.9, 2.3, color=CORAL, lw=1.2)
    # clear path
    arrow(ax, 6.9, 3.65, 3.0, 3.65, color=BLUE, lw=1.3, ls=(0, (4, 2)))
    ax.text(5.2, 3.78, "CLEAR: signed by the policy authority, only after the cause is in the log and one fabric neighbor has acknowledged the checkpoint",
            ha="center", va="bottom", fontsize=6.4, color=BLUE)
    label(ax, 0.4, 1.3, "Which rung a cause starts on", size=7.4, color=INK, weight="bold")
    label(ax, 0.4, 1.05, "is a policy field: a training", size=6.8)
    label(ax, 0.4, 0.85, "job can be reset; a robot's", size=6.8)
    label(ax, 0.4, 0.65, "planner is throttled first.", size=6.8)
    save(fig, "fig-safe-mode.png")


def fig_boot():
    fig, ax = new_fig(10.4, 4.6)
    ax.text(0.3, 4.35, "Boot: the chip's keys are computed from what it booted. Change the firmware and the key changes.", fontsize=10.5, color=INK, fontweight="bold", va="center")
    steps = [("ROM", "measures the loader", "extend MEAS0", "plain"),
             ("Loader", "measures the firmware", "extend MEAS1", "plain"),
             ("Anti-rollback", "firmware version ≥ fuse", "else: stay halted", "warn"),
             ("Policy image", "verify k-of-n signatures", "EPOCH := H(image)", "gov"),
             ("Fabric", "announce quote over nonce", "wait for roster", "gov")]
    for i, (t, a, b, kind) in enumerate(steps):
        x = 0.4 + i * 2.0
        box(ax, x, 2.6, 1.75, 1.1, t, [a, b], kind=kind, align="center", title_size=8.6, line_size=6.8)
        if i < 4:
            arrow(ax, x + 1.75, 3.15, x + 2.0, 3.15, color=INK, lw=1.1)
    box(ax, 0.4, 0.5, 4.3, 1.7, "Key derivation (DICE)", ["CDI_0 = KDF(UDS, MEAS0)         DeviceID key = KDF(CDI_0)", "CDI_1 = KDF(CDI_0, MEAS1)        Alias (signing) key = KDF(CDI_1)",
                                                           "UDS never leaves the fuse block: it is only ever an input to the KDF.", "govsim/root.py · tests/test_h15_tamper.py (keys follow the firmware) · test_h12 (unapproved firmware cannot join)"],
        kind="gov", title_size=8.4, line_size=6.6)
    box(ax, 5.0, 0.5, 5.0, 1.7, "What comes up halted", ["every slot: power brake and PERST# asserted, PWR_EN low", "every governed switch port closed; loop switch open until the first heartbeat",
                                                          "nothing the governor governs runs before the policy authority has said hello", "and the roster has formed  (docs/01 Boot · hw/pcb/rack-integration.md §5)"],
        kind="safe", title_size=8.4, line_size=6.6)
    save(fig, "fig-boot.png")


# ---------------------------------------------------------------------------------------------
# 5. The halt loop as a circuit
# ---------------------------------------------------------------------------------------------
def fig_loop():
    fig, ax = new_fig(10.4, 4.9)
    ax.text(0.3, 4.65, "The halt loop: a series current loop. Every governor is a switch in it and a sensor on it.", fontsize=10.5, color=INK, fontweight="bold", va="center")
    yb, hb = 2.3, 1.0                      # governor boxes
    yw = yb + hb + 0.45                    # the wire runs above the boxes
    yr = yb - 0.35                         # the return wire runs below them
    box(ax, 0.3, yb, 1.5, hb, "Supervisor", ["current source", "4 to 20 mA class"], kind="plain", align="center", title_size=8.2, line_size=6.6)
    xs = [2.3, 4.3, 6.3, 8.3]
    for i, x in enumerate(xs):
        box(ax, x, yb, 1.5, hb, f"Governor {i}", ["switch: fail-OPEN", "sense: 100 µs"], kind="gov", align="center", title_size=8.2, line_size=6.6)
        cx = x + 0.75
        # tap from the wire into the box: the box senses the current and owns the switch
        ax.plot([cx, cx], [yb + hb, yw - 0.02], color=GREEN, lw=1.2, ls=(0, (2, 2)))
    # the wire: supervisor up to the wire level, across, down the right side, back along the return
    ax.plot([1.05, 1.05], [yb + hb, yw], color=GREEN, lw=2.2)
    ax.plot([1.05, 10.0], [yw, yw], color=GREEN, lw=2.2)
    ax.plot([10.0, 10.0], [yw, yr], color=GREEN, lw=2.2)
    ax.plot([10.0, 0.6], [yr, yr], color=GREEN, lw=2.2)
    ax.plot([0.6, 0.6], [yr, yb], color=GREEN, lw=2.2)
    label(ax, 9.6, yw + 0.17, "jumper plug", size=6.4, color=GREEN, ha="center")
    label(ax, 5.2, yr - 0.16, "return", size=6.6, color=GREEN, ha="center")
    # switch symbols on the wire, one per governor
    for x in xs:
        cx = x + 0.75
        ax.plot([cx - 0.25, cx + 0.25], [yw, yw], color="white", lw=4)
        ax.plot([cx - 0.25, cx + 0.18], [yw, yw + 0.24], color=GREEN, lw=1.6)
        ax.plot(cx - 0.25, yw, "o", color=GREEN, ms=3.2)
        ax.plot(cx + 0.25, yw, "o", color=GREEN, ms=3.2)
    label(ax, 1.15, yw + 0.17, "LOOP_OUT → LOOP_IN, tray to tray", size=6.4, color=GREEN)
    box(ax, 0.3, 0.25, 4.6, 1.3, "Opens the loop (everyone halts within the 1 ms bound)", ["this governor: tamper, commanded HALT, boot not finished", "any cut, unplugged tray, dead governor, lost power", "loss is declared after two 100 µs sense periods (debounce); a Phase 2 target"],
        kind="safe", title_size=8, line_size=6.6)
    box(ax, 5.2, 0.25, 4.9, 1.3, "Does not open the loop (local rungs only)", ["heartbeat lost on one governor, its own output budget, an epoch straggler", "those throttle their own slot; the loop is for the rack-wide stop",
                                                                              "govsim/fabric.py HaltLoop · rtl/governor_rtl/halt_loop.py · tests/test_h11_halt_loop.py"],
        kind="plain", title_size=8, line_size=6.6)
    save(fig, "fig-halt-loop.png")


def fig_request():
    fig, ax = new_fig(10.4, 5.6)
    ax.text(0.3, 5.35, "One request: the broker asks, the governor answers four questions, the endpoint re-checks before it acts.", fontsize=10.5, color=INK, fontweight="bold", va="center")
    box(ax, 0.3, 3.5, 1.6, 1.3, "Broker", ["verified host enclave", "typed request, signed:", "action + fields"], kind="nv", align="center", title_size=8.4, line_size=6.6)
    box(ax, 2.3, 3.5, 1.5, 1.3, "Mailbox", ["seq > last?", "epoch current?", "signature ok?"], kind="warn", align="center", title_size=8.4, line_size=6.6)
    box(ax, 4.2, 2.8, 3.3, 2.0, "Gate core: four questions", ["1  Who is asking?  workload = H(gpu fw, host fw, model); exact rule beats wildcard", "2  Is it in the rulebook?  default deny; no rule, no action",
                                                             "3  Does it fit?  typed limits, lane (auto / observer / human)", "4  Is there budget?  the ledger reserves it first;", "    a shared budget is reserved at its owner, over the fabric"],
        kind="gov", title_size=8.4, line_size=6.5)
    box(ax, 7.85, 3.5, 1.2, 1.3, "Ticket", ["one-time", "exact fields", "epoch, expiry"], kind="gov", align="center", title_size=8.4, line_size=6.6)
    box(ax, 7.85, 1.9, 1.2, 1.2, "Hold", ["human lane:", "waits 60 s+", "quorum approves"], kind="warn", align="center", title_size=8.4, line_size=6.6)
    box(ax, 9.25, 3.5, 1.0, 1.3, "Endpoint", ["burns ticket", "commits", "re-checks", "acts"], kind="nv", align="center", title_size=8.0, line_size=6.4)
    arrow(ax, 1.9, 4.15, 2.3, 4.15, color=INK, lw=1.1)
    arrow(ax, 3.8, 4.15, 4.2, 4.15, color=INK, lw=1.1)
    arrow(ax, 7.5, 4.15, 7.85, 4.15, color=GREEN, lw=1.3, text="yes", tsize=6.8)
    arrow(ax, 7.5, 3.3, 7.85, 2.6, color=AMBER, lw=1.3)
    ax.text(7.45, 2.5, "human lane", ha="right", va="center", fontsize=6.4, color=AMBER)
    arrow(ax, 9.05, 4.15, 9.25, 4.15, color=GREEN, lw=1.3)
    arrow(ax, 8.45, 3.1, 8.45, 3.5, color=AMBER, lw=1.1)
    ax.text(8.55, 3.3, "approved", ha="left", va="center", fontsize=6.4, color=AMBER)
    arrow(ax, 5.85, 2.8, 5.85, 2.1, color=CORAL, lw=1.3, text="no", tsize=6.8, toff=(0.2, 0))
    box(ax, 4.2, 1.1, 3.3, 1.0, "Refusal", ["reason code to the broker, entry in the hash-chained log,", "sticky alarm if the policy says so. Nothing else happens."], kind="nv", title_size=8.2, line_size=6.5)
    box(ax, 0.3, 1.1, 3.5, 1.9, "The endpoint's comparator", ["the device that acts holds the governors' keys, its own lists and", "its own sensors; it re-checks the ticket and its sensors against", "them (position, amount, port) and refuses on mismatch even if every", "layer above it is compromised.  tests/test_h06_comparator.py"],
        kind="safe", title_size=8.2, line_size=6.4)
    label(ax, 0.3, 0.6, "Model: govsim/governor.py (_cmd_request, approvals, commit_from_endpoint) · govsim/ledger.py · govsim/endpoints.py · RTL: rtl/governor_rtl/mailbox.py, ticket_store.py", size=6.6)
    label(ax, 0.3, 0.38, "Tests: tests/test_h00_contract.py · test_h04_lane.py · test_h06_comparator.py · test_h08_override.py · test_h13_shared_budget.py", size=6.6)
    save(fig, "fig-request.png")




# ---------------------------------------------------------------------------------------------
# 7 to 10. The ladder (docs/24): the staircase, the three questions, witnesses versus locks,
# and the person on the only path
# ---------------------------------------------------------------------------------------------
import textwrap

LADDER = [
    ("0", "The prompt", "a text field", "one more sentence, or text in a page the agent reads", "plain"),
    ("1", "Training", "the weight file", "a jailbreak, a fine-tune, an afternoon of abliteration on a consumer GPU", "plain"),
    ("2", "Watchers", "a process beside the model", "the same injections and edits as training; root on the box", "plain"),
    ("3", "Runtime and network", "the operator's infrastructure", "a config edit; root on the fleet; a path that never touches the network", "plain"),
    ("4", "The chip", "silicon, fused keys", "nothing the model or the operator can write; a lab with a soldering iron, maybe", "gov"),
    ("5", "A person with a key", "a human", "a conversation; fatigue; a stolen key", "warn"),
]


def wrapped(ax, x, y, text, width, size, color=QUIET, weight="normal", step=0.145, ha="left"):
    """Write text wrapped at `width` characters, top at y; returns the y below the last line."""
    for i, line in enumerate(textwrap.wrap(text, width)):
        ax.text(x, y - i * step, line, ha=ha, va="top", fontsize=size, color=color, fontweight=weight)
    return y - len(textwrap.wrap(text, width)) * step


def fig_ladder():
    fig, ax = new_fig(10.4, 5.5)
    ax.text(0.3, 5.22, "The ladder: six rungs, where each one lives, and what removes it.", fontsize=10.5, color=INK, fontweight="bold", va="center")
    sw, gap, base = 1.58, 0.1, 0.95
    ax.plot([0.3, 6.95], [4.75, 4.75], color=CORAL, lw=1.2)
    ax.text(0.3, 4.9, "SOFTWARE: REMOVED BY WHOEVER CAN WRITE TO WHERE IT LIVES", fontsize=6.8, color=CORAL, fontweight="bold", va="center")
    ax.plot([7.02, 10.28], [4.75, 4.75], color=BLUE, lw=1.2)
    ax.text(7.02, 4.9, "NOT WRITABLE BY THE MODEL OR THE OPERATOR", fontsize=6.8, color=BLUE, fontweight="bold", va="center")
    for i, (n, name, lives, removed, kind) in enumerate(LADDER):
        x = 0.3 + i * (sw + gap)
        h = 1.3 + 0.45 * i
        fill, edge = {"plain": (GRAY_FILL, EDGE), "gov": (BLUE_FILL, BLUE), "warn": (AMBER_FILL, AMBER)}[kind]
        ax.add_patch(FancyBboxPatch((x, base), sw, h, boxstyle="round,pad=0.02,rounding_size=0.06", fc=fill, ec=edge, lw=1.2))
        top = base + h
        ax.text(x + 0.12, top - 0.14, n, ha="left", va="top", fontsize=15, color={"plain": CORAL, "gov": BLUE, "warn": AMBER}[kind], fontweight="bold")
        name_lines = textwrap.wrap(name, 15)
        for k, ln in enumerate(name_lines):
            ax.text(x + 0.42, top - 0.17 - 0.16 * k, ln, ha="left", va="top", fontsize=8.0, color=INK, fontweight="bold")
        y = top - 0.5 - 0.16 * (len(name_lines) - 1)
        ax.text(x + 0.12, y, "lives in", ha="left", va="top", fontsize=6.4, color=INK, fontweight="bold")
        y = wrapped(ax, x + 0.12, y - 0.15, lives, 30, 6.4)
        ax.text(x + 0.12, y - 0.04, "removed by", ha="left", va="top", fontsize=6.4, color=INK, fontweight="bold")
        wrapped(ax, x + 0.12, y - 0.19, removed, 30, 6.4)
    ax.plot([0.3, 10.28], [base, base], color=EDGE, lw=1.2)
    label(ax, 0.3, 0.62, "The rule: a measure is never stronger than the thing it lives in. Read the \"removed by\" lines left to right: text, weights, a process, a fleet, and then nothing a model or an operator can write.", size=6.6)
    label(ax, 0.3, 0.4, "docs/24-the-ladder.md, sections 2 and 3", size=6.6)
    save(fig, "fig-ladder.png")


def fig_ladder_questions():
    fig, ax = new_fig(10.4, 4.6)
    ax.text(0.3, 4.32, "Three questions to ask of any safety measure, and a fourth, answered for every rung.", fontsize=10.5, color=INK, fontweight="bold", va="center")
    heads = ["0  Prompt", "1  Training", "2  Watchers", "3  Runtime, network", "4  The chip", "5  A person"]
    rows = [
        ("Where does it live?", ["a text field", "the weight file", "a process beside the model", "the operator's infrastructure", "silicon, with fused keys", "a human with a key"]),
        ("Who can remove it, and what does it cost?", ["anyone; one sentence", "anyone with the file; an afternoon on a consumer GPU", "root on the box", "root on the fleet, or a path that never touches the network", "nobody who can only write; a lab with a soldering iron, maybe", "anyone who can talk; a conversation"]),
        ("What does it see?", ["words", "words, in context", "words and reasoning", "hosts, identities, policies, telemetry", "typed forms, hashes, signatures, counts", "the form and the log"]),
        ("What can it say?", ["advice", "a refusal", "STOP, as a verdict; never GO", "no, to a connection; quarantine", "no, to the action; hold", "yes or no, once, signed"]),
    ]
    x0, lw_, cw, hh, rh = 0.3, 1.95, 1.3, 0.36, 0.64
    kinds = ["plain", "plain", "plain", "plain", "gov", "warn"]
    ytop = 3.95
    for j, hd in enumerate(heads):
        x = x0 + lw_ + j * cw
        fill, edge = {"plain": (GRAY_FILL, EDGE), "gov": (BLUE_FILL, BLUE), "warn": (AMBER_FILL, AMBER)}[kinds[j]]
        ax.add_patch(FancyBboxPatch((x + 0.03, ytop - hh), cw - 0.06, hh - 0.04, boxstyle="round,pad=0.01,rounding_size=0.04", fc=fill, ec=edge, lw=1.1))
        ax.text(x + cw / 2, ytop - hh / 2 - 0.02, hd, ha="center", va="center", fontsize=7.2, color=INK, fontweight="bold")
    y = ytop - hh - 0.06
    for q, cells in rows:
        wrapped(ax, x0, y - 0.1, q, 26, 7.0, color=INK, weight="bold", step=0.15)
        for j, c in enumerate(cells):
            x = x0 + lw_ + j * cw
            fill = {"plain": "white", "gov": BLUE_FILL, "warn": AMBER_FILL}[kinds[j]]
            ax.add_patch(FancyBboxPatch((x + 0.03, y - rh + 0.03), cw - 0.06, rh - 0.06, boxstyle="round,pad=0.01,rounding_size=0.04", fc=fill, ec=RULE, lw=0.8))
            wrapped(ax, x + 0.1, y - 0.1, c, 24, 6.2, step=0.135)
        y -= rh
    label(ax, 0.3, 0.58, "Rungs 0 to 3 are removed by writing to something the model or the operator can write to. Rung 4 is not. Rung 5 is removed by talking, which no silicon addresses.", size=6.6)
    label(ax, 0.3, 0.36, "docs/24-the-ladder.md, sections 1 and 3", size=6.6)
    save(fig, "fig-ladder-questions.png")


def fig_ladder_witnesses():
    fig, ax = new_fig(10.4, 4.6)
    ax.text(0.3, 4.32, "Rungs compose as witnesses, not as locks: three software rungs are three correlated miss rates. A gate is a gate.", fontsize=10.5, color=INK, fontweight="bold", va="center")
    # left: three sieves with the holes lined up
    ax.text(0.3, 3.85, "Three software rungs in a row", fontsize=8.4, color=INK, fontweight="bold", va="center")
    ymid = 2.35
    box(ax, 0.3, ymid - 0.3, 1.25, 0.6, "a disguised", ["request"], kind="nv", align="center", title_size=7.4, line_size=6.6)
    names = ["rung 1\ntraining", "rung 2\nwatcher A", "rung 2\nwatcher B"]
    for k, x in enumerate([2.15, 3.35, 4.55]):
        for (y0, y1) in [(1.25, ymid - 0.17), (ymid + 0.17, 3.45)]:
            ax.add_patch(FancyBboxPatch((x, y0), 0.34, y1 - y0, boxstyle="round,pad=0.01,rounding_size=0.03", fc=GRAY_FILL, ec=EDGE, lw=1.0))
        ax.text(x + 0.17, 1.08, names[k], ha="center", va="top", fontsize=6.4, color=QUIET)
    ax.plot([1.55, 5.3], [ymid, ymid], color=CORAL, lw=1.0, ls="--")
    arrow(ax, 1.55, ymid, 5.35, ymid, color=CORAL, lw=1.3)
    box(ax, 5.4, ymid - 0.3, 1.0, 0.6, "an action", ["through"], kind="nv", align="center", title_size=7.4, line_size=6.6)
    ax.text(3.45, 3.62, "the holes line up: the same substrate (a transformer), the same injection, the same edit, the same root", ha="center", va="center", fontsize=6.4, color=CORAL)
    label(ax, 0.3, 0.8, "Three rates, and not independent ones. Measured first in YB-0052:", size=6.5, color=CORAL)
    label(ax, 0.3, 0.64, "the keyword baseline overlapped the observer's own vocabulary.", size=6.5, color=CORAL)
    # right: the gate
    ax.plot([6.75, 6.75], [0.95, 3.95], color=RULE, lw=1.0)
    ax.text(6.95, 3.85, "One rung that lives in silicon", fontsize=8.4, color=INK, fontweight="bold", va="center")
    box(ax, 6.95, ymid - 0.3, 1.0, 0.6, "the same", ["request"], kind="nv", align="center", title_size=7.4, line_size=6.6)
    box(ax, 8.2, ymid - 0.75, 1.15, 1.5, "The gate", ["a rule?", "a stamp?", "a witness?", "budget?", "first no wins"], kind="gov", align="center", title_size=7.6, line_size=6.3)
    arrow(ax, 7.95, ymid, 8.2, ymid, color=BLUE, lw=1.3)
    arrow(ax, 9.35, ymid + 0.35, 9.65, ymid + 0.35, color=GREEN, lw=1.3)
    box(ax, 9.65, ymid + 0.1, 0.55, 0.5, "device", ["checks"], kind="safe", align="center", title_size=6.4, line_size=5.8)
    ax.text(9.92, ymid - 0.02, "a ticket", ha="center", va="top", fontsize=6.0, color=GREEN)
    arrow(ax, 8.77, ymid - 0.75, 8.77, 1.45, color=AMBER, lw=1.2)
    box(ax, 8.2, 0.95, 1.15, 0.5, "hold", ["a person with a key"], kind="warn", align="center", title_size=6.6, line_size=5.8)
    ax.text(9.5, 1.6, "no ticket:", ha="left", va="center", fontsize=6.4, color=BLUE, fontweight="bold")
    ax.text(9.5, 1.42, "nothing moves", ha="left", va="center", fontsize=6.4, color=BLUE, fontweight="bold")
    label(ax, 6.95, 0.8, "One structural check. Its failures are halts and holds,", size=6.5, color=BLUE)
    label(ax, 6.95, 0.64, "which are measurable, not misses.", size=6.5, color=BLUE)
    label(ax, 0.3, 0.4, "docs/24-the-ladder.md section 4; the witness guarantees are tests/test_h18_oversight.py; the hold is docs/04 section 5", size=6.6)
    save(fig, "fig-ladder-witnesses.png")


def fig_ladder_person():
    fig, ax = new_fig(10.4, 4.2)
    ax.text(0.3, 3.92, "Human oversight is a rung only when the person is on the only path out.", fontsize=10.5, color=INK, fontweight="bold", va="center")
    # left: the dashboard
    ax.text(0.3, 3.45, "Oversight as a dashboard", fontsize=8.4, color=INK, fontweight="bold", va="center")
    y = 2.1
    box(ax, 0.3, y - 0.3, 1.0, 0.6, "the model", [], kind="plain", align="center", title_size=7.4)
    box(ax, 1.65, y - 0.3, 1.1, 0.6, "the runtime", [], kind="plain", align="center", title_size=7.4)
    box(ax, 3.1, y - 0.3, 1.1, 0.6, "the device", ["acts"], kind="nv", align="center", title_size=7.4, line_size=6.4)
    arrow(ax, 1.3, y, 1.65, y, color=CORAL, lw=1.3)
    arrow(ax, 2.75, y, 3.1, y, color=CORAL, lw=1.3)
    box(ax, 1.5, 2.75, 1.4, 0.55, "a dashboard", ["a person reads it, later"], kind="warn", align="center", title_size=7.0, line_size=6.0)
    ax.plot([2.2, 2.2], [2.4, 2.75], color=AMBER, lw=1.0, ls=":")
    label(ax, 0.3, 1.35, "The action happened before anyone looked. An oversight the", size=6.5, color=CORAL)
    label(ax, 0.3, 1.17, "system can route around is a checkbox, not a rung.", size=6.5, color=CORAL)
    # right: the hold at the gate
    ax.plot([4.75, 4.75], [0.95, 3.6], color=RULE, lw=1.0)
    ax.text(4.95, 3.45, "Oversight as a hold at the gate", fontsize=8.4, color=INK, fontweight="bold", va="center")
    box(ax, 4.95, y - 0.3, 1.0, 0.6, "the model", [], kind="plain", align="center", title_size=7.4)
    box(ax, 6.2, y - 0.3, 1.0, 0.6, "the runtime", [], kind="plain", align="center", title_size=7.4)
    box(ax, 7.45, y - 0.45, 1.0, 0.9, "the chip", ["the gate", "parks a hold"], kind="gov", align="center", title_size=7.4, line_size=6.2)
    box(ax, 8.95, y - 0.3, 1.25, 0.6, "the device", ["checks the ticket, acts"], kind="nv", align="center", title_size=7.4, line_size=6.0)
    arrow(ax, 5.95, y, 6.2, y, color=BLUE, lw=1.3)
    arrow(ax, 7.2, y, 7.45, y, color=BLUE, lw=1.3)
    arrow(ax, 8.45, y, 8.95, y, color=GREEN, lw=1.3, text="ticket", tsize=6.2)
    box(ax, 7.2, 2.8, 1.5, 0.6, "a person with a key", ["reads the typed form, signs"], kind="warn", align="center", title_size=7.0, line_size=6.0)
    arrow(ax, 7.7, y + 0.45, 7.7, 2.8, color=AMBER, lw=1.1, text="hold", tsize=6.2, toff=(-0.22, -0.05))
    arrow(ax, 8.2, 2.8, 8.2, y + 0.45, color=AMBER, lw=1.1, text="approval", tsize=6.2, toff=(0.32, -0.05))
    label(ax, 4.95, 1.35, "No signature, no ticket, nothing moves. The chip does not make the person wiser;", size=6.5, color=BLUE)
    label(ax, 4.95, 1.17, "it makes the person unavoidable, and hands them a form instead of a transcript.", size=6.5, color=BLUE)
    label(ax, 0.3, 0.6, "Persuasion is the residual: a person is an effector no chip gates (docs/18 question 14). Fatigue is the other: the false-halt rate decides whether the hundred-and-first hold gets read.", size=6.5)
    label(ax, 0.3, 0.38, "docs/24-the-ladder.md rung 5; the human lane is docs/04 section 5; holds and approvals are tested in tests/test_h18_oversight.py", size=6.6)
    save(fig, "fig-ladder-person.png")


# ---------------------------------------------------------------------------------------------
# 11 to 13. The rulebook and the board (docs/25): what is in the image, the ten questions in
# order with their codes, and the board wiring to the GPU, the CPU, the switches and the DPU
# ---------------------------------------------------------------------------------------------
def fig_rulebook():
    fig, ax = new_fig(10.4, 6.7)
    ax.text(0.3, 6.42, "The rulebook: one signed form. Keys, numbers, digests and lists; no prose the chip acts on.", fontsize=10.5, color=INK, fontweight="bold", va="center")
    # left: the image, section by section
    ax.text(0.3, 6.0, "The policy image (docs/04 section 4)", fontsize=8.4, color=INK, fontweight="bold", va="center")
    sections = [
        ("version, issued_at, expires_at", "only up; a window", "plain"),
        ("governance_keys, threshold", "n keys, k must sign; hashes in the fuses", "gov"),
        ("approver, heartbeat, publisher, observer, eval keys", "who may release a hold, keep it alive, sign a model, witness, attest an eval", "gov"),
        ("reference_values, revocations", "vendor keys and firmware digests, each with an expiry; the dead", "plain"),
        ("endpoints, budget_owners", "the one device per rule; the one chip per budget", "plain"),
        ("rules [ ... ]", "section 3; the gate reads nothing else", "gov"),
        ("assumptions", "a register row per input, or the image does not load", "warn"),
        ("override_floor_s, safe_mode, fabric", "the floor; the rungs per cause; the timers", "plain"),
        ("buffer_policy, audit, streams, compute_budget, sandbox", "standing fields: what may leave the GPU, what is sampled, what is a sandbox", "plain"),
        ("signatures", "k of n over everything above", "gov"),
    ]
    y = 5.75
    for title, line, kind in sections:
        h = 0.44
        box(ax, 0.3, y - h, 3.5, h, title, [line], kind=kind, title_size=6.9, line_size=6.0, pad=0.08)
        y -= h + 0.045
    # middle: one rule
    ax.text(4.15, 6.0, "One rule (payments.transfer.small, as the model runs it)", fontsize=8.4, color=INK, fontweight="bold", va="center")
    fields = [
        ("measurement", "H(gpu fw, host fw, model) or *", "the key; never a name"),
        ("action", "payments.transfer", "a typed action"),
        ("constraints", "amount 0..1000; currency in {USD}", "typed limits, or a signed list by id"),
        ("requirement", "mode auto | observer | human", "max_risk; approvers_quorum"),
        ("rate", "100 per 60 s", "per workload and action"),
        ("budget", "pay-usd-hourly: amount, 2000 per 3600 s", "reserved at its owner first"),
        ("endpoint", "payment-switch", "the one device that may commit"),
        ("delay_s", "0", "no ticket before issue + delay"),
        ("inputs", "beneficiary-registry", "register rows it relies on"),
    ]
    y = 5.75
    for name, val, note in fields:
        h = 0.44
        ax.add_patch(FancyBboxPatch((4.15, y - h), 2.9, h, boxstyle="round,pad=0.02,rounding_size=0.06", fc=BLUE_FILL, ec=BLUE, lw=1.0))
        ax.text(4.23, y - 0.1, name, ha="left", va="top", fontsize=6.9, color=INK, fontweight="bold")
        ax.text(4.23, y - 0.26, val, ha="left", va="top", fontsize=6.3, color=BLUE)
        ax.text(7.1, y - h / 2, note, ha="left", va="center", fontsize=5.9, color=QUIET)
        y -= h + 0.045
    # right: how a rule is picked
    ax.plot([8.62, 8.62], [0.95, 6.1], color=RULE, lw=1.0)
    ax.text(8.75, 6.0, "How a rule is picked", fontsize=8.4, color=INK, fontweight="bold", va="center")
    steps = [("1", "the verified workload measurement and the action", "plain"),
             ("2", "rules for that exact measurement, then rules for *", "plain"),
             ("3", "the first whose typed limits the fields satisfy", "gov"),
             ("4", "no rule, or no fit: no (gate.no_rule, gate.constraint.*)", "nv")]
    y = 5.7
    for n, text, kind in steps:
        fill, edge = {"plain": (GRAY_FILL, EDGE), "gov": (BLUE_FILL, BLUE), "nv": (CORAL_FILL, CORAL)}[kind]
        ax.add_patch(FancyBboxPatch((8.75, y - 0.62), 1.4, 0.62, boxstyle="round,pad=0.02,rounding_size=0.06", fc=fill, ec=edge, lw=1.0))
        ax.text(8.83, y - 0.08, n, ha="left", va="top", fontsize=7.0, color=INK, fontweight="bold")
        wrapped(ax, 9.0, y - 0.08, text, 21, 6.0, color=INK if kind != "nv" else CORAL, step=0.13)
        if n != "4":
            arrow(ax, 9.42, y - 0.62, 9.42, y - 0.74, color=INK, lw=0.9)
        y -= 0.76
    ax.text(8.75, 2.55, "What never reaches it:", ha="left", va="top", fontsize=6.8, color=CORAL, fontweight="bold")
    wrapped(ax, 8.75, 2.38, "the broker's label for the job, the tenant, the user, the prompt, the words around the fields. select_rule has no parameter they could arrive through (H4).", 26, 6.0, color=CORAL, step=0.13)
    label(ax, 0.3, 0.6, "Model: govsim/policy.py (make_policy, make_rule, select_rule, check_constraints) · the rulebook the suite runs: govsim/cluster.py make_policy_image", size=6.6)
    label(ax, 0.3, 0.38, "Tests: tests/test_h04_lane.py (the fields pick the rule, exact beats wildcard, out of range matches nothing) · test_h07_register.py (lists and the register) · test_h03_quorum.py", size=6.6)
    save(fig, "fig-rulebook.png")


def fig_no_order():
    fig, ax = new_fig(10.4, 7.2)
    ax.text(0.3, 6.92, "What triggers a no: the questions in the order the chip asks them. The first no wins; every no has a code.", fontsize=10.5, color=INK, fontweight="bold", va="center")
    rows = [
        ("0", "Is the letter in order?", "sequence per signer; edition stamp; signature by a key the rulebook names", "mailbox.bad_sequence · policy.stale_epoch · mailbox.bad_signature", "warn"),
        ("1", "Is the form well formed?", "typed fields present, of the right type", "gate.constraint.<field>.missing", "plain"),
        ("2", "Is the asker who it says?", "GPU and host reports verified within the hour; workload token signed by this chip; frame signed by the enclave", "gate.not_attested", "plain"),
        ("3", "Seen this before?", "the request hash against the replay store", "gate.replay", "plain"),
        ("4", "Anything on fire?", "sticky alarms; the heartbeat timer; the edition's expiry", "gate.alarm_active · halt.heartbeat_lost · policy.expired", "plain"),
        ("5", "Which rule?", "measurement x action, exact before wildcard; typed limits; signed lists", "gate.no_rule · gate.constraint.<field>.below_min / above_max / not_allowed / in_denied_list / list_unavailable", "gov"),
        ("6", "Which lane?", "the rule's mode: auto, observer, human", "(a route, not a no)", "plain"),
        ("7", "Witnesses present?", "a verdict by one of the rule's observers over this hash, fresh, risk under the ceiling; for a release: streams, hashes, class, legibility, session budget, escrow", "gate.witness_missing · gate.witness_stale · gate.witness_risk_too_high · release.*", "plain"),
        ("8", "Inside the rate window?", "the ledger's count for this workload and action", "gate.rate_exceeded", "plain"),
        ("9", "Budget?", "the typed amount reserved at the budget's owner, over the fabric if that is another chip", "gate.budget_exceeded · gate.budget_owner_unreachable", "plain"),
        ("10", "Human lane?", "the rule says people: park a hold with an id and a cause", "gate.held_for_human (a hold, not a no)", "warn"),
    ]
    x_n, x_q, x_e, x_c = 0.3, 0.75, 3.15, 6.9
    ax.text(x_q, 6.58, "the question", fontsize=7.0, color=QUIET, va="center", fontweight="bold")
    ax.text(x_e, 6.58, "what it looks at", fontsize=7.0, color=QUIET, va="center", fontweight="bold")
    ax.text(x_c, 6.58, "the no it can say", fontsize=7.0, color=QUIET, va="center", fontweight="bold")
    y = 6.45
    for n, q, ev, code, kind in rows:
        h = 0.43
        fill, edge = {"plain": (GRAY_FILL, EDGE), "gov": (BLUE_FILL, BLUE), "warn": (AMBER_FILL, AMBER)}[kind]
        ax.add_patch(FancyBboxPatch((x_n, y - h), 9.8, h, boxstyle="round,pad=0.01,rounding_size=0.04", fc=fill, ec=edge, lw=0.9))
        ax.text(x_n + 0.08, y - h / 2, n, ha="left", va="center", fontsize=7.4, color=INK, fontweight="bold")
        ax.text(x_q, y - h / 2, q, ha="left", va="center", fontsize=7.0, color=INK, fontweight="bold")
        wrapped(ax, x_e, y - 0.07, ev, 62, 5.9, color=QUIET, step=0.12)
        wrapped(ax, x_c, y - 0.07, code, 56, 5.9, color=CORAL if "not a no" not in code and "route" not in code else QUIET, step=0.12)
        y -= h + 0.04
    # outcomes
    yo = y - 0.12
    box(ax, 0.75, yo - 0.5, 2.6, 0.5, "otherwise: a ticket", ["signed; one endpoint; one edition; five minutes"], kind="safe", title_size=7.4, line_size=6.2, pad=0.09)
    box(ax, 3.6, yo - 0.5, 2.6, 0.5, "a hold", ["waits the floor; the quorum signs with a reason"], kind="warn", title_size=7.4, line_size=6.2, pad=0.09)
    box(ax, 6.45, yo - 0.5, 3.65, 0.5, "a no", ["a code to the asker and a line in the log nobody rewrites"], kind="nv", title_size=7.4, line_size=6.2, pad=0.09)
    label(ax, 0.3, 0.48, "After the ticket exists the approver, the endpoint, the switch port and the levers each have their own no (docs/25 section 5): approve.*, ticket.*, ep.*, loop.* and halt.*", size=6.5)
    label(ax, 0.3, 0.28, "Model: govsim/governor.py (_check_signed, _cmd_request, _release_gate) · codes: govsim/reasons.py · the order is pinned in tests/test_h00_contract.py and the RTL mailbox test", size=6.5)
    save(fig, "fig-no-order.png")


def fig_board():
    fig, ax = new_fig(10.4, 6.4)
    ax.text(0.3, 6.12, "The board: what the governor talks to, over what, and what each side can and cannot do.", fontsize=10.5, color=INK, fontweight="bold", va="center")
    # the three big boxes
    box(ax, 0.4, 3.35, 2.1, 1.95, "GPU (NVIDIA, unchanged)",
        ["signs its attestation report", "(SPDM, in-band to the driver)", "answers the post-box bus", "honours PWRBRK#, PERST#, power", "never sees the governor"], kind="nv", title_size=8.2, line_size=6.2)
    box(ax, 3.85, 2.75, 2.7, 2.55, "Governor module (DC-SCM slot)",
        ["one BAR: the doorbell is the", "only writable word", "verifier · rulebook · gate", "ledger · meter · log", "levers · loop · fabric"], kind="gov", title_size=8.2, line_size=6.2)
    box(ax, 7.9, 3.35, 2.2, 1.95, "Host CPU",
        ["OS, hypervisor, scheduler: couriers", "enclave (TDX, SEV-SNP, CCA):", "  the one key that opens the gate", "OpenShell supervisor + middleware", "driver: relays the GPU's report"], kind="nv", title_size=8.2, line_size=6.2)
    # GPU <-> governor wires in the gutter x 2.5 .. 3.85
    gx = 3.175
    ax.plot([2.5, 3.85], [4.95, 4.95], color=BLUE, lw=1.3)
    ax.text(gx, 5.0, "SMBus post-box", ha="center", va="bottom", fontsize=5.8, color=BLUE)
    ax.text(gx, 4.9, "governor is master", ha="center", va="top", fontsize=5.5, color=BLUE)
    arrow(ax, 3.85, 4.35, 2.5, 4.35, color=GREEN, lw=1.5)
    ax.text(gx, 4.4, "PWRBRK#, PERST#, PWR_EN", ha="center", va="bottom", fontsize=5.8, color=GREEN)
    ax.text(gx, 4.3, "three wires, safe at power-on", ha="center", va="top", fontsize=5.5, color=GREEN)
    ax.plot([2.5, 3.85], [3.75, 3.75], color=QUIET, lw=1.0)
    ax.text(gx, 3.8, "present, fault", ha="center", va="bottom", fontsize=5.8, color=QUIET)
    # the report rides the driver: GPU top -> over the governor -> host top
    ax.plot([1.45, 1.45, 9.0, 9.0], [5.3, 5.72, 5.72, 5.3], color=CORAL, lw=1.1, ls="--")
    ax.text(5.2, 5.77, "the GPU's signed report rides the driver to the host (PCIe, in-band, as today), then the mailbox posts it: VERIFY_GPU", ha="center", va="bottom", fontsize=6.0, color=CORAL)
    # host <-> governor in the gutter x 6.55 .. 7.9
    hx = 7.225
    arrow(ax, 7.9, 4.95, 6.55, 4.95, color=BLUE, lw=1.4, style="<|-|>")
    ax.text(hx, 5.0, "PCIe x1 mailbox", ha="center", va="bottom", fontsize=5.8, color=BLUE)
    ax.text(hx, 4.9, "seq · epoch · cmd · sig", ha="center", va="top", fontsize=5.5, color=BLUE)
    for i, t in enumerate(["signed by the enclave:", "REQUEST, SIGN_OUTPUT,", "CAP_REQUEST, BEGIN_MODEL"]):
        ax.text(hx, 4.58 - 0.13 * i, t, ha="center", va="top", fontsize=5.5, color=INK)
    for i, t in enumerate(["carried, not signed,", "by the host: heartbeat,", "approvals, commits,", "the rulebook, the reports"]):
        ax.text(hx, 4.08 - 0.13 * i, t, ha="center", va="top", fontsize=5.5, color=QUIET)
    # bottom row
    box(ax, 0.4, 0.95, 2.1, 1.25, "NVSwitch, PCIe switch", ["ports as capabilities: one peer,", "one direction, a budget, an expiry", "the governor is the only manager"], kind="nv", title_size=7.8, line_size=6.0)
    box(ax, 4.4, 1.15, 1.6, 0.85, "BMC", ["reads through the governor;", "its writes are refused"], kind="plain", title_size=7.8, line_size=5.8)
    box(ax, 7.9, 0.95, 2.2, 1.25, "DPU (BlueField)", ["flow tables; the egress hold", "Sentry: a witness with a key", "and the quarantine on the path"], kind="nv", title_size=7.8, line_size=6.0)
    # elbows from the governor's bottom edge, in the gutter y 2.2 .. 2.75
    ax.plot([4.2, 4.2, 1.45, 1.45], [2.75, 2.42, 2.42, 2.2], color=BLUE, lw=1.2)
    arrow(ax, 1.45, 2.3, 1.45, 2.2, color=BLUE, lw=1.2)
    ax.text(2.85, 2.47, "I2C / MDIO: port tables", ha="center", va="bottom", fontsize=6.0, color=BLUE)
    ax.plot([6.2, 6.2, 9.0, 9.0], [2.75, 2.42, 2.42, 2.2], color=BLUE, lw=1.2)
    arrow(ax, 9.0, 2.3, 9.0, 2.2, color=BLUE, lw=1.2)
    ax.text(7.6, 2.47, "out-of-band link: flow tables", ha="center", va="bottom", fontsize=6.0, color=BLUE)
    ax.plot([5.2, 5.2], [2.75, 2.0], color=QUIET, lw=1.0)
    ax.text(5.28, 2.3, "pass-through", ha="left", va="center", fontsize=5.8, color=QUIET)
    # the two cluster wires
    ax.plot([3.85, 3.1], [3.05, 3.05], color=GREEN, lw=1.5)
    ax.plot([3.85, 3.1], [2.88, 2.88], color=BLUE, lw=1.2, ls=(0, (2, 1.5)))
    ax.text(3.0, 3.05, "halt loop", ha="right", va="center", fontsize=5.8, color=GREEN)
    ax.text(3.0, 2.88, "message fabric", ha="right", va="center", fontsize=5.8, color=BLUE)
    ax.text(3.0, 2.7, "to the other governors, on wires of their own (docs/02)", ha="right", va="center", fontsize=5.6, color=QUIET)
    label(ax, 0.3, 0.58, "Plugs: docs/03-interfaces.md · wiring: hw/pcb/rack-integration.md · pins: hw/pinout/governor_module.csv · the host side on NVIDIA's platform: hardware-and-silicon/docs/NVIDIA.md", size=6.5)
    label(ax, 0.3, 0.36, "Model: govsim/governor.py (_cmd_verify_gpu, _cmd_verify_host, _cmd_begin_model, _cmd_request, read_meter) · tests/test_h01_attestation.py · test_h16_levers.py · test_h02_enforcement_points.py", size=6.5)
    save(fig, "fig-board.png")


# ---------------------------------------------------------------------------------------------
# 14. The request's path (docs/25 section 0): prompt, words, tokens, CPU and GPU, the governor,
# the rack, and the rulebook triggers, with every no and its code
# ---------------------------------------------------------------------------------------------
def fig_prompt_flow(part: str = "all"):
    """Geometry computed from the text: every row is as tall as its longest wrapped column, the
    governor block as tall as its rows, and the page as tall as the flow, so nothing overlaps.
    part "all" is the whole path in one tall picture (for the web); "a" is the request up to the
    witnesses with the rack beside it, and "b" the governor's triggers and the egress, each the
    shape of a landscape page, for the printed document."""
    X0, BW, EX, EW = 0.4, 4.1, 4.7, 1.9
    LW, EWRAP, LSTEP = 90, 46, 0.118          # wrap widths (characters) and the line step for 5.9 pt text
    steps = [
        ("1 · The prompt: words", "A person types a request for a weapon to destroy a city. The system prompt (rung 0) says don't; a reframing gets past it. Nothing at this step is hardware, and the chip will never see these words."),
        ("2 · Words to bytes: the data-center edge (the DPU)", "The request travels encrypted and enters at the node's DPU. On the way back out, the egress on that DPU holds every response until a ticket admits it. Sentry watches this path."),
        ("3 · Bytes to tokens: the host CPU", "The OpenShell sandbox and its supervisor pass the request to the serving runtime, which turns the words into token ids (integers) and prepends the system prompt. The host's enclave holds the one key that may ask the chip for anything."),
        ("4 · Tokens to the GPU", "The ids cross a PCIe switch port the governor opened for the verified host only. The model generates: an abliterated model answers; an aligned model refuses unless jailbroken (rung 1 lives in the weights). The chip reads the GPU's counters out of band and never sees a token."),
        ("5 · The response: bytes back to the host, held at the edge", "Response and reasoning streams come back; the egress holds them. The runtime presents each stream to the chip (SIGN_OUTPUT): the chip hashes what it is shown and its own random source draws the audit sample."),
        ("6 · The witnesses (rung 2, now with a key)", "The lab's classifier and Sentry on the DPU each sign a verdict over the response hash: risk, hazard class, category, legibility. Software still, but the chip accepts nothing else as an opinion about content."),
    ]
    gates = [
        ("Before the first prompt: BEGIN_MODEL", "Manifest signed by a publisher key? Evaluated, if the deployment gate is on? Licence valid? Only then the model key.",
         "no key: the weights stay ciphertext and the GPU runs nothing · mailbox.bad_signature.manifest · model.not_evaluated · compute.license_invalid"),
        ("The letter and the asker", "Sequence, edition stamp, the enclave's signature; GPU and host attested within the hour; not a replay; no alarm burning.",
         "mailbox.bad_sequence · policy.stale_epoch · mailbox.bad_signature · gate.not_attested · gate.replay · gate.alarm_active"),
        ("Rule: response.release, observer lane", "Every required stream presented? The hashes in the request equal to what was presented?",
         "release.required_stream_missing · release.response_hash_mismatch"),
        ("The witnesses", "A verdict signed by an observer key, over this hash, unexpired, risk under the rule's ceiling?",
         "gate.witness_missing · gate.witness_stale · gate.witness_risk_too_high"),
        ("The verdict against the rule", "hazard_class in allowed_hazard_classes? legibility over the floor? the session under its hazard_budget? the escrow receipt, if sampled or a hazard?",
         "release.hazard_class_not_allowed: refused, or a hold for a person · release.below_legibility_floor · release.session_hazard_budget_exceeded: alarm, the session parked · release.escrow_receipt_required"),
    ]
    ticket = ("Otherwise: a release ticket", "signed by the chip; bound to the session, the response id, the stream hashes and the edition; valid five minutes; one endpoint, the egress")
    last = ("8 · The egress, and the people", "Bytes leave the DPU only against the ticket; the user of a refused request gets a code, not an explanation. A hold waits at least the floor (60 s) for two approvers with keys and a written reason. An alarm stops the gate until the alarm key clears it. Every line is in the log, cross-linked with the neighbours'.")
    notes = [
        ("one rulebook at a time", "The edition is rack-wide: an edition change is staged on every governor and committed at once, and a straggler halts. A ticket from an old edition is dead everywhere.", "docs/02 §4", BLUE),
        ("the session's hazard budget is shared", "A session served by several GPUs still has one hazard budget, kept by one owner governor: the others reserve against it over the fabric. Two racks cannot each spend it.", "docs/02 §6; H13", BLUE),
        ("an alarm fans out", "A session over its budget, or output pushed without being presented, raises a sticky alarm that every governor in the rack sees on the fabric. The gate stops answering until the alarm key clears it.", "H5", CORAL),
        ("the loop halts the domain", "Any governor that opens its switch halts every GPU slot on the loop within a millisecond, with no software in the path.", "docs/11; H11", GREEN),
        ("another site", "The stamp travels, the wire does not: a ticket minted here is checked at another site under that site's own key; there is no planet-wide halt wire, by design.", "Part 7", QUIET),
    ]
    nl = lambda t, w: len(textwrap.wrap(t, w))
    step_h = [0.32 + LSTEP * nl(t, LW) for _, t in steps]
    gate_h = [0.32 + LSTEP * max(nl(t, LW), nl(no, EWRAP)) for _, t, no in gates]
    ticket_h = 0.32 + LSTEP * nl(ticket[1], LW)
    last_h = 0.32 + LSTEP * nl(last[1], LW)
    GAP, GGAP = 0.16, 0.14
    block_h = 0.36 + sum(h + GGAP for h in gate_h) + ticket_h + 0.1
    steps_h = sum(h + GAP for h in step_h)
    W = 10.4
    if part == "all":
        H = 0.85 + steps_h + block_h + GAP + last_h + 0.95
        title = "One request, from the keyboard to the chip's no: words, bytes, tokens, the GPU, the governor, the rack, the rulebook."
        draw_steps, draw_block, note_rows = True, True, notes
    elif part == "a":
        H = 0.85 + steps_h + 0.62 + 0.75
        title = "One request, from the keyboard to the chip (1 of 2): words, bytes, tokens, the GPU, the witnesses, and the rack beside them."
        draw_steps, draw_block, note_rows = True, False, notes[:2]
    else:
        H = 0.85 + block_h + GAP + last_h + 0.6
        title = "One request, from the keyboard to the chip (2 of 2): the governor's rulebook triggers in order, the egress, and the people."
        draw_steps, draw_block, note_rows = False, True, notes[2:]
    fig, ax = new_fig(W, H)
    ax.text(0.3, H - 0.28, title, fontsize=10.2, color=INK, fontweight="bold", va="center")
    ax.text(0.4, H - 0.66, "The request, step by step" if draw_steps else "The governor chip, step by step", fontsize=8.4, color=INK, fontweight="bold", va="center")
    ax.text(6.95, H - 0.66, "Across the rack and the data center", fontsize=8.4, color=INK, fontweight="bold", va="center")
    ax.plot([6.72, 6.72], [0.95, H - 0.85], color=RULE, lw=1.0)

    def down(y0, y1, color=INK, text=None):
        arrow(ax, X0 + BW / 2, y0, X0 + BW / 2, y1, color=color, lw=1.1)
        if text:
            ax.text(X0 + BW / 2 + 0.08, (y0 + y1) / 2, text, ha="left", va="center", fontsize=5.8, color=color)

    y = H - 0.85
    if draw_steps:
        for (t_, text), h in zip(steps, step_h):
            box(ax, X0, y - h, BW, h, "", kind="plain", pad=0.1)
            ax.text(X0 + 0.1, y - 0.09, t_, ha="left", va="top", fontsize=7.4, color=INK, fontweight="bold")
            wrapped(ax, X0 + 0.1, y - 0.27, text, LW, 5.9, color=QUIET, step=LSTEP)
            down(y - h, y - h - GAP)
            y -= h + GAP
        if not draw_block:
            box(ax, X0, y - 0.62, BW, 0.62, "", kind="gov", pad=0.1)
            ax.text(X0 + 0.1, y - 0.09, "7 · The governor chip: the rulebook triggers, in order", ha="left", va="top", fontsize=7.4, color=BLUE, fontweight="bold")
            wrapped(ax, X0 + 0.1, y - 0.27, "continued in figure 2 of 2: the chip's questions, the no each one can say, the ticket, the egress and the people", LW, 5.9, color=BLUE, step=LSTEP)
    if draw_block:
        gtop = y
        ax.add_patch(FancyBboxPatch((X0 - 0.08, gtop - block_h), BW + 0.16 + EW + 0.28, block_h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=BLUE_FILL, ec=BLUE, lw=1.4))
        ax.text(X0 + 0.02, gtop - 0.09, "7 · The governor chip: the rulebook triggers, in the order the chip asks", ha="left", va="top", fontsize=7.6, color=BLUE, fontweight="bold")
        ax.text(X0 + BW + 0.3, gtop - 0.12, "the no it says, with its code", ha="left", va="top", fontsize=6.0, color=CORAL, fontweight="bold")
        gy = gtop - 0.36
        for (t_, text, no), h in zip(gates, gate_h):
            ax.add_patch(FancyBboxPatch((X0, gy - h), BW, h, boxstyle="round,pad=0.015,rounding_size=0.05", fc="white", ec=BLUE, lw=1.0))
            ax.text(X0 + 0.1, gy - 0.09, t_, ha="left", va="top", fontsize=7.0, color=INK, fontweight="bold")
            wrapped(ax, X0 + 0.1, gy - 0.26, text, LW, 5.9, color=QUIET, step=LSTEP)
            ax.add_patch(FancyBboxPatch((EX, gy - h), EW, h, boxstyle="round,pad=0.015,rounding_size=0.05", fc=CORAL_FILL, ec=CORAL, lw=0.9))
            arrow(ax, X0 + BW, gy - h / 2, EX, gy - h / 2, color=CORAL, lw=1.1)
            wrapped(ax, EX + 0.08, gy - 0.1, no, EWRAP, 5.2, color=CORAL, step=LSTEP)
            down(gy - h, gy - h - GGAP, color=GREEN, text="yes")
            gy -= h + GGAP
        box(ax, X0, gy - ticket_h, BW, ticket_h, "", kind="safe", pad=0.1)
        ax.text(X0 + 0.1, gy - 0.09, ticket[0], ha="left", va="top", fontsize=7.0, color=INK, fontweight="bold")
        wrapped(ax, X0 + 0.1, gy - 0.27, ticket[1], LW, 5.9, color=GREEN, step=LSTEP)
        ybot = gtop - block_h
        down(ybot, ybot - GAP, color=GREEN)
        y = ybot - GAP
        box(ax, X0, y - last_h, BW, last_h, "", kind="plain", pad=0.1)
        ax.text(X0 + 0.1, y - 0.09, last[0], ha="left", va="top", fontsize=7.4, color=INK, fontweight="bold")
        wrapped(ax, X0 + 0.1, y - 0.27, last[1], LW, 5.9, color=QUIET, step=LSTEP)
    # right lane: the rack and the data center
    rx, ry = 7.0, H - 1.0
    yy = ry
    if draw_steps:
        ax.text(rx, ry, "Three governors in one rack, on two wires of their own", ha="left", va="top", fontsize=6.6, color=INK, fontweight="bold")
        trays_top = ry - 0.3
        for i in range(3):
            ty = trays_top - i * 0.62
            ax.add_patch(FancyBboxPatch((rx, ty - 0.5), 2.95, 0.5, boxstyle="round,pad=0.01,rounding_size=0.04", fc=GRAY_FILL, ec=EDGE, lw=0.9))
            ax.text(rx + 0.08, ty - 0.1, f"tray {i + 1}", ha="left", va="top", fontsize=5.6, color=QUIET)
            for k in range(6):
                ax.add_patch(FancyBboxPatch((rx + 0.7 + k * 0.33, ty - 0.4), 0.25, 0.28, boxstyle="round,pad=0.005,rounding_size=0.03", fc=CORAL_FILL, ec=CORAL, lw=0.8))
            ax.add_patch(FancyBboxPatch((rx + 2.65, ty - 0.4), 0.22, 0.28, boxstyle="round,pad=0.005,rounding_size=0.03", fc=BLUE_FILL, ec=BLUE, lw=1.0))
            ax.text(rx + 2.76, ty - 0.26, "G", ha="center", va="center", fontsize=5.6, color=BLUE, fontweight="bold")
        lx = rx + 2.76
        yb = trays_top - 2 * 0.62 - 0.5
        ax.plot([lx + 0.26, lx + 0.26], [trays_top - 0.26, yb + 0.1], color=GREEN, lw=1.6)
        ax.plot([lx + 0.4, lx + 0.4], [trays_top - 0.26, yb + 0.1], color=BLUE, lw=1.1, ls=(0, (2, 1.5)))
        ax.text(rx, yb - 0.12, "coral: GPUs · G: the governor · green: the halt loop · dotted: the message fabric", ha="left", va="top", fontsize=5.4, color=QUIET)
        yy = yb - 0.45
    for t_, text, ref, color in note_rows:
        ax.text(rx, yy, t_, ha="left", va="top", fontsize=6.6, color=color, fontweight="bold")
        yend = wrapped(ax, rx, yy - 0.17, text, 50, 5.7, color=QUIET, step=0.118)
        ax.text(rx, yend + 0.02, ref, ha="left", va="top", fontsize=5.3, color=EDGE)
        yy = yend - 0.2
    if part == "all":
        label(ax, 0.3, 0.52, "The chip never reads a word, a byte or a token. It reads signatures, hashes, counters and lists, and the two scenarios in docs/25 section 0 end at the gates above.", size=6.4, color=BLUE)
        label(ax, 0.3, 0.32, "Model: govsim/governor.py (_cmd_begin_model, _cmd_sign_output, _cmd_request, _release_gate) · narrations and tests: docs/17 §4, tests/test_h17_use_cases.py, test_h18_oversight.py, test_h10_leakage.py", size=6.4)
    elif part == "b":
        label(ax, 0.3, 0.35, "The chip never reads a word, a byte or a token: signatures, hashes, counters and lists. Model: govsim/governor.py (_cmd_begin_model, _cmd_request, _release_gate) · docs/17 §4 · tests H17, H18, H10", size=6.2, color=BLUE)
    else:
        label(ax, 0.3, 0.38, "Steps 1 to 6 are software and wires the chip only measures; nothing here can be argued with because nothing here is asked an opinion. The chip's own questions are in figure 2 of 2.", size=6.4, color=BLUE)
    save(fig, {"all": "fig-prompt-flow.png", "a": "fig-prompt-flow-a.png", "b": "fig-prompt-flow-b.png"}[part])


if __name__ == "__main__":
    fig_rack()
    fig_die()
    fig_safe_mode()
    fig_boot()
    fig_loop()
    fig_request()
    fig_ladder()
    fig_ladder_questions()
    fig_ladder_witnesses()
    fig_ladder_person()
    fig_rulebook()
    fig_no_order()
    fig_board()
    fig_prompt_flow()
    fig_prompt_flow("a")
    fig_prompt_flow("b")

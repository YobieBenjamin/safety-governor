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


if __name__ == "__main__":
    fig_rack()
    fig_die()
    fig_safe_mode()
    fig_boot()
    fig_loop()
    fig_request()

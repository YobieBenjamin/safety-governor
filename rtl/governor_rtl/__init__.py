# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""The governor's hard-core digital blocks in Amaranth HDL.

Each block is small, synchronous, and carries one invariant from
``docs/07-verification-plan.md`` §3 that the simulation in ``rtl/tests/`` checks. The crypto
engines (SHA-256, HMAC, AES, P-256, TRNG) are not here; the blocks expose the interface they
need from those engines (``hash_req``/``hash_done``, ``sig_ok``) and the specification names
the IP that provides them.

``python -m rtl.gen`` writes Verilog for every block and for ``governor_core`` into ``rtl/gen/``.
"""
from .monotonic import MonotonicCounter
from .measure_reg import MeasureReg
from .epoch_reg import EpochReg
from .lifecycle import Lifecycle
from .cap_table import CapTable
from .ticket_store import TicketStore
from .heartbeat import Heartbeat
from .halt import HaltSeq
from .halt_loop import LoopIO
from .meter import Meter
from .mailbox import Mailbox
from .alarms import Alarms
from .top import GovernorCore
from .smbus import SMBusTarget
from .smbus_top import GovernorSMBus

__all__ = ["MonotonicCounter", "MeasureReg", "EpochReg", "Lifecycle", "CapTable", "TicketStore", "Heartbeat",
           "HaltSeq", "LoopIO", "Meter", "Mailbox", "Alarms", "GovernorCore", "SMBusTarget", "GovernorSMBus"]

# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""The governor against the public half of the NVIDIA server environment.

Each module checks one interface against what public documents say, and says where the
public record stops:

- ``dcscm``    the OCP DC-SCM 2.x module slot, its DC-SCI connector and LTPI: the pin mapping
               checker for ``hw/pinout/dcscm_mapping.csv`` and a model of LTPI link loss.
- ``cem``      PCIe CEM sideband timing (PERST#, PWRBRK#) checked against the RTL halt sequencer.
- ``spdm``     a DSP0274 SPDM 1.1 / 1.2 responder for the governor, bound to its measurement
               registers and DICE identity, plus an independent requester.
- ``nvtrust``  NVIDIA's GPU attestation report (SPDM MEASUREMENTS from nvtrust) turned into the
               governor's VERIFY_GPU input.
- ``matrix``   the compliance matrix: every requirement, its source, its status, its evidence.

``python -m govsim.hardware_ref`` runs all of it and exits non-zero on any failure.
"""
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""govsim: a functional model of the Safety Governor, its enforcement points, the halt loop
and the message fabric, across a simulated cluster of GPUs.

The model is the tabletop version of the design in ``docs/``. Every block in
``docs/01-architecture.md`` has a class here; every hypothesis in
``docs/07-verification-plan.md`` has a test in ``tests/``; every simplification relative to
the specification is named in the module that makes it.
"""

__version__ = "0.1.0"

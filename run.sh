#!/usr/bin/env bash
# One command: venv, dependencies, the hypothesis suite, the RTL simulation, the Verilog, the report.
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d .venv ]; then python3 -m venv .venv; fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q --upgrade pip >/dev/null
pip install -q -e ".[dev]" >/dev/null
echo "== hypothesis suite (govsim)"
python -m pytest -q tests
echo "== RTL block simulation (amaranth)"
python -m pytest -q rtl/tests
echo "== Verilog"
python -m rtl.gen >/dev/null && python -m rtl.gen --check
echo "== sweep -> results/report.md"
python -m govsim.cli sweep >/dev/null
sed -n '1,30p' results/report.md
if [ "${1:-}" = "demo" ]; then echo "== demo"; python -m govsim.cli demo; fi

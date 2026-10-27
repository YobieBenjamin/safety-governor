#!/usr/bin/env bash
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
# Usage: equiv.sh RTL.v NETLIST.v LIBERTY.lib LOG
# Exit 0 only if yosys proves every matched signal equivalent (equiv_status -assert).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
rtl=$1; nl=$2; lib=$3; log=$4
ys=$(mktemp --suffix=.ys)
sed -e "s#@RTL@#$rtl#" -e "s#@NL@#$nl#" -e "s#@LIB@#$lib#" "$here/equiv.ys.in" > "$ys"
nice -n 10 yosys -q -l "$log" "$ys"
rc=$?
rm -f "$ys"
exit $rc

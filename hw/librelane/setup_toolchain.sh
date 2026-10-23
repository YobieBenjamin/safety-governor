#!/usr/bin/env bash
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
# Builds the sky130 toolchain that worked on the shared container (see TOOLCHAIN.md) under $GOV_TOOLS
# (default /tmp/exp-layout). Idempotent: skips what is already there. Needs only GitHub, PyPI and
# conda.anaconda.org. Prints the tool versions at the end and fails if any tool does not start.
set -euo pipefail
T=${GOV_TOOLS:-/tmp/exp-layout}
PDK_REV=bdc9412b3e468c102d01b7cf6337be06ec6e9c9a
mkdir -p "$T"
export MAMBA_ROOT_PREFIX=$T/mamba
MM=$T/micromamba
CH="--override-channels -c litex-hub -c conda-forge -c anaconda"

if [ ! -x "$MM" ]; then
  curl -sSL -o "$MM" https://github.com/mamba-org/micromamba-releases/releases/download/2.3.2-0/micromamba-linux-64
  chmod +x "$MM"
fi
if [ ! -x "$T/mamba/envs/eda/bin/openroad" ]; then
  nice -n 10 "$MM" create -y -n eda $CH python=3.10 "openroad=2.0_12381_g01bba3695=*py310" \
    "magic=8.3.465_0_g5477395" "netgen=1.5.272_0_g178af5f" "fmt=8"
fi
if [ ! -x "$T/mamba/envs/kl/bin/klayout" ]; then
  nice -n 10 "$MM" create -y -n kl --override-channels -c litex-hub -c anaconda -c conda-forge \
    "klayout=0.28.17_212_gfa14afbbf=*py310"
fi
if [ ! -x "$T/mamba/envs/ys/bin/yosys" ]; then
  nice -n 10 "$MM" create -y -n ys --override-channels -c conda-forge "yosys=0.38" "verilator=5.018"
fi
# conda-forge yosys 0.38 looks for its data under bin/share; point it at share/yosys.
ln -sfn ../share/yosys "$T/mamba/envs/ys/bin/share"
"$MM" clean -a -y >/dev/null

if [ ! -x "$T/olvenv/bin/openlane" ]; then
  "$T/mamba/envs/eda/bin/python3" -m venv "$T/olvenv"
  nice -n 10 "$T/olvenv/bin/pip" install -q openlane==2.0.0 "click==8.1.8"
fi
# OpenROAD's embedded Python 3.10 runs OpenLane's odbpy scripts, which import click and friends.
# OpenLane overwrites PYTHONPATH for those steps, so point the interpreter at the venv with a .pth.
echo "$T/olvenv/lib/python3.10/site-packages" > "$T/mamba/envs/eda/lib/python3.10/site-packages/zz-openlane.pth"
# KLayout's embedded Python ignores PYTHONPATH too; same fix.
mkdir -p "$T/mamba/envs/kl/lib/python3.10/site-packages"
echo "$T/olvenv/lib/python3.10/site-packages" > "$T/mamba/envs/kl/lib/python3.10/site-packages/zz-openlane.pth"

D=$T/pdk/volare/sky130/versions/$PDK_REV
for lib in common sky130_fd_sc_hd sky130_fd_io; do
  stamp=$D/.$lib.done
  [ -f "$stamp" ] && continue
  mkdir -p "$D" "$T/dl"
  curl -sSL -o "$T/dl/$lib.tar.zst" \
    "https://github.com/efabless/volare/releases/download/sky130-$PDK_REV/$lib.tar.zst"
  "$T/olvenv/bin/python" -I -c '
import sys, tarfile, zstandard
src, dst = sys.argv[1], sys.argv[2]
with open(src, "rb") as f:
    t = tarfile.open(fileobj=zstandard.ZstdDecompressor().stream_reader(f), mode="r|")
    for m in t:
        if m.name.startswith("/") or ".." in m.name or not m.name.startswith("sky130A/"):
            continue
        t.extract(m, dst)
' "$T/dl/$lib.tar.zst" "$D"
  rm -f "$T/dl/$lib.tar.zst"
  touch "$stamp"
done
ln -sfn "volare/sky130/versions/$PDK_REV/sky130A" "$T/pdk/sky130A"
echo "$PDK_REV" > "$T/pdk/volare/sky130/current"

cat > "$T/env.sh" <<EOF
export PATH=$T/olvenv/bin:$T/mamba/envs/ys/bin:$T/mamba/envs/eda/bin:$T/mamba/envs/kl/bin:\$PATH
export PDK_ROOT=$T/pdk
export QT_QPA_PLATFORM=offscreen
EOF
. "$T/env.sh"
openlane --version | sed -n 1p
yosys -V
openroad -version
echo "magic $(magic --version)"
echo "klayout: $(klayout -v)"
verilator --version
test -f "$PDK_ROOT/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
echo "toolchain OK at $T"

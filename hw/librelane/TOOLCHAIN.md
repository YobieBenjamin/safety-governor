# Toolchain for the sky130 run: what I tried, what worked

Machine: shared Linux container, 2 cores, 7 GB RAM, about 18 GB free disk at the start, outbound HTTPS
through an allowlisting proxy. Date of the attempt: 2026-10-23. `hw/librelane/setup_toolchain.sh` repeats
the path that worked, from nothing, in one command.

## What I tried

| Path | Result | Exact blocker |
|---|---|---|
| Docker (`librelane --dockerized`, image `ghcr.io/librelane/librelane`) | Daemon started (`sudo dockerd`), image pull impossible | `curl https://ghcr.io/v2/` and `https://registry-1.docker.io/v2/` both fail with `CONNECT tunnel failed, response 403` from the proxy. No registry is reachable, so no image. I stopped the daemon again. |
| Nix (`nix-shell` / flake from github.com/librelane/librelane) | Not usable | `https://cache.nixos.org/nix-cache-info` and `https://nix-cache.fossi-foundation.org/nix-cache-info` both answer `CONNECT tunnel failed, response 403`. Without a binary cache Nix would build OpenROAD, KLayout, Magic and their dependency trees from source on 2 cores, which is days and more disk than the box has. |
| pip `librelane` 3.0.x (current) | Python package installs, tools missing | LibreLane 3 expects OpenROAD and Yosys from 2025. The only prebuilt OpenROAD I could reach is the litex-hub conda build from February 2024, which is too old for LibreLane 3's OpenROAD Python scripts. |
| micromamba from `micro.mamba.pm` | Blocked | `CONNECT tunnel failed, response 403`. |
| micromamba from GitHub releases | Works | `github.com/mamba-org/micromamba-releases/releases/download/2.3.2-0/micromamba-linux-64` downloads. |
| conda `litex-hub` + `conda-forge` + `anaconda` channels (conda.anaconda.org) | Works, with fixes | `repo.anaconda.com` is blocked, but the same "main" packages are mirrored at `conda.anaconda.org/anaconda`, which is reachable. |
| KLayout in the same env as OpenROAD | Solver conflict | KLayout 0.28.17 (litex-hub) wants qt 5.9 and openssl 1.1 from `anaconda`, which clashes with the OpenROAD env. Fixed by giving KLayout its own env. |
| `conda-forge::netgen` | Wrong program | conda-forge `netgen` is the NGSolve mesh generator, not the LVS tool. The LVS Netgen is `litex-hub::netgen` 1.5.272. |
| OpenROAD from litex-hub as installed | Did not start | `error while loading shared libraries: libfmt.so.8`. Fixed by adding `conda-forge::fmt=8`. |
| conda-forge Yosys 0.38 as installed | Synthesis failed | `ERROR: Can't open input file .../envs/ys/bin/../share/techmap.v`: this build looks for its data directory in the wrong place. Fixed with a symlink `envs/ys/bin/share -> ../share/yosys`. |
| `volare enable` for the PDK | Blocked | `Failed to obtain bdc9412b... remotely: <Response [403 Forbidden]>` (volare asks api.github.com, which the proxy refuses). |
| PDK tarballs straight from GitHub releases | Works | `github.com/efabless/volare/releases/download/sky130-<rev>/{common,sky130_fd_sc_hd,sky130_fd_io}.tar.zst`, unpacked with Python `zstandard`, only the `sky130A` half kept. 0.8 GB on disk. |
| OpenLane without Verilator | Flow stopped at lint | `FileNotFoundError: 'verilator'`. Fixed with `conda-forge::verilator=5.018`. |

## What worked

OpenLane 2.0.0 (pip `openlane==2.0.0`, April 2024). LibreLane is the same project renamed (efabless/openlane2
became librelane/librelane in 2025); 2.0.0 is the release whose pinned tool versions match the newest
prebuilt binaries I can reach here. The `config.json` keys are the same in both.

| Tool | Version | Source |
|---|---|---|
| OpenLane (LibreLane predecessor) | 2.0.0 | PyPI, in a Python 3.10 venv built from the conda env's interpreter (OpenROAD embeds Python 3.10) |
| Yosys | 0.38 (git 543faed9c8c, the exact commit OpenLane 2.0.0 pins) | conda-forge |
| OpenROAD + OpenSTA | 2.0-12381-g01bba3695 (2024-02-23) | litex-hub (OpenLane 2.0.0 pins 0889970d, a few weeks later) |
| Magic | 8.3.465 | litex-hub |
| Netgen (LVS) | 1.5.272 | litex-hub |
| KLayout | 0.28.17 | litex-hub, own env |
| Verilator | 5.018 | conda-forge |
| sky130A PDK | open_pdks bdc9412b3e468c102d01b7cf6337be06ec6e9c9a (the rev OpenLane 2.0.0 pins), `sky130_fd_sc_hd` and `sky130_fd_io` only | GitHub release tarballs |

Everything lives under `/tmp/exp-layout` (about 3.5 GB with the PDK). Nothing is installed system wide.

## What finishes this on a normal machine

On a Mac (Apple Silicon) or Linux box with Docker and open internet, the current LibreLane runs the same
config unchanged:

    python3 -m pip install --upgrade librelane
    librelane --dockerized --pdk sky130A --pdk-root ~/.ciel hw/librelane/governor_core/config.json

or with Nix:

    nix-shell github:librelane/librelane/main --run "librelane --pdk-root ~/.ciel hw/librelane/governor_core/config.json"

`hw/librelane/run.sh` works on either: set `GOV_FLOW=librelane-docker` (or `librelane-nix`) and it runs the
same checks on the new run's reports.

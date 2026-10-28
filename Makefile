.PHONY: lanes figures docx run test rtl rtl-test sweep demo bench gds loop clean interfaces prove redteam
run:      ; ./run.sh
test:     ; python3 -m pytest -q tests
rtl-test: ; python3 -m pytest -q rtl/tests
rtl:      ; python3 -m rtl.gen
sweep:    ; python3 -m govsim.cli sweep
demo:     ; python3 -m govsim.cli demo
bench:    ; python3 -m govsim.cli bench
figures:  ; python3 docs/figures/make_figures.py
docx:     ; python3 docs/tools/build_master_docx.py
gds:      ; python3 -m pip install -q --upgrade librelane && librelane --dockerized --pdk-root $(HOME)/.ciel hw/librelane/governor_core/config.json
loop:     ; python3 hw/loop/run_loop.py
interfaces: ; python3 -m govsim.hardware_ref
proof:    ; python3 proofs/core_invariants.py && python3 proofs/commit_point.py && python3 proofs/no_global_kill_switch.py
prove:    ; python3 -m govsim.prove
redteam:  ; python3 -m govsim.redteam
clean:    ; rm -rf .venv .pytest_cache govsim/__pycache__ tests/__pycache__ rtl/__pycache__ rtl/governor_rtl/__pycache__ rtl/tests/__pycache__ hw/librelane/governor_core/runs
archive:  ; python3 tools/archive/build_archive.py --out build/archive --repo . --repo ../hardware-and-silicon && python3 tools/archive/build_project_docs.py --out build/project --governor . --stack ../hardware-and-silicon
HW ?= $(firstword $(wildcard ../hardware-and-silicon ../../../hardware-and-silicon $(HOME)/hardware-and-silicon))
SAFETY ?= $(firstword $(wildcard ../safety ../../../safety $(HOME)/safety))
lanes:
	@test -n "$(SAFETY)" || { echo "lanes: the safety repository was not found; set SAFETY=<path>"; exit 1; }
	@test -n "$(HW)" || { echo "lanes: hardware-and-silicon was not found; set HW=<path>"; exit 1; }
	python3 -m lanes.check --observer $(SAFETY)/observer --hardware $(HW)
	python3 catalogue/export.py $(HW) --check

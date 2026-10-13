.PHONY: run test rtl rtl-test sweep demo bench gds clean
run:      ; ./run.sh
test:     ; python3 -m pytest -q tests
rtl-test: ; python3 -m pytest -q rtl/tests
rtl:      ; python3 -m rtl.gen
sweep:    ; python3 -m govsim.cli sweep
demo:     ; python3 -m govsim.cli demo
bench:    ; python3 -m govsim.cli bench
gds:      ; docker run --rm -v "$(PWD)":/work -w /work/hw/openlane/governor_core ghcr.io/efabless/openlane2:latest openlane config.json
clean:    ; rm -rf .venv .pytest_cache govsim/__pycache__ tests/__pycache__ rtl/__pycache__ rtl/governor_rtl/__pycache__ rtl/tests/__pycache__ hw/openlane/governor_core/runs

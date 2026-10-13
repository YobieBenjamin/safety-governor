.PHONY: run test rtl rtl-test sweep demo bench gds clean
run:      ; ./run.sh
test:     ; python3 -m pytest -q tests
rtl-test: ; python3 -m pytest -q rtl/tests
rtl:      ; python3 -m rtl.gen
sweep:    ; python3 -m govsim.cli sweep
demo:     ; python3 -m govsim.cli demo
bench:    ; python3 -m govsim.cli bench
gds:      ; python3 -m pip install -q --upgrade librelane && librelane --dockerized --pdk-root $(HOME)/.ciel hw/librelane/governor_core/config.json
clean:    ; rm -rf .venv .pytest_cache govsim/__pycache__ tests/__pycache__ rtl/__pycache__ rtl/governor_rtl/__pycache__ rtl/tests/__pycache__ hw/librelane/governor_core/runs

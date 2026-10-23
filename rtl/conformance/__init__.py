"""Spec conformance testing for the governor's hard core: does the RTL do what docs/04 and docs/07 say?

    python -m rtl.conformance            # everything: quotes, tests, differential, catalogue, mutants, report
    python -m rtl.conformance --quick    # the same without the mutation sample
    python -m rtl.conformance --write    # also regenerate rtl/conformance/REQUIREMENTS.md

See PLAIN-ENGLISH.md for what this is, REQUIREMENTS.md for the table, FINDINGS.md for what disagreed.
"""

TEST_MODULES = ("tests_blocks", "tests_differential", "tests_findings", "tests_calls")


def load_tests() -> None:
    import importlib
    for m in TEST_MODULES:
        importlib.import_module(f"{__name__}.{m}")

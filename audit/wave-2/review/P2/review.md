## Review of `exp/p2`: **revise** (the model review could not be trusted; a person decides)

Verifier: clean; model review on ?: 0 blocking, 0 warnings, 0 unsupported claim(s) of 0; estimated $0.91, 13 turns.

### Verifier findings

- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:7: 10333`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:7: 001`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:33: 54`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:34: 54`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:35: 11`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:38: 06034`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:38: 002`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:41: 2.0`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:42: 3.3`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:46: 16`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:46: 16`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:50: 12`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:54: 18`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:54: 16`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:54: 16`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:65: 2.2`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:66: 2.2`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:66: 1.2`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:67: 101024`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:72: 12143`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:72: 001`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:74: 678`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:76: 10577`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:76: 11133`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:76: 12`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:76: 11133`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:76: 11470`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:86: 10333`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:86: 001`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:87: 06034`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:87: 002`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/research/exit-register.md:89: 2.2`

### suite in a clean checkout: exit 0

```
j5tycqcyww0000gn/T/verify-cho_is_c/tests/test_h20_exits.py:45: UserWarning: 12 rows wait on the HGX design guide or a board document: ['X04', 'X11', 'X12', 'X17', 'X21', 'X23', 'X24', 'X25', 'X26', 'X27', 'X28', 'X30']
    warnings.warn(f"{len(nda)} rows wait on the HGX design guide or a board document: {nda}")

tests/test_h20_exits.py::test_register_matches_the_models_enumeration
  /private/var/folders/30/33qb062d34q5p1j5tycqcyww0000gn/T/verify-cho_is_c/tests/test_h20_exits.py:109: UserWarning: the model bricks these exits by policy but the register cannot show it: ['jtag', 'debug']
    warnings.warn(f"the model bricks these exits by policy but the register cannot show it: {unshown}")

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
209 passed, 2 warnings in 2.85s

```

### acceptance in a clean checkout: exit 0

```
te/var/folders/30/33qb062d34q5p1j5tycqcyww0000gn/T/verify-cho_is_c/tests/test_h20_exits.py:45: UserWarning: 12 rows wait on the HGX design guide or a board document: ['X04', 'X11', 'X12', 'X17', 'X21', 'X23', 'X24', 'X25', 'X26', 'X27', 'X28', 'X30']
    warnings.warn(f"{len(nda)} rows wait on the HGX design guide or a board document: {nda}")

tests/test_h20_exits.py::test_register_matches_the_models_enumeration
  /private/var/folders/30/33qb062d34q5p1j5tycqcyww0000gn/T/verify-cho_is_c/tests/test_h20_exits.py:109: UserWarning: the model bricks these exits by policy but the register cannot show it: ['jtag', 'debug']
    warnings.warn(f"the model bricks these exits by policy but the register cannot show it: {unshown}")

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html

```

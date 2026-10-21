"""Write catalogue/attacks.json from hardware_ref/attacks.py (the source of truth for the entries today).

    python3 catalogue/export.py ../hardware-and-silicon            # rewrite attacks.json
    python3 catalogue/export.py ../hardware-and-silicon --check    # fail if attacks.json differs from the live catalogue

Only data is exported: name, layer, expect, description. The attack bodies stay code in hardware_ref.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).parent


def live(repo: str) -> list[dict]:
    sys.dont_write_bytecode = True
    sys.path.insert(0, repo)
    from hardware_ref.attacks import CATALOGUE
    return [{"name": a.name, "layer": a.layer, "expect": a.expect, "description": a.description} for a in CATALOGUE]


def document(entries: list[dict]) -> dict:
    return {"source": "hardware_ref/attacks.py", "attacks": sum(e["expect"] == "blocked" for e in entries),
            "baselines": sum(e["expect"] == "allowed" for e in entries), "entries": entries}


def main(argv: list[str]) -> int:
    repo = argv[1]
    text = json.dumps(document(live(repo)), indent=1, ensure_ascii=False) + "\n"
    target = HERE / "attacks.json"
    if "--check" in argv:
        if target.read_text() != text:
            print("catalogue/attacks.json differs from hardware_ref.attacks.CATALOGUE; rerun export.py")
            return 1
        return 0
    target.write_text(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

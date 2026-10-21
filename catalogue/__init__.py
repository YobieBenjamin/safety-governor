"""The attack and baseline catalogue as data. `load()` is what govsim, hardware_ref and the RTL harness read."""
import json
import pathlib

PATH = pathlib.Path(__file__).with_name("attacks.json")


def load() -> list[dict]:
    return json.loads(PATH.read_text())["entries"]


def names(expect: str | None = None) -> list[str]:
    return [e["name"] for e in load() if expect is None or e["expect"] == expect]

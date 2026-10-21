import subprocess
import sys

import catalogue


def test_catalogue_counts():
    assert len(catalogue.names("blocked")) == 75
    assert len(catalogue.names("allowed")) == 12


def test_lanes_checker_passes():
    r = subprocess.run([sys.executable, "-m", "lanes.check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout

"""Run the dependency-free browser-client regressions when the local Node QA tool is available."""
import shutil
import subprocess
from pathlib import Path

import pytest


def test_browser_client_regressions():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is optional for client QA; it is not a desk runtime dependency")
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([node, "--test", "tests/frontend.test.cjs"], cwd=root, capture_output=True,
                            text=True, encoding="utf-8", timeout=45)
    assert result.returncode == 0, result.stdout + result.stderr

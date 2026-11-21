import pytest

from eventstudy.pipeline import verify_fingerprints
from eventstudy.storage import sha256


def test_concurrent_input_change_invalidates_run(tmp_path):
    path = tmp_path / "input.csv"
    path.write_text("original")
    fingerprints = {"input.csv": sha256(path.read_bytes())}
    verify_fingerprints(tmp_path, fingerprints)
    path.write_text("changed")
    with pytest.raises(ValueError, match="changed during run"):
        verify_fingerprints(tmp_path, fingerprints)


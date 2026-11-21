"""Rerun genuine cached inputs and compare every prior processed CSV/JSON/PNG hash."""
import json
from pathlib import Path

from eventstudy.pipeline import run
from eventstudy.storage import load_config, sha256, write_json


def main():
    root = Path(__file__).resolve().parents[1]
    config = load_config(root / "configs/study.yaml")
    folder = root / config["paths"]["data"] / "processed"
    before = {p.relative_to(folder).as_posix(): sha256(p.read_bytes()) for p in folder.rglob("*") if p.is_file()}
    if not before:
        raise ValueError("Run genuine analysis once before checking cached reproduction")
    summary = run(config)
    after = {p.relative_to(folder).as_posix(): sha256(p.read_bytes()) for p in folder.rglob("*") if p.is_file()}
    differences = {name: {"before": before.get(name), "after": after.get(name)}
                   for name in sorted(before.keys() | after.keys()) if before.get(name) != after.get(name)}
    result = {"files_compared": len(before), "identical": not differences, "differences": differences,
              "run_summary": summary}
    write_json(root / "reports/cached_reproduction_check.json", result)
    print(json.dumps(result, indent=2))
    return 0 if not differences else 1


if __name__ == "__main__":
    raise SystemExit(main())


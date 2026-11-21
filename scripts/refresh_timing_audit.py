"""Rebuild the deterministic evidence packet strictly from pinned SEC cache."""
from pathlib import Path

from eventstudy.collection import audit_filings, make_client
from eventstudy.pipeline import records
from eventstudy.storage import load_config, read_csv, write_json

root = Path(__file__).resolve().parents[1]
config = load_config(root / "configs/study.yaml")
folder = root / config["paths"]["data"] / "interim"
candidates = read_csv(folder / "candidate_events.csv")
packet = audit_filings(records(candidates), make_client(config, offline=True), config["study"]["audit_size"])
write_json(folder / "release_audit.json", packet)
print(f"Rebuilt {len(packet)} filing/exhibit evidence packets; no network requests")


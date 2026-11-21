"""Genuine three-company source/arithmetical preflight; never substitutes for full universe."""
import json
from pathlib import Path

from eventstudy.pipeline import analyze_inputs
from eventstudy.prices import fetch_prices
from eventstudy.storage import load_config, read_csv

root = Path(__file__).resolve().parents[1]
config = load_config(root / "configs/study.yaml")
folder = root / "data/interim/pilot"
prices = {}
for ticker in ["AAPL", "JPM", "CAT", "SPY"]:
    prices[ticker], _ = fetch_prices(ticker, config["study"]["price_start"],
                                     config["study"]["price_end_exclusive"], root / "data/raw/prices", offline=True)
summary = analyze_inputs(config, read_csv(folder / "all_filings.csv"), read_csv(folder / "candidate_events.csv"),
                         read_csv(folder / "issuer_coverage.csv"), prices,
                         json.loads((folder / "source_failures.json").read_text()), root / "reports/pilot",
                         run_robustness=False)
print(json.dumps(summary, indent=2))


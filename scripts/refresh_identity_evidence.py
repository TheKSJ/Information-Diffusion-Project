"""Recheck unresolved annual identity evidence; preserves the original failure ledger."""
import json
from pathlib import Path

import pandas as pd

from eventstudy.collection import historical_identity, make_client
from eventstudy.pipeline import records
from eventstudy.storage import load_config, read_csv, snapshot_manifest, utc_now, write_csv, write_json
from eventstudy.validation import validate_config

root = Path(__file__).resolve().parents[1]
config = load_config(root / "configs/study.yaml")
folder = root / "data/interim"
identity = read_csv(folder / "historical_identity.csv")
coverage = read_csv(folder / "issuer_coverage.csv")
candidates = read_csv(folder / "candidate_events.csv")
unresolved = identity[~identity.historical_cover_verified]
if not (root / "reports/initial_identity_failures.csv").exists():
    write_csv(root / "reports/initial_identity_failures.csv", unresolved)
client = make_client(config)
filings = read_csv(folder / "all_filings.csv", usecols=["ticker", "form", "filingDate", "accessionNumber", "primary_document_url", "source_url"])
for ticker in sorted(unresolved.ticker.unique()):
    issuer = validate_config(config).query("ticker == @ticker").iloc[0].to_dict()
    metadata, _ = client.json(f"https://data.sec.gov/submissions/CIK{int(issuer['cik']):010d}.json")
    valid, evidence = historical_identity(issuer, metadata, records(filings[filings.ticker == ticker]), client)
    identity = identity[identity.ticker != ticker]
    identity = pd.concat([identity, pd.DataFrame(evidence)], ignore_index=True)
    coverage.loc[coverage.ticker == ticker, "historical_identity_verified"] = valid
    candidates.loc[candidates.ticker == ticker, "historical_identity_verified"] = valid
    print(f"{ticker}: {sum(row['historical_cover_verified'] for row in evidence)}/5 annual identity sources corroborated; valid={valid}")
write_csv(folder / "historical_identity.csv", identity.sort_values(["ticker", "year"]))
write_csv(folder / "issuer_coverage.csv", coverage)
write_csv(folder / "candidate_events.csv", candidates)
manifest = json.loads((folder / "fetch_manifest.json").read_text())
manifest["identity_evidence_refreshed_at"] = utc_now()
manifest["snapshots"] = snapshot_manifest(root / "data/raw")
write_json(folder / "fetch_manifest.json", manifest)


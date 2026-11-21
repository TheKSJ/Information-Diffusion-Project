# Synthetic fixtures only

All synthetic companies use SYN-prefixed tickers and explicit fixture labels. They are not
real SEC observations. The small JSON fixture here is for parallel-array/item classification.
The deterministic end-to-end generator lives in eventstudy.demo, uses actual calendar dates
with simulated price processes, and deliberately injects bad-Z acceptance timestamps.
No demo outputs are merged into data/raw, data/processed, or reports/live.


# IDL-REQ-0003 — a bounded graph of the pack

One aggregated endpoint family (`/v1/graph`, `/v1/graph/node/{id}`, `/v1/graph?q=`)
so the Atlas page can show where a pack's data comes from and how measurements and
recorded names connect — without the consumer inferring relationships or pulling rows.
The fixtures in `dss/contracts/fixtures/graph/` are the acceptance shape; the Atlas UI
ships against them with a labelled sample-data fallback until the endpoint exists.

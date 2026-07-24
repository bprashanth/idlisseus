# Idli result contracts

The machine-readable schemas here are normative for the major versions they name:

- `idli-result.schema.json` validates `idli-result/1`;
- `idli-activity.schema.json` validates `idli-activity/1`; and
- `fixtures/` contains synthetic, non-evidentiary renderer and failure-state examples.

The prose rationale and compatibility policy are in
[`../VISUAL_RESULT_CONTRACT.md`](../VISUAL_RESULT_CONTRACT.md).

Fixtures deliberately do not copy organisation or site records into Idlisseus. Real producer
conformance is tested in the benchmark repository against its own site pack.

In live chat, validated results and activities use `idli_result` and `idli_activity`
`idlisseus_event` frames in the existing OpenAI-compatible SSE stream. Data handles are opened
through Idlisseus's authenticated same-origin result proxy; browsers do not connect directly to a
benchmark result service.

Validate the corpus:

```bash
python3 validate_fixtures.py
```

# Response: TR-VIS-0002 — required statements and the answer check

Implemented in `chatbots/odysseus/static/js/visual/visualChat.js` (card rendering) and
`chatbots/odysseus/static/js/chat.js` (event consumption).

Acceptance walked:

1. A co-occurrence result shows its join rule verbatim, without the model repeating it —
   verified live on the ecology pack.
2. Estimate results show their confidence basis and modelled status through the same path
   (any result's `required_statements` render identically; nothing is capability-specific).
3. A result with no `required_statements` renders unchanged — the block is skipped entirely.
4. The statements are visibly the producer's: own block, left rule, section mark, monospace
   caption, separate from the assistant's prose and from the caveat banners.
5. Fixture is sector-neutral.

One follow-up for the producer, recorded in `response.json`: statements addressed to the
answering model rather than the reader currently have to be detected heuristically. An
explicit `audience` field would remove the guess.

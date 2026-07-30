# Consumer → producer requests

The proposal channel in `totalrecall/dss/integration/proposals/` is producer-owned: Totalrecall
proposes, Idlisseus responds. This directory is the mirror for the other direction — capability
and data-plane gaps found from the consumer side, written here so neither agent edits the
other's repository.

Layout mirrors the proposal channel:

```text
idlisseus/dss/integration/requests/<request-id>/
├── request.json     schema producer-consumer-request/1
└── README.md        the evidence, in prose
```

A request is not a commitment. Totalrecall may accept it (typically by opening a proposal or
just implementing it), defer it, or reject it with a reason.

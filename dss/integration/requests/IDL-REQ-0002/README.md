# IDL-REQ-0002 — read the word the user actually typed

`elephant` resolves. `elephants` does not. `hornbill` does not, and neither does
`hornbills` — because no entity is called that, and the only thing grouping those birds is
`Bucerotidae`. So the working co-occurrence map can only be reached by typing the exact alias
and the exact Latin family, which is not how anyone asks a question.

The fix is mostly not a model. Substring plus plural-stripping on `hornbill` already returns
three entities, and those three agree on exactly one family — Bucerotidae. That is a SQL query
and a set intersection, and it is right by construction.

A model is needed only for the residue: `raptor`, `shade tree`, `invasives` — groupings that
are not substrings of any recorded name. There its job is not to search but to **choose from
candidates the index supplied**, returning an identifier that already exists, or none.

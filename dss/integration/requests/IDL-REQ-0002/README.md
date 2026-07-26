# IDL-REQ-0002 — read the word the user actually typed

`elephant` resolves. `elephants` does not. `hornbill` does not, and neither does
`hornbills` — because no entity is called that, and the only thing grouping those birds is
`Bucerotidae`. So the working co-occurrence map can only be reached by typing the exact alias
and the exact Latin family, which is not how anyone asks a question.

**Amended after measuring.** The first draft of this request proposed climbing the taxonomy to
find a shared ancestor. That works for `hornbill` — three matched birds, one shared family —
but it does not generalise, and measurement showed why:

- 828 of 1145 entities carry a family. The rest carry none.
- **Every raptor in this pack has an empty hierarchy** — Black Eagle, Crested Serpent-Eagle,
  Brahminy Kite, Peregrine Falcon, Oriental Honey-Buzzard. They arrive from common-name survey
  sheets, not from a taxonomic backbone. There is no ancestor to climb to.
- Substring widening over-reaches anyway: `%falcon%` matches *Falconeria insignis*, a plant.

So the general mechanism is the simpler one: **give the model the site's own entity list and
let it choose the members of the group**, verifying that every id it returns was in the list it
was given. At this scale that costs about 7k tokens, once, cached. The taxonomy then becomes a
way to *describe* the answer — "read as the family Bucerotidae" — rather than the way to find
it, and its absence stops being fatal.

The result must show the reader how the word was read, and let them correct it. A group the
model assembled is a judgement, and it should look like one.

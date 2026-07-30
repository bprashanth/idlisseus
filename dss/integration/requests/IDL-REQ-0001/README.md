# IDL-REQ-0001 — let a reader see a source's own rows

A scientist's trust question is "show me a row". Today the product can say *2,965 records* and
cannot show one of them, because rows only travel as drill-downs hanging off a computed result.

The data is not the problem. The pack stores every source's original files, with a provenance
record naming the DOI, the retrieved version, the licence and the checksum match, and the index
keeps `source_id` + `source_row` on every event, so the way back to the exact line is intact.

What is missing is a route. Adding one also removes a failure mode we saw in the wild: with no
local route, the model reached for the publisher's website, was refused, and told the user the
data could not be reached — while the file was on disk.

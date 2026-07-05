# Roadblocks for the human to clear (overnight benchmark/improve loop)

Things blocking a fully-fair benchmark or a data source. I will NOT manufacture data around these —
I note them here, work around honestly where possible, and you fix them tomorrow + I rerun.

## BLOCKING the fair cursor benchmark
- **[#1] Fresh Cursor account for a CLEAN frontier baseline.** cursor-agent's memory is
  account/cloud-side and is already seeded with our EBTL context (site bbox, connector names, our
  computed numbers, even "the benchmark run") from every prior in-repo cursor call. There is NO
  memory-disable flag. So cursor on THIS account echoes our homework → not a fair "what Varun's
  cursor would say on its own." **Fix: a fresh Cursor account (or a memory/rules wipe) so B is the
  frontier model with its OWN knowledge, not ours.** Until then I run cursor as-is and FLAG per-question
  contamination (`leaked_our_context`); treat flagged questions as "cursor had our data" (an unfair
  edge to cursor, which is fine — if we still win, strong; the clean rerun will widen the margin).

## Anticipated data paywalls / account requirements (the "serious asks")
- **Hyperspectral (Pixxel ~5 m).** EMIT (free, 60 m) only gives a coarse invasive hint. Crisp
  patch-scale invasive/canopy-chemistry mapping needs Pixxel or similar — commercial, tasking/account.
- **Acoustic bird hardware.** AudioMoth + BirdNET deployments for unbiased, absence-aware site birds
  (eBird is effort-biased, no true absence). Hardware + fieldwork, not an API.
- **eBird "landscape"/habitat field.** eBird has no habitat field; birders would need to log it, or we
  keep deriving it from landcover. (We derive it; noting the native-data gap.)
- (Add here as hit: any account-gated dataset, paywalled paper, rate-limited API needing a key.)

## Notes
- eBird key: DONE (working). Dryad key: DONE.
- Update this file as new blocks appear; the human clears them and we rerun.

## Robustness (Hermes infra, not data)
- **execute_code 60s timeout → "denying command" → A returns empty & LOSES (Q11 grazing).** Some
  connector calls (EE reduceToVectors, multi-taxa GBIF, slow EE init) exceed Hermes's 60s tool
  timeout and get denied; if it happens repeatedly A produces no answer. Mitigations applied: PLAYBOOK
  rule "never return empty; retry once smaller then answer anyway" + "keep calls light". POSSIBLE FIX
  for the human: raise the Hermes execute_code/terminal timeout (currently ~60s) so legit EE/GBIF
  calls finish. Also consider trimming the heaviest connector calls (water.ponds reduceToVectors).

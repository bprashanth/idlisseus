# 2-hour POC results — the self-improving connector loop

Run 2026-07-03 on 122B (`vllm-qwen35`) + Hermes (`hermes-agent-local`). This is the
2h version from [`NOTES.md`](NOTES.md): prove the machine end-to-end at N=1 new
connector. **All three success criteria met**, plus two harness bugs surfaced and
fixed (the whole point of running the short version first).

## Verdict on the plan

The loop **works and is worth scaling**. A frontier writer (Claude) manufactured a
validated connector from 122B's failure, gold was minted only from a *tested*
chain, and the ledger entry replays. Two patches were needed before it was safe to
run unattended — both found here, neither fatal. See "Patches" below.

## The three gates (NOTES §"THE 2-HOUR VERSION")

| Criterion | Result |
|---|---|
| **1. Struggle detector fires** | ✅ struggle run hit the **20-min timeout** (`rc=124`, `wall=1204s`), flagged `STRUGGLED=yes` (timeout + slow + failure_phrase). |
| **2. Self-test catches a broken connector** | ✅ `landcover` legend swap (class 50→"Shrubland", the exact v-1 Q5 error) → **REJECTED**. `greenness` scale-factor break (0.0001→1.0, values → thousands) → **REJECTED**. |
| **3. Ledger entry replays** | ✅ `replay.py` re-ran `greenness.trend` from the gold entry → `REPRODUCED` (12 greening / 13 flat / 1 declining). |

## Track A — validate the gate (~4 min of EE calls)

`landcover` self-test on 3 bet-money-on points (empirically confirmed, not guessed):
Coimbatore→Built-up, Manamboli→Tree cover, Parambikulam reservoir→Water. Real
connector **PASS**; corrupted copy **FAIL/REJECTED**. The gate demonstrably catches
a bad connector, so a green self-test now means something.

## Track B — validate the loop (failure → write → retry)

Question: *"For each restoration site, is it greening up 2019–2024? Rank by NDVI
trend."* Input: the 26 staged restoration sites.

| Phase | Runner | Result |
|---|---|---|
| **Struggle** (no `greenness`) | `run_solver.sh` (connectors mounted, EE fallback allowed) | **20 min, hit timeout.** Hand-wrote a per-year Sentinel-2 `reduceRegion`, then thrashed building a venv / `pip install earthengine-api`. Never produced a trend. **This is the v-1 NDVI failure, reproduced live.** |
| **Write + gate** | frontier writes `greenness.trend` (MOD13Q1 NDVI, owns band + 0.0001 scale + slope fit) + self-test | self-test **PASS**; meta-check (broken scale) **REJECTED**. |
| **Mint gold** | tested `greenness.trend` on 26 sites | 12 greening, 13 flat, 1 declining. Top greener **Selaliparai1** (+0.018/yr); sole decliner **OldValparai_Coffee** (mature coffee, saturated). |
| **Re-solve** (with `greenness`) | `run_solver.sh` | **3m10s, 11 tool calls.** Read the card, called `greenness.trend`, wrote **no EE code**, grouped in pandas. |
| **Judge** vs gold | top-5 overlap 5/5, class counts exact, sole decliner exact | **plan_match ✓ number_match ✓** |

**Contrast: 20-min timeout → 3m10s correct answer**, purely from adding one tested
connector. Same result shape as the v-1→connectors QA/QB jump, now produced *by the
loop* rather than by hand.

## The algebra finding

The question forced a primitive the existing five (FIND / LOOK-UP /
SUMMARISE-IN-AREA / RELATE / GROUP) can't express: **TREND** — a slope over time,
not a single map value. This is the first "over time" breaker from VISION.md, and
it's now a validated primitive. Plan skeleton: **FIND → TREND → GROUP**. `greenness`
is its first implementation.

## Patches that came out of the POC (why the 2h run earned its keep)

1. **Hard timeout on every Solver run (critical).** The stock `run_v-1.sh` /
   `run_connectors.sh` `exec docker run` with no bound; the struggle run would have
   **hung indefinitely** (it was still churning at 20 min). `run_solver.sh` wraps
   the call in `timeout` and treats `rc=124` as a struggle. This is the "don't come
   back to find Hermes hung" guarantee — validated by an actual 20-min hang caught.
2. **Struggle-detector false positive on container noise.** The detector matched
   `"unable to"` in an **s6 init line** (`s6-applyuidgid: … unable to set
   supplementary group list`), flagging a *correct* re-solve as struggled. Fixed:
   `detect_struggle.sh` strips container-plumbing lines before phrase-matching, and
   is factored out so saved logs can be re-scored. Re-scored both runs:
   struggle=yes, resolve=no. ✅

## Harness built (reusable for the 16h run)

- `run_solver.sh` — Hermes/122B with the **current** connector set mounted, hard
  timeout, trace log, struggle verdict. (The runner NOTES §2/§6 assumed but neither
  existing script was.)
- `run_selftest.sh` + `detect_struggle.sh` — the gate and the trigger, factored out.
- `tests/test_landcover.py`, `tests/test_greenness.py` — ground-truth self-tests
  (also copied to `connectors/selftests/` as regression guards).
- `replay.py` — re-runs a ledger chain and asserts the gold reproduces.
- `ledger/ledger.jsonl` — the first benchmark entry (§7 schema); `ledger/gold_*`.

## Ready for the 16-hour run? Yes, with these still to add (NOTES "BRIDGE")

- **Curriculum Controller** — bump difficulty when 122B pass-rate ≥ 80% over last K.
- **Session miner** — read `state.db` across runs → permanent playbook rules.
- **EE quota is the throughput ceiling** — serialize, or parallelize only within
  quota. The 2h run was serial and fine.
- **Phantom-data guard + dedup** on proposed questions (frontier must verify a
  source is queryable before admitting a question).

Nothing structural blocks the 16h run — it's this same tick left running with the
curriculum + miner attached.

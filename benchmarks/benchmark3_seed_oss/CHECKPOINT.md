# Checkpoint log — Benchmark 3 (Seed-OSS-36B vs ds4, literature/document synthesis)

Read this first if context has been compacted. Append a new dated entry after every phase
boundary. Don't rewrite history — append only.

## 2026-06-25 02:57 — Setup launched

- ds4-server stopped (memory: Seed-OSS-36B BF16 needs ~72GB, ds4 alone uses ~108GB of 121GB,
  cannot coexist — confirmed before starting, see PLAN.md).
- Container `seed-oss-vllm` launched: vLLM (`vllm/vllm-openai:cu130-nightly`, already cached from
  Benchmark 2), single GPU (`--tensor-parallel-size 1`, adapted from NVIDIA's 8-GPU example),
  native BF16, `--max-model-len 65536`, `--enable-auto-tool-choice --tool-call-parser seed_oss`,
  bound to `172.17.0.1:8000` (docker bridge IP, same security pattern as every other model this
  session). **Clean startup, no errors** — notably no speculative-decoding config (unlike
  Nemotron-3, which is what broke under long context), no context-window override warning.
- 5 papers picked from Benchmark 2's real downloaded corpus, copied + pdftotext-extracted into
  `benchmark3_seed_oss/papers/` (01, 03, 09, 11, 16 — see PLAN.md for why each was picked).
  Combined 11,765 words (~15-16K tokens), well within context for both models.
- Confirmed earlier (documented in PLAN.md): ds4's "deepseek-v4-pro" option in Odysseus is NOT a
  second model — same loaded q2-imatrix Flash GGUF served under an alias, per ds4's own
  `--help` text. Not relevant to this benchmark directly, but recorded for the record.

## 2026-06-25 03:24 — Download in progress, healthy

- 19GB of 72.3GB after ~26min, no errors, container "Up". No stall detected (will compare growth
  rate against next check). Direct curl to /v1/models still empty/not-yet-serving (expected,
  still downloading + will need engine warmup after).
- Leftover Nemotron-3 cache (~76GB) still in `~/.cache/huggingface` from Benchmark 2, not yet
  cleaned up — fine for now, 626GB free disk, not urgent.
- Next: keep monitoring for stall (same pattern as Nemotron: compare cache-dir size across
  checks, check `.incomplete` blob mtimes if growth stops). Once server responds: run smoke
  tests (non-streaming + streaming /v1/chat/completions, trivial prompt), then the 5-task
  battery from PLAN.md against seed-oss-36b while it's up, then swap to ds4 (stop seed-oss-vllm,
  start ds4-server) and run the identical battery against ds4, then restore ds4 as final state.
- ds4-server currently DOWN (deliberately, for Seed-OSS's memory budget).

## 2026-06-25 03:50 — Download healthy, ~half done

- 37GB of 72.3GB, container up 52min, no errors. Growth rate ~0.69GB/min (19GB->37GB over 26min),
  consistent with prior downloads this session. ETA roughly 50 more minutes. Server not yet
  responding (expected). Continuing to wait.

## 2026-06-25 04:21 — Download nearly done

- 60GB of 72.3GB, ~12GB remaining at ~0.77GB/min -> ETA ~15min, then engine warmup. No errors,
  no stall. Continuing to wait.

## 2026-06-25 04:38 — Seed-OSS up, task battery running

- Server up, smoke tests passed (non-streaming + streaming both clean). Note: Seed-OSS embeds
  reasoning inline as `<seed:think>...</seed:think>` tags in the response content itself (not a
  separate field like Nemotron's reasoning_parser) - account for this when reading responses.
- Task 1 (single-doc summary) done: 287.9s, 4529 prompt tokens, 928 completion tokens (~3.2
  effective tok/s for full round trip including prefill).
- Tasks 2-4 running in background (pid 385338, log seed_oss_run.log) - task 2 (multi-doc
  synthesis, ~15K prompt tokens) likely the slowest. Will take a while given the slow decode
  rate observed.
- All outputs saving to benchmark3_seed_oss/seed_oss_results/ as taskN_prompt.txt /
  taskN_response.txt / taskN_response.json via run_task.py.

## 2026-06-25 10:39 — Task 1, 3 done; task 2 needs retry; fixed script timeout

- Task 1 (single summary): done, 287.9s.
- Task 2 (multi-doc synthesis, ~15K prompt tokens): TIMED OUT at my script's hardcoded 600s
  urllib timeout (not a model/server failure - server was still working, my client gave up too
  early). Needs retry.
- Task 3 (targeted Q&A): done, 528.4s, 10014 prompt tokens, 1658 completion tokens.
- Task 4 (dashboard): was running when discovered, likely to hit the same 600s timeout given it
  also uses all 5 docs (similar size to task 2) plus needs a long structured HTML response.
- Fixed run_task.py: bumped urllib timeout from 600s to 1800s. Waiting for task 4's current
  (old-timeout) attempt to resolve, then will retry both task 2 and task 4 with the fixed script.
- Files so far in seed_oss_results/: task1_*, task3_* complete. task2_prompt.txt exists (written
  before the timeout) but no task2_response - will be overwritten on retry.

## 2026-06-25 10:48 — Both timeouts were client-side bugs, not server failures; real finding emerging

- Task 4's 1800s attempt also timed out client-side, but `nvidia-smi` showed GPU at 0% right
  after (request had finished/been cancelled around the timeout boundary) and vLLM's own logs
  showed sustained "Avg generation throughput: ~3.0-3.1 tokens/s" the whole time it was running -
  confirms the model IS just genuinely slow at this, not stuck.
- **Real finding so far:** Seed-OSS-36B's observed decode rate (~3 tok/s) is roughly 5x SLOWER
  than ds4's baseline (~15 tok/s) for these long-document-context tasks. This runs directly
  counter to the hypothesis motivating this benchmark ("maybe Seed-OSS is better for quicker
  tasks") - worth flagging prominently once the comparison data is complete. Single-GPU BF16 for
  a 36B dense model without any optimization (no speculative decoding, no quantization) may
  simply not be tuned for throughput on this hardware the way ds4's hand-written CUDA kernels are.
- Bumped run_task.py timeout to 3600s, retrying tasks 2 and 4 now (seed_oss_run2.log, pid 394242).
  Given the observed ~3 tok/s rate, task 4 (long HTML output) could take 20-40+ minutes for
  generation alone on top of prefill - this is expected, not a stall, as long as vLLM's own
  logged generation throughput stays > 0.

## 2026-06-25 11:21 — Task 2 succeeded with fixed timeout, quality is notably careful

- Task 2: 1229.2s, 20379 prompt tokens, 3785 completion tokens. Confirms the 3600s timeout fix
  works.
- **Quality finding worth keeping for the report:** Seed-OSS's visible reasoning trace explicitly
  worked through whether the Mahua-cause paper (16) contradicts the general-anthropogenic-cause
  paper (01), and concluded there is NO real disagreement (Mahua collection is presented as a
  specific example/subset of human-caused fires, not a contradicting claim) - rather than
  manufacturing a disagreement just because the prompt asked for one. This is arguably a more
  careful/honest reading than what ds4-agent and Hermes+ds4 both claimed in Benchmark 2 (they
  both described this as a real disagreement). Worth a careful side-by-side re-read when writing
  the final report - it's possible Seed-OSS is right and the earlier benchmark's framing was a
  slight overreach, or vice versa - don't just assume Seed-OSS is correct without re-checking the
  actual paper texts.
- Task 4 still running, GPU 96% utilized, steady ~3 tok/s generation throughput confirmed via
  vLLM's own logs - genuinely working, not stalled. Continuing to wait.

## 2026-06-25 11:42 — Task 4 + 5 done, all 5 seed-oss tasks complete

- Task 4 (dashboard): 1699.9s, 5221 completion tokens. Extracted clean HTML to
  seed_oss_results/task4_dashboard.html - verified: all tags balanced, ZERO external
  dependencies (no CDN links, no <script> tags at all - the "chart" is pure CSS bars). This is
  genuinely the most self-contained dashboard of any produced across all 3 benchmark rounds so
  far (ds4-agent and Hermes+ds4 both linked Chart.js/Plotly via CDN in Benchmarks 1-2).
- Task 5 (short-prompt latency) - HEADLINE FINDING, cuts directly against this benchmark's
  motivating hypothesis: "What is 2+2?" took 59.4s (198 completion tokens, ~3.3 tok/s decode -
  same rate as the long-document tasks, so this isn't a context-length issue). "Name three
  colors" took 42.25s, "spell banana backwards" took 82.91s. In every case nearly all tokens
  went to a visible <seed:think> reasoning block before the actual short answer. Seed-OSS in
  this serving config is dramatically SLOWER for quick interactive queries than ds4
  (~15 tok/s, no mandatory extensive reasoning) - the opposite of what motivated trying it.
  Note for the report: Seed-OSS's model card mentions a "Thinking Budget Feature" that can
  likely be tuned/disabled - this may be a fixable config issue (similar to how Nemotron-3's
  failure was specifically about speculative decoding, not the model itself) rather than an
  inherent limitation. Worth flagging as a next step to try, not a final verdict on the model.
- All 5 seed-oss tasks done and saved in seed_oss_results/. Now proceeding to stop seed-oss-vllm,
  start ds4-server, and run the identical battery against ds4 for direct comparison.

## 2026-06-25 12:01 — All data collection complete: full elapsed-time comparison

| Task | Seed-OSS-36B | ds4 (DeepSeek V4 Flash) | ds4 speedup |
|---|---:|---:|---:|
| 1. Single-doc summary | 287.9s (928 completion tok) | 69.8s (813 completion tok) | ~4.1x |
| 2. Multi-doc synthesis | 1229.2s (3785 completion tok) | 193.1s (1925 completion tok) | ~6.4x |
| 3. Targeted Q&A | 528.4s (1658 completion tok) | 118.6s (1280 completion tok) | ~4.5x |
| 4. Dashboard HTML | 1699.9s (5221 completion tok) | 648.9s (7978 completion tok) | ~2.6x |
| 5a. "What is 2+2?" | 59.4s (198 tok) | 3.53s (47 tok) | ~16.8x |
| 5b. "Name three colors" | 42.25s (140 tok) | 2.14s (30 tok) | ~19.7x |
| 5c. "Spell banana backwards" | 82.91s (275 tok) | 6.14s (92 tok) | ~13.5x |

ds4 is faster on every single task, and the gap is most extreme on short/trivial prompts
(13-20x) - the exact opposite of the hypothesis that motivated this benchmark ("maybe Seed-OSS
is better for quicker tasks"). Root cause: Seed-OSS defaults to extensive visible
`<seed:think>` reasoning even for trivial queries, and its sustained decode rate (~3 tok/s) is
roughly 5x slower than ds4's (~15 tok/s) regardless of task.

Quality findings (not just speed):
- Task 2 disagreement-finding: ds4 found a more thorough, well-triangulated 3-axis disagreement
  analysis (cause-specificity across 3 papers, tech-vs-traditional, policy-vs-feasibility, all
  with specific paper-name citations) in 1925 tokens / 193s. Seed-OSS's reasoning concluded NO
  real disagreement exists (comparing only 2 of the 5 papers directly) in 3785 tokens / 1229s -
  more cautious, but possibly under-exploring papers 03/04/09's relevant framing differences.
  ds4's answer reads as more complete on this task, not just faster.
- Task 4 dashboards: BOTH models produced fully self-contained HTML with zero external CDN
  dependencies when called directly via API (no agent) - Seed-OSS via pure CSS bars, ds4 via a
  hand-drawn <canvas> chart. Both tag-balance-verified well-formed. This is notably better than
  every agent-driven dashboard from Benchmarks 1-2, which all linked Chart.js/Plotly via CDN -
  suggests the CDN-linking behavior is agent-harness-influenced, not a base-model tendency.

All data collection for Benchmark 3 is now complete. ds4-server is the final running state
(confirmed up). seed-oss-vllm container stopped (had --rm, auto-removed). Report NOT yet
written per user's explicit instruction - awaiting their review/go-ahead in a later turn.

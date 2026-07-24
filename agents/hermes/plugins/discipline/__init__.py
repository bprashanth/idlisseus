"""discipline plugin — the benchmark-winning behavior, delivered natively in the real hermes chat.

Why this exists: the constitution PROSE (short/clarify/compute-fresh) is loaded every turn but qwen
ignores it; the benchmark's win came from a per-message NUDGE + a tool cap that were only in the test
harness. This plugin puts both into the live chat where the model actually attends to them:
  - pre_llm_call  : inject a STEER into the current user turn (full steer on a NEW turn incl. clarify-first;
                    a light "wrap up" steer on later calls of the same turn).
  - pre_tool_call : count tool calls this turn; past _CAP, BLOCK the tool + say "answer now" (so it
                    finishes a short answer instead of over-running, and never truncates to empty).
Hooks fire automatically every turn — the user types nothing special.
"""
_CAP = 12
_state = {"tools": 0, "last": None}

STEER = (
    "STEER for this reply — treat as a busy field chat, ~1 minute, NOT an essay:\n"
    "• Lead with the finding in 2-4 sentences + real numbers; then 1-3 short follow-up options.\n"
    "• Say clearly what is OBSERVED vs MODELLED, and 'backed by N records'. Never present modelled as observed.\n"
    "• CLARIFY AT MOST ONCE, and only at the very start: if the OPENING request is too vague to act "
    "('tell me about X', 'what's here'), ask ONE short clarifying question and run no tools that turn. "
    "But if the user has ALREADY given any direction (a species, a goal, an answer to your question), "
    "PROCEED and answer now — do NOT ask a second clarifying question; state assumptions if needed.\n"
    "• Get species records ONLY via `points.py get` (it resolves the name) — never call inaturalist/"
    "occurrence with a raw/common name. Keep any paper_data/litscout query to 1-3 words.")

# Batch-vs-serial is MODEL-SPECIFIC: qwen122b emits malformed empty-name calls when it batches
# (isolated test: qwen 2 empty-name calls, deepseek 0), so qwen must serialize; deepseek/glm batch cleanly
# and should run independent reads concurrently (faster). The plugin owns this per-model — NOT a blanket
# SOUL rule (which wrongly slowed every model).
_SERIAL = ("\n• Make ONE tool call per message (this model's batched calls break with an empty tool name); "
           "run a few in sequence, then STOP and answer.")
_BATCH = ("\n• BATCH independent read-only tool calls into ONE turn (they run concurrently — faster); "
          "serialize only when a call needs a prior result. Then STOP and answer.")


def _pre_llm(user_message=None, is_first_turn=None, model=None, **kw):
    msg = (user_message or "").strip()
    if msg.startswith("/"):            # slash-commands (/why etc.) — don't steer
        return None
    if msg and msg != _state["last"]:  # a genuinely NEW user turn → reset the per-turn tool count
        _state["tools"] = 0
        _state["last"] = msg
    tool_rule = _SERIAL if (model and "qwen" in model.lower()) else _BATCH   # qwen batches buggily → serial
    return {"context": STEER + tool_rule}


def _pre_tool(tool_name=None, function_name=None, **kw):
    # L4 guard (LIMITATIONS L4): block a DIRECT occurrence/inaturalist call that passes a --species NAME —
    # it bypasses the points.py resolver, and a common name maps to the wrong species. Scan every kwarg
    # value (robust to the command's exact key). Allow --describe and already-resolved taxon-key calls,
    # and never touch points.py get (which resolves internally). This does NOT count against the cap.
    cmd = " ".join(str(v) for v in list(kw.values()) + [function_name, tool_name] if v).lower()
    if ("--species" in cmd and "--describe" not in cmd
            and ("occurrence.py" in cmd or "inaturalist.py" in cmd) and "points.py" not in cmd):
        return {"action": "block",
                "message": ("BLOCKED (L4): don't call occurrence.py/inaturalist.py with a --species NAME — a "
                            "common name maps to the WRONG species. Use `points.py get --species \"<name>\" "
                            "--bbox w,s,e,n` (it resolves the name + merges GBIF/iNat/paper), then read the "
                            "returned CSV. For an already-resolved id use the connector's taxon-key/--describe.")}
    _state["tools"] += 1
    if _state["tools"] > _CAP:
        return {"action": "block",
                "message": (f"TOOL BUDGET REACHED ({_state['tools']} calls). Do NOT call any more tools. "
                            "Your NEXT message MUST be the final answer as plain TEXT (never empty, never "
                            "another tool call): directly address the user's LATEST request, lead with the "
                            "finding + real numbers, label observed-vs-modelled (backed by N records), and "
                            "end with 1-3 follow-ups.")}
    return None


def register(ctx):
    ctx.register_hook("pre_llm_call", _pre_llm)
    ctx.register_hook("pre_tool_call", _pre_tool)
